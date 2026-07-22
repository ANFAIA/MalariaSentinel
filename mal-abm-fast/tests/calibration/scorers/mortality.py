"""D2: Adult daily survival (mortality match)."""
from __future__ import annotations
import json
import math
from pathlib import Path
from typing import Any
from scorers.base import Scorer, ScorerResult

class MortalityScorer(Scorer):
    @property
    def name(self) -> str: return "D2_survival"
    @property
    def weight(self) -> float: return 3.0

    def score(self, run_dir: Path, experiment: dict[str, Any]) -> ScorerResult:
        cohort_path = run_dir / "cohort.json"
        if not cohort_path.exists():
            return ScorerResult(score=0.0, value=0.0, target="8-15 days",
                              diagnostics={"error": "cohort.json not found"}, passed=False)
        data = json.loads(cohort_path.read_text())
        daily = data.get("daily", [])
        # Compute mean daily survival rate from days with n_adults > 0
        survival_rates = []
        for entry in daily:
            n_adults = entry.get("n_adults", 0)
            n_deaths = entry.get("n_deaths", 0)
            if n_adults > 0:
                p_d = 1.0 - (n_deaths / n_adults)
                survival_rates.append(p_d)
        if not survival_rates:
            return ScorerResult(score=0.0, value=0.0, target="8-15 days",
                              diagnostics={"error": "no valid survival data"}, passed=False)
        p_d_mean = sum(survival_rates) / len(survival_rates)
        mean_life = 1.0 / (1.0 - p_d_mean) if p_d_mean < 1.0 else float('inf')
        # Score: Gaussian around 11.0 days, sigma=4.0
        score = math.exp(-((mean_life - 11.0) / 4.0) ** 2)
        return ScorerResult(
            score=round(score, 4),
            value=round(mean_life, 2),
            target="8-15 days",
            diagnostics={"p_d_mean": round(p_d_mean, 4), "n_valid_days": len(survival_rates)},
            passed=score >= 0.50,
        )
