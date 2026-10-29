---
name: agent-ops
description: Agent operations patterns for MalariaSentinel. Covers parallel execution, git workflow, protected files, subagent coordination, and kanban discipline. Use when coordinating multi-agent work or understanding how agents operate in this project.
---

# Agent Operations

This skill documents how agents operate in MalariaSentinel — execution patterns, git conventions, protected files, and kanban workflow.

## 1. Parallel Execution

The supervisor **parallelises by default**. When two or more actions have no data dependency, run them in the **same message** so they execute concurrently. Serialise only when B depends on A's output.

### What's Parallel-Safe

| Action | Parallel-safe? | Notes |
|---|---|---|
| `read`, `glob`, `grep`, `bash` (read-only) | Yes | Batch N independent calls into one message. |
| `task` (subagent) | Yes | N subagent briefs in one message; each runs in its own context. |
| `gitagent spawn` | Yes, after `gitagent start` | Spawn N agents in one message, then wait for proposals. |
| `webfetch` / `websearch` (independent URLs/queries) | Yes | Batch. |

### What Must Be Serialised

| Action | Why | Alternative |
|---|---|---|
| Edits to the same file in one message | Race condition — one edit per file per message. | Batch edits across different files; serialise edits to the same file. |
| `gitagent start` / `init` / `propose` / `integrate` / `finalize` | Single-call, ordering matters. | Run each step sequentially. |
| Edits to a protected file | Not via delegation. Always `ask` the user. | Never batch with other edits. |

### Per-Issue Parallelism

The kanban "exactly one issue In Progress at a time" rule still holds. Parallelism is **within** the active issue (e.g. read 3 files, spawn 2 subagents), not **across** issues.

## 2. Git Workflow

### Push Conventions

| Command | Behaviour |
|---|---|
| `git push origin main` | Default: refuses if `origin/main` is not an ancestor of `HEAD`. Safe. |
| `git ps origin main` | Force-pushes `HEAD`, but aborts if the remote ref moved since the last fetch. |
| `git push --force origin main` | Unconditional clobber. **Do not use.** |

**Use `git ps`** (alias for `push --force-with-lease`) when local history was rewritten (`reset`, `rebase`, `amend`).

### Pre-Push Sanity Check

```bash
git fetch origin
git log --oneline origin/main..HEAD   # commits you have that the remote does not
git log --oneline HEAD..origin/main   # commits the remote has that you do not
git merge-base HEAD origin/main       # divergence point, if any
```

### Branch Prefixes

| Prefix | Use for |
|---|---|
| `common/` | Shared utilities, commonlib changes |
| `core/` | Core pipeline logic |
| `exec/` | CLI entrypoints, batch jobs |
| `sim/` | Simulation experiments |
| `data/` | Dataset changes |
| `docs/` | Documentation |
| `abm/` | Agent-based model work |

## 3. Protected Files

Files with `permission.edit: "ask"` in `opencode.json`. Every edit requires explicit user approval.

| Path | Why |
|---|---|
| `AGENTS.md` | Agent's own instructions — changing this changes agent behaviour. |
| `.gitignore` | Affects git tracking. |
| `opencode.json` | Project-wide permissions and agent config. |
| `data/` | Datasets. Prevents accidental edits. |

### Rules

- Every edit to a protected path is a real question. The user approves or denies.
- If denied, stop. Don't retry with a different phrasing.
- Don't batch the change with another edit.
- Don't delegate the edit to a subagent to bypass the prompt.
- Adding a new protected file = edit `opencode.json` and add `"<path>": "ask"` under `permission.edit`.

## 4. Kanban Workflow

### Board Structure

The project uses GitHub Project v2 (ANFAIA #11) with three columns:

| Column | Meaning |
|---|---|
| **Todo** | Issue is scoped but not yet in progress |
| **In Progress** | Exactly one issue at a time; the active task |
| **Done** | Completed, verified, closed |

### Labels on Every Issue

- Milestone label (`M1`...`M6`)
- Type label (`enhancement`, `investigation`)
- `blocked` label if an external dependency is unresolved

### How the Agent Manages the Board

1. **Entering a milestone**: read the open issues from GitHub. Move the highest-priority unblocked issue to **In Progress**.
2. **Working on an issue**: keep it in **In Progress** until all acceptance criteria pass. If a new blocker is discovered, add the `blocked` label, post a comment with the reason, and move to **Todo**.
3. **Completing an issue**: run the acceptance criteria (tests pass, lint clean). Close the issue with a comment referencing the commit SHA. Move it to **Done**.
4. **New work emerging mid-session**: create the issue in Todo with the right milestone/labels. Do not derail the current In Progress item — finish it first.
5. **End of milestone**: close the GitHub milestone, write a summary comment on the last issue.

### Discipline

- Exactly one issue In Progress at a time.
- Never batch closes.
- Always reference the commit SHA in the closing comment so the board is traceable.

## 5. Subagent Coordination

### Brief Format

When delegating to a subagent via `task`, include a brief that covers:
- **Objective**: what to accomplish.
- **Context**: key files, relevant constraints.
- **Acceptance criteria**: what "done" looks like.
- **Gitagent skill**: `Load the gitagent skill via skill({name: "gitagent"})` so subagents understand the propose workflow.

### Gitagent Workflow

The gitagent CLI isolates multi-agent work via worktrees:

1. **`gitagent start`** — initialise the feature branch and worktree.
2. **`gitagent spawn`** — spawn N agents in one message, each working in its own isolated worktree.
3. **`gitagent propose`** — each agent proposes its changes as a patch.
4. **`gitagent accept`** — the supervisor reviews and accepts/rejects proposals.
5. **`gitagent integrate`** — accepted patches are merged into the feature branch.
6. **`gitagent finalize`** — squash-merge into main, push, clean up.

### Parallel Subagent Spawning

Multiple `task` calls in one message run in parallel. Use this to fan out independent subtasks (e.g. spawn 2 subagents for 2 different files).

## 6. Context Discipline

### Context Architecture

| Layer | Owner | Lives in |
|---|---|---|
| Operational | OpenCode (primary agent) | The current session's context window. |
| Compaction | OpenCode (built-in) | Auto-summarised when the operational layer grows. |

### Rules

- Keep the operational layer compact — objective, plan, key decisions, references (paths, commit IDs, proposal IDs).
- Never paste multi-thousand-line tool outputs into the supervisor's prompt. Long outputs go to a summary.
- Subagents see a brief, not the full conversation. If they need more context, they ask the supervisor.

### Where Information Lives

| Information | Where it lives |
|---|---|
| Session objective, plan, key decisions | Operational layer (context window). |
| Project-specific durable facts | GitHub issues, milestones, PR descriptions. |
| Procedural how-to (build, test, push) | `AGENTS.md`. |

## 7. Related Skills

| Skill | Use when |
|---|---|
| `project-setup` | Initialising a new project with agent config. |
| `monorepo-dev` | Working across the monorepo — package structure, dependencies, promotion flow. |
| `gitagent` | Coordinating multi-agent work via isolated worktrees. |
| `subagents-loops` | Reference for the agent loops and how to use them. |
| `mal-execution-api` | CLI entrypoints, training scripts, and HPC automation. |
| `agent-onboarding` | Complete onboarding guide for new agents. |
