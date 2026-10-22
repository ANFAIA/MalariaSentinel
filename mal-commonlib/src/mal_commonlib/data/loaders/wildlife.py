"""Wildlife host proxy loader (raster-based, no GBIF dependency).

Public surface
--------------
``load_wildlife_host_proxy(aoi, *, year=2021, cache_dir=None) -> xr.DataArray``

Estimates spatial suitability for non-human, non-livestock blood hosts
(antelopes, rodents, other wild mammals) as a ``[0, 1]`` score derived
from three existing data layers: a weighted combination of habitat
suitability, water presence and remoteness. The per-class suitability
table and the component weights are model parameters read from
``model_constants.yaml`` (section ``wildlife``) through the read-only
accessor; schema/invariant validation stays in ``mal_core`` (R2).

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
from mal_commonlib.data.loaders.dynamic_world import (
    DW_LABEL_NAMES,
    load_dw_label_mode,
)
from mal_commonlib.model_constants import model_constant

log = logging.getLogger(__name__)


def _class_suitability() -> dict[int, float]:
    """Map DW label code → habitat suitability, read from the YAML.

    The code→name mapping is ``dynamic_world.DW_LABEL_NAMES``: source
    identity, not a calibrated parameter. Values live in
    ``wildlife.class_suitability``.
    """
    scores = model_constant("wildlife", "class_suitability")
    return {code: float(scores[name]) for code, name in DW_LABEL_NAMES.items()}


def _component_weights() -> dict[str, float]:
    """Component weights of the linear combination, read from the YAML."""
    weights = model_constant("wildlife", "weights")
    return {name: float(value) for name, value in weights.items()}


# Import-time snapshot of the class table for external readers (tests,
# notebooks). The product path re-reads ``wildlife.class_suitability`` on
# every call so a config change is observable without re-importing.
HABITAT_SUITABILITY: dict[int, float] = _class_suitability()

# In-range codes not listed above (defensive) map to 0.0; out-of-range or
# NoData pixels keep NoData in the output rather than a fake 0.
_UNKNOWN_CLASS_SCORE = 0.0
_DW_MIN_LABEL = 0
_DW_MAX_LABEL = 8

_NODATA_OUT_SCALAR = float(model_constant("ingest", "nodata_sentinel"))


# -- Habitat suitability from shared WorldCover loader --------------------


def _load_dw_habitat_pc(
    aoi: AOI,
    year: int,
    *,
    suitability: dict[int, float] | None = None,
) -> np.ndarray:
    """Derive habitat suitability from the shared Dynamic World classification.

    ``load_dw_label_mode`` streams each cached EE tile's AOI bbox
    window into the AOI grid with nearest-neighbour resampling and a
    per-year STAC ``datetime`` filter. Because nearest resampling assigns
    each destination cell the same source pixel regardless of whether the
    class→score mapping runs before or after reprojection, mapping the
    reprojected (int32) classification through the YAML class table
    reproduces the original per-tixel mapping exactly.

    Returns (H, W) float32 habitat suitability in [0, 1], or the NoData sentinel for
    NoData.
    """
    lc = load_dw_label_mode(aoi, year=year)
    lc_vals = lc.values

    # Build a lookup array indexed by label code for fast vectorised mapping.
    table = _class_suitability() if suitability is None else suitability
    class_lut = np.full(_DW_MAX_LABEL + 1, _UNKNOWN_CLASS_SCORE, dtype=np.float32)
    for cls, score in table.items():
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

    # Model parameters are read before any I/O: a missing/invalid key must be
    # a loud error, never a silently neutral component.
    suitability = _class_suitability()
    weights = _component_weights()

    H, W = aoi.cells_per_side()
    H, W = int(H), int(W)

    # --- 1. Habitat suitability from Dynamic World --------------------
    try:
        habitat = _load_dw_habitat_pc(aoi, year, suitability=suitability)
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
    proxy = (weights["habitat"] * habitat
             + weights["water"] * water
             + weights["remoteness"] * remote)
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
                "water_presence and remoteness (weights from "
                "model_constants.yaml wildlife.weights)"
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
