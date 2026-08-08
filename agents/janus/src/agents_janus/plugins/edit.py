from __future__ import annotations

from typing import Any, Callable

from agents_janus.plugins.base import Plugin
from agents_janus.subagents.base import SubagentSpec


class EditPlugin(Plugin):
    name = "edit"

    def permissions(self, spec: SubagentSpec) -> list:
        # Permissions are set by the orchestrator in agent.py.
        # The shared worktree path (/.gitagent/worktree/**) is configured there.
        return []

    def preamble(self, spec: SubagentSpec) -> str:
        return (
            "You work in a shared gawt worktree. "
            "ALWAYS use mcp__gitagent__edit_file or mcp__gitagent__write_file for ALL file changes. "
            "NEVER use the host's Edit/Write tools — they bypass attribution and conflict tracking. "
            "Always pass agent_id to every gitagent call. "
            "Set start_intent before your first edit. "
            "Check inbox after each significant edit."
        )

    def tools(self, spec: SubagentSpec) -> list[Callable]:
        # MCP tools are injected by agent.py via mcp_bridge.py.
        # EditPlugin only provides preamble — no additional tools.
        return []
