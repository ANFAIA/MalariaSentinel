"""D9: Patch activation scorer."""
from __future__ import annotations
import math
from pathlib import Path
from typing import Any

import numpy as np
import rasterio

from scorers.base import Scorer, ScorerResult


class ActivationScorer(Scorer):
    @property
    def name(self) -> str:
        return "D9_activation"

    @property
    def weight(self) -> float:
        return 1.0

    def score(self, run_dir: Path, experiment: dict[str, Any]) -> ScorerResult:
        day_files = sorted(run_dir.glob("state_day*.tif")) + sorted(run_dir.glob("state_seed*_day*.tif"))
        if not day_files:
            state = run_dir / "state.tif"
            if state.exists():
                day_files = [state]
        if not day_files:
            return ScorerResult(score=0.0, value=0.0, target="0.05-0.30",
                                diagnostics={"error": "no day files"}, passed=False)
        rates = []
        for f in day_files:
            with rasterio.open(f) as ds:
                b1 = ds.read(2)
            valid = np.isfinite(b1) & (b1 != -9999.0)
            n_active = int(((b1 > 0) & valid).sum())
            n_total = int(valid.sum()) if valid.sum() > 0 else b1.size
            rates.append(n_active / n_total)
        rate = float(np.mean(rates))
        if 0.05 <= rate <= 0.30:
            raw_score = 1.0
        else:
            raw_score = float(math.exp(-((rate - 0.15) / 0.10) ** 2))
        return ScorerResult(
            score=raw_score,
            value=rate,
            target="0.05-0.30",
            diagnostics={"n_days": len(day_files)},
            passed=0.05 <= rate <= 0.30,
        )
