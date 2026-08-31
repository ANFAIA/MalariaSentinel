# mal-abm-fast — C++ ABM Engine

Fast C++20 agent-based model engine for the **MalariaSentinel Centinela**. It
simulates mosquito population dynamics (aquatic stages, dispersal, host
seeking, oviposition) and malaria transmission (EIP, human infection states,
outbreaks) on the AOI grid, and is bit-compatible with the former M1.5 Python
ABM (~1000× faster per rollout).

**Location**: this directory — `mal-core/src/mal_core/abm/`. The engine was
consolidated here when `scripts/` was merged into `mal-core` (the old
top-level `mal-abm-fast/` package no longer exists).

## Layout

| Path | Purpose |
|---|---|
| `include/mal_abm_fast/*.hpp` | Public C++ headers (params, wire, prng, dispersal, eip, climate, habitat_engine, mosquito/human state, host_seeking, coordinator, engine, output_contract, env_reader, aoi, species_params…) |
| `src/*.cpp` | Implementations (engine loop, host landscape, aquatic cohorts, transmission, wind field, seeding, mobility schedule…) |
| `src/main.cpp` | CLI entry point (CLI11) — `run` subcommand, 50+ flags |
| `tests/test_*.cpp` | GoogleTest suites (climate, coordinator, dispersal, eip, engine, env_reader, gonotrophic, effective_hosts…) |
| `cli/` | Python-side CLI helpers (`run.py`, `score.py`, `test.py`) |
| `wrapper.py` | `CppAbmWrapper` — binary resolution + subprocess launch from `malariasim abm` |
| `runner.py` | Manifest-driven run orchestration (`run_abm_from_manifest()`) |
| `compile.py` + `build.sh` | Build entry points used by `malariasim abm --compile` |
| `scripts/` | Input overlay / visualization utilities (hosts overlay, state/mobility/transmission visualization) |
| `pool_hydrology.py` | Pool hydrology reference model |
| `slurm/short.sh`, `slurm/long.sh` | SLURM templates for CESGA FT3 (6 h / 7 d walls) |
| `cmake/` | Compiler warnings + FT3 module finders |
| `docs/wire-spec.md` | **Single source of truth** for data contracts |
| `bin/mal_abm_fast_<platform>` | Compiled binary (wrapper prefers this over `build/`) |

## Build

From anywhere in the repo:

```bash
malariasim abm --compile              # configure + build (build.sh / compile.py)
malariasim abm --compile --clean      # wipe the build dir first
malariasim abm --compile --worktree <path>   # compile inside an isolated gawt worktree
```

> **Binary resolution pitfall**: `CppAbmWrapper` resolves
> `bin/mal_abm_fast_<platform>` (e.g. `bin/mal_abm_fast_darwin`) **before**
> `build/src/mal_abm_fast`. After any cmake build you MUST copy the fresh
> binary, or runs silently use the stale one:
>
> ```bash
> cp build/src/mal_abm_fast bin/mal_abm_fast_darwin
> ```

Manual build (macOS / local dev):

```bash
brew install cmake ninja pkg-config gdal eigen cli11 nlohmann-json googletest
cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_PREFIX_PATH="$(brew --prefix gdal);$(brew --prefix eigen);$(brew --prefix nlohmann-json);$(brew --prefix googletest)"
cmake --build build -j
ctest --test-dir build --output-on-failure
```

FT3 / CESGA: `sbatch slurm/short.sh` (the template handles the Intel oneAPI + GDAL build environment).

## Run

Normally you don't invoke the binary directly — the `malariasim abm` wrapper
resolves the manifest at `data/<aoi>/manifest.json`, validates completeness,
resolves paths, and launches the engine:

```bash
malariasim abm --aoi ghana --days 30 --seed 1
malariasim abm --worktree .gitagent/worktree --aoi ghana --days 30 --seed 1
```

Direct binary invocation (matching what the wrapper does):

```bash
./bin/mal_abm_fast_darwin run \
    --aoi ghana --year 2024 --month 6 --seed 1 --days 30 \
    --env    data/ghana/ghana_regional_2024_2025_env.nc \
    --habitat data/ghana/ghana_habitat_patches.gpkg \
    --output /tmp/rollout/state.tif
```

### Key CLI flags (groups)

`./bin/mal_abm_fast run --help` documents all of them. Main groups:

- **Grid/inputs**: `--aoi` | `--bbox/--crs/--resolution-m/--scale`, `--env`, `--habitat`, `--hosts`, `--human-mobility-day/night`, `--livestock-mobility`, `--wind-field`
- **Run shape**: `--year --month --days(1..731) --seed --n-rollouts --threads --snapshot-every --max-population`
- **Mosquito dynamics**: `--disperse-prob/--disperse-sigma-m/--disperse-max-m`, `--birth-fecundity`, `--larva-bh-alpha`, `--seeding-mode`, `--init-frac`, detection-seeding flags (`--detection-points`, `--n-adults-per-detection`, …)
- **Transmission**: `--beta-hv`, `--beta-vh`, `--human-incubation-days`, `--human-infectious-days`, `--immunity-duration-days`, `--initial-human-prevalence`, outbreak flags (`--human-outbreak-day/--foci/--cases/--min-density`, `--human-foci-coords`, …)
- **Outputs**: `--emit-cohort-log`, `--emit-transmission-log`, `--transmission-snapshot-every`

For multi-year runs, pass all days in one invocation (`--year 2024 --month 1 --days 731`). Do not split by month: a new process re-seeds mosquitoes and loses aquatic cohort and engine state.

### Output artifacts

| File | Description |
|---|---|
| `state.tif` | Final state COG (density + suitability bands) |
| `state.json` | Sidecar JSON for the final snapshot |
| `state_dayNNN.tif` / `.json` | Intermediate snapshots (when `--snapshot-every` > 0) |
| `transmission.tif` | Per-rollout transmission output (when enabled; name derived from the output path) |
| `*_transmission_daily.json` | Daily transmission log (needed by the D25 cases scorer) |
| cohort log JSON | Daily aquatic/adult cohort statistics (`--emit-cohort-log`) |

## Tests

```bash
# C++ unit tests (GoogleTest)
ctest --test-dir build --output-on-failure

# Calibration harness (pytest) — see tests/calibration/README.md
cd tests/calibration && uv run pytest -m fast -v
```

## See also

- `docs/wire-spec.md` — data contracts, module map, per-day contract, determinism rules
- `slurm/` — CESGA FT3 job templates
- `mal-execution/scripts/cesga-run/` — CESGA automation
- `mal-core/README.md` — pipeline stage order and the post-run scoring CLI
