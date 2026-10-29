<!-- Protected file. Edits go through gitagent; user approves each change. -->

# MalariaSentinel — Agent Guide

## What this project is

**MalariaSentinel is a malaria Sentinel / Decision Support System (SDSS) for malaria elimination.** It is the "Centinela" — a framework that ingests spatial and epidemiological data, models transmission risk, and surfaces actionable insights to support elimination programmes in target regions.

**The reference framework is the SDSS for malaria elimination proposed by Kelly et al. (2012)** — see `papers/spatial-analysis/MalariaEliminationWithSpatialDecisionSupportSystems.md`. That paper argues for a spatial decision support framework that integrates surveillance, targeted interventions, and service delivery in endemic settings. The Centinela is the engineering realisation of that framework, parameterised for specific regions (Ghana being the first working case).

- **Stack**: Python (uv workspace).
- **Layout**: monorepo with 5 packages (see "Monorepo layout" below).
- **Runtime**: OpenCode is the agent harness. Configuration lives in `opencode.json` at the project root.

## How to build, test, run

```bash
# Sync the workspace
uv sync --all-packages

# Run the Ghana simulation (via mal-core CLI)
malariasim download --aoi ghana --datasets era5 --outputs wind_6hourly --years 2024,2025
malariasim ingest --aoi ghana --year 2024 --month 6
malariasim abm --aoi ghana --days 30
malariasim score --run-dir runs/abm --tier fast
malariasim train --run-dir runs/abm --epochs 50
malariasim predict --aoi ghana --year 2026

# Run dataset exploration
cd mal-data-explorer
uv run python 03_map_ghana.py
uv run python 12_bias_plot.py

# Download data for an AOI
malariasim download --aoi ghana --datasets era5 --outputs wind_6hourly --years 2024,2025

# Validate data completeness
uv run python -c "from mal_core.download.manifest import validate_completeness; print(validate_completeness('ghana'))"

# Run the calibration scorers (Phase 1+2: 10 scorers + LLM verdict)
cd mal-core/src/mal_core/abm/tests/calibration
uv run pytest -m fast -v          # 10 scorers, 1 seed, 30 days (PR gate)
uv run pytest -m full -v          # 10 scorers + LLM, 5 seeds, 90 days
```

## Monorepo layout

| Package | Role | Internal deps |
|---|---|---|
| `mal-commonlib/` | Shared config, paths, data utilities. | — |
| `mal-core/` | Stable pipeline logic (promoted from research). | commonlib |
| `mal-execution/` | CLI entrypoints, batch jobs. | core + commonlib |
| `mal-ghana-sim/` | Ghana spread simulation + U-Net surrogate (research). | commonlib |
| `mal-data-explorer/` | Dataset visualisation, mapping, bias analysis. | — |
| `agents/` | Agent loops and infrastructure. Not a runtime — OpenCode is. | — |
| `data/`, `papers/`, `terrain/`, `runs/` | Datasets, papers, DEM tiles, experiment outputs (mostly gitignored). | — |

**Dependency rule**: nothing depends on research/script packages. When research code stabilises, promote to `mal-core` or `mal-commonlib` and update `mal-execution` scripts to use the promoted modules.

**Naming**: branches/PRs use `common/`, `core/`, `exec/`, `sim/`, `data/`, `docs/`. Python modules use `mal_commonlib.*`, `mal_core.*`, `mal_cli.*`, `mal_ghana_sim.*`.

## Experiments vs core

