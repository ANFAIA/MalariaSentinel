"""Query claims for a file path."""
from __future__ import annotations
import json

def query_claims_tool(worktree_id: str, filepath: str) -> str:
    """Query all active claims for a filepath."""
    from agents_janus.sibling.intent import query_claims
    claims = query_claims(worktree_id, filepath)
    return json.dumps({"claims": claims, "count": len(claims)})
