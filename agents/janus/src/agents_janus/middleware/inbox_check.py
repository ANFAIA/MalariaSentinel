"""InboxCheckMiddleware — auto-checks gawt inbox after every tool call.

Subagents currently must explicitly call check_inbox(agent_id) after each
edit. If they forget, they miss conflict messages. This middleware wraps
every tool call and automatically checks the inbox, injecting pending
messages into the tool result.

If a conflict is detected (gawt kind="conflict" message from a peer), the middleware
appends a loud conflict marker so the LLM knows to call resolve_conflict
immediately.

Architecture:
- Deepagents middleware wraps tool calls via wrap_tool_call()
- After handler(request) returns, we call check_inbox(agent_id)
- If messages exist, append them to the tool result as a warning block
- If a conflict is detected, mark it loudly so the LLM takes action

State:
- agent_id: extracted from register_agent() tool call arguments
"""
from __future__ import annotations

import json
import logging
from typing import Any

from langchain.agents.middleware.types import AgentMiddleware

_log = logging.getLogger("agents_janus.middleware.inbox_check")

# gawt tools that perform file mutations (where conflicts matter most)
_EDIT_TOOLS = frozenset({
    "mcp__gitagent__edit_file",
    "mcp__gitagent__write_file",
    "mcp__gitagent__delete_file",
})


def _extract_agent_id(tool_args: Any) -> str | None:
    """Extract agent_id from a gawt tool call's arguments."""
    if tool_args is None:
        return None
    for attr in ("agent_id",):
        if isinstance(tool_args, dict):
            if attr in tool_args:
                return tool_args[attr]
        else:
            val = getattr(tool_args, attr, None)
            if val is not None:
                return str(val)
    return None


def _check_inbox_via_mcp(agent_id: str) -> list[dict]:
    """Call gawt check_inbox via a temporary MCP session.

    Returns a list of message dicts, or empty list on failure.
    """
    import asyncio
    from pathlib import Path
    import os

    try:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
    except ImportError:
        return []

    repo_root = Path(__file__).resolve().parent.parent.parent.parent.parent
    env = os.environ.copy()
    env["PWD"] = str(repo_root)
    env["MCP_LOG_LEVEL"] = "ERROR"

    server_params = StdioServerParameters(
        command="uv",
        args=["run", "gitagent-mcp"],
        cwd=str(repo_root),
        env=env,
    )

    async def _call():
        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.call_tool("check_inbox", {"agent_id": agent_id})
                if hasattr(result, "content") and result.content:
                    texts = []
                    for block in result.content:
                        if hasattr(block, "text"):
                            texts.append(block.text)
                    raw = "\n".join(texts) if texts else "[]"
                else:
                    raw = "[]"
                # Parse the result — gawt returns Python dict repr
                try:
                    parsed = json.loads(raw)
                except (json.JSONDecodeError, TypeError):
                    import ast
                    try:
                        parsed = ast.literal_eval(raw)
                    except (ValueError, SyntaxError):
                        parsed = []
                if isinstance(parsed, list):
                    return parsed
                return []

    try:
        return asyncio.run(_call())
    except Exception as e:
        _log.debug("check_inbox failed for %s: %s", agent_id, e)
        return []


class InboxCheckMiddleware(AgentMiddleware):
    """Middleware that auto-checks gawt inbox after each tool call.

    After every tool call, if the agent has an agent_id (extracted from
    register_agent calls), poll check_inbox() and inject any pending
    messages into the tool result.

    If a conflict is detected (gawt kind="conflict"), mark it loudly so the LLM
    knows to call resolve_conflict immediately.

    Usage:
        In agent.py, when building worker_defs:
            middleware=[..., InboxCheckMiddleware()]
    """

    def __init__(self):
        super().__init__()
        self._agent_id: str | None = None

    def before_agent(self, state, runtime):
        pass

    def after_agent(self, state, runtime):
        pass

    def before_model(self, state, runtime):
        pass

    def after_model(self, state, runtime):
        pass

    def wrap_model_call(self, request, handler):
        return handler(request)

    def wrap_tool_call(self, request, handler):
        """After every tool call, check inbox and inject messages if any."""
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

        # Track agent_id from register_agent calls
        if tool_name == "mcp__gitagent__register_agent" and tool_args:
            aid = _extract_agent_id(tool_args)
            if aid:
                self._agent_id = aid

        # Execute the tool
        result = handler(request)

        # Check inbox if we have an agent_id
        if not self._agent_id:
            return result

        try:
            messages = _check_inbox_via_mcp(self._agent_id)
        except Exception:
            return result  # MCP unreachable, don't block

        if not messages:
            return result

        # Detect conflicts (gawt sends kind="conflict", payload is a JSON
        # string with {"file": ..., "conflicting_agent" | "other_edit_ts": ...})
        conflict = None
        routine = []
        for msg in messages:
            if msg.get("kind") == "conflict":
                payload = msg.get("payload", {})
                if isinstance(payload, str):
                    try:
                        payload = json.loads(payload)
                    except (json.JSONDecodeError, TypeError):
                        payload = {}
                files = [payload.get("file")] if payload.get("file") else []
                conflict = {
                    "from_agent": msg.get("from_agent", "unknown"),
                    "message": (
                        f"peer {msg.get('from_agent', 'unknown')} edited the same file"
                    ),
                    "files": files,
                }
            else:
                routine.append(msg)

        if conflict:
            return _mark_conflict(result, conflict)

        # Inject routine messages
        return _inject_messages(result, routine)


def _mark_conflict(result: Any, conflict: dict) -> str:
    """Append loud conflict marker to tool result."""
    marker = (
        f"\n\n🛑 CONFLICT DETECTED from {conflict['from_agent']}.\n"
        f"Files: {', '.join(conflict['files'])}\n"
        f"Message: {conflict['message']}\n\n"
        "REQUIRED ACTION: Call the `resolve_conflict` tool IMMEDIATELY.\n"
        "Do NOT make any more edits until the conflict is resolved.\n"
        "Pass the conflict_message and files list to resolve_conflict()."
    )
    if isinstance(result, str):
        return result + marker
    return str(result) + marker


def _inject_messages(result: Any, messages: list[dict]) -> str:
    """Inject routine inbox messages into tool result."""
    if not messages:
        return result if isinstance(result, str) else str(result)

    lines = ["\n\n📬 Inbox messages:"]
    for msg in messages:
        sender = msg.get("from_agent", "?")
        text = msg.get("message", "")
        lines.append(f"  [{sender}]: {text}")

    block = "\n".join(lines)
    if isinstance(result, str):
        return result + block
    return str(result) + block
