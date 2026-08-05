"""Merge a fork result back into parent context."""
from __future__ import annotations
import json

def merge_result_tool(fork_id: str, result: str, use_summary: bool = False) -> str:
    """Merge fork result back, returning a ≤500 token summary."""
    from agents_janus.sibling.fork import ForkContext, merge_result
    fork = ForkContext(
        parent_sibling_id="",
        fork_id=fork_id,
        task_brief="",
        instructions="",
        created_at="",
        result=result,
    )
    merged = merge_result(fork, result, use_summary=use_summary)
    return json.dumps({"merged_summary": merged, "token_estimate": len(merged.split())})
