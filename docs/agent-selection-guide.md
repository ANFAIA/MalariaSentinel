# Agent Selection Guide

This document defines when to use each agent type and rules for preventing timeouts and poor session hygiene.

## Agent Selection Table

| Task Type | Agent | Why |
|---|---|---|
| Code implementation (editing files) | `general` | Can edit files, run tests, multi-step |
| Codebase exploration (finding files, understanding structure) | `explore` | Fast, read-only, parallel-safe |
| Code review (diff analysis, conventions) | `code-reviewer` | Read-only, structured findings |
| Test iteration (fix until passing) | `test-fixer` | Specialized loop, knows when to stop |
| Knowledge graph writes (nodes, relations) | `memory-curator` | Single writer, validates schema |
| Documentation research | `doc-researcher` | KB-first, web fallback |
| Security audit | `security-auditor` | OWASP-focused, read-only |
| Orchestration ONLY | `supervisor` | Delegates, never implements |

**Rationale**: The supervisor should never touch files directly. It decomposes work, delegates to the right agent, integrates results via `gitagent`, and keeps the kanban in sync. Every time the supervisor edits a file, it burns operational-layer context that could be spent on orchestration.

## Timeout Prevention Rules

Timeouts happen when a single subagent runs too long or when a task is too large for one context window. Apply these rules:

1. **Break tasks with >5 file edits into 2-3 subtasks.** Each subtask targets a logical slice (e.g., "add import + helper function" vs. "wire into main pipeline"). Smaller scopes reduce the chance of context overflow.

2. **Each subtask should complete in <3 minutes.** If you estimate a task will take longer, decompose further. The test-fixer loop is the exception — it iterates until the check passes, but should be given a focused scope (one failing test, not an entire test suite).

3. **If a subagent has been running >5 minutes, check if it needs splitting.** Long-running subagents either have too broad a scope or are stuck. Intervene: read their partial output, split the remaining work, and spawn a new subagent for the rest.

4. **Prefer depth over breadth in subagent briefs.** A brief that says "fix the Ghana simulation" is too broad. A brief that says "add a `validate_config()` function to `scripts/02_suitability.py` that checks DEM path exists before proceeding" is actionable and bounded.

## Session Naming Convention

Session names are derived from the first user message. A poor first message creates an uninformative session name (e.g., "New session - 2026-07-17T10:30:00") that is useless for recall.

**Rules:**

- First message should be descriptive: "Fix bug in X", "Add feature Y", "Investigate Z".
- Avoid empty/generic messages that create timestamp-based names.
- Avoid multi-sentence first messages — keep it to a short imperative phrase.

**Examples:**
- Good: "Add DEM validation to suitability script"
- Good: "Fix timeout in Ghana simulation pipeline"
- Bad: "Can you help me?"
- Bad: "Hi, I need to do something"

## Parallel Execution Rules

Parallelism is the default. Serial execution is the exception. Apply these rules:

1. **When spawning multiple subagents, issue all `task` calls in ONE message.** Each subagent runs in its own context. They do not share state. There is no reason to wait for one to finish before starting another, unless the second depends on the first's output.

2. **Independent reads/greps/globs should be batched in ONE message.** If you need to find files in `mal-core/` and `mal-ghana-sim/`, run both globs in the same message. Context cost is the same; wall-clock time is halved.

3. **Serial execution only when B depends on A's output.** If subagent B needs the UUID from a node created by subagent A, A must complete first. Otherwise, parallelise.

4. **Do not over-serialise.** The most common mistake is: read file → then grep → then spawn subagent → then read another file. These are independent; batch them.

## Decision Flowchart

```
User request arrives
  ├─ Is it orchestration only (kanban update, session log, delegation)?
  │   └─ supervisor handles it directly.
  ├─ Does it involve editing code files?
  │   └─ Delegate to `general` subagent.
  ├─ Does it involve finding/understanding code?
  │   └─ Delegate to `explore` subagent.
  ├─ Does it involve reviewing code?
  │   └─ Delegate to `code-reviewer`.
  ├─ Does it involve iterating on tests?
  │   └─ Delegate to `test-fixer`.
  ├─ Does it involve writing to the knowledge graph?
  │   └─ Delegate to `memory-curator`.
  └─ Anything else: decompose first, then assign.
```
