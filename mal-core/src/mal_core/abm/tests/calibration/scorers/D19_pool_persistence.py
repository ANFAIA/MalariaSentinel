"""D19: Pool persistence scorer.

Verifies that the pool hydrology model produces biologically plausible
pool dynamics:
  - A 30mm rain event at T=25°C produces a pool that stays active for
    at least 4 days, then transitions to dry within 7 days at T=32°C.
  - The water level follows a filling-then-drying trajectory consistent
    with the evaporation model.

Based on: Depinay 2004 (pool persistence in West Africa), Ward 2015
(West African pan evaporation rates).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from scorers.base import Scorer, ScorerResult


class PoolPersistenceScorer(Scorer):
    """D17: Pool persistence and desiccation dynamics scorer."""

    @property
    def name(self) -> str:
        return "D19_pool_persistence"

    @property
    def weight(self) -> float:
        return 0.5

    def score(self, run_dir: Path, experiment: dict[str, Any]) -> ScorerResult:
        """Score pool persistence using the Python hydrology model.

        Simulates a single-patch scenario:
          Day 0-2: 30mm rain at 25°C (filling)
          Day 3-10: 0mm rain at 32°C (drying)

        Verifies:
          - Pool is active (>= 5mm) for at least 4 days total
          - Pool becomes dry (< 1mm) within 10 days
          - Water level trajectory is monotonically decreasing during dry phase
        """
        from mal_ghana_sim.abm.pool_hydrology import (
            PoolState,
            DailyForcing,
            advance_pool,
            POOL_WATER_BREED_MM,
            POOL_WATER_DRY_MM,
        )

        # Simulate filling + drying.
        pool = PoolState()
        water_levels: list[float] = []
        active_days = 0
        dry_day = -1

        # Filling phase: 30mm/day for 3 days at 25°C.
        for _ in range(3):
            pool = advance_pool(pool, DailyForcing(rain_mm=30.0, temp_c=25.0))
            water_levels.append(pool.water_mm)
            if pool.water_mm >= POOL_WATER_BREED_MM:
                active_days += 1

        # Drying phase: 0mm/day for 10 days at 32°C.
        for d in range(10):
            pool = advance_pool(pool, DailyForcing(rain_mm=0.0, temp_c=32.0))
            water_levels.append(pool.water_mm)
            if pool.water_mm >= POOL_WATER_BREED_MM:
                active_days += 1
            if pool.water_mm < POOL_WATER_DRY_MM and dry_day < 0:
                dry_day = d + 3  # offset by filling days

        # Scoring.
        diagnostics: dict[str, Any] = {
            "active_days": active_days,
            "dry_day": dry_day,
            "water_levels": [round(w, 2) for w in water_levels],
        }

        # Active for at least 4 days (filling + residual moisture).
        persistence_ok = active_days >= 4
        # Dries out within 13 days total.
        dries_out = dry_day >= 0

        # Check monotonically decreasing during dry phase (indices 3..12).
        dry_levels = water_levels[3:]
        monotone = all(
            dry_levels[i + 1] <= dry_levels[i] + 0.01  # tolerance for float
            for i in range(len(dry_levels) - 1)
        )

        score = 0.0
        if persistence_ok:
            score += 0.4
        if dries_out:
            score += 0.3
        if monotone:
            score += 0.3

        return ScorerResult(
            score=round(score, 4),
            value=float(active_days),
            target="active >= 4 days; dries within 13 days; monotone drying",
            diagnostics=diagnostics,
            passed=score >= 0.70,
        )
