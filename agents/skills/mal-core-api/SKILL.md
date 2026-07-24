---
name: mal-core-api
description: API reference for the mal-core subpackages — training (UNet model, dataset, trainer, wrapper), prediction (predictor, registry, env/state loaders, AOI aggregator), ABM simulation wrapper, pipeline orchestrator, scoring/calibration, and FastAPI/CLI entrypoints. Use when working with mal-core stable modules, writing code that imports from mal_core, or needing to understand what public APIs are available in the promoted core.
---

# mal-core-api

**Use this skill when:** working with the mal-core promoted modules — UNet training, prediction pipelines, model registry, scenario configuration, AOI/scale definitions, environmental data loading, ABM state loading, C++ ABM wrapper, pipeline orchestration, scoring/calibration, or the FastAPI/CLI entrypoints. This covers the stable, production-grade Centinela core.

## Overview

`mal-core` is the stable pipeline logic of MalariaSentinel (the Centinela). It contains promoted, tested modules organised into six subpackages: `abm/` (C++ simulation wrapper), `training/` (UNet model, dataset, trainer, wrapper), `prediction/` (predictor, registry, env/state loaders, AOI aggregator/resolver), `ingest/` (environment builder), `scoring/` (calibration runner, feedback generator), and `pipeline/` (orchestrator, stages, flag registry). Packages in the experiment tier (`mal-ghana-sim`, `mal-data-explorer`) may depend on these modules; `mal-core` itself depends only on `mal-commonlib`.

```python
import mal_core
```

## Quick reference — public exports

| Export | Module | Type | Purpose |
|---|---|---|---|
| `UNet` | `training.model` | `nn.Module` | U-Net transition surrogate (6→2 channels) |
| `combined_loss` | `training.model` | function | MSE + soft-Dice loss |
| `eval_dice` | `training.model` | function | Dice coefficient evaluation |
| `RolloutDataset` | `training.dataset` | `Dataset` | ABM rollout patch dataset |
| `get_dataloaders` | `training.dataset` | function | Train/val dataloaders from rollout dir |
| `train_unet` | `training.trainer` | function | End-to-end U-Net training loop |
| `UNetWrapper` | `training.wrapper` | class | ModelProtocol wrapper for U-Net checkpoints |
| `make_aoi` | `prediction.aggregator` | function | Create AOI from slug + scale |
| `get_aggregator` | `prediction.aggregator` | function | Get scale-appropriate aggregator |
| `grid_shape` | `prediction.aggregator` | function | AOI grid (H, W) tuple |
| `RegionalAggregator` | `prediction.aggregator` | class | Identity aggregation (raw raster) |
| `NationalAggregator` | `prediction.aggregator` | class | GADM-2 mean-pool |
| `ContinentalAggregator` | `prediction.aggregator` | class | GADM-0 scalar mean |
| `resolve_aoi` | `prediction.aoi_resolver` | function | Resolve AOI data paths from manifest |
| `ModelRegistry` | `prediction.registry` | class | Load/discover models from manifests |
| `ModelManifest` | `prediction.registry` | Pydantic model | model.yaml schema |
| `DummyModel` | `prediction.registry` | class | Zero-output fallback model |
| `run_prediction` | `prediction.predictor` | function | Full prediction pipeline (load→infer→save) |
| `get_latest_prediction` | `prediction.predictor` | function | Path to most recent prediction for AOI |
| `get_prediction_metadata` | `prediction.predictor` | function | Sidecar metadata for latest prediction |
| `load_env_stack` | `prediction.env_loader` | function | Load env rasters for AOI |
| `load_abm_state` | `prediction.state_loader` | function | Load ABM snapshot for AOI |
| `ScenarioConfig` | `scenario` | Pydantic model | Full scenario definition |
| `InterventionConfig` | `scenario` | Pydantic model | Single intervention spec |
| `ClimateConfig` | `scenario` | Pydantic model | Climate anomaly spec |
| `load_scenario` | `scenario` | function | Parse YAML → ScenarioConfig |
| `interventions_to_params` | `scenario` | function | Scenario → model parameter dict |
| `CppAbmWrapper` | `abm.wrapper` | class | Python wrapper for C++ ABM binary |
| `run_abm` | `abm.runner` | function | Run ABM simulation via wrapper |
| `run_pipeline` | `pipeline.runner` | function | Run full SDSS pipeline |
| `Stage` | `pipeline.stages` | Enum | Pipeline stage identifiers |
| `aggregate_flags` | `pipeline.flag_registry` | function | Auto-aggregate flags from subpackages |
| `run_calibration` | `scoring.runner` | function | Run calibration scorers |
| `get_feedback` | `scoring.feedback` | function | Generate feedback from scorecard |
| `build_environment` | `ingest.env_builder` | function | Build env tensor for AOI |
| `fastapi_app` | `server` | `FastAPI` | REST API for the SDSS |
| `cli_main` | `cli` | function | Typer CLI entrypoint |

