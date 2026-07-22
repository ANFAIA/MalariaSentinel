"""D4: Population stability (no extinction, no explosion)."""
from __future__ import annotations
import json
import math
from pathlib import Path
from typing import Any
from scorers.base import Scorer, ScorerResult

class StabilityScorer(Scorer):
    @property
    def name(self) -> str: return "D4_stability"
    @property
    def weight(self) -> float: return 3.0

    def score(self, run_dir: Path, experiment: dict[str, Any]) -> ScorerResult:
        cohort_path = run_dir / "cohort.json"
        if not cohort_path.exists():
            return ScorerResult(score=0.0, value=0.0, target="0.10-0.80 collapse, <=5.0 explosion",
                              diagnostics={"error": "cohort.json not found"}, passed=False)
        data = json.loads(cohort_path.read_text())
        daily = data.get("daily", [])
        if not daily:
            return ScorerResult(score=0.0, value=0.0, target="0.10-0.80 collapse, <=5.0 explosion",
                              diagnostics={"error": "empty daily data"}, passed=False)
        n_alive_series = [e.get("n_alive", 0) for e in daily]
        n_day0 = n_alive_series[0] if n_alive_series[0] > 0 else 1
        # Collapse ratio: min at day 30/60/90 relative to day 0
        check_days = [min(30, len(n_alive_series)-1), min(60, len(n_alive_series)-1), min(90, len(n_alive_series)-1)]
        min_alive = min(n_alive_series[d] for d in check_days)
        collapse_ratio = min_alive / n_day0
        # Explosion ratio: max over all days
        max_alive = max(n_alive_series)
        explosion_ratio = max_alive / n_day0
        # Collapse score
        if 0.10 <= collapse_ratio <= 0.80:
            collapse_ok = 1.0
        elif collapse_ratio > 0.80:
            collapse_ok = math.exp(-((collapse_ratio - 0.80) / 0.20) ** 2)
        else:
            collapse_ok = math.exp(-((collapse_ratio - 0.10) / 0.10) ** 2)
        # Explosion score
        if explosion_ratio <= 5.0:
            explosion_ok = 1.0
        else:
            explosion_ok = math.exp(-((explosion_ratio - 5.0) / 5.0) ** 2)
        sc = (collapse_ok + explosion_ok) / 2.0
        return ScorerResult(
            score=round(sc, 4),
            value=round(collapse_ratio, 4),
            target="0.10-0.80 collapse, <=5.0 explosion",
            diagnostics={
                "collapse_ratio": round(collapse_ratio, 4),
                "explosion_ratio": round(explosion_ratio, 4),
                "n_day0": n_day0,
                "n_day_min": min_alive,
                "n_day_max": max_alive,
            },
            passed=sc >= 0.70,
        )
