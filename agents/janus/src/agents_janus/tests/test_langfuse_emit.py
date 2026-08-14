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
    def __init__(self, name, trace_id="fake-trace-id"):
        self.name = name
        self.trace_id = trace_id
        self.id = f"span-{name}"
        self.updates = []
        self.ended = False

    def update(self, **kwargs):
        self.updates.append(kwargs)

    def end(self):
        self.ended = True

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.ended = True
        return False


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

    # Use dict-style tool_call (matches real ToolCallRequest.tool_call TypedDict)
    request2 = MagicMock()
    request2.tool_call = {"name": "x", "args": {}, "id": "call_x"}
    mw.wrap_tool_call(request2, lambda req: {"ok": True})

    mw.after_agent(state, runtime)

    # sl._append and sl.log_* were called (JSONL sink is always on)
    assert sl._append.called or sl.log_agent_event.called


# ----------------------------------------------------------------------
# ObservabilityMiddleware with langfuse (mocked)
# ----------------------------------------------------------------------

@pytest.fixture
def mock_langfuse(monkeypatch):
    lf = MagicMock()
    # v4 API: start_observation returns a span-like object (used for root + child spans)
    lf.start_observation.return_value = _FakeLangfuseSpan("span")

    # Mock TraceContext so before_agent can import it without langfuse installed
    mock_tc = MagicMock()
    mock_tc.trace_id = "fake-trace-id"
    mock_tc.parent_span_id = "span-root"
    mock_langfuse_types = MagicMock()
    mock_langfuse_types.TraceContext = MagicMock(return_value=mock_tc)
    monkeypatch.setitem(__import__("sys").modules, "langfuse.types", mock_langfuse_types)

    return lf


def test_llm_call_emits_generation(mock_langfuse):
    sl = MagicMock()
    sl.session_dir.name = "janus-test"
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

    # v4: start_observation called with as_type="generation"
    calls = mock_langfuse.start_observation.call_args_list
    gen_calls = [c for c in calls if c.kwargs.get("as_type") == "generation"]
    assert len(gen_calls) == 1
    kwargs = gen_calls[0].kwargs
    assert kwargs["name"] == "llm:implementation_coordinator"
    assert kwargs["model"] == "mimo"
    assert kwargs["usage_details"]["input"] == 100
    assert kwargs["usage_details"]["output"] == 20
    mock_langfuse.flush.assert_called_once()


@pytest.mark.parametrize(
    ("mode", "expected_name"),
    [
        ("request_router", "llm:request_router"),
        ("research_coordinator", "llm:research_coordinator"),
        ("implementation_coordinator", "llm:implementation_coordinator"),
    ],
)
def test_llm_call_uses_coordinator_role(mock_langfuse, mode, expected_name):
    sl = MagicMock()
    sl.session_dir.name = "janus-test"
    mw = ObservabilityMiddleware(sl, langfuse_client=mock_langfuse, mode=mode)
    state = {"messages": []}
    runtime = MagicMock()
    runtime.model_name = "mimo"
    mw.before_agent(state, runtime)

    request = MagicMock()
    request.model.model_name = "mimo"
    request.messages = []
    response = MagicMock()
    response.result = [MagicMock(usage_metadata={}, content="ok")]
    mw.wrap_model_call(request, lambda req: response)

    generations = [
        c for c in mock_langfuse.start_observation.call_args_list
        if c.kwargs.get("as_type") == "generation"
    ]
    assert generations[-1].kwargs["name"] == expected_name


def test_tool_call_emits_span(mock_langfuse):
    sl = MagicMock()
    sl.session_dir.name = "janus-test"
    mw = ObservabilityMiddleware(sl, langfuse_client=mock_langfuse)
    state = {"messages": []}
    runtime = MagicMock()
    runtime.model_name = "m"
    mw.before_agent(state, runtime)

    # Use dict-style tool_call (matches real ToolCallRequest.tool_call TypedDict)
    request = MagicMock()
    request.tool_call = {"name": "abm_run", "args": {"seed": 1, "days": 365}, "id": "call_1"}
    response = MagicMock()
    response.content = "ok 4802 rows"
    mw.wrap_tool_call(request, lambda req: response)

    mw.after_agent(state, runtime)

    # v4: start_observation called with as_type="span" for tool calls
    calls = mock_langfuse.start_observation.call_args_list
    span_calls = [c for c in calls if c.kwargs.get("as_type") == "span" and "tool:" in c.kwargs.get("name", "")]
    assert len(span_calls) == 1
    assert span_calls[0].kwargs["name"] == "tool:abm_run"
    # span.end() was called by the middleware
    span_obj = mock_langfuse.start_observation.return_value
    assert span_obj.ended is True


