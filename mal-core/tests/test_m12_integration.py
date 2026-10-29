"""Contract-v3.0 end-to-end checks: build_daily_env_nc static planes,
coastline saltwater filter, candidate census and download profiles."""
from __future__ import annotations

import numpy as np
import xarray as xr

from _habitat_fixtures import (
    write_air_temp_daily_nc,
    write_jrc_features_nc,
    write_land_mask_tif,
    write_rainfall_nc,
    write_dw_fractions_nc,
)
from mal_core.ingest.daily_nc import build_daily_env_nc
from mal_core.download.registry import discover_downloaders


def _base_inputs(tmp_path, write_manifest, *, times, jrc=None,
                 coastline=None, land_mask=None, extra_manifest=None):
    write_rainfall_nc(
        tmp_path / "ghana_rainfall_daily_2024_2025_daily.nc", times)
    write_air_temp_daily_nc(
        tmp_path / "ghana_air_temp_daily_2024_2025_daily.nc", times)
    write_jrc_features_nc(
        tmp_path / "ghana_habitat_features.nc",
        jrc if jrc is not None else [[0.1, 0.1], [0.1, 0.1]])
    write_dw_fractions_nc(tmp_path / "ghana_class_fractions.nc")
    manifest = {
        "chirps_rainfall_daily": "ghana_rainfall_daily_2024_2025_daily.nc",
        "era5_air_temp_daily": "ghana_air_temp_daily_2024_2025_daily.nc",
        "jrc_habitat_features": "ghana_habitat_features.nc",
        "dw_class_fractions": "ghana_class_fractions.nc",
    }
    if coastline is not None:
        manifest["coastline_land_mask"] = coastline
        write_land_mask_tif(tmp_path / coastline, land_mask)
    if extra_manifest:
        manifest.update(extra_manifest)
    write_manifest(tmp_path, manifest)


def test_daily_env_nc_contract_statics_and_daily_air(tmp_path, write_manifest):
    """The v3.0 env NC: daily rainfall + daily air_temp_c + the five
    static habitat planes. No water_frac, no ndvi, no annual broadcast."""
    times = np.arange(np.datetime64("2024-06-01"), np.datetime64("2024-06-04"))
    _base_inputs(tmp_path, write_manifest, times=times, jrc=[[0.4, 0.0], [0.0, 0.2]])
    result = build_daily_env_nc("ghana", tmp_path)
    assert set(result["variables"]) == {
        "rainfall", "air_temp_c", "jrc_persistent",
        "lc_built", "lc_wetland", "lc_open_plus_water", "lc_crop",
    }
    ds = xr.open_dataset(result["env_path"])
    try:
        assert ds.sizes["time"] == len(times)
        # Rainfall is intact per-day.
        assert float(ds["rainfall"].isel(time=0).values.max()) == 1.0
        # Daily air temperature carries the per-day mean in °C (25) — not
        # an annual raster repeated,
        assert str(ds.time.values[0])[:10] == "2024-06-01"
        np.testing.assert_allclose(
            ds["air_temp_c"].isel(time=1).values,
            np.full((2, 2), 25.0),
        )
        # Static planes are 2-D, in [0, 1].
        for v in ("jrc_persistent", "lc_built", "lc_wetland",
                  "lc_open_plus_water", "lc_crop"):
            arr = ds[v].values
            assert arr.shape == (2, 2)
            assert arr.min() >= 0.0 and arr.max() <= 1.0
        np.testing.assert_allclose(
            ds["jrc_persistent"].values, [[0.4, 0.0], [0.0, 0.2]]
        )
        assert result["n_candidate_cells"] > 0
    finally:
        ds.close()


def test_daily_env_nc_nodata_inputs_fail_loud(tmp_path, write_manifest):
    """Nodata planes (-9999) are treated as zero potential; with no other
    habitat the candidate census raises instead of silently ingesting an
    empty habitat surface."""
    times = np.arange(np.datetime64("2024-06-01"), np.datetime64("2024-06-03"))
    write_rainfall_nc(
        tmp_path / "ghana_rainfall_daily_2024_2025_daily.nc", times)
    write_air_temp_daily_nc(
        tmp_path / "ghana_air_temp_daily_2024_2025_daily.nc", times)
    write_jrc_features_nc(
        tmp_path / "ghana_habitat_features.nc", [[0.0, 0.0], [0.0, 0.0]])
    write_dw_fractions_nc(
        tmp_path / "ghana_class_fractions.nc",
        built=0.0, wetland=0.0, openp=0.0, crop=0.0)
    write_manifest(tmp_path, {
        "chirps_rainfall_daily": "ghana_rainfall_daily_2024_2025_daily.nc",
        "era5_air_temp_daily": "ghana_air_temp_daily_2024_2025_daily.nc",
        "jrc_habitat_features": "ghana_habitat_features.nc",
        "dw_class_fractions": "ghana_class_fractions.nc",
    })
    import pytest

    with pytest.raises(RuntimeError, match="0 candidate habitat"):
        build_daily_env_nc("ghana", tmp_path)