---

## Module docs

### `training/model.py` — U-Net transition surrogate

Input: `(state_t + env)` = `(6, 128, 128)` → Target: `state_{t+1}` = `(2, 128, 128)`.

4 down/up blocks (32→64→128→256), BatchNorm + ReLU, concat skip connections.

```python
from mal_core.training.model import UNet, combined_loss, eval_dice

model = UNet(in_channels=6, out_channels=2, channels=(32, 64, 128, 256))
x = torch.randn(4, 6, 128, 128)  # batch of 4
pred = model(x)                   # (4, 2, 128, 128)

loss, mse_val, dice_val = combined_loss(pred, target)
score = eval_dice(pred, target)   # float, higher is better
```

**Parameters:**
- `UNet(in_channels=6, out_channels=2, channels=(32, 64, 128, 256))`
- `combined_loss(pred, target)` → `(loss, mse, dice)` — MSE + 0.5×soft-dice
- `eval_dice(pred, target, thresh=0.01)` → `float`

---

### `training/dataset.py` — Rollout dataset for U-Net training

Reads ABM rollout snapshots from a run directory, tiles into 128×128 patches, and builds `(state_t + env) → state_{t+1}` pairs. Train/val split: west of 0° lon = train, east = val.

```python
from mal_core.training.dataset import RolloutDataset, get_dataloaders

# Single dataset
ds = RolloutDataset("runs/1year-50r", split="train", subsample=0.5, preload=True)
x, y = ds[0]  # x: (6, 128, 128), y: (2, 128, 128)

# DataLoaders
train_loader, val_loader = get_dataloaders("runs/1year-50r", batch_size=16)
```

**Parameters:**
- `RolloutDataset(run_dir, split="train"|"val", patch_size=128, subsample=1.0, preload=False)`
- `get_dataloaders(run_dir, batch_size=16, num_workers=0, subsample=1.0, preload=False)` → `(train_loader, val_loader)`

**Input channels:** 2 state + 4 env (zeroed in current training set) = 6 total.

---

### `training/trainer.py` — U-Net training loop

```python
from mal_core.training.trainer import train_unet

best_dice = train_unet(
    run_dir="runs/1year-50r",
    output_dir="runs/models/unet-v1",
    epochs=50,
    batch_size=16,
    lr=1e-3,
    device=None,       # auto-detect: cuda > mps > cpu
    subsample=1.0,
    preload=False,
)
# Saves: best_model.pt, final_model.pt, model_epoch_{N}.pt
```

**Parameters:**
- `train_unet(run_dir, output_dir, epochs=50, batch_size=16, lr=1e-3, device=None, subsample=1.0, preload=False)` → `float` (best val dice)

---

### `training/wrapper.py` — ModelProtocol wrapper

Wraps a trained U-Net checkpoint to implement `ModelProtocol` (required by the registry).

