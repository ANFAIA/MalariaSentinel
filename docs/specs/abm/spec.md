# abm Spec

> Owns the agent-based model: C++ engine (`mal-abm-fast/`), Mesa-Geo
> adapter, runner, flags, and the **frozen output contract** that the
> U-Net reader and the calibration scorers consume.

---

```yaml
# Machine-readable affects block — parsed by the drift-check agent.
# Bidirectional: if A affects B, B must declare affected_by A.
# `target` is the folder name under docs/specs/ (stable across KG migrations).
affects:
  - target: training
    direction: downstream
    reason: training reads ABM rollouts via the output contract; shape/dtype/naming pinned here
    severity: breaking
  - target: prediction
    direction: downstream
    reason: prediction runs the trained U-Net on env tensors shaped by ABM output contract
    severity: breaking
  - target: scoring
    direction: downstream
    reason: scoring runs scorers against ABM rollouts; channel semantics pinned here
    severity: breaking
  - target: data
    direction: downstream
    reason: state/env file naming, sidecar schema, and NoData sentinel come from this spec
    severity: breaking
  - target: commonlib
    direction: upstream
    reason: AOI.cells_per_side() pins the (H, W) for state/env rasters
    severity: breaking
# Cross-references to the knowledge graph (names only, no UUIDs — survives KG migrations).
kg_refs:
  adrs: [adr-spec-design-2026-07-30]
  patterns: []
  pitfalls: []
  tools: []
```

## Metadata

| Field | Value |
|---|---|
| Component | `mal-core/src/mal_core/abm/` (Python) + C++ engine (`wire.hpp`, CMake) |
| Version | `v2.0` (output contract); `v1.0` (scorer suite) |
| Status | `stable` |
| Owner | David Flórez-Mazuera |
| Last drift check | `2026-08-05` |

## 1. Objective

The ABM is the **ground-truth simulator** of mosquito dynamics inside
the Centinela. It advances an environmental grid day-by-day (larval
cycle, dispersal, mortality, EIP) and emits per-tick state tensors
that the U-Net surrogate learns from and that calibration scorers
grade.

Without the ABM there is no truth to fit, no calibration target, and
no rollout history to train on. The output contract that this spec
pins is the load-bearing wall: every downstream spec (`training`,
`prediction`, `scoring`) is bound by what the ABM writes.

## 2. In scope

- C++ ABM engine (`wire.hpp`, CMake build) and the Mesa-Geo adapter for the thin slice.
- ABM runner (`runner.py`), the Python wrapper around the binary (`wrapper.py`), and the compile entry (`compile.py`, `malariasim abm --compile`).
- **Output contract** (§5–§7 below): state tensor, env tensor, file naming, sidecar, NoData, tile rules, `H/W`. (The v4.0 `K_max` retirement is documented in INV-2/INV-9.)
- Native in-process GIF renderer (`include/mal_abm_fast/viz.hpp`, `src/viz.cpp`): optional per-run animation, `--gif` on the engine CLI and on `malariasim abm`.
- Pipeline position: stage 3 (after ingest). Reads manifest for env/habitat/hosts paths.

## 3. Out of scope

- Manifest schema → `docs/specs/data/spec.md`.
- Download → `docs/specs/download/spec.md`.
- Ingest (env tensor builder) → `docs/specs/ingest/spec.md` (the ABM reads what ingest writes; this spec pins what the ABM **emits**, ingest pins what it builds).
- U-Net training and inference → `docs/specs/training/spec.md`, `docs/specs/prediction/spec.md`.
- The fitness composite → `docs/specs/scoring/spec.md`.

## 4. Public API

