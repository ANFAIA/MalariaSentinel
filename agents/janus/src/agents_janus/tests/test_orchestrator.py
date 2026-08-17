"""Tests for Janus role prompts and coordinator tool boundaries."""
from __future__ import annotations

from agents_janus.agent import (
    VERIFY_FINALIZE,
    _get_implementation_tools,
    _get_research_tools,
    _render_prompt,
)


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
        assert "mcp__gitagent__start_session" in prompt
        assert "mcp__gitagent__finalize_session" in prompt
        assert "[MODE:implementation]" in prompt
        assert "no direct repository tools" in prompt
        assert "codebase_*" not in prompt
        assert "GAWT Consensus Protocol" in prompt
        assert "SESSION_OPEN" in prompt
        assert "Inbox Semantics" in prompt
        assert "CONFLICT DETECTED" in prompt
        assert "Failure Recovery" in prompt


class TestGetTools:
    def test_research_tools_not_empty(self):
        assert _get_research_tools()

    def test_implementation_tools_not_empty(self):
        assert _get_implementation_tools()
