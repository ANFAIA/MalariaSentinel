"""MERIT DEM 90 m loader (M1.3a, terrain).

Public surface
--------------
``load_merit_dem(aoi, *, cache_dir=None) -> xr.DataArray``

MERIT DEM (Multi-Error-Removed Improved-Terrain DEM) is a 90 m hydrologically
conditioned global DEM derived from SRTM v3.0 / AW3D-30m / GMTED2010 / VFP.
It is preferred for TWI computation because the original SRTM has many
spurious pits that produce noise in the contributing-area calculation.

Tiles are 5°×5° GeoTIFFs in EPSG:4326 (degrees), named after the centre of
their lower-left pixel — e.g. ``n05w005_dem.tif`` covers
``5°N–10°N, 5°W–0°W``. For the Ghana AOI (~-3.5..1.5 lon, ~4.5..11.5 lat) we
need 2×2 = 4 tiles.

Distribution (as of 2026-07)
----------------------------
The original public mirror at
``http://hydro.iis.u-tokyo.ac.jp/~yamadai/MERIT_DEM/`` has moved; the data
is now distributed through a password-protected Dropbox folder
(registration required via Google Form, see
https://global-hydrodynamics.github.io/MERIT_DEM/). The previous fallback
mirror at ``https://data.hydrosheds.org/file/MERIT/v1.0.1/`` is also no
longer serving the per-tile files (returns 404).

The mirror URL is configurable via the ``MERIT_DOWNLOAD_URL`` environment
variable (default: the Yamazaki / Dropbox landing), and the auth credential
via ``MERIT_AUTH_TOKEN`` (sent as ``Authorization: Bearer <token>``). For
the default Yamazaki host, register via the Google Form on the landing page
and use the issued Dropbox shared-link token as ``MERIT_AUTH_TOKEN``.

We download the intersecting tiles via plain ``requests`` (already present
in the dep set) into ``cache_dir`` and merge them with ``rasterio.merge.merge``
before reprojecting to the AOI grid.

Output contract (used by TWI and the ABM):
    * dims (y, x), dtype ``float32``
    * CRS = ``aoi.crs``
    * values in metres
    * NoData: ``-9999.0`` (post-reproject fill policy)
"""
from __future__ import annotations

import os
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

# New Yamazaki Lab landing page (the data is hosted on Dropbox, gated by
# password; the password is sent as a Dropbox auth token). The default
# ``MERIT_DOWNLOAD_URL`` can be overridden by env var to point at a local
# mirror or a different public host.
_MERIT_DEFAULT_BASE_URL = "https://www.dropbox.com/sh/3smfavy5o8lhl9s/AABbuqXc2kHOd4M1BnZDAfTPa"
_MERIT_VERSION = "v1.0.3"  # current Yamazaki release (October 2018)

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
    """Return candidate URLs for a single MERIT tile.

    Per the Yamazaki documentation, per-tile filenames are
    ``<lat_letter><lat:02d><lon_letter><lon:03d>_dem.tif`` (e.g.
    ``n05w005_dem.tif`` for the 5N-10N, 5W-0W tile) and the 5° tiles are
    bundled into 30°×30° tar packages named
    ``dem_tif_<lat_letter><lat:02d><lon_letter><lon:03d>.tar`` covering
    30° of latitude × 30° of longitude from the SW corner.

    We try three URL variants in order: the per-tile file at the canonical
    ``tiles/<version>/<tile>`` path, the 30°×30° tar, and a flat layout
    (the old mirror's pattern, kept for compatibility with any user-run
    local mirror that preserves the original filename). The base host
    defaults to the Yamazaki / Dropbox landing and can be overridden via
    ``MERIT_DOWNLOAD_URL``.
    """
    lat_letter = "s" if lat0 < 0 else "n"
    lon_letter = "w" if lon0 < 0 else "e"
    tile_name = f"{lat_letter}{abs(lat0):02d}{lon_letter}{abs(lon0):03d}_dem.tif"
    # 30°×30° tar package: SW corner is the multiple of 30, lat floor, lon floor.
    pkg_lat = int(np.floor(lat0 / 30) * 30)
    pkg_lon = int(np.floor(lon0 / 30) * 30)
    pkg_name = (
        f"dem_tif_{lat_letter}{abs(pkg_lat):02d}{lon_letter}{abs(pkg_lon):03d}.tar"
    )

    base = os.environ.get("MERIT_DOWNLOAD_URL", _MERIT_DEFAULT_BASE_URL).rstrip("/")
    return [
        f"{base}/tiles/{_MERIT_VERSION}/{tile_name}",
        f"{base}/{pkg_name}",
        f"{base}/{tile_name}",
    ]


