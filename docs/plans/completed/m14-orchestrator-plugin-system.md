# M14 — Two-Tier Orchestrator + Specialised Subagents (Plug-and-Play)

> **Status**: Completed (2026-07-31). Commit `46fadfb`. 35 files, +1352 lines. All 8 unit tests pass. `deepagents onboard`, `deepagents improve`, `deepagents agents list/show` working.
>
> **Predecessor**: M11 — Data Pipeline Unification (`docs/plans/completed/m11-pipeline-unification.md`).
>
> **Sibling work**: M12 — Water Datasets (`docs/plans/in-process/m12-water-datasets.md`), M13 — Daily Env NC (`docs/plans/in-process/m13-daily-env-nc.md`).
>
> **Scope**: Introduce the dual-orchestrator + plugin-transformer architecture in `agents/deepagents/`. No `mal-core` code changes. No new `docs/specs/<x>/spec.md` (the existing 8 specs are consumed as-is). No automatic loading of `docs/plans/in-process/*.md`.

## 0. Why this plan exists now

Two things converged:

1. The ABM-improvement orchestrator (`agents/deepagents/agent.py::create_orchestrator`) currently exposes one tier: a single LLM that spawns one worker type (`abm-worker`) plus a read-only `research-worker`. New stages (`download`, `ingest`, `scoring`, `training`, `prediction`) and new goal types (onboarding, status, plan-driven improvements) need to be first-class without bolting more branches onto the same orchestrator prompt.
2. Commits `9ed425d` (remove pipeline orchestrator) and `6749aab` (CLI help shows stage order) deleted `mal-core/src/mal_core/pipeline/` and `docs/specs/pipeline/spec.md`. Stages are now **standalone CLI subcommands** in order: `download → ingest → abm → score → train → predict`. This plan must respect that boundary — no `pipeline` subagent, no `pipeline` plugin, no reintroduction of a central orchestrator in `mal-core`.

The M14 design treats each CLI stage as one **specialised subagent** in a YAML registry. The onboarding orchestrator and the improvement orchestrator both pull from that registry, attaching different plugins per context. The plugin abstraction is the plug-and-play layer.

## 1. Two tiers, one registry, N subagents

```
                  ┌──────────────────────────────────────┐
   CLI entry  ───▶│  onboarding orchestrator (read-mostly) │
                  │  tools: read, glob, grep, menu,       │
                  │         handoff_to_improver, status   │
                  └──────────────┬───────────────────────┘
                                 │ handoff_to_improver(goal, ctx)
                                 ▼
                  ┌──────────────────────────────────────┐
                  │  improvement orchestrator (edit)      │
                  │  tools: 17 (existing) + 3 new         │
                  │         (mailbox, scope-validate,     │
                  │          handoff from onboarding)     │
                  └──────────────┬───────────────────────┘
                                 │ task(subagent_type=…) — parallel
              ┌──────────────────┼───────────────────────────────┐
              ▼                  ▼                               ▼
        ┌──────────┐       ┌──────────┐                  ┌──────────┐
        │ abm      │       │ download │  … one per spec  │ research │
        │  +Edit   │       │  +Edit   │  (8 total)       │  +Edit   │
        │  +Scorer │       │  +Down-  │                  │  (read-  │
        │          │       │   load   │                  │   only)  │
        └──────────┘       └──────────┘                  └──────────┘
              ▲                  ▲                               ▲
              └──────────┬───────┴───────────────────────────────┘
                         │
                  SubagentSpec registry
                  (config/subagents.yaml, 8 entries)
```

Both orchestrators build a subagent the same way: `registry.get(name) → SubagentSpec → chain(plugin_a, plugin_b, …) → ResolvedSubagent → build → invoke`. The chain is the only thing that differs by context.

## 2. No `pipeline` subagent — by design

`docs/specs/pipeline/spec.md` was removed in commit `9ed425d`. M14 does **not** reintroduce it.

