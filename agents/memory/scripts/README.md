<!-- Module: agents/memory — see AGENTS.md (Protected files) and opencode.json permission.edit. -->

# `agents/memory/scripts/` — Project Memory Infrastructure

The single entry point for the project's knowledge graph. Every write goes
through this package. Every read can either go through it or use the MCP
tools directly. The package enforces one rule that fixes the bug that
required the 2026-07-04 wipe of 261 mis-labelled nodes:

> **Labels are validated against the schema before any Cypher runs.** The
> Graphiti MCP `add_memory` path with `source: "json"` ignores the `type`
> field and re-classifies from text. Do not use it for typed nodes.

> **This package is memory only.** Project-level governance (which files
> are protected, who can modify what) is enforced by OpenCode's
> `permission.edit` block in `opencode.json`. The historical HITL
> subsystem (`tools/hitl/`) was removed in 2026-07 in favour of
> OpenCode-native `ask` prompts. See `AGENTS.md` → "Protected files".

## What this is

A thin shell wrapper around `neo4j-cli` (v1.10+) that:

- Is **project-agnostic**: the project name (Neo4j `group_id`) is read
  from `tools/memory/.project` (a single line, one source of truth). The
  initializing agent picks the slug; every script reads it. See
  "Project resolution" below.
- Validates every label against `memory/config/config.yaml` (lines 81-99)
  before issuing Cypher.
- Uses parameterised Cypher (`--param NAME=VALUE`) for every user-supplied
  string. No string interpolation of labels or values. No injection.
- Is idempotent: every `MERGE` keys on `uuid + group_id`, so re-running
  the same seed converges to the same state.
- Logs every write to `runs/memory.log` (`ts, subcommand, group_id, label,
  uuid, name, ...`).
- Is multi-agent safe: Neo4j's transactional `MERGE` resolves concurrent
  writes without duplicating nodes.
- Runs the three schema invariants on demand via `memory.sh audit` and
  after every `seed.sh` call.

## Project resolution (`.project`)

The project name (Neo4j `group_id`) lives in `tools/memory/.project` —
one line, no extension. This file is gitignored (per-machine runtime
state). The initializing agent writes it:

```bash
make -f tools/memory/Makefile set-project PROJECT=myslug
# writes 'myslug' to tools/memory/.project
```

Every other target reads it. Override on a single command with
`make ... PROJECT=other`. A template lives at `.project.example`.

Resolution order inside every script (first non-empty wins):

1. explicit `--group-id <gid>` on the CLI
2. `$GROUP_ID` env var
3. `tools/memory/.project`
4. fail with a clear message

## Quick start (cold start)

```bash
# 1. Pick the project slug (one-time per checkout)
make -f tools/memory/Makefile set-project PROJECT=myslug

# 2. Cold start: up + status + seed + audit
make -f tools/memory/Makefile bootstrap

# 3. Verify
make -f tools/memory/Makefile audit
make -f tools/memory/Makefile status
make -f tools/memory/Makefile show-project
```

## Subcommands (low-level; usually you use the Makefile)

```bash
# Schema
memory.sh schema                       # list the 8 labels
memory.sh schema describe Pitfall       # one label's description

# Writes (group_id auto-resolved from .project)
memory.sh node --type Component --uuid pkg-mal-core --name mal-core --summary "..." --path mal-core/
memory.sh rel  --type TESTS  --src inv-foo --dst inv-bar
memory.sh rel  --type INCLUDES --src inv-foo --dst paper-x --prop role=anchor

# Reads
memory.sh query "MATCH (n:Component) WHERE n.group_id='myslug' RETURN n.uuid, n.name"
memory.sh query "MATCH (a)-[r:TESTS]->(b) WHERE r.group_id='myslug' RETURN a.name, b.name" --rw

# Project seed (uses .project if no arg, else takes a slug)
memory.sh seed                          # reads tools/memory/seed/<.project>.yaml
memory.sh seed myslug                   # explicit

# Audit
memory.sh audit                         # runs the 3 invariants, exit 0/1

# Stack health
memory.sh status                        # docker + neo4j-cli + graphiti mcp
```

## Makefile targets

```bash
make -f tools/memory/Makefile help
make -f tools/memory/Makefile set-project PROJECT=name
make -f tools/memory/Makefile bootstrap        # up + status + seed + audit
make -f tools/memory/Makefile seed
make -f tools/memory/Makefile audit
make -f tools/memory/Makefile query CYPHER="..."
make -f tools/memory/Makefile wipe             # destructive; backs up to /tmp
make -f tools/memory/Makefile status
make -f tools/memory/Makefile schema-labels
make -f tools/memory/Makefile clean-schema-cache
```