The monorepo separates **production code** (the Centinela) from **experiments** (proof-of-concept work that informs the Centinela's design). This separation is structural, not aspirational — promotion is one-way and explicit.

| Tier | Packages | Purpose | Promotion? |
|---|---|---|---|
| **Core (the Centinela)** | `mal-commonlib/`, `mal-core/`, `mal-execution/` | Stable, reusable code that makes up the SDSS. `mal-core` is empty at the start of the project and is populated by promoting stable parts from experiments. `mal-execution` holds CLI scripts that call into `mal-core` and `mal-commonlib`. | Receives code from experiments. |
| **Experiments** | `mal-ghana-sim/`, `mal-data-explorer/` | Hypothesis-driven, replaceable work that explores one approach to one piece of the SDSS. `mal-ghana-sim` is a Ghana spread simulation + U-Net surrogate. `mal-data-explorer` is a dataset visualisation + bias-analysis sandbox. Both depend on `mal-commonlib` but NOT on each other and NOT on `mal-core`. | Each experiment either dies (gets archived) or **promotes** parts of itself into `mal-core` or `mal-commonlib` (see "Promotion flow" below). |
| **Infrastructure** | `agents/`, `data/`, `papers/`, `terrain/`, `runs/` | Not part of the Centinela's runtime. The agent infrastructure (`agents/`), input data, research papers, terrain, and experiment outputs. | Never promoted. |

**The `mal-core` directory is the goal of the project.** Every stable function in the Centinela should eventually live there or in `mal-commonlib`. Experiments exist to discover what should go into core, and to be deleted once their insight has been promoted.

**Naming tells you which tier a package is in**:
- `mal-core`, `mal-commonlib`, `mal-execution` → core tier.
- `mal-<topic>-sim`, `mal-<topic>-explorer` → experiment tier. New experiments follow this pattern.

## Promotion flow

Promotion moves stable, useful code from an experiment into the core tier. It is one-way (no demotion) and explicit (no auto-promotion).

1. **Verify the experiment works end-to-end** on real data. Tests pass, results are reproducible.
2. **Identify the stable parts** — functions, classes, modules that are not specific to the experiment's hypothesis and would be useful in the next experiment or in the Centinela.
3. **Refactor** those parts into the right home in `mal-core/` or `mal-commonlib/`. Add unit tests. Update any `pyproject.toml` deps.
4. **Delete the original code** from the experiment package. Leave a one-line comment pointing to the new location.
5. **Update `mal-execution/`** scripts to use the promoted module. The experiment may keep a thin wrapper for its own use, but the canonical implementation lives in core.

**Decision table: what goes where when promoting?**

| Stable code from experiment | Lives in |
|---|---|
| Configuration, paths, data utilities (no domain logic) | `mal-commonlib/` |
| Pipeline logic (a complete, reusable piece of the Centinela) | `mal-core/` |
| A CLI script that orchestrates the pipeline | `mal-execution/scripts/` |

**When NOT to promote**: code that is tied to the experiment's specific hypothesis (e.g., Ghana-specific terrain processing that won't generalise to another region), code that is exploratory (changes too fast to be "stable"), code that has no tests.

## Important tools (use these)

| Tool | Use it for | Notes |
|---|---|---|
| `webfetch` | Reading a URL the user points to or that you find. | Returns markdown by default. Prefer this over re-fetching source for web content. |
| `websearch` | Finding current information outside the repo. | Default web search; Exa backend is optional (`OPENCODE_ENABLE_EXA=1`). |
| `bash` | Running shell commands. **Git lives here.** | `git ps` for force-with-lease pushes. `git diff`, `git log`, `git status` are safe. |
| `read`, `write`, `edit` | File I/O. | `edit` and `write` are `ask` on protected files (see below). |
| `glob`, `grep` | Finding files and content. | glob for paths, grep for content. |
| `task` | Delegating to specialised loops and subagents. Subagents get a brief, not the full conversation. **Multiple `task` calls in one message run in parallel** — use this to fan out independent subtasks. | Subagents get a brief, not the full conversation. |
| `skill` | Loading a specialised skill on demand. | Skills live in `agents/skills/`. |
| `todowrite` | Tracking multi-step work. | One list; exactly one item `in_progress` at a time. |
| `question` | Asking the user when you need a decision. | Don't guess on irreversible choices. |
| `mcp__gitagent__*` | **gawt v0.5.0 MCP** — multi-agent git isolation: sessions, agents, intents, file edits, inbox messaging. | Replaces the old gitagent CLI. Use `start_session` → `register_agent` → `edit_file`/`write_file`/`read_file` → `finalize_session`. Supervisor orchestrates; subagents use `edit_file`/`write_file` in their registered agent context. |

## Protected files (opencode-native `permission.edit: "ask"`)

| Path | Why |
|---|---|
| `AGENTS.md` | This file — the agent's own instructions. |
| `.gitignore` | Affects git tracking. |
| `opencode.json` | Project-wide permissions and agent config. |
| `data/` | Datasets. Prevents accidental edits. |

**Rules**:
- Every edit to a protected path is a real question. The user approves or denies. If denied, stop.
- Don't retry with a different phrasing. Don't batch the change with another edit. Don't delegate the edit to a subagent to bypass the prompt.
- Adding a new protected file = edit `opencode.json` and add `"<path>": "ask"` under `permission.edit`.

## gawt MCP — which tool, when

| Path | Use |
|---|---|
| `mcp__gitagent__start_session` | Start a gawt session for a feature. Creates a global worktree. |
| `mcp__gitagent__register_agent` | Register a subagent in the current session. Returns `agent_id`. |
| `mcp__gitagent__edit_file` / `write_file` / `read_file` / `delete_file` | File edits within an agent's isolated worktree. |
| `mcp__gitagent__start_intent` / `repurpose` | Track what an agent is working on (semantic intent). |
| `mcp__gitagent__send_message` / `check_inbox` | Inter-agent messaging within a session. |
| `mcp__gitagent__finalize_session` | Commit all accepted work onto the target branch. |

