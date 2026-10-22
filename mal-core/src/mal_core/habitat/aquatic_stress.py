"""Preserved aquatic stress mechanisms: desiccation ramp + rain washout.

End-mechanism formulas carried over from the retired regime (M14 pool
hydrology), now expressed against the new availability state (plan 02
§7.2: keep the biological bits, drop the mm model):

* ``desiccation_rate(days_dry)`` — grace period first
  ``DESICCATION_GRACE_DAYS`` days, then an exponential ramp to
  ``DESICC_BASE_DAILY``. Applies to eggs and early instars (L1, L2).
  The C++ engine drives ``days_dry`` from consecutive days below the
  activation threshold (a cell with S > ACTIVATION_MIN has days_dry = 0).
* ``washout_fraction(rain_mm)`` — heavy-rain cohort flush, linear from 0
  at ``RAIN_WASH_MM`` to ``RAIN_WASH_FRACTION_MAX`` at ``2 x RAIN_WASH_MM``,
  capped. Applies to all aquatic stages; adults are never washed out.

Both formulas mirror ``mal_abm_fast/aquatic_stress.hpp`` 1:1 and are the
last N14 legacy bits the plan retains.
"""
from __future__ import annotations

from .constants import (
    DESICCATION_GRACE_DAYS,
    DESICC_BASE_DAILY,
    RAIN_WASH_FRACTION_MAX,
    RAIN_WASH_MM,
)


def desiccation_rate(days_dry: int | float) -> float:
    """Daily mortality fraction at a dry (not active) patch."""
    if days_dry <= DESICCATION_GRACE_DAYS:
        return 0.0
    past_grace = float(days_dry) - float(DESICCATION_GRACE_DAYS)
    ramp = 1.0 - float(2.718281828459045) ** (-0.3 * past_grace)
    return DESICC_BASE_DAILY * ramp


def washout_fraction(rain_mm: float) -> float:
    """Fraction of aquatic cohorts flushed by today's rain."""
    if rain_mm < RAIN_WASH_MM:
        return 0.0
    excess = (float(rain_mm) - RAIN_WASH_MM) / RAIN_WASH_MM
    return min(RAIN_WASH_FRACTION_MAX, excess * RAIN_WASH_FRACTION_MAX)


__all__ = ["desiccation_rate", "washout_fraction"]
