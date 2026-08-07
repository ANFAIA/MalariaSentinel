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

## M-AGENT Architecture (gawt MCP-native dispatcher)

### Architecture overview
Janus is a **dispatcher orchestrator** that coordinates specialist agents via gawt MCP.
The orchestrator decomposes goals, dispatches specialists, monitors progress, and finalizes.
It **never edits files directly** — only lifecycle tools.

```
User goal → Orchestrator (dispatcher)
  ├── 1. DECOMPOSE: LLM → subtasks
  ├── 2. WRITE MANIFEST: .gitagent/sessions/<feature>/plan.json
  ├── 3. START SESSION: mcp__gitagent__start_session
  ├── 4. DISPATCH SPECIALISTS: deepagents task (parallel/sequential)
  ├── 5. MONITOR: list_agents, list_edits, list_intents
  └── 6. FINALIZE: mcp__gitagent__finalize_session
```

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

### Inter-specialist coordination
- **Always spawn a new agent** — never reuse existing ones (avoids intent drift)
- `spawn_subagent()` is a local Python function (NOT an MCP server)
- gawt inbox handles conflict detection (advisory, not blocking)
- If conflict: re-read file, re-plan, retry

### Session manifest
- Path: `.gitagent/sessions/<feature>/plan.json`
- Written by orchestrator BEFORE any agent is spawned
- Read by each specialist on init
- Updated by `spawn_subagent` when a specialist spawns a sub-agent
- Schema: `feature`, `agents[]`, `conflict_window_seconds`, `specialist_spawns_allowed`

### Subagent registry
- Config: `config/subagents.yaml` (9 subagents: abm, scoring, ingest, download, prediction, training, data, commonlib, research)
- Each subagent has: `spec`, `skills`, `gawt_role`, `can_call_via`, `edits_allow` (glob patterns), `plugins`
- `gawt_role` maps to the gawt `register_agent(role=...)` parameter

### Plugin model
- `Plugin` ABC at `plugins/base.py` — transformer over `SubagentSpec` → `ResolvedSubagent`.
- `EditPlugin`: gawt MCP preamble (shared worktree instructions).
- `ReadOnlyPlugin`: deny-all writes (onboarding).
- Per-subagent plugins: scoring, download, ingest, training, prediction, data, commonlib, research.

### Scope validator
- Plain Python (not LLM). Validates edits against `edits_allow` globs.
- `validate_edit_scope(edited_files, agent_role, registry)` → `{ok, in_scope, cross_scope, unowned}`
- Cross-scope → warning (not block). Unowned → ask_user.

### Observability
- **LivePanel**: single-agent terminal panel (orchestrator's own stream)
- **MultiAgentPanel**: multi-agent rows (agent_id, role, intent, inbox)
- **SessionLogger**: JSONL in `runs/<session>/session.jsonl`
- **Langfuse SDK**: optional trace dashboard (`--tracing langfuse`)

### CLI
```
janus onboard                # interactive menu (read-only)
janus run -g "..."           # dispatcher (goal-driven)
janus improve -g "..."       # same as run (back-compat)
janus improve -g "..." --plan docs/plans/in-process/m-agent.md
janus improve -g "..." --quiet           # suppress live panel
janus improve -g "..." --tracing langfuse  # + langfuse dashboard
janus status                 # scorecards, plans, subagents
janus agents list            # all subagents
janus agents show abm        # one subagent's details
```

### Removed (M14 → M-AGENT)
- `sibling/` directory (intent, peer_message, watcher, ASTIndex, merge_preflight, recovery, coordination, fork, frame_stack, scan, state)
- `tools/gitagent_tool.py` (old gitagent CLI wrappers)
- `cycles/run_cycle.py` (7-phase methodology, replaced by dispatcher prompt)
- `plugins/sibling.py` (SiblingPlugin)
- `mailbox.py` (file-based mailbox)
- All `tools/mailbox_*.py`, `tools/claim_file.py`, `tools/peer_message_*.py`, `tools/fork_brief_tool.py`, `tools/merge_result_tool.py`, `tools/scope_validate.py`
- Deprecated CLI commands: `calibration`, `feature`, `research`

### Files
```
agents/janus/src/agents_janus/
├── agent.py                    # create_orchestrator (dispatcher mode)
├── cli.py                      # CLI entry (run, improve, onboard, status)
├── improvement.py              # run_improvement (stream orchestrator)
├── onboarding.py               # conversational onboarding
├── live_panel.py               # LivePanel + MultiAgentPanel
├── observability.py            # ObservabilityMiddleware (3 sinks)
├── logger.py                   # SessionLogger (JSONL)
├── scope_validator.py          # validate_edit_scope
├── gawt_client.py              # thin MCP wrapper stubs
├── manifest.py                 # session manifest CRUD
├── config/subagents.yaml       # 9 subagent definitions
├── plugins/                    # Plugin chain (edit, readonly, per-domain)
├── subagents/                  # Registry, builder, base types
├── tools/                      # Pipeline, KG, ask_user, spawn_subagent, scope_tools
├── prompts/                    # orchestrator.md, specialist.md.tmpl, per_subagent/
└── tests/                      # 88+ tests (unit, integration, LLM-as-judge)
```
