"""proxy_habitat_v1 — static breeding-habitat offer + two shared temporal responses.

Canonical model of the pool-hydrology redesign (plan
docs/plans/in-process/redesign/02-oferta-criaderos-proxies-download-ingest-abm.md,
contract v3.0). Combination formulas for the ABM daily capacity:

    S[i,s,t]  = clip(sum_g w[s,g] * H[i,g] * A[i,k(g),t], 0, 1)
    K[i,s,t]  = K_ref[s] * cell_area_km2[i] * S[i,s,t]

Submodules
----------
* ``potential``      — static potential H[i,g] per habitat type from the
  manifest contract v3.0 per-cell feature columns.
* ``availability``   — shared temporal responses A[i,k,t] (persistent = 1,
  pluvial = exponential drying memory + rain recharge), including the
  causal warm-up.
* ``capacity``       — species-indexed capacity S[i,s,t] and Beverton-Holt
  scale K[i,s,t].
* ``aquatic_stress`` — biologically preserved end-mechanisms that act on
  aquatic cohorts (desiccation ramp, heavy-rain washout), mirroring the
  C++ ``mal_abm_fast/aquatic_stress.hpp``.
* ``constants``      — the single value contract (thresholds, scales, names).

These modules are pure python (numpy). The C++ engine re-implements the
same constants verbatim; the parity is enforced by unit tests unit-by-unit
in ``mal-core/tests/test_habitat_*.py`` against the Python reference.
"""
from __future__ import annotations

from .constants import (  # noqa: F401 — re-export the value contract
    ACTIVATION_MIN,
    BETA_URBAN,
    DEFAULT_SPECIES,
    DESICCATION_GRACE_DAYS,
    DESICC_BASE_DAILY,
    DRY_MEMORY_DAYS,
    HABITAT_CANDIDATE_MIN,
    HABITAT_DYNAMICS,
    HABITAT_TYPES,
    K_REF_DAILY_PER_KM2,
    PLUVIAL_TYPES,
    PERSISTENT_TYPES,
    RAIN_SCALE_MM,
    RAIN_WASH_FRACTION_MAX,
    RAIN_WASH_MM,
    SPECIES_HABITAT_WEIGHTS,
)

from . import (  # noqa: F401 — package-level access
    aquatic_stress,
    availability,
    capacity,
    constants,
    potential,
)

__all__ = [
    "aquatic_stress",
    "availability",
    "capacity",
    "constants",
    "potential",
    "HABITAT_TYPES",
    "HABITAT_DYNAMICS",
    "ACTIVATION_MIN",
    "BETA_URBAN",
    "RAIN_SCALE_MM",
    "DRY_MEMORY_DAYS",
]
