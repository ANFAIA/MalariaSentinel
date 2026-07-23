---
name: abm-engine
description: Use the Agent-Based Model (ABM) engines for malaria simulation. Covers both the Python reference implementation (mal-ghana-sim) and the fast C++ engine (mal-abm-fast) for HPC deployment. Use when running ABM simulations, comparing engines, or deploying to CESGA.
---

# ABM Engine Skill

Two implementations of the M1.5 thin-slice ABM for mosquito population dynamics and malaria spread simulation:

| Engine | Location | Use case |
|---|---|---|
| Python reference | `mal-ghana-sim/src/mal_ghana_sim/abm/` | Development, validation, prototyping |
| C++ fast engine | `mal-abm-fast/` | HPC production runs (CESGA FT3), 100x faster |

Both produce identical 2-band COG output (density + suitability) and sidecar JSON, verified by the parity test (F1.e).

## Daily loop (both engines)

Each day the model runs a 5-step loop:

1. **Larva mortality** — inactive patches lose larvae (Beverton-Holt density-dependent + desiccation)
2. **Larva growth** — EIP progress from temperature (Mordecai parabolic, `daily_gd = max(0, T - 16)`)
3. **Larva to adult** — emergence when EIP >= 110 growing-degree-days
4. **Adult dispersal** — configurable % of adults move (clipped Gaussian, default sigma=450m, max=2km)
5. **Birth** — binomial(n_females, fecundity) per active cell, temperature-dependent (Mordecai 2013)

---

## Python ABM

### Location

`mal-ghana-sim/src/mal_ghana_sim/abm/`

### Key files

| File | Role |
|---|---|
| `run.py` | CLI entry point (`abm_run`), Typer app |
| `model.py` | `AnophelesABM` facade — owns coordinator + submodel |
| `coordinator.py` | `CoordinatorModel` — Mesa-Geo spatial layer, climate lookups, density aggregation |
| `mosquito_submodel.py` | `MosquitoSubmodel` — Polars-backed vectorised population (larva/adult stages) |
| `habitat_engine.py` | `HabitatEngine` — loads habitat patches from gpkg |
| `climate.py` | `ClimateEngine` — 4-band env COG lookups (rain, temp, water_frac, ndvi) |
| `eip.py` | EIP growing-degree-day accumulation |
| `patch_state.py` | `PatchState` schema (Polars DataFrame columns) |
| `agents.py` | Mesa agent definitions for HabitatPatch |
| `scheduler.py` | `RandomActivationByTypeShim` — Mesa-Geo scheduler compatibility |

### How to run

```bash
cd mal-ghana-sim

# Using the Python module
uv run python -m mal_ghana_sim.abm.run \
    --aoi ghana --year 2024 --month 6 \
    --env data/runs/ghana/ghana_regional_2024_06_env.tif \
    --habitat data/runs/ghana/ghana_regional_2024_06_habitat_patches.gpkg \
    --seed 42 --days 30 \
    --output data/runs/ghana/ghana_regional_2024_06_state.tif

# Using the entry point (after uv sync)
uv run abm_run \
    --aoi ghana --year 2024 --month 6 \
    --env data/runs/ghana/ghana_regional_2024_06_env.tif \
    --habitat data/runs/ghana/ghana_regional_2024_06_habitat_patches.gpkg \
    --seed 42 --days 30 \
    --output data/runs/ghana/ghana_regional_2024_06_state.tif
```

### CLI parameters

| Flag | Default | Description |
|---|---|---|
| `--aoi` | `ghana` | AOI slug (registered in `_DEFAULT_REGISTRY`) |
| `--bbox` | — | Custom bbox `W,S,E,N` (overrides `--aoi`) |
| `--year` | required | Start year |
| `--month` | required | Start month (1–12) |
| `--seed` | 1 | PRNG seed |
| `--days` | 30 | Simulation days (1–366) |
| `--env` | required | Path to 4-band env COG (.tif) |
| `--habitat` | required | Path to habitat patches gpkg |
| `--output` | required | Output path for state COG (.tif) |
| `--resolution-m` | 1000 | Ground resolution in metres |
| `--scale` | `regional` | AOI scale |

### Expected output

