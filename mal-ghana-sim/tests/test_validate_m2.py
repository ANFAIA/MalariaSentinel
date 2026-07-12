"""Tests for the M2 validation pipeline (validate_m2).

The test exercises the CLI end-to-end via ``typer.testing.CliRunner`` with
heavy mocking: ``subprocess.run`` is mocked so the suite never touches the
network or runs real ABM rollouts, and ``_aggregate_suitability`` /
``_validate_suitability`` are stubbed to return a known-good AUC. A real
env COG is written to ``tmp_path`` so the report's env-attributes section
can read it (no extra mocking required there).
"""
from __future__ import annotations

import json
import pathlib
from unittest.mock import MagicMock

import geopandas as gpd
import numpy as np
import pytest
import rasterio
import typer.testing
from rasterio.transform import from_bounds
from shapely.geometry import Point

from mal_commonlib.aoi import AOI, Scale

from mal_ghana_sim.scripts import validate_m2


runner = typer.testing.CliRunner()


# -- fixtures ---------------------------------------------------------------


@pytest.fixture
def small_ghana_aoi() -> AOI:
    """Tiny AOI registered as ``ghana`` for fast tests (4x4 grid)."""
    return AOI.from_bbox(
        -0.05, -0.05, 0.05, 0.05,
        crs="EPSG:4326", slug="ghana", resolution_m=1000, scale=Scale.REGIONAL,
    )


@pytest.fixture
def patch_ghana_registry(small_ghana_aoi: AOI, monkeypatch: pytest.MonkeyPatch) -> None:
    """Make the validate_m2 module's slug registry resolve to the small AOI."""
    monkeypatch.setitem(validate_m2._DEFAULT_REGISTRY, "ghana", small_ghana_aoi)


def _write_fake_env(env_path: pathlib.Path, aoi: AOI) -> None:
    """Write a minimal 4-band env COG that satisfies the report's reader."""
    h, w = aoi.cells_per_side()
    transform = from_bounds(*aoi.bbox, w, h)
    arr = np.zeros((4, h, w), dtype=np.float32)
    arr[0, :, :] = 0.10   # water_frac
    arr[1, :, :] = 0.50   # rainfall
    arr[2, :, :] = 0.70   # temp_suitability
    arr[3, :, :] = 0.40   # ndvi
    with rasterio.open(
        env_path, "w",
        driver="GTiff", dtype="float32", count=4, height=h, width=w,
        crs=aoi.crs, transform=transform, nodata=-9999.0,
        tiled=True, compress="deflate", blockxsize=128, blockysize=128,
    ) as dst:
        dst.write(arr)
        dst.set_band_description(1, "water_frac")
        dst.set_band_description(2, "rainfall")
        dst.set_band_description(3, "temp_suitability")
        dst.set_band_description(4, "ndvi")
    sidecar = {
        "crs": aoi.crs, "transform": [float(x) for x in transform[:6]],
        "aoi_slug": aoi.slug, "scale": aoi.scale.value,
        "year": 2024, "month": 6,
        "generator_version": "m1-thin-0.1.0",
        "abm_params_hash": "sha256:pending",
        "contract_version": "1.0",
        "band_names": ["water_frac", "rainfall", "temp_suitability", "ndvi"],
    }
    env_path.with_suffix(".json").write_text(json.dumps(sidecar, indent=2))


