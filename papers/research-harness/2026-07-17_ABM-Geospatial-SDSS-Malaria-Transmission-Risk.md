# Research Summary: Malaria Mosquito ABM, Geospatial Analysis & SDSS

**Generated**: 2026-07-17  
**Harness Phase**: Search  
**Topic**: malaria mosquito ABM geospatial analysis | spatial decision support systems malaria elimination | Anopheles gambiae population dynamics modeling | malaria transmission risk mapping Africa | agent-based models malaria intervention evaluation

---

## Executive Summary

This literature survey covers 25+ papers (2020–2026) across five intersecting domains critical to MalariaSentinel: (1) agent-based modeling of malaria transmission, (2) spatial decision support systems, (3) Anopheles population dynamics, (4) geospatial risk mapping, and (5) intervention evaluation. Key findings: the field is converging on **spatio-temporal ABMs** that integrate climate, intervention, and host-vector dynamics; **Bayesian geostatistical models** are the gold standard for risk mapping; and **digital SDSS platforms** (CIMS, eSPT) are proving operational value in real programmes. For MalariaSentinel, the most relevant advances are the integration of suitability maps into household-level ABMs (Walker et al. 2026), the hazard-vulnerability risk decomposition (Senegal framework, 2025), and the EMOD-based ITN transition models calibrated to Tanzania (Gervas et al. 2026).

---

## 1. Agent-Based Models of Malaria Transmission

### 1.1 Spatio-temporal ABM with Household Data — Vietnam Case Study
- **Title**: Spatio-temporal agent-based modelling of malaria
- **Authors**: Walker JR, Anwar MN, Brauninger L, Richards JS, Ataíde R, Ngo Duc Thang, et al.
- **Published**: April 2026 (arXiv: 2505.16240)
- **Key findings**: Developed a stochastic spatio-temporal ABM using mosquito climatic suitability maps (Brown et al. 2024) and household GPS data in Vietnam. Model shows providing broad protection to many households reduces prevalence more than concentrated protection to few households. Interventions (IRS/LLINs) applied at household level based on spatial heterogeneity of bite exposure.
- **Relevance**: Directly applicable to MalariaSentinel's goal of household-level intervention targeting. Demonstrates integration of suitability maps with agent-level spatial data.
- **URL**: https://arxiv.org/html/2505.16240

### 1.2 EMOD-Based ITN Transition Model — Tanzania
- **Title**: Modelling the impact of adopting new-generation insecticide-treated nets on malaria transmission and insecticide resistance
- **Authors**: Hamenyimana EG, Mayengo M, Chacky F, Mlacha YP, Ngowo HS, Okumu FO, et al.
- **Published**: March 2026
- **Key findings**: Used EMOD agent-based model to simulate transition from pyrethroid-only → PBO → Interceptor G2 ITNs in Tanzania. Transitioning reduced homozygous-resistant An. funestus by 62.2% and An. arabiensis by 92.8%. Adding triennial IRS reduced incidence by 76.4%. Model calibrated to northwestern Tanzania incidence/prevalence data with seasonality and resistance dynamics.
- **Relevance**: Demonstrates EMOD platform for intervention sequencing; directly relevant to MalariaSentinel's intervention evaluation module. Shows value of multi-vector, resistance-aware modeling.
- **URL**: https://doi.org/10.64898/2026.03.05.26347588

### 1.3 SMC Evaluation via ABM — Southern Tanzania
- **Title**: Agent-based simulation of seasonal malaria chemoprevention strategy in Southern Tanzania
- **Authors**: Mfala CT, Nyambo DG, Mwaiswelo RO, Mmbando BP, Clemen T
- **Published**: February 2026, Malaria Journal
- **Key findings**: AnyLogic ABM assessed SMC with DP ± SLDPQ. Model incorporated human, mosquito, transmission, intervention, and environment sub-models. Adding SLDPQ to DP reduced prevalence by ~87.6% vs. 53.2% control decline. Temperature sensitivity analysis showed mosquito breeding dynamics are climate-responsive.
- **Relevance**: Demonstrates multi-platform ABM (AnyLogic) for chemoprevention evaluation; useful template for MalariaSentinel's intervention modeling.
- **URL**: https://doi.org/10.1186/s12936-026-05821-3

