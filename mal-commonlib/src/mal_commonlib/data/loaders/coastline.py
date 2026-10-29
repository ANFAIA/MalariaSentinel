"""GSHHG coastline loader — per-cell land fraction + open-sea mask.

Public surface
--------------
``load_coastline_land_mask(aoi, *, resolution=None, coast_band_m=None, cache_dir=None)``
    -> xr.DataArray in [0, 1] (fraction of each AOI cell that is land).

``sea_mask(land_frac, distance_to_land_m, coast_band_m, water_floor=0.05)``
    -> boolean "open sea" mask.

``distance_to_land_m(land_frac, resolution_m, water_floor=0.05)``
    -> distance from every cell to the nearest land cell, in metres.

Why this loader exists
----------------------
The engine must distinguish permanent water on land (lakes, rivers, wetlands,
mangroves) from open-ocean water (JRC GSW sees surf, ports and estuaries as
"permanent water" because the 30 m pixel is genuinely wet year-round).

The first implementation rasterised GSHHG **crude** (`c`) polygons to a binary
mask and then dilated it by 5 km. Measured on ``accra-coastal-test`` (45x61
cells, 1 km): 542 cells flagged as land (19.7 %) where a per-cell land fraction
from GSHHG **full** gives 78 cells >50 % land (2.8 %, 88 >5 %, verified against
Dynamic World: 63 built/crop/wetland cells, r = 0.90, zero DW-land below 5 %
land fraction). The 5 km dilation moved the coast several km inland and put
463 open-ocean cells inside the "land" mask — those cells kept rainfall and JRC
water and produced a large fake habitat block over the sea in the GIF.

Strategy
--------
1. Download / cache the GSHHG shapefile archive (see ``_ensure_gshhg_shapefile``).
2. Open with geopandas, clip polygons to the AOI bbox.
3. Rasterise the clipped polygons at **sub-cell** resolution (~30 m, i.e.
   ``ceil(resolution_m / sub_pixel_m)`` sub-pixels per axis, bounded so the
   temporary array stays sane for any AOI/resolution) and average the
   sub-pixels of each AOI cell -> land fraction in [0, 1].
4. No dilation. The coastal band is a *query* (``sea_mask``), not a mutation:
   ``sea  <=>  land_frac < water_floor  and  distance_to_land > coast_band_m``.

References
----------
Wessel, P., & Smith, W. H. F. (1996). A global, self-consistent, hierarchical,
high-resolution shoreline database. Journal of Geophysical Research, 101(B4),
8741-8743. https://www.soest.hawaii.edu/pwessel/gshhg/
"""
from __future__ import annotations

import math
import pathlib
import shutil
import urllib.request
import zipfile
from typing import TYPE_CHECKING

import geopandas as gpd
import numpy as np
import rasterio
import xarray as xr
from rasterio.features import rasterize
from rasterio.transform import from_bounds
from scipy import ndimage
from shapely.geometry import box

from mal_commonlib.model_constants import model_constant

if TYPE_CHECKING:
    from mal_commonlib.aoi import AOI


_GSHHG_VERSION = "2.3.7"
_GSHHG_SHP_ZIP_URL = (
    f"https://www.soest.hawaii.edu/pwessel/gshhg/gshhg-shp-{_GSHHG_VERSION}.zip"
)
_GSHHG_SHP_ZIP_NAME = f"gshhg-shp-{_GSHHG_VERSION}.zip"
_GSHHG_SUBDIR = "GSHHS_shp"

_DEFAULT_CACHE_DIR = pathlib.Path("~/.cache/malaria_sentinel/gshhg").expanduser()
# GSHHG full ("f") is the default: at a 1 km AOI grid the crude ("c") polygons
# are off by several km. Override with ingest.coastline_resolution.
_DEFAULT_RESOLUTION_FALLBACK = "f"
_LEVEL_LAND = 1

# Sub-cell rasterisation step used to build the land fraction.
_SUB_PIXEL_M = 30.0
# Hard bound on the temporary raster (h*sub * w*sub samples). The 30 m step is
# reduced for very large AOIs/grids so memory stays bounded.
_MAX_SUB_SAMPLES = 40_000_000

# Defaults are read from the single source of truth (model_constants.yaml).
_WATER_FLOOR_FALLBACK = 0.05
_COAST_BAND_M_FALLBACK = 2_000.0

_NODATA_OUT_SCALAR = float(model_constant("ingest", "nodata_sentinel"))