| Symbol | Where | Notes |
|---|---|---|
| `run_abm(...)` | `mal_core.abm.runner` | Runs the C++ binary for one `(aoi, year, month, seed)` and writes state rasters + sidecars. |
| `CppAbmWrapper` | `mal_core.abm.wrapper` | Thin Python wrapper around the compiled C++ binary. Resolves binary path, introspects flags, runs `subprocess`. |
| `run_abm_from_manifest(...)` | `mal_core.abm.wrapper` | Reads manifest, validates completeness, resolves data paths, calls `CppAbmWrapper`. |
| CLI subcommands | `mal_core.cli` | Typer CLI (`malariasim`): `abm` (compile/execute ABM), `score` (score a run dir), plus download/ingest/train/predict stages. |

## 5. Invariants — Output contract (frozen at v2.0)

### §5.1 State tensor

- **INV-1.** Shape `(C=2, T, H, W)`; `dtype = float32`. Channel 0 = `density`, channel 1 = `suitability`.
- **INV-2.** Contract **v4.0** (2026-10-20, plan `03-retirada-k-max`): both state bands are **raw per-cell adult counts** (individuals). The v≤3 normalization `density / K_max` (`K_max=1000`) and the sidecar `k_max` key are retired — no operational `K_MAX` constant exists anymore.
- **INV-3.** `suitability` semantics per version: `v1` binary active-patch map; `v2` per-cell adult density (`n_adults / K_max`); `v2.1` adult density computed from each adult's current `(lon, lat)` snapped via `rasterio.transform.rowcol`; **v4.0** raw per-cell adult counts at each adult's current `(lon, lat)` (all adults, any sex/state). The U-Net reader reads by **band name**, not by index.
- **INV-4.** NoData rasters `-9999.0`, masks `255`. **Any other sentinel is a P0 bug.**
- **INV-5.** State file naming: `{aoi_slug}_{scale}_{year}_{month:02d}_seed{seed:04d}.tif` (+ optional `_r{row:04d}_c{col:04d}` suffix when tiled; see §5.5).

### §5.2 Env tensor

- **INV-6 (v3.0).** Env input is a CF-1.8 daily NetCDF (`.nc`) — the only accepted format. Dims `(time, y, x)`, daily vars `rainfall` (mm/day), `air_temp_c` (°C) + 2-D statics `jrc_persistent, lc_built, lc_wetland, lc_open_plus_water, lc_crop` ∈ [0,1], `_FillValue = -9999.0`. The legacy monthly COG GeoTIFF reader (`read_env_tif`/`load_from_env_tif`) was removed on 2026-09-27. The v2 pool model (`water_frac`/`ndvi`/`water_temp_c` daily bands, `pluvial_pool` rule, per-patch capacity multiplier) was retired with contract v3.0 (2026-10-17) — habitat comes from the habitat gpkg + static planes, not from env channels. A non-`.nc` env path raises a hard error.
- **INV-7.** Env file naming: NC `{aoi}_{product}_{year_start}_{year_end}_env.nc` (multi-year daily) or `{aoi}_{scale}_{year}_{month:02d}_env.nc` (single-month daily). No seed (deterministic per month).

### §5.3 Sidecar JSON

- **INV-8.** Every `.tif` ships a same-basename `.json` sidecar with required keys: `crs`, `transform`, `aoi_slug`, `scale`, `year`, `month`, `seed` (state only), `generator_version`, `abm_params_hash`.
- **INV-9.** Optional keys: `rainfall_cap_mm` (env TIF only), `contract_version` (state; `"4.0"` since v4). The retired `k_max` key was removed with contract v4.0 — readers must not depend on it. Unknown keys must be ignored by readers.
- **INV-10.** Sidecar `transform` is the affine 6-tuple `[a, b, c, d, e, f]` in `rasterio`-row-major order: `(a, b)` = pixel size, `(c, f)` = upper-left corner.

### §5.4 CRS and band descriptions

