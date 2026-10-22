"""D20: Washout response scorer (canonical; contract v3.0, 2026-10-17).

Verifies that heavy rain causes a measured washout of aquatic cohorts:
  - A 50 mm rain event maps to a >= 0.15 flush fraction (0.60 cap at
    80 mm preserved from the M14 pool module).
  - A 30 mm rain event (below the 40 mm threshold) causes no washout.
  - Rain enters as the daily forcing the engine reads (rain_d = daily
    rainfall, not a pool supply state) — the proxy redesign keeps rain
    out of the static habitat planes by design (plan 02 §6).

The 40 mm threshold is the M14 heavy-rain washout anchor.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from mal_core.habitat.aquatic_stress import washout_fraction
from mal_core.habitat.constants import (
    AQUATIC_RAIN_WASH_MM,
    AQUATIC_WASHOUT_FRACTION_MAX,
)
from .base import Scorer, ScorerResult


class WashoutResponseScorer(Scorer):
    """D20: washout response to heavy rain (weighted composite)."""

    name = "D20_washout_response"
    kind = "composite"
    weight = 1.0
    description = (
        f"Heavy rain washes out cohorts: 50mm -> >=0.15 (cap "
        f"{AQUATIC_WASHOUT_FRACTION_MAX} at 80mm); flat below "
        f"{AQUATIC_RAIN_WASH_MM}mm"
    )
    min_score = 0.70

    def score(self, run_dir: Path, ctx: dict[str, Any]) -> ScorerResult:
        """Score washout response with the aquatic-stress contract."""
        diagnostics: dict[str, Any] = {}

        # 1. 50 mm -> real washout.
        frac_50 = washout_fraction(50.0)
        diagnostics["frac_50mm"] = round(frac_50, 4)
        test1_ok = frac_50 >= 0.15

        # 2. 30 mm -> no washout (below threshold).
        frac_30 = washout_fraction(30.0)
        diagnostics["frac_30mm"] = round(frac_30, 4)
        test2_ok = frac_30 == 0.0

        # 3. 80 mm -> cap.
        frac_80 = washout_fraction(80.0)
        diagnostics["frac_80mm"] = round(frac_80, 4)
        test3_ok = abs(frac_80 - AQUATIC_WASHOUT_FRACTION_MAX) < 0.001

        # 4. 40 mm -> exactly at threshold (~0).
        frac_40 = washout_fraction(40.0)
        diagnostics["frac_40mm"] = round(frac_40, 4)
        test4_ok = frac_40 <= 0.01

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
            target=(
                f"washout at 50mm >= 0.15; none at 30mm; cap at 80mm = "
                f"{AQUATIC_WASHOUT_FRACTION_MAX}"
            ),
            diagnostics=diagnostics,
            passed=score >= 0.70,
        )
