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
    Check(name="session_started", description="Primary called mcp__gitagent__start_session to open a shared worktree"),
    Check(name="agents_registered", description="Subagents called mcp__gitagent__register_agent in the shared session"),
    Check(name="intent_declared", description="Agent called mcp__gitagent__start_intent before first edit (semantic attribution)"),
    Check(name="inbox_checked_post_edit", description="Agent called mcp__gitagent__check_inbox after edit to detect conflicts"),
    Check(name="peer_message_sent", description="mcp__gitagent__send_message exchanged between agents"),
    Check(name="resolve_conflict_invoked", description="resolve_conflict tool invoked for self-fork on inbox conflict"),
    Check(name="session_finalized", description="mcp__gitagent__finalize_session produced a commit"),
    Check(name="agents_unregistered", description="Agents called mcp__gitagent__unregister_agent before finalization"),
    Check(name="no_orchestrator_arbitration", description="No orchestrator tool_call between specialist edits"),
    Check(name="scan_markers_emitted", description="SCAN markers present in resolve_conflict output"),
]


def get_check(name: str) -> Check | None:
    """Get a check by name."""
    for c in CHECKS:
        if c.name == name:
            return c
    return None
