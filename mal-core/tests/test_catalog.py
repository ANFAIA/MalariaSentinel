"""Tests for the dataset catalog — identity, resolution, status, migration."""
from __future__ import annotations

import json
import pathlib

import pytest

from mal_core.download.catalog import (
    INGEST_ARTIFACTS,
    Slot,
    catalog_status,
    load_local_manifest,
    register_existing,
    resolve,
    resolve_inputs,
    downloadable_datasets,
)


class TestResolve:
    """resolve() — manifest-first, strict semantics."""

    def test_no_entry_returns_none(self, tmp_path):
        assert resolve("ghana", "host_static", data_dir=tmp_path) is None

    def test_entry_resolves(self, tmp_path):
        (tmp_path / "hs.nc").write_text("x")
        (tmp_path / "manifest.json").write_text(json.dumps({
            "datasets": {"host_static": {"files": {"host_static": "hs.nc"}}},
        }))
        assert resolve("ghana", "host_static", data_dir=tmp_path) \
            == tmp_path / "hs.nc"

    def test_declared_but_missing_raises(self, tmp_path):
        (tmp_path / "manifest.json").write_text(json.dumps({
            "datasets": {"host_static": {"files": {"host_static": "ghost.nc"}}},
        }))
        with pytest.raises(FileNotFoundError, match="missing on disk"):
            resolve("ghana", "host_static", data_dir=tmp_path)


class TestResolveInputs:
    """resolve_inputs() — the consumer declaration API."""

    def test_required_missing_raises_with_hint(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="malariasim download"):
            resolve_inputs("ghana", {"rain": Slot("chirps_rainfall_daily")}, data_dir=tmp_path)

    def test_optional_missing_returns_none(self, tmp_path):
        out = resolve_inputs("ghana", {"coast": Slot("coastline_land_mask", required=False)}, data_dir=tmp_path)
        assert out == {"coast": None}

    def test_explicit_wins_and_validated(self, tmp_path):
        gone = tmp_path / "gone.tif"  # does NOT exist
        with pytest.raises(FileNotFoundError, match="explicit"):
            resolve_inputs(
                "ghana", {"coast": Slot("coastline_land_mask", required=False)},
                data_dir=tmp_path, explicit={"coast": gone},
            )

    def test_per_year_single_entry_covers_years(self, tmp_path):
        # Single-file era5 entry (tests register one year only): usable
        # for every requested year — the pre-manifest fallback semantics,
        # expressed via the manifest.
        (tmp_path / "wt_2024.tif").write_text("x")
        (tmp_path / "manifest.json").write_text(json.dumps({
            "datasets": {"era5_water_temp": {"files": {"era5_water_temp": "wt_2024.tif"}}},
        }))
        out = resolve_inputs(
            "ghana", {"wt": Slot("era5_water_temp", per_year=True)},
            data_dir=tmp_path, years=[2024, 2025],
        )
        assert out["wt"] == tmp_path / "wt_2024.tif"

    def test_per_year_year_keyed_missing_year_raises(self, tmp_path):
        (tmp_path / "wt_2024.tif").write_text("x")
        (tmp_path / "manifest.json").write_text(json.dumps({
            "datasets": {"era5_water_temp": {"files": {"2024": "wt_2024.tif"}}},
        }))
        with pytest.raises(FileNotFoundError, match="per-year"):
            resolve_inputs(
                "ghana", {"wt": Slot("era5_water_temp", per_year=True)},
                data_dir=tmp_path, years=[2025],
            )

    def test_per_year_year_keyed_resolves_by_year(self, tmp_path):
        (tmp_path / "wt_2024.tif").write_text("x")
        (tmp_path / "wt_2025.tif").write_text("x")
        (tmp_path / "manifest.json").write_text(json.dumps({
            "datasets": {"era5_water_temp": {"files": {"2024": "wt_2024.tif", "2025": "wt_2025.tif"}}},
        }))
        out = resolve_inputs(
            "ghana", {"wt": Slot("era5_water_temp", per_year=True)},
            data_dir=tmp_path, years=[2024, 2025],
        )
        assert out["wt"] == {2024: tmp_path / "wt_2024.tif", 2025: tmp_path / "wt_2025.tif"}

    def test_per_year_no_entry_optional(self, tmp_path):
        out = resolve_inputs(
            "ghana", {"ndvi": Slot("modis_ndvi", required=False, per_year=True)},
            data_dir=tmp_path,
        )
        assert out["ndvi"] is None


