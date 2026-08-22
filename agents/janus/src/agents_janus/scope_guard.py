"""Scope enforcement for specialist GAWT file operations."""
from __future__ import annotations

import fnmatch
import contextvars
from typing import Any

from langchain.agents.middleware.types import AgentMiddleware
from langchain_core.messages import ToolMessage
from langchain_core.tools import BaseTool, StructuredTool

_WRITE_TOOLS = {"mcp__gitagent__write_file", "mcp__gitagent__edit_file", "mcp__gitagent__delete_file"}


class ScopeViolationMiddleware(AgentMiddleware):
    """Prevent retries after a terminal specialist scope violation."""

    def __init__(self) -> None:
        super().__init__()
        self._blocked = contextvars.ContextVar(f"scope_blocked_{id(self)}", default=False)

    def before_agent(self, state: Any, runtime: Any) -> None:
        self._blocked.set(False)

    @staticmethod
    def _tool_call_id(request: Any) -> str:
        call = getattr(request, "tool_call", {})
        return str(call.get("id", "")) if isinstance(call, dict) else ""

    def wrap_tool_call(self, request: Any, handler: Any) -> Any:
        if self._blocked.get():
            return ToolMessage(
                content=(
                    "Previous write was rejected for scope. No further tools allowed. "
                    "Report scope violation to coordinator."
                ),
                tool_call_id=self._tool_call_id(request),
            )
        result = handler(request)
        if isinstance(result, dict) and result.get("error_type") == "scope_violation":
            self._blocked.set(True)
        return result

    async def awrap_tool_call(self, request: Any, handler: Any) -> Any:
        if self._blocked.get():
            return ToolMessage(
                content=(
                    "Previous write was rejected for scope. No further tools allowed. "
                    "Report scope violation to coordinator."
                ),
                tool_call_id=self._tool_call_id(request),
            )
        result = await handler(request)
        if isinstance(result, dict) and result.get("error_type") == "scope_violation":
            self._blocked.set(True)
        return result


def _path(args: dict[str, Any]) -> str:
    value = str(args.get("file") or args.get("path") or "")
    return value.removeprefix("./")


def _unsafe_path(path: str) -> bool:
    """Reject paths that could escape the shared project worktree."""
    return path.startswith("/") or ".." in path.split("/")


def guard_gawt_tools(
    tools: list[Any],
    edits_allow: tuple[str, ...],
    edits_deny: tuple[str, ...] = (),
) -> list[Any]:
    """Wrap GAWT mutators so scope is checked before MCP invocation."""
    if not edits_allow:
        return tools
    guarded: list[Any] = []
    for tool in tools:
        if not isinstance(tool, BaseTool) or tool.name not in _WRITE_TOOLS:
            guarded.append(tool)
            continue
        guarded_invoke = _make_guarded_invoke(tool, edits_allow, edits_deny)

        guarded.append(
            StructuredTool.from_function(
                func=guarded_invoke,
                name=tool.name,
                description=tool.description,
                args_schema=tool.args_schema,
            )
        )
    return guarded


def _make_guarded_invoke(
    tool: BaseTool,
    patterns: tuple[str, ...],
    denied_patterns: tuple[str, ...] = (),
):
    def invoke(**kwargs: Any) -> Any:
        path = _path(kwargs)
        denied = any(fnmatch.fnmatchcase(path, pattern) for pattern in denied_patterns)
        if (
            not path
            or _unsafe_path(path)
            or denied
            or not any(fnmatch.fnmatchcase(path, pattern) for pattern in patterns)
        ):
            # Return structured tool output so model can correct path and retry.
            # Raising ToolException aborts some LangGraph tool nodes instead.
            return {
                "error": f"GAWT scope violation: path={path!r} is outside allowed paths {list(patterns)!r}",
                "error_type": "scope_violation",
                "recoverable": True,
                "terminal": True,
                "next_action": "Stop write attempt and report scope violation; do not try alternate paths or filesystem tools.",
                "path": path,
                "allowed_paths": list(patterns),
                "denied_paths": list(denied_patterns),
            }
        return tool.invoke(kwargs)

    return invoke