def _config_float(key: str, fallback: float) -> float:
    try:
        return float(model_constant("ingest", key))
    except Exception:  # pragma: no cover - config always ships these keys
        return float(fallback)


def _config_str(key: str, fallback: str) -> str:
    try:
        return str(model_constant("ingest", key))
    except Exception:  # pragma: no cover
        return fallback


def default_coast_band_m() -> float:
    """Coastal band width (m) from ``ingest.coastline_buffer_m``.

    The key name is historical: it no longer dilates anything, it is the width
    of the shallow coastal band that keeps JRC water inside the saltwater
    filter (``sea_mask``). Keeping the key means old manifests still load.
    """
    return _config_float("coastline_buffer_m", _COAST_BAND_M_FALLBACK)


def default_sea_water_floor() -> float:
    """Land-fraction threshold below which a cell is water (``ingest.sea_water_floor``)."""
    return _config_float("sea_water_floor", _WATER_FLOOR_FALLBACK)


def default_resolution() -> str:
    """GSHHG resolution code from ``ingest.coastline_resolution`` (default ``f``)."""
    return _config_str("coastline_resolution", _DEFAULT_RESOLUTION_FALLBACK)


def _ensure_cache_dir(cache_dir: pathlib.Path | None) -> pathlib.Path:
    if cache_dir is None:
        cache_dir = _DEFAULT_CACHE_DIR
    cache_dir = pathlib.Path(cache_dir).expanduser()
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def _ensure_gshhg_shapefile(
    cache_dir: pathlib.Path, resolution: str = "f"
) -> pathlib.Path:
    """Download and unpack the level-1 GSHHG shapefile if not already cached.

    Returns the path to the per-resolution ``.shp`` file (e.g.
    ``GSHHS_shp/f/GSHHS_f_L1.shp``). The first call downloads the full
    archive (~149 MB); subsequent calls reuse the cached zip and only extract
    the requested resolution's level-1 files (level 1 = land polygons).

    Network note: SOEST does NOT publish per-resolution single-file
    downloads. The single archive ``gshhg-shp-<version>.zip`` contains all 5
    resolutions x 6 levels (~400 MB uncompressed). We accept the one-time
    ~149 MB cost; it is cached permanently under ``cache_dir``.
    """
    cache_dir = pathlib.Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    shp_name = f"GSHHS_{resolution}_L{_LEVEL_LAND}.shp"
    shp_path = cache_dir / _GSHHG_SUBDIR / resolution / shp_name
    if shp_path.exists():
        return shp_path

    zip_path = cache_dir / _GSHHG_SHP_ZIP_NAME
    if not zip_path.exists():
        print(
            f"Downloading GSHHG shapefile archive "
            f"(~149 MB, all 5 resolutions x 6 levels): {_GSHHG_SHP_ZIP_URL}"
        )
        with urllib.request.urlopen(_GSHHG_SHP_ZIP_URL, timeout=600) as response, \
                open(zip_path, "wb") as out:
            shutil.copyfileobj(response, out)

    extract_dir = cache_dir / _GSHHG_SUBDIR / resolution
    if not (extract_dir / shp_name).exists():
        with zipfile.ZipFile(zip_path, "r") as zf:
            # Level 1 only: land polygons are all this loader needs. Levels
            # 2-6 (lakes, islands-in-lakes, ...) would add ~1 GB of
            # extraction for full resolution and are not used.
            members = [
                n for n in zf.namelist()
                if n.startswith(f"{_GSHHG_SUBDIR}/{resolution}/")
                and n.split("/")[-1].startswith(
                    f"GSHHS_{resolution}_L{_LEVEL_LAND}.")
            ]
            if not members:
                raise FileNotFoundError(
                    f"GSHHG archive has no files matching "
                    f"{_GSHHG_SUBDIR}/{resolution}/GSHHS_{resolution}_L"
                    f"{_LEVEL_LAND}.* (resolution={resolution!r})"
                )
            zf.extractall(cache_dir, members=members)

    if not shp_path.exists():
        raise FileNotFoundError(
            f"GSHHG archive extracted but {shp_path} not found"
        )
    return shp_path


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


