"""Tests for per-task GAWT identity injection."""
from __future__ import annotations

from types import SimpleNamespace

from agents_janus.middleware.gawt_context import GawtContextMiddleware


class _Tool:
    def __init__(self, results):
        self.results = iter(results)
        self.calls = []

    def invoke(self, args):
        self.calls.append(args)
        return next(self.results, {"ok": True})


def _request(name, args=None):
    request = SimpleNamespace(
        tool_call={"name": name, "args": dict(args or {})},
    )
    request.override = lambda **kwargs: SimpleNamespace(**kwargs)
    return request


def test_identity_is_registered_for_each_task_invocation():
    register = _Tool([{"agent_id": "a_red"}, {"agent_id": "a_blue"}])
    unregister = _Tool([])
    middleware = GawtContextMiddleware(
        role="commonlib",
        register_tool=register,
        unregister_tool=unregister,
    )

    middleware.before_agent({}, None)
    request = _request("mcp__gitagent__edit_file", {"file": "test.txt"})
    seen = {}
    middleware.wrap_tool_call(request, lambda rewritten: seen.update(rewritten.tool_call["args"]))
    assert seen["agent_id"] == "a_red"
    middleware.after_agent({}, None)

    middleware.before_agent({}, None)
    seen = {}
    middleware.wrap_tool_call(request, lambda rewritten: seen.update(rewritten.tool_call["args"]))
    assert seen["agent_id"] == "a_blue"
    middleware.after_agent({}, None)

    assert register.calls == [{"role": "commonlib"}, {"role": "commonlib"}]
    assert unregister.calls == [{"agent_id": "a_red"}, {"agent_id": "a_blue"}]


def test_before_model_registers_nested_child():
    register = _Tool([{"agent_id": "a_child"}])
    middleware = GawtContextMiddleware(role="self_improve", register_tool=register)

    middleware.before_model({}, None)

    assert register.calls == [{"role": "self_improve"}]


def test_model_cannot_override_registered_identity():
    register = _Tool([{"agent_id": "a_real"}])
    middleware = GawtContextMiddleware(role="commonlib", register_tool=register)
    middleware.before_model({}, None)
    request = _request(
        "mcp__gitagent__write_file",
        {"agent_id": "commonlib_worker", "file": "x", "content": "y"},
    )
    seen = {}

    middleware.wrap_tool_call(request, lambda rewritten: seen.update(rewritten.tool_call["args"]))

    assert seen["agent_id"] == "a_real"