- The 6 stages `download → ingest → abm → score → train → predict` map 1:1 to the 6 specialised subagents (each backed by a surviving spec under `docs/specs/`).
- "Run the full pipeline" is **not** a subagent — it is a goal the onboarding menu offers, which the onboarding orchestrator hands to the improver with a `goal_template` that names the sequence.
- The improver decomposes that goal via LLM into ordered `[(subagent_name, brief)]` tuples and dispatches them sequentially. Stage order is enforced by data dependencies on disk (each stage's CLI subcommand reads the previous stage's output), **not** by an in-process state machine. This is the M14 reading of "no pipeline orchestrator in `mal-core`".
- `data` and `commonlib` are not pipeline stages; they are cross-cutting specs that multiple subagents touch (manifest, paths, config). They get their own subagents and appear in the affects graph of the other 6.

Net subagent count: **8** (download, ingest, abm, scoring, training, prediction, data, commonlib) + **1** read-only (`research`). 9 total.

## 3. Subagent registry (`config/subagents.yaml`)

```yaml
defaults:
  provider: openrouter
  model: xiaomi/mimo-v2.5
  thread_id_prefix: "sub-"

subagents:
  abm:
    description: "ABM C++ engine + Mesa-Geo adapter + runner"
    spec: docs/specs/abm/spec.md
    skills: [abm-engine, calibration-framework]
    mailbox_inbox: inbox-abm
    edits_allow:
      - mal-core/src/mal_core/abm/**
      - mal-core/src/mal_core/abm/tests/calibration/**
    plugins: [scoring]                       # ScorerPlugin is unique to abm
  scoring:
    description: "Calibration scorers + composite"
    spec: docs/specs/scoring/spec.md
    skills: [calibration-framework]
    mailbox_inbox: inbox-scoring
    edits_allow:
      - mal-core/src/mal_core/abm/tests/calibration/**
      - mal-core/src/mal_core/scoring/**
    plugins: []
  ingest:
    description: "Env tensor + host density + mobility builder"
    spec: docs/specs/ingest/spec.md
    mailbox_inbox: inbox-ingest
    edits_allow: [mal-core/src/mal_core/ingest/**]
    plugins: [ingest]
  download:
    description: "Plugin-based data fetcher (loaders, registry, runner)"
    spec: docs/specs/download/spec.md
    mailbox_inbox: inbox-download
    edits_allow:
      - mal-core/src/mal_core/download/**
      - mal-commonlib/src/mal_commonlib/data/loaders/**
    plugins: [download]
  prediction:
    description: "Risk raster predictor"
    spec: docs/specs/prediction/spec.md
    mailbox_inbox: inbox-prediction
    edits_allow: [mal-core/src/mal_core/prediction/**]
    plugins: [prediction]
  training:
    description: "U-Net model, dataset, trainer"
    spec: docs/specs/training/spec.md
    mailbox_inbox: inbox-training
    edits_allow: [mal-core/src/mal_core/training/**]
    plugins: [training]
  data:
    description: "Manifest + naming + completeness validation"
    spec: docs/specs/data/spec.md
    mailbox_inbox: inbox-data
    edits_allow:
      - mal-commonlib/src/mal_commonlib/data/**
      - docs/specs/data/**
    plugins: [data]
  commonlib:
    description: "Shared config + paths + AOI primitives"
    spec: docs/specs/commonlib/spec.md
    mailbox_inbox: inbox-commonlib
    edits_allow: [mal-commonlib/**]
    plugins: [commonlib]
  research:
    description: "Read-only literature synthesist"
    spec: null
    skills: [sdss-reference]
    mailbox_inbox: inbox-research
    edits_allow: []
    plugins: [research]                     # defence-in-depth deny-writes
```

`provider` and `model` per entry are allowed overrides. The improver always appends `EditPlugin` to the chain; onboarding never does.

## 4. Plugin model (transformers over `SubagentSpec`)

