"""Tests for the download runner module — M13 Phase 2 format dispatch."""
from __future__ import annotations

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




