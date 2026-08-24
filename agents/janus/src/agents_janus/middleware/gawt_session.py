"""Enforce GAWT session lifecycle before implementation dispatch."""
from __future__ import annotations

import ast
import contextvars
import json
import logging
import re
import threading
from typing import Any

from langchain.agents.middleware.types import AgentMiddleware

from agents_janus.middleware.gawt_context import (
    clear_current_session_id,
    set_current_session_id,
)

_log = logging.getLogger(__name__)

_LOCK_TTL_SECONDS = 15
_SESSION_SCOPED_TOOLS = frozenset({
    "get_session", "list_agents", "list_edits", "list_intents",
    "list_snapshots", "snapshot_session", "snapshot_status", "abort_session",
    "register_agent", "unregister_agent", "start_intent", "repurpose",
    "get_current_intent", "read_file", "edit_file", "write_file", "delete_file",
})
_FAKE_TOOL_CALL = re.compile(
    r"<(?:tool_call|tool_name|function(?:_name)?|parameter(?: name)?)\b", re.I
)


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


def _extract_session_id(value: Any) -> str | None:
    """Extract session identity from gawt tool responses and list wrappers."""
    parsed = _parse_result(value)
    if not isinstance(parsed, dict):
        return None
    for key in ("session_id", "id"):
        if parsed.get(key):
            return str(parsed[key])
    sessions = parsed.get("sessions")
    if isinstance(sessions, list) and len(sessions) == 1 and isinstance(sessions[0], dict):
        return _extract_session_id(sessions[0])
    return None


