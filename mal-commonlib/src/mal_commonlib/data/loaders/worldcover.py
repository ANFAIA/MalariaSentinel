"""ESA WorldCover 2021 v200 land cover loader (M12 — water dataset).

Public surface
--------------
``load_worldcover_landcover(aoi, *, year=2021, cache_dir=None) -> xr.DataArray``

Plus derived mask helpers:
    * ``load_worldcover_permanent_water(aoi, ...)`` — binary mask of class 80
    * ``load_worldcover_wetland(aoi, ...)`` — binary mask of class 90
    * ``load_worldcover_mangrove(aoi, ...)`` — binary mask of class 95

The ``month`` parameter is accepted for signature uniformity but ignored:
WorldCover is an annual product.

Why this loader exists
----------------------
M12 needs land cover information to classify habitat cells and distinguish
permanent water (class 80), herbaceous wetland (class 90), and mangroves
(class 95) from other land cover types. ESA WorldCover 2021 at 10 m is the
highest-resolution global land cover product available, and is accessible
via the Microsoft Planetary Computer STAC catalog without authentication.

ESA WorldCover 2021 v200 class codes (11 classes):
    10: Tree cover
    20: Shrubland
    30: Grassland
    40: Cropland
    50: Built-up
    60: Bare / sparse vegetation
    70: Snow and Ice
    80: Permanent water bodies    ← M12 key class
    90: Herbaceous wetland        ← M12 key class
    95: Mangroves                 ← M12 key class
    100: Moss and lichen

Output contract:
    * dims (y, x), dtype ``int32`` (for the full land cover)
    * dims (y, x), dtype ``float32`` (for binary masks: {0.0, 1.0})
    * CRS = ``aoi.crs``
    * NoData: ``-9999`` (int) or ``-9999.0`` (float)
"""
from __future__ import annotations

import pathlib
import tempfile
from typing import TYPE_CHECKING

import numpy as np
import rasterio
import rioxarray  # noqa: F401
import xarray as xr
from rasterio.transform import from_bounds
from rasterio.warp import Resampling

if TYPE_CHECKING:
    from mal_commonlib.aoi import AOI

# Microsoft Planetary Computer STAC catalog for ESA WorldCover 2021 v200.
_PC_STAC_URL = "https://planetarycomputer.microsoft.com/api/stac/v1"
_PC_COLLECTION = "esa-worldcover"
_PC_ASSET = "map"  # the 10 m land cover classification band

# ESA WorldCover 2021 v200 class codes
WC_TREE = 10
WC_SHRUBLAND = 20
WC_GRASSLAND = 30
WC_CROPLAND = 40
WC_BUILTUP = 50
WC_BARE = 60
WC_SNOW_ICE = 70
WC_WATER = 80
WC_WETLAND = 90
WC_MANGROVE = 95
WC_MOSS_LICHEN = 100

# All valid class codes.
WC_CLASSES = {
    WC_TREE, WC_SHRUBLAND, WC_GRASSLAND, WC_CROPLAND, WC_BUILTUP,
    WC_BARE, WC_SNOW_ICE, WC_WATER, WC_WETLAND, WC_MANGROVE, WC_MOSS_LICHEN,
}

# M12-relevant water/wetland classes.
WC_WATER_CLASSES = {WC_WATER, WC_WETLAND, WC_MANGROVE}
DEFAULT_WATER_CLASSES = tuple(sorted(WC_WATER_CLASSES))

# Year range. The ESA WorldCover 2021 v200 is a single static product
# (published 2021); PC may also have the 2020 version.
_MIN_YEAR: int = 2020
_MAX_YEAR: int = 2021

_NODATA_OUT_INT = -9999
_NODATA_OUT_SCALAR = -9999.0


def _ensure_cache_dir(cache_dir: pathlib.Path | None) -> pathlib.Path:
    if cache_dir is None:
        cache_dir = pathlib.Path(tempfile.gettempdir()) / "mal_commonlib" / "worldcover"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def _aoi_bbox_wgs84(aoi: "AOI") -> tuple[float, float, float, float]:
    """Return (W, S, E, N) in WGS-84 degrees. Reprojects if needed."""
    import pyproj

    if str(aoi.crs_obj).upper() in {"EPSG:4326", "WGS84", "4326"}:
        return aoi.bbox
    t = pyproj.Transformer.from_crs(aoi.crs, "EPSG:4326", always_xy=True)
    w, s, e, n = aoi.bbox
    w, s = t.transform(w, s)
    e, n = t.transform(e, n)
    return (float(w), float(s), float(e), float(n))


