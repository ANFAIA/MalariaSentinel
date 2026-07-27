# MalariaSentinel DeepAgents

Multi-agent orchestration system for ABM calibration, feature development, and research — built on [deepagents](https://docs.langchain.com/oss/python/deepagents) + [gitagent](https://github.com/nicholaswatertank/gitagent) for isolated worktree workflows.

## Quick start

```bash
# Install (from repo root)
uv sync --all-packages

# Set your OpenRouter API key
export OPENROUTER_API_KEY="sk-or-..."

# Run a calibration cycle (interactive)
uv run python -m agents.deepagents calibration

# Run with a goal + no human-in-the-loop
uv run python -m agents.deepagents calibration -g "Fix D2 scorer regression" --no-verify

# Dry run (print prompt, don't execute)
uv run python -m agents.deepagents calibration -g "Improve spatial scorers" --dry-run
```

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│ ORCHESTRATOR (LLM)                                       │
│ Backend: FilesystemBackend(virtual_mode=True)             │
│ Tools: 17 (gitagent, pipeline, kg, search, improve)      │
│ Read-only via deny-write permissions.                     │
└───────────┬──────────────────────────────────────────────┘
            │ gitagent spawn → worktree
            ▼
┌──────────────────────────────────────────────────────────┐
│ WORKER (LLM, sandboxed)                                  │
│ Backend: FilesystemBackend(virtual_mode=True)             │
│ Tools: abm_run, abm_test, abm_score (3 custom)           │
│ Can only see its own worktree. No secrets/data/git writes.│
└──────────────────────────────────────────────────────────┘
```

### The gitagent workflow

```
gitagent_init → gitagent_start → gitagent_spawn → worker proposes →
gitagent_proposals → gitagent_diff → accept/reject/revise →
gitagent_integrate → gitagent_finalize (1 commit on main)
```

Each feature gets its own isolated worktree. The orchestrator reviews diffs and decides. Workers iterate unlimited times until the change is correct.

## CLI commands

### `calibration` — ABM calibration improvement

```bash
uv run python -m agents.deepagents calibration [OPTIONS]
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
uv run python -m agents.deepagents feature <name> <description> [OPTIONS]
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
uv run python -m agents.deepagents research <topic> [OPTIONS]
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
agents/deepagents/
├── __init__.py
├── __main__.py              # python -m agents.deepagents
├── agent.py                 # create_orchestrator(), create_abm_worker_subagent()
├── cli.py                   # Typer CLI (calibration, feature, research)
├── logger.py                # SessionLogger — JSONL append-only logs
├── pyproject.toml           # Package metadata (mal-deepagents)
├── AGENTS.md                # Agent conventions and pitfalls
│
├── tools/                   # Custom tools for the orchestrator
│   ├── __init__.py          # Exports all 17 tools
│   ├── gitagent_tool.py     # 12 gitagent CLI wrappers (init→finalize)
│   ├── abm_tools.py         # abm_run, abm_test, abm_score (worker tools)
│   ├── opencode_tool.py     # Web search via OpenRouter/Perplexity
│   ├── kg_tool.py           # Knowledge graph recall (Neo4j)
│   ├── pipeline_tool.py     # Run calibration suite, compare scorecards
│   └── improve_tool.py      # Self-improvement: patch prompts from failures
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
└── tests/                   # E2E tests (34 tests, all mocked)
    ├── conftest.py          # sys.path setup for imports
    ├── test_gitagent_tools.py
    ├── test_abm_tools.py
    ├── test_orchestrator.py
    ├── test_cli.py
    └── test_permissions.py
```

## Tools reference

### Orchestrator tools (17)

| Tool | Purpose | Category |
|---|---|---|
| `gitagent_init` | Initialize gitagent in repo (idempotent) | gitagent |
| `gitagent_start` | Open a session for a feature | gitagent |
| `gitagent_spawn` | Spawn worker in isolated worktree | gitagent |
| `gitagent_list_agents` | List active workers | gitagent |
| `gitagent_kill` | Kill a zombie worker | gitagent |
| `gitagent_proposals` | List proposals (JSON) | gitagent |
| `gitagent_diff` | Raw diff for a proposal | gitagent |
| `gitagent_accept` | Mark proposal accepted (no apply) | gitagent |
| `gitagent_reject` | Reject a proposal | gitagent |
| `gitagent_revise` | Send proposal back for iteration | gitagent |
| `gitagent_integrate` | Apply all accepted proposals | gitagent |
| `gitagent_finalize` | Create 1 commit on main + cleanup | gitagent |
| `pipeline_run_calibration` | Run pytest calibration suite | pipeline |
| `pipeline_compare_scorecards` | Compare scorecards against baseline | pipeline |
| `memory_recall_kg` | Recall from Neo4j knowledge graph | kg |
| `opencode_search` | Web search via Perplexity | search |
| `improve_prompt` | Patch prompts from failure analysis | self-improve |

### Worker tools (3)

| Tool | Purpose |
|---|---|
| `abm_run` | Compile (if needed) + run ABM simulation |
| `abm_test` | Run `pytest -m fast -v` on calibration suite |
| `abm_score` | Run 14 scorers + composite + optional LLM verdict |

## Sandboxing

### Orchestrator permissions

| Path | Operation | Mode |
|---|---|---|
| `/**` | read | allow |
| `/.env`, `/**/.env`, `/**/*secret*`, `/**/*credential*` | read | deny |
| `/**` | write, edit | deny |

The orchestrator has **read-only access to the entire repo** via `deny-write` permissions. It writes only via `gitagent_*` tools (which operate through the gitagent CLI, not the filesystem).

### Worker permissions

| Path | Operation | Mode |
|---|---|---|
| `/**` | read, write, edit | allow |
| `/.env`, `/**/.env`, `/**/*secret*`, `/**/*credential*` | read | deny |
| `/data/**` | write, edit | deny |
| `/.gitagent/**`, `/.git/**` | write, edit | deny |

Workers are sandboxed to their gitagent worktree via `FilesystemBackend(virtual_mode=True)`. They cannot:
- Read `.env` files or secrets
- Modify input datasets in `/data/`
- Touch gitagent metadata or git internals
- Escape their worktree (no `../` access)

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
uv run pytest agents/deepagents/tests/ -v

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
uv run python -m agents.deepagents calibration -p anthropic -m claude-sonnet-4-20250514

# OpenAI
uv run python -m agents.deepagents calibration -p openai -m gpt-4o

# Google
uv run python -m agents.deepagents calibration -p google_genai -m gemini-2.0-flash
```

## Dependencies

```
deepagents >= 0.6
langgraph >= 0.4
langchain-core >= 0.3
typer >= 0.9
rich >= 13
langchain-openai >= 0.3  (optional, for OpenRouter)
```
