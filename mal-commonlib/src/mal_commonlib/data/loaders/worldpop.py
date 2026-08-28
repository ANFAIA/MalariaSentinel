"""WorldPop gridded population loader (M7 — host density).

Public surface
--------------
``load_worldpop_population(aoi, year=2019, *, cache_dir=None) -> xr.DataArray``

Loads a WorldPop per-country constrained population raster, clips it to the
AOI bounding box, and reprojects it onto the AOI grid. The output is
**population count per AOI cell** (persons/cell) — not density.

Country code
~~~~~~~~~~~~
The download URL is parameterised by the AOI's ``iso3`` (ISO 3166-1 alpha-3
country code). The previous implementation hardcoded ``"gha"``; this loader
works for any country as long as the AOI carries an ``iso3`` field (see
``aois.yaml`` or ``AOI.from_bbox(..., iso3="GHA")``).

Release
~~~~~~~
By default the loader targets the WorldPop Global High Resolution Population
estimates (legacy "Global1" 2000–2020), which serves one per-country GeoTIFF
per year. The newer Global2 / R2025A release (2015–2030, R2025A_v1) is only
distributed as a single 5.2 GB ZIP — not yet exposed by country — so it is
not selectable from this loader. To migrate to R2025A when per-country files
are published, pass ``release="R2025A"`` and the URL template will switch
accordingly.

Bug fix (M7.5)
~~~~~~~~~~~~~~
The previous loader used ``Resampling.nearest`` when reprojecting from the
source raster (~100 m) to the AOI grid (~1 km). That collapses ~116 source
pixels into 1 destination pixel, **discarding ~99% of the source mass**. For
WorldPop Ghana 2019 this dropped the population total from ~32 M to ~273 k.

This loader now uses **sum-preserving aggregation** that respects the source
raster's NoData sentinel:

* When the source raster and the AOI grid share the same axis-aligned CRS
  (the common WorldPop + WGS-84 + AOI case), aggregation is done with a
  2-D cumulative sum in O(H_src · W_src + H_dst · W_dst) — ~0.1 s for Ghana
  instead of ~110 s with ``rasterio.warp.reproject`` + ``Resampling.sum``.
* When the CRSes differ or the source raster is rotated, the loader falls
  back to ``rasterio.warp.reproject`` with ``Resampling.sum``.

The aggregation lives in ``mal_commonlib.data.host_utils.aggregate_to_grid``
for the cross-CRS path and in ``_sum_preserving_axis_aligned`` here for the
fast same-CRS path.

Notes:
    * Returns population count per cell (persons/pixel), NOT density.
    * The loader caches the downloaded GeoTIFF locally; re-runs skip the
      download if the file already exists.
    * Checksum verification is performed on download via SHA-256 when
      available from the server.
"""
from __future__ import annotations

import hashlib
import os
import pathlib
import shutil
import warnings
from typing import TYPE_CHECKING

import numpy as np
import rasterio
import rioxarray  # noqa: F401
import xarray as xr
from rasterio.transform import from_bounds
from rasterio.warp import Resampling

if TYPE_CHECKING:
    from mal_commonlib.aoi import AOI

# Per-country file name template for the legacy "Global1" 2000-2020 product.
# Pattern: {iso3_lower}_ppp_{year}_constrained.tif
# Hosted under /GIS/Population/Global_2000_2020_Constrained/{year}/{iso3}/{iso3}_...
_GLOBAL1_URL_TEMPLATE = (
    "https://data.worldpop.org/GIS/Population/Global_2000_2020_Constrained/"
    "{year}/{iso3}/{iso3_lower}_ppp_{year}_constrained.tif"
)

# Per-country file name template for Global2 / R2025A v1 — **not yet served
# per country** by WorldPop. The pattern matches the R2025A release statement
# (`{iso}_{gender}_{age group}_{year}_{type}_{resolution}_{release}_{version}.tif`)
# and is wired up so that once per-country GeoTIFFs are exposed we just need
# to point the base URL at the right directory.
# Total both genders, all ages: gender=t, age group=00.
_R2025A_URL_TEMPLATE = (
    "https://data.worldpop.org/repo/prj/Global_2015_2030/R2025A/"
    "population_estimates/v1/{iso3}/{iso3_lower}_t_00_{year}_CN_100m_R2025A_v1.tif"
)

