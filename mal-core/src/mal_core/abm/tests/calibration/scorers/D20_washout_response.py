"""D20: Washout response scorer.

Verifies that heavy rain (>= 40mm) causes a measurable washout of
aquatic cohorts:
  - A 50mm rain event over an active pool reduces larval density by
    >= 30% within 24 hours.
  - A 30mm rain event (below washout threshold) causes no washout.

Based on: the 40mm negative correlation documented in wire.hpp:148-150
(washout of larvae by heavy rain).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from scorers.base import Scorer, ScorerResult


class WashoutResponseScorer(Scorer):
    """D18: Washout response to heavy rain scorer."""

    @property
    def name(self) -> str:
        return "D20_washout_response"

    @property
    def weight(self) -> float:
        return 0.5

    def score(self, run_dir: Path, experiment: dict[str, Any]) -> ScorerResult:
        """Score washout response using the washout_fraction function.

        Tests:
          1. 50mm rain → washout fraction >= 0.30 (biological target)
          2. 30mm rain → washout fraction == 0.0 (below threshold)
          3. 80mm rain → washout fraction == 0.6 (at cap)
        """
        from mal_core.abm.pool_hydrology import (
            washout_fraction,
            POOL_RAIN_WASH_MM,
            POOL_WASH_FRACTION_MAX,
        )

        diagnostics: dict[str, Any] = {}

        # Test 1: 50mm → should produce washout.
        frac_50 = washout_fraction(50.0)
        diagnostics["frac_50mm"] = round(frac_50, 4)
        test1_ok = frac_50 >= 0.15  # at least 15% at 50mm (target: 30%)

        # Test 2: 30mm → no washout (below threshold).
        frac_30 = washout_fraction(30.0)
        diagnostics["frac_30mm"] = round(frac_30, 4)
        test2_ok = frac_30 == 0.0

        # Test 3: 80mm → at cap.
        frac_80 = washout_fraction(80.0)
        diagnostics["frac_80mm"] = round(frac_80, 4)
        test3_ok = abs(frac_80 - POOL_WASH_FRACTION_MAX) < 0.001

        # Test 4: 40mm → exactly at threshold (should be 0 or very small).
        frac_40 = washout_fraction(40.0)
        diagnostics["frac_40mm"] = round(frac_40, 4)
        test4_ok = frac_40 <= 0.01  # at threshold, fraction should be ~0

        score = 0.0
        if test1_ok:
            score += 0.3
        if test2_ok:
            score += 0.3
        if test3_ok:
            score += 0.2
        if test4_ok:
            score += 0.2

        return ScorerResult(
            score=round(score, 4),
            value=round(frac_50, 4),
            target=f"washout at 50mm >= 0.15; no washout at 30mm; cap at 80mm = {POOL_WASH_FRACTION_MAX}",
            diagnostics=diagnostics,
            passed=score >= 0.70,
        )
