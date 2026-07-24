---
name: mal-execution-api
description: CLI entrypoints, training scripts, and HPC/cloud automation in mal-execution. Covers the malariasim CLI, U-Net training/validation scripts, environment building, mobility and host data preparation, and CESGA/Hetzner deployment automation. Use when running production commands, training models, deploying to HPC, or automating batch jobs.
---

# mal-execution-api

**Use this skill when:** running the `malariasim` CLI, training U-Net surrogates, validating models, building environment/host/mobility data, submitting batch jobs on CESGA, or deploying simulations on Hetzner Cloud.

## Module overview

`mal-execution` is the CLI and automation package in the monorepo. It depends on `mal-core` + `mal-commonlib`.

| Layer | Contents |
|---|---|
| `src/mal_cli/` | Minimal Python module (`__init__.py` only — no substantial code) |
| `scripts/` | All the real value: training scripts, data builders, CESGA/Hetzner automation |

**Key dependency**: `mal-execution` scripts call into `mal_core` (training loops, model classes) and `mal_commonlib` (AOI, data loaders, config).

## The `malariasim` CLI

Defined in `mal-core` (`mal_core.cli`), installed as the `malariasim` entrypoint.

### `malariasim predict`

```bash
malariasim predict --aoi ghana --scale regional --year 2026 --month 6
malariasim predict --aoi ghana --scale regional --year 2026 --month 6 --model unet-v1
malariasim predict --scenario scenario.yaml
```

| Flag | Required | Default | Description |
|---|---|---|---|
| `--aoi` | Yes | — | AOI slug (e.g. `ghana`) |
| `--scale` | No | `regional` | Aggregation scale: `regional`, `national`, `continental` |
| `--year` | Yes | — | Target year |
| `--month` | Yes | — | Target month (1–12) |
| `--model` | No | latest | Model name from registry |
| `--scenario` | No | — | Path to scenario YAML (overrides `--aoi/--scale/--year/--month`) |
| `--output-dir` | No | `runs/predictions/` | Where to write the prediction COG |

Runs the full pipeline: load env data → load model → infer → save prediction COG + sidecar JSON.

### `malariasim status`

```bash
malariasim status --aoi ghana
```

Shows the latest prediction metadata, model version, and data freshness for an AOI.

### `malariasim serve`

```bash
malariasim serve --host 127.0.0.1 --port 8000
```

Starts the FastAPI REST API server. Endpoints:

| Endpoint | Method | Description |
|---|---|---|
| `/predict/{aoi}` | GET | Run prediction for an AOI |
| `/status/{aoi}` | GET | Prediction status and metadata |
| `/health` | GET | Server health check |

## Training scripts

All in `mal-execution/scripts/`. Require GPU (CUDA or Apple MPS).

### `train_unet.py`

Full U-Net training pipeline using `mal_core.train_unet`.

```bash
uv run python mal-execution/scripts/train_unet.py <run_dir> <output_dir> [--epochs N] [--subsample F] [--preload]
```

| Arg | Required | Default | Description |
|---|---|---|---|
| `run_dir` | Yes | — | Directory containing ABM rollout `.npy` files |
| `output_dir` | Yes | — | Where to save `best_model.pt` |
| `--epochs` | No | `50` | Training epochs |
| `--subsample` | No | `1.0` | Fraction of data to use (0.0–1.0) |
| `--preload` | No | `False` | Preload all data into memory |

**Output**: `output_dir/best_model.pt` (best validation Dice) + `final_model.pt`.

**Device**: auto-detects CUDA → MPS → CPU.

### `train_unet_subsample.py`

Faster training variant with subsampled rollouts and preloaded data.

```bash
uv run python mal-execution/scripts/train_unet_subsample.py <npy_dir> <output_dir> [--epochs N] [--max-rollouts M]
```