def _load_worldcover_pc(
    aoi: "AOI",
    year: int,
    water_classes: tuple[int, ...] | None = None,
) -> tuple[np.ndarray, dict]:
    """Read ESA WorldCover 2021 v200 ``map`` band via Planetary Computer.

    The 10 m land cover raster is streamed tile-by-tile into the AOI grid.
    Because WorldCover is categorical (integer class codes), we use
    nearest-neighbour reprojection to preserve class integrity.

    Returns:
        (arr, profile) where ``arr`` is a ``(H, W)`` int32 array with
        ESA WorldCover class codes (10–100) and ``-9999`` for NoData.
    """
    import planetary_computer
    import pystac_client
    from rasterio.warp import reproject
    from rasterio.windows import from_bounds as rio_window_from_bounds

    bbox = _aoi_bbox_wgs84(aoi)
    catalog = pystac_client.Client.open(_PC_STAC_URL)
    search = catalog.search(
        collections=[_PC_COLLECTION],
        bbox=list(bbox),
    )
    items = list(search.items())
    if not items:
        raise FileNotFoundError(
            f"No ESA WorldCover tiles in Planetary Computer for bbox={bbox}"
        )
    signed_items = [planetary_computer.sign(item) for item in items]

    H, W = aoi.cells_per_side()
    H = int(H)
    W = int(W)
    ref_transform = from_bounds(*aoi.bbox, W, H)

    # Use a vote accumulator for categorical data: each tile votes for the
    # most common class in each AOI cell.
    vote_count = np.zeros((H, W, 11), dtype=np.float32)
    # Map class codes 10–100 → indices 0–10.  class_to_idx maps
    # the actual class code to the axis index.
    all_classes = sorted(WC_CLASSES)
    class_to_idx = {c: i for i, c in enumerate(all_classes)}
    valid_mask = np.zeros((H, W), dtype=np.float32)

    for item in signed_items:
        href = item.assets[_PC_ASSET].href
        with rasterio.open(href) as src:
            win = rio_window_from_bounds(*bbox, src.transform)
            win = win.intersection(
                rasterio.windows.Window(0, 0, src.width, src.height)
            )
            if win.width <= 0 or win.height <= 0:
                continue
            raw = src.read(1, window=win)
            if hasattr(raw, "filled"):
                raw = np.ma.filled(raw, 0)
            win_transform = src.window_transform(win)
            lc = np.asarray(raw, dtype=np.int32)

            # Valid pixels are those with a known class code.
            tile_valid = np.zeros((H, W), dtype=np.float32)
            reproject(
                source=np.ones((int(win.height), int(win.width)), dtype=np.float32),
                destination=tile_valid,
                src_transform=win_transform,
                src_crs=src.crs,
                dst_transform=ref_transform,
                dst_crs=aoi.crs_obj,
                resampling=Resampling.nearest,
            )

            # Reproject each class as a binary layer for the vote accumulator.
            for class_code in all_classes:
                class_layer = (lc == class_code).astype(np.float32)
                tile_votes = np.zeros((H, W), dtype=np.float32)
                reproject(
                    source=class_layer,
                    destination=tile_votes,
                    src_transform=win_transform,
                    src_crs=src.crs,
                    dst_transform=ref_transform,
                    dst_crs=aoi.crs_obj,
                    resampling=Resampling.nearest,
                )
                vote_count[:, :, class_to_idx[class_code]] += tile_votes

            valid_mask += tile_valid

    # Resolve votes: argmax across classes gives the dominant class.
    # Cells with no valid data get _NODATA_OUT_INT.
    has_data = valid_mask > 0
    result = np.full((H, W), _NODATA_OUT_INT, dtype=np.int32)
    if np.any(has_data):
        argmax = np.argmax(vote_count, axis=2)
        for i, class_code in enumerate(all_classes):
            mask = has_data & (argmax == i)
            result[mask] = class_code

    profile = {
        "crs": aoi.crs_obj,
        "transform": ref_transform,
        "height": H,
        "width": W,
    }
    if water_classes is not None:
        result = np.where(
            result == _NODATA_OUT_INT,
            _NODATA_OUT_SCALAR,
            np.isin(result, water_classes).astype(np.float32),
        ).astype(np.float32)
    return result, profile


# -- public API -------------------------------------------------------------


