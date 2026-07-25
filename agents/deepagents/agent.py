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
    gitagent_spawn,
    gitagent_proposals,
    gitagent_integrate,
    gitagent_finalize,
    pipeline_run_calibration,
    pipeline_compare_scorecards,
    memory_recall_kg,
    improve_prompt,
)

AGENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = _project_root
PROJECT_SKILLS = REPO_ROOT / "agents" / "skills"
GLOBAL_SKILLS = Path.home() / ".agents" / "skills"

ORCHESTRATOR_PROMPT = """\
You are the MalariaSentinel Centinela orchestrator.

CALIBRATION CYCLE — do these 4 steps in order, one tool call per message:
1. memory_recall_kg → recall past patterns
2. pipeline_run_calibration → get baseline score
3. Pick 1 improvement. gitagent_spawn a worker for it.
4. pipeline_run_calibration → score the result

CRITICAL RULES:
- ONE tool call per message. Wait for result, then next step.
- If pipeline_run_calibration returns "tests_failed", say "Baseline: tests_failed" and IMMEDIATELY move to step 3.
- Do NOT investigate test failures. Do NOT read test files. Do NOT glob/grep for test config.
- Do NOT check gitagent_proposals until step 4 completes.
- Under 50 words per response.
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

TOOLS = [
    opencode_search,
    gitagent_spawn,
    gitagent_proposals,
    gitagent_integrate,
    gitagent_finalize,
    pipeline_run_calibration,
    pipeline_compare_scorecards,
    memory_recall_kg,
    improve_prompt,
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

    backend = FilesystemBackend(root_dir=str(REPO_ROOT), virtual_mode=False)

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
    )
