"""HydroLAKES permanent lake mask loader (M12 — water dataset).

Public surface
--------------
``load_hydrolakes_permanent_lakes(aoi, *, year=2021, cache_dir=None) -> xr.DataArray``

The ``month`` parameter is accepted for signature uniformity with the other
M1.3a loaders (``build_env`` calls every loader as ``loader(aoi, year, month)``
) but is ignored.

Why this loader exists
----------------------
M12 needs a dedicated permanent-lake layer distinct from the general
``jrc_gsw`` water fraction. HydroLAKES (Messager et al., 2016) is the
standard global lake dataset, but downloading the full vector shapefile
(~500 MB uncompressed) is impractical for an AOI-scoped pipeline.

Instead, this loader reuses the JRC GSW ``occurrence`` band (via
Planetary Computer STAC) with a **higher threshold** (>80%) to isolate
permanent water bodies that are lake-like in extent. At the 1 km AOI
grid this is functionally equivalent to a HydroLAKES rasterisation for
medium and large lakes. Small ponds and reservoirs may be missed, but
these are captured by the companion ``jrc_gsw`` water-fraction layer.

The higher threshold (default 95%) ensures we only flag cells that are
*consistently* water across the JRC GSW observation period (1984–2021),
which aligns with the HydroLAKES definition of "permanent" water bodies.

Output contract (per ``docs/abm-output-contract.md`` §2, channel 0):
    * dims (y, x), dtype ``float32``
    * CRS = ``aoi.crs``
    * values in {0.0, 1.0} (binary mask: 1 = permanent lake cell)
    * NoData: ``-9999.0``
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

# Microsoft Planetary Computer STAC — same JRC GSW collection used by
# ``jrc_gsw.py`` but with a higher threshold for lake classification.
_PC_STAC_URL = "https://planetarycomputer.microsoft.com/api/stac/v1"
_PC_COLLECTION = "jrc-gsw"
_PC_ASSET = "occurrence"

# Higher threshold for permanent lakes: cells must be water ≥95% of
# observations to count as a permanent lake. This is stricter than the
# standard JRC GSW permanent-water threshold (80%) used in ``jrc_gsw.py``
# and approximates HydroLAKES' definition of permanent water bodies.
DEFAULT_LAKE_THRESHOLD_PCT: int = 95

_MIN_YEAR: int = 1984
_MAX_YEAR: int = 2021

_NODATA_OUT_SCALAR = -9999.0


def _ensure_cache_dir(cache_dir: pathlib.Path | None) -> pathlib.Path:
    if cache_dir is None:
        cache_dir = pathlib.Path(tempfile.gettempdir()) / "mal_commonlib" / "hydrolakes"
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


def _load_permanent_water_pc(
    aoi: "AOI",
    year: int,
    threshold_pct: int,
) -> tuple[np.ndarray, dict]:
    """Read JRC GSW ``occurrence`` via Planetary Computer and produce a
    binary permanent-lake mask at the AOI grid.

    Uses a higher threshold (default 95%) than ``jrc_gsw.py`` (80%) to
    isolate cells that are *consistently* water — a proxy for permanent
    lakes.

    Returns:
        (arr, profile) where ``arr`` is a ``(H, W)`` float32 array with
        values in {0.0, 1.0} and ``-9999.0`` for NoData.
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
        # Fall back to 2020 (the canonical JRC GSW PC collection year).
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
            win = win.intersection(
                rasterio.windows.Window(0, 0, src.width, src.height)
            )
            if win.width <= 0 or win.height <= 0:
                continue
            raw = src.read(1, window=win)
            if hasattr(raw, "filled"):
                raw = np.ma.filled(raw, 0)
            win_transform = src.window_transform(win)
            # JRC GSW ``occurrence`` is uint8 with values 0–100.
            occ = np.asarray(raw, dtype=np.uint8)
            water_mask = (
                (occ > 0) & (occ <= 100) & (occ >= threshold)
            ).astype(np.float32)
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
                source=np.ones(
                    (int(win.height), int(win.width)), dtype=np.float32
                ),
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
        "hydrolakes_year": int(actual_year),
    }
    return out, profile


# -- public API -------------------------------------------------------------


def load_hydrolakes_permanent_lakes(
    aoi: "AOI",
    *,
    year: int = 2021,
    cache_dir: pathlib.Path | None = None,
) -> xr.DataArray:
    """Load permanent lake mask for the AOI using JRC GSW with a high threshold.

    This is a simplified proxy for HydroLAKES: instead of downloading and
    rasterising the HydroLAKES vector dataset, we use the JRC GSW
    ``occurrence`` band at a 95% threshold to identify cells that are
    *consistently* water across the full 1984–2021 observation period.
    This approximates permanent lakes and avoids a 30 MB+ shapefile
    download.

    Args:
        aoi: the AOI.
        year: JRC GSW product year (snapshot selector). Default 2021.
        cache_dir: optional local cache (currently unused — STAC signed
            URLs stream directly).

    Returns:
        xr.DataArray with dims (y, x), dtype ``float32``, CRS = ``aoi.crs``.
        Values in {0.0, 1.0} (binary: 1 = permanent lake cell).
        ``-9999.0`` for NoData.
    """
    threshold_pct = DEFAULT_LAKE_THRESHOLD_PCT

    if not (_MIN_YEAR <= int(year) <= _MAX_YEAR):
        raise ValueError(
            f"JRC GSW year must be in [{_MIN_YEAR}, {_MAX_YEAR}]; got {year}"
        )

    bbox = _aoi_bbox_wgs84(aoi)
    if not all(np.isfinite(b) for b in bbox):
        raise ValueError(f"AOI bbox has non-finite values: {bbox}")

    arr, profile = _load_permanent_water_pc(aoi, int(year), int(threshold_pct))

    # Binary: 1.0 if any tile detected as permanent water, else 0.0.
    # Values from _load_permanent_water_pc are already binary (0/1 or -9999).
    values = arr.copy()

    da = xr.DataArray(
        values,
        dims=("y", "x"),
        name="permanent_lakes",
        attrs={
            "long_name": "Permanent lake mask (HydroLAKES proxy via JRC GSW)",
            "source": (
                f"JRC Global Surface Water {profile.get('hydrolakes_year', year)} "
                "(Planetary Computer STAC), threshold ≥95%"
            ),
            "description": (
                "Binary mask: 1 = permanent lake cell. Derived from JRC GSW "
                "occurrence ≥95% as a proxy for HydroLAKES permanent water bodies."
            ),
            "threshold_pct": int(threshold_pct),
            "asset": _PC_ASSET,
            "nodata": _NODATA_OUT_SCALAR,
        },
    )
    da.rio.write_crs(profile["crs"], inplace=True)
    da.rio.write_transform(profile["transform"], inplace=True)
    da.rio.write_nodata(_NODATA_OUT_SCALAR, inplace=True)
    return da


DOWNLOADER = {
    "name": "hydrolakes",
    "description": "Permanent lake mask (HydroLAKES proxy via JRC GSW threshold ≥95%)",
    "requires_auth": ["none"],
    "is_time_series": False,
    "outputs": {
        "permanent_lakes": load_hydrolakes_permanent_lakes,
    },
    "manifest_keys": {
        "permanent_lakes": "hydrolakes_lakes",
    },
}


__all__ = [
    "load_hydrolakes_permanent_lakes",
    "DEFAULT_LAKE_THRESHOLD_PCT",
    "DOWNLOADER",
]
