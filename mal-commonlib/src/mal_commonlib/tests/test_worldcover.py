"""Tests for mal_commonlib.data.loaders.worldcover (M1.3a).

The WorldCover loader is a thin wrapper around ``requests`` + ``rasterio``.
We assert the dry-run path (monkeypatched downloader returning a synthetic
class-band raster) and the class-mapping behaviour.
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
from mal_commonlib.data.loaders.worldcover import (
    DEFAULT_WATER_CLASSES,
    NODATA_OUT,
    load_worldcover_water_frac,
)


# -- helpers ------------------------------------------------------------------


def _small_aoi() -> AOI:
    return AOI.from_bbox(-1.0, 6.0, 0.0, 7.0, "EPSG:4326", "test-worldcover", 1000)


def _write_synthetic_worldcover(
    path: pathlib.Path, classes: np.ndarray
) -> None:
    """Write a single-band uint8 GeoTIFF with WorldCover class codes."""
    h, w = classes.shape
    transform = from_bounds(-1.0, 6.0, 0.0, 7.0, w, h)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=h,
        width=w,
        count=1,
        dtype="uint8",
        crs="EPSG:4326",
        transform=transform,
    ) as dst:
        dst.write(classes.astype(np.uint8), 1)


def _monkeypatch_downloader(
    monkeypatch: pytest.MonkeyPatch, tile_path: pathlib.Path
) -> None:
    """Patch earthaccess-equivalent downloader to return the local tile."""
    def _fake_download_tiles(lon0, lat0, year, cache):
        # Always return the same synthetic tile, regardless of bbox.
        return tile_path

    monkeypatch.setattr(
        "mal_commonlib.data.loaders.worldcover._download_tile",
        _fake_download_tiles,
        raising=True,
    )


# -- dry-run / no-network path ----------------------------------------------


def test_worldcover_dry_run_no_network(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    """Synthetic WorldCover tile → water_frac in [0, 1] of the right shape."""
    classes = np.full((50, 50), 10, dtype=np.uint8)  # Tree cover everywhere
    classes[10:20, 10:20] = 80  # Permanent water in a square
    tile_path = tmp_path / "synthetic_worldcover.tif"
    _write_synthetic_worldcover(tile_path, classes)
    _monkeypatch_downloader(monkeypatch, tile_path)

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
    # Build a tile where the only "water" class is 40 (cropland). With the
    # default, the output would be all 0. With custom=(40,), the output
    # is all 1.0 in the bbox (after reprojection averaging).
    classes = np.full((30, 30), 40, dtype=np.uint8)
    tile_path = tmp_path / "synthetic_worldcover_2.tif"
    _write_synthetic_worldcover(tile_path, classes)
    _monkeypatch_downloader(monkeypatch, tile_path)

    aoi = _small_aoi()
    out = load_worldcover_water_frac(
        aoi, year=2021, cache_dir=tmp_path / "cache", water_classes=(40,)
    )
    valid = out.values[out.values != NODATA_OUT]
    assert valid.size > 0
    # All valid cells are 1.0 (or very close after reprojection averaging).
    assert float(valid.mean()) > 0.9


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
    """Real WorldCover download for a small AOI. Skips on failure."""
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
