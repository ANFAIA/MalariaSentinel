"""Tests for agent.py — create_orchestrator, create_abm_worker_subagent."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from agents.deepagents.agent import (
    VERIFY_FINALIZE,
    VERIFY_INTEGRATE,
    TOOLS,
    ORCHESTRATOR_PROMPT,
)


class TestModuleFlags:
    def test_verify_flags_exist(self):
        assert isinstance(VERIFY_FINALIZE, bool)
        assert isinstance(VERIFY_INTEGRATE, bool)

    def test_tools_list_not_empty(self):
        assert len(TOOLS) > 0

    def test_orchestrator_prompt_mentions_workflow(self):
        assert "gitagent_init" in ORCHESTRATOR_PROMPT
        assert "gitagent_start" in ORCHESTRATOR_PROMPT
        assert "MULTI-FEATURE" in ORCHESTRATOR_PROMPT


class TestCreateWorkerSubagent:
    def test_worker_subagent_structure(self):
        """Test that create_abm_worker_subagent returns the correct structure."""
        # Mock the deepagents.backends module in sys.modules
        mock_backend_mod = MagicMock()
        mock_backend_class = MagicMock()
        mock_backend_mod.FilesystemBackend = mock_backend_class

        original_backends = sys.modules.get("deepagents.backends")
        sys.modules["deepagents.backends"] = mock_backend_mod

        try:
            from agents.deepagents.agent import create_abm_worker_subagent
            wt = Path("/tmp/test-worktree")
            result = create_abm_worker_subagent(wt)
            assert result["name"] == "abm-worker"
            assert "system_prompt" in result
            assert "backend" in result
            assert "tools" in result
            assert "permissions" in result
            assert len(result["tools"]) == 3  # abm_run, abm_test, abm_score
        finally:
            if original_backends is not None:
                sys.modules["deepagents.backends"] = original_backends
            else:
                sys.modules.pop("deepagents.backends", None)

    def test_worker_backend_virtual_mode(self):
        """Test that the worker backend uses virtual_mode=True."""
        mock_backend_mod = MagicMock()
        mock_backend_class = MagicMock()
        mock_backend_mod.FilesystemBackend = mock_backend_class

        original_backends = sys.modules.get("deepagents.backends")
        sys.modules["deepagents.backends"] = mock_backend_mod

        try:
            from agents.deepagents.agent import create_abm_worker_subagent
            wt = Path("/tmp/test-worktree")
            create_abm_worker_subagent(wt)
            mock_backend_class.assert_called_with(root_dir=str(wt), virtual_mode=True)
        finally:
            if original_backends is not None:
                sys.modules["deepagents.backends"] = original_backends
            else:
                sys.modules.pop("deepagents.backends", None)


class TestCreateOrchestrator:
    def test_orchestrator_read_only_backend(self):
        """Test that the orchestrator uses read_only=True backend."""
        mock_backend_mod = MagicMock()
        mock_backend_class = MagicMock()
        mock_backend_mod.FilesystemBackend = mock_backend_class

        mock_deepagents = MagicMock()
        mock_deepagents.create_deep_agent = MagicMock()
        mock_deepagents.backends = mock_backend_mod

        original_deepagents = sys.modules.get("deepagents")
        original_backends = sys.modules.get("deepagents.backends")
        sys.modules["deepagents"] = mock_deepagents
        sys.modules["deepagents.backends"] = mock_backend_mod

        try:
            # Force re-import to pick up the mock
            import importlib
            import agents.deepagents.agent as agent_mod
            importlib.reload(agent_mod)

            with patch.object(agent_mod, "_resolve_provider") as mock_resolve:
                mock_resolve.return_value = MagicMock()
                agent_mod.create_orchestrator(provider="openrouter", model="test", thread_id="test")
                mock_backend_class.assert_called_with(
                    root_dir=str(agent_mod.REPO_ROOT),
                    virtual_mode=True,
                    read_only=True,
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
            # Re-reload to restore original imports
            importlib.reload(agent_mod)
