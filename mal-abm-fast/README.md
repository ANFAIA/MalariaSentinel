# mal-abm-fast

Fast C++ ABM engine for the **MalariaSentinel Centinela** (M-perf milestone).

Re-implements the M1.5 thin-slice ABM (currently in `mal-ghana-sim/src/mal_ghana_sim/abm/`)
in C++ for the CESGA FT3 HPC cluster. Target: 100 rollouts in **<5 min wall**
on a single FT3 `ilk` node (2× Intel Xeon Ice Lake 8352Y, 64 cores, 256 GB RAM).

## Status

**M-perf F1.a — scaffold.** Code compiles, headers + stub implementations + a
GoogleTest smoke test are in place. The day loop, climate/habitat readers, and
output contract writer ship in F1.b/c/d (see [docs/perf-cpp-abm-plan.md](docs/perf-cpp-abm-plan.md)).

## Layout

| Path | Purpose |
|---|---|
| `include/mal_abm_fast/*.hpp` | Public C++ headers (7 components: prng, dispersal, eip, climate, habitat_engine, mosquito_state, output_contract) |
| `src/*.cpp` | Implementations (stubs in F1.a) |
| `src/main.cpp` | CLI entry point (CLI11) |
| `tests/test_smoke.cpp` | GoogleTest smoke test |
| `slurm/short.sh` | SLURM template for FT3 `ilk`, 6 h wall |
| `slurm/long.sh` | SLURM template for FT3 `ilk`, 7 d wall |
| `vcpkg.json` | vcpkg manifest (eigen3, gdal, cli11, nlohmann-json, googletest) |
| `pyproject.toml` | uv workspace member (the Python wrapper ships in F1.e) |
| `CMakeLists.txt` | Top-level CMake |
| `docs/perf-cpp-abm-plan.md` | M-perf design doc (in the repo root) |

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

F1.a scaffold:

```bash
./mal-abm-fast/build/mal_abm_fast --version
# mal_abm_fast 0.1.0 (M-perf F1.a scaffold)
./mal-abm-fast/build/mal_abm_fast
# prints a PRNG smoke value (stub) + a banner pointing to the design doc
```

F2 will add the real `run` subcommand: `./mal_abm_fast run --env … --habitat … --n-rollouts 100`.

## See also

- [docs/perf-cpp-abm-plan.md](../perf-cpp-abm-plan.md) — full M-perf design
- [docs/m-perf-checklist.md](../m-perf-checklist.md) — F1–F5 issue checklist
- `agents/skills/cesga/SKILL.md` — CESGA FT3 conventions
- `mal-execution/scripts/cesga-run/` — reference SLURM scripts for the Python ABM
