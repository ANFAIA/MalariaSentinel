"""Wildlife host proxy loader (raster-based, no GBIF dependency).

Public surface
--------------
``WildlifeLoader.load(aoi, *, year=2021, cache_dir=None) -> xr.DataArray``

Estimates spatial suitability for non-human, non-livestock blood hosts
(antelopes, rodents, other wild mammals) as a ``[0, 1]`` score derived
from three existing data layers:

    wildlife_host_proxy = (
        0.5 * habitat_suitability   # ESA WorldCover class mapping
      + 0.3 * water_proximity       # JRC GSW occurrence
      + 0.2 * remoteness            # inverse of building density
    )

Sources:
    * **ESA WorldCover 10 m** — class codes mapped to habitat suitability.
    * **JRC GSW 30 m** — occurrence band, normalized (saturates at ~33%).
    * **Overture Maps buildings** — building fraction inverted to remoteness.

The loader is resilient to missing data: if WorldCover or JRC GSW fail
to load, the corresponding component defaults to 0.5 (neutral). If
buildings fail, remoteness defaults to 1.0 (assume remote).

Output contract (per ``docs/abm-output-contract.md``):
    * dims (y, x), dtype ``float32``
    * CRS = ``aoi.crs``
    * values in [0, 1]
    * NoData: ``-9999.0``
"""
from __future__ import annotations

import logging
import pathlib
import tempfile

import numpy as np
import rasterio
import rioxarray  # noqa: F401
import xarray as xr
from rasterio.transform import from_bounds
from rasterio.warp import Resampling

from mal_commonlib.aoi import AOI

log = logging.getLogger(__name__)

# -- ESA WorldCover class → habitat suitability mapping -------------------

HABITAT_SUITABILITY: dict[int, float] = {
    10: 0.9,   # Tree cover
    20: 0.7,   # Shrub cover
    30: 0.6,   # Grassland
    40: 0.3,   # Cropland
    50: 0.05,  # Built-up
    60: 0.2,   # Bare / sparse vegetation
    80: 0.0,   # Permanent water bodies
    90: 0.4,   # Herbaceous wetland
    95: 0.5,   # Mangroves
    100: 0.1,  # Moss and lichen
}

# Weight vector for the three components
_W_HABITAT = 0.5
_W_WATER = 0.3
_W_REMOTE = 0.2

# WorldCover STAC catalog (same as worldcover.py)
_PC_STAC_URL = "https://planetarycomputer.microsoft.com/api/stac/v1"
_PC_COLLECTION = "esa-worldcover"
_TILE_DEG = 3
_VERSION_FOR_YEAR: dict[int, str] = {2020: "v100", 2021: "v200"}

_NODATA_OUT_SCALAR = -9999.0


def _ensure_cache_dir(cache_dir: pathlib.Path | None) -> pathlib.Path:
    if cache_dir is None:
        cache_dir = pathlib.Path(tempfile.gettempdir()) / "mal_commonlib" / "wildlife"
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


def _tiles_for_bbox(bbox: tuple[float, float, float, float]) -> list[tuple[int, int]]:
    w, s, e, n = bbox
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


def _make_reference_grid(aoi: AOI) -> xr.DataArray:
    h, w = aoi.cells_per_side()
    wmin, smin, wmax, smax = aoi.bbox
    transform = from_bounds(wmin, smin, wmax, smax, w, h)
    arr = np.zeros((h, w), dtype=np.float32)
    da = xr.DataArray(arr, dims=("y", "x"), name="ref")
    da.rio.write_crs(aoi.crs, inplace=True)
    da.rio.write_transform(transform, inplace=True)
    return da


# -- Planetary Computer WorldCover loader (all classes) ------------------