```python
@dataclass(frozen=True)
class SubagentSpec:
    name: str
    description: str
    model: str
    provider: str
    spec_path: Path | None
    skills: tuple[str, ...]
    mailbox_inbox: str
    edits_allow: tuple[str, ...]
    plugins: tuple[str, ...]                # unique-to-subagent plugins
    thread_id_prefix: str = "sub-"

@dataclass(frozen=True)
class ResolvedSubagent:
    spec: SubagentSpec
    tools: tuple[Callable, ...]
    permissions: tuple[FilesystemPermission, ...]
    preamble: str
    hooks: dict[str, Callable]

class Plugin(ABC):
    name: str
    def tools(self) -> list[Callable]:              return []
    def permissions(self) -> list[FilesystemPermission]: return []
    def preamble(self) -> str:                     return ""
    def hooks(self) -> dict[str, Callable]:        return {}
        # keys: before_task, after_task, after_proposal, before_finalize
    def apply(self, spec: SubagentSpec) -> ResolvedSubagent: ...
```

Plugins shipped in M14:

| Plugin | Owned by | Adds | Hooks |
|---|---|---|---|
| `EditPlugin` | improver (always) | `gitagent_spawn`, `gitagent_propose`, `scope_validate` tool | `before_task` spawn worktree; `after_proposal` run scope validator; `before_finalize` assert no cross-pkg touches without mailbox ack |
| `ReadOnlyPlugin` | onboarding (always) | (deny-all writes perms) | none |
| `ScorerPlugin` | abm subagent only | `abm_run`, `abm_test`, `abm_score`, `run_scorecard`, `compare_scorecards` | `after_task` auto-runs `score_then_compare` and notifies improver |
| `DownloadPlugin` | download subagent | `download_run`, `manifest_validate` | none |
| `IngestPlugin` | ingest subagent | `ingest_run`, `tensor_check` | none |
| `TrainingPlugin` | training subagent | `train_unet`, `tensor_inspect` | none |
| `PredictionPlugin` | prediction subagent | `predict_run`, `map_predict` | none |
| `DataPlugin` | data subagent | `manifest_lint`, `data_check` | none |
| `CommonlibPlugin` | commonlib subagent | `commonlib_test` | none |
| `ResearchPlugin` | research subagent | (deny-writes defence-in-depth) | none |

Adding a new "thing the subagent can do" means writing one plugin (~50 LOC) and adding it to `subagent.plugins` in YAML. The subagent itself is unchanged. **This is the plug-and-play layer.**

`EditPlugin` is the only one the improver contributes; everything else is a subagent-specific plugin. This is why the improver's chain is:

```python
spec = registry.get(name)
spec = EditPlugin().apply(spec)                        # improver always
for p in spec.plugins:                                 # YAML-declared
    spec = PLUGIN_REGISTRY[p]().apply(spec)
agent = builder.build(spec)
```

The same `registry.get(name)` call in onboarding produces the same subagent minus `EditPlugin` (and minus the subagent-specific plugins, since those are improver-side tooling). The name, model, spec, skills, mailbox inbox, and edit scope are identical.

## 5. Spec → subagent binding (no new spec files)

`docs/specs/<x>/spec.md` already has the right shape (YAML frontmatter + sections 1–10, see `_template.md`). `spec_loader.py` parses the frontmatter and slices sections by `## N. Title` headings. Each subagent's `system_prompt` is built by concatenating:

- Role + name + model + mailbox
- `## 1 Objective`
- `## 2 In scope`
- `## 3 Out of scope`
- `## 4 Public API`
- `## 5 Invariants`
- `## 6 Data contracts`
- `## 8 Drift check` (executable commands)
- Plugin-supplied `preamble()` (mailbox rules, scope rules, hooks)
- "Before editing, call `mailbox_check_inbox`" rule

The `affects` block in each spec is consumed by `affects.py` to compute cross-pkg notifications. No spec file is modified by M14.

## 6. Inter-agent mailbox (file-based)

```
runs/<session>/mailbox/
  inbox-<subagent>/        # what the subagent reads on its next turn
  outbox-<subagent>/       # what the subagent writes
  archive/                 # orchestrator moves resolved messages
```

