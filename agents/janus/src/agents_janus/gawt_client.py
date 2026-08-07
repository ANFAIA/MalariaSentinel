"""gawt_client — thin Python wrappers for gawt MCP tool calls.

The gawt MCP server (stdio transport) provides:
  - Session lifecycle: start_session, finalize_session, abort_session, get_session
  - Agent management: register_agent, unregister_agent, list_agents
  - Intent tracking: start_intent, repurpose, get_current_intent
  - File editing: edit_file, write_file, read_file, delete_file
  - Coordination: check_inbox, send_message, list_edits, list_intents

These wrappers are called by the orchestrator and specialists.
They are thin — they just call the MCP tools and return parsed results.

IMPORTANT: In the deepagents runtime, MCP tools are available as
mcp__gitagent__* functions. This module provides a clean Python API
for cases where direct MCP tool access is inconvenient (e.g., spawn_subagent).
"""
from __future__ import annotations

import json
from typing import Any


def _parse(result: Any) -> dict:
    """Parse an MCP tool result (may be JSON string or dict)."""
    if isinstance(result, str):
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return {"raw": result}
    return result if isinstance(result, dict) else {"raw": str(result)}


# ── Session lifecycle ──────────────────────────────────────────────

def start_session(feature: str, target_branch: str = "main", conflict_window_seconds: int = 30) -> dict:
    """Start a new gawt session. Returns {session_id, worktree, base_sha, ...}."""
    # This is called via MCP: mcp__gitagent__start_session(feature=...)
    # The actual MCP call is made by the orchestrator's LLM.
    # This function exists for programmatic use by spawn_subagent.
    raise NotImplementedError("Call mcp__gitagent__start_session directly from the orchestrator")


def finalize_session(message: str, sign: bool = False) -> dict:
    """Finalize the current session — commit worktree state."""
    raise NotImplementedError("Call mcp__gitagent__finalize_session directly from the orchestrator")


def abort_session() -> dict:
    """Abort the current session — discard worktree."""
    raise NotImplementedError("Call mcp__gitagent__abort_session directly from the orchestrator")


def get_session() -> dict | None:
    """Get the current open session, or None."""
    raise NotImplementedError("Call mcp__gitagent__get_session directly from the orchestrator")


# ── Agent management ───────────────────────────────────────────────

def register_agent(role: str) -> dict:
    """Register a new agent. Returns {agent_id}."""
    raise NotImplementedError("Call mcp__gitagent__register_agent directly")


def unregister_agent(agent_id: str) -> dict:
    """Mark an agent as ended."""
    raise NotImplementedError("Call mcp__gitagent__unregister_agent directly")


def list_agents() -> list[dict]:
    """List all agents in the current session."""
    raise NotImplementedError("Call mcp__gitagent__list_agents directly")


# ── Intent tracking ────────────────────────────────────────────────

def start_intent(agent_id: str, intent: str) -> dict:
    """Record the start of a new intent."""
    raise NotImplementedError("Call mcp__gitagent__start_intent directly")


def repurpose(agent_id: str, intent: str) -> dict:
    """Record an intent shift."""
    raise NotImplementedError("Call mcp__gitagent__repurpose directly")


def get_current_intent(agent_id: str) -> dict:
    """Get the active intent for an agent."""
    raise NotImplementedError("Call mcp__gitagent__get_current_intent directly")


# ── File editing ───────────────────────────────────────────────────

def edit_file(agent_id: str, file: str, old_string: str, new_string: str, replace_all: bool = False) -> dict:
    """Exact-match string replacement with atomic write."""
    raise NotImplementedError("Call mcp__gitagent__edit_file directly")


def write_file(agent_id: str, file: str, content: str) -> dict:
    """Create or overwrite a file with atomic write."""
    raise NotImplementedError("Call mcp__gitagent__write_file directly")


def read_file(agent_id: str, file: str) -> dict:
    """Read a file. Returns content + sha256."""
    raise NotImplementedError("Call mcp__gitagent__read_file directly")


def delete_file(agent_id: str, file: str) -> dict:
    """Remove a file."""
    raise NotImplementedError("Call mcp__gitagent__delete_file directly")


# ── Coordination ───────────────────────────────────────────────────

def check_inbox(agent_id: str) -> list[dict]:
    """Return unread inbox items for the agent."""
    raise NotImplementedError("Call mcp__gitagent__check_inbox directly")


def send_message(from_agent_id: str, to_agent_id: str, message: str) -> dict:
    """Send a message between agents."""
    raise NotImplementedError("Call mcp__gitagent__send_message directly")


def list_edits(agent_id: str | None = None, file: str | None = None, since_ts: str | None = None) -> list[dict]:
    """List edits with optional filters."""
    raise NotImplementedError("Call mcp__gitagent__list_edits directly")


def list_intents(agent_id: str | None = None) -> list[dict]:
    """List intents."""
    raise NotImplementedError("Call mcp__gitagent__list_intents directly")
