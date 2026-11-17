# Age and body size effects on blood meal size and multiple blood feeding by *Aedes aegypti* (Diptera: Culicidae)

**Authors:** Ruilin D. Xue, John D. Edman, Thomas W. Scott
**Journal:** Journal of Medical Entomology | **Year:** 1995 | **DOI:** 10.1093/jmedent/32.4.471
**File:** papers/anopheles-dynamics/xue-edman-scott-1995-blood-meal-size-thresholds-multiple-feeding-aedes.md

---

## Abstract (summary)

Laboratory study combining (a) blood-meal-size manipulations to measure the threshold
above which a female stops seeking hosts, and (b) the threshold of blood-meal size needed
to initiate egg development, as a function of female age and body size, plus (c) a
radio-isotope (rubidium/cesium) host-marking experiment measuring the frequency of
multiple blood feeding.

## Key Results (as used by the model)

- "Ten-day-old, parous *Aedes aegypti* had a **higher threshold of blood meal size for the
  inhibition of continued host-seeking** than did 5-day-old, nulliparous females of the
  same size."
- "Older females of a **smaller-bodied** cohort had a **higher threshold of blood meal size
  for the initiation of egg development** than did younger females. In contrast, **older
  larger-sized females had a lower blood meal-size threshold for egg development**."
  → two *distinct* thresholds (host-seeking inhibition vs. egg-development initiation)
  that depend on age and body size — a direct argument for two separate YAML keys
  (`meal_size_min_ul` vs `blood_meal_target_ul`) rather than one.
- "The blood of paired avian hosts was marked with rubidium and cesium to study the effect
  of age and body size on the frequency of multiple blood feeding. **Chronologically old
  females had a higher frequency of multiple blood feeding** than younger females."
- "In the laboratory, the frequency of multiple blood feeding among **larger-sized females
  was higher** than among small-sized females."

## Relevance to MalariaSentinel (Centinela)

This is the key conceptual source for splitting the physiology into two thresholds: a
*behavioural* threshold (stop looking for hosts) and a *physiological* threshold (start
maturing eggs), and for making both size- and age-dependent. It also shows that
multiple feeding is not a uniform trait of the population (older, larger females feed
multiplicatively more often), which argues for an explicit per-female heterogeneity
mechanism rather than a single expected value.

Caveats: *Aedes aegypti* (proxy species), laboratory, 1995; the abstract gives no absolute
µL values for the thresholds, only their ordering with age/size, so it cannot be used to
set numbers — only the structure.

## License

© Oxford University Press, *Journal of Medical Entomology* (not open access; abstract read
via Europe PMC). Fair use for academic research.
