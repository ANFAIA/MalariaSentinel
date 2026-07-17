# Assessing the impact of climate and control interventions on spatio-temporal malaria dynamics

**Authors:** Angelakis A, Beloconi A, et al.
**Journal:** PLOS Computational Biology | **Year:** 2026 | **DOI:** 10.1371/journal.pcbi.1014004
**File:** papers/abm-intervention/angelakis-et-al-2026-stochastic-metapopulation-malaria.md

---

## Abstract

This paper develops a process-based stochastic metapopulation transmission model incorporating immunity, infectivity, migration, climate variability, and interventions. The model accurately captures effects of small-scale heterogeneity in western Kenya between 2008–2019, demonstrating how climate and control interventions interact to shape spatio-temporal malaria dynamics at sub-county scales.

## Methods

- Process-based stochastic metapopulation model with explicit spatial structure
- Immunity dynamics: acquired immunity, maternal immunity, waning
- Infectivity modelling: parasite density, gametocyte carriage, infectiousness to mosquitoes
- Migration: human movement between sub-populations
- Climate variability: temperature and rainfall effects on vector dynamics
- Intervention modules: ITNs, IRS, treatment, seasonal chemoprevention
- Validation against DHIS2 surveillance data from western Kenya (2008–2019)

## Key Results

- Model accurately captures spatio-temporal dynamics at sub-county scale
- Climate variability explains significant temporal variation in transmission
- Intervention effects (ITN scale-up, IRS) reproduced in model outputs
- Small-scale heterogeneity in immunity and transmission creates complex dynamics
- Migration between sub-populations affects local transmission trajectories
- Stochastic formulation captures realistic outbreak variability

## Relevance to MalariaSentinel (Centinela)

Advanced metapopulation modeling approach for MalariaSentinel's spatial dynamics. The metapopulation structure (sub-populations connected by migration) directly models Ghana's district-level transmission dynamics. The integration of immunity, climate, and interventions provides a comprehensive framework for the Centinela's simulation engine. The 11-year validation period demonstrates long-term model fidelity. The sub-county resolution aligns with the Centinela's goal of fine-grained spatial targeting.

## Limitations

- Kenya-specific parameterisation; transferability to Ghana requires calibration
- Sub-population structure definition may be subjective
- Immunity dynamics are complex and uncertain
- Computational demands for stochastic metapopulation modelling are substantial

## Future Directions

- Calibrate and validate for Ghanaian districts
- Add entomological sub-model for vector dynamics
- Integrate with real-time surveillance data for near-real-time prediction
- Develop reduced-complexity version for operational deployment

---

*Paper condensed from Phase 1 research findings. 2026-07-17.*
