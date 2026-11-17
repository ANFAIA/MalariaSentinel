# docs/ — Concepts, Plans & Website

Project documentation: the conceptual documents (one per pipeline stage),
design plans, and the project website (served from this directory).

## Layout

| Path | Purpose |
|---|---|
| `concepts/` | **Conceptual documents** — one LaTeX document per pipeline stage: `download/`, `ingest/`, `abm/`, `scoring/`, `training/`, `prediction/`. Each stage's question set lives beside its document. `concepts/README.md` is the stance note that governs how they are written; `concepts/contracts.yaml` and `concepts/generated/` are build inputs and build output. |
| `plans/` | Design and execution plans — `completed/` (done work, kept for reference) and `in-process/` |
| `designs/` | Design briefs (`SITEMAP.md` is the registry) — temporary inputs to the drafting step, deleted once the plan absorbs them |
| `index.html` + assets | Project website (GitHub Pages; `CNAME`, favicons, `site.webmanifest`) |
| `licenses.md` | Licence record for the data products |

## Conventions

- **Conceptual document**: one per pipeline stage, under `concepts/<phase>/`.
  The document explains how the stage works — purpose, processes, algorithms,
  inputs and outputs — for a reader who has never opened the code. Values are
  generated at build time from `mal-core/config/model_constants.yaml`; prose
  carries only what survives a refactor. Build with `tools/build_concepts.sh`.
- **Contract facts** (band names, sentinels, contract versions, sidecar keys)
  live in the code and in the tests that pin them. `plans/in-process/spec-retirement-ledger.md`
  is the audit trail of the nine per-domain specs that were retired in favour
  of the conceptual documents.
- **Plans** move from `plans/in-process/` to `plans/completed/` when the
  acceptance criteria pass; never delete completed plans.
