# Design Sitemap

Registry of design documents in this directory. Updated by the EGM
brainstorm and draft skills.

**A design in this directory is temporary.** The EGM flow is: brainstorm →
RFC brief here → drafted plan → implementation. The brief is consumed by the
drafting step and deleted; the plan is the durable artefact, and it lives in
`docs/plans/in-process/<feature>.md` until it is executed, then moves to
`docs/plans/completed/<feature>.md`. A brief that has already been drafted has
no reason to stay in this directory — keeping it produces two documents stating
the same thing with different wording, which is how drift starts.

| Document | Date | Author | Status | Components | Description |
| --- | --- | --- | --- | --- | --- |
| _(none)_ | | | | | |

## Drafted plans (their briefs are gone)

| Plan | Date | Author | Brief deleted | Description |
| --- | --- | --- | --- | --- |
| [Individualization and Movement](../plans/in-process/individualization-and-movement.md) | 2026-11-17 | david-fm | git (brief borrado) | Individualiza las personas (agentes con posición propia en vez de densidad por celda) y rediseña el movimiento de los mosquitos (ley por tramos de distancia con radios y velocidades medidos, micro-integrador de dos bandas en vez de ticks de 1 s), añade la capa macho con sitio de enjambre asignado, el registro acuático por celda con la posición de la madre, un arnés de escenarios sintéticos sobre manifiesto y un ledger de eventos. |
| [Per-Stage Conceptual Documentation](../plans/completed/per-stage-conceptual-documentation.md) | 2026-11-16 | david-fm | git `75dc50c` | Replaces the nine per-domain contract specifications with six per-stage conceptual LaTeX documents (`download`, `ingest`, `abm`, `scoring`, `training`, `prediction`), one shared "how to write a conceptual document" note, a generated technical reference for Python and C++, and a warnings-only coherence review on pull requests. The ODD 2010 description of the ABM becomes the base of `docs/concepts/abm/`. |
