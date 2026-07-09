"""MERIT DEM 90 m loader (M1.3a, terrain).

Public surface
--------------
``load_merit_dem(aoi, *, cache_dir=None) -> xr.DataArray``

MERIT DEM (Multi-Error-Removed Improved-Terrain DEM) is a 90 m hydrologically
conditioned global DEM derived from SRTM v3.0 / AW3D-30m / GMTED2010 / VFP.
It is preferred for TWI computation because the original SRTM has many
spurious pits that produce noise in the contributing-area calculation.

Tiles are 5°×5° GeoTIFFs in EPSG:4326 (degrees). For the Ghana AOI
(~-3.5..1.5 lon, ~4.5..11.5 lat) we need 2×2 = 4 tiles. The public mirror at
``http://hydro.iis.u-tokyo.ac.jp/~yamadai/MERIT_DEM/`` provides a 5-degree
index. We download the intersecting tiles via plain ``requests`` (already
present in the dep set) into ``cache_dir`` and merge them with
``rasterio.merge.merge`` before reprojecting to the AOI grid.

Output contract (used by TWI and the ABM):
    * dims (y, x), dtype ``float32``
    * CRS = ``aoi.crs``
    * values in metres
    * NoData: ``-9999.0`` (post-reproject fill policy)
"""
from __future__ import annotations

import pathlib
import tempfile
from typing import Iterable

import numpy as np
import rasterio
import requests
import rioxarray  # noqa: F401
import xarray as xr
from rasterio.io import MemoryFile
from rasterio.merge import merge as rio_merge
from rasterio.transform import from_bounds
from rasterio.warp import Resampling

from mal_commonlib.aoi import AOI

# Public mirror at U-Tokyo (Yamazaki). Per-tile filenames follow
# ``<lon_min>_<lon_max>_l.tif`` and ``<lat_min>_<lat_max>_l.tif`` (lower-left
# corner). Verified by webfetch of http://hydro.iis.u-tokyo.ac.jp/~yamadai/MERIT_DEM/.
_MERIT_BASE_URL = "http://hydro.iis.u-tokyo.ac.jp/~yamadai/MERIT_DEM"
# Fallback (Hydrosheds mirror) — same tile naming convention.
_MERIT_BASE_URL_FALLBACK = "https://data.hydrosheds.org/file/MERIT/v1.0.1"

# 5°×5° tile grid; tiles are anchored on 5-degree boundaries.
_TILE_DEG = 5

# MERIT's official fill value is -9999. We expose -9999 in the output as well.
_MERIT_FILL = -9999
_NODATA_OUT_SCALAR = -9999.0


def _ensure_cache_dir(cache_dir: pathlib.Path | None) -> pathlib.Path:
    if cache_dir is None:
        cache_dir = pathlib.Path(tempfile.gettempdir()) / "mal_commonlib" / "merit"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def _aoi_bbox_wgs84(aoi: AOI) -> tuple[float, float, float, float]:
    """Return (W, S, E, N) in WGS-84 degrees. Reprojects if needed."""
    import pyproj

    if str(aoi.crs_obj).upper() in {"EPSG:4326", "WGS84", "4326"}:
        return aoi.bbox
    t = pyproj.Transformer.from_crs(aoi.crs, "EPSG:4326", always_xy=True)
    w, s, e, n = aoi.bbox
    w, s = t.transform(w, s)
    e, n = t.transform(e, n)
    return (float(w), float(s), float(e), float(n))


def _tiles_for_bbox(
    bbox: tuple[float, float, float, float],
) -> list[tuple[int, int]]:
    """Return the list of (lon_tile, lat_tile) anchors covering bbox.

    Anchors are multiples of ``_TILE_DEG``. The bbox is in WGS-84 degrees.
    """
    w, s, e, n = bbox
    # Floor west/south to the nearest 5-degree grid anchor; ceiling east/north.
    lon0 = int(np.floor(w / _TILE_DEG) * _TILE_DEG)
    lat0 = int(np.floor(s / _TILE_DEG) * _TILE_DEG)
    lon1 = int(np.ceil(e / _TILE_DEG) * _TILE_DEG)
    lat1 = int(np.ceil(n / _TILE_DEG) * _TILE_DEG)
    tiles: list[tuple[int, int]] = []
    lon = lon0
    while lon < lon1:
        lat = lat0
        while lat < lat1:
            tiles.append((lon, lat))
            lat += _TILE_DEG
        lon += _TILE_DEG
    return tiles


def _tile_urls(lon0: int, lat0: int) -> list[str]:
    """Return candidate URLs for a single MERIT tile (multiple mirrors)."""
    # MERIT naming: e.g. ``n30w090_merit.tif`` for the 30N-35N, 90W-85W tile,
    # lower-left corner. Hemisphere letters: ``n``/``s`` for latitude,
    # ``e``/``w`` for longitude. Pad to 3 digits.
    lon_label = f"{abs(lon0):03d}{'w' if lon0 < 0 else 'e'}"
    lat_label = f"{abs(lat0):02d}{'s' if lat0 < 0 else 'n'}"
    base = f"{lat_label}{lon_label}_merit.tif"
    return [
        f"{_MERIT_BASE_URL}/{base}",
        f"{_MERIT_BASE_URL_FALLBACK}/{base}",
    ]


