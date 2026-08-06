"""Onboarding agent — conversational REPL for the MalariaSentinel SDSS.

Replaces the old numbered-menu onboarding with an interactive agent that
understands natural language and executes tools directly. Bilingual (es/en).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_AGENT_DIR = Path(__file__).resolve().parent
_PROJECT_SKILLS = _REPO_ROOT / "agents" / "skills"

ONBOARD_SYSTEM_PROMPT = """\
You are the MalariaSentinel Centinela assistant. You help users interact with the SDSS (Spatial Decision Support System) for malaria elimination.

LANGUAGE: Respond in the same language the user uses. If they write in Spanish, respond in Spanish. If English, respond in English. Be natural and conversational.

YOUR CAPABILITIES (use your tools):
- Run ABM simulations (onboard_run_abm)
- Run individual pipeline stages (onboard_run_stage: download, ingest, abm, score, train, predict)
- Run the full 6-stage pipeline (onboard_run_pipeline)
- Check system status: scorecards, plans, subagents (onboard_status)
- Diagnose simulation issues with trajectory data (onboard_diagnose)
- List available subagents and components (onboard_list_components)
- Delegate complex code-editing tasks to the improvement orchestrator (onboard_delegate)
- Ask specialists about their domain: onboard_ask_subagent(name, question)
- Recall past patterns and pitfalls from the knowledge base (memory_recall_kg)

PIPELINE STAGES (order matters):
1. download — fetch raw data (ERA5, CHIRPS, etc.)
2. ingest — build env tensor, host density, mobility matrices
3. abm — run agent-based mosquito simulation
4. score — run calibration scorers (D1-D14 + composite)
5. train — train U-Net surrogate model
6. predict — generate risk predictions

HOW TO BEHAVE:
- When the user says something vague (e.g. "run the simulation"), ask a clarifying question before acting. Which AOI? How many days?
- When the user asks about status or results, use onboard_status first.
- When the user reports a problem (e.g. "the population goes extinct"), use onboard_diagnose to get data, then analyze and explain.
- When the user wants code changes (new features, parameter fixes, bug fixes), explain what you'll do, then delegate via onboard_delegate.
- Always explain results in plain language, not raw JSON. Summarize key findings.
- If a tool returns an error, explain what went wrong and suggest next steps.

EXAMPLES:
- "Ejecuta el ABM para Ghana" → onboard_run_abm(aoi="ghana")
- "¿Cuál es el estado?" → onboard_status()
- "Run stage 3 for Ghana" → onboard_run_stage(stage="abm", aoi="ghana")
- "La población se extingue" → onboard_diagnose(symptom="population extinction"), then analyze
- "Añade un scorer para el ciclo gonotrófico" → onboard_delegate(goal="Add gonotrophic cycle scorer D15")

When you don't know what the user wants, ask. Don't guess.
"""


def _build_agent(provider: str, model: str, langfuse_client=None):
    """Build the onboarding deepagent with onboard tools."""
    try:
        from deepagents import create_deep_agent, FilesystemPermission
        from deepagents.backends import FilesystemBackend
    except ImportError:
        raise ImportError(
            "The 'deepagents' package is required. "
            "Install with: pip install 'mal-janus' or pip install deepagents"
        )

    # Resolve LLM
    if provider == "openrouter":
        try:
            from langchain_openai import ChatOpenAI
        except ImportError:
            raise ImportError("langchain-openai is required for OpenRouter.")
        import os
        api_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENROUTER_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY env var required for OpenRouter")
        llm = ChatOpenAI(
            model=model,
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
        )
    else:
        try:
            from langchain.chat_models import init_chat_model
        except ImportError:
            raise ImportError("langchain-core is required.")
        llm = init_chat_model(model=model, model_provider=provider)

    backend = FilesystemBackend(root_dir=str(_REPO_ROOT), virtual_mode=True)

    # Import onboard tools
    from agents_janus.tools.onboard_tools import (
        onboard_run_abm,
        onboard_run_stage,
        onboard_run_pipeline,
        onboard_status,
        onboard_diagnose,
        onboard_list_components,
        onboard_delegate,
        onboard_ask_subagent,
    )
    from agents_janus.tools.kg_tool import memory_recall_kg

    tools = [
        onboard_run_abm,
        onboard_run_stage,
        onboard_run_pipeline,
        onboard_status,
        onboard_diagnose,
        onboard_list_components,
        onboard_delegate,
        onboard_ask_subagent,
        memory_recall_kg,
    ]

    # Build observability middleware if langfuse is active
    middleware = []
    if langfuse_client is not None:
        import agents_janus.agent as agent_mod
        if agent_mod.SESSION_LOGGER is not None:
            from agents_janus.observability import ObservabilityMiddleware
            middleware.append(ObservabilityMiddleware(agent_mod.SESSION_LOGGER, langfuse_client=langfuse_client))

    skills = []
    if _PROJECT_SKILLS.is_dir():
        skills.append("agents/skills/")

    return create_deep_agent(
        model=llm,
        tools=tools,
        system_prompt=ONBOARD_SYSTEM_PROMPT,
        backend=backend,
        skills=skills or None,
        name="centinela-onboarding",
        middleware=middleware or None,
        permissions=[
            FilesystemPermission(operations=["read"], paths=["/**"], mode="allow"),
            FilesystemPermission(operations=["write"], paths=["/**"], mode="deny"),
        ],
    )


def run_onboarding(
    provider: str = "openrouter",
    model: str = "xiaomi/mimo-v2.5",
    quiet: bool = False,
    langfuse_client=None,
) -> str:
    """Run the conversational onboarding agent.

    Creates a deepagent with onboard tools and enters a REPL loop.
    The agent responds in the user's language and executes tools directly.

    Args:
        provider: LLM provider.
        model: Model identifier.
        quiet: If True, suppress technical output (tool calls, etc.).
        langfuse_client: Optional pre-configured langfuse.Langfuse instance.

    Returns:
        Final status message when the user exits.
    """
    import agents_janus.agent as agent_mod
    from agents_janus.logger import SessionLogger

    logger = SessionLogger()
    agent_mod.SESSION_LOGGER = logger

    agent = _build_agent(provider=provider, model=model, langfuse_client=langfuse_client)

    print("\n" + "=" * 60, file=sys.stderr)
    print("  Centinela — MalariaSentinel SDSS Assistant", file=sys.stderr)
    print("  Escribe tu pregunta o tarea. 'salir' para terminar.", file=sys.stderr)
    print("=" * 60 + "\n", file=sys.stderr)

    # Conversation history for multi-turn
    messages: list[dict] = []

    def _cleanup():
        agent_mod.SESSION_LOGGER = None
        if langfuse_client is not None:
            try:
                langfuse_client.flush()
            except ValueError:
                # OpenTelemetry context detach error — non-fatal, traces already
                # shipped by ObservabilityMiddleware.after_agent.
                pass
            except Exception:
                pass

    while True:
        try:
            user_input = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n¡Hasta luego!", file=sys.stderr)
            _cleanup()
            return json.dumps({"status": "quit"})

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "salir", "q"):
            print("¡Hasta luego!", file=sys.stderr)
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