Message schema:

```json
{
  "id": "uuid",
  "ts": "2026-07-31T12:34:56Z",
  "from": "scoring",
  "to": "abm",
  "re": "D12 thresholds raised",
  "severity": "breaking | non-breaking",
  "spec_target": "abm",
  "summary": "...",
  "ask": "ack | counter-propose | block",
  "thread_id": "M12-water-datasets",
  "ttl_minutes": 60,
  "status": "open"
}
```

Three tools: `mailbox_send`, `mailbox_check_inbox`, `mailbox_mark_resolved`. Every subagent prompt includes the rule: "Before editing, call `mailbox_check_inbox`. If a message targets a file you are about to touch, ack, counter-propose, or block. Never ignore `ask=block`."

## 7. Scope validator (plain code, not LLM)

Runs after `gitagent_proposals`, before `gitagent_integrate`. Walks the proposal's diff paths, calls `registry.find_owner(path)`:

- in own `edits_allow` → `ok`
- in another subagent's `edits_allow` → mailbox that subagent with `ask=block`; wait for ack or counter-proposal; arbitrate
- in no subagent's `edits_allow` → mailbox improver with `scope_expansion_request`; `ask_user` to accept (and expand that subagent's `edits_allow` in YAML), reject, or require revision

The validator is a Python function, not an LLM call. The user's earlier request — "un sistema en codigo revisara que no haya modificado fuera de su scope" — is satisfied by this gate.

## 8. Scorer-after-ABM (auto via plugin hook)

`ScorerPlugin.after_task(ctx)` fires whenever an abm-subagent task completes:

1. Run `pytest -m fast -v` in the proposal's worktree.
2. Compute `composite = geometric_mean(scores)`.
3. Compare vs `runs/scorecards/best_history.json`. Emit delta + verdict.
4. If `delta ≥ +threshold` → tag `candidate-promotion`, notify improver.
5. If `delta ≤ −threshold` → `mailbox_send(to=abm, ask=counter-propose, re="regression on D5")`, surface to user.
6. If `|delta| < threshold` → tag `candidate-keep`, leave for human review.
7. Write `runs/scorecards/<ts>.json`.

The improver never has to remember to score; the plugin does it.

## 9. Plans are **not** auto-loaded

Per user decision: `docs/plans/in-process/*.md` are **examples and historical drafts**, not triggers. The improver accepts `--plan PATH` as an explicit hint:

```bash
deepagents improve --plan docs/plans/in-process/m12-water-datasets.md -g "ship M12"
deepagents improve -g "lower D5 regression"              # plan-free
deepagents improve                                         # prompted for goal
```

If `--plan` is passed, the LLM reads it as part of the goal brief. During the run, progress updates are written to `runs/plans/<slug>.state.json`. When acceptance criteria hit, the plan moves to `docs/plans/completed/`. Without `--plan`, no plan file is touched.

The onboarding orchestrator's "Run a plan" menu entry passes the user-selected plan path through `handoff_to_improver(goal, context={plan: <path>})`.

## 10. Onboarding orchestrator + YAML menu

`agents/deepagents/onboarding.py` — read-mostly. No edit tool. No `EditPlugin`. Tools: `read`, `glob`, `grep`, `bash` (read-only patterns), `pipeline_status` (alias for inspecting `runs/<aoi>/`), `last_scorecard`, `kg_health`, `manifest_completeness`, `list_subagents`, `list_plans`, `list_investigations`, plus the special `handoff_to_improver(goal, context)`.

Menu config (`config/onboarding_menu.yaml`):