| Arg | Required | Default | Description |
|---|---|---|---|
| `npy_dir` | Yes | — | Directory with `state_seed*_day*.npy` files |
| `output_dir` | Yes | — | Where to save models |
| `--epochs` | No | `50` | Training epochs |
| `--max-rollouts` | No | all | Limit number of rollouts loaded |

**Output**: `best_model.pt`, `final_model.pt`, `model_epoch_N.pt` (every 10 epochs).

### `validate_unet.py`

Validate a trained U-Net on the held-out eastern third of the grid.

```bash
uv run python mal-execution/scripts/validate_unet.py <run_dir> <model_path> <output_dir>
```

| Arg | Required | Description |
|---|---|---|
| `run_dir` | Yes | Rollout directory (same as training) |
| `model_path` | Yes | Path to `best_model.pt` |
| `output_dir` | Yes | Where to write `validation_results.txt` |

**Target**: Dice > 0.6. Prints PASS/FAIL.

## Environment building

### `build_environment.py`

Build the M1 env tensor (4-band COG) + habitat patches from remote data sources.

```bash
uv run python mal-execution/scripts/build_environment.py \
    --aoi ghana --year 2024 --month 06 --output-dir data/runs/ghana
```

| Flag | Required | Default | Description |
|---|---|---|---|
| `--aoi` | No* | `ghana` | AOI slug from registry |
| `--bbox` | No* | — | Custom bbox `"W,S,E,N"` (overrides slug) |
| `--year` | Yes | — | Year |
| `--month` | Yes | — | Month (1–12) |
| `--output-dir` | Yes | — | Output directory |
| `--scale` | No | `regional` | Aggregation scale |
| `--crs` | No | `EPSG:4326` | CRS for custom bbox |
| `--resolution-m` | No | `1000` | Ground resolution in metres |
| `--format` | No | `tif` | Output: `tif` (COG) or `nc` (daily NetCDF-4) |
| `--skip-era5` | No | `False` | Skip ERA5 (channel becomes NoData) |
| `--skip-modis` | No | `False` | Skip MODIS (channel becomes NoData) |
| `--skip-jrc-gsw` | No | `False` | Skip JRC GSW (water_frac becomes NoData) |

\* Either `--aoi` or `--bbox` is required.

**Output files** (for `--format tif`):
- `<aoi>_<scale>_<YYYY>_<MM>_env.tif` — 4-band COG (water_frac, rainfall, temp_suitability, ndvi)
- `<aoi>_<scale>_<YYYY>_<MM>_env.json` — sidecar metadata
- `<aoi>_<scale>_<YYYY>_<MM>_habitat_patches.gpkg` — pluvial pool points

**Auth policy**: CHIRPS, MERIT-DEM, JRC GSW work without credentials. ERA5 (CDS) and MODIS (EARTHDATA_TOKEN) are auto-skipped with a warning if credentials are missing.

### `build_hosts.py`

Build static host density NetCDF for the ABM engine.

```bash
uv run python mal-execution/scripts/build_hosts.py [--output-dir DIR] [--bbox "W,S,E,N"]
```

| Flag | Required | Default | Description |
|---|---|---|---|
| `--output-dir` | No | `hosts/` | Output directory |
| `--aoi` | No | Ghana default | Path to AOI JSON file |
| `--bbox` | No | — | Custom bbox (overrides `--aoi`) |
| `--worldpop-year` | No | `2019` | WorldPop vintage |
| `--skip-buildings` | No | `False` | Skip Overture Maps (use urban heuristic) |
| `--skip-wildlife` | No | `False` | Skip wildlife proxy (use constant 0.3) |

**Data sources**: WorldPop (human), FAO GLW4 (livestock), GHSL (urban/rural), Overture Maps (buildings), WorldCover+JRC GSW (wildlife proxy).

**Output**: `hosts/host_static.nc` + `hosts/host_manifest.json`.

### `build_mobility.py`

Build gravity-model mobility OD matrices from `host_static.nc`.

