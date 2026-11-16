# Docs PR Agent + Codebase-Memory Bootstrap

> **Status**: In process (2026-08-13). Initial plan — design decisions pending.
>
> **Related**: `docs/plans/in-process/odd-fixes/01-odd-doc-and-papers.md` (ODD
> `.tex` automation — the first concrete consumer of the PR-doc agent proposed here).

## Intentions

1. **Make a documentation change** (the specific doc change is to be scoped when
   this plan is executed; candidate first target: the ODD description per pack 01).
2. **On every pull request, update the documentation on GitHub by calling an
   agent** — a CI job that runs an agent over the PR diff, regenerates the
   affected docs, and lands the result back on the PR branch, so docs never drift
   from the code that merged.

## Part 1 — PR-triggered doc-update agent

### Facts on the ground

- GitHub Pages serves **legacy build from `main:/docs`** (CNAME
  `malariasentinel.com`) → merged docs reach the site automatically; the agent
  only needs to get its output into the PR branch.
- **No `.github/workflows/` exists yet** — this plan creates the first workflow.
- `main` is protected (ruleset: 1 approval, no force-push, no deletion) → the
  agent workflow must **push to the PR branch**, never to `main`. Docs reach the
  website only after the PR merges.

### Proposed design

1. **Workflow**: `.github/workflows/docs-agent.yml`
   - Trigger: `pull_request` (`opened`, `synchronize`) with a `paths:` filter
     over doc-generating sources (e.g. `mal-core/src/mal_core/abm/**`,
     `**/model_constants.yaml`, `docs/specs/**`).
   - Steps: checkout PR head → run agent with the PR diff as input → agent
     regenerates affected docs (`docs/specs/**`, ODD `.tex`, `docs/README.md`)
     → commit + push to the PR branch (bot identity) → if docs changed, post a
     PR comment summarising the diff.
2. **Agent runner** (open decision — cost/trigger policy per pack 01):
   - Candidate A: hosted agent action (e.g. `claude-code-action` /
     `opencode` GitHub action) with a repo-scoped token.
   - Candidate B: self-hosted runner executing the same agent loops the repo
     already ships under `agents/loops/` (doc-researcher + test-fixer pattern).
3. **Loop guard**: the workflow must skip when the commit author is the doc
   bot itself (bot pushes to the branch retrigger `synchronize` → infinite loop).

### Acceptance criteria

- A PR touching an ABM source file gets a bot commit on the same branch with
  regenerated docs, plus a PR comment listing changed doc files.
- `main` is never pushed to by the workflow; merge → Pages rebuild shows the
  updated docs at `malariasentinel.com`.
- No infinite bot loop (verified by two consecutive `synchronize` events).

## Part 2 — Keep codebase-memory updated and in the repo

**Goal**: anyone who clones this repo and opens their agent (pi, opencode, janus)
gets codebase-memory **already loaded** — no manual indexing step.

### Facts on the ground

- MCP server binary: `~/.local/bin/codebase-memory-mcp` (stdio), configured in
  `agents/janus/.../agents.yaml` with `enabled: false` and
  `index_on_startup.enabled: false`.
- `opencode.json` (project) registers only `gitagent` + `langfuse` — **no
  codebase-memory server**.
- No `.codebase-memory/` directory in the repo: `index_repository(persistence=true)`
  writes `.codebase-memory/graph.db.zst`, which is the committable artifact.
- Global pi `AGENTS.md` already injects the codebase-memory usage block, but that
  is user-level, not repo-level — other harnesses don't see it.

### How to keep it in the repo

| # | Mechanism | What it gives |
|---|---|---|
| 2.1 | **Commit the graph snapshot**: run `index_repository(persistence=true)` and commit `.codebase-memory/graph.db.zst` (plus a `.gitignore` carve-out if needed) | A fresh clone ships a queryable graph; agents can `index_status`/`search_graph` before indexing anything |
| 2.2 | **Refresh in the PR doc agent**: the Part-1 workflow re-indexes (`mode: moderate`) after its doc pass and commits the refreshed `.zst` to the same branch | The snapshot tracks `main`, never silently rots |
| 2.3 | **Repo-level bootstrap instructions**: a short `## Codebase-memory` section in the repo `AGENTS.md` (or `.opencode/AGENTS.md`) telling any agent: at session start call `list_projects` → if missing/stale, `index_repository(mode=moderate)` | Works for every harness, independent of user-level config |
| 2.4 | **Register the MCP server in `opencode.json`** (`command: ~/.local/bin/codebase-memory-mcp`) and flip janus `enabled: true` + `index_on_startup.enabled: true` | Auto-connect + auto-index on startup for opencode and janus |

### Trade-offs / open points

- **Snapshot churn**: `.zst` regenerates on every merge → review its size before
  committing (if large, keep 2.2 as a scheduled/weekly refresh instead of per-PR).
- **Binary path portability**: `~/.local/bin/codebase-memory-mcp` is an absolute
  user path — repo config needs either a relative/vendored path or an install
  note (`docs/README.md`).
- **Stale-snapshot risk**: a committed graph can be older than the checkout;
  rule of thumb for agents: trust the snapshot for structure, `check_index_coverage`
  + `read`/`grep` for negative claims (existing evidence-tier rules apply).

### Acceptance criteria

- Fresh clone + open agent → `list_projects` shows `MalariaSentinel` (from the
  committed snapshot) without a manual index step.
- After 2.2 runs on a merged PR, `git diff` shows a refreshed `.codebase-memory/graph.db.zst`.

## Files (target)

- `.github/workflows/docs-agent.yml` (new)
- `docs/plans/in-process/docs-pr-agent-and-codebase-memory.md` (this plan)
- `.codebase-memory/graph.db.zst` (new, committed snapshot)
- `opencode.json` (add `codebase-memory` MCP server)
- `agents/janus/src/agents_janus/config/agents.yaml` (enable server + `index_on_startup`)
- repo `AGENTS.md` (bootstrap section; protected file — user approval required)

## Reference

- Pack 01: `docs/plans/in-process/odd-fixes/01-odd-doc-and-papers.md` (note p.1:
  "Create a GitHub Action to update this document for each PR using an agent").
- Pages config: `docs/CNAME` → `malariasentinel.com`, legacy build `main:/docs`.