def _load_worldcover_habitat_pc(
    aoi: AOI,
    year: int,
) -> tuple[np.ndarray, dict]:
    """Read WorldCover via Planetary Computer, map classes to habitat suitability.

    Streams each tile's AOI bbox window directly into the AOI grid.
    Returns (arr, profile) where arr is (H, W) float32 habitat suitability
    in [0, 1], or -9999.0 for NoData.
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
    if not items:
        raise FileNotFoundError(
            f"No WorldCover tiles in Planetary Computer for bbox={bbox} year={year}"
        )
    signed_items = [planetary_computer.sign(item) for item in items]

    H, W = aoi.cells_per_side()
    H, W = int(H), int(W)
    ref_transform = from_bounds(*aoi.bbox, W, H)
    habitat_sum = np.zeros((H, W), dtype=np.float64)
    valid_count = np.zeros((H, W), dtype=np.float64)

    # Build a lookup array indexed by class code for fast vectorised mapping
    max_class = max(HABITAT_SUITABILITY.keys())
    class_lut = np.full(max_class + 1, np.nan, dtype=np.float32)
    for cls, score in HABITAT_SUITABILITY.items():
        class_lut[cls] = score

    for item in signed_items:
        href = item.assets["map"].href
        with rasterio.open(href) as src:
            win = rio_window_from_bounds(*bbox, src.transform)
            win = win.intersection(rasterio.windows.Window(0, 0, src.width, src.height))
            if win.width <= 0 or win.height <= 0:
                continue
            raw = src.read(1, window=win)
            if hasattr(raw, "filled"):
                raw = np.ma.filled(raw, 0)
            raw_u8 = np.asarray(raw, dtype=np.uint16)
            # Map class codes to suitability; unknown classes → 0
            valid_mask = raw_u8 <= max_class
            suitability = np.where(
                valid_mask,
                np.where(np.isnan(class_lut[raw_u8]), 0.0, class_lut[raw_u8]),
                0.0,
            ).astype(np.float32)

            win_transform = src.window_transform(win)
            tile_habitat = np.zeros((H, W), dtype=np.float32)
            reproject(
                source=suitability,
                destination=tile_habitat,
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
            habitat_sum += tile_habitat
            valid_count += tile_valid

    if not np.any(valid_count > 0):
        return np.full((H, W), _NODATA_OUT_SCALAR, dtype=np.float32), {
            "crs": aoi.crs_obj,
            "transform": ref_transform,
            "height": H,
            "width": W,
        }

    habitat = np.where(
        valid_count > 0,
        habitat_sum / np.maximum(valid_count, 1e-9),
        _NODATA_OUT_SCALAR,
    ).astype(np.float32)
    return habitat, {
        "crs": aoi.crs_obj,
        "transform": ref_transform,
        "height": H,
        "width": W,
    }


# -- Water proximity helper ----------------------------------------------


def _water_proximity(water_frac: np.ndarray) -> np.ndarray:
    """Convert JRC GSW water fraction to water proximity score.

    Formula: min(water_frac * 3, 1.0) — saturates at ~33% water.
    NoData cells (-9999.0) are filled with 0.5 (neutral).
    """
    nodata = water_frac == _NODATA_OUT_SCALAR
    score = np.clip(water_frac * 3.0, 0.0, 1.0)
    score[nodata] = 0.5
    return score.astype(np.float32)


# -- Remoteness helper ---------------------------------------------------


def _remoteness(building_frac: np.ndarray) -> np.ndarray:
    """Convert building fraction to remoteness score.

    Formula: 1.0 - building_fraction. NoData cells are filled with 1.0
    (assume remote).
    """
    nodata = building_frac == _NODATA_OUT_SCALAR
    score = np.clip(1.0 - building_frac, 0.0, 1.0)
    score[nodata] = 1.0
    return score.astype(np.float32)


# -- Public API ----------------------------------------------------------


class WildlifeLoader:
    """Raster-based wildlife host proxy (no GBIF dependency).

    Computes a [0, 1] suitability score from ESA WorldCover habitat
    classes, JRC GSW water proximity, and building remoteness.

    Usage::

        loader = WildlifeLoader()
        proxy = loader.load(aoi)
    """

    def load(
        self,
        aoi: AOI,
        *,
        year: int = 2021,
        cache_dir: pathlib.Path | None = None,
    ) -> xr.DataArray:
        """Load wildlife host proxy for the AOI.

        Args:
            aoi: the AOI (bbox, CRS, resolution_m, slug).
            year: WorldCover product year (2020 or 2021).
            cache_dir: optional local cache for downloaded data.

        Returns:
            xr.DataArray with dims (y, x), dtype float32, CRS = aoi.crs.
            Values in [0, 1]. ``-9999.0`` for NoData.
        """
        _ensure_cache_dir(cache_dir)
        H, W = aoi.cells_per_side()
        H, W = int(H), int(W)

        # --- 1. Habitat suitability from WorldCover ----------------------
        try:
            habitat, profile = _load_worldcover_habitat_pc(aoi, year)
            log.info("WildlifeLoader: WorldCover habitat loaded successfully")
        except Exception as exc:
            log.warning("WildlifeLoader: WorldCover failed (%s), using neutral 0.5", exc)
            habitat = np.full((H, W), 0.5, dtype=np.float32)
            profile = {
                "crs": aoi.crs_obj,
                "transform": from_bounds(*aoi.bbox, W, H),
                "height": H,
                "width": W,
            }

        # --- 2. Water proximity from JRC GSW -----------------------------
        try:
            from mal_commonlib.data.loaders.jrc_gsw import load_jrc_gsw_water_frac

            water_da = load_jrc_gsw_water_frac(aoi, year=year, cache_dir=cache_dir)
            water_frac = water_da.values.astype(np.float32)
            log.info("WildlifeLoader: JRC GSW water loaded successfully")
        except Exception as exc:
            log.warning("WildlifeLoader: JRC GSW failed (%s), using neutral 0.5", exc)
            water_frac = np.full((H, W), 0.5 / 3.0, dtype=np.float32)

        water = _water_proximity(water_frac)

        # --- 3. Remoteness from buildings ---------------------------------
        try:
            from mal_commonlib.data.loaders.buildings import BuildingsLoader

            bld = BuildingsLoader()
            bld_da = bld.load(aoi, cache_dir=cache_dir)
            bld_frac = bld_da.values.astype(np.float32)
            # Replace nodata with 0 (no buildings → remote)
            bld_frac[bld_frac == _NODATA_OUT_SCALAR] = 0.0
            log.info("WildlifeLoader: Buildings loaded successfully")
        except Exception as exc:
            log.warning("WildlifeLoader: Buildings failed (%s), assuming remote", exc)
            bld_frac = np.zeros((H, W), dtype=np.float32)

        remote = _remoteness(bld_frac)

        # --- 4. Compute composite ----------------------------------------
        proxy = _W_HABITAT * habitat + _W_WATER * water + _W_REMOTE * remote
        proxy = np.clip(proxy, 0.0, 1.0).astype(np.float32)

        # Propagate nodata: cells where WorldCover had no data
        nodata_mask = habitat == _NODATA_OUT_SCALAR
        proxy[nodata_mask] = _NODATA_OUT_SCALAR

        # --- 5. Wrap and return -------------------------------------------
        da = xr.DataArray(
            proxy,
            dims=("y", "x"),
            name="wildlife_host_proxy",
            attrs={
                "long_name": "Wildlife host proxy suitability",
                "units": "suitability [0, 1]",
                "source": (
                    f"ESA WorldCover {year} + JRC GSW + Overture Maps buildings"
                ),
                "formula": (
                    "0.5 * habitat_suitability + 0.3 * water_proximity "
                    "+ 0.2 * remoteness"
                ),
                "nodata": _NODATA_OUT_SCALAR,
            },
        )
        da.rio.write_crs(aoi.crs_obj, inplace=True)
        da.rio.write_transform(
            from_bounds(*aoi.bbox, W, H),
            inplace=True,
        )
        da.rio.write_nodata(_NODATA_OUT_SCALAR, inplace=True)
        return da


__all__ = ["WildlifeLoader", "HABITAT_SUITABILITY"]