class GawtSessionMiddleware(AgentMiddleware):
    """Open one shared GAWT session before allowing a child task to run.

    Captures the session_id from start_session and propagates it to any
    GawtContextMiddleware instances so register_agent calls succeed in
    multi-session gawt 0.6.0 environments.
    """

    def __init__(
        self,
        *,
        feature: str,
        start_tool: Any,
        get_tool: Any | None = None,
        abort_tool: Any | None = None,
        context_middlewares: list[Any] | None = None,
        on_session_open: Any | None = None,
        lock_ttl_seconds: int = _LOCK_TTL_SECONDS,
    ) -> None:
        super().__init__()
        self.feature = feature or "janus implementation"
        self.start_tool = start_tool
        self.get_tool = get_tool
        self.abort_tool = abort_tool
        self.context_middlewares = context_middlewares or []
        self.on_session_open = on_session_open
        self.lock_ttl_seconds = lock_ttl_seconds
        self._session_open = contextvars.ContextVar(
            f"gawt_session_open_{id(self)}", default=False
        )
        self._session_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
            f"gawt_session_id_{id(self)}", default=None
        )
        # LangGraph may execute hooks in fresh ContextVar contexts. Keep
        # lifecycle identity on middleware object so every tool sees one SID.
        self._active_session_id: str | None = None
        self._session_lock = threading.RLock()

    @property
    def session_id(self) -> str | None:
        """The GAWT session_id opened by this middleware, if any."""
        return self._active_session_id or self._session_id.get()

    def abort(self) -> None:
        """Abort the GAWT session if one is open. No-op if already closed."""
        with self._session_lock:
            sid = self._active_session_id or self._session_id.get()
            open_session = self._session_open.get() or sid is not None
        if not open_session:
            return
        if sid and self.abort_tool is not None:
            try:
                self.abort_tool.invoke({"session_id": sid})
                _log.info("GAWT session aborted: session_id=%s", sid)
            except Exception as exc:
                _log.warning("GAWT abort_session failed: %s", exc)
        self._session_open.set(False)
        self._session_id.set(None)
        self._active_session_id = None
        clear_current_session_id()

    def _propagate_session_id(self, session_id: str) -> None:
        """Share session_id with all registered GawtContextMiddleware instances."""
        self._session_id.set(session_id)
        self._active_session_id = session_id
        set_current_session_id(session_id)
        for mw in self.context_middlewares:
            if hasattr(mw, "session_id"):
                mw.session_id = session_id
        if self.on_session_open is not None:
            self.on_session_open(session_id)
        _log.info("GAWT session opened: session_id=%s", session_id)

    def before_agent(self, state: Any, runtime: Any) -> None:
        """Open implementation session before root observability starts."""
        self._ensure_session()

    def _ensure_session(self) -> None:
        with self._session_lock:
            if self._active_session_id or self._session_open.get():
                if self._active_session_id:
                    set_current_session_id(self._active_session_id)
                return

            result = _parse_result(
                self.start_tool.invoke({
                    "feature": self.feature,
                    "target_branch": "main",
                    "lock_ttl_seconds": self.lock_ttl_seconds,
                })
            )
            if not isinstance(result, dict) or result.get("error"):
                raise RuntimeError(f"GAWT start_session failed: {result}")
            session_id = _extract_session_id(result)
            if session_id:
                self._propagate_session_id(str(session_id))
            self._session_open.set(True)

    @staticmethod
    def _reject_fake_tool_output(result: Any) -> Any:
        if _FAKE_TOOL_CALL.search(str(result)):
            raise RuntimeError(
                "Specialist returned serialized tool-call markup instead of executing a real tool. "
                "Treat result as invalid and retry with an actual tool call."
            )
        return result

    @staticmethod
    def _reject_snapshot_error(name: str, result: Any) -> Any:
        if name.endswith("snapshot_status"):
            parsed = _parse_result(result)
            text = str(parsed)
            if (
                (isinstance(parsed, dict) and parsed.get("error"))
                or "Error executing tool" in text
                or "No such file or directory" in text
            ):
                raise RuntimeError(f"GAWT snapshot_status failed: {text}")
        return result

    def wrap_tool_call(self, request: Any, handler: Any) -> Any:
        name = _tool_name(request)
        raw_name = name.removeprefix("mcp__gitagent__")
        if raw_name in _SESSION_SCOPED_TOOLS:
            self._ensure_session()
            call = dict(request.tool_call)
            args = dict(call.get("args") or {})
            if self.session_id:
                args.setdefault("session_id", self.session_id)
                request = request.override(tool_call={**call, "args": args})
        if name == "mcp__gitagent__start_session":
            call = dict(request.tool_call)
            args = dict(call.get("args") or {})
            args.setdefault("target_branch", "main")
            # Never allow model-provided values above user safety limit.
            args["lock_ttl_seconds"] = min(int(args.get("lock_ttl_seconds") or _LOCK_TTL_SECONDS), _LOCK_TTL_SECONDS)
            request = request.override(tool_call={**call, "args": args})
            result = handler(request)
            session_id = _extract_session_id(result)
            if session_id:
                self._propagate_session_id(session_id)
                self._session_open.set(True)
            return result
        if name == "task":
            self._ensure_session()
            return self._reject_fake_tool_output(handler(request))
        return self._reject_snapshot_error(name, handler(request))

    async def awrap_tool_call(self, request: Any, handler: Any) -> Any:
        name = _tool_name(request)
        raw_name = name.removeprefix("mcp__gitagent__")
        if raw_name in _SESSION_SCOPED_TOOLS:
            self._ensure_session()
            call = dict(request.tool_call)
            args = dict(call.get("args") or {})
            if self.session_id:
                args.setdefault("session_id", self.session_id)
                request = request.override(tool_call={**call, "args": args})
        if name == "mcp__gitagent__start_session":
            call = dict(request.tool_call)
            args = dict(call.get("args") or {})
            args.setdefault("target_branch", "main")
            args["lock_ttl_seconds"] = min(int(args.get("lock_ttl_seconds") or _LOCK_TTL_SECONDS), _LOCK_TTL_SECONDS)
            request = request.override(tool_call={**call, "args": args})
            result = await handler(request)
            session_id = _extract_session_id(result)
            if session_id:
                self._propagate_session_id(session_id)
                self._session_open.set(True)
            return result
        if name == "task":
            self._ensure_session()
            return self._reject_fake_tool_output(await handler(request))
        return self._reject_snapshot_error(name, await handler(request))
