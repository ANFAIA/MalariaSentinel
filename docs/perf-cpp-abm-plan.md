# M-perf: C++ ABM engine — Design Plan

**Milestone**: M-perf (between M2 "ABM validation" and M3 "U-Net surrogate")
**Status**: planning — design doc, no code yet
**Module**: `mal-abm-fast/` (uv workspace member + CMake + vcpkg)
**Stack**: C++20, CMake ≥ 3.20 (manifest mode), vcpkg, Eigen, GDAL, CLI11, nlohmann-json, GoogleTest, OpenMP
**Targets**: macOS (Apple Clang) for dev, FT3 `ilk` partition (Intel oneAPI 2021.3 + impi) for production
**Author**: docs-writer · **Date**: 2026-07-15

---

## 1. Executive summary

M-perf replaces the Polars-backed M1.5 ABM (Python) with a bit-compatible C++ engine that produces identical output (within 1e-5) ~1000× faster per rollout, scaling to 100 rollouts in under 5 minutes wall time on a single FT3 `ilk` node. The output contract (`arch-abm-output-contract@v1.0`) and the per-day biology (mortality, growth, EIP, dispersal, birth) are frozen; the C++ engine re-derives the Polars expressions in C++ on a Structure-of-Arrays mosquito population, with a deterministic xoshiro256** PRNG seeded per-(rollout, op, step). Integration with the existing Python pipeline is a subprocess CLI first (replacing `mal-ghana-sim/src/mal_ghana_sim/abm/run.py`); a pybind11 binding is M-perf F5+ stretch scope.

## 2. Background

### 2.1 Current ABM (M1.5) — what works

The M1.5 refactor (commit `604327a`, July 2026) split the M1.4 Mesa-Geo ABM into a `CoordinatorModel` (spatial layer: `mesa_geo.GeoSpace`, `HabitatPatch` agents, climate lookups) and a `MosquitoSubmodel` (Polars-backed population). The per-day contract is:

1. `coordinator.activate_patches(day)` — set `patch.activated` from today's climate.
2. `patch_state = coordinator.to_dataframe()` — per-cell `pl.DataFrame` (one row per active cell).
3. `submodel.advance_day(day, patch_state)` — vectorised mortality → growth → EIP → dispersal → birth on the Polars frame.
4. `coordinator.write_state_cog(path, density, suitability, ...)` — 2-band COG + sidecar per `arch-abm-output-contract@v1.0`.

The 2026-07-15 commit (`604327a`) vectorised `to_dataframe` from O(N_active · H·W) per-cell Python loop to O(N_active) fancy-index into pre-fetched (H, W) climate grids, removing the dominant 64% per-day cost on synthetic data and 100% on the 30k-patch real case.

**KB anchors**:
- `op-m1-abm-thin` — M1 scaffolding, DONE 2026-07-09.
- `comp-m1-4-abm-thin-slice` — the M1.4 Mesa-Geo ABM (now superseded by M1.5).
- `op-m2-abm-validation` — M2 acceptance: ≥100 rollouts archived, AUC lower-95% > 0.65, ≤50 h total compute.
- `arch-abm-output-contract` — frozen v1.0 contract; the C++ engine must write a bit-compatible output (channel order, dtype, CRS, sidecar keys).

### 2.2 Where the time still goes (the residual bottleneck)

After the `to_dataframe` vectorisation, profiling of the M1.5 thin slice on a 30k-patch / 9M-agent rollout (Hetzner 16-core) shows the residual cost dominated by:

- **Polars dispatch overhead**: every `with_columns` / `filter` / `join` constructs a new Arrow frame, increments the kernel scheduler, and emits a Python-side projection. Even "vectorised" Polars has 50–200 µs of Python+Arrow overhead per operation, and `advance_day` issues ~10 such operations × 30 days × 100 rollouts ≈ 30k Polars calls.
- **Garbage collection**: the immutable Polars DataFrames are reference-counted; the 30k intermediate frames per rollout cause noticeable GC pauses (~5% wall).
- **Intermediate copies**: each Polars operation allocates a new buffer; the per-day `pl.concat` in `_birth` doubles the population buffer (~80 MB) and the next day's filter copies it again.
- **The Python loop in `_birth`**: despite the Polars vectorisation, `mosquito_submodel._birth` runs `for i in range(n_active)` to call `rasterio.transform.xy` for every active patch — 30k Python iterations per day × 30 days = 900k calls. This is the single biggest Python-side hotspot.

Estimated per-rollout cost on a 16-core Hetzner (M1.5, M3-perf budget): **~30 min/rollout**. 100 rollouts serial = 50 h (the M2 budget ceiling). This is the wall M-perf is breaking through.

### 2.3 Why C++, why now

