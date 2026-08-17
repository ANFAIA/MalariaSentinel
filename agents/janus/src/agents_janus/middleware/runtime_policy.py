"""Small runtime guard for backend tools injected by DeepAgents."""
from __future__ import annotations

from typing import Any

from langchain.agents.middleware.types import AgentMiddleware


BACKEND_TOOLS = frozenset({"execute", "ls", "glob", "grep", "read_file", "write_file", "edit_file", "delete_file"})


class ToolExposureMiddleware(AgentMiddleware):
    """Hide backend-injected tools not granted by declarative policy."""

    def __init__(self, *, allowed_backend_tools: frozenset[str]) -> None:
        super().__init__()
        self.allowed_backend_tools = allowed_backend_tools

    def _filter(self, tools: list[Any]) -> list[Any]:
        result = []
        for tool in tools:
            name = tool.get("name") if isinstance(tool, dict) else getattr(tool, "name", "")
            if name in BACKEND_TOOLS and name not in self.allowed_backend_tools:
                continue
            result.append(tool)
        return result

    def wrap_model_call(self, request: Any, handler: Any) -> Any:
        return handler(request.override(tools=self._filter(request.tools)))

    async def awrap_model_call(self, request: Any, handler: Any) -> Any:
        return await handler(request.override(tools=self._filter(request.tools)))