def load_worldcover_landcover(
    aoi: "AOI",
    *,
    year: int = 2021,
    cache_dir: pathlib.Path | None = None,
) -> xr.DataArray:
    """Load ESA WorldCover 2021 v200 land cover classification for the AOI.

    Downloads the 10 m resolution land cover raster from Planetary Computer
    and reprojects to the AOI grid using nearest-neighbour resampling
    (categorical data). Returns the full 11-class classification.

    Args:
        aoi: the AOI.
        year: WorldCover product year (2020 or 2021). Default 2021.
        cache_dir: optional local cache (currently unused).

    Returns:
        xr.DataArray with dims (y, x), dtype ``int32``, CRS = ``aoi.crs``.
        Values are ESA WorldCover class codes (10, 20, 30, 40, 50, 60,
        70, 80, 90, 95, 100). ``-9999`` for NoData.
    """
    if year not in (_MIN_YEAR, _MAX_YEAR):
        raise ValueError(
            f"WorldCover year must be in [{_MIN_YEAR}, {_MAX_YEAR}]; got {year}"
        )

    bbox = _aoi_bbox_wgs84(aoi)
    if not all(np.isfinite(b) for b in bbox):
        raise ValueError(f"AOI bbox has non-finite values: {bbox}")

    arr, profile = _load_worldcover_pc(aoi, int(year))

    da = xr.DataArray(
        arr,
        dims=("y", "x"),
        name="worldcover",
        attrs={
            "long_name": "ESA WorldCover 2021 v200 land cover classification",
            "source": f"ESA WorldCover {year} v200 (Planetary Computer STAC)",
            "resolution_m": 10,
            "classes": (
                "10=tree, 20=shrubland, 30=grassland, 40=cropland, "
                "50=built-up, 60=bare, 70=snow/ice, 80=water, "
                "90=wetland, 95=mangrove, 100=moss/lichen"
            ),
            "nodata": _NODATA_OUT_INT,
        },
    )
    da.rio.write_crs(profile["crs"], inplace=True)
    da.rio.write_transform(profile["transform"], inplace=True)
    da.rio.write_nodata(_NODATA_OUT_INT, inplace=True)
    return da


def load_worldcover_permanent_water(
    aoi: "AOI",
    *,
    year: int = 2021,
    cache_dir: pathlib.Path | None = None,
) -> xr.DataArray:
    """Load binary permanent water mask (WorldCover class 80) for the AOI.

    Args:
        aoi: the AOI.
        year: WorldCover product year. Default 2021.
        cache_dir: optional local cache.

    Returns:
        xr.DataArray with dims (y, x), dtype ``float32``, CRS = ``aoi.crs``.
        Values: 1.0 (permanent water), 0.0 (not water).
        ``-9999.0`` for NoData.
    """
    lc = load_worldcover_landcover(aoi, year=year, cache_dir=cache_dir)
    mask = np.where(
        lc.values == _NODATA_OUT_INT,
        _NODATA_OUT_SCALAR,
        np.where(lc.values == WC_WATER, 1.0, 0.0),
    ).astype(np.float32)

    da = xr.DataArray(
        mask,
        dims=("y", "x"),
        name="wc_permanent_water",
        attrs={
            "long_name": "ESA WorldCover permanent water bodies (class 80)",
            "source": f"ESA WorldCover {year} v200 (Planetary Computer STAC)",
            "class_code": WC_WATER,
            "nodata": _NODATA_OUT_SCALAR,
        },
    )
    da.rio.write_crs(lc.rio.crs, inplace=True)
    da.rio.write_transform(lc.rio.transform(), inplace=True)
    da.rio.write_nodata(_NODATA_OUT_SCALAR, inplace=True)
    return da


def load_worldcover_wetland(
    aoi: "AOI",
    *,
    year: int = 2021,
    cache_dir: pathlib.Path | None = None,
) -> xr.DataArray:
    """Load binary herbaceous wetland mask (WorldCover class 90) for the AOI.

    Args:
        aoi: the AOI.
        year: WorldCover product year. Default 2021.
        cache_dir: optional local cache.

    Returns:
        xr.DataArray with dims (y, x), dtype ``float32``, CRS = ``aoi.crs``.
        Values: 1.0 (wetland), 0.0 (not wetland).
        ``-9999.0`` for NoData.
    """
    lc = load_worldcover_landcover(aoi, year=year, cache_dir=cache_dir)
    mask = np.where(
        lc.values == _NODATA_OUT_INT,
        _NODATA_OUT_SCALAR,
        np.where(lc.values == WC_WETLAND, 1.0, 0.0),
    ).astype(np.float32)

    da = xr.DataArray(
        mask,
        dims=("y", "x"),
        name="wc_wetland",
        attrs={
            "long_name": "ESA WorldCover herbaceous wetland (class 90)",
            "source": f"ESA WorldCover {year} v200 (Planetary Computer STAC)",
            "class_code": WC_WETLAND,
            "nodata": _NODATA_OUT_SCALAR,
        },
    )
    da.rio.write_crs(lc.rio.crs, inplace=True)
    da.rio.write_transform(lc.rio.transform(), inplace=True)
    da.rio.write_nodata(_NODATA_OUT_SCALAR, inplace=True)
    return da


