# Effect of temperature on the development of the aquatic stages of Anopheles gambiae sensu stricto (Diptera: Culicidae)

**Authors:** M. Nabie Bayoh, Steve W. Lindsay
**Journal:** Bulletin of Entomological Research | **Year:** 2003 | **DOI:** 10.1079/BER2003259
**File:** papers/anopheles-dynamics/bayoh-lindsay-2003-anopheles-gambiae-development-temperature.md

---

## Abstract

Global warming may affect the future pattern of many arthropod-borne diseases, yet the relationship between temperature and development has been poorly described for many key vectors. Here the development of the aquatic stages of Africa's principal malaria vector, *Anopheles gambiae* s.s. Giles, is described at different temperatures. Development time from egg to adult was measured under laboratory conditions at constant temperatures between 10 and 40 °C. Rate of development from one immature stage to the next increased at higher temperatures to a peak around 28 °C and then declined. Adult development rate was greatest between 28 and 32 °C, although adult emergence was highest between 22 and 26 °C. No adults emerged below 18 °C or above 34 °C. Non-linear models were used to describe the relationship between developmental rate and temperature, which could be used for developing process-based models of malaria transmission. The utility of these findings is demonstrated by showing that a map where the climate is suitable for the development of aquatic stages of *A. gambiae* s.s. corresponded closely with the best map of malaria risk currently available for Africa.

## Methods

- **Species:** *Anopheles gambiae* sensu stricto (Giles), the principal African malaria vector.
- **Experimental design:** Mosquitoes reared under 8 constant temperature regimes (10–40 °C in 2 °C increments) at 80 ± 10 % RH, 12:12 photoperiod.
- **Measurements:** Daily checks of mortality and stage transitions (egg → L1 → L2 → L3 → L4 → pupa → adult); pupation success, number of adults produced, sex ratio.
- **Analysis:** Kaplan-Meier survival analysis for stage-specific development times; one-way ANOVA and Kruskal-Wallis tests for group comparisons; non-linear regression to fit thermal response curves.

## Key Results

- **Peak development rate:** Around 28 °C, then declines sharply.
- **Total development time egg → adult at 25 °C:** ~13–16 days (seminal experimental value).
- **Optimal emergence (survival):** Between 22 and 26 °C.
- **Thermal limits:** No adult emergence below 18 °C or above 34 °C.
- **Stage-specific durations at 25 °C:** egg ~1.1 d; each larval instar ~2–3 d; pupa ~1.2 d.
- **Mortality pattern:** Highest mortality in late larval stages (L3, L4) at upper thermal range (30–32 °C); over 70 % of terminal events were deaths (not emergence) at 30–32 °C.

## Relevance to MalariaSentinel (Centinela)

**This is the seminal experimental reference for the development rate of *An. gambiae* aquatic stages.** It is the foundational dataset used by:

- **Depinay et al. 2004** — fitted their larval development thermal curves to this data when building the first *Anopheles* ABM.
- **Mordecai et al. 2013** — used this data as one of the inputs for the larval development rate (MDR) curve in their R₀ model.
- **Couper et al. 2021** — referenced by the current Centinela's thermal_responses.hpp.

**Direct impact on Centinela parameters:** The current Centinela implementation in `mal-core/src/mal_core/abm/include/mal_abm_fast/thermal_responses.hpp` uses `LARVA_A = 0.00052`, which produces a per-instar development rate of ~0.117/day at 25 °C → **8.5 days per instar × 4 instars = 34 days total**. Bayoh & Lindsay measured **13–16 days total at 25 °C**. The discrepancy arises because the Mordecai-fitted curve's `a` parameter captures the *shape* of the response correctly but underestimates the *absolute rate*. Recalibrating `LARVA_A ≈ 0.001` aligns the model with Bayoh & Lindsay (and Depinay's fit of the same data).

This paper also establishes the thermal limits (18–34 °C viable range, 25–28 °C optimum) that should constrain the Ghana regional ABM's habitat activation thresholds.

## Limitations

- Laboratory data at **constant** temperatures; field conditions have diurnal fluctuation which can shift effective optima.
- Single mosquito strain; *An. gambiae* s.l. shows geographic variation in thermal tolerance across its African range.
- Stage-specific rates were averaged; inter-individual variability was not fully quantified.

## Future Directions

- Validate the thermal curves under fluctuating temperature regimes (DTR effects).
- Cross-validate against the Agyekum et al. 2022 Ghana-specific re-measurement and the Ouédraogo et al. 2024 Burkina Faso semi-field data.
- Extend to other dominant African vectors (*An. funestus*, *An. arabiensis*) with different thermal optima.

## References

- Bayoh MN, Lindsay SW (2003). Effect of temperature on the development of the aquatic stages of *Anopheles gambiae* sensu stricto (Diptera: Culicidae). *Bulletin of Entomological Research*, 93(5): 375–381. doi:10.1079/BER2003259
- Depinay JMO, Mbogo CM, Killeen G, et al. (2004). A simulation model of African *Anopheles* ecology and population dynamics for the analysis of malaria transmission. *Malaria Journal*, 3:29. doi:10.1186/1475-2875-3-29
- Mordecai EA, Paaijmans KP, Johnson LR, et al. (2013). Optimal temperature for malaria transmission is dramatically lower than previously predicted. *Ecology Letters*, 16: 22–30. doi:10.1111/ele.12015