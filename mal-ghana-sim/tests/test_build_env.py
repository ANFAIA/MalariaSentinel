"""Tests for the M1.3b build_env CLI (Typer, orchestrates the M1.3a loaders).

The CLI is exercised in-process via ``typer.testing.CliRunner`` (no subprocess).
The data loaders are monkey-patched so the suite runs offline and finishes in
well under a second per test.

Naming
------
The contract filename pattern is
``{aoi_slug}_{scale}_{year}_{month:02d}_env.tif``. To keep the test grid small
(fast TWI), we monkey-patch the in-repo ``_DEFAULT_REGISTRY`` so the
``ghana`` slug resolves to a tiny AOI; the file is still named
``ghana_regional_2024_06_env.tif`` because slug and scale come from the
AOI, not its extent.
"""
from __future__ import annotations

import json
import pathlib

import geopandas as gpd
import numpy as np
import pytest
import rasterio
import typer.testing
import xarray as xr
from rasterio.transform import from_bounds

from mal_commonlib.aoi import AOI, Scale

from mal_ghana_sim.scripts import build_env


runner = typer.testing.CliRunner()


# -- fixtures ---------------------------------------------------------------


@pytest.fixture
def small_ghana_aoi() -> AOI:
    """A tiny AOI registered as ``ghana`` for fast tests (12x12 grid)."""
    return AOI.from_bbox(
        -0.05, -0.05, 0.05, 0.05,
        crs="EPSG:4326", slug="ghana", resolution_m=1000, scale=Scale.REGIONAL,
    )


