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


def test_coastline_loader_returns_binary_land_mask(tmp_path):
    from mal_commonlib.data.loaders.coastline import load_coastline_land_mask

    zip_path = _make_gshhg_zip(
        tmp_path, Polygon([(-1, -1), (1, -1), (1, 1), (-1, 1)])
    )

    aoi = AOI.from_bbox(-0.5, -0.5, 1.5, 1.5, "EPSG:4326", "test-coast-1", 1000)
    with _patch_urlopen(zip_path):
        da = load_coastline_land_mask(aoi, cache_dir=tmp_path / "cache")

    arr = np.asarray(da.values)
    assert arr.shape == aoi.cells_per_side()
    assert arr.dtype == np.float32
    assert set(np.unique(arr).tolist()).issubset({0.0, 1.0})
    land_cells = int(arr.sum())
    assert 0 < land_cells < arr.size, f"unexpected land_cells={land_cells}"


def test_coastline_buffer_dilates_land(tmp_path):
    from mal_commonlib.data.loaders.coastline import load_coastline_land_mask

    land_strip = Polygon([(0, 0), (0.5, 0), (0.5, 2), (0, 2)])
    zip_path = _make_gshhg_zip(tmp_path, land_strip)

    aoi = AOI.from_bbox(0.0, 0.0, 2.0, 2.0, "EPSG:4326", "test-coast-2", 1000)
    with _patch_urlopen(zip_path):
        no_buf = load_coastline_land_mask(aoi, buffer_m=0, cache_dir=tmp_path / "c0")
        with_buf = load_coastline_land_mask(
            aoi, buffer_m=4000.0, cache_dir=tmp_path / "c4"
        )

    no_buf_cells = int(np.asarray(no_buf.values).sum())
    with_buf_cells = int(np.asarray(with_buf.values).sum())
    assert with_buf_cells > no_buf_cells, (
        f"buffer should add cells: {with_buf_cells} vs {no_buf_cells}"
    )


def test_coastline_invalid_resolution_raises():
    from mal_commonlib.data.loaders.coastline import load_coastline_land_mask

    aoi = AOI.from_bbox(0.0, 0.0, 0.5, 0.5, "EPSG:4326", "test-coast-bad", 1000)
    with pytest.raises(ValueError, match="resolution must be one of"):
        load_coastline_land_mask(aoi, resolution="x")
