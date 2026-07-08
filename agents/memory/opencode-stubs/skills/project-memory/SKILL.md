---
name: project-memory
description: Operate the project knowledge graph (Neo4j via the agents/memory module). Use when the user says "remember this", "log a pitfall", "note this pattern", "find what's been said about X", "audit the graph", or any task that should create/read a typed node, relation, or free-form episode in the project's memory subsystem. The eight schema labels are Component, Investigation, Architecture, Pattern, Pitfall, Tool, Operational, Preference. Use the custom tools memory_node / memory_rel / memory_query / memory_audit / memory_seed / memory_status for typed writes, reads, and stack checks; use memory_init first to verify the module is wired up in the current project; use mcp__graphiti-memory__search_nodes for fuzzy semantic recall; use mcp__graphiti-memory__add_memory with source "text" only for free-form session summaries. Never use mcp__graphiti-memory__add_memory with source "json" or the add_triplet tool.
---

# Project Memory

The project has a knowledge graph in Neo4j (via Graphiti MCP 1.26.0) and
a thin shell wrapper that validates every write against a fixed schema
of 8 labels. This skill tells you when to use which path.

## The shape of the graph

- **Nodes** have one schema label (the eight below) plus always `:Entity`
  and `:Component:Entity` etc. as compound labels. `uuid` and `group_id`
  are the merge keys — re-writing the same uuid updates the visible
  properties, does not duplicate.
- **Relations** are typed by a short uppercase name (e.g. `TESTS`,
  `INCLUDES`, `PART_OF`). The endpoint uuids must exist or the write
  fails.
- **Free-form episodes** (text blobs, session summaries) live as
  `Episodic` nodes via `mcp__add_memory` with `source: "text"`.

## The 8 schema labels

| Label | When to use it |
|---|---|
| `Component` | A package, file, service, dataset, or external dep. The structural backbone — one node per AGENTS.md package or significant file. |
| `Investigation` | A bounded research thread with a goal, status (`open` / `in_progress` / `closed`), and findings. Group related Pitfall/Pattern/etc. under one via `[:PART_OF]`. |
| `Architecture` | An architectural decision, dependency rule, or structural fact. |
| `Pattern` | A reusable solution, idiom, or convention that works well here. |
| `Pitfall` | A known gotcha, mistake, or anti-pattern. |
| `Tool` | A specific tool, command, or library that proved useful. |
| `Operational` | A practical fix or command pattern that saves time. |
| `Preference` | A team preference (naming, commit policy, never-do rules). |

## Decision table: which path to use

| If you need to... | Use |
|---|---|
| Check if the memory module is wired up in this project | `memory_init` (read-only; pass `verbose=true` to also probe the docker stack) |
| Record a typed fact (one of the 8 labels) | `memory_node({ type, uuid, name, summary, path? })` |
| Connect two nodes | `memory_rel({ type, src, dst, props? })` |
| Look up by uuid or known-shape cypher | `memory_query({ cypher, rw? })` |
| Fuzzy recall ("what do we know about X?") | `mcp__graphiti-memory__search_nodes({ query })` |
| Record a session summary or free-form observation | `mcp__graphiti-memory__add_memory({ name, episode_body })` with `source: "text"` (MUST be "text") |
| Verify the graph is consistent (3 invariants) | `memory_audit({})` |
| Check stack health (docker + neo4j-cli + graphiti) | `memory_status({})` |
| Re-apply the seed yaml | `memory_seed({ project? })` |

## The custom tools (typed args, no shell escape)

All seven are Zod-validated. Six delegate to shell scripts in
`agents/memory/scripts/` which validate labels against the schema
before any Cypher runs. The seventh (`memory_init`) is read-only and
stays in TypeScript — it only inspects files and (optionally) the
status script.

- `memory_init({ verbose? })`
  Read-only install-state check. Returns a JSON report with what is
  in place (project slug, all six other tools, the skill, the runtime
  `.env`, the `opencode.json` permission rules) and the recommended
  next step. Pass `verbose=true` to also probe the docker stack. Use
  this first when you land in a project that has `agents/memory/`
  but you don't know if it's wired up. The result is a JSON string
  the agent can parse.
- `memory_node({ type, uuid, name, summary, path? })`
  Create or update one typed node. `type` is the label (must be one of
  the 8). `uuid` is your stable id (use a kebab-case slug like
  `pkg-mal-core` or `inv-graphiti-mcp-json-bug`).
- `memory_rel({ type, src, dst, props? })`
  Create or update one typed relation. `src` and `dst` are uuids that
  must exist. `props` is `{ key: value }` for relation properties.
- `memory_query({ cypher, rw? })`
  Run an arbitrary Cypher query. `rw=true` for writes (will fail in
  read-only contexts). Most reads don't need `rw`.
- `memory_audit({})`
  Run the three schema invariants. Returns counts of unlabeled nodes,
  orphan relations, and out-of-schema labels. Should be 0/0/0.
- `memory_seed({ project? })`
  Re-apply the project's seed yaml (and bootstrap entries). Use after
  editing `agents/memory/seed/<project>.yaml`. Idempotent.
- `memory_status({})`
  Check docker + neo4j-cli + Graphiti MCP. Returns human-readable
  health for all three.

