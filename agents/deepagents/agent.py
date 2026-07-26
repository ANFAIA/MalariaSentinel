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

# Module-level flags set by CLI before creating the agent
VERIFY_FINALIZE: bool = True
VERIFY_INTEGRATE: bool = True
SESSION_LOGGER: SessionLogger | None = None

AGENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = _project_root
PROJECT_SKILLS = REPO_ROOT / "agents" / "skills"
GLOBAL_SKILLS = Path.home() / ".agents" / "skills"

ORCHESTRATOR_PROMPT = """\
You are the MalariaSentinel Centinela orchestrator.

WORKFLOW — for each feature:
1. gitagent_init (idempotent)
2. gitagent_start(feature=X) — open session
3. gitagent_spawn(feature=X, agent_id="abm-worker-X", role="abm") — get worktree path
4. Create worker subagent with FilesystemBackend(worktree_path) — use create_abm_worker_subagent()
5. Let worker do its work (compile, test, score)
6. gitagent_proposals(feature=X) — check what worker proposed
7. gitagent_diff(proposal_id, feature=X) — review the changes
8. If OK → gitagent_accept; if not → gitagent_revise with feedback → back to step 5
9. gitagent_integrate(feature=X) — apply accepted proposals
10. gitagent_finalize(feature=X, message="...") — one commit on main

MULTI-FEATURE: you can manage N features in parallel. Each feature is independent.

CRITICAL RULES:
- Always pass --feature to every gitagent command
- Use gitagent_revise (not reject) when you want the worker to iterate
- Iterations are unlimited — keep revising until the change is correct
- Before finalize: review proposals and diffs carefully
- Under 80 words per response unless explaining a decision
"""

WORKER_DEFINITIONS = [
    {
        "name": "abm-worker",
        "description": (
            "Modifies ABM C++ parameters and runs tests. "
            "Use for changes to mortality, dispersal, habitat, or any mal-core/abm/ code."
        ),
        "system_prompt": (
            "You are an ABM calibration worker. You modify C++ parameters in "
            "mal-core/src/mal_core/abm/, run tests, and report results. "
            "Always run: cd mal-core/src/mal_core/abm/tests/calibration && uv run pytest -m fast -v"
        ),
        "skills": [
            "agents/skills/abm-engine/SKILL.md",
            "agents/skills/calibration-framework/SKILL.md",
        ],
    },
    {
        "name": "scorer-worker",
        "description": (
            "Modifies Python calibration scorers and thresholds. "
            "Use for changes to scorers, thresholds.yaml, or composite scoring."
        ),
        "system_prompt": (
            "You are a calibration scorer worker. You modify Python scoring code "
            "in mal-core/src/mal_core/abm/tests/calibration/scorers/, update thresholds.yaml, "
            "and run the calibration suite. "
            "Always run: cd mal-core/src/mal_core/abm/tests/calibration && uv run pytest -m fast -v"
        ),
        "skills": [
            "agents/skills/calibration-framework/SKILL.md",
        ],
    },
    {
        "name": "feature-worker",
        "description": (
            "Implements new features in mal-core. "
            "Use for new pipeline stages, new modules, or structural changes."
        ),
        "system_prompt": (
            "You are a feature implementation worker. You add new modules to "
            "mal-core/src/mal_core/, following the monorepo conventions. "
            "Always run: uv run pytest in the relevant package after changes."
        ),
        "skills": [
            "agents/skills/monorepo-dev/SKILL.md",
        ],
    },
]


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
        from deepagents import create_deep_agent
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
        read_only=True,
    )

    skills = []
    if PROJECT_SKILLS.is_dir():
        skills.append(str(PROJECT_SKILLS))
    if GLOBAL_SKILLS.is_dir():
        skills.append(str(GLOBAL_SKILLS))

    return create_deep_agent(
        model=llm,
        tools=TOOLS,
        subagents=WORKER_DEFINITIONS,
        system_prompt=ORCHESTRATOR_PROMPT,
        backend=backend,
        skills=skills or None,
        name="centinela-orchestrator",
        permissions=[
            {"operations": ["read"], "paths": ["/**"], "mode": "allow"},
            {"operations": ["read"], "paths": ["/.env", "/**/.env", "/**/*secret*", "/**/*credential*"], "mode": "deny"},
            {"operations": ["write", "edit"], "paths": ["/**"], "mode": "deny"},
        ],
    )


def create_abm_worker_subagent(worktree_path: Path) -> dict:
    """Create a worker subagent isolated to its gitagent worktree.

    The worker uses FilesystemBackend with virtual_mode=True to ensure
    it can only access files under its worktree root (no ../ escaping).

    Args:
        worktree_path: Absolute path to the agent's gitagent worktree.

    Returns:
        A dict compatible with deepagents subagent specification.
    """
    try:
        from deepagents.backends import FilesystemBackend
    except ImportError:
        raise ImportError(
            "The 'deepagents' package is required but not installed. "
            "Install it with: pip install 'mal-deepagents' or pip install deepagents"
        )

    worker_backend = FilesystemBackend(
        root_dir=str(worktree_path),
        virtual_mode=True,
    )

    return {
        "name": "abm-worker",
        "description": (
            "Modifies ABM C++ parameters, runs tests, and scores results. "
            "Worktree-isolated — can only see files under its worktree root."
        ),
        "system_prompt": (
            "You are an ABM calibration worker working inside an isolated gitagent worktree. "
            "You can only see files under your worktree root. "
            "Use the 3 custom tools for execution: "
            "abm_run (compile + simulate), abm_test (pytest), abm_score (14 scorers + LLM verdict). "
            "Use read_file/write_file/edit_file/glob/grep for file operations. "
            "When your work is done, run from the REPO ROOT: "
            "gitagent propose --feature <name> --agent <your-id> --title '...' --summary '...' --confidence 0.8"
        ),
        "backend": worker_backend,
        "tools": [
            _wrap_with_logging(_import_abm_run()),
            _wrap_with_logging(_import_abm_test()),
            _wrap_with_logging(_import_abm_score()),
        ],
        "permissions": [
            # Worker can read and write within its worktree
            {"operations": ["read", "write", "edit"], "paths": ["/**"], "mode": "allow"},
            # Deny reading secrets
            {"operations": ["read"], "paths": ["/.env", "/**/.env", "/**/*secret*", "/**/*credential*"], "mode": "deny"},
            # Deny writing to data inputs (read-only)
            {"operations": ["write", "edit"], "paths": ["/data/**"], "mode": "deny"},
            # Deny writing to gitagent metadata
            {"operations": ["write", "edit"], "paths": ["/.gitagent/**", "/.git/**"], "mode": "deny"},
        ],
    }


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
