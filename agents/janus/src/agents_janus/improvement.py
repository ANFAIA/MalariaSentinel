"""Improvement orchestrator — dispatcher mode."""
from __future__ import annotations


def _emit_panel_events(panel, event: dict) -> None:
    """Bridge LangGraph state updates into PanelState events.

    agent.stream(stream_mode="updates") yields dicts keyed by node name:
        {"agent": {"messages": [AIMessage(...)]}}
        {"tools":  {"messages": [ToolMessage(...)]}}

    PanelState.update() expects events with an "event" key. This function
    extracts messages from LangGraph updates and emits the right panel events.
    """
    if not isinstance(event, dict):
        return

    for node_name, delta in event.items():
        if not isinstance(delta, dict) or "messages" not in delta:
            continue

        for msg in delta["messages"]:
            msg_type = type(msg).__name__

            if msg_type == "AIMessage":
                # Extract token usage from AIMessage
                prompt_tokens = 0
                completion_tokens = 0
                if hasattr(msg, "usage_metadata") and msg.usage_metadata:
                    prompt_tokens = msg.usage_metadata.get("input_tokens", 0) or 0
                    completion_tokens = msg.usage_metadata.get("output_tokens", 0) or 0

                content = ""
                if hasattr(msg, "content") and msg.content:
                    content = msg.content if isinstance(msg.content, str) else str(msg.content)

                # Check if this is a tool-call message (has tool_calls)
                has_tool_calls = hasattr(msg, "tool_calls") and bool(getattr(msg, "tool_calls", None))

                # ALWAYS count the LLM call + tokens (every AIMessage = one LLM call)
                panel.on_event({
                    "event": "llm_call",
                    "step": panel.state.current_step + 1,
                    "model": panel.state.current_model or "unknown",
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "response_preview": content[:500] if content else f"[tool_calls: {len(getattr(msg, 'tool_calls', []))} calls]",
                })

            elif msg_type == "ToolMessage":
                tool_name = getattr(msg, "name", None) or "unknown"
                content = ""
                if hasattr(msg, "content") and msg.content:
                    content = msg.content if isinstance(msg.content, str) else str(msg.content)

                panel.on_event({
                    "event": "tool_call",
                    "tool": tool_name,
                    "input": {},
                    "output": content[:500],
                    "latency_s": 0.0,
                })


def run_improvement(
    goal: str,
    plan_path: str | None = None,
    provider: str = "openrouter",
    model: str = "xiaomi/mimo-v2.5",
    thread_id: str = "improvement-session",
    context: dict | None = None,
    quiet: bool = False,
    langfuse_client=None,
    *,
    env: str = "",
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
        env: Environment name (dev/staging/production) for Langfuse tags.

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
            mode="dispatcher",
            goal=goal,
            env=env,
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
                # Bridge LangGraph node-keyed updates into PanelState events
                _emit_panel_events(panel, event)
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

        # Print Langfuse trace URL if available
        trace_url = _get_trace_url(agent_mod)
        if trace_url:
            import sys
            print(f"\n🔗 Langfuse trace: {trace_url}", file=sys.stderr)

        return final_content
    finally:
        if langfuse_client is not None:
            try:
                langfuse_client.flush()
            except Exception:
                pass
        logger.close()
        agent_mod.SESSION_LOGGER = None
        agent_mod.OBSERVABILITY_MIDDLEWARE = None


def _get_trace_url(agent_mod) -> str | None:
    """Extract the Langfuse trace URL from the observability middleware."""
    try:
        mw = agent_mod.OBSERVABILITY_MIDDLEWARE
        if mw is not None:
            return mw.get_trace_url()
    except Exception:
        pass
    return None
