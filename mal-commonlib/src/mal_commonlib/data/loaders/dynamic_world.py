"""Google Dynamic World V1 land-cover loader (contract v3.0 source).

Replaces the ESA WorldCover source (2020/2021 only, retired with commit
history) with Dynamic World V1 on Google Earth Engine:

    ImageCollection: GOOGLE/DYNAMICWORLD/V1  (Brown et al. 2022, Sci Data)
    Coverage:        global, 2015-06-27 → today, ~2-5 day cadence (Sentinel-2)
    License:         CC BY 4.0; contains modified Copernicus Sentinel data

Contract v3.0 consumes ONE static plane per feature column. The agreed
composition (user decision 2026-10-17, option A) is a per-YEAR modal label
composite:

    for each run year Y:
        label[i,j] = mode of DW "label" over all S2 passes in Y
        (cloudy passes contribute transient labels that lose the vote)
    then within each 1 km AOI cell, the AREAL FRACTION of pixels whose modal
    label belongs to each feature column — the exact same semantics the
    WorldCover loader had (areal fraction of a hard label), so the H mapping,
    the C++ mirror and every calibration constant keep their meaning.
    When the run spans several years, the per-year fraction planes are
    averaged (mean of fractions) into a single plane.

Dynamic World label codes (9 classes):
    0 water  1 trees  2 grass  3 flooded_vegetation  4 crops
    5 shrub_and_scrub  6 built  7 bare  8 snow_and_ice

Earth Engine auth: OAuth interactive (user decision 2026-10-17). The loader
calls ``ee.Initialize(project=EE_PROJECT_ID)``; without stored credentials
(~/.config/earthengine/credentials) it raises with the one-line fix:
``earthengine authenticate --project=EE_PROJECT_ID``.
"""
from __future__ import annotations

import io
import json
import logging
import math
from pathlib import Path
from typing import TYPE_CHECKING, Iterable, Sequence

import numpy as np
import rasterio
import rioxarray  # noqa: F401 — registers the .rio accessor
import xarray as xr
from rasterio.transform import from_bounds
from rasterio.warp import Resampling, reproject

from mal_commonlib.model_constants import model_constant

if TYPE_CHECKING:
    from mal_commonlib.aoi import AOI

log = logging.getLogger(__name__)

# Earth Engine project registered for Earth Engine access (user-provided).
EE_PROJECT_ID = "psyched-signal-437808-a7"

_EE_COLLECTION = "GOOGLE/DYNAMICWORLD/V1"

# Native request scale for the modal-label raster. Dynamic World is 10 m;
# 100 m sampling is 100x cheaper and the 1 km aggregation smooths it anyway.
_REQUEST_SCALE_M = 100.0

# Max pixels per getDownloadURL request side (EE caps GeoTIFF exports;
# stay well under). At 100 m, 2000 px = 200 km tiles.
_TILE_MAX_PX = 2000

# --- Dynamic World label codes -------------------------------------------
DW_WATER = 0
DW_TREES = 1
DW_GRASS = 2
DW_FLOODED_VEGETATION = 3
DW_CROPS = 4
DW_SHRUB_SCRUB = 5
DW_BUILT = 6
DW_BARE = 7
DW_SNOW_ICE = 8

DW_LABEL_NAMES: dict[int, str] = {
    DW_WATER: "water",
    DW_TREES: "trees",
    DW_GRASS: "grass",
    DW_FLOODED_VEGETATION: "flooded_vegetation",
    DW_CROPS: "crops",
    DW_SHRUB_SCRUB: "shrub_and_scrub",
    DW_BUILT: "built",
    DW_BARE: "bare",
    DW_SNOW_ICE: "snow_and_ice",
}

