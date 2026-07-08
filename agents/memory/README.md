# `agents/memory/` — Project Memory Infrastructure (installable module)

A self-contained memory subsystem for agent-driven projects. Provides a
Neo4j knowledge graph with validated writes, semantic recall, free-form
episodes, and a session lifecycle. Designed to be copied into another
project and wired up by `install.sh`.

## What it gives you

- **Validated writes** to Neo4j through a thin shell wrapper that
  schema-checks every label before any Cypher runs. Avoids the
  Graphiti-MCP `add_memory json` footgun that re-classifies text into
  mislabelled nodes.
- **Seven native custom tools** (memory_node, memory_rel, memory_query,
  memory_audit, memory_seed, memory_status, memory_init) that the LLM
  can call directly — no shell-escaping the agent has to remember.
- **One conceptual skill** (`project-memory`) the agent loads on
  demand to know the schema, the write/read split, the session
  lifecycle, and the "do not use" rules.
- **A make-driven human CLI** for the developer (audit, seed, wipe,
  status, session-start, session-end) that the same shell scripts
  back.

## Quick start (in this repo, already installed)

```bash
# Show the resolved project name (group_id).
make -f agents/memory/scripts/Makefile show-project

# Cold start the stack: docker compose up + seed + audit.
make -f agents/memory/scripts/Makefile bootstrap

# Per-session routines.
make -f agents/memory/scripts/Makefile session-start
make -f agents/memory/scripts/Makefile session-end
```

## Quick start (in another project)

```bash
# 1. Copy this directory to <other-project>/agents/memory/
cp -r /path/to/this/repo/agents/memory <other-project>/agents/memory

# 2. Run the installer.
cd <other-project>
bash agents/memory/install.sh --project my-project --openai-key sk-...

# 3. Verify.
make -f agents/memory/scripts/Makefile show-project
make -f agents/memory/scripts/Makefile status
```

The installer wires up:

- `agents/memory/.project` (the group_id, gitignored)
- `agents/memory/runtime/.env` (gitignored)
- `.opencode/tools/memory_*.ts` (native tools, skip-if-exist)
- `.agents/skills/project-memory/SKILL.md` (the conceptual skill, skip-if-exist)
- `opencode.json` (new permission rules, idempotent)
- `.gitignore` (new ignore patterns, idempotent)

## For agents: discover me