### 1.4 ABM with House Quality and ITN Coverage — Tanzania
- **Title**: Developing an Agent-based Model for Evaluating the Effectiveness of Malaria Interventions in Nanyumbu and Masasi Districts, Tanzania
- **Authors**: Mfala CT, Nyambo DG, Mwaiswelo R, Mmbando BP, Clemen T
- **Published**: November 2024, Indian J Sci Technol
- **Key findings**: AnyLogic ABM incorporating house quality (eave openness) as a factor in ITN effectiveness. ITN coverage of 80% reduced prevalence from 15.4% to 13.9%. Novel contribution: house construction quality modulates ITN efficacy — open eaves increase mosquito entry despite ITN use.
- **Relevance**: Shows importance of built-environment variables; relevant to MalariaSentinel's geospatial layers for settlement characterization.
- **URL**: https://doi.org/10.17485/ijst/v17i43.2133

### 1.5 Stochastic Metapopulation Model — Western Kenya
- **Title**: Assessing the impact of climate and control interventions on spatio-temporal malaria dynamics using a stochastic metapopulation model
- **Authors**: Angelakis A, Beloconi A, Nyawanda BO, et al.
- **Published**: March 2026, PLOS Computational Biology
- **Key findings**: Developed a SpatPOMP (spatio-temporal partially observed Markov process) model capturing immunity, infectivity, migration, climate variability, and bed net use across sub-populations in western Kenya (2008–2019). Model accurately captured small-scale heterogeneity. Increased bed net use had significant negative effect on force of infection, but cases increased since 2016 due to climate shifts and species composition changes.
- **Relevance**: Generalizable framework for combining climate, intervention, and mobility data at sub-regional scale. Applicable to MalariaSentinel's climate-integration layer.
- **URL**: https://journals.plos.org/ploscompbiol/article?id=10.1371%2Fjournal.pcbi.1014004

### 1.6 Vector Genetics and Gene Drives — ABM Framework
- **Title**: Vector genetics, insecticide resistance and gene drives: An agent-based modeling approach
- **Authors**: Selvaraj P, Wenger EA, Bridenbecker D, et al.
- **Published**: 2020, PLOS Computational Biology
- **Key findings**: First multi-locus ABM of vector genetics embedded within a large-scale malaria transmission model. Modeled genotype-to-phenotype mapping for insecticide resistance and gene drive propagation in Anopheles populations. Results show even small numbers of resistant vectors can dominate under repeated insecticide exposure; gene drives combined with ITNs bring high-transmission settings closer to elimination.
- **Relevance**: Foundational for modeling resistance evolution; relevant to MalariaSentinel's long-term sustainability assessments.
- **URL**: https://journals.plos.org/ploscompbiol/article?id=10.1371%2Fjournal.pcbi.1008121

### 1.7 ABM with Aquatic Habitats — Spatially Explicit
- **Title**: The impact of aquatic habitats on malaria parasite transmission: A view from an agent-based model
- **Authors**: Khelifa A, El Saadi N
- **Published**: 2024, Ecological Modelling
- **Key findings**: Spatially explicit ABM integrating aquatic breeding habitats, dispersal of vectors/hosts, and host immunity. Demonstrates that habitat distribution and proximity to human settlements critically shape transmission intensity.
- **Relevance**: Validates MalariaSentinel's approach of coupling larval habitat mapping with transmission dynamics.
- **URL**: https://doi.org/10.1016/j.ecolmodel.2023.110547

---

## 2. Spatial Decision Support Systems (SDSS)

