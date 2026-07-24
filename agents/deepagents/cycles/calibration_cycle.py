"""Calibration improvement cycle — recall, plan, spawn, score, improve."""
from __future__ import annotations

import json


CALIBRATION_PROMPT = """\
Run a calibration improvement cycle:
1. Recall past patterns from the knowledge graph using memory_recall_kg
2. Analyze the current composite score (baseline) by running pipeline_run_calibration
3. Generate 2-3 hypotheses to improve it (parameter tuning, threshold adjustments)
4. Spawn up to 3 worker agents (abm-worker, scorer-worker) in parallel using gitagent_spawn
5. Each worker modifies code in its isolated worktree and proposes via gitagent
6. Run calibration on each proposal using pipeline_run_calibration
7. Compare scorecards using pipeline_compare_scorecards, accept the best one
8. Analyze failures and patch worker prompts using improve_prompt
9. Repeat for up to {max_iterations} iterations
10. Stop when composite improves by <0.001 for 3 consecutive iterations

Start by recalling what patterns and pitfalls exist from past calibration sessions.
"""


def run_calibration_cycle(max_iterations: int = 10, dry_run: bool = False) -> str:
    """Run the ABM calibration improvement cycle.

    Args:
        max_iterations: Maximum number of improvement iterations.
        dry_run: If True, print the prompt without executing.

    Returns:
        The final agent response after the cycle completes.
    """
    prompt = CALIBRATION_PROMPT.format(max_iterations=max_iterations)

    if dry_run:
        return json.dumps({
            "status": "dry_run",
            "prompt": prompt,
            "max_iterations": max_iterations,
        })

    from agents.deepagents.agent import create_orchestrator

    agent = create_orchestrator()

    result = agent.invoke({
        "messages": [{"role": "user", "content": prompt}]
    })

    return result["messages"][-1].content
