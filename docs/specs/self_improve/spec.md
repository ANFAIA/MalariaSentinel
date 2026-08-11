# self_improve Spec

> Owns **prompt self-improvement** for the Janus multi-agent system.
> When a worker specialist fails repeatedly on a task, the `self_improve`
> specialist analyses the failure, proposes a targeted patch to the
> relevant prompt template, applies it via gawt MCP, and records the
> improvement in the knowledge graph.

---

```yaml
# Machine-readable affects block — parsed by the drift-check agent.
affects:
  - target: abm
    direction: bidirectional
    reason: self_improve patches prompts that abm specialists read (orchestrator, specialist)
    severity: non-breaking
  - target: scoring
    direction: bidirectional
    reason: self_improve patches prompts that scoring specialists read
    severity: non-breaking
  - target: ingest
    direction: bidirectional
    reason: self_improve patches prompts that ingest specialists read
    severity: non-breaking
  - target: download
    direction: bidirectional
    reason: self_improve patches prompts that download specialists read
    severity: non-breaking
  - target: prediction
    direction: bidirectional
    reason: self_improve patches prompts that prediction specialists read
    severity: non-breaking
  - target: training
    direction: bidirectional
    reason: self_improve patches prompts that training specialists read
    severity: non-breaking
  - target: data
    direction: bidirectional
    reason: self_improve patches prompts that data specialists read
    severity: non-breaking
  - target: commonlib
    direction: bidirectional
    reason: self_improve patches prompts that commonlib specialists read
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
| Component | `agents/janus/src/agents_janus/prompts/` + orchestrator + per_subagent templates |
| Version | `v0.1` (initial, replaces `tools/improve_tool.py`) |
| Status | `draft` |
| Owner | David Flórez-Mazuera |
| Last drift check | `2026-08-11` |

## 1. Objective

Self-improvement closes the **meta-loop**: when a specialist fails because
its prompt is unclear, incomplete, or contradictory, the orchestrator
dispatches `self_improve` to patch the prompt so the same failure does not
recur. Without self-improvement, every prompt bug is permanent — we can
only fix it by hand-editing templates, which means every regression costs
human attention.

## 2. In scope

- Editing prompt templates under `agents/janus/src/agents_janus/prompts/`:
  - `orchestrator.md.j2` (the orchestrator system prompt)
  - `specialist.md.tmpl` (the common specialist protocol)
  - `per_subagent/<name>.md.j2` (per-specialist domain clarifications)
- Recording improvements in the knowledge graph (via `memory_recall_kg` /
  `memory.sh`).
- Reading current prompt contents before patching (to avoid clobbering).
- Returning a structured summary of what was changed and why.

## 3. Out of scope

- Code changes (`mal-core/`, `mal-commonlib/`, `mal-execution/`) — these
  belong to their respective specialists.
- Tests, calibration scorers, ABM parameters — same as above.
- Prompt authoring from scratch (greenfield templates) — `self_improve`
  patches existing prompts based on observed failure modes. Greenfield
  authoring is a manual task.

## 4. Public API

`self_improve` is a **specialist agent**, not a Python function. It is
dispatched via the standard `task(subagent_type="self_improve", task=...)`
flow. The task string encodes the failure analysis and proposed patch.

| Task field | Required | Description |
|---|---|---|
| `[MODE:research]` | yes | Mode tag (same protocol as other specialists). |
| failure_analysis | yes | What went wrong, why, which specialist(s) were affected. |
| target_specialist | yes | Name of the specialist whose prompt needs patching (e.g., `abm`, `scoring`, `orchestrator`). |
| proposed_patch | yes | The instruction to add or change in the target prompt. |
| confidence | no | Float 0.0–1.0; informational only. |

The specialist responds with a JSON summary:
```json
{
  "status": "patched" | "skipped" | "failed",
  "target_file": "<path>",
  "patch_summary": "<what was added/changed>",
  "kg_recorded": true | false
}
```

## 5. Invariants

- **INV-1.** `self_improve` edits **only** files under
  `agents/janus/src/agents_janus/prompts/**`. Any other path is a
  scope violation and the orchestrator should reject it.
- **INV-2.** Every patch MUST be preceded by a `read_file` of the
  current prompt contents. Blind overwrites are forbidden.
- **INV-3.** Every successful patch MUST be recorded in the knowledge
  graph with the failure analysis + proposed patch (best-effort;
  KG failure does not block the patch).
- **INV-4.** Patches are **additive or clarifying**. `self_improve` must
  not delete content from an existing prompt unless the deletion is
  explicitly justified in the failure analysis.
- **INV-5.** `self_improve` does NOT modify `tests/` or any non-prompt
  file, even if the failure analysis suggests a code fix. Code fixes
  are dispatched to the relevant code-owning specialist.

## 6. Data contracts

- **Input**: a task string with `[MODE:research]` + failure_analysis +
  target_specialist + proposed_patch.
- **Output**: JSON summary (see §4).
- **Side effects**:
  - One or more `mcp__gitagent__edit_file` calls against the target
    prompt file (only within `agents/janus/src/agents_janus/prompts/**`).
  - One `mcp__gitagent__send_message` to `__orchestrator__` with the
    summary.
  - One knowledge-graph write (best-effort) via `memory.sh`.

## 7. Migration & deprecation

- v0.1: replaces `tools/improve_tool.py::improve_prompt`. The old tool
  pointed at `agents/deepagents/prompts/templates/` which never existed;
  no real prompt files were ever patched by it. After this migration,
  `improve_prompt` is deleted and `self_improve` is the sole path.

## 8. Drift check

```bash
# INV-1: self_improve scope is locked to prompts/
rg "edits_allow" agents/janus/src/agents_janus/config/subagents.yaml \
  | grep -A2 "self_improve"
# Expect: agents/janus/src/agents_janus/prompts/**

# INV-2: read-before-write — check no template modification without a read
rg "edit_file" agents/janus/src/agents_janus/prompts/per_subagent/self_improve.md.j2

# INV-3: KG recording — check the prompt mentions memory.sh or memory_recall_kg
rg "memory" agents/janus/src/agents_janus/prompts/per_subagent/self_improve.md.j2
```

## 9. Examples

### Example 1: ABM specialist keeps producing C++ that doesn't compile

```
task(subagent_type="self_improve",
     task="[MODE:research] target_specialist=abm. "
          "Failure: ABM specialist generates C++ that uses 'auto' return types "
          "for engine.hpp public functions, which fails our clang-tidy gate. "
          "Proposed patch: add to per_subagent/abm.md.j2 a rule 'Use explicit "
          "return types for all public functions in engine.hpp — no auto.'"
          "Confidence: 0.85")
```

### Example 2: Scoring specialist forgets to compare against best historical

```
task(subagent_type="self_improve",
     task="[MODE:research] target_specialist=scoring. "
          "Failure: scoring specialist reports composite vs previous run only, "
          "never vs best historical. Proposed patch: add to "
          "per_subagent/scoring.md.j2 'After computing composite, ALWAYS "
          "compare against load_best(run_dir) and report the delta.'"
          "Confidence: 0.9")
```

### Counter-example: trying to fix code, not prompt

WRONG. `self_improve` should reject this and tell the orchestrator to
dispatch the `abm` specialist instead:
```
task(subagent_type="self_improve",
     task="[MODE:research] fix the bug in params.h line 42")
```

## 10. References

- Old tool (deleted after this migration): `agents/janus/src/agents_janus/tools/improve_tool.py`
- Specialist protocol: `agents/janus/src/agents_janus/prompts/specialist.md.tmpl`
- Orchestrator dispatch protocol: `agents/janus/src/agents_janus/prompts/orchestrator.md.j2`
- Subagent registry: `agents/janus/src/agents_janus/config/subagents.yaml`
- gawt MCP: external `gawt>=0.5.0`