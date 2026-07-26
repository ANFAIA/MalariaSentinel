"""Research + improvement cycle — search, analyze, propose improvements."""
from __future__ import annotations

import json


RESEARCH_PROMPT = """\
GOAL: {goal}

Run a research and improvement cycle for topic: {topic}

FLOW — follow these steps IN ORDER:

Step 1: Recall what the knowledge graph already knows.
  Use memory_recall_kg(query="{topic} findings patterns", k=5)

Step 2: Search the literature.
  Use opencode_search(query="{topic} recent findings 2024 2025")

Step 3: Analyze findings and identify 2-3 actionable improvements.

Step 4: Open gitagent session and spawn workers.
  Use gitagent_init()
  Use gitagent_start(feature="research-<short-topic>")
  Use gitagent_spawn(feature="research-<short-topic>", agent_id="abm-worker-1", role="abm")

Step 5: Create worker subagent with create_abm_worker_subagent(worktree_path).

Step 6: Check proposals and review.
  Use gitagent_proposals + gitagent_diff
  Accept improvements that measurably improve the composite score.

Step 7: Run calibration to measure impact.
  Use pipeline_run_calibration(seed=1, days=30, n_rollouts=1)

Step 8: Finalize accepted improvements.
  gitagent_integrate + gitagent_finalize

Step 9: Record findings in the knowledge graph.
  Use improve_prompt() to record what worked and what didn't.

Keep all actions aligned with the GOAL above."""


def run_research_cycle(
    topic: str,
    goal: str,
    cycles: int = 1,
    provider: str = "openrouter",
    model: str = "xiaomi/mimo-v2.5",
    thread_id: str = "research-session",
    dry_run: bool = False,
) -> str:
    """Run a research + improvement cycle.

    Args:
        topic: Research topic to investigate.
        goal: The objective for this research run.
        cycles: Number of research cycles to run.
        provider: LLM provider.
        model: Model identifier.
        thread_id: Thread ID for checkpointing.
        dry_run: If True, print the prompt without executing.

    Returns:
        The final agent response after the cycle completes.
    """
    prompt = RESEARCH_PROMPT.format(topic=topic, goal=goal)

    if dry_run:
        return json.dumps({
            "status": "dry_run",
            "prompt": prompt,
            "goal": goal,
            "topic": topic,
            "cycles": cycles,
        })

    from agents.deepagents.agent import create_orchestrator
    import agents.deepagents.agent as agent_mod
    from agents.deepagents.logger import SessionLogger

    # Initialize session logger
    logger = SessionLogger()
    agent_mod.SESSION_LOGGER = logger
    logger.log_decision("session_start", f"research cycle: {topic}, goal={goal}, cycles={cycles}")

    try:
        agent = create_orchestrator(provider=provider, model=model, thread_id=thread_id)

        all_results = []
        for i in range(cycles):
            result = agent.invoke(
                {"messages": [{"role": "user", "content": prompt}]},
            )
            all_results.append(result["messages"][-1].content)

        final = "\n\n---\n\n".join(all_results)
        logger.log_summary(final)
        return final
    finally:
        logger.close()
        agent_mod.SESSION_LOGGER = None
