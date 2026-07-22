"""D3: EIP completion rate."""
from __future__ import annotations
import json
import math
from pathlib import Path
from typing import Any
from scorers.base import Scorer, ScorerResult

class EIPScorer(Scorer):
    @property
    def name(self) -> str: return "D3_eip"
    @property
    def weight(self) -> float: return 2.0

    def score(self, run_dir: Path, experiment: dict[str, Any]) -> ScorerResult:
        cohort_path = run_dir / "cohort.json"
        if not cohort_path.exists():
            return ScorerResult(score=0.0, value=0.0, target="0.20-0.50",
                              diagnostics={"error": "cohort.json not found"}, passed=False)
        data = json.loads(cohort_path.read_text())
        daily = data.get("daily", [])
        # Find the entry closest to day 30
        day30 = None
        for entry in daily:
            if entry.get("day", 0) == 30:
                day30 = entry
                break
        if day30 is None and len(daily) > 30:
            day30 = daily[30]
        if day30 is None:
            return ScorerResult(score=0.0, value=0.0, target="0.20-0.50",
                              diagnostics={"error": "no day-30 data"}, passed=False)
        eip_frac = day30.get("eip_frac", 0.0)
        # Score: 1.0 if in range, Gaussian otherwise
        if 0.20 <= eip_frac <= 0.50:
            sc = 1.0
        else:
            sc = math.exp(-((eip_frac - 0.35) / 0.15) ** 2)
        return ScorerResult(
            score=round(sc, 4),
            value=round(eip_frac, 4),
            target="0.20-0.50",
            diagnostics={"day30_n_adults": day30.get("n_adults", 0)},
            passed=sc >= 0.30,
        )
