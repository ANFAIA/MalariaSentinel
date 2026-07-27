# Effects of elevated temperatures on the development of immature stages of Anopheles gambiae (s.l.) mosquitoes

**Authors:** Thomas Peprah Agyekum, John Arko-Mensah, Paul K. Botwe, Jonathan N. Hogarh, Ibrahim Issah, Duah Dwomoh, et al.
**Journal:** Tropical Medicine & International Health | **Year:** 2022 | **DOI:** 10.1111/tmi.13732
**File:** papers/anopheles-dynamics/agyekum-2022-anopheles-gambiae-ghana-temperature.md

---

## Abstract

This study investigated the effects of temperature on the development of the immature stages of *An. gambiae* (s.l.) mosquitoes in **Ghanaian laboratory conditions**. Methods: Mosquito eggs were obtained from laboratory-established colonies and reared under eight temperature regimes (25, 28, 30, 32, 34, 36, 38 and 40 °C), and 80 ± 10 % relative humidity. Larvae were checked daily for development to the next stage and for mortality. Pupation success, number of adults produced, and sex ratio of the newly emerged adults were recorded. **Increasing the temperature from 25 to 36 °C decreased the development time by 10.57 days.** Larval survival and the number of adults produced decreased with increasing temperature. Increasing temperatures also resulted in significantly smaller larvae and pupae. At higher temperatures disproportionately more male than female mosquitoes were produced.

## Methods

- **Species:** *Anopheles gambiae* sensu lato (Ghanaian colony, maintained at the African Regional Postgraduate Program in Insect Science — University of Ghana).
- **Site:** Laboratory rearing at the University of Ghana.
- **Temperature regimes:** 25, 28, 30, 32, 34, 36, 38, 40 °C; 80 ± 10 % RH; 12:12 photoperiod.
- **Density:** 160 L1 larvae per bowl; 1 L dechlorinated water; daily feeding with 10 mg TetraFin goldfish flakes.
- **Measurements:** Daily stage-transition check (L1 → L2 → L3 → L4 → pupa → adult), mortality, pupation success, adult emergence count, sex ratio.
- **Analysis:** Kaplan-Meier survival analysis; one-way ANOVA for normally-distributed variables; Kruskal-Wallis for non-parametric.

## Key Results

| Temperature (°C) | Mean development time (days ± SD) | Pupation success (%) |
|---|---|---|
| **25** | **20.17 ± 0.75** | 53.75 |
| 28 | 18.40 ± 0.89 | 75.00 |
| 30 | 16.08 ± 1.03 | 34.38 |
| 32 | 14.54 ± 0.38 | 28.13 |
| 34 | 13.01 ± 0.61 | 24.38 |
| 36 | 9.60 ± 0.55 | 22.50 |
| 38, 40 | No adult emergence | — |

- **At 25 °C:** Development time from egg to adult = **20.17 days** (Ghanaian strain).
- **Temperature decrease in development time (25 → 36 °C):** **10.57 days**.
- **Optimal emergence (survival):** 28 °C (75 % pupation success).
- **Sex ratio:** Skewed toward males at higher temperatures (implications for vector control).

## Relevance to MalariaSentinel (Centinela)

**This is the most directly relevant paper for the Centinela** because it provides Ghanaian experimental data — not just a model extrapolation from elsewhere. Key implications:

1. **At 25 °C (typical Ghana median temperature), total egg-to-adult development takes ~20 days** — within the 13–20 day range established by Bayoh & Lindsay 2003 (13–16 d) and Ouédraogo 2024 (11.87 d in August conditions, Burkina Faso).

2. **The Centinela's current `LARVA_A = 0.00052` produces 34 days at 25 °C** — **70 % too slow** compared to Ghanaian experimental data. Recalibrating `LARVA_A ≈ 0.001` produces ~17.6 days, matching this paper's measurement.

3. **Pupation success at 25 °C is 53.75 %** — implying that even under optimal conditions, only ~half of larvae successfully pupate. The Centinela's Beverton-Holt larval mortality (LARVA_BH_S0 = 0.95) may be **too generous** at low densities; field conditions include additional predation and desiccation mortality.

4. **Optimal temperature for the Ghanaian strain is 28 °C (75 % pupation success), not 25 °C.** The thermal optimum may be slightly higher in West African populations than the 25 °C peak reported in Bayoh & Lindsay's UK-colony data.

5. **Sex ratio skew at high temperatures** has implications for gene-drive interventions (M7+ roadmap, Selvaraj 2020).

## Limitations

- Single Ghanaian colony; population variation across Ghana's ecological zones not characterised.
- Laboratory conditions (constant temperature, no predation, controlled food) — field conditions include density-dependent mortality, predation, and diurnal temperature fluctuation.
- Eggs obtained from "laboratory established colonies" — these may have adapted to lab conditions over multiple generations.
- The paper does not measure gonotrophic cycle or adult survival — only immature stages.

## Future Directions

- Validate the Centinela's Ghana ABM thermal parameters against this experimental data (specifically: recalibrate `LARVA_A` from 0.00052 to ~0.001 to match 20-day development at 25 °C).
- Couple to field MRR studies from Ghana (currently absent) for survival and dispersal validation.
- Test sensitivity to diurnal temperature range (DTR) effects flagged by Mordecai 2013.

## References

- Agyekum TP, Arko-Mensah J, Botwe PK, Hogarh JN, Issah I, Dwomoh D, et al. (2022). Effects of elevated temperatures on the development of immature stages of *Anopheles gambiae* (s.l.) mosquitoes. *Tropical Medicine & International Health*, 27(4): 338–346. doi:10.1111/tmi.13732
- Bayoh MN, Lindsay SW (2003). Effect of temperature on the development of the aquatic stages of *Anopheles gambiae* sensu stricto. *Bulletin of Entomological Research*, 93(5): 375–381.
- Ouédraogo et al. (2024). *Anopheles* aquatic development kinetic and adults' longevity through different seasons in laboratory and semi-field conditions in Burkina Faso. *Parasites & Vectors*.