## Where knowledge lives

| What | Where |
|---|---|
| Procedural how-to (build, test, push, conventions) | This file (`AGENTS.md`). |
| Project-specific durable facts | GitHub issues, milestones, and PR descriptions. |
| Session working notes and summaries | The session's own context (auto-compacted by OpenCode). |

## Decision table: where does this go?

| If you want to… | Do this | Not this |
|---|---|---|
| Add a stable helper (reusable, no domain) | Put it in `mal-commonlib/`. | Don't put it in `mal-ghana-sim/` (experiment) or `mal-core/` if it's not stable yet. |
| Add a CLI script | Put it in `mal-execution/scripts/`. | Don't put a batch job in `mal-core/` (core is library, not scripts). |
| Run a Ghana-specific experiment | Put it in `mal-ghana-sim/` (experiment tier). | Don't run it inline in `mal-execution/`; that tier is for production. |
| Run a dataset visualisation / bias analysis | Put it in `mal-data-explorer/`. | Don't put it in `mal-core/`; that's for reusable pipeline logic. |
| Promote stable code from an experiment to core | Follow the "Promotion flow" above. | Don't copy-and-tweak — refactor + tests + delete the original. |
| Ask a one-off question | Use the `question` tool. | Don't guess on irreversible choices. |
| Delegate a multi-step task | Use `task` with a `subagent_type`. | Don't do it in this context if the work needs a fresh window. |
| Execute N independent subtasks | Run them in one message: parallel `task` calls + parallel read/grep. | Don't serialise them across N turns. |
| Edit a protected file | Ask the user (the `ask` prompt is the mechanism). | Don't try to bypass the `ask` prompt via delegation. |
| Push to remote after a rewrite | `git ps origin main` (force-with-lease). | Don't use `git push --force`. |

## Data format conventions

The manifest (`data/<aoi>/manifest.json`) is the **single source of truth** for an AOI's data inventory. Full spec: `docs/specs/data/spec.md`.

**Standard naming**:
- Time-series: `<aoi>_<product>_<year>.<ext>` (one file per year)
- Static: `<aoi>_<product>.<ext>` (one file per AOI)

**DOWNLOADER dict**: every loader module exports a `DOWNLOADER` dict with `name`, `outputs` (callable map), and `manifest_keys` (output→manifest key map). See `docs/specs/download/spec.md`.

**Load-or-download API**: public functions (`load_<dataset>_<product>`) check manifest → load if exists → download+register if missing. Never hardcode paths; resolve from manifest.

**ABM manifest mode**: `run_abm_from_manifest()` reads manifest, validates completeness, resolves paths, calls C++ binary. Run `malariasim abm --aoi <aoi>` directly (CLI subcommand per stage).

**Adding a new dataset**: create loader module with `DOWNLOADER` dict → register in `registry.py` → run `malariasim download` → mark `required_for_abm` if ABM needs it. See `docs/specs/data/spec.md` §6.3.

## Calibration framework conventions

When adding a new biological feature (gonotrophic cycle, host-seeking,
reproduction, etc.) that affects adult survival, EIP, or population
dynamics:

1. **Check if an existing scorer covers the new feature.** If not,
   create a new scorer in `mal-core/src/mal_core/abm/tests/calibration/scorers/`.
2. **Register the scorer** in `thresholds.yaml` with `min_score`,
   `max_delta`, and `hard_floor`.
3. **Add the scorer to the composite** by adding its weight to
   `scorers/composite.py::DEFAULT_WEIGHTS`.
4. **Run the calibration tests** before proposing:
   `cd mal-core/src/mal_core/abm/tests/calibration && uv run pytest -m fast -v`
5. **The diff report** shows if the new feature improved or regressed
   the composite vs the previous run AND vs the best historical run.

Scorer naming: `D<id>_<name>.py` where `<id>` is the next number (D17, D18, ...).
The composite handles variable dimensions automatically via the geometric mean.

Delta comparison: every scorecard is compared against both the **previous run**
(immediate delta) and the **best historical run** (all-time best composite).
This prevents losing sight of the all-time best when iterating.

## Context architecture

| Layer | Owner | Lives in |
|---|---|---|
| Operational | OpenCode (this primary agent) | The current session's context window. |
| Compaction | OpenCode (built-in) | Auto-summarised when the operational layer grows. |

