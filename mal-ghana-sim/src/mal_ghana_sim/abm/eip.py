"""EIP (Extrinsic Incubation Period) custom helper for the M1 ABM.

Tracks the parasite's growing-degree-day (GDD) accumulation in an adult
female mosquito. The EIP is the time between an infectious blood meal and
the mosquito becoming infective (sporozoite-positive salivary glands).

Reference: ``docs/abm-mesa-geo-adaptation.md`` §1 (EIP ``[custom]`` row).
``daily_gd = max(0, T - T_base)``; the mosquito is infective when
``eip_progress >= EIP_THRESHOLD_GD``. *P. falciparum* EIP is ~11 days at
25 degrees C (~110 GDD with ``T_base=16``).
"""
from __future__ import annotations

EIP_BASE_TEMP_C: float = 16.0
EIP_THRESHOLD_GD: float = 110.0


def accumulate_eip(eip_progress: float, daily_mean_temp_c: float) -> float:
    """Add one day's worth of growing-degree-days to ``eip_progress``.

    ``daily_gd = max(0, daily_mean_temp_c - EIP_BASE_TEMP_C)``. Temperatures
    at or below the base contribute zero (development halts). The function
    is pure and never mutates the input.
    """
    if not (daily_mean_temp_c == daily_mean_temp_c):  # NaN-safe
        return float(eip_progress)
    daily_gd = max(0.0, float(daily_mean_temp_c) - EIP_BASE_TEMP_C)
    return float(eip_progress) + daily_gd


def is_infective(eip_progress: float) -> bool:
    """True if the mosquito has completed the EIP and is infective."""
    return float(eip_progress) >= EIP_THRESHOLD_GD
