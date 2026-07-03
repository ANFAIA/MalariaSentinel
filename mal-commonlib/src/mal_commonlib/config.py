"""Configuration: AOI, grid, paths, v1 parameters, weights, randomization ranges.

All values come from DESIGN.md (rev 4, APPROVED). Tunable knobs live here.
"""
from __future__ import annotations

import pathlib
from dataclasses import dataclass, field

# --- Paths ---
REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
DATA_DIR = REPO_ROOT / "data"
PAPERS_DIR = REPO_ROOT / "papers"
TERRAIN_DIR = REPO_ROOT / "terrain"
RUNS_DIR = REPO_ROOT / "runs"
RUNS_DIR.mkdir(exist_ok=True)

# --- Datasets (under data/) ---
DATA_REGIONS = {
    "ghana_idit":   "Ghana IDIT (Univ. Ghana Medical School) — larval sampling",
    "colombia":     "Colombia (occasional Anopheles records)",
    "colombia_vl":  "Colombia VectorLink (PMI) — Pacífico colombiano, HLC + indoor/outdoor",
    "react":        "REACT (IRD) — Burkina Faso + Côte d'Ivoire, HLC + PCR + kdr",
    "guf":          "Guayana Francesa + Amapá (Institut Pasteur) — GBIF historical",
}

SRTM_DEM = TERRAIN_DIR / "srtm_maps/ghana_idit/SRTMGL1_-2.97_0.79_4.69_9.79.tif"
OCCURRENCE = DATA_DIR / "ghana_idit/occurrence.txt"
RUNS = RUNS_DIR
LAYER_DIR = RUNS / "layers"
LAYER_DIR.mkdir(exist_ok=True)
STACK_CACHE = RUNS / "env_stack.npz"

# --- AOI & grid (from the SRTM DEM bounds; metres, not degrees) ---
AOI_W, AOI_E = -2.966805555532119, 0.787916666690601
AOI_S, AOI_N = 4.692916666659342, 9.792361111104462
DST_CRS = "EPSG:32630"          # UTM zone 30N (Ghana)
DST_RES = 1000                  # metres (1 km working grid)

# --- Environmental layers (Stage 1) ---
LAYER_FILES = {
    "elevation":   "elevation_1km.tif",
    "water_frac":  "water_frac_1km.tif",
    "rainfall":    "rainfall_1km.tif",
    "temperature": "temperature_1km.tif",
    "ndvi":        "ndvi_1km.tif",
}

# --- Mordecai et al. 2013 thermal response (v1 parabolic approximation) ---
T_OPT = 25.0
T_HALF_WIDTH = 8.0


def temp_suitability(T):
    """Parabolic thermal suitability in [0,1]. T in degrees C."""
    import numpy as np
    return np.clip(1.0 - ((T - T_OPT) / T_HALF_WIDTH) ** 2, 0.0, 1.0)


def mortality_rate(T):
    """Per-step mortality m(T): ~0.05 at 25C, rising parabolically outside the viable range."""
    import numpy as np
    return 0.05 + 0.2 * np.clip(((T - T_OPT) / T_HALF_WIDTH) ** 2, 0.0, None)


# --- Suitability weights (Stage 2) ---
WEIGHTS = {
    "water_frac": 0.35,
    "rainfall":   0.20,
    "temperature": 0.20,
    "ndvi":       0.15,
    "elevation":  0.10,
}
assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9

# --- Simulator v1 parameters (Stage 3) ---
K_MAX = 1000.0
WATER_THRESH = 0.10
MU = 0.20
R_MAX = 0.30
N_STEPS = 60
T_SNAP = 5
SEED_DENSITY_FRAC = 0.1


@dataclass
class SimParams:
    """One parameter set for a rollout (randomized per rollout in Stage 4)."""
    r_max: float = R_MAX
    mu: float = MU
    k_max: float = K_MAX
    water_thresh: float = WATER_THRESH

    def r_of(self, T):
        return self.r_max * temp_suitability(T)


# Randomization ranges for training rollouts (Stage 4)
PARAM_RANGES = {
    "r_max":       (0.15, 0.45),
    "mu":          (0.10, 0.22),
    "k_max":       (500.0, 1500.0),
    "water_thresh": (0.05, 0.20),
}


# --- U-Net / training (Stage 5) ---
PATCH = 64
STRIDE = 48
UNET_CHANNELS = (8, 16, 32, 64)
LOSS_DICE_WEIGHT = 1.0
LOSS_DICE_TAU = 0.05
PRESENCE_THRESH = 0.05
TRAIN_EPOCHS = 8
TRAIN_LR = 1e-3
TRAIN_BATCH = 32
TRAIN_NUM_WORKERS = 0
N_ROLLOUTS = 20
VAL_SPLIT_LON = -1.0

# --- Validation (Stage 2/5) ---
AUC_N_BACKGROUND = 10_000
AUC_BOOTSTRAP = 1000
AUC_CI_TARGET = 0.65
DICE_TARGET = 0.60