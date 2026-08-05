"""Sibling coordination — orchestrates conflict detection and resolution."""
from __future__ import annotations

import json
from pathlib import Path

from agents_janus.sibling import intent, peer_message, ast_index
from agents_janus.sibling.merge_preflight import merge_preflight_check, preflight_to_dict

# Module-level coordinator instance (set by init)
_coordinator: SiblingCoordinator | None = None


def init_coordinator(worktree_id: str) -> SiblingCoordinator:
    """Initialize the global coordinator for a worktree."""
    global _coordinator
    _coordinator = SiblingCoordinator(worktree_id)
    return _coordinator


def get_coordinator() -> SiblingCoordinator | None:
    return _coordinator


def on_file_modified(worktree_id: str, filepath: str) -> None:
    """Called by the watcher when a file is modified. Lazy intent generation."""
    if _coordinator is None:
        return
    _coordinator.handle_file_modified(filepath)


class SiblingCoordinator:
    """Coordinates sibling activities in a shared worktree."""

    def __init__(self, worktree_id: str):
        self.worktree_id = worktree_id
        self._ast_index = ast_index.ASTIndex()

    def handle_file_modified(self, filepath: str) -> None:
        """Handle a file modification — check claims, detect conflicts, notify."""
        # 1. Check claims — who else has touched this file?
        claims = intent.query_claims(self.worktree_id, filepath)

        if len(claims) < 2:
            return

        # 2. Overlap detected — lazy AST parse
        try:
            symbols = self._ast_index.parse(filepath)
        except Exception:
            symbols = []

        # 3. Identify conflicting symbols
        conflicting_symbols = []
        for claim in claims:
            if claim.get("sibling_id") != _current_sibling_id():
                conflicting_symbols.extend([
                    {"name": s.name, "kind": s.kind, "line": s.start_line}
                    for s in symbols
                ])

        if not conflicting_symbols:
            return

        # 4. Generate peer message
        peer_message.peer_message_send(
            from_sibling=_current_sibling_id(),
            to_sibling=claims[0].get("sibling_id", ""),
            worktree_id=self.worktree_id,
            re=f"file_overlap: {Path(filepath).name}",
            severity="warn",
            trigger="symbol_overlap",
            context={
                "filepath": filepath,
                "symbols": conflicting_symbols[:5],
                "claim_count": len(claims),
            },
            ask="adapt",
        )

    def check_merge_preflight(self, base_sha: str, head_sha: str, worktree_path: str) -> dict:
        """Run merge preflight check."""
        result = merge_preflight_check(worktree_path, base_sha, head_sha)
        return preflight_to_dict(result)


def _current_sibling_id() -> str:
    """Get the current sibling's ID from thread-local or default."""
    import threading
    return getattr(threading.current_thread(), "_sibling_id", "unknown")
