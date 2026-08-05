"""Tests for sibling coordination — claim, notify, fork, merge lifecycle."""
from __future__ import annotations

import json
import sqlite3
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))


@pytest.fixture
def tmp_db(tmp_path):
    """Initialize a temp SQLite DB for testing."""
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


def test_claim_file(tmp_db):
    """claim_file inserts a claim row."""
    from agents_janus.sibling.intent import claim_file

    result = json.loads(claim_file("test-wtree", "sibling-a", "/path/to/file.py", "editing function foo"))
    assert result["status"] == "claimed"
    row = tmp_db.execute("SELECT * FROM claims WHERE filepath = '/path/to/file.py'").fetchone()
    assert row is not None


def test_release_claim(tmp_db):
    """release_claim marks claim as released."""
    from agents_janus.sibling.intent import claim_file, release_claim

    claim_file("test-wtree", "sibling-a", "/path/to/file.py")
    row = tmp_db.execute("SELECT id FROM claims WHERE filepath = '/path/to/file.py'").fetchone()
    result = json.loads(release_claim(row[0]))
    assert result["status"] == "released"


def test_query_claims(tmp_db):
    """query_claims returns active claims for a filepath."""
    from agents_janus.sibling.intent import claim_file, query_claims

    claim_file("test-wtree", "sibling-a", "/path/to/file.py")
    claim_file("test-wtree", "sibling-b", "/path/to/file.py")
    claims = query_claims("test-wtree", "/path/to/file.py")
    assert len(claims) == 2
    assert claims[0]["sibling_id"] == "sibling-a"
    assert claims[1]["sibling_id"] == "sibling-b"


def test_peer_message_send(tmp_db):
    """peer_message_send inserts a peer message."""
    from agents_janus.sibling.peer_message import peer_message_send

    result = json.loads(peer_message_send(
        from_sibling="sibling-a",
        to_sibling="sibling-b",
        worktree_id="test-wtree",
        re="file_overlap",
        severity="warn",
        trigger="symbol_overlap",
        context={"filepath": "/path/to/file.py"},
        ask="adapt",
    ))
    assert result["status"] == "sent"
    row = tmp_db.execute("SELECT * FROM peer_messages WHERE to_sibling = 'sibling-b'").fetchone()
    assert row is not None


def test_peer_message_check_inbox(tmp_db):
    """peer_message_check_inbox returns open messages."""
    from agents_janus.sibling.peer_message import peer_message_send, peer_message_check_inbox

    peer_message_send("a", "b", "wt1", "test", "info", "file_overlap", {}, "ack_only")
    result = json.loads(peer_message_check_inbox("b", "wt1"))
    assert result["count"] == 1
    assert result["messages"][0]["re"] == "test"


def test_peer_message_mark_resolved(tmp_db):
    """peer_message_mark_resolved marks message as resolved."""
    from agents_janus.sibling.peer_message import peer_message_send, peer_message_mark_resolved, peer_message_check_inbox

    r = json.loads(peer_message_send("a", "b", "wt1", "test", "info", "file_overlap", {}, "ack_only"))
    msg_id = r["message_id"]
    result = json.loads(peer_message_mark_resolved(msg_id))
    assert result["status"] == "resolved"
    check = json.loads(peer_message_check_inbox("b", "wt1"))
    assert check["count"] == 0


def test_frame_stack_push_pop():
    """FrameStack push/pop works correctly."""
    from agents_janus.sibling.frame_stack import FrameStack, Frame

    stack = FrameStack("sibling-a", max_depth=3)
    stack.push(Frame(goal="edit foo", steps_completed=[], next_step="modify function"))
    stack.push(Frame(goal="negotiate with sibling-b", steps_completed=["read overlap"], next_step="decide"))
    assert stack.depth == 2
    top = stack.pop()
    assert top.goal == "negotiate with sibling-b"
    assert stack.depth == 1


def test_frame_stack_overflow():
    """FrameStack raises OverflowError at max depth."""
    from agents_janus.sibling.frame_stack import FrameStack, Frame

    stack = FrameStack("sibling-a", max_depth=2)
    stack.push(Frame(goal="f1"))
    stack.push(Frame(goal="f2"))
    with pytest.raises(OverflowError):
        stack.push(Frame(goal="f3"))


def test_frame_stack_render_resume():
    """FrameStack render_resume produces readable output."""
    from agents_janus.sibling.frame_stack import FrameStack, Frame

    stack = FrameStack("sibling-a")
    stack.push(Frame(goal="edit scoring", steps_completed=["read file"], next_step="modify function"))
    resume = stack.render_resume()
    assert "edit scoring" in resume
    assert "step" in resume


def test_fork_brief_and_merge_result():
    """fork_brief creates a fork, merge_result returns <=500 tokens."""
    from agents_janus.sibling.fork import fork_brief, merge_result

    fork = fork_brief("sibling-a", "Negotiate overlap on validate_token()", "Adapt to sibling-B's edit")
    assert fork.fork_id is not None
    assert fork.parent_sibling_id == "sibling-a"
    long_result = "word " * 1000
    merged = merge_result(fork, long_result, use_summary=True, max_tokens=50)
    assert len(merged.split()) <= 55
