"""MalariaSentinel DeepAgent orchestrator — create_orchestrator() factory."""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Add the project root to sys.path for tool imports
_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from agents.deepagents.tools import (
    opencode_search,
    gitagent_init,
    gitagent_start,
    gitagent_spawn,
    gitagent_list_agents,
    gitagent_kill,
    gitagent_proposals,
    gitagent_diff,
    gitagent_accept,
    gitagent_reject,
    gitagent_revise,
    gitagent_integrate,
    gitagent_finalize,
    pipeline_run_calibration,
    pipeline_compare_scorecards,
    memory_recall_kg,
    improve_prompt,
)
from agents.deepagents.logger import SessionLogger

try:
    from deepagents import FilesystemPermission
except ImportError:
    FilesystemPermission = None  # type: ignore[assignment,misc]

# Module-level flags set by CLI before creating the agent
VERIFY_FINALIZE: bool = True
VERIFY_INTEGRATE: bool = True
SESSION_LOGGER: SessionLogger | None = None

AGENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = _project_root
PROJECT_SKILLS = REPO_ROOT / "agents" / "skills"
GLOBAL_SKILLS = Path.home() / ".agents" / "skills"


def _wrap_with_logging(tool_func):
    """Wrap a tool function to add structured logging."""
    import functools

    @functools.wraps(tool_func)
    def wrapper(*args, **kwargs):
        import time
        start = time.monotonic()
        result = tool_func(*args, **kwargs)
        elapsed = time.monotonic() - start

        if SESSION_LOGGER is not None:
            # Build input dict from args + kwargs
            import inspect
            sig = inspect.signature(tool_func)
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()
            input_dict = {k: v for k, v in bound.arguments.items()}

            SESSION_LOGGER.log_tool(
                tool_name=tool_func.__name__,
                tool_input=input_dict,
                output=result,
                latency_s=elapsed,
            )
        return result

    return wrapper


def _import_abm_run():
    """Lazy import of abm_run tool."""
    from agents.deepagents.tools.abm_tools import abm_run
    return abm_run


def _import_abm_test():
    """Lazy import of abm_test tool."""
    from agents.deepagents.tools.abm_tools import abm_test
    return abm_test


def _import_abm_score():
    """Lazy import of abm_score tool."""
    from agents.deepagents.tools.abm_tools import abm_score
    return abm_score

ORCHESTRATOR_PROMPT = """\
You are the MalariaSentinel Centinela orchestrator. You manage ABM development — calibration, new features, bug fixes, behavior changes, code removal, anything the codebase needs.

ORDER OF OPERATIONS (MANDATORY — follow this sequence):

1. READ THE CODE FIRST. Before anything else, read the actual C++ files:
   - grep/glob to find relevant files in mal-core/src/mal_core/abm/
   - read_file to understand what the code does
   - You CANNOT delegate if you haven't read the code yourself

2. THEN check the KB — memory_recall_kg(query="...", k=5)
   - Use ONLY for: past failures, project structure, architecture decisions
   - Do NOT use to "understand" the code (you already read it)

3. THEN read papers — papers/ directory
   - Use ONLY for: biological plausibility, parameter validation
   - Do NOT use to debug the simulation

4. THEN search web — opencode_search(query="...")
   - Use ONLY for: field data, scientific literature, parameter ranges
   - Do NOT use to find "why the simulation crashes"

5. THEN delegate to worker — task(subagent_type="abm-worker", description="...")

YOUR CAPABILITIES:
- Read any file in the repo (C++, Python, YAML, papers, configs)
- Search the web for scientific information
- Query the project knowledge base
- Spawn workers to make code changes
- Review and approve/reject changes via gitagent

CONTEXT SOURCES (use in this order):
1. CODE (mal-core/src/mal_core/abm/) — always first
2. KB (memory_recall_kg) — past patterns and pitfalls only
3. Papers (papers/) — biological validation only
4. Web (opencode_search) — scientific literature only

WORKFLOW — for each feature:
1. gitagent_init (idempotent)
2. gitagent_start(feature=X) — open session
3. gitagent_spawn(feature=X, agent_id="worker-X", role="<role>") — get worktree path
4. task(subagent_type="abm-worker", description="<detailed task with code analysis>")
5. gitagent_proposals(feature=X) — check what worker proposed
6. gitagent_diff(proposal_id, feature=X) — review the changes
7. If OK → gitagent_accept; if not → gitagent_revise with feedback → back to step 4
8. gitagent_integrate(feature=X) — apply accepted proposals
9. gitagent_finalize(feature=X, message="...") — one commit on main

MULTI-FEATURE: you can manage N features in parallel. Each feature is independent.

CRITICAL RULES:
- READ CODE BEFORE ANYTHING ELSE. No exceptions.
- Always pass --feature to every gitagent command
- Use gitagent_revise (not reject) when you want the worker to iterate
- Iterations are unlimited — keep revising until the change is correct
- Before finalize: review proposals and diffs carefully
"""

