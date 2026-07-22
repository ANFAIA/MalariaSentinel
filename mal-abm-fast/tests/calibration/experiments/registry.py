"""Named experiment registry."""
from __future__ import annotations
from experiments.experiment import Experiment

# Ghana June 2024 env + habitat paths (relative to repo root)
_ENV = "data/runs/ghana/ghana_regional_2024_06_env.tif"
_HAB = "data/runs/ghana/ghana_regional_2024_06_habitat_patches.gpkg"

EXPERIMENTS: dict[str, Experiment] = {
    "default": Experiment(
        name="default",
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
        env_path=_ENV,
        habitat_path=_HAB,
        n_days=90,
        seeds=[1, 2, 3, 4, 5],
        seeding_mode="uniform",
        snapshot_every=1,
    ),
}
