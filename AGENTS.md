<!-- Protected file. Edits go through gitagent; user approves each change. -->

# MalariaSentinel — Agent Guide

## What this project is

MalariaSentinel: a malaria Sentinel / Decision Support System (SDSS).
Uses spread simulations, U-Net surrogates, and dataset visualisation
to model and predict malaria risk in target regions.

- **Stack**: Python (uv workspace), Neo4j + Graphiti MCP for the knowledge graph.
- **Layout**: monorepo with 5 packages plus `agents/`, `data/`, `papers/`, `terrain/`, `runs/`.
- **Runtime**: OpenCode is the agent harness. Configuration lives in `opencode.json` at the project root.

## How to build, test, run

```bash
# Sync the workspace
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

# Operate the project memory subsystem
make -f agents/memory/scripts/Makefile status
make -f agents/memory/scripts/Makefile audit
make -f agents/memory/scripts/Makefile seed
make -f agents/memory/scripts/Makefile session-start
make -f agents/memory/scripts/Makefile session-end
```

## Monorepo layout

| Package | Role | Internal deps |
|---|---|---|
| `mal-commonlib/` | Shared config, paths, data utilities. | — |
| `mal-core/` | Stable pipeline logic (promoted from research). | commonlib |
| `mal-execution/` | CLI entrypoints, batch jobs. | core + commonlib |
| `mal-ghana-sim/` | Ghana spread simulation + U-Net surrogate (research). | commonlib |
| `mal-data-explorer/` | Dataset visualisation, mapping, bias analysis. | — |
| `agents/` | Loops + installable memory module. Not a runtime — OpenCode is. | — |
| `data/`, `papers/`, `terrain/`, `runs/` | Datasets, papers, DEM tiles, experiment outputs (mostly gitignored). | — |

**Dependency rule**: nothing depends on research/script packages. When research code stabilises, promote to `mal-core` or `mal-commonlib` and update `mal-execution` scripts to use the promoted modules.

**Naming**: branches/PRs use `common/`, `core/`, `exec/`, `sim/`, `data/`, `docs/`. Python modules use `mal_commonlib.*`, `mal_core.*`, `mal_cli.*`, `mal_ghana_sim.*`.

## Important tools (use these)

| Tool | Use it for | Notes |
|---|---|---|
| `webfetch` | Reading a URL the user points to or that you find. | Returns markdown by default. Prefer this over re-fetching source for web content. |
| `websearch` | Finding current information outside the repo. | Default web search; Exa backend is optional (`OPENCODE_ENABLE_EXA=1`). |
| `bash` | Running shell commands. **Git lives here.** | `git ps` for force-with-lease pushes. `git diff`, `git log`, `git status` are safe. |
| `read`, `write`, `edit` | File I/O. | `edit` and `write` are `ask` on protected files (see below). |
| `glob`, `grep` | Finding files and content. | glob for paths, grep for content. |
| `task` | Delegating to specialised loops and subagents. | Subagents get a brief, not the full conversation. |
| `skill` | Loading a specialised skill on demand. | E.g. `project-memory` for the knowledge graph manual. |
| `todowrite` | Tracking multi-step work. | One list; exactly one item `in_progress` at a time. |
| `question` | Asking the user when you need a decision. | Don't guess on irreversible choices. |
| `memory_node`, `memory_rel`, `memory_query`, `memory_audit`, `memory_status`, `memory_seed` | Knowledge graph reads and writes. | All validate labels against the schema before any write. |

## Protected files (opencode-native `permission.edit: "ask"`)

| Path | Why |
|---|---|
| `AGENTS.md` | This file — the agent's own instructions. |
| `.gitignore` | Affects git tracking. |
| `opencode.json` | Project-wide permissions and agent config. |
| `agents/memory/.project` | The Neo4j `group_id` (project identity). |
| `data/` | Datasets. Prevents accidental edits. |

**Rules**:
- Every edit to a protected path is a real question. The user approves or denies. If denied, stop.
- Don't retry with a different phrasing. Don't batch the change with another edit. Don't delegate the edit to a subagent to bypass the prompt.
- Adding a new protected file = edit `opencode.json` and add `"<path>": "ask"` under `permission.edit`.

**Bash denies (defence against typos)**: `make -f agents/memory/scripts/Makefile {wipe,set-project}` are denied for every agent (global block + per-agent block in `opencode.json`). Use `make` itself for normal work; the deny patterns only block the destructive subcommands.

## MCP memory — which tool, when

| Path | Use |
|---|---|
| `mcp__graphiti-memory__add_memory` with `source: "text"` | Free-form session summaries, observations, "remember this" notes. |
| `memory_node` (custom tool) or `memory.sh node` | Typed node writes: `Component`, `Investigation`, `Architecture`, `Pattern`, `Pitfall`, `Tool`, `Operational`, `Preference`. |
| `memory_rel` (custom tool) or `memory.sh rel` | Typed relations between typed nodes. |
| `memory_query` / `memory_audit` / `memory_status` | Reads and invariants. |
| `mcp__graphiti-memory__add_memory` with `source: "json"` | **Forbidden.** The LLM extractor in MCP 1.26.0 ignores `type` and re-classifies from text, producing mis-labelled graphs (verified 2026-07-04: 261-node / 411-rel wipe). |
| `mcp__graphiti-memory__add_triplet` | **Not available in MCP 1.26.0.** Use `memory_node` + `memory_rel`. |

