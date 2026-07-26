"""Tests for permission configuration — secrets, data, gitagent protection."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch
import pytest

from agents.deepagents.agent import create_abm_worker_subagent


class TestWorkerPermissions:
    @patch("agents.deepagents.agent.FilesystemBackend")
    def test_deny_secrets(self, mock_backend):
        wt = Path("/tmp/test-worktree")
        result = create_abm_worker_subagent(wt)
        perms = result["permissions"]
        deny_perms = [p for p in perms if p["mode"] == "deny"]
        # Check that secrets are denied
        all_deny_paths = [path for p in deny_perms for path in p["paths"]]
        assert any("secret" in p for p in all_deny_paths)
        assert any(".env" in p for p in all_deny_paths)

    @patch("agents.deepagents.agent.FilesystemBackend")
    def test_deny_data_write(self, mock_backend):
        wt = Path("/tmp/test-worktree")
        result = create_abm_worker_subagent(wt)
        perms = result["permissions"]
        deny_write = [
            p for p in perms
            if p["mode"] == "deny" and "write" in p["operations"]
        ]
        all_deny_paths = [path for p in deny_write for path in p["paths"]]
        assert any("/data/**" in p for p in all_deny_paths)

    @patch("agents.deepagents.agent.FilesystemBackend")
    def test_deny_gitagent_write(self, mock_backend):
        wt = Path("/tmp/test-worktree")
        result = create_abm_worker_subagent(wt)
        perms = result["permissions"]
        deny_write = [
            p for p in perms
            if p["mode"] == "deny" and "write" in p["operations"]
        ]
        all_deny_paths = [path for p in deny_write for path in p["paths"]]
        assert any(".gitagent" in p for p in all_deny_paths)
        assert any(".git/" in p for p in all_deny_paths)
