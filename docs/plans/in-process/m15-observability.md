# M15 — Janus Observability (Live Panel + Langfuse)

> **Status**: Drafting (2026-08-03). Awaiting first commit.
>
> **Predecessor**: M14 — Two-Tier Orchestrator + Specialised Subagents (`docs/plans/completed/m14-orchestrator-plugin-system.md` — was `in-process`, now complete after commit `46fadfb`).
>
> **Sibling work**: M12 — Water Datasets (`docs/plans/in-process/m12-water-datasets.md`), M13 — Daily Env NC (`docs/plans/in-process/m13-daily-env-nc.md`).
>
> **Scope**: Add real-time terminal visibility and a self-hosted Langfuse trace dashboard to `janus improve` / `janus run`. No `mal-core` changes. No changes to existing JSONL log format. No new subagent or plugin — observability is a cross-cutting concern.
>
> **Deploy split**: This plan has two owners. **Janus code lives on the Mac** (this repo, monorepo). **Langfuse infra lives on the user's Raspberry Pi 4 8GB**, deployed via Dockploy from the artifact at `agents/janus/deploy/langfuse-compose.yml`.

## 0. Why this plan exists now

Three concrete pains, in the user's words:

> "I'm running `janus improve -g 'Implement M13' --plan ...` and I don't have any kind of interactivity or visibility into what the agents think or do. I don't know when the system is stuck, or when it might have done something I don't want, or when to stop it."

The M14 work shipped a robust orchestrator (subagents, plugins, mailbox, scope validator, scorer-after-abm) but **left the operator blind during runs**. Logs go to `runs/deepagent-*/session.jsonl` but the terminal shows nothing until the agent's final response — sometimes 10+ minutes later. When the agent does something unexpected, the operator only finds out after the fact.

Three independent gaps:

1. **No live visibility** — `agent.stream(..., stream_mode="updates")` is consumed but only `full_messages` is appended and the terminal is silent.
2. **No stuck-detection** — `Lurking at 0% CPU` for 5 minutes could mean the agent is reasoning (fine), waiting on a hung subprocess (bad), or stuck in a tool-call loop (very bad). There's no watchdog.
3. **No abort semantics** — Ctrl-C today kills mid-flight; partial session left in `runs/<ts>/`; no summary of what happened. Re-running is wasteful.

Plus a fourth, latent gap: **no team-shareable trace UI**. The JSONL is excellent for `jq` grepping but useless for showing a colleague what the agent did. Langfuse (or LangSmith) gives a free web dashboard.

## 1. Three layers, two of which ship in M15

| # | Layer | In M15? | Status | What it solves |
|---|---|---|---|---|
| 1 | **Live terminal panel** | ✅ | always-on | "What is the agent doing right now?" |
| 2 | **SQLite trace + replay CLI** | ❌ | deferred to M16 | "Show me what happened in session X" |
| 3 | **Langfuse exporter + self-host** | ✅ | opt-in (`--tracing langfuse`) | "Share a trace URL with my team" |

Layer 2 is explicitly out of scope per the user: "Quédemonos solo con langfuse en local y con live panel. Es lo más rápido y directo para solucionar todos mis problemas." If we need replay later, M16 adds SQLite + `janus trace list/show/replay/diff`.

## 2. Architecture

```
                  janus improve -g "..." --plan ... [--tracing langfuse]
                                  │
                                  ▼
                ┌────────────────────────────────┐
                │  agent.stream(updates) loop    │  ← Ctrl-C handler
                │  in improvement.py / run_cycle │
                └────────────────────────────────┘
                                  │ (every event)
                  ┌───────────────┼───────────────┐
                  ▼               ▼               ▼
            Live Panel       JSONL Log       Langfuse SDK
          (rich.Live UI)    (existing)      (opt-in flag)
            always on       always on       --tracing langfuse
            --quiet off                    LANGFUSE_HOST/PK/SK
                                               │
                                               ▼
                                  https://<tunnel>.example.com
                                       (langfuse UI on Pi)
```

Three sinks, all fed by the same `ObservabilityMiddleware` events. JSONL stays the canonical ground truth (zero behavior change for existing runs). Live + Langfuse are new sinks, each toggleable. The `SessionLogger._append()` method is the single fan-out point — change there, propagate everywhere.

## 3. Live Panel (`agents/janus/src/agents_janus/live_panel.py` — new, ~180 lines)