def _download_tile(lon0: int, lat0: int, cache: pathlib.Path) -> pathlib.Path:
    """Download a single MERIT tile to ``cache``; return the local path."""
    dest = cache / f"merit_{lon0:+04d}_{lat0:+04d}.tif"
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    for url in _tile_urls(lon0, lat0):
        try:
            with requests.get(url, stream=True, timeout=60) as r:
                r.raise_for_status()
                with open(dest, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1 << 16):
                        f.write(chunk)
            if dest.stat().st_size > 0:
                return dest
        except Exception:
            # try next mirror
            continue
    raise FileNotFoundError(
        f"Could not download MERIT tile at lon0={lon0} lat0={lat0} from any mirror"
    )


def _stitch_tiles(paths: Iterable[pathlib.Path]) -> tuple[np.ndarray, dict]:
    """Merge the per-tile GeoTIFFs in memory; return (arr, profile)."""
    srcs = [rasterio.open(str(p)) for p in paths]
    try:
        arr, transform = rio_merge(srcs, res=(_TILE_DEG, _TILE_DEG), nodata=_MERIT_FILL)
        profile = {
            "crs": srcs[0].crs,
            "transform": transform,
            "height": arr.shape[1],
            "width": arr.shape[2],
        }
    finally:
        for s in srcs:
            s.close()
    # Squeeze the (1, H, W) -> (H, W) layout that rio_merge returns.
    arr = np.asarray(arr).squeeze(0).astype(np.float32)
    return arr, profile


def _make_reference_grid(aoi: AOI) -> xr.DataArray:
    h, w = aoi.cells_per_side()
    wmin, smin, wmax, smax = aoi.bbox
    transform = from_bounds(wmin, smin, wmax, smax, w, h)
    arr = np.zeros((h, w), dtype=np.float32)
    da = xr.DataArray(arr, dims=("y", "x"), name="ref")
    da.rio.write_crs(aoi.crs, inplace=True)
    da.rio.write_transform(transform, inplace=True)
    return da


def load_merit_dem(
    aoi: AOI,
    *,
    cache_dir: pathlib.Path | None = None,
) -> xr.DataArray:
    """Load MERIT DEM 90 m for the AOI, reprojected to the AOI's grid.

    MERIT is hydrologically conditioned (no spurious pits), which makes
    it the preferred DEM for TWI computation. Public download from
    http://hydro.iis.u-tokyo.ac.jp/~yamadai/MERIT_DEM/ (or the
    per-tile distribution at https://data.hydrosheds.org/).

    Args:
        aoi: the AOI.
        cache_dir: optional local cache for downloaded tiles.

    Returns:
        xr.DataArray with dims (y, x), dtype ``float32``, CRS = ``aoi.crs``.
        Values in metres. ``-9999.0`` for NoData.
    """
    cache = _ensure_cache_dir(cache_dir)
    bbox = _aoi_bbox_wgs84(aoi)
    tiles = _tiles_for_bbox(bbox)
    if not tiles:
        raise ValueError(f"No MERIT tiles intersect bbox={bbox}")

    paths = [_download_tile(lon0, lat0, cache) for (lon0, lat0) in tiles]
    arr, profile = _stitch_tiles(paths)

    # Build an in-memory DataArray on the merged tile grid.
    da = xr.DataArray(
        arr,
        dims=("y", "x"),
        name="elevation",
        attrs={
            "long_name": "MERIT DEM elevation",
            "source": "MERIT DEM v1.0.1",
            "units": "metres",
            "nodata": _MERIT_FILL,
        },
    )
    da.rio.write_crs(profile["crs"], inplace=True)
    da.rio.write_transform(profile["transform"], inplace=True)
    da = da.rio.write_nodata(_MERIT_FILL, inplace=True)

    # Reproject to the AOI's grid using bilinear.
    ref = _make_reference_grid(aoi)
    rep = da.rio.reproject_match(ref, resampling=Resampling.bilinear)
    rep = rep.astype(np.float32)
    rep = rep.rio.write_nodata(_NODATA_OUT_SCALAR)
    # Replace source fill (which may have been promoted to NaN by reproject) with -9999.0
    values = rep.values
    nodata_mask = ~np.isfinite(values)
    values = np.where(nodata_mask, np.float32(_NODATA_OUT_SCALAR), values).astype(np.float32)
    out = xr.DataArray(
        values,
        dims=("y", "x"),
        name="elevation",
        attrs={
            "long_name": "MERIT DEM elevation (reprojected)",
            "source": "MERIT DEM v1.0.1",
            "units": "metres",
            "nodata": _NODATA_OUT_SCALAR,
        },
    )
    out.rio.write_crs(aoi.crs, inplace=True)
    out.rio.write_transform(from_bounds(*aoi.bbox, *aoi.cells_per_side()), inplace=True)
    out.rio.write_nodata(_NODATA_OUT_SCALAR, inplace=True)
    return out


__all__ = ["load_merit_dem", "NODATA_OUT"]
NODATA_OUT = _NODATA_OUT_SCALAR
