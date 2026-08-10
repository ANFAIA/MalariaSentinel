"""Composite score: weighted geometric mean of D1..D18."""
from __future__ import annotations
import math
from scorers.base import ScorerResult

DEFAULT_WEIGHTS: dict[str, float] = {
    "D1_expansion": 2.0, "D2_survival": 3.0, "D3_eip": 2.0,
    "D4_stability": 3.0, "D5_morans": 1.0, "D6_mass": 2.0,
    "D7_determinism": 2.0, "D8_coupling": 2.0, "D9_activation": 1.0, "D10_perf": 1.0,
    "D11_larval_dynamics": 1.0,
    "D12_host_density": 2.0, "D13_host_seeking_distance": 2.0,
    "D14_mobility_conservation": 2.0,
    "D15_long_horizon_persistence": 3.0,
    "D16_suitability_auc": 2.0,
    "D17_pool_persistence": 0.5,
    "D18_washout_response": 0.5,
    # Plan D spatial scorers (kernel expansion + oviposition).
    "D16_spread_rate": 0.15,
    "D17_host_clustering": 0.10,
    "D18_oviposition_fidelity": 0.10,
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