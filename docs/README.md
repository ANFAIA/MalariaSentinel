# docs/ — Specs, Plans & Website

Project documentation: per-domain specs, design plans, diagrams, and the
project website (served from this directory).

## Layout

| Path | Purpose |
|---|---|
| `specs/` | Per-domain specs — one folder per pipeline domain: `download/`, `ingest/`, `abm/`, `scoring/`, `training/`, `prediction/`, `commonlib/`, `data/`, `self_improve/` (each with a `_template.md` to start a new spec) |
| `plans/` | Design and execution plans — `completed/` (done work, kept for reference) and `in-process/` |
| `diagrams/` | Architecture and pipeline diagrams |
| `index.html` + assets | Project website (GitHub Pages; `CNAME`, favicons, `site.webmanifest`) |
| `presentacion-10-minutos.md` / `guion-presentacion-10-minutos.md` | 10-minute presentation slides + script |
| `system-status.md` | Current system status snapshot |
| `agent-selection-guide.md` | Which agent/loop to use for which task |

## Conventions

- **New spec**: copy `specs/_template.md` into the matching domain folder; keep
  specs current when the contract they describe changes (the ABM wire spec —
  `mal-core/src/mal_core/abm/docs/wire-spec.md` — is the single source of
  truth for engine data contracts).
- **Plans** move from `plans/in-process/` to `plans/completed/` when the
  acceptance criteria pass; never delete completed plans.
