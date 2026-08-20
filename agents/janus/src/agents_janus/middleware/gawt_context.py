"""Small runtime adapter that carries GAWT identity through MCP calls."""
from __future__ import annotations

import ast
import contextvars
import json
import logging
from typing import Any

from langchain.agents.middleware.types import AgentMiddleware, AgentState

_log = logging.getLogger(__name__)
_CURRENT_SESSION_ID: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "janus_gawt_session_id", default=None
)


def set_current_session_id(session_id: str | None) -> None:
    """Publish session identity to coordinator and compiled child graphs."""
    if session_id:
        _CURRENT_SESSION_ID.set(str(session_id))


def current_session_id() -> str | None:
    """Return session identity propagated through the active execution context."""
    return _CURRENT_SESSION_ID.get()


def clear_current_session_id() -> None:
    """Clear session identity after Janus-owned session cleanup."""
    _CURRENT_SESSION_ID.set(None)


class GawtContextState(AgentState, total=False):
    """Persistent GAWT identity carried through LangGraph node boundaries."""

    gawt_agent_id: str
    gawt_session_id: str


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
    """Register one GAWT agent and inject agent_id/session_id into MCP calls."""

    state_schema = GawtContextState

    # Tools that require agent_id injection.
    _AGENT_TOOLS = (
        "read_file",
        "edit_file",
        "write_file",
        "delete_file",
        "start_intent",
        "repurpose",
        "get_current_intent",
        "list_edits",
    )

    # Tools that require session_id injection (gawt 0.6.0 multi-session).
    _SESSION_TOOLS = (
        "register_agent",
        "snapshot_session",
        "snapshot_status",
        "abort_session",
    )

    def __init__(self, *, role: str, register_tool: Any, unregister_tool: Any | None = None) -> None:
        super().__init__()
        self.role = role
        self.register_tool = register_tool
        self.unregister_tool = unregister_tool
        self._agent_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
            f"gawt_agent_id_{id(self)}", default=None
        )
        self._session_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
            f"gawt_session_id_{id(self)}", default=None
        )
        self._agent_token: contextvars.ContextVar[contextvars.Token[str | None] | None] = contextvars.ContextVar(
            f"gawt_agent_token_{id(self)}", default=None
        )

    @property
    def session_id(self) -> str | None:
        """Current GAWT session_id, if known."""
        return self._session_id.get() or current_session_id()

    @session_id.setter
    def session_id(self, value: str | None) -> None:
        if value:
            self._session_id.set(str(value))
            set_current_session_id(str(value))

    def _ensure_registered(self, state: Any = None) -> str:
        state_id = state.get("gawt_agent_id") if isinstance(state, dict) else None
        if state_id:
            agent_id = str(state_id)
            self._agent_id.set(agent_id)
            session_id = state.get("gawt_session_id") if isinstance(state, dict) else None
            if session_id:
                self._session_id.set(str(session_id))
            return agent_id
        current_id = self._agent_id.get()
        if current_id is not None:
            return str(current_id)
        # Pass session_id if we already have one (multi-session gawt 0.6.0).
        reg_args: dict[str, Any] = {"role": self.role}
        sid = self.session_id
        if sid:
            reg_args["session_id"] = sid
        result = _parse_result(self.register_tool.invoke(reg_args))
        if not isinstance(result, dict) or not result.get("agent_id"):
            raise RuntimeError(f"GAWT register_agent failed for role {self.role}: {result}")
        agent_id = str(result["agent_id"])
        self._agent_token.set(self._agent_id.set(agent_id))
        session_id = result.get("session_id")
        if session_id:
            self._session_id.set(str(session_id))
        _log.info("GAWT registered role=%s agent_id=%s session_id=%s", self.role, agent_id, self._session_id.get())
        return agent_id

    def before_agent(self, state: Any, runtime: Any) -> dict[str, str]:
        out: dict[str, str] = {"gawt_agent_id": self._ensure_registered(state)}
        sid = self._session_id.get()
        if sid:
            out["gawt_session_id"] = sid
        return out

    def before_model(self, state: Any, runtime: Any) -> dict[str, str]:
        out: dict[str, str] = {"gawt_agent_id": self._ensure_registered(state)}
        sid = self._session_id.get()
        if sid:
            out["gawt_session_id"] = sid
        return out

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

    def _inject_identity(self, request: Any) -> Any:
        """Inject agent_id and/or session_id into gawt MCP tool calls."""
        name = _tool_name(request)
        state = getattr(request, "state", None)
        agent_id = (
            state.get("gawt_agent_id") if isinstance(state, dict) else None
        ) or self._agent_id.get()
        session_id = (
            state.get("gawt_session_id") if isinstance(state, dict) else None
        ) or self.session_id

        if not name.startswith("mcp__gitagent__"):
            return request

        call = dict(request.tool_call)
        args = dict(call.get("args") or {})
        changed = False

        # Inject agent_id for agent-scoped tools.
        if agent_id and (name.endswith(self._AGENT_TOOLS) or "agent_id" in args):
            args["agent_id"] = agent_id
            changed = True

        # Inject session_id for session-scoped tools (gawt 0.6.0 multi-session).
        if session_id and name.endswith(self._SESSION_TOOLS):
            args["session_id"] = session_id
            changed = True

        if changed:
            call["args"] = args
            return request.override(tool_call=call)
        return request

    def wrap_tool_call(self, request: Any, handler: Any) -> Any:
        return handler(self._inject_identity(request))

    async def awrap_tool_call(self, request: Any, handler: Any) -> Any:
        return await handler(self._inject_identity(request))
