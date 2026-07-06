<!-- PROTECTED: requires human-in-the-loop approval to edit. -->
<!-- See tools/memory/.protected and AGENTS.md (Protected files). -->

# OpenCode Permission Guard — MalariaSentinel

This document explains the OpenCode-level guard layer that complements the
project's memory infrastructure (`tools/memory/`). It is project-scoped: the
config lives in `./opencode.json` at the project root and is **not inherited
by other repos** in the same machine.

## Purpose

The `tools/memory/` system already enforces a Human-in-the-Loop (HITL)
policy for protected files (see `AGENTS.md` → "Protected files — human-in-the-loop required"
and `tools/memory/README.md`). That policy has two enforcement levels:

1. **Agent-level**: the agent reads `AGENTS.md` and runs
   `make -f tools/memory/Makefile protected-check P=<path>` before any
   Edit/Write. If blocked, the agent must ask the user for an allowance.
2. **Git-level**: `tools/memory/hooks/pre-commit` rejects any commit that
   touches a protected file without a `protected-edit-approved` marker in
   the commit message.

The OpenCode permission block in `opencode.json` adds a **third,
runtime level** that runs *before* the tool call. It hard-denies a small
set of operations that are **reserved for the user** even when the agent
"forgets" the AGENTS.md rules. The agent cannot bypass it from inside a
session because opencode loads the config once at startup and evaluates
it before the bash/edit tool runs.

## What is hard-denied

### `edit` (the Edit/Write tools)

| Path | Why it's denied |
|---|---|
| `tools/memory/.protected` | Modifying the protected list itself = bypassing HITL |
| `tools/memory/.protected-allowances` | Self-granting permissions = bypassing HITL |
| `tools/memory/.project` | Overriding the Neo4j `group_id` silently |
| `tools/memory/OPENCODE-PERMISSIONS.md` | This document is the spec; agent shouldn't self-edit it |
| `opencode.json` | Self-modifying its own permission rules |

All other files fall back to opencode's default for `edit` (`ask`).
That is consistent with `AGENTS.md`'s HITL model: the user approves
edits of any non-protected file interactively.

### `bash` (the Bash tool)

The default is `allow` (essential so the agent can run `make`, `git`,
`uv`, etc. without prompting for every command). The following patterns
are hard-denied regardless of position in the command line:

| Pattern | What it blocks |
|---|---|
| `make -f tools/memory/Makefile protected-allow *` | The canonical HITL-grant command |
| `make -f tools/memory/Makefile set-project *` | One-time project identity decision |
| `make -f tools/memory/Makefile install-hooks *` | One-time git-hook install |
| `make -f tools/memory/Makefile wipe *` | Destructive — wipes all graph data |
| `git commit --no-verify *` | Bypasses the pre-commit hook |
| `git commit -n *` | Short form of the above |
| `*protected-allow*` | Catches bypasses like `cd tools/memory && make protected-allow P=...` or `sh -c "make protected-allow..."` |
| `*make*set-project*` | Catches bypassed invocations of `set-project` |
| `*make*install-hooks*` | Catches bypassed invocations of `install-hooks` |
| `*make*wipe*` | Catches bypassed invocations of `wipe` |
| `bash tools/memory/check-edit.sh*` | The check script is read-only — denying it prevents the agent from trying to invoke it as a side-channel |

**Pattern evaluation order matters.** In opencode, the **last** matching
rule wins. The file is ordered broad-first, narrow-last:

```jsonc
"bash": {
  "*": "allow",                       // default
  // ...deny rules come AFTER, so they override the default
  "make -f tools/memory/Makefile protected-allow *": "deny",
  // ...
  "*protected-allow*": "deny"
}
```

The wildcard patterns at the end are the safety net for bypass attempts
that re-order or wrap the canonical command. They will also match benign
commands that happen to contain the substring `protected-allow` (e.g. a
filename). The trade-off is intentional: false positives are noisy;
false negatives are a policy breach.

## What is NOT covered (known gaps)

This is the third enforcement level, not the only one. The agent and
git-hook layers still apply. The following gaps remain:

1. **`mcp__graphiti-memory__add_memory` with `source:"json"` and a
   `type` field in the body.** This is an MCP tool argument, not a
   bash pattern, so `permission:` cannot see it. The mitigation today
   is:
   - The prompt-level rule in `AGENTS.md` (FORBIDDEN TOOLS section).
   - The seed graph already contains `Pitfall: supermemory-deprecated`
     and `Preference: supermemory-globally-deprecated` nodes that
     document the policy.
   - **Planned**: a `.opencode/plugin/guard-memory-mcp.ts` plugin
     using the `tool.execute.before` hook to reject these calls at
     runtime. Not yet implemented.

