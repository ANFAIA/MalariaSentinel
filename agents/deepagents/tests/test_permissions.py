"""Tests for permission configuration — secrets, data, gitagent protection."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock
import pytest


class TestWorkerPermissions:
    def _create_worker_with_mock(self):
        """Helper to create worker with mocked backends."""
        mock_backend_mod = MagicMock()
        mock_backend_class = MagicMock()
        mock_backend_mod.FilesystemBackend = mock_backend_class

        original_backends = sys.modules.get("deepagents.backends")
        sys.modules["deepagents.backends"] = mock_backend_mod

        try:
            from agents.deepagents.agent import create_abm_worker_subagent
            wt = Path("/tmp/test-worktree")
            return create_abm_worker_subagent(wt)
        finally:
            if original_backends is not None:
                sys.modules["deepagents.backends"] = original_backends
            else:
                sys.modules.pop("deepagents.backends", None)

    def test_deny_secrets(self):
        result = self._create_worker_with_mock()
        perms = result["permissions"]
        deny_perms = [p for p in perms if p["mode"] == "deny"]
        all_deny_paths = [path for p in deny_perms for path in p["paths"]]
        assert any("secret" in p for p in all_deny_paths)
        assert any(".env" in p for p in all_deny_paths)

    def test_deny_data_write(self):
        result = self._create_worker_with_mock()
        perms = result["permissions"]
        deny_write = [
            p for p in perms
            if p["mode"] == "deny" and "write" in p["operations"]
        ]
        all_deny_paths = [path for p in deny_write for path in p["paths"]]
        assert any("/data/**" in p for p in all_deny_paths)

    def test_deny_gitagent_write(self):
        result = self._create_worker_with_mock()
        perms = result["permissions"]
        deny_write = [
            p for p in perms
            if p["mode"] == "deny" and "write" in p["operations"]
        ]
        all_deny_paths = [path for p in deny_write for path in p["paths"]]
        assert any(".gitagent" in p for p in all_deny_paths)
        assert any(".git/" in p for p in all_deny_paths)
