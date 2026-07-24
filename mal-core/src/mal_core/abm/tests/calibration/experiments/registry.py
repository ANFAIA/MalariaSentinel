"""Named experiment registry."""
from __future__ import annotations

from experiments.experiment import Experiment

# Default AOI for calibration experiments (resolved via aoi_resolver)
DEFAULT_AOI = "ghana"


def get_default_experiment(aoi: str = DEFAULT_AOI) -> Experiment:
    """Create a default experiment for the given AOI.

    All file paths are resolved via mal_core.prediction.aoi_resolver
    so no AOI-specific paths are hardcoded.
    """
    from mal_core.prediction.aoi_resolver import resolve_aoi

    files = resolve_aoi(aoi)

    return Experiment(
        name=f"{aoi}-default",
        params={
            "ADULT_DAILY_MORT_BASAL": 0.95,
            "ADULT_OPT_C": 25.0,
            "ADULT_SIGMA": 7.0,
            "ADULT_MORT_CAP": 0.95,
            "ADULT_MORT_FLOOR": 0.60,
            "ADULT_DISPERSE_SIGMA_M": 450.0,
            "ADULT_DISPERSE_MAX_M": 2000.0,
            "ADULT_DISPERSE_PROB": 0.10,
            "EIP_BASE_C": 16.0,
            "EIP_THRESHOLD_GD": 110.0,
            "K_MAX": 1000,
            "BIRTH_FECUNDITY": 0.10,
        },
        env_path=str(files.env) if files.env else "",
        habitat_path=str(files.habitat) if files.habitat else "",
        n_days=90,
        seeds=[1, 2, 3, 4, 5],
        seeding_mode="uniform",
        snapshot_every=1,
    )


# Backward compatibility: lazy-evaluated EXPERIMENTS dict
EXPERIMENTS: dict[str, Experiment] = {}


def _ensure_experiments():
    if not EXPERIMENTS:
        EXPERIMENTS["default"] = get_default_experiment()
