"""Small runtime guard for backend tools injected by DeepAgents."""
from __future__ import annotations

from typing import Any

from langchain.agents.middleware.types import AgentMiddleware
from langchain_core.messages import ToolMessage

BACKEND_TOOLS = frozenset({"execute", "ls", "glob", "grep", "read_file", "write_file", "edit_file", "delete_file"})
COORDINATOR_GAWT_WRITE_TOOLS = frozenset({
    "mcp__gitagent__read_file",
    "mcp__gitagent__edit_file",
    "mcp__gitagent__write_file",
    "mcp__gitagent__delete_file",
    "mcp__gitagent__start_intent",
    "mcp__gitagent__repurpose",
    "mcp__gitagent__get_current_intent",
})


class ToolExposureMiddleware(AgentMiddleware):
    """Hide backend-injected tools not granted by declarative policy.

    ``allowed_backend_tools`` controls which of the standard backend tools
    (execute, ls, glob, grep, read_file, write_file, edit_file, delete_file)
    are visible.

    ``excluded_tools`` is an additional set of tool names to hide from the
    model *and* block at call time — useful for removing deepagents built-ins
    like ``write_todos`` from agents that should not plan or edit.
    """

    def __init__(
        self,
        *,
        allowed_backend_tools: frozenset[str],
        excluded_tools: frozenset[str] = frozenset(),
        allowed_tools: frozenset[str] | None = None,
    ) -> None:
        super().__init__()
        self.allowed_backend_tools = allowed_backend_tools
        self.excluded_tools = excluded_tools
        self.allowed_tools = allowed_tools

    def _is_blocked(self, name: str) -> bool:
        if self.allowed_tools is not None and name not in self.allowed_tools:
            return True
        if name in self.excluded_tools:
            return True
        return name in BACKEND_TOOLS and name not in self.allowed_backend_tools

    def _filter(self, tools: list[Any]) -> list[Any]:
        result = []
        for tool in tools:
            name = str(tool.get("name") if isinstance(tool, dict) else getattr(tool, "name", "") or "")
            if self._is_blocked(name):
                continue
            result.append(tool)
        return result

    def wrap_model_call(self, request: Any, handler: Any) -> Any:
        filtered = self._filter(request.tools)
        system_message = getattr(request, "system_message", None)
        if isinstance(system_message, str):
            if self.allowed_tools is not None:
                policy = "Tool policy: only tools in current tool list are available. Do not call filesystem, shell, or planning tools not listed."
            else:
                policy = "Tool policy: backend tools not granted by Janus are unavailable. Delegate repository edits through task and GAWT."
            system_message = f"{system_message}\n\n{policy}"
            return handler(request.override(tools=filtered, system_message=system_message))
        return handler(request.override(tools=filtered))

    async def awrap_model_call(self, request: Any, handler: Any) -> Any:
        filtered = self._filter(request.tools)
        system_message = getattr(request, "system_message", None)
        if isinstance(system_message, str):
            policy = (
                "Tool policy: only tools in current tool list are available. Do not call filesystem, shell, or planning tools not listed."
                if self.allowed_tools is not None
                else "Tool policy: backend tools not granted by Janus are unavailable. Delegate repository edits through task and GAWT."
            )
            return await handler(request.override(tools=filtered, system_message=f"{system_message}\n\n{policy}"))
        return await handler(request.override(tools=filtered))

    def wrap_tool_call(self, request: Any, handler: Any) -> Any:
        name = request.tool_call.get("name", "")
        if self._is_blocked(name):
            return ToolMessage(
                content=(
                    f"Backend tool '{name}' blocked by runtime policy; "
                    "delegate through task() to an authorized specialist."
                ),
                tool_call_id=request.tool_call.get("id", ""),
            )
        return handler(request)

    async def awrap_tool_call(self, request: Any, handler: Any) -> Any:
        name = request.tool_call.get("name", "")
        if self._is_blocked(name):
            return ToolMessage(
                content=(
                    f"Backend tool '{name}' blocked by runtime policy; "
                    "delegate through task() to an authorized specialist."
                ),
                tool_call_id=request.tool_call.get("id", ""),
            )
        return await handler(request)
