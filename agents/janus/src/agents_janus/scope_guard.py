"""Scope enforcement for specialist GAWT file operations."""
from __future__ import annotations

import fnmatch
from typing import Any

from langchain_core.tools import BaseTool, StructuredTool, ToolException

_WRITE_TOOLS = {"mcp__gitagent__write_file", "mcp__gitagent__edit_file", "mcp__gitagent__delete_file"}


def _path(args: dict[str, Any]) -> str:
    return str(args.get("file") or args.get("path") or "").lstrip("/")


def guard_gawt_tools(tools: list[Any], edits_allow: tuple[str, ...]) -> list[Any]:
    """Wrap GAWT mutators so scope is checked before MCP invocation."""
    if not edits_allow:
        return tools
    guarded: list[Any] = []
    for tool in tools:
        if not isinstance(tool, BaseTool) or tool.name not in _WRITE_TOOLS:
            guarded.append(tool)
            continue
        guarded_invoke = _make_guarded_invoke(tool, edits_allow)

        guarded.append(
            StructuredTool.from_function(
                func=guarded_invoke,
                name=tool.name,
                description=tool.description,
                args_schema=tool.args_schema,
            )
        )
    return guarded


def _make_guarded_invoke(tool: BaseTool, patterns: tuple[str, ...]):
    def invoke(**kwargs: Any) -> Any:
        path = _path(kwargs)
        if not path or not any(fnmatch.fnmatchcase(path, pattern) for pattern in patterns):
            raise ToolException(
                f"GAWT scope violation: path={path!r} is outside allowed paths {list(patterns)!r}"
            )
        return tool.invoke(kwargs)

    return invoke