### 3.1 Responsibilities
- Render a `rich.Live` panel showing current step, last tool call, last LLM preview, running token totals, elapsed time.
- Detect idle state (no event in >30s) and flash a stuck-warning inside the panel.
- Catch Ctrl-C, flush all sinks (JSONL + Langfuse), print a one-line summary, exit 130.
- Respect `--quiet`: when true, render nothing to stdout but keep the watchdog + abort hooks active.

### 3.2 Public API

```python
from agents_janus.live_panel import LivePanel

with LivePanel(session_id="janus-20260803-142358", quiet=False) as panel:
    for event in agent.stream(updates, stream_mode="updates"):
        panel.on_event(event)         # render + watchdog reset

# OR for the abort path:
panel.abort(reason="user_ctrl_c")     # prints summary, raises KeyboardInterrupt
```

`on_event(event)` is called for every `{node_name: delta}` dict from `agent.stream()`. The panel keeps an internal `PanelState` object with: `current_step`, `last_llm_preview`, `last_tool`, `tokens`, `started_at`, `stuck_warning`.

### 3.3 Panel layout (rendered at ≥2 Hz)

```
╭─ 🩺 janus · session=janus-20260803-142358 · elapsed=02:14 ─────────────────╮
│                                                                          │
│  🧠 step 12 · model=xiaomi/mimo-v2.5 · prompt=2301 tok                  │
│  ┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄  │
│  Last: "Run calibration with seed=1, days=365 to confirm baseline..."   │
│                                                                          │
│  🔧 last tool · abm_run · 7.3s · input={seed:1, days:365}               │
│  Output preview: "completed in 7.3s, 4802 daily records"                │
│                                                                          │
│  Tokens · prompt=47,233 · completion=4,891 · total=52,124               │
│                                                                          │
╰──────────────────────────────────────────────────────────────────────────╯
```

When idle >30s:
```
│  ⏱ idle 47s — agent may be waiting on tool or stuck                    │
│     Press Ctrl-C to abort cleanly                                       │
```

### 3.4 Watchdog

`Live.update(refresh_per_second=4)` runs a render thread ~4 Hz. The panel records `last_event_at = time.monotonic()` on every `on_event()`. The render thread checks `now - last_event_at`:

- `< 30s` → no warning
- `≥ 30s, never warned` → set `stuck_warning = "⏱ idle {N}s — ..."`, render in red border
- `≥ 30s, already warned` → extend the warning with elapsed, but don't keep re-flashing

Threshold is a class constant `IDLE_WARN_S = 30` (per user confirmation 2026-08-03). Easy to tune later if 30s triggers too many false positives.

### 3.5 Ctrl-C handler

The `LivePanel` context manager installs a SIGINT handler that:

1. Sets `panel.state.aborted = True` so the next render shows "⚠ aborting..."
2. Calls `SessionLogger.log_decision("aborted_by_user", detail)`
3. Calls `langfuse.flush()` if active (Langfuse SDK has buffered spans)
4. Calls `SessionLogger.close()` to write the session_end marker
5. Prints one line to stderr: `"⚠ session aborted. logs at runs/<session>/session.jsonl. exit 130"`
6. Raises `KeyboardInterrupt` so the CLI exits 130

Outside a `LivePanel`, the existing default `KeyboardInterrupt` behavior is unchanged (raw crash, partial JSONL). The panel is opt-in per orchestrator entrypoint.

## 4. Wiring into orchestrators

### 4.1 `improvement.py` (~lines 67-89)

Replace:
```python
try:
    agent = agent_mod.create_orchestrator(...)
    full_messages = []
    for event in agent.stream({...}, stream_mode="updates"):
        if isinstance(event, dict):
            for node_name, delta in event.items():
                if isinstance(delta, dict) and "messages" in delta:
                    for msg in delta["messages"]:
                        if hasattr(msg, "content") and msg.content:
                            full_messages.append({...})
    ...
finally:
    logger.close()
```

With:
```python
from agents_janus.live_panel import LivePanel

with LivePanel(session_id=logger.session_dir.name, quiet=quiet) as panel:
    try:
        agent = agent_mod.create_orchestrator(...)
        full_messages = []
        for event in agent.stream({...}, stream_mode="updates"):
            panel.on_event(event)
            if isinstance(event, dict):
                for node_name, delta in event.items():
                    if isinstance(delta, dict) and "messages" in delta:
                        for msg in delta["messages"]:
                            if hasattr(msg, "content") and msg.content:
                                full_messages.append({...})
        final_content = full_messages[-1]["content"] if full_messages else "No response"
        logger.log_summary(final_content)
        return final_content
    except KeyboardInterrupt:
        # LivePanel already printed summary + flushed. Just propagate.
        raise
    finally:
        logger.close()
```

