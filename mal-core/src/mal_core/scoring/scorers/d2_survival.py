"""D2: Adult daily survival.

Mean adult lifespan from the second half of the simulation (steady
state; the first half includes the initial post-seeding crash).

Literature: Saarman 2019 0.87 daily survival; Midega 2007 0.83-0.95
→ mean lifespan 8-15 days. Score: Gaussian around 11 days (sigma 4).
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from .base import Scorer, ScorerResult, find_cohort_file


class SurvivalScorer(Scorer):
    name = "D2_survival"
    kind = "composite"
    weight = 4.0
    description = "Mean adult lifespan vs 8-15 d (Saarman 2019, Midega 2007)"
    min_score = 0.5
    hard_floor = 0.2

    def score(self, run_dir: Path, ctx: dict[str, Any]) -> ScorerResult:
        cohort_path = find_cohort_file(run_dir)
        if cohort_path is None:
            return ScorerResult.skipped(
                "no cohort file (*_cohort.json)", target="8-15 days"
            )
        try:
            data = json.loads(cohort_path.read_text())
        except (json.JSONDecodeError, OSError) as e:
            return ScorerResult.skipped(f"cohort unreadable: {e}", target="8-15 days")
        daily = data.get("daily", [])
        if len(daily) < 8:
            return ScorerResult.skipped(
                f"cohort too short ({len(daily)} days)", target="8-15 days"
            )
        steady = daily[len(daily) // 2 :]
        rates = [
            1.0 - (e.get("n_deaths", 0) / e["n_adults"])
            for e in steady
            if e.get("n_adults", 0) > 0
        ]
        if not rates:
            return ScorerResult.skipped(
                "no valid adult survival days", target="8-15 days"
            )
        p_d = sum(rates) / len(rates)
        mean_life = 1.0 / (1.0 - p_d) if p_d < 1.0 else float("inf")
        score = math.exp(-((mean_life - 11.0) / 4.0) ** 2)
        return ScorerResult(
            score=round(score, 4),
            value=round(mean_life, 2),
            target="8-15 days",
            diagnostics={
                "p_d_mean": round(p_d, 4),
                "n_steady_days": len(steady),
            },
            passed=score >= self.min_score,
        )
