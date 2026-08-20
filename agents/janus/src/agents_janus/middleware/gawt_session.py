"""Enforce GAWT session lifecycle before implementation dispatch."""
from __future__ import annotations

import ast
import contextvars
import json
import logging
from typing import Any

from langchain.agents.middleware.types import AgentMiddleware

_log = logging.getLogger(__name__)

_LOCK_TTL_SECONDS = 15


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
        lock_ttl_seconds: int = _LOCK_TTL_SECONDS,
    ) -> None:
        super().__init__()
        self.feature = feature or "janus implementation"
        self.start_tool = start_tool
        self.get_tool = get_tool
        self.abort_tool = abort_tool
        self.context_middlewares = context_middlewares or []
        self.lock_ttl_seconds = lock_ttl_seconds
        self._session_open = contextvars.ContextVar(
            f"gawt_session_open_{id(self)}", default=False
        )
        self._session_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
            f"gawt_session_id_{id(self)}", default=None
        )

    @property
    def session_id(self) -> str | None:
        """The GAWT session_id opened by this middleware, if any."""
        return self._session_id.get()

    def abort(self) -> None:
        """Abort the GAWT session if one is open. No-op if already closed."""
        if not self._session_open.get():
            return
        sid = self._session_id.get()
        if sid and self.abort_tool is not None:
            try:
                self.abort_tool.invoke({"session_id": sid})
                _log.info("GAWT session aborted: session_id=%s", sid)
            except Exception as exc:
                _log.warning("GAWT abort_session failed: %s", exc)
        self._session_open.set(False)
        self._session_id.set(None)

    def _propagate_session_id(self, session_id: str) -> None:
        """Share session_id with all registered GawtContextMiddleware instances."""
        self._session_id.set(session_id)
        for mw in self.context_middlewares:
            if hasattr(mw, "session_id"):
                mw.session_id = session_id
        _log.info("GAWT session opened: session_id=%s", session_id)

    def _ensure_session(self) -> None:
        if self._session_open.get():
            return
        if self.get_tool is not None:
            current = _parse_result(self.get_tool.invoke({}))
            if isinstance(current, dict) and current.get("session_id"):
                self._propagate_session_id(str(current["session_id"]))
                self._session_open.set(True)
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
        session_id = result.get("session_id")
        if session_id:
            self._propagate_session_id(str(session_id))
        self._session_open.set(True)

    def wrap_tool_call(self, request: Any, handler: Any) -> Any:
        if _tool_name(request) == "task":
            self._ensure_session()
        return handler(request)

    async def awrap_tool_call(self, request: Any, handler: Any) -> Any:
        if _tool_name(request) == "task":
            self._ensure_session()
        return await handler(request)
