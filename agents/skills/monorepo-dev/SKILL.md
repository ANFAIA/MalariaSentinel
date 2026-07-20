---
name: monorepo-dev
description: Work with the MalariaSentinel monorepo structure. Covers package management, dependency rules, code promotion workflow, testing, and contribution guidelines. Use when adding new packages, promoting code from experiments to core, or contributing to the project.
---

# MalariaSentinel Monorepo Development Guide

## Monorepo Overview

MalariaSentinel is a **uv workspace monorepo** with 6 packages. The root `pyproject.toml` defines the workspace; individual packages declare their own dependencies and build config.

```
MalariaSentinel/
├── pyproject.toml              # Workspace root (uv)
├── mal-commonlib/              # Shared config, paths, data utilities
│   ├── pyproject.toml
│   └── src/mal_commonlib/
├── mal-core/                   # Stable pipeline logic (M3-M4 U-Net + M5 SDSS shell)
│   ├── pyproject.toml
│   └── src/mal_core/
├── mal-execution/              # CLI entrypoints, batch jobs (deprecated, use mal-core)
│   ├── pyproject.toml
│   ├── scripts/
│   └── src/
├── mal-ghana-sim/              # Ghana spread simulation + U-Net surrogate (research)
│   ├── pyproject.toml
│   ├── src/mal_ghana_sim/
│   └── tests/
├── mal-data-explorer/          # Dataset visualization, mapping, bias analysis
│   ├── pyproject.toml
│   └── *.py                    # Standalone scripts (no src layout)
├── mal-abm-fast/               # Fast C++ ABM engine (HPC production)
│   ├── pyproject.toml
│   ├── CMakeLists.txt
│   ├── src/
│   ├── include/
│   ├── tests/
│   └── slurm/
├── agents/                     # Agent loops + memory module
├── data/                       # Datasets (gitignored)
├── papers/                     # Research papers
├── terrain/                    # DEM tiles
├── runs/                       # Experiment outputs
└── tools/                      # Shared scripts (run_all_tests.sh, format.sh, verify.sh)
```

**Workspace root** (`pyproject.toml`): declares all members under `[tool.uv.workspace]`:

```toml
[tool.uv.workspace]
members = [
    "mal-commonlib",
    "mal-core",
    "mal-execution",
    "mal-ghana-sim",
    "mal-data-explorer",
    "mal-abm-fast",
]
```

## Dependency Rules

The dependency hierarchy is **strict and one-directional**. Nothing depends on research packages.

```
mal-commonlib          ← no workspace deps (foundation)
    ↑
mal-core               ← depends on mal-commonlib
    ↑
mal-execution          ← depends on mal-core + mal-commonlib (HPC/cloud automation scripts)

mal-ghana-sim          ← depends on mal-commonlib ONLY (NOT mal-core)
mal-data-explorer      ← no workspace deps (standalone scripts)
mal-abm-fast           ← no workspace deps (C++ engine)
```

**Rules:**
- `mal-commonlib` is the foundation — no internal dependencies.
- `mal-core` depends only on `mal-commonlib`.
- `mal-execution` depends on `mal-core` + `mal-commonlib`. Its Python module (`mal_cli`) is minimal, but `scripts/` contains HPC automation (CESGA SLURM, Hetzner cloud).
- `mal-ghana-sim` depends only on `mal-commonlib` — **never** on `mal-core`.
- `mal-data-explorer` and `mal-abm-fast` have no workspace dependencies.
- **Nothing depends on research packages.** Research code promotes into core; it never flows downward.

## Package Management

### Adding dependencies to a package

```bash
# Add to a specific package
cd mal-commonlib && uv add <package>
cd mal-core && uv add <package>
cd mal-ghana-sim && uv add <package>

# Sync all packages after changes
uv sync --all-packages
```

Each package that uses workspace deps declares them in `[tool.uv.sources]`:

```toml
[tool.uv.sources]
mal-commonlib = { workspace = true }
```

### Adding a new package to the workspace

