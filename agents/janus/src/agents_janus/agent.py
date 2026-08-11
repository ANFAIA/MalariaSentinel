"""MalariaSentinel Janus orchestrator — dual-mode (centinela + dispatcher).

The orchestrator decomposes goals, dispatches specialists, monitors progress,
and finalizes via gawt MCP. It never edits files directly.

Two modes:
- centinela: conversational REPL, interacts with user, delegates implementation
- dispatcher: goal-driven, manages gawt session, coordinates specialists
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Literal

_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from agents_janus.logger import SessionLogger
from agents_janus.observability import ObservabilityMiddleware, SubAgentObservabilityMiddleware

try:
    from deepagents import FilesystemPermission
except ImportError:
    FilesystemPermission = None  # type: ignore[assignment,misc]

# Module-level flags set by CLI before creating the agent
VERIFY_FINALIZE: bool = True
SESSION_LOGGER: SessionLogger | None = None
OBSERVABILITY_MIDDLEWARE: ObservabilityMiddleware | None = None

AGENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
PROJECT_SKILLS = REPO_ROOT / "agents" / "skills"
GLOBAL_SKILLS = Path.home() / ".agents" / "skills"

_ORCHESTRATOR_PROMPT_TEMPLATE = AGENT_DIR / "prompts" / "orchestrator.md.j2"
_ORCHESTRATOR_PROMPT_LEGACY = AGENT_DIR / "prompts" / "orchestrator.md"


def _wrap_with_logging(tool_func):
    """Wrap a tool function to add structured logging + error capture.

    If tool_func is already a BaseTool, return it as-is (middleware handles logging).
    If it's a plain function, wrap it with logging.
    """
    from langchain_core.tools import BaseTool
    if isinstance(tool_func, BaseTool):
        return tool_func

    import functools

    @functools.wraps(tool_func)
    def wrapper(*args, **kwargs):
        import time
        start = time.monotonic()
        error = None
        result = None
        try:
            result = tool_func(*args, **kwargs)
        except Exception as e:
            error = e
        elapsed = time.monotonic() - start

        if SESSION_LOGGER is not None:
            import inspect
            sig = inspect.signature(tool_func)
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()
            input_dict = {k: v for k, v in bound.arguments.items()}

            if error:
                SESSION_LOGGER._append({
                    "event": "tool_error",
                    "ts": SESSION_LOGGER._now_iso(),
                    "tool": tool_func.__name__,
                    "input": input_dict,
                    "error": str(error),
                    "error_type": type(error).__name__,
                    "latency_s": round(elapsed, 3),
                })
            else:
                SESSION_LOGGER.log_tool(
                    tool_name=tool_func.__name__,
                    tool_input=input_dict,
                    output=result,
                    latency_s=elapsed,
                )

        if error:
            raise error
        return result

    return wrapper


def _import_abm_run():
    from agents_janus.tools.abm_tools import abm_run
    return abm_run


def _import_abm_test():
    from agents_janus.tools.abm_tools import abm_test
    return abm_test


def _import_abm_score():
    from agents_janus.tools.abm_tools import abm_score
    return abm_score


def _render_prompt(mode: Literal["centinela", "dispatcher"]) -> str:
    """Render the orchestrator prompt from the Jinja2 template."""
    # Load specialist list from registry for programmatic injection
    from agents_janus.subagents.registry import load_registry
    registry = load_registry()
    specialists = [
        {"name": name, "description": spec.description}
        for name, spec in registry.all().items()
    ]

    try:
        from jinja2 import Environment, FileSystemLoader
        env = Environment(
            loader=FileSystemLoader(str(_ORCHESTRATOR_PROMPT_TEMPLATE.parent)),
            keep_trailing_newline=True,
        )
        template = env.get_template(_ORCHESTRATOR_PROMPT_TEMPLATE.name)
        return template.render(mode=mode, specialists=specialists)
    except Exception:
        # Fallback to legacy static prompt (dispatcher only)
        if _ORCHESTRATOR_PROMPT_LEGACY.exists():
            return _ORCHESTRATOR_PROMPT_LEGACY.read_text()
        return _fallback_prompt(mode)


def _fallback_prompt(mode: str) -> str:
    """Minimal fallback prompt if template + legacy both missing."""
    base = """\
You are the Janus orchestrator. Your role is to coordinate specialist agents.

You do NOT edit files. You DO decompose goals and dispatch specialists.

When you dispatch a specialist, prefix the task with:
- [MODE:research] for investigation
- [MODE:implementation] for file edits
"""
    if mode == "centinela":
        base += """
