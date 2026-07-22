"""D8: Density-suitability coupling scorer."""
from __future__ import annotations
from pathlib import Path
from typing import Any

import numpy as np
import rasterio

from scorers.base import Scorer, ScorerResult


def _final_state_file(run_dir: Path) -> Path | None:
    seeds = sorted(run_dir.glob("state_seed*.tif"))
    if seeds:
        return seeds[-1]
    days = sorted(run_dir.glob("state_day*.tif"))
    if days:
        return days[-1]
    return None


class CouplingScorer(Scorer):
    @property
    def name(self) -> str:
        return "D8_coupling"

    @property
    def weight(self) -> float:
        return 2.0

    def score(self, run_dir: Path, experiment: dict[str, Any]) -> ScorerResult:
        final = _final_state_file(run_dir)
        if final is None:
            return ScorerResult(score=0.0, value=0.0, target=">=0.30 r",
                                diagnostics={"error": "no state file"}, passed=False)
        with rasterio.open(final) as ds:
            b0 = ds.read(1)
            b1 = ds.read(2)
        mask = np.isfinite(b0) & np.isfinite(b1) & (b0 != -9999.0) & (b1 != -9999.0) & (b0 > 0)
        if mask.sum() < 2:
            return ScorerResult(score=0.0, value=0.0, target=">=0.30 r",
                                diagnostics={"error": "too few positive density pixels"}, passed=False)
        d = b0[mask].astype(np.float64)
        s = b1[mask].astype(np.float64)
        r = float(np.corrcoef(d, s)[0, 1]) if d.std() > 0 and s.std() > 0 else 0.0
        if np.isnan(r):
            r = 0.0
        raw_score = max(0.0, min(1.0, (r - 0.0) / 0.50))
        return ScorerResult(
            score=raw_score,
            value=r,
            target=">=0.30 r",
            passed=r >= 0.30,
        )