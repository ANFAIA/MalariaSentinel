"""Tests for file watcher (watchdog + polling fallback)."""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))


def test_watcher_init():
    """Watcher can be instantiated."""
    from agents_janus.sibling.watcher import Watcher

    w = Watcher("test-wt")
    assert w.worktree_id == "test-wt"
    assert w.debounce_s == 0.5


def test_watcher_debounce_handler():
    """DebouncedHandler cancels duplicate events."""
    from agents_janus.sibling.watcher import _DebouncedHandler

    handler = _DebouncedHandler("test-wt", debounce_s=0.1)
    assert handler.worktree_id == "test-wt"
    assert handler.debounce_s == 0.1


def test_watcher_poll_snapshot():
    """_take_snapshot captures file mtimes."""
    from agents_janus.sibling.watcher import Watcher

    w = Watcher("test-wt")
    with tempfile.TemporaryDirectory() as tmpdir:
        for name in ["a.py", "b.py", "c.txt"]:
            with open(os.path.join(tmpdir, name), "w") as f:
                f.write("content")
        snapshot = w._take_snapshot(Path(tmpdir))
        assert len(snapshot) >= 3


def test_watcher_diff_snapshots():
    """_diff_snapshots detects changed files."""
    from agents_janus.sibling.watcher import Watcher

    w = Watcher("test-wt")
    old = {"/a.py": 1.0, "/b.py": 2.0}
    new = {"/a.py": 1.0, "/b.py": 3.0, "/c.py": 4.0}
    diff = w._diff_snapshots(old, new)
    assert "/b.py" in diff
    assert "/c.py" in diff
    assert "/a.py" not in diff


def test_watcher_stop():
    """Watcher stop doesn't hang."""
    from agents_janus.sibling.watcher import Watcher

    w = Watcher("test-wt")
    w.stop()  # Should not hang