```python
from mal_core.training.wrapper import UNetWrapper

wrapper = UNetWrapper("runs/models/unet-v1/best_model.pt", device="mps")
pred = wrapper.predict(state, env)  # state: (2,H,W), env: (4,H,W) → (2,H,W)
```

**Parameters:**
- `UNetWrapper(checkpoint_path, device=None)` — auto-detects device if None
- `.predict(state: np.ndarray, env: np.ndarray) → np.ndarray` — concatenates inputs, runs inference

---

### `prediction/aggregator.py` — AOI/scale abstraction and aggregation

Defines grid resolutions per scale and aggregation strategies.

```python
from mal_core.prediction.aggregator import make_aoi, get_aggregator, grid_shape
from mal_commonlib.aoi import Scale

aoi = make_aoi("ghana", Scale.REGIONAL)
h, w = grid_shape(aoi)  # e.g. (128, 128)

agg = get_aggregator(Scale.NATIONAL)
aggregated = agg.aggregate(raster, aoi)  # GADM-2 mean-pool
```

**Scale grids:**

| Scale | Resolution | Grid | Aggregation |
|---|---|---|---|
| `REGIONAL` | 1 km | 128×128 | Identity (raw raster) |
| `NATIONAL` | 2 km | 128×128 | GADM-2 mean-pool (10×10 blocks) |
| `CONTINENTAL` | 5 km | 128×128 | Scalar mean |

**AOI catalogue:** `ghana` — bbox `(-2.97, 4.69, 0.79, 9.79)`, CRS `EPSG:4326`, GADM `GHA`.

---

### `prediction/env_loader.py` — Environmental stack loading

Loads real environmental rasters (water fraction, rainfall, temperature, NDVI) from `runs/env_stack.npz` and resamples to the AOI grid.

```python
from mal_core.prediction.env_loader import load_env_stack, ENV_CHANNEL_ORDER

env = load_env_stack(aoi)  # (4, H, W) float32
# Channel order: water_frac, rainfall, temperature, ndvi
```

**Parameters:**
- `load_env_stack(aoi, env_path=None)` → `np.ndarray (4, H, W)` — defaults to `runs/env_stack.npz`
- `ENV_CHANNEL_ORDER = ["water_frac", "rainfall", "temperature", "ndvi"]`
- `ENV_CHANNELS = 4`

---

### `prediction/predictor.py` — Prediction pipeline orchestrates load → infer → save

```python
from mal_core.prediction.predictor import run_prediction, get_latest_prediction, get_prediction_metadata
from mal_commonlib.aoi import Scale

out = run_prediction(
    aoi_slug="ghana",
    scale=Scale.REGIONAL,
    year=2026,
    month=6,
    model_name="unet-v1",
    model_version=None,   # latest
    scenario=None,         # or ScenarioConfig
    output_dir=None,       # defaults to runs/predictions/
)
# Returns Path to GeoTIFF

latest = get_latest_prediction("ghana")  # Path | None
meta = get_prediction_metadata("ghana")  # dict | None
```

**Output contract v1.1:** GeoTIFF + `.tif.json` sidecar with CRS, transform, model info.

---

### `scenario.py` — Expert-knowledge YAML scenarios

Pydantic-validated scenario configs for intervention plans and climate assumptions.

```yaml
# example_scenario.yaml
scenario:
  aoi: ghana
  scale: regional
  year: 2026
  month: 6
  interventions:
    - type: bednets
      coverage: 0.7
    - type: irs
      coverage: 0.3
  climate:
    rainfall_anomaly: 0.1
    temperature_anomaly: 0.5
```

```python
from mal_core import load_scenario, interventions_to_params, ScenarioConfig

scenario = load_scenario("example_scenario.yaml")
params = interventions_to_params(scenario)
# → {"mortality_multiplier": 0.72, "biting_reduction": 0.78,
#    "rainfall_multiplier": 1.1, "temperature_offset": 0.5}
```

**Intervention types:** `bednets`, `irs`, `larviciding`, `drug_campaign`, `vaccine`