```
abm_run: AOI=ghana year=2024 month=06 seed=42 days=30 -> data/runs/ghana/ghana_regional_2024_06_state.tif
```

---

## C++ Fast Engine

### Location

`mal-abm-fast/`

### Purpose

100x faster than Python for HPC deployment on CESGA FinisTerrae III. Target: 100 rollouts in <5 min wall on a single FT3 ILK node (2x Intel Xeon Ice Lake 8352Y, 64 cores, 256 GB RAM).

### Key source files

| Path | Role |
|---|---|
| `include/mal_abm_fast/*.hpp` | Public headers (12 components) |
| `src/*.cpp` | Implementations (12 source files) |
| `src/main.cpp` | CLI entry point (CLI11) — `run` subcommand |
| `tests/test_*.cpp` | 11 GoogleTest test suites (60 tests) |
| `slurm/short.sh` | SLURM template for FT3 ILK, 6h wall |
| `slurm/long.sh` | SLURM template for FT3 ILK, 7d wall |
| `docs/wire-spec.md` | Data contracts and module signatures |

### Build (macOS / local dev)

```bash
# Install dependencies
brew install cmake ninja pkg-config gdal eigen cli11 nlohmann-json googletest libomp

# Configure (macOS Apple Silicon — requires OpenMP from Homebrew)
cmake -S mal-abm-fast -B mal-abm-fast/build -G Ninja \
      -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_CXX_COMPILER=/opt/homebrew/opt/llvm/bin/clang++ \
      -DOpenMP_CXX_FLAGS="-fopenmp" \
      -DOpenMP_CXX_LIB_NAMES="omp" \
      -DOpenMP_omp_LIBRARY=/opt/homebrew/opt/libomp/lib/libomp.dylib \
      -DCMAKE_PREFIX_PATH="$(brew --prefix gdal);$(brew --prefix eigen);$(brew --prefix nlohmann-json);$(brew --prefix googletest)"

# Build
cmake --build mal-abm-fast/build -j

# Test
ctest --test-dir mal-abm-fast/build --output-on-failure
```

### Build (CESGA FT3)

The SLURM templates handle the FT3 build environment. The binary is built once and cached:

```bash
# From a SLURM job or interactive session
module purge
module load cesga/system
module load intel/2021.3.0
module load impi/2021.3.0
module load gdal/3.7.0

cmake -S $PROJECT_ROOT/mal-abm-fast -B $PROJECT_ROOT/mal-abm-fast/build \
      -DCMAKE_BUILD_TYPE=Release
cmake --build $PROJECT_ROOT/mal-abm-fast/build -j
```

### How to run

```bash
# Single rollout
./mal-abm-fast/build/mal_abm_fast run \
    --aoi ghana --year 2024 --month 6 --seed 1 --days 30 \
    --env data/runs/ghana/ghana_regional_2024_06_env.tif \
    --habitat data/runs/ghana/ghana_regional_2024_06_habitat_patches.gpkg \
    --output data/runs/ghana/ghana_regional_2024_06_state.tif

# Multiple rollouts (each gets fresh PRNG: seed+i)
./mal-abm-fast/build/mal_abm_fast run --n-rollouts 100 \
    --aoi ghana --year 2024 --month 6 --seed 1 --days 30 \
    --env data/runs/ghana/ghana_regional_2024_06_env.tif \
    --habitat data/runs/ghana/ghana_regional_2024_06_habitat_patches.gpkg \
    --output /tmp/rollout/state.tif
# Produces: state_seed0000.tif ... state_seed0099.tif + .json sidecars

# Daily snapshots (for U-Net training time-series)
./mal-abm-fast/build/mal_abm_fast run --snapshot-every 1 --n-rollouts 10 \
    --aoi ghana --year 2024 --month 6 --seed 1 --days 30 \
    --env data/runs/ghana/ghana_regional_2024_06_env.tif \
    --habitat data/runs/ghana/ghana_regional_2024_06_habitat_patches.gpkg \
    --output /tmp/rollout/state.tif
# Produces: state_day001.tif ... state_day030.tif per rollout
```

### CLI flags

