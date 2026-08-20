# self_improve Spec

> Owns **self-improvement of the Janus multi-agent system**.
> When a worker specialist fails repeatedly, when the orchestrator
> misroutes a task, when a subagent configuration is wrong, when a
> prompt is unclear, or when janus-internal code has a bug, the
> `self_improve` specialist fixes the Janus meta-system. Domain code
> (`mal-core/`, `mal-commonlib/`, `mal-execution/`) is owned by other
> specialists — `self_improve` only edits the janus subsystem itself.

---

```yaml
# Machine-readable affects block — parsed by the drift-check agent.
affects:
  - target: abm
    direction: bidirectional
    reason: self_improve patches prompts and janus config that abm specialists read
    severity: non-breaking
  - target: scoring
    direction: bidirectional
    reason: self_improve patches prompts and janus config that scoring specialists read
    severity: non-breaking
  - target: ingest
    direction: bidirectional
    reason: self_improve patches prompts and janus config that ingest specialists read
    severity: non-breaking
  - target: download
    direction: bidirectional
    reason: self_improve patches prompts and janus config that download specialists read
    severity: non-breaking
  - target: prediction
    direction: bidirectional
    reason: self_improve patches prompts and janus config that prediction specialists read
    severity: non-breaking
  - target: training
    direction: bidirectional
    reason: self_improve patches prompts and janus config that training specialists read
    severity: non-breaking
  - target: data
    direction: bidirectional
    reason: self_improve patches prompts and janus config that data specialists read
    severity: non-breaking
  - target: commonlib
    direction: bidirectional
    reason: self_improve patches prompts and janus config that commonlib specialists read
    severity: non-breaking
# Cross-references to the knowledge graph (names only, no UUIDs — survives KG migrations).
kg_refs:
  adrs: []
  patterns: []
  pitfalls: []
  tools: []
```

## Metadata

| Field | Value |
|---|---|
| Component | `agents/janus/**` (the entire Janus subsystem) |
| Version | `v0.2` (scope expanded from prompts-only to full janus subsystem) |
| Status | `draft` |
| Owner | David Flórez-Mazuera |
| Last drift check | `2026-08-11` |

## 1. Objective

Self-improvement closes the **meta-loop**: when the Janus meta-system
itself is the bottleneck — bad prompts, unclear subagent configs,
missing tools, broken wiring, or janus-internal bugs — `self_improve`
fixes it. Without self-improvement, every Janus defect is permanent; we
can only fix it by hand-editing files, which means every regression
costs human attention.

The boundary: `self_improve` edits **the janus subsystem** (how
specialists are configured, what prompts they read, how the orchestrator
dispatches them). It does NOT edit domain code (the malaria simulation,
the calibration scorers, the data loaders) — those are owned by other
specialists. If the root cause is a domain-code bug, dispatch the
relevant domain specialist, not `self_improve`.

## 2. In scope

`self_improve` edits files anywhere under `agents/janus/**` EXCEPT the
runtime-output directories listed in §3. Specifically:

- **Prompts**: `agents/janus/src/agents_janus/prompts/orchestrator.md.j2`,
  `specialist.md.tmpl`, `per_subagent/<name>.md.j2`.
- **Subagent configuration**: `config/subagents.yaml` (add/remove
  specialists, change `edits_allow`, `can_call_via`, `gawt_role`).
- **Tools**: `src/agents_janus/tools/*.py` (add a tool, fix a bug,
  rename, deprecate).
- **Agent wiring**: `src/agents_janus/agent.py`, `cli.py`,
  `improvement.py`, `onboarding.py` (orchestrator factory, dual-mode
  config, dispatcher wiring).
- **Observability**: `src/agents_janus/observability.py`,
  `live_panel.py`, `logger.py` (tool categories, traces, panels).
- **Subagent internals**: `src/agents_janus/subagents/*.py`
  (registry, builder, base types, middleware).
- **Tests**: `src/agents_janus/tests/*.py` (add a test, fix a flaky
  test, drop a broken test when the production code it tests has been
  removed).
