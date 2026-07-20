---
name: project-setup
description: Set up the MalariaSentinel project from a fresh GitHub clone. Covers uv installation, workspace sync, data restoration, environment verification, and troubleshooting. Use when starting work on this project for the first time, or when setting up on a new machine.
---

# Project Setup

Complete setup guide for MalariaSentinel. An agent with only this skill and the GitHub content can get a working development environment.

## Prerequisites

| Requirement | Check | Install |
|---|---|---|
| Python 3.12+ | `python3 --version` | macOS: `brew install python@3.12` |
| uv | `uv --version` | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Git | `git --version` | System package manager |
| CMake + Ninja (ABM engine only) | `cmake --version && ninja --version` | `brew install cmake ninja` |
| GDAL (ABM engine only) | `gdal-config --version` | `brew install gdal` |
| Eigen3, CLI11, nlohmann-json, googletest (ABM engine only) | `brew list eigen cli11 nlohmann-json googletest 2>/dev/null` | `brew install eigen cli11 nlohmann-json googletest` |
| `OPENTOPO_API_KEY` (optional) | `echo $OPENTOPO_API_KEY` | Get a free key from https://opentopography.org/ — needed for SRTM terrain layers |

The ABM engine dependencies (`mal-abm-fast`) are only needed if you plan to build and run the C++ agent-based model. The core Python pipeline works without them.

## Quick Start

```bash
git clone https://github.com/anomalyco/MalariaSentinel.git
cd MalariaSentinel
uv sync --all-packages
```

This installs all workspace packages (`mal-commonlib`, `mal-core`, `mal-execution`, `mal-ghana-sim`, `mal-data-explorer`, `mal-abm-fast`) and their Python dependencies. The first sync may take a few minutes for torch and other large wheels.

## Data Restoration

Raw datasets (~600 MB total) are gitignored. The canonical restore script re-downloads everything:

```bash
uv run --with requests --with rasterio --with matplotlib --with numpy \
    python scripts/restore_data.py
```

What it restores (in order):
1. **GBIF DwC-A datasets** → `data/<name>/occurrence.txt` (Ghana IDIT, REACT, GUF, Colombia VL)
2. **Moua et al. 2016 paper (HAL)** → `data/moua_2016.pdf`
3. **SRTM DEM tiles + map PNGs** → `terrain/srtm_maps/`, `terrain/srtm_guf/`
4. **WorldClim + JRC env layers** → `runs/layers/` (+ `runs/env_stack.npz`)

Steps 3–4 require the `OPENTOPO_API_KEY` environment variable. Without it, the script prints the exact manual commands to run.

The script is **idempotent**: files that already exist with non-trivial size are skipped.

### Restore individual datasets

Pass dataset names to restore only specific ones:

```bash
uv run --with requests python scripts/restore_data.py guf
uv run --with requests python scripts/restore_data.py react
uv run --with requests python scripts/restore_data.py ghana_idit
uv run --with requests python scripts/restore_data.py colombia_vl
```

### What is NOT restored

Model weights and result PNGs in `runs/` must be regenerated via the Ghana simulation pipeline:

```bash
uv run python mal-ghana-sim/scripts/02_suitability.py
uv run python mal-ghana-sim/scripts/03_simulate.py
uv run python mal-ghana-sim/scripts/05_train.py
uv run python mal-ghana-sim/scripts/06_predict_and_map.py
```

## Verification

Quick import check:

```bash
uv run python -c "
from mal_commonlib import config as C
from mal_ghana_sim import config as GC
import mal_core, mal_cli
import mal_data_explorer
import mal_abm_fast
print('All 6 workspace packages import OK')
print('  REPO_ROOT:', C.REPO_ROOT)
print('  DATA_DIR:', C.DATA_DIR)
print('  OCCURRENCE:', GC.OCCURRENCE)
"
```

`mal-core` contains promoted modules (aoi, cli, dataset, env, predict, registry, scenario, server, state, train, unet_wrapper, unet). `mal-execution` contains automation scripts (cesga-run, hetzner-run); its Python module is minimal.

Or use the verify script (also runs `uv sync`):

```bash
tools/verify.sh
```

Both should print `All packages import OK` and show the resolved paths.

## Running Tests

```bash
# Run all Python package tests
tools/run_all_tests.sh

# Run tests for a specific package
cd mal-ghana-sim && uv run pytest
cd mal-commonlib && uv run pytest
cd mal-core && uv run pytest

# C++ ABM engine tests (GoogleTest, requires cmake + build)
cd mal-abm-fast && ctest --test-dir build --output-on-failure
```

The `run_all_tests.sh` script iterates through each workspace package, runs `uv run pytest`, and reports which packages have tests vs. which have none yet.

## Available Dev Tools

```bash
tools/verify.sh       # Verify workspace integrity (runs uv sync + import check)
tools/run_all_tests.sh # Run all Python package tests
tools/format.sh       # Format code
```

## Troubleshooting

### UV cache corruption

If `uv sync` fails with unexpected resolver errors:

```bash
uv cache clean
uv sync --all-packages
```

### Missing `uv` after install

The installer adds uv to `~/.local/bin` (or `~/.cargo/bin`). Add to your PATH:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

### Python version mismatch

If uv picks the wrong Python:

```bash
uv python pin 3.12
uv sync --all-packages
```

### Data restore: OPENTOPO_API_KEY missing

Get a free key from https://opentopography.org/ and export it:

```bash
export OPENTOPO_API_KEY="your_key_here"
```

SRTM terrain and WorldClim/JRC env layers will fail without this key. GBIF datasets and the Moua paper restore fine without it.

### Data restore: download failures

The GBIF IPT servers sometimes rate-limit or go down. Re-run the restore script — it skips already-downloaded files:

```bash
uv run --with requests python scripts/restore_data.py
```

### Import errors after sync

Ensure you are running from the repo root and not a subdirectory:

```bash
cd /path/to/MalariaSentinel
uv run python -c "import mal_commonlib"
```

## Next Steps

Once setup is verified:

- **Run the Ghana pipeline**: see `agents/skills/ghana-pipeline/SKILL.md`
- **Explore datasets**: see `agents/skills/data-explorer/SKILL.md`
- **Build the ABM engine**: see `agents/skills/abm-engine/SKILL.md`
- **Check project conventions**: read `AGENTS.md`