| Flag | Default | Description |
|---|---|---|
| `--aoi` | — | AOI slug (`ghana`) |
| `--bbox` | — | Custom bbox `W,S,E,N` (overrides `--aoi`) |
| `--env` | required | Path to 4-band env GeoTIFF (.tif) or daily NetCDF (.nc) |
| `--habitat` | required | Path to habitat patches gpkg |
| `--output` | required | Output path for state COG (.tif) |
| `--year` | required | Start year |
| `--month` | required | Start month (1–12) |
| `--seed` | 1 | PRNG seed |
| `--days` | 30 | Simulation days (1–730) |
| `--n-rollouts` | 1 | Number of rollouts (>=1), outputs `<stem>_seed{NNNN}.tif` |
| `--snapshot-every` | 0 | Intermediate snapshot frequency in days (0 = only final) |
| `--threads` | 0 | OpenMP threads (0 = auto) |
| `--max-population` | 0 | Population explosion warning threshold (0 = auto) |
| `--seeding-mode` | `uniform` | `uniform`, `random-viable`, or `explicit` |
| `--detection-points` | — | `lat,lon;lat,lon;...` for explicit seeding |
| `--detection-radius-km` | 5.0 | Snap radius for explicit detection points |
| `--n-detections` | 3 | Number of detection points (random-viable mode) |
| `--n-adults-per-detection` | 50 | Adults per detection point |
| `--n-larvae-per-detection` | 30 | Larvae per detection point |
| `--debug-population` | off | Emit per-day population diagnostics to stderr |
| `--disperse-prob` | 0.05 | Adult dispersal probability per day (0.0-1.0) |
| `--disperse-sigma-m` | 450.0 | Dispersal kernel sigma in metres |
| `--disperse-max-m` | 2000.0 | Dispersal kernel max distance in metres |
| `--larva-bh-alpha` | 0.05 | Beverton-Holt competition coefficient (0.0-1.0) |
| `--birth-fecundity` | 0.25 | Per-adult per-day fecundity (0.0-1.0) |

### Expected output

```
abm_run: loaded climate data (30 days, 779x551 grid)
abm_run: rollout 0/100 AOI=ghana year=2024 month=6 seed=1 days=30 -> /tmp/rollout/state_seed0000.tif
...
abm_run: rollout 99/100 AOI=ghana year=2024 month=6 seed=100 days=30 -> /tmp/rollout/state_seed0099.tif
```

---

## Output format

Both engines produce identical output:

### state.tif (2-band COG)

| Band | Name | Description |
|---|---|---|
| 1 | `density` | Normalised adult mosquito density per cell (count / K_MAX, clipped [0, 1]) |
| 2 | `suitability` | Per-cell adult density from post-dispersal lon/lat (count / K_MAX, clipped [0, 1]) |

- **Format**: GeoTIFF, COG-compatible (tiled, deflate, 128x128 blocks)
- **CRS**: EPSG:4326
- **NoData**: -9999.0

### state.json (sidecar)

```json
{
  "crs": "EPSG:4326",
  "transform": [1.0, 0.0, -3.5, 0.0, -1.0, 11.5],
  "aoi_slug": "ghana",
  "scale": "regional",
  "year": 2024,
  "month": 6,
  "seed": 1,
  "generator_version": "m1.5-mesa-frames+polars",
  "contract_version": "1.1",
  "band_names": ["density", "suitability"],
  "nodata": -9999.0,
  "shape": [2, 551, 779],
  "k_max": 1000
}
```

### Intermediate snapshots (C++ only, --snapshot-every > 0)

| File | Description |
|---|---|
| `state_dayNNN.tif` | Snapshot at day N (2-band COG, same format as final) |
| `state_dayNNN.json` | Sidecar for intermediate snapshot |
| `state_seedNNNN.tif` | Per-rollout final snapshot (when --n-rollouts > 1) |

---

## Invasion Simulation

For simulating mosquito invasion from a small initial population, use `--seeding-mode random-viable` with literature-based dispersal parameters.

### Quick start: 1-year invasion

```bash
cd mal-abm-fast && ./build/src/mal_abm_fast run \
  --aoi ghana \
  --env data/ghana/ghana_regional_2024_2025_env.nc \
  --habitat data/runs/ghana/m2_run3seeds/ghana_regional_2024_06_habitat_patches.gpkg \
  --output /tmp/invasion/state.tif \
  --year 2024 --month 1 --days 365 --seed 1 --snapshot-every 1 \
  --seeding-mode random-viable --n-detections 3 \
  --n-adults-per-detection 5000 --n-larvae-per-detection 500 \
  --disperse-prob 0.30 --disperse-sigma-m 1000 --disperse-max-m 5000 \
  --larva-bh-alpha 0.01 --birth-fecundity 0.35 \
  --emit-cohort-log /tmp/invasion/cohort.json
```

