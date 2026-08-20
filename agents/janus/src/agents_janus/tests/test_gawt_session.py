"""Tests for automatic GAWT session opening before child dispatch."""
from __future__ import annotations

from types import SimpleNamespace

from agents_janus.middleware.gawt_context import GawtContextMiddleware
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
    start = FakeTool({"session_id": "s_1"})
    middleware = GawtSessionMiddleware(feature="fix malaria", start_tool=start)
    seen = []

    middleware.wrap_tool_call(request("task"), lambda _: seen.append("task"))

    assert start.calls == [{"feature": "fix malaria", "target_branch": "main", "lock_ttl_seconds": 15}]
    assert seen == ["task"]


def test_multiple_tasks_reuse_session():
    start = FakeTool({"session_id": "s_1"})
    middleware = GawtSessionMiddleware(feature="fix malaria", start_tool=start)

    middleware.wrap_tool_call(request("task"), lambda _: None)
    middleware.wrap_tool_call(request("task"), lambda _: None)

    assert len(start.calls) == 1


def test_existing_session_skips_start():
    start = FakeTool({"session_id": "new"})
    get = FakeTool({"session_id": "existing"})
    middleware = GawtSessionMiddleware(feature="fix malaria", start_tool=start, get_tool=get)

    middleware.wrap_tool_call(request("task"), lambda _: None)

    assert get.calls == [{}]
    assert start.calls == []
    assert middleware.session_id == "existing"


def test_non_task_does_not_open_session():
    start = FakeTool({"session_id": "new"})
    middleware = GawtSessionMiddleware(feature="fix malaria", start_tool=start)

    middleware.wrap_tool_call(request("ask_user"), lambda _: None)

    assert start.calls == []


def test_session_id_propagated_to_context_middleware():
    """GawtSessionMiddleware shares session_id with GawtContextMiddleware."""
    register = _Tool([{"agent_id": "a1"}])
    ctx_mw = GawtContextMiddleware(role="abm", register_tool=register)
    start = FakeTool({"session_id": "s_shared"})
    session_mw = GawtSessionMiddleware(
        feature="test",
        start_tool=start,
        context_middlewares=[ctx_mw],
    )

    session_mw.wrap_tool_call(request("task"), lambda _: None)

    assert session_mw.session_id == "s_shared"
    assert ctx_mw.session_id == "s_shared"


def test_abort_calls_abort_tool():
    """abort() calls abort_session with session_id."""
    start = FakeTool({"session_id": "s_abort"})
    abort = FakeTool({"ok": True})
    middleware = GawtSessionMiddleware(feature="test", start_tool=start, abort_tool=abort)
    middleware.wrap_tool_call(request("task"), lambda _: None)

    middleware.abort()

    assert abort.calls == [{"session_id": "s_abort"}]
    assert middleware.session_id is None


def test_abort_noop_when_no_session():
    """abort() does nothing when no session is open."""
    abort = FakeTool({"ok": True})
    start = FakeTool({"session_id": "s_no"})
    middleware = GawtSessionMiddleware(feature="test", start_tool=start, abort_tool=abort)

    middleware.abort()

    assert abort.calls == []


def test_monitoring_tools_receive_current_session_id():
    start = FakeTool({"session_id": "s_monitor"})
    middleware = GawtSessionMiddleware(feature="test", start_tool=start)
    middleware.wrap_tool_call(request("task"), lambda _: None)
    req = SimpleNamespace(
        tool_call={"name": "mcp__gitagent__list_edits", "args": {}},
    )
    req.override = lambda **kwargs: SimpleNamespace(**kwargs)
    seen = {}
    middleware.wrap_tool_call(req, lambda rewritten: seen.update(rewritten.tool_call["args"]))
    assert seen == {"session_id": "s_monitor"}


def test_model_start_session_is_clamped_and_propagated():
    """Legacy/model calls cannot request lock TTL above 15 seconds."""
    start = FakeTool({"session_id": "s_clamped"})
    middleware = GawtSessionMiddleware(feature="test", start_tool=start)
    request_obj = SimpleNamespace(
        tool_call={
            "name": "mcp__gitagent__start_session",
            "args": {"feature": "test", "target_branch": "main", "lock_ttl_seconds": 300},
        },
    )
    request_obj.override = lambda **kwargs: SimpleNamespace(**kwargs)

    seen = {}
    middleware.wrap_tool_call(
        request_obj,
        lambda rewritten: (seen.update(rewritten.tool_call["args"]) or {"session_id": "s_clamped"}),
    )

    assert seen == {
        "feature": "test",
        "target_branch": "main",
        "lock_ttl_seconds": 15,
    }
    assert middleware.session_id == "s_clamped"


class _Tool:
    def __init__(self, results=None):
        self.results = iter(results or [])
        self.calls = []

    def invoke(self, args):
        self.calls.append(args)
        return next(self.results, {"ok": True})
