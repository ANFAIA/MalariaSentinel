"""Enforce GAWT session lifecycle before implementation dispatch."""
from __future__ import annotations

import ast
import contextvars
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


class GawtSessionMiddleware(AgentMiddleware):
    """Open one shared GAWT session before allowing a child task to run."""

    def __init__(self, *, feature: str, start_tool: Any, get_tool: Any | None = None) -> None:
        super().__init__()
        self.feature = feature or "janus implementation"
        self.start_tool = start_tool
        self.get_tool = get_tool
        self._session_open = contextvars.ContextVar(
            f"gawt_session_open_{id(self)}", default=False
        )

    def _ensure_session(self) -> None:
        if self._session_open.get():
            return
        if self.get_tool is not None:
            current = _parse_result(self.get_tool.invoke({}))
            if isinstance(current, dict) and current:
                self._session_open.set(True)
                return

        result = _parse_result(
            self.start_tool.invoke({"feature": self.feature, "target_branch": "main"})
        )
        if not isinstance(result, dict) or result.get("error"):
            raise RuntimeError(f"GAWT start_session failed: {result}")
        self._session_open.set(True)

    def wrap_tool_call(self, request: Any, handler: Any) -> Any:
        if _tool_name(request) == "task":
            self._ensure_session()
        return handler(request)

    async def awrap_tool_call(self, request: Any, handler: Any) -> Any:
        if _tool_name(request) == "task":
            self._ensure_session()
        return await handler(request)