def _write_fake_habitat(habitat_path: pathlib.Path, aoi: AOI) -> None:
    """Write a 1-row habitat gpkg so the (mocked) abm_run would have input."""
    h, w = aoi.cells_per_side()
    transform = from_bounds(*aoi.bbox, w, h)
    cx = transform.c + (w // 2 + 0.5) * transform.a
    cy = transform.f + (h // 2 + 0.5) * transform.e
    gdf = gpd.GeoDataFrame(
        {
            "twi_value": [9.0], "water_frac_value": [1.0],
            "row": [h // 2], "col": [w // 2], "aoi_slug": [aoi.slug],
        },
        geometry=[Point(cx, cy)],
        crs=aoi.crs,
    )
    gdf.to_file(habitat_path, driver="GPKG")


def _mock_subprocess(monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    """Replace ``subprocess.run`` with a no-op that records the commands."""
    calls: list[list[str]] = []

    def fake_run(cmd, *args, **kwargs):
        calls.append(list(cmd))
        return MagicMock(returncode=0, stdout=b"", stderr=b"")

    monkeypatch.setattr(validate_m2.subprocess, "run", fake_run)
    return calls


# -- tests ------------------------------------------------------------------


def test_validate_m2_help() -> None:
    """`validate_m2 --help` exits 0 and lists the required options."""
    result = runner.invoke(validate_m2.app, ["--help"])
    assert result.exit_code == 0, result.stdout
    for opt in ("--aoi", "--year", "--month", "--output-dir", "--n-rollouts", "--bootstrap", "--strict"):
        assert opt in result.stdout, f"--help must list {opt}"


def test_validate_m2_end_to_end_with_mocks_pass(
    patch_ghana_registry: None,
    small_ghana_aoi: AOI,
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PASS path: 2 rollouts, fake AUC > 0.65, report says PASS, exit 0."""
    env_path = tmp_path / "ghana_regional_2024_06_env.tif"
    habitat_path = tmp_path / "ghana_regional_2024_06_habitat_patches.gpkg"
    _write_fake_env(env_path, small_ghana_aoi)
    _write_fake_habitat(habitat_path, small_ghana_aoi)

    calls = _mock_subprocess(monkeypatch)

    def fake_aggregate(rollout_paths, output_path):
        # Write a 1-band COG matching the env shape.
        h, w = small_ghana_aoi.cells_per_side()
        transform = from_bounds(*small_ghana_aoi.bbox, w, h)
        suit = np.full((h, w), 0.3, dtype=np.float32)
        with rasterio.open(
            output_path, "w",
            driver="GTiff", dtype="float32", count=1, height=h, width=w,
            crs=small_ghana_aoi.crs, transform=transform, nodata=-9999.0,
            tiled=True, compress="deflate", blockxsize=128, blockysize=128,
        ) as dst:
            dst.write(suit, 1)
            dst.set_band_description(1, "suitability_mean")
        return {
            "min": 0.3, "mean": 0.3, "max": 0.3,
            "frac_gt_0_1": 1.0, "frac_gt_0_5": 0.0,
            "n_cells": int(h * w),
        }
    monkeypatch.setattr(validate_m2, "_aggregate_suitability", fake_aggregate)

    n_sites = 20
    site_lats = np.linspace(-0.04, 0.04, n_sites)
    site_lons = np.linspace(-0.04, 0.04, n_sites)
    site_values = np.linspace(0.40, 0.95, n_sites, dtype=np.float32)
    bg_values = np.full(10_000, 0.2, dtype=np.float32)

    def fake_validate(suit_path, occurrence_path, *, bootstrap, seed=42, n_background=10_000):
        return {
            "auc": 0.85, "ci_low": 0.72, "ci_high": 0.91,
            "n_sites": n_sites, "n_backgrounds": n_background,
            "suit_array": np.zeros((4, 4), dtype=np.float32),
            "affine": from_bounds(*small_ghana_aoi.bbox, 4, 4),
            "site_lats": site_lats, "site_lons": site_lons,
            "site_values": site_values, "bg_values": bg_values,
        }
    monkeypatch.setattr(validate_m2, "_validate_suitability", fake_validate)

    result = runner.invoke(
        validate_m2.app,
        [
            "--aoi", "ghana", "--year", "2024", "--month", "6",
            "--output-dir", str(tmp_path), "--n-rollouts", "2",
            "--bootstrap", "50",
        ],
    )
    assert result.exit_code == 0, (
        f"CLI must exit 0; got {result.exit_code}, output:\n{result.stdout}"
    )

    # The fake subprocess recorded the build_env + 2 abm_run calls.
    assert len(calls) == 3, f"expected 3 subprocess calls (build_env + 2 rollouts); got {len(calls)}"
    assert "-m" in calls[0] and "mal_ghana_sim.scripts.build_env" in calls[0]
    for c in calls[1:]:
        assert "mal_ghana_sim.abm.run" in c
        assert "--seed" in c

    # Aggregated suit COG + report + scatter all written.
    suit_path = tmp_path / "suitability_mean_2024_06.tif"
    assert suit_path.exists(), f"suit mean missing: {suit_path}"
    assert (tmp_path / "M2_REPORT.md").exists()
    assert (tmp_path / "m2_validation_scatter.png").exists()

    report = (tmp_path / "M2_REPORT.md").read_text()
    assert "AUC" in report
    assert "PASS" in report
    assert "0.85" in report
    assert "Verdict" in report
    # Per-site table has 20 rows.
    n_data_rows = sum(
        1 for line in report.splitlines()
        if line.startswith("| ") and not line.startswith("| #") and not line.startswith("|---")
    )
    assert n_data_rows >= 20, f"per-site table must have >= 20 rows; got {n_data_rows}"


def test_validate_m2_end_to_end_with_mocks_fail_with_strict(
    patch_ghana_registry: None,
    small_ghana_aoi: AOI,
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FAIL path with --strict: lower-95 < 0.65 -> exit 1, report says FAIL."""
    env_path = tmp_path / "ghana_regional_2024_06_env.tif"
    habitat_path = tmp_path / "ghana_regional_2024_06_habitat_patches.gpkg"
    _write_fake_env(env_path, small_ghana_aoi)
    _write_fake_habitat(habitat_path, small_ghana_aoi)

    _mock_subprocess(monkeypatch)

    def fake_aggregate(rollout_paths, output_path):
        h, w = small_ghana_aoi.cells_per_side()
        transform = from_bounds(*small_ghana_aoi.bbox, w, h)
        suit = np.full((h, w), 0.3, dtype=np.float32)
        with rasterio.open(
            output_path, "w",
            driver="GTiff", dtype="float32", count=1, height=h, width=w,
            crs=small_ghana_aoi.crs, transform=transform, nodata=-9999.0,
            tiled=True, compress="deflate", blockxsize=128, blockysize=128,
        ) as dst:
            dst.write(suit, 1)
            dst.set_band_description(1, "suitability_mean")
        return {
            "min": 0.3, "mean": 0.3, "max": 0.3,
            "frac_gt_0_1": 1.0, "frac_gt_0_5": 0.0,
            "n_cells": int(h * w),
        }
    monkeypatch.setattr(validate_m2, "_aggregate_suitability", fake_aggregate)

    n_sites = 20
    site_lats = np.linspace(-0.04, 0.04, n_sites)
    site_lons = np.linspace(-0.04, 0.04, n_sites)
    site_values = np.full(n_sites, 0.3, dtype=np.float32)
    bg_values = np.full(10_000, 0.3, dtype=np.float32)

    def fake_validate(suit_path, occurrence_path, *, bootstrap, seed=42, n_background=10_000):
        return {
            "auc": 0.55, "ci_low": 0.50, "ci_high": 0.60,  # below 0.65
            "n_sites": n_sites, "n_backgrounds": n_background,
            "suit_array": np.zeros((4, 4), dtype=np.float32),
            "affine": from_bounds(*small_ghana_aoi.bbox, 4, 4),
            "site_lats": site_lats, "site_lons": site_lons,
            "site_values": site_values, "bg_values": bg_values,
        }
    monkeypatch.setattr(validate_m2, "_validate_suitability", fake_validate)

    result = runner.invoke(
        validate_m2.app,
        [
            "--aoi", "ghana", "--year", "2024", "--month", "6",
            "--output-dir", str(tmp_path), "--n-rollouts", "1",
            "--bootstrap", "10", "--strict",
        ],
    )
    assert result.exit_code == 1, (
        f"--strict with ci_low < 0.65 must exit 1; got {result.exit_code}, "
        f"output:\n{result.stdout}"
    )

    report = (tmp_path / "M2_REPORT.md").read_text()
    assert "FAIL" in report
    assert "0.55" in report


def test_validate_m2_non_strict_always_exits_zero_on_fail(
    patch_ghana_registry: None,
    small_ghana_aoi: AOI,
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Without --strict, a failing AUC must still exit 0 (the verdict is in the report)."""
    env_path = tmp_path / "ghana_regional_2024_06_env.tif"
    habitat_path = tmp_path / "ghana_regional_2024_06_habitat_patches.gpkg"
    _write_fake_env(env_path, small_ghana_aoi)
    _write_fake_habitat(habitat_path, small_ghana_aoi)

    _mock_subprocess(monkeypatch)

    def fake_aggregate(rollout_paths, output_path):
        h, w = small_ghana_aoi.cells_per_side()
        transform = from_bounds(*small_ghana_aoi.bbox, w, h)
        suit = np.full((h, w), 0.3, dtype=np.float32)
        with rasterio.open(
            output_path, "w",
            driver="GTiff", dtype="float32", count=1, height=h, width=w,
            crs=small_ghana_aoi.crs, transform=transform, nodata=-9999.0,
            tiled=True, compress="deflate", blockxsize=128, blockysize=128,
        ) as dst:
            dst.write(suit, 1)
            dst.set_band_description(1, "suitability_mean")
        return {
            "min": 0.3, "mean": 0.3, "max": 0.3,
            "frac_gt_0_1": 1.0, "frac_gt_0_5": 0.0,
            "n_cells": int(h * w),
        }
    monkeypatch.setattr(validate_m2, "_aggregate_suitability", fake_aggregate)

    n_sites = 20
    site_lats = np.linspace(-0.04, 0.04, n_sites)
    site_lons = np.linspace(-0.04, 0.04, n_sites)

    def fake_validate(suit_path, occurrence_path, *, bootstrap, seed=42, n_background=10_000):
        return {
            "auc": 0.55, "ci_low": 0.50, "ci_high": 0.60,
            "n_sites": n_sites, "n_backgrounds": n_background,
            "suit_array": np.zeros((4, 4), dtype=np.float32),
            "affine": from_bounds(*small_ghana_aoi.bbox, 4, 4),
            "site_lats": site_lats, "site_lons": site_lons,
            "site_values": np.full(n_sites, 0.3, dtype=np.float32),
            "bg_values": np.full(n_background, 0.3, dtype=np.float32),
        }
    monkeypatch.setattr(validate_m2, "_validate_suitability", fake_validate)

    result = runner.invoke(
        validate_m2.app,
        [
            "--aoi", "ghana", "--year", "2024", "--month", "6",
            "--output-dir", str(tmp_path), "--n-rollouts", "1",
            "--bootstrap", "10",
        ],
    )
    assert result.exit_code == 0, (
        f"non-strict mode must exit 0; got {result.exit_code}, output:\n{result.stdout}"
    )
    report = (tmp_path / "M2_REPORT.md").read_text()
    assert "FAIL" in report
