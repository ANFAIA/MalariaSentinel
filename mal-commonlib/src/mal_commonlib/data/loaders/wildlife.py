"""Wildlife host proxy loader (raster-based, no GBIF dependency).

Public surface
--------------
``load_wildlife_host_proxy(aoi, *, year=2021, cache_dir=None) -> xr.DataArray``

Estimates spatial suitability for non-human, non-livestock blood hosts
(antelopes, rodents, other wild mammals) as a ``[0, 1]`` score derived
from three existing data layers: a weighted combination of habitat
suitability, water presence and remoteness. The weights are the module
constants ``_W_HABITAT`` / ``_W_WATER`` / ``_W_REMOTE``; they are pending
migration to ``model_constants.yaml`` (task-07 backlog).

Sources:
    * **Google Dynamic World V1 10 m** — modal-label codes mapped to habitat
      suitability (via ``mal_commonlib.data.loaders.dynamic_world.load_dw_label_mode``).
    * **JRC GSW 30 m** — occurrence band, normalized (saturates at ~33%).
    * **Overture Maps buildings** — building fraction inverted to remoteness.

The loader is resilient to missing data: if Dynamic World or JRC GSW fail
to load, the corresponding component defaults to 0.5 (neutral). If
buildings fail, remoteness defaults to 1.0 (assume remote).

Output contract (per ``docs/abm-output-contract.md``):
    * dims (y, x), dtype ``float32``
    * CRS = ``aoi.crs``
    * values in [0, 1]
    * NoData: ``NODATA_SENTINEL()``
"""
from __future__ import annotations

import logging
import pathlib

import numpy as np
import rioxarray  # noqa: F401
import xarray as xr
from rasterio.transform import from_bounds

from mal_commonlib.aoi import AOI
from mal_commonlib.data.loaders.dynamic_world import load_dw_label_mode
from mal_commonlib.model_constants import model_constant

log = logging.getLogger(__name__)

# -- Dynamic World label → habitat suitability mapping --------------------
#
# WC heritage of each anchor (the table was re-keyed 2026-10-20 when the
# source swapped WorldCover → Dynamic World; values conserve the WC-era
# anchoring so wildlife calibration keeps meaning):
#   DW 1 trees            <- WC 10  tree cover      0.9
#   DW 5 shrub_and_scrub  <- WC 20  shrub cover     0.7
#   DW 2 grass            <- WC 30  grassland       0.6
#   DW 4 crops            <- WC 40  cropland        0.3
#   DW 6 built            <- WC 50  built-up        0.05
#   DW 7 bare             <- WC 60  bare / sparse   0.2
#   DW 0 water            <- WC 80  perm. water     0.0
#   DW 3 flooded_vegetation <- WC 90 (0.4) + WC 95 mangroves (0.5) → midpoint
#   DW 8 snow_and_ice     <- WC 100 moss/lichen     0.1 (out of range for Ghana)

HABITAT_SUITABILITY: dict[int, float] = {
    0: 0.0,    # water
    1: 0.9,    # trees
    2: 0.6,    # grass
    3: 0.45,   # flooded_vegetation (wetland+mangrove midpoint)
    4: 0.3,    # crops
    5: 0.7,    # shrub_and_scrub
    6: 0.05,   # built
    7: 0.2,    # bare
    8: 0.1,    # snow_and_ice (not expected in Ghana)
}

# In-range codes not listed above (defensive) map to 0.0; out-of-range or
# NoData pixels keep NoData in the output rather than a fake 0.
_UNKNOWN_CLASS_SCORE = 0.0
_DW_MIN_LABEL = 0
_DW_MAX_LABEL = 8

# Weight vector for the three components
_W_HABITAT = 0.5
_W_WATER = 0.3
_W_REMOTE = 0.2

_NODATA_OUT_SCALAR = float(model_constant("ingest", "nodata_sentinel"))


# -- Habitat suitability from shared WorldCover loader --------------------


