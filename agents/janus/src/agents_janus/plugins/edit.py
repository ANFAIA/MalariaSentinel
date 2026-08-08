from __future__ import annotations

from typing import Any, Callable

from langchain_core.tools import tool

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
            "ALWAYS use gawt_write_file / gawt_edit_file / gawt_read_file for ALL file changes. "
            "NEVER use the host's Edit/Write tools — they bypass attribution and conflict tracking. "
            "Always pass agent_id to every gawt call. "
            "Set start_intent before your first edit. "
            "Check inbox after each significant edit."
        )

    def tools(self, spec: SubagentSpec) -> list[Callable]:
        from agents_janus import gawt_client

        @tool
        def gawt_register_agent(role: str) -> str:
            """Register an agent with the gawt session. Returns agent_id. Call this first."""
            result = gawt_client.register_agent(role)
            return str(result)

        @tool
        def gawt_unregister_agent(agent_id: str) -> str:
            """Mark an agent as ended. Call when done."""
            result = gawt_client.unregister_agent(agent_id)
            return str(result)

        @tool
        def gawt_start_intent(agent_id: str, intent: str) -> str:
            """Record the start of a new intent (what you're about to do)."""
            result = gawt_client.start_intent(agent_id, intent)
            return str(result)

        @tool
        def gawt_write_file(agent_id: str, file: str, content: str) -> str:
            """Create or overwrite a file in the worktree. file is relative to repo root."""
            result = gawt_client.write_file(agent_id, file, content)
            return str(result)

        @tool
        def gawt_edit_file(agent_id: str, file: str, old_string: str, new_string: str) -> str:
            """Exact-match string replacement in a file. file is relative to repo root."""
            result = gawt_client.edit_file(agent_id, file, old_string, new_string)
            return str(result)

        @tool
        def gawt_read_file(agent_id: str, file: str) -> str:
            """Read a file from the worktree. file is relative to repo root."""
            result = gawt_client.read_file(agent_id, file)
            return str(result)

        @tool
        def gawt_check_inbox(agent_id: str) -> str:
            """Check for messages from other agents or the orchestrator."""
            result = gawt_client.check_inbox(agent_id)
            return str(result)

        @tool
        def gawt_send_message(from_agent_id: str, to_agent_id: str, message: str) -> str:
            """Send a message to another agent or the orchestrator (__orchestrator__)."""
            result = gawt_client.send_message(from_agent_id, to_agent_id, message)
            return str(result)

        @tool
        def gawt_list_edits(agent_id: str) -> str:
            """List all edits made by this agent."""
            result = gawt_client.list_edits(agent_id=agent_id)
            return str(result)

        return [
            gawt_register_agent,
            gawt_unregister_agent,
            gawt_start_intent,
            gawt_write_file,
            gawt_edit_file,
            gawt_read_file,
            gawt_check_inbox,
            gawt_send_message,
            gawt_list_edits,
        ]