def test_coastline_zeros_ocean_static_plane(tmp_path, monkeypatch, write_manifest):
    """Open-sea cells lose JRC *and* their daily rainfall/temperature.

    With a zero coastal band the water column is open sea, so the coastline
    fix (2026-10) masks it everywhere; land keeps its values. The mask is now
    the land-fraction rule, not a dilated binary raster.
    """
    monkeypatch.setenv("COASTLINE_BUFFER_M", "0")
    times = np.arange(np.datetime64("2024-06-01"), np.datetime64("2024-06-03"))
    _base_inputs(
        tmp_path, write_manifest,
        times=times, jrc=[[1.0, 1.0], [1.0, 1.0]],
        coastline="ghana_land_mask.tif", land_mask=[[1.0, 0.0], [1.0, 0.0]],
    )
    result = build_daily_env_nc("ghana", tmp_path)
    ds = xr.open_dataset(result["env_path"])
    try:
        np.testing.assert_allclose(
            ds["jrc_persistent"].values, [[1.0, 0.0], [1.0, 0.0]]
        )
        np.testing.assert_allclose(
            ds["rainfall"].isel(time=0).values, [[1.0, 0.0], [1.0, 0.0]]
        )
        np.testing.assert_allclose(
            ds["air_temp_c"].isel(time=0).values, [[25.0, 0.0], [25.0, 0.0]]
        )
        # Additive truthful basemap plane.
        assert "land_frac" in ds
        np.testing.assert_allclose(
            ds["land_frac"].values, [[1.0, 0.0], [1.0, 0.0]], atol=1e-6
        )
        assert "land_frac" in result["variables"]
        assert "coastline_applied" not in result
    finally:
        ds.close()


def test_coastline_band_keeps_coastal_water(tmp_path, monkeypatch, write_manifest):
    """Coastal water (inside the band) keeps rain, temperature and JRC.

    Same 2x2 grid as above: the water column is 1 km from land, so a 5 km
    band classifies it as coastal water rather than open sea. This is the
    behaviour the old 5 km dilation faked by turning water into "land".
    """
    monkeypatch.setenv("COASTLINE_BUFFER_M", "5000")
    times = np.arange(np.datetime64("2024-06-01"), np.datetime64("2024-06-03"))
    _base_inputs(
        tmp_path, write_manifest,
        times=times, jrc=[[1.0, 1.0], [1.0, 1.0]],
        coastline="ghana_land_mask.tif", land_mask=[[1.0, 0.0], [1.0, 0.0]],
    )
    result = build_daily_env_nc("ghana", tmp_path)
    ds = xr.open_dataset(result["env_path"])
    try:
        # Nothing is open sea: the water column is inside the band.
        np.testing.assert_allclose(
            ds["jrc_persistent"].values, [[1.0, 1.0], [1.0, 1.0]]
        )
        np.testing.assert_allclose(
            ds["rainfall"].isel(time=0).values, [[1.0, 1.0], [1.0, 1.0]]
        )
        np.testing.assert_allclose(
            ds["air_temp_c"].isel(time=0).values, [[25.0, 25.0], [25.0, 25.0]]
        )
        np.testing.assert_allclose(
            ds["land_frac"].values, [[1.0, 0.0], [1.0, 0.0]], atol=1e-6
        )
    finally:
        ds.close()


