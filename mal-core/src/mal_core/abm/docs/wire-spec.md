# mal-abm-fast — Wire Spec (F1.b / F1.c)

**Audience**: the 4 implementation subagents (`io`, `math`,
`coord+submodel`, `engine+output`) and the F1.e parity test harness.

**Status**: this is the **single source of truth** for the C++ ABM
engine's data contracts and module signatures. The headers under
`mal-abm-fast/include/mal_abm_fast/*.hpp` are the C++ binding; this
document is the narrative the subagents read first.

## 1. Purpose

`mal-abm-fast` is a fast, deterministic re-implementation of the
M1.5 thin-slice ABM in C++20, designed to run on a single CESGA FT3
ilk compute node. The engine is **black-box equivalent** to the
reference Python ABM in `mal_ghana_sim.abm`:

* given the **same** (env NetCDF, habitat gpkg, seed, start_date, days)
  inputs, the C++ engine produces the **same** 2-band state COG
  + sidecar JSON bytes as the Python engine.
* the per-day formulas, constants, and PRNG stream are pinned to
  match `mal_ghana_sim.abm.coordinator.CoordinatorModel` and
  `mal_ghana_sim.abm.mosquito_submodel.MosquitoSubmodel` exactly.

This is the F1.b contract. F1.e writes the parity test (Python
reference, C++ candidate, byte-compare the COGs and sidecars).

## 2. External contract

### CLI

```
mal_abm_fast run \
    --aoi ghana | --bbox W,S,E,N \
    --year 2024 --month 6 --seed 1 --days 30 \
    --env    data/runs/ghana/ghana_regional_2024_06_env.nc \
    --habitat data/runs/ghana/ghana_regional_2024_06_habitat_patches.gpkg \
    --output data/runs/ghana/ghana_regional_2024_06_seed0001.tif
```

F1.c adds `--n-rollouts N` (default 1). With `N > 1`, the engine
is rebuilt N times in the same process — each iteration gets a
fresh `Prng` instance seeded at `seed_rollout = --seed + i` — and
each rollout writes to its own `<stem>_seed{NNNN}.tif` + sidecar
JSON, where NNNN is the 0-indexed rollout id zero-padded to 4
digits. The legacy single-rollout invocation (no `--n-rollouts`
flag) is byte-compatible: the output is written verbatim to
`--output` (e.g. `state.tif`), and the v2.0 sidecar carries
`n_rollouts=1` and `rollout_index=0` so downstream consumers can
detect the new fields.

```
# F1.c: 3 rollouts, base --seed=1, runs rollouts 1, 2, 3
mal_abm_fast run --n-rollouts 3 \
    --aoi ghana --year 2024 --month 6 --seed 1 --days 30 \
    --env    data/runs/ghana/ghana_regional_2024_06_env.nc \
    --habitat data/runs/ghana/ghana_regional_2024_06_habitat_patches.gpkg \
    --output /tmp/rollout/state.tif
# -> /tmp/rollout/state_seed0000.tif  (Prng seed = 1, rollout_index=0)
#    /tmp/rollout/state_seed0000.json
#    /tmp/rollout/state_seed0001.tif  (Prng seed = 2, rollout_index=1)
#    /tmp/rollout/state_seed0001.json
#    /tmp/rollout/state_seed0002.tif  (Prng seed = 3, rollout_index=2)
#    /tmp/rollout/state_seed0002.json
```

* The CLI is implemented in `mal-abm-fast/src/main.cpp` (F1.d). The
  flag surface mirrors `mal_ghana_sim.abm.run`.
* `--aoi` resolves to a registered slug (e.g. `ghana`) and yields the
  default bbox. `--bbox W,S,E,N` overrides. The two are mutually
  exclusive.
* `--crs` defaults to `EPSG:4326`. `--resolution-m` to 1000.
  `--scale` to `regional`.
