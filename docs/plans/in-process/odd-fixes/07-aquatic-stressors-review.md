# Pack 07 — Aquatic stressors and cohort initialization

> Source: ODD 2010 review notes.
**Document sections invalidated (CUJ-4):** `docs/concepts/abm/odd-2010-malariasentinel.tex` → §7.2 "Advance aquatic stages", §5.2 "Mosquito seeding".
When this pack is decided and applied, these are the passages that
must change; the document is amended in the commit that applies the
pack, not in the pack itself.
 Status: initial plan — to be detailed later.

## Objective

Clarify the desiccation/washout mechanics (coupling to K and larval
instars, exclusivity, threshold basis) and the initial development
fractions of seeded cohorts.

## Notes (verbatim)

- **p.20** (desiccation) — "Desiccation disconnected from larvae? Disconnected from K_{p,d}?"
- **p.20** (washout) — "R<40 → theoretical basis? Review this numbers comes from the yaml"
- **p.20** (daily process order) — "can't happen both" *(desiccation and washout)*
- **p.4** (aquatic cohorts) — "if it takes X days and added on day Y, where Y ≤ X, could those individuals take X−Y days to emerge?"
  *(questions the preset development fractions 0.58/0.47/0.38/0.29/0.20/0.00 used at seeding)*
- **p.20** (`last_larval_instar`) — "Theoretical number or mosquito config."

## Initial steps

1. Decide how desiccation should couple to `K_{p,d}` and to larval
   instars (today: only eggs + L1–L2, driven by `dry_days`, not by K).
   This could be alright, but it should be reviewed, based on studies.
2. Justify `wash_threshold_mm = 40` and `wash_fraction_max = 0.60` from
   literature, or adjust; confirm they live in `model_constants.yaml`.
3. Resolve whether desiccation and washout can co-occur (order vs.
   exclusivity) and document the chosen semantics.
4. Review the seeded-cohort development fractions: should a cohort added
   on day Y with stage duration X emerge after X−Y days (age-consistent)?
5. Confirm `last_larval_instar = 4` is a biological constant (cite) vs.
   a config value.

## Dependencies / open points

- Provenance of the numeric thresholds belongs to pack 08 (papers).
- Changing aquatic dynamics shifts calibration — rerun scorers.
