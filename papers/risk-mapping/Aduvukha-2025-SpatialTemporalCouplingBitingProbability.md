# Spatial-temporal coupling of malaria vector habitat suitability and biting probability

**Authors:** Grace Rebecca Aduvukha, Elfatih M. Abdel-Rahman, Onisimo Mutanga, John Odindi, Henri E. Z. Tonnang
**Journal:** Spatial and Spatio-temporal Epidemiology | **Year:** 2025 | **DOI:** 10.1016/j.sste.2025.100777
**File:** papers/risk-mapping/Aduvukha-2025-SpatialTemporalCouplingBitingProbability.md

---

## Abstract

Effective malaria vector control requires understanding both where vectors are present (habitat suitability) and how likely they are to bite humans (biting probability) — yet these two dimensions are rarely modelled jointly. This study integrates MaxEnt species distribution modelling with fuzzy logic rule-based techniques to simultaneously model habitat suitability and biting probability of Anopheles malaria vectors across Cameroon from 2000 to 2018. Remotely sensed environmental data (climate, topography), modelled vector presence, human availability, confirmed insecticide resistance, and bed net usage are combined into two fuzzy rule-based scenarios — one with flexible optimal conditions (ORs) and one with strict conditions (ANDs). Both models achieve 91% mean accuracy against independent An. gambiae complex biting observations (n=25, 2017–2021), revealing reduced biting probability with increased bed net usage amid optimal environmental conditions.

## Methods

- **Species distribution modelling:** MaxEnt (maximum entropy) used to model habitat suitability from presence-only malaria vector data, incorporating remotely sensed climate variables (temperature, rainfall), topographic variables (elevation, slope), and vegetation indices.
- **Biting probability modelling:** Fuzzy logic rule-based approach combining modelled vector presence with additional layers: human availability/presence, confirmed insecticide resistance status, and bed net usage data.
- **Two model scenarios:** Model 1 (flexible conditions using OR rules — optimal climate OR optimal environment) vs. Model 2 (strict conditions using AND rules — optimal climate AND optimal environment).
- **Validation:** Independent dataset of An. gambiae complex biting observations (n=25 sites, 2017–2021).
- **Temporal analysis:** Biting probability trends assessed across the 2000–2018 period to evaluate the impact of increasing intervention coverage.

## Key Results

- **Validation accuracy:** Both models achieved 91% mean accuracy against independent biting observation data.
- **Intervention impact:** Biting probability decreased with increased bed net usage, consistent with observed declines in Plasmodium falciparum prevalence from 2000 to 2018.
- **Environmental coupling:** Biting probability was highest when optimal climatic conditions (temperature, rainfall) coincided with high human availability — demonstrating that vector presence alone is insufficient to predict transmission risk.
- **Insecticide resistance modifier:** Areas with confirmed insecticide resistance showed higher effective biting probability despite bed net coverage, highlighting a critical gap in intervention effectiveness.
- **Spatial-temporal patterns:** The model captured the heterogeneous distribution of biting risk across Cameroon's ecological zones, from forest to humid savanna.

## Relevance to MalariaSentinel (Centinela)

This paper provides a two-layer modelling approach directly applicable to the Centinela's risk-mapping pipeline. The separation of habitat suitability (MaxEnt) from biting probability (fuzzy rules) mirrors the Centinela's architectural separation of environmental suitability and transmission risk. The inclusion of intervention covariates (ITN coverage, insecticide resistance) as modifiers of biting probability reinforces H2 — intervention layers must be integrated as dynamic parameters, not static overlays. The fuzzy logic framework for combining heterogeneous data sources (environmental + behavioural + intervention) offers a practical alternative to purely statistical approaches when data types are mixed. The finding that insecticide resistance modulates effective biting risk is particularly relevant for Ghana, where resistance to pyrethroids (the insecticide used in most ITNs) is widespread.

## Limitations

- The validation dataset is small (n=25 sites) and restricted to An. gambiae complex; performance for other vector species (An. funestus) is untested.
- The fuzzy rule-based approach requires expert knowledge to define rules, introducing subjectivity that data-driven approaches might avoid.
- Bed net usage data are self-reported from surveys and may not reflect actual usage patterns.
- The model does not capture fine-scale spatial heterogeneity (e.g., within-village variation in biting risk).
- Temporal resolution is annual; seasonal dynamics in biting probability are not captured.

## Future Directions

- Validate the fuzzy rule-based approach against entomological surveillance data from Ghana's ecological zones.
- Extend the framework to incorporate An. funestus breeding habitat requirements (permanent/semi-permanent water bodies) as a separate suitability layer.
- Develop seasonal (monthly) biting probability maps using higher-resolution temporal climate data.
- Integrate the insecticide resistance layer with the Centinela's intervention module to model the erosion of ITN effectiveness over time.
- Explore deep learning alternatives (e.g., CNN-based spatial prediction) for the fuzzy rule-based component to reduce expert-subjectivity.

---

## References

- Aduvukha GR, Abdel-Rahman EM, Mutanga O, Odindi J, Tonnang HEZ. (2025). Spatial-temporal coupling of malaria vector habitat suitability and biting probability. *Spatial and Spatio-temporal Epidemiology*, 56: 100777.
- Phillips SJ, Anderson RP, Schapire RE. (2006). Maximum entropy modeling of species geographic distributions. *Ecological Modelling*, 190: 231–259. (MaxEnt framework).
- Mordecai EA, et al. (2013). Optimal temperature for malaria transmission is dramatically lower than previously predicted. *Ecology Letters*, 16: 22–30.
- Ranson H, Lissenden N. (2016). Insecticide resistance in African Anopheles mosquitoes: a worsening situation that needs urgent action to maintain malaria control. *Trends in Parasitology*, 32: 187–196.
