"""Unit tests for the GSHHG coastline loader.

We do NOT hit the real GSHHG download in CI: the network step is mocked
via monkeypatching ``urllib.request.urlopen``. The rasterise / clip / buffer
pipeline is exercised end-to-end on a small synthetic shapefile built
from ``shapely.geometry``.

The fake archive mirrors the real GSHHG layout:
    ``<root>/GSHHS_shp/c/GSHHS_c_L1.{shp,shx,dbf,prj,cpg}``
"""
from __future__ import annotations

import pathlib
import zipfile
from unittest.mock import MagicMock, patch

import geopandas as gpd
import numpy as np
import pytest
from shapely.geometry import Polygon

from mal_commonlib.aoi import AOI


def _make_gshhg_zip(tmp_path: pathlib.Path, geometry: Polygon,
                    resolution: str = "c") -> pathlib.Path:
    """Build a single-resolution GSHHG-shaped archive matching the real layout.

    Layout inside the zip:
        ``GSHHS_shp/<resolution>/GSHHS_<resolution>_L1.<ext>``
    Only ``.shp``, ``.shx``, ``.dbf`` are strictly required by geopandas;
    we also emit ``.prj`` and ``.cpg`` for completeness.
    """
    gdf = gpd.GeoDataFrame({"geometry": [geometry]}, crs="EPSG:4326")
    shp_dir = tmp_path / "shp_src"
    shp_dir.mkdir(parents=True, exist_ok=True)
    gdf.to_file(shp_dir / "GSHHS_c_L1.shp")

    zip_path = tmp_path / f"fake_gshhg_{resolution}.zip"
    subdir = f"GSHHS_shp/{resolution}"
    with zipfile.ZipFile(zip_path, "w") as zf:
        for ext in ("shp", "shx", "dbf", "prj", "cpg"):
            src = shp_dir / f"GSHHS_c_L1.{ext}"
            if src.exists():
                zf.write(src, arcname=f"{subdir}/GSHHS_{resolution}_L1.{ext}")
    return zip_path


def _patch_urlopen(zip_path: pathlib.Path):
    """Patch ``urllib.request.urlopen`` to serve bytes from ``zip_path``.

    Implementation note: the loader uses ``shutil.copyfileobj(response, out)``
    which loops on ``response.read(length)`` until EOF. We therefore stream
    the bytes in fixed-size chunks and raise StopIteration when exhausted.
    """

    def _open(url, *args, **kwargs):
        data = open(zip_path, "rb").read()
        offset = [0]

        def _read(size=-1):
            if size is None or size < 0:
                size = len(data) - offset[0]
            chunk = data[offset[0]:offset[0] + size]
            offset[0] += len(chunk)
            return chunk

        response = MagicMock()
        response.__enter__ = lambda self: self
        response.__exit__ = lambda self, *a: False
        response.read = _read
        response.readline = lambda size=-1: b""
        return response

    return patch("urllib.request.urlopen", _open)


def test_coastline_loader_returns_land_fraction(tmp_path):
    from mal_commonlib.data.loaders.coastline import load_coastline_land_mask

    zip_path = _make_gshhg_zip(
        tmp_path, Polygon([(-1, -1), (1, -1), (1, 1), (-1, 1)])
    )

    aoi = AOI.from_bbox(-0.5, -0.5, 1.5, 1.5, "EPSG:4326", "test-coast-1", 1000)
    with _patch_urlopen(zip_path):
        # resolution="c": the fake archive only ships the crude layer.
        da = load_coastline_land_mask(
            aoi, resolution="c", cache_dir=tmp_path / "cache")

    arr = np.asarray(da.values)
    assert arr.shape == aoi.cells_per_side()
    assert arr.dtype == np.float32
    # A fraction, not a binary raster: every value in [0, 1] and the edge
    # cells land partially (the polygon boundary crosses them).
    assert arr.min() >= 0.0 and arr.max() <= 1.0
    assert 0 < int((arr > 0.5).sum()) < arr.size
    assert ((arr > 0.0) & (arr < 1.0)).any(), "expected partial cells"
    assert float(arr.sum()) > 0.0
    assert da.attrs["variable"] == "land_frac"
    assert da.name == "land_mask"


