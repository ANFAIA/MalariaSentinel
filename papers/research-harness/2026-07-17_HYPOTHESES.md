# Research Hypotheses: Malaria ABM, Geospatial Analysis & SDSS

**Generated**: 2026-07-17  
**Harness Phase**: Hypothesize (Phase 4/4)  
**Source**: Synthesis of 25+ papers (2020–2026) across ABM, SDSS, vector dynamics, risk mapping, and intervention evaluation  

---

## New Hypotheses (from this synthesis cycle)

### H6: Integrating hydrological process modeling (flow accumulation + soil moisture) into the suitability module changes predicted transmission hotspots by >30% compared to precipitation-only models

**Knowledge bridge**: Smith et al. (2024, Science) — hydrology-sensitive malaria suitability ↔ current MalariaSentinel suitability module (precipitation-based)

**Rationale**: Smith et al. (2024) demonstrated that precipitation thresholds are poor proxies for breeding habitat. Process-based hydrology captures surface water persistence, groundwater-fed habitats, and flood recession zones that precipitation alone misses. In Ghana, the Volta basin's complex hydrology (flood plains, irrigation schemes, dam-controlled flows) creates breeding habitats that don't correlate with local rainfall. The current suitability model uses precipitation and temperature but not hydrological processes.

**Testing approach**: 
1. Build a hydrological suitability layer using SRTM DEM + flow accumulation + SoilGrids moisture data in GEE
2. Compare predicted suitable areas against the current precipitation-only layer for Ghana
3. Validate against PMI vector survey data (larval habitat locations)
4. Measure hotspot displacement: which districts shift in/out of "high suitability" between the two approaches?

**Expected impact**: If >30% of predicted hotspots change, the Centinela's intervention targeting would be fundamentally different under hydrological vs. precipitation-based suitability. This would justify investing in process-based hydrology as a core capability.

---

### H7: A neural network emulator trained on Ghana-specific ABM outputs achieves <5% RMSE for prevalence prediction while reducing computation time by 100×

**Knowledge bridge**: Mondal et al. (2025) — ML emulator for EMOD across 8 African sites ↔ MalariaSentinel's U-Net surrogate (currently trained on synthetic data)

**Rationale**: Mondal et al. (2025) demonstrated transferable neural network emulation of EMOD across 8 African sites with leave-one-out validation. Their emulator reduced computation from hours to seconds. MalariaSentinel's U-Net surrogate is trained on synthetic simulation data but hasn't been validated against field-observed prevalence. The question is whether a Ghana-specific emulator can achieve the same accuracy as the pan-African model.

**Testing approach**:
1. Generate 10,000 ABM simulations varying: ITN coverage (0–100%), IRS coverage (0–50%), temperature anomaly (±2°C), rainfall anomaly (±30%), species composition (An. gambiae s.s. vs. arabiensis ratio)
2. Train a neural network emulator on 80% of simulations
3. Validate on 20% held-out + DHS 2019 Ghana prevalence data
4. Measure: RMSE, MAE, computation time ratio

**Expected impact**: If validated, the emulator enables real-time scenario evaluation — "what happens to prevalence if we increase ITN coverage in Northern Region by 20%?" — which is the core value proposition of the Centinela SDSS.

---

### H8: Jointly modeling vector abundance and human incidence (Gbaguidi 2026 approach) identifies different hotspots than incidence-only mapping, and these "vector-driven" hotspots require different interventions

**Knowledge bridge**: Gbaguidi et al. (2026) — joint vector-incidence spatial modeling ↔ current MalariaSentinel risk mapping (incidence-only)

**Rationale**: Gbaguidi et al. (2026) found that An. funestus showed stronger spatial correlation with incidence than An. gambiae in Benin. Joint modeling revealed hotspots where vector abundance was high but incidence was low (high vector capacity, low human exposure) and vice versa. These two types of hotspots require fundamentally different interventions: vector-driven hotspots need larval source management or IRS, while exposure-driven hotspots need ITNs and housing improvement.

**Testing approach**:
1. Compile PMI vector survey data (species-specific abundance) + DHIS2 incidence data for Ghana
2. Fit joint Gaussian spatial model (Gbaguidi approach) using SPDE-INLA
3. Compare hotspot classification: (a) incidence-only, (b) vector-only, (c) joint model
4. For each hotspot type, identify the optimal intervention mix using the cascade framework

**Expected impact**: If joint modeling identifies distinct hotspot types, MalariaSentinel's intervention targeting module should use joint risk surfaces rather than incidence alone. This would improve resource allocation efficiency.

---

### H9: Encoding the ITN effectiveness cascade (Champagne 2025) into the ABM reduces simulated intervention impact by 30–50% compared to simple coverage modeling, but produces more accurate predictions against DHS data

**Knowledge bridge**: Champagne et al. (2025) — 5-factor ITN effectiveness cascade ↔ current ABM intervention modeling (binary on/off)

