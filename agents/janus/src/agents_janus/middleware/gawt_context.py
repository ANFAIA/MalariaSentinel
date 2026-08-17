"""Small runtime adapter that carries GAWT identity through MCP calls."""
from __future__ import annotations

import ast
import json
from typing import Any

from langchain.agents.middleware.types import AgentMiddleware


def _parse_result(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        try:
            return ast.literal_eval(value)
        except (ValueError, SyntaxError):
            return value


def _tool_name(request: Any) -> str:
    call = getattr(request, "tool_call", None)
    if isinstance(call, dict):
        return str(call.get("name", ""))
    return str(getattr(call, "name", ""))


class GawtContextMiddleware(AgentMiddleware):
    """Register one GAWT agent and inject its id into mutating MCP calls."""

    _AGENT_TOOLS = (
        "read_file",
        "edit_file",
        "write_file",
        "delete_file",
        "check_inbox",
        "start_intent",
        "repurpose",
        "get_current_intent",
        "list_edits",
    )

    def __init__(self, *, role: str, register_tool: Any, unregister_tool: Any | None = None) -> None:
        super().__init__()
        self.role = role
        self.register_tool = register_tool
        self.unregister_tool = unregister_tool
        self.agent_id: str | None = None

    def before_agent(self, state: Any, runtime: Any) -> None:
        if self.agent_id is not None:
            return
        result = _parse_result(self.register_tool.invoke({"role": self.role}))
        if not isinstance(result, dict) or not result.get("agent_id"):
            raise RuntimeError(f"GAWT register_agent failed for role {self.role}: {result}")
        self.agent_id = str(result["agent_id"])

    def after_agent(self, state: Any, runtime: Any) -> None:
        if self.agent_id is not None and self.unregister_tool is not None:
            self.unregister_tool.invoke({"agent_id": self.agent_id})
        self.agent_id = None

    def wrap_tool_call(self, request: Any, handler: Any) -> Any:
        name = _tool_name(request)
        if self.agent_id and name.startswith("mcp__gitagent__"):
            call = dict(request.tool_call)
            args = dict(call.get("args") or {})
            if name.endswith(self._AGENT_TOOLS) or "agent_id" in args:
                args["agent_id"] = args.get("agent_id") or self.agent_id
            if name.endswith("send_message"):
                args["from_agent_id"] = args.get("from_agent_id") or self.agent_id
            call["args"] = args
            request = request.override(tool_call=call)
        return handler(request)

    async def awrap_tool_call(self, request: Any, handler: Any) -> Any:
        name = _tool_name(request)
        if self.agent_id and name.startswith("mcp__gitagent__"):
            call = dict(request.tool_call)
            args = dict(call.get("args") or {})
            if name.endswith(self._AGENT_TOOLS) or "agent_id" in args:
                args["agent_id"] = args.get("agent_id") or self.agent_id
            if name.endswith("send_message"):
                args["from_agent_id"] = args.get("from_agent_id") or self.agent_id
            call["args"] = args
            request = request.override(tool_call=call)
        return await handler(request)
