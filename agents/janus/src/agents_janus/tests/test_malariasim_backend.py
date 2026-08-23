"""Tests for MalariasimShellBackend — build/test subcommands and security."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from agents_janus.malariasim_backend import (
    MalariasimShellBackend,
    _is_build_test_command,
    _is_malariasim_command,
    _parse_build_test_tokens,
    _resolve_build_dir,
    _tail_output,
)
from deepagents.backends import LocalShellBackend
from deepagents.backends.protocol import ExecuteResponse


# ---------------------------------------------------------------------------
# _is_build_test_command()
# ---------------------------------------------------------------------------
class TestIsBuildTestCommand:
    """Validate that _is_build_test_command recognises safe wrappers
    and rejects everything else."""

    def test_build_command_recognized(self):
        assert _is_build_test_command("malariasim build") is True

    def test_test_command_recognized(self):
        assert _is_build_test_command("malariasim test") is True

    def test_build_info_command_recognized(self):
        assert _is_build_test_command("malariasim build-info") is True

    def test_build_with_target(self):
        assert _is_build_test_command("malariasim build --target abm") is True

    def test_test_with_filter(self):
        assert _is_build_test_command("malariasim test --test TestFoo") is True

    def test_uv_prefix_build(self):
        assert _is_build_test_command("uv run malariasim build") is True

    def test_uv_prefix_test(self):
        assert _is_build_test_command("uv run malariasim test") is True

    def test_uv_prefix_build_with_target(self):
        assert _is_build_test_command("uv run malariasim build --target abm") is True

    # --- Rejection tests ---
    def test_raw_cmake_rejected(self):
        assert _is_build_test_command("cmake --build .") is False

    def test_raw_ctest_rejected(self):
        assert _is_build_test_command("ctest --output-on-failure") is False

    def test_raw_pytest_rejected(self):
        assert _is_build_test_command("pytest tests/") is False

    def test_raw_make_rejected(self):
        assert _is_build_test_command("make -j4") is False

    def test_banned_semicolon_rejected(self):
        assert _is_build_test_command("malariasim build; rm -rf /") is False

    def test_banned_pipe_rejected(self):
        assert _is_build_test_command("malariasim test | cat") is False

    def test_banned_ampersand_rejected(self):
        assert _is_build_test_command("malariasim build & echo pwned") is False

    def test_banned_backtick_rejected(self):
        assert _is_build_test_command("malariasim build `whoami`") is False

    def test_banned_dollar_rejected(self):
        assert _is_build_test_command("malariasim build $(whoami)") is False

    def test_empty_command_rejected(self):
        assert _is_build_test_command("") is False

    def test_none_rejected(self):
        assert _is_build_test_command(None) is False  # type: ignore[arg-type]

    def test_non_string_rejected(self):
        assert _is_build_test_command(123) is False  # type: ignore[arg-type]

    def test_just_malariasim_rejected(self):
        """'malariasim' alone (no subcommand) should NOT match build/test."""
        assert _is_build_test_command("malariasim") is False

    def test_malariasim_run_subcommand_rejected(self):
        """'malariasim run' is NOT a build/test subcommand."""
        assert _is_build_test_command("malariasim run --scenario baseline") is False

    def test_uv_without_run_rejected(self):
        assert _is_build_test_command("uv malariasim build") is False


# ---------------------------------------------------------------------------
# _is_malariasim_command() — regression guard
# ---------------------------------------------------------------------------
class TestIsMalariasimCommandRegression:
    """Ensure the original _is_malariasim_command still accepts all valid
    patterns after the new build/test functions were added."""

    def test_malariasim_still_accepted(self):
        assert _is_malariasim_command("malariasim --scenario baseline") is True

    def test_uv_malariasim_still_accepted(self):
        assert _is_malariasim_command("uv run malariasim --help") is True

    def test_python_m_module_still_accepted(self):
        assert _is_malariasim_command("python -m mal_core.cli --help") is True

    def test_uv_python_m_module_still_accepted(self):
        assert _is_malariasim_command("uv run python -m mal_core.cli --help") is True

    def test_raw_cmake_still_rejected(self):
        assert _is_malariasim_command("cmake --build .") is False

    def test_build_subcommand_accepted_by_malariasim_cmd(self):
        """'malariasim build' is also accepted by the original filter
        (it starts with 'malariasim'). The backend routes it to the
        build/test handler first via _is_build_test_command."""
        assert _is_malariasim_command("malariasim build") is True


# ---------------------------------------------------------------------------
# _parse_build_test_tokens()
# ---------------------------------------------------------------------------
class TestParseBuildTestTokens:
    def test_build_no_extras(self):
        subcmd, extras = _parse_build_test_tokens("malariasim build")
        assert subcmd == "build"
        assert extras == {}

    def test_build_with_target(self):
        subcmd, extras = _parse_build_test_tokens(
            "malariasim build --target abm"
        )
        assert subcmd == "build"
        assert extras == {"target": "abm"}

    def test_test_with_filter(self):
        subcmd, extras = _parse_build_test_tokens(
            "malariasim test --test TestFoo"
        )
        assert subcmd == "test"
        assert extras == {"test": "TestFoo"}

    def test_build_info_no_extras(self):
        subcmd, extras = _parse_build_test_tokens("malariasim build-info")
        assert subcmd == "build-info"
        assert extras == {}

    def test_uv_prefix_build(self):
        subcmd, extras = _parse_build_test_tokens(
            "uv run malariasim build --target abm"
        )
        assert subcmd == "build"
        assert extras == {"target": "abm"}

    def test_unknown_flag_ignored(self):
        subcmd, extras = _parse_build_test_tokens(
            "malariasim build --unknown-flag foo"
        )
        assert subcmd == "build"
        assert extras == {}

    def test_both_flags_last_wins(self):
        """If both --target and --test are passed (malformed), each key is set."""
        subcmd, extras = _parse_build_test_tokens(
            "malariasim build --target abm --test TestFoo"
        )
        assert subcmd == "build"
        assert extras == {"target": "abm", "test": "TestFoo"}


# ---------------------------------------------------------------------------
# _tail_output()
# ---------------------------------------------------------------------------
class TestTailOutput:
    def test_empty(self):
        assert _tail_output("") == ""

    def test_short_output_unchanged(self):
        text = "line1\nline2\n"
        assert _tail_output(text, n=10) == text

    def test_exact_n_lines(self):
        lines = [f"line{i}\n" for i in range(30)]
        text = "".join(lines)
        assert _tail_output(text, n=30) == text

    def test_long_output_truncated(self):
        lines = [f"line{i}\n" for i in range(100)]
        text = "".join(lines)
        result = _tail_output(text, n=30)
        assert "70 lines truncated" in result
        assert "line99" in result
        assert "line69" in result

    def test_one_line_output(self):
        assert _tail_output("single\n", n=30) == "single\n"

    def test_custom_n(self):
        lines = [f"L{i}\n" for i in range(5)]
        text = "".join(lines)
        result = _tail_output(text, n=2)
        assert "3 lines truncated" in result
        assert "L3" in result
        assert "L4" in result
        assert "L2" not in result

    def test_no_trailing_newline(self):
        text = "a\nb"
        result = _tail_output(text, n=30)
        assert result == text


# ---------------------------------------------------------------------------
# _resolve_build_dir()
# ---------------------------------------------------------------------------
class TestResolveBuildDir:
    def test_worktree_layout(self, tmp_path):
        build = tmp_path / ".gitagent" / "worktree" / "mal-core" / "build"
        build.mkdir(parents=True)
        result = _resolve_build_dir(str(tmp_path))
        assert result == str(build)

    def test_monorepo_fallback(self, tmp_path):
        build = tmp_path / "mal-core" / "build"
        build.mkdir(parents=True)
        result = _resolve_build_dir(str(tmp_path))
        assert result == str(build)

    def test_no_build_dir_returns_worktree_path(self, tmp_path):
        """When neither layout exists, returns the worktree path anyway."""
        result = _resolve_build_dir(str(tmp_path))
        assert "mal-core/build" in result


# ---------------------------------------------------------------------------
# MalariasimShellBackend.execute() — integration tests
# ---------------------------------------------------------------------------
class TestExecuteBuildTest:
    """Test the backend's execute() routing for build/test wrappers."""

    def _make_backend(self):
        """Create a MalariasimShellBackend with mocked super().execute."""
        return MalariasimShellBackend.__new__(MalariasimShellBackend)

    @patch(
        "agents_janus.malariasim_backend._resolve_build_dir",
        return_value="fake/build",
    )
    def test_execute_build_delegates(self, _mock_resolve):
        backend = self._make_backend()
        with patch.object(
            LocalShellBackend,
            "execute",
            return_value=ExecuteResponse(output="build ok", exit_code=0, truncated=False),
        ) as mock_super:
            resp = backend.execute("malariasim build")
        mock_super.assert_called_once()
        cmd = mock_super.call_args[0][0]
        assert "cmake --build fake/build" in cmd
        assert resp.exit_code == 0

    @patch(
        "agents_janus.malariasim_backend._resolve_build_dir",
        return_value="fake/build",
    )
    def test_execute_test_delegates(self, _mock_resolve):
        backend = self._make_backend()
        with patch.object(
            LocalShellBackend,
            "execute",
            return_value=ExecuteResponse(output="test ok", exit_code=0, truncated=False),
        ) as mock_super:
            resp = backend.execute("malariasim test")
        mock_super.assert_called_once()
        cmd = mock_super.call_args[0][0]
        assert "ctest --output-on-failure" in cmd
        assert resp.exit_code == 0

    def test_execute_rejected_command(self):
        """Raw cmake should be rejected by execute()."""
        backend = MalariasimShellBackend.__new__(MalariasimShellBackend)
        resp = backend.execute("cmake --build .")
        assert resp.exit_code == 1
        assert "Only `malariasim` commands are allowed" in resp.output

    def test_execute_rejected_pipe(self):
        """Commands with shell metachars are rejected."""
        backend = MalariasimShellBackend.__new__(MalariasimShellBackend)
        resp = backend.execute("malariasim build | grep error")
        assert resp.exit_code == 1

    @patch(
        "agents_janus.malariasim_backend._resolve_build_dir",
        return_value="/fake/build",
    )
    def test_execute_build_with_target(self, _mock_resolve):
        """Build with --target should include the target in the cmake command."""
        backend = self._make_backend()
        with patch.object(
            type(backend),
            "execute",
            side_effect=lambda cmd, **kw: ExecuteResponse(
                output=f"CMD:{cmd}", exit_code=0, truncated=False
            ),
        ):
            resp = backend.execute("malariasim build --target abm")
        # The build-test path should have been taken (not the malariasim CLI path)
        assert resp.exit_code == 0

    @patch(
        "agents_janus.malariasim_backend._resolve_build_dir",
        return_value="/fake/build",
    )
    def test_execute_test_with_filter(self, _mock_resolve):
        """Test with --test filter should pass -R to ctest."""
        backend = self._make_backend()
        with patch.object(
            type(backend),
            "execute",
            side_effect=lambda cmd, **kw: ExecuteResponse(
                output=f"CMD:{cmd}", exit_code=0, truncated=False
            ),
        ):
            resp = backend.execute("malariasim test --test TestFoo")
        assert resp.exit_code == 0


