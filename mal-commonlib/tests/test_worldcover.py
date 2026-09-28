"""Tests for mal_commonlib.data.loaders.worldcover (M1.3a).

The WorldCover loader streams the AOI bbox window from each 3°×3° tile
through ``rasterio.warp.reproject`` directly into the AOI grid (no full
merge). Tests stub ``_load_worldcover_pc`` to return a synthetic
AOI-grid-shaped binary water mask, so no network is required for the
contract tests. One additional test
(``test_worldcover_pc_streams_without_full_merge``) drives the real
``_load_worldcover_pc`` with a monkeypatched ``rasterio.open`` that
returns a small in-memory fake tile, to verify the streaming code path
without hitting the network.
"""
from __future__ import annotations

import os
import pathlib
import tracemalloc

import numpy as np
import planetary_computer
import pystac_client
import pytest
import rasterio
import rioxarray  # noqa: F401
import xarray as xr
from rasterio.io import MemoryFile
from rasterio.transform import from_bounds
from rasterio.warp import Resampling, reproject

from mal_commonlib.aoi import AOI
from mal_commonlib.data.loaders import worldcover as wc_mod
from mal_commonlib.data.loaders.worldcover import (
    DEFAULT_WATER_CLASSES,
    NODATA_OUT,
    load_worldcover_water_frac,
)


# -- helpers ------------------------------------------------------------------


def _small_aoi() -> AOI:
    return AOI.from_bbox(-1.0, 6.0, 0.0, 7.0, "EPSG:4326", "test-worldcover", 1000)


def _stub_pc_loader(
    monkeypatch: pytest.MonkeyPatch, classes: np.ndarray,
) -> None:
    """Patch ``_load_worldcover_pc`` to return a synthetic binary water
    mask already on the AOI grid (matching the real loader's streaming
    contract: (H, W) float32 in AOI CRS, AOI transform, -9999.0 for
    uncovered cells).

    ``classes`` is a small raster that covers the AOI bbox at its own
    resolution. The stub binarises it against ``water_classes`` and
    reprojects it onto the AOI grid with average resampling.
    """

    def _fake_load_worldcover_pc(
        aoi: AOI,
        year: int,
        water_classes: tuple[int, ...],
    ) -> tuple[np.ndarray, dict]:
        wmin, smin, wmax, smax = aoi.bbox
        H, W = int(aoi.cells_per_side()[0]), int(aoi.cells_per_side()[1])
        src_transform = from_bounds(
            wmin, smin, wmax, smax, classes.shape[1], classes.shape[0]
        )
        water = np.asarray(water_classes, dtype=np.uint8)
        bin_arr = np.isin(classes, water).astype(np.float32)
        out = np.zeros((H, W), dtype=np.float32)
        dst_transform = from_bounds(wmin, smin, wmax, smax, W, H)
        reproject(
            source=bin_arr,
            destination=out,
            src_transform=src_transform,
            src_crs="EPSG:4326",
            dst_transform=dst_transform,
            dst_crs="EPSG:4326",
            resampling=Resampling.average,
        )
        profile = {
            "crs": aoi.crs_obj,
            "transform": dst_transform,
            "height": H,
            "width": W,
        }
        return out, profile

    monkeypatch.setattr(
        wc_mod,
        "_load_worldcover_pc",
        _fake_load_worldcover_pc,
        raising=True,
    )


# -- dry-run / no-network path ----------------------------------------------


