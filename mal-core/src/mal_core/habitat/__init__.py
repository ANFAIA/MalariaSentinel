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
same physics; the parity of shared responses is enforced by unit tests
in ``mal-core/tests/test_habitat_*.py`` against the Python reference.
Constants migrate to ``mal-core/config/model_constants.yaml`` (plan
constants-yaml); engine values win on conflict (see constants.py docstring).
"""
from __future__ import annotations

from . import (  # noqa: F401 — package-level access
    aquatic_stress,
    availability,
    capacity,
    config,
    potential,
)

# constants.py is a tombstone: it raises for every name. The canonical
# path is mal_core.habitat.config (CONFIG) — see habitat/__init__.py.

from .config import (  # noqa: F401
    CONFIG,
    habitat_names,
    dynamics_map,
    persistent_names,
    pluvial_names,
)

HABITAT_TYPES = habitat_names()
HABITAT_DYNAMICS = dynamics_map()

__all__ = [
    "aquatic_stress",
    "availability",
    "capacity",
    "config",
    "potential",
    "CONFIG",
    "HABITAT_TYPES",
    "HABITAT_DYNAMICS",
]
