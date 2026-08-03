"""Tests for CHIRPS v2.0 loaders — unit tests with synthetic data, no network."""
from __future__ import annotations

import inspect
from collections.abc import Sequence
from typing import Callable

import numpy as np
import pytest
import rasterio
import rioxarray  # noqa: F401 — registers .rio accessor
import xarray as xr
from rasterio.transform import from_bounds

from mal_commonlib.aoi import AOI
from mal_commonlib.data.loaders.chirps import (
    load_chirps_rainfall,
    load_chirps_rainfall_daily,
)


# -- helpers ------------------------------------------------------------------


def _small_aoi() -> AOI:
    """10×10 cell AOI for fast unit tests."""
    return AOI.from_bbox(-1.0, 6.0, 0.0, 7.0, "EPSG:4326", "test-chirps", 1000)


def _make_fake_daily_fetch(aoi: AOI, base_value: float = 5.0):
    """Return a _fetch_daily callable that produces synthetic daily rasters.

    Each call returns a (y, x) DataArray on the AOI's grid with values =
    ``base_value + day_offset`` (so different days have slightly different
    values, making concat/stacking verifiable).
    """
    h, w = aoi.cells_per_side()

    def _fetch(year: int, month: int, day: int) -> xr.DataArray:
        arr = np.full((h, w), base_value + day, dtype=np.float32)
        transform = from_bounds(*aoi.bbox, w, h)
        da = xr.DataArray(arr, dims=("y", "x"), coords={
            "y": np.arange(h) * transform.e + transform.f,
            "x": np.arange(w) * transform.a + transform.c,
        })
        da.rio.write_crs(aoi.crs_obj, inplace=True)
        return da

    return _fetch


# -- tests --------------------------------------------------------------------


class TestChirpsDailySignature:
    """load_chirps_rainfall_daily matches the canonical M11 §2.2 signature."""

    def test_has_years_and_months_params(self):
        sig = inspect.signature(load_chirps_rainfall_daily)
        params = sig.parameters
        assert "years" in params, "Missing 'years' parameter"
        assert "months" in params, "Missing 'months' parameter"
        assert "aoi" in params

    def test_no_positional_year_or_month(self):
        """Old singular year/month params must be gone."""
        sig = inspect.signature(load_chirps_rainfall_daily)
        params = sig.parameters
        assert "year" not in params, "Old 'year' param still present"
        assert "month" not in params, "Old 'month' param still present"

    def test_cache_dir_is_kw_only(self):
        sig = inspect.signature(load_chirps_rainfall_daily)
        p = sig.parameters["cache_dir"]
        assert p.kind == inspect.Parameter.KEYWORD_ONLY

    def test_no_output_path_param(self):
        sig = inspect.signature(load_chirps_rainfall_daily)
        assert "output_path" not in sig.parameters

    def test_years_is_sequence(self):
        sig = inspect.signature(load_chirps_rainfall_daily)
        ann = sig.parameters["years"].annotation
        # Should be Sequence[int] or equivalent
        assert "Sequence" in str(ann) or "Sequence" in str(ann)


class TestChirpsDailySingleMonth:
    """Single month request returns 3D (n_days, h, w)."""

    def test_shape(self):
        aoi = _small_aoi()
        fetch = _make_fake_daily_fetch(aoi)
        result = load_chirps_rainfall_daily(
            aoi, years=[2024], months=[6], _fetch_daily=fetch,
        )
        assert result.ndim == 3
        assert result.dims == ("time", "y", "x")
        # June 2024 has 30 days
        assert result.sizes["time"] == 30

    def test_time_coords(self):
        aoi = _small_aoi()
        fetch = _make_fake_daily_fetch(aoi)
        result = load_chirps_rainfall_daily(
            aoi, years=[2024], months=[6], _fetch_daily=fetch,
        )
        import cftime
        times = result.coords["time"].values
        assert len(times) == 30
        # First day should be 2024-06-01
        first = times[0]
        assert isinstance(first, cftime.DatetimeGregorian)
        assert (first.year, first.month, first.day) == (2024, 6, 1)
        # Last day should be 2024-06-30
        last = times[-1]
        assert (last.year, last.month, last.day) == (2024, 6, 30)


class TestChirpsDailyMultiMonth:
    """Multi-month request returns concatenated 3D array."""

    def test_two_months_shape(self):
        aoi = _small_aoi()
        fetch = _make_fake_daily_fetch(aoi)
        result = load_chirps_rainfall_daily(
            aoi, years=[2024], months=[6, 7], _fetch_daily=fetch,
        )
        assert result.ndim == 3
        # June (30) + July (31) = 61 days
        assert result.sizes["time"] == 61

    def test_time_coords_span_months(self):
        aoi = _small_aoi()
        fetch = _make_fake_daily_fetch(aoi)
        result = load_chirps_rainfall_daily(
            aoi, years=[2024], months=[6, 7], _fetch_daily=fetch,
        )
        import cftime
        times = result.coords["time"].values
        first = times[0]
        assert (first.year, first.month, first.day) == (2024, 6, 1)
        last = times[-1]
        assert (last.year, last.month, last.day) == (2024, 7, 31)

    def test_multi_year(self):
        aoi = _small_aoi()
        fetch = _make_fake_daily_fetch(aoi)
        result = load_chirps_rainfall_daily(
            aoi, years=[2024, 2025], months=[1], _fetch_daily=fetch,
        )
        # Jan 2024 (31) + Jan 2025 (31) = 62 days
        assert result.sizes["time"] == 62

    def test_values_not_nan(self):
        aoi = _small_aoi()
        fetch = _make_fake_daily_fetch(aoi, base_value=10.0)
        result = load_chirps_rainfall_daily(
            aoi, years=[2024], months=[6], _fetch_daily=fetch,
        )
        # base_value=10.0 + day offsets → all finite
        assert np.all(np.isfinite(result.values))


class TestChirpsDailyValidation:
    """Edge cases and error handling."""

    def test_bad_month_raises(self):
        aoi = _small_aoi()
        fetch = _make_fake_daily_fetch(aoi)
        with pytest.raises(ValueError, match="month must be in 1..12"):
            load_chirps_rainfall_daily(
                aoi, years=[2024], months=[13], _fetch_daily=fetch,
            )

    def test_bad_year_raises(self):
        aoi = _small_aoi()
        fetch = _make_fake_daily_fetch(aoi)
        with pytest.raises(ValueError, match="CHIRPS starts in 1981"):
            load_chirps_rainfall_daily(
                aoi, years=[1980], months=[6], _fetch_daily=fetch,
            )

    def test_default_months_all_12(self):
        """When months=None, defaults to all 12 months."""
        aoi = _small_aoi()
        fetch = _make_fake_daily_fetch(aoi)
        result = load_chirps_rainfall_daily(
            aoi, years=[2024], _fetch_daily=fetch,
        )
        # 2024 is a leap year: 366 days
        assert result.sizes["time"] == 366