@pytest.fixture
def patch_ghana_registry(small_ghana_aoi: AOI, monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace the in-repo Ghana registry with the small AOI for fast tests."""
    monkeypatch.setitem(build_env._DEFAULT_REGISTRY, "ghana", small_ghana_aoi)


def _synthetic_env_grid(aoi: AOI) -> tuple[int, int]:
    return aoi.cells_per_side()


def _make_synthetic_loader_outputs(aoi: AOI) -> dict[str, xr.DataArray]:
    """Build synthetic xr.DataArrays shaped to the AOI's grid."""
    h, w = _synthetic_env_grid(aoi)
    transform = from_bounds(*aoi.bbox, w, h)

    # 1-cell water mask: only (h//2, w//2) > 0 — guarantees the habitat
    # gpkg has at least one candidate row without scanning a 12x12 grid.
    water = np.zeros((h, w), dtype=np.float32)
    water[h // 2, w // 2] = 1.0
    water_da = xr.DataArray(water, dims=("y", "x"), name="water_frac")
    water_da.rio.write_crs(aoi.crs_obj, inplace=True)
    water_da.rio.write_transform(transform, inplace=True)

    rain = np.full((h, w), 0.5, dtype=np.float32)
    rain_da = xr.DataArray(rain, dims=("y", "x"), name="rainfall")
    rain_da.rio.write_crs(aoi.crs_obj, inplace=True)
    rain_da.rio.write_transform(transform, inplace=True)

    temp = np.full((h, w), 0.7, dtype=np.float32)
    temp_da = xr.DataArray(temp, dims=("y", "x"), name="temp_suitability")
    temp_da.rio.write_crs(aoi.crs_obj, inplace=True)
    temp_da.rio.write_transform(transform, inplace=True)

    ndvi = np.full((h, w), 0.4, dtype=np.float32)
    ndvi_da = xr.DataArray(ndvi, dims=("y", "x"), name="ndvi")
    ndvi_da.rio.write_crs(aoi.crs_obj, inplace=True)
    ndvi_da.rio.write_transform(transform, inplace=True)

    # DEM: a gentle south-east gradient — TWI accumulates towards the
    # bottom-right, which is a meaningful non-trivial test.
    y_idx, x_idx = np.indices((h, w))
    dem = (y_idx * 10 + x_idx * 5).astype(np.float32)
    dem_da = xr.DataArray(dem, dims=("y", "x"), name="elevation")
    dem_da.rio.write_crs(aoi.crs_obj, inplace=True)
    dem_da.rio.write_transform(transform, inplace=True)

    return {
        "water_frac": water_da,
        "rainfall": rain_da,
        "temp_suitability": temp_da,
        "ndvi": ndvi_da,
        "elevation": dem_da,
    }


def _patch_loaders(
    monkeypatch: pytest.MonkeyPatch,
    outputs: dict[str, xr.DataArray],
) -> None:
    """Wire each loader entry point to its synthetic DataArray."""
    monkeypatch.setattr(
        build_env, "load_chirps_rainfall",
        lambda aoi, year, month, **kw: outputs["rainfall"],
    )
    monkeypatch.setattr(
        build_env, "load_era5_temp_suitability",
        lambda aoi, year, month, **kw: outputs["temp_suitability"],
    )
    monkeypatch.setattr(
        build_env, "load_modis_ndvi",
        lambda aoi, year, month, **kw: outputs["ndvi"],
    )
    monkeypatch.setattr(
        build_env, "load_worldcover_water_frac",
        lambda aoi, year, month, **kw: outputs["water_frac"],
    )
    monkeypatch.setattr(
        build_env, "load_merit_dem",
        lambda aoi, **kw: outputs["elevation"],
    )


# -- tests ------------------------------------------------------------------


def test_build_env_help() -> None:
    """`build_env --help` exits 0 and lists the required options."""
    result = runner.invoke(build_env.app, ["--help"])
    assert result.exit_code == 0, result.stdout
    for opt in ("--aoi", "--year", "--month", "--output-dir"):
        assert opt in result.stdout, f"--help must list {opt}"


def test_build_env_ghana_dry_run_with_mocks(
    patch_ghana_registry: None,
    small_ghana_aoi: AOI,
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """All 5 loaders mocked: CLI runs end-to-end and writes the contract outputs."""
    outputs = _make_synthetic_loader_outputs(small_ghana_aoi)
    _patch_loaders(monkeypatch, outputs)

    result = runner.invoke(
        build_env.app,
        ["--aoi", "ghana", "--year", "2024", "--month", "6", "--output-dir", str(tmp_path)],
    )
    assert result.exit_code == 0, result.stdout

    env_path = tmp_path / "ghana_regional_2024_06_env.tif"
    assert env_path.exists(), f"env COG missing: {env_path}"
    with rasterio.open(env_path) as src:
        assert src.count == 4, f"expected 4 bands, got {src.count}"
        assert src.crs.to_epsg() == 4326, f"expected EPSG:4326, got {src.crs}"
        assert src.dtypes[0] == "float32", f"expected float32, got {src.dtypes[0]}"
        assert tuple(src.descriptions) == (
            "water_frac", "rainfall", "temp_suitability", "ndvi",
        ), f"unexpected band descriptions: {src.descriptions}"

    sidecar_path = tmp_path / "ghana_regional_2024_06_env.json"
    assert sidecar_path.exists(), f"sidecar missing: {sidecar_path}"
    sidecar = json.loads(sidecar_path.read_text())
    assert sidecar["contract_version"] == "1.0", (
        f"sidecar contract_version must be '1.0'; got {sidecar.get('contract_version')!r}"
    )
    assert sidecar["aoi_slug"] == "ghana"
    assert sidecar["scale"] == "regional"
    assert sidecar["year"] == 2024
    assert sidecar["month"] == 6

    habitat_path = tmp_path / "ghana_regional_2024_06_habitat_patches.gpkg"
    assert habitat_path.exists(), f"habitat gpkg missing: {habitat_path}"
    gdf = gpd.read_file(habitat_path)
    assert len(gdf) >= 1, f"habitat gpkg must have >= 1 row; got {len(gdf)}"
    assert gdf.crs.to_epsg() == 4326, f"habitat gpkg must be EPSG:4326; got {gdf.crs}"
    for col in ("twi_value", "water_frac_value"):
        assert col in gdf.columns, f"habitat gpkg missing column {col!r}"


def test_build_env_handles_era5_auth_missing(
    patch_ghana_registry: None,
    small_ghana_aoi: AOI,
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When the ERA5 loader raises, the CLI continues with a NoData channel."""
    outputs = _make_synthetic_loader_outputs(small_ghana_aoi)

    def _era5_raises(*args, **kwargs):
        raise RuntimeError("CDS auth missing: set CDSAPI_URL/KEY or ~/.cdsapirc")

    monkeypatch.setattr(
        build_env, "load_chirps_rainfall",
        lambda aoi, year, month, **kw: outputs["rainfall"],
    )
    monkeypatch.setattr(
        build_env, "load_era5_temp_suitability", _era5_raises,
    )
    monkeypatch.setattr(
        build_env, "load_modis_ndvi",
        lambda aoi, year, month, **kw: outputs["ndvi"],
    )
    monkeypatch.setattr(
        build_env, "load_worldcover_water_frac",
        lambda aoi, year, month, **kw: outputs["water_frac"],
    )
    monkeypatch.setattr(
        build_env, "load_merit_dem",
        lambda aoi, **kw: outputs["elevation"],
    )

    result = runner.invoke(
        build_env.app,
        ["--aoi", "ghana", "--year", "2024", "--month", "6", "--output-dir", str(tmp_path)],
    )
    assert result.exit_code == 0, (
        f"CLI must continue past ERA5 auth failure; got exit {result.exit_code}, "
        f"output:\n{result.stdout}"
    )
    assert "WARNING" in (result.stdout + (result.stderr or "")), (
        "CLI must print a clear WARNING when an auth-gated loader fails"
    )
    # The env COG must still be written.
    assert (tmp_path / "ghana_regional_2024_06_env.tif").exists()


def test_build_env_validates_month(
    patch_ghana_registry: None,
    tmp_path: pathlib.Path,
) -> None:
    """Out-of-range month yields a non-zero exit and a clear error."""
    result = runner.invoke(
        build_env.app,
        ["--aoi", "ghana", "--year", "2024", "--month", "13", "--output-dir", str(tmp_path)],
    )
    assert result.exit_code != 0, (
        f"month=13 must fail; got exit 0, output:\n{result.stdout}"
    )
    out = (result.stdout or "") + (result.stderr or "")
    assert "month" in out.lower(), (
        f"error message must mention 'month'; got:\n{out}"
    )


def test_build_env_handles_worldcover_skip(
    patch_ghana_registry: None,
    small_ghana_aoi: AOI,
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`--skip-worldcover` fills the water_frac band with NoData (-9999.0) and
    does not call the WorldCover loader at all."""
    outputs = _make_synthetic_loader_outputs(small_ghana_aoi)
    _patch_loaders(monkeypatch, outputs)

    worldcover_called = {"n": 0}

    def _tracking_worldcover(*args, **kwargs):
        worldcover_called["n"] += 1
        return outputs["water_frac"]
    monkeypatch.setattr(
        build_env, "load_worldcover_water_frac", _tracking_worldcover,
    )

    result = runner.invoke(
        build_env.app,
        [
            "--aoi", "ghana", "--year", "2024", "--month", "6",
            "--output-dir", str(tmp_path),
            "--skip-worldcover",
        ],
    )
    assert result.exit_code == 0, (
        f"CLI must exit 0 with --skip-worldcover; got {result.exit_code}, "
        f"output:\n{result.stdout}"
    )
    out = (result.stdout or "") + (result.stderr or "")
    assert "skip-worldcover" in out, (
        f"CLI must announce the skip; got:\n{out}"
    )
    assert worldcover_called["n"] == 0, (
        f"WorldCover loader must not be called when --skip-worldcover is set; "
        f"was called {worldcover_called['n']} times"
    )

    env_path = tmp_path / "ghana_regional_2024_06_env.tif"
    assert env_path.exists(), f"env COG missing: {env_path}"
    with rasterio.open(env_path) as src:
        assert src.count == 4
        assert tuple(src.descriptions) == (
            "water_frac", "rainfall", "temp_suitability", "ndvi",
        )
        water_band = src.read(1)  # band 1 = water_frac
        assert np.all(water_band == -9999.0), (
            f"water_frac band must be -9999.0 when --skip-worldcover is set; "
            f"got unique values: {np.unique(water_band)[:5]}"
        )
