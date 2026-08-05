"""File watcher — detects changes in shared worktrees for sibling coordination."""
from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Callable

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileModifiedEvent
    HAS_WATCHDOG = True
except ImportError:
    HAS_WATCHDOG = False
    # Fallback base class when watchdog is not installed
    class FileSystemEventHandler:
        pass

from agents_janus.sibling import coordination


class _DebouncedHandler(FileSystemEventHandler):
    """Debounces file modification events."""

    def __init__(self, worktree_id: str, debounce_s: float = 0.5):
        self.worktree_id = worktree_id
        self.debounce_s = debounce_s
        self._timers: dict[str, threading.Timer] = {}
        self._lock = threading.Lock()

    def on_modified(self, event):
        if event.is_directory:
            return
        path = event.src_path
        if "/.git/" in path or "/__pycache__/" in path:
            return
        with self._lock:
            if path in self._timers:
                self._timers[path].cancel()
            timer = threading.Timer(self.debounce_s, self._handle_change, args=[path])
            self._timers[path] = timer
            timer.start()

    def _handle_change(self, path: str) -> None:
        """Called after debounce period — triggers coordination."""
        try:
            coordination.on_file_modified(self.worktree_id, path)
        except Exception:
            pass


class Watcher:
    """File system watcher for shared worktree changes."""

    def __init__(self, worktree_id: str, *, debounce_s: float = 0.5, polling_interval_s: float = 60.0):
        self.worktree_id = worktree_id
        self.debounce_s = debounce_s
        self.polling_interval_s = polling_interval_s
        self._observer: Observer | None = None
        self._handler: _DebouncedHandler | None = None
        self._polling_thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._snapshot: dict[str, float] = {}  # path -> mtime

    def start(self) -> None:
        """Start the file watcher. Uses watchdog if available, falls back to polling."""
        if HAS_WATCHDOG:
            self._start_watchdog()
        else:
            self._start_polling()

    def _start_watchdog(self) -> None:
        """Start watchdog-based file watching."""
        wt_path = self._get_worktree_path()
        if not wt_path:
            return
        self._handler = _DebouncedHandler(self.worktree_id, self.debounce_s)
        self._observer = Observer()
        self._observer.schedule(
            self._handler,
            path=str(wt_path),
            recursive=True,
        )
        self._observer.start()

    def _start_polling(self) -> None:
        """Fallback: poll file mtimes every polling_interval_s."""
        self._stop_event.clear()
        self._polling_thread = threading.Thread(
            target=self._poll_loop, daemon=True, name=f"watcher-{self.worktree_id}"
        )
        self._polling_thread.start()

    def _poll_loop(self) -> None:
        """Polling loop that detects file changes by mtime."""
        wt_path = self._get_worktree_path()
        if not wt_path:
            return
        self._snapshot = self._take_snapshot(wt_path)
        while not self._stop_event.is_set():
            self._stop_event.wait(self.polling_interval_s)
            if self._stop_event.is_set():
                break
            new_snapshot = self._take_snapshot(wt_path)
            changed = self._diff_snapshots(self._snapshot, new_snapshot)
            self._snapshot = new_snapshot
            for path in changed:
                try:
                    coordination.on_file_modified(self.worktree_id, path)
                except Exception:
                    pass

    def _take_snapshot(self, path: Path) -> dict[str, float]:
        """Take a snapshot of file mtimes."""
        snapshot = {}
        try:
            for f in path.rglob("*"):
                if f.is_file() and ".git" not in str(f) and "__pycache__" not in str(f):
                    try:
                        snapshot[str(f)] = f.stat().st_mtime
                    except OSError:
                        pass
        except OSError:
            pass
        return snapshot

    def _diff_snapshots(self, old: dict[str, float], new: dict[str, float]) -> list[str]:
        """Return list of paths that changed between snapshots."""
        changed = []
        for path, mtime in new.items():
            if path not in old or old[path] != mtime:
                changed.append(path)
        return changed

    def _get_worktree_path(self) -> Path | None:
        """Resolve worktree path from worktree_id."""
        from agents_janus.sibling.state import get_conn
        try:
            conn = get_conn()
            row = conn.execute(
                "SELECT worktree_id FROM claims WHERE worktree_id = ? LIMIT 1",
                (self.worktree_id,),
            ).fetchone()
            if row:
                return Path(f".gitagent/features/*/agents/{self.worktree_id}/worktree")
        except Exception:
            pass
        return None

    def stop(self) -> None:
        """Stop the file watcher."""
        self._stop_event.set()
        if self._observer:
            self._observer.stop()
            self._observer.join(timeout=5)
        if self._polling_thread:
            self._polling_thread.join(timeout=5)
