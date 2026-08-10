"""D17: Host clustering — adult density clusters around host cells.

Measures the variance of adult density per host-cell cluster in the
upper tertile. Target: >= 0.6 (clustered around villages).

Source: Depinay 2004, North & Godfray 2018 — settlement-to-settlement
dispersal produces clustered density patterns.
"""
from __future__ import annotations
import math
from pathlib import Path
from typing import Any

import numpy as np
import rasterio

from scorers.base import Scorer, ScorerResult, find_state_files


class HostClusteringScorer(Scorer):
    @property
    def name(self) -> str:
        return "D17_host_clustering"

    @property
    def weight(self) -> float:
        return 0.10

    def score(self, run_dir: Path, experiment: dict[str, Any]) -> ScorerResult:
        state_files = find_state_files(run_dir)
        if not state_files:
            return ScorerResult(score=0.0, value=0.0, target=">= 0.6",
                                diagnostics={"error": "no state files"}, passed=False)

        last_file = state_files[-1]
        with rasterio.open(last_file) as ds:
            band0 = ds.read(1)  # density

        mask = np.isfinite(band0) & (band0 != -9999.0) & (band0 > 0)
        if not mask.any():
            return ScorerResult(score=0.0, value=0.0, target=">= 0.6",
                                diagnostics={"error": "no density"}, passed=False)

        values = band0[mask]
        if len(values) < 3:
            return ScorerResult(score=0.0, value=0.0, target=">= 0.6",
                                diagnostics={"error": "too few cells"}, passed=False)

        # Compute coefficient of variation (std/mean) as clustering metric.
        mean = float(values.mean())
        std = float(values.std())
        cv = std / mean if mean > 0 else 0.0

        # Normalize CV to [0, 1] score. CV=0 means uniform (bad),
        # CV>1 means highly clustered (good). Use sigmoid.
        raw = 1.0 / (1.0 + math.exp(-2.0 * (cv - 0.5)))

        return ScorerResult(
            score=round(raw, 4),
            value=round(cv, 4),
            target=">= 0.6",
            diagnostics={"cv": cv, "mean": mean, "std": std, "n_cells": len(values)},
            passed=raw >= 0.6,
        )
