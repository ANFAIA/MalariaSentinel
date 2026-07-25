"""Calibration improvement cycle — recall, plan, spawn, score, improve."""
from __future__ import annotations

import json


CALIBRATION_PROMPT = """\
Run a calibration improvement cycle (max {max_iterations} iterations).

Steps: recall KG → run baseline calibration → pick 1 improvement → spawn worker → score → compare → improve prompt if failed.

Start with step 1: use memory_recall_kg to find past patterns.
"""


def run_calibration_cycle(
    max_iterations: int = 10,
    provider: str = "openrouter",
    model: str = "xiaomi/mimo-v2.5",
    thread_id: str = "calibration-session",
    dry_run: bool = False,
) -> str:
    """Run the ABM calibration improvement cycle.

    Args:
        max_iterations: Maximum number of improvement iterations.
        provider: LLM provider.
        model: Model identifier.
        thread_id: Thread ID for checkpointing.
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

    agent = create_orchestrator(provider=provider, model=model, thread_id=thread_id)

    result = agent.invoke(
        {"messages": [{"role": "user", "content": prompt}]},
    )

    return result["messages"][-1].content