**Effect table:**

| Intervention | Effect |
|---|---|
| `bednets` | mortality ×0.4, biting reduction 0.6 |
| `irs` | mortality ×0.5, biting reduction 0.4 |
| `larviciding` | breeding reduction 0.5 |
| `drug_campaign` | clearance rate 0.8 |
| `vaccine` | susceptibility reduction 0.3 |

---

### `prediction/registry.py` — Model registry

Loads models from `runs/models/{name}/model.yaml` manifests. Each manifest declares name, version, contract, and checkpoint path.

```python
from mal_core.prediction.registry import ModelRegistry

registry = ModelRegistry()  # defaults to runs/models/
models = registry.list_models()  # [{"name": ..., "version": ..., "path": ...}]

model = registry.load("unet-v1")           # latest version
model = registry.load("unet-v1", "1.0.0")  # specific version
pred = model.predict(state, env)
```

**ModelProtocol:** any class with `predict(state: np.ndarray, env: np.ndarray) → np.ndarray`.

**model.yaml schema (`ModelManifest`):**

```yaml
name: unet-v1
version: "1.0.0"
contract_version: "1.1"
in_channels: 6
out_channels: 2
checkpoint: best_model.pt
description: "U-Net transition surrogate"
```

---

### `server.py` — FastAPI REST API

```python
from mal_core.server import fastapi_app

# Run: uvicorn mal_core.server:app --reload
# Or via CLI: malariasim serve --host 0.0.0.0 --port 8000
```

**Endpoints:**

| Method | Path | Body | Description |
|---|---|---|---|
| `POST` | `/predict` | `PredictRequest` | Run prediction with scenario |
| `GET` | `/aoi/{name}/risk` | — | Latest prediction path for AOI |
| `GET` | `/aoi/{name}/status` | — | Prediction metadata |

---

### `cli.py` — Typer CLI

```bash
# Pipeline
malariasim run --aoi ghana --stages abm,score --days 90

# Individual stages
malariasim ingest --aoi ghana --year 2024 --month 6
malariasim abm --aoi ghana --days 30
malariasim score --run-dir runs/pipeline/
malariasim train --run-dir runs/abm/ --epochs 50
malariasim feedback --run-dir runs/pipeline/

# Existing
malariasim predict --aoi ghana --scale regional --year 2026 --month 6 --model unet-v1
malariasim predict --scenario scenario.yaml
malariasim status --aoi ghana
malariasim serve --host 127.0.0.1 --port 8000
```

---

### `prediction/state_loader.py` — ABM state loading

Loads the ABM rollout snapshot closest to the target month, crops to the AOI bbox, returns `(2, H, W)` float32.

```python
from mal_core.prediction.state_loader import load_abm_state

state = load_abm_state(aoi, month=6, rollout_dir=None, seed=0)
# state: (2, H, W) float32
```

**Parameters:**
- `load_abm_state(aoi, month=1, rollout_dir=None, seed=0)` → `np.ndarray (2, H, W)`
- Default rollout dir: `runs/1year-50r/`
- Picks snapshot at `day = month * 30` (clamped to 7–360)

---

### `abm/wrapper.py` — C++ ABM wrapper

Python wrapper around the compiled C++ ABM binary. Supports flag introspection and parameterized runs.

```python
from mal_core.abm.wrapper import CppAbmWrapper

wrapper = CppAbmWrapper(binary_path="bin/libabm.so")
flags = wrapper.flags()  # dict of available simulation flags
result = wrapper.run(params, days=90, seed=42)
```

**Parameters:**
- `CppAbmWrapper(binary_path)` — loads the shared library
- `.flags()` → `dict[str, str]` — available simulation flags
- `.run(params: dict, days: int = 90, seed: int = 0)` → `np.ndarray` — rollout output

---

### `abm.runner.py` — Run ABM simulation