```yaml
greeting: |
  Hola — soy el orquestador de onboarding. Te ayudo a decidir qué quieres
  ejecutar y cómo. Te haré unas preguntas y, si algo falla, se lo paso
  al orquestador de mejora.

menu:
  - key: run_abm
    label: "Ejecutar ABM"
    description: "Recorrer el ciclo del ABM con datos reales."
    follow_up:
      - { question: "¿AOI?", options: [ghana, niger, tanzania, custom], key: aoi }
      - { question: "¿Cuántos años?", default: "1", key: years }
    handoff: { orchestrator: improve,
               goal_template: "Run ABM for AOI={aoi} over {years} years end-to-end" }

  - key: full_pipeline
    label: "Ejecutar las 6 etapas en orden"
    description: "download → ingest → abm → score → train → predict (secuencial)."
    follow_up:
      - { question: "¿AOI?", options: [ghana, niger, tanzania, custom], key: aoi }
    handoff: { orchestrator: improve,
               goal_template: "Run stages 1-6 in order for AOI={aoi}: download, ingest, abm, score, train, predict. Stop on first failure and report." }

  - key: run_one_stage
    label: "Ejecutar una sola etapa"
    description: "download, ingest, abm, score, train o predict."
    follow_up:
      - { question: "¿Etapa?",
          options: [download, ingest, abm, score, train, predict],
          key: stage }
      - { question: "¿AOI?", options: [ghana, niger, tanzania, custom], key: aoi }
    handoff: { orchestrator: improve,
               goal_template: "Run only stage '{stage}' for AOI={aoi}" }

  - key: run_a_plan
    label: "Ejecutar un plan"
    description: "Lee un plan de docs/plans/in-process/ y lo lleva a cabo."
    follow_up:
      - { question: "¿Plan?",
          options_from: "list_in_process_plans()",
          key: plan_path }
    handoff: { orchestrator: improve,
               goal_template: "Execute the plan at {plan_path}" }

  - key: diagnose
    label: "Diagnosticar un fallo"
    description: "Contéstame qué falla y reproduzco el síntoma."
    follow_up:
      - { question: "¿Qué ha fallado?", free_text: true, key: symptom }
    handoff: { orchestrator: improve,
               goal_template: "Diagnose and fix: {symptom}" }

  - key: status
    label: "Ver estado actual"
    description: "Scorecards, plans abiertos, investigaciones activas."
    no_handoff: true

  - key: list_components
    label: "Ver componentes y subagentes"
    description: "Lista de subagentes, specs editables, modelos asignados."
    no_handoff: true

  - key: quit
    label: "Salir"
    no_handoff: true
```

`handoff_to_improver` runs the improver synchronously in the same process so the mailbox state is shared. Onboarding shows the improver's summary verbatim and asks "siguiente paso?".

## 11. CLI surface

```bash
deepagents onboard                                 # interactive menu (YAML-driven)
deepagents improve [-g GOAL] [--plan PATH]         # improver; --plan optional
deepagents status                                  # session + scorecard + KG summary
deepagents agents list                             # all subagents with model + plugins + scope
deepagents agents show <name>                      # spec link, edits_allow, plugins, mailbox
deepagents run [...]                               # back-compat alias for `improve`
deepagents calibration / feature / research        # back-compat aliases
```

`deepagents run`, `deepagents calibration`, `deepagents feature`, `deepagents research` keep working and delegate to `improvement_cycle.run_cycle()` (the existing function stays as a shim that translates to the new flow).

## 12. File layout (additions only; nothing in `mal-core/` is touched)

