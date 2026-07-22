---
name: project-memory
description: Operate the project knowledge graph (Neo4j via the agents/memory module). Use when the user says "remember this", "log a pitfall", "note this pattern", "find what's been said about X", "audit the graph", or any task that should create/read a typed node, relation, or free-form episode in the project's memory subsystem. The eight schema labels are Component, Investigation, Architecture, Pattern, Pitfall, Tool, Operational, Preference. Use the custom tools memory_node / memory_rel / memory_query / memory_recall / memory_audit / memory_seed / memory_status for typed writes, reads, and stack checks; use memory_init first to verify the module is wired up in the current project; use memory_recall for semantic recall (NOT mcp__graphiti-memory__search_nodes — it's broken on our wrapper-written nodes due to a DateTime serialization bug). Use mcp__graphiti-memory__add_memory with source "text" only for free-form session summaries. Never use mcp__graphiti-memory__add_memory with source "json" or the add_triplet tool.
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
- **Relations** are typed by a short uppercase name. There are two
  classes:
  - **Hierarchy**: `PART_OF` (child → parent). Forms 6 parallel trees.
  - **Lateral** (8 verbs): `USES`, `IMPLEMENTS`, `VALIDATES`,
    `REFERENCES`, `RELEVANT_TO`, `SUPERSEDES`, `BLOCKS`, `MITIGATED_BY`.
- **Free-form episodes** (text blobs, session summaries) live as
  `Episodic` nodes via `mcp__add_memory` with `source: "text"`.

## The 6 trees (organization, orthogonal to schema)

Each tree has a root node. New nodes hang off the appropriate root via
`PART_OF` unless they have a more specific parent (e.g. an M1 sub-issue
hangs off `op-m1-abm-thin`, not the project root).

| Tree | Root | Houses |
|---|---|---|
| Centinela (project spine) | `obj-centinela-sdss` | the objective, milestones M1-M7+, high-level decisions, stakeholders |
| Pipeline (the code) | `comp-centinela` | the 5 monorepo packages, the 5 centinela components, sub-issues |
| Research (papers, datasets) | `research-knowledge-base` | papers, datasets, modeling methods |
| Agents & Memory (infra) | `agents-module` | loops, memory module, opencode config, agent patterns, agent tools |
| Wisdom (cross-cutting) | `project-wisdom` | patterns, pitfalls, preferences, tools that inform any tree |
| Architecture decisions | `architecture-decisions` | ADRs (each is an Architecture node) |

## The 8 schema labels

| Label | When to use it |
|---|---|
| `Component` | A package, file, service, dataset, or external dep. The structural backbone — one node per AGENTS.md package or significant file. |
| `Investigation` | A bounded research thread with a goal, status (`open` / `in_progress` / `closed`), and findings. Group related Pitfall/Architecture/Tool/Pattern findings under one via `[:PART_OF]`. |
| `Architecture` | An architectural decision, dependency rule, or structural fact. |
| `Pattern` | A reusable solution, idiom, or convention that works well here. |
| `Pitfall` | A known gotcha, mistake, or anti-pattern. |
| `Tool` | A specific tool, command, or library that proved useful. |
| `Operational` | A practical fix, command pattern, or runbook. |
| `Preference` | A team preference (naming, commit policy, never-do rules). |

## The 8 lateral verbs

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

If the relation you want doesn't fit one of these, **don't invent a
new verb** — use `RELEVANT_TO` and document the precise relationship in
the source node's summary.

## Decision table: which path to use

| If you need to... | Use |
|---|---|
| Check if the memory module is wired up in this project | `memory_init` (read-only; pass `verbose=true` to also probe the docker stack) |
| Record a typed fact (one of the 8 labels) | `memory_node({ type, uuid, name, summary, path?, parent? })` |
| Connect two nodes | `memory_rel({ type, src, dst, props? })` |
| Look up by uuid or known-shape cypher | `memory_query({ cypher, rw? })` |
| Fuzzy recall ("what do we know about X?") | **`memory_recall({ query, k? })`** — vector search over the wrapper's embeddings, with chain_to_root and lateral neighbourhood attached. Returns JSON. |
| Look up raw Episodic nodes | `mcp__graphiti-memory__get_episodes({ max_episodes })` |
| Record a free-form session summary | `mcp__graphiti-memory__add_memory({ name, episode_body })` with `source: "text"` (MUST be "text") |
| Verify the graph is consistent (3 invariants) | `memory_audit({})` |
| Check stack health (docker + neo4j-cli + graphiti) | `memory_status({})` |
| Re-apply the seed yaml | `memory_seed({ project? })` |

## The custom tools (typed args, no shell escape)

All eight are Zod-validated. Seven delegate to shell scripts in
`agents/memory/scripts/` which validate labels against the schema
before any Cypher runs (`memory_node`, `memory_rel`, `memory_query`,
`memory_recall`, `memory_audit`, `memory_seed`, `memory_status`).
The eighth (`memory_init`) is read-only and stays in TypeScript —
it only inspects files and (optionally) the status script.

- `memory_init({ verbose? })`
  Read-only install-state check. Returns a JSON report with what is
  in place (project slug, all six other tools, the skill, the runtime
  `.env`, the `opencode.json` permission rules) and the recommended
  next step. Pass `verbose=true` to also probe the docker stack. Use
  this first when you land in a project that has `agents/memory/`
  but you don't know if it's wired up. The result is a JSON string
  the agent can parse.
