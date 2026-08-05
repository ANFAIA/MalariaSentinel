"""Tests for lazy claim generation — low token cost."""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))


@pytest.fixture
def tmp_db(tmp_path):
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


def test_claim_is_lazy(tmp_db):
    """claim_file does NOT parse AST — just inserts a row."""
    from agents_janus.sibling.intent import claim_file

    result = json.loads(claim_file("test-wt", "sib-a", "/any/file.py", "editing"))
    assert result["status"] == "claimed"


def test_claim_no_ast_parsing(tmp_db):
    """claim_file works even if file doesn't exist."""
    from agents_janus.sibling.intent import claim_file

    result = json.loads(claim_file("test-wt", "sib-a", "/nonexistent/file.py"))
    assert result["status"] == "claimed"


def test_claim_description_stored(tmp_db):
    """claim_file stores the description."""
    from agents_janus.sibling.intent import claim_file

    claim_file("test-wt", "sib-a", "/f.py", "editing validate_token()")
    row = tmp_db.execute("SELECT description FROM claims WHERE filepath = '/f.py'").fetchone()
    assert "validate_token" in row[0]


def test_claim_default_status(tmp_db):
    """New claims have status='active'."""
    from agents_janus.sibling.intent import claim_file

    claim_file("test-wt", "sib-a", "/f.py")
    row = tmp_db.execute("SELECT status FROM claims WHERE filepath = '/f.py'").fetchone()
    assert row[0] == "active"


def test_claim_timestamp(tmp_db):
    """claim_file includes a created_at timestamp."""
    from agents_janus.sibling.intent import claim_file

    claim_file("test-wt", "sib-a", "/f.py")
    row = tmp_db.execute("SELECT created_at FROM claims WHERE filepath = '/f.py'").fetchone()
    assert row[0] is not None
    assert "T" in row[0]
