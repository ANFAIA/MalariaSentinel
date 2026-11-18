"""D1: Habitat occupancy rate.

Fraction of HABITAT cells (band 2 > 0, i.e. cells the engine treats as
aquatic-capable habitat) that are actually occupied by adults (band 1
> 0) in the FINAL state snapshot. This is the Anopheles "larval-habitat
occupancy" quantity measured by longitudinal field studies:

- Fillinger et al. 2008 / Majambere et al. 2008 / Ndenga et al. 2011
  (reviewed in Herrera-Varela 2015): on any given sampling date only a
  fraction of aquatic habitats contained anopheline larvae.
- Bogh et al. 2004 (Mbita, Kenya, long survey): average share of
  available habitats colonized by Anopheles per sampling date.
- Ndenga et al. 2011 (western Kenya): season-dependent positive
  habitat share.

The literature band and Gaussian centring live in ``OCC_BAND`` /
``OCC_CENTER`` / ``OCC_SIGMA`` below. Occupancy 0 (extinction) scores ~0.

References: doi:10.1111/j.1365-3156.2004.01335.x (Bogh et al. 2004) and
doi:10.1186/1475-2875-10-81 (Ndenga et al. 2011).
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import numpy as np
import rasterio

from .base import NODATA, Scorer, ScorerResult, find_final_state

OCC_BAND = [0.20, 0.70]
OCC_CENTER = 0.45
OCC_SIGMA = 0.15


class HabitatOccupancyScorer(Scorer):
    """Measures the share of aquatic-capable habitat cells that are
    actually occupied by adults in the final snapshot.

    This is the field "larval-habitat occupancy" fraction reported by
    longitudinal surveys (Bogh 2004; Ndenga 2011). A score of 1 means
    the occupancy falls inside the literature band declared in
    ``OCC_BAND``; outside it the score falls off as a Gaussian around
    ``OCC_CENTER``, so 0 (no habitat occupied) scores 0.
    """

    name = "D1_habitat_occupancy"
    kind = "composite"
    weight = 1.0
    description = "Occupied habitat cells vs literature 20-70% (Bogh 2004; Ndenga 2011)"
    min_score = 0.5
    hard_floor = 0.2

    def score(self, run_dir: Path, ctx: dict[str, Any]) -> ScorerResult:
        """Compute the habitat occupancy fraction and its score.

        Returns the occupied share of habitat cells as the value, or a
        skipped result when the run has no state snapshot or no habitat
        cells at all.
        """
        target = "0.20-0.70 of habitat cells occupied"
        final = find_final_state(run_dir)
        if final is None:
            return ScorerResult.skipped("no state files", target)
        with rasterio.open(final) as ds:
            density = ds.read(1)
            habitat = ds.read(2)
        valid_d = np.isfinite(density) & (density != NODATA)
        valid_h = np.isfinite(habitat) & (habitat != NODATA)
        habitat_cells = valid_h & (habitat > 0)
        n_habitat = int(habitat_cells.sum())
        if n_habitat == 0:
            return ScorerResult.skipped("no habitat cells (band 2 empty)", target)
        occupied = valid_d & (density > 0) & habitat_cells
        occupancy = int(occupied.sum()) / n_habitat
        lo, hi = OCC_BAND
        if lo <= occupancy <= hi:
            score = 1.0
        else:
            score = max(0.0, math.exp(-((occupancy - OCC_CENTER) / OCC_SIGMA) ** 2))
        return ScorerResult(
            score=round(score, 4),
            value=float(occupancy),
            target=target,
            diagnostics={
                "occupied_habitat_cells": int(occupied.sum()),
                "habitat_cells": n_habitat,
                "final_file": final.name,
            },
            passed=score >= self.min_score,
        )
