"""Tests for mal_commonlib.terrain.twi (M1.3a).

These tests are pure-numpy: we build small synthetic DEMs and assert the
expected qualitative properties of the Topographic Wetness Index. The
``compute_twi`` function is deterministic (no RNG, no network).
"""
from __future__ import annotations

import math

import numpy as np
import pytest
import rasterio
import rioxarray  # noqa: F401
import xarray as xr
from rasterio.transform import from_bounds

from mal_commonlib.terrain.twi import NODATA_OUT, compute_twi


# -- helpers ------------------------------------------------------------------


def _gaussian_bump(h: int, w: int, *, height: float = 100.0, std: float = 5.0) -> np.ndarray:
    """Return a 2-D array with a centred Gaussian bump, in metres."""
    yy, xx = np.mgrid[0:h, 0:w]
    cy, cx = (h - 1) / 2.0, (w - 1) / 2.0
    z = height * np.exp(-((yy - cy) ** 2 + (xx - cx) ** 2) / (2.0 * std * std))
    return z.astype(np.float32)


def _inclined_plane(h: int, w: int, *, slope: float = 0.01) -> np.ndarray:
    """Return a 2-D array that tilts linearly from y=0 to y=h-1.

    z(y, x) = slope * y * cell_size, so the downhill direction is +y.
    """
    yy, xx = np.mgrid[0:h, 0:w]
    z = slope * yy
    return z.astype(np.float32)


def _wrap_dem(z: np.ndarray, *, cell_size: float = 30.0) -> xr.DataArray:
    """Wrap a 2-D numpy array in an xr.DataArray with a synthetic 30 m grid."""
    h, w = z.shape
    transform = from_bounds(0.0, 0.0, w * cell_size, h * cell_size, w, h)
    da = xr.DataArray(z, dims=("y", "x"), name="elevation")
    da.rio.write_crs("EPSG:32630", inplace=True)
    da.rio.write_transform(transform, inplace=True)
    return da


# -- tests --------------------------------------------------------------------


def test_twi_returns_float32() -> None:
    z = _gaussian_bump(30, 30)
    dem = _wrap_dem(z, cell_size=30.0)
    out = compute_twi(dem, cell_size_m=30.0)
    assert out.dtype == np.float32
    assert out.dims == ("y", "x")
    assert str(out.rio.crs) == dem.rio.crs.to_string() or out.rio.crs == dem.rio.crs


def test_twi_synthetic_gaussian_bump() -> None:
    """Max TWI is near the bottom of a Gaussian bump; the peak is a source.

    On a Gaussian bump, the centre of the bump is the local maximum (no
    contributing area beyond the cell itself), so its TWI is low. The
    bottom of the bump (the cells with the most upstream cells) has the
    highest TWI.
    """
    z = _gaussian_bump(40, 40, height=100.0, std=6.0)
    dem = _wrap_dem(z, cell_size=30.0)
    out = compute_twi(dem, cell_size_m=30.0)
    arr = out.values
    cy, cx = 19.5, 19.5  # centre of a 40x40 array
    peak = arr[int(cy), int(cx)]
    # The peak should be much smaller than the max TWI.
    finite = np.where(np.isfinite(arr) & (arr != NODATA_OUT))
    non_nodata = arr[finite]
    non_nodata = non_nodata[np.isfinite(non_nodata)]
    assert non_nodata.size > 0
    # The peak's TWI is local minimum (a "summit" with 1 contributing cell
    # and a steep slope). The "bottom" of the bump — the cells below the
    # peak with the largest upstream area — has the highest TWI.
    bottom_row = int(cy) + 12  # well below the centre
    bottom = arr[bottom_row, int(cx)]
    assert bottom > peak


def test_twi_synthetic_inclined_plane() -> None:
    """TWI is higher at the low end of a tilted plane (more upstream cells).

    On a uniformly tilted plane z = slope * y, the high end (large y, high
    z) has only itself as upstream. The low end (small y, low z) has every
    cell above it as upstream. So the contributing area grows from 1 cell
    at the top of the slope to ``h * w`` at the bottom, and TWI is largest
    at the bottom of the slope.
    """
    z = _inclined_plane(20, 10, slope=0.01)
    dem = _wrap_dem(z, cell_size=30.0)
    out = compute_twi(dem, cell_size_m=30.0)
    arr = out.values
    # Skip the 1-cell border (rows 0 and 19 are nodata).
    # The "bottom of the slope" (low z) is at low y indices; the "top of
    # the slope" (high z) is at high y indices.
    bottom_of_slope = arr[2, 5]
    top_of_slope = arr[-3, 5]
    assert np.isfinite(bottom_of_slope)
    assert np.isfinite(top_of_slope)
    assert bottom_of_slope > top_of_slope
    # TWI decreases monotonically down a uniform plane.
    centre_col = arr[1:-1, 5]
    # Skip nodata cells.
    centre_col_valid = centre_col[centre_col != NODATA_OUT]
    diffs = np.diff(centre_col_valid)
    assert (diffs <= 1e-3).all()  # monotonically non-increasing


