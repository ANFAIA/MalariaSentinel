"""Named checks for sibling coordination trial validation."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass
class Check:
    name: str
    description: str
    passed: bool = False
    evidence: str = ""


CHECKS: list[Check] = [
    Check(name="primary_spawned_worktree", description="Primary subagent spawned a worktree"),
    Check(name="sibling_join_shared_worktree", description="Sibling joined the shared worktree"),
    Check(name="claim_file_registered", description="claim_file registered in SQLite"),
    Check(name="watcher_fired_on_file_overlap", description="Watcher detected file overlap"),
    Check(name="peer_message_sent", description="Peer message sent between siblings"),
    Check(name="fork_brief_invoked", description="fork_brief created a sub-context"),
    Check(name="merge_result_returned", description="merge_result returned ≤500 tokens"),
    Check(name="frame_stack_push_pop", description="Frame stack push/pop recorded in SQLite"),
    Check(name="no_parent_arbitration", description="No orchestrator tool_call between siblings"),
    Check(name="scan_markers_emitted", description="SCAN markers present in fork output"),
]


def get_check(name: str) -> Check | None:
    """Get a check by name."""
    for c in CHECKS:
        if c.name == name:
            return c
    return None