2. **Pattern wildcards in `bash` can be evaded with `eval` or
   base64-decoded shell.** The agent is well-instructed against this
   in `AGENTS.md`; a runtime defense would require a separate
   shell-level audit tool.

3. **The user's global OpenCode config (`~/.config/opencode/`) is not
   protected by this file.** It is intentional — the project-scoped
   config cannot lock down a shared global config. The
   `supermemory-*` slash-commands have been removed from
   `~/.config/opencode/command/` to retire that pathway.

## How to make a one-off exception

The denies are hard. To run one of these commands, the user does it
manually in their own terminal (not through the agent). Examples:

```bash
# User runs in their own shell:
make -f tools/memory/Makefile protected-allow P=tools/memory/Makefile
make -f tools/memory/Makefile install-hooks
make -f tools/memory/Makefile set-project PROJECT=foo
make -f tools/memory/Makefile wipe
```

After a `protected-allow`, the agent can resume editing the target
file — but only if the target is **not** in the `edit:` deny list
above. The two policies compose:

- `permission: edit: { "tools/memory/.protected": "deny" }` — always
  blocked, regardless of allowances.
- `protected-allow` — adds an entry to
  `tools/memory/.protected-allowances` (gitignored). Used by
  `check-edit.sh` to allow the agent-level policy to pass.
- Pre-commit hook — refuses the commit unless the commit message
  contains `protected-edit-approved`.

## Why this is not in the global config

`~/.config/opencode/opencode.json` is shared across every project on
the machine. Putting the deny rules there would:

- Block the same patterns in unrelated projects (false positives).
- Couple the project's HITL policy to a per-machine file that has no
  audit trail.
- Make the config unscoped, so a future repo could not opt out.

The project-scoped `opencode.json` is the right scope: it travels with
the repo, is visible in the project's git history, and applies only
when opencode is started in this directory.

## Why project root, not `.opencode/`

OpenCode accepts the project config in two locations:
`./opencode.json` (project root) or `.opencode/opencode.json`.
This project uses the **root location** on purpose.

The `.opencode/` directory in this checkout is **not** an
OpenCode configuration directory — it is a local checkout of the
opencode TUI source (npm package). It contains `package.json`,
`node_modules/`, `tui.json`, and its own `.opencode/opencode.json`
(the TUI's plugin config, not the project's). Putting the project
config at `.opencode/opencode.json` would overwrite the TUI's
config and break the `opencode-speech-to-text` plugin.

A future agent that wonders "should this be in `.opencode/`?"
should answer: **no**, because `.opencode/` is already used
for something else. This is the same reason that `AGENTS.md`
and `.gitignore` live in the project root and not in a
subdirectory: project-level governance files sit at the root.

## Verification

After a fresh clone, the user can verify the guard is live:

```bash
# 1. opencode.json is blocked from agent edits
make -f tools/memory/Makefile protected-check P=opencode.json
# → exit 1, BLOCKED

# 2. After restarting opencode with the new config, an agent run of
#    `make -f tools/memory/Makefile protected-allow P=foo` is denied
#    by opencode before the shell even sees it.

# 3. Normal commands work
make -f tools/memory/Makefile status
make -f tools/memory/Makefile audit
uv run pytest
```

## Lifecycle

| Event | Action |
|---|---|
| New protected file added to `tools/memory/.protected` | If it lives under `tools/memory/`, the `edit: ask` default applies. If it's a project-level file (like `opencode.json`), add a `deny` entry here. |
| New user-only command is introduced | Add a `deny` pattern to the `bash:` block. |
| User wants to override a deny for a session | User runs the command in their own shell, not via the agent. |
| Agent finds a false positive in the `*protected-allow*` pattern | Refine the pattern to be more specific, but never more permissive. |

## File metadata

- **Path**: `opencode.json` (project root) and `tools/memory/OPENCODE-PERMISSIONS.md` (this file).
- **Schema**: <https://opencode.ai/config.json> (`Config.permission` block).
- **Reload semantics**: opencode loads config at startup only. After any edit to `opencode.json`, the user must quit and restart opencode for the new rules to take effect.
- **Protected**: both files are listed in `tools/memory/.protected` (T3: project-level governance).
