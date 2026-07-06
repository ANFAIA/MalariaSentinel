# `tools/hitl/` — Human-in-the-loop Permission Guard

The file-edit / command-control subsystem for the project. It enforces the
HITL policy: a small list of files and bash patterns are reserved for the
user, and the agent must ask before touching them.

This package is **independent** of `tools/memory/` (the knowledge-graph
subsystem). They used to share a directory for convenience; that made
people think the two were coupled. They aren't. Memory writes are Cypher;
permission decisions are file-pattern matches. Different problems, different
machinery.

## What this is

A small Makefile-driven guard with three enforcement layers, all
configurable from the project root:

1. **Agent-level (AGENTS.md)** — the agent reads `AGENTS.md` and runs
   `make -f tools/hitl/Makefile protected-check P=<path>` before any
   edit to a file in the protected list. If the check fails, the agent
   asks the user.
2. **Git-level (pre-commit hook)** — once installed, refuses any commit
   that touches a protected file unless (a) the file is in
   `.protected-allowances` for this session, or (b) the commit message
   contains the literal string `protected-edit-approved`.
3. **OpenCode-level (`opencode.json`)** — runtime deny rules that run
   *before* the tool call. Hard-deny a small set of paths and bash
   patterns. The agent cannot bypass this from inside a session
   because opencode loads the config once at startup.

The three layers are independent. Drop any one and the other two still
work. Keep all three for defence in depth.

## Quick start

```bash
# 1. List the protected files
make -f tools/hitl/Makefile protected-list

# 2. Check whether a path needs approval
make -f tools/hitl/Makefile protected-check P=opencode.json
# → exit 1 if blocked

# 3. Grant a one-off allowance (logged to runs/protected.log)
make -f tools/hitl/Makefile protected-allow P=opencode.json

# 4. Install the git hook (one-time per clone)
make -f tools/hitl/Makefile install-hooks

# 5. Verify the subsystem is consistent
make -f tools/hitl/Makefile audit
```

## Files in this package

| File | Purpose |
|---|---|
| `Makefile` | Entry points. Targets: `protected-list`, `protected-check`, `protected-allow`, `install-hooks`, `uninstall-hooks`, `audit`. |
| `.protected` | The canonical list of files that require human approval. One path per line; `#` for comments; fnmatch globs allowed. |
| `.protected-allowances` | Per-session allowances. One path per line. Gitignored. The agent reads this to know "the user already said yes for this." |
| `check-edit.sh` | The script that decides whether a path is allowed. Reads `.protected` + `.protected-allowances`. Used by the Makefile. |
| `hooks/pre-commit` | The git backstop. Source of truth lives here; `install-hooks` copies it to `.git/hooks/pre-commit`. |
| `OPENCODE-PERMISSIONS.md` | The spec for the `opencode.json` `permission:` block (what is hard-denied, why, and how to override). |
| `README.md` | This file. |

## The protected list (`.protected`)

Three tiers:

- **T1: core HITL infrastructure** (highest protection) — `Makefile`,
  `check-edit.sh`, `.protected`. Modifying these would be modifying the
  policy itself.
- **T2: reusable templates** — none yet.
- **T3: top-level project files governing agent behaviour** — `AGENTS.md`,
  `.gitignore`, `opencode.json`, `OPENCODE-PERMISSIONS.md`. These are the
  project-level governance files the agent must not self-edit.

To add a new protected path: edit `.protected` (T1 — needs an
allowance first), add the path, commit.

## Allowances (`.protected-allowances`)

Per-session permissions. When the user says "yes, edit that file once"
in chat, the agent runs `make protected-allow P=<path>` to record the
allowance. The next `protected-check` and the next commit will let it
through. The file is gitignored — it is **runtime, per-machine state**,
never committed.

Allowances are matched as fnmatch globs. `tools/hitl/*.sh` allows every
`.sh` in this package for the session. Be deliberate with globs.

## Why this is in `tools/hitl/` and not `tools/memory/`

Originally the whole stack — Neo4j memory, schema, audit, seed, AND the
HITL file guard, AND the git hook — lived under `tools/memory/`. Two
unrelated subsystems sharing a directory. The result: the user kept
saying "memory and permissions are different things, why are they
together?" The honest answer was "historical accident, fixed in 2026-07-06."

The split is purely organisational. No logic moved. The same files, the
same scripts, the same hook — just under a directory whose name
describes its contents.

## What this is NOT

- This is not an OS-level sandbox. The process can still see the whole
  filesystem; the agent just gets a deny at the OpenCode tool-call layer
  and a deny at the git-commit layer. If you want a deny at the syscall
  layer, that's a different tool (e.g. nono on macOS / Landlock on Linux)
  and a different design conversation.
- This is not a malware scanner. It only enforces the protected list;
  it does not analyse file contents.
- This does not protect the user's global `~/.config/opencode/`. That
  lives outside the repo and is intentionally not in scope.

## See also

- `tools/memory/README.md` — the memory subsystem. Independent.
- `AGENTS.md` — the prompt that drives the agent-level check.
- `opencode.json` — the runtime deny block (project root).
