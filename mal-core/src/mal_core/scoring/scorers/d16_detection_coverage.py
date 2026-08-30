"""D16: Detection-point coverage — launch-and-measure validation.

Unlike every other scorer, this one is meant to be fed a run produced
by the dedicated ``malariasim validate-detections`` command, which
LAUNCHES a simulation seeding mosquitoes at the AOI's real detection
points (``--seeding-mode explicit`` + ``--detection-points``), runs it
for >= 1 year, and then this scorer measures how many of those
detection spots the simulated population actually reached: covered =
at least one occupied cell (band 1 > 0) within ``radius_km`` of the
spot in the final snapshot. Score = covered / spots.

Radius default 5 km (~5 cells at ~1 km grain): matches the engine's
own ``detection_radius_km`` snap convention — a mosquito within 5 km
of a trap is the same local population. Sensitivity at 2/5/10 km is
reported in diagnostics.

Extinction (cohort final adults == 0) scores 0 with an ``extinct``
diagnostic — the population failed to establish, which IS the result.

AOI-dependent (manual activation, explicit ``--aoi`` required): needs
the AOI's occurrence dataset.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import rasterio

from .base import (
    NODATA,
    Scorer,
    ScorerResult,
    find_final_state,
    grid_transform,
    load_occurrence_spots,
    require_aoi,
    resolve_aoi_artifact,
    find_cohort_file,
)

RADIUS_KM_DEFAULT = 5.0
COVERAGE_TARGET = 0.5
SENSITIVITY_RADII_KM = (2.0, 5.0, 10.0)

OCCURRENCE_CANDIDATES = [
    "data/{aoi}/{aoi}_occurrence.txt",
    "data/{aoi}_idit/occurrence.txt",
]


class DetectionCoverageScorer(Scorer):
    name = "D16_detection_coverage"
    kind = "composite"
    weight = 4.0
    description = "Fraction of detection spots reached by a seeded 1-year run (validate-detections)"
    min_score = 0.5
    hard_floor = 0.2
    manual = True  # AOI-dependent: needs the AOI's occurrence dataset

    def score(self, run_dir: Path, ctx: dict[str, Any]) -> ScorerResult:
        target = f"coverage >= {COVERAGE_TARGET} @ r={RADIUS_KM_DEFAULT}km"
        aoi = require_aoi(ctx)
        if not aoi:
            return ScorerResult.skipped(
                "requires explicit --aoi (never inferred)", target
            )
        occ = ctx.get("occurrence_path") or resolve_aoi_artifact(
            aoi, OCCURRENCE_CANDIDATES
        )
        if occ is None or not Path(occ).exists():
            return ScorerResult.skipped(
                f"occurrence file not resolved for AOI {aoi!r}", target
            )
        final = find_final_state(run_dir)
        if final is None:
            return ScorerResult.skipped("no state files", target)
        transform = grid_transform(run_dir, ctx)
        if transform is None:
            return ScorerResult.skipped("no usable grid transform", target)

        lats, lons = load_occurrence_spots(Path(occ))
        if len(lats) == 0:
            return ScorerResult.skipped("no valid detection spots", target)

        with rasterio.open(final) as ds:
            band = ds.read(1)
        h, w = band.shape

        from rasterio.transform import rowcol

        rows, cols = rowcol(transform, lons, lats)
        rows = np.asarray(rows)
        cols = np.asarray(cols)
        in_grid = (rows >= 0) & (rows < h) & (cols >= 0) & (cols < w)
        if not in_grid.any():
            return ScorerResult.skipped("no detection spots inside the run grid", target)

        occupied_mask = np.isfinite(band) & (band != NODATA) & (band > 0)
        occ_rows, occ_cols = np.where(occupied_mask)
        if len(occ_rows) == 0:
            # distinguish extinction from genuine zero-coverage
            extinct = self._extinct(run_dir)
            result_target = target
            return ScorerResult(
                score=0.0,
                value=0.0,
                target=result_target,
                diagnostics={
                    "extinct": extinct,
                    "n_spots": int(len(lats)),
                    "n_in_grid": int(in_grid.sum()),
                    "final_file": final.name,
                },
                passed=False,
            )

        # cell size in km (degrees grid: mean cell extent)
        cell_km = self._cell_size_km(transform)
        cov_by_radius: dict[str, float] = {}
        for r_km in SENSITIVITY_RADII_KM:
            r_cells = r_km / cell_km
            cov = self._coverage(rows, cols, in_grid, occ_rows, occ_cols, r_cells)
            cov_by_radius[f"coverage_r{int(r_km)}km"] = round(cov, 4)
        coverage = cov_by_radius[f"coverage_r{int(RADIUS_KM_DEFAULT)}km"]

        score = 1.0 if coverage >= COVERAGE_TARGET else round(coverage / COVERAGE_TARGET, 4)
        return ScorerResult(
            score=round(float(score), 4),
            value=float(coverage),
            target=target,
            diagnostics={
                "n_spots": int(len(lats)),
                "n_in_grid": int(in_grid.sum()),
                "n_occupied_cells": int(len(occ_rows)),
                "cell_km": round(cell_km, 3),
                "extinct": False,
                "final_file": final.name,
                **cov_by_radius,
            },
            passed=float(score) >= self.min_score,
        )

    @staticmethod
    def _extinct(run_dir: Path) -> bool | None:
        cohort = find_cohort_file(run_dir)
        if cohort is None:
            return None
        try:
            import json

            data = json.loads(cohort.read_text())
            daily = data.get("daily", [])
            return bool(daily) and daily[-1].get("n_adults", 0) == 0
        except (OSError, ValueError):
            return None

    @staticmethod
    def _cell_size_km(transform: Any) -> float:
        import math

        a = abs(transform.a)
        e = abs(transform.e)
        return (a + e) / 2.0 * 111.32

    @staticmethod
    def _coverage(
        rows: np.ndarray,
        cols: np.ndarray,
        in_grid: np.ndarray,
        occ_rows: np.ndarray,
        occ_cols: np.ndarray,
        r_cells: float,
    ) -> float:
        if len(occ_rows) == 0 or not in_grid.any():
            return 0.0
        r2 = float(r_cells * r_cells)
        covered = 0
        total = 0
        for spot_row, spot_col, ok in zip(rows, cols, in_grid):
            if not ok:
                continue
            total += 1
            d2 = (occ_rows - spot_row) ** 2 + (occ_cols - spot_col) ** 2
            if bool((d2 <= r2).any()):
                covered += 1
        return covered / total if total else 0.0