The `LivePanel` owns the SIGINT hook; we just let exceptions propagate.

### 4.2 `cycles/run_cycle.py` (~lines 281-315)

Same pattern. Identical changes inside the `try` block, plus `from agents_janus.live_panel import LivePanel` at the top.

### 4.3 `cli.py` — new flags

```python
@app.command()
def improve(
    goal: str = typer.Option(None, "--goal", "-g", ...),
    plan: str = typer.Option(None, "--plan", ...),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Disable live panel. JSONL + Langfuse still emit."),
    tracing: str = typer.Option("", "--tracing", help="Tracing backend. Empty = no extra tracing. 'langfuse' = enable Langfuse."),
    provider: str = typer.Option("openrouter", ...),
    model: str = typer.Option("xiaomi/mimo-v2.5", ...),
    thread_id: str = typer.Option("improvement-session", ...),
    no_verify: bool = typer.Option(False, ...),
):
    ...
    result = run_improvement(
        goal=goal, plan_path=plan, provider=provider, model=model,
        thread_id=thread_id, quiet=quiet, tracing=tracing,
    )
```

Same changes for `run` (the deprecated `calibration` / `feature` / `research` aliases don't need the flag — they're hidden anyway). The `--tracing` value also reads from `JANUS_TRACING` env var as a project-wide default: if `JANUS_TRACING=langfuse` is set in `.env`, `--tracing` is optional.

`JANUS_TRACING` resolution:
```python
tracing = tracing or os.environ.get("JANUS_TRACING", "")
```

## 5. Langfuse SDK wiring (`observability.py` — extend)

### 5.1 Constructor change

```python
class ObservabilityMiddleware(AgentMiddleware):
    def __init__(self, session_logger, langfuse_client=None):
        self.logger = session_logger
        self.langfuse = langfuse_client
        ...
```

If `langfuse_client` is `None`, behavior is identical to today. Zero behavior change for users without `--tracing langfuse`.

### 5.2 Trace structure

Each `janus improve` / `janus run` call becomes one Langfuse **trace**. Sub-calls become nested observations:

```
Trace: "janus-improve goal='Implement M13' plan=m13-daily-env-nc.md"
├── Span: agent_start
├── Generation: llm_call #1 (model=xiaomi/mimo-v2.5, tokens=2301+186, latency=3.5s)
├── Span: tool_call abm_run (input={seed:1, days:365}, output_preview=..., latency=7.3s)
├── Generation: llm_call #2 (…)
├── Span: tool_call gitagent_spawn (input={feature:...}, output=..., latency=0.5s)
├── Generation: llm_call #3
├── … (one span/generation per LLM or tool call)
└── Span: agent_end (summary=..., llm_calls=N, tool_calls=M, total_tokens=...)
```

### 5.3 Event mapping

| JSONL event | Langfuse observation | Why |
|---|---|---|
| `agent_start` | `trace.update()` + top-level span | One trace per session |
| `llm_call_start` | `langfuse.generation(name="llm_call", …)` open | Open span w/ model + start time |
| `llm_call` (end) | `generation.end(usage=…, output=…)` | Close with tokens + preview |
| `llm_response` | merged into `generation.end()` | Same observation, no separate span |
| `tool_call` / `tool_call_detailed` | `langfuse.span(name=tool_name, input=…, output=…)` | Tool execution |
| `tool_error` | `span.end(status="error", error=…)` | Error tagging |
| `agent_end` | `trace.update(end_time=…)` | Close trace |

The current `_llm_call_count` / `_tool_call_count` counters in `ObservabilityMiddleware` are reused for span IDs / names so the Langfuse UI shows them in order.

### 5.4 Flush on every exit path

`langfuse.flush()` is **critical** — the SDK buffers spans and ships them in batches. If we don't flush on abort, the trace is lost. The flush point:

```python
def after_agent(self, state, runtime):
    ...
    if self.langfuse:
        self.langfuse.flush()    # ship to langfuse before exit
```

The `LivePanel.abort()` path also calls `langfuse.flush()` if a Langfuse client is wired.

### 5.5 Error containment