- **INV-11.** CRS ∈ `EPSG:4326` or UTM (`EPSG:326xx` / `EPSG:327xx`). The writer **must** auto-reproject; silent mis-CRS is forbidden.
- **INV-12.** Band descriptions: state COG bands set via `rasterio.set_band_description` or GDAL: `["adult_patch_count", "adult_cell_count"]` (C++ `STATE_BAND_NAMES` in `wire.hpp`; v4.0 — the retired names were `["adult_occupancy", "host_seeking_pressure"]`). **Legacy alias**: `["density", "suitability"]` used in older Python code and some docs — historically the same two bands. Env NC: variable names `rainfall, air_temp_c` + statics `jrc_persistent, lc_built, lc_wetland, lc_open_plus_water, lc_crop` (no band descriptions — NetCDF variables).

### §5.5 Tile rules

- **INV-13.** U-Net input patch is `H = W = 128`. AOI < `128×128` → zero-pad to the right/bottom with NoData (real NoData, not zeros). AOI > `128×128` → tile into `128×128` non-overlapping patches, origin at AOI's upper-left.
- **INV-14.** Tile suffix `_r{row:04d}_c{col:04d}` matches a shared `tile_index.json` in the run directory. The full env tensor re-tiles with the same `(row, col)` indices as state tiles.

### §5.6 Versioning

- **INV-15.** The contract is pinned at `v4.0` (C++ `CONTRACT_VERSION` in `wire.hpp`). Previous versions: `v1.0` (M1 thin slice), `v1.1` (F1.c `n_rollouts`/`rollout_index`), `v2.0` (M7.1+M7.2), `v3.0` (proxy_habitat_v1 — env NC/habitat gpkg change, state COG unchanged), `v4.0` (2026-10-20, plan `03-retirada-k-max` — state bands become raw adult counts, sidecar `k_max` removed, band names renamed). Changes to shape, dtype, channel order, naming, NoData, units, `H/W` bump MAJOR. Additive changes (new optional sidecar key, new env channel) bump MINOR.
- **INV-16.** Readers read by **band name**, not by index. Readers **must** refuse a sidecar whose `contract_version` major > `MAX_SUPPORTED_CONTRACT_VERSION`. Silent fallback is forbidden.

## 6. Data contracts

- Output: GeoTIFF state COG + sidecar JSON per §5.1, §5.3, §5.4.
- Optional run artifacts (not part of the data contract, never consumed downstream): a native GIF rendered in-process by `--gif` (`--gif-every`, `--gif-fps`, `--gif-max-width`) from live engine state, and the cohort/transmission JSON logs. Per-day transmission COGs are **not** emitted by default: `--transmission-snapshot-every 0` now means final snapshot only (the retired `visualize_transmission.py` was their only consumer).
- Input env: CF-1.8 daily NetCDF (per §5.2 INV-6; the only accepted format — the legacy COG reader was removed on 2026-09-27). The C++ engine has one reader: `read_env_nc`. The habitat/availability model v3.0 reads the static planes + habitat gpkg feature list directly from this path.
- Input mobility + host layers: produced by `ingest`. `run_abm_from_manifest` validates manifest completeness and resolves paths; the pipeline-level `pipeline/spec.md` §5 INV-3 is the authoritative validation point for the full pipeline.

## 7. Migration & deprecation

- Bumping the output contract (e.g. the `v4.0` raw-counts change, 2026-10-20) requires:
  1. New spec version here.
  2. A reader feature flag (`MAX_SUPPORTED_CONTRACT_VERSION`) bumped in `training` and `prediction` specs.
  3. A migration script for old rasters (or an explicit decision to drop them).
  4. `CONTRACT_VERSION` bump in C++ `wire.hpp` + all readers agreeing (the state contract and the env-NC contract are versioned separately).
- Deprecation policy: 1 MINOR version carries the deprecation warning; removed in the next MAJOR.

## 8. Drift check

