# Plan: Janus Audit — Deprecated Files, Misnamed Tools, Stubs

> **Status**: draft (2026-08-10)
> **Type**: investigation / cleanup
> **Scope**: `agents/janus/src/agents_janus/` and `agents/janus/src/agents_janus/prompts/`
> **Related**: `docs/plans/in-process/janus-dual-orchestrator.md`, `docs/plans/in-process/m-agent-gitagent-redesign.md`, `agents/janus/AGENTS.md`

## Summary

This is an **audit document**, not an implementation plan. It catalogs the current state of every file/folder the user flagged, classifies each as either **deprecated** (delete), **needs refactor** (update), or **wrongly accused** (keep as-is), and proposes specific actions.

The audit follows the architectures already proposed in:
- `janus-dual-orchestrator.md` (centinela + dispatcher dual-mode)
- `m-agent-gitagent-redesign.md` (gawt-native, sibling system removed)

Both plans are referenced as the **canonical truth** for what should exist. Anything that contradicts them is dead code.

| Verdict | Count |
|---|---|
| DELETE | 12 paths |
| REFACTOR | 16 paths |
| KEEP | 2 (scope_validator, plugins/) |

---

## 1. Files flagged as deprecated

### 1.1 `scope_validator.py` — KEEP, REFACTOR

**User claim**: "Already covered by the MCP that we adapted to."

**Reality**:
- `m-agent-gitagent-redesign.md` §1.4 and §2.3 explicitly say: *"gawt does NOT enforce per-agent edit scopes. Any agent can edit any file in the shared worktree."*
- The redesign proposes **refactoring** this validator (not removing it). It still has a job: post-edit advisory validation against `edits_allow` in the registry.
- Currently the validator takes `edited_files: list[str]` as input. Under the new gawt world, it should query gawt's `edits` table (`mcp__gitagent__list_edits(since_ts=...)`) to discover the edits, then validate against `edits_allow`.
- Test coverage active: `tests/test_scope_tools.py`, `tests/test_subagents.py`, `tests/test_gawt_integration.py`.

**Verdict**: **Keep, refactor.** The current implementation is a stub that requires the caller to pass the edited files. The gawt-native version should:

```python
# agents/janus/src/agents_janus/scope_validator.py
def validate_edit_scope(
    agent_role: str,
    registry: Registry,
    since_ts: str | None = None,
) -> dict:
    """Validate that an agent's recent edits are within its declared scope.
    
    Source: mcp__gitagent__list_edits(agent_id=...) via gawt SQLite.
    Falls back to the passed-in list if gawt is unreachable.
    """
    ...
```

**Action**:
- Replace manual `edited_files` input with a gawt MCP call.
- Keep the function signature + result schema (cross_scope, unowned, in_scope) for backward compat with tests.
- Update `tests/test_gawt_integration.py` to mock the gawt MCP call.

---

### 1.2 `trace_analyzer/` directory — MIXED (delete + refactor)

| File | Verdict | Reason |
|---|---|---|
| `__init__.py` | Refactor | Re-exports to keep, drop the dead ones. |
| `checks.py` | DELETE | 10 checks reference removed sibling tools (`claim_file`, `peer_message`, `fork_brief`, `merge_result`, `scan_markers`). These are all part of the system removed by `m-agent-gitagent-redesign.md`. |
| `analyzer.py` | DELETE | `_evaluate_check` is a static rule-based scorer for the 10 sibling checks. Useless without `checks.py`. |
| `judge.py` | KEEP + REFACTOR | LLM-as-judge is still useful; just simplify to use Langfuse MCP instead of raw trace JSON. |
| `harness.py` | KEEP + REFACTOR | Trial harness is still valid; remove `TRIAL_GOAL_DEFAULT`, make `goal` mandatory. |

**Evidence for deletes**:
- `checks.py` defines checks like `claim_file_registered`, `peer_message_sent`, `fork_brief_invoked`, `merge_result_returned`, `frame_stack_push_pop`, `scan_markers_emitted` — all reference removed tools.
- `analyzer.py` `_evaluate_check` only handles those 10 checks. Nothing else calls it.
- `m-agent-gitagent-redesign.md` §1.4 **Removed** list: `sibling/` (intent, peer_message, watcher, ASTIndex, merge_preflight, recovery, coordination, fork, frame_stack, scan, state), `plugins/sibling.py`, `mailbox.py`, `tools/claim_file.py`, `tools/peer_message_*.py`, `tools/fork_brief_tool.py`, `tools/merge_result_tool.py`. → confirms sibling system is dead.

**Tests to update**:
- `tests/test_trace_harness.py` references all 4 files. After delete: prune tests for `checks.py` and `analyzer.py`, keep and update tests for `judge.py` and `harness.py`.

---

### 1.3 `tools/abm_tools.py` — DELETE (outright)

**User claim**: "Mostly deprecated."

**Reality**:
- The module is built around a **per-agent worktree registry** (`_WORKTREE_REGISTRY`, `_thread_local`, `register_worktree`, `unregister_worktree`, `set_current_agent`, `clear_current_agent`, `_resolve_worktree`).
- This implements the **old M14 model** where each agent had its own worktree. The new gawt model has **one shared worktree per session**.
- `agent.py` still imports `abm_run`, `abm_test`, `abm_score` from this module (lines 101, 106, 111). The dispatcher uses these.
- The fall-through `_resolve_worktree()` returns `REPO_ROOT` when no agent is registered — which means the tools effectively run in the repo root regardless. This is misleading.

**Verdict**: **DELETE**. The thin wrappers (`run_abm_from_manifest`, `pytest -m fast`, `score_run`) are already exposed via:
- `tools/pipeline_tool.py` (canonical pipeline tools: `pipeline_run_calibration`, `pipeline_compare_scorecards`)
- `tools/onboard_tools.py` (centinela: `onboard_run_abm`, `onboard_run_stage`)

The dispatcher doesn't need a third path. If we want `abm_test` and `abm_score` exposed to the dispatcher, move them into `pipeline_tool.py` as `pipeline_run_tests` and `pipeline_score_run`.

**Action**:
- Delete `agents/janus/src/agents_janus/tools/abm_tools.py`.
- Delete `tests/test_abm_tools.py`.
- Remove the 3 imports from `agents/janus/src/agents_janus/agent.py` (lines 100-112, 179-181).
- If `abm_test` / `abm_score` are needed by the dispatcher, port them to `pipeline_tool.py` (worktree-independent).

---

### 1.4 `tools/improve_tool.py` — DELETE

**User claim**: Deprecated.

**Reality**:
- Line 7: `PROMPTS_DIR = Path("agents/deepagents/prompts/templates")` — this path **doesn't exist** in the project. The actual prompts live at `agents/janus/src/agents_janus/prompts/per_subagent/`.
- Lines 31-35: `agent_type` only accepts `abm_worker`, `scorer_worker`, `feature_worker` — old naming. The new system uses `subagents.yaml` with `abm`, `scoring`, `training`, etc.
- Lines 70-96: KG recording uses `agents/memory/scripts/memory.sh` — that's the agents/memory Makefile, not the Janus KG. Wrong tool for the job.
- The tool is **registered** in `tools/__init__.py` line 8, but no other code calls it.

