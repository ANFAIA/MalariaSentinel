---
name: ghana-pipeline
description: Run the Ghana malaria simulation pipeline end-to-end. Covers environment ingestion, habitat suitability modeling, reaction-diffusion simulation, U-Net training, and risk-expansion mapping. Use when running Ghana simulations, training U-Net models, or generating risk maps.
---

# Ghana Simulation Pipeline

End-to-end guide for running the MalariaSentinel Ghana malaria spread simulation and U-Net surrogate pipeline. The pipeline ingests satellite environmental rasters, builds a habitat-suitability field, runs a mechanistic reaction-diffusion simulator, trains a U-Net transition surrogate, and produces risk-expansion maps.

## New: Unified Pipeline (M9)

As of M9, the primary way to run ABM simulations is through the unified pipeline in `mal-core`:

```bash
# Run the full pipeline (ingest → ABM → score → train → predict)
malariasim run --aoi ghana --stages ingest,abm,score --days 90 --seed 1

# Run individual stages
malariasim ingest --aoi ghana --year 2024 --month 6
malariasim abm --aoi ghana --year 2024 --month 1 --days 90 --seed 1
malariasim score --run-dir runs/pipeline/
malariasim train --run-dir runs/abm/ --epochs 50
malariasim feedback --run-dir runs/pipeline/
```

### Data organization

All Ghana data lives in `data/ghana/`:

| File | Purpose | ABM flag |
|---|---|---|
| `ghana_regional_2024_2025_env.nc` | Daily env tensor (731 days, 4 vars) | `--env` |
| `ghana_regional_2024_06_habitat_patches.gpkg` | Habitat patches | `--habitat` |
| `host_static.nc` | Host density (5 vars) | `--hosts` |
| `human_mobility_day.csr` | Day mobility matrix | `--human-mobility-day` |
| `human_mobility_night.csr` | Night mobility matrix | `--human-mobility-night` |
| `livestock_mobility_season.csr` | Livestock mobility | `--livestock-mobility` |
| `manifest.json` | AOI data manifest | (used by aoi_resolver) |

### Adding a new AOI

1. Create `data/<aoi>/manifest.json` listing all data files
2. Run `malariasim ingest --aoi <aoi>` to build env tensor
3. Run `malariasim abm --aoi <aoi>` to simulate

The system is AOI-agnostic: `mal_core.prediction.aoi_resolver` resolves paths from the manifest.

## 1. Pipeline Overview

> **Note**: The sections below describe the original mal-ghana-sim reaction-diffusion pipeline (stages 1-6). For the ABM-based pipeline, see the "New: Unified Pipeline (M9)" section above.

The pipeline has 6 stages, each with a dedicated script:

| Stage | Script | What it does |
|---|---|---|
| 1. Ingest | `01_ingest.py` | Reproject & resample env rasters to a common 1 km EPSG:32630 grid |
| 2. Suitability | `02_suitability.py` | Weighted overlay + Mordecai thermal curve → carrying-capacity field K |
| 3. Simulate | `03_simulate.py` | Fisher-KPP reaction-diffusion simulator; seed from occurrence sites; snapshot every T=5 steps |
| 4. Dataset | `04_build_dataset.py` | Generate rollouts with randomized params → transition pairs → patch tiling + augmentation |
| 5. Train | `05_train.py` | Train U-Net transition surrogate (MSE + soft-Dice loss) on GPU |
| 6. Predict & map | `06_predict_and_map.py` | Rollout from seed (sim + U-Net); render side-by-side risk-expansion map |

### Data layers

| Layer | Source | Resolution | Notes |
|---|---|---|---|
| Elevation | SRTMGL1 | 30 m → 1 km | Mean-aggregated |
| Water fraction | JRC Global Surface Water (occurrence) | 30 m → 1 km | Threshold ≥10 → binary → fraction per cell |
| Rainfall | CHIRPSclim v2.0 annual mean | ~5 km → 1 km | Resampled |
| Temperature | WorldClim 2.1 BIO1 (annual mean °C) | ~1 km | Applied through parabolic suitability curve s(T) |
| NDVI | MODIS MOD13A2 multi-year annual mean | 1 km | Requires NASA Earthdata login; optional in v1 |

### Key parameters (all in `config.py`)

| Parameter | Value | Meaning |
|---|---|---|
| AOI | lon[-2.97, 0.79] lat[4.69, 9.79] | Northern Ghana / Tolon region |
| Grid | EPSG:32630 @ 1000 m | UTM zone 30N, 1 km working resolution |
| Water weight | 0.35 | Highest suitability driver |
| Rainfall weight | 0.20 | |
| Temperature weight | 0.20 | Applied as s(T) = max(0, 1 − ((T−25)/8)²) |
| NDVI weight | 0.15 | |
| Elevation weight | 0.10 | |
| r_max | 0.30 | Max logistic growth rate (temperature-gated) |
| μ (diffusion) | 0.20 | 4-neighbor Laplacian (stable ≤ 0.25) |
| K_max | 1000 | Carrying capacity at max suitability |
| water_thresh | 0.10 | Water fraction above which breeding occurs |
| N_STEPS | 60 | Rollout length (~2 months, 1 step ≈ 1 day) |
| T_SNAP | 5 | Snapshot interval → 12 transition pairs per rollout |

