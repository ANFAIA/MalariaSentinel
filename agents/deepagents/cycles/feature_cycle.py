"""Feature development cycle — research, implement, test."""
from __future__ import annotations

import json


FEATURE_PROMPT = """\
GOAL: {goal}

Run a feature development cycle for: {feature_name}
Description: {description}

FLOW — follow these steps IN ORDER:

Step 1: Recall relevant patterns and architecture decisions.
  Use memory_recall_kg(query="<feature topic> patterns architecture", k=5)

Step 2: Research if needed.
  Use opencode_search(query="<feature topic> implementation best practices")

Step 3: Open gitagent session and spawn a worker.
  Use gitagent_init()
  Use gitagent_start(feature="feature-<short-name>")
  Use gitagent_spawn(feature="feature-<short-name>", agent_id="abm-worker-1", role="abm")

Step 4: Create worker subagent with create_abm_worker_subagent(worktree_path).

Step 5: Check proposals.
  Use gitagent_proposals(feature="feature-<short-name>")
  If NO proposals: report "Worker spawned, waiting for proposal" and STOP.

Step 6: Review and decide.
  Use gitagent_diff(proposal_id, feature="feature-<short-name>")
  If OK → gitagent_accept; if not → gitagent_revise with feedback → back to step 5

Step 7: Run tests to verify.
  Use pipeline_run_calibration(seed=1, days=30, n_rollouts=1)

Step 8: Finalize.
  If tests pass: gitagent_integrate + gitagent_finalize
  If tests fail: gitagent_revise with feedback about failures → back to step 5

Keep all actions aligned with the GOAL above."""


def run_feature_cycle(
    name: str,
    description: str,
    goal: str,
    provider: str = "openrouter",
    model: str = "xiaomi/mimo-v2.5",
    thread_id: str = "feature-session",
    dry_run: bool = False,
) -> str:
    """Run a feature development cycle.

    Args:
        name: Feature name.
        description: Feature description.
        goal: The objective for this feature run.
        provider: LLM provider.
        model: Model identifier.
        thread_id: Thread ID for checkpointing.
        dry_run: If True, print the prompt without executing.

    Returns:
        The final agent response after the cycle completes.
    """
    prompt = FEATURE_PROMPT.format(feature_name=name, description=description, goal=goal)

    if dry_run:
        return json.dumps({
            "status": "dry_run",
            "prompt": prompt,
            "goal": goal,
            "feature_name": name,
        })

    from agents.deepagents.agent import create_orchestrator
    import agents.deepagents.agent as agent_mod
    from agents.deepagents.logger import SessionLogger

    # Initialize session logger
    logger = SessionLogger()
    agent_mod.SESSION_LOGGER = logger
    logger.log_decision("session_start", f"feature cycle: {name}, goal={goal}")

    try:
        agent = create_orchestrator(provider=provider, model=model, thread_id=thread_id)

        result = agent.invoke(
            {"messages": [{"role": "user", "content": prompt}]},
        )

        final_content = result["messages"][-1].content
        logger.log_summary(final_content)
        return final_content
    finally:
        logger.close()
        agent_mod.SESSION_LOGGER = None
