# 'A mate or a meal' — pre-gravid behaviour of female *Anopheles gambiae* from the islands of São Tomé and Príncipe, West Africa

**Authors:** J. D. Charlwood, J. Pinto, C. A. Sousa, C. Ferreira, V. Petrarca, V. do E. Rosario
**Journal:** Malaria Journal | **Year:** 2003 | **DOI:** 10.1186/1475-2875-2-9
**File:** papers/anopheles-dynamics/charlwood-2003-mate-or-a-meal-pre-gravid-anopheles-gambiae.md

---

## Abstract (summary)

Field and laboratory study of *Anopheles gambiae* on São Tomé and Príncipe (the only
vector on the islands) during the **first** gonotrophic cycle. It measures survival,
sporozoite rate, mating order relative to first feeding, and describes the "pre-gravid"
behaviour in which a female feeds but does not yet mature eggs.

## Key Results (as used by the model)

- "**Anophelines generally feed just once per gonotrophic (oviposition) cycle. Newly
  emerged insects, however, may feed two or more times during their first oviposition
  cycle** thus increasing the likelihood of becoming infected."
  → explicit statement that the **first** cycle is the multi-meal case, consistent with
  `briegel-horler-1993-…` and `takken-2024-…`.
- "The reasons for multiple feeding are not clearly understood and it is still uncertain
  whether the behaviour is **facultative or obligatory**."
- "**All newly emerged insects blood fed on the second night following emergence but only
  became gonotrophically active on the third night after emergence.**"
  → the first blood meal and the start of the gonotrophic cycle are **decoupled in time**
  (a one-night lag); this is the "pre-gravid" state.
- "We suggest that **insufficiency of Juvenile Hormone until the third day of adult life**
  is responsible for gonotrophic inactivity" → the physiological reason the first meal
  does not immediately start oogenesis.
- "**Overall 49 % of females mated on the second night after emergence before feeding, and
  51 % on the third night and thus fed before mating.** The likelihood of mating before
  feeding increased with wing size."
- "Estimated survival rates ranged between **0.834–0.849 per day** in São Tomé and
  **0.801–0.818 per day** in Príncipe."
- "Parous insects were **gonotrophically concordant**." → the multi-meal behaviour is
  concentrated in the first cycle; later cycles are concordant.

## Relevance to MalariaSentinel (Centinela)

Justifies a **first-cycle / pre-gravid branch** in the redesigned state machine: after
emergence the female may take two or more meals before the gonotrophic cycle starts, and
this first cycle is also the one with the highest probability of acquiring infection
(because it involves extra host contacts). The engine already has a separate
`first_cycle_days` (4.0 d) vs `cycle_duration_days` (2.0 d); this paper says the first
cycle is *not* just slower, it is *multi-meal*.

Caveats: São Tomé and Príncipe (West African *An. gambiae* in a different, island
setting — a useful `gambiae` s.l. proxy but not Ghana), 2003, and the paper measures
survival and mating order rather than blood volumes.

## License

Open access (Malaria Journal / BMC); CC-BY.