Langfuse SDK can throw (network down, malformed event). Wrap every `self.langfuse.<call>()` in `try/except Exception as e: logger._append({"event": "langfuse_error", "error": str(e)})` and continue. Langfuse failures **never** abort a janus run.

## 6. Langfuse self-host deploy — owner's side (user)

This plan does **not** edit `agents/memory/runtime/docker-compose.yml`. Instead, a stand-alone artifact ships at `agents/janus/deploy/langfuse-compose.yml` for the user to copy into Dockploy.

### 6.1 Why not the existing compose

`agents/memory/runtime/docker-compose.yml` is the project's core stack (Neo4j + Graphiti MCP). Mixing langfuse there would:

1. Bloat the Neo4j/Graphiti-only stack file with unrelated services
2. Make langfuse deploy lifecycle (restart on Pi) coupled to memory subsystem lifecycle
3. Hide the deployment instruction from `agents/janus/` where janus users will look for it

### 6.2 Compose artifact (5 services)

```yaml
# agents/janus/deploy/langfuse-compose.yml
# Copy this into Dockploy as a new app on the Pi (Raspberry Pi 4 8GB).
# Pi 4 8GB is comfortable: ~2GB idle, ~4GB under load.
#
# First boot: open https://<your-cloudflared-tunnel>, sign up, create a project,
# copy LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY into your Mac's .env file.
# Cloudflared config is separate — point at langfuse-web:3000.

services:
  langfuse-clickhouse:
    image: clickhouse/clickhouse-server:24.3
    restart: unless-stopped
    volumes:
      - clickhouse_data:/var/lib/clickhouse
    environment:
      CLICKHOUSE_DB: langfuse
      CLICKHOUSE_USER: ${LANGFUSE_CLICKHOUSE_USER:-langfuse}
      CLICKHOUSE_PASSWORD: ${LANGFUSE_CLICKHOUSE_PASSWORD:-langfuse_pw}
      CLICKHOUSE_DEFAULT_ACCESS_MANAGEMENT: 1
    healthcheck:
      test: ["CMD", "wget", "-q", "--spider", "http://localhost:8123/ping"]
      interval: 10s
      timeout: 5s
      retries: 10
      start_period: 30s

  langfuse-postgres:
    image: postgres:16-alpine
    restart: unless-stopped
    volumes:
      - langfuse_pg:/var/lib/postgresql/data
    environment:
      POSTGRES_DB: ${LANGFUSE_PG_DB:-langfuse}
      POSTGRES_USER: ${LANGFUSE_PG_USER:-langfuse}
      POSTGRES_PASSWORD: ${LANGFUSE_PG_PASSWORD:-langfuse_pw}
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${LANGFUSE_PG_USER:-langfuse}"]
      interval: 10s
      timeout: 5s
      retries: 10

  langfuse-redis:
    image: redis:7-alpine
    restart: unless-stopped
    volumes:
      - langfuse_redis:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  langfuse-worker:
    image: langfuse/langfuse-worker:3
    restart: unless-stopped
    depends_on:
      langfuse-postgres:
        condition: service_healthy
      langfuse-redis:
        condition: service_healthy
      langfuse-clickhouse:
        condition: service_healthy
    environment:
      DATABASE_URL: postgresql://${LANGFUSE_PG_USER:-langfuse}:${LANGFUSE_PG_PASSWORD:-langfuse_pw}@langfuse-postgres:5432/${LANGFUSE_PG_DB:-langfuse}
      REDIS_URL: redis://langfuse-redis:6379
      CLICKHOUSE_URL: clickhouse://${LANGFUSE_CLICKHOUSE_USER:-langfuse}:${LANGFUSE_CLICKHOUSE_PASSWORD:-langfuse_pw}@langfuse-clickhouse:8123/${LANGFUSE_CLICKHOUSE_DB:-langfuse}
      CLICKHOUSE_MIGRATION_URL: clickhouse://${LANGFUSE_CLICKHOUSE_USER:-langfuse}:${LANGFUSE_CLICKHOUSE_PASSWORD:-langfuse_pw}@langfuse-clickhouse:8123/${LANGFUSE_CLICKHOUSE_DB:-langfuse}
      SALT: ${LANGFUSE_SALT:-change-me-in-production-please-32-chars}
      TELEMETRY_ENABLED: "false"
      LANGFUSE_LOG_LEVEL: info

  langfuse-web:
    image: langfuse/langfuse:3
    restart: unless-stopped
    ports:
      - "3000:3000"   # bind to Pi's localhost; cloudflared exposes to internet
    depends_on:
      langfuse-postgres:
        condition: service_healthy
      langfuse-redis:
        condition: service_healthy
      langfuse-clickhouse:
        condition: service_healthy
      langfuse-worker:
        condition: service_started
    environment:
      DATABASE_URL: postgresql://${LANGFUSE_PG_USER:-langfuse}:${LANGFUSE_PG_PASSWORD:-langfuse_pw}@langfuse-postgres:5432/${LANGFUSE_PG_DB:-langfuse}
      REDIS_URL: redis://langfuse-redis:6379
      CLICKHOUSE_URL: clickhouse://${LANGFUSE_CLICKHOUSE_USER:-langfuse}:${LANGFUSE_CLICKHOUSE_PASSWORD:-langfuse_pw}@langfuse-clickhouse:8123/${LANGFUSE_CLICKHOUSE_DB:-langfuse}
      CLICKHOUSE_MIGRATION_URL: clickhouse://${LANGFUSE_CLICKHOUSE_USER:-langfuse}:${LANGFUSE_CLICKHOUSE_PASSWORD:-langfuse_pw}@langfuse-clickhouse:8123/${LANGFUSE_CLICKHOUSE_DB:-langfuse}
      SALT: ${LANGFUSE_SALT:-change-me-in-production-please-32-chars}
      NEXTAUTH_SECRET: ${LANGFUSE_NEXTAUTH_SECRET}
      NEXTAUTH_URL: ${LANGFUSE_NEXTAUTH_URL:-http://localhost:3000}
      LANGFUSE_INIT_ORG_ID: ${LANGFUSE_INIT_ORG_ID:-malaria-sentinel}
      LANGFUSE_INIT_PROJECT_ID: ${LANGFUSE_INIT_PROJECT_ID:-janus}
      LANGFUSE_INIT_PROJECT_NAME: ${LANGFUSE_INIT_PROJECT_NAME:-Janus}
      LANGFUSE_INIT_PROJECT_PUBLIC_KEY: ${LANGFUSE_INIT_PROJECT_PUBLIC_KEY}
      LANGFUSE_INIT_PROJECT_SECRET_KEY: ${LANGFUSE_INIT_PROJECT_SECRET_KEY}
      LANGFUSE_INIT_USER_EMAIL: ${LANGFUSE_INIT_USER_EMAIL}
      LANGFUSE_INIT_USER_PASSWORD: ${LANGFUSE_INIT_USER_PASSWORD}
      LANGFUSE_INIT_USER_NAME: ${LANGFUSE_INIT_USER_NAME:-Janus Admin}
      TELEMETRY_ENABLED: "false"
      LANGFUSE_LOG_LEVEL: info

volumes:
  clickhouse_data:
  langfuse_pg:
  langfuse_redis:
```