**Rationale**: Most ABMs model ITN intervention as "X% of population protected." Champagne et al. (2025) showed that the gap between entomological efficacy and population-level effectiveness is driven by: (1) imperfect usage (10–12 point drop), (2) exposure timing mismatch (8–10 point drop), (3) functional survival of nets, (4) insecticidal durability, and (5) in-bed exposure windows. The net effect is that "80% ITN coverage" might translate to only 40–50% actual protection. Current ABMs systematically overestimate intervention impact.

**Testing approach**:
1. Parameterize the 5-factor cascade using Ghana ITN survey data (DHS usage rates, net durability studies)
2. Run ABM with: (a) simple coverage model, (b) cascade model
3. Compare simulated prevalence trajectories against DHS 2010, 2015, 2019 observed values
4. Measure: which model better matches observed prevalence declines?

**Expected impact**: If the cascade model produces more accurate predictions, MalariaSentinel's intervention optimization would be fundamentally different — it would optimize for usage, durability, and timing, not just coverage numbers. This has direct operational implications for ITN distribution strategies.

---

### H10: Agricultural calendar coupling (rice cultivation cycles) explains 15–25% of seasonal variance in vector abundance in northern Ghana that climate variables alone cannot capture

**Knowledge bridge**: Rakotoarison et al. (2025) — agricultural calendar integration in Madagascar ↔ MalariaSentinel seasonal dynamics module (climate-only)

**Rationale**: Rakotoarison et al. (2025) showed that integrating rice cultivation calendars reduced overestimation of host-seeking females in Madagascar. In northern Ghana, rice is cultivated in major (June–September) and minor (October–November) seasons. Flooding of rice paddies creates temporary breeding habitats that don't correlate with local rainfall — they're driven by irrigation schedules and farmer behavior. The current climate-only model would miss these anthropogenic breeding pulses.

**Testing approach**:
1. Obtain Ghana rice cultivation calendar data (Ministry of Agriculture, remote sensing of paddy flooding)
2. Build a habitat availability layer that includes: natural habitats (climate-driven) + agricultural habitats (calendar-driven)
3. Compare vector abundance predictions: (a) climate-only, (b) climate + agricultural calendar
4. Validate against PMI mosquito trap data from northern Ghana districts

**Expected impact**: If agricultural coupling explains >15% of seasonal variance, MalariaSentinel should integrate agricultural calendars as a first-class input. This would improve seasonal forecasting and enable targeted SMC timing aligned with post-harvest transmission peaks.

---

## Updated Prior Hypotheses (from papers/hypotheses.md)

The following hypotheses from the existing document remain valid and are reinforced by this synthesis:

| ID | Hypothesis | Reinforcing Evidence |
|---|---|---|
| H1 | Lag-response dynamics improve forecasting by 15% | Okiring 2021 DLNM analysis; sub-monthly dynamics matter |
| H2 | ITN/IRS layers reduce simulated prevalence by 30–60% | Onimisi 2025 (ITN as top predictor); Aduvukha 2026 |
| H3 | Species-specific thermal curves improve spatial prediction | Rakotoarison 2025 (multi-species); Golumbeanu 2024 (AnophelesModel) |
| H4 | Backward bifurcation requires 15–25% higher coverage | Gatore Sinigirira 2025 (SEIR-SEI with bistability) |
| H5 | Human mobility quantifies importation risk | Kelly 2012 (SDSS framework); Angelakis 2026 (metapopulation) |

---

## Hypothesis Priority Matrix

| Hypothesis | Impact | Feasibility | Priority |
|---|---|---|---|
| H6 (Hydrological suitability) | High | Medium (needs DEM + soil data) | **P1** |
| H7 (ML emulator validation) | Very High | High (U-Net already exists) | **P1** |
| H8 (Joint risk surfaces) | High | Medium (needs vector survey data) | **P2** |
| H9 (ITN cascade modeling) | High | High (parameterization available) | **P2** |
| H10 (Agricultural calendar) | Medium | Medium (needs crop calendar data) | **P3** |
| H1 (Lag-response dynamics) | Medium | High (climate data available) | **P2** |
| H2 (ITN/IRS intervention layers) | High | High (DHS data available) | **P1** |
| H3 (Species-specific thermal) | Medium | Low (needs entomological surveys) | **P3** |
| H4 (Backward bifurcation) | Medium | Low (theoretical, hard to validate) | **P3** |
| H5 (Human mobility) | High | Low (needs mobility data) | **P3** |

---

## Recommended Testing Order

**Phase A (M1-M2, immediate)**: H7 (emulator validation) + H2 (ITN/IRS layers) — highest feasibility, highest impact. These use existing data and code infrastructure.

**Phase B (M3-M4, near-term)**: H6 (hydrological suitability) + H9 (ITN cascade) + H1 (lag-response) — requires new data layers but well-established methods.

**Phase C (M5-M6, medium-term)**: H8 (joint risk surfaces) + H10 (agricultural calendar) + H3 (species-specific) + H5 (human mobility) + H4 (backward bifurcation) — requires new data collection or novel methodological development.

---

*Generated by MalariaSentinel Research Harness — Phase 4 (Hypothesize)*
