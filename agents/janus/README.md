# MalariaSentinel Janus

Multi-agent orchestration system for ABM calibration, feature development, and research — built on [deepagents](https://docs.langchain.com/oss/python/deepagents) + [gawt](https://github.com/nicholaswatertank/gitagent) (`gitagent-mcp`) for shared-worktree, per-file-locked editing.

## Quick start

```bash
# Install (from repo root)
uv sync --all-packages

# Set your LLM API key
export OPENROUTER_API_KEY="sk-or-..."

# Start the request-router REPL (research + dispatch; no args)
uv run janus

# Goal-driven implementation coordinator (edits via gawt, finalizes changes)
uv run janus improve -g "Fix D2 scorer regression"
uv run janus improve -g "Improve spatial scorers" --plan docs/plans/calibration.md

# Inspect rendered prompts + tool schemas
uv run janus prompts
```

## CLI

`janus` is the entry point (`agents_janus.cli:app`, package `mal-janus`).

| Command | What it does |
|---|---|
| `janus` | **Request router REPL** — routes each request to a coordinator: runs ABM/pipeline stages via `malariasim`, asks specialists, dispatches implementation work. |
| `janus improve` | **Implementation coordinator** — decomposes a goal, opens a gawt session, dispatches specialists, monitors the pheromone, snapshots changes. |
| `janus prompts` | Print rendered prompts and visible tool schemas. |

Global flags: `--no-tracing` (Langfuse tracing is ON by default), `--no-codebase-index` (skip codebase-memory index on startup), `--env dev|staging|production`, `--dump-prompts` (write prompts to `prompt_snapshots.jsonl`).

`janus improve` options: `--goal/-g`, `--plan`, `--provider/-p` (openrouter, openai, anthropic), `--model/-m` (default `xiaomi/mimo-v2.5`), `--no-verify` (skip approval gates).

> The old `calibration` / `feature` / `research` subcommands were removed —
> everything goes through the request router (`janus`) or the implementation
> coordinator (`janus improve`).

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│ REQUEST ROUTER (centinela)                               │
│ Backend: MalariasimShellBackend(virtual_mode=True)       │
│ execute tool (bash) → malariasim only                    │
│ + onboard tools, memory_kg, ask_user, task()             │
└───────────┬──────────────────────────────────────────────┘
            │ delegate_to_dispatcher() → gawt session
            ▼
┌──────────────────────────────────────────────────────────┐
│ IMPLEMENTATION COORDINATOR (dispatcher)                  │
│ start_session → register_agent + dispatch specialists    │
│ monitor via pheromone (list_edits) + list_agents         │
│ snapshot_session → partial commit on target branch       │
└───────────┬──────────────────────────────────────────────┘
            ▼
┌──────────────────────────────────────────────────────────┐
│ SPECIALISTS (8, from config/subagents.yaml)              │
│ abm · scoring · ingest · download · prediction ·         │
│ training · data · commonlib                              │
│ abm only: execute → malariasim (ToolFilterMiddleware     │
│ filters it out for every other specialist)               │
└──────────────────────────────────────────────────────────┘
```

Both coordinator modes run on `MalariasimShellBackend` — the deepagents
built-in `execute` tool restricted to `malariasim` commands. Filesystem deny
rules (secrets, `/data/**`, `/.git/**`) are backend policy hooks, not
`FilesystemPermission` (incompatible with execution backends).

### Delegation model

- **Research tasks**: the router dispatches specialists directly via `task()` (no gawt session).
- **Implementation tasks**: the router calls `delegate_to_dispatcher()`; the dispatcher owns the gawt session lifecycle.
- **Quick questions**: `onboard_ask_subagent(name, question)` — single LLM call.

### The gawt workflow (gawt v0.6.0)

```
start_session → register_agent + dispatch specialists →
specialists declare intent (start_intent), edit via mcp__gitagent__*
(per-file locks + informed reads) →
coordinator monitors pheromone (list_edits) + list_agents →
snapshot_session (partial commit) → abort_session (last open session removes worktree)
```

gawt v0.6.0 has **no inbox**: coordination emerges from the pheromone (the
SQLite `edits` log), per-file write locks with informed reads
(`read_file` returns `content`, `sha256`, `base_sha`, `diff`, `edits[]`,
`warning`), and partial snapshots. Write rejections (`{status: "rejected"}`)
mean re-read, re-plan, retry — never blind-retry.

## Project structure

```
agents/janus/
├── src/agents_janus/
│   ├── agent.py                 # create_orchestrator (dual-mode: centinela + dispatcher)
│   ├── cli.py                   # Typer CLI (janus, improve, prompts)
│   ├── improvement.py           # run_improvement (dispatcher stream)
│   ├── onboarding.py            # centinela REPL
│   ├── live_panel.py            # LivePanel + MultiAgentPanel
│   ├── observability.py         # ObservabilityMiddleware (mode tags, Langfuse)
│   ├── logger.py                # SessionLogger (JSONL)
│   ├── scope_validator.py       # validate_edit_scope
│   ├── manifest.py              # session manifest CRUD
│   ├── malariasim_backend.py    # execute → malariasim-only policy hooks
│   ├── middleware/              # ToolFilterMiddleware (execute only for abm)
│   ├── config/subagents.yaml    # 8 specialist definitions
│   ├── plugins/                 # Plugin chain (per-domain)
│   ├── subagents/               # Registry, builder, base types
│   ├── tools/                   # KG recall, ask_user, delegate_to_dispatcher, onboard_tools
│   ├── prompts/                 # orchestrator.md.j2, specialist templates, per-subagent/
│   └── tests/                   # unit, integration, LLM-as-judge tests
├── pyproject.toml               # Package metadata (mal-janus) + `janus` script
├── AGENTS.md                    # Agent conventions, tool matrix, pitfalls
└── README.md                    # This file
```

## Tools reference

| Tool | Router | Dispatcher | Specialists |
|---|---|---|---|
| `ask_user` | ✅ | ✅ | ✅ |
| `memory_recall_kg` (Neo4j knowledge graph) | ✅ | ✅ | via plugin |
| `execute` (bash → `malariasim` only) | ✅ | ✅ | abm only |
| `onboard_status`, `onboard_ask_subagent` | ✅ | ❌ | ❌ |
| `delegate_to_dispatcher` | ✅ | ❌ | ❌ |
| `gawt_mcp_*` (session lifecycle, edits) | ❌ | ✅ | ✅ |
| `task()` (subagent dispatch) | ✅ | ✅ | ❌ |

## Sandboxing

| Path / command | Operation | Mode |
|---|---|---|
| `/.env`, `/**/.env`, `/**/*secret*`, `/**/*credential*` | read | deny |
| `/.gitagent/worktree/**` | write, edit | allow |
| `/data/**`, `/.git/**`, everything else | write, edit | deny |
| shell commands not starting with `malariasim` | execute | deny |

## Observability

- **LivePanel / MultiAgentPanel** — terminal panels (own stream / per-agent rows).
- **SessionLogger** — JSONL at `runs/<session>/session.jsonl`.
- **Langfuse** — on by default (`--no-tracing` to disable); nested spans for LLM calls, tool calls, specialist dispatches; tags `agent:<role>`, `env:<env>`, `mode:centinela|dispatcher`, `stage:<phase>`.

## Running tests

```bash
uv run pytest agents/janus/src/agents_janus/tests/ -v   # all mocked, no LLM/gawt needed
cd mal-core/src/mal_core/abm/tests/calibration && uv run pytest -m fast -v
```

## Dependencies

```
deepagents >= 0.6
langgraph >= 0.4
langchain-core >= 0.3
typer >= 0.9
rich >= 13
langchain-openai >= 0.3  (optional, for OpenRouter)
gawt >= 0.6.0            (MCP server `gitagent-mcp`)
```
