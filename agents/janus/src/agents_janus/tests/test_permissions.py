"""Tests for backend policy hooks — secrets, data, gitagent protection.

FilesystemPermission is no longer passed to deepagents (it is incompatible
with execution-capable backends). The deny rules now live in
MalariasimShellBackend as backend policy hooks:
- execute(): only `malariasim` commands
- read(): denies secrets/.env
- write()/edit(): only under the gawt worktree
"""
from __future__ import annotations

import pytest


def _output(result) -> str:
    return getattr(result, "output", "")


def _rejected(result) -> bool:
    return "Only `malariasim` commands" in _output(result)


class TestMalariasimShellBackendExecute:
    @pytest.fixture()
    def backend(self):
        from agents_janus.malariasim_backend import MalariasimShellBackend
        return MalariasimShellBackend(root_dir="/tmp", virtual_mode=True, inherit_env=True)

    def test_allows_malariasim(self, backend):
        # malariasim may not be on PATH; what matters is the command is NOT
        # rejected by the policy hook (it reaches the shell).
        result = backend.execute("malariasim --help")
        assert not _rejected(result)

    def test_allows_uv_run_malariasim(self, backend):
        result = backend.execute("uv run malariasim --help")
        assert not _rejected(result)

    def test_rejects_non_malariasim(self, backend):
        result = backend.execute("ls -la")
        assert _rejected(result)
        assert result.exit_code == 1

    def test_rejects_shell_escape(self, backend):
        result = backend.execute("malariasim --help; rm -rf /")
        assert _rejected(result)

    def test_rejects_pipe_escape(self, backend):
        result = backend.execute("malariasim --help | sh")
        assert _rejected(result)

    def test_rejects_command_substitution(self, backend):
        result = backend.execute("malariasim --aoi $(whoami)")
        assert _rejected(result)


class TestMalariasimShellBackendFilesystem:
    @pytest.fixture()
    def backend(self, tmp_path):
        from agents_janus.malariasim_backend import MalariasimShellBackend
        return MalariasimShellBackend(root_dir=str(tmp_path), virtual_mode=True)

    def test_read_denies_secrets(self, backend):
        result = backend.read("/.env")
        assert result.error is not None
        assert "denied" in result.error

    def test_read_allows_normal_files(self, backend):
        result = backend.write("/.gitagent/worktree/notes.txt", "hello")
        assert result.error is None
        result = backend.read("/.gitagent/worktree/notes.txt")
        assert result.error is None

    def test_write_denied_outside_worktree(self, backend):
        result = backend.write("/data/ghana/foo.tif", "x")
        assert result.error is not None
        assert "denied" in result.error

    def test_write_denied_git_internals(self, backend):
        result = backend.write("/.git/config", "x")
        assert result.error is not None
        assert "denied" in result.error

    def test_write_allowed_in_worktree(self, backend):
        result = backend.write("/.gitagent/worktree/test.txt", "hi")
        assert result.error is None

    def test_edit_denied_outside_worktree(self, backend):
        result = backend.edit("/data/ghana/foo.tif", "a", "b")
        assert result.error is not None
        assert "denied" in result.error
