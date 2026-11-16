# Once bitten, twice shy: A modeling framework for incorporating heterogeneous mosquito biting into transmission models

**Authors:** Kevin J. Dahlin, Madison A. Robert, Leah M. Childs
**Journal:** Bulletin of Mathematical Biology | **Year:** 2025 | **DOI:** 10.1007/s11538-025-01540-z
**File:** papers/anopheles-dynamics/dahlin-2025-heterogeneous-mosquito-biting-transmission-framework.md

---

## Abstract (summary)

A general mathematical framework for transmission models in which mosquitoes may bite more
than once per reproductive (gonotrophic) cycle. The framework yields explicit formulas for
the basic offspring number *N0* and the basic reproduction number *R0* under several
biting-process assumptions (empirical, phenomenological, mechanistic), and relates them
to the gonotrophic cycle duration (GCD).

## Key Results (as used by the model)

- "standard models of mosquito-borne disease transmission inherently assume that **mosquitoes
  bite only once per reproductive cycle — an assumption commonly violated in nature**."
- "Drivers of multiple biting, such as **host defensive behaviors or climate factors**,
  also affect the mosquito gonotrophic cycle duration (GCD), a quantity customarily used to
  estimate the biting rate." → the coupling between multi-biting and the biting rate is
  not an assumption but a modelled link; in the engine, `cycle_duration_days` and the
  multi-meal mechanism are currently independent and should not be.
- "Using the gonotrophic cycle duration as a standard quantity to make comparisons among
  the models, we show that **assumptions about the biting process strongly affect the
  relationship between GCD and *R0***. While under the standard assumption of one bite per
  reproductive cycle, *R0* is an increasing linear function of the inverse of the GCD,
  alternative models of the biting process can exhibit **saturating or concave
  relationships**. Critically, from a mechanistic perspective, **decreases in the GCD can
  lead to substantial decreases in *R0***."
- "Through sensitivity analysis of the mechanistic model, we determine that **parameters
  related to probing and ingesting success are the most important targets for disease
  control**."
- "Drivers of multiple biting, such as host defensive behaviors or climate factors" — the
  mechanistic model explicitly contains separate probing and ingesting success
  probabilities, i.e. *two* distinct failure modes for a feeding attempt.

## Relevance to MalariaSentinel (Centinela)

Shows that switching the engine from "one bite per cycle" to a multi-bite model changes
the *sign* of the relationship between cycle duration and transmission — so the redesign
cannot be validated by re-tuning `cycle_duration_days` alone. Also identifies
"probing success" and "ingesting success" as separate parameters, which supports splitting
the current single `feeding_success_rate` into at least two (attempt → engorge → reach
target).

Caveats: analytical framework, no new primary data; the numbers it uses for probing /
ingesting success are illustrative, and the paper is not specific to *Anopheles coluzzii*
or to Ghana.

## License

CC-BY 4.0 (Bulletin of Mathematical Biology open access).
