"""Named checks for gawt MCP coordination trial validation."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass
class Check:
    name: str
    description: str
    passed: bool = False
    evidence: str = ""


CHECKS: list[Check] = [
    Check(name="session_started", description="Primary called mcp__gitagent__start_session to open the shared worktree"),
    Check(name="agents_registered", description="Subagents called mcp__gitagent__register_agent in the shared session"),
    Check(name="intent_declared", description="Agent called mcp__gitagent__start_intent before first edit (semantic attribution)"),
    Check(name="read_informed_before_write", description="Agent used informed read_file (pheromone/diff) before editing"),
    Check(name="write_lock_protocol", description="Writes go through gawt edit/write with per-file lock handling"),
    Check(name="rejection_handled", description="Informed write rejection (status: rejected / STALE_WRITE) led to re-read + retry"),
    Check(name="pheromone_traceable", description="Edits recorded in the pheromone (mcp__gitagent__list_edits) with intent attribution"),
    Check(name="session_snapshotted", description="mcp__gitagent__snapshot_session published a partial commit to the target branch"),
    Check(name="agents_unregistered", description="Agents called mcp__gitagent__unregister_agent before snapshot"),
    Check(name="no_orchestrator_arbitration", description="No orchestrator tool_call between specialist edits"),
    Check(name="scan_markers_emitted", description="SCAN evaluation / informed rejection handling markers present"),
]


def get_check(name: str) -> Check | None:
    """Get a check by name."""
    for c in CHECKS:
        if c.name == name:
            return c
    return None
