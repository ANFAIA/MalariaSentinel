"""Small end-to-end checks for M12 water composition and download profiles."""
from __future__ import annotations

import numpy as np
import rasterio
import xarray as xr
from rasterio.transform import from_origin

from mal_core.ingest.daily_nc import build_daily_env_nc
from mal_core.download.registry import discover_downloaders


def _write_tif(path, values):
    values = np.asarray(values, dtype=np.float32)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=values.shape[0],
        width=values.shape[1],
        count=1,
        dtype="float32",
        crs="EPSG:4326",
        transform=from_origin(0, 2, 1, 1),
        nodata=-9999.0,
    ) as dst:
        dst.write(values, 1)


def test_m12_two_month_env_uses_permanent_masks(tmp_path):
    """Daily rainfall survives while M12 masks enrich static water.

    Cell layout (2x2): lake, JRC-low, river, WorldCover-water. JRC base is
    [[0.0, 0.1], [0.0, 0.0]]. Expected ``water_frac`` per cell:
      - (0,0): max(JRC=0, lake=1) = 1.0 (lake)
      - (0,1): JRC=0.1 (no mask)        = 0.1 (low-JRC cell)
      - (1,0): max(JRC=0, river=1)      = 1.0 (river)
      - (1,1): max(JRC=0, wc_water=1)   = 1.0 (WorldCover water)
    Wetland contributes diagnostic-only and does not raise any cell.
    """
    times = np.arange(np.datetime64("2024-06-01"), np.datetime64("2024-08-01"))
    rainfall = np.ones((len(times), 2, 2), dtype=np.float32)
    rainfall[10, 0, 0] = 20.0
    xr.Dataset(
        {"rainfall": (("time", "y", "x"), rainfall)},
        coords={"time": times, "y": [0, 1], "x": [0, 1]},
    ).to_netcdf(tmp_path / "ghana_rainfall_daily_2024_2025_daily.nc")

    _write_tif(tmp_path / "ghana_water_occurrence.tif", [[0.0, 0.1], [0.0, 0.0]])
    _write_tif(tmp_path / "ghana_water_temp_2024.tif", [[25.0, 25.0], [25.0, 25.0]])
    _write_tif(tmp_path / "ghana_ndvi_2024.tif", [[0.5, 0.5], [0.5, 0.5]])
    _write_tif(tmp_path / "ghana_permanent_lakes.tif", [[1.0, 0.0], [0.0, 0.0]])
    _write_tif(tmp_path / "ghana_permanent_rivers.tif", [[0.0, 0.0], [1.0, 0.0]])
    _write_tif(tmp_path / "ghana_wc_permanent_water.tif", [[0.0, 0.0], [0.0, 1.0]])
    _write_tif(tmp_path / "ghana_wc_wetland.tif", [[0.0, 1.0], [0.0, 0.0]])

    result = build_daily_env_nc("ghana", tmp_path)
    ds = xr.open_dataset(result["env_path"])
    try:
        assert ds.sizes["time"] == len(times)
        np.testing.assert_allclose(
            ds["water_frac"].isel(time=0).values,
            [[1.0, 0.1], [1.0, 1.0]],
        )
        assert "permanent_water_mask" in ds
        assert "m12_permanent_lakes" in ds
        assert "m12_permanent_rivers" in ds
        assert "m12_worldcover_permanent_water" in ds
        assert "wetland_mask" in ds
        assert result["m12_enriched"] is True
    finally:
        ds.close()


def test_jrc_only_path_emits_permanent_water_mask(tmp_path):
    """When no M12 enrichment TIFs are present, daily_nc still derives
    permanent_water_mask from the JRC+coast result (M12-fix 2026-08-26).

    This previously failed: the mask was only emitted when hydrolakes/
    worldcover enrichment was on disk, leaving ``permanent_water_mask``
    empty and forcing ``hab_type='pluvial_pool'`` for every habitat patch.
    """
    times = np.arange(np.datetime64("2024-06-01"), np.datetime64("2024-06-03"))
    rainfall = np.ones((len(times), 2, 2), dtype=np.float32)
    xr.Dataset(
        {"rainfall": (("time", "y", "x"), rainfall)},
        coords={"time": times, "y": [0, 1], "x": [0, 1]},
    ).to_netcdf(tmp_path / "ghana_rainfall_daily_2024_2025_daily.nc")

    _write_tif(tmp_path / "ghana_water_occurrence.tif", [[0.5, 0.7], [0.0, 0.0]])
    _write_tif(tmp_path / "ghana_water_temp_2024.tif", [[25.0, 25.0], [25.0, 25.0]])
    _write_tif(tmp_path / "ghana_ndvi_2024.tif", [[0.5, 0.5], [0.5, 0.5]])
    # No permanent_lakes / permanent_rivers / wc_permanent_water TIFs.
    # No coastline_land_mask.tif either (so JRC base is used as-is).

    result = build_daily_env_nc("ghana", tmp_path)
    ds = xr.open_dataset(result["env_path"])
    try:
        assert "permanent_water_mask" in ds, (
            "permanent_water_mask must be present even without M12 enrichment"
        )
        pwm = ds["permanent_water_mask"].isel(time=0).values
        # All water_frac < 1.0 cells (0.5, 0.7, 0.0, 0.0) → pwm == 0 everywhere.
        np.testing.assert_array_equal(
            pwm, [[0.0, 0.0], [0.0, 0.0]],
        )
        # And the diagnostic variable for the JRC-derived mask is present.
        assert "m12_jrc_permanent_water" in ds
    finally:
        ds.close()


