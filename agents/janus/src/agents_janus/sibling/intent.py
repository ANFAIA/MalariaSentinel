"""Lazy intent generation — claim/release/query file claims."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from agents_janus.sibling.state import get_conn


def claim_file(worktree_id: str, sibling_id: str, filepath: str, description: str = "") -> str:
    """INSERT into claims, return JSON status."""
    claim_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    conn = get_conn()
    conn.execute(
        "INSERT INTO claims (id, worktree_id, sibling_id, filepath, description, created_at, status) "
        "VALUES (?, ?, ?, ?, ?, ?, 'active')",
        (claim_id, worktree_id, sibling_id, filepath, description, now),
    )
    conn.commit()
    return json.dumps({"status": "claimed", "claim_id": claim_id, "filepath": filepath})


def release_claim(claim_id: str) -> str:
    """UPDATE status='released', return JSON."""
    conn = get_conn()
    conn.execute("UPDATE claims SET status = 'released' WHERE id = ?", (claim_id,))
    conn.commit()
    return json.dumps({"status": "released", "claim_id": claim_id})


def query_claims(worktree_id: str, filepath: str) -> list[dict]:
    """SELECT active claims for filepath, return list of dicts."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, worktree_id, sibling_id, filepath, description, created_at, status "
        "FROM claims WHERE worktree_id = ? AND filepath = ? AND status = 'active'",
        (worktree_id, filepath),
    ).fetchall()
    return [
        {"id": r[0], "worktree_id": r[1], "sibling_id": r[2], "filepath": r[3],
         "description": r[4], "created_at": r[5], "status": r[6]}
        for r in rows
    ]
