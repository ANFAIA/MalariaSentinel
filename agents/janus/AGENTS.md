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
- Workers share a single gawt worktree (no per-agent isolation)
- Never edit files directly from the orchestrator — dispatch specialists
- Always use `mcp__gitagent__edit_file` / `write_file` — never host Edit/Write
- Always call `register_agent` before editing (agent_id required on every call)
- Always call `start_intent` before first edit (semantic attribution)
- Always call `check_inbox` after each significant edit (conflict detection)
- gawt MCP uses SQLite internally — threading errors if called from wrong thread
- Only one gawt session can be open at a time (session singleton)
- `finalize_session` warns if agents still active — unregister first

## Scorer naming convention
Scorers follow the pattern `D<id>_<name>.py` where `<id>` is the next number (D1, D2, ... D10 currently).
Each scorer must be registered in `thresholds.yaml` with `min_score`, `max_delta`, and `hard_floor`.

## Dual-Mode Orchestrator (Centinela + Dispatcher)

### Architecture

Janus has **two orchestrator modes** sharing the same factory (`create_orchestrator()`):

```
create_orchestrator(mode="centinela")     create_orchestrator(mode="dispatcher")
  │                                         │
  ├─ prompt: orchestrator.md.j2             ├─ prompt: orchestrator.md.j2
  │  (rendered mode=centinela)               │  (rendered mode=dispatcher)
  │                                         │
  ├─ tools: onboard + ask_user              ├─ tools: search + gawt_mcp + ask_user
  │  + memory_kg + delegate_to_disp         │  + memory_kg
  │                                         │
  ├─ subagents: 8 specialists ✅             ├─ subagents: 8 specialists ✅
  │                                         │
  └─ backend: MalariasimShellBackend        └─ backend: MalariasimShellBackend
     (execute → malariasim only)              (execute → malariasim only)
```

Both modes run on `MalariasimShellBackend` — the built-in deepagents `execute`
tool (bash) is restricted to `malariasim` commands. Filesystem deny rules
(secrets, `/data/**`, `/.git/**`) are enforced as backend policy hooks instead
of `FilesystemPermission` (which is incompatible with execution backends).

### Delegation Model

```
Centinela (REPL, talks to user):
  ├─ Research:  task("abm", "[MODE:research] ...")     ← direct dispatch
  └─ Implement: delegate_to_dispatcher(goal="...")     ← opens gawt session

Dispatcher (goal-driven, one-shot):
  ├─ start_session → task("scoring", "[MODE:implementation] ...") → finalize
  └─ returns summary to centinela
```

- **Research tasks**: centinela dispatches directly via `task()` (no gawt session needed)
- **Implementation tasks**: centinela delegates to dispatcher via `delegate_to_dispatcher()` (dispatcher manages session lifecycle)
- **Quick questions**: centinela uses `onboard_ask_subagent(name, question)` (lightweight, single LLM call)

### Prompt Template

`prompts/orchestrator.md.j2` — Jinja2 template with two protocol sections:
- `{% if mode == "centinela" %}` — conversational REPL, explain-then-delegate, onboard tools
- `{% if mode == "dispatcher" %}` — decompose → session → dispatch → monitor → finalize

### Tool Matrix

| Tool | Centinela | Dispatcher | Subagents |
|---|---|---|---|
| `ask_user` | ✅ | ✅ | ✅ |
| `memory_recall_kg` | ✅ | ✅ | via plugin |
| `execute` (bash → `malariasim` only) | ✅ | ✅ | abm only |
| `onboard_status` | ✅ | ❌ | ❌ |
| `onboard_ask_subagent` | ✅ | ❌ | ❌ |
| `delegate_to_dispatcher` | ✅ | ❌ | ❌ |
| `gawt_mcp_*` | ❌ | ✅ | ✅ |
| `task()` (subagents) | ✅ | ✅ | ❌ |

**Shell access**: only the orchestrator and the `abm` specialist see the
`execute` tool, and it only runs `malariasim` commands (enforced by
`MalariasimShellBackend` policy hook in `malariasim_backend.py`). No custom
ABM execution tools (`abm_run`/`abm_test`/`abm_score`/`pipeline_*` were
removed). All other subagents have `execute` filtered out via
`ToolFilterMiddleware`.

### gawt MCP server (external dependency)
- Package: `gawt>=0.5.0` (branch `feat/mcp-sqlite-core`)
- Transport: stdio (MCP server at `gitagent-mcp`)
- Single shared worktree per session (`.gitagent/worktree/`)
- SQLite-backed state (`.gitagent/state.db`)
- Tools: `start_session`, `finalize_session`, `register_agent`, `edit_file`, `write_file`, `read_file`, `check_inbox`, `send_message`, `list_agents`, `list_edits`, `list_intents`

