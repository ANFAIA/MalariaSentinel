# mal-core — Stable Core

`mal-core` contains the stable, reusable logic for MalariaSentinel (the Centinela). It is the production code promoted from experiments (`mal-data-explorer`, former `mal-ghana-sim`). The `malariasim` CLI entry point lives here (`pyproject.toml` → `mal_core:cli_main`); a future GUI/agent interface will compose these CLI calls.

## Pipeline stage order

Run each stage's CLI subcommand directly. There is no orchestrator (`malariasim run`).

| # | Stage | Function | CLI subcommand | Default output |
|---|---|---|---|---|
| 1 | download | plugin-based fetchers | `malariasim download` | `data/<aoi>/` |
| 2a | ingest (env) | `build_env_tensor()` | `malariasim ingest` | `runs/ingest/` |
| 2b | ingest (hosts) | `build_host_dataset()` | `malariasim ingest --stage hosts` | `runs/hosts/` |
| 2c | ingest (mobility) | `build_mobility_dataset()` | `malariasim ingest --stage mobility` | `runs/mobility/` |
| 3 | abm | `run_abm_from_manifest()` | `malariasim abm` | `runs/abm/` |
| 4 | scoring | `run_scoring()` | `malariasim score` | `scorecard.json` inside the run dir |
| 5 | training | `train_unet()` | `malariasim train` | `runs/training/` |
| 6 | prediction | `run_prediction()` | `malariasim predict` | `runs/prediction/` |
| — | detection audit | D16 launch-and-measure | `malariasim validate-detections` | `runs/validate-detections/` |
| — | cases audit | D25 DHIMS cases check | `malariasim validate-cases` | `runs/validate-cases/` |

Every command accepts `--output-dir` to override the default location.

### Data dependencies (filesystem handoff)

Each stage reads artefacts written by the previous stage:

- **ingest** reads raw data from `data/<aoi>/` (written by download).
- **abm** reads the manifest at `data/<aoi>/manifest.json`, which references env, habitat, hosts, and mobility files.
- **scoring** reads the ABM output directory passed via `--run-dir` and writes `scorecard.json` **inside** it.
- **training** reads the ABM output (rollout snapshot tifs).
- **prediction** reads the trained model from `runs/training/` and the env tensor from `data/<aoi>/`.

### Example: sequential run

```bash
# Optional: compile C++ ABM engine (can be run from anywhere, or with --worktree)
malariasim abm --compile
# Or inside a gawt worktree:
# malariasim abm --compile --worktree .gitagent/worktree

malariasim download --aoi ghana --years 2024,2025
malariasim ingest --aoi ghana --year 2024 --month 6
malariasim abm --aoi ghana --year 2024 --month 6 --days 90 --seed 1
malariasim score --run-dir runs/abm/2024-06_seed0001
malariasim train --run-dir runs/abm/2024-06_seed0001 --epochs 50
malariasim predict --aoi ghana --scale regional --year 2024
```

## Scoring (`malariasim score`)

Post-run scoring lives in `scoring/` (not in the pytest calibration harness). It runs every registered scorer against the run's artefacts (state COGs, cohort/aquatic JSONs), computes a weighted-composite scorecard with binary gates reported separately, and writes `scorecard.json` into `--run-dir`.

```bash
malariasim score --run-dir runs/abm/2024-06_seed0001            # all scorers
malariasim score --run-dir runs/abm --only d2_survival,d15_persistence
malariasim score --run-dir runs/abm --skip g24_urban_ratio --list
malariasim score --run-dir runs/abm --enable d25_cases_ghana    # activate a MANUAL scorer
```

- **MANUAL scorers** (AOI-dependent: `D16_detection_coverage`, `D25_cases_ghana`, `G24_urban_ratio`) never run by default — activate with `--enable <name>` or `enabled: true` in a scoring YAML.
- The AOI is always explicit via `--aoi <aoi>` when the run metadata lacks it; it is never inferred from paths.
- `--tier` is a legacy flag (belongs to the calibration pytest harness).
- Skip a dimension and it is excluded from the composite.

## Modules

| Module | Purpose |
|---|---|
| `download/` | Plugin-based data fetcher (DOWNLOADER dict, registry, runner, auth gate, manifest) |
| `ingest/` | Build env tensor, host density, mobility matrices from raw data |
| `abm/` | C++ ABM engine, wrapper, build scripts — see its [README](src/mal_core/abm/README.md) |
| `scoring/` | Post-run scorers (D1..D25 + gates) + composite + scorecard writer |
| `training/` | U-Net model, dataset, trainer, wrapper |
| `prediction/` | Risk raster prediction (registry, aggregators, predictor) |
| `cli.py` | The `malariasim` Typer application (all subcommands) |
| `scenario.py` | Scenario definitions for prediction |
| `server.py` | API server (`malariasim serve`) |

## Tests

| Suite | Command |
|---|---|
| Python unit tests | `cd mal-core && uv run pytest` |
| C++ engine tests | `ctest --test-dir src/mal_core/abm/build --output-on-failure` |
| Calibration harness (pytest) | see `src/mal_core/abm/tests/calibration/README.md` |
