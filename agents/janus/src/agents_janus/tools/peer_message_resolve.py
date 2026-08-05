"""Resolve a peer message."""
from __future__ import annotations
import json

def peer_message_resolve_tool(message_id: str, resolution: str = "ack") -> str:
    """Mark a peer message as resolved."""
    from agents_janus.sibling.peer_message import peer_message_mark_resolved
    return peer_message_mark_resolved(message_id, resolution)
