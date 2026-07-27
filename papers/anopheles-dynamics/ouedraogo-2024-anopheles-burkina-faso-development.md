# Anopheles aquatic development kinetic and adults' longevity through different seasons in laboratory and semi-field conditions in Burkina Faso

**Authors:** [Ouédraogo et al.]
**Journal:** Parasites & Vectors | **Year:** 2024 | **DOI:** 10.1186/s13071-024-06260-2
**File:** papers/anopheles-dynamics/ouedraogo-2024-anopheles-burkina-faso-development.md

---

## Abstract

Environmental conditions were simulated in the laboratory using incubators to mimic the environmental conditions of two important periods of the year in Burkina Faso: the peak of rainy season (August) and the onset of dry season (December). Eggs from wild *An. coluzzii* and *An. gambiae* s.l. were reared separately under each environmental condition. Four replicates were carried out for this experiment. Then, egg hatching rate, pupation rate, larval development time, larva-to-pupae development time, adult emergence dynamics and longevity of *Anopheles* were evaluated. Also, pupae-to-adult development time from wild L3 and L4 *Anopheles* larvae was estimated under semi-field conditions in December. **Larval development time and longevity of *An. gambiae* s.l. female were significantly longer at the onset of the dry season compared than at the peak of the rainy season.** Adult emergence was spread over 48 and 96 h at the peak of the rainy season and onset of dry season conditions respectively.

## Methods

- **Species:** Wild *Anopheles coluzzii* and *Anopheles gambiae* s.l. collected from Bama village, Burkina Faso (IRSS research site).
- **Conditions:** Simulated August (rainy season peak, 24.5–28.5 °C, 76–80 % RH) and December (dry season onset) in laboratory incubators.
- **Semi-field validation:** Malaria-sphere enclosure in Bama village for December pupae-to-adult validation.
- **Analysis:** Kaplan-Meier survival analysis; GLMM (binomial errors, logit link) for proportion outcomes; Wilcoxon Mann-Whitney for development time; Cox regression for adult survival.

## Key Results

- **Larval development time L1 → pupation (August conditions, 24.5–28.5 °C):** **11.87 ± 0.12 days** (median; mean 11.87 ± 0.12 d).
- **Larval development time (December conditions):** **13.82 ± 0.15 days** (significantly longer).
- ***An. gambiae* s.l. specifically (August):** 11.98 ± 0.16 days.
- **First pupae appearance:** Day 7 (August) vs day 11 (December).
- **Pupae-to-adult emergence spread:** 48 h (August) vs 96 h (December).
- **Adult longevity:** Significantly longer in December (cooler, less predation pressure).
- **Optimal conditions:** 24.5–28.5 °C and 76–80 % RH — consistent with Bayoh & Lindsay 2003 optimum.

## Relevance to MalariaSentinel (Centinela)

This paper provides **independent confirmation** of the Bayoh & Lindsay 2003 development rates under semi-field conditions in **West African savanna** — ecologically the closest analog to northern Ghana. Key findings:

1. **At 24.5–28.5 °C (August peak rainy season, Bama, Burkina Faso), total L1-to-pupation takes ~12 days.** This is **even faster than Bayoh & Lindsay's 13–16 days** at 25 °C, and **dramatically faster than the Centinela's current 34 days**.

2. **Pupae-to-adult emergence is rapid (48 h in August)** — consistent with the Brière pupa development rate in `thermal_responses.hpp`.

3. **Seasonal variation matters:** Cooler dry-season conditions (December) extend development to ~14 days. The Centinela's thermal response should capture this naturally (lower T → lower rate → longer development).

4. **Validation pipeline:** The combination of Agyekum 2022 (Ghana, 20 d at 25 °C lab), Ouédraogo 2024 (Burkina Faso, 12 d at 24.5–28.5 °C semi-field), and Bayoh & Lindsay 2003 (UK lab, 13–16 d at 25 °C) converges on **12–20 days** for total egg-to-adult development in West African *An. gambiae* populations. The Centinela's 34 days is **out of range**.

## Limitations

- Single Burkina Faso site; not directly Ghana data.
- "Wild" mosquitoes were collected and reared in incubators — partial lab adaptation.
- Focus on L1 → pupation time; egg-to-L1 hatching and pupa-to-adult durations reported separately.
- December semi-field data was collected from a single month — limited temporal replication.

## Future Directions

- Compare with Ghanaian field-collected colonies (Agyekum 2022 was lab colony; field validation needed).
- Couple development time measurements with adult survival estimates (the Centinela's `ADULT_DAILY_MORT_BASAL`).
- Extend to insecticide-resistant populations (resistance carries fitness costs that may alter development time).
- Validate the Centinela's `LARVA_A` calibration against the 12-day Burkina Faso data point.

## References

- Ouédraogo et al. (2024). *Anopheles* aquatic development kinetic and adults' longevity through different seasons in laboratory and semi-field conditions in Burkina Faso. *Parasites & Vectors*, 17: Article 162. doi:10.1186/s13071-024-06260-2
- Bayoh MN, Lindsay SW (2003). Effect of temperature on the development of the aquatic stages of *Anopheles gambiae* sensu stricto. *Bulletin of Entomological Research*, 93(5): 375–381.
- Agyekum TP et al. (2022). Effects of elevated temperatures on the development of immature stages of *Anopheles gambiae* (s.l.) mosquitoes. *Tropical Medicine & International Health*, 27(4): 338–346.
- Holstein MH (1954). Biology of *Anopheles gambiae* in West Africa. WHO monograph.