def _load_dw_habitat_pc(
    aoi: AOI,
    year: int,
) -> np.ndarray:
    """Derive habitat suitability from the shared Dynamic World classification.

    ``load_dw_label_mode`` streams each cached EE tile's AOI bbox
    window into the AOI grid with nearest-neighbour resampling and a
    per-year STAC ``datetime`` filter. Because nearest resampling assigns
    each destination cell the same source pixel regardless of whether the
    class→score mapping runs before or after reprojection, mapping the
    reprojected (int32) classification through ``HABITAT_SUITABILITY``
    reproduces the original per-tixel mapping exactly.

    Returns (H, W) float32 habitat suitability in [0, 1], or the NoData sentinel for
    NoData.
    """
    lc = load_dw_label_mode(aoi, year=year)
    lc_vals = lc.values

    # Build a lookup array indexed by label code for fast vectorised mapping.
    class_lut = np.full(_DW_MAX_LABEL + 1, _UNKNOWN_CLASS_SCORE, dtype=np.float32)
    for cls, score in HABITAT_SUITABILITY.items():
        class_lut[cls] = score

    # NoData pixels stay NoData in the output: an unobserved cell is
    # not a zero-suitability cell — downstream treats NoData as neutral.
    nodata = lc_vals == _NODATA_OUT_SCALAR
    valid = (lc_vals >= _DW_MIN_LABEL) & (lc_vals <= _DW_MAX_LABEL)
    habitat = np.full_like(lc_vals, _NODATA_OUT_SCALAR, dtype=np.float32)
    inrange = valid & ~nodata
    habitat[inrange] = class_lut[lc_vals[inrange]]

    return habitat


# -- Water proximity helper ----------------------------------------------


def _water_presence(water_frac: np.ndarray) -> np.ndarray:
    """Convert a JRC water-fraction plane to a within-cell water presence.

    Formula: min(water_frac * 3, 1.0) — 0 → 0.0 (no water pixels in the
    cell), saturating at 1.0 when ~33% of the cell area is water. This is
    *presence/abundance inside the cell*, not spatial proximity: cells
    without water receive no falloff contribution from neighbouring
    cells. Kept under this semantics for output parity with previously
    produced wildlife_proxy layers.

    Contract v3.0 note: the input is now the ``jrc_persistent`` plane of
    ``jrc_habitat_features`` (the >=80%-occurrence fraction — the same
    plane the habitat contract carries). The retired per-year
    ``load_jrc_gsw_water_frac`` is gone.

    NoData cells (configured sentinel) are filled with 0.5 (neutral).
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
        year: Dynamic World composite year (2015 → today).
        cache_dir: optional local cache for downloaded data.

    Returns:
        xr.DataArray with dims (y, x), dtype float32, CRS = aoi.crs.
        Values in [0, 1]. ``NODATA_SENTINEL()`` for NoData.
    """
    if isinstance(aoi, str):
        aoi = AOI.from_slug(aoi)

    H, W = aoi.cells_per_side()
    H, W = int(H), int(W)

    # --- 1. Habitat suitability from Dynamic World --------------------
    try:
        habitat = _load_dw_habitat_pc(aoi, year)
        log.info("wildlife: Dynamic World habitat loaded successfully")
    except Exception as exc:
        log.warning("wildlife: Dynamic World failed (%s), using neutral 0.5", exc)
        habitat = np.full((H, W), 0.5, dtype=np.float32)

    # --- 2. Water proximity from JRC GSW -----------------------------
    try:
        from mal_commonlib.data.loaders.jrc_gsw import (
            load_jrc_gsw_habitat_features,
        )

        jrc = load_jrc_gsw_habitat_features(aoi, cache_dir=cache_dir)
        water_frac = jrc["jrc_persistent"].values.astype(np.float32)
        log.info("wildlife: JRC persistent-water surface loaded successfully")
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
                "weighted combination of habitat_suitability, "
                "water_presence and remoteness (weights: module "
                "constants _W_*, pending model_constants.yaml migration)"
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

__all__ = ["load_wildlife_host_proxy", "HABITAT_SUITABILITY", "DOWNLOADER"]