def _sub_factor(h: int, w: int, resolution_m: float,
                sub_pixel_m: float = _SUB_PIXEL_M) -> int:
    """Sub-pixels per AOI cell axis, bounded by ``_MAX_SUB_SAMPLES``."""
    if sub_pixel_m <= 0:
        return 1
    sub = max(1, int(math.ceil(float(resolution_m) / float(sub_pixel_m))))
    while sub > 1 and (h * sub) * (w * sub) > _MAX_SUB_SAMPLES:
        sub -= 1
    return sub


def _land_fraction(
    clipped: gpd.GeoDataFrame, aoi, h: int, w: int,
    sub_pixel_m: float = _SUB_PIXEL_M,
) -> np.ndarray:
    """Average sub-cell rasterisation of ``clipped`` polygons into [0, 1]."""
    if clipped.empty:
        return np.zeros((h, w), dtype=np.float32)
    sub = _sub_factor(h, w, float(aoi.resolution_m), sub_pixel_m)
    shapes = ((geom, _LEVEL_LAND) for geom in clipped.geometry
              if geom is not None and not geom.is_empty)
    if sub <= 1:
        return rasterize(
            shapes, out_shape=(h, w),
            transform=from_bounds(*aoi.bbox, w, h),
            fill=0, dtype=np.float32,
        ).astype(np.float32)
    big = rasterize(
        shapes, out_shape=(h * sub, w * sub),
        transform=from_bounds(*aoi.bbox, w * sub, h * sub),
        fill=0, dtype=np.uint8,
    )
    frac = big.reshape(h, sub, w, sub).mean(axis=(1, 3), dtype=np.float32)
    return frac.astype(np.float32)


def distance_to_land_m(
    land_frac: np.ndarray, resolution_m: float,
    water_floor: float | None = None,
) -> np.ndarray:
    """Euclidean distance (m) from each cell to the nearest land cell.

    Land = ``land_frac >= water_floor`` (default ``ingest.sea_water_floor``).
    Computed on the AOI grid with ``scipy.ndimage.distance_transform_edt``;
    one cell unit equals ``resolution_m``.
    """
    lf = np.asarray(land_frac, dtype=np.float64)
    floor = default_sea_water_floor() if water_floor is None else float(water_floor)
    land = lf >= floor
    if not land.any():
        return np.full(lf.shape, np.inf, dtype=np.float64)
    return ndimage.distance_transform_edt(~land) * float(resolution_m)


def sea_mask(
    land_frac: np.ndarray, distance_to_land_m: np.ndarray,
    coast_band_m: float, water_floor: float | None = None,
) -> np.ndarray:
    """Boolean "open sea" mask.

    Rule (documented contract): a cell is open sea when

        ``land_frac < water_floor``  AND  ``distance_to_land > coast_band_m``

    i.e. it is water rather than land, and it is farther than the coastal band
    from the nearest land. Inside the band (lagoons, estuaries, the surf zone,
    the shallow plume visible in satellite imagery) the cell is *coastal
    water*: it keeps its JRC permanent-water signal and its rainfall.

    Args:
        land_frac: per-cell land fraction in [0, 1].
        distance_to_land_m: per-cell distance to nearest land, metres
            (``distance_to_land_m``).
        coast_band_m: width of the coastal band in metres. ``<= 0`` disables
            the band (only land-fraction decides).
        water_floor: land-fraction threshold below which a cell is water.
            Defaults to ``ingest.sea_water_floor``.
    """
    lf = np.asarray(land_frac, dtype=np.float64)
    dist = np.asarray(distance_to_land_m, dtype=np.float64)
    floor = default_sea_water_floor() if water_floor is None else float(water_floor)
    water = lf < floor
    if coast_band_m is None or float(coast_band_m) <= 0:
        return water
    return water & (dist > float(coast_band_m))


