"""Tests for mal_commonlib.data.loaders.dem (M1.3a).

The MERIT DEM loader is a thin wrapper around ``requests`` + ``rasterio``.
We assert the synthetic-DEM path (TWI from a Gaussian bump) and the
NaN / flat-area edge cases. The real download is exercised by an integration
test that skips cleanly if the network is unavailable.
"""
from __future__ import annotations

import os
import pathlib

import numpy as np
import pytest
import rasterio
import rioxarray  # noqa: F401
import xarray as xr
from rasterio.transform import from_bounds

from mal_commonlib.aoi import AOI
from mal_commonlib.data.loaders import dem as dem_mod
from mal_commonlib.data.loaders.dem import NODATA_OUT, load_merit_dem
from mal_commonlib.terrain.twi import compute_twi


# -- synthetic DEM helpers ---------------------------------------------------


def _gaussian_bump(h: int, w: int, *, height: float = 100.0, std: float = 5.0) -> np.ndarray:
    yy, xx = np.mgrid[0:h, 0:w]
    cy, cx = (h - 1) / 2.0, (w - 1) / 2.0
    z = height * np.exp(-((yy - cy) ** 2 + (xx - cx) ** 2) / (2.0 * std * std))
    return z.astype(np.float32)


def _wrap_dem(z: np.ndarray, *, cell_size: float = 30.0) -> xr.DataArray:
    h, w = z.shape
    transform = from_bounds(0.0, 0.0, w * cell_size, h * cell_size, w, h)
    da = xr.DataArray(z, dims=("y", "x"), name="elevation")
    da.rio.write_crs("EPSG:32630", inplace=True)
    da.rio.write_transform(transform, inplace=True)
    return da


# -- TWI sanity (DEM loader is paired with the TWI helper) ------------------


def test_dem_synthetic_gaussian_bump_twi() -> None:
    """Gaussian bump → TWI max near the bottom, TWI low at the peak."""
    z = _gaussian_bump(50, 50, height=100.0, std=5.0)
    dem = _wrap_dem(z, cell_size=30.0)
    twi = compute_twi(dem, cell_size_m=30.0)
    assert twi.shape == dem.shape
    assert twi.dtype == np.float32
    valid = twi.values[twi.values != NODATA_OUT]
    assert valid.size > 0
    assert np.isfinite(valid).all()
    # The peak is a local maximum (no contributing area), so the cell at the
    # centre should have a low TWI relative to the global max.
    cy, cx = 25, 25
    assert twi.values[cy, cx] < valid.max()


def test_dem_handles_nan_in_dem() -> None:
    """NaN cells in the DEM propagate to -9999.0 in the TWI."""
    z = _gaussian_bump(40, 40, height=100.0, std=5.0)
    z[20, 20] = np.nan
    dem = _wrap_dem(z, cell_size=30.0)
    twi = compute_twi(dem, cell_size_m=30.0)
    assert twi.values[20, 20] == NODATA_OUT
    # Surrounding cells still finite.
    assert twi.values[20, 21] != NODATA_OUT


def test_dem_flat_area_twi() -> None:
    """A flat DEM (all 0) gives a finite, bounded TWI."""
    z = np.zeros((30, 30), dtype=np.float32)
    dem = _wrap_dem(z, cell_size=30.0)
    twi = compute_twi(dem, cell_size_m=30.0)
    valid = twi.values[twi.values != NODATA_OUT]
    assert np.isfinite(valid).all()
    assert valid.max() < 30.0  # bounded
    assert valid.min() > 0.0


# -- integration test --------------------------------------------------------


@pytest.mark.integration
@pytest.mark.skipif(
    not os.environ.get("MAL_MERIT_NETWORK"),
    reason="MAL_MERIT_NETWORK not set; integration test skipped",
)
def test_dem_download(tmp_path: pathlib.Path) -> None:
    """Real MERIT DEM download for a small AOI. Skips on failure."""
    # Small AOI: 1° × 1° box over Ghana's coast (~1°×1°=4 tiles at 5°).
    aoi = AOI.from_bbox(-1.0, 5.0, 0.0, 6.0, "EPSG:4326", "test-dem", 90)
    try:
        out = load_merit_dem(aoi, cache_dir=tmp_path / "cache")
    except Exception as e:
        pytest.skip(f"MERIT download failed: {e}")
    assert out.dtype == np.float32
    valid = out.values[out.values != NODATA_OUT]
    assert valid.size > 0
    # MERIT elevations in Ghana's coastal plain are 0..1000 m. Allow a wide
    # band: -100..3000 m.
    assert valid.min() > -100.0
    assert valid.max() < 3000.0


# -- NASADEM fallback (unit) -------------------------------------------------


