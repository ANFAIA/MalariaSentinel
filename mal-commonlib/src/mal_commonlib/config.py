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
# DEPRECATED: use AOI.from_slug("ghana") from aois.yaml instead.
# These constants are the SRTM DEM crop, not the full national bbox.
AOI_W, AOI_E = -2.966805555532119, 0.787916666690601
AOI_S, AOI_N = 4.692916666659342, 9.792361111104462
DST_CRS = "EPSG:32630"          # UTM zone 30N (Ghana)
DST_RES = 1000                  # metres (1 km working grid)

# --- Environmental layers (contract v3.0 names) ----------------------------
# Retired with pool_hydrology (plan 01 §7): water_frac / ndvi / temperature
# (annual) are gone; the M6-era parabolic suitability surfaces were never
# wired to the redesign habitat contract and are deleted with it.
LAYER_FILES = {
    "rainfall":          "rainfall_1km.tif",
    "air_temp_c":        "air_temp_c_1km.tif",
    "jrc_persistent":    "jrc_persistent_1km.tif",
    "lc_built":          "lc_built_1km.tif",
    "lc_wetland":        "lc_wetland_1km.tif",
    "lc_open_plus_water": "lc_open_plus_water_1km.tif",
    "lc_crop":           "lc_crop_1km.tif",
}

# --- Simulator v1 parameters (Stage 3) ---
# K_MAX retired (2026-10-20, plan 03-retirada-k-max): the C++ ABM uses
# the absolute per-cell habitat capacity K_ref × area × S, explicit
# seeding counts, and a separate --max-population operational guard.
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
    water_thresh: float = WATER_THRESH

    def r_of(self, T):
        return self.r_max * temp_suitability(T)


# Randomization ranges for training rollouts (Stage 4)
PARAM_RANGES = {
    "r_max":       (0.15, 0.45),
    "mu":          (0.10, 0.22),
    "water_thresh": (0.05, 0.20),
}


# --- U-Net / training (Stage 5) ---
PATCH = 64
STRIDE = 48
UNET_CHANNELS = (8, 16, 32, 64)
LOSS_DICE_WEIGHT = 1.0
LOSS_DICE_TAU = 0.05
# Presence threshold for state bands. Contract 4.0: bands carry raw
# per-cell adult counts, so the threshold is expressed in adults
# (0.5 ⇒ any cell with >= 1 adult counts as present).
PRESENCE_THRESH = 0.5
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