### 2.1 Real-Time SDSS for IRS — Bioko Island
- **Title**: Real-time, spatial decision support to optimize malaria vector control: The case of indoor residual spraying on Bioko Island
- **Authors**: García GA, Atkinson BJ, Donfack OT, et al.
- **Published**: May 2022, PLOS Digital Health
- **Key findings**: The Campaign Information Management System (CIMS) SDSS improved IRS operational efficiency on Bioko Island. Optimal coverage (80–85%) achieved in 37.7% of map-sectors in 2021 (vs. 17% in 2017). Real-time data processing at 100×100m granularity enabled better spray team management. References Kelly et al. (2012) SDSS framework.
- **Relevance**: Proven operational SDSS model; MalariaSentinel's decision support layer should follow this real-time, fine-granularity approach.
- **URL**: https://doi.org/10.1371/journal.pdig.0000025

### 2.2 Digital Entomological Surveillance Planning Tool (eSPT)
- **Title**: Evaluation of a digital entomological surveillance planning tool for malaria vector control
- **Authors**: (Multiple authors, 3-country pilot)
- **Published**: March 2025, PLOS ONE
- **Key findings**: eSPT translates WHO/PMI normative guidance into operational decision-support for vector control planning. Piloted in Ethiopia, Malawi, Mozambique. Improved target users' knowledge and self-efficacy in surveillance planning. Supports devolution of planning to provincial/district level. Mobile-device compatibility recommended.
- **Relevance**: Direct precedent for MalariaSentinel's planning tools; demonstrates that digital decision-support tools improve local programme capacity.
- **URL**: https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0303915

### 2.3 GIS for Targeted Intervention Allocation in Africa
- **Title**: The Role of GIS in Designing Timely and Targeted Malaria Intervention Allocation in Africa
- **Author**: Bello A
- **Published**: June 2025, IntechOpen
- **Key findings**: Comprehensive review of GIS applications in malaria mapping. Emphasizes that georeferenced entomological data linked to environmental indices is essential for accurate small-scale risk maps. References the Global Malaria Atlas Project (MAP) and MARA/ARMA as foundational frameworks. Calls for integration of GPS-survey data with spatial risk models.
- **Relevance**: Provides theoretical grounding for MalariaSentinel's GIS architecture and data integration approach.
- **URL**: https://www.intechopen.com/chapters/1217969

---

## 3. Anopheles Population Dynamics Modeling

### 3.1 AnophelesModel R Package
- **Title**: AnophelesModel: An R package to interface mosquito bionomics, human exposure and intervention effects with models of malaria intervention impact
- **Authors**: Golumbeanu M, Briët O, Champagne C, et al.
- **Published**: September 2024, PLOS Computational Biology
- **Key findings**: R package estimating species-specific vectorial capacity for any Anopheles species. Models LLIN, IRS, and house screening effects on vectorial capacity. Generates parameters for OpenMalaria. Demonstrates that An. gambiae (indoor night-biter) vs. An. farauti (outdoor evening-biter) have dramatically different intervention response profiles.
- **Relevance**: Directly usable by MalariaSentinel for parameterizing intervention effects per vector species. The package's database is a valuable resource for model calibration.
- **URL**: https://doi.org/10.1371/journal.pcbi.1011609

### 3.2 Spatial Modeling of Anopheles Population Dynamics — Madagascar
- **Title**: Spatial modeling of the population dynamics of Anopheles mosquitoes in Madagascar
- **Authors**: Rakotoarison HA, Nepomichene T, Guis H, et al.
- **Published**: November 2025, International Journal of Health Geographics
- **Key findings**: Mechanistic ODE-based model of four Anopheles species (An. arabiensis, An. coustani, An. funestus, An. gambiae) incorporating aquatic and aerial life stages, climate, and agricultural calendar (rice cultivation). Ocelet language for spatial simulation. Validated against field data (r=0.70–0.76). Agricultural calendar integration reduced overestimation of adult females.
- **Relevance**: Demonstrates that agricultural practices are critical drivers of Anopheles populations — essential for MalariaSentinel's seasonal dynamics module. Multi-species approach is novel.
- **URL**: https://doi.org/10.1186/s12942-025-00424-8

