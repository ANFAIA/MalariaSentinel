"""Configuration: AOI, grid, paths, v1 parameters, weights, randomization ranges.

All values come from DESIGN.md (rev 4, APPROVED). Tunable knobs live here.
"""
from __future__ import annotations

import pathlib
from dataclasses import dataclass, field

# --- Paths ---
REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
SRTM_DEM = REPO_ROOT / "terrain/srtm_maps/ghana_idit/SRTMGL1_-2.97_0.79_4.69_9.79.tif"
OCCURRENCE = REPO_ROOT / "data/ghana_idit/occurrence.txt"
RUNS = REPO_ROOT / "runs"
RUNS.mkdir(exist_ok=True)

# --- AOI & grid (from the SRTM DEM bounds; metres, not degrees) ---
AOI_W, AOI_E = -2.966805555532119, 0.787916666690601
AOI_S, AOI_N = 4.692916666659342, 9.792361111104462
DST_CRS = "EPSG:32630"          # UTM zone 30N (Ghana)
DST_RES = 1000                  # metres (1 km working grid)

# --- Environmental layers (Stage 1) ---
# name -> (relative_path_under_runs/layers, source_url_or_note)
LAYER_FILES = {
    "elevation":   "elevation_1km.tif",      # from SRTM (local)
    "water_frac":  "water_frac_1km.tif",     # JRC GSW occurrence -> binary -> mean
    "rainfall":    "rainfall_1km.tif",       # CHIRPSclim v2.0 annual mean
    "temperature": "temperature_1km.tif",    # WorldClim 2.1 BIO1 (annual mean, deg C)
    "ndvi":        "ndvi_1km.tif",           # MODIS MOD13A2 multi-year annual mean
}
LAYER_DIR = RUNS / "layers"
LAYER_DIR.mkdir(exist_ok=True)
STACK_CACHE = RUNS / "env_stack.npz"

# --- Mordecai et al. 2013 thermal response (v1 parabolic approximation) ---
# Optimum 25 deg C, zero outside ~17-33 deg C. Used for both reproduction r(T)
# and the suitability overlay temperature channel.
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
    "temperature": 0.20,   # applied as temp_suitability(T), not raw T
    "ndvi":       0.15,
    "elevation":  0.10,
}
assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9

# --- Simulator v1 parameters (Stage 3) ---
K_MAX = 1000.0          # carrying capacity at max suitability (mosquitoes/cell)
WATER_THRESH = 0.10     # water_frac above which breeding occurs
MU = 0.20               # diffusion coefficient (<=0.25 stable for 4-neighbour laplacian)
R_MAX = 0.30            # max logistic growth rate; effective r(T) = R_MAX * temp_suitability(T)
N_STEPS = 60            # rollout length (~2 months, 1 step ~ 1 day)
T_SNAP = 5              # snapshot interval (weekly) -> 12 transition pairs/rollout
SEED_DENSITY_FRAC = 0.1 # D_0 = SEED_DENSITY_FRAC * K at seeded cells


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
STRIDE = 48           # denser sampling so presence patches are numerous enough
UNET_CHANNELS = (8, 16, 32, 64)
LOSS_DICE_WEIGHT = 1.0
LOSS_DICE_TAU = 0.05  # soft-Dice relaxation temperature
PRESENCE_THRESH = 0.05 # D_norm > thresh => "presence" (eval metric, hard)
TRAIN_EPOCHS = 8
TRAIN_LR = 1e-3
TRAIN_BATCH = 32
TRAIN_NUM_WORKERS = 0
N_ROLLOUTS = 20       # v1 demo (keeps training fast; production bar is >=100)
VAL_SPLIT_LON = -1.0  # sub-region split: west of this -> train, east -> val (~80/20)

# --- Validation (Stage 2/5) ---
AUC_N_BACKGROUND = 10_000
AUC_BOOTSTRAP = 1000
AUC_CI_TARGET = 0.65   # lower 95% bootstrap bound must exceed this
DICE_TARGET = 0.60     # surrogate-vs-simulator front-overlap