**Verdict**: **DELETE**. The new system has these capabilities elsewhere:
- Self-improvement patches: not part of the gawt-native design (worker prompts are spec-driven, not patched at runtime).
- KG recordings: handled by `memory_recall_kg` (`tools/kg_tool.py`) + direct `mcp__graphiti-memory__add_memory` calls.

**Action**:
- Delete `tools/improve_tool.py`.
- Remove import from `tools/__init__.py` line 8.
- Remove import from `agent.py` line 174, 185.
- Update `tests/test_orchestrator.py` if it tests this tool.

---

### 1.5 `prompts/templates/` — DELETE

**User claim**: "Now in `per_subagent`."

**Reality**:
- Files: `abm_worker.md`, `feature_worker.md`, `scorer_worker.md` — old naming.
- No code references them. Confirmed by grep:
  - `subagents/builder.py` only loads `specialist.md.tmpl` and `per_subagent/<name>.md.j2`.
  - `agent.py` doesn't reference `templates/`.
  - `tools/improve_tool.py` writes to a **wrong path** (`agents/deepagents/prompts/templates`).
- The completed plan `m16-registry-integration.md` says they are "fallback only" when `spec_loader` cannot reach the spec — but `spec_loader.py` doesn't actually reference them. The fallback path is also broken since `agent.py` no longer calls `spec_loader`.

**Verdict**: **DELETE**. The active system uses `per_subagent/<role>.md.j2` (Layer C in `builder.py`).

**Action**:
- Delete `agents/janus/src/agents_janus/prompts/templates/` directory.

---

### 1.6 `prompts/patches/` — DELETE

**User claim**: "Not used."

**Reality**:
- Directory contains only `.gitkeep`.
- No references anywhere.

**Verdict**: **DELETE**.

**Action**: Remove the directory (and `.gitkeep`).

---

### 1.7 `prompts/config/onboarding_menu.yaml` — DELETE (stale)

**User claim**: "Deprecated in favor of `config/subagents.yaml`."

**User is partially wrong**: `config/subagents.yaml` is a **different thing** — it defines subagent specs (description, skill, edits_allow, plugins). The menu YAML defined a list of user actions with `onboard_*` tool names.

**Reality**:
- The menu YAML references `onboard_delegate` — **a tool that doesn't exist anymore** (replaced by `delegate_to_dispatcher` in `tools/onboard_tools.py`).
- The file has **no imports** anywhere. Confirmed by grep: no `.py` file loads it.
- `m16-registry-integration.md` mentioned it as a "YAML-driven menu (M14 gap)" — but the actual menu system was never wired into the agent.

**Verdict**: **DELETE**. The YAML menu was a designed feature that was never integrated. The current centinela has an LLM-driven conversation flow, not a menu.

**Action**: Delete `agents/janus/src/agents_janus/prompts/config/onboarding_menu.yaml` and the empty `prompts/config/` directory.

---

### 1.8 `prompts/drift/` — DELETE (with redesign note)

**User question**: Where is `drift` injected? Should it be useful for inter-agent communication?

**Reality**:
- Files: `fork_negotiation.md.j2`, `resume_protocol.md.j2`, `scan_markers.md.j2`.
- All three reference the **removed sibling system**: `SCAN_1..SCAN_7`, `frame_stack`, `merge_result`, `push/pop`, `peer_message`.
- **No code loads them**. `subagents/builder.py` only loads `specialist.md.tmpl` and `per_subagent/<role>.md.j2`.
- The orchestrator template (`orchestrator.md.j2`) doesn't reference them either.

**Verdict**: **DELETE these files**. The user is right that inter-agent communication protocols are valuable — but the new gawt-native design uses:
- `mcp__gitagent__send_message` for direct messages
- `mcp__gitagent__check_inbox` for inbox polling
- `mcp__gitagent__start_intent` / `repurpose` for semantic intent
- `mcp__gitagent__list_edits` / `list_intents` for observability

If a drift / inter-agent coordination protocol is needed in the future, it should be **redesigned for gawt primitives**, not ported from the dead sibling system.

**Action**:
- Delete `agents/janus/src/agents_janus/prompts/drift/` (all 3 files).
- Mark an investigation in the project KB: `Architecture decision: deadlock protocol on gawt primitives (deferred)`.

---

### 1.9 `plugins/` directory — KEEP

**User question**: "Could they be deleted?"

**Reality**: **NO**. The plugins are actively used:
- `plugins/__init__.py` exports `PLUGIN_REGISTRY` with 7 plugins: `scoring`, `download`, `ingest`, `training`, `prediction`, `data`, `commonlib`.
- `config/subagents.yaml` references these 7 plugins across 8 subagents (e.g., `abm: plugins: [scoring]`).
- `agent.py` line 351: `plugin_chain = [PLUGIN_REGISTRY[p]() for p in spec.plugins]` — every subagent's plugin chain is instantiated here.
- `agent.py` line 354: `all_tools.extend(plugin.tools(spec))` — plugin tools are added to each subagent.

**What the redesign plan says**:
- `m-agent-gitagent-redesign.md` §1.4: *"plugins/: Kept (except sibling). Domain plugins."*
- `agents/sibling.py` was to be removed (per §1.4). It's already removed — not on disk.

**Verdict**: **KEEP**. The plugins are the integration layer for subagent-specific tools (e.g., `pipeline_*` for scoring, `download_*` for the download plugin). Cannot be deleted.

---

### 1.10 `prompts/sibling_protocol.md.j2` + `common_role.md.j2` — DELETE

**Bonus find**: Two additional unreferenced prompt templates.
- `sibling_protocol.md.j2`: references `claim_file`, `peer_message_check_inbox`, SCAN protocol, `handoff_to_subagent`, fork brief, `merge_result`. All dead sibling system.
- `common_role.md.j2`: references `mailbox_check_inbox`, `peer_message_check_inbox`, `claim_file`, SCAN_1..SCAN_7, `merge_result`, `frame_stack`. All dead.
- No code references either file.

**Verdict**: **DELETE**.

---

## 2. Files needing updates

### 2.1 `trace_analyzer/judge.py` — REFACTOR to use Langfuse MCP