## 2. Prerequisites

- Project setup complete (`uv sync --all-packages` from repo root)
- Data restored: `python scripts/restore_data.py` (from repo root) or raw rasters in place
- For U-Net training (Stage 5): **GPU required** (CPU training is infeasible for production)
- MODIS NDVI is optional in v1; if absent, its 0.15 weight is auto-redistributed

## 3. Running the Pipeline

All commands run from the `mal-ghana-sim/` directory:

```bash
cd mal-ghana-sim

# Stage 1: Ingest & reproject env rasters (one-time, add --download to fetch missing layers)
uv run python scripts/01_ingest.py --download

# Stage 2: Suitability field + AUC validation
uv run python scripts/02_suitability.py

# Stage 3: Reaction-diffusion simulator
uv run python scripts/03_simulate.py

# Stage 4: Build dataset (optional — training does this internally)
uv run python scripts/04_build_dataset.py

# Stage 5: Train U-Net (args: n_rollouts epochs, defaults: 20 rollouts, 8 epochs)
uv run python scripts/05_train.py [n_rollouts] [epochs]

# Stage 6: Predict & render risk-expansion map
uv run python scripts/06_predict_and_map.py
```

**Quick smoke test** (Stages 1–3 only, no GPU needed):

```bash
cd mal-ghana-sim
uv run python scripts/01_ingest.py --download
uv run python scripts/02_suitability.py
uv run python scripts/03_simulate.py
```

**Full pipeline** (requires GPU for Stage 5):

```bash
cd mal-ghana-sim
uv run python scripts/01_ingest.py --download
uv run python scripts/02_suitability.py
uv run python scripts/03_simulate.py
uv run python scripts/05_train.py 20 8
uv run python scripts/06_predict_and_map.py
```

## 4. Configuration

All parameters live in `mal-ghana-sim/src/mal_ghana_sim/config.py`. Key sections:

- **AOI & grid**: `AOI_W/E/S/N`, `DST_CRS = "EPSG:32630"`, `DST_RES = 1000`
- **Layer files**: `LAYER_FILES` dict mapping layer name to filename under `runs/layers/`
- **Suitability weights**: `WEIGHTS` dict (water=0.35, rainfall=0.20, temperature=0.20, NDVI=0.15, elevation=0.10); must sum to 1.0
- **Mordecai thermal curve**: `T_OPT = 25.0`, `T_HALF_WIDTH = 8.0`; functions `temp_suitability(T)` and `mortality_rate(T)`
- **Simulator params**: `SimParams` dataclass with `r_max`, `mu`, `k_max`, `water_thresh`
- **Training randomization**: `PARAM_RANGES` dict for rollout parameter sampling
- **U-Net config**: `PATCH = 64`, `STRIDE = 48`, `UNET_CHANNELS = (8, 16, 32, 64)`, loss weights
- **Validation targets**: `AUC_CI_TARGET = 0.65`, `DICE_TARGET = 0.60`

To tune parameters, edit `config.py` directly. All scripts import from there.

## 5. Understanding the Output

All outputs go to the `runs/` directory (gitignored):

| Artifact | Path | Description |
|---|---|---|
| Env stack | `runs/env_stack.npz` | Cached (5, H, W) float32 array of reprojected layers |
| Layer GeoTIFFs | `runs/layers/*.tif` | Individual reprojected rasters |
| Suitability map | `runs/suitability_static.png` | Habitat suitability heatmap with AUC annotation |
| Sim rollout frames | `runs/sim/rollout_000/*.npz` | Density snapshots D[t] at t=0,5,10,...,60 |
| Sim visualization | `runs/sim_rollout.png` | 6-panel figure: K, seed D0, final D, 3 intermediate frames |
| U-Net checkpoint | `runs/unet_best.pt` | Best model weights (by validation Dice) |
| Risk expansion map | `runs/risk_expansion.png` | Side-by-side simulator vs U-Net risk prediction |

### Interpreting results

- **Suitability AUC**: Measures how well the suitability field ranks known larval sites above background. Lower 95% CI bound > 0.65 is the acceptance criterion. A low AUC (e.g., 0.33) indicates the 1 km water layer cannot resolve small breeding sites — a known resolution limitation.
- **Simulation frames**: Density D[t] shows mosquito population expanding from seed points. The spread front follows water bodies and suitable temperatures.
- **U-Net Dice**: Front-overlap Dice between simulator and U-Net on held-out data. Target > 0.6. Low Dice (e.g., 0.24) indicates the surrogate underfits — scaling rollouts and GPU training is the fix.
- **Risk expansion map**: The final deliverable — shows predicted spread from a seed point overlaid on SRTM hillshade.

## 6. Validation

### Suitability (Stage 2)

- Presence-only AUC against 24 in-AOI larval sites
- ~10,000 random background points
- Bootstrap 95% CI (1,000 resamples)
- **Criterion**: lower 95% bound > 0.65

### U-Net surrogate (Stages 5–6)

