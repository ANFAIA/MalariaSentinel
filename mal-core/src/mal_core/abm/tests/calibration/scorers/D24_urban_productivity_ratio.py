"""D24: Urban productivity ratio — urban cells carry less vector density
than rural cells when capacity scaling is active.

Plan: `docs/plans/in-process/m17-4-capacity-scaling.md` §6 PR-D.

Compares mean adult vector density (state band 1) in cells where
`urban_class == 30` (GHS-SMOD urban) vs cells where
`urban_class == 50` (GHS-SMOD rural). With the per-patch K_eff from
PR-C, urban cells should carry less density than rural cells at the
same rainfall (urban buildings limit standing-water productivity).

Score: 1.0 if ratio <= 0.7 (urban correctly under-capacity). Falls off
toward 0.0 as ratio approaches 0.95 (no scaling detected). Score = 0.0
if ratio > 0.95 (capacity scaling is broken).

Threshold rationale: with URBAN_CAPACITY_FLOOR = 0.30 (plan §6.4),
dense rural cells have ~3.3x more productive standing water than the
sparsest urban cell. Observed Ghana ratio is ~0.4-0.6 (calibration
target). 0.7 is the conservative upper bound.
"""
from __future__ import annotations
import math
from pathlib import Path
from typing import Any

import numpy as np
import rasterio

from scorers.base import Scorer, ScorerResult, find_state_files


class UrbanProductivityRatioScorer(Scorer):
    @property
    def name(self) -> str:
        return "D24_urban_productivity_ratio"

    @property
    def weight(self) -> float:
        return 0.05  # low weight — guardrail, not driver

    def score(self, run_dir: Path, experiment: dict[str, Any]) -> ScorerResult:
        state_files = find_state_files(run_dir)
        if not state_files:
            return ScorerResult(
                score=0.0, value=0.0, target="<= 0.7",
                diagnostics={"error": "no state files"}, passed=False)

        last_file = state_files[-1]
        with rasterio.open(last_file) as ds:
            density = ds.read(1)  # band 1 = adult_occupancy

        # Locate the urban_class raster. Convention: same AOI dir as
        # the env .nc. The calibration harness resolves
        # `experiment["aoi_dir"]`; fall back to /data/ghana.
        aoi_dir = experiment.get("aoi_dir", "/Users/davidflorezmazuera/Downloads/MalariaSentinel/data/ghana")
        urban_class_path = Path(aoi_dir) / "ghana_urban_class.tif"
        if not urban_class_path.exists():
            return ScorerResult(
                score=0.0, value=0.0, target="<= 0.7",
                diagnostics={"error": f"missing {urban_class_path}"},
                passed=False)

        with rasterio.open(urban_class_path) as ds:
            urban_class = ds.read(1)
            nodata = ds.nodata

        # Mask out nodata + zeros in BOTH grids. Density is non-zero
        # only at active patches; we want to compare apples-to-apples
        # across urban/rural cells.
        mask_d = np.isfinite(density) & (density != -9999.0) & (density > 0)
        mask_u = (urban_class == 30) | (urban_class == 50)
        if nodata is not None:
            mask_u &= (urban_class != nodata)
        # Require same shape (raster align).
        if mask_d.shape != mask_u.shape:
            return ScorerResult(
                score=0.0, value=0.0, target="<= 0.7",
                diagnostics={"error": "shape mismatch"},
                passed=False)

        urban_mask = mask_d & (urban_class == 30)
        rural_mask = mask_d & (urban_class == 50)
        n_urban = int(urban_mask.sum())
        n_rural = int(rural_mask.sum())

        if n_urban < 10 or n_rural < 10:
            # Too few cells of each class for a stable ratio.
            return ScorerResult(
                score=0.0, value=0.0, target="<= 0.7",
                diagnostics={"error": "insufficient cells",
                             "n_urban": n_urban, "n_rural": n_rural},
                passed=False)

        urban_mean = float(density[urban_mask].mean())
        rural_mean = float(density[rural_mask].mean())

        if rural_mean <= 0.0:
            return ScorerResult(
                score=0.0, value=0.0, target="<= 0.7",
                diagnostics={"error": "rural mean <= 0"}, passed=False)

        ratio = urban_mean / rural_mean

        # Score: 1.0 if ratio <= 0.7, Gaussian falloff to 0.0 at 0.95.
        if ratio <= 0.7:
            raw = 1.0
        elif ratio >= 0.95:
            raw = 0.0
        else:
            # Smooth falloff: 0.7 → 1.0, 0.95 → 0.0.
            raw = math.exp(-((ratio - 0.7) / 0.15) ** 2)

        return ScorerResult(
            score=round(raw, 4),
            value=round(ratio, 4),
            target="<= 0.7",
            diagnostics={
                "urban_mean": round(urban_mean, 4),
                "rural_mean": round(rural_mean, 4),
                "n_urban_cells": n_urban,
                "n_rural_cells": n_rural,
            },
            passed=ratio <= 0.7,
        )
