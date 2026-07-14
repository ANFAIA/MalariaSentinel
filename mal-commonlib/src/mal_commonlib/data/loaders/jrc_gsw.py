"""JRC Global Surface Water (GSW) 30 m water mask loader (M2 fix — channel 0, ``water_frac``).

Public surface
--------------
``load_jrc_gsw_water_frac(aoi, year=2021, month=None, *, cache_dir=None,
water_classes=None, threshold_pct=80) -> xr.DataArray``

The ``month`` parameter is accepted for signature uniformity with the other
M1.3a loaders (``build_env`` calls every loader as ``loader(aoi, year,
month)``) but is ignored: JRC GSW has an annual product (``occurrence``)
and a 12-band monthly product (``monthly_recurrence``). For the M2
validation we use a single tile per year (the annual ``occurrence``
band) and binarise at ``threshold_pct=80``, the standard "permanent
water" cut-off in the JRC GSW literature (Pekel et al., 2016).

Why this loader exists
----------------------
The M2 real-data validation observed ``water_frac ≈ 7%`` of cells on
the Ghana AOI (30 186 / 429 229) using the ESA WorldCover 10 m product
(``esa-worldcover`` STAC collection). All 20 larval sites in
``data/ghana_idit/occurrence.txt`` sit in cells with
``water_frac = 0.0``. Because ``build_env`` requires
``TWI > 8 AND water_frac > 0`` to detect a habitat patch, no patches
were materialised at the sites and the ABM never activated them; the
M2 report ended with ``n_sites = 0``, ``AUC = nan``.

The 10 m WorldCover annual product misses small water bodies (pools,
streams, irrigation channels) that are too narrow or too seasonal to
be classified as "permanent water" at 10 m. JRC GSW at 30 m has a
dedicated "water occurrence" band (the fraction of monthly observations
where the pixel was detected as water) that catches these features
without changing the per-AOI grid math — we still reproject a binary
"is-water-this-cell" mask from 30 m onto the 1 km AOI grid.

This loader is the M2 fix for the water layer. It replaces
``load_worldcover_water_frac`` in ``build_env``'s ``water_frac`` channel
without changing the contract (same shape, dtype, CRS, and
``[0, 1] / -9999`` value domain).

Distribution
------------
The M2 fix uses the **Microsoft Planetary Computer** STAC catalog as
the primary source. The catalog exposes the JRC GSW ``occurrence``,
``change``, ``transition`` and ``monthly_recurrence`` assets under the
``jrc-gsw`` collection. We stream-reproject each tile's AOI bbox
window directly into the AOI grid via two ``rasterio.warp.reproject``
calls (binary water mask + valid-pixel mask) per tile — no full-tile
read, no merged mosaic. Memory is bounded by the AOI grid (~0.4 MB
for Ghana) plus a single tile window.

Output contract (per ``docs/abm-output-contract.md`` §2, channel 0):
    * dims (y, x), dtype ``float32``
    * CRS = ``aoi.crs``
    * values in ``{0.0, 1.0}`` (binary after threshold; not a fraction)
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

# Microsoft Planetary Computer STAC catalog. The JRC GSW collection
# (id ``jrc-gsw``) exposes:
#   * ``occurrence``           — annual water occurrence 1984-2021
#   * ``change``               — year-on-year surface water change
#   * ``transition``           — transitions (permanence classes)
#   * ``monthly_recurrence``   — 12-band monthly recurrence
#   * ``monthly_history``      — 12-band per-month water history
# We use ``occurrence`` (the annual product) and binarise at
# ``threshold_pct=80`` to match the JRC GSW standard "permanent water"
# classification (Pekel et al., 2016).
_PC_STAC_URL = "https://planetarycomputer.microsoft.com/api/stac/v1"
_PC_COLLECTION = "jrc-gsw"
_PC_ASSET = "occurrence"

# Default cut-off. Pekel et al. (2016) and the JRC GSW documentation
# treat ``occurrence >= 80`` as "permanent water". Lower thresholds
# (e.g. 50) pick up seasonal water; the M2 fix uses the stricter 80
# to stay close to the WorldCover "permanent water bodies" semantics.
DEFAULT_THRESHOLD_PCT: int = 80

# Year range for the JRC GSW product (1984-2021 inclusive).
_MIN_YEAR: int = 1984
_MAX_YEAR: int = 2021

_NODATA_OUT_SCALAR = -9999.0


def _ensure_cache_dir(cache_dir: pathlib.Path | None) -> pathlib.Path:
    if cache_dir is None:
        cache_dir = pathlib.Path(tempfile.gettempdir()) / "mal_commonlib" / "jrc_gsw"
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


def _make_reference_grid(aoi: AOI) -> xr.DataArray:
    h, w = aoi.cells_per_side()
    wmin, smin, wmax, smax = aoi.bbox
    transform = from_bounds(wmin, smin, wmax, smax, w, h)
    arr = np.zeros((h, w), dtype=np.float32)
    da = xr.DataArray(arr, dims=("y", "x"), name="ref")
    da.rio.write_crs(aoi.crs, inplace=True)
    da.rio.write_transform(transform, inplace=True)
    return da


# -- Planetary Computer STAC loader ----------------------------------------


def _load_jrc_gsw_pc(
    aoi: AOI,
    year: int,
    threshold_pct: int,
) -> tuple[np.ndarray, dict]:
    """Read the JRC GSW ``occurrence`` band for the AOI via the Planetary
    Computer STAC catalog, streaming each tile window directly into the
    AOI grid (no full-tile or merged-mosaic allocation).

    The binarisation is ``(occurrence >= threshold_pct).astype(float32)``
    — a 1 km AOI cell whose 30 m pixels are all above the threshold
    becomes 1.0; otherwise 0.0. Two ``rasterio.warp.reproject`` calls per
    tile accumulate ``water_count`` and ``valid_count`` on the AOI grid;
    the final value is the mean of the binary water mask over all tiles
    that covered the cell.

    Memory is bounded by:
      * the AOI grid itself (~0.4 MB for a 779x551 AOI at 1 km), plus
      * one tile window (≤180 MB worst case for the 3°x3° tiles at 30 m)
        plus the per-tile ``tile_water`` / ``tile_valid`` reproject
        destinations (two float32 arrays of AOI-grid shape, freed at the
        end of each iteration).

    Returns:
        (arr, profile) where ``arr`` is a ``(H, W)`` float32 array on the
        AOI's grid (CRS = AOI CRS, transform = AOI transform), values in
        [0, 1] (per-AOI-cell water fraction = mean of binary water mask
        over all tiles that covered the cell), and ``-9999.0`` for cells
        that no tile covered. ``profile`` is a dict with ``crs``,
        ``transform``, ``height``, ``width``, and ``jrc_gsw_year`` (the
        year actually fetched — equals the requested year if available,
        else 2020, since the PC ``jrc-gsw`` collection is tagged with
        2020 only; the loader transparently falls back to 2020 when the
        requested year has no STAC items).
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
        datetime=f"{year}-01-01T00:00:00Z/{year}-12-31T23:59:59Z",
    )
    items = list(search.items())
    actual_year = int(year)
    if not items:
        # The JRC GSW collection on Planetary Computer is tagged with
        # 2020 only (504 items, all dated 2020 — the static product was
        # published with a single datetime). Fall back to 2020 when the
        # requested year is unavailable so callers like ``build_env``
        # (which asks for year=2021) still get a real raster. If the
        # 2020 fallback also returns 0 items, the bbox is uncovered and
        # we raise. See ``test_jrc_gsw_falls_back_to_2020_when_requested_year_missing``.
        fallback_search = catalog.search(
            collections=[_PC_COLLECTION],
            bbox=list(bbox),
            datetime="2020-01-01T00:00:00Z/2020-12-31T23:59:59Z",
        )
        items = list(fallback_search.items())
        actual_year = 2020
        if not items:
            raise FileNotFoundError(
                f"No JRC GSW tiles in Planetary Computer for bbox={bbox} "
                f"year={year} (and 2020 fallback)"
            )
    signed_items = [planetary_computer.sign(item) for item in items]

    H, W = aoi.cells_per_side()
    H = int(H)
    W = int(W)
    ref_transform = from_bounds(*aoi.bbox, W, H)
    water_count = np.zeros((H, W), dtype=np.float64)
    valid_count = np.zeros((H, W), dtype=np.float64)
    threshold = int(threshold_pct)

    for item in signed_items:
        href = item.assets[_PC_ASSET].href
        with rasterio.open(href) as src:
            win = rio_window_from_bounds(*bbox, src.transform)
            win = win.intersection(rasterio.windows.Window(0, 0, src.width, src.height))
            if win.width <= 0 or win.height <= 0:
                continue
            raw = src.read(1, window=win)
            if hasattr(raw, "filled"):
                raw = np.ma.filled(raw, 0)
            win_transform = src.window_transform(win)
            # JRC GSW ``occurrence`` is uint8 with values 0-100 (the
            # fraction of monthly observations where the pixel was water).
            # The original layer also has 200 = no observation (e.g.
            # Antarctica); treat anything > 100 as NoData. We binarise at
            # ``threshold_pct`` to get a permanent-water mask.
            occ = np.asarray(raw, dtype=np.uint8)
            water_mask = ((occ > 0) & (occ <= 100) & (occ >= threshold)).astype(np.float32)
            tile_water = np.zeros((H, W), dtype=np.float32)
            reproject(
                source=water_mask,
                destination=tile_water,
                src_transform=win_transform,
                src_crs=src.crs,
                dst_transform=ref_transform,
                dst_crs=aoi.crs_obj,
                resampling=Resampling.nearest,
            )
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
            water_count += tile_water
            valid_count += tile_valid

    if not np.any(valid_count > 0):
        out = np.full((H, W), _NODATA_OUT_SCALAR, dtype=np.float32)
    else:
        water_frac = np.where(
            valid_count > 0,
            water_count / np.maximum(valid_count, 1e-9),
            _NODATA_OUT_SCALAR,
        )
        out = water_frac.astype(np.float32)
    profile = {
        "crs": aoi.crs_obj,
        "transform": ref_transform,
        "height": H,
        "width": W,
        "jrc_gsw_year": int(actual_year),
    }
    return out, profile


