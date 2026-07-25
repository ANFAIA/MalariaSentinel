"""Calibration improvement cycle — recall, plan, spawn, score, improve."""
from __future__ import annotations

import json


CALIBRATION_PROMPT = """\
Run a calibration improvement cycle (max {max_iterations} iterations).

FLOW — follow these steps IN ORDER. Do NOT skip steps or investigate failures.

Step 1: Recall past patterns.
  Use memory_recall_kg(query="calibration improvement patterns ABM scoring regression", k=5)

Step 2: Run baseline calibration.
  Use pipeline_run_calibration(seed=1, days=30, n_rollouts=1)
  If tests_failed: note the failure count, do NOT investigate. Move to step 3.

Step 3: Spawn a worker to fix the failures.
  Use gitagent_spawn(agent_id="scorer-worker-1", role="scorer", brief="Fix the calibration test failures identified in step 2. Do NOT skip or weaken tests.")

Step 4: Check if worker proposed changes.
  Use gitagent_proposals()
  If NO proposals: report "Worker spawned, waiting for proposal" and STOP.
  If proposals exist: continue to step 5.

Step 5: Re-run calibration to score the result.
  Use pipeline_run_calibration(seed=1, days=30, n_rollouts=1)

Step 6: Compare against baseline.
  If tests pass now: use gitagent_integrate() then gitagent_finalize() to land the fix.
  If tests still fail: use improve_prompt() to record what didn't work.

Start with step 1 now."""


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

    import agents.deepagents.agent as agent_mod
    from agents.deepagents.logger import SessionLogger

    # Initialize session logger
    logger = SessionLogger()
    agent_mod.SESSION_LOGGER = logger
    logger.log_decision("session_start", f"calibration cycle, max_iterations={max_iterations}")

    try:
        agent = agent_mod.create_orchestrator(provider=provider, model=model, thread_id=thread_id)

        result = agent.invoke(
            {"messages": [{"role": "user", "content": prompt}]},
        )

        final_content = result["messages"][-1].content
        logger.log_summary(final_content)
        return final_content
    finally:
        logger.close()
        agent_mod.SESSION_LOGGER = None
