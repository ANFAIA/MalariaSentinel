# mal-core — Stable Core

`mal-core` contains the stable, reusable logic for MalariaSentinel (the Centinela). It is the production code promoted from experiments (`mal-ghana-sim`, `mal-data-explorer`). No orchestrator lives here — a future GUI/agent interface will compose these CLI calls.

## Pipeline stage order

Run each stage's CLI subcommand directly. There is no orchestrator (`malariasim run`) in `mal-core`.

| # | Stage | Function | CLI subcommand | Output |
|---|---|---|---|---|
| 1 | download | `run_download()` | `malariasim download` | `data/<aoi>/` |
| 2a | ingest (env) | `build_env_tensor()` | `malariasim ingest` | `runs/<aoi>/ingest/` |
| 2b | ingest (hosts) | `build_host_dataset()` | `malariasim ingest --stage hosts` | `runs/<aoi>/hosts/` |
| 2c | ingest (mobility) | `build_mobility_dataset()` | `malariasim ingest --stage mobility` | `runs/<aoi>/mobility/` |
| 3 | abm | `run_abm_from_manifest()` | `malariasim abm` | `runs/<aoi>/abm/` |
| 4 | scoring | `run_calibration()` | `malariasim score` | `runs/<aoi>/scoring/` |
| 5 | training | `train_unet()` | `malariasim train` | `runs/<aoi>/training/` |
| 6 | prediction | `run_prediction()` | `malariasim predict` | `runs/<aoi>/prediction/` |

### Data dependencies (filesystem handoff)

Each stage reads artefacts written by the previous stage:

- **ingest** reads raw data from `data/<aoi>/` (written by download).
- **abm** reads the manifest at `data/<aoi>/manifest.json` which references env, habitat, hosts, and mobility files.
- **scoring** reads the ABM output from `runs/<aoi>/abm/`.
- **training** reads the ABM output from `runs/<aoi>/abm/` (rollout tifs).
- **prediction** reads the trained model from `runs/<aoi>/training/` and the env tensor from `data/<aoi>/`.

### Example: sequential run

```bash
malariasim download --aoi ghana --years 2024,2025
malariasim ingest --aoi ghana --year 2024 --month 6
malariasim abm --aoi ghana --year 2024 --month 6 --days 90 --seed 1
malariasim score --run-dir runs/ghana/abm/
malariasim train --run-dir runs/ghana/abm/ --epochs 50
malariasim predict --aoi ghana --scale regional --year 2024
```

## Modules

| Module | Purpose |
|---|---|
| `download/` | Plugin-based data fetcher (DOWNLOADER dict, registry, runner, auth gate) |
| `ingest/` | Build env tensor, host density, mobility matrices from raw data |
| `abm/` | C++ ABM engine wrapper + output contract (state .tif, env NC) |
| `scoring/` | Calibration scorers (D1..D15) + composite + LLM scorer |
| `training/` | U-Net model, dataset, trainer, wrapper |
| `prediction/` | Risk raster prediction (registry, aggregators, predictor) |
