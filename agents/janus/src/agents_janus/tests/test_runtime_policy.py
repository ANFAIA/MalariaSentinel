"""Tests for coordinator backend-tool enforcement."""
from __future__ import annotations

from types import SimpleNamespace

from agents_janus.middleware.runtime_policy import ToolExposureMiddleware


def test_blocked_backend_tool_returns_delegate_message():
    middleware = ToolExposureMiddleware(allowed_backend_tools=frozenset())
    request = SimpleNamespace(
        tool_call={"id": "call-1", "name": "write_file", "args": {}},
    )

    result = middleware.wrap_tool_call(request, lambda _: None)

    assert "delegate through task()" in result.content
