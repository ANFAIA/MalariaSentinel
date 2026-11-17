# 02 — Aquatic phase: desiccation, washout, and the initial development of seeded cohorts

> **Status**: pending (2026-11-17). This document holds **only work that has not been
> done**. The parts already covered by other plans are not repeated here: the
> per-cell registry, the removal of the `patch_id` vocabulary and the mother-position
> payload live in `docs/plans/in-process/individualization-and-movement.md` (§9), and
> the dry-patch freeze semantics are documented there too (§0, invariantes).
> **Source**: ODD 2010 review notes
> (`.cache/odd-latex/odd-2010-malariasentinel-notes.tex`), pack 07.
> **ODD sections to amend when this is applied**: §7.2 "Advance aquatic stages",
> §5.2 "Mosquito seeding".

## Objective

Give the aquatic stress mechanics a defensible definition (how desiccation couples to
capacity and to instars, whether washout can co-occur with desiccation, on what basis
the thresholds are set), and make the initial development of a seeded cohort coherent
with the day it was seeded.

## Index

| # | Question | Note |
|---|---|---|
| 2.1 | Is desiccation connected to the larvae and to `K_{p,d}`? | p.20 |
| 2.2 | The washout threshold (`R < 40`) — what is its theoretical basis? | p.20 |
| 2.3 | Can desiccation and washout happen on the same day? | p.20 |
| 2.4 | A cohort seeded on day Y with stage duration X — should it emerge after X−Y days? | p.4 |
| 2.5 | Is `last_larval_instar = 4` a biological constant or a configuration value? | p.20 |

---

## 2.1 Desiccation: coupling to capacity and to instars

**Note (verbatim)** — **p.20**: "Desiccation disconnected from larvae? Disconnected from
K_{p,d}?"

**Current state.** Desiccation is driven by a **dry-day streak** (`dry_days`) and
targets **eggs and L1–L2 only**; L3, L4 and pupae are frozen, not killed. It is
therefore *not* coupled to `K_{p,d}` (the Beverton–Holt capacity of the patch): the
capacity plays no role in the desiccation rule.

**Decision needed.**

1. Is the streak rule the right mechanism, or should desiccation scale with the
   habitat's own state (the `dry` flag of the cell, the pluvial response `z`)?
2. Should the frozen stages (L3, L4, pupa) be modelled as *surviving* or as *dead
   but not removed*? Today they persist through a dry spell and resume when the
   patch reactivates.
3. What is the source for the desiccation thresholds (streak length, which stages)?

**Done when.** The rule is stated as a formula with its tier and reference, and the
test suite covers the three cases (dry streak inside the grace period, streak beyond
it, reactivation).

---

## 2.2 The washout threshold

**Note (verbatim)** — **p.20**: "R<40 → theoretical basis? Review this numbers comes
from the yaml".

**Current state.** `habitat.wash_threshold_mm = 40.0` (daily rainfall that triggers
the washout of cohorts) and `habitat.wash_fraction_max = 0.60` (maximum fraction of
cohorts washed out by rain), both in `model_constants.yaml:38-39` — the YAML is
already the single source, but the numbers have no anchor.

**Decision needed.** What is the published basis for both numbers, and are they two
parameters or one (a threshold and its consequence)? If no source exists, they become
engineering priors with an explicit tier.

**Done when.** Each number has either an anchor in `papers/REFERENCES.md` or an
explicit `[EP]` mark, and the interaction with 2.3 is specified.

---

## 2.3 Can desiccation and washout co-occur?

**Note (verbatim)** — **p.20**: "can't happen both" *(desiccation and washout)*.

**Decision needed.** Fix the order or the exclusivity of the two daily processes:
does a heavy rain event (washout) reset the dry streak (and thus prevent
desiccation), or do both apply on the same day in a fixed order? Today the two are
independent rules evaluated on the same day.

**Done when.** The daily order of the aquatic processes is written down (the ODD's
§7.2 already has a process order) and the interaction is one sentence in it.

---

## 2.4 Initial development fractions of a seeded cohort

**Note (verbatim)** — **p.4** (aquatic cohorts): "if it takes X days and added on day
Y, where Y ≤ X, could those individuals take X−Y days to emerge?"

**Current state.** Seeding splits an adult population into aquatic cohorts with
**preset development fractions** — `0.58` (pupa), `0.47` (L4), `0.38` (L3), `0.29`
(L2), plus `0.20` (L1) and `0.00` (eggs) — at `mosquito_submodel.cpp:402-415`. The
fraction is the progress already made within the stage, so the cohort has a
development *duration* measured from the day it was seeded, not from a biological
origin.

**Decision needed.** Is a seeded cohort "already `f` of the way through the stage" (a
snapshot of a population that has been developing for a while), or "at the start of
the stage, with the clock already running"? The first reading is defensible for
warming up a run; the second makes `X−Y` meaningful. It also interacts with the
single master seed (the aquatic stream now derives from it) and with the fact that
seeding changes only warm-up speed, not the adult equilibrium.

**Done when.** The semantics of the seeded fractions is written down, and the
scenarios that depend on it (the synthetic harness) use the same reading.

---

## 2.5 `last_larval_instar`

**Note (verbatim)** — **p.20**: "Theoretical number or mosquito config."

**Current state.** `habitat.last_larval_instar = 4` (`model_constants.yaml:273`),
i.e. L4 is the last larval instar (the species has four larval instars before the
pupa). It is a per-**species** biological fact, but it lives as a global key under
`habitat:`.

**Decision needed.** Move it into the per-species block (`species.<name>.last_larval_instar`)
with the citation for the four-instar life cycle, or keep it global and cite the
species it applies to.

**Done when.** The key lives where the rest of the species facts live, in all three
copies (YAML, `config_validation.py`, `config.hpp`), with its reference.

## Dependencies / open points

- The provenance of the numeric thresholds belongs to document 05
  (parameters and calibration): decide the values there, cite them here.
- Changing the aquatic dynamics shifts the calibration baseline — rerun the scorers.
- 2.4 interacts with the seeding changes of
  `docs/plans/in-process/individualization-and-movement.md` (§13.3, individual
  seeding): if seeding becomes per-individual, the preset fractions may be replaced
  by explicit per-cohort development.
