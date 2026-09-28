"""Wildlife host proxy loader (raster-based, no GBIF dependency).

Public surface
--------------
``load_wildlife_host_proxy(aoi, *, year=2021, cache_dir=None) -> xr.DataArray``

Estimates spatial suitability for non-human, non-livestock blood hosts
(antelopes, rodents, other wild mammals) as a ``[0, 1]`` score derived
from three existing data layers:

    wildlife_host_proxy = (
        0.5 * habitat_suitability   # ESA WorldCover class mapping
      + 0.3 * water_presence        # JRC GSW occurrence (within-cell)
      + 0.2 * remoteness            # inverse of building density
    )

Sources:
    * **ESA WorldCover 10 m** — class codes mapped to habitat suitability
      (via ``mal_commonlib.data.loaders.worldcover.load_worldcover_landcover``).
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
import warnings

import numpy as np
import rioxarray  # noqa: F401
import xarray as xr
from rasterio.transform import from_bounds

from mal_commonlib.aoi import AOI
from mal_commonlib.data.loaders.worldcover import load_worldcover_landcover

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

# Unknown / unlisted WorldCover class codes (e.g. snow/ice, class 70, or any
# out-of-collection pixel value) map to 0.0 in the direct-pixel mapping of
# the original implementation.
_UNKNOWN_CLASS_SCORE = 0.0

# Weight vector for the three components
_W_HABITAT = 0.5
_W_WATER = 0.3
_W_REMOTE = 0.2

_NODATA_OUT_SCALAR = -9999.0


# -- Habitat suitability from shared WorldCover loader --------------------


def _load_worldcover_habitat_pc(
    aoi: AOI,
    year: int,
) -> np.ndarray:
    """Derive habitat suitability from the shared WorldCover classification.

    ``load_worldcover_landcover`` streams each 3-degree tile's AOI bbox
    window into the AOI grid with nearest-neighbour resampling and a
    per-year STAC ``datetime`` filter. Because nearest resampling assigns
    each destination cell the same source pixel regardless of whether the
    class→score mapping runs before or after reprojection, mapping the
    reprojected (int32) classification through ``HABITAT_SUITABILITY``
    reproduces the original per-tixel mapping exactly.

    Returns (H, W) float32 habitat suitability in [0, 1], or -9999.0 for
    NoData.
    """
    lc = load_worldcover_landcover(aoi, year=year)
    lc_vals = lc.values

    # Build a lookup array indexed by class code for fast vectorised mapping.
    max_class = max(HABITAT_SUITABILITY)
    class_lut = np.full(max_class + 1, _UNKNOWN_CLASS_SCORE, dtype=np.float32)
    for cls, score in HABITAT_SUITABILITY.items():
        class_lut[cls] = score

    habitat = np.full_like(lc_vals, _NODATA_OUT_SCALAR, dtype=np.float32)
    known = (lc_vals >= 0) & (lc_vals <= max_class)
    habitat[known] = class_lut[lc_vals[known]]

    return habitat


# -- Water proximity helper ----------------------------------------------


def _water_presence(water_frac: np.ndarray) -> np.ndarray:
    """Convert JRC GSW water fraction to a within-cell water presence score.

    Formula: min(water_frac * 3, 1.0) — 0 → 0.0 (no water pixels in the
    cell), saturating at 1.0 when ~33% of the cell area is water. This is
    *presence/abundance inside the cell*, not spatial proximity: cells
    without water receive no falloff contribution from neighbouring
    cells. Kept under this semantics for output parity with previously
    produced wildlife_proxy layers.

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


def load_wildlife_host_proxy(
    aoi: AOI | str,
    *,
    year: int = 2021,
    cache_dir: pathlib.Path | None = None,
) -> xr.DataArray:
    """Load wildlife host proxy suitability for the AOI.

    Computes a [0,1] suitability score from ESA WorldCover habitat
    classes, JRC GSW water presence, and building remoteness.

    Args:
        aoi: the AOI (bbox, CRS, resolution_m, slug).
        year: WorldCover product year (2020 or 2021).
        cache_dir: optional local cache for downloaded data.

    Returns:
        xr.DataArray with dims (y, x), dtype float32, CRS = aoi.crs.
        Values in [0, 1]. ``-9999.0`` for NoData.
    """
    if isinstance(aoi, str):
        aoi = AOI.from_slug(aoi)

    H, W = aoi.cells_per_side()
    H, W = int(H), int(W)

    # --- 1. Habitat suitability from WorldCover ----------------------
    try:
        habitat = _load_worldcover_habitat_pc(aoi, year)
        log.info("wildlife: WorldCover habitat loaded successfully")
    except Exception as exc:
        log.warning("wildlife: WorldCover failed (%s), using neutral 0.5", exc)
        habitat = np.full((H, W), 0.5, dtype=np.float32)

    # --- 2. Water proximity from JRC GSW -----------------------------
    try:
        from mal_commonlib.data.loaders.jrc_gsw import load_jrc_gsw_water_frac

        water_da = load_jrc_gsw_water_frac(aoi, year=year, cache_dir=cache_dir)
        water_frac = water_da.values.astype(np.float32)
        log.info("wildlife: JRC GSW water loaded successfully")
    except Exception as exc:
        log.warning("wildlife: JRC GSW failed (%s), using neutral 0.5", exc)
        water_frac = np.full((H, W), 0.5 / 3.0, dtype=np.float32)

    water = _water_presence(water_frac)

    # --- 3. Remoteness from buildings ---------------------------------
    try:
        from mal_commonlib.data.loaders.buildings import load_buildings_fraction

        bld_da = load_buildings_fraction(aoi, cache_dir=cache_dir)
        bld_frac = bld_da.values.astype(np.float32)
        # Replace nodata with 0 (no buildings → remote)
        bld_frac[bld_frac == _NODATA_OUT_SCALAR] = 0.0
        log.info("wildlife: Buildings loaded successfully")
    except Exception as exc:
        log.warning("wildlife: Buildings failed (%s), assuming remote", exc)
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
                "0.5 * habitat_suitability + 0.3 * water_presence "
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


class WildlifeLoader:
    """DEPRECATED: Use load_wildlife_host_proxy() instead."""

    def load(
        self,
        aoi: AOI,
        *,
        year: int = 2021,
        cache_dir: pathlib.Path | None = None,
    ) -> xr.DataArray:
        warnings.warn(
            "WildlifeLoader is deprecated; use load_wildlife_host_proxy()",
            DeprecationWarning,
            stacklevel=2,
        )
        return load_wildlife_host_proxy(aoi, year=year, cache_dir=cache_dir)


DOWNLOADER = {
    "name": "wildlife",
    "description": "Wildlife host proxy suitability from WorldCover + JRC GSW + buildings",
    "requires_auth": ["none"],
    "license": "CC-BY-4.0+ODbL-1.0",
    "attribution": (
        "Derived from ESA WorldCover (CC BY 4.0: © ESA WorldCover project "
        "[2021] / Contains modified Copernicus Sentinel data (2021) "
        "processed by ESA WorldCover consortium), JRC GSW (CC BY 4.0) and "
        "Overture buildings (© OpenStreetMap contributors, Overture Maps "
        "Foundation, ODbL 1.0)."),
    "is_time_series": False,
    "outputs": {
        "wildlife_host_proxy": load_wildlife_host_proxy,
    },
    "manifest_keys": {
        "wildlife_host_proxy": "wildlife_proxy",
    },
}

__all__ = ["load_wildlife_host_proxy", "WildlifeLoader", "HABITAT_SUITABILITY", "DOWNLOADER"]
