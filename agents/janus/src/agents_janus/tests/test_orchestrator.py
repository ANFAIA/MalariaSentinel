"""Tests for agent.py — create_orchestrator, _load_orchestrator_prompt, TOOLS."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from agents_janus.agent import (
    VERIFY_FINALIZE,
    TOOLS,
    _load_orchestrator_prompt,
)


class TestModuleFlags:
    def test_verify_finalize_is_bool(self):
        assert isinstance(VERIFY_FINALIZE, bool)

    def test_tools_list_not_empty(self):
        assert len(TOOLS) > 0

    def test_tools_no_gitagent_functions(self):
        """TOOLS must not contain any gitagent_* functions (replaced by gawt MCP)."""
        for tool in TOOLS:
            name = getattr(tool, "__name__", str(tool))
            assert "gitagent_" not in name, f"Old gitagent tool found in TOOLS: {name}"


class TestOrchestratorPrompt:
    def test_prompt_is_string(self):
        prompt = _load_orchestrator_prompt()
        assert isinstance(prompt, str)
        assert len(prompt) > 100

    def test_prompt_mentions_gawt_mcp_tools(self):
        """Orchestrator prompt must reference gawt MCP tools, not old gitagent_*."""
        prompt = _load_orchestrator_prompt()
        assert "mcp__gitagent__start_session" in prompt
        assert "mcp__gitagent__finalize_session" in prompt
        assert "mcp__gitagent__list_agents" in prompt

    def test_prompt_does_not_mention_old_tools(self):
        """Old gitagent_spawn/propose/integrate must be gone."""
        prompt = _load_orchestrator_prompt()
        assert "gitagent_spawn" not in prompt
        assert "gitagent_propose" not in prompt
        assert "gitagent_integrate" not in prompt

    def test_prompt_mentions_dispatcher_concepts(self):
        prompt = _load_orchestrator_prompt()
        assert "specialist" in prompt.lower() or "dispatch" in prompt.lower()
        assert "gawt" in prompt.lower()


class TestCreateOrchestrator:
    def test_orchestrator_read_only_backend(self):
        """Test that create_orchestrator uses virtual_mode=True backend."""
        mock_backend_mod = MagicMock()
        mock_backend_class = MagicMock()
        mock_backend_mod.FilesystemBackend = mock_backend_class

        mock_deepagents = MagicMock()
        mock_deepagents.create_deep_agent = MagicMock()
        mock_deepagents.backends = mock_backend_mod
        mock_deepagents.FilesystemPermission = MagicMock

        original_deepagents = sys.modules.get("deepagents")
        original_backends = sys.modules.get("deepagents.backends")
        sys.modules["deepagents"] = mock_deepagents
        sys.modules["deepagents.backends"] = mock_backend_mod

        try:
            import importlib
            import agents_janus.agent as agent_mod
            importlib.reload(agent_mod)

            with patch.object(agent_mod, "_resolve_provider") as mock_resolve:
                mock_resolve.return_value = MagicMock()
                agent_mod.create_orchestrator(provider="openrouter", model="test", thread_id="test")
                mock_backend_class.assert_called_with(
                    root_dir=str(agent_mod.REPO_ROOT),
                    virtual_mode=True,
                )
        finally:
            if original_deepagents is not None:
                sys.modules["deepagents"] = original_deepagents
            else:
                sys.modules.pop("deepagents", None)
            if original_backends is not None:
                sys.modules["deepagents.backends"] = original_backends
            else:
                sys.modules.pop("deepagents.backends", None)
            importlib.reload(agent_mod)