### 3.3 Spatio-temporal Phenotypic Resistance Modeling — Africa
- **Title**: Spatio-temporal characterization of phenotypic resistance in malaria vector species
- **Authors**: Ibrahim EA, Wamalwa M, Odindi J, Tonnang HEZ
- **Published**: May 2024, BMC Biology
- **Key findings**: Cellular automata (CA) model for dynamic insecticide resistance prediction across An. gambiae complex and An. arabiensis in Ethiopia, Nigeria, Cameroon, Chad, Burkina Faso. Identifies human density, insecticide usage, agriculture, and climate as key IR drivers. Model validated on out-of-sample countries with classification accuracy.
- **Relevance**: Provides a resistance forecasting layer that MalariaSentinel could integrate for long-term intervention planning.
- **URL**: https://doi.org/10.1186/s12915-024-01915-z

---

## 4. Geospatial Risk Mapping

### 4.1 Hazard-Vulnerability Decomposition — Senegal
- **Title**: Integrating vulnerability and hazard in malaria risk mapping: the elimination context of Senegal
- **Authors**: (Multiple authors)
- **Published**: August 2025, BMC Infectious Diseases
- **Key findings**: Decomposes malaria risk into 'hazard' (infected vector presence — climate/land use) and 'vulnerability' (population predisposition — health access, housing). Bayesian geostatistical models at 1km resolution using 2017 DHS + 2020-21 MIS. Best model (R²=0.64) combined both components. Interactive web maps produced for hotspot identification.
- **Relevance**: **Directly aligns with MalariaSentinel's risk decomposition philosophy.** The hazard-vulnerability framework is the conceptual foundation for our SDSS. Open-source, replicable methodology.
- **URL**: https://link.springer.com/article/10.1186/s12879-025-11412-5

### 4.2 Fine-Scale Urban Malaria Mapping — Dakar, Senegal
- **Title**: Fine-scale mapping of urban malaria exposure under data scarcity
- **Authors**: Vanhuysse S, Diédhiou SM, Grippa T, Georganos S, et al.
- **Published**: 2023, Malaria Journal
- **Key findings**: Knowledge-based geospatial framework for mapping urban malaria hazard and exposure at 100m resolution. Uses vector ecology expert input + deductive MCDA (AHP) for larval habitat suitability. Integrates urban morphological deprivation as vulnerability proxy. Validated with entomological field data from Dakar suburbs (575 positive water bodies).
- **Relevance**: Demonstrates expert-driven geospatial modeling when entomological data is scarce — applicable to MalariaSentinel's data-scarce regions. Urban focus addresses growing urban malaria challenge.
- **URL**: https://malariajournal.biomedcentral.com/articles/10.1186/s12936-023-04527-0

### 4.3 Bayesian Spatio-temporal Risk Mapping — Tanzania
- **Title**: Bayesian spatio-temporal modeling and prediction of malaria cases in Tanzania mainland (2016-2023)
- **Authors**: (Multiple authors)
- **Published**: August 2025, International Journal of Health Geographics
- **Key findings**: INLA-based Bayesian spatio-temporal model with CAR + RW2 for monthly malaria counts. Identified LLINs as significantly protective (1% coverage increase → 1.2% risk decrease for under-5s, 7% for 5+). Climate drivers: humidity, min temperature, wind speed, vegetation indices. Produced risk maps at regional level.
- **Relevance**: Reproducible INLA framework for routine surveillance data integration; applicable to MalariaSentinel's DHIS2 data pipeline.
- **URL**: https://link.springer.com/article/10.1186/s12942-025-00408-8

### 4.4 ML-Based Risk Mapping — Nigeria
- **Title**: Integrating DHS/MIS Biomarkers with 34 Years of CHIRPS-NDVI Climate Data for Malaria Risk Prediction in Nigeria
- **Author**: Onimisi D
- **Published**: December 2025
- **Key findings**: Random Forest classifier integrating DHS/MIS parasitemia biomarkers (2010, 2015, 2021) with 34-year CHIRPS rainfall and MODIS-NDVI via Google Earth Engine. Cross-year temporal validation. SHAP interpretability for feature importance. Generated LGA-level risk maps showing north-south gradient with hotspots in NW (Katsina, Zamfara, Sokoto).
- **Relevance**: ML pipeline replicable for other endemic countries; demonstrates GEE-based feature engineering at scale.
- **URL**: https://doi.org/10.64898/2025.12.14.25342244

