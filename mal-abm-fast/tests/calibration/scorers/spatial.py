"""D5: Moran's I spatial autocorrelation scorer."""
from __future__ import annotations
import math
from pathlib import Path
from typing import Any

import numpy as np
import rasterio

from scorers.base import Scorer, ScorerResult


def _morans_i(grid: np.ndarray) -> float:
    valid = np.isfinite(grid) & (grid != 0)
    if valid.sum() < 9:
        return 0.0
    z = grid - np.nanmean(grid[valid])
    z[~valid] = 0.0
    n = int(valid.sum())
    rows, cols = np.where(valid)
    idx = np.zeros_like(valid, dtype=int)
    idx[valid] = np.arange(n)
    from scipy import sparse
    data: list[float] = []
    r_ind: list[int] = []
    c_ind: list[int] = []
    for di in [-1, 0, 1]:
        for dj in [-1, 0, 1]:
            if di == 0 and dj == 0:
                continue
            nr = rows + di
            nc = cols + dj
            bounds = ((nr >= 0) & (nr < grid.shape[0])
                      & (nc >= 0) & (nc < grid.shape[1]))
            nr_safe = np.clip(nr, 0, grid.shape[0] - 1)
            nc_safe = np.clip(nc, 0, grid.shape[1] - 1)
            mask = bounds & valid[nr_safe, nc_safe]
            r_ind.extend(idx[rows[mask], cols[mask]])
            c_ind.extend(idx[nr_safe[mask], nc_safe[mask]])
            data.extend([1.0] * int(mask.sum()))
    W = sparse.csr_matrix((data, (r_ind, c_ind)), shape=(n, n))
    W_sum = W.sum()
    if W_sum == 0:
        return 0.0
    z_valid = z[valid]
    numerator = float(z_valid @ (W @ z_valid))
    denominator = float(z_valid @ z_valid)
    if denominator == 0:
        return 0.0
    return float((n / W_sum) * (numerator / denominator))


def _final_state_file(run_dir: Path) -> Path | None:
    seeds = sorted(run_dir.glob("state_seed*.tif"))
    if seeds:
        return seeds[-1]
    days = sorted(run_dir.glob("state_day*.tif"))
    if days:
        return days[-1]
    state = run_dir / "state.tif"
    if state.exists():
        return state
    return None


class MoransScorer(Scorer):
    @property
    def name(self) -> str:
        return "D5_morans"

    @property
    def weight(self) -> float:
        return 1.0

    def score(self, run_dir: Path, experiment: dict[str, Any]) -> ScorerResult:
        final = _final_state_file(run_dir)
        if final is None:
            return ScorerResult(score=0.0, value=0.0, target="0.20-0.70",
                                diagnostics={"error": "no state file"}, passed=False)
        with rasterio.open(final) as ds:
            band2 = ds.read(2)
        I = _morans_i(band2)
        if 0.20 <= I <= 0.70:
            raw_score = 1.0
        else:
            raw_score = float(math.exp(-((I - 0.45) / 0.20) ** 2))
        return ScorerResult(
            score=raw_score,
            value=I,
            target="0.20-0.70",
            passed=0.20 <= I <= 0.70,
        )
