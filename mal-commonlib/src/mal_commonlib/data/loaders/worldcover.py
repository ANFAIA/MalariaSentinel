"""ESA WorldCover 10 m water / wetland mask loader (M1.3a, env channel 0 — ``water_frac``).

Public surface
--------------
``load_worldcover_water_frac(aoi, year=2021, month=None, *, cache_dir=None, water_classes=None) -> xr.DataArray``

The ``month`` parameter is accepted for signature uniformity with the other
M1.3a loaders (``build_env`` calls every loader as ``loader(aoi, year, month)``)
but is ignored: ESA WorldCover 10 m is an annual product, not monthly.

ESA WorldCover 10 m is a global land cover map produced by ESA / VanderSat
/ partners, derived from Sentinel-1 + Sentinel-2. The 2020 and 2021 maps
are publicly available. The 3°×3° tiles are published as Cloud-Optimized
GeoTIFFs on the official ESA / AWS Open Data bucket
(``s3://esa-worldcover/``, mirrored at
``https://esa-worldcover.s3.eu-central-1.amazonaws.com/``) AND on the
Microsoft Planetary Computer STAC catalog (``esa-worldcover`` collection).

Distribution choice (as of 2026-07)
-----------------------------------
The M2 real-data validation run observed a 15-min hang on the S3 path
even though the GET of a single 24 MB tile completes in ~2 s. The hang
is downstream of the network: each 3°×3° tile is 36 000 × 36 000 pixels
(~1.3 GB in memory), and the previous loader read the whole tile, copied
it through a ``rasterio.io.MemoryFile`` for each intersecting tile, and
then merged those memory files — multi-GB of memory traffic per tile
that thrashes on machines with <16 GB RAM.

This loader now uses the **Planetary Computer** STAC catalog as the
primary source. The STAC search returns the intersecting 3°×3° tiles
and we read only the **AOI bbox window** from each (typically a few
hundred KB instead of 1.3 GB) before merging. The output contract is
unchanged. The S3 URL is still listed as a reference in this docstring
in case a future user wants to add it as an explicit fallback.

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
import requests  # noqa: F401 — kept for tests / future S3 fallback
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

# Tile size in degrees. WorldCover 3°×3° tiles are anchored on multiples
# of 3 from the equator / prime meridian, e.g. ``N03W006`` covers
# 3°N–6°N, 6°W–3°W.
_TILE_DEG = 3

# Reference S3 URL (kept for documentation; not the active path):
_WORLDCOVER_S3_BASE = "https://esa-worldcover.s3.eu-central-1.amazonaws.com"
_VERSION_FOR_YEAR: dict[int, str] = {2020: "v100", 2021: "v200"}

# Microsoft Planetary Computer STAC catalog — WorldCover is exposed under
# the ``esa-worldcover`` collection, with the same 3°×3° tile scheme as
# the S3 bucket. The asset key is ``map`` (a 36000×36000 uint8 GeoTIFF).
_PC_STAC_URL = "https://planetarycomputer.microsoft.com/api/stac/v1"
_PC_COLLECTION = "esa-worldcover"

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


def _make_reference_grid(aoi: AOI) -> xr.DataArray:
    h, w = aoi.cells_per_side()
    wmin, smin, wmax, smax = aoi.bbox
    transform = from_bounds(wmin, smin, wmax, smax, w, h)
    arr = np.zeros((h, w), dtype=np.float32)
    da = xr.DataArray(arr, dims=("y", "x"), name="ref")
    da.rio.write_crs(aoi.crs, inplace=True)
    da.rio.write_transform(transform, inplace=True)
    return da


# -- Planetary Computer STAC loader (primary path) --------------------------


def _load_worldcover_pc(
    aoi: AOI,
    year: int,
    water_classes: tuple[int, ...],
) -> tuple[np.ndarray, dict]:
    """Read the WorldCover ``map`` band for the AOI bbox via the Planetary
    Computer STAC catalog and return a (binary-water-mask) mosaic in
    memory.

    This is the primary download path (M2): the 3°×3° tiles are 1.3 GB
    each in memory, so we read only the AOI bbox window from each
    intersecting tile (typically a few hundred KB) and merge those
    small windows with ``rasterio.merge``. The result has the same CRS
    and dtype as a single tile.

    Returns:
        (arr, profile) where ``arr`` is a ``(H, W)`` float32 array in
        [0, 1] (per-cell water fraction within the merged AOI bbox
        window) and ``profile`` is a dict with ``crs``, ``transform``,
        ``height``, ``width``.
    """
    import planetary_computer
    import pystac_client
    from rasterio.merge import merge as rio_merge
    from rasterio.windows import from_bounds as rio_window_from_bounds

    bbox = _aoi_bbox_wgs84(aoi)
    catalog = pystac_client.Client.open(_PC_STAC_URL)
    search = catalog.search(
        collections=[_PC_COLLECTION],
        bbox=list(bbox),
        datetime=f"{year}-01-01T00:00:00Z/{year}-12-31T23:59:59Z",
    )
    items = list(search.items())
    if not items:
        raise FileNotFoundError(
            f"No WorldCover tiles in Planetary Computer for bbox={bbox} year={year}"
        )
    signed_items = [planetary_computer.sign(item) for item in items]

    # For each tile, read ONLY the AOI bbox window. Each 3°×3° tile at 10 m
    # is 36 000 × 36 000 pixels; the AOI window is typically a few hundred
    # pixels on a side.
    bin_windows: list[tuple[np.ndarray, object, object]] = []
    water_arr = np.asarray(water_classes, dtype=np.uint8)
    for item in signed_items:
        href = item.assets["map"].href
        with rasterio.open(href) as src:
            win = rio_window_from_bounds(*bbox, src.transform)
            win = win.intersection(rasterio.windows.Window(0, 0, src.width, src.height))
            if win.width <= 0 or win.height <= 0:
                continue
            raw = src.read(1, window=win)
            if hasattr(raw, "filled"):
                raw = np.ma.filled(raw, 0)
            arr = np.asarray(raw, dtype=np.uint8)
            bin_arr = np.isin(arr, water_arr).astype(np.uint8, copy=False)
            win_transform = src.window_transform(win)
            bin_windows.append((bin_arr, win_transform, src.crs))

    if not bin_windows:
        raise ValueError(
            f"No WorldCover tile windows intersected the AOI bbox={bbox}"
        )

    # Merge the small per-tile windows in memory. Each window is much
    # smaller than the full tile, so this is fast.
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
        for (a, t, c) in bin_windows
    ]
    try:
        for src, (a, _, _) in zip(sources, bin_windows):
            src.write(a, indexes=1)
        merged, transform = rio_merge(sources, nodata=0)
    finally:
        for s in sources:
            s.close()
    arr = np.asarray(merged).squeeze(0).astype(np.float32)
    profile = {
        "crs": bin_windows[0][2],
        "transform": transform,
        "height": arr.shape[0],
        "width": arr.shape[1],
    }
    return arr, profile


# -- legacy S3 path (kept for tests / future fallback) ---------------------


def _tile_urls(lon0: int, lat0: int, year: int) -> list[str]:
    """Candidate URLs for a single WorldCover tile (reference only)."""
    ns = "S" if lat0 < 0 else "N"
    ew = "W" if lon0 < 0 else "E"
    grid_name = f"{ns}{abs(lat0):02d}{ew}{abs(lon0):03d}"
    version = _VERSION_FOR_YEAR.get(year)
    if version is None:
        return []
    return [
        f"{_WORLDCOVER_S3_BASE}/{version}/{year}/map/"
        f"ESA_WorldCover_10m_{year}_{version}_{grid_name}_Map.tif"
    ]


def _download_tile(lon0: int, lat0: int, year: int, cache: pathlib.Path) -> pathlib.Path:
    """Download a single WorldCover tile from the S3 mirror; return local path.

    Kept for tests and for callers that explicitly want the S3 path (e.g.
    offline air-gapped environments that mirror the S3 bucket). The
    public ``load_worldcover_water_frac`` does NOT use this helper any
    more — it goes through ``_load_worldcover_pc`` to avoid the
    1.3 GB-per-tile memory explosion of reading whole tiles.
    """
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

    Note: this reads the WHOLE tile to a numpy array, which costs ~1.3 GB
    of memory per 3°×3° tile. Prefer ``_load_worldcover_pc`` for new
    callers — it reads only the AOI bbox window per tile.
    """
    from rasterio.merge import merge as rio_merge

    srcs = []
    bin_arrs = []
    for p in paths:
        with rasterio.open(str(p)) as s:
            raw = s.read(1)
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
            src.write(a, indexes=1)
        merged, transform = rio_merge(sources, nodata=0)
    finally:
        for s in sources:
            s.close()
    arr = np.asarray(merged).squeeze(0).astype(np.float32)
    return arr, {"crs": profile["crs"], "transform": transform, "height": arr.shape[0], "width": arr.shape[1]}