class TestCatalogStatus:
    """catalog_status() — loaders + artifacts vs manifest vs disk."""

    def test_lists_registry_and_artifacts(self, tmp_path):
        (tmp_path / "ghana").mkdir()
        rows = catalog_status("ghana", data_root=tmp_path)
        keys = {r["key"] for r in rows}
        # Registry-derived (loader keys present no matter the manifest)
        assert "chirps_rainfall_daily" in keys
        assert "jrc_water" in keys
        assert "smap_salinity" in keys
        # Ingest artifacts derived from INGEST_ARTIFACTS
        assert {"env", "habitat", "host_static", "mobility_day"} <= keys
        kinds = {r["key"]: r["kind"] for r in rows}
        assert kinds["env"] == "artifact"
        assert kinds["jrc_water"] == "download"
        # All registry downloadables covered
        assert len(rows) == len(downloadable_datasets()) + len(INGEST_ARTIFACTS)

    def test_manifest_and_disk_flags(self, tmp_path):
        d = tmp_path / "ghana"
        d.mkdir()
        (d / "ghana_water_occurrence.tif").write_text("x")
        (d / "manifest.json").write_text(json.dumps({
            "datasets": {"jrc_water": {"files": {"jrc_water": "ghana_water_occurrence.tif"}}},
        }))
        rows = {r["key"]: r for r in catalog_status("ghana", data_root=tmp_path)}
        assert rows["jrc_water"]["in_manifest"] is True
        assert rows["jrc_water"]["on_disk"] is True
        assert rows["chirps_rainfall_daily"]["in_manifest"] is False
        assert rows["chirps_rainfall_daily"]["on_disk"] is False


class TestRegisterExisting:
    """register_existing() — one-shot migration for pre-manifest dirs."""

    def _mk_dir(self, tmp_path: pathlib.Path) -> pathlib.Path:
        d = tmp_path / "ghana"
        d.mkdir()
        (d / "ghana_rainfall_daily_2024_2025_daily.nc").touch()
        (d / "ghana_elevation.tif").touch()
        (d / "ghana_host_static.nc").touch()
        (d / "host_manifest.json").touch()
        (d / "ghana_mobility_day.csr").touch()
        (d / "ghana_mobility_night.csr").touch()
        (d / "ghana_livestock_mobility.csr").touch()
        (d / "ghana_regional_2024_2025_env.nc").touch()
        (d / "ghana_habitat_patches.gpkg").touch()
        return d

    def test_dry_run_writes_nothing(self, tmp_path):
        d = self._mk_dir(tmp_path)
        summary = register_existing("ghana", data_dir=d, dry_run=True)
        assert load_local_manifest(d) == {}
        assert any("chirps_rainfall_daily" in r for r in summary["registered"])
        assert d / "manifest.json" not in [None]

    def test_registers_downloadables_and_artifacts(self, tmp_path):
        d = self._mk_dir(tmp_path)
        summary = register_existing("ghana", data_dir=d)
        manifest = load_local_manifest(d)
        assert "chirps_rainfall_daily" in manifest
        assert manifest["chirps_rainfall_daily"]["files"]["chirps_rainfall_daily"] \
            == "ghana_rainfall_daily_2024_2025_daily.nc"
        # Ingest artifacts keyed by INGEST_ARTIFACTS, with abm flags
        assert "host_static" in manifest
        assert manifest["host_static"]["required_for_abm"] is True
        assert "mobility_day" in manifest
        assert "env" in manifest
        # Second run never overwrites / duplicates
        summary2 = register_existing("ghana", data_dir=d)
        assert all("already registered" in s for s in summary2["skipped"])

    def test_missing_files_reported(self, tmp_path):
        d = tmp_path / "ghana"
        d.mkdir()
        summary = register_existing("ghana", data_dir=d, dry_run=True)
        # Every artifact falls into "missing" — nothing on disk
        assert summary["registered"] == []
        assert len(summary["missing"]) > 0


class TestIngestArtifactsTable:
    """INGEST_ARTIFACTS — the single source of derived-artifact identity."""

    def test_expected_keys_present(self):
        assert {"env", "habitat", "host_static", "host_manifest",
                "mobility_day", "mobility_night", "livestock_mobility",
                "mobility_manifest"} == set(INGEST_ARTIFACTS)
        assert all(art.producer.startswith("mal_core.ingest.")
                   for art in INGEST_ARTIFACTS.values())
        assert INGEST_ARTIFACTS["env"].required_for_abm
        assert INGEST_ARTIFACTS["mobility_day"].required_for_abm
        assert not INGEST_ARTIFACTS["host_manifest"].required_for_abm

    def test_keys_match_ghana_manifest(self):
        """The real ghana manifest must carry every ABM-required artifact."""
        manifest = json.loads(
            (pathlib.Path("data") / "ghana" / "manifest.json").read_text()
        )
        for key, art in INGEST_ARTIFACTS.items():
            if art.required_for_abm:
                assert key in manifest["datasets"], key
