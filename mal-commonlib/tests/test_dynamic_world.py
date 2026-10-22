"""Tests for the Dynamic World V1 loader (Earth Engine, contract v3.0).

The EE surface is fully mocked: these tests pin the *contract* (feature
mapping, mode-of-year composition, areal-fraction aggregation, NoData
handling, attribution) without touching the network or credentials.
"""
import io
from unittest import mock

import numpy as np
import pytest
import xarray as xr
from rasterio.transform import from_bounds

from mal_commonlib.aoi import AOI
from mal_commonlib.data.loaders import dynamic_world as dw


@pytest.fixture
def accra_aoi() -> AOI:
    # 'ghana' is the registered slug; the fraction math is AOI-agnostic.
    return AOI.from_slug("ghana")


# ---------------------------------------------------------------- mapping


def test_feature_mapping_is_the_contract_swap() -> None:
    assert dw.FEATURE_CLASSES["lc_built"] == (dw.DW_BUILT,)
    assert dw.FEATURE_CLASSES["lc_wetland"] == (dw.DW_FLOODED_VEGETATION,)
    assert dw.FEATURE_CLASSES["lc_crop"] == (dw.DW_CROPS,)
    assert dw.FEATURE_CLASSES["lc_open_plus_water"] == (
        dw.DW_GRASS, dw.DW_SHRUB_SCRUB, dw.DW_BARE, dw.DW_WATER,
    )


def test_downloader_contract() -> None:
    assert dw.DOWNLOADER["name"] == "dynamic_world"
    assert dw.DOWNLOADER["manifest_keys"]["class_fractions"] == (
        "dw_class_fractions"
    )
    assert dw.DOWNLOADER["required_for_abm"]["class_fractions"] is True
    assert dw.DOWNLOADER["license"] == "CC-BY-4.0"
    assert "Copernicus Sentinel" in dw.DOWNLOADER["attribution"]


# ------------------------------------------------------- ee surface mocked


class _FakeCollection:
    """Mimics the subset of the EE ImageCollection API the loader uses."""

    def __init__(self, size: int = 30) -> None:
        self._size = size

    def filterBounds(self, _region):  # noqa: N802 (EE naming)
        return self

    def filterDate(self, _start, _end):
        return self

    def select(self, _band):
        return self

    def size(self):
        return self

    def getInfo(self) -> int:
        return self._size

    def mode(self):
        return _FakeModeImage()


class _FakeModeImage:
    def getDownloadURL(self, params) -> str:
        from types import SimpleNamespace

        scale = params["scale"]
        region = (
            params["region"].getInfo()
            if hasattr(params["region"], "getInfo")
            else params["region"]
        )
        coords = region["coordinates"][0]
        w = min(c[0] for c in coords)
        e = max(c[0] for c in coords)
        s = min(c[1] for c in coords)
        n = max(c[1] for c in coords)

        nx = int(round((e - w) * 111_320.0 / scale))
        ny = int(round((n - s) * 111_320.0 / scale))
        nx = max(2, min(nx, dw._TILE_MAX_PX))
        ny = max(2, min(ny, dw._TILE_MAX_PX))
        # Built label fills the lower half, water the upper half.
        arr = np.where(
            (np.arange(ny)[:, None] / ny) < 0.5,
            dw.DW_BUILT, dw.DW_WATER,
        ).astype(np.int32)
        tif = _write_geotiff_bytes(arr, (w, s, e, n))
        url = f"http://ee-fake/{w:.3f}-{s:.3f}-{e:.3f}-{n:.3f}.tif"

        def _fake_get(u, timeout=None):
            return SimpleNamespace(
                content=tif, raise_for_status=lambda: None
            )

        self._patcher = mock.patch("requests.get", side_effect=_fake_get)
        self._patcher.start()
        return url


def _fake_rectangle(xs):
    """GeoJSON-polygon shaped stand-in for ee.Geometry.Rectangle()."""
    w, s, e, n = xs
    return {"coordinates": [[[w, s], [w, n], [e, n], [e, s]]]}


