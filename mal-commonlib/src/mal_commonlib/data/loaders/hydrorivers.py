"""HydroRIVERS permanent river mask loader (M12 — water dataset).

Public surface
--------------
``load_hydrorivers_permanent_rivers(aoi, *, year=2021, cache_dir=None) -> xr.DataArray``

The ``month`` parameter is accepted for signature uniformity with the other
M1.3a loaders (``build_env`` calls every loader as ``loader(aoi, year, month)``
) but is ignored.

Why this loader exists
----------------------
M12 needs a river-proximity layer to complement the lake and water-fraction
layers. HydroRIVERS (Lehner et al., 2013) is the standard global river-network
dataset, but:

1. Rivers are **thin linear features** (often <30 m wide) that are extremely
   hard to rasterise at the 1 km AOI grid without significant buffering.
2. The full HydroRIVERS vector dataset is >1 GB uncompressed.

Instead, this loader reuses the JRC GSW ``occurrence`` band (via Planetary
Computer STAC) with a **moderate threshold** (≥60%) to identify permanent
river channels. At the 30 m resolution of JRC GSW, narrow permanent rivers
that are consistently detected as water throughout the observation period
(1984–2021) are captured. When reprojected to the 1 km AOI grid, these
appear as a binary river-proximity mask.

The lower threshold (60% vs. the 95% used for lakes) ensures that seasonal
and semi-permanent river channels — which are ecologically important for
malaria larval habitats — are included.

For a more nuanced river-proximity field, the companion
``load_hydrorivers_river_proximity`` function returns a continuous
[0, 1] fractional field that can be used as a weighted input to the
ABM habitat model.

Output contract (per ``docs/abm-output-contract.md`` §2, channel 0):
    * dims (y, x), dtype ``float32``
    * CRS = ``aoi.crs``
    * values in {0.0, 1.0} (binary mask: 1 = permanent river cell)
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

# Microsoft Planetary Computer STAC — same JRC GSW collection.
_PC_STAC_URL = "https://planetarycomputer.microsoft.com/api/stac/v1"
_PC_COLLECTION = "jrc-gsw"
_PC_ASSET = "occurrence"

# Moderate threshold for permanent rivers: ≥60% of observations must
# detect water. This is lower than the lake threshold (95%) because
# rivers have more seasonal variability but are still ecologically
# important permanent/semi-permanent water bodies.
DEFAULT_RIVER_THRESHOLD_PCT: int = 60

_MIN_YEAR: int = 1984
_MAX_YEAR: int = 2021

_NODATA_OUT_SCALAR = -9999.0


def _ensure_cache_dir(cache_dir: pathlib.Path | None) -> pathlib.Path:
    if cache_dir is None:
        cache_dir = pathlib.Path(tempfile.gettempdir()) / "mal_commonlib" / "hydrorivers"
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


def _load_jrc_occurrence_pc(
    aoi: "AOI",
    year: int,
    threshold_pct: int,
    *,
    return_continuous: bool = False,
) -> tuple[np.ndarray, dict]:
    """Read JRC GSW ``occurrence`` via Planetary Computer for the AOI.

    Args:
        aoi: the AOI.
        year: JRC GSW year.
        threshold_pct: binarisation threshold.
        return_continuous: if True, return the continuous [0, 1]
            fraction instead of a binary mask.

    Returns:
        (arr, profile) where ``arr`` is a ``(H, W)`` float32 array with
        values in [0, 1] (binary if ``return_continuous=False``) and
        ``-9999.0`` for NoData.
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
            occ = np.asarray(raw, dtype=np.uint8)

            if return_continuous:
                # Continuous: normalise occurrence [0, 100] → [0, 1].
                water_mask = np.where(
                    (occ > 0) & (occ <= 100),
                    occ.astype(np.float32) / 100.0,
                    np.float32(0),
                )
            else:
                # Binary: permanent river if occurrence ≥ threshold.
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
        "hydrorivers_year": int(actual_year),
    }
    return out, profile


# -- public API -------------------------------------------------------------


