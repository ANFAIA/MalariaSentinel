"""D21: Spread rate — p90 displacement matches Thomas 2013.

Measures the 90th percentile of adult mosquito displacement from
the seeding centroid at day 180. Target: 5-20 km.

Source: Thomas et al. 2013 (PLOS ONE): p90 = 1.28 km at day 1;
p95 half-Cauchy = 2.83 km. At day 180, cumulative displacement
should reach 5-20 km for realistic dispersal.
"""
from __future__ import annotations
import math
from pathlib import Path
from typing import Any

import numpy as np
import rasterio

from scorers.base import Scorer, ScorerResult, find_state_files


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
         * math.sin(dlon / 2) ** 2)
    return R * 2 * math.asin(math.sqrt(a))


class SpreadRateScorer(Scorer):
    @property
    def name(self) -> str:
        return "D21_spread_rate"

    @property
    def weight(self) -> float:
        return 0.15

    def score(self, run_dir: Path, experiment: dict[str, Any]) -> ScorerResult:
        state_files = find_state_files(run_dir)
        if not state_files:
            return ScorerResult(score=0.0, value=0.0, target="5-20 km",
                                diagnostics={"error": "no state files"}, passed=False)

        # Use the last state file (day 180 or end of sim).
        last_file = state_files[-1]
        with rasterio.open(last_file) as ds:
            band0 = ds.read(1)
            transform = ds.transform

        mask = np.isfinite(band0) & (band0 != -9999.0) & (band0 > 0)
        if not mask.any():
            return ScorerResult(score=0.0, value=0.0, target="5-20 km",
                                diagnostics={"error": "no density"}, passed=False)

        # Centroid of density.
        rows, cols = np.where(mask)
        weights = band0[mask]
        total_w = weights.sum()
        if total_w <= 0:
            return ScorerResult(score=0.0, value=0.0, target="5-20 km",
                                diagnostics={"error": "zero weight"}, passed=False)
        centroid_row = float(np.average(rows, weights=weights))
        centroid_col = float(np.average(cols, weights=weights))
        lon_c, lat_c = transform * (centroid_col, centroid_row)

        # Distance of each active cell from centroid.
        distances = np.empty(len(rows), dtype=np.float64)
        for i in range(len(rows)):
            lon_i, lat_i = transform * (cols[i], rows[i])
            distances[i] = _haversine_km(lat_c, lon_c, lat_i, lon_i)

        p90 = float(np.percentile(distances, 90))

        # Score: 1.0 if in [5, 20] km, Gaussian otherwise.
        if 5.0 <= p90 <= 20.0:
            raw = 1.0
        elif p90 < 5.0:
            raw = math.exp(-((p90 - 5.0) / 3.0) ** 2)
        else:
            raw = math.exp(-((p90 - 20.0) / 10.0) ** 2)

        return ScorerResult(
            score=round(raw, 4),
            value=round(p90, 2),
            target="5-20 km",
            diagnostics={"p90_km": p90, "n_active_cells": len(rows)},
            passed=5.0 <= p90 <= 20.0,
        )
