# odd-fixes — ODD 2010 review notes turned into work packs

Source: handwritten review notes transcribed in
`.cache/odd-latex/odd-2010-malariasentinel-notes.tex` (ODD 2010 description
of `mal_abm_fast`, review copy, ~85 comments on pp. 1–32).

Each file groups one thematic pack of notes. Plans are **initial and
concise** on purpose: they capture what we want to change and the verbatim
notes. They will be refined later into detailed plans (exact files,
functions, contracts, tests).

| Pack | Theme |
|---|---|
| [01-odd-doc-and-papers](01-odd-doc-and-papers.md) | ODD document automation + papers folder restructure |
| [02-entity-individualization](02-entity-individualization.md) | Humans as individuals, adult-level cohort placement, feeding success per individual |
| [03-movement-seeking-redesign](03-movement-seeking-redesign.md) | Guided direction-vector movement; individual/pheromone-based sensing |
| [04-gonotrophic-feeding-review](04-gonotrophic-feeding-review.md) | Feeding frequency, gonotrophic timings, mating, phase weights |
| [05-habitat-species-coherence](05-habitat-species-coherence.md) | Species-aware habitat, H-equation terms, state duplication, GeoPackage bugs |
| [06-sea-salinity-coast](06-sea-salinity-coast.md) | Open-sea masking, coastal influence, salinity effect |
| [07-aquatic-stressors-review](07-aquatic-stressors-review.md) | Desiccation/washout mechanics, cohort initial development |
| [08-params-provenance-calibration](08-params-provenance-calibration.md) | Every engineering prior backed by literature; k_ref; naming/units |
| [09-single-master-seed](09-single-master-seed.md) | One master seed for all RNG streams |
| [10-observation-output-unification](10-observation-output-unification.md) | Unified observation layer, state COG, sidecar/eip_frac fixes |
| [11-transmission-semantics](11-transmission-semantics.md) | Same-day death bites, EIP feasibility, E_H infectiousness, R-M coherence |
| [12-engine-simplifications](12-engine-simplifications.md) | Remove/strictify dead paths: no-host fallback, empty pop, unused ctor |
| [13-open-design-questions](13-open-design-questions.md) | Parked design questions (adaptation, prediction, async loading, survival) |

Notes that were resolved or superseded during triage:

- p.8 "reduce calibration" → means *refine `k_ref`*; already covered by pack 08.
- p.11 "necessary for non-? human/livestock?" → discarded (human/livestock
  movement already covered by packs 02/03).