**User request**: Simplify using the Langfuse MCP server (https://cloud.langfuse.com/api/public/mcp) and `langchain-mcp-adapters`.

**Current state**:
- `judge_trace(trace_data: dict, ...)`: takes a parsed dict.
- `_build_trace_summary(trace_data)`: extracts tool_calls, spans, generations from the dict.
- Calls `ChatOpenAI` for OpenRouter or `init_chat_model` for other providers.

**Refactor strategy**:
1. Replace `trace_data: dict` input with `trace_id: str` (Langfuse trace ID).
2. Use `MultiServerMCPClient` from `langchain-mcp-adapters` to connect to the Langfuse MCP server (config from `opencode.json`).
3. Call `mcp__langfuse__get_observation` / `mcp__langfuse__list_observations` (or whatever the Langfuse MCP exposes) to fetch the trace.
4. Keep the LLM judge call (separate from the trace fetch) — the judge is still a ChatModel.
5. Keep `_parse_judge_response` and `JUDGE_SYSTEM_PROMPT` as-is.

**Sketch**:
```python
from langchain_mcp_adapters.client import MultiServerMCPClient

async def fetch_trace_via_mcp(trace_id: str) -> dict:
    """Fetch a Langfuse trace via the Langfuse MCP server."""
    config = {
        "langfuse": {
            "url": "https://cloud.langfuse.com/api/public/mcp",
            "transport": "streamable_http",
            "headers": {
                "Authorization": f"Basic {os.environ['LANGFUSE_MCP_AUTH']}"
            }
        }
    }
    client = MultiServerMCPClient(config)
    tools = await client.get_tools()
    # Find the trace-fetching tool (e.g., mcp__langfuse__getTrace or similar)
    # ... call it, return parsed dict ...
```

**Watchpoints**:
- `trace_analyzer/harness.py` currently calls `langfuse_client.get_trace(trace_id)` directly via the SDK. After this refactor, both `judge.py` and `harness.py` should go through the same MCP path for consistency.
- The judge needs to produce a verdict in a known shape. Keep `_build_trace_summary` as a fallback for traces that come in as a dict (e.g., from `_trace_from_result` in harness.py).
- If the MCP server is unreachable, fall back to raw `langfuse.Langfuse` SDK (what `harness.py` does today).

**Action**: Refactor `judge.py` to call Langfuse MCP, keep `_build_trace_summary` as a fallback.

---

### 2.2 `trace_analyzer/harness.py` — Make `goal` compulsory

**User request**: Remove `TRIAL_GOAL_DEFAULT`, make `goal` mandatory.

**Current state**:
- Line 28-34: `TRIAL_GOAL_DEFAULT = "TRIAL: run a full e2e test..."` — a long default sibling-coordination trial.
- Line 38: `def run_trial(goal: str = TRIAL_GOAL_DEFAULT, ...)`.
- Line 247: `parser.add_argument("--goal", "-g", default=TRIAL_GOAL_DEFAULT, ...)`.

**The default is doubly broken**:
1. It references the **removed sibling system** ("Use abm-worker as primary, spawn scoring-worker and ingest-worker as siblings").
2. The user wants `goal` to be required.

**Action**:
- Delete `TRIAL_GOAL_DEFAULT` (lines 28-34).
- Change `run_trial(goal: str = ...)` to `run_trial(goal: str)`.
- Change `parser.add_argument("--goal", default=...)` to `parser.add_argument("--goal", required=True)`.
- Update `tests/test_trace_harness.py` to pass an explicit `goal`.

---

### 2.3 `tools/onboard_tools.py` — MINOR CLEANUP

**User request**: Check if it needs updates.

**Reality**:
- Has `delegate_to_dispatcher` (matches dual-orchestrator plan §3 Step 5).
- Has `onboard_ask_subagent` (lightweight LLM call).
- The other tools (`onboard_run_abm`, `onboard_run_stage`, `onboard_run_pipeline`, `onboard_status`, `onboard_diagnose`, `onboard_list_components`) are all wired into the centinela tools in `agent.py` lines 204-214.

**Minor issue**: `onboard_run_abm` calls `mal_core.abm.runner.run_abm` directly. There's a parallel `tools/abm_tools.py` `abm_run` that calls `mal_core.abm.wrapper.run_abm_from_manifest`. Either consolidate or keep both intentionally.

**Action**: No major changes. Optional: consolidate `onboard_run_abm` with `abm_run` after deleting `abm_tools.py` (§1.3).

---

### 2.4 `tools/opencode_tool.py` — RENAME + rename function

**User request**: Rename the tool (the file is named `opencode_tool.py` but the function is `opencode_search`). Ensure it's available to agents.

**Current state**:
- File: `agents/janus/src/agents_janus/tools/opencode_tool.py`
- Function: `opencode_search(query, num_results=5)` — uses OpenRouter + Perplexity sonar for web search.
- Referenced by:
  - `tools/__init__.py` line 2, 22.
  - `agent.py` line 170, 178 (dispatcher tools).
  - `observability.py` line 80 (tool category map).
  - `agents/janus/README.md` (line 127, 171).
  - `docs/system-status.md`, `docs/plans/in-process/janus-dual-orchestrator.md`.
  - `social-networks/Janus Video/index.html` (third-party doc, ignore).

**Why "opencode" is misleading**:
- The filename suggests it's related to OpenCode (the agent harness). It's not.
- It's a generic web search tool that uses OpenRouter + Perplexity.

**Rename strategy**:
- File: `tools/opencode_tool.py` → `tools/web_search.py`
- Function: `opencode_search(query, ...)` → `web_search(query, ...)`
- Update all references:
  - `tools/__init__.py` (import + `__all__`)
  - `agent.py` (`_get_dispatcher_tools`)
  - `observability.py` (`_TOOL_CATEGORIES` map key)
  - `docs/system-status.md` (table row)
  - `README.md` (line 127, 171)
  - `docs/plans/in-process/janus-dual-orchestrator.md` (tool matrix)

**Note**: The dual-orchestrator plan tool matrix lists `opencode_search` as a dispatcher tool. Update that table after the rename.

**Action**: Rename file + function, update all references.

---

### 2.5 `tools/spawn_subagent.py` — DELETE

**User question**: Does it actually spawn a subagent or just point to the YAML?

**Reality**: It **only writes to the manifest and returns instructions**. Confirmed by reading the file:
- Lines 55-69: calls `append_agent(manifest_path, ...)` to update the YAML.
- Lines 78-90: returns a JSON string with instructions for the specialist to follow.

It does **NOT** actually call `mcp__gitagent__register_agent` or trigger a deepagents task. The function is a stub. The actual spawn happens when the orchestrator's LLM calls `mcp__gitagent__register_agent` and runs the deepagents task.

**Per the redesign plan §4.3**:
- The plan describes `spawn_subagent` as a "local Python function that wraps `mcp__gitagent__register_agent` + manifest update + deepagents task spawn."
- The current implementation does **none of the actual spawning** — just the manifest update + instructions.

**Verdict**: **DELETE**. The orchestrator-side dispatch uses deepagents' `task()` tool directly (per `orchestrator.md.j2` §5). The "cross-specialist call" case in `specialist.md.tmpl` line 71 mentions `spawn_subagent` but in the new model, a specialist should also just call `task()` directly (or use `mcp__gitagent__send_message` for messaging).

**Action**:
- Delete `tools/spawn_subagent.py`.
- Update `specialist.md.tmpl` line 71 to say "call the appropriate specialist via the `task()` tool" instead of `spawn_subagent`.
- Remove references in `tests/test_gawt_integration.py` (line 113) and `tests/test_llm_judge.py` (lines 185, 194, 365).
- Mark `m-agent-gitagent-redesign.md` §4.3/§6.4 as superseded.

**Counter-argument**: If we want a TRUE Python function that orchestrates a spawn (rather than relying on the LLM to chain `register_agent` + `task` + `start_intent`), we could refactor `spawn_subagent` to:
1. Call `mcp__gitagent__register_agent(role=...)` synchronously.
2. Append to manifest.
3. Call the deepagents task spawn function (not yet a helper).
4. Await or return.

But this is **considerably more work** and the spec is unclear. The simpler path is to delete and rely on the LLM-driven dispatch already in `orchestrator.md.j2`.

**Decision**: Delete. Revisit only if specialists need a non-LLM spawn path.

---

## 3. Files wrongly accused (KEEP)

| File | Why it's fine |
|---|---|
| `scope_validator.py` | Refactor needed, not delete. |
| `plugins/` | Active. Per-subagent tool composition. |

---

## 4. Master delete list

| Path | Reason |
|---|---|
| `trace_analyzer/checks.py` | Sibling system removed. |
| `trace_analyzer/analyzer.py` | Built on `checks.py`. |
| `tools/abm_tools.py` | Old per-agent worktree model. |
| `tools/improve_tool.py` | Wrong path, wrong concept. |
| `tools/spawn_subagent.py` | Doesn't actually spawn. |
| `prompts/templates/` (dir) | Old naming, unreferenced. |
| `prompts/patches/` (dir) | Empty. |
| `prompts/config/` (dir, 1 yaml) | Never wired in. |
| `prompts/drift/` (dir) | Replaced by self-fork peer coordination (§11) |
| `prompts/sibling_protocol.md.j2` | Replaced by Peer Coordination Protocol in specialist.md.tmpl (§11) |
| `prompts/common_role.md.j2` | Role duties merged into specialist.md.tmpl + InboxCheckMiddleware (§11) |
| `plugins/` (dir, 8 files) | Over-engineered: 6/7 were 1-line preamble stubs. ScorerPlugin hook never wired. Replaced by per_subagent templates (§13) |
| `tests/test_abm_tools.py` | Tests the deleted module. |

## 5. Master refactor list

| Path | Action |
|---|---|
| `scope_validator.py` | Source from `mcp__gitagent__list_edits` |
| `trace_analyzer/__init__.py` | Update exports |
| `trace_analyzer/judge.py` | Langfuse MCP |
| `trace_analyzer/harness.py` | `goal` mandatory |
| `tools/opencode_tool.py` → `tools/web_search.py` | Rename file + function |
| `tools/__init__.py` | Update imports + `__all__` |
| `tools/onboard_tools.py` | Remove `plugin_chain=[]` kwarg, remove `"plugins"` from JSON response (§13) |
| `agent.py` | Remove dead imports, rename `opencode_search` → `web_search` |
| `agent.py` | Remove PLUGIN_REGISTRY import + plugin_chain loop (§13) |
| `subagents/builder.py` | Remove build_resolved(), plugin_chain param, plugin preamble block (§13) |
| `subagents/base.py` | Remove ResolvedSubagent dataclass, plugins field from SubagentSpec (§13) |
| `subagents/__init__.py` | Remove ResolvedSubagent export (§13) |
| `subagents/registry.py` | Remove plugins= from spec construction (§13) |
| `config/subagents.yaml` | Remove plugins: lines from all 8 entries (§13) |
| `observability.py` | Update `_TOOL_CATEGORIES` map |
| `prompts/specialist.md.tmpl` | Replace `spawn_subagent` reference with `task()` + add Peer Coordination Protocol (§11) |
| `prompts/per_subagent/abm.md.j2` | Fix false claim "scoring runs automatically via ScorerPlugin" (§13) |
| `prompts/orchestrator.md.j2` | Add "Scoring after ABM changes" section (§13) |
| `tests/test_subagents.py` | Remove 3 broken tests + ResolvedSubagent test, clean up (§13) |
| `tests/test_scope_tools.py` | Remove plugins=() from _make_registry (§13) |
| `tests/test_gawt_integration.py` | Remove plugins=() from _make_registry (§13) |
| `tests/test_onboarding_e2e.py` | Remove plugin_chain assertions, rewrite test 3 (§13) |
| `tests/test_trace_harness.py` | Prune + explicit goal |
| `tests/test_gawt_integration.py` | Drop `spawn_subagent` |
| `tests/test_llm_judge.py` | Drop `spawn_subagent` |
| `middleware/inbox_check.py` | NEW: InboxCheckMiddleware — auto-checks inbox, detects conflicts (§11) |
| `tools/resolve_conflict.py` | NEW: resolve_conflict tool — self-fork + resolve + merge + cleanup (§11) |
| `tests/test_inbox_middleware.py` | NEW: unit tests for InboxCheckMiddleware (§11) |
| `tests/test_resolve_conflict.py` | NEW: integration tests for self-fork flow (§11) |
| `agent.py` | Wire InboxCheckMiddleware + resolve_conflict tool into subagent (§11) |
| `README.md` | Update tool table |
| `docs/system-status.md` | Update tool table |
| `docs/plans/in-process/janus-dual-orchestrator.md` | Update tool matrix |
| `docs/plans/in-process/m-agent-gitagent-redesign.md` | Mark §4.3/§6.4 superseded |

## 6. Order of operations

To keep the repo compilable after each step, do these in order:

0. **Plugin system removal (§13)** — DONE:
   - Deleted `plugins/` directory (8 files)
   - Removed plugin wiring from `agent.py`, `builder.py`, `base.py`, `__init__.py`, `registry.py`
   - Removed `plugins:` from `config/subagents.yaml`
   - Removed `plugins=()` from `test_scope_tools.py`, `test_gawt_integration.py`, `test_subagents.py`, `test_onboarding_e2e.py`
   - Removed `plugin_chain` from `tools/onboard_tools.py`
   - Fixed `per_subagent/abm.md.j2` scoring falsehood
   - Added scoring dispatch note to `orchestrator.md.j2`
   - Tests: 61/61 passing

1. **Delete-only pass** (no semantic changes):
   - Delete checks.py, analyzer.py
   - Delete templates/, patches/, config/, drift/
   - Delete sibling_protocol.md.j2, common_role.md.j2
   - Run tests: `cd agents/janus && uv run pytest tests/ -x --ignore=tests/test_trace_harness.py`

2. **Trace analyzer refactor**:
   - Update `__init__.py` exports
   - Refactor `judge.py` to use Langfuse MCP
   - Refactor `harness.py` to make `goal` mandatory
   - Update `tests/test_trace_harness.py`

3. **Tool deletions + renames**:
   - Delete `improve_tool.py`
   - Delete `abm_tools.py` + `test_abm_tools.py`
   - Delete `spawn_subagent.py`
   - Rename `opencode_tool.py` → `web_search.py`, `opencode_search` → `web_search`
   - Update `tools/__init__.py`, `agent.py`, `observability.py`
   - Update `specialist.md.tmpl` (replace `spawn_subagent` reference)
   - Update `tests/test_gawt_integration.py`, `tests/test_llm_judge.py`

4. **scope_validator refactor**:
   - Source from `mcp__gitagent__list_edits`
   - Update `tests/test_gawt_integration.py`

5. **Peer coordination protocol (§11)**:
   - Create `middleware/inbox_check.py` with InboxCheckMiddleware
   - Create `tests/test_inbox_middleware.py`
   - Update `specialist.md.tmpl` with Peer Coordination Protocol
   - Wire InboxCheckMiddleware in `agent.py`
   - Update `tests/test_gawt_integration.py`

6. **Docs pass**:
   - Update `README.md`, `docs/system-status.md`, `docs/plans/in-process/janus-dual-orchestrator.md`
   - Mark `m-agent-gitagent-redesign.md` §4.3 / §6.4 as superseded

## 7. Open questions

1. **`spawn_subagent.py`**: Delete (default) vs. refactor to actually call `mcp__gitagent__register_agent` + deepagents task? Simpler path: delete. Faithful path: refactor. **Recommendation: delete.**

2. **~~`prompts/drift/` redesign~~**: **RESOLVED** — see §11 below. Delete drift/, sibling_protocol.md.j2, common_role.md.j2. Replace with gawt-native peer coordination protocol injected into specialist.md.tmpl + InboxCheckMiddleware.

3. **Renaming `opencode_search`**: `web_search` (default) vs. `internet_search` vs. `exa_search`? **Recommendation: `web_search` — neutral, matches the project's no-brand convention.**

4. **`abm_test`/`abm_score`**: After deleting `abm_tools.py`, port to `pipeline_tool.py` or assume `pipeline_run_calibration` covers them? **Recommendation: assume coverage; port only if dispatcher workflow breaks.**

## 8. Risk notes

- **Deleting `trace_analyzer/` pieces** affects `tests/test_trace_harness.py` (40+ references). Need a careful test prune.
- **Deleting `abm_tools.py`** removes the dispatcher's only direct path to `abm_test` and `abm_score`. If we keep `pipeline_run_calibration` and `pipeline_compare_scorecards` for the dispatcher, this is fine. Otherwise, port `abm_test` and `abm_score` to `pipeline_tool.py`.
- **Deleting `spawn_subagent.py`** removes the only Python-level entry point for cross-specialist delegation. The replacement is the LLM-driven `task()` call already documented in `specialist.md.tmpl`. If users are calling `spawn_subagent` directly elsewhere, this is a breaking change.
- **Renaming `opencode_search` → `web_search`** affects `docs/system-status.md`, `README.md`, and the dual-orchestrator plan. Document the rename in the changelog.
- **Refactoring `judge.py` to use Langfuse MCP** adds a network dependency to the judge call. If the MCP server is unreachable, the judge fails. Add a fallback path that uses the raw `langfuse.Langfuse` SDK (which is what `harness.py` currently does).

## 9. Knowledge graph updates

After this audit, the following KB nodes should be created/updated:

| Node type | UUID | Summary |
|---|---|---|
| Pitfall | `pitfall-sibling-system-removed` | All `claim_file`, `peer_message`, `fork_brief`, `merge_result`, `scan_markers`, `frame_stack`, `mailbox` references are dead. Cite `m-agent-gitagent-redesign.md` §1.4. |
| Architecture | `arch-janus-tool-rename-opencode-to-websearch` | Renamed `opencode_search` → `web_search`. |
| Architecture | `arch-janus-trace-judge-uses-langfuse-mcp` | Langfuse MCP integration for trace fetching. |
| Architecture | `arch-spawn-subagent-deprecated` | Decision to delete `spawn_subagent.py` in favor of LLM-driven `task()`. |
| Architecture | `arch-peer-coordination-gawt-native` | Drift/ sibling protocols replaced by gawt-native peer coordination: InboxCheckMiddleware (auto-inbox detection), resolve_conflict tool (self-managed fork + SCAN evaluation + merge back + cleanup). Standardized CONFLICT_RESOLUTION_SCHEMA document produced per conflict. Original thread untouched, goal preserved. |
| Operational | `op-audit-janus-2026-08-10` | This audit document's findings. |

## 10. Out of scope (for later)

- **Migrating `abm_test` and `abm_score` to `pipeline_tool.py`**: do this if the delete breaks dispatcher workflow.
- **Cleaning up `m-agent-gitagent-redesign.md` §4.3 / §6.4**: just mark as superseded; full rewrite is a separate doc.
- **`research` subagent in `per_subagent/`**: only 9 files in `per_subagent/` (abm, commonlib, data, download, ingest, prediction, research, scoring, training) — `research` exists but is not in `subagents.yaml`. Either add to the registry or delete the template.

---

## 11. prompts/drift/ redesign — gawt-native peer coordination via self-fork

### Problem

The drift/ files (`fork_negotiation.md.j2`, `resume_protocol.md.j2`, `scan_markers.md.j2`) plus `sibling_protocol.md.j2` and `common_role.md.j2` contain **valuable inter-agent communication patterns** but reference the dead sibling system (`claim_file`, `peer_message`, `frame_stack`, `merge_result`, `SCAN_N` markers). These files are currently unreferenced by any code.

The audit (§1.8, §1.10) recommended deleting them. The user counter-proposal: **extract the useful protocols, adapt to gawt primitives, and inject into the specialist template using self-managed fork for conflict resolution**.

### What's useful vs what's dead

| Source file | Useful concept | Dead parts (sibling system) |
|---|---|---|
| `fork_negotiation.md.j2` | "When you receive a conflict: adapt / counter-propose / both" | frame_stack push/pop, SCAN markers, merge_result |
| `resume_protocol.md.j2` | "After resolving conflict, return to original goal" | frame_stack pop, render_resume() |
| `scan_markers.md.j2` | **7-question evaluation framework** for conflict analysis | @@SCAN_N syntax, CHECK/MISSED format |
| `sibling_protocol.md.j2` | "Check inbox, stay in scope, coordinate with peers" | claim_file, peer_message_check_inbox, frame_stack |
| `common_role.md.j2` | Role base: duties, peer registry, failure modes | mailbox_check_inbox, peer_message, claim_file, SCAN_1..7 |

### Design decision: self-fork over orchestrator interrupt()

Two architectures were considered:

| Aspect | Self-fork (chosen) | Orchestrator interrupt() |
|---|---|---|
| Who resolves | The agent itself (via internal fork) | The orchestrator (external loop) |
| Latency | Higher (extra LLM in fork) | Lower (orchestrator resolves fast) |
| Isolation | Strong (fork thread isolated) | Medium (shared checkpoint) |
| Complexity | Recursive (agent calls itself) | Linear (orchestrator loop) |
| Best for | Complex conflicts needing deep analysis | Simple conflicts, quick decision |

**Self-fork is chosen** because it keeps subagents autonomous — no orchestrator involvement required for peer coordination. The orchestrator only sees the final result.

### Architecture: three mechanisms

#### Mechanism 1: InboxCheckMiddleware (automatic notification via callback)

**Problem**: Subagents currently must explicitly call `check_inbox(agent_id)` after each edit. If they forget, they miss conflict messages.

**Solution**: A deepagents middleware that wraps every tool call and automatically checks the inbox. The subagent never has to remember.

**How it works** (based on deepagents `wrap_tool_call` pattern):

```python
# agents/janus/src/agents_janus/middleware/inbox_check.py

from langchain.agents.middleware import wrap_tool_call
from typing import Any

class InboxCheckMiddleware:
    """Middleware that auto-checks gawt inbox after each tool call.

    Uses deepagents' wrap_tool_call pattern. After every tool call,
    if the agent has an agent_id in state, poll check_inbox() and
    inject any pending messages into the tool result.

    Architecture:
    - Deep Agents middleware wraps tool calls via wrap_tool_call()
    - After handler(request) returns, we call check_inbox(agent_id)
    - If messages exist, append them to the tool result as a warning block
    - The LLM sees peer messages on EVERY tool call, not just when it remembers to poll
    - If a conflict is detected (file_overlap), mark it loudly so the LLM
      knows to call resolve_conflict immediately

    State extension:
    - agent_id: str — set by specialist after register_agent()
    - inbox_last_checked_at: str — ISO timestamp of last auto-check
    - pending_peer_messages: list[dict] — accumulated unchecked messages
    """

    name = "InboxCheckMiddleware"

    def wrap_tool_call(self, request, handler):
        result = handler(request)

        agent_id = self._get_agent_id(request)
        if not agent_id:
            return result

        try:
            messages = self._check_inbox(agent_id)
        except Exception:
            return result  # MCP unreachable, don't block

        if not messages:
            return result

        # Check if any message is a conflict (targets files this agent owns)
        conflict = self._detect_conflict(messages, request)

        if conflict:
            return self._mark_conflict(result, conflict)

        # No conflict — inject routine messages
        return self._inject_messages(result, messages)

    def _detect_conflict(self, messages, request) -> dict | None:
        """Check if any inbox message targets files this agent is editing."""
        for msg in messages:
            if msg.get("type") == "file_overlap":
                return {
                    "from_agent": msg["from_agent"],
                    "message": msg["message"],
                    "files": msg.get("files", []),
                }
        return None

    def _mark_conflict(self, result, conflict: dict) -> str:
        """Append loud conflict marker to tool result so the LLM takes action."""
        marker = (
            f"\n\n🛑 CONFLICT DETECTED from {conflict['from_agent']}.\n"
            f"Files: {', '.join(conflict['files'])}\n"
            f"Message: {conflict['message']}\n\n"
            "REQUIRED ACTION: Call the `resolve_conflict` tool IMMEDIATELY.\n"
            "Do NOT make any more edits until the conflict is resolved.\n"
            "Pass the conflict_message and files list to resolve_conflict()."
        )
        if isinstance(result, str):
            return result + marker
        return str(result) + marker
```

#### Mechanism 2: resolve_conflict tool (self-managed fork + resolve + merge)

**Problem**: When an agent receives a conflict, it needs to resolve it without losing its original goal or repeating work.

**Solution**: A tool that the agent calls to **fork its own conversation**, run conflict resolution in the fork, extract a structured summary, merge the summary back into the original thread, and **clean up the fork**.

**How it works**:

```python
# agents/janus/src/agents_janus/tools/resolve_conflict.py

from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage
import uuid
import json
from datetime import datetime, timezone


# Standardized conflict resolution document schema
CONFLICT_RESOLUTION_SCHEMA = {
    "type": "object",
    "properties": {
        "resolution_id": {"type": "string"},
        "timestamp": {"type": "string", "format": "date-time"},
        "conflict": {
            "type": "object",
            "properties": {
                "from_agent": {"type": "string"},
                "message": {"type": "string"},
                "files": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["from_agent", "message", "files"],
        },
        "scan_evaluation": {
            "type": "object",
            "properties": {
                "peer_intent": {"type": "string"},
                "peer_edits_summary": {"type": "string"},
                "my_goal": {"type": "string"},
                "decision_rationale": {"type": "string"},
            },
        },
        "decision": {
            "type": "string",
            "enum": ["adapt", "counter_propose", "both", "escalate"],
        },
        "actions_taken": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "action": {"type": "string"},
                    "target": {"type": "string"},
                    "result": {"type": "string"},
                },
            },
        },
        "files_kept_by_me": {"type": "array", "items": {"type": "string"}},
        "files_reverted_by_me": {"type": "array", "items": {"type": "string"}},
        "summary": {"type": "string"},
        "next_steps": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "resolution_id",
        "timestamp",
        "conflict",
        "decision",
        "summary",
    ],
}


def make_resolve_conflict_tool(agent, config, checkpointer=None):
    """Create a resolve_conflict tool bound to the agent's own graph.

    The tool uses the agent's self-reference to fork its own conversation,
    resolve the conflict in the fork, extract a structured resolution
    document, merge it into the original thread, and clean up the fork.

    Args:
        agent: The compiled agent graph (from create_deep_agent)
        config: The agent's main config (with thread_id)
        checkpointer: Optional checkpointer for cleanup
    """

    @tool
    def resolve_conflict(conflict_message: str, files: list[str]) -> str:
        """Fork your conversation, resolve the conflict, merge back, and clean up.

        Use this tool IMMEDIATELY when you see a CONFLICT DETECTED marker
        in a tool result. The tool:

        1. Forks your current conversation into an isolated thread
        2. Runs conflict resolution (SCAN evaluation, peer communication)
        3. Extracts a structured resolution document
        4. Injects the resolution into your current thread
        5. Cleans up the fork thread (memory freed)
        6. Returns the resolution summary so you can continue your task

        Args:
            conflict_message: The conflict description from the peer agent
            files: List of files involved in the conflict

        Returns:
            A structured JSON document (see CONFLICT_RESOLUTION_SCHEMA)
            containing the resolution summary, decisions, and next steps.
        """
        # 1. Snapshot current state from original thread
        snapshot = agent.get_state(config)

        # 2. Create fork thread with unique ID
        fork_thread_id = f"conflict-{uuid.uuid4().hex[:8]}"
        fork_config = {"configurable": {"thread_id": fork_thread_id}}

        # 3. Fork: copy state to new thread (non-destructive)
        agent.update_state(fork_config, snapshot.values)

        # 4. Inject conflict resolution prompt into fork
        resolution_prompt = (
            "CONFLICT RESOLUTION MODE\n\n"
            f"Peer message: {conflict_message}\n"
            f"Affected files: {', '.join(files)}\n\n"
            "You are in an isolated fork. Do NOT trigger further conflicts.\n"
            "Do NOT edit any files directly from this fork — only communicate.\n\n"
            "Steps:\n"
            "1. Read peer intent via gawt_list_intents()\n"
            "2. Read peer edits via gawt_list_edits(since_ts=...)\n"
            "3. Evaluate using SCAN framework (7 questions):\n"
            "   - What is the other agent trying to achieve?\n"
            "   - What is MY original goal?\n"
            "   - What exactly did they change?\n"
            "   - Options: A) Adapt, B) Counter-propose, C) Both\n"
            "   - Which rules are at risk?\n"
            "   - Failure mode?\n"
            "   - Negotiation vocabulary?\n"
            "4. Decide: adapt / counter-propose / both / escalate\n"
            "5. Communicate via gawt_send_message()\n"
            "6. Provide your resolution as a JSON document matching this schema:\n"
            f"{json.dumps(CONFLICT_RESOLUTION_SCHEMA, indent=2)}\n\n"
            "Your FINAL message must be ONLY the JSON document."
        )

        agent.update_state(fork_config, {
            "messages": [HumanMessage(content=resolution_prompt)]
        })

        # 5. Run resolution in fork (same agent, same model)
        try:
            result = agent.invoke(None, fork_config)
            resolution_text = result["messages"][-1].content
        except Exception as e:
            # Fork failed — clean up and escalate
            if checkpointer:
                checkpointer.delete_thread(fork_thread_id)
            return json.dumps({
                "resolution_id": f"failed-{uuid.uuid4().hex[:8]}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "conflict": {
                    "from_agent": "unknown",
                    "message": conflict_message,
                    "files": files,
                },
                "decision": "escalate",
                "summary": f"Fork resolution failed: {str(e)}. Escalating to orchestrator.",
                "actions_taken": [],
            })

        # 6. Parse resolution document
        try:
            resolution_doc = json.loads(resolution_text)
        except json.JSONDecodeError:
            # LLM didn't return valid JSON — wrap it
            resolution_doc = {
                "resolution_id": f"unstructured-{uuid.uuid4().hex[:8]}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "conflict": {
                    "from_agent": "unknown",
                    "message": conflict_message,
                    "files": files,
                },
                "decision": "unclear",
                "summary": resolution_text,
                "actions_taken": [],
            }

        # 7. Inject structured resolution into ORIGINAL thread
        agent.update_state(config, {
            "messages": [SystemMessage(content=(
                "CONFLICT RESOLVED via self-fork.\n\n"
                f"Resolution document:\n{json.dumps(resolution_doc, indent=2)}\n\n"
                "Continue your original task. The conflict has been resolved."
            ))]
        })

        # 8. Clean up fork thread (memory freed)
        if checkpointer:
            try:
                checkpointer.delete_thread(fork_thread_id)
            except Exception:
                pass  # best-effort cleanup

        # 9. Return structured document for immediate LLM context
        return json.dumps(resolution_doc, indent=2)

    return resolve_conflict
```

#### Mechanism 3: SCAN 7-question framework (preserved from drift/)

The SCAN markers from `scan_markers.md.j2` are a **excellent evaluation framework**. We preserve the 7 questions, adapting them to gawt primitives:

| SCAN original | gawt-native equivalent |
|---|---|
| `@@SCAN_1`: What the other agent is about to do | `list_intents()` → read their `start_intent` |
| `@@SCAN_2`: Your original goal | Read from fork snapshot (preserved by fork) |
| `@@SCAN_3`: What they changed | `list_edits(since_ts=...)` → file + lines |
| `@@SCAN_4`: Adapt / Counter-propose / Both | Same decision logic |
| `@@SCAN_5`: Rules at risk | Same (API contracts, scope boundaries) |
| `@@SCAN_6`: Failure mode | Same |
| `@@SCAN_7`: Negotiation vocabulary | Same — terms for proposing common ground |

### State schema

```python
class SpecialistState(TypedDict):
    # gawt identity
    agent_id: str | None              # set after register_agent()
    original_goal: str                # saved at start_intent
    current_step: str | None          # "step 3/5: editing engine.hpp"

    # inbox tracking
    inbox_last_checked_at: str        # ISO timestamp
    pending_peer_messages: list       # accumulated routine messages

    # fork tracking (telemetry + cleanup)
    conflict_count: int               # number of conflicts resolved
    last_fork_thread_id: str | None   # for debugging/audit

    # inherited from DeepAgentState
    messages: Annotated[list[AnyMessage], DeltaChannel(...)]
```

### How self-fork preserves state

```
ORIGINAL THREAD (agent working on goal X)
  ↓
edit_file("engine.hpp") → tool OK
  ↓
InboxCheckMiddleware detects conflict from "scoring"
  ↓
Tool result includes: "🛑 CONFLICT DETECTED... Call resolve_conflict"
  ↓
LLM sees marker → calls resolve_conflict("...", ["engine.hpp"])
  ↓
resolve_conflict tool runs:
  │
  ├─ 1. snapshot = agent.get_state(original_config)
  ├─ 2. fork_thread_id = "conflict-abc123"
  ├─ 3. agent.update_state(fork_config, snapshot.values)  ← FORK CREATED
  ├─ 4. agent.update_state(fork_config, {messages: [HumanMessage(resolution_prompt)]})
  ├─ 5. agent.invoke(None, fork_config)                   ← LLM RUNS IN FORK
  │     ├─ LLM reads peer intents
  │     ├─ LLM reads peer edits
  │     ├─ LLM evaluates SCAN
  │     ├─ LLM decides
  │     ├─ LLM sends message to peer
  │     └─ LLM returns JSON resolution document
  ├─ 6. resolution_doc = parse JSON
  ├─ 7. agent.update_state(original_config, {messages: [SystemMessage(resolution)]})
  │                                                          ← MERGE BACK
  ├─ 8. checkpointer.delete_thread(fork_thread_id)          ← CLEANUP
  └─ 9. return resolution_doc
  ↓
Agent sees: "CONFLICT RESOLVED: {...resolution document...}"
  ↓
Agent continues original goal X with conflict resolved
  ↓
No tool calls re-executed
Original thread messages preserved (just appended SystemMessage)
```

### Flow diagram

```
┌─────────────────────────────────────────────────────┐
│         ORIGINAL THREAD (a_abm)                      │
│                                                     │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐      │
│  │  LLM call │───▶│  Tools   │───▶│  Inbox   │      │
│  │           │    │  execute │    │  check   │      │
│  └──────────┘    └──────────┘    └─────┬────┘      │
│                                        │            │
│                                  Conflict?           │
│                                  Yes │               │
│                                       │              │
│                                       ▼              │
│                              LLM calls               │
│                              resolve_conflict()      │
│                                       │              │
└───────────────────────────────────────┼──────────────┘
                                        │
                                        ▼
        ┌───────────────────────────────────────────┐
        │  resolve_conflict TOOL                     │
        │                                           │
        │  1. snapshot original state               │
        │  2. fork thread: "conflict-{uuid}"        │
        │  3. copy state to fork                    │
        │  4. inject resolution prompt              │
        │  5. run agent.invoke(None, fork_config)   │
        │  6. extract resolution document           │
        │  7. inject into original thread           │
        │  8. cleanup fork (delete_thread)          │
        │  9. return document                       │
        └───────────────────────────────────────────┘
                                        │
                                        ▼
        ┌───────────────────────────────────────────┐
        │  FORK THREAD (conflict-{uuid})            │
        │                                           │
        │  Isolated copy of original state          │
        │  + Resolution prompt                      │
        │  + LLM runs SCAN evaluation               │
        │  + LLM communicates with peer             │
        │  + Final message: JSON resolution doc     │
        │                                           │
        │  Lifecycle: created → resolve → DELETED   │
        └───────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────┐
│  ORIGINAL THREAD (resumes with resolution injected)  │
│                                                     │
│  Agent sees: SystemMessage with resolution doc      │
│  Continues original goal with conflict resolved      │
│  No re-execution, no goal drift                      │
└─────────────────────────────────────────────────────┘
```

### Standardized conflict resolution document

Every conflict resolution produces a JSON document conforming to `CONFLICT_RESOLUTION_SCHEMA`:

```json
{
  "resolution_id": "conflict-abc12345",
  "timestamp": "2026-08-11T15:30:00Z",
  "conflict": {
    "from_agent": "a_scoring",
    "message": "Editing D14 scorer temperature curve",
    "files": ["mal-core/src/mal_core/abm/d14_scorer.py"]
  },
  "scan_evaluation": {
    "peer_intent": "scoring wants to fix adult survival curve",
    "peer_edits_summary": "Modified lines 45-67, changed temperature coefficient",
    "my_goal": "Fix gonotrophic cycle parameters",
    "decision_rationale": "Peer's change doesn't affect my files. Safe to adapt."
  },
  "decision": "adapt",
  "actions_taken": [
    {
      "action": "send_message",
      "target": "a_scoring",
      "result": "Acknowledged your change. Proceeding with my work."
    }
  ],
  "files_kept_by_me": [],
  "files_reverted_by_me": [],
  "summary": "Conflict resolved by acknowledging peer's independent change. My work on gonotrophic cycle unaffected.",
  "next_steps": [
    "Continue editing gonotrophic cycle parameters",
    "Verify no overlap after my next edit"
  ]
}
```

This document is:
- **Structured** — parseable by other agents and tools
- **Self-describing** — includes conflict context, decision, and rationale
- **Auditable** — timestamp + resolution_id + actions_taken
- **Actionable** — next_steps tell the agent what to do

### Files to delete

| Path | Reason |
|---|---|
| `prompts/drift/fork_negotiation.md.j2` | Replaced by resolve_conflict tool (self-fork) |
| `prompts/drift/resume_protocol.md.j2` | Replaced by fork + merge back |
| `prompts/drift/scan_markers.md.j2` | 7-question framework injected into fork prompt |
| `prompts/sibling_protocol.md.j2` | Replaced by Peer Coordination Protocol |
| `prompts/common_role.md.j2` | Role duties merged into specialist.md.tmpl |

### Files to create

| Path | Purpose |
|---|---|
| `middleware/inbox_check.py` | InboxCheckMiddleware — auto-checks inbox, detects conflicts |
| `tools/resolve_conflict.py` | resolve_conflict tool — self-fork + resolve + merge + cleanup |
| `tests/test_inbox_middleware.py` | Unit tests for InboxCheckMiddleware |
| `tests/test_resolve_conflict.py` | Integration tests for self-fork flow |

### Files to modify

| Path | Change |
|---|---|
| `prompts/specialist.md.tmpl` | Add Peer Coordination Protocol section (self-fork-aware) |
| `agent.py` | Wire InboxCheckMiddleware + resolve_conflict tool into subagent |
| `tests/test_gawt_integration.py` | Add tests for self-fork conflict flow |

### Implementation order

1. Create `middleware/inbox_check.py` with InboxCheckMiddleware
2. Create `tools/resolve_conflict.py` with resolve_conflict tool
3. Update `specialist.md.tmpl` with Peer Coordination Protocol
4. Wire everything in `agent.py`
5. Delete drift/, sibling_protocol.md.j2, common_role.md.j2
6. Create tests
7. Run full test suite

### Risk notes

- **Fork memory cost**: each conflict creates a new thread with full state copy. Mitigation: `delete_thread()` after resolution.
- **Recursive complexity**: agent calls itself via tool. The resolve_conflict tool runs the SAME agent in the fork with a different prompt. Risk of infinite recursion if the fork also triggers a conflict. Mitigation: the fork prompt explicitly says "Do NOT trigger further conflicts" and uses read-only tools (list_intents, list_edits, send_message).
- **Fork LLM cost**: fork runs additional LLM calls with the SAME model. Mitigation: acceptable cost for autonomous conflict resolution.
- **No orchestrator oversight**: orchestrator doesn't see conflict resolution unless agent explicitly sends message. Mitigation: `resolve_conflict` sends a brief notification to `__orchestrator__` via `send_message` with the resolution_id.
- **JSON parsing failure**: LLM might not return valid JSON. Mitigation: wrap unstructured output in a valid schema with `decision: "unclear"` and `summary: <raw text>`.
- **Fork cleanup failure**: `delete_thread()` might fail (e.g., checkpointer doesn't support it). Mitigation: best-effort cleanup, fork threads are isolated and don't affect original thread.

---

## §13 — Plugin system removal (flattened into per_subagent templates)

**Date**: 2026-08-11
**Status**: DONE

### Problem

The plugin system (`plugins/` directory, 8 files, ~80 lines) was over-engineered for its actual use case. 6 of 7 plugins were stubs returning a single-line preamble. The `ScorerPlugin` defined an `after_task` hook that was **never wired** — the hook existed in code but no lifecycle code invoked it. The `ResolvedSubagent` dataclass, `build_resolved()` function, and `plugin_chain` parameter were infrastructure that never connected to a consumer.

Additionally, `ReadOnlyPlugin` and `EditPlugin` were referenced in tests but didn't exist on disk (only `.pyc` in `__pycache__`), causing 3 test failures.

### What was removed

| File | Reason |
|---|---|
| `plugins/__init__.py` | PLUGIN_REGISTRY + re-exports |
| `plugins/base.py` | Plugin ABC with tools/permissions/preamble/hooks/apply |
| `plugins/scoring.py` | after_task hook (never invoked) + 1-line preamble |
| `plugins/download.py` | 1-line preamble stub |
| `plugins/ingest.py` | 1-line preamble stub |
| `plugins/training.py` | 1-line preamble stub |
| `plugins/prediction.py` | 1-line preamble stub |
| `plugins/data.py` | 1-line preamble stub |
| `plugins/commonlib.py` | 1-line preamble stub |

### What was refactored

| File | Change |
|---|---|
| `agent.py` | Removed `PLUGIN_REGISTRY` import, `plugin_chain` loop, simplified to direct gawt_tools + ask_user_tool |
| `subagents/builder.py` | Removed `build_resolved()` function, `plugin_chain` param, plugin preamble block. Now takes `(spec, all_specs)` only |
| `subagents/base.py` | Removed `ResolvedSubagent` dataclass, `plugins` field from `SubagentSpec`, `Any`/`Callable` imports |
| `subagents/__init__.py` | Removed `ResolvedSubagent` export, updated `build_subagent` → `build_subagent_prompt` |
| `subagents/registry.py` | Removed `plugins=tuple(entry.get("plugins", []))` from spec construction |
| `config/subagents.yaml` | Removed `plugins: [...]` from all 8 subagent entries |
| `tools/onboard_tools.py` | Removed `plugin_chain=[]` kwarg, removed `"plugins"` from JSON response |
| `tests/test_subagents.py` | Removed 3 broken tests (`test_readonly_plugin`, `test_edit_plugin`, `test_builder_chain`), `test_resolved_subagent`, all `plugins=()` kwargs. Added `test_subagent_spec_no_plugins_field` |
| `tests/test_scope_tools.py` | Removed `plugins=()` from `_make_registry()` (6 SubagentSpec instances) |
| `tests/test_gawt_integration.py` | Removed `plugins=()` from `_make_registry()` (3 SubagentSpec instances) |
| `tests/test_onboarding_e2e.py` | Removed `mock_spec.plugins = ()` assignments, rewrote test 3 to verify new signature |
| `prompts/per_subagent/abm.md.j2` | Fixed false claim "scoring runs automatically via ScorerPlugin" → "orchestrator dispatches scoring explicitly" |
| `prompts/orchestrator.md.j2` | Added "Scoring after ABM changes" section — orchestrator must dispatch scoring after ABM edits |

### Result

- **Before**: 7 plugin files + base ABC + PLUGIN_REGISTRY + build_resolved + ResolvedSubagent + plugin_chain param + 3 broken tests = ~130 lines of dead/over-engineered code
- **After**: 0 plugin references in code. Prompt content lives in `per_subagent/*.md.j2` templates (already existed). Orchestrator prompt documents scoring responsibility.
- **Tests**: 61/61 passing (was 9/9 broken + 6/6 passing in test_subagents.py; now 6/6 passing with no broken tests)

### Where prompt content lives now

| Content | Location |
|---|---|
| Per-subagent domain instructions | `prompts/per_subagent/{name}.md.j2` (already existed, 4-7 lines each) |
| Behavioral spec (from docs/specs/) | Injected via `build_subagent_prompt()` Layer A |
| Specialist protocol (gawt lifecycle) | `prompts/specialist.md.tmpl` (Layer B) |
| Scoring responsibility | `prompts/orchestrator.md.j2` + `prompts/per_subagent/abm.md.j2` |
