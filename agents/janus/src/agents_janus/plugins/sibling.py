"""SiblingPlugin — adds sibling coordination tools for shared-worktree calls."""
from __future__ import annotations
from agents_janus.plugins.base import Plugin
from agents_janus.subagents.base import SubagentSpec


class SiblingPlugin(Plugin):
    """Adds read+write + peer_message + fork_brief for sibling invocations."""
    name = "sibling"

    def __init__(self, shared_worktree_id: str = ""):
        self.shared_worktree_id = shared_worktree_id

    def tools(self, spec: SubagentSpec) -> list:
        from agents_janus.tools.claim_file import claim_file_tool
        from agents_janus.tools.release_claim import release_claim_tool
        from agents_janus.tools.query_claims import query_claims_tool
        from agents_janus.tools.peer_message_send_tool import peer_message_send_tool
        from agents_janus.tools.peer_message_check import peer_message_check_tool
        from agents_janus.tools.peer_message_resolve import peer_message_resolve_tool
        from agents_janus.tools.fork_brief_tool import fork_brief_tool
        from agents_janus.tools.merge_result_tool import merge_result_tool
        return [
            claim_file_tool, release_claim_tool, query_claims_tool,
            peer_message_send_tool, peer_message_check_tool, peer_message_resolve_tool,
            fork_brief_tool, merge_result_tool,
        ]

    def preamble(self, spec: SubagentSpec) -> str:
        return (
            "You are in a shared worktree with sibling agents. "
            "Claim files before editing. Check peer_message inbox for overlap warnings. "
            "Use SCAN protocol for negotiation. Push/pop frame stack during forks."
        )
