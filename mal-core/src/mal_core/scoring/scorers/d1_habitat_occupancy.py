"""D1: Habitat occupancy rate.

Fraction of HABITAT cells (band 2 > 0, i.e. cells the engine treats as
aquatic-capable habitat) that are actually occupied by adults (band 1
> 0) in the FINAL state snapshot. This is the Anopheles "larval-habitat
occupancy" quantity measured by longitudinal field studies:

- Fillinger et al. 2008 / Majambere et al. 2008 / Ndenga et al. 2011
  (reviewed in Herrera-Varela 2015): on any given sampling date only
  20-50% of aquatic habitats contained anopheline larvae.
- Bogh et al. 2004 (Mbita, Kenya, 20-month survey): on average 67% of
  available habitats colonized by Anopheles per sampling date.
- Ndenga et al. 2011 (western Kenya): 24-41% of habitats positive,
  season-dependent.

Literature band: [0.20, 0.70] occupancy, centered ~0.45. Occupancy 0
(extinction) scores ~0.

References: see papers/anopheles-dynamics/bogh-2004-larval-habitats-mbita.md
and papers/anopheles-dynamics/ndenga-2011-larval-habitats-western-kenya.md.
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
    name = "D1_habitat_occupancy"
    kind = "composite"
    weight = 1.0
    description = "Occupied habitat cells vs literature 20-70% (Bogh 2004; Ndenga 2011)"
    min_score = 0.5
    hard_floor = 0.2

    def score(self, run_dir: Path, ctx: dict[str, Any]) -> ScorerResult:
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
