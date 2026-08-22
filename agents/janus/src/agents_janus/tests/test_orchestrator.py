"""Tests for Janus role prompts and coordinator tool boundaries."""
from __future__ import annotations

from agents_janus.agent import (
    VERIFY_FINALIZE,
    _get_implementation_tools,
    _get_research_tools,
    _render_prompt,
    _create_request_router,
)
from langchain_core.messages import AIMessage


class TestModuleFlags:
    def test_verify_finalize_is_bool(self):
        assert isinstance(VERIFY_FINALIZE, bool)


class TestRenderPrompt:
    def test_router_prompt_is_minimal(self):
        prompt = _render_prompt("request_router")
        assert "request router" in prompt
        assert "research_coordinator" in prompt
        assert "implementation_coordinator" in prompt
        assert "mcp__gitagent__" not in prompt
        assert "codebase_" not in prompt

    def test_research_prompt_has_research_protocol(self):
        prompt = _render_prompt("research_coordinator")
        assert "Janus Research Coordinator" in prompt
        assert "[MODE:research]" in prompt
        assert "You do NOT edit files" in prompt
        assert "mcp__gitagent__" in prompt

    def test_implementation_prompt_has_gawt_protocol(self):
        prompt = _render_prompt("implementation_coordinator")
        assert "Janus Implementation Coordinator" in prompt
        assert "mcp__gitagent__start_session" not in prompt
        assert "mcp__gitagent__snapshot_session" in prompt
        assert "mcp__gitagent__snapshot_status" in prompt
        assert "[MODE:implementation]" in prompt
        assert "no direct repository tools" in prompt
        assert "codebase_*" not in prompt
        assert "GAWT Consensus Protocol" in prompt
        assert "SESSION_OPEN" in prompt
        assert "Pheromone & Locks Semantics" in prompt
        assert "pheromone" in prompt
        assert "informed" in prompt
        assert "Failure Recovery" in prompt


class TestGetTools:
    def test_research_tools_not_empty(self):
        assert _get_research_tools()

    def test_implementation_tools_not_empty(self):
        assert _get_implementation_tools()


class _Classifier:
    def __init__(self, route):
        self.route = route
        self.calls = []

    def invoke(self, messages):
        self.calls.append(messages)
        return type("Decision", (), {"route": self.route})()


class _RouterLLM:
    def __init__(self, classifier):
        self.classifier = classifier

    def with_structured_output(self, _schema):
        return self.classifier


class _Child:
    def __init__(self, text):
        self.text = text
        self.calls = []

    def invoke(self, state, config=None):
        self.calls.append((state, config))
        return {"messages": [AIMessage(content=self.text)]}


def test_request_router_classifies_once_and_dispatches_original_request():
    classifier = _Classifier("implementation_coordinator")
    research = _Child("research")
    implementation = _Child("implementation")
    router = _create_request_router(
        _RouterLLM(classifier), research, implementation
    )

    result = router.invoke(
        {"messages": [{"role": "user", "content": "Edit file"}]},
        config={"configurable": {"thread_id": "router-test"}},
    )

    assert len(classifier.calls) == 1
    assert not research.calls
    assert implementation.calls[0][0]["messages"][0].content == "Edit file"
    assert result["messages"][-1].content == "implementation"
