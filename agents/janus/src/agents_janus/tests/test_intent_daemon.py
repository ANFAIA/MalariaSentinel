"""Tests for intent daemon — lazy claim generation."""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))


@pytest.fixture
def tmp_db(tmp_path):
    """Initialize a temp SQLite DB."""
    from agents_janus.sibling import state

    db = tmp_path / "test.db"
    conn = sqlite3.connect(str(db))
    conn.executescript("""
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
    conn.commit()
    state._conn = conn
    yield conn
    state._conn = None
    conn.close()


def test_claim_inserts_row(tmp_db):
    """claim_file inserts a row into claims table."""
    from agents_janus.sibling.intent import claim_file

    result = json.loads(claim_file("test-wt", "sib-a", "/path/to/foo.py"))
    assert result["status"] == "claimed"
    assert tmp_db.execute("SELECT COUNT(*) FROM claims").fetchone()[0] == 1


def test_multiple_claims_same_file(tmp_db):
    """Multiple siblings can claim the same file."""
    from agents_janus.sibling.intent import claim_file

    claim_file("test-wt", "sib-a", "/f.py")
    claim_file("test-wt", "sib-b", "/f.py")
    assert tmp_db.execute("SELECT COUNT(*) FROM claims WHERE filepath = '/f.py'").fetchone()[0] == 2


def test_release_claim(tmp_db):
    """release_claim sets status to 'released'."""
    from agents_janus.sibling.intent import claim_file, release_claim

    claim_file("test-wt", "sib-a", "/f.py")
    row = tmp_db.execute("SELECT id FROM claims WHERE filepath = '/f.py'").fetchone()
    release_claim(row[0])
    row2 = tmp_db.execute("SELECT status FROM claims WHERE id = ?", (row[0],)).fetchone()
    assert row2[0] == "released"


def test_query_claims_returns_active(tmp_db):
    """query_claims returns only active claims."""
    from agents_janus.sibling.intent import claim_file, release_claim, query_claims

    claim_file("test-wt", "sib-a", "/f.py")
    claim_file("test-wt", "sib-b", "/f.py")
    row = tmp_db.execute("SELECT id FROM claims WHERE sibling_id = 'sib-a'").fetchone()
    release_claim(row[0])
    active = query_claims("test-wt", "/f.py")
    assert len(active) == 1
    assert active[0]["sibling_id"] == "sib-b"


def test_query_claims_empty_path(tmp_db):
    """query_claims returns empty for unknown path."""
    from agents_janus.sibling.intent import query_claims

    claims = query_claims("test-wt", "/nonexistent.py")
    assert len(claims) == 0
