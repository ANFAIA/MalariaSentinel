# M-perf F1.a — Scaffold Checklist

**Status**: in progress (this PR)
**Acceptance**: the module compiles locally (macOS) and on FT3 (an ilk compute node), the smoke test passes, the SLURM templates submit and complete.

## Files created (F1.a)

### Build system (f1a-build agent)
- [ ] `mal-abm-fast/CMakeLists.txt`
- [ ] `mal-abm-fast/cmake/CompilerWarnings.cmake`
- [ ] `mal-abm-fast/cmake/FindFT3Modules.cmake` (stub for F2/F3)
- [ ] `mal-abm-fast/vcpkg.json`
- [ ] `mal-abm-fast/.gitignore`
- [ ] `mal-abm-fast/pyproject.toml`
- [ ] root `pyproject.toml` — add `"mal-abm-fast"` to `[tool.uv.workspace] members`

### C++ stubs (f1a-cxx agent)
- [ ] `mal-abm-fast/include/mal_abm_fast/{prng,dispersal,eip,climate,habitat_engine,mosquito_state,output_contract}.hpp`
- [ ] `mal-abm-fast/src/{prng,dispersal,eip,climate,habitat_engine,mosquito_state,output_contract}.cpp` (stubs)
- [ ] `mal-abm-fast/src/main.cpp` (CLI11 hello world)
- [ ] `mal-abm-fast/src/CMakeLists.txt`
- [ ] `mal-abm-fast/tests/CMakeLists.txt`
- [ ] `mal-abm-fast/tests/test_smoke.cpp`

### HPC + docs (this agent)
- [ ] `mal-abm-fast/slurm/short.sh`
- [ ] `mal-abm-fast/slurm/long.sh`
- [ ] `mal-abm-fast/README.md`
- [ ] `mal-abm-fast/docs/perf-cpp-abm-f1a-checklist.md` (this file)

## Verification

### Local (macOS, Apple Clang)
```bash
brew install cmake ninja pkg-config gdal eigen cli11 nlohmann-json googletest
cmake -S mal-abm-fast -B mal-abm-fast/build -G Ninja \
      -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_PREFIX_PATH="$(brew --prefix gdal);$(brew --prefix eigen);$(brew --prefix nlohmann-json);$(brew --prefix googletest)"
cmake --build mal-abm-fast/build -j
ctest --test-dir mal-abm-fast/build --output-on-failure
./mal-abm-fast/build/mal_abm_fast --version
./mal-abm-fast/build/mal_abm_fast   # PRNG smoke + banner
```

### CESGA FT3 (ilk compute node)
```bash
sbatch mal-abm-fast/slurm/short.sh
squeue -u $USER
# when done (SLURM writes the .o file to the job's cwd, which is $PROJECT_ROOT):
cat mal-abm-fast-<jobid>.o
```

## Acceptance criteria

- [ ] `cmake --build` succeeds on macOS with no warnings (apart from any compiler-version noise).
- [ ] `ctest` reports 3/3 tests passing (`VersionConstant`, `PrngStub`, `EipAccumulate`).
- [ ] `./mal_abm_fast --version` prints `mal_abm_fast 0.1.0 (M-perf F1.a scaffold)`.
- [ ] `./mal_abm_fast` prints the banner + a PRNG smoke uniform draw.
- [ ] `sbatch mal-abm-fast/slurm/short.sh` runs on FT3 ilk and exits 0.

## Next

F1.b — implement the climate + habitat_engine modules (env.tif + gpkg readers).
F1.c — implement the SoA + PRNG + day loop (5 per-day operations).
F1.d — implement the output contract writer (bit-compatible COG + sidecar).
F1.e — parity test harness (Python: same seed → same COG within 1e-5 vs M1.5).
