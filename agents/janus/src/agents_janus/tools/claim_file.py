"""Claim file — lazy intent registration for sibling coordination."""
from __future__ import annotations
import json

def claim_file_tool(worktree_id: str, sibling_id: str, filepath: str, description: str = "") -> str:
    """Register a file claim. Lazy: ~20 tokens, no AST parsing."""
    from agents_janus.sibling.intent import claim_file
    return claim_file(worktree_id, sibling_id, filepath, description)
