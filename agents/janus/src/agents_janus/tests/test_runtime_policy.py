"""Tests for coordinator backend-tool enforcement."""
from __future__ import annotations

from types import SimpleNamespace

from agents_janus.middleware.runtime_policy import ToolExposureMiddleware


def _make_request(name: str, args: dict | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        tool_call={"id": f"call-{name}", "name": name, "args": args or {}},
    )


def test_blocked_backend_tool_returns_delegate_message():
    middleware = ToolExposureMiddleware(allowed_backend_tools=frozenset())
    request = _make_request("write_file")

    result = middleware.wrap_tool_call(request, lambda _: None)

    assert "delegate through task()" in result.content


def test_excluded_tools_blocked_at_call_time():
    middleware = ToolExposureMiddleware(
        allowed_backend_tools=frozenset(),
        excluded_tools=frozenset({"write_todos"}),
    )
    request = _make_request("write_todos")

    result = middleware.wrap_tool_call(request, lambda _: None)

    assert "delegate through task()" in result.content


def test_excluded_tools_filtered_from_model_view():
    middleware = ToolExposureMiddleware(
        allowed_backend_tools=frozenset(),
        excluded_tools=frozenset({"write_todos", "execute"}),
    )

    tools = [
        {"name": "task"},
        {"name": "write_todos"},
        {"name": "execute"},
        {"name": "ask_user"},
    ]

    filtered = middleware._filter(tools)

    assert [t["name"] for t in filtered] == ["task", "ask_user"]


def test_allowed_backend_tools_still_visible():
    middleware = ToolExposureMiddleware(
        allowed_backend_tools=frozenset({"execute"}),
        excluded_tools=frozenset(),
    )

    tools = [
        {"name": "execute"},
        {"name": "write_file"},
        {"name": "task"},
    ]

    filtered = middleware._filter(tools)

    assert [t["name"] for t in filtered] == ["execute", "task"]
