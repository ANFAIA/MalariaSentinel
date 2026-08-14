"""E2E tests for the onboarding agent tools.

Tests cover:
- onboard_ask_subagent: returns answer, handles unknown subagent
- tool completeness: all expected research tools are callable
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

# Pre-import so module-level patches work (avoids import-inside-with issues)
from agents_janus.tools.onboard_tools import (
    onboard_status,
    onboard_list_components,
    onboard_ask_subagent,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_fake_llm(content: str = "Test specialist response"):
    """Create a mock ChatOpenAI that returns fixed content."""
    fake_llm = MagicMock()
    mock_response = MagicMock()
    mock_response.content = content
    fake_llm.invoke.return_value = mock_response
    return fake_llm


def _make_fake_registry():
    """Create a mock Registry with two known subagents."""
    mock_spec = MagicMock()
    mock_spec.name = "scoring"
    mock_spec.description = "Runs calibration scorers"
    mock_spec.spec_path = None
    mock_spec.model = "xiaomi/mimo-v2.5"
    mock_spec.provider = "openrouter"
    mock_spec.skills = ()
    mock_spec.mailbox_inbox = "inbox-scoring"
    mock_spec.edits_allow = ("runs/**",)

    mock_spec_abm = MagicMock()
    mock_spec_abm.name = "abm"
    mock_spec_abm.description = "Runs ABM simulations"
    mock_spec_abm.spec_path = None
    mock_spec_abm.model = "xiaomi/mimo-v2.5"
    mock_spec_abm.provider = "openrouter"
    mock_spec_abm.skills = ()
    mock_spec_abm.mailbox_inbox = "inbox-abm"
    mock_spec_abm.edits_allow = ("mal-core/**",)

    mock_registry = MagicMock()
    mock_registry.get.return_value = mock_spec
    mock_registry.all.return_value = {
        "scoring": mock_spec,
        "abm": mock_spec_abm,
    }
    return mock_registry


# ---------------------------------------------------------------------------
# Test 1: onboard_ask_subagent returns answer
# ---------------------------------------------------------------------------

def test_onboard_ask_subagent_returns_answer():
    """onboard_ask_subagent should return JSON with a response string."""
    with (
        patch("agents_janus.tools.onboard_tools._resolve_llm") as mock_llm,
        patch("agents_janus.subagents.builder.build_subagent_prompt") as mock_build,
        patch("agents_janus.subagents.registry.load_registry") as mock_load,
    ):
        mock_load.return_value = _make_fake_registry()
        mock_build.return_value = "You are a scoring specialist."
        mock_llm.return_value = _make_fake_llm("We have D1-D14 scorers plus composite.")

        result = json.loads(onboard_ask_subagent("scoring", "What scorers do you have?"))

    assert result["status"] == "ok"
    assert result["subagent"] == "scoring"
    assert result["question"] == "What scorers do you have?"
    assert "D1-D14" in result["response"]
    mock_llm.assert_called_once()


# ---------------------------------------------------------------------------
# Test 2: onboard_ask_subagent with unknown subagent
# ---------------------------------------------------------------------------

def test_onboard_ask_subagent_unknown_subagent():
    """onboard_ask_subagent should return error for unknown subagent name."""
    with patch("agents_janus.subagents.registry.load_registry") as mock_load:
        mock_reg = _make_fake_registry()
        mock_reg.get.side_effect = KeyError("Unknown subagent: nonexistent")
        mock_load.return_value = mock_reg

        result = json.loads(onboard_ask_subagent("nonexistent", "hello"))

    assert result["status"] == "error"
    assert "Unknown subagent" in result["error"] or "nonexistent" in result["error"]
    assert "available" in result


# ---------------------------------------------------------------------------
# Test 3: onboard_ask_subagent builds prompt without plugins
# ---------------------------------------------------------------------------

def test_onboard_ask_subagent_builds_prompt():
    """build_subagent_prompt should be called with spec and all_specs."""
    with (
        patch("agents_janus.tools.onboard_tools._resolve_llm") as mock_llm,
        patch("agents_janus.subagents.builder.build_subagent_prompt") as mock_build,
        patch("agents_janus.subagents.registry.load_registry") as mock_load,
    ):
        mock_load.return_value = _make_fake_registry()
        mock_build.return_value = "You are READ-ONLY."
        mock_llm.return_value = _make_fake_llm("ok")

        onboard_ask_subagent("scoring", "test")

        # Verify build_subagent_prompt was called (no plugin_chain param)
        mock_build.assert_called_once()
        call_args = mock_build.call_args
        # First positional arg is spec
        assert call_args[0][0].name == "scoring"
        # all_specs is a keyword arg
        assert "all_specs" in call_args.kwargs


# ---------------------------------------------------------------------------
# Test 4: tool completeness
# ---------------------------------------------------------------------------

def test_onboarding_tools_complete():
    """All expected tools should be callable."""
    expected_tools = [
        onboard_status,
        onboard_list_components,
        onboard_ask_subagent,
    ]
    for tool in expected_tools:
        assert callable(tool), f"{tool.__name__} is not callable"

    assert onboard_ask_subagent.__name__ == "onboard_ask_subagent"
    assert "name" in onboard_ask_subagent.__code__.co_varnames
    assert "question" in onboard_ask_subagent.__code__.co_varnames