- **Project conventions**: `agents/janus/AGENTS.md` (project
  conventions, known pitfalls, scorer naming, dual-mode orchestrator
  notes — only the janus subsystem's own AGENTS.md, not the root one).
- **Docs**: `agents/janus/SKILL.md`, `agents/janus/README.md`.
- **Package metadata**: `agents/janus/pyproject.toml` (add a dep, bump
  a version).

## 3. Out of scope

`self_improve` does NOT edit:

- **Domain code**: `mal-core/**`, `mal-commonlib/**`,
  `mal-execution/**`, `mal-data-explorer/**`.
  These are owned by the corresponding specialists (`abm`, `scoring`,
  `ingest`, `download`, `prediction`, `training`, `data`, `commonlib`).
  If a janus bug is caused by a domain-code bug, dispatch the
  domain-code specialist instead — `self_improve` does not fix
  domain code.
- **Runtime artifacts**: `agents/janus/runs/**`, `__pycache__/`,
  `.pytest_cache/`, `.gitagent/`. These are generated outputs, not
  source.
- **External data**: `data/**` (downloaded AOI datasets).
- **Knowledge graph content**: `agents/memory/seed/*.yaml` is owned by
  the curator role. `self_improve` reads the KG but does not edit
  seed yaml.
- **Root project files**: the root `AGENTS.md` is the agent's own
  operating instructions and is human-owned.
- **Other specialists' outputs**: `runs/<session>/session.jsonl`,
  trace dumps, etc.

## 4. Public API

`self_improve` is a **specialist agent**, not a Python function. It is
dispatched via the standard `task(subagent_type="self_improve", task=...)`
flow.

| Task field | Required | Description |
|---|---|---|
| `[MODE:research]` | yes | Mode tag (same protocol as other specialists). |
| category | yes | One of: `prompt`, `config`, `tool`, `wiring`, `observability`, `test`, `convention`, `docs`, `metadata`. |
| target_specialist | no | If the fix improves another specialist, its name (e.g., `abm`). |
| failure_analysis | yes | What went wrong, why, what should happen instead. |
| proposed_change | yes | The instruction (for prompt/config changes) or the bug/feature spec (for code changes). |
| confidence | no | Float 0.0–1.0; informational only. |

The specialist responds with a JSON summary:
```json
{
  "status": "patched" | "skipped" | "failed",
  "category": "prompt",
  "files_changed": ["<path1>", "<path2>"],
  "patch_summary": "<what was added/changed>",
  "tests_run": true | false,
  "tests_pass": true | false,
  "kg_recorded": true | false
}
```

## 5. Invariants

- **INV-1.** `self_improve` edits **only** files under `agents/janus/**`,
  minus the runtime-artifact exceptions in §3. Any other path is a
  scope violation and the orchestrator should reject it.
- **INV-2.** Every patch MUST be preceded by a `read_file` of the
  current file contents. Blind overwrites are forbidden.
- **INV-3.** Every successful patch MUST be recorded in the knowledge
  graph with the failure analysis + proposed change (best-effort;
  KG failure does not block the patch).
- **INV-4.** Patches are **additive or clarifying**. `self_improve` must
  not delete content from an existing file unless the deletion is
  explicitly justified in the failure analysis.
- **INV-5.** After any non-trivial change to janus code (tools,
  wiring, subagent internals, observability), `self_improve` MUST run
  the relevant tests and report the result in the response JSON.
  Prompt-only and config-only changes do not require a test run.
- **INV-6.** `self_improve` does NOT modify `mal-core/`,
  `mal-commonlib/`, `mal-execution/`, or any non-janus file. If the
  root cause is a domain-code bug, dispatch the relevant
  domain-code specialist instead.

## 6. Data contracts

- **Input**: a task string with `[MODE:research]` + category +
  failure_analysis + proposed_change (+ optional target_specialist +
  confidence).
- **Output**: JSON summary (see §4).
- **Side effects**:
  - One or more `mcp__gitagent__edit_file` or `write_file` calls
    against the target file(s), all under `agents/janus/**`.
  - Optional `mcp__gitagent__read_file` to load current contents
    before editing.
  - Optional pytest invocation via `uv run pytest
    agents/janus/src/agents_janus/tests/` to verify the change.
  - One `mcp__gitagent__send_message` to `__orchestrator__` with the
    summary.
  - One knowledge-graph write (best-effort) via `memory.sh`.

## 7. Migration & deprecation

- v0.1: replaces `tools/improve_tool.py::improve_prompt`. The old tool
  pointed at `agents/deepagents/prompts/templates/` which never
  existed; no real prompt files were ever patched by it.
- v0.2: scope expanded from prompts-only to the full janus subsystem.
  `self_improve` is now the canonical path for janus meta-improvements.

## 8. Drift check

```bash
# INV-1: self_improve scope is locked to agents/janus/**
rg "edits_allow" agents/janus/src/agents_janus/config/subagents.yaml \
  | grep -A2 "self_improve"
# Expect: agents/janus/**

# INV-2: read-before-write — check no template modification without a read
rg "edit_file" agents/janus/src/agents_janus/prompts/per_subagent/self_improve.md.j2

# INV-3: KG recording — check the prompt mentions memory.sh or memory_recall_kg
rg "memory" agents/janus/src/agents_janus/prompts/per_subagent/self_improve.md.j2

# INV-6: no domain-code edits — check the prompt says no mal-core edits
rg "mal-core|mal-commonlib|mal-execution" agents/janus/src/agents_janus/prompts/per_subagent/self_improve.md.j2

# Verify the spec itself is reachable
test -f docs/specs/self_improve/spec.md
```

## 9. Examples

### Example 1: prompt improvement (the original use case)

```
task(subagent_type="self_improve",
     task="[MODE:research] category=prompt target_specialist=abm. "
          "Failure: ABM specialist generates C++ that uses 'auto' return "
          "types for engine.hpp public functions, which fails clang-tidy. "
          "Proposed change: add to per_subagent/abm.md.j2 a rule 'Use "
          "explicit return types for all public functions in engine.hpp.'")
```

### Example 2: subagent config improvement

```
task(subagent_type="self_improve",
     task="[MODE:research] category=config. "
          "Failure: the ingest specialist cannot reach gawt MCP because "
          "its edits_allow does not include gawt's manifest dir, so its "
          "first edit crashes with a scope warning. Proposed change: "
          "add '.gitagent/worktree/**' to ingest's edits_allow.")
```

### Example 3: janus-internal bug fix

```
task(subagent_type="self_improve",
     task="[MODE:research] category=tool. "
          "Failure: tools/ask_user_tool.py drops KeyboardInterrupt on "
          "EOF, but it should fall back to the default answer, not "
          "crash. Proposed change: wrap the EOF branch in try/except "
          "KeyboardInterrupt and return the default.")
```

### Example 4: project-convention update

```
task(subagent_type="self_improve",
     task="[MODE:research] category=convention. "
          "Failure: agents/janus/AGENTS.md still lists 'mailbox_inbox' "
          "as the default name for subagents, but the field is "
          "deprecated and gawt uses '__orchestrator__' inbox instead. "
          "Proposed change: replace the mailbox_inbox mention with "
          "the gawt-inbox convention.")
```

### Counter-example: trying to fix domain code

WRONG. `self_improve` should reject this and tell the orchestrator to
dispatch the `abm` specialist instead:
```
task(subagent_type="self_improve",
     task="[MODE:research] category=tool. "
          "fix the bug in mal-core/src/mal_core/abm/params.h line 42")
```

## 10. References

- Old tool (deleted after v0.1 migration): `agents/janus/src/agents_janus/tools/improve_tool.py`
- Specialist protocol: `agents/janus/src/agents_janus/prompts/specialist.md.tmpl`
- Orchestrator dispatch protocol: `agents/janus/src/agents_janus/prompts/orchestrator.md.j2`
- Subagent registry: `agents/janus/src/agents_janus/config/subagents.yaml`
- Janus subsystem layout: `agents/janus/AGENTS.md`
- gawt MCP: external `gawt>=0.5.0`