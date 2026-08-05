"""Peer message — sibling↔sibling communication within a shared worktree."""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Literal

from agents_janus.sibling.state import get_conn


@dataclass(frozen=True)
class PeerMessage:
    id: str
    ts: str
    from_sibling: str
    to_sibling: str
    worktree_id: str
    re: str
    severity: Literal["info", "warn", "block"]
    trigger: Literal["file_overlap", "symbol_overlap", "merge_conflict", "completion"]
    context: dict
    ask: Literal["adapt", "counter_propose", "block", "ack_only"]
    thread_id: str
    ttl_minutes: int = 30
    status: Literal["open", "resolved", "expired"] = "open"


def peer_message_send(
    from_sibling: str,
    to_sibling: str,
    worktree_id: str,
    re: str,
    severity: str,
    trigger: str,
    context: dict,
    ask: str,
    thread_id: str = "",
    ttl_minutes: int = 30,
) -> str:
    """Send a peer message to a sibling's inbox."""
    msg_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    conn = get_conn()
    conn.execute(
        """INSERT INTO peer_messages
           (id, from_sibling, to_sibling, worktree_id, re, severity, trigger,
            context_json, ask, thread_id, ttl_minutes, status, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'open', ?)""",
        (msg_id, from_sibling, to_sibling, worktree_id, re, severity, trigger,
         json.dumps(context), ask, thread_id, ttl_minutes, now),
    )
    conn.commit()
    return json.dumps({"status": "sent", "message_id": msg_id, "to": to_sibling})


def peer_message_check_inbox(sibling_id: str, worktree_id: str) -> str:
    """Check inbox for a sibling. Returns list of open messages."""
    conn = get_conn()
    rows = conn.execute(
        """SELECT id, from_sibling, to_sibling, worktree_id, re, severity, trigger,
                  context_json, ask, thread_id, ttl_minutes, status, created_at
           FROM peer_messages
           WHERE to_sibling = ? AND worktree_id = ? AND status = 'open'
           ORDER BY created_at ASC""",
        (sibling_id, worktree_id),
    ).fetchall()

    messages = []
    for row in rows:
        messages.append({
            "id": row[0], "from_sibling": row[1], "to_sibling": row[2],
            "worktree_id": row[3], "re": row[4], "severity": row[5],
            "trigger": row[6], "context": json.loads(row[7]),
            "ask": row[8], "thread_id": row[9], "ttl_minutes": row[10],
            "status": row[11], "created_at": row[12],
        })

    return json.dumps({"messages": messages, "count": len(messages)})


def peer_message_mark_resolved(message_id: str, resolution: str = "ack") -> str:
    """Mark a peer message as resolved."""
    conn = get_conn()
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "UPDATE peer_messages SET status = 'resolved' WHERE id = ?",
        (message_id,),
    )
    conn.commit()
    return json.dumps({"status": "resolved", "message_id": message_id, "resolution": resolution})


def peer_message_counter_propose(
    message_id: str,
    to_sibling: str,
    re: str,
    context: dict,
    proposal: str,
    worktree_id: str,
    from_sibling: str,
) -> str:
    """Send a counter-proposal in response to a peer message."""
    return peer_message_send(
        from_sibling=from_sibling,
        to_sibling=to_sibling,
        worktree_id=worktree_id,
        re=f"counter: {re}",
        severity="warn",
        trigger="file_overlap",
        context={**context, "counter_proposal": proposal, "in_reply_to": message_id},
        ask="adapt",
    )