def test_habitat_excludes_open_ocean_cells(tmp_path, monkeypatch):
    """Open-ocean cells with JRC>0 must NOT become pluvial_pool patches
    even when the raw JRC TIF sees them as water (M12-fix 2026-08-26).

    The saltwater filter in daily_nc removes permanent water from open
    ocean but the gpkg is built from the RAW JRC TIF so we must re-apply
    the open-ocean exclusion here too. Otherwise the coastline strip
    of pluvial pools becomes a band of "ocean" patches that overlap the
    ocean boundary shown in m12_water_pipeline.png panel (b).
    """
    times = np.arange(np.datetime64("2024-06-01"), np.datetime64("2024-06-03"))
    rainfall = np.ones((len(times), 2, 2), dtype=np.float32)
    xr.Dataset(
        {"rainfall": (("time", "y", "x"), rainfall)},
        coords={"time": times, "y": [0, 1], "x": [0, 1]},
    ).to_netcdf(tmp_path / "ghana_rainfall_daily_2024_2025_daily.nc")

    _write_tif(tmp_path / "ghana_water_occurrence.tif", [[0.5, 0.0], [0.7, 0.0]])
    _write_tif(tmp_path / "ghana_water_temp_2024.tif", [[25.0, 25.0], [25.0, 25.0]])
    _write_tif(tmp_path / "ghana_ndvi_2024.tif", [[0.5, 0.5], [0.5, 0.5]])

    # Land mask: (0,0)=1 (land), (0,1)=0 (ocean), (1,0)=1 (land), (1,1)=0 (ocean)
    _write_tif(tmp_path / "ghana_land_mask.tif", [[1.0, 0.0], [1.0, 0.0]])

    monkeypatch.setenv("COASTLINE_BUFFER_M", "0")

    result = build_daily_env_nc("ghana", tmp_path)
    ds = xr.open_dataset(result["env_path"])
    try:
        wf = ds["water_frac"].isel(time=0).values
        # Saltwater filter drops ocean cells (col 1) — only (0,0) and (1,0) survive.
        np.testing.assert_allclose(
            wf, [[0.5, 0.0], [0.7, 0.0]],
            err_msg="filter should keep land JRC values, drop ocean",
        )
    finally:
        ds.close()


def test_jrc_permanent_water_mask_jrc_only_high(tmp_path):
    """JRC=1.0 cells produce permanent_water_mask=1 with no M12 enrichment
    and no coastline file (i.e. raw JRC binarised at the input resolution)."""
    times = np.arange(np.datetime64("2024-06-01"), np.datetime64("2024-06-03"))
    rainfall = np.ones((len(times), 2, 2), dtype=np.float32)
    xr.Dataset(
        {"rainfall": (("time", "y", "x"), rainfall)},
        coords={"time": times, "y": [0, 1], "x": [0, 1]},
    ).to_netcdf(tmp_path / "ghana_rainfall_daily_2024_2025_daily.nc")

    _write_tif(tmp_path / "ghana_water_occurrence.tif", [[1.0, 0.5], [1.0, 0.0]])
    _write_tif(tmp_path / "ghana_water_temp_2024.tif", [[25.0, 25.0], [25.0, 25.0]])
    _write_tif(tmp_path / "ghana_ndvi_2024.tif", [[0.5, 0.5], [0.5, 0.5]])

    result = build_daily_env_nc("ghana", tmp_path)
    ds = xr.open_dataset(result["env_path"])
    try:
        pwm = ds["permanent_water_mask"].isel(time=0).values
        np.testing.assert_array_equal(pwm, [[1.0, 0.0], [1.0, 0.0]])
    finally:
        ds.close()