## Files in this package

| File | Purpose |
|---|---|
| `Makefile` | Project-agnostic entry points. Reads `.project`. |
| `memory.sh` | Low-level dispatcher. |
| `schema.sh` | Parses `memory/config/config.yaml`, caches label list in `runs/schema.cache`. Subcommands: `labels`, `describe <L>`, `validate <L>`, `all`. |
| `add-node.sh` | Validates label + resolves project + runs MERGE for one typed node. |
| `add-rel.sh` | Resolves project + validates src/dst exist + runs MATCH+MERGE. |
| `audit.sh` | Resolves project + runs `invariants.cypher`, exits 0/1. |
| `seed.sh` | Compiles `seed/<project>.yaml` into Cypher, runs atomically, audits after. |
| `lib/project.sh` | Shared helper that resolves the project (group_id). |
| `invariants.cypher` | The three schema invariants. `__GROUP_ID__` and `__SCHEMA_LABELS__` are substituted at runtime. |
| `seed.template.cypher` | Reference shape of a generated seed (read-only doc). |
| `seed.config.example.yaml` | Copy-and-edit template for a new project. |
| `seed/<project>.yaml` | Per-project seed. Agent-owned. |
| `.project.example` | Template for `.project` (commented). |
| `README.md` | This file. |

## The three invariants

`memory.sh audit` runs these. Any non-zero result fails the audit. They
operate on the project resolved from `.project` (not a hardcoded group_id).

1. **No Entity-only node.** Every node must have at least one schema label
   besides `:Entity`. (`MATCH (n:Entity) WHERE size(labels(n)) = 1 ...`)
2. **No orphan relation.** Every rel endpoint must exist. (`MATCH
   (a)-[r]->(b) WHERE a IS NULL OR b IS NULL ...`)
3. **No label outside the schema.** Every label must be in
   `memory/config/config.yaml`. (`UNWIND labels(n) ... NOT IN [...]`)

## How to seed a project

1. Set the project slug (one-time): `make -f tools/memory/Makefile set-project PROJECT=myproject`
2. `cp tools/memory/seed.config.example.yaml tools/memory/seed/myproject.yaml`
3. Edit the yaml. Every node needs `uuid`, `name`, `summary` (and
   optionally `path`). Every relation needs `src`, `type`, `dst`. The
   `project:` field is required (used in logs); `group_id:` is optional
   (the resolved slug is authoritative).
4. `make -f tools/memory/Makefile seed`. The seed runs atomically and
   immediately audits. If the audit fails, the script exits 1; the graph
   may be in a partial state but a re-run converges (every `MERGE` is
   idempotent).
5. If the seed is bad and you need a clean slate: `make -f tools/memory/Makefile wipe`
   (backs up to `/tmp/<project>-wipe-<ts>.json` first).

## How to extend the schema

The schema lives in one place: `memory/config/config.yaml` (lines 81-99).

1. Edit the file. Add a new `entity_types` entry under
   `graphiti.entity_types`. Each entry has a `name` and a `description`
   (the description guides the LLM extractor and is what `schema.sh
   describe` returns).
2. Restart the Graphiti MCP container so it picks up the new config:
   `cd memory && docker compose restart graphiti-mcp`.
3. Run `memory.sh schema` to confirm the new label appears.

Do not invent a label at write time. The wrapper will reject unknown
labels with `error: '<Label>' is not in schema`.

## When to use MCP `add_memory` (and when not to)

`add_memory` is acceptable for **free-form episode text** that does not
need a typed node. Examples:

- Session summaries ("On 2026-07-04 the user approved plan X. The next
  step is Y.").
- Observations ("The 03_train.py script ran for 4.2 hours with n_rollouts=50.").
- Anything that should be retrievable via `search_nodes` but does not
  belong to a structural class (Component, Investigation, etc.).

`add_memory` is **forbidden for typed nodes**. Use `memory.sh node` /
`memory.sh rel` instead. The MCP path silently re-classifies the
`type: "json"` field and produces mis-labelled graphs (verified
2026-07-04 after a 261-node wipe).

## TODO (post-MVP)

- Pre-commit hook that runs `make audit` on graph-touching commits.
- Lock advisory: a `memory.sh lock --scope <label>` that appends a
  `:Lock` Episodic node and refuses writes during the lock window.
  Useful for serialising multi-agent sweeps over the same group.
- yq-based yaml parser to replace the inline Python parser. The current
  parser is correct for the conventions we use but breaks if a value
  contains a colon at line start. The seed files do not, but the
  example.yaml shows that `props: {k=v, k=v}` could in principle be
  misread.
