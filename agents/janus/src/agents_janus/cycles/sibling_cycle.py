"""Sibling cycle — spawn siblings for cooperative work in a shared worktree."""
from __future__ import annotations
import json


def spawn_siblings(
    primary_id: str,
    sibling_specs: list[dict],
    worktree_id: str,
    brief: str,
) -> list[dict]:
    """Spawn sibling agents in a shared worktree.

    Args:
        primary_id: The primary subagent's ID.
        sibling_specs: List of {"name": str, "description": str} for each sibling.
        worktree_id: Shared worktree identifier.
        brief: The task brief for all siblings.

    Returns:
        List of spawned sibling info dicts.
    """
    from agents_janus.sibling.state import init_state
    from agents_janus.sibling.intent import claim_file
    from agents_janus.sibling.watcher import Watcher
    from agents_janus.sibling.coordination import init_coordinator

    # Initialize state for this worktree
    init_state(worktree_id)

    # Initialize coordinator
    init_coordinator(worktree_id)

    # Start watcher
    watcher = Watcher(worktree_id)
    watcher.start()

    # Spawn info for each sibling
    spawned = []
    for spec in sibling_specs:
        spawned.append({
            "name": spec["name"],
            "description": spec.get("description", ""),
            "worktree_id": worktree_id,
            "role": "sibling",
        })

    return spawned


def monitor_siblings(worktree_id: str) -> dict:
    """Check sibling status: active claims, pending messages, frame stacks."""
    from agents_janus.sibling.state import get_conn

    try:
        conn = get_conn()

        # Active claims
        claims = conn.execute(
            "SELECT sibling_id, filepath, description FROM claims WHERE worktree_id = ? AND status = 'active'",
            (worktree_id,),
        ).fetchall()

        # Pending peer messages
        messages = conn.execute(
            "SELECT from_sibling, to_sibling, re, severity FROM peer_messages WHERE worktree_id = ? AND status = 'open'",
            (worktree_id,),
        ).fetchall()

        return {
            "worktree_id": worktree_id,
            "active_claims": [{"sibling": c[0], "filepath": c[1], "description": c[2]} for c in claims],
            "pending_messages": [{"from": m[0], "to": m[1], "re": m[2], "severity": m[3]} for m in messages],
        }
    except Exception as e:
        return {"worktree_id": worktree_id, "error": str(e)}
