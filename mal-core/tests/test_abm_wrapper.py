"""Tests for the ABM wrapper."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mal_core.abm.wrapper import CppAbmWrapper
from mal_core.abm.flags import ABM_FLAGS_SCHEMA, AbmFlags


def test_abm_flags_schema_has_keys():
    assert "aoi" in ABM_FLAGS_SCHEMA
    assert "year" in ABM_FLAGS_SCHEMA
    assert "days" in ABM_FLAGS_SCHEMA
    assert "n_rollouts" in ABM_FLAGS_SCHEMA
    assert "seed" in ABM_FLAGS_SCHEMA
    assert "snapshot_every" in ABM_FLAGS_SCHEMA


def test_abm_flags_schema_types():
    assert ABM_FLAGS_SCHEMA["aoi"]["type"] is str
    assert ABM_FLAGS_SCHEMA["year"]["type"] is int
    assert ABM_FLAGS_SCHEMA["days"]["type"] is int


def test_wrapper_resolve_binary_not_found(tmp_path):
    """CppAbmWrapper raises FileNotFoundError when binary is missing."""
    fake_pkg = tmp_path / "fake_pkg"
    fake_pkg.mkdir()
    with pytest.raises(FileNotFoundError, match="ABM binary not found"):
        CppAbmWrapper(binary_path=None)
        # This will fail because we're not in the real package dir
        # but that's expected


def test_wrapper_run_builds_command():
    """Test that run() builds the correct CLI command."""
    mock_binary = Path("/fake/binary")
    wrapper = CppAbmWrapper.__new__(CppAbmWrapper)
    wrapper.binary = mock_binary
    wrapper._flags_schema = {"aoi": {"type": str}, "days": {"type": int}}

    with patch("mal_core.abm.wrapper.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            stdout="ok", stderr="", returncode=0
        )
        result = wrapper.run(aoi="ghana", days=30)

    assert result["stdout"] == "ok"
    assert result["returncode"] == 0
    call_args = mock_run.call_args[0][0]
    assert str(mock_binary) in call_args
    assert "--aoi" in call_args
    assert "ghana" in call_args
    assert "--days" in call_args
    assert "30" in call_args
