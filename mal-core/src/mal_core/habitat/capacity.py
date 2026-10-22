"""Species-indexed habitat capacity S[i,s,t] and Beverton-Holt scale K[i,s,t].

    S[i,s,t] = clip(sum_g w[s,g] * H[i,g] * A[i,k(g),t], 0, 1)
    K[i,s,t] = K_ref[s] * cell_area_km2[i] * S[i,s,t]

* The shared temporal responses A and the static potentials H are
  species-independent; only ``w[s,g]`` carries species preferences.
* The returned K is an ABSOLUTE per-cell aquatic capacity (individuals per
  day) — it replaced the retired per-cell multiplier `k_capacity_mult`
  (contract 3.0), and the retired global K_MAX fallback was removed with
  contract 4.0 (plan 03-retirada-k-max): the Beverton-Holt consumer uses
  exactly this grid, with K=0 meaning explicit zero larval survival.
* cell_area_km2 accounts for the true ground area of each grid row
  (resolution_m x resolution_m x cos(lat)). Edge cells clipped by the AOI
  bbox are NOT area-corrected in the MVP (all rows are regular), but the
  factor is documented; plan 02 §8 lists row-accurate edge de-limitation
  as a sensitivity extension.
"""
from __future__ import annotations

from typing import Mapping

import numpy as np

from .config import CONFIG
# Emergency-adult scaling constant for the py DIAGNOSTIC capacity path
# (renamed from the retired K_REF_DAILY_PER_KM2 .py constant; it is NOT a
# model_constants.yaml key — the engine's k_ref = 50.0 is a different
# concept; plan constants-yaml §9.1: dies here without conversion).
K_REF_DIAG_PER_KM2: float = 0.143 * 9.3 * 1.0e6  # [ind·km⁻²·d⁻¹ diagnostic]
from .potential import total_potential

_DEFAULT_SPECIES = str(CONFIG["species"]["default_species"])
_PLUVIAL_TYPES = frozenset(
    g for g, k in CONFIG["habitat_types"]["dynamics"].items()
    if k == "pluvial")


def cell_area_km2(lat_deg: np.ndarray | float, resolution_m: float) -> np.ndarray | float:
    """Ground area of one AOI cell (approximation: constant width within
    the row's latitude). ``lat_deg`` may be scalar or a per-row array
    (height = number of rows); returns array of the same broadcast shape."""
    lat = np.asarray(lat_deg, dtype=np.float64)
    width_m = resolution_m * np.cos(np.deg2rad(lat))
    height_m = float(resolution_m)
    return width_m * height_m / 1.0e6


def species_accuracy(
    h: Mapping[str, np.ndarray],
    z_pluvial: np.ndarray,
    weights: Mapping[str, float] | None = None,
) -> np.ndarray:
    """Sum_g w[g] * H[g] * (1 if persistent else z). Applied per cell.

    Args:
        h: mapping habitat type -> per-cell potential in [0, 1].
        z_pluvial: per-cell pluvial availability in [0, 1] for today.
        weights: species affinity w[s, g]; defaults to the coluzzii
            profile when ``species`` was default; the plan's contract is
            that neither H nor z are species-dependent.
    Returns:
        per-cell S in [0, 1].
    """
    w = weights if weights is not None else dict(
        CONFIG["species"][_DEFAULT_SPECIES]["weights"])
    acc = np.zeros_like(z_pluvial, dtype=np.float64)
    for g, val in h.items():
        weight = float(w.get(g, 0.0))
        if weight <= 0.0:
            continue
        avail = (z_pluvial if g in _PLUVIAL_TYPES
                 else float(CONFIG["capacity"]["persistent_availability"]))
        c = np.asarray(val, dtype=np.float64)
        acc += weight * c * avail
    return np.clip(acc, 0.0, 1.0)


def k_habitat(
    s: np.ndarray,
    lat: np.ndarray,
    resolution_m: float,
    K_ref: float | None = None,
) -> np.ndarray:
    """Beverton-Holt per-cell capacity K[i,s,t] in larval-equivalents."""
    k_ref = K_ref if K_ref is not None else K_REF_DIAG_PER_KM2
    area = np.asarray(cell_area_km2(lat, resolution_m), dtype=np.float64)
    if area.shape != s.shape:
        # Broadcast per-row scalars down a 2-D S: rows all share the same
        # latitude-derived ground area.
        if area.ndim == 1 and s.ndim == 2 and area.shape[0] == s.shape[0]:
            area = area[:, None]
        else:
            area = np.broadcast_to(area, s.shape)
    return k_ref * area * np.asarray(s, dtype=np.float64)


def accuracy_amplitude(h: Mapping[str, np.ndarray]) -> np.ndarray:
    """H_total alias used for patch seeding weights / diagnostics."""
    return np.asarray(total_potential(h), dtype=np.float64)


__all__ = [
    "cell_area_km2",
    "k_habitat",
    "species_accuracy",
    "accuracy_amplitude",
]
