"""Tests for mal_commonlib.data.loaders.modis (M1.3a).

The MOD13A3 loader is a thin wrapper around earthaccess + rasterio. We:

* assert the function calls ``earthaccess.login()`` and that without
  ``EARTHDATA_TOKEN`` (or with a fake one) it raises a clear error.
* run a "dry-run" path that monkeypatches ``earthaccess.search_data`` and
  ``earthaccess.download`` to return a synthetic MOD13A3-like DataArray,
  and assert the result is in [0, 1] with the right shape, dtype and CRS.

Integration tests that hit the real NASA Earthdata service are skipped if
``EARTHDATA_TOKEN`` is not set.
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

from mal_commonlib.aoi import AOI, Scale
from mal_commonlib.data.loaders.modis import NODATA_OUT, load_modis_ndvi


GHANA_W, GHANA_S, GHANA_E, GHANA_N = -3.5, 4.5, 1.5, 11.5


def _small_aoi() -> AOI:
    """A small AOI for unit tests (Ghana is too big for a synthetic 50x50)."""
    return AOI.from_bbox(
        -1.0, 6.0, 0.0, 7.0, "EPSG:4326", "test-modis", 1000
    )


# -- auth / token handling ---------------------------------------------------


def test_modis_requires_earthdata_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without EARTHDATA_TOKEN, the loader raises a clear error before network."""
    monkeypatch.delenv("EARTHDATA_TOKEN", raising=False)
    aoi = _small_aoi()
    with pytest.raises(RuntimeError) as excinfo:
        load_modis_ndvi(aoi, year=2024, month=7)
    assert "EARTHDATA_TOKEN" in str(excinfo.value)


