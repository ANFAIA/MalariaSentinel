"""D8: Density-suitability coupling.

Pearson r between adult density (band 1) and host-seeking pressure
(band 2) on active pixels of the FINAL state. Verifies the engine
actually allocates density according to the habitat field
(birth-at-cell fix C1). r >= 0.30 passes; score = r/0.50 clipped.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import rasterio

from .base import NODATA, Scorer, ScorerResult, find_final_state


class CouplingScorer(Scorer):
    name = "D8_coupling"
    kind = "composite"
    weight = 2.0
    description = "Correlation density vs habitat pressure on active cells"
    min_score = 0.4
    hard_floor = 0.1

    def score(self, run_dir: Path, ctx: dict[str, Any]) -> ScorerResult:
        final = find_final_state(run_dir)
        if final is None:
            return ScorerResult.skipped("no state files", target=">=0.30 r")
        with rasterio.open(final) as ds:
            b1 = ds.read(1)
            b2 = ds.read(2)
        mask = (
            np.isfinite(b1)
            & np.isfinite(b2)
            & (b1 != NODATA)
            & (b2 != NODATA)
            & (b1 > 0)
        )
        if int(mask.sum()) < 2:
            return ScorerResult.skipped(
                "too few active pixels", target=">=0.30 r"
            )
        d = b1[mask].astype(np.float64)
        s = b2[mask].astype(np.float64)
        if d.std() == 0 or s.std() == 0:
            r = 0.0
        else:
            r = float(np.corrcoef(d, s)[0, 1])
            if np.isnan(r):
                r = 0.0
        score = max(0.0, min(1.0, r / 0.50))
        return ScorerResult(
            score=round(score, 4),
            value=round(r, 4),
            target=">=0.30 r",
            diagnostics={"n_active": int(mask.sum())},
            passed=r >= 0.30,
        )
