"""D20: Washout response scorer (canonical; contract v3.0, 2026-10-17).

Verifies that heavy rain causes a measured washout of aquatic cohorts:
  - A rain event above ``aquatic_stress.wash_threshold_mm`` maps to a
    flush fraction that grows linearly and is capped by
    ``aquatic_stress.wash_fraction_max``.
  - A rain event below that threshold causes no washout.
  - Rain enters as the daily forcing the engine reads (rain_d = daily
    rainfall, not a pool supply state) — the proxy redesign keeps rain
    out of the static habitat planes by design (plan 02 §6).

Both anchors are read from model_constants.yaml (single source).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from mal_core.habitat.config import CONFIG
from mal_core.habitat.aquatic_stress import washout_fraction

from .base import Scorer, ScorerResult

_WASH_MM = float(CONFIG["aquatic_stress"]["wash_threshold_mm"])
_WASH_MAX = float(CONFIG["aquatic_stress"]["wash_fraction_max"])


class WashoutResponseScorer(Scorer):
    """D20: washout response to heavy rain (weighted composite)."""

    name = "D20_washout_response"
    kind = "composite"
    weight = 1.0
    description = (
        f"Heavy rain washes out cohorts: 50mm -> >=0.15 (cap "
        f"{_WASH_MAX} at 80mm); flat below "
        f"{_WASH_MM}mm"
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
        test3_ok = abs(frac_80 - _WASH_MAX) < 0.001

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
                f"{_WASH_MAX}"
            ),
            diagnostics=diagnostics,
            passed=score >= 0.70,
        )
