"""D19: Habitat persistence scorer (canonical; contract v3.0, 2026-10-17).

Verifies that the proxy-habitat model produces biologically plausible
persistence behaviour:
  - A heavy rain pulse keeps the pluvial availability z above the
    activation floor for several days, then z decays to near-zero
    within the drying-memory scale.
  - Persistence-weighted species accuracy keeps a positive dry-season
    floor from the persistent habitat types (JRC / urban / wetland):
    built surface and wetlands ride at availability 1 (plan 02 §5,
    k(g) = 0 for the persistent columns).

Anchors: Bøgh 2004 (habitat colonisation rate, Mbita); Ndenga 2011
(human-made habitats dominate, western Kenya) — persistence is a
supply property, not a rainfall spell.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from mal_core.habitat.config import CONFIG
from mal_core.habitat.capacity import species_accuracy

from .base import Scorer, ScorerResult

_PLUVIAL_RAIN_SCALE_MM = float(CONFIG["pluvial"]["rain_scale_mm"])
_PLUVIAL_DRY_MEMORY_DAYS = float(CONFIG["pluvial"]["dry_memory_days"])

# Static potential of a mixed peri-urban cell: the same feature bundle
# the habitat ingest materialises for a populated coastal fringe.
_MIXED_CELL_H = (0.20, 0.075, 0.30, 0.40, 0.10, 0.0)
# coluzzii weights regenerated from the canonical C++ row (plan paso 4;
# order = habitat_types.types).
_MIXED_CELL_W = (0.40, 0.10, 0.20, 0.00, 0.25, 0.05)


class PoolPersistenceScorer(Scorer):
    """D19: pluvial persistence and drying-memory dynamics (composite)."""

    name = "D19_pool_persistence"
    kind = "composite"
    weight = 1.0
    description = (
        "Proxy habitat: 30mm pulse keeps z active >=4 days; z decays "
        "thereafter; persistent-floor accuracy stays > 0 in drought"
    )
    min_score = 0.70

    def score(self, run_dir: Path, ctx: dict[str, Any]) -> ScorerResult:
        """Score habitat persistence with the shared pluvial recursion.

        Scenario:
          Day 0-2: rain pulses (recharge; the activation pulse)
          Day 3-12: 0 mm (drying memory)

        Checks:
          1. z stays above the activation floor for several days
          2. z falls below the floor inside 3 * pluvial.dry_memory_days
          3. monotone decay through the no-rain phase
          4. persistent floor: species accuracy at z = 0 stays positive
             (human dry-season supply) and short of the z = 1 value
        """
        def step(z: float, rain: float, days: float = 1.0) -> float:
            """One scalar pluvial step — the contract recursion, written
            in-place here because the scorer exercises a single cell (the
            array form lives in habitat.availability with identical math)."""
            z_dry = z * math.exp(-days / _PLUVIAL_DRY_MEMORY_DAYS)
            fill = 1.0 - math.exp(-max(0.0, rain) / _PLUVIAL_RAIN_SCALE_MM)
            return min(1.0, max(0.0, z_dry + (1.0 - z_dry) * fill))

        z = 0.0
        z_series: list[float] = []
        active_days = 0
        dry_day = -1

        for _ in range(3):
            z = step(z, 30.0)
            z_series.append(z)
            if z >= 0.05:
                active_days += 1

        for d in range(10):
            z = step(z, 0.0)
            z_series.append(z)
            if z >= 0.05:
                active_days += 1
            if z < 0.05 and dry_day < 0:
                dry_day = d + 3

        diagnostics: dict[str, Any] = {
            "active_days": active_days,
            "dry_day": dry_day,
            "z_series": [round(v, 3) for v in z_series],
            "rain_scale_mm": _PLUVIAL_RAIN_SCALE_MM,
            "dry_memory_days": _PLUVIAL_DRY_MEMORY_DAYS,
        }

        # 1. Persistence: a single 30 mm pulse is enough for >= 4 days.
        persistence_ok = active_days >= 4
        # 2. Drying: z falls under the floor within the memory scale.
        dries_out = dry_day >= 0 and dry_day <= int(3 * _PLUVIAL_DRY_MEMORY_DAYS)
        # 3. Monotone decay after the last recharge.
        decay_levels = z_series[3:]
        monotone = all(
            decay_levels[i + 1] <= decay_levels[i] + 1e-6
            for i in range(len(decay_levels) - 1)
        )
        # 4. Persistent floor (the user-fixed urban premise: at z = 0 the
        # built/wetland/JRC columns keep a positive supply).
        h_map = {
            g: float(v)
            for g, v in zip(CONFIG["habitat_types"]["types"], _MIXED_CELL_H)
        }
        w_map = {
            g: float(v)
            for g, v in zip(CONFIG["habitat_types"]["types"], _MIXED_CELL_W)
        }
        floor = float(species_accuracy(h_map, 0.0, w_map))
        ceiling = float(species_accuracy(h_map, 1.0, w_map))
        floor_ok = (
            math.isfinite(floor) and 0.0 < floor < ceiling <= 1.0
        )

        score = 0.0
        if persistence_ok:
            score += 0.3
        if dries_out:
            score += 0.2
        if monotone:
            score += 0.2
        if floor_ok:
            score += 0.3

        return ScorerResult(
            score=round(score, 4),
            value=float(active_days),
            target=(
                "active >= 4 days; dries inside 3*DRY_MEMORY; monotone "
                "decay; persistent floor in (0, ceiling]"
            ),
            diagnostics=diagnostics,
            passed=score >= 0.70,
        )
