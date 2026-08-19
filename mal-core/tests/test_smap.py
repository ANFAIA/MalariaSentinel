"""Tests for the SMAP salinity integration (M7.8, Phase 5-Python).

Covers:
  * registry discovery of the ``smap`` downloader
  * the ``monthly_nc`` runner branch (multi-year monthly NetCDF + manifest)
  * the synthetic SMAP loader path (PSU scaling, lon conversion, fill/land mask)
  * the daily-NC ingest broadcast (monthly salinity -> per-day salinity_ppt)
  * backward compatibility when no salinity file is present
"""
from __future__ import annotations

import numpy as np
import rasterio
import xarray as xr
from rasterio.transform import from_bounds, from_origin

import mal_core.download.runner as runner_mod
import mal_commonlib.data.loaders.smap as smap_mod
from mal_core.download.manifest import read_manifest
from mal_core.download.registry import discover_downloaders
from mal_core.download.runner import _standard_path_monthly_nc
from mal_core.ingest.daily_nc import build_daily_env_nc
from mal_commonlib.aoi import AOI
from mal_commonlib.data.loaders.smap import load_smap_salinity_synthetic


def _ghana() -> AOI:
    return AOI.from_slug("ghana")


# ---------------------------------------------------------------- registry


def test_smap_registered_in_discovery():
    registry = discover_downloaders()
    assert "smap" in registry
    spec = registry["smap"]
    assert spec.requires_auth == ["earthdata"]
    assert spec.is_time_series is True
    assert spec.formats == {"salinity": "monthly_nc"}
    assert spec.manifest_keys == {"salinity": "smap_salinity"}
    assert spec.outputs["salinity"].__name__ == "load_smap_salinity"


def test_standard_path_monthly_nc(tmp_path):
    import mal_core.download.runner as mod
    original = mod._REPO_ROOT
    mod._REPO_ROOT = tmp_path
    try:
        p = _standard_path_monthly_nc("ghana", "salinity", 2024, 2025)
        assert p == tmp_path / "data" / "ghana" / "ghana_salinity_2024_2025_monthly.nc"
    finally:
        mod._REPO_ROOT = original


# ------------------------------------------------------- monthly_nc branch


def _fake_salinity_loader(aoi=None, *, years=None, months=None, cache_dir=None):
    times = [
        np.datetime64(f"{y:04d}-{m:02d}-01")
        for y in (2024, 2025) for m in (1, 6)
    ]
    vals = np.full((len(times), 2, 2), np.float32(33.0))
    vals[0, 0, 0] = np.nan
    da = xr.DataArray(
        vals,
        dims=("time", "y", "x"),
        coords={
            "time": times,
            "y": np.array([0.0, 0.25]),
            "x": np.array([0.0, 0.25]),
        },
        name="salinity",
    )
    da.rio.write_crs("EPSG:4326", inplace=True)
    return da


def test_runner_monthly_nc_branch(tmp_path, monkeypatch):
    monkeypatch.setattr(runner_mod, "_check_auth", lambda spec: True)
    # Replace only the smap outputs slot; the DOWNLOADER dict is cached, so we
    # mutate the dict that discover_downloaders() reads.
    monkeypatch.setitem(
        smap_mod.DOWNLOADER["outputs"], "salinity", _fake_salinity_loader
    )
    # Route output + manifest under tmp_path via _REPO_ROOT (matches the
    # existing _standard_path_daily test pattern).
    original = runner_mod._REPO_ROOT
    runner_mod._REPO_ROOT = tmp_path
    try:
        results = runner_mod.run_download(
            "ghana",
            datasets=["smap"], outputs=["salinity"],
            years=[2024, 2025], months=[1, 6],
        )
    finally:
        runner_mod._REPO_ROOT = original

    assert results["smap"]["status"] == "ok"

    out = tmp_path / "data" / "ghana" / "ghana_salinity_2024_2025_monthly.nc"
    assert out.exists(), f"expected monthly NC at {out}"

    manifest = read_manifest("ghana", tmp_path / "data")
    entry = manifest["datasets"]["smap_salinity"]
    assert entry["format"] == "nc"
    assert entry["period"] == {"start": "2024-01-01", "end": "2025-06-01"}
    assert list(entry["files"].values()) == ["ghana_salinity_2024_2025_monthly.nc"]

    with xr.open_dataset(out) as ds:
        assert "salinity" in ds
        assert ds.sizes["time"] == 4
        assert np.isnan(ds["salinity"].isel(time=0)[0, 0])
        assert ds["salinity"].isel(time=0)[1, 1] == 33.0


# --------------------------------------------------------------- loader


def test_load_smap_salinity_synthetic_scaling_lon_fill():
    out = load_smap_salinity_synthetic(_ghana(), years=[2024], months=[1])
    assert out.attrs.get("units") == "psu"
    assert "time" not in out.dims  # single month -> 2D

    # PSU scaling: raw 33000 * 1e-3 -> 33.0
    assert np.nanmax(out.values) == 33.0
    # ocean cell (interior of Ghana bbox, lat < 10) is 33.0
    assert out.values[0, 0] == 33.0

    # lon converted 0..360 -> -180..180: all longitudes are in range, negatives exist
    assert out.x.values.max() < 180.0
    assert (out.x.values < 0.0).any()
    # the fill cell was at lon 359.875 -> now -0.125, inside the bbox, masked to NaN
    lon_fill = -0.125
    i_x = int(np.argmin(np.abs(out.x.values - lon_fill)))
    assert np.isclose(out.x.values[i_x], lon_fill)
    assert np.isnan(out.values[:, i_x]).any()

    # land cells (lat > 10 within the Ghana bbox) are masked to NaN
    i_y = int(np.argmin(np.abs(out.y.values - 10.375)))
    assert np.isnan(out.values[i_y, :]).all()


