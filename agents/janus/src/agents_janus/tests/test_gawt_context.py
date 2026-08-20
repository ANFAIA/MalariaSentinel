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


def test_session_id_injected_into_register_agent():
    """register_agent receives session_id when context middleware has one."""
    register = _Tool([{"agent_id": "a1", "session_id": "s_abc"}])
    middleware = GawtContextMiddleware(role="abm", register_tool=register)
    middleware.before_agent({}, None)
    assert middleware.session_id == "s_abc"

    # Now register_agent should include session_id on next registration.
    register2 = _Tool([{"agent_id": "a2"}])
    middleware2 = GawtContextMiddleware(role="scoring", register_tool=register2)
    middleware2.session_id = "s_abc"
    middleware2.before_agent({}, None)
    assert register2.calls == [{"role": "scoring", "session_id": "s_abc"}]


def test_session_id_injected_into_session_scoped_tools():
    """snapshot_session, snapshot_status, abort_session get session_id."""
    register = _Tool([{"agent_id": "a1", "session_id": "s_xyz"}])
    middleware = GawtContextMiddleware(role="abm", register_tool=register)
    middleware.before_agent({}, None)

    for tool_name in ("mcp__gitagent__snapshot_session", "mcp__gitagent__snapshot_status", "mcp__gitagent__abort_session"):
        request = _request(tool_name, {})
        seen = {}
        middleware.wrap_tool_call(request, lambda rewritten: seen.update(rewritten.tool_call["args"]))
        assert seen.get("session_id") == "s_xyz", f"session_id not injected for {tool_name}"


def test_session_id_from_state():
    """session_id can be set via agent state dict."""
    register = _Tool([{"agent_id": "a1"}])
    middleware = GawtContextMiddleware(role="abm", register_tool=register)
    middleware.before_agent({"gawt_agent_id": "from_state", "gawt_session_id": "s_from_state"}, None)
    assert middleware.session_id == "s_from_state"