- `memory_node({ type, uuid, name, summary, path?, parent? })`
  Create or update one typed node. `type` is the label (must be one of
  the 8). `uuid` is your stable id (use a kebab-case slug like
  `pkg-mal-core` or `inv-graphiti-mcp-json-bug`). `path` is optional
  filesystem path. `parent` is optional uuid — if passed, creates
  `(child)-[:PART_OF]->(parent)` atomically and fails loudly if the
  parent doesn't exist.
- `memory_rel({ type, src, dst, props? })`
  Create or update one typed relation. `src` and `dst` are uuids that
  must exist. `props` is `{ key: value }` for relation properties.
- `memory_query({ cypher, rw? })`
  Run an arbitrary Cypher query. `rw=true` for writes (will fail in
  read-only contexts). Most reads don't need `rw`.
- `memory_recall({ query, k?, gid? })`
  Semantic recall. Embeds the query with `text-embedding-3-small` (1536d),
  runs `db.index.vector.queryNodes('entity_name_embedding', k, $q)`,
  and for each hit attaches the `chain_to_root` (path through PART_OF)
  and the `connected` neighbourhood (depth-1, all lateral verbs, both
  directions). Returns JSON.
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

- `mcp__graphiti-memory__search_nodes({ query })` — **DEPRECATED for
  this project.** The Graphiti MCP 1.26.0 server has a known
  DateTime serialization bug that fails on our wrapper-written
  nodes. Use `memory_recall` instead.
- `mcp__graphiti-memory__search_memory_facts({ query })` — same
  status. Use `memory_query` with cypher instead.
- `mcp__graphiti-memory__add_memory({ name, episode_body, source })`
  — **Only with `source: "text"`.** Use for session summaries,
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
- **Never** write a node outside the 8 schema labels. If a
  fact doesn't fit, reject it and propose a label change
  (which is an ADR, not a one-off).
- **Never** use a rel type outside the 8 lateral verbs + `PART_OF`.
  Use `RELEVANT_TO` and document the relationship in the summary.

## The writing contract: which tree, which label

When you write a new node, decide both the schema label and the
tree. The combination determines the parent:

| Fact | Label | Parent tree (root or specific node) |
|---|---|---|
| A new milestone M* | `Operational` | `obj-centinela-sdss` |
| A milestone sub-issue (M1.1, M1.2a, ...) | `Component` or `Investigation` | the milestone, e.g. `op-m1-abm-thin` |
| A component (package, service, dataset) | `Component` | `comp-centinela` (Pipeline) or `research-knowledge-base` (Research) |
| A paper | `Component` | `research-knowledge-base` |
| A pattern (cross-cutting) | `Pattern` | `project-wisdom` |
| An agent-internal pattern | `Pattern` | `agents-module` |
| A pitfall | `Pitfall` | `project-wisdom` |
| A team preference | `Preference` | `project-wisdom` (cross-cutting) or `agents-module` (infra) |
| A tool | `Tool` | `project-wisdom` (cross-cutting) or `agents-module` (infra) or `comp-centinela-*` (in-pipeline) |
| A decision (ADR) | `Architecture` | `architecture-decisions` |
| A research thread | `Investigation` | the most relevant milestone, e.g. `op-m3-m4-unet` |

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
   Architecture, Preference, Component) you discovered. The
   memory-curator loop is the only one that writes; delegate to it.
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
  `memory_recall`.

If a relevant node exists, update it (`memory_node` is a MERGE —
same uuid updates the existing one). Never duplicate.

## Schema invariants (what `memory_audit` checks)

1. **No Entity-only node.** Every node has at least one schema label
   besides `:Entity`. Catches "write bypassed the wrapper" scenarios.
2. **No orphan relation.** Every rel endpoint exists. Catches dangling
   references after a partial wipe.
3. **No label outside the schema.** Every label is in
   `agents/memory/runtime/config/config.yaml` (lines 81-97). Catches
   typos in ad-hoc Cypher.

All three should be 0. Any non-zero is a `Pitfall` worth recording
("the wrapper rejected X but a raw cypher write slipped through").

## Where the pieces live

- `agents/memory/scripts/memory.sh` — the dispatcher. All custom
  tools delegate here. `bash agents/memory/scripts/memory.sh <sub>`
  works directly.
- `agents/memory/scripts/recall.sh` — the recall script (called by
  `memory_recall`). Embeds the query, runs vector search, attaches
  chain_to_root and connected.
- `agents/memory/scripts/reembed.sh` — re-embed all nodes (after a
  partial wipe or OpenAI outage).
- `agents/memory/scripts/audit.sh` — runs the 3 invariants.
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

- **Not an automatic RAG pipeline.** The agent decides when to query.
  The cost of `memory_query` / `memory_recall` is paid only when you
  call it.
- **Not an automatic entity extractor.** Every typed write takes
  explicit args from the agent. There is no LLM in the write path
  that re-classifies your input. The 2026-07-04 wipe (261 mis-labelled
  nodes) was caused by the Graphiti MCP extractor re-classifying text
  from `add_memory source: "json"`. Never use that path. Use
  `memory_node` + `memory_rel` for anything with a structural class.
- **Not multi-user.** `group_id` is per-checkout (one `.project` per
  repo). Multi-user collaboration would need an additional `user_id`
  discriminator on every node — not currently supported.
- **Not a code index.** Use Component nodes for packages / significant
  files, not for every line. The graph is for project facts, not for
  grep.