You are the Centinela — a conversational assistant. You interact with the user,
explain results, and delegate implementation work to the dispatcher via
delegate_to_dispatcher(goal="...").
"""
    else:
        base += """
You are the Dispatcher — a goal-driven agent. You decompose goals, start gawt
sessions, dispatch specialists, monitor progress, and finalize.
"""
    return base


# ── Tool sets ───────────────────────────────────────────────────────────

def _get_dispatcher_tools():
    """Tools for dispatcher mode: pipeline, ABM, search, memory."""
    from agents_janus.tools import (
        web_search,
        pipeline_run_calibration,
        pipeline_compare_scorecards,
        memory_recall_kg,
        ask_user,
    )
    return [
        _wrap_with_logging(web_search),
        _wrap_with_logging(_import_abm_run()),
        _wrap_with_logging(_import_abm_test()),
        _wrap_with_logging(_import_abm_score()),
        _wrap_with_logging(pipeline_run_calibration),
        _wrap_with_logging(pipeline_compare_scorecards),
        _wrap_with_logging(memory_recall_kg),
        _wrap_with_logging(ask_user),
    ]


def _get_centinela_tools():
    """Tools for centinela mode: onboard tools + memory + ask_user."""
    from agents_janus.tools.kg_tool import memory_recall_kg
    from agents_janus.tools.ask_user_tool import ask_user
    from agents_janus.tools.onboard_tools import (
        onboard_run_abm,
        onboard_run_stage,
        onboard_run_pipeline,
        onboard_status,
        onboard_diagnose,
        onboard_list_components,
        delegate_to_dispatcher,
        onboard_ask_subagent,
    )
    return [
        _wrap_with_logging(onboard_run_abm),
        _wrap_with_logging(onboard_run_stage),
        _wrap_with_logging(onboard_run_pipeline),
        _wrap_with_logging(onboard_status),
        _wrap_with_logging(onboard_diagnose),
        _wrap_with_logging(onboard_list_components),
        _wrap_with_logging(delegate_to_dispatcher),
        _wrap_with_logging(onboard_ask_subagent),
        _wrap_with_logging(memory_recall_kg),
        _wrap_with_logging(ask_user),
    ]


MEMORY_FILES = [str(AGENT_DIR / "AGENTS.md")]


def _resolve_provider(provider: str, model: str):
    """Resolve the LLM based on provider and model."""
    if provider == "openrouter":
        try:
            from langchain_openai import ChatOpenAI
        except ImportError:
            raise ImportError(
                "langchain-openai is required for OpenRouter. "
                "Install with: pip install 'mal-janus[openrouter]'"
            )
        api_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENROUTER_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY or OPENROUTER_KEY env var required for OpenRouter provider")
        return ChatOpenAI(
            model=model,
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
            timeout=180,
            max_retries=2,
        )
    else:
        try:
            from langchain.chat_models import init_chat_model
        except ImportError:
            raise ImportError(
                "langchain-core is required. Install with: pip install deepagents"
            )
        return init_chat_model(model=model, model_provider=provider)


def create_orchestrator(
    provider: str = "openrouter",
    model: str = "xiaomi/mimo-v2.5",
    thread_id: str = "centinela-session",
    langfuse_client=None,
    *,
    mode: Literal["centinela", "dispatcher"] = "dispatcher",
    goal: str = "",
    env: str = "",
    iteration: int = 0,
):
    """Create an orchestrator agent using deepagents.

    Two modes:
    - centinela: conversational REPL, interacts with user, delegates implementation
    - dispatcher: goal-driven, manages gawt session, coordinates specialists

    Both modes have access to 8 specialist subagents via the task() tool.

    Args:
        mode: Orchestrator mode (centinela or dispatcher).
        goal: The session goal (enriches Langfuse trace metadata + tags).
        env: Environment name (dev/staging/production). Enriches Langfuse tags.
        iteration: Improvement iteration number. Enriches Langfuse metadata.
    """
    global OBSERVABILITY_MIDDLEWARE

    try:
        from deepagents import (
            create_deep_agent,
            FilesystemPermission,
            GeneralPurposeSubagentProfile,
            HarnessProfile,
            register_harness_profile,
        )
        from deepagents.backends import FilesystemBackend
    except ImportError:
        raise ImportError(
            "The 'deepagents' package is required but not installed. "
            "Install it with: pip install 'mal-janus' or pip install deepagents"
        )

    # Disable the auto-added general-purpose subagent so the LLM only sees
    # our specialist subagents (abm, scoring, ingest, etc.). Without this,
    # deepagents inserts "general-purpose" at position 0 and the LLM defaults
    # to it because the built-in TASK_TOOL_DESCRIPTION has 5 examples all
    # using "general-purpose".
    #
    # Key must be "openai" (the resolved provider), NOT "openrouter".
    # deepagents resolves ChatOpenAI as provider='openai' regardless of the
    # base_url pointing to OpenRouter. The lookup order is:
    #   1. "openai:xiaomi/mimo-v2.5" (provider:model)
    #   2. "openai" (provider fallback)
    register_harness_profile(
        "openai",
        HarnessProfile(
            general_purpose_subagent=GeneralPurposeSubagentProfile(enabled=False),
        ),
    )

    llm = _resolve_provider(provider, model)

    backend = FilesystemBackend(
        root_dir=str(REPO_ROOT),
        virtual_mode=True,
    )

    # Observability middleware
    middleware = []
    obs = None
    if SESSION_LOGGER is not None:
        obs = ObservabilityMiddleware(
            SESSION_LOGGER,
            langfuse_client=langfuse_client,
            goal=goal,
            thread_id=thread_id,
            env=env,
            iteration=iteration,
            mode=mode,
        )
        middleware.append(obs)
        OBSERVABILITY_MIDDLEWARE = obs

    skills = []
    if PROJECT_SKILLS.is_dir():
        skills.append("agents/skills/")

    # ── Subagent definitions (shared across both modes) ──────────────
    from agents_janus.subagents.registry import load_registry
    from agents_janus.subagents.builder import build_subagent_prompt
    from agents_janus.mcp_bridge import get_gawt_mcp_tools_sync, filter_gawt_tools
    from agents_janus.tools.ask_user_tool import ask_user as ask_user_tool
    from agents_janus.scope_validator import ScopeValidationMiddleware

    all_mcp_tools = get_gawt_mcp_tools_sync()
    gawt_tools = filter_gawt_tools(all_mcp_tools)

    registry = load_registry()
    worker_defs = []
    for name, spec in registry.all().items():
        all_tools = list(gawt_tools)
        all_tools.append(ask_user_tool)

        wrapped_tools = [_wrap_with_logging(t) for t in all_tools]
        system_prompt = build_subagent_prompt(spec, registry.all())

        wd = {
            "name": name,
            "description": spec.description,
            "system_prompt": system_prompt,
            "tools": wrapped_tools,
            "middleware": [
                ScopeValidationMiddleware(registry, name),
                SubAgentObservabilityMiddleware(obs, name),
            ] if obs else [ScopeValidationMiddleware(registry, name)],
        }

        if FilesystemPermission is not None:
            wd["permissions"] = [
                FilesystemPermission(operations=["read"], paths=["/.env", "/**/.env", "/**/*secret*", "/**/*credential*"], mode="deny"),
                FilesystemPermission(operations=["write"], paths=["/data/**"], mode="deny"),
                FilesystemPermission(operations=["write"], paths=["/.git/**"], mode="deny"),
                FilesystemPermission(operations=["write"], paths=["/.gitagent/worktree/**"], mode="allow"),
                FilesystemPermission(operations=["write"], paths=["/**"], mode="deny"),
                FilesystemPermission(operations=["read"], paths=["/**"], mode="allow"),
            ]

        worker_defs.append(wd)

    # ── Orchestrator permissions (both modes: read-only) ─────────────
    orch_permissions = []
    if FilesystemPermission is not None:
        orch_permissions = [
            FilesystemPermission(operations=["read"], paths=["/.env", "/**/.env", "/**/*secret*", "/**/*credential*"], mode="deny"),
            FilesystemPermission(operations=["write"], paths=["/**"], mode="deny"),
            FilesystemPermission(operations=["read"], paths=["/**"], mode="allow"),
        ]

    # ── Orchestrator tools (mode-specific) ───────────────────────────
    if mode == "centinela":
        orch_tools = _get_centinela_tools()
    else:
        orch_tools = _get_dispatcher_tools() + [_wrap_with_logging(t) for t in gawt_tools]

    return create_deep_agent(
        model=llm,
        tools=orch_tools,
        subagents=worker_defs,
        system_prompt=_render_prompt(mode),
        backend=backend,
        skills=skills or None,
        name=f"janus-orchestrator-{mode}",
        middleware=middleware,
        permissions=orch_permissions,
    )