def load_hydrorivers_permanent_rivers(
    aoi: "AOI",
    *,
    year: int = 2021,
    cache_dir: pathlib.Path | None = None,
) -> xr.DataArray:
    """Load permanent river mask for the AOI using JRC GSW with moderate threshold.

    This is a simplified proxy for HydroRIVERS: instead of downloading and
    rasterising the HydroRIVERS vector network, we use the JRC GSW
    ``occurrence`` band at a 60% threshold to identify cells with permanent
    or semi-permanent river channels.

    Rivers are thin linear features that are difficult to rasterise at the
    1 km AOI grid from vector data. JRC GSW at 30 m captures these
    channels well in the occurrence band; when reprojected to 1 km, they
    appear as a binary river-proximity mask.

    Args:
        aoi: the AOI.
        year: JRC GSW product year (snapshot selector). Default 2021.
        cache_dir: optional local cache (currently unused).

    Returns:
        xr.DataArray with dims (y, x), dtype ``float32``, CRS = ``aoi.crs``.
        Values in {0.0, 1.0} (binary: 1 = permanent river cell).
        ``-9999.0`` for NoData.
    """
    threshold_pct = DEFAULT_RIVER_THRESHOLD_PCT

    if not (_MIN_YEAR <= int(year) <= _MAX_YEAR):
        raise ValueError(
            f"JRC GSW year must be in [{_MIN_YEAR}, {_MAX_YEAR}]; got {year}"
        )

    bbox = _aoi_bbox_wgs84(aoi)
    if not all(np.isfinite(b) for b in bbox):
        raise ValueError(f"AOI bbox has non-finite values: {bbox}")

    arr, profile = _load_jrc_occurrence_pc(
        aoi, int(year), int(threshold_pct), return_continuous=False
    )

    values = arr.copy()

    da = xr.DataArray(
        values,
        dims=("y", "x"),
        name="permanent_rivers",
        attrs={
            "long_name": "Permanent river mask (HydroRIVERS proxy via JRC GSW)",
            "source": (
                f"JRC Global Surface Water {profile.get('hydrorivers_year', year)} "
                "(Planetary Computer STAC), threshold ≥60%"
            ),
            "description": (
                "Binary mask: 1 = permanent river cell. Derived from JRC GSW "
                "occurrence ≥60% as a proxy for HydroRIVERS permanent river channels."
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


def load_hydrorivers_river_proximity(
    aoi: "AOI",
    *,
    year: int = 2021,
    cache_dir: pathlib.Path | None = None,
) -> xr.DataArray:
    """Load continuous river-proximity field for the AOI using JRC GSW.

    Unlike ``load_hydrorivers_permanent_rivers`` (which returns a binary
    mask), this function returns a continuous [0, 1] field where each cell
    value is the normalised JRC GSW occurrence fraction. This can be used
    as a weighted river-proximity input to the ABM habitat model.

    Cells with high occurrence values (close to 1.0) are in or very near
    permanent water channels; cells with low values (close to 0.0) are
    dry land far from rivers.

    Args:
        aoi: the AOI.
        year: JRC GSW product year. Default 2021.
        cache_dir: optional local cache (currently unused).

    Returns:
        xr.DataArray with dims (y, x), dtype ``float32``, CRS = ``aoi.crs``.
        Values in [0, 1]. ``-9999.0`` for NoData.
    """
    if not (_MIN_YEAR <= int(year) <= _MAX_YEAR):
        raise ValueError(
            f"JRC GSW year must be in [{_MIN_YEAR}, {_MAX_YEAR}]; got {year}"
        )

    bbox = _aoi_bbox_wgs84(aoi)
    if not all(np.isfinite(b) for b in bbox):
        raise ValueError(f"AOI bbox has non-finite values: {bbox}")

    arr, profile = _load_jrc_occurrence_pc(
        aoi, int(year), threshold_pct=0, return_continuous=True
    )

    values = np.clip(arr, 0.0, 1.0).astype(np.float32)
    values = np.where(values < 0, _NODATA_OUT_SCALAR, values)

    da = xr.DataArray(
        values,
        dims=("y", "x"),
        name="river_proximity",
        attrs={
            "long_name": "River proximity field (JRC GSW occurrence fraction)",
            "source": (
                f"JRC Global Surface Water {profile.get('hydrorivers_year', year)} "
                "(Planetary Computer STAC)"
            ),
            "description": (
                "Continuous [0, 1] field: normalised JRC GSW occurrence. "
                "Higher values indicate cells with more persistent water "
                "(i.e., closer to permanent river channels)."
            ),
            "asset": _PC_ASSET,
            "nodata": _NODATA_OUT_SCALAR,
        },
    )
    da.rio.write_crs(profile["crs"], inplace=True)
    da.rio.write_transform(profile["transform"], inplace=True)
    da.rio.write_nodata(_NODATA_OUT_SCALAR, inplace=True)
    return da


DOWNLOADER = {
    "name": "hydrorivers",
    "description": "Permanent river mask and proximity field (HydroRIVERS proxy via JRC GSW)",
    "requires_auth": ["none"],
    "is_time_series": False,
    "outputs": {
        "permanent_rivers": load_hydrorivers_permanent_rivers,
        "river_proximity": load_hydrorivers_river_proximity,
    },
    "manifest_keys": {
        "permanent_rivers": "hydrorivers_rivers",
        "river_proximity": "hydrorivers_proximity",
    },
}


__all__ = [
    "load_hydrorivers_permanent_rivers",
    "load_hydrorivers_river_proximity",
    "DEFAULT_RIVER_THRESHOLD_PCT",
    "DOWNLOADER",
]
