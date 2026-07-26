"""Tests for agent.py — create_orchestrator, create_abm_worker_subagent."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from agents.deepagents.agent import (
    VERIFY_FINALIZE,
    VERIFY_INTEGRATE,
    TOOLS,
    ORCHESTRATOR_PROMPT,
    create_abm_worker_subagent,
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
    @patch("agents.deepagents.agent.FilesystemBackend")
    @patch("agents.deepagents.agent.FilesystemPermission")
    def test_worker_subagent_structure(self, mock_perm, mock_backend):
        wt = Path("/tmp/test-worktree")
        result = create_abm_worker_subagent(wt)
        assert result["name"] == "abm-worker"
        assert "system_prompt" in result
        assert "backend" in result
        assert "tools" in result
        assert "permissions" in result
        assert len(result["tools"]) == 3  # abm_run, abm_test, abm_score

    @patch("agents.deepagents.agent.FilesystemBackend")
    def test_worker_backend_virtual_mode(self, mock_backend):
        wt = Path("/tmp/test-worktree")
        create_abm_worker_subagent(wt)
        mock_backend.assert_called_with(root_dir=str(wt), virtual_mode=True)


class TestCreateOrchestrator:
    @patch("agents.deepagents.agent._resolve_provider")
    @patch("agents.deepagents.agent.create_deep_agent")
    @patch("agents.deepagents.agent.FilesystemBackend")
    def test_orchestrator_read_only_backend(self, mock_backend, mock_create, mock_resolve):
        mock_resolve.return_value = MagicMock()
        mock_create.return_value = MagicMock()
        from agents.deepagents.agent import create_orchestrator
        create_orchestrator(provider="openrouter", model="test", thread_id="test")
        mock_backend.assert_called_with(
            root_dir=str(Path(__file__).resolve().parent.parent.parent.parent.parent),
            virtual_mode=True,
            read_only=True,
        )
