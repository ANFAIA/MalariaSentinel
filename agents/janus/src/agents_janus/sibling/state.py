"""SQLite WAL schema for sibling coordination state."""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

_db_path: str | None = None
_conn: sqlite3.Connection | None = None


def init_state(worktree_id: str) -> None:
    """Create DB file at runs/sibling-{worktree_id}.db, create tables if not exist."""
    global _db_path, _conn
    runs_dir = Path("runs")
    runs_dir.mkdir(parents=True, exist_ok=True)
    _db_path = str(runs_dir / f"sibling-{worktree_id}.db")
    _conn = sqlite3.connect(_db_path)
    _conn.execute("PRAGMA journal_mode=WAL")
    _conn.executescript("""
        CREATE TABLE IF NOT EXISTS claims (
            id TEXT PRIMARY KEY,
            worktree_id TEXT,
            sibling_id TEXT,
            filepath TEXT,
            description TEXT,
            created_at TEXT,
            status TEXT DEFAULT 'active'
        );
        CREATE TABLE IF NOT EXISTS frame_stacks (
            sibling_id TEXT,
            frame_json TEXT,
            depth INTEGER,
            pushed_at TEXT
        );
        CREATE TABLE IF NOT EXISTS fork_dag (
            fork_id TEXT PRIMARY KEY,
            parent_sibling_id TEXT,
            task_brief TEXT,
            instructions TEXT,
            created_at TEXT,
            result TEXT,
            merged_at TEXT
        );
        CREATE TABLE IF NOT EXISTS peer_messages (
            id TEXT PRIMARY KEY,
            from_sibling TEXT,
            to_sibling TEXT,
            worktree_id TEXT,
            re TEXT,
            severity TEXT,
            trigger TEXT,
            context_json TEXT,
            ask TEXT,
            thread_id TEXT,
            ttl_minutes INTEGER DEFAULT 30,
            status TEXT DEFAULT 'open',
            created_at TEXT
        );
    """)
    _conn.commit()


def get_conn() -> sqlite3.Connection:
    """Return connection (creates if needed)."""
    if _conn is None:
        init_state("default")
    return _conn


class SiblingState:
    """Typed wrapper around the SQLite state for a single worktree."""

    def __init__(self, worktree_id: str, conn: sqlite3.Connection):
        self.worktree_id = worktree_id
        self._conn = conn

    def get_claims(self, filepath: str | None = None) -> list[dict]:
        if filepath:
            rows = self._conn.execute(
                "SELECT id, worktree_id, sibling_id, filepath, description, created_at, status "
                "FROM claims WHERE filepath = ?",
                (filepath,),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT id, worktree_id, sibling_id, filepath, description, created_at, status "
                "FROM claims"
            ).fetchall()
        return [
            {"id": r[0], "worktree_id": r[1], "sibling_id": r[2], "filepath": r[3],
             "description": r[4], "created_at": r[5], "status": r[6]}
            for r in rows
        ]

    def get_frame_stacks(self) -> dict[str, list[dict]]:
        rows = self._conn.execute(
            "SELECT sibling_id, frame_json FROM frame_stacks"
        ).fetchall()
        stacks: dict[str, list[dict]] = {}
        for sibling_id, frame_json in rows:
            stacks.setdefault(sibling_id, []).append(json.loads(frame_json))
        return stacks

    def get_unprocessed_claims(self) -> list[dict]:
        rows = self._conn.execute(
            "SELECT id, worktree_id, sibling_id, filepath, description, created_at, status "
            "FROM claims WHERE status = 'active'"
        ).fetchall()
        return [
            {"id": r[0], "worktree_id": r[1], "sibling_id": r[2], "filepath": r[3],
             "description": r[4], "created_at": r[5], "status": r[6]}
            for r in rows
        ]


def load_from_wal(worktree_id: str) -> dict | None:
    """Load state from DB, return None if no DB exists."""
    db_path = Path("runs") / f"sibling-{worktree_id}.db"
    if not db_path.exists():
        return None

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")

    claims_rows = conn.execute("SELECT * FROM claims").fetchall()
    claims = [
        {"id": r[0], "worktree_id": r[1], "sibling_id": r[2], "filepath": r[3],
         "description": r[4], "created_at": r[5], "status": r[6]}
        for r in claims_rows
    ]

    stack_rows = conn.execute("SELECT sibling_id, frame_json FROM frame_stacks").fetchall()
    frame_stacks: dict[str, list[dict]] = {}
    for sibling_id, frame_json in stack_rows:
        frame_stacks.setdefault(sibling_id, []).append(json.loads(frame_json))

    conn.close()

    return {
        "claims": claims,
        "unprocessed_claims": [c for c in claims if c["status"] == "active"],
        "frame_stacks": frame_stacks,
    }
