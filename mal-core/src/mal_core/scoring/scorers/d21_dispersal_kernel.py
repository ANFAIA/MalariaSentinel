"""D21: Dispersal kernel match (individual-scale, MRR-anchored).

Measures the displacement distribution of the adult population from the
SEEDING centroid at the day-30 snapshot (individual scale, one month —
still dominated by first-generation movement) and compares it with
mark-release-recapture (MRR) expectations:

- Costantini et al. 1996 (Burkina Faso): 350-650 m/day mean daily
  dispersal.
- Thomas et al. 2013 (The Gambia): median 295-386 m; 90th percentile
  1.28-1.64 km; 95th percentile 1.67-2.83 km (negative exponential and
  half-Cauchy fits).
- Midega et al. 2007 (Kenya coast): maximum flight distance recorded
  661 m; sub-km daily movement.
- Saarman et al. 2019: mean first-flight MDT 579 m.

Expected bands at one month: p50 in [0.15, 0.70] km, p90 in
[0.70, 3.00] km. Score = mean of both sub-scores (Gaussian falloff
outside each band).

Full table with references:
papers/anopheles-dynamics/dispersal-kernel-calibration.md.
"""
from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Any

import numpy as np
import rasterio

from .base import (
    NODATA,
    Scorer,
    ScorerResult,
    find_state_files,
    grid_transform,
)

P50_BAND = (0.15, 0.70)   # km — Thomas 2013 median 295-386 m
P90_BAND = (0.70, 3.00)   # km — Thomas 2013 p90-p95; Midega max 661 m
P50_CENTER, P50_SIGMA = 0.40, 0.20
P90_CENTER, P90_SIGMA = 1.60, 0.80


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.asin(math.sqrt(a))


class DispersalKernelScorer(Scorer):
    name = "D21_dispersal_kernel"
    kind = "composite"
    weight = 1.0
    description = "p50/p90 displacement at day 30 vs MRR kernels (Thomas 2013; Costantini 1996)"
    min_score = 0.7
    hard_floor = 0.3

    def score(self, run_dir: Path, ctx: dict[str, Any]) -> ScorerResult:
        target = f"p50 {P50_BAND[0]}-{P50_BAND[1]} km, p90 {P90_BAND[0]}-{P90_BAND[1]} km @ day30"
        files = find_state_files(run_dir)
        if not files:
            return ScorerResult.skipped("no state files", target)
        transform = grid_transform(run_dir, ctx)
        if transform is None:
            return ScorerResult.skipped("no usable grid transform", target)

        day_files: dict[int, Path] = {}
        for f in files:
            m = re.search(r"_day(\d+)\.tif$", f.name)
            if m:
                day_files[int(m.group(1))] = f
        if not day_files:
            return ScorerResult.skipped("no day snapshots", target)

        # seeding origin = centroid of occupied cells in the FIRST snapshot
        first_day = min(day_files)
        origin_file = day_files[first_day]
        with rasterio.open(origin_file) as ds:
            band0 = ds.read(1)
        mask0 = np.isfinite(band0) & (band0 != NODATA) & (band0 > 0)
        if not mask0.any():
            return ScorerResult.skipped("no occupied cells in first snapshot", target)
        rows0, cols0 = np.where(mask0)
        lon0, lat0 = transform * (float(cols0.mean()), float(rows0.mean()))

        # measurement snapshot: nearest available day <= 30
        horizon = max((d for d in day_files if d <= 30), default=None)
        if horizon is None or horizon == first_day:
            return ScorerResult.skipped(
                f"no snapshot between day {first_day + 1} and 30", target
            )
        with rasterio.open(day_files[horizon]) as ds:
            band = ds.read(1)
        mask = np.isfinite(band) & (band != NODATA) & (band > 0)
        rows, cols = np.where(mask)
        if len(rows) < 3:
            return ScorerResult.skipped(
                f"too few occupied cells at day {horizon}", target
            )
        distances = np.empty(len(rows), dtype=np.float64)
        for i in range(len(rows)):
            lon_i, lat_i = transform * (cols[i], rows[i])
            distances[i] = _haversine_km(lat0, lon0, lat_i, lon_i)
        p50 = float(np.percentile(distances, 50))
        p90 = float(np.percentile(distances, 90))

        lo, hi = P50_BAND
        if lo <= p50 <= hi:
            p50_ok = 1.0
        else:
            p50_ok = max(0.0, math.exp(-((p50 - P50_CENTER) / P50_SIGMA) ** 2))
        lo, hi = P90_BAND
        if lo <= p90 <= hi:
            p90_ok = 1.0
        else:
            p90_ok = max(0.0, math.exp(-((p90 - P90_CENTER) / P90_SIGMA) ** 2))

        score = (p50_ok + p90_ok) / 2.0
        return ScorerResult(
            score=round(score, 4),
            value=round(p90, 3),
            target=target,
            diagnostics={
                "p50_km": round(p50, 3),
                "p90_km": round(p90, 3),
                "horizon_day": horizon,
                "origin_day": first_day,
                "n_cells": int(len(rows)),
            },
            passed=score >= self.min_score,
        )