```
agents/deepagents/
├── onboarding.py                       # NEW
├── improvement.py                      # NEW (replaces the run path inside agent.py)
├── agent.py                            # KEEP — umbrella; create_orchestrator(tier=...)
├── cli.py                              # new top-level commands
├── subagents/
│   ├── __init__.py                     # load_all_from_yaml()
│   ├── base.py                         # SubagentSpec (frozen) + ResolvedSubagent
│   ├── builder.py                      # build_subagent(spec) → deepagents subagent
│   └── registry.py                     # subagent_name → SubagentSpec loader
├── plugins/                            # NEW
│   ├── __init__.py                     # PLUGIN_REGISTRY (name → plugin class)
│   ├── base.py                         # Plugin ABC
│   ├── edit.py                         # EditPlugin
│   ├── readonly.py                     # ReadOnlyPlugin
│   ├── scoring.py                      # ScorerPlugin
│   ├── download.py                     # DownloadPlugin
│   ├── ingest.py                       # IngestPlugin
│   ├── training.py                     # TrainingPlugin
│   ├── prediction.py                   # PredictionPlugin
│   ├── data.py                         # DataPlugin
│   ├── commonlib.py                    # CommonlibPlugin
│   └── research.py                     # ResearchPlugin
├── config/
│   ├── subagents.yaml                  # NEW
│   └── onboarding_menu.yaml            # NEW
├── mailbox.py                          # NEW
├── scope_validator.py                  # NEW
├── affects.py                          # NEW
├── spec_loader.py                      # NEW
├── registry.py                         # NEW
├── tools/
│   ├── mailbox_send.py                 # NEW
│   ├── mailbox_check_inbox.py          # NEW
│   ├── mailbox_mark_resolved.py        # NEW
│   ├── scope_validate.py               # NEW
│   ├── subagent_invoke.py              # NEW (handoff_to_improver)
│   └── ... existing tools unchanged ...
├── cycles/
│   ├── improvement_cycle.py            # NEW
│   └── score_then_compare.py           # NEW
├── prompts/templates/<subagent>.md     # NEW (one per registered subagent)
└── tests/
```

## 13. Implementation order

1. `subagents/base.py` + `subagents/builder.py` + `registry.py` (no plugins, no orchestrator wiring yet).
2. `plugins/base.py` + `plugins/readonly.py` + `plugins/research.py` (minimal proof).
3. Wire `onboarding.py` with `readonly` chain only; CLI `deepagents onboard` works (read-only menu).
4. `mailbox.py` + 3 tools (`mailbox_send`, `mailbox_check_inbox`, `mailbox_mark_resolved`).
5. `plugins/edit.py` + `scope_validator.py` + integration into the improvement path.
6. `config/subagents.yaml` skeleton; migrate existing `abm-worker` to chain `EditPlugin + ScorerPlugin`.
7. `plugins/scoring.py` + `cycles/score_then_compare.py` (auto after abm).
8. `config/onboarding_menu.yaml` + `subagent_invoke` tool (handoff).
9. Remaining per-subagent plugins (download, ingest, data, commonlib, pipeline*, training, prediction) — one at a time. *(`pipeline` plugin intentionally omitted per §2.)*
10. `improvement.py` + `cycles/improvement_cycle.py` replacing `run_cycle`; keep `run_cycle` as shim.
11. Tests: plugin chain unit tests, scope-validator unit tests, mailbox round-trip, end-to-end with one plan (e.g. M12 stub).
12. `AGENTS.md` update + KG `Operational` node `op-m14-orchestrator-plugin-system` recording the new architecture.

## 14. Backwards compatibility

- `WORKER_DEFINITIONS` (`abm-worker`, `research-worker`) become aliases loaded from the registry. Existing `task(subagent_type="abm-worker")` calls keep working.
- `prompts/templates/abm_worker.md` becomes a fallback used when `spec_loader` cannot reach the spec. Real prompts are generated from `spec.md` + plugin `preamble()`.
- `run`, `calibration`, `feature`, `research` CLI commands keep working and delegate to `improvement_cycle`.
- No `mal-core/` code changes. No new `docs/specs/<x>/spec.md`. No reintroduction of `docs/specs/pipeline/spec.md`.

## 15. Acceptance criteria

