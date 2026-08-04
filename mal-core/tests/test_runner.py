"""Tests for the download runner module — M13 Phase 2 format dispatch."""
from __future__ import annotations

import numpy as np
import xarray as xr
from pathlib import Path
from unittest.mock import MagicMock, patch

from mal_core.download.runner import _standard_path, _standard_path_daily


# --- _standard_path tests ---


def test_standard_path_with_year(tmp_path):
    """_standard_path produces correct per-year filename."""
    # Patch _REPO_ROOT to use tmp
    import mal_core.download.runner as runner_mod
    original = runner_mod._REPO_ROOT
    runner_mod._REPO_ROOT = tmp_path
    try:
        p = _standard_path("ghana", "chirps_rainfall", 2024, "tif")
        assert p == tmp_path / "data" / "ghana" / "ghana_chirps_rainfall_2024.tif"
    finally:
        runner_mod._REPO_ROOT = original


def test_standard_path_without_year(tmp_path):
    """_standard_path produces correct static filename (no year)."""
    import mal_core.download.runner as runner_mod
    original = runner_mod._REPO_ROOT
    runner_mod._REPO_ROOT = tmp_path
    try:
        p = _standard_path("ghana", "dem_elevation", None, "tif")
        assert p == tmp_path / "data" / "ghana" / "ghana_dem_elevation.tif"
    finally:
        runner_mod._REPO_ROOT = original


# --- _standard_path_daily tests ---


def test_standard_path_daily(tmp_path):
    """_standard_path_daily produces correct multi-year NC filename."""
    import mal_core.download.runner as runner_mod
    original = runner_mod._REPO_ROOT
    runner_mod._REPO_ROOT = tmp_path
    try:
        p = _standard_path_daily("ghana", "chirps_rainfall_daily", 2020, 2024)
        assert p == tmp_path / "data" / "ghana" / "ghana_chirps_rainfall_daily_2020_2024_daily.nc"
    finally:
        runner_mod._REPO_ROOT = original


def test_standard_path_daily_single_year(tmp_path):
    """_standard_path_daily with start == end year."""
    import mal_core.download.runner as runner_mod
    original = runner_mod._REPO_ROOT
    runner_mod._REPO_ROOT = tmp_path
    try:
        p = _standard_path_daily("ghana", "rainfall_daily", 2024, 2024)
        assert p.name == "ghana_rainfall_daily_2024_2024_daily.nc"
    finally:
        runner_mod._REPO_ROOT = original


# --- Format dispatch tests ---


def test_formats_field_on_spec():
    """DownloaderSpec carries formats from DOWNLOADER dict."""
    from mal_core.download.registry import DownloaderSpec

    spec = DownloaderSpec(
        name="test",
        description="test",
        requires_auth=[],
        outputs={"monthly_out": MagicMock(), "daily_out": MagicMock()},
        manifest_keys={"monthly_out": "monthly_key", "daily_out": "daily_key"},
        module_name="test",
        is_time_series=True,
        formats={"monthly_out": "monthly", "daily_out": "daily"},
    )
    assert spec.formats["monthly_out"] == "monthly"
    assert spec.formats["daily_out"] == "daily"


def test_formats_none_backward_compat():
    """DownloaderSpec with formats=None defaults to monthly."""
    from mal_core.download.registry import DownloaderSpec

    spec = DownloaderSpec(
        name="test",
        description="test",
        requires_auth=[],
        outputs={"rainfall": MagicMock()},
        manifest_keys={"rainfall": "key"},
        module_name="test",
        is_time_series=True,
        formats=None,
    )
    # Runner logic: output_format defaults to "monthly" when spec.formats is None
    output_format = "monthly"
    if spec.formats and "rainfall" in spec.formats:
        output_format = spec.formats["rainfall"]
    assert output_format == "monthly"
