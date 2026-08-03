# MalariaSentinel Janus — Memory File

## Project conventions
- ABM C++ code lives in `mal-core/src/mal_core/abm/` (headers: `params.h`, `wire.hpp`, `engine.hpp`)
- Calibration scorers live in `mal-abm-fast/tests/calibration/scorers/`
- Thresholds are in `mal-abm-fast/tests/calibration/thresholds.yaml`
- Composite scorer is `mal-abm-fast/tests/calibration/scorers/composite.py`
- Tests run with: `cd mal-abm-fast/tests/calibration && uv run pytest -m fast -v`
- Python modules are in `mal-core/src/mal_core/`
- The monorepo uses `uv` for dependency management

## Known pitfalls
- Don't weaken tests or skip scorers to force a pass
- Always compare against the best historical composite score
- Maximum 3 parallel workers at a time
- Workers must run in isolated gitagent worktrees
- Never edit files directly from the orchestrator — always spawn a worker

## Scorer naming convention
Scorers follow the pattern `D<id>_<name>.py` where `<id>` is the next number (D1, D2, ... D10 currently).
Each scorer must be registered in `thresholds.yaml` with `min_score`, `max_delta`, and `hard_floor`.

## M14 Architecture (Two-Tier Orchestrator + Plugin System)

### Two orchestrators
- **Onboarding** (`janus onboard`): read-only, YAML-menu-driven, hands off to improver.
- **Improvement** (`janus improve -g "..."`): edit-capable, goal-driven, uses registry + plugin chain.

### Subagent registry
- Config: `config/subagents.yaml` (8 subagents + 1 read-only research).
- Each subagent has: `spec` (path to spec.md), `skills`, `mailbox_inbox`, `edits_allow` (glob patterns), `plugins`.

### Plugin model
- `Plugin` ABC at `plugins/base.py` — transformer over `SubagentSpec` → `ResolvedSubagent`.
- `EditPlugin`: added by improver (worktree-scoped writes).
- `ReadOnlyPlugin`: added by onboarding (deny-all writes).
- Per-subagent plugins: scoring, download, ingest, training, prediction, data, commonlib, research.

### Inter-agent mailbox
- File-based at `runs/<session>/mailbox/{inbox,outbox}-<name>/`.
- Three tools: `mailbox_send`, `mailbox_check_inbox`, `mailbox_mark_resolved`.
- Every subagent checks inbox before editing.

### Scope validator
- Plain Python (not LLM). Runs after `gitagent_proposals`, before `gitagent_integrate`.
- Validates diff paths against `edits_allow` globs. Cross-scope → mailbox + block. Unowned → ask_user.

### Scorer-after-ABM
- `ScorerPlugin.after_task` auto-runs `score_then_compare` after any ABM subagent task.
- Writes scorecard, compares vs best history, tags regression/promotion/keep.

### Plans
- `docs/plans/in-process/*.md` are NOT auto-loaded. Improver accepts `--plan PATH` as explicit hint only.

### CLI
```
janus onboard                # interactive menu
janus improve -g "..."       # improver (live panel by default)
janus improve -g "..." --plan docs/plans/in-process/m12.md
janus improve -g "..." --quiet           # suppress live panel
janus improve -g "..." --tracing langfuse  # + langfuse dashboard
janus status                 # scorecards, plans, subagents
janus agents list            # all subagents
janus agents show abm        # one subagent's details
janus run -g "..."           # back-compat alias
```

## M15 Observability (Live Panel + Langfuse)

### Live terminal panel (`live_panel.py`)

A `rich.Live` panel renders while `agent.stream()` is consuming events.

- Shows: session id, elapsed time, current LLM step + model, last LLM preview,
  last tool name + input + output preview + latency, running token totals.
- Refreshes 4 Hz.
- **Idle watchdog**: 30s without an event → "⏱ idle Ns — agent may be waiting
  on tool or stuck (Ctrl-C to abort)" appears in red border.
- **Ctrl-C handler**: graceful abort — fires `_on_abort` callback, calls
  `langfuse.flush()`, prints summary, raises `KeyboardInterrupt` (exit 130).
- `--quiet` flag disables the rich render but keeps watchdog + abort hooks.

### Three sinks, one fan-out

`ObservabilityMiddleware` emits events to all three sinks:

1. **SessionLogger** → JSONL in `runs/<session>/session.jsonl` (always on).
2. **LivePanel** → terminal (on by default, `--quiet` to disable).
3. **Langfuse SDK** → self-hosted langfuse UI (opt-in via `--tracing langfuse`
   or `JANUS_TRACING=langfuse`).

A sink failure never aborts the run — errors are logged to JSONL
(`event: "langfuse_error"`) and ignored.

### Langfuse self-host

- Deploy artifact: `agents/janus/deploy/langfuse-compose.yml` (5 services).
- Pi target: Raspberry Pi 4 8GB. ~1.2GB idle, ~3.2GB under load.
- Reach from Mac via Cloudflare tunnel — see `agents/janus/deploy/README.md`.
- Mac env: `LANGFUSE_HOST`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`.
- Install SDK: `uv pip install -e 'agents/janus[observability]'`.

### Trace structure in langfuse

One trace per `janus improve` / `janus run`. Nested observations:
- `generation` per LLM call (model + tokens + latency + preview).
- `span` per tool call (input + output + latency; marked ERROR on failure).
- Top-level metadata: session_id, llm_calls, tool_calls, token totals.

`langfuse.flush()` is called on every exit path (success, abort, exception)
so no trace is ever lost.
