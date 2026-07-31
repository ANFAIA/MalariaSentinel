"""Handoff tool — onboarding orchestrator invokes the improvement orchestrator."""
from __future__ import annotations
import json

def handoff_to_improver(goal: str, context: dict | None = None) -> str:
    """Hand off a goal from the onboarding orchestrator to the improvement orchestrator.
    
    Runs synchronously in the same process so mailbox state is shared.
    Returns the improver's summary as a string.
    """
    from agents_janus.cycles.improvement_cycle import run_improvement_cycle
    result = run_improvement_cycle(goal=goal, context=context or {})
    return json.dumps({"status": "ok", "goal": goal, "result": result})

__all__ = ["handoff_to_improver"]
