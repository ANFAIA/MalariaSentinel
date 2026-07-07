# `agents/` — Project Agents Module

The home of the project's agent-related infrastructure. This directory is a
**logical umbrella** for everything that drives the agent's behaviour,
context, and protection model. It is **not** a runtime: OpenCode is the
runtime, and the actual configuration lives in `opencode.json` at the
project root.

## What lives here

| Subdir / file | Purpose |
|---|---|
| `loops/AGENTS.md` | Common rules for every specialised loop agent. Loaded automatically via `opencode.json` → `instructions`. |
| `loops/test-fixer.md` | Subagent: iterate a check command until it exits 0. |
| `loops/code-reviewer.md` | Subagent: review a code change and return structured findings. Read-only. |
| `loops/doc-researcher.md` | Subagent: query the project knowledge base first; web is a fallback. |
| `loops/security-auditor.md` | Subagent: OWASP-style audit. Read-only. |
| `memory/README.md` | The `agents/memory/` installable module — see its README for layout, install, uninstall. |

## How the pieces relate

- **OpenCode** is the runtime. Agents are defined in `.opencode/agents/<name>.md`
  (per-project) and the active primary agent (Build / Plan / General)
  supervises the session. See `opencode.json` for the active configuration.
- **Knowledge base** lives in `agents/memory/` (Neo4j + Graphiti MCP, plus
  native OpenCode tools and a conceptual skill). The `doc-researcher` loop
  queries it first, before going to the web. Other loops and the supervisor
  can also query it on demand.
- **Protection** of project-level governance files (this README,
  `AGENTS.md`, `.gitignore`, `opencode.json`, `agents/memory/.project`) is
  handled by OpenCode's `permission.edit` block in `opencode.json`. Every
  edit to a protected file prompts the user — no allowance subsystem, no
  pre-commit hook, no separate file list.

## What is NOT in this module

- **No Python code.** OpenCode already implements the primary agent, the
  compaction agent, subagent invocation, and per-tool permissions. A
  Python layer would duplicate that.
- **No orchestration wrapper.** Loops are just subagents. The supervisor
  invokes them with `@<name>` or via the `task` tool; OpenCode handles
  session isolation and child session navigation.
- **No state store.** The knowledge base (Neo4j) is the only persistent
  state. The session itself is the only short-term state.

## Adding a new loop

1. Create `agents/loops/<name>.md` with frontmatter (`description`, `mode:
   subagent`, `permission`) and a prompt body that follows the structure
   documented in `agents/loops/AGENTS.md`.
2. If the loop should be auto-invoked by the primary agent, add a
   `permission.task` entry for it in `opencode.json` → `agent.build`
   (`"allow"` for mechanical loops, `"ask"` for anything that reads or
   reports project state).
3. Restart OpenCode so the new agent is registered. New subagents are
   picked up at startup, not on the fly.
4. Add a `Component` node in the knowledge base (see
   `agents/memory/README.md`) so the next session can recall it exists.

## The `agents/memory/` installable module

The `memory/` subdirectory is a self-contained, installable package:
Neo4j + Graphiti MCP docker stack, a shell wrapper that validates
labels, a conceptual skill (`project-memory`), and 6 custom tools
(`memory_node`, `memory_rel`, `memory_query`, `memory_audit`,
`memory_seed`, `memory_status`) that the LLM can call directly. The
`install.sh` script wires it into a consumer project: writes
`.project` and `runtime/.env`, copies the opencode-stubs (skill +
tools) into the project's `.agents/skills/` and `.opencode/tools/`,
and patches `opencode.json` and `.gitignore` idempotently. The
`uninstall.sh` script reverses the install.

`tools/hitl/` was removed in 2026-07 in favour of OpenCode-native
`permission.edit`. The earlier design (with `tools/memory/` and `memory/` at the
project root) was project-agnostic but split across two trees. The
consolidated form under `agents/memory/` is the same idea — copy-
pasteable to other repos — but with a single installer, a single
file-protect scheme, and a single entry point for the agent.
