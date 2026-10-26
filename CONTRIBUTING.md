# Contributing to MalariaSentinel

## Workflow: `main` is protected

All changes land via **pull request**. Direct pushes, force-pushes, and deletions on `main` are
blocked by the **Main Protection** ruleset (repository maintainers are on its bypass list for
emergencies).

1. Branch off the latest `main` with `type/short-slug`, where `type` is one of
   `feat | fix | docs | test | chore` (e.g. `fix/abm-catalog-aoi`).
2. Commit following the conventions below.
3. Push the branch and open a pull request against `main`.
4. Merge with **squash** or **rebase** — merge commits are not used.
5. Delete the branch after merging. Keep branches short-lived.

One approving review is required. GitHub never counts self-approval, so a solo maintainer
merges their own PRs through the ruleset bypass; external contributors need an approval from
someone other than the PR author.

Automation and AI agents follow the same workflow. They commit with the maintainer's identity
and therefore inherit the maintainer's bypass, but opening a PR is still the expected path so
every change stays reviewable.

## Commit messages

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
type(scope): summary
```

Scopes name the package or area being touched: `abm`, `config`, `cli`, `commonlib`, `docs`,
`tests`. Real examples from the history:

```
feat(abm): render the run GIF inside the C++ engine and prune dead artifacts
fix(abm): resolve catalog AOIs and propagate engine failures
docs(config): document every YAML leaf and strip values from comments
test(abm): audit the suite and harden golden and sidecar contracts
```

## Local quality gates before opening a PR

### Python

```bash
uv sync --all-packages
uv run pytest        # canonical entry point, from the repo root
```

`uv run pytest` excludes the `integration` and `full` markers by default. Run them explicitly
when your change touches network or LLM paths:

```bash
uv run pytest -m integration
```

### C++ ABM engine

Required whenever you touch `mal-core/src/mal_core/abm/`:

```bash
uv run malariasim abm --compile           # configure + build + copy the binary into bin/
uv run malariasim abm --compile --clean   # clean rebuild
ctest --test-dir mal-core/src/mal_core/abm/build
```

`malariasim abm --compile` copies the fresh binary to
`mal-core/src/mal_core/abm/bin/mal_abm_fast_<platform>` (e.g. `mal_abm_fast_darwin`), the path
the Python wrapper resolves first. **Only if you build with raw `cmake` commands** must you copy
the binary there yourself — otherwise runs silently use a stale binary.

### Helpers

`tools/format.sh`, `tools/verify.sh`, and `tools/run_all_tests.sh` wrap the formatting, lint and
test commands used by the project.

## Where changes go

Respect the monorepo dependency rules:

| Package | Depends on |
|---|---|
| `mal-commonlib` | — |
| `mal-core` | `mal-commonlib` |
| `mal-execution` | `mal-core`, `mal-commonlib` |
| `mal-data-explorer` | — (scripts only) |
| `agents/janus` | `mal-core` (via the `malariasim` CLI) |

Nothing depends on the research packages. When research code stabilizes, promote it into
`mal-core` or `mal-commonlib` instead of importing across boundaries.

## Project rules a PR must respect

- **Single source of truth for constants.** Tunables live in
  `mal-core/config/model_constants.yaml`, validated by pydantic (`extra=forbid`, no defaults)
  and mirrored in the C++ `config.cc`. Do not add magic numbers to Python or C++ code; every
  YAML leaf carries a comment and `[unit]`.
- **Versioned contracts.** The environment-NC contract is `3.0` and the state-output contract
  is `4.0`; they version independently. If you change a schema, bump the relevant version and
  update the sidecar and parity tests in the same PR.
- **Protected files.** `AGENTS.md` is protected — edits go through gitagent with user approval.
- **Generated and heavy data stay out of git.** Raw datasets and `runs/` are gitignored and
  regenerated with `uv run malariasim download` / the pipeline.

## PR checklist

- [ ] `uv run pytest` is green.
- [ ] C++ touched: `uv run malariasim abm --compile` and `ctest` are green.
- [ ] New constants live in `model_constants.yaml` with a comment and unit.
- [ ] Contract versions bumped when a schema changed, with parity tests updated.
- [ ] Documentation updated when behavior or commands changed.
- [ ] No generated artifacts, raw data, or checkpoints committed.

## Reviewing a PR

- Does the change include tests, and do existing gates still pass?
- Are schema/contract changes versioned and covered by parity tests?
- Are new numbers defined in the YAML rather than inline in code or CLI flags?
- Are regenerable artifacts excluded from the diff?