### Specialist workflow
Each specialist is a **planner + executor** in the shared worktree:

1. `register_agent(role=...)` → get agent_id
2. `read_file(plan.json)` → read manifest, find own entry
3. `start_intent(intent=...)` → declare work
4. `check_inbox()` → check for peer conflicts
5. `edit_file` / `write_file` → make edits (ALWAYS via gawt MCP)
6. `check_inbox()` → verify no conflicts after edit
7. `send_message(to=__orchestrator__, message="done: ...")` → report
8. `unregister_agent()` → clean up

### Subagent registry
- Config: `config/subagents.yaml` (8 subagents: abm, scoring, ingest, download, prediction, training, data, commonlib)
- Each subagent has: `spec`, `skills`, `gawt_role`, `can_call_via`, `edits_allow` (glob patterns), `plugins`
- `gawt_role` maps to the gawt `register_agent(role=...)` parameter

### Observability
- **LivePanel**: single-agent terminal panel (orchestrator's own stream)
- **MultiAgentPanel**: multi-agent rows (agent_id, role, intent, inbox)
- **SessionLogger**: JSONL in `runs/<session>/session.jsonl`
- **Langfuse SDK**: optional trace dashboard (`--tracing langfuse`)
- Tags: `agent:<role>`, `env:<env>`, `mode:centinela|dispatcher`, `stage:<phase>`, `tool:<category>`
- Dispatch spans: one per specialist, nested under root trace
- Delegation spans: dispatcher trace nested under centinela trace

### CLI
```
janus                          # centinela REPL (conversational)
janus --tracing langfuse       # with Langfuse tracing
janus onboard                  # same as bare janus
janus run -g "..."             # dispatcher (goal-driven)
janus run -g "..." --plan docs/plans/calibration.md
janus run -g "..." --tracing langfuse
janus improve -g "..."         # same as run (back-compat)
janus improve -g "..." --plan docs/plans/calibration.md
janus status                   # scorecards, plans, subagents
janus agents list              # all subagents
janus agents show abm          # one subagent's details
```

### Removed (M14 → M-AGENT → Dual-Mode)
- `sibling/` directory (intent, peer_message, watcher, ASTIndex, merge_preflight, recovery, coordination, fork, frame_stack, scan, state)
- `tools/gitagent_tool.py` (old gitagent CLI wrappers)
- `cycles/run_cycle.py` (7-phase methodology, replaced by dispatcher prompt)
- `cycles/improvement_cycle.py` (shim, replaced by direct run_improvement call)
- `tools/subagent_invoke.py` (handoff_to_improver, replaced by delegate_to_dispatcher)
- `plugins/sibling.py` (SiblingPlugin)
- `mailbox.py` (file-based mailbox)
- All `tools/mailbox_*.py`, `tools/claim_file.py`, `tools/peer_message_*.py`, `tools/fork_brief_tool.py`, `tools/merge_result_tool.py`, `tools/scope_validate.py`
- Deprecated CLI commands: `calibration`, `feature`, `research`
- `tools/abm_tools.py` (abm_run/abm_test/abm_score) + `tools/pipeline_tool.py` — replaced by the built-in `execute` tool restricted to `malariasim`
- `FilesystemPermission` on orchestrator/subagents — replaced by backend policy hooks in `malariasim_backend.py` (incompatible with execution-capable backends)

### Files
```
agents/janus/src/agents_janus/
├── agent.py                    # create_orchestrator (dual-mode: centinela + dispatcher)
├── cli.py                      # CLI entry (run, improve, onboard, status)
├── improvement.py              # run_improvement (dispatcher stream)
├── onboarding.py               # centinela REPL (conversational)
├── live_panel.py               # LivePanel + MultiAgentPanel
├── observability.py            # ObservabilityMiddleware (mode tag, Langfuse)
├── logger.py                   # SessionLogger (JSONL)
├── scope_validator.py          # validate_edit_scope
├── manifest.py                 # session manifest CRUD
├── malariasim_backend.py       # MalariasimShellBackend (execute → malariasim only)
├── middleware/                 # ToolFilterMiddleware (excludes execute from non-abm)
├── config/subagents.yaml       # 8 subagent definitions
├── plugins/                    # Plugin chain (per-domain)
├── subagents/                  # Registry, builder, base types
├── tools/                      # KG, ask_user, delegate_to_dispatcher, onboard_tools
├── prompts/                    # orchestrator.md.j2, specialist.md.tmpl, per_subagent/
└── tests/                      # unit, integration, LLM-as-judge tests
```