def test_coastline_band_does_not_dilate_the_mask(tmp_path):
    """The coastal band is a query, not a mask mutation.

    Old behaviour: the loader dilated the land mask by ``buffer_m``, which
    moved the real coastline several km inland. Now the loader returns the
    same fraction for any band width; ``sea_mask`` applies the band.
    """
    from mal_commonlib.data.loaders.coastline import (
        distance_to_land_m,
        load_coastline_land_mask,
        sea_mask,
    )

    land_strip = Polygon([(0, 0), (0.5, 0), (0.5, 2), (0, 2)])
    zip_path = _make_gshhg_zip(tmp_path, land_strip)

    aoi = AOI.from_bbox(0.0, 0.0, 2.0, 2.0, "EPSG:4326", "test-coast-2", 1000)
    with _patch_urlopen(zip_path):
        narrow = load_coastline_land_mask(
            aoi, resolution="c", coast_band_m=0.0, cache_dir=tmp_path / "c0")
        wide = load_coastline_land_mask(
            aoi, resolution="c", coast_band_m=4000.0, cache_dir=tmp_path / "c4")

    np.testing.assert_allclose(
        np.asarray(narrow.values), np.asarray(wide.values),
        err_msg="the loader must not dilate the land fraction",
    )
    assert narrow.attrs["coast_band_m"] == 0.0
    assert wide.attrs["coast_band_m"] == 4000.0

    frac = np.asarray(wide.values)
    dist_m = distance_to_land_m(frac, 1000.0, water_floor=0.05)
    sea_narrow = sea_mask(frac, dist_m, 0.0, 0.05)
    sea_wide = sea_mask(frac, dist_m, 4000.0, 0.05)
    # The wide band keeps strictly more water (as coastal water).
    assert int(sea_wide.sum()) < int(sea_narrow.sum())
    # Land is never sea, and the band never rewrites land into water.
    assert not (sea_wide & (frac >= 0.05)).any()


def test_sea_mask_rule():
    """sea <=> land_frac < water_floor AND distance > coast_band_m."""
    from mal_commonlib.data.loaders.coastline import sea_mask

    frac = np.array([[1.0, 0.0, 0.0, 0.0]], dtype=np.float32)
    dist = np.array([[0.0, 1000.0, 3000.0, 9000.0]], dtype=np.float64)
    got = sea_mask(frac, dist, coast_band_m=2000.0, water_floor=0.05)
    np.testing.assert_array_equal(got, [[False, False, True, True]])
    # Zero band: every water cell is sea.
    np.testing.assert_array_equal(
        sea_mask(frac, dist, 0.0, 0.05), [[False, True, True, True]])
    # A cell below the floor but very close to land can never be sea when the
    # band is wide.
    np.testing.assert_array_equal(
        sea_mask(frac, dist, 10_000.0, 0.05), [[False, False, False, False]])


def test_distance_to_land_and_sea_mask_consistent():
    from mal_commonlib.data.loaders.coastline import (
        distance_to_land_m, sea_mask,
    )

    frac = np.zeros((3, 3), dtype=np.float32)
    frac[1, 1] = 1.0
    dist = distance_to_land_m(frac, 1000.0, water_floor=0.05)
    assert dist[1, 1] == 0.0
    assert abs(dist[0, 1] - 1000.0) < 1e-6
    assert abs(dist[0, 0] - 1414.2135) < 1e-3
    sea = sea_mask(frac, dist, 1000.0, 0.05)
    assert not sea[0, 1]      # exactly 1 km: not *beyond* a 1 km band
    assert sea[0, 0]          # 1.41 km: outside the band
    assert not sea[1, 1]      # land


def test_coastline_invalid_resolution_raises():
    from mal_commonlib.data.loaders.coastline import load_coastline_land_mask

    aoi = AOI.from_bbox(0.0, 0.0, 0.5, 0.5, "EPSG:4326", "test-coast-bad", 1000)
    with pytest.raises(ValueError, match="resolution must be one of"):
        load_coastline_land_mask(aoi, resolution="x")


def test_default_resolution_is_gshhg_full():
    """The loader now defaults to GSHHG full ("f"); crude was off by km."""
    from mal_commonlib.data.loaders.coastline import (
        default_coast_band_m, default_resolution, default_sea_water_floor,
    )

    assert default_resolution() == "f"
    assert default_coast_band_m() == 2000.0
    assert default_sea_water_floor() == 0.05
