"""Onboarding agent — conversational REPL for the MalariaSentinel SDSS.

Uses the dual-mode orchestrator (centinela mode) to interact with users.
The centinela has access to 8 specialist subagents, onboard tools, and
can delegate implementation work to the dispatcher.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_AGENT_DIR = Path(__file__).resolve().parent

ONBOARD_BANNER = """\

======================================================================
  Centinela — MalariaSentinel SDSS Assistant
  Escribe tu pregunta o tarea. 'salir' para terminar.
======================================================================
"""


def run_onboarding(
    provider: str = "openrouter",
    model: str = "xiaomi/mimo-v2.5",
    quiet: bool = False,
    langfuse_client=None,
    *,
    env: str = "",
) -> str:
    """Run the conversational onboarding agent.

    Creates the centinela orchestrator and enters a REPL loop.
    The agent responds in the user's language and executes tools directly.

    Args:
        provider: LLM provider.
        model: Model identifier.
        quiet: If True, suppress technical output (tool calls, etc.).
        langfuse_client: Optional pre-configured langfuse.Langfuse instance.
        env: Environment name (dev/staging/production) for Langfuse tags.

    Returns:
        Final status message when the user exits.
    """
    import agents_janus.agent as agent_mod
    from agents_janus.logger import SessionLogger

    logger = SessionLogger()
    agent_mod.SESSION_LOGGER = logger

    agent = agent_mod.create_orchestrator(
        provider=provider,
        model=model,
        mode="centinela",
        langfuse_client=langfuse_client,
        goal="onboarding",
        env=env,
    )

    print(ONBOARD_BANNER, file=sys.stderr)

    # Conversation history for multi-turn
    messages: list[dict] = []

    def _cleanup():
        agent_mod.SESSION_LOGGER = None
        if langfuse_client is not None:
            try:
                langfuse_client.flush()
            except Exception:
                pass

    while True:
        try:
            user_input = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nHasta luego!", file=sys.stderr)
            _cleanup()
            return json.dumps({"status": "quit"})

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "salir", "q"):
            print("Hasta luego!", file=sys.stderr)
            _cleanup()
            return json.dumps({"status": "quit"})

        # Add user message to history
        messages.append({"role": "user", "content": user_input})

        # Stream agent response
        try:
            full_response = ""
            for event in agent.stream(
                {"messages": messages},
                stream_mode="updates",
            ):
                if not quiet and isinstance(event, dict):
                    for node_name, delta in event.items():
                        if isinstance(delta, dict) and "messages" in delta:
                            for msg in delta["messages"]:
                                if hasattr(msg, "content") and msg.content:
                                    content = msg.content if isinstance(msg.content, str) else str(msg.content)
                                    if content and not content.startswith("{"):
                                        full_response = content

            if full_response:
                # Add assistant response to history
                messages.append({"role": "assistant", "content": full_response})
                print(f"\n{full_response}\n", file=sys.stderr)
            else:
                print("\n(no response)\n", file=sys.stderr)

        except KeyboardInterrupt:
            print("\n(interrupted — continuing conversation)\n", file=sys.stderr)
        except Exception as e:
            print(f"\nError: {e}\n", file=sys.stderr)


# Keep helpers for backwards compat (used by cli.py status command)
def _show_status() -> str:
    """Show current status: scorecards, open plans, active investigations."""
    from agents_janus.tools.onboard_tools import onboard_status
    return onboard_status()


def _list_components() -> str:
    """List all subagents with their specs."""
    from agents_janus.tools.onboard_tools import onboard_list_components
    return onboard_list_components()