WORKER_DEFINITIONS = [
    {
        "name": "abm-worker",
        "description": (
            "Modifies ABM C++ code: parameters, behaviors, new features, bug fixes. "
            "Can read/write any file, compile, run tests, and score results. "
            "Use for any change to mal-core/src/mal_core/abm/ or related code."
        ),
        "system_prompt": (
            "You are an ABM development worker in an isolated gitagent worktree. "
            "You can modify ANY part of the C++ codebase — parameters, behaviors, "
            "new features, bug fixes, or remove broken code. "
            "You have access to: read_file, write_file, edit_file, glob, grep (file ops), "
            "execute (shell commands), abm_run (compile + simulate), abm_test (pytest), "
            "abm_score (14 scorers + LLM verdict). "
            "Use opencode_search to find scientific literature if you need parameter ranges "
            "or biological context. Use memory_recall_kg to check past patterns and pitfalls. "
            "Read papers in papers/ directory for domain knowledge. "
            "When your work is done, run from the REPO ROOT: "
            "gitagent propose --feature <name> --agent <your-id> --title '...' --summary '...' --confidence 0.8"
        ),
        "tools": [
            _wrap_with_logging(_import_abm_run()),
            _wrap_with_logging(_import_abm_test()),
            _wrap_with_logging(_import_abm_score()),
        ],
        # Permissions are added dynamically in create_orchestrator() if FilesystemPermission is available
    },
]


def _gitagent_finalize_wrapped(feature: str, message: str) -> str:
    """Wrapper that injects the verify flag from module-level setting."""
    return gitagent_finalize(feature, message, verify=VERIFY_FINALIZE)


def _gitagent_integrate_wrapped(feature: str) -> str:
    """Wrapper that injects the verify flag from module-level setting."""
    return gitagent_integrate(feature, verify=VERIFY_INTEGRATE)


TOOLS = [
    _wrap_with_logging(opencode_search),
    _wrap_with_logging(gitagent_init),
    _wrap_with_logging(gitagent_start),
    _wrap_with_logging(gitagent_spawn),
    _wrap_with_logging(gitagent_list_agents),
    _wrap_with_logging(gitagent_kill),
    _wrap_with_logging(gitagent_proposals),
    _wrap_with_logging(gitagent_diff),
    _wrap_with_logging(gitagent_accept),
    _wrap_with_logging(gitagent_reject),
    _wrap_with_logging(gitagent_revise),
    _wrap_with_logging(_gitagent_integrate_wrapped),
    _wrap_with_logging(_gitagent_finalize_wrapped),
    _wrap_with_logging(pipeline_run_calibration),
    _wrap_with_logging(pipeline_compare_scorecards),
    _wrap_with_logging(memory_recall_kg),
    _wrap_with_logging(improve_prompt),
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
                "Install with: pip install 'mal-deepagents[openrouter]'"
            )
        api_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENROUTER_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY or OPENROUTER_KEY env var required for OpenRouter provider")
        return ChatOpenAI(
            model=model,
            base_url="https://openrouter.ai/api/v1",
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
    thread_id: str = "centinela-session",
):
    """Create the main orchestrator agent using deepagents.

    Args:
        provider: LLM provider ("openrouter", "anthropic", "openai", "google_genai").
        model: Model identifier.
        thread_id: Thread ID for checkpointing.

    Returns:
        A compiled agent graph ready to invoke.

    Raises:
        ImportError: If required packages are not installed.
    """
    try:
        from deepagents import create_deep_agent, FilesystemPermission
        from deepagents.backends import FilesystemBackend
    except ImportError:
        raise ImportError(
            "The 'deepagents' package is required but not installed. "
            "Install it with: pip install 'mal-deepagents' or pip install deepagents"
        )

    llm = _resolve_provider(provider, model)

    backend = FilesystemBackend(
        root_dir=str(REPO_ROOT),
        virtual_mode=True,
    )

    skills = []
    if PROJECT_SKILLS.is_dir():
        skills.append("agents/skills/")

    # Add permissions to worker definitions dynamically
    worker_defs = []
    for w in WORKER_DEFINITIONS:
        wd = dict(w)
        wd["permissions"] = [
            FilesystemPermission(operations=["read"], paths=["/.env", "/**/.env", "/**/*secret*", "/**/*credential*"], mode="deny"),
            FilesystemPermission(operations=["write"], paths=["/data/**"], mode="deny"),
            FilesystemPermission(operations=["write"], paths=["/.gitagent/**", "/.git/**"], mode="deny"),
            FilesystemPermission(operations=["read", "write"], paths=["/**"], mode="allow"),
        ]
        worker_defs.append(wd)

    return create_deep_agent(
        model=llm,
        tools=TOOLS,
        subagents=worker_defs,
        system_prompt=ORCHESTRATOR_PROMPT,
        backend=backend,
        skills=skills or None,
        name="centinela-orchestrator",
        permissions=[
            FilesystemPermission(operations=["read"], paths=["/.env", "/**/.env", "/**/*secret*", "/**/*credential*"], mode="deny"),
            FilesystemPermission(operations=["write"], paths=["/**"], mode="deny"),
            FilesystemPermission(operations=["read"], paths=["/**"], mode="allow"),
        ],
    )

