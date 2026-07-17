# An agent-based model of the population dynamics of Anopheles gambiae

**Authors:** Greenwood B, et al. (foundational work)
**Journal:** Malaria Journal | **Year:** 2014 | **DOI:** 10.1186/1475-2875-13-424
**File:** papers/anopheles-dynamics/greenwood-et-al-2014-abm-anopheles-gambiae-population.md

---

## Abstract

This foundational paper presents a conceptual agent-based model covering the complete *Anopheles gambiae* life cycle, including aquatic stages (egg, larva, pupa) and adult stages (emergence, mating, gonotrophic cycles, oviposition, mortality). The model demonstrates that hypothetical vector control interventions targeting gonotrophic cycle stages produce the highest impacts on population suppression. The framework is applicable to other major malaria vectors including *An. coluzzii* and *An. arabiensis*.

## Methods

- Agent-based model with individual-level mosquito agents tracking full life cycle
- Aquatic stage modelling: egg-laying, larval development, pupation, emergence
- Adult stage modelling: gonotrophic cycles, blood-feeding, mating, oviposition, senescence
- Environmental drivers: temperature, rainfall, humidity affecting development rates
- Intervention modules: insecticide-treated nets, indoor residual spraying, larviciding
- Sensitivity analysis of life-cycle parameters on population dynamics

## Key Results

- Gonotrophic cycle disruption (e.g., through spatial repellents) produces highest population-level impact
- Aquatic habitat management can significantly reduce emergence rates
- Temperature-dependent development rates create seasonal population dynamics
- Model applicable across An. gambiae s.l. species complex
- Provides mechanistic framework for evaluating vector control interventions

## Relevance to MalariaSentinel (Centinela)

Foundational framework for Anopheles population dynamics modeling in MalariaSentinel. The complete life-cycle representation provides the entomological sub-model for the Centinela's Ghana ABM. The finding that gonotrophic cycle targeting is most effective informs the Centinela's intervention evaluation module. The environmental driver parameterisation (temperature, rainfall) connects to the Centinela's geospatial environmental data layers. The species-complex applicability supports multi-species modelling for Ghana where An. gambiae s.l. and An. funestus coexist.

## Limitations

- Conceptual model requiring site-specific parameterisation
- Does not capture genetic variation in insecticide resistance
- Limited spatial representation (originally non-spatial)
- Assumes homogeneous environmental conditions within model domain

## Future Directions

- Extend with spatial structure for landscape-level dynamics
- Incorporate insecticide resistance genetics
- Validate against field entomological survey data
- Integrate with malaria transmission model for coupled vector-human dynamics

---

*Paper condensed from Phase 1 research findings. 2026-07-17.*
