---
name: agent-ops
description: Agent operations patterns for MalariaSentinel. Covers session lifecycle, parallel execution, git workflow, memory graph conventions, protected files, and kanban discipline. Use when starting a session, coordinating multi-agent work, or understanding how agents operate in this project.
---

# Agent Operations

This skill documents how agents operate in MalariaSentinel — session protocols, execution patterns, git conventions, memory graph usage, protected files, and kanban workflow.

## 1. Session Lifecycle

### Session Start (run at the top of every non-trivial session)

1. **Run the session-start make target:**
   ```bash
   make -f agents/memory/scripts/Makefile session-start
   ```
   This runs the schema audit, then lists open investigations, active pitfalls, recent architecture decisions, components, preferences, and operational patterns.

2. **If audit fails**, stop and fix the source issue before proceeding. Do not patch the audit output.

3. **Review open investigations** — pick the one this session will advance, or note that you're opening a new investigation.

### Session End (non-trivial sessions only)

1. **Update** any `Investigation` nodes advanced during the session (`memory_node` to update status/summary).
2. **Add** newly-discovered typed nodes (Pattern, Pitfall, Tool, Operational, Architecture, Preference, Component).
3. **Write** a free-form session episode via `mcp__graphiti-memory__add_memory` with `source: "text"`, named `session-YYYY-MM-DD: <one-line summary>`, body a short paragraph (10-20 lines) of what was done, decisions taken, blockers, next step.
4. **Edit** `AGENTS.md` if a new convention emerged (requires user approval — protected file).
5. **Re-run** the audit to confirm 0/0/0:
   ```bash
   make -f agents/memory/scripts/Makefile audit
   ```

### When to Skip the Session Contract

Skip the full start/end protocol for trivial sessions: single tool call, no state change, no investigation advanced.

## 2. Parallel Execution

The supervisor **parallelises by default**. When two or more actions have no data dependency, run them in the **same message** so they execute concurrently. Serialise only when B depends on A's output.

### What's Parallel-Safe

| Action | Parallel-safe? | Notes |
|---|---|---|
| `read`, `glob`, `grep`, `bash` (read-only) | Yes | Batch N independent calls into one message. |
| `task` (subagent) | Yes | N subagent briefs in one message; each runs in its own context. |
| `gitagent spawn` | Yes, after `gitagent start` | Spawn N agents in one message, then wait for proposals. |
| `memory_query` / `memory_recall` / `mcp__search_nodes` | Yes | Run N queries in one message; merge results. |
| `webfetch` / `websearch` (independent URLs/queries) | Yes | Batch. |

### What Must Be Serialised

