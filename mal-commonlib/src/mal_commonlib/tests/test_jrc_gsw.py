"""Tests for ``mal_commonlib.data.loaders.jrc_gsw`` (M2 fix — channel 0, ``water_frac``).

The JRC GSW loader streams the AOI bbox window from each 3°x3° tile
through ``rasterio.warp.reproject`` directly into the AOI grid (no full
merge). Tests stub ``_load_jrc_gsw_pc`` so the suite runs offline and
exercises the contract test path; one additional test
(``test_jrc_gsw_pc_streams_without_full_merge``) drives the real
``_load_jrc_gsw_pc`` with a monkeypatched ``rasterio.open`` that
returns a small in-memory fake JRC GSW tile, to verify the streaming
code path without hitting the network.
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
from mal_commonlib.data.loaders import jrc_gsw as jrc_mod
from mal_commonlib.data.loaders.jrc_gsw import (
    DEFAULT_THRESHOLD_PCT,
    NODATA_OUT,
    _load_jrc_gsw_pc,
    load_jrc_gsw_water_frac,
)


# -- helpers ------------------------------------------------------------------


def _small_aoi() -> AOI:
    return AOI.from_bbox(-1.0, 6.0, 0.0, 7.0, "EPSG:4326", "test-jrc-gsw", 1000)


def _stub_pc_loader(
    monkeypatch: pytest.MonkeyPatch, occurrence: np.ndarray,
    threshold_pct: int = DEFAULT_THRESHOLD_PCT,
) -> None:
    """Patch ``_load_jrc_gsw_pc`` to return a synthetic permanent-water mask
    already on the AOI grid (matching the real loader's streaming
    contract: (H, W) float32 in AOI CRS, AOI transform, -9999.0 for
    uncovered cells).

    ``occurrence`` is a small raster covering the AOI bbox at its own
    resolution. The stub binarises it against ``threshold_pct`` and
    reprojects it onto the AOI grid with average resampling.
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
        # Same binarisation as the real loader.
        occ = np.asarray(occurrence, dtype=np.uint8)
        water_mask = ((occ > 0) & (occ <= 100) & (occ >= int(threshold_pct))).astype(np.float32)
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
        }
        return out, profile

    monkeypatch.setattr(
        jrc_mod,
        "_load_jrc_gsw_pc",
        _fake_load_jrc_gsw_pc,
        raising=True,
    )


# -- contract / dry-run / no-network path -----------------------------------


def test_jrc_gsw_dry_run_no_network(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path,
) -> None:
    """Synthetic JRC GSW occurrence values → water_frac in {0, 1} of the right
    shape, dtype, CRS.

    A 50×50 occurrence array covering the AOI bbox. Top-left 10×10 square
    is permanent water (occurrence = 95); everywhere else is dry
    (occurrence = 5). After binarisation at threshold_pct=80, the AOI
    grid should have a few cells with water_frac ≈ 1 and most cells
    with water_frac ≈ 0.
    """
    occurrence = np.full((50, 50), 5, dtype=np.uint8)  # dry everywhere
    occurrence[10:20, 10:20] = 95  # permanent water in a square
    _stub_pc_loader(monkeypatch, occurrence)

    aoi = _small_aoi()
    out = load_jrc_gsw_water_frac(aoi, year=2021, cache_dir=tmp_path / "cache")

    assert out.dtype == np.float32
    assert out.dims == ("y", "x")
    h, w = aoi.cells_per_side()
    assert out.shape == (h, w)
    valid = out.values[out.values != NODATA_OUT]
    assert valid.min() >= 0.0
    assert valid.max() <= 1.0
    # Most cells are not permanent water; mean should be dominated by
    # zeros (the permanent-water square is small).
    assert float(valid.mean()) < 0.5


def test_jrc_gsw_binarisation_at_threshold() -> None:
    """``threshold_pct=80`` is the standard JRC GSW permanent-water cut-off."""
    assert DEFAULT_THRESHOLD_PCT == 80


