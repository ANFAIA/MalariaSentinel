---
name: subagents-loops
description: Reference guide for all 7 subagent loops in MalariaSentinel. Covers when to use each loop, what brief to send, expected outputs, and coordination patterns. Use when delegating work to a subagent, choosing the right loop for a task, or understanding the agent architecture.
---

# Subagent Loops Reference

The supervisor delegates work to 7 specialised loops. Each loop is a self-contained subagent (or primary agent) with bounded permissions and a structured output contract. This skill tells you **which loop to spawn**, **what to put in the brief**, and **what comes back**.

## Overview

| Loop | Mode | Read/Write | Use when | Brief needs |
|---|---|---|---|---|
| `test-fixer` | subagent | write (edit+bash) | Tests/lint/checks fail | `check_command`, `worktree_path` |
| `code-reviewer` | subagent | read-only | Reviewing a diff, validating conventions | `diff_or_paths`, `focus_areas` |
| `doc-researcher` | subagent | read-only + web | Answering a research question | `question` |
| `security-auditor` | subagent | read-only | Security review, OWASP audit | `paths` or `diff` or `config` |
| `memory-curator` | subagent | write (KG only) | Recording findings, adding nodes/rels | items to record |
| `kb-updater` | primary | read-only + KG read | Daily KB maintenance from commits | none (self-directed) |
| `improvement-agent` | primary | write (harness only) | After a research cycle, improving prompts/tools | phase outputs |

---

## 1. test-fixer

**Purpose:** Iterates a check command until it exits 0. The loop is: run → read failure → minimal fix → re-run. Never skips, comments out, or weakens tests to force a pass.

**When to use:**
- `uv run pytest` fails
- `ruff check` or any linter fails
- Any CLI check command returns non-zero and you need it fixed

**When NOT to use:**
- You need a code review (use `code-reviewer`)
- You need to understand *why* something fails before fixing (use `doc-researcher` or investigate manually first)
- The failure requires knowledge graph changes (route to `memory-curator`)

**Brief format:**
```json
{
  "check_command": "uv run pytest mal-core/tests/ -v",
  "target_paths": ["mal-core/tests/test_foo.py"],
  "worktree_path": "/path/to/gitagent/worktree",
  "context": "Fails on line 42 with AssertionError"
}
```

- `check_command` — **required**. The exact command to make pass.
- `target_paths` — optional. Files the fix likely touches.
- `worktree_path` — **expected** (required if edits needed). The gitagent worktree directory. If missing and edits are needed, the loop returns `blocked`.
- `context` — optional. Free-form context about the failure.

**Expected output:**
```json
{
  "status": "ok" | "blocked",
  "summary": "Fixed by adding missing import in foo.py",
  "evidence_refs": ["git diff abc123"],
  "blocker": "... (only if blocked)",
  "next_action": "... (only if blocked)"
}
```

**Permissions:** `edit=allow`, `bash(uv run pytest, git diff/status/log)=allow`, `webfetch/websearch=deny`. All other bash is `ask`.

**Example invocation:**
```json
{
  "description": "Fix failing test suite",
  "subagent_type": "test-fixer",
  "prompt": "Check command: uv run pytest mal-core/tests/ -v\nWorktree: /path/to/worktree\nContext: 2 tests fail in test_dataset.py — KeyError on missing column 'elevation'"
}
```

**Gitagent:** If the loop edits files, it finishes with `gitagent propose` from inside its worktree. The supervisor integrates.

---

## 2. code-reviewer

**Purpose:** Reviews code changes and returns structured findings. Read-only — never edits files, even if asked.

**When to use:**
- Reviewing a PR diff before merging
- Validating code conventions across changed files
- Checking for anti-patterns, performance issues, or security concerns in a diff

**When NOT to use:**
- You need someone to *fix* the code (route findings to `test-fixer`)
- You need domain knowledge (use `doc-researcher`)
- You need a security-specific audit (use `security-auditor`)

