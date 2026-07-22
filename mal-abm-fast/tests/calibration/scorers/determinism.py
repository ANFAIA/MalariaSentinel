"""D7: Determinism scorer."""
from __future__ import annotations
import hashlib
from collections import defaultdict
from pathlib import Path
from typing import Any

from scorers.base import Scorer, ScorerResult


def _seed_tag(path: Path) -> str:
    name = path.name
    import re
    m = re.search(r"seed(\d+)", name)
    return m.group(0) if m else "default"


class DeterminismScorer(Scorer):
    @property
    def name(self) -> str:
        return "D7_determinism"

    @property
    def weight(self) -> float:
        return 2.0

    def score(self, run_dir: Path, experiment: dict[str, Any]) -> ScorerResult:
        tifs = sorted(run_dir.glob("state_seed*.tif"))
        if not tifs:
            return ScorerResult(score=1.0, value=1.0, target="1.00",
                                diagnostics={"note": "no seed files, assumed OK"})
        groups: dict[str, list[Path]] = defaultdict(list)
        for t in tifs:
            groups[_seed_tag(t)].append(t)
        mismatches = 0
        for tag, files in groups.items():
            if len(files) < 2:
                continue
            hashes = set()
            for f in files:
                h = hashlib.md5(f.read_bytes()).hexdigest()
                hashes.add(h)
            if len(hashes) > 1:
                mismatches += 1
        return ScorerResult(
            score=0.0 if mismatches > 0 else 1.0,
            value=0.0 if mismatches > 0 else 1.0,
            target="1.00",
            diagnostics={"mismatches": mismatches},
            passed=mismatches == 0,
        )