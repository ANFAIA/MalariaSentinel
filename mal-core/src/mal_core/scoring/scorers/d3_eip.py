"""D3: EIP (extrinsic incubation period) completion dynamics.

The cohort log records ``eip_frac`` = fraction of infected mosquitoes
whose EIP has completed. Without the transmission module enabled the
field is degenerate (constant 1.0 from seeding) — in that case the
scorer reports ``skipped`` rather than punishing the run.

With transmission on, the target is a completed-EIP fraction of
0.20-0.50 at day 30 (Mordecai 2013: Briere optimum 25 C, EIP 11-14 d
at 25-28 C).
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from .base import Scorer, ScorerResult, find_cohort_file


class EIPScorer(Scorer):
    name = "D3_eip"
    kind = "composite"
    weight = 3.0
    description = "Completed-EIP fraction at day 30 vs 0.20-0.50 (transmission runs)"
    min_score = 0.3
    hard_floor = 0.1

    def score(self, run_dir: Path, ctx: dict[str, Any]) -> ScorerResult:
        cohort_path = find_cohort_file(run_dir)
        if cohort_path is None:
            return ScorerResult.skipped(
                "no cohort file (*_cohort.json)", target="0.20-0.50"
            )
        try:
            data = json.loads(cohort_path.read_text())
        except (json.JSONDecodeError, OSError) as e:
            return ScorerResult.skipped(f"cohort unreadable: {e}", target="0.20-0.50")
        daily = data.get("daily", [])
        if not daily:
            return ScorerResult.skipped("empty cohort", target="0.20-0.50")

        eip_values = [e.get("eip_frac", 0.0) for e in daily]
        if len(set(eip_values)) <= 1:
            return ScorerResult.skipped(
                "eip_frac is constant — transmission dynamics not recorded "
                "(enable --enable-transmission)",
                target="0.20-0.50",
            )

        day30 = next((e for e in daily if e.get("day") == 30), daily[-1])
        eip_frac = day30.get("eip_frac", 0.0)
        if 0.20 <= eip_frac <= 0.50:
            score = 1.0
        else:
            score = math.exp(-((eip_frac - 0.35) / 0.15) ** 2)
        return ScorerResult(
            score=round(score, 4),
            value=round(eip_frac, 4),
            target="0.20-0.50",
            diagnostics={"day": day30.get("day"), "n_days": len(daily)},
            passed=score >= self.min_score,
        )