The `LANGFUSE_INIT_*` env vars are **optional** (only set if you want langfuse to bootstrap a default org/project/user on first boot). If unset, the user signs up manually the first time they open the URL — matches the official langfuse quickstart path (per user decision 2026-08-03: "Manual signup, copy keys").

### 6.3 Dockploy deployment steps (user-side)

1. In Dockploy: create a new app on the Pi, paste `agents/janus/deploy/langfuse-compose.yml`.
2. Set env vars: `LANGFUSE_NEXTAUTH_SECRET` (any 32+ char random), `LANGFUSE_SALT` (any 32+ char random). The `LANGFUSE_INIT_*` vars are optional.
3. Deploy. Wait ~2-3 min for first-boot migrations (clickhouse + postgres init + langfuse DB migrations).
4. Open `https://<your-tunnel>` → sign up → create a project named `janus` → copy `PUBLIC_KEY` + `SECRET_KEY` from project settings.
5. Add to Mac's `.env` (project root):
   ```
   LANGFUSE_HOST=https://<your-tunnel>
   LANGFUSE_PUBLIC_KEY=pk-lf-...
   LANGFUSE_SECRET_KEY=sk-lf-...
   JANUS_TRACING=langfuse
   ```
6. Cloudflared config (separate from this plan): `cloudflared tunnel route <tunnel> langfuse-web:3000`.

### 6.4 Pi 4 8GB sizing

