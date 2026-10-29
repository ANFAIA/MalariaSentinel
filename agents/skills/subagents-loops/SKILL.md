---
name: subagents-loops
description: Reference guide for all 5 subagent loops in MalariaSentinel. Covers when to use each loop, what brief to send, expected outputs, and coordination patterns. Use when delegating work to a subagent, choosing the right loop for a task, or understanding the agent architecture.
---

# Subagent Loops Reference

The supervisor delegates work to 5 specialised loops. Each loop is a self-contained subagent (or primary agent) with bounded permissions and a structured output contract. This skill tells you **which loop to spawn**, **what to put in the brief**, and **what comes back**.

## Overview

| Loop | Mode | Read/Write | Use when | Brief needs |
|---|---|---|---|---|
| `test-fixer` | subagent | write (edit+bash) | Tests/lint/checks fail | `check_command`, `worktree_path` |
| `code-reviewer` | subagent | read-only | Reviewing a diff, validating conventions | `diff_or_paths`, `focus_areas` |
| `doc-researcher` | subagent | read-only + web | Answering a research question | `question` |
| `security-auditor` | subagent | read-only | Security review, OWASP audit | `paths` or `diff` or `config` |
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
  "focus_areas": ["security", "performance", "conventions"]
}
```

- `diff_or_paths` — **required**. Either a diff string or a list of file paths.
- `focus_areas` — optional. Areas to focus on (e.g. `security`, `performance`, `conventions`).

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

**Purpose:** Answers research questions by searching the repo and the web, then returning a sourced brief. Returns a summary, not raw content.

**When to use:**
- "What does the Kelly et al. 2012 paper say about X?"
- "How do we handle terrain data in the pipeline?"
- "What's the current approach to calibration scoring?"

**When NOT to use:**
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
    {"source": "repo", "ref": "mal-core/src/mal_core/suitability.py", "excerpt": "..."},
    {"source": "web", "ref": "https://...", "excerpt": "..."}
  ]
}
```

**Permissions:** `edit=deny`, `webfetch/websearch=allow`. Read-only — returns a sourced brief for the supervisor to integrate.

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

## 5. improvement-agent

**Purpose:** Reviews the output of a complete research cycle and auto-applies improvements to prompts, tools, skills, and papers. The only loop that edits the research harness.

**When to use:**
- After a research cycle completes (Search → Write → Review → Hypothesis phases)
- When research outputs are consistently low quality and prompts need tuning
- When new tools or skills are needed for the harness

**When NOT to use:**
- You need general code review (use `code-reviewer`)
- You need to fix tests (use `test-fixer`)

**Brief format:** None — this is a primary agent. It receives phase outputs and decides what to improve.

**Scope of edits:**
- `agents/research_harness/` — prompts, tools, orchestrator, config, skills
- `papers/` — research papers, hypotheses, documentation
- `opencode.json` — only for research-runner/improvement-agent config

**Cannot edit:** `AGENTS.md`, `.gitignore`, `opencode.json` (beyond its own config), `data/`, or code outside `agents/research_harness/` and `papers/`.

**Expected output:**
```json
{
  "improvements_applied": [
    {"file": "agents/research_harness/prompts.py", "change": "Added DOI requirement", "reason": "3/5 papers missing DOIs"}
  ],
  "skills_updated": ["malaria_research"],
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

### Pattern 3: Research cycle pipeline

```
research-runner (primary)
  → runs Search → Write → Review → Hypothesis phases
  → spawns improvement-agent with phase outputs
  → improvement-agent edits prompts/tools/skills
```

### Pattern 4: Security gate

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
| Answer a research question | `doc-researcher` | do it yourself in-context |
| Audit for security issues | `security-auditor` | `code-reviewer` |
| Improve research harness | `improvement-agent` | `test-fixer` |