### Parameter rationale (literature-based)

| Parameter | Invasion value | Source |
|---|---|---|
| `--disperse-prob 0.30` | 30% adults disperse/day | Costantini 1996 (Burkina Faso MRR) |
| `--disperse-sigma-m 1000` | σ=1km | Midega 2019 (579m MDT, Kenya) |
| `--disperse-max-m 5000` | max=5km | Caputo 2013 (95% < 2.8km, Gambia) |
| `--larva-bh-alpha 0.01` | Low competition | Allows cold-start survival |
| `--birth-fecundity 0.35` | High fecundity | Dozens of eggs per female |
| `--n-detections 3` | 3 starting points | Random per rollout |
| `--n-adults-per-detection 5000` | 5000 adults/point | Enough for establishment |

### Expected behavior

- Day 1: Mosquitoes appear at 3 random points (123 active cells)
- Day 365: Population expands to ~700 active cells (0.16% coverage)
- Population stabilizes around 17,000 individuals
- Each rollout starts at different random locations

### Steady-state vs invasion

| Mode | Seeding | Dispersal | Duration | Use case |
|---|---|---|---|---|
| Steady-state | `uniform` | Default (5%/450m) | 30 days | Calibration, validation |
| Invasion | `random-viable` | High (30%/1km) | 365 days | Expansion dynamics |

### Visualization

Use `mal-abm-fast/scripts/visualize_state.py` to generate GIF animations:

```bash
cd mal-abm-fast && uv run python scripts/visualize_state.py \
  --run-dir /tmp/invasion \
  --output /tmp/invasion/animation.gif \
  --sample-every 5
```

---

## Testing

### C++ unit tests (GoogleTest)

```bash
ctest --test-dir mal-abm-fast/build --output-on-failure
# 60 tests: prng, dispersal, eip, climate, habitat_engine, mosquito_submodel,
#           coordinator, engine, output_contract, state_cog, smoke
```

### Python parity test (F1.e)

```bash
cd mal-ghana-sim && uv run pytest tests/test_abm_fast_parity.py -v
# 5 tests: 3-day, 30-day, 10 random triples, determinism, sidecar keys
# Tolerance: max(2e-2 abs, 12% rel) per band mean
```

### Python smoke test

```bash
cd mal-ghana-sim && uv run pytest tests/test_abm_smoke.py -v
```

---

## CESGA Deployment

For HPC deployment on CESGA FinisTerrae III, use the `cesga` skill (`skill({ name: "cesga" })`) for connection, VPN, SLURM, and data transfer details.

### Quick start: build + run on CESGA

```bash
ssh cesga
cd $STORE/MalariaSentinel

# Transfer data (from local)
rsync -avz --progress ./data/runs/ghana/ cesga:$STORE/MalariaSentinel/data/runs/ghana/

# Build C++ engine (one-time)
module load cesga/system intel/2021.3.0 impi/2021.3.0 gdal/3.7.0
cmake -S mal-abm-fast -B mal-abm-fast/build -DCMAKE_BUILD_TYPE=Release
cmake --build mal-abm-fast/build -j

# Run 100 rollouts
srun mal-abm-fast/build/mal_abm_fast run \
    --aoi ghana --year 2024 --month 6 --seed 1 --days 30 \
    --env data/runs/ghana/m2/ghana_regional_2024_06_env.tif \
    --habitat data/runs/ghana/m2/ghana_regional_2024_06_habitat_patches.gpkg \
    --output runs/m-perf/ghana_2024_06/state.tif \
    --n-rollouts 100 --threads 64

# Transfer results back
rsync -avz --progress cesga:$STORE/MalariaSentinel/runs/m-perf/ ./runs/m-perf/
```

### Using SLURM templates