- The Polars submodel is already SIMD-friendly; the only thing missing is C++ control over memory layout and PRNG. The biology is not the bottleneck — Python interpreter overhead and Polars dispatch are.
- FT3 has 64-core Ice Lake nodes sitting idle outside the U-Net training windows. M-perf turns them into a 100-rollout-per-5-min target generation engine for M3-M4.
- Mesa-Geo is not portable to C++ (Shapely/GEOS, RTree, GeoDataFrame), and the M1.5 refactor already removed the GeoSpace from the hot path (the coordinator's only GeoSpace use is CRS bookkeeping). A C++ engine that re-implements the Polars expressions in C++ does not need Mesa-Geo at all.

## 3. Goals and non-goals

### 3.1 Goals (M-perf acceptance)

1. **Bit-compatible output**: same env + habitat + seed → same COG + sidecar as M1.5, within 1e-5 per band, every required sidecar key present (`crs`, `transform`, `aoi_slug`, `scale`, `year`, `month`, `seed`, `generator_version`, `abm_params_hash`).
2. **M2 target hit**: 100 rollouts in **<5 min wall** on one FT3 `ilk` node.
3. **Subprocess CLI**: drop-in replacement for `mal-ghana-sim/src/mal_ghana_sim/abm/run.py`. Same `--env`, `--habitat`, `--output`, `--seed`, `--days` flags, same output path layout.
4. **F1 perf target**: ≤30 s/rollout on a single core, workstation-class (M1 Macbook / Hetzner single core).
5. **F2 perf target**: 64 rollouts in **≤1 min wall** on one `ilk` node (one rollout per core, OpenMP embarrassingly parallel).
6. **F3 perf target**: 100 rollouts in **≤3 min wall** on one `ilk` node (intra-rollout parallelism via OpenMP + SIMD on the SoA population).
7. **Determinism**: same seed + same env + same habitat → identical COG bytes (modulo 1e-5 floating-point reproducibility across compilers).
8. **FT3 integration**: SLURM `sbatch` templates for `short` (6h) and `long` (7d) partitions, `$LUSTRE` scratch for input/output, module loads in the script header.

### 3.2 Non-goals (explicit)

- **No Mesa-Geo port**. The C++ engine reads env + habitat directly (GDAL + GEOS-on-the-side); Mesa-Geo is a Python-only construct. The `coordinator.to_dataframe` is re-implemented in C++ from the env COG and the habitat gpkg.
- **No M7+ biology**. M-perf is a 1:1 port of the M1.5 thin slice. EIP stays as 110 GD threshold on 16°C base. No host-seeking, no wind dispersal, no resting state, no 4-stage life cycle, no *An. stephensi*, no resistance, no sugar feeding, no aestivation. `pitfall-overcommit-abm` still applies.
- **No output contract change**. `arch-abm-output-contract@v1.0` is frozen; the C++ engine writes the same `(C=2, H, W)` float32 COG with bands `density` + `suitability` (v2.1 M2 combined semantics: per-cell adult density / K_MAX), the same sidecar JSON, the same `128×128` deflate tiles, the same `EPSG:4326` (or AOI CRS).
- **No GPU in M-perf**. F5 (SYCL/CUDA) is a stretch and is *blocked-by* F4-results; it is M7+ scope and will not block M3-M4 U-Net training.
- **No pybind11 in M-perf core**. The subprocess CLI is the integration contract for M2/M3; a `pybind11` module is F5+ (stretch), and is not on the M2/M3 critical path.

## 4. Architecture

### 4.1 Module layout

The `mal-abm-fast/` workspace member is a sibling of `mal-ghana-sim/`. It is **not** a Python package — it is a CMake project that builds a `mal_abm_fast` CLI binary, plus a small Python package (`mal_abm_fast/`) for the parity test harness and Python-side glue.

```
mal-abm-fast/
├── CMakeLists.txt              # top-level: project, find_package, add_subdirectory
├── vcpkg.json                  # manifest: eigen3, gdal, cli11, nlohmann-json, gtest
├── cmake/
│   ├── FindFT3Modules.cmake    # helper for intel/2021.3.0 + impi/2021.3.0 detection
│   └── CompilerWarnings.cmake  # -Wall -Wextra -Wpedantic + -Werror on CI
├── include/
│   └── mal_abm_fast/
│       ├── prng.hpp            # xoshiro256** + splitmix64
│       ├── dispersal.hpp       # clipped Gaussian in metres
│       ├── eip.hpp             # degree-day accumulation
│       ├── climate.hpp         # env COG reader
│       ├── habitat_engine.hpp  # gpkg reader → active-cell registry
│       ├── mosquito_state.hpp  # SoA population + day loop
│       └── output_contract.hpp # COG + sidecar writer (asserts v1.0 schema)
├── src/
│   ├── prng.cpp
│   ├── dispersal.cpp
│   ├── eip.cpp
│   ├── climate.cpp
│   ├── habitat_engine.cpp
│   ├── mosquito_state.cpp
│   ├── output_contract.cpp
│   └── main.cpp                # CLI entry point (CLI11)
├── tests/
│   ├── CMakeLists.txt
│   ├── test_prng.cpp           # GoogleTest
│   ├── test_dispersal.cpp
│   ├── test_eip.cpp
│   ├── test_output_contract.cpp
│   ├── test_parity.py          # Python harness: same seed → same COG vs M1.5
│   └── test_benchmark.cpp      # perf binary
├── python/
│   └── mal_abm_fast/
│       ├── __init__.py
│       └── parity.py           # `python -m mal_abm_fast.parity` CLI
├── slurm/
│   ├── short.sh                # #SBATCH --partition=short --time=06:00:00
│   └── long.sh                 # #SBATCH --partition=long  --time=7-00:00:00
└── README.md
```

**Naming convention**: `mal_abm_fast` (C++ namespace) / `mal_abm_fast` (Python package, importable from the parity harness). The CLI binary is `mal_abm_fast` and is invoked as `mal_abm_fast run --env ... --habitat ... --output ... --seed 42 --days 30`.

### 4.2 Per-day contract (Polars → C++)

The M1.5 submodel's `advance_day` is a 5-step sequence. The C++ engine re-derives each step on the SoA population.

**SoA layout** (`mosquito_state.hpp`):
```cpp
struct MosquitoState {
    // Per-agent columns (SoA, not AoS — contiguous in memory for SIMD).
    std::vector<int64_t>   unique_id;   // not touched by the day loop; for tests
    std::vector<int64_t>   patch_id;    // join key with patch-state
    std::vector<int32_t>   row;         // (row, col) per agent, updated by dispersal
    std::vector<int32_t>   col;
    std::vector<uint8_t>   stage;       // 0 = larva, 1 = adult (Categorical → uint8)
    std::vector<float>     lon;         // post-dispersal lon (M2 combined C1)
    std::vector<float>     lat;         // post-dispersal lat
    std::vector<float>     eip_progress;
    std::vector<int32_t>   stage_age;
    // Per-step state (small, indexed by step within the day loop).
    xoshiro256pp            rng;        // per-rollout sub-stream
    int32_t                 n() const { return static_cast<int32_t>(patch_id.size()); }
};
```

**Per-day operations** (mirror the M1.5 Polars expressions, see `mal-ghana-sim/src/mal_ghana_sim/abm/mosquito_submodel.py:219-460`):

1. **Larva mortality at inactive patches** — `mosquito_state.larva_mortality(patch_state)`. Mark `stage = REMOVED` for larvae whose `patch_id` is in the inactive set. `REMOVED` is a sentinel written into a parallel `alive: std::vector<bool>` vector, not into `stage` (so the SoA stays dense for SIMD). Sweep at end of day.
2. **Larva growth + EIP accumulation** — `mosquito_state.larva_growth(patch_state)`. For alive larvae at active patches: `stage_age += 1`, `eip_progress += max(0, temp_d - 16)`. Per-agent temperature comes from a pre-fetched `temp_d[patch_id]` lookup.
3. **Larva → adult (EIP threshold)** — `mosquito_state.larva_to_adult()`. If `eip_progress >= 110`, set `stage = ADULT`, reset `stage_age = 0`. The M1.5 collapse (no pupa) is preserved.
4. **Adult dispersal** — `mosquito_state.adult_dispersal()`. For each adult, draw `u ~ U(0,1)`. If `u < 0.2`, draw `(dx, dy) ~ N(0, 1000m^2)`, clip to `dist <= 2000m`, convert to (dlon, dlat) at the adult's current latitude (`m_per_deg_lon = 111320 * cos(lat)`), add to `lon`/`lat`. The draw uses the per-(rollout, op, step) sub-seed (see §4.3).
5. **Birth** — `mosquito_state.birth(patch_state)`. For each active patch, draw `n_birth ~ Binomial(K=1000, p=0.005)`. The newborn `lon`/`lat` is the centre of the patch's (row, col) cell on the AOI transform (M2 combined C1, replaces the M1.5 (0, 0) placeholder). `patch_id`, `row`, `col` are copied from the parent patch. `stage = LARVA`, `eip_progress = 0`, `stage_age = 0`. `unique_id` is allocated from a monotonic counter.

**End-of-day sweep** removes the `alive == false` rows in one pass, preserving SoA contiguity. The population is therefore always a dense `n()`-sized vector (no holes).

**The C++ `birth` is the cleanest improvement**: the M1.5 `_birth` has a `for i in range(n_active)` Python loop calling `rasterio.transform.xy` per patch (~30k iterations per day). The C++ version pre-computes the (lon, lat) per (row, col) once at engine startup (the AOI transform is a 6-tuple affine), then the `binomial` draws produce per-patch counts that are looked up via an `O(1)` `std::vector<float>` indexed by `patch_id`. Net: 30k Python iterations → 30k SIMD-friendly integer draws.

### 4.3 PRNG scheme

The M1.5 submodel uses `numpy.random.default_rng(seed)`, which is PCG64. The C++ engine uses **xoshiro256\*\***, seeded by a **splitmix64** sub-stream scheme that gives deterministic, non-overlapping per-(rollout, op, step) sub-seeds.

```cpp
// SplitMix64: 64-bit avalanche mixer; maps any 64-bit seed to a "good" 64-bit value.
static uint64_t splitmix64(uint64_t& state) {
    uint64_t z = (state += 0x9E3779B97F4A7C15ULL);
    z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ULL;
    z = (z ^ (z >> 27)) * 0x94D049BB133111EBULL;
    return z ^ (z >> 31);
}

// xoshiro256** state, seeded by four splitmix64 draws.
struct xoshiro256pp {
    uint64_t s[4];
    void seed_from(uint64_t s0) {
        // Use splitmix to expand s0 into four 64-bit values.
        uint64_t sm = s0;
        for (int i = 0; i < 4; ++i) s[i] = splitmix64(sm);
    }
    uint64_t next() { /* standard xoshiro256** */ }
    double   uniform() { return (next() >> 11) * (1.0 / (1ULL << 53)); }
    double   normal()  { /* Box-Muller on uniform() */ }
    int32_t  binomial(int32_t n, double p);  // for births
};
```

**Sub-seed scheme** (deterministic, never overlaps):
```
seed_rollout  = splitmix(seed XOR (rollout_idx << 32))          // one per rollout
seed_op_kind  = splitmix(seed_rollout XOR hash(op_kind))         // per operation
seed_per_step = splitmix(seed_op_kind XOR step)                  // per step within an op

// At step N, the engine holds a xoshiro256** state seeded with seed_per_step.
// Per-draw uniforms come from .next() on the current state. State persists
// across draws (so a per-step sub-seed also implicitly produces a per-draw
// sequence).
```

**Hash on `op_kind`**: 5 named ops (`larva_mortality`, `larva_growth`, `larva_to_adult`, `adult_dispersal`, `birth`). The hash is a simple FNV-1a over the lowercase string — collision-free on this 5-element domain.

**Why this matters for parity**: the M1.5 submodel draws in a fixed order (`_rng.random(n)` first, then `_rng.normal(...)` for dispersers, then `_rng.binomial(...)` for births). The C++ engine draws in the same order, and the sub-seeds ensure the per-op streams are independent. Two engines (Python + C++) with the same `seed` will not produce *bit-equal* draws because PCG64 ≠ xoshiro256**, but the **statistical** output is within the 1e-5 tolerance (the dispersal kernel is a clipped Gaussian; tiny individual differences average out over millions of agents).

### 4.4 Output contract writer

`output_contract.hpp` writes a bit-compatible COG + sidecar per `arch-abm-output-contract@v1.0`. The writer's **invariants** (asserted at runtime, not just documented):

```cpp
void write_state_cog(
    const std::string& path,
    const float* density,            // (H, W) row-major
    const float* suitability,        // (H, W) row-major
    int H, int W,
    const AOI& aoi,
    int year, int month, int seed,
    const std::string& abm_params_hash
);
```

**Hard asserts inside the writer** (GoogleTest checks too, but the production writer asserts on every call):
1. `H == W == 128` *or* the sidecar's `transform` matches the AOI's `bbox` at the AOI's `resolution_m`. (The contract allows AOI < 128×128 with zero-padding; the writer must NOT crash on a 64×64 AOI.)
2. `density.dtype == float32` and `suitability.dtype == float32` (compile-time check via `static_assert` on the input pointer type).
3. Sidecar JSON has all 9 required keys: `crs`, `transform`, `aoi_slug`, `scale`, `year`, `month`, `seed`, `generator_version`, `abm_params_hash`. Optional keys allowed: `rainfall_cap_mm` (env only), `k_max` (state only), `contract_version`, `band_names`, `nodata`, `shape`.
4. The COG has 2 bands with the exact descriptions `density` (band 1) and `suitability` (band 2). Set via `GDALSetDescription` (the C++ equivalent of `rasterio.set_band_description`).
5. The COG is **tiled** (BLOCKXSIZE=128, BLOCKYSIZE=128), **deflate-compressed** (COMPRESS=DEFLATE), and tagged with the AOI's CRS (`EPSG:4326` for the thin slice, or UTM zone if the AOI is projected).
6. The NoData sentinel is `-9999.0` (state rasters) and is written into the GeoTIFF metadata.
7. The `transform` is a 6-tuple affine in `rasterio`-row-major order: `[a, b, c, d, e, f]` where `(a, b)` is the pixel size (positive for north-up rasters) and `(c, f)` is the upper-left corner.

**Bit-compat goal**: a COG written by the C++ engine and one written by `coordinator.write_state_cog` should be byte-identical (modulo the 1e-5 tolerance on the raster values, which is the per-band mean difference, not the per-cell difference). The sidecar JSON should be byte-identical (same indentation, same key order) — both writers use `nlohmann-json` / `json.dump(indent=2)` with sorted keys (sorted on both sides).

**Bit-compat caveat**: the per-cell values will differ at the 1e-5 level because the C++ engine uses xoshiro256** and the Python engine uses PCG64. The **band-mean** difference is what the parity test measures, not the per-cell max diff.

## 5. Performance model

These are **estimates**, not promises — F1 will measure them and may revise F2/F3 targets if reality diverges by more than 2×.

| Implementation | Single rollout (30 d, 30k patches, ~9M agents) | 100 rollouts serial | 100 rollouts parallel |
|---|---|---|---|
| M1.5 Python+Polars (16-core Hetzner) | ~30 min | ~50 h (M2 budget ceiling) | n/a |
| M-perf F1: C++ single-thread (Apple Clang / icx, 1 core) | ~5–15 s | ~10–25 min | n/a |
| M-perf F2: 64 rollouts in parallel (1 node, 64 cores) | ~5–15 s/rollout | n/a | ~5–15 s wall |
| M-perf F3: intra-rollout OpenMP + SIMD (1 node, 64 cores) | ~1–3 s/rollout | n/a | **~1–3 min wall** |
| M-perf F4: MPI multi-node (2–8 `ilk` nodes) | ~1–3 s/rollout | n/a | ~1–3 min wall (no change vs F3) |
| M2 acceptance target | — | — | **<5 min wall for 100 rollouts** |

**Where the speedup comes from**:
- **Python interpreter + Polars dispatch removal** (~50–100×): 5–15 s instead of 30 min for a single rollout.
- **OpenMP embarrassingly parallel rollouts (F2)**: 64 rollouts / 64 cores → ~1× the single-rollout time on a full node.
- **OpenMP intra-rollout + SIMD (F3)**: the SoA population is contiguous `float` arrays; the per-day operations are simple kernels (element-wise add, draw Bernoulli, draw normal, clip). SIMD on a single Ice Lake core = 8× `float32` lanes on AVX-512 = ~1–3 s/rollout.
- **MPI (F4)**: not on the critical path. The F3 estimate already hits the M2 target; F4 only matters if F3 doesn't (e.g. memory bandwidth saturation).

**Why F4 is gated**: see §10 (Risks & pitfalls). Starting MPI on a guess burns 2–4 weeks of work and complicates the build. Don't.

## 6. Phases (F1–F5)

### F1 — Load-bearing: single-thread C++ engine with bit-compatible output

**Scope**: scaffold `mal-abm-fast/`, port the 5 per-day operations + climate/habitat readers + COG writer to C++20, single-thread, single-rollout. Parity test against the M1.5 Python ABM on a small synthetic AOI (5 patches, 1k agents, 30 days). Benchmark on a workstation single core.

**Deliverable**: `mal-abm_fast run --env ... --habitat ... --output ... --seed 42 --days 30` produces a COG that matches the M1.5 output within 1e-5 per band mean, with all 9 sidecar keys present.

**Acceptance criteria**:
1. Parity test: 1000 random `(env, habitat, seed, days)` triples; for each, run both M1.5 and the C++ engine; assert `|mean(C++ density) - mean(M1.5 density)| < 1e-5` and the same for suitability. Test runs in `<10 min` on a workstation.
2. Determinism test: same triple → same COG bytes (within the same 1e-5 tolerance) on two separate runs.
3. Benchmark: single rollout, single core, ≤30 s on a workstation (M1 Macbook or Hetzner single core).
4. SLURM `short.sh` template produces a working `sbatch` that runs 1 rollout on an `ilk` node.
5. All GoogleTest unit tests pass (`prng`, `dispersal`, `eip`, `output_contract`).

**Dependencies**: none. F1 is the foundation.

**Gating rules**: none. F1 must land before F2/F3.

### F2 — OpenMP embarrassingly parallel rollouts

**Scope**: add a `OMP_NUM_THREADS` env var; the engine runs N rollouts in parallel, one per thread, with each thread getting its own `(seed_rollout, op_kind, step)` sub-stream. No intra-rollout parallelism yet.

**Deliverable**: a `--n-rollouts 64` flag (or `MAL_ABM_N_ROLLOUTS` env var) that runs 64 rollouts on 64 cores, each writing to its own `*_seed{NNNN}.tif`.

**Acceptance criteria**:
1. 64 rollouts, 1 `ilk` node, 64 cores → ≤1 min wall.
2. Per-rollout output is identical to F1 single-thread output (within 1e-5).
3. Sub-stream isolation: a corrupted `seed_op` for one rollout does not affect the others (verified by a deliberate corruption test).

**Dependencies**: F1.

**Gating rules**: F2 must hit its 1-min target. If it doesn't, profile F1 to find the bottleneck before moving to F3.

### F3 — OpenMP intra-rollout + SIMD on SoA

**Scope**: parallelise the per-day operations across the population. The `birth` step (per-patch binomial draws) and the `larva_growth` step (per-agent `eip_progress += ...`) are embarrassingly parallel across agents. The `adult_dispersal` step is per-adult random draws — also parallel. SIMD on the SoA arrays via `std::experimental::simd` (C++20) or compiler intrinsics.

**Deliverable**: same CLI as F2, with `--omp-intra-rollout` flag (default on). On 1 `ilk` node (64 cores), each rollout uses 1 thread; F3 turns 1 thread into 64 threads per rollout (so 64 rollouts in 64 threads, then re-distribute).

**Acceptance criteria**:
1. 100 rollouts, 1 `ilk` node → ≤3 min wall.
2. M2 target hit: 100 rollouts, 1 `ilk` node → **<5 min wall**.
3. Per-rollout output still within 1e-5 of the M1.5 reference (the SIMD reductions introduce floating-point reorderings; the tolerance accounts for this).
4. AVX-512 path is selected at runtime via `__builtin_cpu_supports("avx512f")`; falls back to AVX2 on Apple Clang (M1/M2 do not have AVX-512).

**Dependencies**: F1, F2.

**Gating rules**: F3 is the M2 acceptance milestone. F4 only starts if F3 misses the <5 min target by >2×.

### F4 — MPI multi-node (GATED)

**Scope**: domain-decompose the AOI across nodes; each node runs a subset of the active patches and exchanges boundary adults via MPI. Requires `impi/2021.3.0` on FT3.

**Deliverable**: `--mpi` flag on the CLI; runs N rollouts across M nodes, with patch-state partitioned by `(row, col)` ranges.

**Acceptance criteria**:
1. 100 rollouts, 4 `ilk` nodes → ≤3 min wall.
2. Per-rollout output still within 1e-5 of the M1.5 reference.
3. Infiniband HDR 100 is used for MPI transport (verified via `mpirun --report-bindings` and `ibstat`).

**Dependencies**: F1, F2, F3 **AND** a documented profiling result showing F3 misses the M2 target by >2×.

**Gating rules** (the F4 pitfall, see §10):
- **F4 does not start until F1+F2+F3 are in production** (i.e. merged to main, passing all tests, running on FT3).
- **F4 does not start on a guess**. The profiling report must show "per-rollout cost is the bottleneck, not the per-rollout parallelisation".
- If F3 hits the M2 target, F4 is **cancelled** and moved to M7+.

### F5 — SYCL / CUDA stretch (M7+ scope, not in M-perf)

**Scope**: port the SoA kernels to SYCL (Intel oneAPI DPC++) for the FT3 Ponte Vecchio GPUs, or to CUDA for an NVIDIA A100 node. F5 is **explicitly out of M-perf** — it is a stretch that depends on F4-results.

**Deliverable**: same CLI as F4, with `--gpu` flag.

**Acceptance criteria**: TBD, depends on F3/F4 results.

**Dependencies**: F4-results (F4 success, F4 cancellation, or M7+ biology being added).

**Gating rules**: F5 is **blocked-by F4-results**. If F4 is cancelled (F3 hits the target), F5 is also cancelled.

## 7. Build & dependencies

### 7.1 CMakeLists.txt (top-level)

```cmake
cmake_minimum_required(VERSION 3.20)
project(mal_abm_fast CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# vcpkg manifest mode (vcpkg.json in the same directory).
include(${CMAKE_CURRENT_SOURCE_DIR}/vcpkg.json OPTIONAL RESULT_VARIABLE VCPKG_JSON)

# Find packages via vcpkg (or system packages on macOS dev).
find_package(Eigen3  REQUIRED CONFIG)
find_package(GDAL   REQUIRED)        # libgdal-dev on Linux, gdal on macOS via brew
find_package(CLI11  REQUIRED CONFIG)
find_package(nlohmann_json REQUIRED)
find_package(OpenMP REQUIRED)
find_package(GTest  REQUIRED)

add_subdirectory(src)
enable_testing()
add_subdirectory(tests)
```

### 7.2 vcpkg.json (manifest)

```json
{
  "name": "mal-abm-fast",
  "version-string": "0.1.0",
  "dependencies": [
    "eigen3",
    "gdal",
    "cli11",
    "nlohmann-json",
    "googletest"
  ]
}
```

### 7.3 FT3 module loads (`slurm/short.sh`)

```bash
#!/bin/bash
#SBATCH --partition=short
#SBATCH --time=06:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=64
#SBATCH --job-name=mal-abm-fast
#SBATCH --output=runs/%j.out
#SBATCH --error=runs/%j.err
set -euo pipefail

module purge
module load intel/2021.3.0
module load impi/2021.3.0
module load gdal/3.7.0

# LUSTRE is the FT3 scratch filesystem; place input/output there.
export MAL_ABM_INPUT_DIR="$LUSTRE/mal-abm-fast/input"
export MAL_ABM_OUTPUT_DIR="$LUSTRE/mal-abm-fast/output"
mkdir -p "$MAL_ABM_INPUT_DIR" "$MAL_ABM_OUTPUT_DIR"

# Run 100 rollouts in parallel, one per core.
OMP_NUM_THREADS=64 OMP_PROC_BIND=close OMP_PLACES=cores \
  srun mal_abm_fast run \
    --env "$MAL_ABM_INPUT_DIR/ghana_regional_2024_06_env.tif" \
    --habitat "$MAL_ABM_INPUT_DIR/ghana_regional_2024_06_habitat_patches.gpkg" \
    --output-dir "$MAL_ABM_OUTPUT_DIR" \
    --n-rollouts 100 \
    --seed-base 1 \
    --days 30
```

### 7.4 macOS dev setup

```bash
# Apple Clang 15 (Xcode 15 toolchain) — no AVX-512 on M1/M2, falls back to AVX2.
brew install cmake ninja pkg-config gdal eigen cli11 nlohmann-json googletest
cmake -S mal-abm-fast -B mal-abm-fast/build -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_PREFIX_PATH="$(brew --prefix gdal);$(brew --prefix eigen);$(brew --prefix nlohmann-json);$(brew --prefix googletest)"
cmake --build mal-abm-fast/build -j
ctest --test-dir mal-abm-fast/build --output-on-failure
```

## 8. Testing strategy

### 8.1 Unit tests (GoogleTest)

| Test | File | What it asserts |
|---|---|---|
| `test_prng` | `tests/test_prng.cpp` | `splitmix64` is bijective on the seed space; `xoshiro256**` produces the reference test vectors from Vigna; sub-seed scheme is collision-free on the 5 op kinds × 30 steps × 100 rollouts. |
| `test_dispersal` | `tests/test_dispersal.cpp` | Clipped Gaussian: the empirical mean is 0, the empirical stddev is 1000 m, the empirical max is 2000 m. The `cos(lat)` correction produces the correct m→deg conversion. |
| `test_eip` | `tests/test_eip.cpp` | `eip_progress` accumulates `max(0, T - 16)` correctly; EIP threshold triggers larva→adult at exactly 110 GD; larvae at inactive patches do not accumulate. |
| `test_output_contract` | `tests/test_output_contract.cpp` | Writer asserts all 9 sidecar keys; COG has 2 bands with the correct descriptions; COG is tiled (128×128), deflate-compressed, EPSG-tagged; NoData is `-9999.0`. |

### 8.2 Parity test (Python harness)

The parity test is the most important test in M-perf. It runs the M1.5 Python ABM and the C++ engine on the same `(env, habitat, seed, days)` triple and asserts the statistical output is within 1e-5.

**CLI**: `python -m mal_abm_fast.parity --env ... --habitat ... --n-rollouts 1000 --days 30 --report parity_report.json`

**Harness logic** (lives in `python/mal_abm_fast/parity.py`):
1. Generate 1000 random `(seed, days)` pairs (deterministic, fixed RNG).
2. For each pair, invoke the M1.5 Python ABM via `subprocess.run(["uv", "run", "python", "-m", "mal_ghana_sim.abm.run", ...])` and the C++ engine via `subprocess.run(["mal_abm_fast", "run", ...])`.
3. Read both COGs with `rasterio`, compute `mean(C++ band 0) - mean(M1.5 band 0)` and the same for band 1.
4. Assert both deltas are `< 1e-5` for every pair.
5. Write `parity_report.json` with per-pair deltas and the max delta over the 1000 pairs.

**Why 1e-5 and not bit-equal**: xoshiro256** ≠ PCG64, so the per-cell values will differ. The dispersal kernel is a clipped Gaussian over millions of agents, so the per-band mean converges to the same value within 1e-5. The parity test asserts on the **statistical** output, not the per-cell max diff. The supervisor may tighten this to 1e-6 or 1e-7 after F1 lands and the empirical distribution is known.

**Why we test 1000 pairs, not 1**: a single pair passing is consistent with both engines being correct *and* both being broken in the same way. 1000 pairs across random seeds and days catches systematic drift.

### 8.3 Determinism test

Same `(env, habitat, seed, days)` → same COG bytes (modulo the 1e-5 tolerance) on two separate runs. This is a stronger version of the parity test: it asserts the C++ engine is internally deterministic (no time-dependent state, no thread-id-derived seeds, no uninitialised memory).

CLI: `python -m mal_abm_fast.parity --n-rollouts 100 --determinism` runs each `(seed, days)` pair twice and asserts the COG bytes are identical.

### 8.4 Performance test (benchmark binary)

`tests/test_benchmark.cpp` is a `main()` that:
1. Loads the env COG + habitat gpkg once.
2. Runs N rollouts (default 1, configurable via `--n-rollouts`).
3. Reports wall time per rollout and total wall time.

Targets:
- **F1**: single rollout, single core, ≤30 s on a workstation (Apple M1/M2 or Hetzner single core).
- **F2**: 64 rollouts, 1 `ilk` node, ≤1 min wall.
- **F3**: 100 rollouts, 1 `ilk` node, ≤3 min wall (with `--omp-intra-rollout` on).

## 9. HPC integration

### 9.1 SLURM templates

Two templates in `mal-abm-fast/slurm/`:

- **`short.sh`** — `short` partition, 6h wall, 1 node, 64 cores, 64 GB RAM (the per-rollout memory budget for F3 is ~500 MB × 64 rollouts = 32 GB; 64 GB is comfortable).
- **`long.sh`** — `long` partition, 7d wall, 1–8 nodes, for overnight multi-rollout runs (e.g. 1000 rollouts for U-Net training data).

The template headers (see §7.3) include the `intel/2021.3.0`, `impi/2021.3.0`, `gdal/3.7.0` module loads, the `$LUSTRE` scratch env vars, and the `OMP_*` env vars for binding.

### 9.2 Data transfer

Input env + habitat files live in `data/runs/<aoi>/` locally. On FT3, the convention is `$LUSTRE/mal-abm-fast/input/` (rsync from local before submitting) and `$LUSTRE/mal-abm-fast/output/` (the run writes here). The `sbatch` script is responsible for `mkdir -p` and the `srun` invocation reads from `$LUSTRE`.

For multi-node MPI (F4), the input is replicated to each node's local SSD via `slurm --spread-job` (SLURM distributes the `srun` payload across nodes; the input is a single `rsync` followed by a per-node read).

### 9.3 Output archival

The 100 rollouts × 30 days × ~10 KB per COG ≈ 30 MB per month per AOI. The `$LUSTRE` scratch holds ~10 TB, so a year of monthly rollouts is ~5 GB. The supervisor script (`slurm/short.sh`) optionally `--rsync-back` to `data/runs/` on completion.

## 10. Risks & pitfalls

The M-perf design inherits and respects the existing KB pitfalls. The new M-perf-specific pitfall (`pitfall-premature-mpi`) is recorded in the knowledge graph (KB write deferred to the M-perf execution phase; see §11 Open questions).

### 10.1 `pitfall-overcommit-abm` — don't add biology

**Source**: `pitfall-overcommit-abm` in `project-wisdom`.

**Application to M-perf**: the C++ engine is a 1:1 port of the M1.5 thin slice. **No** EIP enrichment, no host-seeking, no wind dispersal, no 4-stage life cycle, no *An. stephensi*, no resistance, no sugar feeding, no aestivation. M-perf is a performance rewrite, not a biology rewrite. The biology rewrite is M7+ (`op-m7-abm-full`).

**Symptom of hitting this pitfall in M-perf**: a PR adds a new per-day operation (e.g. wind dispersal) under the guise of "we have C++ now, let's use it". The C++ engine's biology must be a *copy* of `mosquito_submodel.py`'s 5 ops, not an extension.

### 10.2 `pitfall-hardcoded-aoi` — region-agnostic

**Source**: `pitfall-hardcoded-aoi` in `project-wisdom`.

**Application to M-perf**: the C++ engine reads the AOI from the env COG and the habitat gpkg — there is no hardcoded `ghana` bbox or `EPSG:4326` assumption in the C++ code. The AOI is a parameter (see `mal-commonlib/src/mal_commonlib/aoi.py`); the engine consumes `AOI.crs`, `AOI.bbox`, `AOI.scale`, `AOI.slug`. The C++ `AOI` struct is a mirror of the Pydantic model (read once from the env COG sidecar, no separate JSON).

**Symptom of hitting this pitfall in M-perf**: a PR adds a `if (aoi.slug == "ghana")` branch. The C++ engine must work for any AOI that satisfies the output contract; the AOI is an input, not a switch.

### 10.3 `pitfall-premature-mpi` (new) — F4 is gated

**Source**: not yet in the KB; the supervisor (this design doc's audience) should `memory_node`-record it before F1 starts.

**Application to M-perf**: F4 (MPI multi-node) is the most complex deliverable in M-perf (2–4 weeks of work, MPI build setup, domain decomposition, boundary exchange, Infiniband tuning). It only matters if F3 misses the M2 target by >2×. If F3 hits <5 min for 100 rollouts on a single `ilk` node, F4 is **cancelled** and the effort is moved to M7+.

**Gating rule** (repeated from §6 F4):
1. F4 does not start until F1+F2+F3 are in production (merged to main, all tests pass, running on FT3).
2. F4 does not start on a guess. The profiling report must show "per-rollout cost is the bottleneck, not the per-rollout parallelisation".
3. If F3 hits the M2 target, F4 is **cancelled** and the work is moved to M7+ (`op-m7-abm-full`).

**Symptom of hitting this pitfall in M-perf**: a PR opens F4 work in parallel with F1/F2/F3. F4 is the *last* deliverable in M-perf, gated on F1+F2+F3 results.

### 10.4 Compiler portability (Apple Clang vs Intel oneAPI)

**Risk**: Apple Clang on M1/M2 does not support `std::experimental::simd` (C++20 SIMD is a GCC/Intel extension). Intel `icx` does. The SoA + SIMD path in F3 must be guarded by `#ifdef __INTEL_COMPILER` (or `__clang__` + `__has_include(<experimental/simd>)`).

**Mitigation**: F1 does not use SIMD. F3 is gated on F1, and the F3 engineer profiles both `icx` and Apple Clang paths before committing to a SIMD backend. The M1 dev box runs the AVX2 path; the FT3 production runs the AVX-512 path.

## 11. Open questions

1. **GDAL version on FT3**: the `slurm/short.sh` template hardcodes `gdal/3.7.0`; we need to confirm this is the right module name on the `ilk` partition (the FT3 user guide lists the available modules; see References).
2. **vcpkg on FT3**: vcpkg is a Linux/macOS toolchain; FT3 may not have it pre-installed. The build script may need to clone the vcpkg repo and bootstrap it (1-time cost; cache the binary tree on `$LUSTRE`).
3. **Bit-compat tolerance**: 1e-5 per band mean is the supervisor's pre-meeting estimate. The actual tolerance depends on the empirical distribution of `|C++ − M1.5|` over 1000 random seeds. The F1 parity test report will tighten or loosen this.
4. **Sub-seed collision risk**: splitmix64 on `(seed_rollout XOR hash(op_kind))` — the 5 op kinds × 30 steps × 100 rollouts = 15k sub-streams. The probability of a collision in a 64-bit space is ~10⁻¹⁴, but a `static_assert` in `prng.hpp` should verify the first 1000 sub-seeds are distinct (defence-in-depth, not a real concern).
5. **Should the parity test live in CI?**: the parity test takes ~10 min on a workstation; running it in CI on every PR is expensive. The proposal: run on every merge to `main` and on a nightly schedule, not on every PR. The supervisor should decide.

## 12. References

### 12.1 Existing docs

- `docs/abm-output-contract.md` — `arch-abm-output-contract@v1.0`, the frozen output contract.
- `docs/abm-mesa-geo-adaptation.md` — the M1 thin-slice biology scope.
- `mal-ghana-sim/src/mal_ghana_sim/abm/model.py` — the M1.5 facade (`AnophelesABM`).
- `mal-ghana-sim/src/mal_ghana_sim/abm/coordinator.py` — the per-day contract (`CoordinatorModel`).
- `mal-ghana-sim/src/mal_ghana_sim/abm/mosquito_submodel.py` — the per-day operations to port (mortality, growth, EIP, dispersal, birth).
- `mal-ghana-sim/src/mal_ghana_sim/abm/run.py` — the Python CLI; the C++ CLI is a drop-in replacement.
- `mal-commonlib/src/mal_commonlib/aoi.py` — the AOI schema; both Python and C++ consume this.

### 12.2 Knowledge graph (KB) nodes

- `op-m1-abm-thin` — M1: ABM scaffolding (DONE 2026-07-09).
- `comp-m1-4-abm-thin-slice` — M1.4 Mesa-Geo ABM thin slice (the M1.5 ancestor).
- `op-m2-abm-validation` — M2: ABM validation (≥100 rollouts, AUC > 0.65, ≤50 h).
- `op-m3-m4-unet` — M3-M4: U-Net training (the consumer of M-perf output).
- `op-m6-sdss-end-to-end` — M6: SDSS end-to-end run.
- `op-m7-abm-full` — M7+: ABM in full (the biology rewrite that M-perf is *not* doing).
- `arch-abm-output-contract` — frozen v1.0 output contract.
- `pitfall-overcommit-abm` — don't add biology before SDSS loop is validated.
- `pitfall-hardcoded-aoi` — region-agnostic from M1.
- `pitfall-premature-mpi` (new, pending KB write) — F4 MPI is gated on F1-F3 results.
- `pattern-thin-slice-teacher` — build the simplest ABM that produces the patterns the U-Net needs.
- `pattern-region-agnostic-data` — AOI / CRS / data source are parameters, not constants.

### 12.3 HPC and tooling

- CESGA FT3 user guide: <https://www.cesga.es/en/finisterrae-iii-user-guide> (Intel oneAPI 2021.3 + impi 2021.3 module names, `ilk` partition specs).
- vcpkg manifest mode: <https://vcpkg.io/en/docs/users/manifests.html>.
- xoshiro256** reference + test vectors: <https://prng.di.unimi.it/xoshiro256starstar.c>.
- GDAL C++ API (COG + GeoTIFF + sidecar): <https://gdal.org/api/raster_cpp.html>.
- OpenMP 5.0 on Ice Lake: <https://www.openmp.org/spec-html/5.0/openmp-spec.html>.
- Intel oneAPI DPC++ (F5 stretch, not M-perf): <https://www.intel.com/content/www/us/en/developer/tools/oneapi/dpc-compiler.html>.

### 12.4 GitHub Project v2 board (ANFAIA #11)

- The M-perf issues are created from `docs/m-perf-checklist.md`; the #TBD placeholders are replaced with real GH issue numbers by the user.
- Labels on every issue: `M-perf`, type (`enhancement` or `investigation`), `blocked` (F4, F5).
- The board columns: Todo (scoped, not started), In Progress (exactly one), Done (closed with commit SHA).