def load_worldcover_mangrove(
    aoi: "AOI",
    *,
    year: int = 2021,
    cache_dir: pathlib.Path | None = None,
) -> xr.DataArray:
    """Load binary mangrove mask (WorldCover class 95) for the AOI.

    Args:
        aoi: the AOI.
        year: WorldCover product year. Default 2021.
        cache_dir: optional local cache.

    Returns:
        xr.DataArray with dims (y, x), dtype ``float32``, CRS = ``aoi.crs``.
        Values: 1.0 (mangrove), 0.0 (not mangrove).
        ``-9999.0`` for NoData.
    """
    lc = load_worldcover_landcover(aoi, year=year, cache_dir=cache_dir)
    mask = np.where(
        lc.values == _NODATA_OUT_INT,
        _NODATA_OUT_SCALAR,
        np.where(lc.values == WC_MANGROVE, 1.0, 0.0),
    ).astype(np.float32)

    da = xr.DataArray(
        mask,
        dims=("y", "x"),
        name="wc_mangrove",
        attrs={
            "long_name": "ESA WorldCover mangrove (class 95)",
            "source": f"ESA WorldCover {year} v200 (Planetary Computer STAC)",
            "class_code": WC_MANGROVE,
            "nodata": _NODATA_OUT_SCALAR,
        },
    )
    da.rio.write_crs(lc.rio.crs, inplace=True)
    da.rio.write_transform(lc.rio.transform(), inplace=True)
    da.rio.write_nodata(_NODATA_OUT_SCALAR, inplace=True)
    return da


def load_worldcover_water_frac(
    aoi: "AOI",
    *,
    year: int = 2021,
    cache_dir: pathlib.Path | None = None,
    water_classes: tuple[int, ...] = DEFAULT_WATER_CLASSES,
) -> xr.DataArray:
    """Load binary water fraction using configurable WorldCover classes."""
    if year not in (_MIN_YEAR, _MAX_YEAR):
        raise ValueError(
            f"WorldCover year must be in [{_MIN_YEAR}, {_MAX_YEAR}]; got {year}"
        )
    arr, profile = _load_worldcover_pc(aoi, int(year), tuple(water_classes))
    da = xr.DataArray(
        arr.astype(np.float32), dims=("y", "x"), name="water_frac",
        attrs={
            "long_name": "ESA WorldCover water fraction",
            "source": f"ESA WorldCover {year} v200 (Planetary Computer STAC)",
            "water_classes": list(water_classes),
            "nodata": _NODATA_OUT_SCALAR,
        },
    )
    da.rio.write_crs(profile["crs"], inplace=True)
    da.rio.write_transform(profile["transform"], inplace=True)
    da.rio.write_nodata(_NODATA_OUT_SCALAR, inplace=True)
    return da


DOWNLOADER = {
    "name": "worldcover",
    "description": "ESA WorldCover 2021 v200 land cover classification (10 m)",
    "requires_auth": ["none"],
    "is_time_series": False,
    "outputs": {
        "landcover": load_worldcover_landcover,
        "wc_permanent_water": load_worldcover_permanent_water,
        "wc_wetland": load_worldcover_wetland,
        "wc_mangrove": load_worldcover_mangrove,
    },
    "manifest_keys": {
        "landcover": "worldcover_lc",
        "wc_permanent_water": "worldcover_water",
        "wc_wetland": "worldcover_wetland",
        "wc_mangrove": "worldcover_mangrove",
    },
}


__all__ = [
    "load_worldcover_landcover",
    "load_worldcover_permanent_water",
    "load_worldcover_wetland",
    "load_worldcover_mangrove",
    "WC_TREE",
    "WC_SHRUBLAND",
    "WC_GRASSLAND",
    "WC_CROPLAND",
    "WC_BUILTUP",
    "WC_BARE",
    "WC_SNOW_ICE",
    "WC_WATER",
    "WC_WETLAND",
    "WC_MANGROVE",
    "WC_MOSS_LICHEN",
    "WC_CLASSES",
    "WC_WATER_CLASSES",
    "DEFAULT_WATER_CLASSES",
    "NODATA_OUT",
    "load_worldcover_water_frac",
    "DOWNLOADER",
]

NODATA_OUT = _NODATA_OUT_SCALAR
