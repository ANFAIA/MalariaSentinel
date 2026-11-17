# 05 — Parameters and calibration: provenance of every constant

> **Status**: pending (2026-11-17). This document holds **only work that has not been
> done**. The **rule** is already binding: every parameter that enters the engine must
> have an entry in `model_constants.yaml` with its value, unit, evidence tier
> ([M]/[P]/[EP]/[NR]) and reference, and a row in `papers/REFERENCES.md`
> (`docs/plans/in-process/individualization-and-movement.md`, G9, NFR-5, NFR-8 and
> verification level 7). What is missing is the **audit of the constants that already
> exist**, and the three naming/unit decisions the ODD flagged.
> **Source**: ODD 2010 review notes
> (`.cache/odd-latex/odd-2010-malariasentinel-notes.tex`), pack 08, plus the survival
> question from pack 13.
> **ODD sections to amend when this is applied**: the generated parameter table,
> Appendix A (implementation details) and Appendix B.3 "Calibration and validation
> status".

## Objective

Turn the constants file into a table with a source in every row: for each key, either
a published anchor or an explicitly-marked engineering prior. Start with the keys the
ODD singled out (`k_ref`, the mortality-named survival keys, the EIP constants, the
aquatic thresholds), and finish with the naming and unit decisions.

## Index

| # | Item | Note |
|---|---|---|
| 5.1 | The provenance table of every key in `model_constants.yaml` | p.19, p.20, p.22, p.26 |
| 5.2 | `k_ref`: what the 50 means, and its unit | p.30 A.9, p.6, p.4 |
| 5.3 | Completeness of the YAML for the stochasticity constants | p.10 |
| 5.4 | The mortality-named keys are survival keys: rename them | p.30 A.10 |
| 5.5 | The Beverton–Holt form and its parameters | p.21, p.10 |
| 5.6 | The aquatic thresholds (`wash_threshold_mm`, `wash_fraction_max`) | p.20 (document 02) |
| 5.7 | The EIP constants (`base_c`, `threshold_gd`) | p.28 (document 04) |
| 5.8 | Adult daily survival as a function of urban area and hibernation | p.2 (document 08) |

---

## 5.1 The provenance table

**Note (verbatim)** — **p.19**: "Review engineered priors constants" — **p.20**:
"find papers to support these data" — **p.22**: "All of them came from papers. Review."
— **p.26**: "Review papers behind".

