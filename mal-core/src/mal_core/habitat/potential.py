"""Static breeding-habitat potential H[i,g] per proxy habitat type.

The only knowledge this module has is the plan-defined mapping from the
contract v3.0 per-cell feature columns to the six H values (plan
docs/plans/in-process/redesign/02-oferta-criaderos-proxies-download-ingest-abm.md
§6.2-§6.4). It is an INDEX: a relative offer potential in [0, 1]; it is not
a measured pool count, depth or water volume, and the plan explicitly
rejects interpreting it as such.

Mapping (per cell i; features are column numpy arrays of the env NC statics):

    P := jrc_persistent          (JRC occurrence >= 80 %, post-coast-filter fraction)
    V := lc_wetland              (ESA WorldCover classes 90 + 95 area fraction)
    U := lc_built                (ESA WorldCover class 50 area fraction)
    O := lc_open_plus_water      (open/low vegetation + bare + water, area fraction)
    C := lc_crop                 (ESA WorldCover class 40 area fraction)

    H_surface_persistent = P
    H_wetland_persistent = V
    H_urban_persistent   = BETA_URBAN * U
    H_wetland_pluvial    = V
    H_open_pluvial       = O
    H_crop_pluvial       = C

Binding rules (plan §6.4 + project rule #167):
* The urban persistent contribution is NOT gated by JRC or rainfall: a cell
  with built cover and zero JRC water keeps a small persistent offer for the
  whole dry season.
* H is clipped to [0, 1]; nan features are treated as 0 (absence of
  land-cover evidence, not a wet signal). NaN counts of valid WorldCover
  pixels are NOT used to rescale here — quality lives in the writer.
* No alpha/theta matrix: the plan dropped the phase-1 linear-weight design;
  if a future weighting needs fitting, it must NOT resurrect the alpha
  matrix without a new user decision.
"""
from __future__ import annotations

from typing import Mapping

import numpy as np

from .constants import BETA_URBAN, FEATURE_COLUMNS, HABITAT_TYPES


def static_potential(
    features: Mapping[str, np.ndarray | float],
) -> dict[str, np.ndarray | float]:
    """Compute the six H[i,g] values from contract v3.0 feature columns.

    Args:
        features: mapping ``feature_column`` -> per-cell array/scalar.
            Missing or non-finite values are treated as 0. Extra keys are
            ignored; missing required keys raise KeyError (the ingest
            builder is contract-strict).

    Returns:
        mapping habitat type -> per-cell H array/scalar clipped [0, 1].
    """
    p = _feature(features, "jrc_persistent")
    v = _feature(features, "lc_wetland")
    u = _feature(features, "lc_built")
    o = _feature(features, "lc_open_plus_water")
    c = _feature(features, "lc_crop")

    out: dict[str, np.ndarray | float] = {
        "surface_persistent": p,
        "wetland_persistent": v,
        "urban_persistent": _clip(BETA_URBAN * u),
        "wetland_pluvial": v,
        "open_pluvial": o,
        "crop_pluvial": c,
    }
    assert set(out) == set(HABITAT_TYPES)
    return out


def total_potential(h: Mapping[str, np.ndarray | float]) -> np.ndarray | float:
    """Sum of the six H values (used as the candidate filter and as the
    oviposition-attraction amplitude). Clipped to [0, 1]."""
    total = None
    for g in HABITAT_TYPES:
        val = _clip(h[g])
        total = val if total is None else total + val
    return _clip(total)


def _feature(
    features: Mapping[str, np.ndarray | float], name: str
) -> np.ndarray | float:
    if name not in features:
        raise KeyError(
            f"missing contract v3.0 feature column '{name}' "
            f"(present: {sorted(features)})"
        )
    return _clip(features[name])


def _clip(x):
    import numpy as _np

    arr = _np.asarray(x, dtype=_np.float64)
    arr = _np.nan_to_num(arr, nan=0.0)
    return _np.clip(arr, 0.0, 1.0)


__all__ = ["static_potential", "total_potential", "FEATURE_COLUMNS"]
