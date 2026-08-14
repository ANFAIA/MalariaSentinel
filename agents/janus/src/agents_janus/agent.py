"""MalariaSentinel Janus orchestrator hierarchy.

The orchestrator decomposes goals, dispatches specialists, monitors progress,
and finalizes via gawt MCP. It never edits files directly.

Roles:
- request_router: minimal parent that routes user requests
- research_coordinator: read-only research parent
- implementation_coordinator: editing and GAWT parent
"""
from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Literal

_log = logging.getLogger("agents_janus.agent")

_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from agents_janus.logger import SessionLogger
from agents_janus.malariasim_backend import MalariasimShellBackend
from agents_janus.middleware.tool_filter import ToolFilterMiddleware
from agents_janus.observability import ObservabilityMiddleware, SubAgentObservabilityMiddleware

# Module-level flags set by CLI before creating the agent
VERIFY_FINALIZE: bool = True
CODEBASE_INDEX_ON_STARTUP: bool = True
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


def _checkpointer():
    """Create the in-memory checkpointer for the orchestrator graph.

    resolve_conflict forks the conversation via get_state/update_state/invoke,
    which require a checkpointer. deepagents' create_deep_agent accepts a
    checkpointer but doesn't default to one.
    """
    try:
        from langgraph.checkpoint.memory import MemorySaver
        return MemorySaver()
    except ImportError:
        return None


def _render_prompt(
    mode: Literal[
        "request_router",
        "research_coordinator",
        "implementation_coordinator",
    ],
) -> str:
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
        # Fallback to legacy static prompt when the template is unavailable.
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
    if mode == "request_router":
        base += """
You are the request router. Delegate each request to exactly one coordinator:
research_coordinator or implementation_coordinator.
"""
    elif mode == "research_coordinator":
        base += """
You are the research coordinator. Dispatch specialists with [MODE:research].
Never edit files.
"""
    else:
        base += """
You are the implementation coordinator. Start GAWT sessions, dispatch specialists,
monitor progress, and finalize changes.
"""
    return base


# ── Tool sets ───────────────────────────────────────────────────────────

def _get_implementation_tools():
    """Tools for implementation coordinator: search, memory, ask_user.

    Shell access comes from the built-in `execute` tool (MalariasimShellBackend
    restricts it to `malariasim` only) — no custom ABM execution tools.
    """
    from agents_janus.tools import (
        web_search,
        memory_recall_kg,
        ask_user,
    )
    return [
        _wrap_with_logging(web_search),
        _wrap_with_logging(memory_recall_kg),
        _wrap_with_logging(ask_user),
    ]


def _get_research_tools():
    """Tools for research coordinator mode: clarification only.

    Repository and knowledge tools belong to research specialists. Keeping
    them off the coordinator forces repository questions through task().
    """
    from agents_janus.tools.ask_user_tool import ask_user
    return [_wrap_with_logging(ask_user)]


def _get_router_tools():
    """Minimal tools for the request router.

    The router only receives user input and delegates to one coordinator via
    deepagents' built-in task tool. It must not inspect or edit the repository.
    """
    return []


MEMORY_FILES = [str(AGENT_DIR / "AGENTS.md")]