| Service | Idle RAM | Under load |
|---|---|---|
| langfuse-clickhouse | ~500MB | ~1.5GB |
| langfuse-postgres | ~150MB | ~400MB |
| langfuse-redis | ~30MB | ~100MB |
| langfuse-worker | ~250MB | ~500MB |
| langfuse-web (Next.js) | ~300MB | ~700MB |
| **Total** | **~1.2GB** | **~3.2GB** |

Pi 4 8GB has 4-5GB headroom even at load. No swap, no special tuning needed.

## 7. pyproject.toml changes

```toml
[project]
dependencies = [
    # ... existing deps ...
]

[project.optional-dependencies]
observability = [
    "langfuse>=3.0",
]
```

Install with: `uv pip install -e 'agents/janus[observability]'`.

`langfuse>=3.0` is the v3 SDK with the clean Python API (`from langfuse import Langfuse`). The v2 API had `langfuse_context` and decorator patterns that changed between minor versions. v3 is stable as of mid-2026 and matches the Langfuse self-host v3 server image.

## 8. Tests

### 8.1 `tests/test_live_panel.py` (new, ~150 lines)

- `test_render_basic` — call `panel.on_event({event_type: llm_call, ...})` 3 times, snapshot `panel.render()` output, assert it shows step count, last tool, tokens.
- `test_idle_watchdog_fires_at_30s` — set `last_event_at = now - 31s`, call `_render_for_test()`, assert `stuck_warning` is set.
- `test_idle_watchdog_no_warning_under_30s` — set `last_event_at = now - 5s`, assert no warning.
- `test_quiet_mode_no_renders` — instantiate with `quiet=True`, call `on_event` 5 times, assert `live` is None (no rich Live instance).
- `test_abort_calls_flush_and_logs` — mock `SessionLogger`, mock `langfuse_client`, call `panel.abort()`, assert both were called.
- `test_ctrl_c_propagates_keyboardinterrupt` — wrap in `with panel: raise KeyboardInterrupt`, assert the panel caught and re-raised cleanly.

Use `rich.console.Console(record=True)` to capture render output for snapshot assertions.

### 8.2 `tests/test_langfuse_emit.py` (new, ~120 lines)

Mock the `langfuse.Langfuse` class. Tests:
- `test_llm_call_emits_generation` — feed an `llm_call` event into the middleware, assert `mock_client.generation()` was called with model + tokens + output.
- `test_tool_call_emits_span` — feed a `tool_call` event, assert `mock_client.span()` was called.
- `test_agent_start_creates_trace` — call `before_agent`, assert `mock_client.update()` was called with session_id + name.
- `test_flush_called_on_agent_end` — call `after_agent`, assert `mock_client.flush()` was called.
- `test_langfuse_error_does_not_crash` — make `mock_client.generation()` raise `Exception`, assert middleware doesn't propagate.
- `test_no_langfuse_when_disabled` — instantiate middleware without langfuse_client, call all hooks, assert no langfuse calls and no errors.

### 8.3 Existing tests

All 8 `test_subagents.py` tests must still pass (no changes to subagents / plugins). Run:
```bash
cd agents/janus && uv run pytest -v
```

## 9. Acceptance criteria

- [ ] `janus improve -g "..."` shows live `rich.Live` panel from first LLM event onward
- [ ] Panel refreshes ≥2×/sec; displays step number, last tool name, last result preview, running token totals, elapsed time
- [ ] After 30s without an event, panel shows "⏱ idle 30s — agent may be waiting on tool or stuck" in a distinct color
- [ ] Ctrl-C during a run prints "⚠ session aborted" + session_id + log path to stderr, exits 130
- [ ] `langfuse.flush()` is called on success, abort, and exception paths (no trace lost)
- [ ] `--quiet` flag disables the live panel but keeps JSONL + watchdog + abort hooks
- [ ] `--tracing langfuse` reads `LANGFUSE_HOST`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY` from env and emits traces to the langfuse server
- [ ] One `janus improve` call creates one Langfuse trace with one nested span per LLM call and tool call
- [ ] Langfuse SDK errors (network down, malformed event) never abort a janus run — they're logged and the run continues
- [ ] `docker compose up` (in Dockploy) brings langfuse at `https://<your-tunnel>` on first deploy
- [ ] All 8 existing `test_subagents.py` tests still pass + 12 new tests pass
- [ ] `AGENTS.md` updated with the new flags + langfuse section + network diagram

## 10. Out of scope (defer to M16+)

