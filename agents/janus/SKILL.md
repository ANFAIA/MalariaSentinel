---
name: janus-orchestrator
description: 'LangChain deepagents-based multi-agent orchestrator for MalariaSentinel ABM calibration. Use when running calibration cycles, spawning worker agents, or improving ABM parameters.'
---

# Janus Orchestrator

Multi-agent orchestrator for MalariaSentinel ABM calibration improvement.

## Commands

```bash
# Calibration improvement cycle
uv run python -m agents.janus calibration --max-iterations 10

# Feature development cycle
uv run python -m agents.janus feature "name" "description"

# Research + improvement cycle
uv run python -m agents.janus research "topic" --cycles 3

# Dry-run (prints prompt without executing)
uv run python -m agents.janus calibration --dry-run
```

## Workers

- `abm-worker`: Modifies C++ ABM parameters
- `scorer-worker`: Modifies Python calibration scorers
- `feature-worker`: Implements new features in mal-core

## Provider

Default: `openrouter:xiaomi/mimo-v2.5`

Set `OPENROUTER_API_KEY` env var for OpenRouter access.