### 4.5 Environmental Suitability Mapping — Malawi
- **Title**: Leveraging big data for public health: Mapping malaria vector suitability in Malawi with Google Earth Engine
- **Authors**: Frake AN, Peter BG, Walker ED, Messina JP
- **Published**: August 2020, PLOS ONE
- **Key findings**: Raster-based suitability model at 30m resolution using GEE. Considers temperature, NDVI, land cover, precipitation, flow accumulation, water resources. Seasonal analysis: 28.24% of Malawi suitable in rainy season, <2% in dry season. Framework parameterized for An. gambiae but transferable to other species.
- **Relevance**: GEE-based approach is directly replicable for MalariaSentinel's environmental layer generation.
- **URL**: https://doi.org/10.1371/journal.pone.0235697

### 4.6 ML-Driven Risk Mapping — Benin
- **Title**: Guiding malaria elimination interventions: a data-driven approach to resource optimization in Benin
- **Authors**: (Multiple authors)
- **Published**: July 2026, Malaria Journal
- **Key findings**: SPDE model with remote sensing covariates (temperature, vegetation, soil, built-up areas). RDT data from DHS. Identified hotspots in northern/central Benin. Sensitivity 0.619, specificity 1.000. Demonstrates that environmental covariates capture spatial variability of transmission.
- **Relevance**: Bayesian spatial modeling framework applicable to MalariaSentinel's risk mapping pipeline.
- **URL**: https://link.springer.com/article/10.1186/s12936-026-06033-5

### 4.7 Hydrology-Sensitive Malaria Suitability — Africa
- **Title**: Future malaria environmental suitability in Africa is sensitive to hydrology
- **Authors**: Smith MW, Willis T, Mroz E, et al.
- **Published**: 2024, Science
- **Key findings**: Weighted ensemble of global hydrological + climate models predicts net decrease in malaria-suitable areas from 2025 onward. Hydrology-based estimates show greater sensitivity to RCP scenarios than precipitation-only estimates. Precipitation thresholds are poor proxies for breeding habitat; process-based hydrology gives different, more complex transmission patterns.
- **Relevance**: **Critical finding for MalariaSentinel**: hydrological process-based modeling gives fundamentally different projections than precipitation-only approaches. Should inform our environmental suitability module.
- **URL**: https://doi.org/10.1126/science.adq4567 (Science 384, 697-703)

---

## 5. Intervention Evaluation and Targeting

### 5.1 Pyrethroid-Pyrrole ITN Epidemiological Benefit
- **Title**: The epidemiological benefit of pyrethroid–pyrrole insecticide treated nets against malaria
- **Authors**: Churcher TS et al.
- **Published**: 2024, Lancet (via PMC)
- **Key findings**: Individual-based model validated against CRTs in Benin and Tanzania. Pyrethroid-pyrrole nets reduce prevalence by 25–60% in moderate transmission (vs. 15–45% for pyrethroid-only). MINT (Malaria Intervention Tool) interface allows NMPs to explore budget-optimal intervention allocation across regions with different characteristics.
- **Relevance**: MINT interface concept is directly relevant to MalariaSentinel's intervention optimization layer. Model parameterized for diverse settings.
- **URL**: https://pmc.ncbi.nlm.nih.gov/articles/PMC11584316/

### 5.2 ITN Effectiveness Cascade — Tanzania
- **Title**: Cascades of effectiveness of new-generation insecticide-treated nets against malaria
- **Authors**: Champagne C, Lemant J, Assenga A, et al.
- **Published**: February 2025 (preprint)
- **Key findings**: Quantifies loss of ITN impact from entomological efficacy to population-level effectiveness across 5 factors: entomological efficacy, functional survival, usage at distribution, insecticidal durability, and in-bed exposure. Main drivers of loss: imperfect usage (10–12 point drop) and in-bed exposure (8–10 point drop). Interactive dashboard for setting-specific product selection.
- **Relevance**: Cascade framework is essential for MalariaSentinel's intervention effectiveness modeling — it's not just about the tool, but how it's used.
- **URL**: https://doi.org/10.1101/2025.02.07.25321565

