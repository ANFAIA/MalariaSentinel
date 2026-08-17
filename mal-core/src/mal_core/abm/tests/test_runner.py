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
            run_abm(aoi="ghana", days=732)


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