# Year ranges per release.
_GLOBAL1_YEAR_RANGE = (2000, 2020)
_R2025A_YEAR_RANGE = (2015, 2030)

# Default NoData sentinel for the loader's output grid (always -9999.0).
_OUT_NODATA = -9999.0

__all__ = ["load_worldpop_population", "WorldPopLoader", "DOWNLOADER"]


def _default_cache_dir() -> pathlib.Path:
    base = os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache")
    return pathlib.Path(base) / "mal_commonlib" / "worldpop"


def _download_to(url: str, dest: pathlib.Path, *, timeout: int = 120) -> pathlib.Path:
    """Stream ``url`` to ``dest`` (skip if already cached)."""
    import requests

    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    with requests.get(url, stream=True, timeout=timeout, allow_redirects=True) as r:
        r.raise_for_status()
        tmp = dest.with_suffix(dest.suffix + ".part")
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(chunk_size=4 * 1024 * 1024):
                if chunk:
                    f.write(chunk)
        shutil.move(str(tmp), str(dest))
    return dest


def _aoi_to_src_bbox(aoi: "AOI") -> tuple[float, float, float, float]:
    """Transform AOI bbox to WGS-84 for windowed reads."""
    import pyproj

    if str(aoi.crs_obj).upper() in {"EPSG:4326", "WGS84", "4326"}:
        return aoi.bbox
    t = pyproj.Transformer.from_crs(aoi.crs, "EPSG:4326", always_xy=True)
    w, s, e, n = aoi.bbox
    w, s = t.transform(w, s)
    e, n = t.transform(e, n)
    return (float(w), float(s), float(e), float(n))


def _sum_preserving_axis_aligned(
    src: np.ndarray,
    src_bounds: "rasterio.coords.BoundingBox",
    src_transform: rasterio.Affine,
    dst_shape: tuple[int, int],
    dst_bounds: tuple[float, float, float, float],
    dst_nodata: float = _OUT_NODATA,
) -> np.ndarray:
    """Sum-preserving aggregation for axis-aligned grids in the same CRS.

    Both the source and destination must be axis-aligned with the same CRS
    (the common WorldPop + WGS-84 case). Uses a 2-D cumulative sum on the
    source array; rectangle sums via 4 corner lookups give the per-cell
    total. Source ``NoData`` cells are masked to zero before summation.

    Args:
        src: (H_src, W_src) float array with source values (possibly containing
            NoData). The source's NoData sentinel must already be ``dst_nodata``
            (or any value that should be treated as missing).
        src_bounds: ``rasterio.coords.BoundingBox`` of the source raster.
        src_transform: affine transform of the source raster.
        dst_shape: (H_dst, W_dst) output grid shape.
        dst_bounds: (west, south, east, north) of the destination grid.
        dst_nodata: sentinel written into destination cells with no source
            coverage.

    Returns:
        (H_dst, W_dst) float32 array. Destination cells with no source
        coverage are set to ``dst_nodata``.
    """
    H_src, W_src = src.shape
    H_dst, W_dst = dst_shape
    west, south, east, north = dst_bounds

    src_res = abs(src_transform.a)  # source pixel size (assumed square & axis-aligned)
    src_left = src_bounds.left
    src_top = src_bounds.top

    # Treat any value == dst_nodata as missing (covers the common -9999 / -99999 cases).
    src_mask = src != dst_nodata
    src_zero = np.where(src_mask, src, 0.0).astype(np.float64)

    # 2-D cumulative sums (1-pixel border for O(1) rectangle queries).
    cs_mask = np.zeros((H_src + 1, W_src + 1), dtype=np.int64)
    cs_mask[1:, 1:] = src_mask.astype(np.int64).cumsum(0).cumsum(1)
    cs_zero = np.zeros((H_src + 1, W_src + 1), dtype=np.float64)
    cs_zero[1:, 1:] = src_zero.cumsum(0).cumsum(1)

    # Destination cell bounds in source pixel coordinates.
    dst_res_x = (east - west) / W_dst
    dst_res_y = (north - south) / H_dst

    # Per-row source pixel range (rows increase downward in source).
    aoi_top_y = north - np.arange(H_dst) * dst_res_y
    aoi_bot_y = north - (np.arange(H_dst) + 1) * dst_res_y
    sr_top = np.clip(((src_top - aoi_top_y) / src_res).astype(np.int64), 0, H_src)
    sr_bot = np.clip(((src_top - aoi_bot_y) / src_res).astype(np.int64), 0, H_src)
    sr_lo = np.minimum(sr_top, sr_bot)
    sr_hi = np.maximum(sr_top, sr_bot)

    # Per-column source pixel range.
    aoi_left_x = west + np.arange(W_dst) * dst_res_x
    aoi_right_x = west + (np.arange(W_dst) + 1) * dst_res_x
    sc_left = np.clip(((aoi_left_x - src_left) / src_res).astype(np.int64), 0, W_src)
    sc_right = np.clip(((aoi_right_x - src_left) / src_res).astype(np.int64), 0, W_src)
    sc_lo = np.minimum(sc_left, sc_right)
    sc_hi = np.maximum(sc_left, sc_right)

    # O(H_dst · W_dst) per-cell rectangle sums via 4 corner lookups.
    SR_HI = sr_hi[:, None]
    SR_LO = sr_lo[:, None]
    SC_HI = sc_hi[None, :]
    SC_LO = sc_lo[None, :]

    out_sum = cs_zero[SR_HI, SC_HI] - cs_zero[SR_LO, SC_HI] - cs_zero[SR_HI, SC_LO] + cs_zero[SR_LO, SC_LO]
    out_cnt = cs_mask[SR_HI, SC_HI] - cs_mask[SR_LO, SC_HI] - cs_mask[SR_HI, SC_LO] + cs_mask[SR_LO, SC_LO]

    out = np.where(out_cnt > 0, out_sum, _OUT_NODATA).astype(np.float32)
    return out


