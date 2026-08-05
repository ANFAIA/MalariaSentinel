"""Fork a sub-context for sibling negotiation."""
from __future__ import annotations
import json

def fork_brief_tool(
    parent_sibling_id: str,
    instructions: str,
    task_brief: str,
) -> str:
    """Create a forked sub-context for negotiation."""
    from agents_janus.sibling.fork import fork_brief
    fork = fork_brief(parent_sibling_id, instructions, task_brief)
    return json.dumps({
        "fork_id": fork.fork_id,
        "parent_sibling_id": fork.parent_sibling_id,
        "task_brief": fork.task_brief,
        "created_at": fork.created_at,
    })