def test_jrc_gsw_custom_threshold(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path,
) -> None:
    """A custom ``threshold_pct`` controls the binarisation cut-off.

    With ``occurrence = 50`` everywhere and ``threshold_pct=40``,
    every cell is permanent water. With ``threshold_pct=60``,
    no cell is permanent water.
    """
    occurrence = np.full((30, 30), 50, dtype=np.uint8)
    _stub_pc_loader(monkeypatch, occurrence)

    aoi = _small_aoi()

    # threshold_pct=40 (below 50) → all permanent water.
    out = load_jrc_gsw_water_frac(
        aoi, year=2021, cache_dir=tmp_path / "cache", threshold_pct=40,
    )
    valid = out.values[out.values != NODATA_OUT]
    assert valid.size > 0
    assert float(valid.mean()) > 0.9

    # threshold_pct=60 (above 50) → no permanent water.
    out = load_jrc_gsw_water_frac(
        aoi, year=2021, cache_dir=tmp_path / "cache", threshold_pct=60,
    )
    valid = out.values[out.values != NODATA_OUT]
    assert valid.size > 0
    assert float(valid.mean()) < 0.1


def test_jrc_gsw_year_must_be_in_range() -> None:
    """The loader rejects years outside the JRC GSW product range (1984-2021)."""
    aoi = _small_aoi()
    with pytest.raises(ValueError):
        load_jrc_gsw_water_frac(aoi, year=1983)
    with pytest.raises(ValueError):
        load_jrc_gsw_water_frac(aoi, year=2022)


