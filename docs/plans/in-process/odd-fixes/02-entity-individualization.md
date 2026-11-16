# Pack 02 — Entity individualization (humans, cohorts at adult level, feeding success)

> Source: ODD 2010 review notes. Status: initial plan — to be detailed later.

## Objective

Move the model away from cell-level aggregates where individuality matters:
human hosts become (static) ABM individuals, aquatic cohorts are placed at
the *adult's* position rather than the cell (making aquatic cohorts some kind
of collective), and feeding success becomes a per-individual stochastic draw.

## Notes (verbatim)

- **p.3** (human hosts) — "what if agents also?"
- **p.3** (aquatic immatures) — "what if adults also cohort = eggs laid by female → inhereting position and stage"
  *Clarified by user: cohorts should be placed by the adults at the adult's
  position — at adult level, not cell level (eggs inherit the female's
  position and stage).*
- **p.3** (collectives) — "shouldn't be any collectives? → Example, mosquito males forms collectives in many species to attract the female"
- **p.14** (human compartments) — "shoud be individuals (ABM), even if they are static ones."
- **p.24** (below eq. 14) — "rething movement for individuals (not patches distances, but continues distances)."
- **p.29 A.2** — "Feeding success rate must be used when putting individuals"
  *(moved here per user: applies together with human individualization)*
- **p.30 A.12** (mobility) — "Removed when population is made agents."
- Cross-ref **p.14** — "Host landscape must be compulsory without host no malaria." → executed in pack 12.

## Initial steps

1. Design decision: representation of human individuals (static agents
   carrying an infection state?) and how the FOI/bite ledger aggregates
   them back to compartments — or whether compartments are retired.
   Human answer: Humans carry an infection state, and there is no need
   for aggregate them back as compartments, other thing is to make
   statistics out of them for logs or visualization purposes.
2. Egg/immature placement at the adult female's exact position (and
   inherited stage) instead of the snapped cell.
3. Wire `feeding_success_rate` into the per-individual feeding draw
   (today it is loaded but never consumed).
4. Defer: continuous-distance host movement (replacing OD matrices) and
   male swarms as a collective — scoped as follow-ups of this pack. As
   a first version humans, and animals (including wildlife). Will be represented
   as static agents.

## Dependencies / open points

- Heavy refactor; interacts with packs 03 (movement), 10 (state COG must
  become "individuals array + aquatic cohort") and 11 (transmission
  aggregation).
- Decide ordering: humans-first or adults-first.
