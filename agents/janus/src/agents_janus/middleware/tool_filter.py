"""Tool exclusion middleware — filters tools out of a subagent's model request.

The `execute` tool (bash) is exposed to every agent that uses a sandbox
backend, because the backend is shared across the graph. This middleware lets
us strip `execute` from subagents that must NOT run bash (only the orchestrator
and the `abm` specialist get shell access).
"""
from __future__ import annotations

from typing import Any

from langchain.agents.middleware.types import AgentMiddleware


def _tool_name(tool: Any) -> str | None:
    if isinstance(tool, dict):
        name = tool.get("name")
        return name if isinstance(name, str) else None
    return getattr(tool, "name", None)


class ToolFilterMiddleware(AgentMiddleware[Any, Any, Any]):
    """Filter a set of tool names out of the model request.

    Place it late in the middleware stack (after all tool-injecting
    middleware) so it strips middleware-injected tools like `execute`.
    """

    def __init__(self, *, excluded: frozenset[str]) -> None:
        super().__init__()
        self._excluded = excluded

    def wrap_model_call(self, request, handler):
        if self._excluded:
            filtered = [t for t in request.tools if _tool_name(t) not in self._excluded]
            request = request.override(tools=filtered)
        return handler(request)

    async def awrap_model_call(self, request, handler):
        if self._excluded:
            filtered = [t for t in request.tools if _tool_name(t) not in self._excluded]
            request = request.override(tools=filtered)
        return await handler(request)


__all__ = ["ToolFilterMiddleware"]
