"""Pool hydrology — per-patch water-balance model (M14).

Python parity with ``mal_abm_fast/pool_hydrology.hpp``. The constants
must match the C++ header exactly so the two engines produce bit-for-bit
identical outputs on the same (rain, temp) forcing sequences.

Public surface
--------------
``PoolState`` — per-patch water state (dataclass).
``DailyForcing`` — daily climate inputs (dataclass).
``advance_pool(prev, forcing) -> PoolState`` — evolve one day.
``desiccation_rate(pool) -> float`` — larval mortality rate when dry.
``washout_fraction(rain_mm) -> float`` — fraction flushed by heavy rain.
``POOL_WATER_BREED_MM``, ``POOL_WATER_DRY_MM``, etc. — constants.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Constants — must match wire.hpp exactly (M14).
# ---------------------------------------------------------------------------
POOL_WATER_BREED_MM: float = 5.0
POOL_WATER_DRY_MM: float = 1.0
POOL_WATER_MAX_MM: float = 500.0
POOL_RAIN_WASH_MM: float = 40.0
POOL_DESICCATION_GRACE_DAYS: int = 5
POOL_EVAP_REF_MM: float = 5.0
POOL_EVAP_REF_T: float = 30.0
POOL_EVAP_T_COEFF: float = 0.07
POOL_WASH_FRACTION_MAX: float = 0.6
POOL_DESICC_BASE_DAILY: float = 0.10

# Re-export the rain threshold for refill semantics.
PLUVIAL_POOL_RAIN_THRESHOLD_MM: float = 15.0


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------
@dataclass
class PoolState:
    """Per-patch daily water state."""

    water_mm: float = 0.0
    days_dry: int = 0
    days_since_fill: int = 0


@dataclass
class DailyForcing:
    """Daily climate inputs for one patch."""

    rain_mm: float = 0.0
    temp_c: float = 25.0


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------
def advance_pool(prev: PoolState, forcing: DailyForcing) -> PoolState:
    """Evolve water balance for one day. Pure function, no side effects.

    Parity with ``mal_abm_fast::advance_pool`` in ``pool_hydrology.hpp``.
    """
    # 1. Evaporation — simplified Penman-Monteith (mm/day).
    evap = POOL_EVAP_REF_MM * (
        1.0 + POOL_EVAP_T_COEFF * (forcing.temp_c - POOL_EVAP_REF_T)
    )
    if evap < 0.5:
        evap = 0.5

    # 2. Water update.
    w = prev.water_mm + forcing.rain_mm - evap
    if w < 0.0:
        w = 0.0
    if w > POOL_WATER_MAX_MM:
        w = POOL_WATER_MAX_MM

    # 3. Dry-day counter.
    days_dry = prev.days_dry + 1 if w < POOL_WATER_DRY_MM else 0

    # 4. Days since last significant rain.
    if forcing.rain_mm > PLUVIAL_POOL_RAIN_THRESHOLD_MM:
        days_since_fill = 0
    else:
        days_since_fill = prev.days_since_fill + 1

    return PoolState(
        water_mm=w,
        days_dry=days_dry,
        days_since_fill=days_since_fill,
    )


def desiccation_rate(pool: PoolState) -> float:
    """Larval mortality rate when pool is dry.

    Only eggs and early instars (L1, L2) are vulnerable.
    Grace period: first POOL_DESICCATION_GRACE_DAYS dry days → no mortality.
    After grace: rate ramps exponentially to POOL_DESICC_BASE_DAILY.

    Parity with ``mal_abm_fast::desiccation_rate`` in ``pool_hydrology.hpp``.
    """
    if pool.water_mm >= POOL_WATER_DRY_MM:
        return 0.0
    if pool.days_dry <= POOL_DESICCATION_GRACE_DAYS:
        return 0.0
    past_grace = pool.days_dry - POOL_DESICCATION_GRACE_DAYS
    ramp = 1.0 - math.exp(-0.3 * past_grace)
    return POOL_DESICC_BASE_DAILY * ramp


def washout_fraction(rain_mm: float) -> float:
    """Fraction of aquatic cohorts flushed by heavy rain.

    Linear from 0 at POOL_RAIN_WASH_MM to POOL_WASH_FRACTION_MAX at
    2 * POOL_RAIN_WASH_MM, capped.

    Parity with ``mal_abm_fast::washout_fraction`` in ``pool_hydrology.hpp``.
    """
    if rain_mm < POOL_RAIN_WASH_MM:
        return 0.0
    excess = (rain_mm - POOL_RAIN_WASH_MM) / POOL_RAIN_WASH_MM
    return min(POOL_WASH_FRACTION_MAX, excess * POOL_WASH_FRACTION_MAX)


__all__ = [
    "PoolState",
    "DailyForcing",
    "advance_pool",
    "desiccation_rate",
    "washout_fraction",
    "POOL_WATER_BREED_MM",
    "POOL_WATER_DRY_MM",
    "POOL_WATER_MAX_MM",
    "POOL_RAIN_WASH_MM",
    "POOL_DESICCATION_GRACE_DAYS",
    "POOL_EVAP_REF_MM",
    "POOL_EVAP_REF_T",
    "POOL_EVAP_T_COEFF",
    "POOL_WASH_FRACTION_MAX",
    "POOL_DESICC_BASE_DAILY",
    "PLUVIAL_POOL_RAIN_THRESHOLD_MM",
]
