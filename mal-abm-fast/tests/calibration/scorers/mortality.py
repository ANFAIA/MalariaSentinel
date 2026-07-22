"""D2: Adult daily survival (mortality match).

Uses the steady-state approach: compute mean adult lifespan from the
second half of the simulation. The first half is excluded because it
includes the initial population crash from seeding, which is not
representative of steady-state survival.

Note: n_deaths in the cohort log counts adult deaths from the
adult_mortality step (Op 6). The formula p_d = 1 - (n_deaths / n_adults)
gives the daily survival rate. Mean lifespan = 1 / (1 - p_d).
"""
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
            cohort_files = sorted(run_dir.glob("cohort_seed*.json"))
            if not cohort_files:
                return ScorerResult(score=0.0, value=0.0, target="8-15 days",
                                  diagnostics={"error": "cohort.json not found"}, passed=False)
            cohort_path = cohort_files[0]
        data = json.loads(cohort_path.read_text())
        daily = data.get("daily", [])
        if len(daily) < 4:
            return ScorerResult(score=0.0, value=0.0, target="8-15 days",
                              diagnostics={"error": "too few days"}, passed=False)
        # Use second half of simulation (steady state, skip initial crash)
        half = len(daily) // 2
        steady_days = daily[half:]
        # Compute mean daily survival rate from steady-state days
        survival_rates = []
        for entry in steady_days:
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
            diagnostics={"p_d_mean": round(p_d_mean, 4), "n_steady_days": len(steady_days), "n_valid": len(survival_rates)},
            passed=score >= 0.50,
        )