def _resolve_provider(provider: str, model: str):
    """Resolve the LLM based on provider and model."""
    if provider == "openrouter":
        try:
            from langchain_openrouter import ChatOpenRouter
        except ImportError:
            raise ImportError(
                "langchain-openrouter is required for OpenRouter. "
                "Install with: pip install langchain-openrouter"
            )
        api_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENROUTER_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY or OPENROUTER_KEY env var required for OpenRouter provider")
        return ChatOpenRouter(
            model=model,
            api_key=api_key,
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
    thread_id: str = "request-router-session",
    langfuse_client=None,
    *,
    mode: Literal[
        "request_router",
        "research_coordinator",
        "implementation_coordinator",
    ] = "implementation_coordinator",
    goal: str = "",
    env: str = "",
    iteration: int = 0,
):
    """Create an orchestrator agent using deepagents.

    Three roles:
    - request_router: minimal parent that routes each request to a coordinator
    - research_coordinator: user-facing research coordinator
    - implementation_coordinator: goal-driven editor and GAWT coordinator

    Coordinator roles have access to domain specialists via task().

    Args:
        mode: Orchestrator role.
        goal: The session goal (enriches Langfuse trace metadata + tags).
        env: Environment name (dev/staging/production). Enriches Langfuse tags.
        iteration: Improvement iteration number. Enriches Langfuse metadata.
    """
    global OBSERVABILITY_MIDDLEWARE

    try:
        from deepagents import (
            create_deep_agent,
            GeneralPurposeSubagentProfile,
            HarnessProfile,
            register_harness_profile,
        )
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
    # Key must match the resolved provider. ChatOpenRouter resolves as
    # provider='openrouter'; ChatOpenAI resolves as 'openai'.
    # Lookup order:
    #   1. "openrouter:xiaomi/mimo-v2.5" (provider:model)
    #   2. "openrouter" (provider fallback)
    register_harness_profile(
        "openrouter",
        HarnessProfile(
            general_purpose_subagent=GeneralPurposeSubagentProfile(enabled=False),
        ),
    )

    llm = _resolve_provider(provider, model)

    # Request router is intentionally minimal: its children own all capabilities.
    if mode == "request_router":
        from deepagents import CompiledSubAgent

        research_agent = create_orchestrator(
            provider=provider,
            model=model,
            thread_id=f"{thread_id}-research",
            langfuse_client=langfuse_client,
            mode="research_coordinator",
            goal=goal,
            env=env,
            iteration=iteration,
        )
        implementation_agent = create_orchestrator(
            provider=provider,
            model=model,
            thread_id=f"{thread_id}-implementation",
            langfuse_client=langfuse_client,
            mode="implementation_coordinator",
            goal=goal,
            env=env,
            iteration=iteration,
        )

        router_middleware = []
        if SESSION_LOGGER is not None:
            router_obs = ObservabilityMiddleware(
                SESSION_LOGGER,
                langfuse_client=langfuse_client,
                goal=goal,
                thread_id=thread_id,
                env=env,
                iteration=iteration,
                mode=mode,
            )
            router_middleware.append(router_obs)
            OBSERVABILITY_MIDDLEWARE = router_obs

        router = create_deep_agent(
            model=llm,
            tools=_get_router_tools(),
            subagents=[
                CompiledSubAgent(
                    name="research_coordinator",
                    description="Researches and explains the system. Never edits files.",
                    runnable=research_agent,
                ),
                CompiledSubAgent(
                    name="implementation_coordinator",
                    description="Plans and implements repository changes through GAWT.",
                    runnable=implementation_agent,
                ),
            ],
            system_prompt=_render_prompt(mode),
            skills=None,
            name="janus-request-router",
            middleware=router_middleware,
            checkpointer=_checkpointer(),
        )
        return router

    # MalariasimShellBackend exposes the built-in `execute` tool (bash) but
    # restricts it to `malariasim` commands via a policy hook. Filesystem
    # deny rules (secrets, data/, .git/) are enforced in the backend too, so
    # no FilesystemPermission is passed to deepagents (it is incompatible
    # with execution-capable backends).
    backend = MalariasimShellBackend(
        root_dir=str(REPO_ROOT),
        virtual_mode=True,
        inherit_env=True,
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
    if mode == "research_coordinator":
        middleware.append(
            ToolFilterMiddleware(
                excluded=frozenset({"write_file", "edit_file", "delete_file"})
            )
        )

    skills = []
    if PROJECT_SKILLS.is_dir():
        skills.append("agents/skills/")

    # ── Subagent definitions (shared across both modes) ──────────────
    from agents_janus.subagents.registry import load_registry
    from agents_janus.subagents.builder import build_subagent_prompt
    from agents_janus.mcp_bridge import (
        get_mcp_tools_sync,
        load_janus_config,
        filter_gawt_tools,
        filter_codebase_tools,
    )
    from agents_janus.tools.ask_user_tool import ask_user as ask_user_tool
    from agents_janus.scope_validator import ScopeValidationMiddleware
    from agents_janus.middleware.inbox_check import InboxCheckMiddleware
    from agents_janus.tools.resolve_conflict import make_resolve_conflict_tool, set_agent_ref

    janus_config = load_janus_config()
    all_mcp_tools = get_mcp_tools_sync(janus_config, REPO_ROOT)
    gawt_tools = filter_gawt_tools(all_mcp_tools)
    codebase_tools = filter_codebase_tools(all_mcp_tools)

    # Index codebase on startup if enabled (idempotent — no-op if already fresh)
    if CODEBASE_INDEX_ON_STARTUP:
        from agents_janus.mcp_bridge import ensure_index_on_startup
        import asyncio
        try:
            asyncio.run(ensure_index_on_startup(janus_config, REPO_ROOT))
        except Exception as e:
            _log.warning("ensure_index_on_startup failed (non-fatal): %s", e)

    # Create resolve_conflict tool (lazy agent ref — populated after agent creation)
    resolve_conflict_tool = make_resolve_conflict_tool()

    registry = load_registry()
    worker_defs: list[Any] = []
    for name, spec in registry.all().items():
        if mode == "research_coordinator":
            all_tools: list[Any] = list(codebase_tools) + [ask_user_tool]
        else:
            all_tools = list(gawt_tools) + list(codebase_tools)
            all_tools.append(ask_user_tool)
            all_tools.append(resolve_conflict_tool)

        wrapped_tools = [_wrap_with_logging(t) for t in all_tools]
        system_prompt = build_subagent_prompt(
            spec,
            registry.all(),
            coordinator_mode="research" if mode == "research_coordinator" else "implementation",
        )

        wd = {
            "name": name,
            "description": spec.description,
            "system_prompt": system_prompt,
            "tools": wrapped_tools,
            "middleware": (
                [SubAgentObservabilityMiddleware(obs, name)] if obs else []
            ) if mode == "research_coordinator" else (
                [
                    ScopeValidationMiddleware(registry, name),
                    InboxCheckMiddleware(),
                    SubAgentObservabilityMiddleware(obs, name),
                ] if obs else [
                    ScopeValidationMiddleware(registry, name),
                    InboxCheckMiddleware(),
                ]
            ),
        }

        # Only the abm specialist gets shell access (the built-in `execute`
        # tool). Every other subagent has `execute` filtered out. The
        # orchestrator keeps `execute` (it runs malariasim directly).
        excluded_tools = {"execute"} if name != "abm" else set()
        if mode == "research_coordinator":
            excluded_tools.update({"write_file", "edit_file", "delete_file"})
        if excluded_tools:
            wd["middleware"].append(
                ToolFilterMiddleware(excluded=frozenset(excluded_tools))
            )

        worker_defs.append(wd)

    # ── Orchestrator tools (mode-specific) ───────────────────────────
    if mode == "research_coordinator":
        # Research coordinators must delegate repository investigation to
        # specialists. They retain clarification and memory tools, but no
        # direct codebase tools that let them bypass task().
        orch_tools = _get_research_tools()
    else:
        orch_tools = _get_implementation_tools() + [_wrap_with_logging(t) for t in gawt_tools] + [_wrap_with_logging(t) for t in codebase_tools]

    agent = create_deep_agent(
        model=llm,
        tools=orch_tools,
        subagents=worker_defs,
        system_prompt=_render_prompt(mode),
        backend=backend,
        skills=skills or None,
        name=f"janus-orchestrator-{mode}",
        middleware=middleware,
        checkpointer=_checkpointer(),
    )

    # Wire resolve_conflict lazy reference — tool can now access the agent graph
    set_agent_ref(agent, {"configurable": {"thread_id": thread_id}})

    return agent
