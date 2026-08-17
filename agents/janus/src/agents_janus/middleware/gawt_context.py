"""Small runtime adapter that carries GAWT identity through MCP calls."""
from __future__ import annotations

import ast
import contextvars
import json
import logging
from typing import Any

from langchain.agents.middleware.types import AgentMiddleware, AgentState


_log = logging.getLogger(__name__)


class GawtContextState(AgentState, total=False):
    """Persistent GAWT identity carried through LangGraph node boundaries."""

    gawt_agent_id: str


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

    state_schema = GawtContextState

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
        self._agent_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
            f"gawt_agent_id_{id(self)}", default=None
        )
        self._agent_token: contextvars.ContextVar[contextvars.Token[str | None] | None] = contextvars.ContextVar(
            f"gawt_agent_token_{id(self)}", default=None
        )

    def _ensure_registered(self, state: Any = None) -> str:
        state_id = state.get("gawt_agent_id") if isinstance(state, dict) else None
        if state_id:
            agent_id = str(state_id)
            self._agent_id.set(agent_id)
            return agent_id
        current_id = self._agent_id.get()
        if current_id is not None:
            return str(current_id)
        result = _parse_result(self.register_tool.invoke({"role": self.role}))
        if not isinstance(result, dict) or not result.get("agent_id"):
            raise RuntimeError(f"GAWT register_agent failed for role {self.role}: {result}")
        agent_id = str(result["agent_id"])
        self._agent_token.set(self._agent_id.set(agent_id))
        _log.info("GAWT registered role=%s agent_id=%s", self.role, agent_id)
        return agent_id

    def before_agent(self, state: Any, runtime: Any) -> dict[str, str]:
        return {"gawt_agent_id": self._ensure_registered(state)}

    def before_model(self, state: Any, runtime: Any) -> dict[str, str]:
        return {"gawt_agent_id": self._ensure_registered(state)}

    def after_agent(self, state: Any, runtime: Any) -> None:
        agent_id = (
            state.get("gawt_agent_id") if isinstance(state, dict) else None
        ) or self._agent_id.get()
        if agent_id is not None and self.unregister_tool is not None:
            self.unregister_tool.invoke({"agent_id": agent_id})
        token = self._agent_token.get()
        if token is not None:
            self._agent_id.reset(token)
            self._agent_token.set(None)

    def wrap_tool_call(self, request: Any, handler: Any) -> Any:
        name = _tool_name(request)
        state = getattr(request, "state", None)
        agent_id = (
            state.get("gawt_agent_id") if isinstance(state, dict) else None
        ) or self._agent_id.get()
        if agent_id and name.startswith("mcp__gitagent__"):
            call = dict(request.tool_call)
            args = dict(call.get("args") or {})
            if name.endswith(self._AGENT_TOOLS) or "agent_id" in args:
                args["agent_id"] = agent_id
            if name.endswith("send_message"):
                args["from_agent_id"] = agent_id
            call["args"] = args
            request = request.override(tool_call=call)
        return handler(request)

    async def awrap_tool_call(self, request: Any, handler: Any) -> Any:
        name = _tool_name(request)
        state = getattr(request, "state", None)
        agent_id = (
            state.get("gawt_agent_id") if isinstance(state, dict) else None
        ) or self._agent_id.get()
        if agent_id and name.startswith("mcp__gitagent__"):
            call = dict(request.tool_call)
            args = dict(call.get("args") or {})
            if name.endswith(self._AGENT_TOOLS) or "agent_id" in args:
                args["agent_id"] = agent_id
            if name.endswith("send_message"):
                args["from_agent_id"] = agent_id
            call["args"] = args
            request = request.override(tool_call=call)
        return await handler(request)
