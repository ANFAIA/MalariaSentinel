# odd-fixes — ODD 2010 review notes, regrouped into pending work

Source: handwritten review notes transcribed in
`.cache/odd-latex/odd-2010-malariasentinel-notes.tex` (ODD 2010 description of
`mal_abm_fast`, review copy, ~85 comments on pp. 1–32).

**What this directory is now (2026-11-17).** Every note from the ODD review was
contrasted against the two plans that `docs/designs/SITEMAP.md` registers —
`docs/plans/in-process/individualization-and-movement.md` (the model change) and
`docs/plans/completed/per-stage-conceptual-documentation.md` (the documentation
layer) — and the notes were regrouped by theme. **Each document below contains only
work that has not been done**: the parts already covered are not repeated, they live
in the plan that covers them (each document says which).

| # | Document | Theme | Origin packs |
|---|---|---|---|
| 01 | [Habitat and environment](01-habitat-and-environment.md) | Species-aware habitat, the contested terms of the potential equation, the sea and the salinity channel | 05, 06 |
| 02 | [Aquatic phase](02-aquatic-phase.md) | Desiccation and washout mechanics, the initial development of seeded cohorts | 07 |
| 03 | [Vector behaviour](03-vector-behaviour.md) | Dispersal kernel, starvation rule, fauna as a cue, gonotrophic durations | 03, 04 |
| 04 | [Transmission semantics](04-transmission-semantics.md) | Same-day death bites, EIP feasibility, `E_H` infectiousness, Ross–Macdonald coherence | 11 |
| 05 | [Parameters and calibration](05-parameters-and-calibration.md) | Provenance table, `k_ref`, naming and units, the constants the ODD singled out | 08, 13 |
| 06 | [Observation and output](06-observation-and-output.md) | One diagnostic artifact, honest fields (`abm_params_hash`, `eip_frac`), one schema source | 10 |
| 07 | [Engine hygiene](07-engine-hygiene.md) | Dead paths, duplicated state, the `dynamics` column type lie | 12, 03, 05 |
| 08 | [Parked design questions](08-parked-questions.md) | Adaptation, prediction phase, asynchronous environment loading | 13 |
| 09 | [Docs and papers](09-docs-and-papers.md) | The `papers/` corpus as a generated artifact | 01 |

## How to work on one of them

Every document has the same shape:

- **Status** — pending, and where the already-covered part lives.
- **Objective** — the one thing the document is for.
- **Index** — the open questions, with the note they come from.
- **One section per question**: the note *verbatim*, the current state with the
  code/config references, the decision to be made, and **done when** (the criterion
  that closes it).
- **Dependencies / open points** — what has to land first, and what it collides with.

## Notes resolved or superseded during triage

- p.8 "reduce calibration" → means *refine `k_ref`*; it is item 5.2.
- p.11 "necessary for non-? human/livestock?" → discarded (human and livestock
  movement are covered by the movement redesign).
- p.25 "this keeps the same" (wind) → the wind channel is kept, unchanged.
- The male/female survival difference (p.27) → answered in document 05's sibling
  plan, `individualization-and-movement.md` §8.6; kept for traceability at the end of
  document 08.