def test_twi_handles_nan_dem() -> None:
    """NaN cells in the DEM propagate to -9999.0 in the TWI."""
    z = _gaussian_bump(30, 30, height=100.0, std=5.0)
    z[15, 15] = np.nan
    z[10, 20] = np.nan
    dem = _wrap_dem(z, cell_size=30.0)
    out = compute_twi(dem, cell_size_m=30.0)
    assert out.values[15, 15] == NODATA_OUT
    assert out.values[10, 20] == NODATA_OUT
    # The surrounding cells should still have a finite TWI (i.e. not -9999.0).
    assert out.values[15, 16] != NODATA_OUT
    assert out.values[10, 19] != NODATA_OUT


def test_twi_handles_flat_areas() -> None:
    """A flat DEM produces a finite, bounded TWI (no NaN / Inf).

    A perfectly flat DEM has slope = 0, so tan(β) = ε. The accumulation
    still flows to the deterministic D8 neighbour, and the TWI is finite
    and bounded by the accumulated count × cell_size² / ε.
    """
    z = np.zeros((20, 20), dtype=np.float32)
    dem = _wrap_dem(z, cell_size=30.0)
    out = compute_twi(dem, cell_size_m=30.0)
    arr = out.values
    valid = arr[arr != NODATA_OUT]
    assert valid.size > 0
    # No NaN or Inf on the flat case.
    assert np.all(np.isfinite(valid))
    # The ε guard keeps TWI bounded; for cell_size=30 and ε=tan(0.1°)≈0.0017,
    # the worst case (one cell, ε-slope) gives ln(900/0.0017) ≈ 13.3.
    assert valid.max() < 30.0  # bounded
    assert valid.min() > 0.0  # all values positive (ln of something > 1)


def test_twi_edge_cells_are_nodata() -> None:
    """The 1-cell border (where np.gradient uses one-sided differences) is -9999.0."""
    z = _gaussian_bump(30, 30, height=100.0, std=5.0)
    dem = _wrap_dem(z, cell_size=30.0)
    out = compute_twi(dem, cell_size_m=30.0)
    arr = out.values
    # Top row.
    assert (arr[0, :] == NODATA_OUT).all()
    # Bottom row.
    assert (arr[-1, :] == NODATA_OUT).all()
    # Left column.
    assert (arr[:, 0] == NODATA_OUT).all()
    # Right column.
    assert (arr[:, -1] == NODATA_OUT).all()


def test_twi_preserves_crs() -> None:
    z = _gaussian_bump(20, 20)
    dem = _wrap_dem(z, cell_size=30.0)
    out = compute_twi(dem, cell_size_m=30.0)
    assert out.rio.crs is not None
    assert dem.rio.crs == out.rio.crs


def test_twi_infers_cell_size_from_rio() -> None:
    """When cell_size_m is None, infer from .rio.resolution()."""
    z = _gaussian_bump(20, 20)
    dem = _wrap_dem(z, cell_size=90.0)
    out = compute_twi(dem)  # no explicit cell_size_m
    # TWI should still be finite in the interior.
    arr = out.values
    interior = arr[2:-2, 2:-2]
    assert np.all(np.isfinite(interior[interior != NODATA_OUT]))


def test_twi_rejects_non_2d_input() -> None:
    z = np.zeros((10, 10, 3), dtype=np.float32)
    dem = xr.DataArray(z, dims=("y", "x", "band"), name="elevation")
    dem.rio.write_crs("EPSG:32630", inplace=True)
    with pytest.raises(ValueError):
        compute_twi(dem, cell_size_m=30.0)


def test_twi_rejects_missing_dims() -> None:
    z = np.zeros((10, 10), dtype=np.float32)
    dem = xr.DataArray(z, dims=("a", "b"), name="elevation")
    dem.rio.write_crs("EPSG:32630", inplace=True)
    with pytest.raises(ValueError):
        compute_twi(dem, cell_size_m=30.0)