| Action | Why | Alternative |
|---|---|---|
| `memory_node` then `memory_rel` (when rel needs the node's uuid) | Two messages: write → read uuid → write rel. | Write the node first, then read the uuid, then write the rel. |
| Edits to the same file in one message | Race condition — one edit per file per message. | Batch edits across different files; serialise edits to the same file. |
| `gitagent start` / `init` / `propose` / `integrate` / `finalize` | Single-call, ordering matters. | Run each step sequentially. |
| Edits to a protected file | Not via delegation. Always `ask` the user. | Never batch with other edits. |

### Per-Issue Parallelism

The kanban "exactly one issue In Progress at a time" rule still holds. Parallelism is **within** the active issue (e.g. read 3 files, spawn 2 subagents, query 2 KB nodes), not **across** issues.

## 3. Git Workflow

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

## 4. Memory Graph Patterns

### Recall Before Writing

Before creating a node, search first:
- For known-shape lookups (by uuid, by label, by cypher): `memory_query`.
- For fuzzy lookups ("have we already documented X?"): `memory_recall`.

If a relevant node exists, update it (`memory_node` is a MERGE — same uuid updates the existing one). Never duplicate.

### The 8 Schema Labels

| Label | When to use it |
|---|---|
| `Component` | A package, file, service, dataset, or external dep. The structural backbone. |
| `Investigation` | A bounded research thread with a goal, status (`open` / `in_progress` / `closed`), and findings. |
| `Architecture` | An architectural decision, dependency rule, or structural fact. |
| `Pattern` | A reusable solution, idiom, or convention that works well here. |
| `Pitfall` | A known gotcha, mistake, or anti-pattern. |
| `Tool` | A specific tool, command, or library that proved useful. |
| `Operational` | A practical fix, command pattern, or runbook. |
| `Preference` | A team preference (naming, commit policy, never-do rules). |

### The 8 Lateral Verbs

| Verb | Meaning | Example |
|---|---|---|
| `USES` | "I depend on you to exist" | M3 U-Net —[:USES]-> Mesa-Geo Tool |
| `IMPLEMENTS` | "I am the realisation of you" | mal-ghana-sim —[:IMPLEMENTS]-> M1 |
| `VALIDATES` | "I am the proof that you work" | 24 larval sites —[:VALIDATES]-> Suitability layer |
| `REFERENCES` | "I cite you as a source" | M2 —[:REFERENCES]-> Odhiambo 2024 |
| `RELEVANT_TO` | "I affect you / you affect me" (generic) | pitfall-hardcoded-aoi —[:RELEVANT_TO]-> M5 |
| `SUPERSEDES` | "I replace you" | new ADR —[:SUPERSEDES]-> old ADR |
| `BLOCKS` | "I prevent you from advancing" | inv-incidence-data-source —[:BLOCKS]-> M3-M4 |
| `MITIGATED_BY` | "I prevent you" | pitfall-X —[:MITIGATED_BY]-> pattern-Y |

If the relation doesn't fit one of these, use `RELEVANT_TO` and document the precise relationship in the source node's summary.

### The 6 Trees (PART_OF Hierarchy)

| Tree | Root | Houses |
|---|---|---|
| Centinela (project spine) | `obj-centinela-sdss` | objectives, milestones M1-M7+, high-level decisions, stakeholders |
| Pipeline (the code) | `comp-centinela` | the 5 monorepo packages, the 5 centinela components, sub-issues |
| Research (papers, datasets) | `research-knowledge-base` | papers, datasets, modeling methods |
| Agents & Memory (infra) | `agents-module` | loops, memory module, opencode config, agent patterns, agent tools |
| Wisdom (cross-cutting) | `project-wisdom` | patterns, pitfalls, preferences, tools that inform any tree |
| Architecture decisions | `architecture-decisions` | ADRs (each is an Architecture node) |

### Hard Rules

- **Never** use `mcp__graphiti-memory__add_memory` with `source: "json"` — the LLM extractor in MCP 1.26.0 re-classifies text, producing mislabelled nodes (verified 2026-07-04: 261-node / 411-rel wipe).
- **Never** use `mcp__graphiti-memory__add_triplet` — not available in MCP 1.26.0. Use `memory_node` + `memory_rel`.
- **Never** run `make -f agents/memory/scripts/Makefile wipe` without explicit user approval.
- **Never** edit `agents/memory/.project` or `agents/memory/runtime/.env` without user approval.
- **Never** write a node outside the 8 schema labels.
- **Never** use a rel type outside the 8 lateral verbs + `PART_OF`.

## 5. Protected Files

Files with `permission.edit: "ask"` in `opencode.json`. Every edit requires explicit user approval.

| Path | Why |
|---|---|
| `AGENTS.md` | Agent's own instructions — changing this changes agent behaviour. |
| `.gitignore` | Affects git tracking. |
| `opencode.json` | Project-wide permissions and agent config. |
| `agents/memory/.project` | The Neo4j `group_id` (project identity). |
| `data/` | Datasets. Prevents accidental edits. |

### Rules

- Every edit to a protected path is a real question. The user approves or denies.
- If denied, stop. Don't retry with a different phrasing.
- Don't batch the change with another edit.
- Don't delegate the edit to a subagent to bypass the prompt.
- Adding a new protected file = edit `opencode.json` and add `"<path>": "ask"` under `permission.edit`.

### Bash Denies (Defence Against Typos)

`make -f agents/memory/scripts/Makefile {wipe,set-project}` are denied for every agent (global block + per-agent block in `opencode.json`). Use `make` itself for normal work; the deny patterns only block the destructive subcommands.

## 6. Kanban Workflow

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
5. **End of milestone**: close the GitHub milestone, write a KB entry summarising the outcome.

### Discipline

- Exactly one issue In Progress at a time.
- Never batch closes.
- Always reference the commit SHA in the closing comment so the board is traceable.

## 7. Subagent Coordination

### Brief Format

When delegating to a subagent via `task`, include a brief that covers:
- **Objective**: what to accomplish.
- **Context**: key files, relevant KB nodes, constraints.
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

## 8. Context Discipline

### Context Architecture (3 Layers + 2)

| Layer | Owner | Lives in |
|---|---|---|
| Operational | OpenCode (primary agent) | The current session's context window. |
| Compaction | OpenCode (built-in) | Auto-summarised when the operational layer grows. |
| Episodic | `agents/memory/` | Free-form session summaries, observations. |
| Semantic | `agents/memory/` | Typed nodes: components, investigations, patterns, etc. |

### Rules

- Keep the operational layer compact — objective, plan, key decisions, references (paths, UUIDs, commit IDs, proposal IDs).
- Never paste multi-thousand-line tool outputs into the supervisor's prompt. Long outputs go to the knowledge graph or a summary.
- Subagents see a brief, not the full conversation. If they need more context, they query the knowledge graph or ask the supervisor.

### When to Use Knowledge Graph vs Operational Layer

| Information | Where it lives |
|---|---|
| Session objective, plan, key decisions | Operational layer (context window). |
| Project-specific facts (components, investigations, patterns) | Knowledge graph — query just-in-time. |
| Free-form session notes, observations | Knowledge graph as text episodes. |
| Procedural how-to (build, test, push) | `AGENTS.md`. |

## 9. Related Skills

| Skill | Use when |
|---|---|
| `project-memory` | Operating the knowledge graph — typed node/relation writes, recall, audit. |
| `project-setup` | Initialising a new project with the memory module, Neo4j, and agent config. |
| `monorepo-dev` | Working across the monorepo — package structure, dependencies, promotion flow. |
| `gitagent` | Coordinating multi-agent work via isolated worktrees. |
| `memory-setup` | Installing, configuring, and troubleshooting the knowledge graph. |
| `subagents-loops` | Reference for all 7 agent loops and how to use them. |
| `mal-execution-api` | CLI entrypoints, training scripts, and HPC automation. |
| `agent-onboarding` | Complete onboarding guide for new agents. |