### 5.3 Entomological Surveillance Planning — 3-Country Pilot
- **Title**: Evaluation of a digital entomological surveillance planning tool for malaria vector control
- **Published**: March 2025, PLOS ONE
- **Key findings**: eSPT piloted in Ethiopia, Malawi, Mozambique. Improved surveillance planning knowledge and self-efficacy. Supports devolution of vector control planning to district level. Recommends mobile-device compatibility for field use.
- **Relevance**: Operational model for MalariaSentinel's field-facing decision support tools.
- **URL**: https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0303915

### 5.4 Human-Vector Behavioral Overlap — Mozambique
- **Title**: Overlaying human and mosquito behavioral data to estimate residual exposure
- **Authors**: Fernandez Montoya L, et al.
- **Published**: 2021, PLOS ONE
- **Key findings**: In Magude district (combined IRS + LLINs), An. arabiensis responsible for >74% of residual exposure. LLINs averted 39.2% of exposure at observed usage levels; potential protection if all used nets: much higher. Exposure varies by season, age, and gender. Five vector species with distinct biting behaviors.
- **Relevance**: Demonstrates importance of behavioral data integration for understanding residual transmission — critical for MalariaSentinel's intervention gap analysis.
- **URL**: https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0270882

### 5.5 Microstratification for Elimination — Malawi
- **Title**: Defining health facility catchment areas for malaria microstratification using routine data
- **Authors**: Kalonde PK, et al.
- **Published**: August 2025
- **Key findings**: Delineated health facility catchment areas using road network, land cover, elevation, and walking speeds. Combined with DHIS2 routine data for facility-level burden stratification in Balaka district. High-burden facilities identified for targeted intervention. Approach generalizable across Malawi.
- **Relevance**: Demonstrates operational microstratification using routine data — directly applicable to MalariaSentinel's targeting layer.
- **URL**: https://doi.org/10.21203/rs.3.rs-6924841/v1

---

## Cross-Cutting Themes for MalariaSentinel

### Theme 1: Convergence on Hybrid Modeling
The field is moving toward **hybrid approaches** combining mechanistic ABMs with statistical/ML models. Walker et al. (2026) embed suitability maps into ABMs; Golumbeanu et al. (2024) interface bionomics packages with compartmental models; Onimisi (2025) uses ML for spatial risk while mechanistic models handle dynamics. **MalariaSentinel should adopt this hybrid architecture.**

### Theme 2: Operational SDSS Proving Value
CIMS (Bioko Island) and eSPT (Ethiopia/Malawi/Mozambique) demonstrate that digital SDSS platforms improve operational outcomes when they provide real-time, fine-granularity data to field teams. **Key success factors**: real-time data processing, local adaptation, and mobile accessibility.

### Theme 3: Hydrology > Precipitation
Smith et al. (2024, Science) provides definitive evidence that precipitation-based suitability estimates are fundamentally limited. Process-based hydrology gives different, more complex transmission patterns and greater sensitivity to climate scenarios. **MalariaSentinel should integrate hydrological process modeling, not just precipitation thresholds.**

### Theme 4: Intervention Cascades Matter
Champagne et al. (2025) shows that tool-level efficacy ≠ population-level effectiveness. The gap is driven by usage, exposure timing, and durability. **MalariaSentinel's intervention module must model the full cascade, not just entomological impact.**

### Theme 5: Multi-Species Reality
Multiple papers (Rakotoarison 2025, Gervas 2026, Fernandez Montoya 2021) emphasize that malaria transmission involves multiple Anopheles species with different behaviors, resistance profiles, and intervention responses. **MalariaSentinel must support multi-vector parameterization.**

---

## Key Tools & Platforms Referenced

