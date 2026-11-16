# Pack 10 — Observation and output unification

> Source: ODD 2010 review notes. Status: initial plan — to be detailed later.

## Objective

Correct and unify the observation layer: a state output that carries
individuals + aquatic cohorts, merged diagnostics logs, and clean-up of
placeholder/broken sidecar fields.

## Notes (verbatim)

- **p.11** (Observation heading) — "Must be corrected and unified."
- **p.11** (State COG bullet) — "Wrong!! Must be individuals (array) + aquatic cohort (which may be individuals or a collective)"
- **p.12** — (Aquatic diagnostics) "include in state COG"; (brace over Aquatic diagnostics + Cohort log) "should be one"
- **p.12** — "Review the optimal output, must be at cell resolution or individual?"
- **p.26** (patch snap) — "It won't be necessary to record it; can be looked where it is by location and maping the cell, and put the eggs where it is"
- **p.29 A.7** (sidecar `abm_params_hash` = "sha256:pending") — "What is its use? Eliminate?"
- **p.29 A.8** (`eip_frac` actually = adults/alive) — "resolve this."
- **p.30 B.1** (contracts) — "what if only C++ version + Python reads (C++ version)"

## Initial steps

1. Design the unified state output: individual adult array + aquatic
   cohorts (cross-ref pack 02 — this is the output side of
   individualization), deciding cell vs. individual resolution.
2. Merge "Aquatic diagnostics" + "Cohort log" into a single artifact and
   fold aquatic diagnostics into the state COG.
3. Decide the fate of the patch band / `patch_id` recording (derivable
   from location per p.26).
4. Fix or remove `abm_params_hash`; fix or remove `eip_frac`.
5. Resolve the contract-versioning question, single C++ source of truth
   that Python reads, for yaml processing. Avoiding, duplicated code that
   needs to be equally changed and review, when the yaml changes.

## Dependencies / open points

- Output shape depends on packs 02 and 09 (seed semantics).
- Consumers to update: `state_loader.py`, GIF renderer, surrogate
  training pipelines, calibration scorers.