```bash
# INV-1, INV-4: dtype + NoData on a fresh rollout
uv run pytest mal-core/tests/test_abm_wrapper.py -v

# INV-5, INV-7: file naming
uv run python -c "
from pathlib import Path
import re
state = re.compile(r'^[a-z0-9-]+_[a-z0-9-]+_\d{4}_\d{2}_seed\d{4}(_r\d{4}_c\d{4})?\.tif$')
env_nc = re.compile(r'^[a-z0-9-]+_[a-z0-9-]+_\d{4}_\d{2}_env\.nc$')
# walk runs/ and verify each state .tif matches state pattern
# walk data/ and verify each env file matches the NC pattern
"

# INV-6: NC env has daily rainfall (not monthly aggregate)
uv run python -c "
import xarray as xr
from pathlib import Path
for p in Path('data/ghana').glob('*_env.nc'):
    ds = xr.open_dataset(p)
    assert 'rainfall' in ds.data_vars, f'{p}: missing rainfall'
    assert 'time' in ds.dims, f'{p}: missing time dim (not daily?)'
    assert ds.dims['time'] > 1, f'{p}: time dim is not daily (only {ds.dims["time"]} steps)'
"

# INV-8, INV-9: sidecar required keys
uv run python -c "
import json, sys
for path in Path('runs/').rglob('*.json'):
    sidecar = json.loads(path.read_text())
    for k in ('crs','transform','aoi_slug','scale','year','month','generator_version','abm_params_hash'):
        assert k in sidecar, f'missing {k} in {path}'
"

# INV-13: H/W is the only fixed shape; no code outside this spec hardcodes 128
rg "H\s*=\s*W\s*=\s*128|H\s*=\s*128\b|W\s*=\s*128\b" mal-core/src/mal_core/abm/ mal-core/src/mal_core/training/ mal-core/src/mal_core/prediction/

# INV-15/16: contract version stamp on the latest rollouts
uv run python -c "
import json
from pathlib import Path
for p in Path('runs/').rglob('*.json'):
    sidecar = json.loads(p.read_text())
    cv = sidecar.get('contract_version', '2.0')
    assert cv.startswith('2.'), f'unexpected major: {p} has contract_version={cv}'
"

# Canon scoring registry: 13 composite dims + 6 gates
uv run python -c "
from mal_core.scoring.registry import build_registry, COMPOSITE_WEIGHTS
r = build_registry()
dims = sorted(n for n, s in r.items() if s.kind == 'composite')
gates = sorted(n for n, s in r.items() if s.kind == 'gate')
print(f'{len(dims)} dims, {len(gates)} gates')
assert len(dims) == 13 and len(gates) == 6, (dims, gates)
assert set(dims) == set(COMPOSITE_WEIGHTS)
"
```

## 9. Examples

Writer (via C++ binary, typical pipeline path):

```python
from mal_core.abm import run_abm

result = run_abm(aoi="ghana", year=2024, month=6, seed=1, days=30)
# result = {"stdout": ..., "stderr": ..., "returncode": 0}
```

Writer (manifest-resolved):

```python
from mal_core.abm.wrapper import run_abm_from_manifest

result = run_abm_from_manifest(aoi="ghana", year=2024, month=6, seed=1, days=30)
# result = {"output_path": "runs/ghana/ghana_abm_seed0001.tif", ...}
```

Reader (training, reads by band name — uses C++ band names):

```python
import rasterio
def read_state_by_name(path):
    with rasterio.open(path) as src:
        names = src.descriptions
        # v4.0: both bands are raw per-cell adult counts (individuals).
        density      = src.read(names.index("adult_patch_count") + 1)  # band 1
        suitability  = src.read(names.index("adult_cell_count") + 1)   # band 2
    return density, suitability
```

Scoring a run directory:

```python
from mal_core.scoring import run_scoring
from pathlib import Path

scorecard = run_scoring(Path("runs/ghana/"))
print(f"Composite: {scorecard['composite']} ({scorecard['verdict']})")
```

## 10. References

- KG ADR: `adr-spec-design-2026-07-30` (template).
- Specs (by folder): `data`, `commonlib`, `training`, `prediction`, `scoring`, `ingest`, `pipeline`.
- External: Mesa-Geo docs (geospatial agent framework); Beven & Kirkby (1979) for TWI (cited from `commonlib`).