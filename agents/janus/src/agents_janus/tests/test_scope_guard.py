"""Tests for specialist path scope enforcement."""
from __future__ import annotations

import asyncio
from types import SimpleNamespace
from langchain_core.tools import StructuredTool

from agents_janus.scope_guard import ScopeViolationMiddleware, guard_gawt_tools


def _tool():
    return StructuredTool.from_function(
        lambda file, content: {"file": file, "content": content},
        name="mcp__gitagent__write_file",
        description="write",
    )


def test_write_inside_scope_allowed():
    guarded = guard_gawt_tools([_tool()], ("mal-commonlib/**",))
    assert guarded[0].invoke({"file": "mal-commonlib/tmp.txt", "content": "x"})["file"] == "mal-commonlib/tmp.txt"


def test_write_outside_scope_returns_model_visible_error_before_mcp():
    guarded = guard_gawt_tools([_tool()], ("mal-commonlib/**",))
    result = guarded[0].invoke({"file": "tmp.txt", "content": "x"})
    assert result["error"] == "GAWT scope violation: path='tmp.txt' is outside allowed paths ['mal-commonlib/**']"
    assert result["error_type"] == "scope_violation"
    assert result["recoverable"] is True
    assert result["terminal"] is True
    assert result["path"] == "tmp.txt"
    assert result["allowed_paths"] == ["mal-commonlib/**"]


def test_absolute_path_is_rejected_before_mcp():
    guarded = guard_gawt_tools([_tool()], ("mal-commonlib/**",))
    result = guarded[0].invoke({"file": "/mal-commonlib/tmp.txt", "content": "x"})
    assert result["error_type"] == "scope_violation"
    assert result["terminal"] is True
    assert "do not try alternate paths" in result["next_action"]
    assert result["path"] == "/mal-commonlib/tmp.txt"


def test_denied_scope_wins_over_broad_allow_scope():
    guarded = guard_gawt_tools(
        [_tool()], ("**",), ("mal-commonlib/**",)
    )
    result = guarded[0].invoke({"file": "mal-commonlib/tmp.txt", "content": "x"})
    assert result["error_type"] == "scope_violation"
    assert result["denied_paths"] == ["mal-commonlib/**"]


def test_broad_scope_still_rejects_worktree_escape():
    guarded = guard_gawt_tools([_tool()], ("**",))
    result = guarded[0].invoke({"file": "../outside.txt", "content": "x"})
    assert result["error_type"] == "scope_violation"


def test_async_write_outside_scope_returns_error():
    guarded = guard_gawt_tools([_tool()], ("mal-commonlib/**",))
    result = asyncio.run(guarded[0].ainvoke({"file": "tmp.txt", "content": "x"}))
    assert result["error_type"] == "scope_violation"


def test_scope_violation_blocks_followup_tools():
    middleware = ScopeViolationMiddleware()
    first = {"error_type": "scope_violation", "terminal": True}
    assert middleware.wrap_tool_call(_request("write"), lambda _: first) == first
    blocked = middleware.wrap_tool_call(_request("read"), lambda _: {"unexpected": True})
    assert "No further tools allowed" in blocked.content


def _request(name: str):
    return SimpleNamespace(tool_call={"name": name, "id": "call-1", "args": {}})
