"""gawt_client — Python wrappers for gawt MCP tool calls.

These wrappers call gawt functions directly via Python imports.
No MCP protocol needed — bypasses the stdio transport layer.

The gawt package provides:
  - Session lifecycle: start_session, finalize_session, abort_session, get_session
  - Agent management: register_agent, unregister_agent, list_agents
  - Intent tracking: start_intent, repurpose, get_current_intent
  - File editing: edit, write, read, delete_file, list_edits
  - Coordination: check_inbox, send_message, list_intents

These are called by janus subagents via EditPlugin tools.
"""
from __future__ import annotations

import json
import logging
from typing import Any

_log = logging.getLogger("agents_janus.gawt_client")


def _parse(result: Any) -> dict:
    """Parse a gawt result (may be JSON string or dict)."""
    if isinstance(result, str):
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return {"raw": result}
    return result if isinstance(result, dict) else {"raw": str(result)}


def _safe_call(fn, *args, **kwargs) -> dict:
    """Call a gawt function, parse result, log errors."""
    try:
        result = fn(*args, **kwargs)
        return _parse(result)
    except Exception as e:
        _log.error("gawt call failed: %s(%s) -> %s", fn.__name__, args, e)
        return {"error": str(e), "error_type": type(e).__name__}


# ── Session lifecycle ──────────────────────────────────────────────

def start_session(feature: str, target_branch: str = "main", conflict_window_seconds: int = 30) -> dict:
    """Start a new gawt session. Returns {session_id, worktree, base_sha, ...}."""
    from gitagent.session import start_session as _start
    return _safe_call(_start, feature, target_branch=target_branch)


def finalize_session(message: str, sign: bool = False) -> dict:
    """Finalize the current session — commit worktree state."""
    from gitagent.session import finalize_session as _finalize
    return _safe_call(_finalize, message, sign=sign)


def abort_session() -> dict:
    """Abort the current session — discard worktree."""
    from gitagent.session import abort_session as _abort
    return _safe_call(_abort)


def get_session() -> dict | None:
    """Get the current open session, or None."""
    from gitagent.session import get_session as _get
    return _safe_call(_get)


# ── Agent management ───────────────────────────────────────────────

def register_agent(role: str) -> dict:
    """Register a new agent. Returns {agent_id}."""
    from gitagent.agents import register_agent as _register
    return _safe_call(_register, role)


def unregister_agent(agent_id: str) -> dict:
    """Mark an agent as ended."""
    from gitagent.agents import unregister_agent as _unregister
    return _safe_call(_unregister, agent_id)


def list_agents() -> list[dict]:
    """List all agents in the current session."""
    from gitagent.agents import list_agents as _list
    result = _safe_call(_list)
    return result if isinstance(result, list) else result.get("raw", [])


# ── Intent tracking ────────────────────────────────────────────────

def start_intent(agent_id: str, intent: str) -> dict:
    """Record the start of a new intent."""
    from gitagent.intents import start_intent as _start
    return _safe_call(_start, agent_id, intent)


def repurpose(agent_id: str, intent: str) -> dict:
    """Record an intent shift."""
    from gitagent.intents import repurpose as _repurpose
    return _safe_call(_repurpose, agent_id, intent)


def get_current_intent(agent_id: str) -> dict:
    """Get the active intent for an agent."""
    from gitagent.intents import get_current_intent as _get
    return _safe_call(_get, agent_id)


# ── File editing ───────────────────────────────────────────────────

def edit_file(agent_id: str, file: str, old_string: str, new_string: str, replace_all: bool = False) -> dict:
    """Exact-match string replacement with atomic write."""
    from gitagent.edits import edit as _edit
    return _safe_call(_edit, agent_id, file, old_string, new_string, replace_all=replace_all)


def write_file(agent_id: str, file: str, content: str) -> dict:
    """Create or overwrite a file with atomic write."""
    from gitagent.edits import write as _write
    return _safe_call(_write, agent_id, file, content)


def read_file(agent_id: str, file: str) -> dict:
    """Read a file. Returns content + sha256."""
    from gitagent.edits import read as _read
    return _safe_call(_read, agent_id, file)


def delete_file(agent_id: str, file: str) -> dict:
    """Remove a file."""
    from gitagent.edits import delete_file as _delete
    return _safe_call(_delete, agent_id, file)


def list_edits(agent_id: str | None = None, file: str | None = None, since_ts: str | None = None) -> list[dict]:
    """List edits with optional filters."""
    from gitagent.edits import list_edits as _list
    result = _safe_call(_list, agent_id=agent_id, file=file, since_ts=since_ts)
    return result if isinstance(result, list) else result.get("raw", [])


# ── Coordination ───────────────────────────────────────────────────

def check_inbox(agent_id: str) -> list[dict]:
    """Return unread inbox items for the agent."""
    from gitagent.inbox import check_inbox as _check
    result = _safe_call(_check, agent_id)
    return result if isinstance(result, list) else result.get("raw", [])


def send_message(from_agent_id: str, to_agent_id: str, message: str) -> dict:
    """Send a message between agents."""
    from gitagent.inbox import send_message as _send
    return _safe_call(_send, from_agent_id, to_agent_id, message)