def test_tool_error_marks_span_as_failed(mock_langfuse):
    sl = MagicMock()
    sl.session_dir.name = "janus-test"
    mw = ObservabilityMiddleware(sl, langfuse_client=mock_langfuse)
    state = {"messages": []}
    runtime = MagicMock()
    runtime.model_name = "m"
    mw.before_agent(state, runtime)

    def failing_handler(req):
        raise RuntimeError("kaboom")

    # Use dict-style tool_call (matches real ToolCallRequest.tool_call TypedDict)
    request = MagicMock()
    request.tool_call = {"name": "broken", "args": {}, "id": "call_err"}

    with pytest.raises(RuntimeError):
        mw.wrap_tool_call(request, failing_handler)

    span_obj = mock_langfuse.start_observation.return_value
    # update was called with error info
    assert span_obj.updates, "span.update should have been called"
    update = span_obj.updates[0]
    assert update.get("level") == "ERROR"
    assert "kaboom" in update.get("output", {}).get("error", "")
    assert span_obj.ended is True


def test_langfuse_error_does_not_crash(mock_langfuse):
    """A failing langfuse SDK must not abort the orchestrator run."""
    sl = MagicMock()
    sl.session_dir.name = "janus-test"
    mock_langfuse.start_observation.side_effect = RuntimeError("network down")

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
    # Should NOT raise despite langfuse failing
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
    # v4: start_observation called with session_id metadata
    mock_langfuse.start_observation.assert_called_once()
    kwargs = mock_langfuse.start_observation.call_args.kwargs
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


# ----------------------------------------------------------------------
# _extract_content_preview
# ----------------------------------------------------------------------

def test_extract_content_preview_string():
    from agents_janus.observability import _extract_content_preview
    result = MagicMock()
    result.content = "hello world"
    assert _extract_content_preview(result) == "hello world"


def test_extract_content_preview_list_blocks():
    from agents_janus.observability import _extract_content_preview
    result = MagicMock()
    result.content = [{"type": "text", "text": "block1"}, {"type": "text", "text": "block2"}]
    assert "block1" in _extract_content_preview(result)
    assert "block2" in _extract_content_preview(result)


def test_extract_content_preview_no_content():
    from agents_janus.observability import _extract_content_preview
    # Object without .content — falls back to str()
    result = "plain string result"
    assert _extract_content_preview(result) == "plain string result"


def test_extract_content_preview_dict():
    from agents_janus.observability import _extract_content_preview
    result = {"content": "dict content", "other": "field"}
    assert _extract_content_preview(result) == "dict content"


def test_extract_content_preview_dict_output_key():
    from agents_janus.observability import _extract_content_preview
    result = {"output": "output value"}
    assert _extract_content_preview(result) == "output value"


# ----------------------------------------------------------------------
# Dict-style tool_call extraction (real ToolCallRequest shape)
# ----------------------------------------------------------------------

def test_dict_tool_call_extracts_name_and_args(mock_langfuse):
    """ToolCallRequest.tool_call is a ToolCall TypedDict (dict), not an object.

    The middleware must extract name/args via dict.get(), not attribute access.
    """
    sl = MagicMock()
    sl.session_dir.name = "janus-test"
    mw = ObservabilityMiddleware(sl, langfuse_client=mock_langfuse)
    state = {"messages": []}
    runtime = MagicMock()
    mw.before_agent(state, runtime)

    # Real shape: tool_call is a dict
    request = MagicMock()
    request.tool_call = {
        "name": "gitagent_status",
        "args": {"aoi": "ghana"},
        "id": "call_abc123",
        "type": "tool_call",
    }
    response = MagicMock()
    response.content = "status: ready"
    mw.wrap_tool_call(request, lambda req: response)

    mw.after_agent(state, runtime)

    # Verify span was created with correct tool name
    calls = mock_langfuse.start_observation.call_args_list
    span_calls = [c for c in calls if c.kwargs.get("as_type") == "span" and "tool:" in c.kwargs.get("name", "")]
    assert len(span_calls) == 1
    assert span_calls[0].kwargs["name"] == "tool:gitagent_status"
