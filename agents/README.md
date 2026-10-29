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
| `loops/supervisor.md` | Primary orchestrator: talks to the user, plans, delegates, integrates results. |
| `loops/test-fixer.md` | Subagent: iterate a check command until it exits 0. |
| `loops/code-reviewer.md` | Subagent: review a code change and return structured findings. Read-only. |
| `loops/doc-researcher.md` | Subagent: research questions from the repo and the web; returns a sourced brief. |
| `loops/security-auditor.md` | Subagent: OWASP-style audit. Read-only. |
| `loops/gawt-editor.md` | Subagent: file-editing specialist inside a shared gawt worktree (all edits via gawt MCP). |
| `loops/improvement-agent.md` | Subagent: reviews research-harness cycles and auto-applies improvements. |
| `janus/README.md` | The `agents/janus/` deepagents multi-agent orchestrator (separate subsystem). |

## How the pieces relate

- **OpenCode** is the runtime. Agents are defined in `.opencode/agents/<name>.md`
  (per-project) and the active primary agent (Build / Plan / General)
  supervises the session. See `opencode.json` for the active configuration.
- **Protection** of project-level governance files (this README,
  `AGENTS.md`, `.gitignore`, `opencode.json`) is
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
- **No state store.** The session itself is the only short-term state;
  durable facts live in GitHub issues, milestones, and PR descriptions.

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