**Brief format:**
```json
{
  "diff_or_paths": "git diff main..HEAD" | ["mal-core/foo.py", "mal-core/bar.py"],
  "focus_areas": ["security", "performance", "conventions"],
  "conventions_ref": "pref-python-conventions"
}
```

- `diff_or_paths` — **required**. Either a diff string or a list of file paths.
- `focus_areas` — optional. Areas to focus on (e.g. `security`, `performance`, `conventions`).
- `conventions_ref` — optional. UUID of a `Preference` node in the KB with project conventions.

**Expected output:**
```json
{
  "status": "ok" | "blocked",
  "findings": [
    {"severity": "high", "area": "security", "file": "mal-core/api.py", "line": 42, "message": "Secret in plaintext", "suggestion": "Use env var"}
  ],
  "summary": "3 findings: 1 high, 2 medium",
  "evidence_refs": []
}
```

**Permissions:** `edit=deny`, `bash(git diff/log)=allow`. Read-only — no writes, no network.

**Example invocation:**
```json
{
  "description": "Review diff before merge",
  "subagent_type": "code-reviewer",
  "prompt": "Diff: git diff main..HEAD\nFocus: security, conventions"
}
```

---

## 3. doc-researcher

**Purpose:** Answers research questions by querying the knowledge base first, falling back to web search when the KB is insufficient. Returns a brief summary, not raw content.

**When to use:**
- "What does the Kelly et al. 2012 paper say about X?"
- "How do we handle terrain data in the pipeline?"
- "What's the current approach to calibration scoring?"

**When NOT to use:**
- You need to record a new finding (use `memory-curator`)
- You need code fixed (use `test-fixer`)
- You need a code review (use `code-reviewer`)

**Brief format:**
```json
{
  "question": "How does the suitability model use elevation data?"
}
```

- `question` — **required**. The research question.

**Expected output:**
```json
{
  "status": "ok" | "partial" | "blocked",
  "brief": "The suitability model uses DEM tiles from...",
  "evidence": [
    {"source": "kb", "ref": "uuid-comp-terrain", "excerpt": "..."},
    {"source": "web", "ref": "https://...", "excerpt": "..."}
  ],
  "suggested_kb_writes": [
    {"type": "Pattern", "name": "Terrain data pipeline", "summary": "..."}
  ]
}
```

**Permissions:** `edit=deny`, `webfetch/websearch=allow`. No writes to the KB — returns `suggested_kb_writes` for the supervisor to route to `memory-curator`.

**Example invocation:**
```json
{
  "description": "Research terrain data approach",
  "subagent_type": "doc-researcher",
  "prompt": "Question: How does the suitability model use elevation data from the DEM tiles?"
}
```

---

## 4. security-auditor

**Purpose:** OWASP Top 10 audit. Read-only. Identifies security issues and ranks them by severity with CWE IDs.

**When to use:**
- Before merging sensitive changes (new API endpoints, auth logic, data handling)
- Periodic security review of the codebase
- After adding external dependencies

**When NOT to use:**
- You need general code review (use `code-reviewer`)
- You need code fixed (route findings to `test-fixer`)
- You need to research security best practices (use `doc-researcher`)

**Brief format:**
```json
{
  "paths": ["mal-core/api/"],
  "diff": "git diff main..HEAD -- mal-core/api/",
  "config": ["opencode.json"]
}
```

At least one of `paths`, `diff`, or `config` is required.

**Expected output:**
```json
{
  "status": "ok" | "blocked",
  "findings": [
    {"severity": "critical", "owasp_id": "A02", "file": "mal-core/api/auth.py", "line": 15, "message": "Hardcoded API key", "fix_suggestion": "Use environment variable", "cwe_id": "CWE-798"}
  ],
  "summary": "1 critical, 2 medium findings",
  "evidence_refs": []
}
```

**Permissions:** `edit=deny`, `bash=deny`, `web=deny`. Purely read-only analysis.

**Example invocation:**
```json
{
  "description": "Security audit of API layer",
  "subagent_type": "security-auditor",
  "prompt": "Paths: mal-core/api/\nFocus: OWASP Top 10"
}
```

---

## 5. memory-curator

