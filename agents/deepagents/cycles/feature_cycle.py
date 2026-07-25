"""Feature development cycle — research, implement, test."""
from __future__ import annotations

import json


FEATURE_PROMPT = """\
Run a feature development cycle for: {feature_name}
Description: {description}

1. Recall relevant patterns and architecture decisions from the knowledge graph
2. Research the literature using opencode_search if needed
3. Plan the implementation with write_todos
4. Spawn a feature-worker in an isolated worktree using gitagent_spawn
5. The worker implements the feature and proposes via gitagent
6. Run tests to verify the implementation
7. If tests pass, accept the proposal; if not, patch the worker prompt and retry
8. Integrate and finalize
"""


def run_feature_cycle(
    name: str,
    description: str,
    provider: str = "openrouter",
    model: str = "xiaomi/mimo-v2.5",
    thread_id: str = "feature-session",
    dry_run: bool = False,
) -> str:
    """Run a feature development cycle.

    Args:
        name: Feature name.
        description: Feature description.
        provider: LLM provider.
        model: Model identifier.
        thread_id: Thread ID for checkpointing.
        dry_run: If True, print the prompt without executing.

    Returns:
        The final agent response after the cycle completes.
    """
    prompt = FEATURE_PROMPT.format(feature_name=name, description=description)

    if dry_run:
        return json.dumps({
            "status": "dry_run",
            "prompt": prompt,
            "feature_name": name,
        })

    from agents.deepagents.agent import create_orchestrator
    import agents.deepagents.agent as agent_mod
    from agents.deepagents.logger import SessionLogger

    # Initialize session logger
    logger = SessionLogger()
    agent_mod.SESSION_LOGGER = logger
    logger.log_decision("session_start", f"feature cycle: {name}")

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