## The MCP tools (use narrowly)

- `mcp__graphiti-memory__search_nodes({ query })`
  Semantic recall by natural-language query. Returns matching nodes
  with name/summary/embedding. Use this first when the user asks
  "what do we know about X?" — `memory_query` requires you to know
  the cypher; `search_nodes` does the recall for you.
- `mcp__graphiti-memory__search_facts({ query })`
  Relation-focused search. Use when you need "what does A depend
  on?" or similar.
- `mcp__graphiti-memory__add_memory({ name, episode_body, source })`
  **Only with `source: "text"`.** Use for session summaries,
  observations, free-form notes. The episode_body is stored verbatim
  as a text node and indexed for semantic search.

## Hard rules (don't break these)

- **Never** use `mcp__graphiti-memory__add_memory` with
  `source: "json"` or any `type` field. The LLM extractor in
  MCP 1.26.0 ignores the `type` and re-classifies from text,
  producing mislabelled nodes (verified 2026-07-04 after a
  261-node / 411-rel wipe). The `memory_node` tool replaces
  every legitimate use of this path.
- **Never** use `mcp__graphiti-memory__add_triplet`. The tool
  does not exist in MCP 1.26.0. Use `memory_node` + `memory_rel`.
- **Never** run `make -f agents/memory/scripts/Makefile wipe`
  without explicit user approval. The catch-all bash deny rule
  blocks it; ask the supervisor first.
- **Never** edit `agents/memory/.project` or `agents/memory/runtime/.env`
  without user approval — both are `permission.edit: "ask"`.

## Session lifecycle

### Session start (run at the top of every non-trivial session)

1. `make -f agents/memory/scripts/Makefile session-start` — runs
   audit, then lists open investigations, active pitfalls, recent
   architecture decisions, components, preferences, operational
   patterns. If audit fails, stop and fix first.
2. Glance at the open investigations. Pick the one this session
   will advance (or note that you're opening a new one).

### Session end (run before closing the chat)

1. **Update** any Investigation node you advanced
   (`memory_node` to update status/summary).
2. **Add** any new typed nodes (Pitfall, Pattern, Tool, Operational,
   Architecture, Preference, Component) you discovered.
3. **Write** a free-form session episode via
   `mcp__graphiti-memory__add_memory` with `source: "text"`,
   named `session-YYYY-MM-DD: <one-line summary>`, body a short
   paragraph (10-20 lines) of what was done, decisions taken,
   blockers, next step.
4. **Re-run** `memory_audit` to confirm 0/0/0.

## Recall before writing

Before creating a node, search first:

- For known-shape lookups (by uuid, by label, by cypher):
  `memory_query`.
- For fuzzy lookups ("have we already documented X?"):
  `mcp__graphiti-memory__search_nodes`.

If a relevant node exists, update it (`memory_node` is a MERGE —
same uuid updates the existing one). Never duplicate.

## Schema invariants (what `memory_audit` checks)

1. **No Entity-only node.** Every node has at least one schema label
   besides `:Entity`. Catches "write bypassed the wrapper" scenarios.
2. **No orphan relation.** Every rel endpoint exists. Catches dangling
   references after a partial wipe.
3. **No label outside the schema.** Every label is in
   `agents/memory/runtime/config/config.yaml` (lines 81-99). Catches
   typos in ad-hoc Cypher.

All three should be 0. Any non-zero is a `Pitfall` worth recording
("the wrapper rejected X but a raw cypher write slipped through").

## Where the pieces live

- `agents/memory/scripts/memory.sh` — the dispatcher. All custom
  tools delegate here. `bash agents/memory/scripts/memory.sh <sub>`
  works directly.
- `agents/memory/scripts/Makefile` — the make targets (status,
  audit, seed, wipe, set-project, session-start, session-end).
- `agents/memory/runtime/config/config.yaml` — the schema source
  (8 entity types declared here).
- `agents/memory/runtime/.env` — Neo4j + OpenAI credentials. Read
  by `neo4j-cli` from this file when invoked from `runtime/`.
- `agents/memory/.project` — the Neo4j `group_id`. Per-project,
  per-machine, gitignored.
- `agents/memory/seed/<project>.yaml` — the seed yaml for the
  current project. Re-applied via `memory_seed` or `make seed`.
- `agents/memory/bootstrap/*.yaml` — pre-configured knowledge that
  every session re-asserts (architecture decisions, conventions,
  the agents layer, the protection model).

## What this module does NOT do

- **No automatic RAG.** The agent decides when to query. The cost of
  `memory_query` / `search_nodes` is paid only when you call it.
- **No automatic entity extraction.** Every typed write takes explicit
  args from the agent. There is no LLM in the write path that re-classifies
  your input. The 2026-07-04 wipe (261 mis-labelled nodes) was caused
  by the Graphiti MCP extractor re-classifying text from `add_memory
  source: "json"`. Never use that path. Use `memory_node` + `memory_rel`
  for anything with a structural class.
- **No multi-user.** `group_id` is per-checkout (one `.project` per
  repo). Multi-user collaboration would need an additional `user_id`
  discriminator on every node — not currently supported.
- **No code index.** Use Component nodes for packages / significant
  files, not for every line. The graph is for project facts, not for
  grep.
