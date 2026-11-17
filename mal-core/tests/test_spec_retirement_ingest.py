"""Checks migrated from the retired ingest specification.

The spec is gone; the facts live in the code and in this file. See
docs/plans/in-process/spec-retirement-ledger.md for the row that maps
each assertion to this test.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pytest
import xarray as xr

from _habitat_fixtures import (
    write_air_temp_daily_nc,
    write_dw_fractions_nc,
    write_jrc_features_nc,
    write_rainfall_nc,
)
from mal_core.habitat.config import CONFIG
from mal_core.ingest.daily_nc import (
    HABITAT_CANDIDATE_MIN,
    NODATA_SENTINEL,
    build_daily_env_nc,
)

INGEST_SRC = Path(__file__).resolve().parents[1] / "src" / "mal_core" / "ingest"


# ---------------------------------------------------------------------------
# INV-20: the habitat candidate floor
# ---------------------------------------------------------------------------

def test_habitat_candidate_min_is_the_configured_floor():
    assert CONFIG["ingest"]["candidate_min_ingest"] == 1e-6
    assert HABITAT_CANDIDATE_MIN == 1e-6


def test_nodata_sentinel_is_the_configured_value():
    assert NODATA_SENTINEL == float(CONFIG["ingest"]["nodata_sentinel"])
    assert NODATA_SENTINEL == -9999.0


# ---------------------------------------------------------------------------
# INV-7..INV-10 / INV-21: the env NetCDF
# ---------------------------------------------------------------------------

def _inputs(tmp_path, write_manifest, *, times, jrc=None):
    write_rainfall_nc(tmp_path / "ghana_rainfall_daily_2024_2025_daily.nc", times)
    write_air_temp_daily_nc(tmp_path / "ghana_air_temp_daily_2024_2025_daily.nc", times)
    write_jrc_features_nc(
        tmp_path / "ghana_habitat_features.nc",
        jrc if jrc is not None else [[0.4, 0.0], [0.0, 0.2]],
    )
    write_dw_fractions_nc(tmp_path / "ghana_class_fractions.nc")
    write_manifest(tmp_path, {
        "chirps_rainfall_daily": "ghana_rainfall_daily_2024_2025_daily.nc",
        "era5_air_temp_daily": "ghana_air_temp_daily_2024_2025_daily.nc",
        "jrc_habitat_features": "ghana_habitat_features.nc",
        "dw_class_fractions": "ghana_class_fractions.nc",
    })


def test_env_nc_is_cf18_with_the_pinned_contract_and_generator(tmp_path, write_manifest):
    times = np.arange(np.datetime64("2024-06-01"), np.datetime64("2024-06-04"))
    _inputs(tmp_path, write_manifest, times=times)
    result = build_daily_env_nc("ghana", tmp_path)
    with xr.open_dataset(result["env_path"]) as ds:
        assert ds.attrs.get("Conventions") == "CF-1.8"
        assert ds.attrs.get("contract_version") == "3.0"
        assert ds.attrs.get("generator_version") == "proxy-habitat-v1-0.1.0"


def test_env_nc_carries_the_pinned_variable_set(tmp_path, write_manifest):
    times = np.arange(np.datetime64("2024-06-01"), np.datetime64("2024-06-04"))
    _inputs(tmp_path, write_manifest, times=times)
    result = build_daily_env_nc("ghana", tmp_path)
    with xr.open_dataset(result["env_path"]) as ds:
        assert set(ds.data_vars) == {
            "rainfall", "air_temp_c", "jrc_persistent",
            "lc_built", "lc_wetland", "lc_open_plus_water", "lc_crop",
        }


def test_env_nc_statics_are_2d_float32_and_never_broadcast(tmp_path, write_manifest):
    times = np.arange(np.datetime64("2024-06-01"), np.datetime64("2024-06-04"))
    _inputs(tmp_path, write_manifest, times=times)
    result = build_daily_env_nc("ghana", tmp_path)
    with xr.open_dataset(result["env_path"]) as ds:
        for var in ("jrc_persistent", "lc_built", "lc_wetland",
                    "lc_open_plus_water", "lc_crop"):
            assert ds[var].dims == ("y", "x"), f"{var} was broadcast over time"
            assert ds[var].dtype == np.float32
        assert ds["rainfall"].dtype == np.float32
        assert ds["air_temp_c"].dtype == np.float32


def test_env_nc_uses_zlib_compression_level_four(tmp_path, write_manifest):
    times = np.arange(np.datetime64("2024-06-01"), np.datetime64("2024-06-04"))
    _inputs(tmp_path, write_manifest, times=times)
    result = build_daily_env_nc("ghana", tmp_path)
    with xr.open_dataset(result["env_path"]) as ds:
        enc = ds["rainfall"].encoding
        assert enc.get("zlib") is True
        assert enc.get("complevel") == 4


def test_env_nc_time_axis_covers_every_rainfall_day(tmp_path, write_manifest):
    times = np.arange(np.datetime64("2024-01-01"), np.datetime64("2024-01-01")
                      + np.timedelta64(400, "D"))
    _inputs(tmp_path, write_manifest, times=times)
    result = build_daily_env_nc("ghana", tmp_path)
    with xr.open_dataset(result["env_path"]) as ds:
        assert ds.sizes["time"] == len(times)
        assert ds.sizes["time"] >= 365


def test_env_nc_filename_follows_the_regional_multi_year_convention(tmp_path, write_manifest):
    times = np.arange(np.datetime64("2024-01-01"), np.datetime64("2024-01-01")
                      + np.timedelta64(400, "D"))
    _inputs(tmp_path, write_manifest, times=times)
    result = build_daily_env_nc("ghana", tmp_path)
    # The start/end years are inferred from the CHIRPS daily input file.
    assert Path(result["env_path"]).name == "ghana_regional_2024_2025_env.nc"
    assert re.fullmatch(r"[a-z0-9-]+_regional_\d{4}_\d{4}_env\.nc",
                        Path(result["env_path"]).name)


def test_env_nc_requires_air_temperature_for_every_rainfall_day(tmp_path, write_manifest):
    """The daily air temperature NC must cover the whole rainfall period."""
    rainfall_times = np.arange(np.datetime64("2024-06-01"), np.datetime64("2024-06-04"))
    temp_times = np.arange(np.datetime64("2024-06-01"), np.datetime64("2024-06-03"))
    write_rainfall_nc(tmp_path / "ghana_rainfall_daily_2024_2025_daily.nc",
                      rainfall_times)
    write_air_temp_daily_nc(tmp_path / "ghana_air_temp_daily_2024_2025_daily.nc",
                            temp_times)
    write_jrc_features_nc(tmp_path / "ghana_habitat_features.nc",
                          [[0.4, 0.0], [0.0, 0.2]])
    write_dw_fractions_nc(tmp_path / "ghana_class_fractions.nc")
    write_manifest(tmp_path, {
        "chirps_rainfall_daily": "ghana_rainfall_daily_2024_2025_daily.nc",
        "era5_air_temp_daily": "ghana_air_temp_daily_2024_2025_daily.nc",
        "jrc_habitat_features": "ghana_habitat_features.nc",
        "dw_class_fractions": "ghana_class_fractions.nc",
    })
    with pytest.raises(Exception):
        build_daily_env_nc("ghana", tmp_path)


# ---------------------------------------------------------------------------
# INV-6: the habitat GeoPackage columns
# ---------------------------------------------------------------------------

def _small_aoi():
    from mal_commonlib.aoi import AOI, Scale

    return AOI(slug="tiny", name="Tiny", bbox=(0.0, 0.0, 0.02, 0.02),
               crs="EPSG:4326", resolution_m=1000, scale=Scale.REGIONAL)


def test_habitat_gpkg_carries_the_documented_columns(tmp_path):
    from mal_core.ingest.env import _write_habitat_patches_gpkg

    aoi = _small_aoi()
    h, w = aoi.cells_per_side()
    statics = {
        "jrc_persistent": np.full((h, w), 0.5, dtype=np.float32),
        "lc_built": np.zeros((h, w), dtype=np.float32),
        "lc_wetland": np.zeros((h, w), dtype=np.float32),
        "lc_open_plus_water": np.zeros((h, w), dtype=np.float32),
        "lc_crop": np.zeros((h, w), dtype=np.float32),
    }
    path = tmp_path / "tiny_habitat_patches.gpkg"
    _write_habitat_patches_gpkg(path, statics, aoi)

    import geopandas as gpd

    gdf = gpd.read_file(path)
    for col in ("hab_type", "habitat_potential", "dynamics", "row", "col",
                "aoi_slug"):
        assert col in gdf.columns, f"the habitat gpkg is missing the {col!r} column"
    assert set(gdf["aoi_slug"]) == {"tiny"}
    assert set(gdf["dynamics"]) <= {"persistent", "pluvial"}
    assert (gdf["habitat_potential"] > 0).all()


# ---------------------------------------------------------------------------
# INV-13 / INV-14: the GHSL SMOD reclassification and the fallbacks
# ---------------------------------------------------------------------------

def test_ghsl_reclassification_and_fallback_constants_are_pinned():
    """The reclassification and the fallback constants live in hosts.py."""
    source = (INGEST_SRC / "hosts.py").read_text(encoding="utf-8")
    assert "urban_class == 30" in source          # 30 -> 30 (urban)
    assert "(urban_class >= 20) & (urban_class < 30)" in source  # 20-29 -> 50
    assert "(urban_class >= 0) & (urban_class < 20)" in source   # 0-19 -> 20
    assert "np.full((h, w), 50, dtype=np.int32)" in source       # fallback: rural
    assert "np.where(urban_class == 30, 0.6, 0.1)" in source      # building fraction
    assert "np.full((h, w), 0.3, dtype=np.float32)" in source    # wildlife proxy


def test_host_manifest_declares_the_nine_host_variables():
    source = (INGEST_SRC / "hosts.py").read_text(encoding="utf-8")
    for var in ("human", "cattle", "goats", "sheep", "pigs", "chickens",
                "urban_class", "building_fraction", "wildlife_host_proxy"):
        assert f'"{var}"' in source, f"{var} is not declared by the host builder"


# ---------------------------------------------------------------------------
# INV-15 / INV-16: the mobility CSRs
# ---------------------------------------------------------------------------

def _host_static_nc(path, h=4, w=4):
    from mal_commonlib.data.host_utils import build_host_static_nc
    from rasterio.transform import from_bounds

    grid_spec = {
        "crs": "EPSG:4326",
        "transform": from_bounds(0, 0, 1, 1, h, w),
        "height": h,
        "width": w,
    }
    ones = np.ones((h, w), dtype=np.float32)
    build_host_static_nc(
        human=ones, cattle=ones, goats=ones, sheep=ones,
        urban_class=np.full((h, w), 50, dtype=np.int32),
        output_path=path, grid_spec=grid_spec,
    )


def test_mobility_writes_the_three_csr_files_with_the_gravity_parameters(tmp_path):
    from mal_core.ingest.mobility import build_mobility_dataset

    hosts = tmp_path / "tiny_host_static.nc"
    _host_static_nc(hosts)
    out = tmp_path / "mobility"
    result = build_mobility_dataset(hosts, output_dir=out, aoi_slug="tiny")

    for name in ("tiny_mobility_day.csr", "tiny_mobility_night.csr",
                 "tiny_livestock_mobility.csr"):
        assert (out / name).exists(), f"{name} was not written"

    manifest = json.loads((out / "mobility_manifest.json").read_text())
    assert manifest["cell_size_km"] == 1.0
    assert manifest["beta_day"] == 0.05
    assert manifest["beta_night"] == 0.5
    assert manifest["beta_livestock"] == 0.1
    assert manifest["max_distance_km"] == 50.0
    assert result["n_cells"] == 16


def test_mobility_requires_the_host_static_file(tmp_path):
    from mal_core.ingest.mobility import build_mobility_dataset

    with pytest.raises(FileNotFoundError):
        build_mobility_dataset(tmp_path / "missing_host_static.nc",
                               output_dir=tmp_path / "out", aoi_slug="tiny")


# ---------------------------------------------------------------------------
# INV-17: ingest never downloads
# ---------------------------------------------------------------------------

def test_the_ingest_package_never_calls_the_download_runner():
    for path in INGEST_SRC.glob("*.py"):
        source = path.read_text(encoding="utf-8")
        assert "run_download" not in source, (
            f"{path.name} must not download: ingest only consumes files")
