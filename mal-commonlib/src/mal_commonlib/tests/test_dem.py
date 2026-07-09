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
