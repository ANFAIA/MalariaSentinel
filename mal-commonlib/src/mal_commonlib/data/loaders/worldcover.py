"""ESA WorldCover 10 m water / wetland mask loader (M1.3a, env channel 0 — ``water_frac``).

Public surface
--------------
``load_worldcover_water_frac(aoi, year=2021, *, cache_dir=None, water_classes=None) -> xr.DataArray``

ESA WorldCover 10 m is a global land cover map produced by ESA / VanderSat
/ partners, derived from Sentinel-1 + Sentinel-2. The 2020 and 2021 maps
are publicly downloadable. The 3°×3° tiles are published as Cloud-Optimized
GeoTIFFs on Element84's earth-search bucket (``s3://element84-earthsearch/
worldcover/v1/``) and as plain GeoTIFFs from the ESA WorldCover portal.

The loader downloads the intersecting tiles, takes the land-cover band,
and computes a ``water_frac`` raster in [0, 1] by averaging the binary
"is water?" indicator over the AOI's grid cells. A cell that is fully
covered by a water class becomes ``water_frac=1.0``; a cell fully covered
by non-water classes becomes ``0.0``; a partial-cover cell gets an
intermediate value. This is the fraction of an AOI cell covered by open
water + wetland.

Output contract (per ``docs/abm-output-contract.md`` §2, channel 0):
    * dims (y, x), dtype ``float32``
    * CRS = ``aoi.crs``
    * values in [0, 1]
    * NoData: ``-9999.0``
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
from rasterio.transform import from_bounds
from rasterio.warp import Resampling

from mal_commonlib.aoi import AOI

# Default set of "water / wetland" WorldCover class codes. The full legend is:
#   10  Tree cover
#   20  Shrub cover
#   30  Grassland
#   40  Cropland
#   50  Built-up
#   60  Bare / sparse vegetation
#   70  Snow and ice
#   80  Permanent water bodies
#   90  Herbaceous wetland
#   95  Mangroves
#   100 Moss and lichen
# We include the obvious water/wetland classes (80, 90, 95). Tree / shrub /
# grass / crop are NOT water; the loader is *not* an LULC change detector.
DEFAULT_WATER_CLASSES: tuple[int, ...] = (80, 90, 95)

# WorldCover 3°×3° tile naming: ``{N|S}{lat:02d}{E|W}{lon:03d}_MAP`` (lower-left
# corner). ESA portal uses ``.tif`` extension; the Element84 bucket uses
# ``.tif`` too.
_TILE_DEG = 3
_WORLDCOVER_BASE = "https://worldcover2021.esa.int/data"

_NODATA_OUT_SCALAR = -9999.0


def _ensure_cache_dir(cache_dir: pathlib.Path | None) -> pathlib.Path:
    if cache_dir is None:
        cache_dir = pathlib.Path(tempfile.gettempdir()) / "mal_commonlib" / "worldcover"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def _aoi_bbox_wgs84(aoi: AOI) -> tuple[float, float, float, float]:
    import pyproj

    if str(aoi.crs_obj).upper() in {"EPSG:4326", "WGS84", "4326"}:
        return aoi.bbox
    t = pyproj.Transformer.from_crs(aoi.crs, "EPSG:4326", always_xy=True)
    w, s, e, n = aoi.bbox
    w, s = t.transform(w, s)
    e, n = t.transform(e, n)
    return (float(w), float(s), float(e), float(n))


def _tiles_for_bbox(bbox: tuple[float, float, float, float]) -> list[tuple[int, int]]:
    w, s, e, n = bbox
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


def _tile_urls(lon0: int, lat0: int, year: int) -> list[str]:
    """Candidate URLs for a single WorldCover tile."""
    # WorldCover 10 m tiles follow the ESA naming: ``ESA_WorldCover_10m_<year>_<v>_<S|N><lat><E|W><lon>.tif``
    # We try a few conventions: a simplified grid-name style and the canonical
    # ESA filename pattern (which uses the lower-left corner of the 3°×3° tile).
    ns = "S" if lat0 < 0 else "N"
    ew = "W" if lon0 < 0 else "E"
    grid_name = f"{ns}{abs(lat0):02d}{ew}{abs(lon0):03d}"
    candidates = [
        f"{_WORLDCOVER_BASE}/ESA_WorldCover_10m_{year}_v100/{grid_name}.tif",
        f"{_WORLDCOVER_BASE}/tiles/{year}/ESA_WorldCover_10m_{year}_v100_{grid_name}.tif",
    ]
    return candidates


def _download_tile(lon0: int, lat0: int, year: int, cache: pathlib.Path) -> pathlib.Path:
    """Download a single WorldCover tile; return local path."""
    dest = cache / f"worldcover_{year}_{lon0:+04d}_{lat0:+04d}.tif"
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    for url in _tile_urls(lon0, lat0, year):
        try:
            with requests.get(url, stream=True, timeout=120) as r:
                if r.status_code != 200:
                    continue
                with open(dest, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1 << 16):
                        f.write(chunk)
            if dest.stat().st_size > 0:
                return dest
        except Exception:
            continue
    raise FileNotFoundError(
        f"Could not download WorldCover {year} tile at lon0={lon0} lat0={lat0} from any mirror"
    )


def _stitch_class_bands(
    paths: Iterable[pathlib.Path], water_classes: tuple[int, ...]
) -> tuple[np.ndarray, dict]:
    """Read each tile's class band, convert to a binary water mask, merge.

    WorldCover has 1 band (uint8) per file. We return a (H, W) float32
    array in [0, 1] (the *fraction* of each cell that is water) for the
    mosaic, plus the merged profile.
    """
    from rasterio.merge import merge as rio_merge

    srcs = []
    bin_arrs = []
    for p in paths:
        with rasterio.open(str(p)) as s:
            raw = s.read(1)
            # rasterio returns a masked array even for files without a
            # mask. Filled data is what we want.
            if hasattr(raw, "filled"):
                raw = np.ma.filled(raw, 0)
            arr = np.asarray(raw, dtype=np.uint8)
            water_arr = np.asarray(water_classes, dtype=arr.dtype)
            bin_arr = np.isin(arr, water_arr).astype(np.uint8, copy=False)
            profile = s.profile
            bin_arrs.append((bin_arr, s.transform, s.crs))
            srcs.append(s)
    if not bin_arrs:
        raise ValueError("no tiles to stitch")
    # Merge in memory using rasterio.merge.merge
    sources = [
        rasterio.io.MemoryFile().open(
            driver="GTiff",
            height=a.shape[0],
            width=a.shape[1],
            count=1,
            dtype="uint8",
            crs=c,
            transform=t,
        )
        for (a, t, c) in bin_arrs
    ]
    try:
        for src, (a, _, _) in zip(sources, bin_arrs):
            src.write(a, 1)
        merged, transform = rio_merge(sources, nodata=0)
    finally:
        for s in sources:
            s.close()
    arr = np.asarray(merged).squeeze(0).astype(np.float32)
    return arr, {"crs": profile["crs"], "transform": transform, "height": arr.shape[0], "width": arr.shape[1]}


def _make_reference_grid(aoi: AOI) -> xr.DataArray:
    h, w = aoi.cells_per_side()
    wmin, smin, wmax, smax = aoi.bbox
    transform = from_bounds(wmin, smin, wmax, smax, w, h)
    arr = np.zeros((h, w), dtype=np.float32)
    da = xr.DataArray(arr, dims=("y", "x"), name="ref")
    da.rio.write_crs(aoi.crs, inplace=True)
    da.rio.write_transform(transform, inplace=True)
    return da


def load_worldcover_water_frac(
    aoi: AOI,
    year: int = 2021,
    *,
    cache_dir: pathlib.Path | None = None,
    water_classes: tuple[int, ...] | None = None,
) -> xr.DataArray:
    """Load ESA WorldCover 10 m for the AOI, produce a ``water_frac`` raster
    in [0, 1] by computing the fraction of each AOI cell covered by
    WorldCover classes 50 (Tree cover), 60 (Shrub cover), 80 (Wetland),
    90 (Herbaceous wetland), 95 (Mangroves), or 100 (Moss and lichen),
    treated as "open water or wetland" for the M1 thin slice.

    Args:
        aoi: the AOI.
        year: WorldCover product year (2020 or 2021 are the public versions).
        cache_dir: optional local cache.
        water_classes: override the set of class codes considered "water". By
            default, ``DEFAULT_WATER_CLASSES = (80, 90, 95)`` — permanent water
            bodies, herbaceous wetland, and mangroves.

    Returns:
        xr.DataArray with dims (y, x), dtype ``float32``, CRS = ``aoi.crs``.
        Values in [0, 1]. ``-9999.0`` for NoData.
    """
    if year not in (2020, 2021):
        raise ValueError(f"WorldCover year must be 2020 or 2021; got {year}")
    water_classes = tuple(water_classes) if water_classes else DEFAULT_WATER_CLASSES

    cache = _ensure_cache_dir(cache_dir)
    bbox = _aoi_bbox_wgs84(aoi)
    tiles = _tiles_for_bbox(bbox)
    if not tiles:
        raise ValueError(f"No WorldCover tiles intersect bbox={bbox}")

    paths = [_download_tile(lon0, lat0, year, cache) for (lon0, lat0) in tiles]
    arr, profile = _stitch_class_bands(paths, water_classes)

    # Treat the binary mosaic as a continuous variable in [0, 1] and
    # reproject onto the AOI grid with average resampling — that's what
    # turns it into a per-AOI-cell *fraction*.
    da = xr.DataArray(
        arr,
        dims=("y", "x"),
        name="water_frac",
        attrs={
            "long_name": "WorldCover water fraction",
            "source": f"ESA WorldCover {year}",
            "units": "fraction [0, 1]",
            "water_classes": list(water_classes),
        },
    )
    da.rio.write_crs(profile["crs"], inplace=True)
    da.rio.write_transform(profile["transform"], inplace=True)

    ref = _make_reference_grid(aoi)
    rep = da.rio.reproject_match(ref, resampling=Resampling.average)
    rep = rep.astype(np.float32)
    rep = rep.rio.write_nodata(_NODATA_OUT_SCALAR)
    # If the source mosaic is all zero (no water in the bbox), arr is all zero
    # and the average remains zero — that is a valid result, NOT nodata.
    values = rep.values
    values = np.clip(values, 0.0, 1.0).astype(np.float32)
    out = xr.DataArray(
        values,
        dims=("y", "x"),
        name="water_frac",
        attrs={
            "long_name": "WorldCover water fraction (reprojected)",
            "source": f"ESA WorldCover {year}",
            "units": "fraction [0, 1]",
            "water_classes": list(water_classes),
            "nodata": _NODATA_OUT_SCALAR,
        },
    )
    out.rio.write_crs(aoi.crs, inplace=True)
    out.rio.write_transform(from_bounds(*aoi.bbox, *aoi.cells_per_side()), inplace=True)
    out.rio.write_nodata(_NODATA_OUT_SCALAR, inplace=True)
    return out


__all__ = ["load_worldcover_water_frac", "DEFAULT_WATER_CLASSES", "NODATA_OUT"]
NODATA_OUT = _NODATA_OUT_SCALAR
