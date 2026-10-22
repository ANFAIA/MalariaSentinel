"""Single value contract for proxy_habitat_v1.

Every constant here is mirrored verbatim in the C++ headers
``mal_abm_fast/habitat_availability.hpp`` and
``mal_abm_fast/aquatic_stress.hpp``; unit tests on both sides assert
parity (new regime: no per-species recalculation of the shared responses
k[g] or the temporal responses A[i,k,t] — those stay shared across
species, per plan docs/plans/in-process/redesign/02-*.md §3-§6).
"""
from __future__ import annotations

import math

# -- Habitat types ------------------------------------------------------------
# Six static proxy habitat types ("g" in the plan). The first three use the
# persistent availability response (k[g] = persistent, A = 1 in the MVP);
# the last three use the pluvial response (k[g] = pluvial, A = z).
HABITAT_TYPES: tuple[str, ...] = (
    "surface_persistent",
    "wetland_persistent",
    "urban_persistent",
    "wetland_pluvial",
    "open_pluvial",
    "crop_pluvial",
)

HABITAT_DYNAMICS: dict[str, str] = {
    "surface_persistent": "persistent",
    "wetland_persistent": "persistent",
    "urban_persistent": "persistent",
    "wetland_pluvial": "pluvial",
    "open_pluvial": "pluvial",
    "crop_pluvial": "pluvial",
}

PERSISTENT_TYPES: frozenset[str] = frozenset(
    g for g, k in HABITAT_DYNAMICS.items() if k == "persistent"
)
PLUVIAL_TYPES: frozenset[str] = frozenset(
    g for g, k in HABITAT_DYNAMICS.items() if k == "pluvial"
)

# -- Static potential (ingest features -> H[i,g]) -----------------------------
# Per-cell feature column names carried by the contract v3.0 env NC statics
# (see docstring in potential.static_potential; names match daily_nc.py).
FEATURE_COLUMNS: tuple[str, ...] = (
    "jrc_persistent",
    "lc_wetland",
    "lc_built",
    "lc_open_plus_water",
    "lc_crop",
)

# Urban persistent hypothesis (memory #167, plan 02 §6.4): leaks, seepage,
# drainage and human water storage can support a small dry-season breeding
# supply even with JRC=0 and no recent rainfall. Modelled as a
# species-independent static proxy: H_urban_persistent = BETA_URBAN * U.
# 0 < BETA_URBAN <= 1 is a configurable engineering prior that must not be
# silently initialised to zero; zero-beta ablation is an explicitly-named
# calibration experiment, never the default.
BETA_URBAN: float = 0.75  # mirrors URBAN_PERSISTENT_BETA in habitat_availability.hpp
assert 0.0 < BETA_URBAN <= 1.0

# Candidate cells (ABM patch union) are the cells whose summed static
# potential fails this micro-threshold. Documented engineering threshold:
# it is a numerical floor, not a biological dry-day signal; sensitivity
# tests sweep it.
HABITAT_CANDIDATE_MIN: float = 1.0e-6

# -- Temporal responses -------------------------------------------------------
# Pluvial availability (plan 02 §6.3):
#   z_dry = z_prev * exp(-delta_days / DRY_MEMORY_DAYS)
#   z     = z_dry + (1 - z_dry) * (1 - exp(-rain_mm / RAIN_SCALE_MM))
# Persistent availability A[persistent] = 1 (MVP; dry-season scarcity of
# persistent offer is a documented non-goal of this version).
RAIN_SCALE_MM: float = 20.0    # mm/day input scale for pluvial recharge
DRY_MEMORY_DAYS: float = 5.0   # e-fold drying memory, in days

# Activation threshold (engineering): a cell is a live patch for a species
# on day t when its accuracy-weighted S[i,s,t] exceeds this value. 0.10 is
# the documented 'active but shallow' baseline of the plan; sensitivity
# tests sweep it (0.05/0.10/0.20).
ACTIVATION_MIN: float = 0.10

# -- Canonical names of the aquatic stress constants (the C++
# `aquatic_stress.hpp` mirror; see habitat/aquatic_stress.py). Kept here so
# the D20 scorer and the engine quote the same value surface.
AQUATIC_RAIN_WASH_MM: float = 40.0    # mirror of the C++ aquatic_stress.hpp
AQUATIC_WASHOUT_FRACTION_MAX: float = 0.60

# -- Species index ------------------------------------------------------------
# Both defaults be parameterised by.
DEFAULT_SPECIES: str = "coluzzii"

# Species weight surface (plan 02 §6.5 example A). Weights in [0, 1] and
# sum to 1.0. These are hypotheses to calibrate, not measured values; they
# must stay explicit, documented and unit-tested as a surface.
#   6.5 example A: urban importance prior to calibration in the urban set.
SPECIES_HABITAT_WEIGHTS: dict[str, dict[str, float]] = {
    "coluzzii": {
        "surface_persistent": 0.40,
        "wetland_persistent": 0.20,
        "urban_persistent": 0.15,
        "wetland_pluvial": 0.10,
        "open_pluvial": 0.10,
        "crop_pluvial": 0.05,
    },
}

# Per-habitat-type capacity scale (adult-equivalent emergence per km2 at
# S = 1]; literature-anchored defaults from the prior regime are kept for
# 'surface_persistent'; surface/wetland types sit near the previous
# literature anchoring (0.143 adults m^-2 d^-1 emergence x 9.3 d mean adult
# lifetime, Ndenga/Fillinger 2011, Depinay 2004); the remaining types inherit
# the same scale for MVP unless biology suggests different K_ref (see
# calibration plan). Units of the returned capacity are larvae-equivalents
# per cell per day; to be replaced by a proper larval calibration in
# Mal-core rec. The numeric value is per species; canon prints the theory
# anchored constant once the species gets seated.
K_REF_DAILY_PER_KM2: dict[str, float] = {
    "coluzzii": 0.143 * 9.3 * 1.0e6,  # ≈ 1.33e6 adults-equivalents per km2
}

# -- Aquatic stress constants (mirrored verbatim in C++) ----------------------
# Values carried from the retired regime's biological bits (plan 02 §7.2):
# desiccating grace, ramp, baseline rate, heavy-rain washout window.
DESICCATION_GRACE_DAYS: int = 5
DESICC_BASE_DAILY: float = 0.10
RAIN_WASH_MM: float = 40.0
RAIN_WASH_FRACTION_MAX: float = 0.60

assert all(sum(w.values()) >= 0 and math.isclose(sum(w.values()), 1.0)
           for w in SPECIES_HABITAT_WEIGHTS.values())
