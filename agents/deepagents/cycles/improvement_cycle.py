"""Improvement cycle — replaces run_cycle for the new architecture.

Provides run_improvement_cycle() and keeps backwards-compatible shims.
"""
from __future__ import annotations


def run_improvement_cycle(
    goal: str,
    plan_path: str | None = None,
    provider: str = "openrouter",
    model: str = "xiaomi/mimo-v2.5",
    thread_id: str = "improvement-session",
    context: dict | None = None,
) -> str:
    """Run an improvement cycle using the new improvement orchestrator."""
    from agents.deepagents.improvement import run_improvement
    return run_improvement(
        goal=goal,
        plan_path=plan_path,
        provider=provider,
        model=model,
        thread_id=thread_id,
        context=context,
    )
