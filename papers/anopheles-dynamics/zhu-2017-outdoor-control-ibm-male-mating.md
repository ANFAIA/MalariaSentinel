# Is outdoor vector control needed for malaria elimination? — a spatial IBM that simulates males but assumes mating succeeds

**Authors:** Zhu C, Müller C, Marshall C, Arheart KL, Qualls J, Hlaing MY, Schlein A, Traore SF, et al.
**Journal:** Malaria Journal | **Year:** 2017 (16:266) | **DOI:** 10.1186/s12936-017-1920-y
**File:** papers/anopheles-dynamics/zhu-2017-outdoor-control-ibm-male-mating.md

---

## Abstract (summary)

A spatial individual-based model of *Anopheles gambiae* and humans in a
600 × 600 m African village (25 houses, 50 sugar sources, 50 outdoor resting sites,
50 larval habitats, 100 humans), used to compare LLIN coverage, attractive toxic
sugar baits (ATSB) and their combination over intervention efficacy periods of
30–180 days, and to estimate the probability of local mosquito extinction and the
annual entomological inoculation rate (EIR).

## Key Results (as used by the model)

- **Males ARE simulated, but only as a shadow population.** "**Male mosquitoes were
  simulated in ten repetitions and followed similar population dynamic patterns as
  females, so they were not included in the results.**" The male module exists
  because ATSB kills males: "ATSB can also target male *An. gambiae* mosquitoes
  because males solely feed on sugar for energy and **they require at least two sugar
  meals per night**."
- **Mating has no dynamics — mating always succeeds.** "**Successful mating was
  assumed in the model**, if mating opportunity was taken into account, outdoor ATSB
  intervention may have even better vector control results." The authors then state
  the counterfactual explicitly: "as outdoor ATSBs killed more male mosquitoes, **it
  would reduce the mating opportunities for females, which would either lead to lower
  mosquito reproduction or additional flights for females and hence increased
  mortality**."
- **Baseline:** female population equilibrates at **~400** mosquitoes in the 600 × 600 m
  village; annual EIR equilibrates at **~200 infectious bites per person per year**;
  with 50 % LLIN coverage the population falls to 2–193 and annual EIR to 0–4.
- Other fixed parameters: max lifespan **30 days**, EIP **10 days**, 20 % chance of
  infection per bite, humans protected by LLINs between 23:00 and morning; mosquitoes
  active 19:00–05:00; 50 repetitions per scenario.

## Relevance to MalariaSentinel (Centinela)

This paper is the clearest published statement of the **gap that the male decision
closes**. It simulates males, kills them with a realistic intervention, and then
cannot translate male mortality into transmission, because mating is a free assumption.
It also names the two distinct epidemiological mechanisms a male module would have to
choose between:

1. **fertilisation limitation** → lower mosquito reproduction (fewer eggs laid);
2. **search-cost limitation** → females that fail to mate must search longer / fly
   more → higher female mortality (a *mortality* channel, not a *fertility* channel).

Both are absent from the Centinela today (mating is instantaneous, and the sex ratio
is a fixed Bernoulli(0.5) draw), and both are absent from every malaria ABM reviewed
here.

**Caveats:** *An. gambiae*, hypothetical village, no parasite dynamics (EIR is an
index), no insecticide resistance; the model is a demonstration platform, not a
calibrated model of any real village.

## License

CC BY 4.0 (© The Author(s) 2017; Malaria Journal, BMC open access).
Open-access copy: https://pmc.ncbi.nlm.nih.gov/articles/PMC5496196/
