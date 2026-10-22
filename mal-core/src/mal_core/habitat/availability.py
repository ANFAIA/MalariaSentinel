"""Shared temporal availability responses A[i,k(g),t].

Two responses only (plan 02 §5.2-§5.4):

* ``persistent``   — A = 1.0 every day (MVP: the persistent offer is not
  reduced by extraordinary drought; a future calibrated scarcity term is a
  documented extension, never part of this contract).
* ``pluvial``      — state z[i,t] in [0, 1] with exponential drying memory
  and saturating rain recharge:

      z_dry = z_prev * exp(-delta_days / DRY_MEMORY_DAYS)
      z     = z_dry + (1 - z_dry) * (1 - exp(-rain_mm / RAIN_SCALE_MM))

  Applied once per (cell, calendar day) in the daily ABM loop — never per
  patch and never per species. Causal warm-up (plan §6.5 rule of daily
  step from previous dates): the state before the first simulated day is
  integrated forward from the days of the env NC that precede it, with
  z[i, 0] = 0 at the cold start, so the first available day is not
  artificially dry.

The Python functions here mirror ``mal_abm_fast::update_z_series`` /
``mal_abm_fast::habitat_availability.hpp`` 1:1.
"""
from __future__ import annotations

import math

import numpy as np

from .constants import DRY_MEMORY_DAYS, RAIN_SCALE_MM


def update_pluvial_state(
    z_prev: np.ndarray | float,
    rain_mm: np.ndarray | float,
    *, delta_days: float = 1.0,
) -> np.ndarray | float:
    """One pluvial-response step (pure; state z in [0, 1])."""
    import numpy as np

    z_arr = np.atleast_1d(np.asarray(z_prev, dtype=np.float64))
    rain = np.atleast_1d(np.asarray(rain_mm, dtype=np.float64))
    z_dry = z_arr * math.exp(-float(delta_days) / DRY_MEMORY_DAYS)
    recharge = np.exp(-rain / RAIN_SCALE_MM)
    z = z_dry + (1.0 - z_dry) * (1.0 - recharge)
    z = np.clip(z, 0.0, 1.0)
    if np.isscalar(z_prev) and np.isscalar(rain_mm):
        return float(z[0])
    return z


def warm_up_pluvial(
    rain_series: np.ndarray, *, cold_start: float = 0.0
) -> np.ndarray:
    """Integrate the pluvial response over a (n_steps,) rain series.

    Returns the z state after the last step (or the cold start value when
    the series is empty). Used by the C++ engine before the first
    simulated day and by tests to prove warm-up causality: a heavy rain
    before day 0 must raise day-0 availability, and a dry warm-up must
    leave it at the cold start.
    """
    z: np.ndarray | float = cold_start
    rain_series = np.asarray(rain_series, dtype=np.float64)
    for r in rain_series:
        z = update_pluvial_state(z, float(r), delta_days=1.0)
    return _as_array(z)


def _as_array(x) -> np.ndarray:
    arr = np.asarray(x, dtype=np.float64)
    return np.nan_to_num(arr, nan=0.0)


__all__ = ["update_pluvial_state", "warm_up_pluvial"]