```bash
# 1. Create directory structure
mkdir -p mal-new-package/src/mal_new_package
mkdir -p mal-new-package/tests

# 2. Create pyproject.toml
cat > mal-new-package/pyproject.toml << 'EOF'
[project]
name = "mal-new-package"
version = "0.1.0"
description = "New package for MalariaSentinel"
requires-python = ">=3.12"
dependencies = ["mal-commonlib"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/mal_new_package"]

[tool.uv.sources]
mal-commonlib = { workspace = true }

[dependency-groups]
dev = ["pytest>=8.0"]
EOF

# 3. Add to root workspace — edit pyproject.toml and append to members list:
#    "mal-new-package",

# 4. Sync
uv sync --all-packages
```

**Naming convention for new packages:** `mal-<topic>-sim/` (experiments) or `mal-<topic>-explorer/` (visualization). Never create packages outside the `mal-*` namespace.

## Code Promotion Workflow

Promotion moves stable, useful code from an experiment (e.g., `mal-ghana-sim`) into the core tier (`mal-core` or `mal-commonlib`). It is **one-way** (no demotion) and **explicit** (no auto-promotion).

### Steps

1. **Verify the experiment works end-to-end** on real data. Tests pass, results are reproducible.
2. **Identify stable parts** — functions, classes, modules that are not experiment-specific and would be useful in the next experiment or in the Centinela.
3. **Refactor** into the right home in `mal-core/` or `mal-commonlib/`. Add unit tests.
4. **Delete the original code** from the experiment package. Leave a one-line comment pointing to the new location.
5. **Update `mal-execution/`** scripts to use the promoted module.
6. **Sync and test**: `uv sync --all-packages && tools/run_all_tests.sh`

### Decision table: what goes where

| Stable code from experiment | Lives in |
|---|---|
| Configuration, paths, data utilities (no domain logic) | `mal-commonlib/` |
| Pipeline logic (reusable SDSS piece) | `mal-core/` |
| A CLI script that orchestrates the pipeline | `mal-execution/scripts/` or `mal-core` CLI entrypoint |
| A new schema label or domain entity | `agents/memory/runtime/config/config.yaml` (after a `Pitfall` node explains why) |

### When NOT to promote

- Code tied to the experiment's specific hypothesis (e.g., Ghana-specific terrain processing).
- Code that is exploratory (changes too fast to be "stable").
- Code that has no tests.

## Testing

### Running tests

```bash
# Run all tests across all packages
tools/run_all_tests.sh

# Run tests for a specific package
cd mal-commonlib && uv run pytest
cd mal-core && uv run pytest
cd mal-ghana-sim && uv run pytest

# C++ ABM engine (GoogleTest)
cd mal-abm-fast && ctest --test-dir build --output-on-failure
```

### Testing conventions

- **Python packages**: tests go in `tests/` at the package root (e.g., `mal-ghana-sim/tests/`) or `src/<package>/tests/` (e.g., `mal-commonlib/src/mal_commonlib/tests/`).
- **Framework**: pytest for Python. GoogleTest for C++ (`mal-abm-fast`).
- **Dev dependencies**: declared in `[dependency-groups] dev = ["pytest>=8.0"]` in each package's `pyproject.toml`.
- Every promoted module **must** have tests before it lands in `mal-core` or `mal-commonlib`.

### Quality checks

```bash
# Format code
tools/format.sh

# Verify workspace integrity
tools/verify.sh
```

## Naming Conventions

### Git branches and PRs

Use prefixes that match the package tier:

| Prefix | Package |
|---|---|
| `common/` | `mal-commonlib` |
| `core/` | `mal-core` |
| `exec/` | `mal-execution` |
| `sim/` | `mal-ghana-sim` |
| `data/` | `mal-data-explorer` |
| `docs/` | Documentation |
| `abm/` | `mal-abm-fast` |

### Python modules

