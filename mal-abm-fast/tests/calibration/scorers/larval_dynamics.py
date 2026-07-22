"""D11: Larval dynamics scorer.

Measures the fraction of population in larval vs adult stages.
Target: 30-60% larvae, 5-15% pupae (if 4-stage) or just larvae (if 2-stage).

Based on: Mordecai et al. (2013) "Thermal biology of mosquito-borne disease"
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scorers.base import Scorer, ScorerResult


class LarvalDynamicsScorer(Scorer):
    """D11: Larval population fraction scorer."""

    @property
    def name(self) -> str:
        return "D11_larval_dynamics"

    @property
    def weight(self) -> float:
        return 1.0

    def score(self, run_dir: Path, experiment: dict[str, Any]) -> ScorerResult:
        """Score larval dynamics based on population stage distribution."""
        cohort_path = run_dir / "cohort.json"
        if not cohort_path.exists():
            cohort_files = sorted(run_dir.glob("cohort_seed*.json"))
            if not cohort_files:
                return ScorerResult(
                    score=0.0,
                    value=0.0,
                    target="30-60% larvae fraction",
                    diagnostics={"error": "cohort.json not found"},
                    passed=False,
                )
            cohort_path = cohort_files[0]

        data = json.loads(cohort_path.read_text())
        daily = data.get("daily", [])
        if not daily:
            return ScorerResult(
                score=0.0,
                value=0.0,
                target="30-60% larvae fraction",
                diagnostics={"error": "empty daily data"},
                passed=False,
            )

        # Calculate average larval fraction across all days
        larval_fracs = []
        for day in daily:
            n_alive = day.get("n_alive", 0)
            n_larvae = day.get("n_larvae", 0)
            if n_alive > 0:
                larval_fracs.append(n_larvae / n_alive)

        if not larval_fracs:
            return ScorerResult(
                score=0.0,
                value=0.0,
                target="30-60% larvae fraction",
                diagnostics={"error": "no valid larval fraction data"},
                passed=False,
            )

        avg_larval_frac = sum(larval_fracs) / len(larval_fracs)

        # Target: 30-60% larvae (biological range for Anopheles gambiae)
        # Score: 1.0 if in range, linear decay outside
        if 0.30 <= avg_larval_frac <= 0.60:
            score = 1.0
        elif avg_larval_frac < 0.30:
            # Too few larvae - population may be crashing
            score = max(0.0, avg_larval_frac / 0.30)
        else:
            # Too many larvae - may not be maturing
            score = max(0.0, (0.60 - avg_larval_frac) / 0.30)

        return ScorerResult(
            score=round(score, 4),
            value=round(avg_larval_frac, 4),
            target="30-60% larvae fraction",
            diagnostics={
                "avg_larval_fraction": round(avg_larval_frac, 4),
                "target_range": [0.30, 0.60],
                "n_days": len(daily),
            },
            passed=score >= 0.70,
        )
