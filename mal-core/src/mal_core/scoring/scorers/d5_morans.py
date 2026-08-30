"""D5: Moran's I spatial autocorrelation of active habitat.

Moran's I computed on ACTIVE pixels only (band 2, host-seeking
pressure) — including the ~99% empty background biases I toward 0.

Target band [0.20, 0.85]: larval habitats cluster strongly in
heterogeneous landscapes (Tokarz & Novak 2018; Bissett 2026);
empirical Ghana 731-day value ≈ 0.52. Band catches spatial randomness
(I ≈ 0) and pathological over-clustering (I → 1).
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import numpy as np
import rasterio

from .base import NODATA, Scorer, ScorerResult, find_final_state


def morans_i_active(grid: np.ndarray) -> float:
    """Moran's I on active (non-zero) pixels with queen contiguity."""
    active = np.isfinite(grid) & (grid != NODATA) & (grid > 0)
    n = int(active.sum())
    if n < 9:
        return 0.0
    z = np.where(active, grid - float(np.mean(grid[active])), 0.0)
    rows, cols = np.where(active)
    num = 0.0
    w_sum = 0
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            if di == 0 and dj == 0:
                continue
            nr = rows + di
            nc = cols + dj
            bounds = (
                (nr >= 0)
                & (nr < grid.shape[0])
                & (nc >= 0)
                & (nc < grid.shape[1])
            )
            nr_safe = np.clip(nr, 0, grid.shape[0] - 1)
            nc_safe = np.clip(nc, 0, grid.shape[1] - 1)
            m = bounds & active[nr_safe, nc_safe]
            w_sum += int(m.sum())
            num += float((z[rows[m], cols[m]] * z[nr_safe[m], nc_safe[m]]).sum())
    if w_sum == 0:
        return 0.0
    denom = float(z[active] @ z[active])
    if denom == 0:
        return 0.0
    return (n / w_sum) * (num / denom)


class MoransScorer(Scorer):
    name = "D5_morans"
    kind = "composite"
    weight = 1.0
    description = "Spatial autocorrelation of active habitat (Moran's I)"
    min_score = 0.5
    hard_floor = 0.2

    def score(self, run_dir: Path, ctx: dict[str, Any]) -> ScorerResult:
        final = find_final_state(run_dir)
        if final is None:
            return ScorerResult.skipped("no state files", target="0.20-0.85")
        with rasterio.open(final) as ds:
            band = ds.read(1)  # adult_occupancy density
        active = np.isfinite(band) & (band != NODATA) & (band > 0)
        if int(active.sum()) < 9:
            return ScorerResult.skipped(
                f"too few active cells ({int(active.sum())}) for spatial statistics",
                target="0.20-0.85",
            )
        i_value = morans_i_active(band)
        if 0.20 <= i_value <= 0.85:
            score = 1.0
        else:
            score = max(0.0, math.exp(-((i_value - 0.5) / 0.25) ** 2))
        return ScorerResult(
            score=round(score, 4),
            value=round(i_value, 4),
            target="0.20-0.85",
            diagnostics={"n_active_pixels": int(active.sum()), "final_file": final.name},
            passed=score >= self.min_score,
        )
