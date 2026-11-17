# 03 — Vector behaviour: dispersal kernel, starvation, fauna as a cue, gonotrophic timings

> **Status**: pending (2026-11-17). This document holds **only work that has not been
> done**. The movement law itself — the four-tranche sensory cascade, the two-band
> micro-integrator, the per-species radii and speeds, the multipicadura and probing
> machine, the mating layer and the dry-season arrest — is designed in
> `docs/plans/in-process/individualization-and-movement.md` (§4, §5, §6, §7, §8, §12)
> and is not repeated here.
> **Source**: ODD 2010 review notes
> (`.cache/odd-latex/odd-2010-malariasentinel-notes.tex`), packs 03 and 04.
> **ODD sections to amend when this is applied**: §4.7 "Sensing", §4.8 "Interaction",
> §5.4 "Randomness and reproducibility", §7.4 "Run the gonotrophic cycle",
> §7.6 "Seek hosts and feed", §7.7 "Disperse adults".

## Objective

Close the four decisions the movement redesign left open: the shape of the local
dispersal kernel, the starvation rule under partial feeding, the role of the fauna as
a low-grade attractant, and the durations of the gonotrophic state machine (fixed
today, environment-independent).

## Index

| # | Question | Note |
|---|---|---|
| 3.1 | What is the shape of the local dispersal kernel? | p.9, p.24 |
| 3.2 | Is the 7-day starvation rule right under partial feeding? | p.6 |
| 3.3 | Should the fauna act as a low pheromone over the whole area? | p.17 |
| 3.4 | Are the fixed gonotrophic durations (2.0 / 4.0 / 0.5 days) right? | p.22 |

---

## 3.1 The shape of the local dispersal kernel

**Note (verbatim)** — **p.9**: "Review its possible deletion for simplification" —
**p.24**: "the gaussian kernel of displacement … review its possible deletion for
simplification".

**Current state.** The adult displacement is a Gaussian step with
`dispersal.adult_sigma_m = 450.0` m and a cap `dispersal.adult_max_m = 2000.0` m
(`model_constants.yaml`), applied with probability `dispersal.adult_prob_day = 0.05`
per day. The YAML already records the tension: Costantini 1996 measures 350–650 m/day
(so 450 is a conservative prior *inside* the range) and Thomas 2013 gives p95 = 1.67 km
(exponential) or 2.83 km (half-Cauchy), so the 2 km cap is a compromise, not a p95.
The movement redesign retires the *cell-to-cell jump* as a mechanism but keeps a daily
movement capacity (its own open question, Q-B).

**Decision needed.**

1. Which shape: Gaussian, exponential (median 386 m, p90 1.28 km) or half-Cauchy
   (median 295 m, p90 1.64 km, p95 2.83 km)? The published data are **quantiles
   only** (FR50/FR90), so no source discriminates the tails — this is a design
   decision that must be declared as such.
2. Or: drop the kernel and use a hard exploration radius, consistent with the
   measured post-emergence permanence (< 60 % of *arabiensis* adults move further
   than 50 m from the larval site) that the redesign uses to cap the exploration
   range.

**Done when.** Either the kernel is replaced by a declared shape with its
consequences on the tail recorded (the redesign's sensitivity band), or the
displacement is removed from the configuration and the ODD's §7.7 says so.

---

## 3.2 The starvation rule

**Note (verbatim)** — **p.6**: "without knowing if hosts are not ABMs".

**Current state.** `host_seeking.starvation_days = 7` (maximum days without a host
before dying), consumed as `HOST_SEEKING_STARVATION_DAYS()` in `wire.hpp`. Under the
new regime the female is an individual that can take **partial** meals and returns to
`HOST_SEEKING` the same night, with its own clock (`days_since_target_reached`,
which does not reset on partial meals).

**Decision needed.**

1. Does the seven-day clock run from the last **attempt** or from the last
   **completed** meal? Under partial feeding the two differ, and the redesign's
   starvation clock is explicitly "not restarted by partial meals".
2. Is 7 days defensible? What is the published starvation/maximum-lifetime figure
   for the species, and is the value a prior or a measurement?

**Done when.** The clock's origin is stated in the ODD, the value has a tier and a
reference, and the test suite covers the partial-meal case.

---

## 3.3 The fauna as a low-grade attractant

**Note (verbatim)** — **p.17**: "Think of it as a low pheromone in whole area → if human
around → more attraction depending on species (natural behavior)".

**Current state.** The prey choice is per individual (roulette over species
preference plus distance), and the fauna is one of the prey types; there is **no**
area-wide low-grade attractant field. The species rows do carry a preference for
livestock and the host landscape contributes `indoor_attraction_add` and
`urbanicity_add` to the attraction kernel.

**Decision needed.** Is there a mechanism in which the presence of animals raises
the mosquito's activity over a whole area (i.e. an area-wide cue with a small
amplitude), as opposed to a per-individual prey choice? If yes, what is its
amplitude, its spatial extent and its species weighting — and is it compatible with
the redesign's decision that the cell is no longer a decision unit (it would have to
be a *cue*, not a *target*)?

**Done when.** Either the mechanism is specified with a published anchor, or the ODD
records it as an explicit limit of the model (the redesign's N-list already records
such limits).

---

## 3.4 The durations of the gonotrophic state machine

**Note (verbatim)** — **p.22**: "Review timings, seems fixed dates, when its mortality
is based on environment, the rest is not? This behavior limit oviposition and blood
feeding".

**Current state.** The durations are constants:

| Key | Value | Meaning |
|---|---|---|
| `gonotrophic.cycle_duration_days` | 2.0 | maturation after the first cycle (ceil) |
| `gonotrophic.first_cycle_days` | 4.0 | maturation of the first cycle (ceil) |
| `gonotrophic.resting_duration_days` | 0.5 | BLOOD_FED→RESTING (int rounding) |

The redesign sets the post-prandial window explicitly and moves the dry-season
response to `ARRESTED` (an arrest, not a death), but it does **not** decide whether
ovarian maturation and cycle duration should be **functions of temperature** instead
of constants. The model already has a thermal layer
(`mal-core/src/mal_core/abm/include/mal_abm_fast/thermal_responses.hpp`), which is
where a duration response would live if it were adopted.

**Decision needed.**

1. Do the durations become temperature-dependent (which form?), or stay constant?
2. If they become functions, the YAML schema changes type for three keys (schema
   version 3), and the three copies (YAML, `config_validation.py`, `config.hpp`) plus
   the dump (`config_dump.cpp`) change together.
3. What happens to the synthetic scenarios that assert the cycle timing (E2, E4, E5,
   E6 in the redesign's Appendix A)?

**Done when.** The three durations have a stated functional form (or a stated reason
for staying constant), a tier and a reference, and the scenarios are updated.

## Dependencies / open points

- All four points touch the same machinery the redesign replaces: apply them **after**
  `docs/plans/in-process/individualization-and-movement.md` (steps 4 and 10), or in
  the same pull request.
- 3.1 and 3.4 change configuration keys → schema bump → the Python/C++ parity test and
  the golden configuration dump are regenerated in the same pull request.
- 3.2 and 3.3 change the vector's behaviour → the calibration scorers are recalibrated
  (the redesign's step 10).
- Removing the dead `multirate_scheduler` is **not** here: it is with the other
  engine-hygiene work (document 07).
