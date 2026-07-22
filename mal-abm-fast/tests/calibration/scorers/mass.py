"""D6: Mass conservation scorer."""
from __future__ import annotations
from pathlib import Path
from typing import Any

import numpy as np
import rasterio

from scorers.base import Scorer, ScorerResult


class MassScorer(Scorer):
    @property
    def name(self) -> str:
        return "D6_mass"

    @property
    def weight(self) -> float:
        return 2.0

    def score(self, run_dir: Path, experiment: dict[str, Any]) -> ScorerResult:
        tifs = sorted(run_dir.glob("state_*.tif"))
        if not tifs:
            state = run_dir / "state.tif"
            if state.exists():
                tifs = [state]
        if not tifs:
            return ScorerResult(score=0.0, value=0.0, target="1.00",
                                diagnostics={"error": "no tifs"}, passed=False)
        total_valid = 0
        total_pixels = 0
        for tif in tifs:
            with rasterio.open(tif) as ds:
                for bidx in [1, 2]:
                    band = ds.read(bidx)
                    nodata = ds.nodata
                    finite = np.isfinite(band)
                    if nodata is not None:
                        finite = finite & (band != nodata)
                    finite = finite & (band != -9999.0)
                    in_range = finite & (band >= 0.0) & (band <= 1.0)
                    total_valid += int(in_range.sum())
                    total_pixels += band.size
        if total_pixels == 0:
            return ScorerResult(score=0.0, value=0.0, target="1.00",
                                diagnostics={"error": "no pixels"}, passed=False)
        return ScorerResult(
            score=float(total_valid / total_pixels),
            value=float(total_valid / total_pixels),
            target="1.00",
            diagnostics={"total_valid": total_valid, "total_pixels": total_pixels},
            passed=total_valid == total_pixels,
        )