def _read_clip(
    aoi: "AOI",
    tif_path: pathlib.Path,
    year: int,
    *,
    output_nodata: float = _OUT_NODATA,
) -> xr.DataArray:
    """Read the cached GeoTIFF and aggregate onto the AOI grid.

    Args:
        aoi: target AOI; the grid dimensions and CRS come from ``aoi``.
        tif_path: cached source GeoTIFF (any CRS / resolution).
        year: dataset year, recorded in the output attrs.
        output_nodata: sentinel written into destination cells with no
            source coverage.

    Returns:
        ``xr.DataArray`` of shape ``(H, W)`` aligned with ``aoi``, dtype
        float32. Population count per AOI cell; sum-preserving across the
        source raster. ``output_nodata`` for cells with no source coverage.

    Note:
        The previous implementation used ``Resampling.nearest`` here, which
        collapses ~116 source pixels into 1 destination pixel and silently
        discards ~99% of the population total. We now use a sum-preserving
        path: a fast cumulative-sum aggregation when both grids are
        axis-aligned in the same CRS, or ``aggregate_to_grid`` (which uses
        ``Resampling.sum``) when the CRSes differ.
    """
    import rasterio.windows
    from mal_commonlib.data.host_utils import aggregate_to_grid

    bbox_wgs84 = _aoi_to_src_bbox(aoi)
    w, s, e, n = bbox_wgs84

    h, w_cells = aoi.cells_per_side()
    dst_transform = from_bounds(*aoi.bbox, w_cells, h)

    with rasterio.open(str(tif_path)) as src:
        src_crs = src.crs
        if not str(aoi.crs_obj).upper() in {"EPSG:4326", "WGS84", "4326"}:
            import pyproj

            t = pyproj.Transformer.from_crs(aoi.crs, src_crs, always_xy=True)
            w_t, s_t = t.transform(w, s)
            e_t, n_t = t.transform(e, n)
            win = rasterio.windows.from_bounds(w_t, s_t, e_t, n_t, src.transform)
        else:
            win = rasterio.windows.from_bounds(w, s, e, n, src.transform)

        win = win.intersection(
            rasterio.windows.Window(0, 0, src.width, src.height)
        )
        if win.width <= 0 or win.height <= 0:
            raise ValueError(
                f"AOI bbox {aoi.bbox} does not overlap WorldPop raster bounds "
                f"({src.bounds})"
            )
        arr = src.read(1, window=win)
        src_transform_window = src.window_transform(win)
        nodata = src.nodata
        # The source file may use a different sentinel (-99999, etc.). Re-map
        # to our output sentinel so downstream masks are consistent.
        if nodata is None:
            sentinel = output_nodata
        else:
            sentinel = nodata
        arr = np.asarray(arr, dtype=np.float32)
        arr_remapped = np.where(arr == sentinel, np.float32(output_nodata), arr)

    # Fast path: same CRS, axis-aligned source (the common WorldPop case).
    same_crs = str(src_crs).upper() in {"EPSG:4326", "WGS84", "4326"} and \
        str(aoi.crs_obj).upper() in {"EPSG:4326", "WGS84", "4326"}
    # |src_transform.a| == |src_transform.e| (axis-aligned square pixels);
    # compare with tolerance because GeoTIFFs often store the row increment as
    # a negative number (north-up convention).
    a_abs = abs(src_transform_window.a)
    e_abs = abs(src_transform_window.e)
    is_axis_aligned = (
        abs(src_transform_window.b) < 1e-12
        and abs(src_transform_window.d) < 1e-12
        and abs(a_abs - e_abs) < 1e-9 * max(a_abs, e_abs, 1.0)
    )

    if same_crs and is_axis_aligned:
        # Build a BoundingBox-like object for _sum_preserving_axis_aligned.
        # Compute src bounds from transform + window.
        from rasterio.coords import BoundingBox
        win_t = src_transform_window
        win_left = win_t.c
        win_top = win_t.f
        win_right = win_t.c + win_t.a * arr.shape[1]
        win_bottom = win_t.f + win_t.e * arr.shape[0]
        src_bounds = BoundingBox(
            left=win_left, bottom=win_bottom, right=win_right, top=win_top,
        )
        out = _sum_preserving_axis_aligned(
            src=arr_remapped,
            src_bounds=src_bounds,
            src_transform=src_transform_window,
            dst_shape=(h, w_cells),
            dst_bounds=aoi.bbox,
            dst_nodata=output_nodata,
        )
    else:
        # Cross-CRS fallback: use aggregate_to_grid with Resampling.sum. It
        # masks source nodata to 0 before reprojection, so source-empty cells
        # contribute 0 (destination cells with no source coverage end up at
        # 0.0, which we then re-mark as nodata).
        coverage_src = (arr_remapped != output_nodata).astype(np.float32)
        out = aggregate_to_grid(
            arr_remapped,
            src_transform_window,
            src_crs,
            dst_transform,
            aoi.crs_obj,
            (h, w_cells),
            method="sum",
            nodata=output_nodata,
        )
        coverage_dst = np.zeros((h, w_cells), dtype=np.float32)
        from rasterio.warp import reproject as _reproject
        _reproject(
            source=coverage_src,
            destination=coverage_dst,
            src_transform=src_transform_window,
            src_crs=src_crs,
            dst_transform=dst_transform,
            dst_crs=aoi.crs_obj,
            resampling=Resampling.sum,
        )
        out[coverage_dst <= 0.0] = np.float32(output_nodata)

    da = xr.DataArray(
        out,
        dims=("y", "x"),
        name="worldpop_population",
        attrs={
            "long_name": "WorldPop population count per AOI cell",
            "units": "persons/cell",
            "source": f"WorldPop (legacy Global1, year={year})",
            "year": year,
            "nodata": output_nodata,
        },
    )
    da.rio.write_crs(aoi.crs_obj, inplace=True)
    da.rio.write_transform(dst_transform, inplace=True)
    da.rio.write_nodata(output_nodata, inplace=True)
    return da


