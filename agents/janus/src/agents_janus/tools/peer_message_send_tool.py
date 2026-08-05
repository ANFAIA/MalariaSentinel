"""Send a peer message to a sibling."""
from __future__ import annotations
import json

def peer_message_send_tool(
    from_sibling: str,
    to_sibling: str,
    worktree_id: str,
    re: str,
    severity: str,
    trigger: str,
    context: dict,
    ask: str,
    thread_id: str = "",
) -> str:
    """Send a peer message (fire-and-forget)."""
    from agents_janus.sibling.peer_message import peer_message_send
    return peer_message_send(
        from_sibling=from_sibling,
        to_sibling=to_sibling,
        worktree_id=worktree_id,
        re=re,
        severity=severity,
        trigger=trigger,
        context=context,
        ask=ask,
        thread_id=thread_id,
    )
