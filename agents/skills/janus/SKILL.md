---
name: janus
description: LangChain deepagents-based multi-agent orchestrator for MalariaSentinel ABM calibration. Use when running calibration cycles, spawning worker agents, improving ABM parameters, or managing multi-agent workflows for model optimization.
---

# Janus Orchestrator

Multi-agent orchestrator for MalariaSentinel ABM calibration improvement. Janus uses LangChain's Deep Agents framework with a dual-mode architecture (Centinela + Dispatcher) for autonomous calibration cycles.

## Overview

Janus is the autonomous calibration system for the MalariaSentinel ABM. It coordinates multiple specialist agents to iteratively improve model parameters, validate against calibration scorers, and maintain biological plausibility.

## Package Location

```
agents/janus/
├── src/agents_janus/
│   ├── agent.py                 # create_orchestrator (dual-mode)
│   ├── cli.py                   # CLI entrypoint
│   ├── improvement.py           # run_improvement (dispatcher stream)
│   ├── onboarding.py            # centinela REPL
│   ├── live_panel.py            # LivePanel + MultiAgentPanel
│   ├── observability.py         # ObservabilityMiddleware
│   ├── logger.py                # SessionLogger (JSONL)
│   ├── scope_validator.py       # validate_edit_scope
│   ├── manifest.py              # session manifest CRUD
│   ├── malariasim_backend.py    # MalariasimShellBackend
│   ├── middleware/               # ToolFilterMiddleware
│   ├── config/subagents.yaml    # 8 subagent definitions
│   ├── plugins/                 # Plugin chain
│   ├── subagents/               # Registry, builder, base types
│   ├── tools/                   # KG, ask_user, delegate_to_dispatcher
│   ├── prompts/                 # orchestrator.md.j2, specialist.md.tmpl
│   └── tests/                   # unit, integration, LLM-as-judge tests
├── SKILL.md                     # This skill
├── pyproject.toml               # Package configuration
└── README.md                    # Project documentation
```

## Quick Start

```bash
# Install dependencies
cd agents/janus
uv sync

# Run centinela REPL (conversational)
uv run janus

# Run dispatcher (goal-driven)
uv run janus run -g "Improve ABM calibration score by 10%"

# Run with Langfuse tracing
uv run janus run -g "..." --tracing langfuse

# Check status
uv run janus status

# List subagents
uv run janus agents list
```

## Dependencies

| Package | Purpose |
|---|---|
| `deepagents>=0.6` | Deep Agent framework |
| `langgraph>=0.4` | LangGraph for agent orchestration |
| `langchain-core>=0.3` | LangChain core |
| `langchain-openai>=0.3` | OpenAI integration |
| `langchain-openrouter>=0.1` | OpenRouter support |
| `mcp>=2.0` | Model Context Protocol |
| `pydantic>=2.0` | Data validation |
| `typer>=0.9.0` | CLI framework |
| `rich>=13.0.0` | Terminal formatting |
| `jinja2>=3.1.0` | Template rendering |
| `gawt>=0.6.3` | Git Agent Worktree (gawt) MCP |

### Optional Dependencies

```bash
# Langfuse observability
uv sync --extras observability
```

## Dual-Mode Architecture

Janus has **two orchestrator modes** sharing the same factory:

```
Centinela (REPL, talks to user):
  ├─ Research:  task("abm", "[MODE:research] ...")     ← direct dispatch
  └─ Implement: delegate_to_dispatcher(goal="...")     ← opens gawt session

Dispatcher (goal-driven, one-shot):
  ├─ start_session → task("scoring", "[MODE:implementation] ...") → finalize
  └─ returns summary to centinela
```

### Mode Selection

| Mode | Use when | Interface |
|---|---|---|
| `centinela` | Interactive REPL, explaining then delegating | Conversational |
| `dispatcher` | Autonomous goal execution, one-shot | Goal-driven |

## Workers (Subagents)

| Worker | Role | Can Edit |
|---|---|---|
| `abm-worker` | Modifies C++ ABM parameters | `mal-core/src/mal_core/abm/` |
| `scorer-worker` | Modifies Python calibration scorers | `mal-core/src/mal_core/abm/tests/calibration/` |
| `feature-worker` | Implements new features in mal-core | `mal-core/src/mal_core/` |
| `ingest-worker` | Handles data ingestion pipelines | `mal-core/src/mal_core/ingest/` |
| `download-worker` | Manages data downloads | `mal-core/src/mal_core/download/` |
| `prediction-worker` | Updates prediction pipelines | `mal-core/src/mal_core/prediction/` |
| `training-worker` | Modifies training workflows | `mal-core/src/mal_core/training/` |
| `data-worker` | Works with data utilities | `mal-commonlib/` |

## CLI Commands

```bash
# Centinela REPL (default)
uv run janus
uv run janus onboard

# Dispatcher (goal-driven)
uv run janus run -g "Improve calibration score"
uv run janus run -g "..." --plan docs/plans/calibration.md

# With observability
uv run janus run -g "..." --tracing langfuse

# Status and inspection
uv run janus status
uv run janus agents list
uv run janus agents show abm
```

