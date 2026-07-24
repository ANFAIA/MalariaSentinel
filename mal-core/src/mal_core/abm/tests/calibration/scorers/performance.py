"""D10: Performance scorer."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

from scorers.base import Scorer, ScorerResult


class PerformanceScorer(Scorer):
    @property
    def name(self) -> str:
        return "D10_perf"

    @property
    def weight(self) -> float:
        return 1.0

    def score(self, run_dir: Path, experiment: dict[str, Any]) -> ScorerResult:
        meta_path = run_dir / "run_metadata.json"
        if not meta_path.exists():
            return ScorerResult(score=1.0, value=0.0, target="<=30s",
                                diagnostics={"note": "no metadata, assumed OK"})
        meta = json.loads(meta_path.read_text())
        wall_s = meta.get("wall_s", 0.0)
        if wall_s <= 0:
            return ScorerResult(score=1.0, value=wall_s, target="<=30s",
                                diagnostics={"note": "wall_s<=0, assumed OK"})
        raw_score = min(1.0, 30.0 / wall_s)
        return ScorerResult(
            score=raw_score,
            value=wall_s,
            target="<=30s",
            passed=wall_s <= 30.0,
        )