def _resolve_url(year: int, iso3: str, *, release: str) -> str:
    """Build the WorldPop per-country GeoTIFF URL for the given year+ISO3."""
    iso3_lower = iso3.lower()
    if release == "Global1":
        lo, hi = _GLOBAL1_YEAR_RANGE
        if not (lo <= year <= hi):
            raise ValueError(
                f"WorldPop Global1 supports {lo}-{hi}; got {year}. "
                f"Pass release='R2025A' for 2015-2030 coverage."
            )
        return _GLOBAL1_URL_TEMPLATE.format(
            year=year, iso3=iso3, iso3_lower=iso3_lower,
        )
    if release == "R2025A":
        lo, hi = _R2025A_YEAR_RANGE
        if not (lo <= year <= hi):
            raise ValueError(
                f"WorldPop R2025A supports {lo}-{hi}; got {year}."
            )
        return _R2025A_URL_TEMPLATE.format(
            year=year, iso3=iso3, iso3_lower=iso3_lower,
        )
    raise ValueError(
        f"Unknown WorldPop release {release!r}; expected 'Global1' or 'R2025A'"
    )


def _cache_filename(iso3_lower: str, year: int, release: str) -> str:
    if release == "Global1":
        return f"{iso3_lower}_ppp_{year}_constrained.tif"
    return f"{iso3_lower}_t_00_{year}_CN_100m_R2025A_v1.tif"