| Item | Reason |
|---|---|
| SQLite trace replay CLI (`janus trace list/show/replay/diff`) | User explicitly excluded for M15. JSONL stays the canonical log. |
| LangSmith backend | langfuse is the chosen path. LangSmith would be a parallel exporter if needed later. |
| Live tail to browser | Live terminal panel covers this for now. Could add a websocket streamer later. |
| Token cost dashboard | Langfuse UI shows token costs in the trace view — that satisfies the basic need. Dedicated dashboards in M16+. |
| Alerts (webhook on stuck/error) | Watchdog warning in the panel is enough for one operator. Alerts matter when there are many concurrent runs. |
| Persistence of `--tracing` choice | Today it's per-CLI-flag. If we want to make `JANUS_TRACING=langfuse` the default in `.env`, that's covered — no extra config layer needed. |

## 11. File summary

| File | Action | LoC |
|---|---|---|
| `agents/janus/src/agents_janus/live_panel.py` | **create** | ~180 |
| `agents/janus/src/agents_janus/improvement.py` | modify | +12, -8 |
| `agents/janus/src/agents_janus/cycles/run_cycle.py` | modify | +12, -8 |
| `agents/janus/src/agents_janus/cli.py` | modify | +24, -8 |
| `agents/janus/src/agents_janus/observability.py` | modify | +90, -0 |
| `agents/janus/pyproject.toml` | modify | +6, -0 |
| `agents/janus/deploy/langfuse-compose.yml` | **create** | ~110 |
| `agents/janus/deploy/README.md` | **create** | ~80 |
| `agents/janus/src/agents_janus/tests/test_live_panel.py` | **create** | ~150 |
| `agents/janus/src/agents_janus/tests/test_langfuse_emit.py` | **create** | ~120 |
| `AGENTS.md` | modify | +25, -0 |
| `docs/plans/in-process/m15-observability.md` | **create** (this file) | ~360 |
| KB node `op-m15-observability` | **create** via `memory_node` | 1 |
| **Total new** | | **~960** |
| **Total modified** | | **~125** |

## 12. Open questions

None at time of writing. Resolved during planning:
- ✅ Langfuse auth: manual signup + copy keys (per user 2026-08-03)
- ✅ Watchdog threshold: 30s idle (per user 2026-08-03)
- ✅ Scope: only langfuse + live panel (per user 2026-08-03)
- ✅ Compose location: `agents/janus/deploy/` (per user 2026-08-03)
- ✅ Pi reachability: Cloudflare tunnel (per user 2026-08-03)
- ✅ Pi specs: Pi 4 8GB (per user 2026-08-03)

If any of these change during implementation, this file is updated and a new commit is added with a "Plan amendment" note.

## 13. Execution order (when approved)

1. Create `live_panel.py` (skeleton, no events yet) + `test_live_panel.py` (skeleton tests)
2. Wire `LivePanel` into `improvement.py` + `cycles/run_cycle.py` (just `with panel` + `panel.on_event(event)`, no real render)
3. Add `--quiet` flag to `cli.py`
4. Verify the panel actually renders: `janus improve -g "ls -la"` (trivial goal that finishes in 2-3 steps)
5. Add watchdog logic + Ctrl-C handler
6. Verify watchdog: run a goal that takes 60s with no events, confirm warning fires
7. Verify Ctrl-C: run a long goal, hit Ctrl-C, confirm exit 130 + log entry
8. Add langfuse SDK to `pyproject.toml` (`[observability]` extra)
9. Extend `observability.py` with langfuse emitter (mocked in tests)
10. Verify event mapping with `test_langfuse_emit.py` — all 6 tests pass
11. Add `--tracing langfuse` flag + `JANUS_TRACING` env to `cli.py`
12. Create `agents/janus/deploy/langfuse-compose.yml` + `agents/janus/deploy/README.md`
13. Update `AGENTS.md` with M15 section
14. Record KB node `op-m15-observability`
15. Commit (single commit or split into 2-3 logical commits — judgement call)
16. Update M15 status line at top of this file from "Drafting" to "Completed"

Step 15 decision: I'll split into 3 commits:
- `feat(M15): live panel with stuck-detection and graceful abort` (steps 1-7)
- `feat(M15): langfuse SDK wiring + self-host deploy artifact` (steps 8-12)
- `docs(M15): observability section + KB node` (steps 13-14)

The plan file move (step 16) goes in commit 3.