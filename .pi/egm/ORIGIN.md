# EGM bundle — provenance and maintenance

This directory is a **vendored subset** of the Elephant-Goldfish Model (EGM)
upstream, not original MalariaSentinel code.

- Upstream: <https://github.com/google/elephant-goldfish-model>
- Upstream commit: `270b10326bf366d823bc76fd662cf83808d5781e`
- Vendored: 2026-11-13
- License: Apache-2.0 (see `LICENSE`); upstream `README.md` kept for reference.

## What is included (runtime-minimal set)

| Path | Why it is needed |
| --- | --- |
| `skills/` (all 7) | The EGM workflow skills; registered via `../settings.json` (`"skills": ["egm/skills"]`). Whole skill dirs are kept intact (upstream tests check their internal links). |
| `agents/` (all 10 personas) | Read at runtime by the wrapper agents in `.pi/agents/egm-*.md` and passed as persona paths by the skills. |
| `resources/` | `execution_instructions.md` (read by `egm-draft`) and `document_standards/` (passed to reviewers). |
| `docs/*.md` (top level) | `harnesses.md` is cited unconditionally by the skills; the other top-level docs keep its cross-links intact. |
| `LICENSE`, `README.md` | Apache-2.0 redistribution requirement + provenance. |

## What was deliberately excluded

- `docs/designs/` (upstream's own design history), `docs/site/`, `docs/assets/`
- `site/`, `scripts/`, `tests/`, `assets/`, `.github/`, `com.github.copilot/`,
  `.claude-plugin/`, `.agents/`, `pyproject.toml`, `AGENTS.md`, `AI_POLICY.md`,
  `CONTRIBUTING.md`, `TESTING.md`, `plugin.json`
- **No upstream file inside this bundle has been modified.** Integration glue
  lives entirely outside it (see below).

## Integration files (outside this directory, MalariaSentinel-owned)

| File | Role |
| --- | --- |
| `.pi/settings.json` | Declares `egm/skills` as a project skill directory. |
| `.pi/APPEND_SYSTEM.md` | Tells every session to resolve `agents/`, `resources/`, `docs/` against `.pi/egm/`. |
| `.pi/agents/egm-*.md` (10 files) | pi wrappers: frontmatter (`tools`, `prompt_mode`, `run_in_background`, `allowed_subagents`) + pointer to the persona in this bundle. |

## Upgrade procedure

1. Clone upstream at the desired commit into a temp dir.
2. Re-copy the included paths listed above (rsync/cp), replacing this directory's
   content but keeping `ORIGIN.md`.
3. Diff upstream `agents/` and `skills/` against this copy to check whether
   persona or skill dispatch instructions changed in a way that requires
   updating the wrappers in `.pi/agents/`.
4. Update the commit hash at the top of this file.
5. Run `/reload` in pi and smoke-test `/skill:egm-review <file>`.