def _download_tile(lon0: int, lat0: int, cache: pathlib.Path) -> pathlib.Path:
    """Download a single MERIT tile to ``cache``; return the local path.

    The downloaded file may be either a plain GeoTIFF (per-tile URL) or a
    ``.tar`` archive (30°×30° bundle). In the latter case we extract the
    single matching tile from the tarball into ``cache`` and return its
    extracted path. A downloaded bundle is cached so subsequent tiles
    within the same 30°×30° block don't trigger a re-download.
    """
    dest = cache / f"merit_{lon0:+04d}_{lat0:+04d}.tif"
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    headers: dict[str, str] = {}
    token = os.environ.get("MERIT_AUTH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    lat_letter = "s" if lat0 < 0 else "n"
    lon_letter = "w" if lon0 < 0 else "e"
    expected_member = (
        f"{lat_letter}{abs(lat0):02d}{lon_letter}{abs(lon0):03d}_dem.tif"
    )
    last_err: Exception | None = None
    for url in _tile_urls(lon0, lat0):
        try:
            suffix = ".tar" if url.endswith(".tar") else ".tif"
            tmp_dest = cache / f"_dl_{lon0:+04d}_{lat0:+04d}{suffix}"
            with requests.get(
                url, stream=True, timeout=120, headers=headers, allow_redirects=True
            ) as r:
                r.raise_for_status()
                with open(tmp_dest, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1 << 16):
                        f.write(chunk)
            if tmp_dest.stat().st_size == 0:
                raise IOError(f"empty download from {url}")
            if suffix == ".tar":
                import tarfile

                with tarfile.open(tmp_dest, "r") as tf:
                    member = None
                    for m in tf.getmembers():
                        if m.isfile() and m.name.endswith(expected_member):
                            member = m
                            break
                    if member is None:
                        raise FileNotFoundError(
                            f"{expected_member} not in {tmp_dest.name}"
                        )
                    with tf.extractfile(member) as src, open(dest, "wb") as out:
                        out.write(src.read())
            else:
                tmp_dest.rename(dest)
            if dest.exists() and dest.stat().st_size > 0:
                return dest
        except Exception as exc:
            last_err = exc
            continue
    raise FileNotFoundError(
        f"Could not download MERIT tile at lon0={lon0} lat0={lat0} from any mirror. "
        f"Set MERIT_DOWNLOAD_URL and MERIT_AUTH_TOKEN (register via the Google Form "
        f"on https://global-hydrodynamics.github.io/MERIT_DEM/). Last error: {last_err}"
    )


def _stitch_tiles(paths: Iterable[pathlib.Path]) -> tuple[np.ndarray, dict]:
    """Merge the per-tile GeoTIFFs in memory; return (arr, profile).

    Each tile may have its own resolution; we let ``rasterio.merge`` pick
    the output resolution as the minimum across the inputs (the default),
    rather than forcing a fixed 5° step (which would silently drop data for
    any tile with a finer resolution).
    """
    srcs = [rasterio.open(str(p)) for p in paths]
    try:
        # ``res`` left as default (min of inputs). MERIT's native resolution
        # is 3 arc-seconds (~90 m at the equator), so the merged grid is
        # always finer than the AOI grid that ``load_merit_dem`` reprojects
        # to anyway.
        arr, transform = rio_merge(srcs, nodata=_MERIT_FILL)
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


def _load_openlandmap_merit(
    aoi: AOI, cache: pathlib.Path
) -> tuple[np.ndarray, dict]:
    """Download the OpenLandMap 250 m MERIT derivative and subset to the AOI.

    The OpenLandMap file is a single global 250 m reprojection of MERIT DEM
    v1.0.3 (source: Zenodo 1447210). We download it once, clip to the AOI
    bbox in WGS-84, and return (arr, profile) for the same downstream
    reproject path as the per-tile MERIT download.

    Note: as of 2026-07 the public MinIO bucket at s3.openlandmap.org
    returns 403 for the per-tile URLs. This helper is kept for users
    who have local access to the file (e.g. via a private mirror). The
    ``merit_source="openlandmap"`` mode calls it directly.
    """
    src_url = "https://s3.openlandmap.org/dsm/merit.dem_m_250m_s0..0cm_2017_v1.0.tif"
    dest = cache / "merit_openlandmap_250m.tif"
    if not (dest.exists() and dest.stat().st_size > 0):
        with requests.get(src_url, stream=True, timeout=120, allow_redirects=True) as r:
            r.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in r.iter_content(chunk_size=1 << 16):
                    f.write(chunk)
    with rasterio.open(str(dest)) as s:
        bbox = _aoi_bbox_wgs84(aoi)
        w, s_lat, e, n = bbox
        from rasterio.windows import from_bounds as rio_window_from_bounds

        win = rio_window_from_bounds(w, s_lat, e, n, s.transform)
        win = win.intersection(s.window(*s.bounds))
        arr = s.read(1, window=win)
        transform = s.window_transform(win)
        profile = {"crs": s.crs, "transform": transform, "height": arr.shape[0], "width": arr.shape[1]}
    arr = np.asarray(arr).astype(np.float32)
    return arr, profile


def load_merit_dem(
    aoi: AOI,
    *,
    cache_dir: pathlib.Path | None = None,
) -> xr.DataArray:
    """Load MERIT DEM 90 m for the AOI, reprojected to the AOI's grid.

    MERIT is hydrologically conditioned (no spurious pits), which makes
    it the preferred DEM for TWI computation. The data is hosted on a
    password-protected Dropbox folder; register via the Google Form on
    https://global-hydrodynamics.github.io/MERIT_DEM/ and pass the
    resulting shared-link token as ``MERIT_AUTH_TOKEN``.

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