- [ ] `deepagents onboard` walks the YAML menu and answers all 8 items (5 with handoff, 3 local).
- [ ] `deepagents agents list` shows all 9 subagents with model, plugins, edits_allow, mailbox inbox.
- [ ] `deepagents improve -g "..."` works for: (a) single-subagent goal (e.g. "raise D12 floor"), (b) multi-subagent goal (e.g. "ingest fails on chirps daily"), (c) goal spanning all 6 stages ("full pipeline for ghana 2024").
- [ ] A proposal that touches a path in another subagent's `edits_allow` triggers a mailbox message and the improver blocks finalize until ack or counter-propose.
- [ ] A proposal that touches a path in no subagent's `edits_allow` triggers a `scope_expansion_request` and `ask_user`; the user can accept (and YAML is updated) or reject.
- [ ] After any abm-subagent task, `score_then_compare` runs without the improver asking, and writes a scorecard.
- [ ] `--plan PATH` flow: improver reads the plan, updates `runs/plans/<slug>.state.json`, and moves the file to `completed/` when acceptance criteria hit.
- [ ] `make -f agents/memory/scripts/Makefile audit` is clean (no schema violations from any new node).
- [ ] KG node `op-m14-orchestrator-plugin-system` recorded with summary + commit SHA.
- [ ] No file under `mal-core/` is modified by this milestone.

## 16. Risks

| # | Risk | Mitigation |
|---|---|---|
| 1 | Two orchestrators drift in capability over time | Both are built from the same `registry.get()` + plugin chain; capability = (registry) + (plugins). Adding a plugin to one does not auto-add it to the other — explicit. |
| 2 | Plugin chain order matters (e.g. `EditPlugin` must run first) | Document order in `plugins/base.py`; `apply()` is `__init__.py`-driven. Add unit test that checks each plugin's invariants. |
| 3 | Onboarding's `handoff_to_improver` makes the improver a single point of failure | Handoff is synchronous; failure surfaces back to onboarding verbatim; onboarding then offers "retry" or "back to menu". |
| 4 | `docs/plans/in-process/*.md` start being treated as auto-triggers by future contributors | AGENTS.md note + onboarding menu's "Run a plan" entry is the only path that mentions them. |
| 5 | Scope validator gets out of sync with YAML | Validator reads the same `subagents.yaml`; one source of truth. |
| 6 | The 8 subagents × per-subagent plugins → combinatorial test surface | Test each plugin in isolation + one integration test per subagent (abm gets the full score-after chain). |
| 7 | User expectation that the improvement orchestrator auto-picks the next plan from `in-process/` | Explicit `--plan` flag and onboarding menu only; AGENTS.md note. |

## 17. References

- `docs/plans/completed/m11-pipeline-unification.md` — M11 plan (predecessor).
- `docs/plans/in-process/m12-water-datasets.md` — sibling.
- `docs/plans/in-process/m13-daily-env-nc.md` — sibling.
- `mal-core/README.md` — stage order and data dependencies (the contract this plan respects).
- `docs/specs/_template.md` — spec format consumed by `spec_loader.py`.
- `agents/deepagents/agent.py` — current single-orchestrator implementation to be wrapped, not rewritten.
- `agents/deepagents/SKILL.md` — current quick-start (to be updated in step 12).
- `agents/deepagents/README.md` — current architecture diagram (to be updated in step 12).
- `opencode.json` `agent.deepagent-orchestrator` — primary agent entry; onboarding + improver are added as siblings in step 12.
- KG `Operational` node: `op-m11-data-pipeline-unification` (predecessor).
- KG `Operational` node: `op-m14-orchestrator-plugin-system` (this plan, recorded in step 12).

## 18. Change log

| Date | Author | Change |
|---|---|---|
| 2026-07-31 | supervisor | Plan drafted. Aligns with commits `9ed425d` (remove pipeline orchestrator) and `6749aab` (CLI help stage order): no `pipeline` subagent/plugin, stages 1–6 are standalone CLI subcommands invoked by 6 of the 8 subagents, "full pipeline" is a menu item that the onboarding orchestrator hands to the improver as a goal. |
| 2026-07-31 | supervisor | Implementation complete. Commit `46fadfb`. 35 files, +1352 lines. Steps 1–12 done. All 8 unit tests pass. `plugins/__init__.py` fixed post-integrate to include all 10 plugins. AGENTS.md updated with M14 architecture section. |
