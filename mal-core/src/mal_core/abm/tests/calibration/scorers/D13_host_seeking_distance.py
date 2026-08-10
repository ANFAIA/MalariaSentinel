"""D13: Host-seeking distance — kernel parameters match 70-300m detection range."""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from scorers.base import Scorer, ScorerResult

# Expected detection range for An. gambiae CO₂ + body-odour plume.
# Giraldo 2023: CO₂ ~60m; Spitzen 2013: 60-70m nocturnal;
# Okumu 2013: significant at 70m, activates at 100m;
# Yang 2009: 94% malaria reduction <300m.
EXPECTED_SCALE_M = 100.0
MIN_SCALE_M = 70.0
MAX_SCALE_M = 300.0


class HostSeekingDistanceScorer(Scorer):
    @property
    def name(self) -> str:
        return "D13_host_seeking_distance"

    @property
    def weight(self) -> float:
        return 2.0

    def score(self, run_dir: Path, experiment: dict[str, Any]) -> ScorerResult:
        scale_m = experiment.get("host_seeking_scale_m", EXPECTED_SCALE_M)

        if MIN_SCALE_M <= scale_m <= MAX_SCALE_M:
            raw = math.exp(-((scale_m - EXPECTED_SCALE_M) / 20.0) ** 2)
        else:
            if scale_m < MIN_SCALE_M:
                raw = math.exp(-((MIN_SCALE_M - scale_m) / 10.0) ** 2)
            else:
                raw = math.exp(-((scale_m - MAX_SCALE_M) / 30.0) ** 2)

        return ScorerResult(
            score=round(raw, 4),
            value=round(scale_m, 1),
            target=f"{MIN_SCALE_M}-{MAX_SCALE_M}m (baseline {EXPECTED_SCALE_M}m)",
            diagnostics={
                "kernel_scale_m": scale_m,
                "expected_scale_m": EXPECTED_SCALE_M,
                "within_range": MIN_SCALE_M <= scale_m <= MAX_SCALE_M,
            },
            passed=raw >= 0.70,
        )