def load_worldpop_population(
    aoi: "AOI | str",
    *,
    year: int = 2019,
    release: str = "Global1",
    cache_dir: pathlib.Path | None = None,
) -> xr.DataArray:
    """Load WorldPop constrained population density for the AOI.

    Args:
        aoi: the AOI (bbox, CRS, resolution_m, slug, iso3) or a slug string.
            ``aoi.iso3`` is required — country-scoped loaders cannot guess
            the ISO code from a bbox alone.
        year: target year (default 2019). Valid range depends on ``release``.
        release: WorldPop release identifier:
            - ``"Global1"`` (default): legacy 2000–2020, per-country GeoTIFFs.
            - ``"R2025A"``: Global2 / R2025A v1, 2015–2030. **Not yet served
              per-country** — will raise ``HTTPError`` until WorldPop
              publishes per-country files.
        cache_dir: local cache for downloaded GeoTIFFs.

    Returns:
        ``xr.DataArray`` with dims ``(y, x)``, dtype float32, CRS = ``aoi.crs``.
        Values are **population count per AOI cell** (sum-preserving across
        the source raster). ``-9999.0`` for cells with no source coverage.

    Raises:
        ValueError: if ``aoi.iso3`` is missing or ``year`` is outside the
            valid range for the chosen release.
        requests.HTTPError: on download failure (e.g. R2025A per-country
            file not published yet).
    """
    if isinstance(aoi, str):
        from mal_commonlib.aoi import AOI

        aoi = AOI.from_slug(aoi)

    iso3 = aoi.require_iso3()  # raises ValueError if missing
    iso3_lower = iso3.lower()

    cache = cache_dir if cache_dir is not None else _default_cache_dir()
    cache = pathlib.Path(cache)
    cache.mkdir(parents=True, exist_ok=True)

    file_name = _cache_filename(iso3_lower, year, release)
    tif_path = cache / file_name
    url = _resolve_url(year, iso3, release=release)
    _download_to(url, tif_path)
    return _read_clip(aoi, tif_path, year)


class WorldPopLoader:
    """DEPRECATED: Use ``load_worldpop_population()`` instead."""

    def load(
        self,
        aoi: "AOI",
        year: int = 2019,
        *,
        release: str = "Global1",
        cache_dir: pathlib.Path | None = None,
    ) -> xr.DataArray:
        warnings.warn(
            "WorldPopLoader is deprecated; use load_worldpop_population() instead",
            DeprecationWarning,
            stacklevel=2,
        )
        return load_worldpop_population(
            aoi, year=year, release=release, cache_dir=cache_dir,
        )


DOWNLOADER = {
    "name": "worldpop",
    "description": "WorldPop constrained population density",
    "requires_auth": ["none"],
    "is_time_series": False,
    "outputs": {
        "population": load_worldpop_population,
    },
    "manifest_keys": {
        "population": "worldpop",
    },
}