If you are an agent landing in a project that contains `agents/memory/`
and you want to know whether the module is wired up, call the
`memory_init` tool (after a restart if it isn't in your toolset yet).
It returns a JSON report — read-only, no files modified, no Cypher run:

```json
{
  "project_root": "/abs/path/to/project",
  "project_slug": "myproject" | null,
  "checks": [
    { "name": ".project",                                 "ok": true,  "detail": "slug='myproject'" },
    { "name": "opencode tool: memory_node.ts",            "ok": true,  "detail": "installed" },
    { "name": "opencode tool: memory_init.ts",            "ok": true,  "detail": "installed" },
    { "name": "skill: project-memory",                    "ok": true,  "detail": "installed" },
    { "name": "runtime .env",                             "ok": true,  "detail": "present" },
    { "name": "opencode.json perms",                      "ok": true,  "detail": "edit(.project)=ok, bash-deny=ok, memory-tools=ok" }
  ],
  "next_step": "Memory module is fully wired up. ...",
  "ready": true
}
```

- If `ready` is `true`, follow `next_step` and start using the other six
  tools.
- If `ready` is `false`, follow `next_step`. Typical fix:
  `bash agents/memory/install.sh` (the installer is idempotent).
- Pass `verbose=true` to also probe the docker stack (slower — runs
  `memory.sh status` under the hood).

If `memory_init` is not in your toolset, the project has the module as
source (`agents/memory/opencode-stubs/tools/`) but the stubs were never
copied to `.opencode/tools/`. Re-run the installer: it's idempotent and
the tool-copy loop is a `*.ts` glob, so it picks up new tools on the
next pass. If the installer is not available, the install steps are
documented above in "Quick start (in another project)".

If you are an agent in a different harness (not OpenCode) and
`memory_init` is not available, the source TypeScript at
`agents/memory/opencode-stubs/tools/memory_init.ts` shows exactly what
to check — it is a single file with a `Check` / `Report` shape, no
harness-specific APIs.

## Layout

```
agents/memory/
  README.md                     this file
  install.sh                    THE installer
  uninstall.sh                  best-effort reverser
  opencode-stubs/               source of files copied to consumer project
    skills/project-memory/SKILL.md
    tools/memory_node.ts
    tools/memory_rel.ts
    tools/memory_query.ts
    tools/memory_audit.ts
    tools/memory_seed.ts
    tools/memory_status.ts
    tools/memory_init.ts
  runtime/                      docker stack (Neo4j + Graphiti MCP)
    docker-compose.yml
    .env.example
    .gitignore
    config/config.yaml          the schema (8 entity types)
  scripts/                      the wrapper (the Makefile entry points)
    memory.sh                   dispatcher
    schema.sh  add-node.sh  add-rel.sh
    audit.sh  seed.sh  bootstrap-apply.sh
    session-start.sh  session-end.sh
    Makefile
    lib/{project.sh, parse-yaml.py}
    bootstrap/                  pre-configured knowledge entries
    README.md                   wrapper contract
  seed.config.example.yaml      starter for seed/<project>.yaml
  invariants.cypher
  seed.template.cypher
  .project.example              template for .project
  # .project                    generated by install.sh, gitignored
  # runtime/.env                generated by install.sh, gitignored
  # seed/<project>.yaml         generated by install.sh, gitignored
```

## Architecture in one paragraph

The agent uses the **custom tools** for typed writes (memory_node,
memory_rel) and reads (memory_query, memory_audit, memory_status,
memory_seed, memory_init) — these are native LLM-callable functions
with Zod-typed args. Behind the scenes the six write/read tools
delegate to a shell script in `scripts/`, which validates the label
against `runtime/config/config.yaml` and runs parameterised Cypher
via `neo4j-cli`. `memory_init` is the odd one out: it stays in
TypeScript, runs no Cypher, and just inspects files (and optionally
probes the docker stack) to tell you whether the module is wired up.
Semantic recall and free-form text episodes go through the **Graphiti
MCP server** (in the `runtime/` docker stack):
`mcp__graphiti-memory__search_nodes`, `mcp__graphiti-memory__search_facts`,
`mcp__graphiti-memory__add_memory` with `source: "text"`. The
**conceptual skill** (`project-memory`) loads on demand and tells the
agent when to use which path.

## Why install via the wrapper, not via `mcp__add_memory`

`mcp__graphiti-memory__add_memory` with `source: "json"` accepts a
`type` field but the LLM extractor in MCP 1.26.0 ignores it and
re-classifies from text, producing mislabelled nodes. The wrapper
script (`scripts/memory.sh node`) validates the label against the
schema before any Cypher runs, so a wrong label exits 1 and never
writes. The custom tools (`memory_node`, `memory_rel`) wrap the
wrapper, giving the LLM typed args and the safety of schema
validation. Use the wrapper for anything that needs a structural
class. Use `mcp__add_memory` only for `source: "text"` (free-form
episodes, session summaries).

## Schema

8 entity types, declared in `runtime/config/config.yaml` (lines 81-99).
Add or remove a type by editing the yaml and restarting
`graphiti-mcp` (`cd agents/memory/runtime && docker compose restart
graphiti-mcp`).

| Label | One-line use |
|---|---|
| `Component` | A package, file, service, dataset, or external dep. The structural backbone. |
| `Investigation` | A bounded research thread with status (open/closed) and findings. Group Pitfall/Pattern/etc. under one via `[:PART_OF]`. |
| `Architecture` | An architectural decision, dependency rule, or structural fact. |
| `Pattern` | A reusable solution, idiom, or convention that works well here. |
| `Pitfall` | A known gotcha or anti-pattern. |
| `Tool` | A specific tool, command, or library that proved useful. |
| `Operational` | A practical fix or command pattern that saves time. |
| `Preference` | A team preference (naming, commit policy, never-do rules). |

## Three schema invariants (`memory_audit`)

1. **No Entity-only node.** Every node has at least one schema label
   besides `:Entity`. Catches "write bypassed the wrapper" scenarios.
2. **No orphan relation.** Every rel endpoint exists. Catches dangling
   references after a partial wipe.
3. **No label outside the schema.** Every label is in
   `runtime/config/config.yaml`. Catches typos in ad-hoc Cypher.

## Uninstalling

`uninstall.sh` reverses the install: removes the opencode-stubs that
were copied (if unchanged), reverses the `opencode.json` patches and
the `.gitignore` patches. It does NOT delete `agents/memory/` itself
— that's a `git rm -r` the human does, since the module is the
project's source of truth.

```bash
bash agents/memory/uninstall.sh
```

## Why a shell wrapper, not a Python package

The wrapper has to (a) parse the schema yaml at runtime to validate
labels, (b) emit parameterised Cypher (not string interpolation), (c)
idempotently MERGE on `uuid + group_id`, and (d) be invokable from a
Makefile, the bash tool, and a Bun `$` template tag. A 200-line
bash + python lib does all four with no install step. A Python
package would add a `uv sync` dependency and a venv just to do the
same thing.
