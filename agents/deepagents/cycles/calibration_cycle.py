"""Calibration improvement cycle — recall, plan, spawn, score, improve."""
from __future__ import annotations

import json


CALIBRATION_PROMPT = """\
GOAL: {goal}

Run a calibration improvement cycle (max {max_iterations} iterations).

FLOW — follow these steps IN ORDER:

Step 1: Recall past patterns.
  Use memory_recall_kg(query="calibration improvement patterns ABM scoring regression", k=5)

Step 2: Run baseline calibration.
  Use pipeline_run_calibration(seed=1, days=30, n_rollouts=1)
  If tests_failed: note the failure count, do NOT investigate. Move to step 3.

Step 3: Open gitagent session and spawn a worker.
  Use gitagent_init()
  Use gitagent_start(feature="calibration-<short-id>")  # pick a unique name
  Use gitagent_spawn(feature="calibration-<short-id>", agent_id="abm-worker-1", role="abm")

Step 4: Create worker subagent with create_abm_worker_subagent(worktree_path).
  The worker will compile, run tests, and score results in its isolated worktree.

Step 5: Check proposals.
  Use gitagent_proposals(feature="calibration-<short-id>")
  If NO proposals: report "Worker spawned, waiting for proposal" and STOP.
  If proposals exist: continue to step 6.

Step 6: Review the diff.
  Use gitagent_diff(proposal_id, feature="calibration-<short-id>")
  Review the changes carefully.

Step 7: Decide.
  If changes are correct: gitagent_accept(proposal_id, feature="calibration-<short-id>")
  If changes need revision: gitagent_revise(proposal_id, feature="calibration-<short-id>", feedback="...") then go back to step 5
  If changes are wrong: gitagent_reject(proposal_id, feature="calibration-<short-id>", reason="...")

Step 8: Re-run calibration to score the result.
  Use pipeline_run_calibration(seed=1, days=30, n_rollouts=1)

Step 9: Finalize.
  If tests pass: gitagent_integrate(feature="calibration-<short-id>") then gitagent_finalize(feature="calibration-<short-id>", message="calibration: <description>")
  If tests still fail: use improve_prompt() to record what didn't work, then go back to step 3 with a new feature name.

Keep all actions aligned with the GOAL above. Start with step 1 now."""


def run_calibration_cycle(
    goal: str,
    max_iterations: int = 10,
    provider: str = "openrouter",
    model: str = "xiaomi/mimo-v2.5",
    thread_id: str = "calibration-session",
    dry_run: bool = False,
) -> str:
    """Run the ABM calibration improvement cycle.

    Args:
        goal: The objective for this calibration run.
        max_iterations: Maximum number of improvement iterations.
        provider: LLM provider.
        model: Model identifier.
        thread_id: Thread ID for checkpointing.
        dry_run: If True, print the prompt without executing.

    Returns:
        The final agent response after the cycle completes.
    """
    prompt = CALIBRATION_PROMPT.format(goal=goal, max_iterations=max_iterations)

    if dry_run:
        return json.dumps({
            "status": "dry_run",
            "prompt": prompt,
            "goal": goal,
            "max_iterations": max_iterations,
        })

    import agents.deepagents.agent as agent_mod
    from agents.deepagents.logger import SessionLogger

    # Initialize session logger
    logger = SessionLogger()
    agent_mod.SESSION_LOGGER = logger
    logger.log_decision("session_start", f"calibration cycle, goal={goal}, max_iterations={max_iterations}")

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
