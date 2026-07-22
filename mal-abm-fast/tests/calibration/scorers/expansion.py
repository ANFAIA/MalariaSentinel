"""D1: Habitat coverage scorer.

Measures what fraction of the AOI grid has non-zero density.
In a multi-point seeding model (patches spread across the AOI),
this measures how well the population spreads across the landscape.

Target: 0.02-0.10 (2-10% of the AOI should have density > 0).
"""
from __future__ import annotations
import math
import re
from pathlib import Path
from typing import Any

import numpy as np
import rasterio

from scorers.base import Scorer, ScorerResult


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
         * math.sin(dlon / 2) ** 2)
    return R * 2 * math.asin(math.sqrt(a))


def _seed_files(run_dir: Path) -> list[Path]:
    files = sorted(run_dir.glob("state_seed*.tif"))
    if not files:
        state = run_dir / "state.tif"
        if state.exists():
            files = [state]
    return files


def _day0_file(run_dir: Path) -> Path | None:
    candidates = sorted(run_dir.glob("state_day000*.tif"))
    if candidates:
        return candidates[0]
    state = run_dir / "state.tif"
    if state.exists():
        return state
    return None


def _seed_cell(run_dir: Path, transform) -> tuple[int, int]:
    day0 = _day0_file(run_dir)
    seed_files = sorted(run_dir.glob("state_seed*.tif"))
    if day0 is not None:
        src = day0
    elif seed_files:
        src = seed_files[0]
    else:
        state = run_dir / "state.tif"
        src = state if state.exists() else None
    if src is None:
        return 0, 0
    with rasterio.open(src) as ds:
        band0 = ds.read(1)
    mask = np.isfinite(band0) & (band0 != -9999.0)
    if not mask.any():
        return 0, 0
    flat = band0.copy()
    flat[~mask] = -1
    idx = np.unravel_index(np.argmax(flat), band0.shape)
    return int(idx[0]), int(idx[1])


def _p90_distance_km(seed_file: Path, seed_row: int, seed_col: int) -> float:
    with rasterio.open(seed_file) as ds:
        band0 = ds.read(1)
        transform = ds.transform
    lat_seed, lon_seed = transform * (seed_col, seed_row)
    mask = np.isfinite(band0) & (band0 != -9999.0) & (band0 >= 0.05)
    if not mask.any():
        return 0.0
    rows, cols = np.where(mask)
    distances = np.empty(len(rows), dtype=np.float64)
    for i in range(len(rows)):
        lon_c, lat_c = transform * (cols[i], rows[i])
        distances[i] = _haversine_km(lat_seed, lon_seed, lat_c, lon_c)
    return float(np.percentile(distances, 90))


class ExpansionScorer(Scorer):
    @property
    def name(self) -> str:
        return "D1_expansion"

    @property
    def weight(self) -> float:
        return 2.0

    def score(self, run_dir: Path, experiment: dict[str, Any]) -> ScorerResult:
        state_files = _seed_files(run_dir)
        if not state_files:
            return ScorerResult(score=0.0, value=0.0, target="0.02-0.10",
                                diagnostics={"error": "no state files"}, passed=False)
        with rasterio.open(state_files[0]) as ds:
            band0 = ds.read(1)
        # Count valid habitat pixels (non-NoData, non-zero density)
        valid = np.isfinite(band0) & (band0 != -9999.0)
        n_valid = int(valid.sum())
        if n_valid == 0:
            return ScorerResult(score=0.0, value=0.0, target="0.02-0.10",
                                diagnostics={"error": "no valid pixels"}, passed=False)
        # Count pixels with non-zero density (activated habitat)
        active = valid & (band0 > 0)
        n_active = int(active.sum())
        coverage = n_active / n_valid
        # Score: 1.0 if in range [0.02, 0.10], Gaussian otherwise
        if 0.02 <= coverage <= 0.10:
            raw_score = 1.0
        else:
            raw_score = float(math.exp(-((coverage - 0.06) / 0.04) ** 2))
        return ScorerResult(
            score=raw_score,
            value=coverage,
            target="0.02-0.10",
            diagnostics={"n_active": n_active, "n_valid": n_valid},
            passed=0.02 <= coverage <= 0.10,
        )