def load_coastline_land_mask(
    aoi: "AOI",
    *,
    resolution: str | None = None,
    coast_band_m: float | None = None,
    buffer_m: float | None = None,
    cache_dir: pathlib.Path | None = None,
    sub_pixel_m: float = _SUB_PIXEL_M,
) -> xr.DataArray:
    """Load a per-cell land *fraction* for the AOI using GSHHG.

    Args:
        aoi: the AOI.
        resolution: GSHHG resolution code (``"c"`` crude, ``"l"`` low,
            ``"i"`` intermediate, ``"h"`` high, ``"f"`` full). Defaults to
            ``ingest.coastline_resolution`` (``"f"``): at a 1 km grid the
            crude polygons are off by several km.
        coast_band_m: width of the coastal band in metres, used by
            ``sea_mask`` downstream (daily_nc.py). Recorded in the attrs;
            the loader itself no longer dilates anything. Defaults to
            ``ingest.coastline_buffer_m``.
        buffer_m: DEPRECATED alias for ``coast_band_m`` (old manifests and
            call sites). Passing it raises no error, it just forwards.
        cache_dir: local cache for the GSHHG archive. Defaults to
            ``~/.cache/malaria_sentinel/gshhg/``.
        sub_pixel_m: sub-cell rasterisation step (metres) used to build the
            fraction. Default 30 m (the native GSHHG full scale).

    Returns:
        xr.DataArray with dims (y, x), dtype ``float32``, CRS = ``aoi.crs``,
        values in [0, 1]: the fraction of each AOI cell covered by land
        (1.0 = fully land, 0.0 = fully water). The variable name stays
        ``land_mask`` so the manifest/registry contract is unchanged; the
        values and attrs are no longer binary.
    """
    if resolution is None:
        resolution = default_resolution()
    if resolution not in {"c", "l", "i", "h", "f"}:
        raise ValueError(
            f"GSHHG resolution must be one of c/l/i/h/f; got {resolution!r}"
        )
    if buffer_m is not None and coast_band_m is None:
        coast_band_m = float(buffer_m)
    if coast_band_m is None:
        coast_band_m = default_coast_band_m()
    coast_band_m = float(coast_band_m)

    cache_dir = _ensure_cache_dir(cache_dir)
    shp_path = _ensure_gshhg_shapefile(cache_dir, resolution)

    H, W = aoi.cells_per_side()
    H = int(H)
    W = int(W)
    ref_transform = from_bounds(*aoi.bbox, W, H)

    bbox = _aoi_bbox_wgs84(aoi)
    bbox_gdf = gpd.GeoDataFrame(geometry=[box(*bbox)], crs="EPSG:4326")
    coast = gpd.read_file(shp_path)
    if coast.crs is None:
        coast = coast.set_crs("EPSG:4326")
    elif str(coast.crs).upper() not in {"EPSG:4326", "WGS84", "4326"}:
        coast = coast.to_crs("EPSG:4326")

    clipped = gpd.clip(coast, bbox_gdf)
    land_frac = _land_fraction(clipped, aoi, H, W, sub_pixel_m)

    floor = default_sea_water_floor()
    da = xr.DataArray(
        land_frac.astype(np.float32),
        dims=("y", "x"),
        name="land_mask",
        attrs={
            "long_name": (
                "GSHHG land fraction per AOI cell (0 = open water, "
                "1 = fully land)"
            ),
            "units": "1",
            "source": (
                f"GSHHG {_GSHHG_VERSION} resolution={resolution} "
                f"L{_LEVEL_LAND}"
            ),
            "variable": "land_frac",
            "sub_pixel_m": float(sub_pixel_m),
            "coast_band_m": float(coast_band_m),
            "sea_water_floor": float(floor),
            "sea_rule": (
                "sea <=> land_frac < sea_water_floor and "
                "distance_to_land > coast_band_m"
            ),
            "resolution_m": float(aoi.resolution_m),
            "nodata": _NODATA_OUT_SCALAR,
        },
    )
    da.rio.write_crs(aoi.crs, inplace=True)
    da.rio.write_transform(ref_transform, inplace=True)
    return da


DOWNLOADER = {
    "name": "coastline",
    "description": (
        "GSHHG coastline rasterised to a per-cell land fraction on the AOI "
        "grid, plus the open-sea rule (land fraction + coastal band) used by "
        "daily_nc.py to exclude open-ocean cells from JRC GSW permanent water."
    ),
    "requires_auth": ["none"],
    "license": "LicenseRef-GSHHG-LGPL-3.0",
    "attribution": (
        "Wessel, P., & Smith, W. H. F. (1996), A global, self-consistent, "
        "hierarchical, high-resolution shoreline database, JGR 101, "
        "8741-8743. GSHHG distributed under LGPL v3+."),
    "is_time_series": False,
    "outputs": {
        "land_mask": load_coastline_land_mask,
    },
    "manifest_keys": {
        "land_mask": "coastline_land_mask",
    },
}


__all__ = [
    "load_coastline_land_mask",
    "sea_mask",
    "distance_to_land_m",
    "default_coast_band_m",
    "default_sea_water_floor",
    "default_resolution",
    "DOWNLOADER",
]
