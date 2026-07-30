"""Tests for agent.py — create_orchestrator, WORKER_DEFINITIONS."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from agents.deepagents.agent import (
    VERIFY_FINALIZE,
    VERIFY_INTEGRATE,
    TOOLS,
    ORCHESTRATOR_PROMPT,
    WORKER_DEFINITIONS,
)


class TestModuleFlags:
    def test_verify_flags_exist(self):
        assert isinstance(VERIFY_FINALIZE, bool)
        assert isinstance(VERIFY_INTEGRATE, bool)

    def test_tools_list_not_empty(self):
        assert len(TOOLS) > 0

    def test_orchestrator_prompt_mentions_workflow(self):
        assert "set_worktree_context" in ORCHESTRATOR_PROMPT
        assert "clear_worktree_context" in ORCHESTRATOR_PROMPT
        assert "gitagent_spawn" in ORCHESTRATOR_PROMPT
        assert "gitagent_integrate" in ORCHESTRATOR_PROMPT
        assert "RECONNAISSANCE" in ORCHESTRATOR_PROMPT
        assert "HYPOTHESES" in ORCHESTRATOR_PROMPT
        assert "DIAGNOSTICS" in ORCHESTRATOR_PROMPT
        assert "ASK WHEN UNCERTAIN" in ORCHESTRATOR_PROMPT
        assert "PARALLEL WORKERS" in ORCHESTRATOR_PROMPT
        assert "ask_user" in ORCHESTRATOR_PROMPT


class TestWorkerDefinitions:
    def test_workers_exist(self):
        """Both abm-worker (code-modifying) and research-worker (read-only) are defined."""
        names = [w["name"] for w in WORKER_DEFINITIONS]
        assert "abm-worker" in names
        assert "research-worker" in names

    def test_abm_worker_has_tools(self):
        """abm-worker has 3 custom tools: abm_run, abm_test, abm_score."""
        abm = next(w for w in WORKER_DEFINITIONS if w["name"] == "abm-worker")
        assert "tools" in abm
        assert len(abm["tools"]) == 3

    def test_research_worker_is_read_only(self):
        """research-worker has no code-modifying tools (read-only)."""
        rw = next(w for w in WORKER_DEFINITIONS if w["name"] == "research-worker")
        # Empty tools list — uses only deepagents' default filesystem tools
        assert rw["tools"] == []
        # System prompt mentions read-only
        assert "READ-ONLY" in rw["system_prompt"]

    def test_worker_system_prompt_is_general(self):
        """abm-worker prompt mentions general C++ modification, not just calibration."""
        abm = next(w for w in WORKER_DEFINITIONS if w["name"] == "abm-worker")
        sp = abm["system_prompt"]
        assert "ANY part" in sp or "any" in sp.lower()
        assert "gitagent propose" in sp


class TestCreateOrchestrator:
    def test_orchestrator_read_only_backend(self):
        """Test that the orchestrator uses virtual_mode=True backend with deny-write permissions."""
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
            import agents.deepagents.agent as agent_mod
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