# Contract feature-class mapping (same areal-fraction semantics as the
# retired WorldCover FEATURE_CLASSES):
#   built   <- DW built (was WC 50)
#   wetland <- DW flooded_vegetation (was WC 90 + 95)
#   crop    <- DW crops (was WC 40)
#   open_plus_water <- grass + shrub + bare + water (was WC 20/30/60/100/80)
FEATURE_CLASSES: dict[str, tuple[int, ...]] = {
    "lc_built": (DW_BUILT,),
    "lc_wetland": (DW_FLOODED_VEGETATION,),
    "lc_crop": (DW_CROPS,),
    "lc_open_plus_water": (DW_GRASS, DW_SHRUB_SCRUB, DW_BARE, DW_WATER),
}
FEATURE_NAMES: tuple[str, ...] = tuple(FEATURE_CLASSES)

MIN_YEAR: int = 2015  # DW record starts 2015-06-27

# NoData sentinel shared with the engine: model_constants.yaml: ingest.*
# (read-only accessor; validation lives in mal-core, R2).
NODATA_OUT = float(model_constant("ingest", "nodata_sentinel"))
NODATA_OUT_INT = int(model_constant("ingest", "nodata_sentinel_int"))

ATTRIBUTION = (
    "Dynamic World V1 (Brown et al. 2022, doi:10.1038/s41597-022-01307-4) "
    "© Google, CC BY 4.0; contains modified Copernicus Sentinel data [Year]."
)


def _ensure_ee():
    """Import and initialize Earth Engine (OAuth credentials on this machine).

    Raises a RuntimeError with the fix when no stored credentials exist —
    the loader never triggers the interactive browser flow silently.
    """
    import ee
    from ee import oauth as _ee_oauth

    # nono sandbox gotcha: ee/oauth.get_appdefault_project probes
    # ~/.config/gcloud/application_default_credentials.json for an optional
    # quota_project_id and only catches FileNotFoundError; under the sandbox
    # the open() raises PermissionError (the dir is in the required
    # deny_credentials group) and ee.Initialize hard-crashes even though the
    # earthengine credentials file is readable. Shim: treat any OSError as
    # "no quota project" — the EE refresh token carries no project anyway.
    if not getattr(_ee_oauth, "_nono_safe_appdefault", False):
        _orig = _ee_oauth.get_appdefault_project

        def _safe_appdefault_project() -> str | None:
            try:
                return _orig()
            except OSError:
                return None

        _safe_appdefault_project.__nono_patched__ = True  # type: ignore[attr-defined]
        _ee_oauth.get_appdefault_project = _safe_appdefault_project
        _ee_oauth._nono_safe_appdefault = True  # type: ignore[attr-defined]

    try:
        ee.Initialize(project=EE_PROJECT_ID)
    except Exception as exc:  # ee.EEException: not registered / no creds
        raise RuntimeError(
            "Earth Engine is not authenticated for project "
            f"{EE_PROJECT_ID!r}. Fix once in any terminal:\n"
            f"    earthengine authenticate\n"
            "(or: python -c \"import ee; ee.Authenticate()\") — the stored "
            "OAuth token is then reused non-interactively. "
            f"Original error: {exc}"
        ) from exc
    return ee


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


def _ensure_cache_dir(cache_dir: Path | None) -> Path:
    base = Path(cache_dir) if cache_dir is not None else (
        Path.home() / ".cache" / "mal_commonlib" / "dynamic_world"
    )
    base.mkdir(parents=True, exist_ok=True)
    return base


def _tile_bounds(
    bbox: tuple[float, float, float, float],
    scale_m: float,
    max_px: int = _TILE_MAX_PX,
) -> list[tuple[float, float, float, float]]:
    """Split a WGS-84 bbox into (w, s, e, n) tiles of <= max_px * scale m.

    Uses a degree approximation for the tile span (constant per latitude
    span is not needed for cache-keying or EE limits).
    """
    w, s, e, n = bbox
    span_deg = (scale_m * max_px) / 111_320.0
    nx = max(1, math.ceil((e - w) / span_deg))
    ny = max(1, math.ceil((n - s) / span_deg))
    dx = (e - w) / nx
    dy = (n - s) / ny
    tiles: list[tuple[float, float, float, float]] = []
    for j in range(ny):
        for i in range(nx):
            tiles.append(
                (w + i * dx, s + j * dy, w + (i + 1) * dx, s + (j + 1) * dy)
            )
    return tiles


