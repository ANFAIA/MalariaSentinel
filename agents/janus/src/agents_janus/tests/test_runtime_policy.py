"""Tests for coordinator backend-tool enforcement."""
from __future__ import annotations

from types import SimpleNamespace

from agents_janus.middleware.runtime_policy import (
    COORDINATOR_GAWT_WRITE_TOOLS,
    ToolExposureMiddleware,
)


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


def test_allowlist_hides_everything_except_router_task():
    middleware = ToolExposureMiddleware(
        allowed_backend_tools=frozenset(),
        allowed_tools=frozenset({"task"}),
    )
    filtered = middleware._filter([
        {"name": "task"},
        {"name": "write_todos"},
        {"name": "write_file"},
        {"name": "ask_user"},
    ])
    assert [tool["name"] for tool in filtered] == ["task"]


def test_model_prompt_receives_explicit_tool_policy():
    middleware = ToolExposureMiddleware(
        allowed_backend_tools=frozenset(),
        allowed_tools=frozenset({"task"}),
    )
    request = SimpleNamespace(
        tools=[{"name": "task"}, {"name": "write_file"}],
        system_message="Janus router prompt",
    )
    request.override = lambda **kwargs: SimpleNamespace(**kwargs)
    seen = {}
    middleware.wrap_model_call(request, lambda rewritten: seen.update({
        "tools": [tool["name"] for tool in rewritten.tools],
        "system": rewritten.system_message,
    }))
    assert seen["tools"] == ["task"]
    assert "only tools in current tool list" in seen["system"]


def test_coordinator_gawt_mutators_are_excluded():
    middleware = ToolExposureMiddleware(
        allowed_backend_tools=frozenset(),
        excluded_tools=COORDINATOR_GAWT_WRITE_TOOLS,
    )
    filtered = middleware._filter([
        {"name": "task"},
        {"name": "mcp__gitagent__write_file"},
        {"name": "mcp__gitagent__list_edits"},
    ])
    assert [tool["name"] for tool in filtered] == ["task", "mcp__gitagent__list_edits"]