```bash
# Short job (6h, 100 rollouts)
sbatch mal-abm-fast/slurm/short.sh

# Override parameters
MONTH=6 YEAR=2024 N_ROLLOUTS=100 sbatch mal-abm-fast/slurm/short.sh

# Long job (7d, multi-month)
NUM_MONTHS=24 N_ROLLOUTS=100 sbatch mal-abm-fast/slurm/long.sh
```

### Python ABM on CESGA

```bash
cd $STORE/MalariaSentinel
uv sync --all-packages

# Build environment
uv run python -m mal_ghana_sim.scripts.build_env \
    --aoi ghana --year 2024 --month 6 --scale regional \
    --output-dir $STORE/runs/ghana-sim/env/2024-06/

# Run ABM
uv run python -m mal_ghana_sim.abm.run \
    --env-cog $STORE/runs/ghana-sim/env/2024-06/env.tif \
    --habitat-gpkg $STORE/runs/ghana-sim/env/2024-06/habitat.gpkg \
    --seed 42 --days 30 \
    --output $STORE/runs/ghana-sim/snapshots/2024-06/seed42/
```

---

## Troubleshooting

### Build issues

| Error | Cause | Fix |
|---|---|---|
| `Could not find GDAL` | GDAL not installed or not in CMAKE_PREFIX_PATH | `brew install gdal` and add `$(brew --prefix gdal)` to `CMAKE_PREFIX_PATH` |
| `CLI/CLI.hpp not found` | CLI11 not installed | `brew install cli11` |
| `nlohmann/json.hpp not found` | nlohmann-json not installed | `brew install nlohmann-json` |
| `Eigen/Dense not found` | Eigen not installed | `brew install eigen` |
| `omp.h not found` | OpenMP not available | On macOS, use `brew install libomp`; on CESGA, load `intel/2021.3.0` |
| C++ build succeeds but tests fail | Outdated build cache | `rm -rf mal-abm-fast/build && cmake ...` (clean rebuild) |

### Runtime issues

| Error | Cause | Fix |
|---|---|---|
| `--env not found` | Wrong path to env COG | Check the path; files are under `data/runs/<aoi>/m2/` |
| `--habitat not found` | Wrong path to habitat gpkg | Check the path; files are under `data/runs/<aoi>/m2/` |
| `diverged on day N` | Population explosion or NaN | Check `--debug-population` output; reduce `--n-rollouts` or use `--max-population` |
| Empty output (all NaN) | No active patches | Verify env COG has non-zero rainfall and water_frac bands |
| Python parity mismatch | Version skew between engines | Ensure both engines use the same `wire.hpp` constants; run `uv sync --all-packages` |

### Performance issues

| Symptom | Fix |
|---|---|
| Python ABM is too slow for >10 rollouts | Use the C++ engine (`mal-abm-fast`) |
| C++ engine uses too much memory | Reduce `--n-rollouts` or `--threads`; check grid size |
| SLURM job killed (OOM) | Increase `--mem`; reduce grid resolution or `--n-rollouts` |
| Rollouts not parallelising | Check `OMP_NUM_THREADS` and `--threads` flag |

---

## Architecture reference

The C++ engine mirrors the Python reference's 2-layer architecture:

| Layer | Python | C++ |
|---|---|---|
| Spatial coordinator | `CoordinatorModel` (Mesa-Geo) | `CoordinatorModel` |
| Mosquito population | `MosquitoSubmodel` (Polars DataFrame) | `MosquitoSubmodel` (SoA vectors) |
| Facade | `AnophelesABM` | `Engine` |
| Climate | `ClimateEngine` | `ClimateEngine` |
| Habitat | `HabitatEngine` | `HabitatEngine` |
| PRNG | `numpy.default_rng` | `Prng` (PCG-XSL-RR, BTPE binomial) |

Key design decisions in the C++ engine:
- **SoA population layout** — struct-of-arrays for cache-friendly access
- **BTPE binomial** — Kachitvichyanukul & Schmeiser 1988 algorithm (faster than naive inversion)
- **Dense vector lookups** — `std::vector` indexed by `patch_id` (replaces `unordered_map`)
- **Per-rollout PRNG isolation** — fresh `Prng(seed+i)` per rollout, no state leakage
- **Shared ClimateEngine** — loaded once, cloned per thread (reduces memory from O(n_rollouts * n_days * grid) to O(n_days * grid))
