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
| Component | `mal-core/src/mal_core/abm/` (Python) + `mal-core/src/mal_core/abm/` (C++/CMake/vcpkg) |
| Version | `v1.0` (output contract) |
| Status | `stable` |
| Owner | David Flórez-Mazuera |
| Last drift check | `2026-07-30` |

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

- C++ ABM engine (`mal-abm-fast/`) and the Mesa-Geo adapter for the thin slice.
- ABM runner (`runner.py`), flag schema (`flags.py`), and the Python wrapper around the binary (`wrapper.py`).
- **Output contract** (§5–§7 below): state tensor, env tensor, file naming, sidecar, NoData, tile rules, `K_max`, `H/W`.
- Calibration scorers and the calibration test framework (`abm/tests/calibration/`).

## 3. Out of scope

- Manifest schema → `docs/specs/data/spec.md`.
- Download → `docs/specs/download/spec.md`.
- Ingest (env tensor builder) → `docs/specs/ingest/spec.md` (the ABM reads what ingest writes; this spec pins what the ABM **emits**, ingest pins what it builds).
- U-Net training and inference → `docs/specs/training/spec.md`, `docs/specs/prediction/spec.md`.
- The fitness composite → `docs/specs/scoring/spec.md`.

## 4. Public API

| Symbol | Where | Notes |
|---|---|---|
| `abm.run(...)` | `mal_core.abm.runner` | Runs the C++ binary for one `(aoi, scale, year, month, seed)` and writes state rasters + sidecars. |
| `ABM_FLAGS_SCHEMA`, `AbmFlags` | `mal_core.abm.flags` | Pydantic schema for ABM CLI flags. New flags bump MINOR. |
| `arch-abm-output-contract` constants | `mal_core.abm` (module) | Channel names, dtypes, NoData sentinel, `K_max`, `H/W`. |
| Calibration scorers | `mal_core.abm.tests.calibration.scorers.D<id>_<name>` | Each scorer is a `D<id>_<name>.py` module exporting `score(rollout) -> dict`. Adding a scorer is non-breaking. |
| `run_calibration_from_manifest(...)` | `mal_core.scoring.runner` (called by pipeline) | Cross-spec: ABM owns the rollout files consumed. |

## 5. Invariants — Output contract (frozen at v1.0)

### §5.1 State tensor

- **INV-1.** Shape `(C=2, T, H, W)`; `dtype = float32`. Channel 0 = `density`, channel 1 = `suitability`.
- **INV-2.** `density` is written normalized as `density / K_max`, `K_max = 1000` (default; overridable via sidecar `k_max`).
- **INV-3.** `suitability` semantics per version: `v1` binary active-patch map; `v2` per-cell adult density (`n_adults / K_max`); `v2.1` adult density computed from each adult's current `(lon, lat)` snapped via `rasterio.transform.rowcol`. The U-Net reader reads by **band name**, not by index.
- **INV-4.** NoData rasters `-9999.0`, masks `255`. **Any other sentinel is a P0 bug.**
- **INV-5.** State file naming: `{aoi_slug}_{scale}_{year}_{month:02d}_seed{seed:04d}.tif` (+ optional `_r{row:04d}_c{col:04d}` suffix when tiled; see §5.5).

### §5.2 Env tensor

- **INV-6.** Shape `(C_env=4, H, W)`; `dtype = float32`. Channels: `water_frac ∈ [0,1]`, `rainfall` raw mm, `temp_suitability ∈ [0,1]`, `ndvi ∈ [0,1]`.
- **INV-7.** Env file naming: `{aoi_slug}_{scale}_{year}_{month:02d}_env.tif` — no seed (deterministic per month).

### §5.3 Sidecar JSON

- **INV-8.** Every `.tif` ships a same-basename `.json` sidecar with required keys: `crs`, `transform`, `aoi_slug`, `scale`, `year`, `month`, `seed` (state only), `generator_version`, `abm_params_hash`.
- **INV-9.** Optional keys: `rainfall_cap_mm` (env), `k_max` (state), `contract_version` (string `"1.0"`). Unknown keys must be ignored by readers.
- **INV-10.** Sidecar `transform` is the affine 6-tuple `[a, b, c, d, e, f]` in `rasterio`-row-major order: `(a, b)` = pixel size, `(c, f)` = upper-left corner.

