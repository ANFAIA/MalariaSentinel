"""Tests for the ABM Python runner / wrapper pipeline.

These tests verify the *flag plumbing* and *chunking logic* without
requiring a compiled C++ binary or real geospatial data.  They mock
the subprocess call so the tests run in any CI environment.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ── Chunking helpers ──────────────────────────────────────────────

class TestChunkingLogic:
    """Verify that run_abm_full_period splits months correctly."""

    def test_single_month_no_split(self):
        """A single month (Jan 2024, 31 days) should produce one chunk."""
        from mal_core.abm.runner import _month_days, _next_month

        assert _month_days(2024, 1) == 31
        assert _next_month(2024, 1) == (2024, 2)
        assert _next_month(2024, 12) == (2025, 1)

    def test_leap_year_feb(self):
        """2024 is a leap year; Feb has 29 days."""
        from mal_core.abm.runner import _month_days

        assert _month_days(2024, 2) == 29
        assert _month_days(2025, 2) == 28

    def test_full_year_chunk_count(self):
        """2024 alone (leap year) = 366 days → 1 chunk at max_chunk_days=730."""
        from mal_core.abm.runner import run_abm_full_period

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            with patch("mal_core.abm.runner.CppAbmWrapper") as MockWrapper:
                mock_instance = MockWrapper.return_value
                mock_instance.run.return_value = {
                    "stdout": "", "stderr": "", "returncode": 0,
                }
                result = run_abm_full_period(
                    aoi="ghana", year=2024, month=1,
                    end_year=2024, end_month=12,
                    output_dir=out, max_chunk_days=730,
                )
                # 2024 has 366 days < 730, so exactly 1 chunk
                assert result["n_chunks"] == 1
                assert result["total_days"] == 366
                assert result["success"] is True

    def test_two_year_split(self):
        """2024-2025 = 731 days → 2 chunks at max_chunk_days=730."""
        from mal_core.abm.runner import run_abm_full_period

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            with patch("mal_core.abm.runner.CppAbmWrapper") as MockWrapper:
                mock_instance = MockWrapper.return_value
                mock_instance.run.return_value = {
                    "stdout": "", "stderr": "", "returncode": 0,
                }
                result = run_abm_full_period(
                    aoi="ghana", year=2024, month=1,
                    end_year=2025, end_month=12,
                    output_dir=out, max_chunk_days=730,
                )
                # 731 days total → 730 + 1
                assert result["n_chunks"] == 2
                assert result["total_days"] == 731
                assert result["success"] is True

    def test_small_chunk_splits_month(self):
        """A month of 31 days with max_chunk_days=10 → 4 chunks (10+10+10+1)."""
        from mal_core.abm.runner import run_abm_full_period

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            with patch("mal_core.abm.runner.CppAbmWrapper") as MockWrapper:
                mock_instance = MockWrapper.return_value
                mock_instance.run.return_value = {
                    "stdout": "", "stderr": "", "returncode": 0,
                }
                result = run_abm_full_period(
                    aoi="ghana", year=2024, month=1,
                    end_year=2024, end_month=1,
                    output_dir=out, max_chunk_days=10,
                )
                assert result["n_chunks"] == 4
                assert result["total_days"] == 31

    def test_chunk_failure_marks_overall_failure(self):
        """If one chunk fails (non-zero returncode), overall success=False."""
        from mal_core.abm.runner import run_abm_full_period

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            with patch("mal_core.abm.runner.CppAbmWrapper") as MockWrapper:
                mock_instance = MockWrapper.return_value
                # First chunk succeeds, second fails
                mock_instance.run.side_effect = [
                    {"stdout": "", "stderr": "", "returncode": 0},
                    {"stdout": "", "stderr": "FATAL", "returncode": 1},
                ]
                result = run_abm_full_period(
                    aoi="ghana", year=2024, month=1,
                    end_year=2025, end_month=12,
                    output_dir=out, max_chunk_days=730,
                )
                assert result["success"] is False
                assert result["n_chunks"] == 2


# ── Flag plumbing ─────────────────────────────────────────────────

class TestFlagPlumbing:
    """Verify that flags reach the C++ binary correctly."""

    def test_run_abm_passes_snapshot_every(self):
        """run_abm() should include snapshot_every in flags."""
        from mal_core.abm.runner import run_abm

        with patch("mal_core.abm.runner.CppAbmWrapper") as MockWrapper:
            mock_instance = MockWrapper.return_value
            mock_instance.run.return_value = {
                "stdout": "", "stderr": "", "returncode": 0,
            }
            run_abm(
                aoi="ghana", year=2024, month=1,
                days=7, seed=1, snapshot_every=1,
            )
            # Check that snapshot_every=1 was in the flags
            call_kwargs = mock_instance.run.call_args[1]
            assert call_kwargs.get("snapshot_every") == 1

    def test_run_abm_passes_timeout(self):
        """run_abm() timeout should reach subprocess via wrapper."""
        from mal_core.abm.runner import run_abm

        with patch("mal_core.abm.runner.CppAbmWrapper") as MockWrapper:
            mock_instance = MockWrapper.return_value
            mock_instance.run.return_value = {
                "stdout": "", "stderr": "", "returncode": 0,
            }
            run_abm(
                aoi="ghana", year=2024, month=1,
                days=7, seed=1, timeout=1200,
            )
            call_kwargs = mock_instance.run.call_args[1]
            assert call_kwargs.get("_timeout") == 1200

    def test_run_abm_output_dir_created(self):
        """Output directory should be created if it doesn't exist."""
        from mal_core.abm.runner import run_abm

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "new_subdir"
            assert not out.exists()
            with patch("mal_core.abm.runner.CppAbmWrapper") as MockWrapper:
                mock_instance = MockWrapper.return_value
                mock_instance.run.return_value = {
                    "stdout": "", "stderr": "", "returncode": 0,
                }
                run_abm(
                    aoi="ghana", year=2024, month=1,
                    days=7, output_dir=out,
                )
                assert out.exists()

    def test_run_abm_rejects_bad_days(self):
        """days out of range should raise ValueError."""
        from mal_core.abm.runner import run_abm

        with pytest.raises(ValueError, match="days must be"):
            run_abm(aoi="ghana", days=0)
        with pytest.raises(ValueError, match="days must be"):
            run_abm(aoi="ghana", days=731)


