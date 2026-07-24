"""MalariaSentinel DeepAgent orchestrator — create_orchestrator() factory."""
from __future__ import annotations

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

ORCHESTRATOR_PROMPT = """\
You are the MalariaSentinel Centinela orchestrator — an autonomous agent \
that improves the ABM calibration by running parallel experiments.

## Your workflow

1. RECALL: Use memory_recall_kg to find past patterns, pitfalls, and best practices.
2. PLAN: Use write_todos to plan hypotheses to test.
3. RESEARCH: Use opencode_search to find relevant literature (OpenCode has Exa).
4. SPAWN: Use gitagent_spawn to create worker agents in isolated worktrees.
5. WAIT: Workers edit code and propose changes via gitagent.
6. SCORE: Use pipeline_run_calibration to evaluate each proposal.
7. COMPARE: Use pipeline_compare_scorecards to find the best improvement.
8. DECIDE: Accept the best proposal, reject others.
9. IMPROVE: Use improve_prompt to update worker prompts based on failures.
10. LOOP: Repeat from step 1 until convergence (3 iterations without improvement).

## Rules
- Maximum 3 parallel workers at a time.
- Always compare against the best historical composite score.
- Never weaken tests or skip scorers.
- Record every improvement and failure in the knowledge graph.
- When a worker fails, analyze WHY and patch its prompt before the next iteration.
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
            "Always run: cd mal-abm-fast/tests/calibration && uv run pytest -m fast -v"
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
            "in mal-abm-fast/tests/calibration/scorers/, update thresholds.yaml, "
            "and run the calibration suite. "
            "Always run: cd mal-abm-fast/tests/calibration && uv run pytest -m fast -v"
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

MEMORY_FILES = ["agents/deepagents/AGENTS.md"]
SKILLS_DIR = "agents/skills/"


def create_orchestrator():
    """Create the main orchestrator agent using deepagents.

    Returns:
        A compiled agent graph ready to invoke.

    Raises:
        ImportError: If the `deepagents` package is not installed.
    """
    try:
        from deepagents import create_deep_agent
    except ImportError:
        raise ImportError(
            "The 'deepagents' package is required but not installed. "
            "Install it with: pip install deepagents"
        )

    return create_deep_agent(
        model="openrouter:xiaomi/mimo-v2.5",
        tools=TOOLS,
        subagents=WORKER_DEFINITIONS,
        system_prompt=ORCHESTRATOR_PROMPT,
        memory=MEMORY_FILES,
        skills=[SKILLS_DIR],
        interrupt_on={
            "gitagent_integrate": True,
            "gitagent_finalize": True,
        },
    )
