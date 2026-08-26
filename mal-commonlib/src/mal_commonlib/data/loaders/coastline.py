"""GSHHG coastline loader (M12-fix) — produces a binary land/ocean mask.

Public surface
--------------
``load_coastline_land_mask(aoi, *, resolution="c", cache_dir=None) -> xr.DataArray``

Why this loader exists
----------------------
M12-fix needs to distinguish permanent water on land (lakes, rivers, wetlands,
mangroves) from open-ocean permanent water (JRC GSW sees surf, ports, and
estuaries as "permanent water" because the 30 m pixel is genuinely wet year-round).

The earlier M12 proposal used a 10 km buffer around a synthetic coastline, but
no coastline loader existed; the rule was unimplemented. This loader implements
the rule with a real coastline (GSHHG = Global Self-consistent Hierarchical
High-resolution Geography, Wessel & Smith 1996) rasterised onto the AOI grid.

Strategy
--------
1. Download a single GSHHG shapefile archive (~149 MB) to ``cache_dir`` if
   not already present. SOEST does NOT publish per-resolution single-file
   downloads — only the multi-resolution archive is. The zip is cached
   permanently and re-used across AOIs and resolutions.

   DO NOT confuse this with the GMT netCDF-4 distribution
   (``gshhg-gmt-...tar.gz``) which is ~25 GB; that one is for GMT's tiled
   grid and is **not** what this loader downloads.
2. Extract only the requested ``resolution/c/GSHHS_<res>_L1.*`` subdirectory
   on demand (~160 KB). Full extraction would write ~400 MB across the
   whole archive.
3. Open with geopandas; clip polygons to the AOI bbox.
4. ``rasterio.features.rasterize`` the result onto the AOI grid as
   fill=1 (land), background=0 (ocean).
5. Apply the 5 km coastline buffer by dilating the land mask outward
   (so cells within 5 km of the coast are treated as "coastal water" and
   kept by the saltwater filter — see daily_nc.py && env.py for consumer).

The output is a binary raster aligned to the AOI grid:
    * dims (y, x), dtype ``float32``
    * CRS = ``aoi.crs``
    * values in {0.0, 1.0} (1 = land, 0 = ocean)
    * NoData: ``-9999.0``

Notes
-----
* GSHHG ``c`` (crude) resolution is sufficient for a 1 km AOI grid.
  The smoother ``l`` or ``i`` resolutions may improve the coastline shape
  in irregular regions but are an order of magnitude larger; not justified
  at the current AOI scale.
* The default 5 km buffer is applied via morphological dilation in cells
  (5 km / cell_size_m rounded up). Set ``buffer_m=0`` to disable.
* The loader's archive download is one-time and cached; subsequent calls
  with the same ``cache_dir`` only extract the per-resolution files.

References
----------
Wessel, P., & Smith, W. H. F. (1996). A global, self-consistent, hierarchical,
high-resolution shoreline database. Journal of Geophysical Research, 101(B4),
8741-8743. https://www.soest.hawaii.edu/pwessel/gshhg/
"""
from __future__ import annotations

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

if TYPE_CHECKING:
    from mal_commonlib.aoi import AOI


_GSHHG_VERSION = "2.3.7"
_GSHHG_SHP_ZIP_URL = (
    f"https://www.soest.hawaii.edu/pwessel/gshhg/gshhg-shp-{_GSHHG_VERSION}.zip"
)
_GSHHG_SHP_ZIP_NAME = f"gshhg-shp-{_GSHHG_VERSION}.zip"
_GSHHG_SUBDIR = "GSHHS_shp"

_DEFAULT_CACHE_DIR = pathlib.Path("~/.cache/malaria_sentinel/gshhg").expanduser()
_DEFAULT_RESOLUTION = "c"
_DEFAULT_BUFFER_M = 5_000.0
_LEVEL_LAND = 1

_NODATA_OUT_SCALAR = -9999.0