* `--n-rollouts` is validated with `CLI::PositiveNumber` (must be
  `>= 1`). The default is 1. F2 will OpenMP-parallel the per-rollout
  loop; F1.c is sequential.

### Inputs

* **Env NetCDF** (`--env`): a NetCDF4 file with CF-1.8 metadata. Dimensions and variables:

  | Variable           | Dims        | dtype    | Units    | Notes                        |
  |--------------------|-------------|----------|----------|------------------------------|
  | `rainfall`         | (time,y,x)  | float32  | mm/day   | CHIRPS daily precipitation   |
  | `water_temp_c`     | (time,y,x)  | float32  | °C       | ERA5-Land 2m temperature     |
  | `water_frac`       | (time,y,x)  | float32  | [0,1]    | JRC GSW (broadcast per day)  |
  | `ndvi`             | (time,y,x)  | float32  | [0,1]    | MODIS NDVI (broadcast)       |
  | `twi` (optional)   | (y,x)       | float32  | —        | Static TWI grid              |

  **Time dimension**: `time` is in "days since YYYY-MM-01" with `calendar = "noleap"`.
  One index per day of the month (28–31). The climate engine reads the current day's
  slice via `set_day(day_index)`.

  **Temperature**: stored in **°C directly** (not temp_suitability). The Mordecai inverse
  is NOT applied on read — the engine receives deg C and computes EIP as `max(0, T - 16)`.

  **Contract version**: `2.0` (breaking change from v1.0 COG format).

* **Habitat patches gpkg** (`--habitat`): a single-layer OGR
  datasource with one Point feature per patch. M1.5 honours
  `hab_type = 'pluvial_pool'` only. Columns read:

  | Column        | dtype   | Default | Notes                             |
  |---------------|---------|---------|-----------------------------------|
  | `hab_type`    | string  | —       | filter to 'pluvial_pool'          |
  | `K`           | int32   | 1000    | carrying capacity                 |
  | `twi`         | float   | 0.0     | static TWI value                  |
  | `row`         | int32   | derived | pre-computed cell index (F1.3b)   |
  | `col`         | int32   | derived | pre-computed cell index (F1.3b)   |
  | geometry      | Point   | —       | EPSG:4326 lon/lat                 |

### Outputs

* **2-band state COG** (`--output`): tiled, deflate, 128x128 blocks,
  `nodata = -9999` (NODATA_SENTINEL). Band 1 = density
  (mosquitoes / K_MAX ∈ [0, 1]); band 2 = suitability (per-cell adult
  density / K_MAX ∈ [0, 1]).

* **Sidecar JSON** (`<output>.json`): the F1.e parity test's primary
  input. Keys (in this order):

  | Key                 | Value                                          |
  |---------------------|------------------------------------------------|
  | `crs`               | e.g. `"EPSG:4326"`                             |
  | `transform`         | GDAL affine 6-tuple (list of 6 floats)         |
  | `aoi_slug`          | e.g. `"ghana"`                                 |
  | `scale`             | `"regional"` / `"national"` / `"continental"`  |
  | `year`              | int                                            |
  | `month`             | int                                            |
  | `seed`              | int (`--seed + rollout_index` for multi-rollout) |
  | `n_rollouts`        | int (F1.c, default 1)                          |
  | `rollout_index`     | int (F1.c, 0-indexed, default 0)               |
  | `generator_version` | pinned `"m1.5-mesa-frames+polars"`             |
  | `abm_params_hash`   | `"sha256:..."` (or `"sha256:pending"` in F1.b) |
  | `contract_version`  | pinned `"2.0"` (breaking change from v1.x COG)   |
  | `band_names`        | `["density", "suitability"]`                   |
  | `nodata`            | `-9999.0`                                      |
  | `shape`             | `[2, H, W]`                                    |
  | `k_max`             | `1000`                                         |

### Constants (pinned by `wire.hpp`)

