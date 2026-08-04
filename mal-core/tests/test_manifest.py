"""Tests for download manifest module — v3.1 schema with period support."""
from __future__ import annotations

import importlib
import json
import pathlib

import pytest

import mal_core.download.manifest as manifest_mod
from mal_core.download.manifest import (
    read_manifest,
    update_dataset,
    validate_completeness,
)


@pytest.fixture
def temp_aoi(tmp_path, monkeypatch):
    """Create a temporary AOI directory and patch DATA_ROOT."""
    aoi_dir = tmp_path / "test-aoi"
    aoi_dir.mkdir()
    monkeypatch.setattr(manifest_mod, "DATA_ROOT", tmp_path)
    return "test-aoi"


@pytest.fixture
def _data_root(tmp_path, monkeypatch):
    """Patch DATA_ROOT and return the patched path for direct file creation."""
    monkeypatch.setattr(manifest_mod, "DATA_ROOT", tmp_path)
    return tmp_path


class TestUpdateDatasetV3:
    """update_dataset stores v3 metadata fields."""

    def test_basic_update(self, temp_aoi):
        update_dataset(temp_aoi, "chirps_rainfall", 2024, "test_2024.tif")
        manifest = read_manifest(temp_aoi)
        ds = manifest["datasets"]["chirps_rainfall"]
        assert ds["files"]["2024"] == "test_2024.tif"
        assert ds["type"] == "time-series"

    def test_period_stored(self, temp_aoi):
        update_dataset(
            temp_aoi, "chirps_rainfall_daily", None,
            "test_daily.nc",
            format="nc",
            period={"start": "2024-01-01", "end": "2025-12-31"},
        )
        manifest = read_manifest(temp_aoi)
        ds = manifest["datasets"]["chirps_rainfall_daily"]
        assert ds["period"] == {"start": "2024-01-01", "end": "2025-12-31"}
        assert ds["format"] == "nc"

    def test_required_for_abm_stored(self, temp_aoi):
        update_dataset(
            temp_aoi, "chirps_rainfall", 2024, "test.tif",
            required_for_abm=True,
        )
        manifest = read_manifest(temp_aoi)
        assert manifest["datasets"]["chirps_rainfall"]["required_for_abm"] is True

    def test_variables_stored(self, temp_aoi):
        update_dataset(
            temp_aoi, "era5_temp", 2024, "test.tif",
            variables=["temperature_2m"],
        )
        manifest = read_manifest(temp_aoi)
        assert manifest["datasets"]["era5_temp"]["variables"] == ["temperature_2m"]

    def test_year_none_uses_dataset_name_as_key(self, temp_aoi):
        update_dataset(temp_aoi, "daily_nc", None, "output.nc")
        manifest = read_manifest(temp_aoi)
        assert manifest["datasets"]["daily_nc"]["files"]["daily_nc"] == "output.nc"


class TestValidateCompleteness:
    """validate_completeness checks period coverage for daily NC entries."""

    def test_empty_manifest_returns_no_missing(self, temp_aoi):
        missing = validate_completeness(temp_aoi)
        assert missing == []

    def test_missing_file_detected(self, temp_aoi):
        update_dataset(temp_aoi, "test_data", 2024, "missing.tif")
        missing = validate_completeness(temp_aoi)
        assert "missing.tif" in missing

    def test_period_coverage_pass(self, temp_aoi):
        # Create the file so it exists
        (manifest_mod.DATA_ROOT / temp_aoi / "daily.nc").write_text("dummy")
        update_dataset(
            temp_aoi, "chirps_daily", None, "daily.nc",
            period={"start": "2024-01-01", "end": "2025-12-31"},
        )
        missing = validate_completeness(temp_aoi, years=[2024, 2025])
        # No missing: period covers both years
        period_errors = [m for m in missing if "period" in m]
        assert period_errors == []

    def test_period_coverage_fail(self, temp_aoi):
        (manifest_mod.DATA_ROOT / temp_aoi / "daily.nc").write_text("dummy")
        update_dataset(
            temp_aoi, "chirps_daily", None, "daily.nc",
            period={"start": "2024-01-01", "end": "2024-12-31"},
        )
        missing = validate_completeness(temp_aoi, years=[2024, 2025])
        # 2025 not covered
        period_errors = [m for m in missing if "period" in m and "2025" in m]
        assert len(period_errors) == 1