def _ensure_cache_dir(cache_dir: pathlib.Path | None) -> pathlib.Path:
    if cache_dir is None:
        cache_dir = _DEFAULT_CACHE_DIR
    cache_dir = pathlib.Path(cache_dir).expanduser()
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def _ensure_gshhg_shapefile(
    cache_dir: pathlib.Path, resolution: str = _DEFAULT_RESOLUTION
) -> pathlib.Path:
    """Download and unpack the GSHHG shapefile archive if not already cached.

    Returns the path to the per-resolution ``.shp`` file (e.g.
    ``GSHHS_shp/c/GSHHS_c_L1.shp``). The first call downloads the full
    archive (~149 MB); subsequent calls reuse the cached zip and only
    extract the requested resolution subdirectory on demand.

    Network note: SOEST does NOT publish per-resolution single-file
    downloads. The single archive ``gshhg-shp-<version>.zip`` contains
    all 5 resolutions × 6 levels (~400 MB uncompressed). We accept the
    one-time ~149 MB cost; it is cached permanently under ``cache_dir``
    and re-used across AOIs and resolutions.
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
            members = [
                n for n in zf.namelist()
                if n.startswith(f"{_GSHHG_SUBDIR}/{resolution}/")
                and n.split("/")[-1].startswith(f"GSHHS_{resolution}_L")
            ]
            if not members:
                raise FileNotFoundError(
                    f"GSHHG archive has no files matching "
                    f"{_GSHHG_SUBDIR}/{resolution}/GSHHS_{resolution}_L* "
                    f"(resolution={resolution!r}, level={_LEVEL_LAND})"
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


def load_coastline_land_mask(
    aoi: "AOI",
    *,
    resolution: str = _DEFAULT_RESOLUTION,
    buffer_m: float = _DEFAULT_BUFFER_M,
    cache_dir: pathlib.Path | None = None,
) -> xr.DataArray:
    """Load a binary land-vs-ocean mask for the AOI using GSHHG.

    Args:
        aoi: the AOI.
        resolution: GSHHG resolution code (``"c"`` crude, ``"l"`` low,
            ``"i"`` intermediate, ``"h"`` high, ``"f"`` full). Default ``"c"``,
            which is sufficient at the 1 km AOI grid.
        buffer_m: distance (in metres) to dilate the land mask outward. Cells
            within this distance of the coastline are treated as "coastal water"
            and kept by the saltwater filter (i.e. land-side buffer, allowing
            lagoons and estuaries but excluding open ocean). Default 5_000 m.
            Set to 0 to disable buffering.
        cache_dir: local cache for the GSHHG archive. Defaults to
            ``~/.cache/malaria_sentinel/gshhg/``.

    Returns:
        xr.DataArray with dims (y, x), dtype ``float32``, CRS = ``aoi.crs``.
        Values in {0.0, 1.0}: 1.0 = land (or coastal water), 0.0 = open ocean.
        ``-9999.0`` for NoData (only when the AOI bbox falls entirely outside
        the GSHHG coverage; not expected for Ghana).
    """
    if resolution not in {"c", "l", "i", "h", "f"}:
        raise ValueError(
            f"GSHHG resolution must be one of c/l/i/h/f; got {resolution!r}"
        )

    cache_dir = _ensure_cache_dir(cache_dir)
    shp_path = _ensure_gshhg_shapefile(cache_dir, resolution)

    H, W = aoi.cells_per_side()
    H = int(H)
    W = int(W)
    ref_transform = from_bounds(*aoi.bbox, W, H)

    bbox = _aoi_bbox_wgs84(aoi)
    bbox_gdf = gpd.GeoDataFrame(
        geometry=[box(*bbox)], crs="EPSG:4326"
    )
    coast = gpd.read_file(shp_path)
    if coast.crs is None:
        coast = coast.set_crs("EPSG:4326")
    elif str(coast.crs).upper() not in {"EPSG:4326", "WGS84", "4326"}:
        coast = coast.to_crs("EPSG:4326")

    clipped = gpd.clip(coast, bbox_gdf)
    if clipped.empty:
        land_mask = np.zeros((H, W), dtype=np.float32)
    else:
        shapes = ((geom, _LEVEL_LAND) for geom in clipped.geometry)
        land_mask = rasterize(
            shapes,
            out_shape=(H, W),
            transform=ref_transform,
            fill=0,
            dtype=np.float32,
        )

    if buffer_m > 0 and land_mask.any():
        cell_size_m = float(aoi.resolution_m)
        radius_cells = max(1, int(np.ceil(buffer_m / cell_size_m)))
        structure = np.ones((2 * radius_cells + 1, 2 * radius_cells + 1), dtype=bool)
        land_mask = ndimage.binary_dilation(
            land_mask > 0.5, structure=structure
        ).astype(np.float32)

    da = xr.DataArray(
        land_mask.astype(np.float32),
        dims=("y", "x"),
        name="land_mask",
        attrs={
            "long_name": "GSHHG land mask (1=land or coastal water, 0=open ocean)",
            "source": f"GSHHG {_GSHHG_VERSION} resolution={resolution} L{_LEVEL_LAND}",
            "buffer_m": float(buffer_m),
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
        "GSHHG coastline rasterised to a binary land/coastal-water mask on the AOI grid. "
        "Used by daily_nc.py to exclude open-ocean cells from JRC GSW permanent water."
    ),
    "requires_auth": ["none"],
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
    "DEFAULT_BUFFER_M",
    "DOWNLOADER",
]