| Tool | Type | Relevance |
|------|------|-----------|
| EMOD (InstituteforDiseaseModeling) | ABM platform | Intervention sequencing; resistance dynamics |
| AnyLogic | ABM platform | Multi-paradigm modeling; GIS integration |
| OpenMalaria | Individual-based model | Intervention impact; vectorial capacity |
| MINT (Malaria Intervention Tool) | Decision support interface | Budget-optimal intervention allocation |
| AnophelesModel (R package) | Bionomics + intervention effects | Species-specific parameterization |
| Google Earth Engine | Geospatial computation | Environmental layer generation |
| INLA/R-INLA | Bayesian spatial statistics | Risk mapping with spatial autocorrelation |
| Ocelet | Spatial dynamics language | Population dynamics simulation |
| CIMS | Real-time SDSS | IRS operational management |
| eSPT | Digital surveillance planning | Vector control decision support |

---

## Gaps and Opportunities for MalariaSentinel

1. **No unified platform** exists that combines suitability mapping, ABM transmission dynamics, intervention cascades, and decision support in one framework. MalariaSentinel can fill this gap.

2. **Seasonal agricultural practices** (rice cultivation calendars) significantly affect mosquito populations but are rarely modeled explicitly. MalariaSentinel should integrate agricultural calendars as a first-class input.

3. **Urban malaria** is understudied relative to rural settings, despite rapid urbanization across Africa. The Vanhuysse (2023) framework provides a template.

4. **Real-time integration** of DHIS2 routine data with environmental layers is technically feasible but operationally rare. MalariaSentinel should prioritize this.

5. **Climate-hydrology-malaria coupling** is the frontier (Smith et al. 2024). MalariaSentinel should adopt hydrological process models rather than precipitation thresholds.

---

## References (DOIs)

1. 10.1186/s12936-026-05821-3 — Mfala et al. 2026 (SMC ABM, Tanzania)
2. 10.1186/s12915-024-01915-z — Ibrahim et al. 2024 (IR dynamics)
3. 10.1186/s12879-025-11412-5 — Senegal hazard-vulnerability risk mapping
4. 10.1186/s12936-023-04527-0 — Vanhuysse et al. 2023 (Urban malaria, Dakar)
5. 10.1371/journal.pdig.0000025 — García et al. 2022 (CIMS SDSS, Bioko)
6. 10.1371/journal.pone.0303915 — eSPT evaluation 2025
7. 10.1371/journal.pone.0235697 — Frake et al. 2020 (GEE suitability, Malawi)
8. 10.1371/journal.pcbi.1014004 — Angelakis et al. 2026 (SpatPOMP, Kenya)
9. 10.1371/journal.pcbi.1008121 — Selvaraj et al. 2020 (Vector genetics ABM)
10. 10.1016/j.ecolmodel.2023.110547 — Khelifa & El Saadi 2024 (ABM aquatic habitats)
11. 10.17485/ijst/v17i43.2133 — Mfala et al. 2024 (ABM house quality, Tanzania)
12. 10.1371/journal.pcbi.1011609 — Golumbeanu et al. 2024 (AnophelesModel R)
13. 10.1186/s12942-025-00424-8 — Rakotoarison et al. 2025 (Anopheles dynamics, Madagascar)
14. 10.1186/s12942-025-00408-8 — Tanzania Bayesian spatio-temporal 2025
15. 10.1186/s12936-026-06033-5 — Benin risk mapping 2026
16. Science 384, 697-703 (2024) — Smith et al. Hydrology-malaria suitability
17. PMC11584316 — Churcher et al. 2024 (Pyrethroid-pyrrole ITNs)
18. 10.1101/2025.02.07.25321565 — Champagne et al. 2025 (ITN cascade)
19. 10.1371/journal.pone.0270882 — Fernandez Montoya et al. 2021 (Residual exposure, Mozambique)
20. 10.21203/rs.3.rs-6924841/v1 — Kalonde et al. 2025 (Microstratification, Malawi)
21. 10.64898/2026.03.05.26347588 — Gervas et al. 2026 (EMOD ITN transition, Tanzania)
22. 10.64898/2025.12.14.25342244 — Onimisi 2025 (ML risk mapping, Nigeria)

---

*Generated by MalariaSentinel Research Harness — Phase 1 (Search)*
