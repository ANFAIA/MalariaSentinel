"""Merge preflight — detects conflicts before actual merge using git merge-tree."""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class MergeConflict:
    filepath: str
    their_branch: str
    our_start: int
    our_end: int
    their_start: int
    their_end: int


@dataclass
class PreflightResult:
    ok: bool
    conflicts: list[MergeConflict]
    clean_files: list[str]


def merge_preflight_check(worktree_path: str, base_sha: str, head_sha: str) -> PreflightResult:
    """Run git merge-tree --write-tree to detect conflicts.

    Args:
        worktree_path: Path to the worktree to check.
        base_sha: The common ancestor commit.
        head_sha: The current HEAD to merge into.

    Returns:
        PreflightResult with conflict details.
    """
    wt = Path(worktree_path)
    try:
        result = subprocess.run(
            ["git", "merge-tree", "--write-tree", base_sha, head_sha],
            cwd=str(wt),
            capture_output=True,
            text=True,
            timeout=30,
        )

        conflicts = []
        clean_files = []

        lines = result.stdout.splitlines()
        current_file = None
        for line in lines:
            if line.startswith("CONFLICT"):
                parts = line.split(" in ")
                if len(parts) > 1:
                    current_file = parts[-1].strip()
                    conflicts.append(MergeConflict(
                        filepath=current_file,
                        their_branch="sibling",
                        our_start=0, our_end=0,
                        their_start=0, their_end=0,
                    ))
            elif line.startswith("Auto-merging"):
                parts = line.split()
                if len(parts) > 1:
                    clean_files.append(parts[-1].strip())

        return PreflightResult(
            ok=len(conflicts) == 0,
            conflicts=conflicts,
            clean_files=clean_files,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        return PreflightResult(ok=False, conflicts=[], clean_files=[])


def preflight_to_dict(result: PreflightResult) -> dict:
    """Convert PreflightResult to JSON-serializable dict."""
    return {
        "ok": result.ok,
        "conflicts": [asdict(c) for c in result.conflicts],
        "clean_files": result.clean_files,
    }
