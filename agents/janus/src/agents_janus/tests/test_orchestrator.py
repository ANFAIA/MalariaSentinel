"""Tests for agent.py — create_orchestrator, _render_prompt, _get_*_tools."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from agents_janus.agent import (
    VERIFY_FINALIZE,
    _render_prompt,
    _get_dispatcher_tools,
    _get_centinela_tools,
)


class TestModuleFlags:
    def test_verify_finalize_is_bool(self):
        assert isinstance(VERIFY_FINALIZE, bool)


class TestRenderPrompt:
    def test_dispatcher_prompt_is_string(self):
        prompt = _render_prompt("dispatcher")
        assert isinstance(prompt, str)
        assert len(prompt) > 100

    def test_centinela_prompt_is_string(self):
        prompt = _render_prompt("centinela")
        assert isinstance(prompt, str)
        assert len(prompt) > 100

    def test_dispatcher_has_protocol(self):
        prompt = _render_prompt("dispatcher")
        assert "Dispatcher Protocol" in prompt
        assert "DECOMPOSE" in prompt
        assert "START SESSION" in prompt
        assert "FINALIZE" in prompt

    def test_centinela_has_protocol(self):
        prompt = _render_prompt("centinela")
        assert "Centinela Protocol" in prompt
        assert "delegate_to_dispatcher" in prompt

    def test_dispatcher_has_gawt_tools(self):
        prompt = _render_prompt("dispatcher")
        assert "mcp__gitagent__start_session" in prompt

    def test_centinela_has_onboard_tools(self):
        prompt = _render_prompt("centinela")
        assert "onboard_status" in prompt
        assert "delegate_to_dispatcher" in prompt

    def test_centinela_has_execute(self):
        prompt = _render_prompt("centinela")
        assert "execute(command=\"malariasim" in prompt


class TestGetTools:
    def test_dispatcher_tools_not_empty(self):
        tools = _get_dispatcher_tools()
        assert len(tools) > 0

    def test_centinela_tools_not_empty(self):
        tools = _get_centinela_tools()
        assert len(tools) > 0

    def test_centinela_has_delegate_to_dispatcher(self):
        tools = _get_centinela_tools()
        names = [getattr(t, "name", getattr(t, "__name__", "")) for t in tools]
        assert "delegate_to_dispatcher" in names

    def test_centinela_has_onboard_ask_subagent(self):
        tools = _get_centinela_tools()
        names = [getattr(t, "name", getattr(t, "__name__", "")) for t in tools]
        assert "onboard_ask_subagent" in names
