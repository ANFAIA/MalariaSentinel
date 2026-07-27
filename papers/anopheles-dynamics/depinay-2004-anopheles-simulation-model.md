# A simulation model of African Anopheles ecology and population dynamics for the analysis of malaria transmission

**Authors:** Jean-Marc O Depinay, Charles M Mbogo, Gerry Killeen, Bart Knols, John Beier, John Carlson, Jonathan Dushoff, Peter Billingsley, Henry Mwambi, John Githure, Abdoulaye M Touré, F Ellis McKenzie
**Journal:** Malaria Journal | **Year:** 2004 | **DOI:** 10.1186/1475-2875-3-29
**File:** papers/anopheles-dynamics/depinay-2004-anopheles-simulation-model.md

---

## Abstract

Malaria is one of the oldest and deadliest infectious diseases in humans. Many mathematical models of malaria have been developed during the past century, and applied to potential interventions. However, malaria remains uncontrolled and is increasing in many areas, as are vector and parasite resistance to insecticides and drugs. This study presents a simulation model of African malaria vectors. This individual-based model incorporates current knowledge of the mechanisms underlying *Anopheles* population dynamics and their relations to the environment. One of its main strengths is that it is based on both biological and environmental variables. The model made it possible to structure existing knowledge, assembled in a comprehensive review of the literature, and also pointed out important aspects of basic *Anopheles* biology about which knowledge is lacking. One simulation showed several patterns similar to those seen in the field, and made it possible to examine different analyses and hypotheses for these patterns; sensitivity analyses on temperature, moisture, predation and preliminary investigations of nutrient competition were also conducted.

## Methods

- **Model type:** Individual-based model (the first object-oriented simulation of the complete *An. gambiae* life cycle).
- **Life cycle:** Four stages — egg, larva, pupa, adult — with explicit individual tracking.
- **Thermal response:** Schoolfield-Sharpe enzyme kinetics model fitted to **Bayoh & Lindsay (2003)** data for An. gambiae egg, larva, pupa, and gonotrophic cycle rates.
- **Density dependence:** Nutrient competition in the larval stage with minimum weight requirement for pupation (weight determines adult fecundity).
- **Adult survival:** **0.911/day** on non-ovipositing days; reduced by a predation/host-seeking lag term on ovipositing days.
- **Validation scenario:** 20-month simulation with meteorological data from Kilifi, Kenya (May 2000 – Dec 2001) for a 6-house / 3-pool cluster.

## Key Results

- **Adult daily survival:** 0.911 (base, non-ovipositing).
- **Larval mortality:** Arbitrarily set to 25 % (density-dependent) with a daily mortality conversion formula.
- **Egg mortality:** 5 % batch + 0.99 daily survivorship.
- **Larval development:** Fitted to Bayoh & Lindsay 2003 → total egg-to-adult ~11–13 days at 25 °C.
- **Predation:** Lag-time density-dependent mortality in temporary pools.
- **Validation:** Simulated adult abundance curves showed patterns consistent with field observations from coastal Kenya, including the post-drought recovery peak.

## Relevance to MalariaSentinel (Centinela)

**This is the foundational ABM for African *Anopheles* population dynamics.** Several of its design choices directly inform the Centinela:

1. **Thermal curve source:** Depinay used Bayoh & Lindsay (2003) directly. The current Centinela uses Mordecai (2013), which also fits the same data but with a different functional form. Where the two diverge in *absolute timescale*, Depinay's fit is closer to the experimental measurements (13–16 d vs 34 d at 25 °C).

2. **Adult survival parameter:** 0.911/day is **within the field MRR range** (0.80–0.95, see dispersal-kernel-calibration.md). The current Centinela uses 0.93, which is at the upper end but defensible — consistent with Midega 2007 (Kenya coast, 0.83–0.95) and Diallo 2026 (Mali, 0.94 corrected).

3. **Modular structure:** Depinay separated abiotic drivers (temperature, moisture) from biotic regulators (competition, predation, dispersal). The Centinela's split into `aquatic_cohort_bank` (biotic/abiotic) + `host_seeking` + `dispersal` mirrors this design.

4. **Calibration strategy:** Depinay explicitly identified which parameters needed additional field data (predation lag, aestivation survival). The Centinela's ongoing calibration of D1–D15 scorers follows the same philosophy.

## Limitations

- Several parameters were "arbitrarily set" (larval mortality 25 %, egg mortality) because of data scarcity — a problem the Centinela inherits.
- Predation and disease are modelled abstractly (lag term) without species-specific parameterisation.
- No genetic variation / insecticide resistance module.
- Spatial structure is local (6-house cluster), not landscape-scale.
- The model does not couple to a malaria transmission (human-side) component.

## Future Directions

- Couple the Depinay-style ABM with landscape dispersal and U-Net emulators (the Centinela's M7+ roadmap).
- Replace the arbitrary larval mortality with species-specific, food-density-driven formulations.
- Validate against the Ghana entomological surveillance data (Agyekum 2022 strain).
- Couple to the Gatore Sinigirira 2025 SEIR-SEI framework for full transmission dynamics.

## References

- Depinay JMO, Mbogo CM, Killeen G, et al. (2004). A simulation model of African *Anopheles* ecology and population dynamics for the analysis of malaria transmission. *Malaria Journal*, 3:29. doi:10.1186/1475-2875-3-29
- Bayoh MN, Lindsay SW (2003). Effect of temperature on the development of the aquatic stages of *Anopheles gambiae* sensu stricto. *Bulletin of Entomological Research*, 93(5): 375–381.
- Costantini C, Li S, della Torre A, et al. (1996). Density, survival and dispersal of *Anopheles gambiae* complex mosquitoes in a West African Sudan savanna village. *Medical and Veterinary Entomology*, 10(3): 203–219.