**Purpose:** The **only** loop that writes to the knowledge graph. Decides label, tree placement, parent, and lateral edges. All other loops read the KB; they never write.

**When to use:**
- Recording a pitfall, pattern, or architecture decision
- Adding a new component or investigation node
- Connecting nodes with lateral edges (USES, IMPLEMENTS, BLOCKS, etc.)
- Updating existing nodes with new evidence

**When NOT to use:**
- You need to *read* the KB (use `doc-researcher` or query directly)
- You need code fixed (use `test-fixer`)
- You need to plan a KB update from commits (use `kb-updater`)

**Brief format:**
```json
{
  "items": [
    {"action": "create|update|connect", "type": "Pitfall", "name": "...", "summary": "...", "parent": "project-wisdom"},
    {"action": "connect", "type": "MITIGATED_BY", "src": "pitfall-x", "dst": "pattern-y"}
  ],
  "pre_approved": false
}
```

- `items` — **required**. List of operations (create, update, connect).
- `pre_approved` — optional. If `true` and UUIDs are provided, skips individual recall.

**Mandatory first step:** Load the `project-memory` skill before doing anything.

**Expected output:**
```json
{
  "status": "ok" | "blocked" | "needs_decision",
  "writes": [
    {"op": "create", "uuid": "pitfall-test-skip", "type": "Pitfall", "label": "Pitfall", "summary_of_change": "Created node"}
  ],
  "evidence_refs": ["memory_audit output"]
}
```

**Permissions:** `memory_node/memory_rel=ask` (every write prompts approval), `memory_query/recall/audit/status=allow`. No `edit`, no `bash`, no `web`.

**Example invocation:**
```json
{
  "description": "Record new pitfall from test failure investigation",
  "subagent_type": "memory-curator",
  "prompt": "Items:\n- create Pitfall uuid=pitfall-unet-missing-import summary='U-Net training fails when mal_commonlib.geometry is not imported before torch...'\n- connect MITIGATED_BY src=pitfall-unet-missing-import dst=pattern-import-ordering"
}
```

---

## 6. kb-updater

**Purpose:** Daily KB maintenance — reviews recent commits, identifies what's missing from the knowledge graph, produces a structured update plan, and delegates execution to `memory-curator`. **Never writes to the KG directly.**

**When to use:**
- End-of-day or end-of-session KB sync
- After a batch of commits that introduced new components, decisions, or patterns
- Periodic maintenance to keep the KG current

**When NOT to use:**
- You need to record a single finding immediately (use `memory-curator` directly)
- You need code or tests fixed (use `test-fixer`)

**Brief format:** None — this is a primary agent that runs self-directed. It reads `git log` and the KG on its own.

**Expected output:** A structured plan (markdown tables of updates, creates, connections, episode) that gets passed as the brief to `memory-curator`.

**Mode:** Primary (Tab or `opencode run --agent kb-updater`). Not spawned via `task`.

**Permissions:** `git log/show/diff=allow`, `memory_query/recall=allow`, `task=allow` (to delegate to `memory-curator`). No `edit`, no `memory_node/rel`.

**Pipeline:**
1. `kb-updater` reviews commits, produces plan
2. `kb-updater` spawns `memory-curator` via `task` with the plan as pre-approved brief
3. `memory-curator` executes the writes
4. `kb-updater` verifies with `memory_audit`

---

## 7. improvement-agent

**Purpose:** Reviews the output of a complete research cycle and auto-applies improvements to prompts, tools, skills, and papers. The only loop that edits the research harness.

**When to use:**
- After a research cycle completes (Search → Write → Review → Hypothesis phases)
- When research outputs are consistently low quality and prompts need tuning
- When new tools or skills are needed for the harness

**When NOT to use:**
- You need to record improvements in the KB (use `memory-curator` after this loop)
- You need general code review (use `code-reviewer`)
- You need to fix tests (use `test-fixer`)

**Brief format:** None — this is a primary agent. It receives phase outputs and decides what to improve.

