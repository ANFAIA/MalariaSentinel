"""Tests for peer message — sibling↔sibling communication."""
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


def test_send_and_check(tmp_db):
    """Send a message, check inbox."""
    from agents_janus.sibling.peer_message import peer_message_send, peer_message_check_inbox

    peer_message_send("sib-a", "sib-b", "wt1", "overlap warning", "warn", "symbol_overlap", {"path": "/f.py"}, "adapt")
    result = json.loads(peer_message_check_inbox("sib-b", "wt1"))
    assert result["count"] == 1
    assert result["messages"][0]["severity"] == "warn"


def test_mark_resolved(tmp_db):
    """Mark resolved removes from open inbox."""
    from agents_janus.sibling.peer_message import peer_message_send, peer_message_check_inbox, peer_message_mark_resolved

    r = json.loads(peer_message_send("a", "b", "wt1", "test", "info", "file_overlap", {}, "ack_only"))
    peer_message_mark_resolved(r["message_id"])
    check = json.loads(peer_message_check_inbox("b", "wt1"))
    assert check["count"] == 0


def test_counter_propose(tmp_db):
    """counter_propose sends a response."""
    from agents_janus.sibling.peer_message import peer_message_send, peer_message_counter_propose, peer_message_check_inbox

    r = json.loads(peer_message_send("a", "b", "wt1", "overlap", "warn", "file_overlap", {"path": "/f.py"}, "adapt"))
    peer_message_counter_propose(
        message_id=r["message_id"],
        to_sibling="a",
        re="counter",
        context={"path": "/f.py"},
        proposal="I take foo(), you take bar()",
        worktree_id="wt1",
        from_sibling="b",
    )
    check = json.loads(peer_message_check_inbox("a", "wt1"))
    assert check["count"] == 1
    assert "counter" in check["messages"][0]["re"]


def test_multiple_recipients(tmp_db):
    """Messages to different siblings don't mix."""
    from agents_janus.sibling.peer_message import peer_message_send, peer_message_check_inbox

    peer_message_send("a", "b", "wt1", "msg1", "info", "file_overlap", {}, "ack_only")
    peer_message_send("a", "c", "wt1", "msg2", "info", "file_overlap", {}, "ack_only")
    b_inbox = json.loads(peer_message_check_inbox("b", "wt1"))
    c_inbox = json.loads(peer_message_check_inbox("c", "wt1"))
    assert b_inbox["count"] == 1
    assert c_inbox["count"] == 1
    assert b_inbox["messages"][0]["re"] == "msg1"
    assert c_inbox["messages"][0]["re"] == "msg2"


def test_message_fields(tmp_db):
    """Peer message has all required fields."""
    from agents_janus.sibling.peer_message import peer_message_send, peer_message_check_inbox

    peer_message_send("a", "b", "wt1", "test", "block", "merge_conflict", {"path": "/f.py"}, "block", thread_id="t1")
    result = json.loads(peer_message_check_inbox("b", "wt1"))
    msg = result["messages"][0]
    assert msg["from_sibling"] == "a"
    assert msg["to_sibling"] == "b"
    assert msg["severity"] == "block"
    assert msg["trigger"] == "merge_conflict"
    assert msg["ask"] == "block"
    assert msg["thread_id"] == "t1"
