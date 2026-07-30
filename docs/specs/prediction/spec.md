# prediction Spec

> Owns the **inference + aggregation + registry** layer: load a
> trained surrogate, run it on real env tensors, aggregate per
> scale, and emit a risk raster.

---

```yaml
# Machine-readable affects block — parsed by the drift-check agent.
# Bidirectional: if A affects B, B must declare affected_by A.
# `target` is the folder name under docs/specs/ (stable across KG migrations).
affects:
  - target: training
    direction: upstream
    reason: prediction loads checkpoints from UNetWrapper; in_channels/out_channels shape pinned here
    severity: breaking
  - target: abm
    direction: upstream
    reason: prediction reads ABM state as the surrogate input (state_loader)
    severity: breaking
  - target: ingest
    direction: upstream
    reason: prediction's env_loader reads env tensors written by ingest (NetCDF or COG)
    severity: breaking
  - target: data
    direction: upstream
    reason: prediction's contract_version and sidecar keys come from the data spec
    severity: breaking
  - target: commonlib
    direction: upstream
    reason: AOI, Scale, RUNS_DIR come from commonlib
    severity: non-breaking
  - target: pipeline
    direction: bidirectional
    reason: pipeline dispatches Stage.PREDICTION → run_prediction (hardcodes scale=REGIONAL, see §5.4)
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
| Component | `mal-core/src/mal_core/prediction/` |
| Version | `v1.1` (output contract); `v1.0` (model registry) |
| Status | `stable` |
| Owner | David Flórez-Mazuera |
| Last drift check | `2026-07-30` |

## 1. Objective

Prediction is the **decision-support surface**. It loads a trained
surrogate (per `training/spec.md`), runs it on the actual env
tensor for an AOI/month, aggregates per `Scale`, and writes a risk
raster consumable by downstream tooling (maps, dashboards,
intervention planning).

Without prediction the training stage would produce dead
checkpoints. The aggregators (`RegionalAggregator`,
`NationalAggregator`, `ContinentalAggregator`) are what make the
SDSS multi-scale.

## 2. In scope

- `run_prediction(aoi_slug, scale, year, month=1, *, model_name="dummy", model_version=None, scenario=None, output_dir=None) -> Path`.
- Model registry (`ModelRegistry`, `ModelManifest`, `RegistryEntry`, `DummyModel`, `UNetWrapper`).
- Per-scale aggregators: `RegionalAggregator` (passthrough), `NationalAggregator` (10×10 mean-pool), `ContinentalAggregator` (GADM-0 scalar).
- `make_aoi(slug, scale)`, `get_aggregator(scale)`, `grid_shape(aoi)`.
- `get_latest_prediction(aoi_slug)`, `get_prediction_metadata(aoi_slug)`.
- `load_env_stack(aoi)` and `load_abm_state(aoi, month)` (state and env loaders).
- Flag schema (`PREDICTION_FLAGS_SCHEMA`, `PredictionFlags`).

## 3. Out of scope

- Training the surrogate → `docs/specs/training/spec.md`.
- ABM rollouts → `docs/specs/abm/spec.md`.
- Env tensor production → `docs/specs/ingest/spec.md`.
- File naming on disk → `docs/specs/data/spec.md`.
- AOI/Scale → `docs/specs/commonlib/spec.md`.

## 4. Public API

| Symbol | Where | Notes |
|---|---|---|
| `run_prediction(...)` | `mal_core.prediction.predictor` | Returns `Path` of the written `_risk.tif`. |
| `get_latest_prediction(aoi_slug)` | `mal_core.prediction.predictor` | Returns `Path | None` of the most recent `_risk.tif` for the AOI. |
| `get_prediction_metadata(aoi_slug)` | `mal_core.prediction.predictor` | Returns `dict | None` from the sidecar. |
| `ModelRegistry()` | `mal_core.prediction.registry` | Scans `runs/models/` (default) for `model.yaml` manifests. |
| `ModelManifest` | `mal_core.prediction.registry` | Pydantic: `name, version, contract_version="1.1", in_channels=5, out_channels=1, checkpoint="", description=""`. |
| `DummyModel` | `mal_core.prediction.registry` | Returns zeros `(1, H, W)`. Default if no checkpoint. |
| `make_aoi(slug, scale)` | `mal_core.prediction.aggregator` | Wraps `commonlib.AOI.from_slug` with per-scale `GridDef`. |
| `get_aggregator(scale)` | `mal_core.prediction.aggregator` | Returns `RegionalAggregator | NationalAggregator | ContinentalAggregator`. |
| `grid_shape(aoi)` | `mal_core.prediction.aggregator` | `(H, W) = aoi.cells_per_side()`. |
| `SCALE_GRIDS`, `AOI_CATALOGUE` | `mal_core.prediction.aggregator` | Per-scale grid definitions and slug catalog (currently just `ghana`). |
| `load_env_stack(aoi)` | `mal_core.prediction.env_loader` | Loads `runs/env_stack.npz`, selects the 4 env channels, reprojects to AOI grid. Returns `(4, H, W)`. |
| `load_abm_state(aoi, month, rollout_dir=None, seed=0)` | `mal_core.prediction.state_loader` | Picks the snapshot closest to `month*30` (clamped to `[7, 360]`). Returns `(2, H, W)`. |

## 5. Invariants

### §5.1 Input contract

- **INV-1.** `model.predict(state: (2,H,W) float32, env: (4,H,W) float32) -> (1,H,W) float32`. State and env channels per `abm/spec.md` §5.1 INV-1 and §5.2 INV-6.
- **INV-2.** `load_env_stack` selects channels in order `["water_frac", "rainfall", "temperature", "ndvi"]` (note: `temperature`, **not** `temp_suitability` — see §6.2).
- **INV-3.** `load_abm_state` picks `state_seed{seed:04d}_day{min(360,max(7,month*30)):03d}.{npy,tif}`. Falls back to the first available snapshot if the target day is missing. Raises `FileNotFoundError` if no snapshots exist.

### §5.2 Model registry

- **INV-4.** Models live under `runs/models/<name>_<version>/model.yaml`. The YAML schema: `name, version, contract_version, in_channels, out_channels, checkpoint, description`.
- **INV-5.** `ModelRegistry.load(name, version=None)` returns the model instance. If `version=None`, picks the lexicographically latest `<name>@<version>`. If `checkpoint=""` → returns `DummyModel()`. Otherwise instantiates `UNetWrapper(<entry_path>/<checkpoint>)`.
- **INV-6.** `ModelManifest.contract_version` defaults to `"1.1"` (the prediction output contract). Models trained before this default must declare their version explicitly.

### §5.3 Aggregators (per `Scale`)

- **INV-7.** `RegionalAggregator` returns the input unchanged. Default `GridDef`: `resolution_m=1000, tile_size=128`.
- **INV-8.** `NationalAggregator` pools with `(n_rows, n_cols) = (max(1, H//10), max(1, W//10))`, block size = `(H // n_rows, W // n_cols)`. Trims to `block_h * n_rows, block_w * n_cols`, then `mean(axis=(-3, -1))`. Default `GridDef`: `resolution_m=2000, tile_size=128`.
- **INV-9.** `ContinentalAggregator` returns `np.array([float(raster.mean())])` — a single scalar per AOI. Default `GridDef`: `resolution_m=5000, tile_size=128`.
- **INV-10.** `AOI_CATALOGUE` is the source of truth for which slugs `make_aoi` accepts. Adding a slug is a MINOR change; removing one is MAJOR.

### §5.4 Pipeline integration

- **INV-11.** The `pipeline` spec hardcodes `scale=Scale.REGIONAL` when dispatching `Stage.PREDICTION`. Bumping this default requires both specs to bump in lockstep.
- **INV-12.** Output filename: `{aoi_slug}_{scale}_{year}_{month:02d}_risk.tif`. Sidecar: `<file>.tif.json` (the unusual `.tif.json` suffix is preserved for backward compat with current artefacts).

### §5.5 Output GeoTIFF + sidecar

- **INV-13.** GeoTIFF: `driver="GTiff"`, `dtype="float32"`, `count=1`, `nodata=-9999.0`, `tiled=True`, `compress="deflate"`, `blockxsize=blockysize=128`, `crs=aoi.crs`, transform from `from_bounds(*aoi.bbox, w, h)`.
- **INV-14.** Band description: `["risk"]` (single band).
- **INV-15.** Sidecar keys: `crs, transform, aoi_slug, scale, year, month, model_name, model_version, contract_version, generator_version`. Required for downstream consumers.
- **INV-16.** `contract_version: "1.1"` on every emitted file. (Note: differs from `abm/spec.md` §5.1 INV-15 which pins `1.0` for state/env. The prediction output is a different file family — see §6.2.)

## 6. Data contracts

### §6.1 Output raster

`{aoi_slug}_{scale}_{year}_{month:02d}_risk.tif` per §5.4–§5.5. Single-band float32 risk raster with sidecar JSON per §5.5 INV-15.

### §6.2 Known drift (must be fixed in v1.2 / v2.0)

| Item | Spec says | Code says | Severity |
|---|---|---|---|
| Env channel name | `temp_suitability` (`abm/spec.md` §5.2) | `temperature` (`prediction/env_loader.py:21`) | **P0 drift** — `load_env_stack` will fail if the env NPZ doesn't contain a `temperature` key. |
| Env loader source | NetCDF written by ingest | `runs/env_stack.npz` (legacy M5 stack) | **P1 drift** — the M5 stack pre-dates the M11 ingest. Predictions against the current AOI bbox use hardcoded bounds `(-3.0, 4.0, 2.0, 12.0)` (line 93). |
| `in_channels` | 6 (state + env) per `training/spec.md` | 5 default in `ModelManifest` | **P1 drift** — placeholder default; real models must set 6. |
| Sidecar suffix | `.json` (per `abm/spec.md` §5.3) | `.tif.json` (line 126 of `predictor.py`) | **P0 drift** — prediction sidecars are not picked up by the ABM-side readers that expect `.json`. |

These must be reconciled before the next MAJOR bump. Tracked here until fixed.

## 7. Migration & deprecation

- **Bumping `contract_version` to v1.2** is non-breaking if the change is additive (new optional sidecar key, new aggregator scale).
- **Adding a new `Scale`** → bump MINOR (additive). Requires updating `commonlib/spec.md` §4 (the `Scale` enum) and `pipeline/spec.md` §5.3 INV-10.
- **Adding a new aggregator class** is additive (MINOR).
- **Switching the sidecar suffix** (`.tif.json` → `.json`) is BREAKING (MAJOR). Requires a migration script for existing artefacts.
- Deprecation policy: 1 MINOR spec version carries the warning; removed in the next MAJOR.

## 8. Drift check

```bash
# INV-1: input/output shape contract
uv run python -c "
import numpy as np
from mal_core.prediction.registry import DummyModel
m = DummyModel()
out = m.predict(np.zeros((2,128,128),dtype='float32'), np.zeros((4,128,128),dtype='float32'))
assert out.shape == (1, 128, 128)
"

# INV-5: DummyModel fallback when checkpoint=""
uv run python -c "
from mal_core.prediction.registry import DummyModel, ModelManifest
m = ModelManifest(name='x', version='v1', checkpoint='')
assert isinstance(ModelRegistry().load.__wrapped__ if False else DummyModel(), DummyModel)
"

# §6.2 P0 drift #1: env channel naming mismatch
uv run python -c "
from mal_core.prediction.env_loader import ENV_CHANNEL_ORDER
assert ENV_CHANNEL_ORDER == ['water_frac', 'rainfall', 'temperature', 'ndvi']
" && echo "DRIFT: env channel uses 'temperature', not 'temp_suitability'"

# §6.2 P0 drift #4: sidecar suffix mismatch
rg "with_suffix\(\"\.tif\.json\"\)" mal-core/src/mal_core/prediction/predictor.py && echo "DRIFT: sidecar suffix is .tif.json, not .json"

# INV-13/14: output GeoTIFF metadata
uv run python -c "
from pathlib import Path
import rasterio
preds = sorted(Path('runs/predictions').glob('*_risk.tif'))
if preds:
    with rasterio.open(preds[-1]) as src:
        assert src.nodata == -9999.0
        assert src.descriptions[0] == 'risk'
        assert src.dtypes[0] == 'float32'
"

# INV-7/8/9: aggregators return sane shapes
uv run python -c "
import numpy as np
from mal_core.prediction.aggregator import RegionalAggregator, NationalAggregator, ContinentalAggregator
from mal_commonlib.aoi import AOI, Scale
aoi = AOI.from_slug('ghana')
r = np.random.RandomState(0).rand(2, 128, 128).astype('float32')
assert RegionalAggregator().aggregate(r, aoi).shape == r.shape
n = NationalAggregator().aggregate(r, aoi)
assert n.ndim == 3
c = ContinentalAggregator().aggregate(r, aoi)
assert c.shape == (1,)
"
```

## 9. Examples

```python
from pathlib import Path
from mal_core.prediction import run_prediction
from mal_commonlib.aoi import Scale

out = run_prediction(
    aoi_slug="ghana",
    scale=Scale.REGIONAL,
    year=2024,
    month=7,
    model_name="unet-ghana",
    output_dir=Path("runs/predictions"),
)
assert out.exists() and out.suffix == ".tif"
```

```python
# Registry lookup
from mal_core.prediction.registry import ModelRegistry
reg = ModelRegistry()
print(reg.list_models())
model = reg.load("unet-ghana")  # latest version
```

```python
# Per-scale aggregation
from mal_core.prediction.aggregator import make_aoi, get_aggregator
from mal_commonlib.aoi import Scale

for scale in Scale:
    aoi = make_aoi("ghana", scale)
    agg = get_aggregator(scale)
    risk = agg.aggregate(raster, aoi)
```

## 10. References

- KG ADR: `adr-spec-design-2026-07-30`.
- Specs (by folder): `training`, `abm`, `ingest`, `data`, `commonlib`, `pipeline`.
- Plan: `m11-pipeline-unification` (covers several §6.2 drift items).