"""Tests for ``mal_commonlib.data.loaders.jrc_gsw`` (contract v3.0).

The JRC GSW loader streams the AOI bbox window from each 3°x3° tile
through ``rasterio.warp.reproject`` directly into the AOI grid (no full
merge). Tests stub ``_load_jrc_gsw_pc`` so the suite runs offline, plus a
streaming test that drives the real ``_load_jrc_gsw_pc`` path through a
monkeypatched ``rasterio.open`` (memory bounds) and the 2020 fallback.
"""
from __future__ import annotations

import os
import pathlib
import tracemalloc
from unittest.mock import MagicMock

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
from mal_commonlib.data.loaders import jrc_gsw as jrc_mod
from mal_commonlib.data.loaders.jrc_gsw import (
    PERMANENT_THRESHOLD_PCT,
    NODATA_OUT,
    _load_jrc_gsw_pc,
    load_jrc_gsw_habitat_features,
)


# -- helpers ------------------------------------------------------------------


def _small_aoi() -> AOI:
    return AOI.from_bbox(-1.0, 6.0, 0.0, 7.0, "EPSG:4326", "test-jrc-gsw", 1000)


def _stub_pc_loader(
    monkeypatch: pytest.MonkeyPatch, occurrence: np.ndarray,
    threshold_pct: int = PERMANENT_THRESHOLD_PCT,
) -> None:
    """Patch ``_load_jrc_gsw_pc`` to return a synthetic >=80% permanent-water
    fraction already on the AOI grid.

    ``occurrence`` is a small raster covering the AOI bbox at its own
    resolution. The stub binarises it against ``threshold_pct`` and
    reprojects onto the AOI grid with average resampling (matching the
    per-cell fraction semantics of the real streaming path).
    """

    def _fake_load_jrc_gsw_pc(
        aoi: AOI,
        year: int,
        threshold_pct: int,
    ) -> tuple[np.ndarray, dict]:
        wmin, smin, wmax, smax = aoi.bbox
        H, W = int(aoi.cells_per_side()[0]), int(aoi.cells_per_side()[1])
        src_transform = from_bounds(
            wmin, smin, wmax, smax, occurrence.shape[1], occurrence.shape[0]
        )
        occ = np.asarray(occurrence, dtype=np.uint8)
        water_mask = (
            (occ > 0) & (occ <= 100) & (occ >= int(threshold_pct))
        ).astype(np.float32)
        out = np.zeros((H, W), dtype=np.float32)
        dst_transform = from_bounds(wmin, smin, wmax, smax, W, H)
        reproject(
            source=water_mask,
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
            "jrc_gsw_year": int(year),
        }
        return out, profile

    monkeypatch.setattr(
        jrc_mod, "_load_jrc_gsw_pc", _fake_load_jrc_gsw_pc, raising=True
    )


# -- contract / dry-run / no-network path -----------------------------------


def test_jrc_gsw_dry_run_no_network(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path,
) -> None:
    """Synthetic JRC GSW occurrence → jrc_persistent fraction in [0, 1]."""
    occurrence = np.full((50, 50), 5, dtype=np.uint8)  # dry everywhere
    occurrence[10:20, 10:20] = 95  # permanent water in a square
    _stub_pc_loader(monkeypatch, occurrence)

    aoi = _small_aoi()
    ds = load_jrc_gsw_habitat_features(aoi, year=2021, cache_dir=tmp_path / "cache")

    assert isinstance(ds, xr.Dataset)
    assert "jrc_persistent" in ds
    out = ds["jrc_persistent"]
    assert out.dtype == np.float32
    assert out.dims == ("y", "x")
    h, w = aoi.cells_per_side()
    assert out.shape == (h, w)
    valid = out.values[out.values != NODATA_OUT]
    assert valid.min() >= 0.0
    assert valid.max() <= 1.0
    assert float(valid.mean()) < 0.5