### §5.4 CRS and band descriptions

- **INV-11.** CRS ∈ `EPSG:4326` or UTM (`EPSG:326xx` / `EPSG:327xx`). The writer **must** auto-reproject; silent mis-CRS is forbidden.
- **INV-12.** Band descriptions set via `rasterio.set_band_description`: state `[density, suitability]`, env `[water_frac, rainfall, temp_suitability, ndvi]`.

### §5.5 Tile rules

- **INV-13.** U-Net input patch is `H = W = 128`. AOI < `128×128` → zero-pad to the right/bottom with NoData (real NoData, not zeros). AOI > `128×128` → tile into `128×128` non-overlapping patches, origin at AOI's upper-left.
- **INV-14.** Tile suffix `_r{row:04d}_c{col:04d}` matches a shared `tile_index.json` in the run directory. The full env tensor re-tiles with the same `(row, col)` indices as state tiles.

### §5.6 Versioning

- **INV-15.** The contract is pinned at `v1.0`. Changes to shape, dtype, channel order, naming, NoData, `K_max`, `H/W` bump MAJOR. Additive changes (new optional sidecar key, new env channel) bump MINOR.
- **INV-16.** Readers read by **band name**, not by index. Readers **must** refuse a sidecar whose `contract_version` major > `MAX_SUPPORTED_CONTRACT_VERSION`. Silent fallback is forbidden.

## 6. Data contracts

- Output: GeoTIFF + sidecar JSON (rules pinned in §5).
- Input: env tensor file + mobility + host layers, all produced by `ingest`. The ABM does not validate the manifest — that's the pipeline's job (`pipeline/spec.md` §5 INV-3).

## 7. Migration & deprecation

- Bumping the output contract to `v2.0` requires:
  1. New spec version here.
  2. A reader feature flag (`MAX_SUPPORTED_CONTRACT_VERSION`) bumped in `training` and `prediction` specs.
  3. A migration script for old rasters (or an explicit decision to drop them).
- Deprecation policy: 1 MINOR version carries the deprecation warning; removed in the next MAJOR.

## 8. Drift check

```bash
# INV-1, INV-4: dtype + NoData on a fresh rollout
uv run pytest mal-core/tests/test_abm_output_contract.py -v

# INV-5, INV-7: file naming
uv run python -c "
from pathlib import Path
import re
state = re.compile(r'^[a-z0-9-]+_[a-z0-9-]+_\d{4}_\d{2}_seed\d{4}(_r\d{4}_c\d{4})?\.tif$')
env   = re.compile(r'^[a-z0-9-]+_[a-z0-9-]+_\d{4}_\d{2}_env\.tif$')
# walk runs/ and verify each .tif matches state|env
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
    assert sidecar.get('contract_version','1.0').startswith('1.'), f'unexpected major: {p}'
"
```

## 9. Examples

Writer (M1.4, illustrative):

```python
import numpy as np, rasterio
from rasterio.transform import Affine
from mal_core.abm import write_state_tick, K_MAX, H_W

def write_month(aoi_slug, scale, year, month, seed, density, suitability, transform):
    assert density.shape == (H_W, H_W) and suitability.shape == (H_W, H_W)
    arr = np.stack([density / K_MAX, suitability], axis=0).astype(np.float32)
    path = f"runs/{aoi_slug}_{scale}_{year}_{month:02d}_seed{seed:04d}.tif"
    write_state_tick(path, arr, transform, crs="EPSG:4326", nodata=-9999.0)
    return path
```

Reader (training, reads by band name):

```python
import rasterio
def read_state_by_name(path):
    with rasterio.open(path) as src:
        names = src.descriptions
        density      = src.read(names.index("density") + 1)
        suitability  = src.read(names.index("suitability") + 1)
    return density, suitability
```

## 10. References

- KG ADR: `adr-spec-design-2026-07-30` (template).
- Specs (by folder): `data`, `commonlib`, `training`, `prediction`, `scoring`, `ingest`, `pipeline`.
- External: Mesa-Geo docs (geospatial agent framework); Beven & Kirkby (1979) for TWI (cited from `commonlib`).