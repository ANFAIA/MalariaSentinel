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
    """Saltwater filter (preserved): ocean cells' JRC persistent plane is
    zeroed; the daily channels keep their values."""
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
        # rainfall survives everywhere (the filter targets statics).
        assert float(ds["rainfall"].isel(time=0).values.max()) == 1.0
        assert "coastline_applied" not in result
    finally:
        ds.close()


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
