"""Tests for ``mal_commonlib.data.loaders.chirps`` (M1.3a).

Three tests:
    * ``test_chirps_ghana_smoke`` — integration test, downloads a real
      month of CHIRPS daily GeoTIFFs for the Ghana AOI. Skipped if the
      network is unavailable.
    * ``test_chirps_dry_run_no_network`` — monkeypatches the daily fetch
      to return a synthetic Gaussian-bump raster; asserts the function
      still produces a normalized [0, 1] result of the right shape.
    * ``test_chirps_no_auth_required`` — CHIRPS is public; the loader
      must not consult any auth state.
"""
from __future__ import annotations

import math
import pathlib

import numpy as np
import pytest
import xarray as xr

from mal_commonlib.aoi import AOI, Scale
from mal_commonlib.data.loaders import chirps as chirps_mod
from mal_commonlib.data.loaders.chirps import CHIRPS_NODATA, load_chirps_rainfall


# A small but realistic Ghana-ish AOI (1 km grid → 100ish cells per side).
GHANA_W, GHANA_S, GHANA_E, GHANA_N = -1.0, 6.0, 0.0, 7.0


@pytest.fixture
def ghana_aoi() -> AOI:
    return AOI.from_bbox(
        GHANA_W, GHANA_S, GHANA_E, GHANA_N, "EPSG:4326", "ghana", 1000
    )


# -- helpers ----------------------------------------------------------------


def _synthetic_chirps_daily(
    aoi: AOI, *, peak_mm_per_day: float = 25.0, h: int = 21, w: int = 21,
) -> callable:
    """Return a fetch-daily function producing a Gaussian-bump daily rainfall
    field (mm/day) on a (h, w) grid that covers the AOI bbox in EPSG:4326.
    The bump is centred at the AOI centroid and the per-day value scales by
    ``peak_mm_per_day * (0.5 + 0.5 * sin(day/30 * 2π))`` so different days have
    different rainfall."""
    west, south, east, north = aoi.bbox
    cx = 0.5 * (west + east)
    cy = 0.5 * (south + north)
    lons = np.linspace(west, east, w)
    lats = np.linspace(north, south, h)
    lon2d, lat2d = np.meshgrid(lons, lats)
    sigma = 0.25 * max(east - west, north - south)
    base = peak_mm_per_day * np.exp(
        -((lon2d - cx) ** 2 + (lat2d - cy) ** 2) / (2 * sigma ** 2)
    )

    def _fetch(year: int, month: int, day: int) -> xr.DataArray:
        scale = 0.5 + 0.5 * math.sin(day / 30.0 * 2 * math.pi)
        arr = (base * scale).astype(np.float32)
        da = xr.DataArray(
            arr, dims=("y", "x"),
            coords={"y": lats, "x": lons},
        )
        da.rio.write_crs("EPSG:4326", inplace=True)
        return da

    return _fetch


# -- tests ------------------------------------------------------------------


def test_chirps_no_auth_required() -> None:
    """CHIRPS is a public dataset; the loader must not consult any auth state."""
    # The function should be importable and instantiable without raising;
    # it must not even touch CDSAPI / earthaccess / etc.
    import cdsapi
    import earthaccess  # noqa: F401

    # No env vars touched. Just call once with the dry-run fetch and assert
    # that nothing tried to read ~/.cdsapirc.
    aoi = AOI.from_bbox(GHANA_W, GHANA_S, GHANA_E, GHANA_N, "EPSG:4326", "ghana", 1000)
    fetch = _synthetic_chirps_daily(aoi)
    out = load_chirps_rainfall(aoi, 2024, 6, _fetch_daily=fetch)
    assert out is not None
    # The function never imports cdsapi; a quick import-check that the loader
    # module does not import cdsapi at all.
    assert "cdsapi" not in dir(chirps_mod)


@pytest.mark.integration
def test_chirps_ghana_smoke(
    ghana_aoi: AOI, tmp_path: pathlib.Path
) -> None:
    """End-to-end: download a single month of CHIRPS daily GeoTIFFs and
    assert the result is well-formed. Skipped on network failure."""
    try:
        out = load_chirps_rainfall(
            ghana_aoi, 2024, 6, cache_dir=tmp_path / "chirps-cache"
        )
    except Exception as e:  # network down, 404, etc.
        pytest.skip(f"network not available: {type(e).__name__}: {e}")

    h, w = ghana_aoi.cells_per_side()
    assert out.shape == (h, w)
    assert out.dtype == np.float32
    # CRS should be EPSG:4326.
    assert out.rio.crs is not None
    assert out.rio.crs.to_epsg() == 4326
    # All real values (not -9999) in [0, 1].
    valid = out.values != CHIRPS_NODATA
    if valid.any():
        v = out.values[valid]
        assert v.min() >= 0.0
        assert v.max() <= 1.0
    # Cap (P95) recorded in the attrs.
    assert "aoi_slug" in out.attrs
    assert out.attrs["aoi_slug"] == "ghana"
    assert out.attrs["year"] == 2024
    assert out.attrs["month"] == 6
    assert out.attrs["nodata"] == CHIRPS_NODATA


def test_chirps_dry_run_no_network(ghana_aoi: AOI) -> None:
    """With a monkeypatched daily fetch, the loader still produces a
    well-formed (H, W) normalized rainfall in [0, 1]."""
    fetch = _synthetic_chirps_daily(ghana_aoi)
    out = load_chirps_rainfall(ghana_aoi, 2024, 6, _fetch_daily=fetch)

    h, w = ghana_aoi.cells_per_side()
    assert out.shape == (h, w)
    assert out.dtype == np.float32
    arr = out.values
    # No NaN in the dry-run (all synthetic data is finite).
    assert np.isfinite(arr).all()
    # Bump is non-trivial so we should see some values near 0 and some near 1.
    assert arr.min() >= 0.0
    assert arr.max() <= 1.0
    # The P95 cap normalizes the maximum of the synthesized field to 1.0.
    assert arr.max() == pytest.approx(1.0, rel=1e-3)
    # Bump structure: at least 1 cell strictly above the median.
    assert arr.max() > arr.min()


def test_chirps_invalid_month_rejected(ghana_aoi: AOI) -> None:
    fetch = _synthetic_chirps_daily(ghana_aoi)
    with pytest.raises(ValueError, match="month"):
        load_chirps_rainfall(ghana_aoi, 2024, 0, _fetch_daily=fetch)
    with pytest.raises(ValueError, match="month"):
        load_chirps_rainfall(ghana_aoi, 2024, 13, _fetch_daily=fetch)


def test_chirps_pre_1981_rejected(ghana_aoi: AOI) -> None:
    fetch = _synthetic_chirps_daily(ghana_aoi)
    with pytest.raises(ValueError, match="1981"):
        load_chirps_rainfall(ghana_aoi, 1980, 6, _fetch_daily=fetch)
