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
    """Daily rainfall survives while M12 masks enrich static water."""
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


def test_download_profiles_match_current_abm_contract():
    """Default profile excludes unused monthly, wind, river and landcover outputs."""
    registry = discover_downloaders()
    assert registry["chirps"].abm_default_outputs == ["rainfall_daily"]
    assert registry["era5"].abm_default_outputs == ["water_temp"]
    assert registry["era5"].formats["wind_6hourly"] == "daily"
    assert registry["hydrolakes"].abm_default_outputs == ["permanent_lakes"]
    assert registry["hydrorivers"].abm_default_outputs == []
    assert registry["worldcover"].abm_default_outputs == []