def test_open_sea_has_no_habitat_statics_and_no_candidate(
        tmp_path, monkeypatch, write_manifest):
    """D1: open sea carries zero habitat.

    Dynamic World reports its "water" class at 1.0 on every ocean cell, so
    without masking all five statics, ``h_total > 0`` everywhere and the
    habitat gpkg keeps a breeding candidate in mid-ocean (the engine then
    seeded aquatic cohorts on cells with S = 0). The coastal band keeps its
    statics: lagoons and river mouths are real habitat.
    """
    from mal_core.habitat.potential import static_potential, total_potential

    monkeypatch.setenv("COASTLINE_BUFFER_M", "0")
    times = np.arange(np.datetime64("2024-06-01"), np.datetime64("2024-06-03"))
    # 2x2: column 0 land, column 1 ocean. DW open+water = 1.0 everywhere,
    # i.e. exactly the ocean artefact this test pins.
    _base_inputs(
        tmp_path, write_manifest,
        times=times, jrc=[[0.5, 0.5], [0.5, 0.5]],
        coastline="ghana_land_mask.tif", land_mask=[[1.0, 0.0], [1.0, 0.0]],
        extra_manifest=None,
    )
    result = build_daily_env_nc("ghana", tmp_path)
    ds = xr.open_dataset(result["env_path"])
    try:
        sea = np.array([[False, True], [False, True]])
        for name in ("jrc_persistent", "lc_built", "lc_wetland",
                     "lc_open_plus_water", "lc_crop"):
            arr = ds[name].values
            assert np.all(arr[sea] == 0.0), f"{name} leaks into open sea"
            assert np.any(arr[~sea] > 0.0), f"{name} wiped on land"
        h_total = total_potential(static_potential({
            "jrc_persistent": ds.jrc_persistent.values,
            "lc_built": ds.lc_built.values,
            "lc_wetland": ds.lc_wetland.values,
            "lc_open_plus_water": ds.lc_open_plus_water.values,
            "lc_crop": ds.lc_crop.values,
        }))
        assert np.all(np.asarray(h_total)[sea] == 0.0)
    finally:
        ds.close()

    # The gpkg candidate union follows the statics: land cells only here,
    # i.e. exactly the number of non-sea cells with h_total > 0.
    import geopandas as gpd

    from mal_core.ingest.env import _write_habitat_patches_gpkg

    ds = xr.open_dataset(result["env_path"])
    statics = {
        "jrc_persistent": ds.jrc_persistent.values,
        "lc_built": ds.lc_built.values,
        "lc_wetland": ds.lc_wetland.values,
        "lc_open_plus_water": ds.lc_open_plus_water.values,
        "lc_crop": ds.lc_crop.values,
    }
    ds.close()
    # Minimal AOI stub matching the 2x2 grid written by the fixtures.
    class _Stub:
        slug = "ghana"
        crs = "EPSG:4326"
        bbox = (0.0, 0.0, 2.0, 2.0)

        @staticmethod
        def cells_per_side():
            return (2, 2)

    path = _write_habitat_patches_gpkg(
        tmp_path / "patches.gpkg", statics, _Stub())
    gdf = gpd.read_file(path)
    expected = int((np.asarray(total_potential(static_potential(statics))) > 0).sum())
    assert len(gdf) == expected
    assert len(gdf) < 4, "open sea must not become a candidate cell"


def test_coastline_disabled_by_negative_env(tmp_path, monkeypatch, write_manifest):
    monkeypatch.setenv("COASTLINE_BUFFER_M", "-1")
    times = np.arange(np.datetime64("2024-06-01"), np.datetime64("2024-06-03"))
    _base_inputs(
        tmp_path, write_manifest,
        times=times, jrc=[[1.0, 1.0], [1.0, 1.0]],
        coastline="ghana_land_mask.tif", land_mask=[[1.0, 0.0], [1.0, 0.0]],
    )
    result = build_daily_env_nc("ghana", tmp_path)
    ds = xr.open_dataset(result["env_path"])
    try:
        np.testing.assert_allclose(
            ds["jrc_persistent"].values, [[1.0, 1.0], [1.0, 1.0]]
        )
    finally:
        ds.close()


def test_download_profiles_match_current_abm_contract():
    """Contract-v3.0 profile: rainfall + daily air temp; wind optional;
    coastline retired."""
    registry = discover_downloaders()
    assert registry["chirps"].abm_default_outputs == ["rainfall_daily"]
    assert "air_temp_daily" in registry["era5"].abm_default_outputs
    assert "water_temp" not in registry["era5"].abm_default_outputs
    assert registry["era5"].formats["wind_6hourly"] == "daily"
    assert "dem" not in registry  # retried in plan 01
    assert "dynamic_world" in registry