# ── Wrapper flag formatting ───────────────────────────────────────

class TestCppAbmWrapper:
    """Test the flag-to-CLI conversion logic."""

    def test_bool_flag_true(self):
        """Boolean True should produce --flag (no value)."""
        from mal_core.abm.wrapper import CppAbmWrapper

        wrapper = CppAbmWrapper.__new__(CppAbmWrapper)
        wrapper._flags_schema = {}
        # Mock the binary path to avoid file-not-found
        wrapper.binary = Path("/dev/null")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout="", stderr=""
            )
            # We need to catch the error from /dev/null not being a real binary
            try:
                wrapper.run(aoi="ghana", debug=True, days=7)
            except Exception:
                pass

            # Check the command that was built
            cmd = mock_run.call_args[0][0]
            assert "--debug" in cmd
            assert "--days" in cmd
            assert "7" in cmd

    def test_snapshot_every_in_flags(self):
        """snapshot_every should appear as --snapshot-every in CLI."""
        from mal_core.abm.wrapper import CppAbmWrapper

        wrapper = CppAbmWrapper.__new__(CppAbmWrapper)
        wrapper._flags_schema = {}
        wrapper.binary = Path("/dev/null")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout="", stderr=""
            )
            try:
                wrapper.run(aoi="ghana", snapshot_every=1, days=7)
            except Exception:
                pass

            cmd = mock_run.call_args[0][0]
            assert "--snapshot-every" in cmd
            idx = cmd.index("--snapshot-every")
            assert cmd[idx + 1] == "1"


# ── run_abm_from_manifest snapshot_every ─────────────────────────

class TestManifestWrapper:
    """Test that run_abm_from_manifest includes snapshot_every."""

    def test_snapshot_every_default_in_flags(self):
        """Default snapshot_every=1 should be in the flags dict."""
        from mal_core.abm.wrapper import CppAbmWrapper

        with patch("mal_core.abm.wrapper.CppAbmWrapper") as MockWrapper:
            mock_instance = MockWrapper.return_value
            mock_instance.run.return_value = {
                "stdout": "", "stderr": "", "returncode": 0,
            }
            # Mock the manifest functions
            with patch("mal_core.download.manifest.validate_completeness", return_value=[]):
                with patch("mal_core.download.manifest.read_manifest") as mock_read:
                    mock_read.return_value = {
                        "datasets": {
                            "env": {"files": {"2024": "env.tif"}},
                            "habitat": {"files": {"2024": "hab.gpkg"}},
                        }
                    }
                    with tempfile.TemporaryDirectory() as tmp:
                        data_dir = Path(tmp) / "data" / "ghana"
                        data_dir.mkdir(parents=True)
                        (data_dir / "env.tif").touch()
                        (data_dir / "hab.gpkg").touch()
                        out_dir = Path(tmp) / "runs" / "ghana"

                        # Patch Path("data") to use tmp
                        with patch("mal_core.abm.wrapper.Path") as MockPath:
                            # Make Path("data") return the tmp data dir
                            original_path = Path

                            def path_factory(*args, **kwargs):
                                if args and args[0] == "data":
                                    return original_path(tmp) / "data"
                                elif args and args[0] == "runs":
                                    return original_path(tmp) / "runs"
                                return original_path(*args, **kwargs)

                            MockPath.side_effect = path_factory
                            MockPath.__class__ = type(original_path)

                            from mal_core.abm.wrapper import run_abm_from_manifest
                            result = run_abm_from_manifest(
                                aoi="ghana", year=2024, month=1,
                                days=7, output_dir=out_dir,
                            )
                            # Check snapshot_every was in the call
                            call_kwargs = mock_instance.run.call_args[1]
                            assert call_kwargs.get("snapshot_every") == 1
