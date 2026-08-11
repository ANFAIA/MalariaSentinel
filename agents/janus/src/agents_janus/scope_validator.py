"""Scope validator — validates agent edits against subagent edit scopes.

gawt does NOT enforce per-agent edit scopes. Any agent can edit any file
in the shared worktree. This module provides advisory validation:
- After an agent makes edits, check if files are in its scope
- Cross-scope edits trigger a warning (not a block)
- Unowned edits trigger ask_user

The validation runs automatically via ScopeValidationMiddleware, which
intercepts gawt edit/write/delete tool calls on every subagent and
validates the file path against the agent's edits_allow patterns.

For post-hoc batch validation, use validate_agent_edits() which can
source edits from gawt's SQLite state database.
"""
from __future__ import annotations

import fnmatch
import json
import logging
import sqlite3
import threading
from pathlib import Path
from typing import Any

from langchain.agents.middleware.types import AgentMiddleware
from agents_janus.subagents.registry import Registry

_log = logging.getLogger("agents_janus.scope_validator")

# gawt tools that perform file mutations (scope-relevant)
_EDIT_TOOLS = frozenset({
    "mcp__gitagent__edit_file",
    "mcp__gitagent__write_file",
    "mcp__gitagent__delete_file",
})


def validate_edit_scope(
    edited_files: list[str],
    agent_role: str,
    registry: Registry,
) -> dict:
    """Validate that an agent's edits are within its declared scope.

    Args:
        edited_files: List of file paths that were edited.
        agent_role: The agent's role (e.g., "abm", "scoring").
        registry: The subagent registry.

    Returns:
        {
            "ok": bool — True if all edits are in scope,
            "in_scope": [paths in agent's edits_allow],
            "cross_scope": [{"path": str, "owner": str}] — owned by another agent,
            "unowned": [paths not in any agent's scope],
        }
    """
    try:
        spec = registry.get(agent_role)
    except KeyError:
        return {
            "ok": False,
            "error": f"Unknown agent role: {agent_role}",
            "in_scope": [],
            "cross_scope": [],
            "unowned": edited_files,
        }

    in_scope = []
    cross_scope = []
    unowned = []

    for path in edited_files:
        own_match = any(fnmatch.fnmatch(path, p) for p in spec.edits_allow)
        if own_match:
            in_scope.append(path)
            continue

        owner = registry.find_owner(path)
        if owner and owner != agent_role:
            cross_scope.append({"path": path, "owner": owner})
        else:
            unowned.append(path)

    return {
        "ok": len(cross_scope) == 0 and len(unowned) == 0,
        "in_scope": in_scope,
        "cross_scope": cross_scope,
        "unowned": unowned,
    }


def validate_single_file(file_path: str, agent_role: str, registry: Registry) -> dict:
    """Validate a single file path against an agent's scope.

    Lightweight check for use in middleware (one file at a time).
    Returns the same schema as validate_edit_scope, but for a single file.
    """
    return validate_edit_scope([file_path], agent_role, registry)


def query_gawt_edits(
    agent_id: str,
    worktree_root: Path | str | None = None,
    since_ts: str | None = None,
) -> list[str]:
    """Query gawt's SQLite state database for an agent's recent edits.

    Reads .gitagent/state.db directly (gawt MCP is not importable from Python).
    Returns a list of file paths the agent edited.

    Args:
        agent_id: The gawt agent ID (e.g., "a_abm").
        worktree_root: Path to the worktree root containing .gitagent/.
            Defaults to REPO_ROOT.
        since_ts: ISO timestamp — only return edits after this time.
            None means all edits for this agent.

    Returns:
        List of file paths (may be empty if no edits found or db missing).
    """
    REPO = Path(__file__).resolve().parent.parent.parent.parent.parent
    root = Path(worktree_root) if worktree_root else REPO
    db_path = root / ".gitagent" / "state.db"

    if not db_path.exists():
        return []

    try:
        conn = sqlite3.connect(str(db_path), timeout=5)
        try:
            # gawt stores edits in an 'edits' table with columns:
            # agent_id, file, action, timestamp, content (schema from gawt 0.5.x)
            query = "SELECT file FROM edits WHERE agent_id = ?"
            params: list[Any] = [agent_id]
            if since_ts:
                query += " AND timestamp > ?"
                params.append(since_ts)
            query += " ORDER BY timestamp ASC"

            cursor = conn.execute(query, params)
            return [row[0] for row in cursor.fetchall()]
        finally:
            conn.close()
    except Exception as e:
        _log.warning("Could not query gawt edits from %s: %s", db_path, e)
        return []


