"""Tests for permission configuration — secrets, data, gitagent protection."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest


class TestWorkerPermissions:
    """Test that worker permissions are correctly configured via create_orchestrator."""

    def _create_orchestrator_with_mock(self):
        """Helper to create orchestrator with mocked deepagents."""
        mock_backend_mod = MagicMock()
        mock_backend_class = MagicMock()
        mock_backend_mod.FilesystemBackend = mock_backend_class

        mock_deepagents = MagicMock()
        mock_deepagents.create_deep_agent = MagicMock()
        mock_deepagents.backends = mock_backend_mod
        mock_deepagents.FilesystemPermission = MagicMock

        originals = {
            "deepagents": sys.modules.get("deepagents"),
            "deepagents.backends": sys.modules.get("deepagents.backends"),
        }
        sys.modules["deepagents"] = mock_deepagents
        sys.modules["deepagents.backends"] = mock_backend_mod

        try:
            import importlib
            import agents.janus.agent as agent_mod
            importlib.reload(agent_mod)

            with patch.object(agent_mod, "_resolve_provider") as mock_resolve:
                mock_resolve.return_value = MagicMock()
                agent_mod.create_orchestrator(provider="openrouter", model="test", thread_id="test")

            # Get the worker definitions that were passed to create_deep_agent
            call_kwargs = mock_deepagents.create_deep_agent.call_args
            worker_defs = call_kwargs.kwargs.get("subagents", call_kwargs.args[2] if len(call_kwargs.args) > 2 else [])
            return worker_defs[0] if worker_defs else None
        finally:
            for key, val in originals.items():
                if val is not None:
                    sys.modules[key] = val
                else:
                    sys.modules.pop(key, None)
            importlib.reload(agent_mod)

    def test_deny_secrets(self):
        result = self._create_orchestrator_with_mock()
        assert result is not None, "No worker definitions found"
        perms = result.get("permissions", [])
        deny_perms = [p for p in perms if hasattr(p, 'mode') and p.mode == "deny"]
        all_deny_paths = [path for p in deny_perms for path in p.paths]
        assert any("secret" in p for p in all_deny_paths)
        assert any(".env" in p for p in all_deny_paths)

    def test_deny_data_write(self):
        result = self._create_orchestrator_with_mock()
        assert result is not None
        perms = result.get("permissions", [])
        deny_write = [
            p for p in perms
            if hasattr(p, 'mode') and p.mode == "deny" and "write" in p.operations
        ]
        all_deny_paths = [path for p in deny_write for path in p.paths]
        assert any("/data/**" in p for p in all_deny_paths)

    def test_deny_gitagent_write(self):
        result = self._create_orchestrator_with_mock()
        assert result is not None
        perms = result.get("permissions", [])

        # .git/ must be denied (git internals protection)
        deny_write = [
            p for p in perms
            if hasattr(p, 'mode') and p.mode == "deny" and "write" in p.operations
        ]
        all_deny_paths = [path for p in deny_write for path in p.paths]
        assert any(".git/" in p for p in all_deny_paths), ".git/ should be in deny paths"

        # .gitagent worktree paths must be explicitly ALLOWED (overrides catch-all deny)
        allow_write = [
            p for p in perms
            if hasattr(p, 'mode') and p.mode == "allow" and "write" in p.operations
        ]
        all_allow_paths = [path for p in allow_write for path in p.paths]
        assert any(".gitagent" in p and "worktree" in p for p in all_allow_paths), \
            ".gitagent worktree paths should be in allow paths"
