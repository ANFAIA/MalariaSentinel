"""Tests for specialist path scope enforcement."""
from __future__ import annotations

import pytest
from langchain_core.tools import StructuredTool, ToolException

from agents_janus.scope_guard import guard_gawt_tools


def _tool():
    return StructuredTool.from_function(
        lambda file, content: {"file": file, "content": content},
        name="mcp__gitagent__write_file",
        description="write",
    )


def test_write_inside_scope_allowed():
    guarded = guard_gawt_tools([_tool()], ("mal-commonlib/**",))
    assert guarded[0].invoke({"file": "mal-commonlib/tmp.txt", "content": "x"})["file"] == "mal-commonlib/tmp.txt"


def test_write_outside_scope_rejected_before_mcp():
    guarded = guard_gawt_tools([_tool()], ("mal-commonlib/**",))
    with pytest.raises(ToolException, match="scope violation"):
        guarded[0].invoke({"file": "tmp.txt", "content": "x"})


def test_absolute_path_is_normalized_for_scope_check():
    guarded = guard_gawt_tools([_tool()], ("mal-commonlib/**",))
    assert guarded[0].invoke({"file": "/mal-commonlib/tmp.txt", "content": "x"})["file"].startswith("/")
