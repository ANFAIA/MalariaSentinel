"""Policies applied before Janus dispatches a child task."""
from __future__ import annotations

import re
from typing import Any

from langchain.agents.middleware.types import AgentMiddleware


# GAWT paths are relative to its one shared worktree. Keep punctuation outside
# the token so prompts such as ``/test/file.txt`` and ``/test/file.txt,`` work.
_ABSOLUTE_PATH = re.compile(r"(?P<prefix>(?<![\w.-]))/(?P<path>[A-Za-z0-9_./-]+)")


def normalize_gawt_paths(text: str) -> str:
    """Convert absolute-looking dispatch paths to GAWT-relative paths."""
    if not isinstance(text, str):
        return text

    def replace(match: re.Match[str]) -> str:
        path = match.group("path")
        if not path or path.startswith(("/", ".//")):
            return match.group(0)
        return f"{match.group('prefix')}{path}"

    return _ABSOLUTE_PATH.sub(replace, text)


def _tool_name(request: Any) -> str:
    call = getattr(request, "tool_call", None)
    if isinstance(call, dict):
        return str(call.get("name", ""))
    return str(getattr(call, "name", ""))


class DispatchPathMiddleware(AgentMiddleware):
    """Normalize paths in child-task descriptions before model dispatch."""

    @staticmethod
    def _rewrite(request: Any) -> Any:
        if _tool_name(request) != "task":
            return request
        call = dict(request.tool_call)
        args = dict(call.get("args") or {})
        if "description" in args:
            args["description"] = normalize_gawt_paths(args["description"])
        call["args"] = args
        return request.override(tool_call=call)

    def wrap_tool_call(self, request: Any, handler: Any) -> Any:
        return handler(self._rewrite(request))

    async def awrap_tool_call(self, request: Any, handler: Any) -> Any:
        return await handler(self._rewrite(request))
