# MalariaSentinel — Agent Guide

## Monorepo Structure

```
MalariaSentinel/
  mal-commonlib/       Shared config, paths, data utilities
  mal-core/            Stable pipeline logic (empty, ready for promotion)
  mal-execution/       CLI entrypoints, batch jobs (empty)
  mal-ghana-sim/       Ghana spread simulation + U-Net surrogate (research)
  mal-data-explorer/   Dataset visualization, mapping, bias analysis (scripts)

  data/                Datasets
  papers/              Research PDFs
  terrain/             SRTM DEM tiles and download scripts
  runs/                Experiment outputs (gitignored)
  tools/               Dev scripts
```

## Dependency Rules

- `mal-commonlib` — no internal dependencies
- `mal-core` — depends on `mal-commonlib`
- `mal-execution` — depends on `mal-core` and `mal-commonlib`
- `mal-ghana-sim` — depends on `mal-commonlib` (research package)
- `mal-data-explorer` — no internal deps (standalone scripts)

**Nothing depends on research/script packages.** When research code stabilizes, promote to `mal-core` or `mal-commonlib`.

## Naming Conventions

- Branches/PRs: `common/`, `core/`, `exec/`, `sim/`, `data/`, `docs/`
- Modules: `mal_commonlib.*`, `mal_core.*`, `mal_cli.*`, `mal_ghana_sim.*`

## Running Commands

```bash
# Sync the entire workspace
uv sync --all-packages

# Run the Ghana simulation
cd mal-ghana-sim
uv run python scripts/01_ingest.py --download
uv run python scripts/02_suitability.py
uv run python scripts/03_simulate.py
uv run python scripts/05_train.py [n_rollouts] [epochs]
uv run python scripts/06_predict_and_map.py

# Run dataset exploration
cd mal-data-explorer
uv run python 03_map_ghana.py
uv run python 12_bias_plot.py
```

## Promotion Flow

1. Experiment works in `mal-*-sim/` research package
2. Refactor stable parts into `mal-core/` or `mal-commonlib/`
3. Delete the experimental version from the research package
4. Update `mal-execution/` scripts to use the promoted modules

## Where to Put New Code

| What | Where |
|------|-------|
| Shared config, utils, data helpers | `mal-commonlib/src/mal_commonlib/` |
| Stable pipeline code | `mal-core/src/mal_core/` |
| CLI scripts, batch jobs | `mal-execution/src/mal_cli/` + `scripts/` |
| New experiment / simulation | `mal-<name>-sim/` (new package, add to workspace) |
| New dataset visualization / analysis | `mal-data-explorer/` (scripts) |
| Research papers (PDFs) | `papers/<topic>/` |
| Datasets | `data/<region>/` |
| Terrain / SRTM | `terrain/` |
| Dev tooling | `tools/` |