"""Onboarding agent tools — status, diagnostics, and delegation for the centinela.

For shell access, the centinela uses the built-in `execute` tool (restricted
to `malariasim` by MalariasimShellBackend). For code-editing tasks, use
delegate_to_dispatcher to hand off to the dispatcher orchestrator.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent

# ---------------------------------------------------------------------------
# LLM helper — builds a ChatOpenAI client from env vars
# ---------------------------------------------------------------------------

def _resolve_llm():
    """Resolve an LLM client from environment variables.

    Uses ChatOpenRouter for OpenRouter, falls back to OpenAI for local models.
    Returns a langchain ChatOpenRouter or ChatOpenAI instance.
    """
    api_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENROUTER_KEY")
    if api_key:
        try:
            from langchain_openrouter import ChatOpenRouter
        except ImportError:
            raise ImportError("langchain-openrouter is required for OpenRouter LLM calls.")
        model = os.environ.get("ONBOARDING_MODEL", "xiaomi/mimo-v2.5")
        return ChatOpenRouter(model=model, api_key=api_key)

    openai_key = os.environ.get("OPENAI_API_KEY")
    if openai_key:
        try:
            from langchain_openai import ChatOpenAI
        except ImportError:
            raise ImportError("langchain-openai is required for local LLM calls.")
        model = os.environ.get("ONBOARDING_MODEL", "gpt-4o-mini")
        return ChatOpenAI(model=model, api_key=openai_key)

    raise ValueError(
        "No LLM API key found. Set OPENROUTER_API_KEY or OPENAI_API_KEY."
    )

# ---------------------------------------------------------------------------
# Stage definitions for the malariasim CLI pipeline
# ---------------------------------------------------------------------------
STAGES = ("download", "ingest", "abm", "score", "train", "predict")


def onboard_status() -> str:
    """Show current system status: scorecards, plans, subagents, recent runs.

    Returns JSON with all available status information.
    """
    info: dict = {"scorecards": {}, "plans": [], "subagents": [], "recent_runs": []}

    # Best historical scorecard
    best_path = Path("runs/scorecards/best_history.json")
    if best_path.exists():
        try:
            best = json.loads(best_path.read_text())
            info["scorecards"]["best_composite"] = best.get("composite")
            info["scorecards"]["best_ts"] = best.get("ts")
        except (json.JSONDecodeError, OSError):
            pass

    # Open plans
    plans_dir = Path("docs/plans/in-process")
    if plans_dir.exists():
        info["plans"] = [f.name for f in plans_dir.glob("*.md")]

    # Subagents
    try:
        from agents_janus.subagents.registry import load_registry
        reg = load_registry()
        info["subagents"] = list(reg.all().keys())
    except (FileNotFoundError, Exception):
        info["subagents"] = ["registry not available"]

    # Recent ABM runs
    runs_dir = Path("runs/abm")
    if runs_dir.exists():
        run_dirs = sorted(runs_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
        info["recent_runs"] = [d.name for d in run_dirs[:5] if d.is_dir()]

    return json.dumps(info, indent=2)


def onboard_list_components() -> str:
    """List all registered subagents with their specs."""
    try:
        from agents_janus.subagents.registry import load_registry
        reg = load_registry()
        result = []
        for name, spec in reg.all().items():
            result.append({
                "name": name,
                "description": spec.description,
                "model": f"{spec.provider}/{spec.model}",
                "edits_allow": list(spec.edits_allow),
                "mailbox_inbox": spec.mailbox_inbox,
                "spec": str(spec.spec_path) if spec.spec_path else None,
            })
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def _active_langfuse_client():
    """Return the langfuse client owned by the running orchestrator, if any.

    When delegate_to_dispatcher runs, the centinela's ObservabilityMiddleware
    holds the active Langfuse client. Propagating it to the delegated
    dispatcher keeps its trace visible in the same Langfuse project instead
    of running as an unobservable ghost.
    """
    try:
        import agents_janus.agent as agent_mod
        mw = getattr(agent_mod, "OBSERVABILITY_MIDDLEWARE", None)
        if mw is not None:
            return getattr(mw, "langfuse", None)
    except Exception:
        pass
    return None


def delegate_to_dispatcher(
    goal: str,
    context: str = "{}",
    plan_path: str = "",
    provider: str = "openrouter",
    model: str = "xiaomi/mimo-v2.5",
) -> str:
    """Delegate implementation work to the dispatcher orchestrator.

    Creates a dispatcher orchestrator, streams until done, returns summary.
    Runs in a separate LangGraph invocation (not nested in REPL).
    The centinela REPL is paused during execution — user sees LivePanel output.

    Args:
        goal: The objective for the dispatcher.
        context: JSON string with additional context (research findings, etc.).
        plan_path: Optional path to a plan file. If provided, the dispatcher
                   reads it as context for decomposition (equivalent to
                   `janus improve -g "..." --plan <path>`).
        provider: LLM provider (default: openrouter).
        model: Model identifier (default: xiaomi/mimo-v2.5).

    Returns:
        JSON with the dispatcher's summary.
    """
    try:
        ctx = json.loads(context) if isinstance(context, str) else context
    except json.JSONDecodeError:
        ctx = {"raw_context": context}

    try:
        from agents_janus.improvement import run_improvement
    except ImportError as e:
        return json.dumps({"status": "error", "error": f"Import failed: {e}"})

    try:
        result = run_improvement(
            goal=goal,
            plan_path=plan_path or None,
            provider=provider,
            model=model,
            context=ctx,
            langfuse_client=_active_langfuse_client(),
        )
        return json.dumps({"status": "ok", "goal": goal, "result": result})
    except Exception as e:
        return json.dumps({"status": "error", "goal": goal, "error": str(e)})


def onboard_ask_subagent(name: str, question: str) -> str:
    """Ask a specialist subagent a read-only question about the system.

    Builds the specialist's system prompt and invokes the LLM directly
    (no worktree, no gitagent, lightweight single call).

    Args:
        name: Subagent name (abm, scoring, ingest, download, prediction,
              training, data, commonlib).
        question: The question to ask.

    Returns:
        JSON with the specialist's response.
    """
    try:
        from agents_janus.subagents.registry import load_registry
        from agents_janus.subagents.builder import build_subagent_prompt
    except ImportError as e:
        return json.dumps({"status": "error", "error": f"Import failed: {e}"})

    # Load registry and validate subagent name
    try:
        registry = load_registry()
        spec = registry.get(name)
    except (FileNotFoundError, KeyError) as e:
        return json.dumps({
            "status": "error",
            "error": str(e),
            "available": list(registry.all().keys()) if "registry" in dir() else [],
        })

    # Build prompt (read-only question, no plugins needed)
    system_prompt = build_subagent_prompt(spec, all_specs=registry.all())

    # Resolve LLM and invoke
    try:
        llm = _resolve_llm()
    except (ImportError, ValueError) as e:
        return json.dumps({"status": "error", "error": str(e)})

    try:
        from langchain_core.messages import SystemMessage, HumanMessage
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=question),
        ]
    except ImportError:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ]

    try:
        response = llm.invoke(messages)
        answer = response.content if hasattr(response, "content") else str(response)
        return json.dumps({
            "status": "ok",
            "subagent": name,
            "question": question,
            "response": answer,
        })
    except Exception as e:
        return json.dumps({
            "status": "error",
            "subagent": name,
            "error": str(e),
        })