def test_worldcover_dry_run_no_network(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    """Synthetic WorldCover classes → water_frac in [0, 1] of the right shape.

    A 50×50 class array covering the AOI bbox. Top-left 10×10 square is
    water (80); everywhere else is tree cover (10). After reprojection
    averaging, the AOI grid should have a few cells with water_frac ≈ 1
    and most cells with water_frac ≈ 0.
    """
    classes = np.full((50, 50), 10, dtype=np.uint8)  # Tree cover everywhere
    classes[10:20, 10:20] = 80  # Permanent water in a square
    _stub_pc_loader(monkeypatch, classes)

    aoi = _small_aoi()
    out = load_worldcover_water_frac(aoi, year=2021, cache_dir=tmp_path / "cache")

    assert out.dtype == np.float32
    assert out.dims == ("y", "x")
    h, w = aoi.cells_per_side()
    assert out.shape == (h, w)
    valid = out.values[out.values != NODATA_OUT]
    # Most cells are non-water (10) → water_frac ~0.
    # The water square (80) reprojects to a few AOI cells with water_frac ~1.
    assert valid.min() >= 0.0
    assert valid.max() <= 1.0
    # The average should be dominated by zeros (the water square is small).
    assert float(valid.mean()) < 0.5


def test_worldcover_class_mapping() -> None:
    """Classes {80, 90, 95} → water; class 10 (Tree cover) → not water."""
    # DEFAULT_WATER_CLASSES is the contract.
    assert 80 in DEFAULT_WATER_CLASSES
    assert 90 in DEFAULT_WATER_CLASSES
    assert 95 in DEFAULT_WATER_CLASSES
    assert 10 not in DEFAULT_WATER_CLASSES  # Tree cover is not water
    assert 20 not in DEFAULT_WATER_CLASSES  # Shrub is not water
    assert 40 not in DEFAULT_WATER_CLASSES  # Cropland is not water


def test_worldcover_custom_water_classes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    """A custom water_classes=... overrides the default."""
    # Build a class array where the only "water" class is 40 (cropland).
    # With the default, the output would be all 0. With custom=(40,),
    # the output is all 1.0 in the bbox (after reprojection averaging).
    classes = np.full((30, 30), 40, dtype=np.uint8)
    _stub_pc_loader(monkeypatch, classes)

    aoi = _small_aoi()
    out = load_worldcover_water_frac(
        aoi, year=2021, cache_dir=tmp_path / "cache", water_classes=(40,)
    )
    valid = out.values[out.values != NODATA_OUT]
    assert valid.size > 0
    # All valid cells are 1.0 (or very close after reprojection averaging).
    assert float(valid.mean()) > 0.9


def test_worldcover_pc_stub_returns_valid_contract(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    """The PC loader stub returns a water_frac in [0, 1] of the right
    shape, dtype, CRS, and metadata. This test exercises the full
    downstream contract without the network.
    """
    classes = np.full((40, 40), 80, dtype=np.uint8)  # all water
    _stub_pc_loader(monkeypatch, classes)

    aoi = _small_aoi()
    out = load_worldcover_water_frac(aoi, year=2021, cache_dir=tmp_path / "cache")

    assert isinstance(out, xr.DataArray)
    assert out.dtype == np.float32
    assert out.dims == ("y", "x")
    h, w = aoi.cells_per_side()
    assert out.shape == (h, w)
    assert out.rio.crs is not None
    assert out.rio.crs.to_epsg() == 4326
    valid = out.values[out.values != NODATA_OUT]
    assert valid.min() >= 0.0
    assert valid.max() <= 1.0
    # All water → average ≈ 1.0
    assert float(valid.mean()) > 0.9
    # The PC source is recorded in the attrs.
    assert "Planetary Computer" in out.attrs["source"]
    assert out.attrs["water_classes"] == list(DEFAULT_WATER_CLASSES)


def test_worldcover_year_must_be_2020_or_2021() -> None:
    """The loader rejects unsupported WorldCover years."""
    aoi = _small_aoi()
    with pytest.raises(ValueError):
        load_worldcover_water_frac(aoi, year=2019)


def test_worldcover_pc_streams_without_full_merge(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Drive the real ``_load_worldcover_pc`` with a Ghana-sized AOI and
    a 60×60 fake tile served by monkeypatched ``rasterio.open``. The
    streaming reprojection approach must (1) produce a (H_aoi, W_aoi)
    array in the AOI's CRS, (2) avoid the 1.6 GB ``rasterio.merge``
    allocation (peak < 50 MB), and (3) treat every cell covered by the
    fake tile as a valid observation (no -9999).
    """
    aoi = AOI.from_bbox(
        -3.5, 4.5, 1.5, 11.5, "EPSG:4326", "test-wc-streaming", 1000
    )
    H, W = int(aoi.cells_per_side()[0]), int(aoi.cells_per_side()[1])
    assert (H, W) == (779, 551), "Ghana 1 km grid should be 779×551"

    wmin, smin, wmax, smax = aoi.bbox
    tile_h, tile_w = 60, 60
    tile_data = np.full((tile_h, tile_w), 80, dtype=np.uint8)  # all water
    tile_transform = from_bounds(wmin, smin, wmax, smax, tile_w, tile_h)
    tile_profile = {
        "driver": "GTiff",
        "dtype": "uint8",
        "nodata": None,
        "width": tile_w,
        "height": tile_h,
        "count": 1,
        "crs": "EPSG:4326",
        "transform": tile_transform,
    }

    def _fake_rasterio_open(href, *args, **kwargs):
        memfile = MemoryFile()
        ds = memfile.open(**tile_profile)
        ds.write(tile_data, 1)
        return ds

    class _FakeAsset:
        def __init__(self, href: str) -> None:
            self.href = href

    class _FakeItem:
        def __init__(self, href: str) -> None:
            self.assets = {"map": _FakeAsset(href)}

    fake_items = [_FakeItem("https://fake.example/tile.tif")]

    class _FakeSearch:
        def items(self):
            return iter(fake_items)

    class _FakeCatalog:
        def search(self, **kwargs):
            return _FakeSearch()

    class _FakeSTACClient:
        @staticmethod
        def open(url):
            return _FakeCatalog()

    monkeypatch.setattr(pystac_client, "Client", _FakeSTACClient)
    monkeypatch.setattr(planetary_computer, "sign", lambda x: x)
    monkeypatch.setattr(rasterio, "open", _fake_rasterio_open)

    tracemalloc.start()
    try:
        arr, profile = wc_mod._load_worldcover_pc(aoi, 2021, DEFAULT_WATER_CLASSES)
        current, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    peak_mb = peak / (1024 * 1024)

    # (1) result is AOI-grid shaped
    assert arr.shape == (H, W)
    assert arr.dtype == np.float32
    # (2) CRS matches the AOI
    assert str(profile["crs"]) == str(aoi.crs_obj)
    assert profile["height"] == H
    assert profile["width"] == W
    # (3) peak memory bounded
    assert peak_mb < 50, (
        f"peak memory {peak_mb:.1f} MB exceeded 50 MB threshold "
        f"(streaming reproject should stay well under)"
    )
    # Sanity: every cell is covered by the fake tile and all pixels are
    # water (80 ∈ DEFAULT_WATER_CLASSES), so the mean should be ~1.
    assert not np.any(arr == NODATA_OUT)
    assert float(arr.mean()) > 0.9


# -- integration test --------------------------------------------------------


@pytest.mark.integration
@pytest.mark.skipif(
    not os.environ.get("MAL_WORLDCOVER_NETWORK"),
    reason="MAL_WORLDCOVER_NETWORK not set; integration test skipped",
)
def test_worldcover_download(tmp_path: pathlib.Path) -> None:
    """Real WorldCover download for a small AOI via Planetary Computer. Skips on failure."""
    aoi = AOI.from_bbox(-1.0, 5.0, 0.0, 6.0, "EPSG:4326", "test-wc", 1000)
    try:
        out = load_worldcover_water_frac(aoi, year=2021, cache_dir=tmp_path / "cache")
    except Exception as e:
        pytest.skip(f"WorldCover download failed: {e}")
    assert out.dtype == np.float32
    valid = out.values[out.values != NODATA_OUT]
    assert valid.size > 0
    assert 0.0 <= valid.min() <= 1.0
    assert 0.0 <= valid.max() <= 1.0