def test_coastline_zeros_ocean_cells_but_keeps_coastal(tmp_path, monkeypatch):
    """Saltwater filter: cells inside the buffered land mask stay, outside go to 0.

    JRC base ``[[1.0, 1.0], [1.0, 1.0]]`` (everything wet). Land mask
    ``[[1.0, 0.0], [1.0, 0.0]]`` with a 1-cell buffer applied at the
    loader level — buffered mask becomes ``[[1.0, 1.0], [1.0, 1.0]]``
    (radius=1, neighbours all become land), so JRC survives everywhere
    except where the buffered mask is 0. We test the strictly unbuffered
    path: write a pre-baked land_mask TIF and disable the in-``daily_nc``
    buffer via ``COASTLINE_BUFFER_M=0`` so the loader's pre-baked mask is
    the source of truth.
    """
    monkeypatch.setenv("COASTLINE_BUFFER_M", "0")

    times = np.arange(np.datetime64("2024-06-01"), np.datetime64("2024-06-03"))
    rainfall = np.ones((len(times), 2, 2), dtype=np.float32)
    xr.Dataset(
        {"rainfall": (("time", "y", "x"), rainfall)},
        coords={"time": times, "y": [0, 1], "x": [0, 1]},
    ).to_netcdf(tmp_path / "ghana_rainfall_daily_2024_2025_daily.nc")

    _write_tif(tmp_path / "ghana_water_occurrence.tif", [[1.0, 1.0], [1.0, 1.0]])
    _write_tif(tmp_path / "ghana_water_temp_2024.tif", [[25.0, 25.0], [25.0, 25.0]])
    _write_tif(tmp_path / "ghana_ndvi_2024.tif", [[0.5, 0.5], [0.5, 0.5]])

    _write_tif(tmp_path / "ghana_land_mask.tif", [[1.0, 0.0], [1.0, 0.0]])

    result = build_daily_env_nc("ghana", tmp_path)
    ds = xr.open_dataset(result["env_path"])
    try:
        np.testing.assert_allclose(
            ds["water_frac"].isel(time=0).values,
            [[1.0, 0.0], [1.0, 0.0]],
        )
        assert "coastline_applied" not in result  # internal flag, not exported
    finally:
        ds.close()


def test_coastline_disabled_by_negative_env(tmp_path, monkeypatch):
    """Setting COASTLINE_BUFFER_M to a negative value disables the filter entirely."""
    monkeypatch.setenv("COASTLINE_BUFFER_M", "-1")

    times = np.arange(np.datetime64("2024-06-01"), np.datetime64("2024-06-03"))
    rainfall = np.ones((len(times), 2, 2), dtype=np.float32)
    xr.Dataset(
        {"rainfall": (("time", "y", "x"), rainfall)},
        coords={"time": times, "y": [0, 1], "x": [0, 1]},
    ).to_netcdf(tmp_path / "ghana_rainfall_daily_2024_2025_daily.nc")

    _write_tif(tmp_path / "ghana_water_occurrence.tif", [[1.0, 1.0], [1.0, 1.0]])
    _write_tif(tmp_path / "ghana_water_temp_2024.tif", [[25.0, 25.0], [25.0, 25.0]])
    _write_tif(tmp_path / "ghana_ndvi_2024.tif", [[0.5, 0.5], [0.5, 0.5]])
    _write_tif(tmp_path / "ghana_land_mask.tif", [[1.0, 0.0], [1.0, 0.0]])

    result = build_daily_env_nc("ghana", tmp_path)
    ds = xr.open_dataset(result["env_path"])
    try:
        np.testing.assert_allclose(
            ds["water_frac"].isel(time=0).values,
            [[1.0, 1.0], [1.0, 1.0]],
        )
    finally:
        ds.close()


def test_download_profiles_match_current_abm_contract():
    """Default profile excludes unused monthly, wind, river and landcover outputs."""
    registry = discover_downloaders()
    assert registry["chirps"].abm_default_outputs == ["rainfall_daily"]
    assert registry["era5"].abm_default_outputs == ["water_temp"]
    assert registry["era5"].formats["wind_6hourly"] == "daily"
    assert "coastline" in registry
    assert registry["coastline"].abm_default_outputs == ["land_mask"]
    assert registry["hydrorivers"].abm_default_outputs == []
    assert "hydrolakes" not in registry
