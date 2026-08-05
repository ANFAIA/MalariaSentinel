"""Check peer message inbox."""
from __future__ import annotations
import json

def peer_message_check_tool(sibling_id: str, worktree_id: str) -> str:
    """Check inbox for peer messages."""
    from agents_janus.sibling.peer_message import peer_message_check_inbox
    return peer_message_check_inbox(sibling_id, worktree_id)