def test_load_smap_salinity_synthetic_multimonth_time():
    out = load_smap_salinity_synthetic(_ghana(), years=[2024], months=[1, 2])
    assert out.dims == ("time", "y", "x")
    assert out.sizes["time"] == 2
    assert str(out.time.values[0])[:10] == "2024-01-01"
    assert str(out.time.values[1])[:10] == "2024-02-01"


def test_smap_gap_month_produces_nan_not_crash():
    """A missing month (mission gap) yields an all-NaN slice, not a crash."""
    aoi = _ghana()

    def fetch(year, month):
        if month == 7:
            return None  # 2019-06..07 gap simulated
        return smap_mod._synthetic_raw_ds(aoi)

    out = smap_mod.load_smap_salinity(
        aoi, years=[2019], months=[6, 7], _fetch_monthly=fetch
    )
    assert out.sizes["time"] == 2
    assert np.isnan(out.sel(time="2019-07-01").values).all()
    assert np.nanmax(out.sel(time="2019-06-01").values) == 33.0


# ------------------------------------------------------------ ingest


def _write_tif(path, values):
    values = np.asarray(values, dtype=np.float32)
    with rasterio.open(
        path, "w", driver="GTiff",
        height=values.shape[0], width=values.shape[1], count=1,
        dtype="float32", crs="EPSG:4326",
        transform=from_origin(0, 2, 1, 1), nodata=-9999.0,
    ) as dst:
        dst.write(values, 1)


def _write_rainfall(tmp_path, times):
    rainfall = np.ones((len(times), 2, 2), dtype=np.float32)
    xr.Dataset(
        {"rainfall": (("time", "y", "x"), rainfall)},
        coords={"time": times, "y": [0, 1], "x": [0, 1]},
    ).to_netcdf(tmp_path / "ghana_rainfall_daily_2024_2025_daily.nc")


def _write_static_inputs(tmp_path):
    _write_tif(tmp_path / "ghana_water_occurrence.tif", [[0.1, 0.1], [0.1, 0.1]])
    _write_tif(tmp_path / "ghana_water_temp_2024.tif", [[25.0, 25.0], [25.0, 25.0]])
    _write_tif(tmp_path / "ghana_ndvi_2024.tif", [[0.5, 0.5], [0.5, 0.5]])


def test_daily_nc_salinity_monthly_broadcast(tmp_path):
    times = np.arange(np.datetime64("2024-06-01"), np.datetime64("2024-08-01"))
    _write_rainfall(tmp_path, times)
    _write_static_inputs(tmp_path)

    # Monthly salinity on the same (y, x) grid as the env: June 33 PSU with a
    # no-data cell; July 30 PSU everywhere.
    y = np.array([0.0, 1.0])
    x = np.array([0.0, 1.0])
    s = np.array(
        [
            [[33.0, 33.0], [33.0, np.nan]],  # June
            [[30.0, 30.0], [30.0, 30.0]],    # July
        ],
        dtype=np.float32,
    )
    sda = xr.DataArray(
        s,
        dims=("time", "y", "x"),
        coords={
            "time": np.array(["2024-06-01", "2024-07-01"], dtype="datetime64[D]"),
            "y": y, "x": x,
        },
        name="salinity",
    )
    sda.rio.write_crs("EPSG:4326", inplace=True)
    sda.rio.write_transform(from_bounds(0, 0, 1, 1, 2, 2), inplace=True)
    sda.to_netcdf(tmp_path / "ghana_salinity_2024_2025_monthly.nc")

    result = build_daily_env_nc("ghana", tmp_path)
    assert "salinity_ppt" in result["variables"]

    ds = xr.open_dataset(result["env_path"])
    try:
        assert "salinity_ppt" in ds
        sp = ds["salinity_ppt"]
        assert sp.attrs["units"] == "psu"
        assert ds.sizes["time"] == len(times)
        # June days carry the June value; the no-data cell -> freshwater 0.0
        np.testing.assert_allclose(
            sp.isel(time=0).values, [[33.0, 33.0], [33.0, 0.0]]
        )
        np.testing.assert_allclose(
            sp.isel(time=29).values, [[33.0, 33.0], [33.0, 0.0]]
        )
        # July days carry the July value
        np.testing.assert_allclose(
            sp.isel(time=30).values, [[30.0, 30.0], [30.0, 30.0]]
        )
        np.testing.assert_allclose(
            sp.isel(time=-1).values, [[30.0, 30.0], [30.0, 30.0]]
        )
    finally:
        ds.close()


def test_daily_nc_no_salinity_backward_compat(tmp_path):
    times = np.arange(np.datetime64("2024-06-01"), np.datetime64("2024-07-01"))
    _write_rainfall(tmp_path, times)
    _write_static_inputs(tmp_path)

    result = build_daily_env_nc("ghana", tmp_path)
    assert "salinity_ppt" not in result["variables"]

    ds = xr.open_dataset(result["env_path"])
    try:
        assert "salinity_ppt" not in ds
        assert "rainfall" in ds
    finally:
        ds.close()