```python
from mal_core.abm.runner import run_abm

rollout = run_abm(
    aoi_slug="ghana",
    days=30,
    seed=0,
    params=None,  # optional overrides
)
# Returns path to rollout directory
```

---

### `pipeline/runner.py` — Pipeline orchestrator

Runs the full SDSS pipeline across selected stages.

```python
from mal_core.pipeline.runner import run_pipeline
from mal_core.pipeline.stages import Stage

result = run_pipeline(
    aoi_slug="ghana",
    stages=[Stage.INGEST, Stage.ABM, Stage.SCORE],
    days=90,
    seed=0,
)
```

**Parameters:**
- `run_pipeline(aoi_slug, stages, days=90, seed=0)` → `dict` — results keyed by stage

---

### `pipeline/stages.py` — Pipeline stage identifiers

```python
from mal_core.pipeline.stages import Stage

# Stage.INGEST, Stage.ABM, Stage.SCORE, Stage.TRAIN, Stage.PREDICT, Stage.FEEDBACK
```

---

### `pipeline/flag_registry.py` — Auto-aggregate flags

```python
from mal_core.pipeline.flag_registry import aggregate_flags

flags = aggregate_flags("ghana")
# Merges flags from abm, training, prediction subpackages
```

---

### `scoring/runner.py` — Calibration runner

```python
from mal_core.scoring.runner import run_calibration

scorecard = run_calibration(
    run_dir="runs/pipeline/",
    scorers=None,  # all registered scorers
)
# Returns dict with scorer_name → {score, delta, best}
```

---

### `scoring/feedback.py` — Feedback generator

```python
from mal_core.scoring.feedback import get_feedback

feedback = get_feedback(scorecard)
# Returns structured feedback with recommendations
```

---

### `ingest/env_builder.py` — Environment builder

```python
from mal_core.ingest.env_builder import build_environment

env_tensor = build_environment(aoi_slug="ghana", year=2024, month=6)
# Returns (4, H, W) float32 environmental tensor
```

---

### `prediction/aoi_resolver.py` — AOI data path resolver

```python
from mal_core.prediction.aoi_resolver import resolve_aoi

paths = resolve_aoi("ghana")
# Returns dict with env_path, state_path, rollout_path, etc.
```

---

## Integration guide

### From `mal-execution/scripts/`

```python
from mal_core.prediction.predictor import run_prediction
from mal_core.scenario import load_scenario
from mal_commonlib.aoi import Scale

# Direct call
out = run_prediction("ghana", Scale.REGIONAL, 2026, month=6)

# From scenario YAML
scenario = load_scenario("scenarios/ghana_baseline.yaml")
out = run_prediction(scenario.aoi, scenario.scale, scenario.year, scenario.month, scenario=scenario)
```

### From `mal-ghana-sim/scripts/`

```python
from mal_core.training.trainer import train_unet
from mal_core.training.dataset import RolloutDataset

# Train from rollout data produced by the simulation
best_dice = train_unet("runs/1year-50r", "runs/models/ghana-unet", epochs=100)

# Use the dataset directly for experimentation
ds = RolloutDataset("runs/1year-50r", split="train", subsample=0.25)
```

### Serving predictions

```bash
# Start the API
malariasim serve --port 8000

# POST a prediction
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"aoi": "ghana", "scale": "regional", "year": 2026, "month": 6, "model_name": "unet-v1"}'
```

## Common patterns

1. **Auto device detection** — every module defaults to `cuda > mps > cpu`. Pass `device=None` to use it.
2. **Graceful fallback** — `run_prediction` falls back to zero arrays if ABM state or env stack is unavailable (dummy mode).
3. **Output contract v1.1** — all predictions write a `.tif.json` sidecar alongside the GeoTIFF with CRS, transform, model info.
4. **Scale → aggregation** — use `get_aggregator(scale)` to get the right post-processing for the output resolution.
5. **ModelProtocol** — any class with `predict(state, env) → np.ndarray` can be registered. Wrap custom models in a thin class.