**Current state.** The YAML already carries per-key comments with units and, in
several cases, the anchor (for example `adults.daily_mort_basal`, `habitat.egg_daily_mort`
with its "engineering prior (Giglioli no es verificable en papers/)" note, or the
dispersal block's "Costantini 1996 mide 350–650 m/día"). The coverage is uneven:
some keys have an anchor, some have a "[EP]" mark, some have only a unit.

**Decision needed.** Build the table: key → value → anchor (full citation) or
engineering prior (with its tier). The table's home is the ODD's generated parameter
table (`tools/gen_concepts_values.py` already emits it) or a companion file it
reads.

**Done when.** Every key of `model_constants.yaml` appears in the table exactly once,
with either a `papers/REFERENCES.md` row or an explicit `[EP]`/`[NR]` mark, and the
count of engineering priors is stated (that count is the metric the note asks for:
minimise priors, maximise papers).

---

## 5.2 `k_ref`

**Note (verbatim)** — **p.30 A.9**: "parameter to review in detail." — **p.6**: "calibrate
with scientific base k_ref" — **p.4**: "Must be calibrated correctly, if possible with
scientific studies behind supporting the calibration."

**Current state.** `habitat.k_ref = 50.0` is annotated `[ind·km⁻²·d⁻¹]` and consumed
as a **standing count** in `K_gt_habitat = K_REF_GHANA(50) · cell_area_km2 · S`
(`model_constants.yaml:50-51`; the YAML itself notes that a per-species `K_ref` is a
future extension). The unit annotation therefore does not match the use.

**Decision needed.**

1. What does the 50 represent: a capacity of 50 individuals per cell per habitat
   unit? a per-km² density? Fix the annotation to match the use.
2. Is the value a measured capacity for any species in the literature, and if not,
   what makes it 50 (the Beverton–Holt form is scale-free in S, so the number is a
   free scale that has to be pinned by something)?
3. Should it become per-species (`species.<name>.k_ref`), as the YAML comment
   anticipates?

**Done when.** The annotation matches the use, the value has an anchor or an explicit
tier, and the decision on per-species vs global is written down.

---

## 5.3 Completeness of the YAML for the stochasticity constants

**Note (verbatim)** — **p.10**: "Not in yaml?"

**Current state.** The ODD lists the stochastic elements of the model; the YAML
carries the seeds it needs (the `rng:` block) and the redesign retires the three
fixed aquatic seeds in favour of the master seed. But the list of stochastic
processes in the document and the list of constants in the YAML have never been
reconciled.

**Decision needed.** For every stochastic element the ODD names, name the YAML key
that controls it, or state that it is not configurable (and why).

**Done when.** The ODD's stochasticity list and the YAML are in bijection.

---

## 5.4 Rename the mortality-named survival keys

**Note (verbatim)** — **p.30 A.10**: "rename".

**Current state.** The keys are named as mortalities but hold survivals:
`adults.daily_mort_basal = 0.87` (the YAML says: "OJO: las claves `mort_*` son
SUPERVIVENCIA diaria (p_d), no mortalidad"), `adults.mort_cap = 0.93` (the dormant
ceiling), `adults.mort_floor = 0.60`. In C++ they are `ADULT_DAILY_MORT_BASAL`,
`ADULT_MORT_CAP`, `ADULT_MORT_FLOOR`.

**Decision needed.** Rename to survival semantics (`daily_survival_basal`,
`survival_cap`, `survival_floor`) in all three copies (YAML, `config_validation.py`,
`config.hpp`) plus the dump (`config_dump.cpp`), or keep the historical names and
make the warning impossible to miss.

**Done when.** The names and the quantities agree, in all copies, with the golden
configuration dump regenerated.

---

## 5.5 The Beverton–Holt form and its parameters

**Note (verbatim)** — **p.21**: "review theory." — **p.10** (larval competition):
"Must be calibrated."

**Current state.** The contract states the aquatic capacity contract as
`p = s0·K/(K + α·N)` (Beverton–Holt), with `K == 0 ⇒ p = 0`, `k_habitat < 0/NaN/+inf`
or a missing patch → error, and `larva_bh_alpha` finite and ≥ 0 — a contract with no
fallback (the old `K_MAX` fallback was retired).

**Decision needed.** Is the functional form the right one for the density dependence
of the aquatic stages, with the parameters (`larva_bh_alpha`, `s0`) anchored? Does
the `K == 0 ⇒ p = 0` rule deserve a source (it is a strong claim)?

**Done when.** The form, its parameters and the `K == 0` rule each have an anchor or
an explicit prior with tier, and the contract text in the ODD matches.

---

## 5.6 The aquatic thresholds

**Note (verbatim)** — **p.20**: "R<40 → theoretical basis? Review this numbers comes
from the yaml" (`wash_threshold_mm = 40.0`, `wash_fraction_max = 0.60`).

**Decision needed.** See document 02 (aquatic phase) for the *semantics*; here the
provenance: each number gets an anchor or a tier.

**Done when.** Both numbers appear in the provenance table with an anchor or `[EP]`.

---

## 5.7 The EIP constants

**Note (verbatim)** — **p.28**: "find paper support for it." (EIP base 16 °C /
threshold 110 degree-days).

**Decision needed.** The degree-day form (`eip.base_c = 16.0`, `eip.threshold_gd =
110.0`) needs an anchor, and the feasibility question of document 04 needs the
answer to be read against it.

**Done when.** Both constants appear in the provenance table with an anchor or `[EP]`.

---

## 5.8 Adult daily survival as a function of the environment

**Note (verbatim)** — **p.2**: "dependent from urban area, hibernation, temperatures →
fuzzy or formula".

**Current state.** Adult daily survival is `adults.daily_mort_basal = 0.87` (a
constant), clamped between `mort_floor = 0.60` and `mort_cap = 0.93`; the dry-season
response is a separate state (`ARRESTED`) in the redesign, not a survival curve.

**Decision needed.**

1. Should `p_d` be a function of the urban fraction (urban populations have
   different survival), of a hibernation/dormancy state, and of temperature — and if
   so, what shape: a rule ("fuzzy") or a formula?
2. Is the question about the *value* (then it belongs in 5.1) or about the *shape*
   (then it is a model change)?

**Done when.** The question is answered one way or the other, and the answer is
either a row in the provenance table or a change to the survival model.

## Dependencies / open points

- This document is the **prerequisite** of the formal calibration cycle; documents 02,
  03 and 04 change the dynamics and therefore reopen some values.
- The table has to be generated, not typed: the ODD's parameter table is emitted by
  `tools/gen_concepts_values.py` from the YAML, so the table's schema is a natural
  extension of that generator.
- `k_ref` and `beta_urban` are also touched in document 01: one pull request per key,
  so that the calibration history stays readable.
- The renaming in 5.4 touches the same three copies as every other key: apply it
  with the schema bump of document 06 (single source of truth) if that lands first.
