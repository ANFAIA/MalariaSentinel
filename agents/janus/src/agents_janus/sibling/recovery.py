"""Recovery — hot-restart watcher state from SQLite WAL."""
from __future__ import annotations

from agents_janus.sibling.state import SiblingState, load_from_wal
from agents_janus.sibling.watcher import Watcher
from agents_janus.sibling.frame_stack import FrameStack, Frame
from agents_janus.sibling import coordination


def hot_restart(worktree_id: str) -> Watcher:
    """On janus startup, recover watcher state from SQLite WAL.

    RTO: <1 second (state reload is O(claims * avg_edit_time)).
    """
    state = load_from_wal(worktree_id)
    if state is None:
        return Watcher(worktree_id)

    # Replay unprocessed claims
    for claim in state.get("unprocessed_claims", []):
        coordination.on_file_modified(worktree_id, claim.get("filepath", ""))

    # Re-attach frame stacks
    for sibling_id, frames in state.get("frame_stacks", {}).items():
        stack = FrameStack.from_list(sibling_id, frames)
        import threading
        setattr(threading.current_thread(), f"_frame_stack_{sibling_id}", stack)

    # Start a fresh watcher
    watcher = Watcher(worktree_id)
    watcher.start()
    return watcher