def test_jrc_gsw_threshold_still_permits_fraction() -> None:
    """``occurrence >= 80`` is the permanent-water cut-off; the retention is
    the per-cell MEAN of the binary mask (a fraction), not a binarised
    raster."""
    assert PERMANENT_THRESHOLD_PCT == 80


def test_jrc_gsw_year_must_be_in_range() -> None:
    aoi = _small_aoi()
    with pytest.raises(ValueError):
        load_jrc_gsw_habitat_features(aoi, year=1983)
    with pytest.raises(ValueError):
        load_jrc_gsw_habitat_features(aoi, year=2022)


def test_jrc_gsw_parts_of_contract_metadata(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path,
) -> None:
    occurrence = np.full((40, 40), 95, dtype=np.uint8)  # all permanent water
    _stub_pc_loader(monkeypatch, occurrence)
    aoi = _small_aoi()
    ds = load_jrc_gsw_habitat_features(aoi, year=2021, cache_dir=tmp_path / "cache")
    out = ds["jrc_persistent"]
    valid = out.values[out.values != NODATA_OUT]
    assert float(valid.mean()) > 0.9
    assert "Planetary Computer" in ds.attrs["source"]
    assert ds["jrc_persistent"].attrs["threshold_pct"] == PERMANENT_THRESHOLD_PCT
    assert ds["jrc_persistent"].attrs["asset"] == "occurrence"
    assert ds["jrc_persistent"].rio.crs is not None


def test_jrc_gsw_treats_out_of_range_occurrence_as_dry(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path,
) -> None:
    """Occurrence pixels > 100 (NoData, e.g. Antarctica) are dry."""
    occurrence = np.full((30, 30), 5, dtype=np.uint8)
    occurrence[5:10, 5:10] = 200
    _stub_pc_loader(monkeypatch, occurrence)
    aoi = _small_aoi()
    ds = load_jrc_gsw_habitat_features(aoi, year=2021, cache_dir=tmp_path / "cache")
    valid = ds["jrc_persistent"].values[ds["jrc_persistent"].values != NODATA_OUT]
    assert float(valid.mean()) < 0.1