**Scope of edits:**
- `agents/research_harness/` — prompts, tools, orchestrator, config, skills
- `papers/` — research papers, hypotheses, documentation
- `opencode.json` — only for research-runner/improvement-agent config

**Cannot edit:** `AGENTS.md`, `.gitignore`, `agents/memory/.project`, `data/`, or code outside `agents/research_harness/` and `papers/`.

**Expected output:**
```json
{
  "improvements_applied": [
    {"file": "agents/research_harness/prompts.py", "change": "Added DOI requirement", "reason": "3/5 papers missing DOIs"}
  ],
  "skills_updated": ["malaria_research"],
  "memory_nodes_created": ["improvement-2026-07-17-001"],
  "recommendations_for_supervisor": ["Consider adding a citation validation tool"]
}
```

**Mode:** Primary (Tab or `opencode run --agent improvement-agent`). Not spawned via `task`.

---

## Coordination Patterns

### Pattern 1: Test fails → fix

```
supervisor → test-fixer (brief: check_command, worktree_path)
           → test-fixer returns ok
           → supervisor integrates proposal
```

### Pattern 2: Code review → findings → fix

```
supervisor → code-reviewer (brief: diff_or_paths)
           → code-reviewer returns findings
           → supervisor routes each finding to test-fixer
           → test-fixer fixes, proposes
           → supervisor integrates
```

### Pattern 3: Discovery → KB write

```
supervisor finds something (pitfall, pattern, decision)
           → memory-curator (brief: items to record)
           → memory-curator loads project-memory skill, recalls, writes
           → memory-curator returns artifact
           → supervisor verifies with memory_audit
```

### Pattern 4: Daily maintenance pipeline

```
kb-updater (primary, self-directed)
  → reviews git log, recalls from KG
  → produces structured plan
  → spawns memory-curator with pre-approved brief
  → memory-curator executes writes
  → kb-updater verifies with memory_audit
```

### Pattern 5: Research cycle pipeline

```
research-runner (primary)
  → runs Search → Write → Review → Hypothesis phases
  → spawns improvement-agent with phase outputs
  → improvement-agent edits prompts/tools/skills
  → improvement-agent records changes in KG
```

### Pattern 6: Security gate

```
supervisor → security-auditor (brief: paths or diff)
           → security-auditor returns findings
           → supervisor decides: block merge or route fixes to test-fixer
```

---

## Gitagent Integration

Loops that **edit files** must operate inside a gitagent worktree:

1. **Spawn the loop** with `worktree_path` in the brief.
2. **The loop edits files** only inside that worktree.
3. **The loop finishes** with `gitagent propose --agent <id> --title "..." --confidence <0..1>`.
4. **The supervisor integrates** by reviewing and accepting/rejecting the proposal.

Loops that are **read-only** (`code-reviewer`, `security-auditor`, `doc-researcher`) do NOT need a worktree — they return artifacts directly.

Loops that write **only to the KG** (`memory-curator`) do NOT need a gitagent worktree — they use `memory_node`/`memory_rel` tools with `ask` permission.

---

## Parallel Spawning

Multiple `task` calls in one message run **in parallel**. Each loop gets its own context. Use this for independent work:

```json
// Same message — runs concurrently:
{"task": "code-reviewer", "prompt": "Review diff main..HEAD"},
{"task": "security-auditor", "prompt": "Audit mal-core/api/"},
{"task": "doc-researcher", "prompt": "Research calibration scoring approach"}
```

**Rule:** Parallelism is within the active issue. The kanban rule (exactly one issue In Progress at a time) still holds across issues.

---

## Decision Quick-Reference

| You need to… | Spawn | Not |
|---|---|---|
| Make tests pass | `test-fixer` | `code-reviewer` |
| Review code quality | `code-reviewer` | `test-fixer` |
| Answer a research question | `doc-researcher` | `memory-curator` |
| Audit for security issues | `security-auditor` | `code-reviewer` |
| Write to the knowledge graph | `memory-curator` | any other loop |
| Sync KB with recent commits | `kb-updater` | `memory-curator` directly |
| Improve research harness | `improvement-agent` | `test-fixer` |
