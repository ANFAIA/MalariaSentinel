---
name: agent-onboarding
description: "Complete onboarding guide for new agents starting from scratch on MalariaSentinel. Covers the full path from GitHub clone to expert operation: project setup, understanding the monorepo, running pipelines, using subagents, and contributing. Load this skill FIRST when you land in this project for the first time."
---

# Agent Onboarding

Single entry point for any agent starting from scratch on MalariaSentinel. Follow the steps in order — each builds on the previous. Estimated total time: ~25 minutes for full onboarding, or skip ahead using the Quick Reference Card.

## Quick Reference Card

| I need to... | Skill to load |
|---|---|
| Set up the project | `project-setup` |
| Understand the domain | `sdss-reference` |
| Run Ghana simulation | `ghana-pipeline` |
| Run ABM simulations | `abm-engine` |
| Validate ABM output | `abm-engine` (`malariasim score --run-dir <dir>`) |
| Explore datasets | `data-explorer` |
| Deploy to HPC | `cesga` |
| Use shared utilities | `mal-commonlib-api` |
| Use core API | `mal-core-api` |
| Work across packages | `monorepo-dev` |
| Use subagents/loops | `subagents-loops` |
| Run CLI commands | `mal-execution-api` |
| Onboard from scratch | `agent-onboarding` (this skill) |

## Step 1: Project Setup (~5 min)

Clone the repo and sync the uv workspace:

```bash
git clone https://github.com/anomalyco/MalariaSentinel.git
cd MalariaSentinel
uv sync --all-packages
```

Restore the ~600 MB of gitignored datasets:

```bash
uv run --with requests --with rasterio --with matplotlib --with numpy \
    python scripts/restore_data.py
```

Verify the environment:

```bash
python -c "import mal_commonlib; import mal_core; import mal_cli; print('OK')"
```

Or use the full verification script:

```bash
bash tools/verify.sh
```

**Full details**: load the `project-setup` skill for prerequisites (Python 3.12+, uv, CMake/Ninja for ABM, GDAL), troubleshooting, and data source documentation.

## Step 2: Session Start (~2 min)

Every session begins by orienting on the project state:

1. Read `AGENTS.md` at the repo root — conventions, decision tables, protected files.
2. Check the kanban (GitHub Projects): exactly one issue In Progress; pick the highest-priority unblocked issue if none is active.
3. Read the issue's acceptance criteria before touching code.

Durability across sessions comes from GitHub (issues, milestones, and PR descriptions) — not from any local memory service.

## Step 3: Understand the Project (~10 min)

Read `AGENTS.md` at the repo root — it contains the project's rules, the monorepo layout, the promotion flow, and the decision tables.

Then load these skills for deeper context:

| Skill | What it covers |
|---|---|
| `sdss-reference` | Kelly 2012 SDSS framework — the domain theory behind the Centinela |
| `monorepo-dev` | 5-package layout, dependency rules, experiment vs core tiers, promotion flow |
| `mal-commonlib-api` | Shared config, paths, data utilities |
| `mal-core-api` | Stable mal-core API |

**Key insight**: MalariaSentinel has two tiers — **core** (the Centinela: `mal-commonlib`, `mal-core`, `mal-execution`) and **experiments** (`mal-data-explorer`). Experiments either die or promote stable code into core. Nothing depends on experiments.

## Step 4: Run Something (~5 min)

Get a working pipeline run under your belt.

**Ghana simulation** (ABM pipeline, no GPU needed):

```bash
uv run malariasim ingest --aoi ghana --year 2024 --month 6
uv run malariasim abm --aoi ghana --days 30
```

**Or dataset exploration**:

```bash
cd mal-data-explorer
uv run python 03_map_ghana.py
```

**Full details**: load `ghana-pipeline` for the 6-stage pipeline (ingest → suitability → simulate → train → predict → map) or `data-explorer` for the 20+ visualization and bias-analysis scripts.

## Step 5: Use Subagents (when needed)

The supervisor agent delegates to specialised loops via the `task` tool. Available loops:

| Agent | Role |
|---|---|
| `test-fixer` | Iterate a check command until it passes |
| `code-reviewer` | Structured diff review (read-only) |
| `doc-researcher` | Research from repo and web; returns a sourced brief |
| `security-auditor` | OWASP-style audit (read-only) |

For multi-agent isolated edits (multiple features in parallel), use the `gitagent` skill — it spawns worktrees per agent, collects proposals as patches, and integrates one clean commit.

**Parallelism rule**: the supervisor parallelises by default. N independent `task` calls in one message run concurrently. Serialise only when B depends on A's output.

**Full details**: load `subagents-loops` for loop selection and the `gitagent` skill for the propose/worktree workflow.

## Step 6: Contribute

Branch naming conventions:

| Prefix | Scope |
|---|---|
| `common/` | `mal-commonlib` changes |
| `core/` | `mal-core` changes |
| `exec/` | `mal-execution` changes |
| `data/` | `mal-data-explorer` changes |
| `docs/` | Documentation only |

**Promotion flow** (experiment → core):

1. Verify the experiment works end-to-end on real data.
2. Identify stable parts (not hypothesis-specific, reusable).
3. Refactor into `mal-core/` or `mal-commonlib/`. Add tests.
4. Delete the original from the experiment. Leave a pointer comment.
5. Update `mal-execution/` scripts to use the promoted module.

**Decision table**: config/paths → `mal-commonlib`, pipeline logic → `mal-core`, CLI scripts → `mal-execution/scripts`.

**Full details**: load `monorepo-dev` for the full contribution guide and the promotion decision table.

## Step 7: Deploy to HPC (optional)

For large-scale simulations on CESGA's HPC cluster:

- Load the `cesga` skill for SLURM job scripts, module loading, data transfer, and multi-node GPU training.

## End of Session

When wrapping up a non-trivial session:

1. Edit `AGENTS.md` if a new convention emerged.

Skip the contract for trivial sessions (single tool call, no state change).
