# Agent-based simulation of seasonal malaria chemoprevention strategy in Southern Tanzania

**Authors:** Mfala CT, Nyambo DG, et al.
**Journal:** Malaria Journal | **Year:** 2026 | **DOI:** 10.1186/s12936-026-05821-3
**File:** papers/abm-geospatial/mfala-et-al-2026-abm-seasonal-malaria-chemoprevention.md

---

## Abstract

This study uses the AnyLogic platform to simulate the effectiveness of seasonal malaria chemoprevention (SMC) strategies in Southern Tanzania, comparing dihydroartemisinin-piperaquine (DP) with and without single low-dose primaquine (SLDPQ). The model incorporates human, mosquito, transmission, intervention, and environment sub-models to capture the full transmission cycle. Results show that adding SLDPQ to DP leads to approximately 87.6% decline in malaria prevalence, demonstrating the potential of combined chemoprevention strategies.

## Methods

- AnyLogic-based agent-based model with five interacting sub-models: human population, mosquito population, transmission dynamics, intervention delivery, and environmental drivers
- SMC strategy simulation using DP monotherapy versus DP + SLDPQ combination
- Parameterisation from Tanzanian epidemiological and entomological data
- Sensitivity analysis on intervention coverage, timing, and drug efficacy parameters
- Comparison of prevalence reduction across different coverage scenarios

## Key Results

- DP + SLDPQ combination achieved ~87.6% decline in malaria prevalence
- SMC timing aligned with seasonal peak transmission maximised impact
- Coverage thresholds identified below which SMC effectiveness drops significantly
- Model captures age-stratified immunity dynamics and their interaction with chemoprevention
- Environmental sub-model captures rainfall-driven transmission seasonality

## Relevance to MalariaSentinel (Centinela)

Demonstrates ABM application for evaluating combined intervention strategies in seasonal transmission settings. The multi-sub-model architecture (human, mosquito, transmission, intervention, environment) provides a template for the Centinela's Ghana simulation module. The finding on combination therapy effectiveness is relevant for the Centinela's intervention optimisation component, particularly for seasonal settings in northern Ghana where SMC is deployed. The AnyLogic-based approach also demonstrates a platform option for rapid prototyping.

## Limitations

- AnyLogic platform is proprietary; open-source alternatives may be preferable for reproducibility
- Parameterisation specific to Southern Tanzania; transferability to Ghana requires recalibration
- SLDPQ efficacy data may be limited
- Model does not capture drug resistance dynamics

## Future Directions

- Validate against SMC trial data from other seasonal transmission settings
- Extend to incorporate drug resistance monitoring
- Integrate with geospatial environmental layers for spatially explicit SMC optimisation
- Compare with alternative delivery strategies (e.g., focal versus mass administration)

---

*Paper condensed from Phase 1 research findings. 2026-07-17.*
