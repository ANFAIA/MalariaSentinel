"""Tests for automatic GAWT session opening before child dispatch."""
from __future__ import annotations

from types import SimpleNamespace

from agents_janus.middleware.gawt_session import GawtSessionMiddleware


class FakeTool:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def invoke(self, args):
        self.calls.append(args)
        return self.result


def request(name: str):
    return SimpleNamespace(tool_call={"name": name, "args": {}})


def test_task_opens_session_before_handler():
    start = FakeTool({"id": "session-1"})
    middleware = GawtSessionMiddleware(feature="fix malaria", start_tool=start)
    seen = []

    middleware.wrap_tool_call(request("task"), lambda _: seen.append("task"))

    assert start.calls == [{"feature": "fix malaria", "target_branch": "main"}]
    assert seen == ["task"]


def test_multiple_tasks_reuse_session():
    start = FakeTool({"id": "session-1"})
    middleware = GawtSessionMiddleware(feature="fix malaria", start_tool=start)

    middleware.wrap_tool_call(request("task"), lambda _: None)
    middleware.wrap_tool_call(request("task"), lambda _: None)

    assert start.calls == [{"feature": "fix malaria", "target_branch": "main"}]


def test_existing_session_skips_start():
    start = FakeTool({"id": "new"})
    get = FakeTool({"id": "existing"})
    middleware = GawtSessionMiddleware(feature="fix malaria", start_tool=start, get_tool=get)

    middleware.wrap_tool_call(request("task"), lambda _: None)

    assert get.calls == [{}]
    assert start.calls == []


def test_non_task_does_not_open_session():
    start = FakeTool({"id": "new"})
    middleware = GawtSessionMiddleware(feature="fix malaria", start_tool=start)

    middleware.wrap_tool_call(request("ask_user"), lambda _: None)

    assert start.calls == []
