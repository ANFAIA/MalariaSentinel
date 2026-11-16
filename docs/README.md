# docs/ — Concepts, Plans & Website

Project documentation: the conceptual documents (one per pipeline stage),
design plans, and the project website (served from this directory).

## Layout

| Path | Purpose |
|---|---|
| `concepts/` | **Conceptual documents** — one LaTeX document per pipeline stage: `download/`, `ingest/`, `abm/`, `scoring/`, `training/`, `prediction/`. Each stage's question set lives beside its document. `concepts/README.md` is the stance note that governs how they are written; `concepts/contracts.yaml` and `concepts/generated/` are build inputs and build output. |
| `specs/` | Per-domain specs — being **retired**, stage by stage, as each conceptual equivalent lands. `specs/_template.md` is the template a new spec starts from. **These specs are not authoritative**: an agent must verify every claim against the code before acting on it. |
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
- **Spec**: copy `specs/_template.md` into the matching domain folder. A spec
  is retired in the same commit that lands its conceptual equivalent.
- **Plans** move from `plans/in-process/` to `plans/completed/` when the
  acceptance criteria pass; never delete completed plans.
