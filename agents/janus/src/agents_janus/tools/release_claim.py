"""Release a file claim."""
from __future__ import annotations
import json

def release_claim_tool(claim_id: str) -> str:
    """Release a previously claimed file."""
    from agents_janus.sibling.intent import release_claim
    return release_claim(claim_id)
