"""Improvement orchestrator — dispatcher mode."""
from __future__ import annotations


def run_improvement(
    goal: str,
    plan_path: str | None = None,
    provider: str = "openrouter",
    model: str = "xiaomi/mimo-v2.5",
    thread_id: str = "improvement-session",
    context: dict | None = None,
    quiet: bool = False,
    langfuse_client=None,
) -> str:
    """Run the improvement dispatcher for a given goal.

    Creates the orchestrator agent and streams until done. The orchestrator
    prompt (loaded from disk by agent.py) contains the full methodology.

    Args:
        goal: The objective (required).
        plan_path: Optional path to a plan file to read as context.
        provider: LLM provider.
        model: Model identifier.
        thread_id: Thread ID for checkpointing.
        context: Additional context from onboarding.
        quiet: If True, suppress the live terminal panel.
        langfuse_client: Optional langfuse.Langfuse instance.

    Returns:
        The orchestrator's final response.
    """
    from pathlib import Path
    import json

    import agents_janus.agent as agent_mod
    from agents_janus.live_panel import LivePanel
    from agents_janus.logger import SessionLogger

    logger = SessionLogger()
    agent_mod.SESSION_LOGGER = logger
    logger.log_decision("improvement_start", f"goal={goal}, plan={plan_path}")

    # Build the user message
    parts = [f"GOAL: {goal}\n"]
    if plan_path:
        plan_file = Path(plan_path)
        if plan_file.exists():
            parts.append(f"## Plan ({plan_path})\n{plan_file.read_text()}\n")
        else:
            parts.append(f"Plan file not found: {plan_path}\n")
    if context:
        parts.append(f"## Context from onboarding\n{json.dumps(context, indent=2)}\n")
    prompt = "\n".join(parts)

    def _on_abort() -> None:
        logger.log_decision("aborted_by_user", "Ctrl-C during improvement stream")
        if langfuse_client is not None:
            try:
                langfuse_client.flush()
            except Exception:
                pass

    try:
        agent = agent_mod.create_orchestrator(
            provider=provider,
            model=model,
            thread_id=thread_id,
            langfuse_client=langfuse_client,
        )

        with LivePanel(
            session_id=logger.session_dir.name,
            quiet=quiet,
            on_abort=_on_abort,
        ) as panel:
            full_messages = []
            for event in agent.stream(
                {"messages": [{"role": "user", "content": prompt}]},
                stream_mode="updates",
            ):
                panel.on_event(event)
                if isinstance(event, dict):
                    for node_name, delta in event.items():
                        if isinstance(delta, dict) and "messages" in delta:
                            for msg in delta["messages"]:
                                if hasattr(msg, "content") and msg.content:
                                    full_messages.append({
                                        "type": type(msg).__name__,
                                        "content": msg.content if isinstance(msg.content, str) else str(msg.content),
                                    })

        final_content = full_messages[-1]["content"] if full_messages else "No response"
        logger.log_summary(final_content)
        return final_content
    finally:
        if langfuse_client is not None:
            try:
                langfuse_client.flush()
            except Exception:
                pass
        logger.close()
        agent_mod.SESSION_LOGGER = None