- Front-overlap Dice on hard mask `D_norm > 0.1·suitability`
- Held-out east sub-region rollouts (spatial split, not random)
- **Criterion**: Dice > 0.6

### Known limitations

- Static environment: all v1 layers are long-term climatological normals; no temporal variation
- Dynamics unvalidated: spread patterns are simulator-internal, not grounded against temporal incidence data
- Resolution: 1 km grid cannot resolve sub-km breeding sites (documented v1 limitation)
- MODIS NDVI optional: without it, its 0.15 weight is redistributed

## 7. Troubleshooting

### Common issues

| Symptom | Likely cause | Fix |
|---|---|---|
| `FileNotFoundError` on SRTM DEM | Data not restored | Run `python scripts/restore_data.py` from repo root, or verify `terrain/srtm_maps/ghana_idit/` exists |
| `--download` fails for MODIS | No Earthdata credentials | Set `EARTHDATA_USER`/`EARTHDATA_PASS` env vars, or skip NDVI (weight auto-redistributes) |
| AUC < 0.65 | 1 km water layer too coarse | Expected in v1; see DESIGN.md. Fix in v1.5 with MaxEnt or finer water layer |
| OOM during training | GPU RAM exhaustion | Reduce `TRAIN_BATCH` in config.py, or use fewer rollouts |
| CPU training very slow | No GPU available | Use MPS (Apple Silicon) if available; CPU training is infeasible for production |
| `Dice ≈ 0` on unrolled inference | U-Net divergence in multi-step rollout | Known v1 limitation; U-Net is reliable for single-step t→t+T only |
| `ModuleNotFoundError: mal_ghana_sim` | Package not synced | Run `uv sync --all-packages` from repo root |
| Deprecation warnings from rasterio/rioxarray | Library version mismatch | Run `uv lock --upgrade` then `uv sync --all-packages` |

### Debugging tips

- Run stages individually to isolate failures
- Check `runs/layers/` to verify env stack was built correctly
- Stage 4 (`04_build_dataset.py`) reports patch counts — low counts indicate sparse spread
- Stage 5 prints per-epoch train/val loss and Dice — watch for overfitting (val loss rising while train loss drops)

## 8. Advanced Usage

### Custom AOIs

Edit `AOI_W`, `AOI_E`, `AOI_S`, `AOI_N` in `config.py`. Ensure the SRTM DEM tile covers the new bbox. Re-run Stage 1 with `--download` to fetch layers for the new extent.

### Parameter tuning

All simulator parameters are in `config.py`:
- `WEIGHTS` dict: adjust suitability layer importance
- `SimParams`: change `r_max`, `mu`, `k_max`, `water_thresh`
- `PARAM_RANGES`: adjust randomization bounds for training rollouts
- `temp_suitability()` / `mortality_rate()`: modify the thermal response curve

### Multi-month simulations

The v1 simulator uses static climatological normals. For temporal variation:
- Provide time-varying temperature/rainfall layers (one stack per month)
- Modify `03_simulate.py` to swap layers per timestep
- This is a v2 feature (see DESIGN.md "Temporal climate")

### Using the ABM engine

The project includes an agent-based model engine at `mal-ghana-sim/src/mal_ghana_sim/abm/`. The ABM tracks individual mosquito agents rather than grid-level densities. Use it for:
- Fine-grained movement behavior studies
- Comparing individual-level vs population-level dynamics

The ABM is designed for HPC execution (CESGA FinisTerrae III). See the `cesga` skill for SLURM batch job templates, or use the pre-built automation in `mal-execution/scripts/cesga-run/` for a streamlined workflow.

### Running on HPC

For large-scale parameter sweeps or production U-Net training, use CESGA's GPU nodes. See the `cesga` skill for connection, SLURM templates, and data transfer instructions.

## 9. HPC & Cloud Automation

The `mal-execution/scripts/` directory contains pre-built automation for running the pipeline on HPC and cloud infrastructure:

### CESGA SLURM automation (`mal-execution/scripts/cesga-run/`)

| Script | Purpose |
|---|---|
| `setup_env.sh` | Install uv, sync workspace, configure venv on CESGA |
| `prepare_data.sh` | Transfer data to CESGA `$STORE`, restore datasets |
| `run_abm.sh` | Submit ABM rollouts via SLURM job arrays |
| `manage_jobs.sh` | Monitor, cancel, and query SLURM jobs |
| `cesga_config.sh` | Configuration variables (paths, partitions, resources) |

Quick start:
```bash
cd mal-execution/scripts/cesga-run
# Edit cesga_config.sh with your CESGA paths
bash setup_env.sh          # First-time setup
bash prepare_data.sh       # Transfer data
bash run_abm.sh            # Submit ABM jobs
bash manage_jobs.sh status # Monitor jobs
```

### Hetzner cloud automation (`mal-execution/scripts/hetzner-run/`)

| File | Purpose |
|---|---|
| `cloud-init.yaml` | Hetzner Cloud init script for provisioning |
| `lib/` | Shared shell functions |
| `tests/` | Integration tests for the automation |

See `mal-execution/scripts/hetzner-run/README.md` for full setup instructions.
