# MBITES (Wu et al. 2020) — a framework with a male module that the published paper switches off

**Authors:** Wu S-L, Sánchez CHM, Henry JM, Citron DT, Zhang Q, Compton K, Liang B, Verma A, Cummings DAT, Le Menach A, Scott TW, Wilson AL, Lindsay SW, Moyes CL, Hancock PA, Russell TL, Burkot TR, Marshall JM, Kiware S, Reiner RC Jr, Smith DL
**Journal:** PLoS Computational Biology | **Year:** 2020 (16(4):e1007446) | **DOI:** 10.1371/journal.pcbi.1007446
**File:** papers/anopheles-dynamics/wu-2020-mbitses-males-and-mating-states.md

> Companion extract (blood-feeding / egg-batch algorithms):
> `wu-2020-mbitses-vector-bionomics-emergent-properties.md`. This file records only
> what the MBITES paper says about **males and mating**.

---

## Abstract (summary)

MBITES (Mosquito Bout-based and Individual-based Transmission Ecology Simulator)
represents adult mosquitoes as sequences of activity bouts with explicit state
transitions, coupled to a companion ODE model, and shows that classical
Ross–Macdonald bionomics (including the blood-feeding rate) *emerge* from behavioural
algorithms interacting with resource landscapes.

## Key Results (as used by the model)

- **The framework has a male component.** "**MBITES is capable of modeling both female
  and male mosquito populations and behavior.**"
- **The published applications turn males off.** "**In this manuscript, male
  mosquitoes are not considered and the optional behavioral states of sugar feeding and
  mating and all associated variables have been turned off** in order to introduce and
  focus on algorithms describing blood feeding and egg laying by females."
- **Males would make the framework unusual.** "Additionally, a model allowing for
  heterogeneity in individual mosquitoes and **modelling both male and female
  mosquitoes is really unique.**"
- The female-side algorithms (which the Centinela already mirrors) are: stochastic
  blood-meal size; an accumulation target for blood provision that may require
  several meals; re-feeding probability as a function of the size of the previous
  meal or the previous egg batch; three oogenesis variants (phenomenological Gaussian,
  semi-mechanistic linear proportionality, replacement); infection evaluated at each
  meal; optional "overfeeding" mortality as an increasing function of meal size.

## Relevance to MalariaSentinel (Centinela)

MBITES is the strongest **engineering precedent for a male module that is switched on
per use case**: the framework already contains the male and mating states, so the
Centinela's decision (A vs B) is a decision about *which* states to activate, not
about building a framework from scratch. It also shows that the mainstream
vector-modelling community treats male/mating behaviour as **optional detail to be
switched off when the question is transmission** — a fact the Centinela must either
accept (option A) or deliberately depart from (option B), with the departure justified
by the biology rather than by taste.

**Caveats:** the numbers MBITES reports for *An. gambiae* are simulation outputs, not
primary measurements; MBITES has no spatial mosquito movement, no swarms, and no
parasite/human transmission module.

## License

CC BY 4.0 (© 2020 Wu et al; PLoS Computational Biology open access).
Open-access copy: https://pmc.ncbi.nlm.nih.gov/articles/PMC7197866/