| Package | Import name |
|---|---|
| `mal-commonlib` | `mal_commonlib` |
| `mal-core` | `mal_core` |
| `mal-execution` | (scripts only, no importable module) |
| `mal-ghana-sim` | `mal_ghana_sim` |
| `mal-data-explorer` | (standalone scripts, no importable module) |
| `mal-abm-fast` | (C++ engine, no Python module) |

### New experiments

Follow the pattern: `mal-<topic>-sim/` or `mal-<topic>-explorer/`.

## Current Package Contents

### mal-commonlib
Shared config, paths, data utilities. Modules: `config`, `aoi`, `data/`, `terrain/`.

### mal-core
Stable pipeline logic (promoted from experiments). Modules: `aoi`, `cli`, `dataset`, `env`, `predict`, `registry`, `scenario`, `server`, `state`, `train`, `unet_wrapper`, `unet`. Entry point: `malariasim` CLI.

### mal-execution
HPC and cloud automation. Python module is minimal (`mal_cli/__init__.py`). Key content:
- `scripts/cesga-run/` — CESGA SLURM automation (setup_env.sh, prepare_data.sh, run_abm.sh, manage_jobs.sh, cesga_config.sh)
- `scripts/hetzner-run/` — Hetzner cloud automation (cloud-init.yaml, lib/, tests/)
- `scripts/train_unet.py`, `train_unet_subsample.py`, `validate_unet.py` — training scripts

### mal-ghana-sim
Ghana spread simulation + U-Net surrogate. Modules: `config`, `dataset`, `ingest`, `predict`, `simulator`, `suitability`, `train`, `unet`, `viz`, `abm/` (agent-based model).

### mal-data-explorer
Standalone visualization scripts (01-12). No src layout, no importable module.

### mal-abm-fast
C++ agent-based model engine. Built with CMake. 12 source files, 11 GoogleTest suites (60 tests). CLI via CLI11.

## Contribution Guidelines

### Adding a new feature

1. Determine the right package using the dependency rules and decision table.
2. Create a branch with the appropriate prefix (e.g., `core/add-unet-predict`).
3. Implement in the chosen package. Add tests.
4. Run `tools/run_all_tests.sh` and `tools/format.sh`.
5. Open a PR referencing the relevant milestone/issue.

### Fixing bugs

1. Write a failing test that reproduces the bug (if practical).
2. Fix the bug in the appropriate package.
3. Verify the test passes.
4. Run the full test suite.

### Promoting code from experiment to core

Follow the "Code Promotion Workflow" section above. The key steps are: verify, identify, refactor, test, delete original, update consumers.

### Adding a new package

Follow the "Adding a new package to the workspace" section. Ensure:
- It follows the `mal-*` naming convention.
- It declares workspace deps via `[tool.uv.sources]`.
- It has at least a basic test.
- It is added to the root `pyproject.toml` workspace members.

## Troubleshooting

### `uv sync` fails with unresolved dependency

Check that the package is listed in the root `pyproject.toml` `[tool.uv.workspace]` members. Ensure `[tool.uv.sources]` declares workspace deps correctly:

```toml
[tool.uv.sources]
mal-commonlib = { workspace = true }
```

### Import errors after adding a new package

Run `uv sync --all-packages` from the repo root. Verify the package's `pyproject.toml` has the correct `[tool.hatch.build.targets.wheel]` paths.

### Tests fail with `ModuleNotFoundError`

Ensure you are running tests with `uv run pytest` (not bare `pytest`), so the workspace venv is active.

### C++ build fails (`mal-abm-fast`)

Ensure CMake and a C++17 compiler are available. Check `mal-abm-fast/CMakeLists.txt` for required dependencies (vcpkg).

### Promotion broke an experiment

If promoting code out of an experiment breaks it, the experiment was depending on implementation details rather than a stable interface. Revert the promotion, define a stable interface in the experiment first, then promote the interface + implementation together.

### `tools/run_all_tests.sh` skips a package

The script uses `2>/dev/null || echo "  no tests"` — a package with no tests is silently skipped. This is expected. If the package should have tests, add them.