def test_merit_falls_back_to_nasadem(monkeypatch: pytest.MonkeyPatch) -> None:
    """When MERIT download raises FileNotFoundError, fall back to NASADEM.

    Both layers are stubbed so no network is required. The test asserts:
      1. The MERIT download path was attempted and failed.
      2. The NASADEM loader was called exactly once.
      3. The returned DataArray honours the loader's public contract
         (dims, dtype, CRS).
    """
    # 1) Force the MERIT download to fail.
    def _fail_download(*args, **kwargs):  # noqa: ARG001
        raise FileNotFoundError(
            "MERIT upstream 404 (simulated) — falling back to NASADEM"
        )

    monkeypatch.setattr(dem_mod, "_download_tile", _fail_download)

    # 2) Stub the NASADEM loader to return a synthetic valid DataArray.
    called = {"n": 0}

    def _fake_nasadem(aoi: AOI) -> xr.DataArray:
        called["n"] += 1
        h, w = aoi.cells_per_side()
        arr = np.full((h, w), 200.0, dtype=np.float32)
        da = xr.DataArray(arr, dims=("y", "x"), name="elevation")
        transform = from_bounds(*aoi.bbox, w, h)
        da.rio.write_crs(aoi.crs, inplace=True)
        da.rio.write_transform(transform, inplace=True)
        return da

    monkeypatch.setattr(dem_mod, "_load_nasadem_dem", _fake_nasadem)

    # 3) Exercise the public entry point.
    aoi = AOI.from_bbox(-3.5, 4.5, 1.5, 11.5, "EPSG:4326", "ghana-nasadem", 1000)
    out = load_merit_dem(aoi)

    # Assertions
    assert called["n"] == 1, "NASADEM fallback loader was not invoked"
    assert isinstance(out, xr.DataArray)
    assert out.dtype == np.float32
    assert out.dims == ("y", "x")
    assert str(out.rio.crs).upper() == "EPSG:4326"
    # Synthetic fill is 200 m everywhere — the fallback returned our stub.
    assert np.all(out.values == 200.0)


def test_merit_corrupt_cache_triggers_redownload(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path,
) -> None:
    """A non-zero cache file that is not a valid GeoTIFF must be detected
    and replaced with a freshly downloaded valid tile.

    The MERIT upstream now serves a Dropbox login page (HTML) for the
    per-tile URL. ``_download_tile`` writes whatever it gets to cache, so
    a subsequent call would return the cached HTML — which ``rasterio.open``
    cannot read. ``_is_valid_geotiff`` must detect this, fall through to
    re-download, and the resulting tile must be openable.
    """
    import requests

    # 1) Pre-populate the cache with an HTML page — the symptom of a
    # password-gated upstream that returns the Dropbox login page.
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    corrupt_path = cache_dir / "merit_+000_+005.tif"  # the bbox tile is lon0=0, lat0=5
    corrupt_path.write_bytes(b"<html>login required</html>")
    assert corrupt_path.stat().st_size > 0
    # The real validator must reject the HTML.
    assert dem_mod._is_valid_geotiff(corrupt_path) is False

    # 2) Build a 1×1 valid GeoTIFF and capture its bytes for the fake
    # downloader to return.
    real_tif = cache_dir / "merit_+000_+005_valid.tif"
    with rasterio.open(
        real_tif,
        "w",
        driver="GTiff",
        height=1,
        width=1,
        count=1,
        dtype="float32",
        crs="EPSG:4326",
        transform=from_bounds(0.0, 0.0, 5.0, 5.0, 1, 1),
    ) as dst:
        dst.write(np.array([[100.0]], dtype="float32"), indexes=1)
    real_bytes = real_tif.read_bytes()

    # 3) Stub ``requests.get`` to return those bytes — simulating a
    # successful re-download after the corruption was detected.
    class _Resp:
        def __init__(self, body: bytes) -> None:
            self._body = body
            self.status_code = 200

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def raise_for_status(self) -> None:
            return None

        def iter_content(self, chunk_size: int):
            yield self._body

    def _fake_get(url, stream=True, timeout=120, headers=None, allow_redirects=True):  # noqa: ARG001
        return _Resp(real_bytes)

    monkeypatch.setattr(requests, "get", _fake_get)

    # 4) Drive the download loop directly.
    out_path = dem_mod._download_tile(0, 5, cache_dir)

    # The file at ``dest`` is the freshly written GeoTIFF, not the HTML.
    assert out_path == corrupt_path
    assert out_path.exists()
    assert out_path.stat().st_size > 0
    # rasterio must be able to open the new file.
    with rasterio.open(str(out_path)) as src:
        assert src.count >= 1
    # The validator now agrees the cached file is valid.
    assert dem_mod._is_valid_geotiff(out_path) is True