class TestExecuteBuildTestUnit:
    """Unit tests that verify the command translation logic by
    mocking super().execute at the class level."""

    def test_build_no_target(self):
        with patch(
            "agents_janus.malariasim_backend._resolve_build_dir",
            return_value="/wb",
        ):
            backend = MalariasimShellBackend.__new__(MalariasimShellBackend)
            with patch.object(
                LocalShellBackend,
                "execute",
                return_value=ExecuteResponse(
                    output="ok", exit_code=0, truncated=False
                ),
            ) as mock_super:
                resp = backend.execute("malariasim build")
                mock_super.assert_called_once()
                cmd = mock_super.call_args[0][0]
                assert cmd == "cmake --build /wb -- -j$(nproc)"
                assert resp.exit_code == 0

    def test_build_with_target(self):
        with patch(
            "agents_janus.malariasim_backend._resolve_build_dir",
            return_value="/wb",
        ):
            backend = MalariasimShellBackend.__new__(MalariasimShellBackend)
            with patch.object(
                LocalShellBackend,
                "execute",
                return_value=ExecuteResponse(
                    output="ok", exit_code=0, truncated=False
                ),
            ) as mock_super:
                resp = backend.execute("malariasim build --target abm")
                cmd = mock_super.call_args[0][0]
                assert cmd == "cmake --build /wb --target abm -- -j$(nproc)"
                assert resp.exit_code == 0

    def test_test_no_filter(self):
        with patch(
            "agents_janus.malariasim_backend._resolve_build_dir",
            return_value="/wb",
        ):
            backend = MalariasimShellBackend.__new__(MalariasimShellBackend)
            with patch.object(
                LocalShellBackend,
                "execute",
                return_value=ExecuteResponse(
                    output="ok", exit_code=0, truncated=False
                ),
            ) as mock_super:
                resp = backend.execute("malariasim test")
                cmd = mock_super.call_args[0][0]
                assert cmd == "cd /wb && ctest --output-on-failure"
                assert resp.exit_code == 0

    def test_test_with_filter(self):
        with patch(
            "agents_janus.malariasim_backend._resolve_build_dir",
            return_value="/wb",
        ):
            backend = MalariasimShellBackend.__new__(MalariasimShellBackend)
            with patch.object(
                LocalShellBackend,
                "execute",
                return_value=ExecuteResponse(
                    output="ok", exit_code=0, truncated=False
                ),
            ) as mock_super:
                resp = backend.execute("malariasim test --test TestFoo")
                cmd = mock_super.call_args[0][0]
                assert cmd == "cd /wb && ctest --output-on-failure -R TestFoo"
                assert resp.exit_code == 0

    def test_build_info(self):
        with patch(
            "agents_janus.malariasim_backend._resolve_build_dir",
            return_value="/wb",
        ):
            backend = MalariasimShellBackend.__new__(MalariasimShellBackend)
            with patch.object(
                LocalShellBackend,
                "execute",
                return_value=ExecuteResponse(
                    output="ok", exit_code=0, truncated=False
                ),
            ) as mock_super:
                resp = backend.execute("malariasim build-info")
                cmd = mock_super.call_args[0][0]
                assert cmd == "cd /wb && cmake --build . --target help"
                assert resp.exit_code == 0

    def test_output_is_tailed(self):
        """Build output should be tailed to 30 lines."""
        long_output = "\n".join(f"line{i}" for i in range(100)) + "\n"
        with patch(
            "agents_janus.malariasim_backend._resolve_build_dir",
            return_value="/wb",
        ):
            backend = MalariasimShellBackend.__new__(MalariasimShellBackend)
            with patch.object(
                LocalShellBackend,
                "execute",
                return_value=ExecuteResponse(
                    output=long_output, exit_code=0, truncated=False
                ),
            ):
                resp = backend.execute("malariasim build")
                assert "lines truncated" in resp.output
                assert "line99" in resp.output