| Symbol                          | Value  | Used in                                  |
|---------------------------------|--------|------------------------------------------|
| `K_MAX`                         | 1000   | carrying capacity, density normalisation |
| `K_PER_PATCH_DEFAULT`           | 1000   | submodel seeding                         |
| `INIT_FRAC`                     | 0.30   | submodel seeding (30% of K)              |
| `EIP_BASE_C`                    | 16.0   | EIP growing-degree-day base              |
| `EIP_THRESHOLD_GD`              | 110.0  | EIP infective threshold                  |
| `ADULT_DISPERSE_PROB`           | 0.20   | adult dispersal probability              |
| `ADULT_DISPERSE_SIGMA_M`        | 1000.0 | dispersal kernel sigma (m)               |
| `ADULT_DISPERSE_MAX_M`          | 2000.0 | dispersal cap (m)                        |
| `BIRTH_RATE`                    | 0.005  | binomial per active patch                |
| `PLUVIAL_POOL_RAIN_THRESHOLD_MM`| 15.0   | dynamic patch rule (rain)                |
| `PLUVIAL_POOL_TWI_THRESHOLD`    | 8.0    | dynamic patch rule (TWI)                 |
| `PLUVIAL_POOL_WATER_FRAC_MIN`   | 0.0    | dynamic patch rule (water; strictly > 0) |
| `NODATA_SENTINEL`               | -9999.0| state COG nodata                         |
| `CONTRACT_VERSION`              | "2.0"  | sidecar (breaking change from v1.x COG)         |
| `GENERATOR_VERSION`             | "m1.5-mesa-frames+polars" | sidecar                  |

## 3. Module map

```
                          main.cpp
                          (CLI11)
                              |
                              v
              +-------------------------------+
              |      CoordinatorModel         |
              |   (AOI, current_date,         |
              |    ClimateEngine,             |
              |    HabitatEngine, Prng,       |
              |    dynamic-patch registry)    |
              +-------+-------+-------+-------+
                      |       |       |
                      v       v       v
              +-------+   +---+---+   +----------------+
              |       |   |       |   |                |
       ClimateEngine  |  Habitat- |   |  MosquitoSubmodel
       (env NetCDF    |  Engine   |   |  (SoA, PRNG,
        reader +      |  (gpkg    |   |   5 per-day ops)
        set_day())    |  reader)  |   |                |
              |       |   |       |   |                |
              v       v   v       v   v                |
              +-------+---+-------+---+----------------+
                              |
                              v
              +-------------------------------+
              |  output_contract.{hpp,cpp}   |
              |  write_state_cog (GDAL)      |
              |  write_state_sidecar (json)  |
              +-------------------------------+
```

The `CoordinatorModel` is the **only** owner of the AOI / climate /
habitat / Prng state. The `MosquitoSubmodel` is the **only** owner
of the mosquito population (`MosquitoSoA`). They communicate via a
per-day `std::vector<PatchState>` (coordinator → submodel) and the
two query methods (`density_by_patch`, `adult_density_by_cell`)
that the coordinator uses to build the (H, W) state COG bands.

## 4. Per-day contract

The 5 ops run in this exact order. Formulas and constants match
`mal_ghana_sim.abm.mosquito_submodel.MosquitoSubmodel.advance_day`.

```
submodel.advance_day(aoi, patch_states):
    1. larva_mortality_inactive(patch_states)
    2. larva_growth(patch_states)
    3. larva_to_adult()
    4. adult_dispersal()
    5. birth(aoi, patch_states)
```

| Step | Formula | Constants                                  |
|------|---------|--------------------------------------------|
| 1    | drop larvae where `patch.activated == false` | —                              |
| 2    | `stage_age += 1`; `eip_progress += max(0, T - EIP_BASE_C)` | `EIP_BASE_C = 16`               |
| 3    | `stage = adult` if `eip_progress >= EIP_THRESHOLD_GD` | `EIP_THRESHOLD_GD = 110`        |
| 4    | 20% of adults move: `(dx, dy) ~ N(0, sigma_m^2)`, clip to `max_m`, convert to (dlon, dlat) | `sigma_m = 1000`, `max_m = 2000` |
| 5    | `binomial(K, BIRTH_RATE)` new larvae per active patch; `lon/lat = patch cell centre` | `BIRTH_RATE = 0.005`            |

