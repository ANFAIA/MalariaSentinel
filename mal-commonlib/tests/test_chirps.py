"""Tests for CHIRPS loaders — unit tests with synthetic data, no network."""
from __future__ import annotations

import inspect

import numpy as np
import pytest
import xarray as xr
import rioxarray  # noqa: F401

from mal_commonlib.aoi import AOI
from mal_commonlib.data.loaders.chirps import (
    load_chirps_rainfall_daily,
    DOWNLOADER,
)


def _small_aoi() -> AOI:
    """10x10 cell AOI for fast unit tests."""
    return AOI.from_bbox(-1.0, 6.0, 0.0, 7.0, "EPSG:4326", "test-chirps", 1000)


def _mock_fetch_daily(aoi: AOI):
    """Return a _fetch_daily hook that generates synthetic daily rasters."""
    h, w = aoi.cells_per_side()
    counter = [0]

    def _fetch(year: int, month: int, day: int) -> xr.DataArray:
        counter[0] += 1
        arr = np.full((h, w), float(counter[0] % 10), dtype=np.float32)
        da = xr.DataArray(arr, dims=("y", "x"), coords={
            "y": np.linspace(aoi.bbox[3], aoi.bbox[1], h),
            "x": np.linspace(aoi.bbox[0], aoi.bbox[2], w),
        })
        da.rio.write_crs(aoi.crs_obj, inplace=True)
        return da

    return _fetch


class TestChirpsDailySignature:
    """load_chirps_rainfall_daily matches canonical M11 §2.2 pattern."""

    def test_has_years_param(self):
        sig = inspect.signature(load_chirps_rainfall_daily)
        assert "years" in sig.parameters

    def test_has_months_param(self):
        sig = inspect.signature(load_chirps_rainfall_daily)
        assert "months" in sig.parameters

    def test_no_year_param(self):
        sig = inspect.signature(load_chirps_rainfall_daily)
        assert "year" not in sig.parameters

    def test_no_month_param(self):
        sig = inspect.signature(load_chirps_rainfall_daily)
        assert "month" not in sig.parameters

    def test_cache_dir_is_keyword_only(self):
        sig = inspect.signature(load_chirps_rainfall_daily)
        assert sig.parameters["cache_dir"].kind == inspect.Parameter.KEYWORD_ONLY

    def test_months_defaults_to_none(self):
        sig = inspect.signature(load_chirps_rainfall_daily)
        assert sig.parameters["months"].default is None


class TestChirpsDailySingleMonth:
    """load_chirps_rainfall_daily with years=[2024], months=[6] returns 3D (30, h, w)."""

    def test_shape(self):
        aoi = _small_aoi()
        fetch = _mock_fetch_daily(aoi)
        result = load_chirps_rainfall_daily(aoi, years=[2024], months=[6], _fetch_daily=fetch)
        assert result.ndim == 3
        h, w = aoi.cells_per_side()
        assert result.shape == (30, h, w)  # June has 30 days

    def test_time_coords(self):
        aoi = _small_aoi()
        fetch = _mock_fetch_daily(aoi)
        result = load_chirps_rainfall_daily(aoi, years=[2024], months=[6], _fetch_daily=fetch)
        # Time coordinate should span June 1-30
        assert len(result.time) == 30

    def test_dims(self):
        aoi = _small_aoi()
        fetch = _mock_fetch_daily(aoi)
        result = load_chirps_rainfall_daily(aoi, years=[2024], months=[6], _fetch_daily=fetch)
        assert set(result.dims) == {"time", "y", "x"}


class TestChirpsDailyMultiMonth:
    """load_chirps_rainfall_daily with months=[6,7] returns correct shape."""

    def test_shape_june_july(self):
        aoi = _small_aoi()
        fetch = _mock_fetch_daily(aoi)
        result = load_chirps_rainfall_daily(aoi, years=[2024], months=[6, 7], _fetch_daily=fetch)
        assert result.ndim == 3
        h, w = aoi.cells_per_side()
        assert result.shape == (61, h, w)  # June 30 + July 31 = 61 days


class TestChirpsDailyDownloaderFormats:
    """DOWNLOADER dict has formats field with monthly/daily per output."""

    def test_formats_key_exists(self):
        assert "formats" in DOWNLOADER

    def test_rainfall_monthly_output_removed(self):
        """The historical load_chirps_rainfall monthly interface was deleted (2026-09-29)."""
        assert "rainfall" not in DOWNLOADER["outputs"]
        assert "rainfall" not in DOWNLOADER["manifest_keys"]

    def test_rainfall_daily_is_daily(self):
        assert DOWNLOADER["formats"]["rainfall_daily"] == "daily"

    def test_formats_matches_outputs(self):
        assert set(DOWNLOADER["formats"].keys()) == set(DOWNLOADER["outputs"].keys())


class TestCoastalWindowRegression:
    """Regression of the 2026-10 coastal-window bug (state-report AGENTE 1
    GAP #1): a tight (8x11 px, 0.05 deg) windowed CHIRPS clip — like
    accra-coastal-test — used to reproject to 100% NaN because the source
    DataArray had NO explicit transform/nodata attached and nearest
    inference from 1-D coords failed. The read path must attach the
    window transform + nodata explicitly, and the reprojected field must
    keep the valid land pixels (all-nodata-not-all-9)."""

    def test_coastal_window_keeps_valid_cells(self, tmp_path):
        import rasterio
        from rasterio.transform import from_bounds

        from mal_commonlib.data.loaders.chirps import (
            _read_chirps_tif_gz,
            _reproject_to_aoi_grid,
            CHIRPS_NODATA,
        )

        # Synthetic daily GeoTIFF covering the accra-coastal-test window:
        # 0.05-deg pixel, 8 rows x 11 cols, ocean nodata + land values.
        h, w = 8, 11
        west, south, east, north = 0.05, 5.35, 0.60, 5.75
        arr = np.full((h, w), CHIRPS_NODATA, dtype=np.float32)
        arr[:4, :] = 12.5  # land band (northern rows): NOT all-nodata
        transform = from_bounds(west, south, east, north, w, h)
        path = tmp_path / "chirps_day.tif"
        profile = {
            "driver": "GTiff", "height": h, "width": w, "count": 1,
            "dtype": "float32", "nodata": CHIRPS_NODATA,
            "crs": "EPSG:4326", "transform": transform,
        }
        with rasterio.open(path, "w", **profile) as dst:
            dst.write(arr, 1)

        aoi = AOI.from_bbox(west, south, east, north, "EPSG:4326",
                            "accra-coastal-test", 1000)
        da = _read_chirps_tif_gz(path, aoi)

        # The fix guards: explicit transform + nodata on the DataArray.
        assert da.shape == (h, w)
        assert da.rio.nodata is not None
        assert da.rio.crs is not None
        assert float(da.rio.transform().a) == pytest.approx(0.05)

        out = _reproject_to_aoi_grid(da, aoi)
        assert out.shape == aoi.cells_per_side()
        # Not all -9999/NaN: the land pixels survive the reproject.
        valid = out[np.isfinite(out)]
        assert valid.size > 0, "all-nodata window regression"
        assert not np.allclose(valid, 0.0)
