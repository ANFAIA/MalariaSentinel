# Design Sitemap

Registry of design documents in this directory. Updated by the EGM
brainstorm and draft skills.

Each design has an executable plan under `docs/plans/in-process/`; the plan
moves to `docs/plans/completed/` when it is implemented.

| Document | Date | Author | Status | Components | Description |
| --- | --- | --- | --- | --- | --- |
| [Per-Stage Conceptual Documentation](per-stage-conceptual-documentation.md) | 2026-11-16 | david-fm | RFC (awaiting team feedback) | `docs/concepts/*`, `docs/reference/*`, `docs/specs/*`, `docs/index.html` | Replaces the eight `docs/specs/` contract documents with six per-stage conceptual LaTeX documents (`download`, `ingest`, `abm`, `scoring`, `training`, `prediction`), one shared "how to write a conceptual document" note, a generated technical reference for Python and C++, and a warnings-only coherence review on pull requests. The ODD 2010 description of the ABM becomes the base of `docs/concepts/abm/`. Its executable plan is `docs/plans/in-process/per-stage-conceptual-documentation.md`. |
