"""Improvement orchestrator — edit-capable, goal-driven, registry-based."""
from __future__ import annotations
import json
from pathlib import Path


def run_improvement(
    goal: str,
    plan_path: str | None = None,
    provider: str = "openrouter",
    model: str = "xiaomi/mimo-v2.5",
    thread_id: str = "improvement-session",
    context: dict | None = None,
) -> str:
    """Run the improvement orchestrator for a given goal.

    Args:
        goal: The objective (required).
        plan_path: Optional path to a plan file to read as context.
        provider: LLM provider.
        model: Model identifier.
        thread_id: Thread ID for checkpointing.
        context: Additional context from onboarding (answers, menu_key, etc.).

    Returns:
        The orchestrator's final response.
    """
    from agents.janus.subagents.registry import load_registry

    reg = load_registry()

    # Build the prompt
    prompt_parts = [f"GOAL: {goal}\n"]

    if plan_path:
        plan_file = Path(plan_path)
        if plan_file.exists():
            plan_content = plan_file.read_text()
            prompt_parts.append(f"## Plan ({plan_path})\n{plan_content}\n")
        else:
            prompt_parts.append(f"Plan file not found: {plan_path}\n")

    if context:
        prompt_parts.append(f"## Context from onboarding\n{json.dumps(context, indent=2)}\n")

    # List available subagents
    prompt_parts.append("## Available subagents\n")
    for name, spec in reg.all().items():
        prompt_parts.append(f"- **{name}**: {spec.description} (model={spec.model}, plugins={list(spec.plugins)})")

    prompt_parts.append("\n## Methodology\n")
    prompt_parts.append("Follow the standard improvement methodology: reconnaissance → diagnostics → hypotheses → diagnosis → delegate → validate.")
    prompt_parts.append("\nBefore editing, call `mailbox_check_inbox` for the target subagent.")
    prompt_parts.append("After proposals, the scope validator runs automatically.")
    prompt_parts.append("After any ABM task, scoring runs automatically via ScorerPlugin.")

    prompt = "\n".join(prompt_parts)

    # Delegate to the existing orchestrator with the built prompt
    import agents.janus.agent as agent_mod
    from agents.janus.logger import SessionLogger

    logger = SessionLogger()
    agent_mod.SESSION_LOGGER = logger
    logger.log_decision("improvement_start", f"goal={goal}, plan={plan_path}")

    try:
        agent = agent_mod.create_orchestrator(provider=provider, model=model, thread_id=thread_id)

        full_messages = []
        for event in agent.stream(
            {"messages": [{"role": "user", "content": prompt}]},
            stream_mode="updates",
        ):
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
        logger.close()
        agent_mod.SESSION_LOGGER = None
