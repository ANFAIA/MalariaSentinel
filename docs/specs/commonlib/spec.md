# commonlib Spec

> Foundation layer. Owns AOI, paths, config, terrain (TWI), and reusable
> data utilities (host loaders, mobility). No domain logic, no ABM, no
> pipeline orchestration.

---

```yaml
# Machine-readable affects block — parsed by the drift-check agent.
# Bidirectional: if A affects B, B must declare affected_by A.
# `target` is the folder name under docs/specs/ (stable across KG migrations).
affects:
  - target: download
    direction: bidirectional
    reason: download uses AOI + paths from commonlib; commonlib consumes downloaded xr objects via data utils
    severity: breaking
  - target: ingest
    direction: downstream
    reason: ingest imports AOI, terrain (TWI), and data utils from commonlib
    severity: breaking
  - target: abm
    direction: downstream
    reason: ABM consumes AOI + paths; AOI.cells_per_side pins the (H, W) shape
    severity: breaking
  - target: training
    direction: downstream
    reason: training reads rollouts whose AOI shape comes from commonlib.AOI
    severity: breaking
  - target: prediction
    direction: downstream
    reason: prediction needs AOI + grid resolution to instantiate the U-Net input window
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
| Component | `mal-commonlib/src/mal_commonlib/` |
| Version | `v0.1.0` |
| Status | `stable` |
| Owner | David Flórez-Mazuera |
| Last drift check | `2026-07-30` |

## 1. Objective

`mal-commonlib` is the cross-pipeline substrate. It provides the
**AOI**, the repo-relative **paths**, the **TWI** terrain computation,
and the **data utilities** (host loaders, mobility helpers) that every
other spec assumes exist. Without it, the ABM, ingest, training, and
prediction layers would all reinvent bbox/CRS handling and the TWI
formula.

The package carries **no** domain logic — it does not know what
malaria is, does not call the ABM, does not own the manifest. It is
imported by everything else.

## 2. In scope

- `AOI` and `Scale` (region-agnostic, M1.2a). Frozen Pydantic model.
- TWI computation from a DEM (`compute_twi`, pure numpy/scipy).
- Repo path constants (`REPO_ROOT`, `DATA_DIR`, `PAPERS_DIR`, `TERRAIN_DIR`, `RUNS_DIR`).
- Data utilities (`data/utils.py`, `data/host_utils.py`, `data/mobility.py`).
- Data loaders (`data/loaders/*.py`) — exposed to the download registry.
- Slug registry inside `AOI.from_slug` (current entry: `ghana`).

## 3. Out of scope

- Manifest schema → `docs/specs/data/spec.md`.
- DOWNLOADER dict convention → `docs/specs/download/spec.md`.
- ABM C++ engine + Mesa-Geo adapter → `docs/specs/abm/spec.md`.

## 4. Public API

| Symbol | Where | Notes |
|---|---|---|
| `AOI` | `mal_commonlib.aoi` | Frozen Pydantic model. `slug` matches `[a-z0-9]+(-[a-z0-9]+)*`. `bbox = (west, south, east, north)` with `west < east`, `south < north`. `crs` must parse via `pyproj.CRS.from_user_input`. `resolution_m > 0`. `scale` ∈ `{REGIONAL, NATIONAL, CONTINENTAL}`. |
| `Scale` | `mal_commonlib.aoi` | Enum: `REGIONAL` (1 km, raw raster), `NATIONAL` (GADM-2 mean-pool), `CONTINENTAL` (5 km + GADM-0 mean-pool, U-Net only). |
| `AOI.cells_per_side()` | `mal_commonlib.aoi` | `(H, W)` cells to cover `bbox` at `resolution_m`, rounded up. **Pin for the ABM output tensor shape.** |
| `AOI.from_slug(slug)` | `mal_commonlib.aoi` | Build from the in-code registry. `ghana` is the only entry today. Adding entries here is a non-breaking change. |
| `AOI.from_gadm(...)` | `mal_commonlib.aoi` | Build from GADM shapefile. Resolves `gadm_path` via arg or `MAL_GADM_PATH` env. |
| `compute_twi(dem, *, cell_size_m=None)` | `mal_commonlib.terrain.twi` | D8 + central-difference slope. Returns `xr.DataArray`, dtype `float32`, NoData `-9999.0`. |
| `REPO_ROOT`, `DATA_DIR`, `PAPERS_DIR`, `TERRAIN_DIR`, `RUNS_DIR` | `mal_commonlib.config` | Repo-relative paths, computed from `__file__`. `RUNS_DIR` is created at import. |
| Host utilities | `mal_commonlib.data.host_utils` | Shared host-loading helpers reused by ingest. |
| Mobility utilities | `mal_commonlib.data.mobility` | Shared mobility matrix helpers. |
| Data loaders | `mal_commonlib.data.loaders.<name>` | Function-style. Each module exports `DOWNLOADER`. The runner iterates these via `importlib`. |

## 5. Invariants

- **INV-1.** `AOI` is frozen (`model_config = {"frozen": True}`). Mutating `aoi.bbox = ...` raises.
- **INV-2.** `AOI.slug` always matches `[a-z0-9]+(-[a-z0-9]+)*`.
- **INV-3.** `AOI.bbox` always satisfies `west < east ∧ south < north`.
- **INV-4.** `AOI.crs` is always parseable by `pyproj.CRS.from_user_input`.
- **INV-5.** `compute_twi` output dtype is `float32` and NoData sentinel is exactly `-9999.0`.
- **INV-6.** `AOI.cells_per_side()` is the single source of truth for the ABM output `(H, W)`. Any code that hardcodes `H = W = 128` outside `commonlib` is a drift bug.
- **INV-7.** `RUNS_DIR` exists after import of `mal_commonlib.config`.

## 6. Data contracts

- `AOI.to_file(path)` writes a JSON payload with keys `slug`, `name`, `bbox`, `crs`, `resolution_m`, `scale`, `gadm_id`. `AOI.from_file(path)` is the inverse.
- `compute_twi` input: `xr.DataArray` with dims `(y, x)`, dtype coercible to `float32`. Output: same dims, `float32`, NoData `-9999.0`, attrs `long_name="Topographic Wetness Index"`, `source="D8 + central-difference slope (Beven & Kirkby 1979)"`.
- Loaders return `xr.DataArray | xr.Dataset` in memory (see `download/spec.md` §4 for the canonical signature).

## 7. Migration & deprecation

- Adding a new `Scale` value → bump MINOR (additive).
- Adding a new slug to `AOI.from_slug`'s registry → PATCH (data, not API).
- Renaming `AOI` field → bump MAJOR.
- Changing TWI formula → bump MAJOR (output consumers are pinned).
- Deprecation policy: 1 MINOR version carries the deprecation warning; removed in the next MAJOR.

## 8. Drift check

```bash
# INV-1: AOI is frozen
uv run python -c "from mal_commonlib.aoi import AOI; a = AOI.from_slug('ghana'); a.bbox = (0,0,0,0); print('FAIL: not frozen')"

# INV-2/3/4: validator surface
uv run pytest mal-commonlib/tests/test_aoi.py -v

# INV-5: TWI output contract
uv run pytest mal-commonlib/tests/test_twi.py -v

# INV-6: cells_per_side is the only source of (H, W)
rg "H\s*=\s*W\s*=\s*128|H\s*=\s*128|W\s*=\s*128" mal-core/src/ mal-execution/src/ | grep -v tests

# INV-7: paths exist
test -d "$(uv run python -c 'from mal_commonlib.config import RUNS_DIR; print(RUNS_DIR)')"
```

## 9. Examples

```python
from mal_commonlib.aoi import AOI, Scale

# Canonical construction
aoi = AOI.from_slug("ghana")
assert aoi.scale == Scale.REGIONAL
H, W = aoi.cells_per_side()  # drives the ABM output tensor shape

# Round-trip via JSON
aoi.to_file("data/ghana/aoi.json")
aoi2 = AOI.from_file("data/ghana/aoi.json")
assert aoi2 == aoi
```

```python
import xarray as xr
from mal_commonlib.terrain.twi import compute_twi

dem = xr.open_dataarray("terrain/ghana_dem.tif")
twi = compute_twi(dem, cell_size_m=1000)
assert twi.dtype == "float32"
assert float(twi.rio.nodata) == -9999.0
```

## 10. References

- KG ADR: `adr-spec-design-2026-07-30` (spec template + affects block).
- Specs (by folder): `data`, `download`, `ingest`, `abm`, `training`, `prediction`.
- External: Beven & Kirkby (1979) — TWI reference formulation.