def test_jrc_gsw_threshold_must_be_in_range(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The loader rejects threshold_pct outside [0, 100]."""
    occurrence = np.full((30, 30), 80, dtype=np.uint8)
    _stub_pc_loader(monkeypatch, occurrence)
    aoi = _small_aoi()
    with pytest.raises(ValueError):
        load_jrc_gsw_water_frac(aoi, year=2021, threshold_pct=-1)
    with pytest.raises(ValueError):
        load_jrc_gsw_water_frac(aoi, year=2021, threshold_pct=101)


def test_jrc_gsw_pc_stub_returns_valid_contract(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path,
) -> None:
    """The PC loader stub returns a water_frac in {0, 1} of the right shape,
    dtype, CRS, and metadata. This test exercises the full downstream
    contract without the network.
    """
    occurrence = np.full((40, 40), 95, dtype=np.uint8)  # all permanent water
    _stub_pc_loader(monkeypatch, occurrence)

    aoi = _small_aoi()
    out = load_jrc_gsw_water_frac(aoi, year=2021, cache_dir=tmp_path / "cache")

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
    # All permanent water → mean ≈ 1.0
    assert float(valid.mean()) > 0.9
    # The PC source and threshold are recorded in the attrs.
    assert "Planetary Computer" in out.attrs["source"]
    assert out.attrs["threshold_pct"] == DEFAULT_THRESHOLD_PCT
    assert out.attrs["asset"] == "occurrence"


def test_jrc_gsw_treats_out_of_range_occurrence_as_dry(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path,
) -> None:
    """JRC GSW encodes out-of-valid-range observations as 200 (or >100).
    These pixels must be treated as not-permanent-water, not as 100 %.
    """
    occurrence = np.full((30, 30), 5, dtype=np.uint8)
    occurrence[5:10, 5:10] = 200  # NoData (e.g. Antarctica) — must NOT count as water.
    _stub_pc_loader(monkeypatch, occurrence)

    aoi = _small_aoi()
    out = load_jrc_gsw_water_frac(aoi, year=2021, cache_dir=tmp_path / "cache")
    valid = out.values[out.values != NODATA_OUT]
    # Almost all cells are dry (5 < 80) and the 200 square is not water.
    # Mean should be ~0.
    assert float(valid.mean()) < 0.1


def test_jrc_gsw_pc_streams_without_full_merge(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Drive the real ``_load_jrc_gsw_pc`` with a Ghana-sized AOI and
    a 60×60 fake tile served by monkeypatched ``rasterio.open``. The
    streaming reprojection approach must (1) produce a (H_aoi, W_aoi)
    array in the AOI's CRS, (2) avoid the 1.6 GB ``rasterio.merge``
    allocation (peak < 50 MB), and (3) treat every cell covered by the
    fake tile as a valid observation (no -9999).
    """
    aoi = AOI.from_bbox(
        -3.5, 4.5, 1.5, 11.5, "EPSG:4326", "test-jrc-streaming", 1000,
    )
    H, W = int(aoi.cells_per_side()[0]), int(aoi.cells_per_side()[1])
    assert (H, W) == (779, 551), "Ghana 1 km grid should be 779×551"

    wmin, smin, wmax, smax = aoi.bbox
    tile_h, tile_w = 60, 60
    # All pixels are permanent water at the default threshold.
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
        arr, profile = jrc_mod._load_jrc_gsw_pc(aoi, 2021, DEFAULT_THRESHOLD_PCT)
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
    # permanent water, so the mean should be ~1.
    assert not np.any(arr == NODATA_OUT)
    assert float(arr.mean()) > 0.9


def test_jrc_gsw_falls_back_to_2020_when_requested_year_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path,
) -> None:
    """If the requested year has no PC STAC items, fall back to 2020.

    The JRC GSW collection on Planetary Computer has 504 items, all
    dated 2020 (the static product was tagged with 2020). Earlier
    versions of the loader raised FileNotFoundError when the
    requested year wasn't 2020, which broke M2 because build_env
    calls load_jrc_gsw_water_frac(aoi, year=2021). After this fix,
    year=2021 requests fall back to year=2020 transparently, and
    profile["jrc_gsw_year"] reports the actual year fetched (2020).
    """
    from unittest.mock import MagicMock

    # A tiny AOI: 4x4 cells at 1000m. Bbox spans ~0.035° so the AOI grid
    # is exactly 4x4.
    aoi = AOI.from_bbox(0.0, 0.0, 0.035, 0.035, "EPSG:4326", "test-fallback", 1000)
    H, W = int(aoi.cells_per_side()[0]), int(aoi.cells_per_side()[1])
    assert H == 4 and W == 4, f"AOI grid should be 4x4, got {H}x{W}"

    # Build a synthetic 4x4 occurrence COG (all pixels = 100, above threshold)
    # covering the AOI bbox.
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

    # Build a stub STAC item that points at the synthetic COG.
    stub_item = MagicMock()
    stub_item.assets = {"occurrence": MagicMock(href=str(cog_path))}
    stub_item.bbox = list(aoi.bbox)
    stub_item.datetime = None

    # Stub the catalog: first search (year=2021) returns [], second
    # (year=2020 fallback) returns [stub_item].
    search_calls: list[tuple] = []

    def _search_side_effect(*, collections, bbox, datetime, **_):
        search_calls.append((tuple(collections), tuple(bbox), str(datetime)))
        dt = str(datetime)
        if dt.startswith("2020-01-01"):
            return _FakeSearch([stub_item])
        return _FakeSearch([])

    class _FakeSearch:
        def __init__(self, items):
            self._items = items

        def items(self):
            return iter(self._items)

    class _FakeCatalog:
        def __init__(self):
            self.search = _search_side_effect

    class _FakeSTACClient:
        @staticmethod
        def open(url):
            return _FakeCatalog()

    monkeypatch.setattr(pystac_client, "Client", _FakeSTACClient)
    monkeypatch.setattr(planetary_computer, "sign", lambda x: x)

    # Call the loader with year=2021.
    arr, returned_profile = _load_jrc_gsw_pc(aoi, year=2021, threshold_pct=80)

    # The loader must have done two searches (one for 2021, one for 2020 fallback).
    assert len(search_calls) >= 2
    assert any(c[2].startswith("2021") for c in search_calls)
    assert any(c[2].startswith("2020") for c in search_calls)
    # The synthetic COG had all pixels = 100, so the binary water mask is
    # 1.0 everywhere, and the AOI mean is 1.0.
    assert arr.shape == (4, 4)
    assert arr.dtype == np.float32
    assert float(arr.mean()) > 0.99
    # The profile reports the actual year fetched (the 2020 fallback).
    assert returned_profile["jrc_gsw_year"] == 2020
    assert returned_profile["height"] == 4
    assert returned_profile["width"] == 4


def test_jrc_gsw_raises_when_even_2020_fallback_has_no_items(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When both the requested year AND the 2020 fallback return 0 STAC
    items, the loader raises FileNotFoundError (the original behaviour
    for uncovered bboxes)."""
    from unittest.mock import MagicMock

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
    """Real JRC GSW download for a small AOI via Planetary Computer. Skips on failure."""
    aoi = AOI.from_bbox(-1.0, 5.0, 0.0, 6.0, "EPSG:4326", "test-jrc", 1000)
    try:
        out = load_jrc_gsw_water_frac(aoi, year=2021, cache_dir=tmp_path / "cache")
    except Exception as e:
        pytest.skip(f"JRC GSW download failed: {e}")
    assert out.dtype == np.float32
    valid = out.values[out.values != NODATA_OUT]
    assert valid.size > 0
    assert set(np.unique(valid).tolist()).issubset({0.0, 1.0}) or (
        valid.min() >= 0.0 and valid.max() <= 1.0
    )