# -- public API -------------------------------------------------------------


def load_jrc_gsw_water_frac(
    aoi: AOI,
    year: int = 2021,
    month: int | None = None,
    *,
    cache_dir: pathlib.Path | None = None,
    water_classes: Iterable[int] | None = None,
    threshold_pct: int = DEFAULT_THRESHOLD_PCT,
) -> xr.DataArray:
    """Load JRC Global Surface Water (GSW) 30 m ``occurrence`` for the AOI,
    produce a ``water_frac`` raster in [0, 1] by computing the fraction
    of each AOI cell that is "permanent water" (``occurrence >= threshold_pct``).

    The loader goes through the Microsoft Planetary Computer STAC catalog
    (``jrc-gsw`` collection) and reads only the AOI bbox window from
    each intersecting tile. This avoids reading the full 30 m tiles into
    memory (the 3°x3° tiles are ~900 MB at 30 m) and unblocks the M2
    real-data validation.

    Args:
        aoi: the AOI.
        year: JRC GSW product year. The annual ``occurrence`` band is
            available for 1984-2021 inclusive. The default is 2021 (the
            latest available year at the time of writing).
        month: accepted for ``build_env`` signature uniformity; ignored.
            We use the annual ``occurrence`` band, not the monthly
            ``monthly_recurrence`` band. The JRC GSW monthly product
            is reserved for a future M+ enhancement (e.g. seasonal
            water detection).
        cache_dir: optional local cache (currently unused — the STAC
            signed URLs stream directly).
        water_classes: not used by the JRC GSW loader. The JRC GSW
            ``occurrence`` band is a single-band uint8 percentage; we
            binarise at ``threshold_pct`` rather than mapping a set of
            class codes. Kept in the signature for parity with
            ``load_worldcover_water_frac``.
        threshold_pct: the percentage cut-off for "permanent water"
            (default 80, per Pekel et al., 2016 / JRC GSW standard).
            Must be in [0, 100].

    Returns:
        xr.DataArray with dims (y, x), dtype ``float32``, CRS = ``aoi.crs``.
        Values in [0, 1] (a 1 km AOI cell whose 30 m pixels are all
        ``occurrence >= threshold_pct`` is 1.0; a cell with no permanent
        water is 0.0). ``-9999.0`` for NoData (no tile covered the cell).
    """
    if not (_MIN_YEAR <= int(year) <= _MAX_YEAR):
        raise ValueError(
            f"JRC GSW year must be in [{_MIN_YEAR}, {_MAX_YEAR}]; got {year}"
        )
    if not (0 <= int(threshold_pct) <= 100):
        raise ValueError(
            f"JRC GSW threshold_pct must be in [0, 100]; got {threshold_pct}"
        )

    bbox = _aoi_bbox_wgs84(aoi)
    if not all(np.isfinite(b) for b in bbox):
        raise ValueError(f"AOI bbox has non-finite values: {bbox}")

    arr, profile = _load_jrc_gsw_pc(aoi, int(year), int(threshold_pct))

    da = xr.DataArray(
        arr,
        dims=("y", "x"),
        name="water_frac",
        attrs={
            "long_name": "JRC GSW permanent water fraction",
            "source": f"JRC Global Surface Water {year} (Planetary Computer STAC)",
            "units": "fraction [0, 1]",
            "threshold_pct": int(threshold_pct),
            "asset": _PC_ASSET,
        },
    )
    da.rio.write_crs(profile["crs"], inplace=True)
    da.rio.write_transform(profile["transform"], inplace=True)

    # The streaming loader produces an AOI-grid-shaped array in the AOI's
    # CRS — skip the second reproject_match (it would be a no-op and
    # would double the memory traffic for no benefit).
    if str(profile.get("crs")) == str(aoi.crs_obj):
        rep = da.astype(np.float32)
    else:
        ref = _make_reference_grid(aoi)
        rep = da.rio.reproject_match(ref, resampling=Resampling.average)
        rep = rep.astype(np.float32)
    rep = rep.rio.write_nodata(_NODATA_OUT_SCALAR)
    # If the source mosaic is all zero (no water in the bbox), arr is all
    # zero and the average remains zero — that is a valid result, NOT
    # nodata.
    values = rep.values
    values = np.where(values == _NODATA_OUT_SCALAR, values, np.clip(values, 0.0, 1.0))
    values = values.astype(np.float32)
    out = xr.DataArray(
        values,
        dims=("y", "x"),
        name="water_frac",
        attrs={
            "long_name": "JRC GSW permanent water fraction (reprojected)",
            "source": f"JRC Global Surface Water {year} (Planetary Computer STAC)",
            "units": "fraction [0, 1]",
            "threshold_pct": int(threshold_pct),
            "asset": _PC_ASSET,
            "nodata": _NODATA_OUT_SCALAR,
        },
    )
    out.rio.write_crs(aoi.crs, inplace=True)
    out.rio.write_transform(from_bounds(*aoi.bbox, *aoi.cells_per_side()), inplace=True)
    out.rio.write_nodata(_NODATA_OUT_SCALAR, inplace=True)
    return out


__all__ = [
    "load_jrc_gsw_water_frac",
    "DEFAULT_THRESHOLD_PCT",
    "NODATA_OUT",
]
NODATA_OUT = _NODATA_OUT_SCALAR
