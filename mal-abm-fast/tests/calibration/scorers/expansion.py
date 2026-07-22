"""D1: Expansion radius scorer."""
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
    return files


def _day0_file(run_dir: Path) -> Path | None:
    candidates = sorted(run_dir.glob("state_day000*.tif"))
    return candidates[0] if candidates else None


def _seed_cell(run_dir: Path, transform) -> tuple[int, int]:
    day0 = _day0_file(run_dir)
    src = day0 if day0 is not None else sorted(run_dir.glob("state_seed*.tif"))[0]
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
        seed_files = _seed_files(run_dir)
        if not seed_files:
            return ScorerResult(score=0.0, value=0.0, target="1.0-1.4 km",
                                diagnostics={"error": "no seed files"}, passed=False)
        with rasterio.open(seed_files[0]) as ds:
            transform = ds.transform
        seed_row, seed_col = _seed_cell(run_dir, transform)
        p90s = []
        for sf in seed_files:
            p90s.append(_p90_distance_km(sf, seed_row, seed_col))
        r_obs = float(np.median(p90s))
        raw_score = math.exp(-((r_obs - 1.2) / 0.4) ** 2)
        return ScorerResult(
            score=raw_score,
            value=r_obs,
            target="1.0-1.4 km",
            diagnostics={"p90_per_seed": p90s, "seed_cell": [seed_row, seed_col]},
            passed=1.0 <= r_obs <= 1.4,
        )