# -- public API -------------------------------------------------------------


def load_worldcover_water_frac(
    aoi: AOI,
    year: int = 2021,
    month: int | None = None,
    *,
    cache_dir: pathlib.Path | None = None,
    water_classes: tuple[int, ...] | None = None,
) -> xr.DataArray:
    """Load ESA WorldCover 10 m for the AOI, produce a ``water_frac`` raster
    in [0, 1] by computing the fraction of each AOI cell covered by
    WorldCover classes 80 (Permanent water bodies), 90 (Herbaceous
    wetland), 95 (Mangroves), treated as "open water or wetland".

    The loader goes through the Microsoft Planetary Computer STAC catalog
    (``esa-worldcover`` collection) and reads only the AOI bbox window
    from each intersecting 3°×3° tile. This avoids the 1.3 GB-per-tile
    memory cost of reading the full tiles and unblocks the M2 real-data
    validation (the previous S3 path hung for 15+ min on Ghana).

    Args:
        aoi: the AOI.
        year: WorldCover product year (2020 or 2021 are the public versions).
        month: accepted for ``build_env`` signature uniformity; ignored.
            WorldCover 10 m is an annual product, not monthly.
        cache_dir: optional local cache (currently unused — the STAC
            signed URLs stream directly).
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

    bbox = _aoi_bbox_wgs84(aoi)
    if not _tiles_for_bbox(bbox):
        raise ValueError(f"No WorldCover tiles intersect bbox={bbox}")

    arr, profile = _load_worldcover_pc(aoi, year, water_classes)

    # Treat the binary mosaic as a continuous variable in [0, 1] and
    # reproject onto the AOI grid with average resampling — that's what
    # turns it into a per-AOI-cell *fraction*.
    da = xr.DataArray(
        arr,
        dims=("y", "x"),
        name="water_frac",
        attrs={
            "long_name": "WorldCover water fraction",
            "source": f"ESA WorldCover {year} (Planetary Computer STAC)",
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
            "source": f"ESA WorldCover {year} (Planetary Computer STAC)",
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
