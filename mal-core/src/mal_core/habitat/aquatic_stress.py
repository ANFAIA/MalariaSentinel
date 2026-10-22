"""Preserved aquatic stress mechanisms: desiccation ramp + rain washout.

End-mechanism formulas carried over from the retired regime (M14 pool
hydrology), now expressed against the new availability state (plan 02
§7.2: keep the biological bits, drop the mm model):

* ``desiccation_rate(days_dry)`` — grace period first
  ``aquatic_stress.desicc_grace_days`` days, then an exponential ramp to
  ``desicc_base_daily`` (ramp exponent ``desicc_ramp_decay``). Applies to
  eggs and early instars (L1, L2).
  The C++ engine drives ``days_dry`` from consecutive days below the
  activation threshold (a cell with S > habitat.activation_min_engine
  has days_dry = 0).
* ``washout_fraction(rain_mm)`` — heavy-rain cohort flush, linear from 0
  at ``wash_threshold_mm`` to ``wash_fraction_max`` at
  ``2 x wash_threshold_mm``, capped. Applies to all aquatic stages;
  adults are never washed out.

Values live in ``mal-core/config/model_constants.yaml`` (aquatic_stress
section); both formulas mirror ``mal_abm_fast/aquatic_stress.hpp`` 1:1.
"""
from __future__ import annotations

import math

from .config import CONFIG

_STRESS = CONFIG["aquatic_stress"]


def desiccation_rate(days_dry: int | float) -> float:
    """Daily mortality fraction at a dry (not active) patch."""
    grace = float(_STRESS["desicc_grace_days"])
    if days_dry <= grace:
        return 0.0
    past_grace = float(days_dry) - grace
    ramp = 1.0 - math.exp(
        -float(_STRESS["desicc_ramp_decay"]) * past_grace)
    return float(_STRESS["desicc_base_daily"]) * ramp


def washout_fraction(rain_mm: float) -> float:
    """Fraction of aquatic cohorts flushed by today's rain."""
    wash_mm = float(_STRESS["wash_threshold_mm"])
    frac_max = float(_STRESS["wash_fraction_max"])
    if rain_mm < wash_mm:
        return 0.0
    excess = (float(rain_mm) - wash_mm) / wash_mm
    return min(frac_max, excess * frac_max)


__all__ = ["desiccation_rate", "washout_fraction"]