```bash
uv run python mal-execution/scripts/build_mobility.py \
    --hosts hosts/host_static.nc --output-dir hosts/ \
    --cell-size-km 1.0 --beta-day 0.05 --beta-night 0.5 --max-distance-km 50.0
```

| Flag | Required | Default | Description |
|---|---|---|---|
| `--hosts` | Yes | — | Path to `host_static.nc` |
| `--output-dir` | No | same as `--hosts` | Output directory |
| `--cell-size-km` | No | `1.0` | Grid cell size in km |
| `--beta-day` | No | `0.05` | Human daytime friction |
| `--beta-night` | No | `0.5` | Human nighttime friction |
| `--beta-livestock` | No | `0.1` | Livestock friction |
| `--max-distance-km` | No | `50.0` | Maximum mobility distance |

**Output**: `human_mobility_day.csr`, `human_mobility_night.csr`, `livestock_mobility_season.csr`, `mobility_manifest.json`.

## CESGA automation

All scripts in `mal-execution/scripts/cesga-run/`. See also the `cesga` skill for full HPC/SLURM reference.

### Quick start

```bash
ssh cesga
cd /mnt/lustre/scratch/nlsas/home/ulc/cursos/curso309/MalariaSentinel/mal-execution/scripts/cesga-run

# 1. First-time setup (install uv, create venv, sync workspace)
bash setup_env.sh

# 2. Build environment data (run on login node)
bash prepare_data.sh

# 3. Submit ABM rollouts via SLURM
bash manage_jobs.sh submit

# 4. Monitor
bash manage_jobs.sh status
```

### Configuration (`cesga_config.sh`)

Source this file; do not execute directly. Key variables:

| Variable | Default | Description |
|---|---|---|
| `DATA_DIR` | `$PROJECT_ROOT/data/runs/ghana/m2` | Input env COGs |
| `RUNS_DIR` | `$PROJECT_ROOT/runs` | ABM output |
| `LOGS_DIR` | `$PROJECT_ROOT/runs/logs` | SLURM logs |
| `SLURM_PARTITION` | `medium` | `short`/`medium`/`long`/`ondemand` |
| `SLURM_CORES` | `32` | Cores per job |
| `SLURM_MEM` | `64G` | Memory per job |
| `ABM_SEED_START` | `1` | Starting seed |
| `ABM_NUM_MONTHS` | `24` | Months to simulate |

### Script reference

| Script | Purpose | Where to run |
|---|---|---|
| `setup_env.sh` | Install uv, create venv, sync workspace | Login node (once) |
| `prepare_data.sh` | Validate/rebuild env COGs + habitat patches | Login node |
| `run_abm.sh` | SLURM batch script — runs N months sequentially | `sbatch` from login |
| `manage_jobs.sh submit` | Submit a single ABM run | Login node |
| `manage_jobs.sh submit_array S N` | Submit array of N jobs starting at seed S | Login node |
| `manage_jobs.sh status` | Show running/pending jobs | Login node |
| `manage_jobs.sh cancel <JOB_ID>` | Cancel a job | Login node |
| `manage_jobs.sh efficiency` | Show efficiency stats for completed jobs | Login node |
| `manage_jobs.sh logs <JOB_ID>` | Show stdout/stderr for a job | Login node |

### `run_abm.sh` details

Runs 24 months (configurable) sequentially. Each month:
1. Checks for env COG + habitat gpkg in `$DATA_DIR`
2. Runs `uv run python -m mal_ghana_sim.abm.run` with the month's data
3. Writes output TIF to `$RUNS_DIR`

Override defaults via `--export` on `sbatch`:
```bash
sbatch --export="ABM_SEED=5,ABM_START_MONTH=7,ABM_NUM_MONTHS=12" run_abm.sh
```

## Hetzner automation

All scripts in `mal-execution/scripts/hetzner-run/`. Pure bash — no Python dependency.