## Calibration Workflow

### 1. Start a Calibration Cycle

```bash
# Interactive mode
uv run janus

# Autonomous mode
uv run janus run -g "Improve ABM calibration by optimizing dispersal parameters"
```

### 2. Monitor Progress

The orchestrator provides:
- **LivePanel**: Real-time terminal output
- **SessionLogger**: JSONL logs in `runs/<session>/`
- **Langfuse**: Optional trace dashboard

### 3. Review Results

```bash
# Check calibration scores
uv run janus status

# View session logs
cat runs/<session>/session.jsonl | jq .
```

## gawt MCP Integration

Janus uses gawt (Git Agent Worktree) for isolated multi-agent editing:

### Features
- Single shared worktree per repo
- Per-file write locks
- Informed reads (see peer edits)
- Partial snapshots
- SQLite-backed state

### Tool Reference

| Tool | Effect |
|---|---|
| `start_session(feature, target_branch)` | Create worktree + session |
| `register_agent(role)` | Register a specialist agent |
| `start_intent(agent_id, intent)` | Declare work intent |
| `edit_file(agent_id, file, old, new)` | Edit with lock protection |
| `list_edits(agent_id)` | See peer pheromone |
| `finalize_session(message)` | Commit to target branch |

## Observability

### LivePanel
Single-agent terminal panel for the orchestrator's own stream.

### MultiAgentPanel
Multi-agent rows showing agent_id, role, intent, and inbox status.

### SessionLogger
JSONL logging in `runs/<session>/session.jsonl`:
```json
{"timestamp": "...", "agent": "abm", "action": "edit", "file": "params.h", "intent": "optimize dispersal"}
```

### Langfuse Tracing
Optional trace dashboard for production monitoring:
```bash
uv run janus run -g "..." --tracing langfuse
```

Tags: `agent:<role>`, `env:<env>`, `mode:centinela|dispatcher`, `stage:<phase>`, `tool:<category>`

## Configuration

### Subagent Registry

Configuration in `config/subagents.yaml`:
- Each subagent has: `spec`, `skills`, `gawt_role`, `can_call_via`, `edits_allow` (glob patterns), `plugins`
- `gawt_role` maps to the gawt `register_agent(role=...)` parameter

### Provider

Default: `openrouter:xiaomi/mimo-v2.5`

Set `OPENROUTER_API_KEY` env var for OpenRouter access.

## Integration with MalariaSentinel

### ABM Calibration

Janus improves the ABM by:
1. Running calibration scorers (10 scorers + LLM verdict)
2. Identifying parameter gaps
3. Proposing parameter adjustments
4. Validating against biological constraints
5. Iterating until composite score improves

### Related Components

| Component | Location | Purpose |
|---|---|---|
| ABM Engine | `mal-core/src/mal_core/abm/` | C++ simulation |
| Calibration Scorers | `mal-core/src/mal_core/abm/tests/calibration/` | Validation metrics |
| Thresholds | `mal-core/src/mal_core/abm/tests/calibration/thresholds.yaml` | Score boundaries |
| Composite Score | `mal-core/src/mal_core/abm/tests/calibration/scorers/composite.py` | Aggregated metric |

## Related Skills

| Skill | Use when |
|---|---|
| `abm-engine` | Understanding the C++ ABM |
| `calibration-framework` | Running calibration scorers |
| `mal-core-api` | Accessing core APIs |
| `project-memory` | Querying the knowledge graph |
| `gitagent` | Understanding gawt worktree isolation |

## Troubleshooting

### No Checkpointer Set

```
Error: No checkpointer set
```

Ensure the orchestrator is created with a checkpointer:
```python
from agents_janus.agent import create_orchestrator
orchestrator = create_orchestrator(mode="dispatcher")
```

### gawt MCP Connection Issues

```bash
# Verify gawt is installed
pip show gawt

# Check MCP server
gitagent-mcp --help
```

### Worker Conflicts

If workers conflict on file edits:
1. Check `list_edits` for peer pheromone
2. Re-read the conflicting file
3. Re-plan your edit
4. Retry with updated content

### Calibration Score Not Improving

```bash
# Check current scores
uv run janus status

# Review threshold boundaries
cat mal-core/src/mal_core/abm/tests/calibration/thresholds.yaml

# Check composite scorer weights
cat mal-core/src/mal_core/abm/tests/calibration/scorers/composite.py
```

## Development

### Adding a New Worker

1. Define the worker in `config/subagents.yaml`
2. Create the worker prompt in `prompts/per_subagent/`
3. Add edit permissions (glob patterns)
4. Test with `uv run janus agents show <worker-name>`

### Running Tests

```bash
cd agents/janus
uv run pytest

# Live tests (require external services)
uv run pytest -m live
```

### Customizing Prompts

Templates are in `prompts/`:
- `orchestrator.md.j2` — Main orchestrator prompt (Jinja2)
- `specialist.md.tmpl` — Worker prompt template
- `per_subagent/` — Per-worker customizations
