"""Composite score: weighted geometric mean of D1..D10."""
from __future__ import annotations
import math
from scorers.base import ScorerResult

DEFAULT_WEIGHTS: dict[str, float] = {
    "D1_expansion": 2.0, "D2_survival": 3.0, "D3_eip": 2.0,
    "D4_stability": 3.0, "D5_morans": 1.0, "D6_mass": 2.0,
    "D7_determinism": 2.0, "D8_coupling": 2.0, "D9_activation": 1.0, "D10_perf": 1.0,
    "D11_larval_dynamics": 1.0,
}

def geometric_mean(scores: dict[str, ScorerResult], weights: dict[str, float] | None = None) -> float:
    w = weights or DEFAULT_WEIGHTS
    total_weight = 0.0
    log_sum = 0.0
    for dim, result in scores.items():
        wi = w.get(dim, 1.0)
        if result.score <= 0.0:
            return 0.0
        log_sum += wi * math.log(result.score)
        total_weight += wi
    if total_weight <= 0.0:
        return 0.0
    return math.exp(log_sum / total_weight)