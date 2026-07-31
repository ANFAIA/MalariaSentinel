"""Scope validator — plain code, not LLM. Validates proposals against subagent edit scopes."""
from __future__ import annotations
import fnmatch
import json
from agents_janus.subagents.registry import Registry

def validate_proposal_scope(
    diff_paths: list[str],
    agent_name: str,
    registry: Registry,
) -> dict:
    """Validate that a proposal only touches files within the agent's scope.
    
    Returns:
        {
            "ok": bool,
            "in_scope": [paths that are in the agent's edits_allow],
            "cross_scope": [{"path": str, "owner": str}] — paths owned by another agent,
            "unowned": [paths not in any agent's scope],
        }
    """
    in_scope = []
    cross_scope = []
    unowned = []
    
    spec = registry.get(agent_name)
    for path in diff_paths:
        # Check if in own scope
        own_match = any(fnmatch.fnmatch(path, p) for p in spec.edits_allow)
        if own_match:
            in_scope.append(path)
            continue
        # Check if in another agent's scope
        owner = registry.find_owner(path)
        if owner and owner != agent_name:
            cross_scope.append({"path": path, "owner": owner})
        else:
            unowned.append(path)
    
    return {
        "ok": len(cross_scope) == 0 and len(unowned) == 0,
        "in_scope": in_scope,
        "cross_scope": cross_scope,
        "unowned": unowned,
    }
