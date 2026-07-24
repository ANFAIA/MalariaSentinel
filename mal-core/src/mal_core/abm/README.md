# mal-abm-fast

Fast C++ ABM engine for the **MalariaSentinel Centinela** (M-perf milestone).

Re-implements the M1.5 thin-slice ABM (currently in `mal-ghana-sim/src/mal_ghana_sim/abm/`)
in C++ for the CESGA FT3 HPC cluster. Target: 100 rollouts in **<5 min wall**
on a single FT3 `ilk` node (2× Intel Xeon Ice Lake 8352Y, 64 cores, 256 GB RAM).

## Status

**M-perf F1 — complete.** The C++ engine is a black-box equivalent of the Python
reference (`mal_ghana_sim.abm`). All F1 acceptance criteria are met:

| Criterion | Status | Commit |
|---|---|---|
| F1.a scaffold | ✅ | `016b902` |
| F1.b full engine | ✅ | `744b594` (60/60 ctest) |
| F1.c perf (BTPE + vectors + n-rollouts) | ✅ | `8ab7a58` |
| F1.d output contract (COG + sidecar) | ✅ | verified by F1.e parity |
| F1.e Python↔C++ parity test | ✅ | `fdc4cdf` (5/5 pytest) |
| F1.f determinism test | ✅ | included in F1.c review fixes |
| F1.g FT3 benchmark | ⏳ | deferred to FT3 measurement |

## Layout

| Path | Purpose |
|---|---|
| `include/mal_abm_fast/*.hpp` | Public C++ headers (12 components: prng, dispersal, eip, climate, habitat_engine, mosquito_state, mosquito_submodel, coordinator, engine, output_contract, env_reader, aoi) |
| `src/*.cpp` | Implementations (12 source files) |
| `src/main.cpp` | CLI entry point (CLI11) — `run` subcommand |
| `tests/test_*.cpp` | 11 GoogleTest test suites (60 tests total) |
| `slurm/short.sh` | SLURM template for FT3 `ilk`, 6 h wall |
| `slurm/long.sh` | SLURM template for FT3 `ilk`, 7 d wall |
| `vcpkg.json` | vcpkg manifest (eigen3, gdal, cli11, nlohmann-json, googletest) |
| `pyproject.toml` | uv workspace member |
| `CMakeLists.txt` | Top-level CMake |
| `docs/wire-spec.md` | Single source of truth for data contracts (424 lines) |

## Build (macOS / local dev)

```bash
brew install cmake ninja pkg-config gdal eigen cli11 nlohmann-json googletest
cmake -S mal-abm-fast -B mal-abm-fast/build -G Ninja \
      -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_PREFIX_PATH="$(brew --prefix gdal);$(brew --prefix eigen);$(brew --prefix nlohmann-json);$(brew --prefix googletest)"
cmake --build mal-abm-fast/build -j
ctest --test-dir mal-abm-fast/build --output-on-failure
```

## Build (FT3 / CESGA)

The `slurm/short.sh` template handles the FT3 build environment (Intel oneAPI
2021.3 + impi 2021.3 + GDAL 3.7.0). Submit with:

```bash
sbatch mal-abm-fast/slurm/short.sh
```

## Run

### Single rollout (F1.b)

```bash
./mal-abm-fast/build/mal_abm_fast run \
    --aoi ghana --year 2024 --month 6 --seed 1 --days 30 \
    --env    data/runs/ghana/ghana_regional_2024_06_env.tif \
    --habitat data/runs/ghana/ghana_regional_2024_06_habitat_patches.gpkg \
    --output data/runs/ghana/ghana_regional_2024_06_state.tif
```

Outputs `state.tif` (2-band COG: density + suitability) + `state.json` (sidecar).

### Multiple rollouts (F1.c)

```bash
./mal-abm-fast/build/mal_abm_fast run --n-rollouts 100 \
    --aoi ghana --year 2024 --month 6 --seed 1 --days 30 \
    --env    data/runs/ghana/ghana_regional_2024_06_env.tif \
    --habitat data/runs/ghana/ghana_regional_2024_06_habitat_patches.gpkg \
    --output /tmp/rollout/state.tif
```

Outputs `state_seed0000.tif` … `state_seed0099.tif` + corresponding `.json` sidecars.
Each rollout gets a fresh PRNG instance (per-rollout isolation for F2 OpenMP).

### Daily snapshots (time-series generation)

```bash
./mal-abm-fast/build/mal_abm_fast run --snapshot-every 1 --n-rollouts 10 \
    --aoi ghana --year 2024 --month 6 --seed 1 --days 30 \
    --env    data/runs/ghana/ghana_regional_2024_06_env.tif \
    --habitat data/runs/ghana/ghana_regional_2024_06_habitat_patches.gpkg \
    --output /tmp/rollout/state.tif
```

With `--snapshot-every 1`, a snapshot is taken every day (30 files per rollout). Files are named `state_day001.tif` … `state_day030.tif` alongside the final `state.tif`. This produces time-series data for U-Net training.

### Output structure

| File | Description |
|---|---|
| `state.tif` | Final snapshot (backward compatible) |
| `state.json` | Sidecar JSON for final snapshot |
| `state_dayNNN.tif` | Intermediate snapshot at day N (when `--snapshot-every` > 0) |
| `state_dayNNN.json` | Sidecar JSON for intermediate snapshot |

### CLI flags

| Flag | Default | Description |
|---|---|---|
| `--aoi` | — | AOI slug (e.g. `ghana`) |
| `--bbox` | — | Custom bbox `W,S,E,N` (mutually exclusive with `--aoi`) |
| `--env` | — | Path to 4-band env GeoTIFF |
| `--habitat` | — | Path to habitat GeoPackage |
| `--output` | — | Output path for state COG |
| `--year` | 2024 | Start year |
| `--month` | 6 | Start month (1–12) |
| `--seed` | 1 | PRNG seed |
| `--days` | 30 | Simulation days (1–366) |
| `--n-rollouts` | 1 | Number of rollouts (≥1) |
| `--snapshot-every` | 0 | Intermediate snapshot frequency in days (0 = only final). Files named `<stem>_dayNNN.tif` |

## Tests

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

## Architecture

The engine follows a 5-step daily loop (matching the Python reference):

1. **Larva mortality** — inactive patches lose larvae
2. **Larva growth** — EIP progress based on temperature (Mordecai)
3. **Larva to adult** — emergence when EIP ≥ 110
4. **Adult dispersal** — 20% of adults disperse (clipped Gaussian, σ=1km, max=2km)
5. **Birth** — binomial(K=1000, p=0.005) per active patch

Key design decisions:
- **SoA population layout** — struct-of-arrays for cache-friendly access
- **BTPE binomial** — Kachitvichyanukul & Schmeiser 1988 algorithm
- **Dense vector lookups** — `std::vector` indexed by `patch_id` (replaces `unordered_map`)
- **Per-rollout PRNG isolation** — fresh `Prng(seed+i)` per rollout in `--n-rollouts` mode

## See also

- [docs/wire-spec.md](docs/wire-spec.md) — data contracts and module signatures
- [docs/perf-cpp-abm-plan.md](../perf-cpp-abm-plan.md) — full M-perf design
- [docs/m-perf-checklist.md](../m-perf-checklist.md) — F1–F5 issue checklist
- `agents/skills/cesga/SKILL.md` — CESGA FT3 conventions
- `mal-execution/scripts/cesga-run/` — reference SLURM scripts for the Python ABM
