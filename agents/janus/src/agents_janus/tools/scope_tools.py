"""scope_tools.py — scope validation for gawt-based multi-agent sessions.

Validates that an agent's edits (tracked in gawt's edits table) stay within
its declared scope (edits_allow from subagents.yaml).

gawt does NOT enforce per-agent edit scopes — any agent can edit any file.
This module provides advisory validation after edits are made.
"""
from __future__ import annotations

import fnmatch
import json

from agents_janus.subagents.registry import Registry


def validate_edit_scope(
    agent_id: str,
    edited_files: list[str],
    agent_role: str,
    registry: Registry,
) -> str:
    """Validate that an agent's edits are within its declared scope.

    Args:
        agent_id: The gawt agent ID.
        edited_files: List of file paths that were edited.
        agent_role: The agent's role (e.g., "abm", "scoring").
        registry: The subagent registry.

    Returns:
        JSON with validation result:
        {
            "ok": bool,
            "in_scope": [paths in agent's edits_allow],
            "cross_scope": [{"path": str, "owner": str}] — owned by another agent,
            "unowned": [paths not in any agent's scope],
        }
    """
    try:
        spec = registry.get(agent_role)
    except KeyError:
        return json.dumps({
            "ok": False,
            "error": f"Unknown agent role: {agent_role}",
        })

    in_scope = []
    cross_scope = []
    unowned = []

    for path in edited_files:
        # Check if in own scope
        own_match = any(fnmatch.fnmatch(path, p) for p in spec.edits_allow)
        if own_match:
            in_scope.append(path)
            continue

        # Check if in another agent's scope
        owner = registry.find_owner(path)
        if owner and owner != agent_role:
            cross_scope.append({"path": path, "owner": owner})
        else:
            unowned.append(path)

    ok = len(cross_scope) == 0 and len(unowned) == 0
    return json.dumps({
        "ok": ok,
        "in_scope": in_scope,
        "cross_scope": cross_scope,
        "unowned": unowned,
    })
