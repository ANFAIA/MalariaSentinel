"""JRC Global Surface Water (GSW) 30 m static habitat loader (contract v3.0).

Public surface
--------------
``load_jrc_gsw_habitat_features(aoi, *, year=2021, cache_dir=None) -> xr.Dataset``

A single retained channel: ``jrc_persistent``, the per-cell FRACTION of
water pixels with occurrence >= 80 % (coastline masking excluded). The
retired threshold-80 binary mask and the ``water_frac`` channel are gone
(plan docs/plans/in-process/redesign/01-retirada-hidrologia-dem-escorrentia.md
§6): the fraction IS the feature the redesign consumes, a continuous [0, 1]
per-cell value, not a binarised raster.

Why this loader exists
----------------------
Small water bodies (pools, streams, irrigation channels) are missed by
the 10 m WorldCover classification. JRC GSW at 30 m has a dedicated
"water occurrence" band (the fraction of monthly observations where the
pixel was detected as water) that catches these features; the per-cell
mean of the binary "occurrence >= 80" mask directly IS the
persistent-water fraction used as static potential habitat.

Distribution
------------
The loader uses the **Microsoft Planetary Computer** STAC catalog
(``jrc-gsw`` collection) and streams each tile's AOI-bbox window directly
into the AOI grid via ``rasterio.warp.reproject`` — no full-tile read,
no merged mosaic.

Output contract (plan 02 §5, static plane):
    * dims (y, x), dtype ``float32``
    * CRS = ``aoi.crs``
    * values in ``[0, 1]`` (fraction of >= 80 %-permanent pixels)
    * NoData: ``NODATA_SENTINEL()``
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
from mal_commonlib.model_constants import model_constant

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

_NODATA_OUT_SCALAR = float(model_constant("ingest", "nodata_sentinel"))


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
        over all tiles that covered the cell), and ``NODATA_SENTINEL()`` for cells
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


def load_jrc_gsw_habitat_features(
    aoi: AOI,
    *,
    year: int = 2021,
    cache_dir: pathlib.Path | None = None,
) -> xr.Dataset:
    """Load the contract v3.0 static habitat features derived from the JRC
    Global Surface Water (GSW) 30 m ``occurrence`` band.

    Single channel retained from the retired binary water/seasonal split
    (plan docs/plans/in-process/redesign/01-retirada-hidrologia-dem-escorrentia.md
    §6): the per-cell FRACTION of water pixels with occurrence >= 80 %,
    coastline-masking excluded, as the only static surface-water signal the
    redesign consumes (``jrc_persistent`` feature column). The old
    threshold-80 binary mask (a whole-country binary raster with ~5 525
    cells, useless for a relative habitat index) is NOT produced anymore;
    the fraction IS the feature.

    The loader goes through the Microsoft Planetary Computer STAC catalog
    (``jrc-gsw`` collection) and reads only the AOI bbox window from
    each intersecting tile.

    Args:
        aoi: the AOI.
        year: JRC GSW product year (snapshot selector). The annual
            ``occurrence`` band is available for 1984-2021 inclusive.
            Default is 2021 (the latest available year).
        cache_dir: optional local cache (currently unused — the STAC
            signed URLs stream directly).

    Returns:
        ``xr.Dataset`` with one variable ``jrc_persistent`` of dims
        (y, x), dtype float32, CRS = ``aoi.crs``, in [0, 1];
        ``NODATA_SENTINEL()`` for NoData.
    """
    if not (_MIN_YEAR <= int(year) <= _MAX_YEAR):
        raise ValueError(
            f"JRC GSW year must be in [{_MIN_YEAR}, {_MAX_YEAR}]; got {year}"
        )

    bbox = _aoi_bbox_wgs84(aoi)
    if not all(np.isfinite(b) for b in bbox):
        raise ValueError(f"AOI bbox has non-finite values: {bbox}")

    # The feature needs NO 80 % binarisation: the per-cell mean of the
    # binary "occurrence >= threshold" mask directly IS the fraction of
    # the cell covered by >=80 %-permanent water pixels. The retired code
    # multiplied the resulting fraction into a separate 0.8 binary step —
    # dropped; the mean at threshold_pct = PERMANENT_THRESHOLD_PCT.
    arr, profile = _load_jrc_gsw_pc(
        aoi, int(year), int(PERMANENT_THRESHOLD_PCT)
    )

    values = arr.astype(np.float32)
    values = np.where(values == _NODATA_OUT_SCALAR, values,
                      np.clip(values, 0.0, 1.0))

    out = xr.DataArray(
        values,
        dims=("y", "x"),
        name="jrc_persistent",
        attrs={
            "long_name": "JRC GSW fraction of >=80%-occurrence water pixels",
            "source": f"JRC Global Surface Water {year} (Planetary Computer STAC)",
            "units": "fraction of cell area [0, 1]",
            "threshold_pct": int(PERMANENT_THRESHOLD_PCT),
            "asset": _PC_ASSET,
            "nodata": _NODATA_OUT_SCALAR,
        },
    )
    out.rio.write_crs(profile["crs"], inplace=True)
    if str(profile["crs"]) != str(aoi.crs_obj):
        ref = _make_reference_grid(aoi)
        out = out.rio.reproject_match(ref, resampling=Resampling.average)
        out = out.astype(np.float32)
    ds = out.to_dataset(name="jrc_persistent")
    ds.rio.write_crs(aoi.crs, inplace=True)
    ds.rio.write_transform(from_bounds(*aoi.bbox, *aoi.cells_per_side()), inplace=True)
    ds["jrc_persistent"].rio.write_nodata(_NODATA_OUT_SCALAR, inplace=True)
    ds.attrs = {
        "contract": "habitat-v3.0-statics",
        "source": f"JRC Global Surface Water {year} (Planetary Computer STAC)",
        "asset": _PC_ASSET,
        "year_used": int(profile["jrc_gsw_year"]),
        "nodata": _NODATA_OUT_SCALAR,
    }
    return ds


DOWNLOADER = {
    "name": "jrc_gsw",
    "description": "JRC Global Surface Water: per-cell permanent-water feature for the habitat contract",
    "requires_auth": ["none"],
    "license": "CC-BY-4.0",
    "attribution": (
        "JRC Global Surface Water v1.4 © European Union/JRC (CC BY 4.0, "
        "Decision 2011/833/EU). Pekel, J.-F., et al., 2016, High-resolution "
        "mapping of global surface water and its long-term changes, "
        "Nature 540, 418-422."
    ),
    "is_time_series": False,
    "outputs": {
        "habitat_features": load_jrc_gsw_habitat_features,
    },
    "manifest_keys": {
        "habitat_features": "jrc_habitat_features",
    },
}


__all__ = [
    "load_jrc_gsw_habitat_features",
    "PERMANENT_THRESHOLD_PCT",
    "DEFAULT_THRESHOLD_PCT",
    "NODATA_OUT",
    "DOWNLOADER",
]
NODATA_OUT = _NODATA_OUT_SCALAR
PERMANENT_THRESHOLD_PCT: int = 80