def _year_mode_label_tifs(
    year: int,
    bbox: tuple[float, float, float, float],
    cache_dir: Path,
) -> list[Path]:
    """Download (and cache) the per-year modal-label GeoTIFF tiles.

    Returns the tile file paths in row-major order matching _tile_bounds.
    """
    import requests

    ee = _ensure_ee()
    region = ee.Geometry.Rectangle([bbox[0], bbox[1], bbox[2], bbox[3]])

    tiles = _tile_bounds(bbox, _REQUEST_SCALE_M)
    paths: list[Path] = []
    for idx, (tw, ts, te, tn) in enumerate(tiles):
        key = (
            f"dw_label_mode_{year}_"
            f"{tw:.3f}_{ts:.3f}_{te:.3f}_{tn:.3f}.tif"
        )
        path = cache_dir / key
        paths.append(path)
        if path.exists() and path.stat().st_size > 0:
            continue

        coll = (
            ee.ImageCollection(_EE_COLLECTION)
            .filterBounds(region)
            .filterDate(f"{year}-01-01", f"{year + 1}-01-01")
            .select("label")
        )
        n_img = coll.size().getInfo()
        if n_img == 0:
            raise FileNotFoundError(
                f"No Dynamic World images for year={year} bbox={bbox}"
            )
        mode_img = coll.mode()
        url = mode_img.getDownloadURL(
            {
                "scale": _REQUEST_SCALE_M,
                "crs": "EPSG:4326",
                "region": ee.Geometry.Rectangle([tw, ts, te, tn]),
                "format": "GEO_TIFF",
            }
        )
        resp = requests.get(url, timeout=600)
        resp.raise_for_status()
        path.write_bytes(resp.content)
        log.info(
            "dynamic_world: cached %s (%d imgs, tile %d/%d)",
            path.name, n_img, idx + 1, len(tiles),
        )
    return paths


def _read_tile(path: Path) -> tuple[np.ndarray, rasterio.Affine, object]:
    with rasterio.open(path) as src:
        arr = src.read(1)
        if hasattr(arr, "filled"):
            arr = np.ma.filled(arr, arr.dtype.type(0))
        return arr, src.transform, src.crs


def _year_fraction_planes(
    year: int,
    bbox: tuple[float, float, float, float],
    ref_transform: rasterio.Affine,
    dst_crs: object,
    shape: tuple[int, int],
    cache_dir: Path,
) -> tuple[dict[str, np.ndarray], np.ndarray]:
    """Per-year areal-fraction planes on the AOI grid from cached tiles."""
    H, W = shape
    feed_names = sorted(
        {c for classes in FEATURE_CLASSES.values() for c in classes}
    )
    class_sums: dict[int, np.ndarray] = {
        c: np.zeros((H, W), dtype=np.float32) for c in feed_names
    }
    valid_count = np.zeros((H, W), dtype=np.float32)

    for path in _year_mode_label_tifs(year, bbox, cache_dir):
        raw, win_transform, src_crs = _read_tile(path)
        h, w = raw.shape
        tile_valid = np.zeros((H, W), dtype=np.float32)
        reproject(
            source=np.ones((h, w), dtype=np.float32),
            destination=tile_valid,
            src_transform=win_transform,
            src_crs=src_crs,
            dst_transform=ref_transform,
            dst_crs=dst_crs,
            resampling=Resampling.average,
        )
        for class_code in feed_names:
            class_layer = (raw == class_code).astype(np.float32)
            tile_frac = np.zeros((H, W), dtype=np.float32)
            reproject(
                source=class_layer,
                destination=tile_frac,
                src_transform=win_transform,
                src_crs=src_crs,
                dst_transform=ref_transform,
                dst_crs=dst_crs,
                resampling=Resampling.average,
            )
            class_sums[class_code] += tile_frac
        valid_count += tile_valid

    data: dict[str, np.ndarray] = {}
    for feature in FEATURE_NAMES:
        acc = np.zeros((H, W), dtype=np.float32)
        for class_code in FEATURE_CLASSES[feature]:
            acc = acc + class_sums[class_code]
        frac = np.where(
            valid_count > 0,
            acc / np.maximum(valid_count, 1e-9),
            NODATA_OUT,
        ).astype(np.float32)
        frac = np.clip(np.where(frac == NODATA_OUT, frac, frac.clip(0.0, 1.0)),
                       0.0, 1.0)
        frac[valid_count <= 0] = NODATA_OUT
        data[feature] = frac
    return data, valid_count


