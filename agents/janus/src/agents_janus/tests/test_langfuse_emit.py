"""Tests for ObservabilityMiddleware's langfuse emitter.

Mocks the langfuse.Langfuse client so we can assert event mapping without
hitting a real langfuse server.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from agents_janus.observability import ObservabilityMiddleware, _safe_call


class _FakeLangfuseSpan:
    """Mock span object that records update/end calls."""
    def __init__(self, name):
        self.name = name
        self.updates = []
        self.ended = False

    def update(self, **kwargs):
        self.updates.append(kwargs)

    def end(self):
        self.ended = True


# ----------------------------------------------------------------------
# _safe_call
# ----------------------------------------------------------------------

def test_safe_call_returns_value_on_success():
    result = _safe_call(lambda: "hello")
    assert result == "hello"


def test_safe_call_returns_error_marker_on_exception():
    marker = _safe_call(lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    assert hasattr(marker, "error")
    assert isinstance(marker.error, RuntimeError)


# ----------------------------------------------------------------------
# ObservabilityMiddleware without langfuse
# ----------------------------------------------------------------------

def test_no_langfuse_when_disabled():
    """No langfuse_client passed → no langfuse calls, no errors."""
    sl = MagicMock()
    mw = ObservabilityMiddleware(sl)

    # Simulate a state object
    state = {"messages": []}
    runtime = MagicMock()
    runtime.model_name = "test/model"

    mw.before_agent(state, runtime)
    mw.before_model(state, runtime)

    # handler is a no-op
    request = MagicMock()
    request.model.model_name = "test/model"
    request.messages = []
    response = MagicMock()
    response.result = []
    mw.wrap_model_call(request, lambda req: response)
    mw.after_model(state, runtime)

    request2 = MagicMock()
    request2.tool_call.name = "x"
    request2.tool_call.args = {}
    mw.wrap_tool_call(request2, lambda req: {"ok": True})

    mw.after_agent(state, runtime)

    # sl._append and sl.log_* were called (JSONL sink is always on)
    assert sl._append.called or sl.log_agent_event.called


# ----------------------------------------------------------------------
# ObservabilityMiddleware with langfuse (mocked)
# ----------------------------------------------------------------------

@pytest.fixture
def mock_langfuse():
    lf = MagicMock()
    lf.span.return_value = _FakeLangfuseSpan("tool:x")
    lf.generation.return_value = _FakeLangfuseSpan("llm_call")
    return lf


def test_llm_call_emits_generation(mock_langfuse):
    sl = MagicMock()
    mw = ObservabilityMiddleware(sl, langfuse_client=mock_langfuse)
    state = {"messages": []}
    runtime = MagicMock()
    runtime.model_name = "mimo"
    mw.before_agent(state, runtime)
    mw.before_model(state, runtime)

    request = MagicMock()
    request.model.model_name = "mimo"
    request.messages = [MagicMock(content="hi"), MagicMock(content="there")]
    response = MagicMock()
    response.result = [
        MagicMock(
            usage_metadata={"input_tokens": 100, "output_tokens": 20},
            content="hello back",
        )
    ]
    mw.wrap_model_call(request, lambda req: response)
    mw.after_model(state, runtime)
    mw.after_agent(state, runtime)

    mock_langfuse.generation.assert_called_once()
    kwargs = mock_langfuse.generation.call_args.kwargs
    assert kwargs["name"] == "llm_call"
    assert kwargs["model"] == "mimo"
    assert kwargs["usage"] == {"input": 100, "output": 20, "total": 120}
    mock_langfuse.flush.assert_called_once()


def test_tool_call_emits_span(mock_langfuse):
    sl = MagicMock()
    mw = ObservabilityMiddleware(sl, langfuse_client=mock_langfuse)
    state = {"messages": []}
    runtime = MagicMock()
    runtime.model_name = "m"
    mw.before_agent(state, runtime)

    request = MagicMock()
    request.tool_call.name = "abm_run"
    request.tool_call.args = {"seed": 1, "days": 365}
    response = MagicMock()
    response.content = "ok 4802 rows"
    mw.wrap_tool_call(request, lambda req: response)

    mw.after_agent(state, runtime)

    mock_langfuse.span.assert_called_once()
    span_kwargs = mock_langfuse.span.call_args.kwargs
    assert span_kwargs["name"] == "tool:abm_run"
    # span.end() was called by the middleware
    span_obj = mock_langfuse.span.return_value
    assert span_obj.ended is True


def test_tool_error_marks_span_as_failed(mock_langfuse):
    sl = MagicMock()
    mw = ObservabilityMiddleware(sl, langfuse_client=mock_langfuse)
    state = {"messages": []}
    runtime = MagicMock()
    runtime.model_name = "m"
    mw.before_agent(state, runtime)

    def failing_handler(req):
        raise RuntimeError("kaboom")

    request = MagicMock()
    request.tool_call.name = "broken"
    request.tool_call.args = {}

    with pytest.raises(RuntimeError):
        mw.wrap_tool_call(request, failing_handler)

    span_obj = mock_langfuse.span.return_value
    # update was called with error info
    assert span_obj.updates, "span.update should have been called"
    update = span_obj.updates[0]
    assert update.get("level") == "ERROR"
    assert "kaboom" in update.get("output", {}).get("error", "")
    assert span_obj.ended is True


def test_langfuse_error_does_not_crash(mock_langfuse):
    """A failing langfuse SDK must not abort the orchestrator run."""
    sl = MagicMock()
    mock_langfuse.generation.side_effect = RuntimeError("network down")

    mw = ObservabilityMiddleware(sl, langfuse_client=mock_langfuse)
    state = {"messages": []}
    runtime = MagicMock()
    runtime.model_name = "m"
    mw.before_agent(state, runtime)
    mw.before_model(state, runtime)

    request = MagicMock()
    request.model.model_name = "m"
    request.messages = []
    response = MagicMock()
    response.result = [
        MagicMock(usage_metadata={"input_tokens": 1, "output_tokens": 1}, content="hi")
    ]
    # Should NOT raise despite langfuse.generation() failing
    result = mw.wrap_model_call(request, lambda req: response)
    assert result is response

    mw.after_agent(state, runtime)

    # A langfuse_error event was logged to JSONL
    appended = [c.args[0] for c in sl._append.call_args_list]
    assert any(ev.get("event") == "langfuse_error" for ev in appended)


def test_flush_called_on_agent_end(mock_langfuse):
    sl = MagicMock()
    mw = ObservabilityMiddleware(sl, langfuse_client=mock_langfuse)
    state = {"messages": []}
    runtime = MagicMock()
    runtime.model_name = "m"
    mw.before_agent(state, runtime)
    mw.after_agent(state, runtime)
    mock_langfuse.flush.assert_called_once()


def test_before_agent_writes_session_id_metadata(mock_langfuse):
    sl = MagicMock()
    sl.session_dir.name = "janus-20260803-123456"
    mw = ObservabilityMiddleware(sl, langfuse_client=mock_langfuse)
    state = {"messages": []}
    runtime = MagicMock()
    runtime.model_name = "m"
    mw.before_agent(state, runtime)
    mock_langfuse.update_current_observation.assert_called_once()
    kwargs = mock_langfuse.update_current_observation.call_args.kwargs
    assert kwargs["metadata"]["session_id"] == "janus-20260803-123456"


def test_no_langfuse_flush_when_disabled():
    """Without a langfuse client, flush() is never called."""
    sl = MagicMock()
    mw = ObservabilityMiddleware(sl, langfuse_client=None)
    state = {"messages": []}
    runtime = MagicMock()
    runtime.model_name = "m"
    mw.before_agent(state, runtime)
    mw.after_agent(state, runtime)
    # No exceptions, no langfuse calls (no client to call).
    sl.log_token_summary.assert_called_once()