def test_jrc_gsw_pc_streams_without_full_merge(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Drive the real ``_load_jrc_gsw_pc`` with a Ghana-sized AOI. Peak
    memory must stay bounded (streaming reproject, no 1.6 GB merge)."""
    aoi = AOI.from_bbox(
        -3.5, 4.5, 1.5, 11.5, "EPSG:4326", "test-jrc-streaming", 1000,
    )
    H, W = int(aoi.cells_per_side()[0]), int(aoi.cells_per_side()[1])

    wmin, smin, wmax, smax = aoi.bbox
    tile_h, tile_w = 60, 60
    tile_data = np.full((tile_h, tile_w), 95, dtype=np.uint8)
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
            self.assets = {"occurrence": _FakeAsset(href)}

    class _FakeSearch:
        def items(self):
            return iter([_FakeItem("https://fake.example/tile.tif")])

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
        arr, profile = jrc_mod._load_jrc_gsw_pc(aoi, 2021, PERMANENT_THRESHOLD_PCT)
        current, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    peak_mb = peak / (1024 * 1024)
    assert arr.shape == (H, W)
    assert arr.dtype == np.float32
    assert str(profile["crs"]) == str(aoi.crs_obj)
    assert profile["height"] == H
    assert profile["width"] == W
    assert peak_mb < 50, (
        f"peak memory {peak_mb:.1f} MB exceeded 50 MB threshold"
    )
    assert not np.any(arr == NODATA_OUT)
    assert float(arr.mean()) > 0.9


def test_jrc_gsw_falls_back_to_2020_when_requested_year_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path,
) -> None:
    """2021 requests fall back to 2020 transparently; the profile reports
    the year actually fetched."""
    aoi = AOI.from_bbox(0.0, 0.0, 0.035, 0.035, "EPSG:4326", "test-fallback", 1000)
    H, W = int(aoi.cells_per_side()[0]), int(aoi.cells_per_side()[1])
    assert (H, W) == (4, 4)

    transform = from_bounds(*aoi.bbox, 4, 4)
    cog_profile = {
        "driver": "GTiff", "dtype": "uint8", "count": 1, "height": 4, "width": 4,
        "crs": "EPSG:4326", "transform": transform, "nodata": 255,
    }
    with MemoryFile() as memfile:
        with memfile.open(**cog_profile) as src:
            src.write(np.full((1, 4, 4), 100, dtype=np.uint8))
        cog_bytes = memfile.read()
    cog_path = tmp_path / "occurrence.tif"
    cog_path.write_bytes(cog_bytes)

    stub_item = MagicMock()
    stub_item.assets = {"occurrence": MagicMock(href=str(cog_path))}
    stub_item.bbox = list(aoi.bbox)
    stub_item.datetime = None

    search_calls: list[tuple] = []

    class _FakeSearch:
        def __init__(self, items):
            self._items = items

        def items(self):
            return iter(self._items)

    def _search_side_effect(*, collections, bbox, datetime, **_):
        search_calls.append((tuple(collections), tuple(bbox), str(datetime)))
        if str(datetime).startswith("2020-01-01"):
            return _FakeSearch([stub_item])
        return _FakeSearch([])

    class _FakeCatalog:
        def __init__(self):
            self.search = _search_side_effect

    class _FakeSTACClient:
        @staticmethod
        def open(url):
            return _FakeCatalog()

    monkeypatch.setattr(pystac_client, "Client", _FakeSTACClient)
    monkeypatch.setattr(planetary_computer, "sign", lambda x: x)

    arr, returned_profile = _load_jrc_gsw_pc(aoi, year=2021, threshold_pct=80)

    assert len(search_calls) >= 2
    assert any(c[2].startswith("2021") for c in search_calls)
    assert any(c[2].startswith("2020") for c in search_calls)
    assert arr.shape == (4, 4)
    assert arr.dtype == np.float32
    assert float(arr.mean()) > 0.99
    assert returned_profile["jrc_gsw_year"] == 2020


def test_jrc_gsw_raises_when_even_2020_fallback_has_no_items(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _FakeSearch:
        def __init__(self, items):
            self._items = items

        def items(self):
            return iter(self._items)

    class _FakeCatalog:
        def search(self, **kwargs):
            return _FakeSearch([])

    class _FakeSTACClient:
        @staticmethod
        def open(url):
            return _FakeCatalog()

    monkeypatch.setattr(pystac_client, "Client", _FakeSTACClient)
    monkeypatch.setattr(planetary_computer, "sign", lambda x: x)

    aoi = AOI.from_bbox(0.0, 0.0, 0.035, 0.035, "EPSG:4326", "test-empty", 1000)
    with pytest.raises(FileNotFoundError):
        _load_jrc_gsw_pc(aoi, year=2021, threshold_pct=80)


# -- integration test --------------------------------------------------------


@pytest.mark.integration
@pytest.mark.skipif(
    not os.environ.get("MAL_JRC_GSW_NETWORK"),
    reason="MAL_JRC_GSW_NETWORK not set; integration test skipped",
)
def test_jrc_gsw_download(tmp_path: pathlib.Path) -> None:
    """Real JRC GSW download for a small AOI via Planetary Computer.

    Opt-in via ``-m integration``; once enabled, a failed download is a
    failure, not a skip.
    """
    aoi = AOI.from_bbox(-1.0, 5.0, 0.0, 6.0, "EPSG:4326", "test-jrc", 1000)
    ds = load_jrc_gsw_habitat_features(
        aoi, year=2021, cache_dir=tmp_path / "cache"
    )
    valid = ds["jrc_persistent"].values[ds["jrc_persistent"].values != NODATA_OUT]
    assert valid.size > 0
    assert valid.min() >= 0.0 and valid.max() <= 1.0