### Quick start

```bash
# Dry run — see what would happen
hetzner-run --dry-run sim-run

# Actually run (boots VM, pushes repo, runs sim, pulls results, destroys VM)
hetzner-run sim-run

# List VMs
hetzner-run status

# Cost estimate
hetzner-run cost --type ccx33 --hours 2
```

### Commands

| Command | Description |
|---|---|
| `start [--type T] [--name N]` | Create a VM, wait for SSH |
| `stop <name>` | Graceful shutdown |
| `destroy <name>` | Delete VM + remove local cache |
| `status [<name>]` | VM status (one or all `ms-*`) |
| `exec <name> <cmd>` | SSH into VM and run command |
| `push <name> <local> <remote>` | rsync local → VM |
| `pull <name> <remote> <local>` | rsync VM → local |
| `sim-run [--keep-vm]` | High-level: boot → push → run → pull → destroy |
| `train [--keep-vm]` | Like `sim-run` but runs U-Net training |
| `cost --type T --hours H` | Print cost estimate |

### Prerequisites

1. Hetzner account + API token: `hcloud context create malariasentinel`
2. SSH key registered: `hcloud ssh-key create --public-key-from-file ~/.ssh/id_ed25519.pub`
3. Local tools: `hcloud`, `jq`, `ssh`, `rsync`

### Environment variables

| Variable | Default | Description |
|---|---|---|
| `HETZNER_RUN_DRY_RUN=1` | unset | Same as `--dry-run` |
| `HETZNER_RUN_DEBUG=1` | unset | Same as `--debug` |
| `HETZNER_RUN_SSH_KEY_NAME` | `davidflorezmazuera@gmail.com` | SSH key name in Hetzner |
| `HETZNER_RUN_ASSUME_YES=1` | unset | Skip confirmation prompts |

### Default VM type

`ccx33`: 8 dedicated AMD EPYC cores, 32 GB RAM, 240 GB SSD — €0.030/h. A typical 1-hour run costs ~€0.030.

## Common patterns

### Full pipeline: build → train → validate → predict

```bash
# 1. Build environment for multiple months
for M in $(seq 1 12); do
  uv run python mal-execution/scripts/build_environment.py \
    --aoi ghana --year 2024 --month $M --output-dir data/runs/ghana
done

# 2. Build host population + mobility
uv run python mal-execution/scripts/build_hosts.py --output-dir hosts/
uv run python mal-execution/scripts/build_mobility.py --hosts hosts/host_static.nc

# 3. Run ABM rollouts (generates training data)
uv run python -m mal_ghana_sim.abm.run \
  --env data/runs/ghana/ghana_regional_2024_01_env.tif \
  --habitat data/runs/ghana/ghana_regional_2024_01_habitat_patches.gpkg \
  --seed 1 --days 30 --output runs/rollouts/

# 4. Train U-Net surrogate
uv run python mal-execution/scripts/train_unet.py runs/rollouts/ runs/models/ --epochs 50

# 5. Validate
uv run python mal-execution/scripts/validate_unet.py runs/rollouts/ runs/models/best_model.pt runs/validation/

# 6. Predict
malariasim predict --aoi ghana --scale regional --year 2025 --month 1 --model unet-v1
```

### Submit batch jobs on CESGA

```bash
# Single run
sbatch mal-execution/scripts/cesga-run/run_abm.sh

# Array: 10 seeds
bash mal-execution/scripts/cesga-run/manage_jobs.sh submit_array 1 10

# Monitor
bash mal-execution/scripts/cesga-run/manage_jobs.sh status
```

### Deploy on Hetzner

```bash
# One-liner: boot → push → train → pull → destroy
hetzner-run train --config my-config.yaml

# Keep VM alive for debugging
hetzner-run sim-run --keep-vm
hetzner-run exec <name> 'htop'
hetzner-run destroy <name>
```
