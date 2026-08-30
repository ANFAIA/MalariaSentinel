"""D4: Population stability (no adult collapse, no explosion).

Collapse: min(n_alive) at days 30/60/90 relative to day 0 — target
0.10-0.80. Explosion: max(n_alive)/day0 ≤ 5x. Mean of both sub-scores.

Note: n_alive in the cohort log counts adults; larval stages live in
the aquatic JSONs (see D11).
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from .base import Scorer, ScorerResult, find_cohort_file


class StabilityScorer(Scorer):
    name = "D4_stability"
    kind = "composite"
    weight = 2.0
    description = "Adult population within collapse/explosion bounds"
    min_score = 0.7
    hard_floor = 0.3

    def score(self, run_dir: Path, ctx: dict[str, Any]) -> ScorerResult:
        cohort_path = find_cohort_file(run_dir)
        if cohort_path is None:
            return ScorerResult.skipped(
                "no cohort file (*_cohort.json)",
                target="collapse 0.10-0.80, explosion <=5x",
            )
        try:
            data = json.loads(cohort_path.read_text())
        except (json.JSONDecodeError, OSError) as e:
            return ScorerResult.skipped(
                f"cohort unreadable: {e}",
                target="collapse 0.10-0.80, explosion <=5x",
            )
        daily = data.get("daily", [])
        if len(daily) < 8:
            return ScorerResult.skipped(
                f"cohort too short ({len(daily)} days)",
                target="collapse 0.10-0.80, explosion <=5x",
            )
        series = [e.get("n_alive", 0) for e in daily]
        n_day0 = series[0] if series[0] > 0 else 1
        check_days = [min(d, len(series) - 1) for d in (30, 60, 90)]
        min_alive = min(series[d] for d in check_days)
        max_alive = max(series)
        collapse_ratio = min_alive / n_day0
        explosion_ratio = max_alive / n_day0

        if 0.10 <= collapse_ratio <= 0.80:
            collapse_ok = 1.0
        elif collapse_ratio > 0.80:
            collapse_ok = math.exp(-((collapse_ratio - 0.80) / 0.20) ** 2)
        else:
            collapse_ok = math.exp(-((collapse_ratio - 0.10) / 0.10) ** 2)

        if explosion_ratio <= 5.0:
            explosion_ok = 1.0
        else:
            explosion_ok = math.exp(-((explosion_ratio - 5.0) / 5.0) ** 2)

        score = (collapse_ok + explosion_ok) / 2.0
        return ScorerResult(
            score=round(score, 4),
            value=round(collapse_ratio, 4),
            target="collapse 0.10-0.80, explosion <=5x",
            diagnostics={
                "collapse_ratio": round(collapse_ratio, 4),
                "explosion_ratio": round(explosion_ratio, 4),
                "n_day0": n_day0,
                "n_min": min_alive,
                "n_max": max_alive,
            },
            passed=score >= self.min_score,
        )
