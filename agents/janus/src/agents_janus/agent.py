"""MalariaSentinel Janus orchestrator — dispatcher mode.

The orchestrator decomposes goals, dispatches specialists, monitors progress,
and finalizes via gawt MCP. It never edits files directly.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from agents_janus.tools import (
    opencode_search,
    pipeline_run_calibration,
    pipeline_compare_scorecards,
    memory_recall_kg,
    improve_prompt,
    ask_user,
)
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

_ORCHESTRATOR_PROMPT_PATH = AGENT_DIR / "prompts" / "orchestrator.md"


def _wrap_with_logging(tool_func):
    """Wrap a tool function to add structured logging + error capture."""
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


def _load_orchestrator_prompt() -> str:
    """Load the dispatcher prompt from disk, with fallback to inline."""
    if _ORCHESTRATOR_PROMPT_PATH.exists():
        return _ORCHESTRATOR_PROMPT_PATH.read_text()
    return """\
You are the Janus orchestrator. Your role is to coordinate specialist agents via gawt.

You do NOT:
- Edit files via mcp__gitagent__edit_file or write_file
- Read code in detail
- Run ABM simulations
- Form hypotheses about bugs

You DO:
- Receive the user's goal
- Decompose it into subtasks using the LLM
- Identify which specialists can handle each subtask
- Start a gawt session via mcp__gitagent__start_session
- Dispatch specialists via deepagents task tool
- Monitor progress via mcp__gitagent__list_agents, list_edits, list_intents
- Finalize when all specialists are done via mcp__gitagent__finalize_session

When you dispatch a specialist, you give them:
- A clear, specific task
- The user's full goal (as context)
- Any constraints (e.g., "do not break existing calibration")

You do NOT give them hypotheses. They form their own.

You may run multiple specialists in parallel if their tasks are independent.
You may run specialists sequentially if one depends on another's output.

When all specialists have reported done, run mcp__gitagent__finalize_session
with a summary commit message.
"""


TOOLS = [
    _wrap_with_logging(opencode_search),
    _wrap_with_logging(_import_abm_run()),
    _wrap_with_logging(_import_abm_test()),
    _wrap_with_logging(_import_abm_score()),
    _wrap_with_logging(pipeline_run_calibration),
    _wrap_with_logging(pipeline_compare_scorecards),
    _wrap_with_logging(memory_recall_kg),
    _wrap_with_logging(improve_prompt),
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
    goal: str = "",
    env: str = "",
    iteration: int = 0,
):
    """Create the dispatcher orchestrator agent using deepagents.

    The orchestrator decomposes goals, dispatches specialists via gawt MCP,
    monitors progress, and finalizes. It never edits files directly.

    gawt MCP tools are injected via mcp_bridge.py — the same interface
    used by subagents. Both share the same MCP server and SQLite state.

    Args:
        goal: The session goal (enriches Langfuse trace metadata + tags).
        env: Environment name (dev/staging/production). Enriches Langfuse tags.
        iteration: Improvement iteration number. Enriches Langfuse metadata.
    """
    global OBSERVABILITY_MIDDLEWARE

    try:
        from deepagents import create_deep_agent, FilesystemPermission
        from deepagents.backends import FilesystemBackend
    except ImportError:
        raise ImportError(
            "The 'deepagents' package is required but not installed. "
            "Install it with: pip install 'mal-janus' or pip install deepagents"
        )

    llm = _resolve_provider(provider, model)

    backend = FilesystemBackend(
        root_dir=str(REPO_ROOT),
        virtual_mode=True,
    )

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
        )
        middleware.append(obs)
        OBSERVABILITY_MIDDLEWARE = obs

    skills = []
    if PROJECT_SKILLS.is_dir():
        skills.append("agents/skills/")

    from agents_janus.subagents.registry import load_registry
    from agents_janus.subagents.builder import build_subagent_prompt
    from agents_janus.plugins import PLUGIN_REGISTRY
    from agents_janus.plugins.edit import EditPlugin
    from agents_janus.mcp_bridge import get_gawt_mcp_tools_sync, filter_gawt_tools

    # Get gawt MCP tools (shared across orchestrator + all subagents)
    all_mcp_tools = get_gawt_mcp_tools_sync()
    gawt_tools = filter_gawt_tools(all_mcp_tools)
    _log.info("Loaded %d gawt MCP tools for subagents: %s",
              len(gawt_tools), [t.name for t in gawt_tools])

    registry = load_registry()
    worker_defs = []
    for name, spec in registry.all().items():
        plugin_chain = [PLUGIN_REGISTRY[p]() for p in spec.plugins]
        plugin_chain.insert(0, EditPlugin())

        all_tools = []
        for plugin in plugin_chain:
            all_tools.extend(plugin.tools(spec))

        # Add gawt MCP tools to each subagent
        all_tools.extend(gawt_tools)

        wrapped_tools = [_wrap_with_logging(t) for t in all_tools]

        system_prompt = build_subagent_prompt(spec, plugin_chain, registry.all())

        wd = {
            "name": name,
            "description": spec.description,
            "system_prompt": system_prompt,
            "tools": wrapped_tools,
            "middleware": [SubAgentObservabilityMiddleware(obs, name)] if obs else [],
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

    orch_permissions = []
    if FilesystemPermission is not None:
        orch_permissions = [
            FilesystemPermission(operations=["read"], paths=["/.env", "/**/.env", "/**/*secret*", "/**/*credential*"], mode="deny"),
            FilesystemPermission(operations=["write"], paths=["/**"], mode="deny"),
            FilesystemPermission(operations=["read"], paths=["/**"], mode="allow"),
        ]

    # Add gawt MCP tools to orchestrator (session lifecycle, agent management)
    orch_tools = TOOLS + [_wrap_with_logging(t) for t in gawt_tools]

    return create_deep_agent(
        model=llm,
        tools=orch_tools,
        subagents=worker_defs,
        system_prompt=_load_orchestrator_prompt(),
        backend=backend,
        skills=skills or None,
        name="janus-orchestrator",
        middleware=middleware,
        permissions=orch_permissions,
    )