**Schema (8 labels, validated on every write)**: `Component`, `Investigation`, `Architecture`, `Pattern`, `Pitfall`, `Tool`, `Operational`, `Preference`. The full manual — schema details, 3 invariants, session lifecycle, recall-before-write rule — is in the `project-memory` skill: `skill({ name: "project-memory" })` on demand.

**Three invariants** (run on every `make audit`):
1. No `Entity`-only node — every node has at least one schema label.
2. No orphan relation — every rel endpoint exists.
3. No out-of-schema label — every label is in `agents/memory/runtime/config/config.yaml`.

## Where knowledge lives

| What | Where |
|---|---|
| Procedural how-to (build, test, push, session lifecycle, conventions) | This file (`AGENTS.md`). |
| Project-specific facts (components, investigations, patterns, pitfalls, conventions) | Knowledge graph (Neo4j via `agents/memory/`). Use `memory_node` / `memory_rel` for typed writes; `memory_query` for reads. |
| Free-form session notes, observations, summaries | Knowledge graph as text episodes via `mcp__add_memory` with `source: "text"`. |
| Stack health / schema / session routines | `make -f agents/memory/scripts/Makefile {status,audit,session-start,session-end}`. |

**Why split**: `AGENTS.md` enters every session. Project-specific facts would bloat it with context irrelevant to most tasks. The knowledge graph is queried just-in-time.

**Recall before writing**: always run `memory_query` or `mcp__graphiti-memory__search_nodes` first. If a relevant node or fact already exists, supersede it with a new write — never duplicate.

## Decision table: where does this go?

| If you want to… | Do this | Not this |
|---|---|---|
| Add a stable helper | Put it in `mal-commonlib/`. | Don't put it in `mal-ghana-sim/` (research) or `mal-core/` if it's not stable yet. |
| Add a CLI script | Put it in `mal-execution/scripts/`. | Don't put a batch job in `mal-core/` (core is library, not scripts). |
| Record a project fact | Use `memory_node` / `memory_rel`. | Don't paste it into `AGENTS.md` (one-off facts bloat the file). |
| Recall a fact from last session | Use `memory_query` or `mcp__graphiti-memory__search_nodes`. | Don't re-read source files hoping to find it. |
| Ask a one-off question | Use the `question` tool. | Don't guess on irreversible choices. |
| Delegate a multi-step task | Use `task` with a `subagent_type`. | Don't do it in this context if the work needs a fresh window. |
| Edit a protected file | Ask the user (the `ask` prompt is the mechanism). | Don't try to bypass the `ask` prompt via delegation. |
| Push to remote after a rewrite | `git ps origin main` (force-with-lease). | Don't use `git push --force`. |
| Wipe or set the project | `make -f agents/memory/scripts/Makefile wipe` / `set-project`. | Don't call without the global+per-agent `deny` being lifted by the user. |

## Context architecture (3 layers + 2)

| Layer | Owner | Lives in |
|---|---|---|
| Operational | OpenCode (this primary agent) | The current session's context window. |
| Compaction | OpenCode (built-in) | Auto-summarised when the operational layer grows. |
| Episodic | `agents/memory/` | Free-form session summaries, observations, "what was done". |
| Semantic | `agents/memory/` | Typed nodes: components, investigations, patterns, etc. |

**Discipline**: keep the operational layer compact — objective, plan, key decisions, references (paths, UUIDs, commit IDs, proposal IDs). Never paste multi-thousand-line tool outputs into the supervisor's prompt. Long outputs go to the knowledge graph or a summary.

**Subagents** see a brief, not the full conversation. If they need more context, they query the knowledge graph or ask the supervisor.

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

**Start**: `make -f agents/memory/scripts/Makefile session-start` — runs the audit, then lists open investigations, active pitfalls, architecture decisions, components, preferences, and operational patterns. If the audit fails, fix at the source (don't patch the audit).

**End** (non-trivial sessions only):
1. Update affected `Investigation` nodes (open / in-progress / resolved / blocked + evidence).
2. Add newly-discovered typed nodes (patterns, pitfalls, components, architecture).
3. Write a free-form session episode via `mcp__graphiti-memory__add_memory` with `source: "text"`.
4. Edit `AGENTS.md` if a new convention emerged.
5. `make -f agents/memory/scripts/Makefile audit` — re-verify.

**Skip the contract for trivial sessions** (single tool call, no state change).

## Specialised loops

Invoke with `@<name>` or the `task` tool. Each subagent's prompt lives at `agents/loops/<name>.md`. Brief summary:

| Agent | Role | Auto-invoked by supervisor? |
|---|---|---|
| `test-fixer` | Iterate a check command until it exits 0. | `allow` |
| `code-reviewer` | Review a diff; return structured findings. Read-only. | `ask` |
| `doc-researcher` | Query the knowledge base first; web is a fallback. | `ask` |
| `security-auditor` | OWASP-style audit. Read-only. | `ask` |

The supervisor is the default primary agent (`default_agent: "supervisor"` in `opencode.json`). It owns the running context, decomposes work, delegates to loops and subagents, and integrates via `gitagent` for isolated multi-agent edits. The supervisor's prompt (`.opencode/agents/supervisor.md`) is generic and reusable; project rules live here in `AGENTS.md`. Tab cycles between `supervisor` (default), `build` (single-tool ad-hoc), and `plan` (read-only review).
