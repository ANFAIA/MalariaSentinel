"""manifest.py — session manifest (.gitagent/sessions/<feature>/plan.json).

The manifest is the orchestrator's single source of truth for the work split.
Written before any agent is spawned. Read by each specialist on init.
Updated by spawn_subagent when a specialist spawns a sub-agent.

Schema:
{
  "feature": str,
  "target_branch": str,
  "base_sha": str,
  "created_at": str (ISO),
  "agents": [
    {
      "requested_id": str,
      "agent_id": str | null,
      "role": str,
      "task": str,
      "owns": [str],
      "propose_order": int,
      "depends_on": [str],
      "spawned_by": "orchestrator" | "subagent",
      "status": "pending" | "spawned" | "running" | "completed" | "blocked"
    }
  ],
  "conflict_window_seconds": int,
  "specialist_spawns_allowed": bool
}
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def write_manifest(
    feature: str,
    agents: list[dict],
    target_branch: str = "main",
    base_sha: str = "",
    conflict_window_seconds: int = 30,
    specialist_spawns_allowed: bool = True,
    worktree_root: Path | None = None,
) -> Path:
    """Write the session manifest. Returns the manifest path.

    Args:
        feature: The gawt session feature key.
        agents: List of agent dicts with at least: requested_id, role, task, owns.
        target_branch: Git branch to commit onto.
        base_sha: HEAD SHA at session start.
        conflict_window_seconds: gawt conflict detection window.
        specialist_spawns_allowed: Whether specialists can spawn sub-agents.
        worktree_root: Root of the worktree. Defaults to .gitagent/worktree.

    Returns:
        Path to the written manifest.
    """
    root = worktree_root or Path(".gitagent/worktree")
    manifest_dir = root / ".gitagent" / "sessions" / feature
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = manifest_dir / "plan.json"

    # Ensure each agent has required fields
    for i, agent in enumerate(agents):
        agent.setdefault("requested_id", f"a_{i}")
        agent.setdefault("agent_id", None)
        agent.setdefault("role", "unknown")
        agent.setdefault("task", "")
        agent.setdefault("owns", [])
        agent.setdefault("propose_order", i)
        agent.setdefault("depends_on", [])
        agent.setdefault("spawned_by", "orchestrator")
        agent.setdefault("status", "pending")

    manifest = {
        "feature": feature,
        "target_branch": target_branch,
        "base_sha": base_sha,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "agents": agents,
        "conflict_window_seconds": conflict_window_seconds,
        "specialist_spawns_allowed": specialist_spawns_allowed,
    }

    manifest_path.write_text(json.dumps(manifest, indent=2))
    return manifest_path


def read_manifest(manifest_path: str | Path) -> dict:
    """Read the session manifest. Returns the parsed JSON."""
    path = Path(manifest_path)
    if not path.exists():
        raise FileNotFoundError(f"Manifest not found: {path}")
    return json.loads(path.read_text())


def append_agent(manifest_path: str | Path, agent_entry: dict) -> None:
    """Append a new agent entry to the manifest (used by spawn_subagent)."""
    path = Path(manifest_path)
    manifest = read_manifest(path)

    agent_entry.setdefault("status", "spawned")
    agent_entry.setdefault("spawned_by", "subagent")
    agent_entry.setdefault("depends_on", [])
    agent_entry.setdefault("owns", [])
    agent_entry.setdefault("propose_order", len(manifest["agents"]))

    manifest["agents"].append(agent_entry)
    path.write_text(json.dumps(manifest, indent=2))


def update_agent_status(
    manifest_path: str | Path,
    requested_id: str,
    status: str,
    agent_id: str | None = None,
) -> None:
    """Update an agent's status (and optionally agent_id) in the manifest."""
    path = Path(manifest_path)
    manifest = read_manifest(path)

    for agent in manifest["agents"]:
        if agent["requested_id"] == requested_id:
            agent["status"] = status
            if agent_id is not None:
                agent["agent_id"] = agent_id
            break

    path.write_text(json.dumps(manifest, indent=2))


def find_agent(manifest_path: str | Path, requested_id: str) -> dict | None:
    """Find an agent entry by requested_id."""
    manifest = read_manifest(manifest_path)
    for agent in manifest["agents"]:
        if agent["requested_id"] == requested_id:
            return agent
    return None


def get_manifest_path(feature: str, worktree_root: Path | None = None) -> Path:
    """Get the manifest path for a feature."""
    root = worktree_root or Path(".gitagent/worktree")
    return root / ".gitagent" / "sessions" / feature / "plan.json"
