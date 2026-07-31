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
janus improve -g "..."       # improver
janus improve -g "..." --plan docs/plans/in-process/m12.md
janus status                 # scorecards, plans, subagents
janus agents list            # all subagents
janus agents show abm        # one subagent's details
janus run -g "..."           # back-compat alias
```