def load_dw_class_fractions(
    aoi: "AOI",
    *,
    years: Sequence[int],
    months: Sequence[int] | None = None,  # runner kwarg; ignored (annual mode)
    cache_dir: Path | None = None,
) -> xr.Dataset:
    """Per-year Dynamic World modal-label fractions on the AOI grid.

    Args:
        aoi: the AOI.
        years: run years to composite (one modal-label composite each).
            The returned dataset has a ``time`` dim with one frame per year
            (Jan 1 of that year); the ingest averages the frames into the
            single static plane of the contract.
        cache_dir: local cache root for the modal-label tiles (default
            ``~/.cache/mal_commonlib/dynamic_world``).

    Returns:
        ``xr.Dataset`` dims (time, y, x) with variables ``lc_built``,
        ``lc_wetland``, ``lc_crop``, ``lc_open_plus_water`` (float32,
        [0,1], ``ingest.nodata_sentinel`` NoData), CRS = aoi.crs.
    """
    if not years:
        raise ValueError("load_dw_class_fractions needs at least one year")
    if min(years) < MIN_YEAR:
        raise ValueError(
            f"Dynamic World record starts {MIN_YEAR}-06-27; got {min(years)}"
        )

    bbox = _aoi_bbox_wgs84(aoi)
    if not all(np.isfinite(b) for b in bbox):
        raise ValueError(f"AOI bbox has non-finite values: {bbox}")

    cache = _ensure_cache_dir(cache_dir)
    H, W = aoi.cells_per_side()
    ref_transform = from_bounds(*aoi.bbox, int(W), int(H))

    frames: list[xr.Dataset] = []
    for year in sorted(set(int(y) for y in years)):
        data, _ = _year_fraction_planes(
            year, bbox, ref_transform, aoi.crs_obj, (int(H), int(W)), cache
        )
        ds = xr.Dataset(
            {name: xr.DataArray(arr, dims=("y", "x"), name=name)
             for name, arr in data.items()},
            attrs={
                "contract": "habitat-v3.0-statics",
                "source": f"Dynamic World V1 modal label, year {year} (GEE)",
                "resolution_m": _REQUEST_SCALE_M,
                # netCDF attrs cannot hold dicts — serialize as JSON.
                "class_map": json.dumps(
                    {k: list(v) for k, v in FEATURE_CLASSES.items()}
                ),
                "attribution": ATTRIBUTION.replace("[Year]", str(year)),
                "nodata": NODATA_OUT,
            },
        )
        ds = ds.assign_coords(time=np.datetime64(f"{year}-01-01", "D"))
        ds.rio.write_crs(aoi.crs_obj, inplace=True)
        ds.rio.write_transform(
            from_bounds(*aoi.bbox, *aoi.cells_per_side()), inplace=True
        )
        for name in data:
            ds[name].rio.write_nodata(NODATA_OUT, inplace=True)
        frames.append(ds)

    out = xr.concat(frames, dim="time")
    out.attrs.update(frames[0].attrs)
    out.attrs["source"] = (
        "Dynamic World V1 modal label per year, averaged over "
        f"{[int(y) for y in sorted(set(int(y) for y in years))]} (GEE)"
    )
    return out


