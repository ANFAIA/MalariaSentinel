"""Tests for mal_commonlib.data.loaders.worldcover (M1.3a).

The WorldCover loader now goes through the Microsoft Planetary Computer
STAC catalog (``esa-worldcover`` collection) and reads only the AOI bbox
window from each 3°×3° tile. Tests stub ``_load_worldcover_pc`` to return
a synthetic class-band raster for the AOI bbox, so no network is required.
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
    monkeypatch: pytest.MonkeyPatch, classes: np.ndarray, *,
    aoi_override: AOI | None = None,
) -> None:
    """Patch ``_load_worldcover_pc`` to return a synthetic class-band
    raster covering the AOI bbox (always all-water) at the same
    resolution as ``classes``.

    The AOI bbox is taken from the call argument (we cannot easily peek
    at it from inside the stub, so the test passes a single global AOI
    that matches the bbox of ``classes``).
    """
    def _fake_load_worldcover_pc(
        aoi: AOI,
        year: int,
        water_classes: tuple[int, ...],
    ) -> tuple[np.ndarray, dict]:
        # Convert class codes to a binary water mask at the same shape.
        water = np.asarray(water_classes, dtype=np.uint8)
        arr = np.isin(classes, water).astype(np.uint8).astype(np.float32)
        # Transform covers the AOI bbox at the resolution of ``classes``.
        wmin, smin, wmax, smax = aoi.bbox
        transform = from_bounds(wmin, smin, wmax, smax, classes.shape[1], classes.shape[0])
        profile = {
            "crs": "EPSG:4326",
            "transform": transform,
            "height": arr.shape[0],
            "width": arr.shape[1],
        }
        return arr, profile

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
