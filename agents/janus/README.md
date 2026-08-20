# MalariaSentinel Janus

Multi-agent orchestration system for ABM calibration, feature development, and research — built on [deepagents](https://docs.langchain.com/oss/python/deepagents) + [gitagent](https://github.com/nicholaswatertank/gitagent) for isolated worktree workflows.

## Quick start

```bash
# Install (from repo root)
uv sync --all-packages

# Set your OpenRouter API key
export OPENROUTER_API_KEY="sk-or-..."

# Run a calibration cycle (interactive)
uv run python -m agents_janus calibration

# Run with a goal + no human-in-the-loop
uv run python -m agents_janus calibration -g "Fix D2 scorer regression" --no-verify

# Dry run (print prompt, don't execute)
uv run python -m agents_janus calibration -g "Improve spatial scorers" --dry-run
```

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│ ORCHESTRATOR (LLM)                                       │
│ Backend: MalariasimShellBackend(virtual_mode=True)       │
│ execute tool (bash) → malariasim only                   │
│ + gawt MCP, search, kg, ask_user                        │
└───────────┬──────────────────────────────────────────────┘
            │ gitagent spawn → worktree
            ▼
┌──────────────────────────────────────────────────────────┐
│ WORKER (LLM)                                             │
│ Backend: MalariasimShellBackend(virtual_mode=True)       │
│ abm specialist: execute → malariasim only               │
│ others: execute filtered out (ToolFilterMiddleware)     │
│ No secrets/data/git writes (backend policy hooks).       │
└──────────────────────────────────────────────────────────┘
```

Shell access is the deepagents built-in `execute` tool — restricted to
`malariasim` commands via the `MalariasimShellBackend` policy hook. The old
custom ABM tools (`abm_run`, `abm_test`, `abm_score`) and pipeline tools were
removed.

### The gitagent workflow (gawt v0.6.0)

```
orchestrator start_session(session_id) → register_agent + dispatch specialists →
specialists declare intent, edit via mcp__gitagent__* (per-file lock + informed read) →
orchestrator monitor via pheromone (list_edits) + list_agents →
orchestrator snapshot_session(session_id, message, files) → partial commit on main →
orchestrator abort_session(session_id)
```

In gawt v0.6.0 multiple sessions share **one** global worktree
(`.gitagent/worktree/`). There is **no inbox** — coordination emerges from the
pheromone (the SQLite `edits` log), per-file write locks with informed reads
(`read_file` returns `content`, `sha256`, `base_sha`, `diff`, `edits[]`,
`warning`), and partial snapshots (`snapshot_session`). `finalize_session`,
`check_inbox`, and `send_message` no longer exist. The orchestrator reviews
informed reads and rejection payloads and decides.

## CLI commands

### `calibration` — ABM calibration improvement

```bash
uv run python -m agents_janus calibration [OPTIONS]
```

| Flag | Default | Description |
|---|---|---|
| `-g, --goal` | (interactive) | Goal for this calibration run |
| `-n, --max-iterations` | 10 | Maximum improvement iterations |
| `-p, --provider` | openrouter | LLM provider |
| `-m, --model` | xiaomi/mimo-v2.5 | Model identifier |
| `-t, --thread-id` | calibration-session | Thread ID for checkpointing |
| `--dry-run` | false | Print prompt without executing |
| `--no-verify` | false | Skip ALL human-in-the-loop approval gates |

### `feature` — Feature development

```bash
uv run python -m agents_janus feature <name> <description> [OPTIONS]
```

| Flag | Default | Description |
|---|---|---|
| `-g, --goal` | (interactive) | Goal for this feature run |
| `-p, --provider` | openrouter | LLM provider |
| `-m, --model` | xiaomi/mimo-v2.5 | Model identifier |
| `--dry-run` | false | Print prompt without executing |
| `--no-verify` | false | Skip ALL human-in-the-loop approval gates |

### `research` — Research + improvement

```bash
uv run python -m agents_janus research <topic> [OPTIONS]
```

| Flag | Default | Description |
|---|---|---|
| `-g, --goal` | (interactive) | Goal for this research run |
| `-c, --cycles` | 1 | Number of research cycles |
| `-p, --provider` | openrouter | LLM provider |
| `-m, --model` | xiaomi/mimo-v2.5 | Model identifier |
| `--dry-run` | false | Print prompt without executing |
| `--no-verify` | false | Skip ALL human-in-the-loop approval gates |

### `--no-verify` semantics

When `--no-verify` is set:
- Skips the approval prompt before `gitagent_integrate`
- Skips the approval prompt before `gitagent_finalize`
- No human interaction required — fully autonomous

When `--no-verify` is NOT set (default):
- Requires `[y/N]` confirmation before `gitagent_integrate`
- Requires `[y/N]` confirmation before `gitagent_finalize`

## Project structure

```
agents_janus/
├── __init__.py
├── __main__.py              # python -m agents_janus
├── agent.py                 # create_orchestrator(), create_abm_worker_subagent()
├── cli.py                   # Typer CLI (calibration, feature, research)
├── logger.py                # SessionLogger — JSONL append-only logs
├── pyproject.toml           # Package metadata (mal-janus)
├── AGENTS.md                # Agent conventions and pitfalls
│
├── tools/                   # Custom tools for the orchestrator
│   ├── __init__.py          # Exports all tools
│   ├── web_search.py        # Web search via OpenRouter/Perplexity
│   ├── kg_tool.py           # Knowledge graph recall (Neo4j)
│   ├── onboard_tools.py     # Status, list components, delegate, ask_subagent
│   └── ask_user_tool.py     # Ask the user
│
├── malariasim_backend.py    # MalariasimShellBackend — execute → malariasim only
│
├── middleware/              # Agent middleware (scope, inbox, tool filter)
│   ├── inbox_check.py
│   └── tool_filter.py       # Excludes execute from non-abm subagents
│
├── cycles/                  # High-level workflows
│   ├── calibration_cycle.py # Calibration improvement cycle (9 steps)
│   ├── feature_cycle.py     # Feature development cycle
│   └── research_cycle.py    # Research + improvement cycle
│
├── prompts/                 # Prompt templates + patches
│   ├── templates/           # Per-worker prompt templates
│   └── patches/             # Self-improvement patches
│
└── tests/                   # E2E tests (all mocked)
    ├── conftest.py          # sys.path setup for imports
    ├── test_orchestrator.py
    ├── test_cli.py
    └── test_permissions.py  # Backend policy hooks (execute + fs denies)
```

## Tools reference

### Orchestrator tools

| Tool | Purpose | Category |
|---|---|---|
| `execute` | Shell — **only `malariasim`** (built-in, restricted by backend) | abm |
| `web_search` | Web search via Perplexity | search |
| `memory_recall_kg` | Recall from Neo4j knowledge graph | kg |
| `ask_user` | Ask the user for clarification | user |
| `onboard_status` | Show system status (centinela) | pipeline |
| `onboard_list_components` | List registered subagents (centinela) | pipeline |
| `delegate_to_dispatcher` | Hand off implementation to dispatcher (centinela) | dispatch |
| `onboard_ask_subagent` | Quick specialist question (centinela) | user |
| `mcp__gitagent__*` | gawt session lifecycle (dispatcher) | gawt |

### Worker tools (subagents)

| Tool | Purpose |
|---|---|
| `mcp__gitagent__*` | gawt edit/read/list (shared worktree) |
| `execute` | **abm specialist only** — shell restricted to `malariasim` |
| `ask_user`, `resolve_conflict` | Interaction helpers |

## Sandboxing

Shell access is the deepagents built-in `execute` tool, restricted to
`malariasim` via the `MalariasimShellBackend` policy hook
(`malariasim_backend.py`). Only the orchestrator and the `abm` specialist see
`execute`; every other subagent has it filtered out by `ToolFilterMiddleware`.
Filesystem deny rules are enforced as backend policy hooks (not
`FilesystemPermission`, which is incompatible with execution backends):

### Backend policy hooks (all agents)

| Path | Operation | Mode |
|---|---|---|
| `/.env`, `/**/.env`, `/**/*secret*`, `/**/*credential*` | read | deny |
| `/.gitagent/worktree/**` | write, edit | allow |
| `/data/**`, `/.git/**`, anything else | write, edit | deny |
| shell commands not starting with `malariasim` | execute | deny |

Agents cannot:
- Read `.env` files or secrets
- Modify input datasets in `/data/`
- Touch gitagent metadata or git internals
- Run any shell command other than `malariasim`

## Session logging

Every run creates a JSONL log at `runs/deepagent-<timestamp>/session.jsonl`:

```jsonl
{"event": "session_start", "ts": "2026-07-26T10:00:00+00:00", "session_dir": "runs/deepagent-20260726-100000"}
{"event": "tool_call", "ts": "...", "step": 0, "tool": "gitagent_init", "input": {}, "output": "{\"status\": \"initialized\"}", "latency_s": 0.12}
{"event": "decision", "ts": "...", "step": 1, "decision": "session_start", "reason": "calibration cycle, goal=Fix D2"}
{"event": "summary", "ts": "...", "step": 10, "summary": "Calibration complete. Composite improved from 0.65 to 0.72."}
{"event": "session_end", "ts": "...", "total_steps": 11, "elapsed_s": 45.2}
```

## Running tests

```bash
# DeepAgents E2E tests (all mocked, no LLM/gitagent needed)
uv run pytest agents_janus/tests/ -v

# ABM calibration tests (1 seed, fast tier)
cd mal-core/src/mal_core/abm/tests/calibration
uv run pytest -m fast -v
```

## Provider setup

### OpenRouter (default)

```bash
export OPENROUTER_API_KEY="sk-or-..."
# or
export OPENROUTER_KEY="sk-or-..."
```

### Other providers

```bash
# Anthropic
uv run python -m agents_janus calibration -p anthropic -m claude-sonnet-4-20250514

# OpenAI
uv run python -m agents_janus calibration -p openai -m gpt-4o

# Google
uv run python -m agents_janus calibration -p google_genai -m gemini-2.0-flash
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