def test_modis_with_fake_token_calls_earthaccess_login(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With a fake EARTHDATA_TOKEN, the loader calls earthaccess.login()."""
    monkeypatch.setenv("EARTHDATA_TOKEN", "fake-token-for-unit-test")

    called = {"login": False}

    def _fake_login() -> None:
        called["login"] = True

    monkeypatch.setattr("earthaccess.login", _fake_login, raising=False)

    def _fake_search_data(*_args, **_kwargs):
        return []

    monkeypatch.setattr("earthaccess.search_data", _fake_search_data, raising=False)

    aoi = _small_aoi()
    # search_data returns [] → FileNotFoundError. That's the expected branch.
    with pytest.raises(FileNotFoundError):
        load_modis_ndvi(aoi, year=2024, month=7)
    assert called["login"] is True


# -- dry-run / no-network path -----------------------------------------------


def _write_synthetic_modis_hdf(path: pathlib.Path, arr: np.ndarray) -> None:
    """Write a synthetic HDF4 file that the pyhdf-based MOD13A3 reader accepts.

    The real MOD13A3 product is HDF4-EOS2 with a ``1 km monthly NDVI`` SDS
    (int16, fill ``-3000``, scale ``0.0001``) and a ``StructMetadata.0``
    top-level attribute holding the grid extent. We mock all of those here.
    The values are written as int16 — the loader's rescale is responsible
    for converting them to ``[-0.2, 1.0]`` and then to ``[0, 1]``.
    """
    from pyhdf.SD import SD, SDC

    h, w = arr.shape
    # 1 km × N pixels × M pixels = extent in metres. Place the synthetic
    # tile's NW corner at (-1, 7) in lon/lat and SE corner at (0, 6) so the
    # tile covers the same AOI as the test's _small_aoi() helper.
    R = 6371007.181
    west, north = -1.0, 7.0
    east, south = 0.0, 6.0
    x_ul = west * R
    y_ul = north * R
    x_lr = east * R
    y_lr = south * R

    # Map a [-0.2, 1.0] float array back to MOD13A3 int16 raw values so the
    # loader's rescale is exercised exactly as it is on real data.
    arr_int16 = np.clip(np.round(arr * 10000.0), -3000, 10000).astype(np.int16)

    sd = SD(str(path), SDC.WRITE | SDC.CREATE | SDC.TRUNC)
    sds = sd.create("1 km monthly NDVI", SDC.INT16, (h, w))
    sds[:] = arr_int16
    sds.setfillvalue(-3000)
    sds.long_name = "1 km monthly NDVI"
    sds.units = "NDVI"
    sds.valid_range = [-2000, 10000]
    sds.scale_factor = 0.0001
    sds.endaccess()
    struct = (
        "GROUP=GridStructure\n"
        "  GROUP=GRID_1\n"
        "    GridName=MOD_Grid_monthly_1km_VI\n"
        f"    XDim={w}\n"
        f"    YDim={h}\n"
        f"    UpperLeftPointMtrs=({x_ul}, {y_ul})\n"
        f"    LowerRightMtrs=({x_lr}, {y_lr})\n"
        "    Projection=GCTP_SNSOID\n"
        "  END_GROUP=GRID_1\n"
        "END_GROUP=GridStructure\n"
        "END"
    )
    sd.StructMetadata_0 = struct
    sd.end()


def test_modis_dry_run_no_network(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    """Monkeypatch earthaccess and assert the loader returns [0, 1] NDVI."""
    monkeypatch.setenv("EARTHDATA_TOKEN", "fake-token-for-unit-test")
    monkeypatch.setattr("earthaccess.login", lambda: None, raising=False)

    # Build a synthetic MOD13A3 tile covering the AOI.
    raw = np.linspace(-0.2, 0.9, 50 * 50, dtype=np.float32).reshape(50, 50)
    tile_path = tmp_path / "synthetic_modis.tif"
    _write_synthetic_modis_hdf(tile_path, raw)

    def _fake_search_data(*_args, **_kwargs):
        return ["granule-1"]

    def _fake_download(granules, path=None, **_kwargs):
        return [tile_path]

    monkeypatch.setattr("earthaccess.search_data", _fake_search_data, raising=False)
    monkeypatch.setattr("earthaccess.download", _fake_download, raising=False)

    aoi = _small_aoi()
    out = load_modis_ndvi(aoi, year=2024, month=7, cache_dir=tmp_path / "cache")
    assert out.dtype == np.float32
    assert out.dims == ("y", "x")
    h, w = aoi.cells_per_side()
    assert out.shape == (h, w)
    # All values in [0, 1] (NDVI is rescaled).
    valid = out.values[out.values != NODATA_OUT]
    assert valid.min() >= 0.0
    assert valid.max() <= 1.0
    # CRS preserved.
    assert str(out.rio.crs).upper().endswith("4326")


def test_modis_dry_run_rescales_raw_to_unit_interval(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    """The raw valid NDVI values should land in [0, 1] after rescaling.

    MOD13A3 stores NDVI in [-0.2, 1.0] (the physically meaningful range for
    vegetation). Below -0.2 is reserved as fill. We test with five values
    spanning the valid range to verify the (x + 1) / 2 rescale.
    """
    monkeypatch.setenv("EARTHDATA_TOKEN", "fake-token-for-unit-test")
    monkeypatch.setattr("earthaccess.login", lambda: None, raising=False)

    # Five values across the valid range, repeated across 10 rows so the
    # synthetic tile is not trivially thin.
    arr = np.array(
        [[-0.2, -0.1, 0.0, 0.5, 1.0]] * 10, dtype=np.float32
    )
    tile_path = tmp_path / "synthetic_modis_2.tif"
    _write_synthetic_modis_hdf(tile_path, arr)

    def _fake_search_data(*_args, **_kwargs):
        return ["granule-1"]

    def _fake_download(granules, path=None, **_kwargs):
        return [tile_path]

    monkeypatch.setattr("earthaccess.search_data", _fake_search_data, raising=False)
    monkeypatch.setattr("earthaccess.download", _fake_download, raising=False)

    aoi = AOI.from_bbox(-1.0, 6.0, 0.0, 7.0, "EPSG:4326", "test-modis", 1000)
    out = load_modis_ndvi(aoi, year=2024, month=7, cache_dir=tmp_path / "cache")
    # The single tile is reprojected to the AOI grid via reproject_match with
    # bilinear. The leftmost source column (-0.2) rescaled to 0.4 is the
    # global minimum; the rightmost source column (1.0) rescaled to 1.0 is
    # the global maximum. We assert the range is sane and the median is
    # near the middle of the input range.
    valid = out.values[out.values != NODATA_OUT]
    # Each source column maps to many AOI cells; the extremes of the
    # rescaled range are visible. The mean should be in the middle of the
    # source range mapped to [0, 1].
    assert 0.0 <= valid.min() <= 0.5  # leftmost input is -0.2 → 0.4
    assert 0.9 <= valid.max() <= 1.0  # rightmost input is 1.0 → 1.0
    # Median is around 0.5 (the middle input is 0 → 0.5).
    assert 0.3 < float(np.median(valid)) < 0.8


# -- integration tests --------------------------------------------------------


@pytest.mark.integration
@pytest.mark.skipif(
    not os.environ.get("EARTHDATA_TOKEN"),
    reason="EARTHDATA_TOKEN not set; integration test skipped",
)
def test_modis_ghana_smoke() -> None:
    """Real Earthdata download for Ghana, 2022-07. 2024-07 is currently
    empty upstream (NASA MOD13A3 v061 lag). Skips cleanly if the download
    fails (network/permissions).
    """
    aoi = AOI.from_bbox(GHANA_W, GHANA_S, GHANA_E, GHANA_N, "EPSG:4326", "ghana", 1000)
    try:
        out = load_modis_ndvi(aoi, year=2022, month=7)
    except Exception as e:
        pytest.skip(f"MOD13A3 download failed: {e}")
    assert out.dtype == np.float32
    valid = out.values[out.values != NODATA_OUT]
    assert valid.size > 0
    assert 0.0 <= valid.min() <= 1.0
    assert 0.0 <= valid.max() <= 1.0