**Discipline**: keep the operational layer compact — objective, plan, key decisions, references (paths, commit IDs, proposal IDs). Never paste multi-thousand-line tool outputs into the supervisor's prompt. Long outputs go to a summary.

**Subagents** see a brief, not the full conversation. If they need more context, they ask the supervisor.

## Git push workflow

When local history was rewritten (`reset`, `rebase`, `amend`), a plain `git push` refuses with "non-fast-forward". Use `git ps` — a global alias for `push --force-with-lease`:

```bash
git config --global alias.ps "push --force-with-lease"
```

| Command | Behaviour |
|---|---|
| `git push origin main` | Default: refuses if `origin/main` is not an ancestor of `HEAD`. Safe. |
| `git ps origin main` | Force-pushes `HEAD`, but **aborts** if the remote ref moved since the last fetch. |
| `git push --force origin main` | Unconditional clobber. **Do not use.** |

Pre-push sanity check:

```bash
git fetch origin
git log --oneline origin/main..HEAD   # commits you have that the remote does not
git log --oneline HEAD..origin/main   # commits the remote has that you do not
git merge-base HEAD origin/main       # divergence point, if any
```

## Session lifecycle

**End** (non-trivial sessions only):
1. Edit `AGENTS.md` if a new convention emerged (requires user approval — protected file).

**Skip the contract for trivial sessions** (single tool call, no state change).

## Milestones and kanban (M* system)

The project follows numbered milestones (**M1**, **M2**, …). Each milestone is a named deliverable (e.g. "ABM scaffolding", "U-Net training", "End-to-end run"). Milestones are tracked as GitHub milestones; this file only describes the format and the workflow.

**Milestone shape** (what every milestone looks like):
- A numbered identifier (`M<n>`), a short deliverable name, and an acceptance threshold (model metric, run time, artifact output).
- A list of granular issues in GitHub, each with the milestone label (`M<n>`) and a type label (`enhancement`, `investigation`).
- A `blocked` label on any issue gated by an external dependency.
- The GitHub milestone has the same name and due date.

### Issue <-> board <-> agent workflow

Every milestone decomposes into issues tracked on the **MalariaSentinel GitHub Project v2 kanban** (ANFAIA #11). The board has three status columns:

| Column | Meaning |
|---|---|
| **Todo** | Issue is scoped but not yet in progress |
| **In Progress** | Exactly one issue at a time; the active task the agent is working on |
| **Done** | Completed, verified, closed |

**Labels on every issue**: the milestone (`M1`...`M6`), the type (`enhancement`, `investigation`), and `blocked` if an external dependency is unresolved.

### How the agent manages the board

The agent (supervisor) is responsible for keeping the board in sync with the session's work:

1. **Entering a milestone**: read the open issues for the milestone from GitHub. Move the highest-priority unblocked issue to **In Progress**.
2. **Working on an issue**: keep it in **In Progress** until all acceptance criteria pass. If a new blocker is discovered, add the `blocked` label, post a comment with the reason, and move to **Todo**.
3. **Completing an issue**: run the acceptance criteria (tests pass, lint clean). Close the issue with a comment referencing the commit SHA. Move it to **Done**.
4. **New work emerging mid-session**: create the issue in Todo with the right milestone/labels. Do not derail the current In Progress item — finish it first.
5. **End of milestone**: close the GitHub milestone (which auto-closes remaining issues or moves them to the next milestone). Write a summary comment on the last issue.

**Discipline**: exactly one issue In Progress at a time. Never batch closes. Always reference the commit SHA in the closing comment so the board is traceable.

## Specialised loops

Invoke with `@<name>` or the `task` tool. Each subagent's prompt lives at `agents/loops/<name>.md`. Brief summary:

| Agent | Role | Auto-invoked by supervisor? |
|---|---|---|
| `test-fixer` | Iterate a check command until it exits 0. | `allow` |
| `code-reviewer` | Review a diff; return structured findings. Read-only. | `ask` |
| `doc-researcher` | Research documentation and code; returns a brief with sources. | `ask` |
| `security-auditor` | OWASP-style audit. Read-only. | `ask` |

The supervisor is the default primary agent (`default_agent: "supervisor"` in `opencode.json`). It owns the running context, decomposes work, delegates to loops and subagents, and integrates via the gawt MCP (`mcp__gitagent__*`) for isolated multi-agent edits. The supervisor's prompt (`.opencode/agents/supervisor.md`) is generic and reusable; project rules live here in `AGENTS.md`. Tab cycles between `supervisor` (default), `build` (single-tool ad-hoc), and `plan` (read-only review).