def validate_agent_edits(
    agent_id: str,
    registry: Registry,
    edited_files: list[str] | None = None,
    since_ts: str | None = None,
    worktree_root: Path | str | None = None,
) -> dict:
    """Validate an agent's edits against its declared scope.

    Post-hoc batch validation — useful for session-end audit or conflict
    investigation. Complements the real-time per-call validation done by
    ScopeValidationMiddleware.

    If edited_files is provided, validates those directly (no gawt query).
    If edited_files is None, queries gawt's state.db via query_gawt_edits().

    Args:
        agent_id: The gawt agent ID (used for gawt query and scope lookup).
        registry: The subagent registry.
        edited_files: Explicit list of file paths. If None, queries gawt.
        since_ts: ISO timestamp — only validate edits after this time.
            Only used when edited_files is None (gawt query mode).
        worktree_root: Path to worktree root containing .gitagent/.

    Returns:
        Same schema as validate_edit_scope:
        {
            "ok": bool,
            "in_scope": [paths in agent's edits_allow],
            "cross_scope": [{"path": str, "owner": str}],
            "unowned": [paths not in any agent's scope],
        }
    """
    # Determine the agent's role from the agent_id (strip leading "a_" prefix)
    role = agent_id.removeprefix("a_") if agent_id.startswith("a_") else agent_id

    # Resolve edited_files
    if edited_files is None:
        edited_files = query_gawt_edits(agent_id, worktree_root, since_ts)

    if not edited_files:
        return {"ok": True, "in_scope": [], "cross_scope": [], "unowned": []}

    return validate_edit_scope(edited_files, role, registry)


def _extract_file_path(tool_args: Any) -> str | None:
    """Extract the file path from a gawt edit tool's arguments.

    Handles both dict-like args and Pydantic model args.
    """
    if tool_args is None:
        return None

    # Try common parameter names used by gawt MCP tools
    for attr in ("file", "file_path", "path"):
        if isinstance(tool_args, dict):
            if attr in tool_args:
                return tool_args[attr]
        else:
            val = getattr(tool_args, attr, None)
            if val is not None:
                return str(val)

    return None


def _build_scope_warning(
    file_path: str,
    agent_role: str,
    validation_result: dict,
    registry: Registry,
) -> str:
    """Build a human-readable scope warning for injection into tool results.

    The warning is addressed to the LLM agent so it can adjust behavior.
    """
    try:
        spec = registry.get(agent_role)
        allowed = ", ".join(spec.edits_allow) if spec.edits_allow else "(none)"
    except KeyError:
        allowed = "(unknown role)"

    lines = [
        f"⚠️ SCOPE WARNING: file `{file_path}` is outside your declared scope.",
        f"  Your scope: {allowed}",
    ]

    for v in validation_result.get("cross_scope", []):
        lines.append(f"  Owned by: {v['owner']} specialist")

    for p in validation_result.get("unowned", []):
        lines.append(f"  No specialist owns this file")

    lines.append(
        "  Action: call the owning specialist via task() for this file, "
        "or ask the orchestrator for guidance."
    )

    return "\n".join(lines)


def _append_warning(tool_result: Any, warning: str) -> str:
    """Append a scope warning to a tool result.

    Handles str, dict, and other types by converting to string.
    """
    if isinstance(tool_result, str):
        return f"{tool_result}\n\n{warning}"

    if isinstance(tool_result, dict):
        tool_result["scope_warning"] = warning
        return json.dumps(tool_result, default=str)

    return f"{tool_result}\n\n{warning}"


class ScopeValidationMiddleware(AgentMiddleware):
    """Middleware that validates subagent file edits against declared scopes.

    Intercepts gawt edit/write/delete tool calls and checks the file path
    against the agent's edits_allow patterns. Cross-scope edits are logged
    as warnings (advisory — never blocks the tool call).

    Usage:
        In agent.py, when building worker_defs:
            middleware=[SubAgentObservabilityMiddleware(obs, name),
                       ScopeValidationMiddleware(registry, name)]
    """

    def __init__(self, registry: Registry, agent_role: str):
        super().__init__()
        self._registry = registry
        self._agent_role = agent_role

    def before_agent(self, state, runtime):
        pass  # no-op — we only care about tool calls

    def after_agent(self, state, runtime):
        pass  # no-op

    def before_model(self, state, runtime):
        pass

    def after_model(self, state, runtime):
        pass

    def wrap_model_call(self, request, handler):
        return handler(request)

    def wrap_tool_call(self, request, handler):
        """Intercept tool calls and validate scope for gawt edit operations.

        If a scope violation is detected, the warning is appended to the
        tool result so the LLM sees it and can adjust its behavior.
        """
        tool_name = "unknown"
        tool_args: Any = None

        try:
            tc = getattr(request, "tool_call", None)
            if tc is None and isinstance(request, dict):
                tc = request.get("tool_call")
            if isinstance(tc, dict):
                tool_name = tc.get("name", "unknown")
                tool_args = tc.get("args", {})
            elif tc is not None:
                tool_name = getattr(tc, "name", "unknown")
                tool_args = getattr(tc, "args", {})
        except Exception:
            pass

        # Validate scope for edit tools
        warning_text = None
        if tool_name in _EDIT_TOOLS:
            file_path = _extract_file_path(tool_args)
            if file_path:
                result = validate_single_file(file_path, self._agent_role, self._registry)

                if not result["ok"]:
                    warning_text = _build_scope_warning(
                        file_path, self._agent_role, result, self._registry
                    )
                    _log.warning(
                        "SCOPE %s: agent=%s file=%s",
                        "VIOLATION" if result.get("cross_scope") else "WARNING",
                        self._agent_role,
                        file_path,
                    )

        # Execute the tool
        tool_result = handler(request)

        # Inject scope warning into the tool result
        if warning_text:
            tool_result = _append_warning(tool_result, warning_text)

        return tool_result
