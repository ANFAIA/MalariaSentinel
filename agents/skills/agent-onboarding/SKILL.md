---
name: agent-onboarding
description: Complete onboarding guide for new agents starting from scratch on MalariaSentinel. Covers the full path from GitHub clone to expert operation: project setup, memory module initialization, understanding the monorepo, running pipelines, using subagents, and contributing. Load this skill FIRST when you land in this project for the first time.
---

# Agent Onboarding

Single entry point for any agent starting from scratch on MalariaSentinel. Follow the steps in order — each builds on the previous. Estimated total time: ~35 minutes for full onboarding, or skip ahead using the Quick Reference Card.

## Quick Reference Card

| I need to... | Skill to load |
|---|---|
| Set up the project | `project-setup` |
| Start a session | `agent-ops` |
| Understand the domain | `sdss-reference` |
| Run Ghana simulation | `ghana-pipeline` |
| Run ABM simulations | `abm-engine` |
| Validate ABM output | `calibration-framework` |
| Explore datasets | `data-explorer` |
| Use the knowledge graph | `project-memory` |
| Deploy to HPC | `cesga` |
| Use shared utilities | `mal-commonlib-api` |
| Use core pipeline | `mal-core-api` |
| Work across packages | `monorepo-dev` |
| Set up memory module | `project-memory` (install section) |

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
python -c "import mal_commonlib; import mal_core; import mal_ghana_sim; print('OK')"
```

Or use the full verification script:

```bash
bash tools/verify.sh
```

**Full details**: load the `project-setup` skill for prerequisites (Python 3.12+, uv, CMake/Ninja for ABM, GDAL), troubleshooting, and data source documentation.

## Step 2: Memory Module Setup (~10 min)

The knowledge graph (Neo4j + Graphiti MCP) gives the agent persistent project memory across sessions. Docker must be running.

```bash
# Install the memory module (interactive — asks for project slug, Neo4j password, OpenAI key)
bash agents/memory/install.sh

# Cold-start: seed the graph with bootstrap entries
make -f agents/memory/scripts/Makefile bootstrap

# Verify everything is healthy
make -f agents/memory/scripts/Makefile status
make -f agents/memory/scripts/Makefile audit
```

If `audit` reports violations (orphan rels, unlabeled nodes, out-of-schema labels), fix them before proceeding — see the `project-memory` skill for the schema and invariant details.

**Troubleshooting**: load the `project-memory` skill. It covers the 8-label schema (`Component`, `Investigation`, `Architecture`, `Pattern`, `Pitfall`, `Tool`, `Operational`, `Preference`), the three invariants, and the session lifecycle contract.

## Step 3: Session Start (~2 min)

Every session begins with a memory recall to load prior context:

```bash
make -f agents/memory/scripts/Makefile session-start
```

This runs the audit, then surfaces open investigations, active pitfalls, architecture decisions, components, and operational patterns. Pick one open investigation to advance.

**Full details**: load the `agent-ops` skill for the complete session lifecycle (start, parallel execution, end-of-session writes), the kanban workflow, and the "exactly one issue In Progress" discipline.

## Step 4: Understand the Project (~10 min)

Read `AGENTS.md` at the repo root — it contains the project's rules, the monorepo layout, the promotion flow, and the decision tables.

Then load these skills for deeper context:

| Skill | What it covers |
|---|---|
| `sdss-reference` | Kelly 2012 SDSS framework — the domain theory behind the Centinela |
| `monorepo-dev` | 6-package layout, dependency rules, experiment vs core tiers, promotion flow |
| `mal-commonlib-api` | Shared config, paths, data utilities |
| `mal-core-api` | Stable pipeline logic API |

**Key insight**: MalariaSentinel has two tiers — **core** (the Centinela: `mal-commonlib`, `mal-core`, `mal-execution`) and **experiments** (`mal-ghana-sim`, `mal-data-explorer`, `mal-abm-fast`). Experiments either die or promote stable code into core. Nothing depends on experiments.

## Step 5: Run Something (~5 min)

Get a working pipeline run under your belt.

**Ghana simulation** (stages 1–3, no GPU needed):

```bash
cd mal-ghana-sim
uv run python scripts/01_ingest.py --download
uv run python scripts/02_suitability.py
uv run python scripts/03_simulate.py
```

**Or dataset exploration**:

```bash
cd mal-data-explorer
uv run python 03_map_ghana.py
```

**Full details**: load `ghana-pipeline` for the 6-stage pipeline (ingest → suitability → simulate → train → predict → map) or `data-explorer` for the 20+ visualization and bias-analysis scripts.

## Step 6: Use Subagents (when needed)

The supervisor agent delegates to specialised loops via the `task` tool. Available loops:

| Agent | Role |
|---|---|
| `test-fixer` | Iterate a check command until it passes |
| `code-reviewer` | Structured diff review (read-only) |
| `doc-researcher` | Query knowledge graph first, web as fallback |
| `security-auditor` | OWASP-style audit (read-only) |

For multi-agent isolated edits (multiple features in parallel), use the `gitagent` skill — it spawns worktrees per agent, collects proposals as patches, and integrates one clean commit.

**Parallelism rule**: the supervisor parallelises by default. N independent `task` calls in one message run concurrently. Serialise only when B depends on A's output.

**Full details**: load `agent-ops` for parallel execution patterns and the `gitagent` skill for the propose/worktree workflow.

## Step 7: Contribute

Branch naming conventions:

| Prefix | Scope |
|---|---|
| `common/` | `mal-commonlib` changes |
| `core/` | `mal-core` changes |
| `exec/` | `mal-execution` changes |
| `sim/` | `mal-ghana-sim` changes |
| `data/` | `mal-data-explorer` changes |
| `docs/` | Documentation only |
| `abm/` | `mal-abm-fast` changes |

**Promotion flow** (experiment → core):

1. Verify the experiment works end-to-end on real data.
2. Identify stable parts (not hypothesis-specific, reusable).
3. Refactor into `mal-core/` or `mal-commonlib/`. Add tests.
4. Delete the original from the experiment. Leave a pointer comment.
5. Update `mal-execution/` scripts to use the promoted module.

**Decision table**: config/paths → `mal-commonlib`, pipeline logic → `mal-core`, CLI scripts → `mal-execution/scripts`, domain entities → knowledge graph.

**Full details**: load `monorepo-dev` for the full contribution guide and the promotion decision table.

## Step 8: Deploy to HPC (optional)

For large-scale simulations on CESGA's HPC cluster:

- Load the `cesga` skill for SLURM job scripts, module loading, data transfer, and multi-node GPU training.

## End of Session

When wrapping up a non-trivial session:

1. Update affected `Investigation` nodes (status + evidence).
2. Add newly-discovered typed nodes (patterns, pitfalls, components).
3. Write a free-form session episode via `mcp__graphiti-memory__add_memory` with `source: "text"`.
4. Edit `AGENTS.md` if a new convention emerged.
5. Run `make -f agents/memory/scripts/Makefile audit` to re-verify.

Skip the contract for trivial sessions (single tool call, no state change).