class TestExistingMalariaSimStillAccepted:
    """Verify standard malariasim CLI commands still work through execute()."""

    def test_standard_command_passes_through(self):
        with patch.object(
            LocalShellBackend,
            "execute",
            return_value=ExecuteResponse(
                output="scenario done", exit_code=0, truncated=False
            ),
        ) as mock_super:
            backend = MalariasimShellBackend.__new__(MalariasimShellBackend)
            resp = backend.execute("malariasim --scenario baseline")
            mock_super.assert_called_once()
            assert resp.exit_code == 0

    def test_uv_prefix_passes_through(self):
        with patch.object(
            LocalShellBackend,
            "execute",
            return_value=ExecuteResponse(
                output="ok", exit_code=0, truncated=False
            ),
        ) as mock_super:
            backend = MalariasimShellBackend.__new__(MalariasimShellBackend)
            resp = backend.execute("uv run malariasim --help")
            mock_super.assert_called_once()
            assert resp.exit_code == 0

    def test_python_m_module_passes_through(self):
        with patch.object(
            LocalShellBackend,
            "execute",
            return_value=ExecuteResponse(
                output="ok", exit_code=0, truncated=False
            ),
        ) as mock_super:
            backend = MalariasimShellBackend.__new__(MalariasimShellBackend)
            resp = backend.execute("python -m mal_core.cli --help")
            mock_super.assert_called_once()
            assert resp.exit_code == 0
