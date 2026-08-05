"""Tests for fork sub-context and merge result."""
from __future__ import annotations

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))


def test_fork_context_fields():
    """ForkContext has all required fields."""
    from agents_janus.sibling.fork import ForkContext

    fork = ForkContext(
        parent_sibling_id="a",
        fork_id="f1",
        task_brief="negotiate",
        instructions="adapt",
        created_at="2026-01-01T00:00:00Z",
    )
    assert fork.parent_sibling_id == "a"
    assert fork.fork_id == "f1"
    assert not fork.merged


def test_readonly_context_peek():
    """ReadOnlyChatContext.peek returns last N messages."""
    from agents_janus.sibling.fork import ReadOnlyChatContext

    ctx = ReadOnlyChatContext()
    for i in range(10):
        ctx.add_message("user", f"msg {i}")
    last3 = ctx.peek(3)
    assert len(last3) == 3
    assert last3[0]["content"] == "msg 7"


def test_merge_result_truncation():
    """merge_result truncates to max_tokens."""
    from agents_janus.sibling.fork import ForkContext, merge_result

    fork = ForkContext("a", "f1", "brief", "instr", "ts")
    result = "word " * 500
    merged = merge_result(fork, result, use_summary=True, max_tokens=100)
    assert len(merged.split()) <= 105


def test_merge_result_raw():
    """merge_result without use_summary returns raw (truncated by char)."""
    from agents_janus.sibling.fork import ForkContext, merge_result

    fork = ForkContext("a", "f1", "brief", "instr", "ts")
    result = "x" * 5000
    merged = merge_result(fork, result, use_summary=False, max_tokens=100)
    assert len(merged) <= 4000


def test_create_readonly_context():
    """create_readonly_context builds from message list."""
    from agents_janus.sibling.fork import create_readonly_context

    msgs = [{"role": "user", "content": "hello"}, {"role": "assistant", "content": "hi"}]
    ctx = create_readonly_context(msgs)
    assert len(ctx.peek(10)) == 2