def _write_geotiff_bytes(arr: np.ndarray, bbox) -> bytes:
    """Encode arr as an EPSG:4326 GeoTIFF (in-memory)."""
    import rasterio.io

    w, s, e, n = bbox
    buf = io.BytesIO()
    with rasterio.io.MemoryFile() as mem:
        with mem.open(
            driver="GTiff", height=arr.shape[0], width=arr.shape[1],
            count=1, dtype="int32", crs="EPSG:4326",
            transform=from_bounds(w, s, e, n, arr.shape[1], arr.shape[0]),
        ) as dst:
            dst.write(arr, 1)
        buf.write(mem.read())
    return buf.getvalue()


def test_class_fractions_mode_of_year(
    accra_aoi: AOI, tmp_path
) -> None:
    fake_ee = mock.MagicMock()
    fake_ee.Geometry.Rectangle = _fake_rectangle
    fake_ee.ImageCollection = lambda _c: _FakeCollection()
    with mock.patch.object(dw, "_ensure_ee", return_value=fake_ee):
        ds = dw.load_dw_class_fractions(accra_aoi, years=[2024],
                                        cache_dir=tmp_path)

    assert set(ds.data_vars) >= {"lc_built", "lc_wetland", "lc_crop",
                                 "lc_open_plus_water"}
    assert ds.sizes["time"] == 1
    built = ds["lc_built"].isel(time=0).values
    water_open = ds["lc_open_plus_water"].isel(time=0).values
    # The synthetic scene: top half water, bottom half built → the two
    # planes are complementary per cell and each averages ~0.5 overall.
    assert np.allclose(built + water_open, 1.0, atol=0.05)
    assert 0.35 < float(built.mean()) < 0.65
    valid_built = built[built != dw.NODATA_OUT]
    assert float(valid_built.min()) >= 0.0 and float(valid_built.max()) <= 1.0
    assert np.all((ds["lc_wetland"].values == 0.0) | (
        ds["lc_wetland"].values == dw.NODATA_OUT))
    assert ds.attrs["contract"] == "habitat-v3.0-statics"
    assert "Copernicus Sentinel" in ds.attrs["attribution"]
    assert ds["lc_built"].rio.nodata == dw.NODATA_OUT


def test_class_fractions_averages_years(
    accra_aoi: AOI, tmp_path
) -> None:
    fake_ee = mock.MagicMock()
    fake_ee.Geometry.Rectangle = _fake_rectangle
    fake_ee.ImageCollection = lambda _c: _FakeCollection()
    with mock.patch.object(dw, "_ensure_ee", return_value=fake_ee):
        ds = dw.load_dw_class_fractions(accra_aoi, years=[2024, 2025],
                                        cache_dir=tmp_path)
    assert ds.sizes["time"] == 2
    assert ds["time"].values[0] == np.datetime64("2024-01-01", "D")
    assert ds["time"].values[1] == np.datetime64("2025-01-01", "D")


def test_year_before_record_raises(accra_aoi: AOI, tmp_path) -> None:
    with pytest.raises(ValueError, match="starts 2015"):
        dw.load_dw_class_fractions(accra_aoi, years=[2014],
                                   cache_dir=tmp_path)


def test_missing_years_raises(accra_aoi: AOI) -> None:
    with pytest.raises(ValueError, match="at least one year"):
        dw.load_dw_class_fractions(accra_aoi, years=[])


def test_not_authenticated_error_is_actionable(accra_aoi: AOI) -> None:
    with mock.patch.object(
        dw, "_ensure_ee",
        side_effect=RuntimeError("earthengine authenticate"),
    ), pytest.raises(RuntimeError, match="earthengine authenticate"):
        dw.load_dw_class_fractions(accra_aoi, years=[2024])


# ------------------------------------------------------------- label mode


def test_label_mode_single_year(accra_aoi: AOI, tmp_path) -> None:
    fake_ee = mock.MagicMock()
    fake_ee.Geometry.Rectangle = _fake_rectangle
    fake_ee.ImageCollection = lambda _c: _FakeCollection()
    with mock.patch.object(dw, "_ensure_ee", return_value=fake_ee):
        lc = dw.load_dw_label_mode(accra_aoi, year=2024, cache_dir=tmp_path)
    vals = lc.values
    assert lc.dtype == np.int32
    assert set(np.unique(vals[vals != -9999])) <= {dw.DW_BUILT, dw.DW_WATER}
    assert lc.attrs["source"].startswith("Dynamic World V1")