def load_dw_label_mode(
    aoi: "AOI",
    *,
    year: int,
    cache_dir: Path | None = None,
) -> xr.DataArray:
    """Dominant-class Dynamic World raster on the AOI grid (shared utility).

    Same role the retired ``load_worldcover_landcover`` had for independent
    consumers (the wildlife host proxy loader maps the label raster through
    a suitability table). NOT part of the habitat contract — the habitat
    ingest consumes ``load_dw_class_fractions`` only.

    Returns:
        xr.DataArray dims (y, x), dtype int32, CRS = aoi.crs, values are
        Dynamic World label codes 0-8. ``ingest.nodata_sentinel_int`` NoData.
    """
    bbox = _aoi_bbox_wgs84(aoi)
    if not all(np.isfinite(b) for b in bbox):
        raise ValueError(f"AOI bbox has non-finite values: {bbox}")

    cache = _ensure_cache_dir(cache_dir)
    H, W = aoi.cells_per_side()
    ref_transform = from_bounds(*aoi.bbox, int(W), int(H))

    vote = np.full((H, W), -1, dtype=np.int32)
    votes_acc = np.zeros((H, W, 9), dtype=np.float32)
    valid = np.zeros((H, W), dtype=np.float32)
    for path in _year_mode_label_tifs(year, bbox, cache):
        raw, win_transform, src_crs = _read_tile(path)
        h, w = raw.shape
        tile_valid = np.zeros((H, W), dtype=np.float32)
        reproject(
            source=np.ones((h, w), dtype=np.float32),
            destination=tile_valid,
            src_transform=win_transform,
            src_crs=src_crs,
            dst_transform=ref_transform,
            dst_crs=aoi.crs_obj,
            resampling=Resampling.nearest,
        )
        for code in range(9):
            layer = (raw == code).astype(np.float32)
            plane = np.zeros((H, W), dtype=np.float32)
            reproject(
                source=layer,
                destination=plane,
                src_transform=win_transform,
                src_crs=src_crs,
                dst_transform=ref_transform,
                dst_crs=aoi.crs_obj,
                resampling=Resampling.average,
            )
            votes_acc[:, :, code] = np.maximum(
                votes_acc[:, :, code], plane * (tile_valid > 0)
            )
        valid = np.maximum(valid, tile_valid)

    covered = valid > 0
    if covered.any():
        vote[covered] = np.argmax(votes_acc[covered], axis=-1).astype(np.int32)
    vote[~covered] = NODATA_OUT_INT

    da = xr.DataArray(vote, dims=("y", "x"), name="label")
    da.rio.write_crs(aoi.crs_obj, inplace=True)
    da.rio.write_transform(
        from_bounds(*aoi.bbox, *aoi.cells_per_side()), inplace=True
    )
    da.rio.write_nodata(NODATA_OUT_INT, inplace=True)
    da.attrs["source"] = f"Dynamic World V1 modal label {year} (GEE)"
    da.attrs["attribution"] = ATTRIBUTION.replace("[Year]", str(year))
    return da


DOWNLOADER = {
    "name": "dynamic_world",
    "description": "Google Dynamic World V1: 10 m land cover (modal label per year, 2015→today, Earth Engine)",
    "requires_auth": ["earthengine"],
    "is_time_series": True,
    "formats": {"class_fractions": "daily"},  # "daily" = the runner's multi-year-NC writer path
    "license": "CC-BY-4.0",
    "attribution": ATTRIBUTION,
    "outputs": {
        "class_fractions": load_dw_class_fractions,
    },
    "manifest_keys": {
        "class_fractions": "dw_class_fractions",
    },
    "required_for_abm": {"class_fractions": True},
}


__all__ = [
    "load_dw_class_fractions",
    "load_dw_label_mode",
    "FEATURE_CLASSES",
    "FEATURE_NAMES",
    "DW_LABEL_NAMES",
    "EE_PROJECT_ID",
    "NODATA_OUT",
    "DOWNLOADER",
]