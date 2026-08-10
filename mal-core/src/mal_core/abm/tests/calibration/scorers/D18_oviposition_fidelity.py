"""D18: Oviposition fidelity — eggs concentrated at preferred patches.

Measures the ratio of eggs per patch in the top tertile vs uniform
baseline. Target: >= 1.5 (patches are not uniformly used).

Source: Lindh 2015 (gravid site preference), Mwingira 2020
(chemical attractants concentrate oviposition).
"""
from __future__ import annotations
import math
import json
from pathlib import Path
from typing import Any

from scorers.base import Scorer, ScorerResult, find_cohort_file


class OvipositionFidelityScorer(Scorer):
    @property
    def name(self) -> str:
        return "D18_oviposition_fidelity"

    @property
    def weight(self) -> float:
        return 0.10

    def score(self, run_dir: Path, experiment: dict[str, Any]) -> ScorerResult:
        cohort_file = find_cohort_file(run_dir)
        if not cohort_file:
            return ScorerResult(score=0.0, value=0.0, target=">= 1.5",
                                diagnostics={"error": "no cohort file"}, passed=False)

        try:
            data = json.loads(cohort_file.read_text())
        except Exception as e:
            return ScorerResult(score=0.0, value=0.0, target=">= 1.5",
                                diagnostics={"error": str(e)}, passed=False)

        # Extract egg counts per patch from cohort data.
        # The cohort JSON has patch_id → {eggs, larvae, pupae} structure.
        egg_counts = []
        if isinstance(data, dict):
            for pid, info in data.items():
                if isinstance(info, dict) and "eggs" in info:
                    egg_counts.append(info["eggs"])
                elif isinstance(info, (int, float)):
                    egg_counts.append(info)

        if not egg_counts or sum(egg_counts) == 0:
            return ScorerResult(score=0.0, value=0.0, target=">= 1.5",
                                diagnostics={"error": "no egg data"}, passed=False)

        counts = sorted(egg_counts, reverse=True)
        n = len(counts)
        if n < 3:
            # Too few patches — score based on concentration.
            ratio = max(counts) / (sum(counts) / n) if sum(counts) > 0 else 1.0
        else:
            # Top tertile average / overall average.
            top_tertile = counts[: n // 3]
            top_avg = sum(top_tertile) / len(top_tertile)
            overall_avg = sum(counts) / n
            ratio = top_avg / overall_avg if overall_avg > 0 else 1.0

        # Score: 1.0 if ratio >= 1.5, Gaussian falloff otherwise.
        if ratio >= 1.5:
            raw = 1.0
        else:
            raw = math.exp(-((ratio - 1.5) / 0.5) ** 2)

        return ScorerResult(
            score=round(raw, 4),
            value=round(ratio, 4),
            target=">= 1.5",
            diagnostics={"top_tertile_ratio": ratio, "n_patches": n},
            passed=ratio >= 1.5,
        )