`accumulate_eip` is NaN-safe: when `daily_mean_temp_c` is NaN (e.g.
the env NetCDF's nodata pixel), the
function returns `eip_progress` unchanged. The C++ header is:

```cpp
inline float accumulate_eip(float eip_progress, float daily_mean_temp_c) {
    if (std::isnan(daily_mean_temp_c)) return eip_progress;
    const float gd = std::max(0.0f, daily_mean_temp_c - EIP_BASE_C);
    return eip_progress + gd;
}
```

The F1.a smoke test (`tests/test_smoke.cpp::EipAccumulate`) pins
the below-base, above-base, and NaN cases.

## 4.1 F1.c indexing (perf)

The 5 per-day ops in `mosquito_submodel.cpp` use
**contiguous, dense-indexed `std::vector` lookups keyed by `patch_id`**
(or `(row * w + col)` for the per-cell queries) instead of
`std::unordered_map` / `std::unordered_set`. Patches are assigned
dense, monotonically-increasing pids by `coordinator.cpp`
(pre-existing 0..N-1, then `next_dynamic_patch_id_++` for dynamic
cells), so a per-call `std::vector<uint8_t>`/`std::vector<float>` of
size `max_pid + 1` is bounded, cache-friendly, and replaces the
hash-lookup in the inner loops. This matches the SoA pattern and
removes the hash overhead from the hot per-agent loops.

## 5. Spatial model

### AOI

The `AOI` struct lives in `wire.hpp`. The `cells_per_side()` method
returns the number of cells along the east-west axis (W). The
implementation is in `aoi.hpp`:

```cpp
inline int32_t AOI::cells_per_side() const noexcept {
    const double centroid_lat_rad = ((north + south) * 0.5) * (M_PI / 180.0);
    const double width_m = (east - west) * 111320.0 * std::cos(centroid_lat_rad);
    int32_t cells = static_cast<int32_t>(std::lround(width_m / static_cast<double>(resolution_m)));
    if (cells < 1) cells = 1;
    return cells;
}
```

The H (north-south) is `cells_per_side_h(aoi)` (also in
`aoi.hpp`): no `cos(lat)` factor, same formula. The C++ code uses
H and W for the (H, W) state COG band shapes.

### Grid transform

`GDAL`-compatible affine 6-tuple is built from the AOI bbox:

```cpp
transform = from_bounds(west, south, east, north, W, H);
```

(Where `from_bounds` is `rasterio.transform.from_bounds` in Python,
and the C++ engine uses `GDALGetGeoTransform` after the COG write.)

### rowcol / xy

`rasterio.transform.rowcol(transform, lon, lat)` snaps a (lon, lat)
point to the (row, col) cell. The C++ engine does the same
calculation manually (it's a 2-line formula) for the
`adult_density_by_cell` query:

```cpp
const double centroid_lat_rad = (aoi.north + aoi.south) * 0.5 * M_PI / 180.0;
const double m_per_deg_lon = 111320.0 * std::cos(centroid_lat_rad);
const double m_per_deg_lat = 111320.0;
const double x_m = (lon - aoi.west) * m_per_deg_lon;
const double y_m = (aoi.north - lat) * m_per_deg_lat;  // y inverted
const int32_t col = static_cast<int32_t>(std::lround(x_m / aoi.resolution_m));
const int32_t row = static_cast<int32_t>(std::lround(y_m / aoi.resolution_m));
```

The result is clamped to `[0, H-1] x [0, W-1]`. Out-of-bounds
(lon outside the AOI) snaps to the nearest cell on the boundary.

## 6. Determinism

The engine uses **xoshiro256\*\*** (Vigna's reference
implementation, public domain) as the canonical PRNG. The
`Prng` class wraps a 4-word state and exposes `uniform_double`,
`normal`, `binomial`, and `peek_state` (test helper).

The CLI seeds the per-rollout `Prng` with `--seed + i` (where
`i` is the 0-indexed rollout id). The `Engine` constructor
takes this `Prng&`, derives two independent sub-stream seeds
(coord + submodel) via `peek_state()` (with one
`uniform_double()` advance in between), and constructs the
`CoordinatorModel` and `MosquitoSubmodel` with the derived
seeds. The master Prng is **not** cached as an Engine member —
each rollout rebuilds the Engine from a fresh `Prng` instance,
so no Prng state leaks across rollouts.

Two runs with the same `(seed, i, days, AOI, env, habitat)`
inputs produce **byte-equal** state COG bytes (within float32
precision; the F1.e parity test allows 1e-5 relative error per
pixel). Two rollouts with different seeds (different `i`) in
the same process produce **byte-different** state COGs — this
is the F1.c determinism property that `--n-rollouts N` relies
on, validated by `tests/test_state_cog.cpp::TwoRolloutsDifferentSeedsProduceDifferentCogs`
and `tests/test_engine.cpp::TwoRolloutsWithDifferentSeedsProduceDifferentCogs`.

Per-day climate lookups from the NetCDF file are deterministic:
the same `(env_nc_path, day_index)` pair always yields the same
`(rainfall, water_temp_c, water_frac, ndvi)` slice. The NetCDF
reader is stateless between calls — `set_day(day_index)` selects
the slice; no interpolation or caching mutates the result.

`peek_state()` returns the raw `s[0]` state word. The F1.e parity
test uses it to assert the stream is reproducible at the
xoshiro256** level — if `peek_state()` ever differs from a saved
reference, the F1.e test fails fast.

The F1.c `Prng` class holds its 4-word state inline (`s_[0..3]`) on
the class — the previous file-scope `unordered_map<const void*, ...>`
workaround is gone. `Prng::binomial` uses the **BTPE** algorithm
(Kachitvichyanukul & Schmeiser, 1988, "Binomial Random Variate
Generation") for `n*p >= 30` (truncated-normal outer draw + Knuth
Poisson inner + squeeze) and **BINV** (inverse-CDF) for `n*p < 30`.
Both are O(1) per draw regardless of `n`, replacing the previous
O(n) sum-of-Bernoulli loop and the coarse normal approximation.

## 7. Wave 1 stub tests (F1.a)

`tests/test_smoke.cpp` pins three properties the F1.b+ subagents
must preserve:

| Test               | Assertion                                                  |
|--------------------|------------------------------------------------------------|
| `VersionConstant`  | `EIP_BASE_C == 16.0`, `EIP_THRESHOLD_GD == 110.0`           |
| `PrngStub`         | `xoshiro256pp::next() == 0u` (F1.a stub; F1.c replaces)    |
| `EipAccumulate`    | `accumulate_eip` is NaN-safe, returns GDD above base       |

These three tests must keep passing through F1.c, F1.d, and F1.e.
F1.c's real xoshiro256** replaces the `PrngStub` with a non-zero
return — the test is then updated to check a non-zero, deterministic
value (see F1.c plan).

## 8. Out of scope for F1.b–F1.f

* **Daily CHIRPS interpolation** — now implemented. The NetCDF env
  file contains daily `rainfall` slices (CHIRPS mm/day), eliminating
  the need for separate interpolation.
* **pybind11 binding** (F4). The C++ engine is wrapped in a
  Python module so `mal_ghana_sim.abm` can call into it.
* **MPI** (F4). Multi-node parallel ABM rollouts. The F1 thin
  slice is single-node; MPI lands in F4.
* **SYCL / CUDA** (F5). GPU offload of the 5 per-day ops. F1.b
  ships CPU-only; F5 is the GPU port.
* **M7+ biology**. M2+ extensions: temperature-modulated
  pupation, gonotrophic cycles, multi-cohort dynamics. F1.b
  is the M1.5 thin slice only.
* **Multi-species**. M1.5 has *An. gambiae* s.s. only. Multi-
  species lands in M8.
* **Weekly cadence**. F1.b is daily. Weekly/monthly land in M7.

## 9. Layout

```
mal-abm-fast/
├── CMakeLists.txt                  # root CMake (unchanged)
├── cmake/CompilerWarnings.cmake   # warnings library (ALIAS fix in F1.b)
├── docs/
│   ├── perf-cpp-abm-f1a-checklist.md  (F1.a checklist)
│   └── wire-spec.md                # this file
├── include/mal_abm_fast/
│   ├── wire.hpp                    # canonical types + constants
│   ├── aoi.hpp                     # AOI::cells_per_side() inline impl
│   ├── prng.hpp                    # Prng class + xoshiro256pp shim
│   ├── eip.hpp                     # inline accumulate_eip / is_infective
│   ├── dispersal.hpp               # DispOffset + offset_m
│   ├── climate.hpp                 # ClimateEngine class
│   ├── env_reader.hpp              # EnvReader: read_env_nc() for NetCDF4 env
│   ├── habitat_engine.hpp          # HabitatEngine class
│   ├── coordinator.hpp             # CoordinatorModel class
│   ├── mosquito_state.hpp          # MosquitoSoA struct
│   ├── mosquito_submodel.hpp       # MosquitoSubmodel class
│   └── output_contract.hpp         # StateCogMetadata + writers
├── src/
│   ├── CMakeLists.txt              # builds the static lib + main
│   ├── eip.cpp                     # empty (header-only)
│   ├── prng.cpp                    # xoshiro256pp + Prng stubs (F1.c replaces)
│   ├── dispersal.cpp               # offset_m stub (F1.c replaces)
│   ├── climate.cpp                 # ClimateEngine stubs (F1.b replaces)
│   ├── env_reader.cpp              # NetCDF4 env reader (read_env_nc, set_day)
│   ├── habitat_engine.cpp          # HabitatEngine stubs (F1.b replaces)
│   ├── coordinator.cpp             # CoordinatorModel stubs (F1.b/c replaces)
│   ├── mosquito_state.cpp          # empty (no logic in the header struct)
│   ├── mosquito_submodel.cpp       # MosquitoSubmodel stubs (F1.c replaces)
│   ├── output_contract.cpp         # writer stubs (F1.d replaces)
│   └── main.cpp                    # CLI (F1.d adds `run` subcommand)
└── tests/
    ├── CMakeLists.txt              # unchanged
    └── test_smoke.cpp              # unchanged
```

## 10. Cross-references

* `mal_ghana_sim.abm.run` (Python CLI) — the ground truth for
  flag names, defaults, and the env NetCDF variable naming convention.
* `mal_ghana_sim.abm.coordinator.CoordinatorModel` — the Python
  counterpart of `mal_abm_fast::CoordinatorModel`.
* `mal_ghana_sim.abm.mosquito_submodel.MosquitoSubmodel` — the
  Python counterpart of `mal_abm_fast::MosquitoSubmodel`. The
  per-day op order and formulas are identical.
* `mal_commonlib.aoi.AOI` — the Python counterpart of
  `mal_abm_fast::AOI`. The `cells_per_side` formula matches.
* `papers/spatial-analysis/MalariaEliminationWithSpatialDecisionSupportSystems.md`
  — the SDSS framework this engine is a building block of.
* `mal-abm-fast/docs/perf-cpp-abm-f1a-checklist.md` — the F1.a
  scaffold checklist (prerequisite for F1.b).
