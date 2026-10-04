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


class TestResolveDatasetFile:
    """resolve_dataset_file — manifest-first, strict on declared-but-missing."""

    def _with_files(self, tmp_path, files: dict[str, str], datasets: dict) -> pathlib.Path:
        """Create files inside a data-dir and return the dir."""
        for rel in files.values():
            p = tmp_path / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("dummy")
        return tmp_path

    def _mk_manifest(self, datasets: dict) -> dict:
        return {"datasets": datasets}

    def test_no_entry_returns_none(self, tmp_path):
        from mal_core.download.manifest import resolve_dataset_file

        assert resolve_dataset_file(
            "aoi", "host_static", data_dir=tmp_path, manifest={}
        ) is None

    def test_single_file_resolved(self, tmp_path):
        from mal_core.download.manifest import resolve_dataset_file

        data_dir = self._with_files(tmp_path, {}, {
            "host_static": {"files": {"host_static": "a_host_static.nc"}},
        })
        (tmp_path / "a_host_static.nc").write_text("x")
        p = resolve_dataset_file(
            "aoi", "host_static", data_dir=data_dir,
            manifest=self._mk_manifest({
                "host_static": {"files": {"host_static": "a_host_static.nc"}},
            }),
        )
        assert p == tmp_path / "a_host_static.nc"

    def test_declared_but_missing_is_strict(self, tmp_path):
        from mal_core.download.manifest import resolve_dataset_file

        with pytest.raises(FileNotFoundError):
            resolve_dataset_file(
                "aoi", "host_static", data_dir=tmp_path,
                manifest=self._mk_manifest({
                    "host_static": {"files": {"host_static": "ghost.nc"}},
                }),
            )

    def test_strict_false_returns_missing_path(self, tmp_path):
        from mal_core.download.manifest import resolve_dataset_file

        p = resolve_dataset_file(
            "aoi", "host_static", data_dir=tmp_path, strict=False,
            manifest=self._mk_manifest({
                "host_static": {"files": {"host_static": "ghost.nc"}},
            }),
        )
        assert p == tmp_path / "ghost.nc"

    def test_per_year_selection(self, tmp_path):
        from mal_core.download.manifest import resolve_dataset_file

        data_dir = self._with_files(tmp_path, {}, {})
        (tmp_path / "w_2024.tif").write_text("x")
        (tmp_path / "w_2025.tif").write_text("x")
        manifest = self._mk_manifest({
            "era5_water_temp": {"files": {"2024": "w_2024.tif", "2025": "w_2025.tif"}},
        })
        assert resolve_dataset_file("aoi", "era5_water_temp", year=2025, data_dir=data_dir, manifest=manifest) \
            == tmp_path / "w_2025.tif"
        assert resolve_dataset_file("aoi", "era5_water_temp", year=2024, data_dir=data_dir, manifest=manifest) \
            == tmp_path / "w_2024.tif"

    def test_per_year_missing_year_is_strict(self, tmp_path):
        from mal_core.download.manifest import resolve_dataset_file

        manifest = self._mk_manifest({
            "era5_water_temp": {"files": {"2024": "w_2024.tif"}},
        })
        (tmp_path / "w_2024.tif").write_text("x")
        with pytest.raises(FileNotFoundError, match="nothing for 2025"):
            resolve_dataset_file("aoi", "era5_water_temp", year=2025, data_dir=tmp_path, manifest=manifest)

    def test_year_on_non_year_entry_uses_named_file(self, tmp_path):
        from mal_core.download.manifest import resolve_dataset_file

        (tmp_path / "rain.nc").write_text("x")
        manifest = self._mk_manifest({
            "chirps_rainfall_daily": {"files": {"chirps_rainfall_daily": "rain.nc"}},
        })
        assert resolve_dataset_file("aoi", "chirps_rainfall_daily", year=2024, data_dir=tmp_path, manifest=manifest) \
            == tmp_path / "rain.nc"
