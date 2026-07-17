# Research Hypotheses for MalariaSentinel

**Generated**: 2026-07-17
**Harness Phase**: Hypothesize (Phase 4/4)
**Scope**: 15 hypotheses (H1–H15) across ABM, geospatial analysis, SDSS, vector dynamics, risk mapping, and intervention evaluation
**Source**: Synthesis of 37+ papers (2000–2026) + knowledge graph audit

---

## Part I: Original Hypotheses (H1–H5)

These hypotheses were generated in the initial research cycle and form the foundational layer of the MalariaSentinel research programme.

---

### H1: Encoding DLNM-derived lag-response dynamics into the ABM climate module improves short-term transmission forecasting accuracy by at least 15%

**Knowledge bridge:** Environmental lag dynamics (Okiring 2021) ↔ ABM climate parameterization (current MalariaSentinel ABM)

**Supporting evidence:** Okiring 2021's distributed lag nonlinear model (DLNM) analysis in Uganda demonstrates that temperature effects on malaria incidence peak at lag 2 weeks (IRR 2.00, 95% CI 1.53–2.61), with cumulative IRR reaching 8.16 at lag 4. Rainfall peaks at lag 0 (IRR 1.24) but NDVI effects peak at lag 2 (IRR 1.31, cumulative 1.57 at lag 4). The current ABM uses instantaneous climate values in its suitability-to-carrying-capacity calculation, ignoring these well-characterized delayed responses. Granger causality tests confirmed that all three covariates have predictive power for IRR, establishing that lag structure carries genuine signal rather than mere correlation.

**Testing approach:** Extend the ABM's `SuitabilityModel` class to accept lagged climate rasters (1–4 week offsets). Run parallel 52-week simulations: (a) baseline with instantaneous climate, (b) with 2-week temperature lag + 0-week rainfall lag, (c) with full Okiring lag structure (temp lag 2, rain lag 0, NDVI lag 2). Evaluate against CHIRPS/MODIS-derived hindcasts using RMSE and skill score relative to persistence. Retrain the U-Net surrogate on lagged-input simulation data to test whether the surrogate can learn lag dynamics more efficiently than the ABM encodes them.

**Expected impact:** If confirmed, lag-aware climate forcing would produce actionable 2–4 week nowcasts of transmission intensity, enabling targeted reactive interventions (e.g., focal MDA or reactive case detection) timed to peak risk windows rather than current conditions.

---

### H2: Adding ITN/IRS intervention layers as dynamic ABM parameters reduces simulated prevalence by 30–60%, aligning model outputs with DHS-observed prevalence declines in Ghana

**Knowledge bridge:** Intervention coverage as dominant predictor (Onimisi 2025) ↔ ABM intervention dynamics (currently absent)

**Supporting evidence:** Onimisi 2025's machine learning framework across 34 years of DHS/MIS data in Nigeria identifies ITN coverage as the single most important predictor of malaria prevalence (feature importance 0.1285), exceeding all climate variables. Cross-year validation reveals temporal non-stationarity (accuracy drops from 62% to 37% to 40% across validation years), suggesting that intervention coverage drives regime shifts that climate alone cannot explain. Aduvukha 2026 independently finds that bed net use is the most influential predictor of biting probability in Cameroon, reinforcing the centrality of vector-control interventions. The current ABM has no mechanism to model these dynamics.

**Testing approach:** Introduce a `CoverageLayer` module that ingests DHS/MIS-derived ITN and IRS coverage rasters (available from the MalariaAtlas R package and PMI datasets). Parameterize species-specific bite-rate reductions: An. gambiae s.s. (high endophily → strong ITN effect), An. arabiensis (zoophilic/exophagic → weak ITN effect). Run counterfactual simulations: (a) zero coverage, (b) Ghana 2015 coverage (~50% ITN), (c) Ghana 2020 coverage (~65% ITN). Compare simulated prevalence trajectories against DHS observed values. Use the U-Net to learn the coverage→prevalence transfer function from ABM sweeps.

**Expected impact:** A validated intervention module would allow the Centinela to forecast the impact of coverage gaps and target distribution campaigns to areas where coverage falls below the effective threshold for transmission suppression.

---

### H3: Splitting the vector suitability model into species-specific thermal response curves improves spatial prediction accuracy for high-biodiversity regions

**Knowledge bridge:** Multi-species vector ecology (Perplexity investigations, An. gambiae complex) ↔ environmental suitability modeling (current MalariaSentinel suitability module)

**Supporting evidence:** The An. gambiae complex comprises at least 8 cryptic species (including An. gambiae s.s., An. coluzzii, and An. arabiensis) with distinct thermal optima, habitat preferences, and behavioral profiles. An. funestus produces up to 90% of infective bites in East/Southern Africa and has different breeding habitat requirements (permanent/semi-permanent water bodies) compared to An. gambiae s.s. (ephemeral puddles). An. arabiensis is more zoophilic and exophagic, making it less affected by indoor interventions. The current suitability model applies a single Mordecai 2013 thermal response curve uniformly, treating the vector community as monospecific. Gatore Sinigirira 2025 further demonstrates that optimal transmission occurs within T = 20–25°C, but this range likely differs across species.

**Testing approach:** Decompose the suitability model into species-specific components using published thermal response parameters: An. gambiae s.s. (lower thermal limit ~18°C, optimum ~25°C, upper ~34°C), An. arabiensis (wider thermal tolerance, optimum ~27°C), An. funestus (narrower breeding habitat filter). Generate species-specific suitability maps using the existing environmental layers. Validate against entomological survey data (Ifakara Health Institute and PMI vector surveillance datasets) where species composition is known. Measure whether multi-species suitability improves AUC over monospecific suitability for districts with known mixed-species populations.

**Expected impact:** Species-aware suitability mapping would enable targeted intervention design: ITN-heavy strategies where An. gambiae s.s. dominates, larval source management where An. funestus breeding sites are identifiable, and IRS or livestock-associated approaches where An. arabiensis predominates.

---

### H4: Incorporating backward bifurcation dynamics into the ABM's transmission model reveals that sub-R₀ elimination targets require 15–25% higher intervention coverage than classical thresholds predict

**Knowledge bridge:** Backward bifurcation theory (Gatore Sinigirira 2025) ↔ elimination threshold modeling (MalariaSentinel SDSS elimination targeting)

**Supporting evidence:** Gatore Sinigirira 2025's SEIR-SEI model for Burundi demonstrates that backward bifurcation can occur in malaria transmission dynamics — a regime where R₀ < 1 does not guarantee disease elimination because endemic equilibria persist below the classical threshold. Their model, integrating temperature, rainfall, and NDVI, shows R₀ is projected to increase through 2070, meaning elimination windows may close. The Centinela currently uses classical R₀ > 1 as its elimination threshold criterion, with no mechanism to detect or model bistable dynamics. Kleinschmidt 2000's spatial logistic regression framework and Gwitira 2020's spatio-temporal clustering analysis both implicitly assume monotonic dose-response between environmental risk and prevalence, which backward bifurcation violates.

**Testing approach:** Implement a bistable transmission module in the ABM that tracks both the disease-free equilibrium and the endemic equilibrium. Parameterize using the Gatore Sinigirira formulation: extend the current SIS/SEI compartmental model to include a nonlinear force of infection that permits two stable states. Sweep intervention coverage (0–100%) and measure the "hysteresis width" — the gap between the coverage needed to eliminate from endemic equilibrium vs. the coverage at which reintroduction causes re-emergence. Compare against classical single-threshold predictions. Use the U-Net to learn the bistable transfer function and identify spatial regions where hysteresis is most pronounced in Ghana.

**Expected impact:** If backward bifurcation is relevant in Ghana (likely in areas with An. funestus-driven transmission), elimination programs would need to sustain higher coverage than current targets specify, and "elimination achieved" status would require monitoring for re-emergence even after R₀ dips below 1.

---

### H5: Coupling human mobility data with the ABM quantifies importation risk and identifies which districts require cross-border surveillance coordination for sustained elimination

**Knowledge bridge:** Human mobility and importation risk (Kelly 2012 SDSS framework) ↔ ABM population dynamics (currently absent)

**Supporting evidence:** Kelly 2012's reference SDSS framework explicitly identifies human movement as a critical input for malaria elimination decision-making, noting that cross-border migration drives reintroduction in settings approaching elimination. In Ghana, internal migration between northern savanna zones (higher transmission) and southern urban areas creates importation corridors that sustain low-level transmission even where local vector capacity is declining. The current ABM models mosquito populations and environmental suitability but contains no human agents, making it structurally incapable of capturing importation dynamics. Onimisi 2025's finding that temporal non-stationarity in prevalence (62%→37%→40%) may partly reflect mobile populations moving between high- and low-transmission zones further motivates this gap.

**Testing approach:** Integrate mobile phone mobility data (MalariaSIM consortium or Ghana Statistical Service migration surveys) as a human movement layer in the ABM. Define districts as nodes and movement volumes as edge weights. Introduce infected agents entering from high-prevalence source districts at empirically calibrated rates. Measure: (a) the prevalence threshold below which importation becomes the dominant transmission sustainer, (b) which origin-destination pairs pose the highest reintroduction risk, (c) whether reactive case detection at mobility hubs (markets, transport nodes) outperforms uniform surveillance. Validate against Ghana Health Service district-level incidence data where importation events are documented.

**Expected impact:** An importation-aware model would enable the Centinela to prioritize cross-district and cross-border coordination, target surveillance at mobility corridors rather than just high-prevalence zones, and set realistic elimination timelines that account for reintroduction pressure.

---

## Part II: Synthesis-Generated Hypotheses (H6–H10)

These hypotheses were generated from the 2026-07-17 literature synthesis cycle, bridging advances in hydrological modeling, neural network emulation, joint risk surfaces, ITN effectiveness cascades, and agricultural calendar integration.

---

### H6: Integrating hydrological process modeling (flow accumulation + soil moisture) into the suitability module changes predicted transmission hotspots by >30% compared to precipitation-only models

**Knowledge bridge:** Smith et al. (2024, Science) — hydrology-sensitive malaria suitability ↔ current MalariaSentinel suitability module (precipitation-based)

**Supporting evidence:** Smith et al. (2024) demonstrated that precipitation thresholds are poor proxies for breeding habitat. Process-based hydrology captures surface water persistence, groundwater-fed habitats, and flood recession zones that precipitation alone misses. In Ghana, the Volta basin's complex hydrology (flood plains, irrigation schemes, dam-controlled flows) creates breeding habitats that don't correlate with local rainfall. The current suitability model uses precipitation and temperature but not hydrological processes.

**Testing approach:**
1. Build a hydrological suitability layer using SRTM DEM + flow accumulation + SoilGrids moisture data in GEE
2. Compare predicted suitable areas against the current precipitation-only layer for Ghana
3. Validate against PMI vector survey data (larval habitat locations)
4. Measure hotspot displacement: which districts shift in/out of "high suitability" between the two approaches?

**Expected impact:** If >30% of predicted hotspots change, the Centinela's intervention targeting would be fundamentally different under hydrological vs. precipitation-based suitability. This would justify investing in process-based hydrology as a core capability.

---

### H7: A neural network emulator trained on Ghana-specific ABM outputs achieves <5% RMSE for prevalence prediction while reducing computation time by 100×

**Knowledge bridge:** Mondal et al. (2025) — ML emulator for EMOD across 8 African sites ↔ MalariaSentinel's U-Net surrogate (currently trained on synthetic data)

**Supporting evidence:** Mondal et al. (2025) demonstrated transferable neural network emulation of EMOD across 8 African sites with leave-one-out validation. Their emulator reduced computation from hours to seconds. MalariaSentinel's U-Net surrogate is trained on synthetic simulation data but hasn't been validated against field-observed prevalence. The question is whether a Ghana-specific emulator can achieve the same accuracy as the pan-African model.

**Testing approach:**
1. Generate 10,000 ABM simulations varying: ITN coverage (0–100%), IRS coverage (0–50%), temperature anomaly (±2°C), rainfall anomaly (±30%), species composition (An. gambiae s.s. vs. arabiensis ratio)
2. Train a neural network emulator on 80% of simulations
3. Validate on 20% held-out + DHS 2019 Ghana prevalence data
4. Measure: RMSE, MAE, computation time ratio

**Expected impact:** If validated, the emulator enables real-time scenario evaluation — "what happens to prevalence if we increase ITN coverage in Northern Region by 20%?" — which is the core value proposition of the Centinela SDSS.

---

### H8: Jointly modeling vector abundance and human incidence (Gbaguidi 2026 approach) identifies different hotspots than incidence-only mapping, and these "vector-driven" hotspots require different interventions

**Knowledge bridge:** Gbaguidi et al. (2026) — joint vector-incidence spatial modeling ↔ current MalariaSentinel risk mapping (incidence-only)

**Supporting evidence:** Gbaguidi et al. (2026) found that An. funestus showed stronger spatial correlation with incidence than An. gambiae in Benin. Joint modeling revealed hotspots where vector abundance was high but incidence was low (high vector capacity, low human exposure) and vice versa. These two types of hotspots require fundamentally different interventions: vector-driven hotspots need larval source management or IRS, while exposure-driven hotspots need ITNs and housing improvement.

**Testing approach:**
1. Compile PMI vector survey data (species-specific abundance) + DHIS2 incidence data for Ghana
2. Fit joint Gaussian spatial model (Gbaguidi approach) using SPDE-INLA
3. Compare hotspot classification: (a) incidence-only, (b) vector-only, (c) joint model
4. For each hotspot type, identify the optimal intervention mix using the cascade framework

**Expected impact:** If joint modeling identifies distinct hotspot types, MalariaSentinel's intervention targeting module should use joint risk surfaces rather than incidence alone. This would improve resource allocation efficiency.

---

### H9: Encoding the ITN effectiveness cascade (Champagne 2025) into the ABM reduces simulated intervention impact by 30–50% compared to simple coverage modeling, but produces more accurate predictions against DHS data

**Knowledge bridge:** Champagne et al. (2025) — 5-factor ITN effectiveness cascade ↔ current ABM intervention modeling (binary on/off)

**Supporting evidence:** Most ABMs model ITN intervention as "X% of population protected." Champagne et al. (2025) showed that the gap between entomological efficacy and population-level effectiveness is driven by: (1) imperfect usage (10–12 point drop), (2) exposure timing mismatch (8–10 point drop), (3) functional survival of nets, (4) insecticidal durability, and (5) in-bed exposure windows. The net effect is that "80% ITN coverage" might translate to only 40–50% actual protection. Current ABMs systematically overestimate intervention impact.

**Testing approach:**
1. Parameterize the 5-factor cascade using Ghana ITN survey data (DHS usage rates, net durability studies)
2. Run ABM with: (a) simple coverage model, (b) cascade model
3. Compare simulated prevalence trajectories against DHS 2010, 2015, 2019 observed values
4. Measure: which model better matches observed prevalence declines?

**Expected impact:** If the cascade model produces more accurate predictions, MalariaSentinel's intervention optimization would be fundamentally different — it would optimize for usage, durability, and timing, not just coverage numbers. This has direct operational implications for ITN distribution strategies.

---

### H10: Agricultural calendar coupling (rice cultivation cycles) explains 15–25% of seasonal variance in vector abundance in northern Ghana that climate variables alone cannot capture

**Knowledge bridge:** Rakotoarison et al. (2025) — agricultural calendar integration in Madagascar ↔ MalariaSentinel seasonal dynamics module (climate-only)

**Supporting evidence:** Rakotoarison et al. (2025) showed that integrating rice cultivation calendars reduced overestimation of host-seeking females in Madagascar. In northern Ghana, rice is cultivated in major (June–September) and minor (October–November) seasons. Flooding of rice paddies creates temporary breeding habitats that don't correlate with local rainfall — they're driven by irrigation schedules and farmer behavior. The current climate-only model would miss these anthropogenic breeding pulses.

**Testing approach:**
1. Obtain Ghana rice cultivation calendar data (Ministry of Agriculture, remote sensing of paddy flooding)
2. Build a habitat availability layer that includes: natural habitats (climate-driven) + agricultural habitats (calendar-driven)
3. Compare vector abundance predictions: (a) climate-only, (b) climate + agricultural calendar
4. Validate against PMI mosquito trap data from northern Ghana districts

**Expected impact:** If agricultural coupling explains >15% of seasonal variance, MalariaSentinel should integrate agricultural calendars as a first-class input. This would improve seasonal forecasting and enable targeted SMC timing aligned with post-harvest transmission peaks.

---

## Part III: New Gap-Bridging Hypotheses (H11–H15)

These hypotheses address the most critical gaps identified in the knowledge graph audit: the absence of extreme weather event response, routine surveillance integration, sub-national tailoring, multi-species intervention response profiling, and spatial resource optimization. They bridge literature areas that H1–H10 do not cover.

---

### H11: Integrating extreme weather event detection (flood/drought) as a real-time risk modifier reduces malaria nowcast lag by 2–4 weeks compared to climate-average-based suitability

**Knowledge bridge:** Symons et al. (2026, Nature) — extreme weather drives 79% of additional malaria cases ↔ Eudaric et al. (2026) — 12 million Pf-exposed individuals in flood zones ↔ current MalariaSentinel climate-average suitability module

**Supporting evidence:** Symons et al. (2026) provide the definitive decomposition of future malaria burden: under current control levels, 123 million additional cases and 532,000 additional deaths are projected for 2024–2050, and **79% of these additional cases are attributable to extreme weather events** (floods, droughts, heatwaves), not gradual climate trends. Eudaric et al. (2026) independently demonstrate that flood exposure is the primary driver of malaria burden in 492 flood-prone zones across 38 African countries, with ~12 million Pf-diagnosed individuals exposed to flooding. The critical implication is that malaria transmission responds to **discrete extreme events**, not smoothly varying climate averages. The current MalariaSentinel suitability module uses monthly CHIRPS precipitation and ERA5 temperature as continuous covariates — it is structurally blind to the 3–6 week post-flood transmission surge that Symons and Eudaric document. Ghana's Volta Basin, coastal lowlands, and northern savanna floodplains are all flood-prone, yet no component of the Centinela detects or responds to flood events.

**Testing approach:**
1. Acquire GloFAS flood extent maps and CHIRPS daily precipitation anomalies for Ghana (2010–2024)
2. Build an `ExtremeEventLayer` that classifies districts into flood/drought/normal status using GloFAS thresholds and CHIRPS anomaly z-scores
3. Extend the suitability module to apply a multiplicative risk modifier during and after extreme events: flood (+40–80% breeding habitat for 4–8 weeks), drought (−30–50% for 8–12 weeks), calibrated from Eudaric et al.'s continental coefficients
4. Run parallel 52-week nowcasts: (a) baseline climate-average suitability, (b) climate-average + extreme event modifier
5. Validate against DHIS2 weekly case reports: measure lead time improvement (weeks earlier that case surges are predicted) and RMSE reduction during extreme event periods
6. Use the U-Net to learn the extreme-event-to-incidence transfer function from ABM simulations forced with flood/drought scenarios

**Expected impact:** If extreme event detection improves nowcast accuracy by >15% and provides 2–4 weeks of additional lead time, MalariaSentinel would enable **pre-positioning of emergency response resources** (MDA stockpiles, rapid diagnostic test shipments, reactive case detection teams) before post-flood surges peak. This directly addresses the single largest driver of future malaria burden identified by Symons et al. (2026).

---

### H12: Classifying Ghana's districts into transmission archetypes (Bertozzi-Villa 2024 approach) reveals that optimal intervention packages differ by >40% across archetypes, justifying sub-national tailoring per WHO SNT recommendations

**Knowledge bridge:** Bertozzi-Villa et al. (2024) — archetypes framework for intervention impact ↔ PATH/CHAI SNT Toolbox (2025) — sub-national tailoring for elimination ↔ current MalariaSentinel (uniform intervention recommendations)

**Supporting evidence:** Bertozzi-Villa et al. (2024) demonstrated that malaria transmission environments can be classified into distinct archetypes based on epidemiological and ecological characteristics, and that intervention effectiveness varies systematically across archetypes. Their transferability framework enables impact estimation in data-poor settings by borrowing strength from data-rich settings within the same archetype. The SNT Toolbox (PATH/CHAI/IDM, 2025) operationalizes this concept as a country-owned digital platform for optimizing intervention allocation through WHO-recommended Sub-National Tailoring (SNT). Ghana's malaria landscape is highly heterogeneous: northern savanna districts have high perennial transmission with An. gambiae s.s. dominance; coastal districts have lower, seasonal transmission; urban centers (Accra, Kumasi) have low-endemic, imported-case-driven dynamics; and the Volta Basin has flood-modulated transmission. Despite this heterogeneity, the Centinela currently treats all districts uniformly — the same intervention recommendation applies regardless of local transmission archetype. This is a structural limitation that SNT is designed to overcome.

**Testing approach:**
1. Compile a district-level feature matrix for all 260 Ghana districts: prevalence (DHS/MIS), incidence (DHIS2), ITN coverage, IRS coverage, species composition (PMI surveys), climate zone, urbanization rate, health facility density, flood exposure
2. Apply the Bertozzi-Villa archetypes classification (k-means or Gaussian mixture model) to identify 4–6 transmission archetypes
3. For each archetype, estimate intervention effectiveness using the Centinela's ABM: sweep ITN (0–100%), IRS (0–50%), SMC (0–80%) coverage levels
4. Identify the cost-optimal intervention package per archetype subject to budget constraints
5. Compare: (a) uniform allocation (current approach), (b) archetype-tailored allocation
6. Measure the prevalence reduction difference between (a) and (b)

**Expected impact:** If archetype-tailored allocation achieves >15% greater prevalence reduction than uniform allocation at the same budget, the Centinela should recommend archetype-specific intervention packages. This directly operationalizes the WHO SNT framework for Ghana and aligns with the SNT Toolbox's national adoption trajectory.

---

### H13: Integrating DHIS2 routine surveillance data as a dynamic calibration signal for the ABM improves 3-month prevalence forecasts by >20% compared to static parameterization

**Knowledge bridge:** García et al. (2022, CIMS/Bioko) — real-time SDSS for IRS ↔ Kalonde et al. (2025) — facility-level microstratification using routine data ↔ current MalariaSentinel (batch-only, no real-time data integration)

**Supporting evidence:** The single most critical gap in the MalariaSentinel knowledge base is the absence of real incidence data. The `inv-incidence-data-source` investigation is open and blocking M3–M4 external validation. Without real data, every model component (suitability, ABM, U-Net) is validated against itself, not against the real world. García et al. (2022) demonstrated that CIMS on Bioko Island achieved 37.7% optimal IRS coverage (vs. 17% in 2017) by processing routine surveillance data at 100×100m granularity in real time. Kalonde et al. (2025) showed that DHIS2 routine data, when combined with health facility catchment area delineation (road network + land cover + walking speeds), enables facility-level burden stratification that is operationally actionable. The SNT Toolbox (2025) similarly relies on routine surveillance as its primary data input. The Centinela currently operates in batch mode: data is ingested, models are run, outputs are generated. There is no feedback loop where incoming surveillance data recalibrates model parameters or updates risk predictions. This is a fundamental limitation for operational deployment.

**Testing approach:**
1. Acquire Ghana DHIS2 malaria case data (weekly or monthly, district-level, 2015–2024) from the Ghana Health Service
2. Build a `DHIS2DataLoader` in `mal-commonlib/` that ingests, cleans, and validates routine surveillance data (handle missing data, reporting delays, population denominators)
3. Implement a data assimilation layer: use an Ensemble Kalman Filter (EnKF) or particle filter to sequentially update ABM prevalence estimates as new DHIS2 data arrives
4. Run a 52-week forecasting experiment: (a) static parameterization (current approach), (b) EnKF-updated parameterization with monthly DHIS2 assimilation
5. Evaluate forecast skill at 1-, 2-, and 3-month horizons using CRPS, RMSE, and coverage probability
6. Test whether facility-level microstratification (Kalonde approach) improves district-level forecasts compared to district-aggregate data

**Expected impact:** If DHIS2 data assimilation improves 3-month forecast skill by >20%, the Centinela would transition from a batch planning tool to a **dynamic forecasting system** — the core value proposition for operational deployment. This closes the Kelly 2012 SDSS loop: routine HIS data enters → models are updated → decisions are produced → outcomes are monitored → data re-enters.

---

### H14: Parameterizing multi-species vector dynamics with species-specific ITN response profiles (via AnophelesModel) identifies 25–35% of Ghana districts where single-species models would recommend suboptimal intervention strategies

**Knowledge bridge:** Rakotoarison et al. (2025) — 4-species mechanistic model with agricultural calendars ↔ Fernandez Montoya et al. (2021) — behavioral overlap driving residual exposure in Mozambique ↔ Golumbeanu et al. (2024) — AnophelesModel R package for species-specific vectorial capacity ↔ current MalariaSentinel (monospecific suitability model)

**Supporting evidence:** Multiple papers converge on a critical finding: malaria transmission involves **multiple Anopheles species** with fundamentally different behaviors, intervention response profiles, and resistance dynamics. Rakotoarison et al. (2025) modeled 4 species in Madagascar with distinct thermal optima and habitat requirements, finding that agricultural calendar integration reduced overestimation of host-seeking females. Fernandez Montoya et al. (2021) showed that in Magude district (Mozambique), with combined IRS + LLINs, **An. arabiensis was responsible for >74% of residual exposure** because of its exophagic and zoophilic behavior — interventions targeting indoor-biting species (An. gambiae s.s., An. funestus) left the outdoor-biting species largely unaffected. Golumbeanu et al. (2024) developed the AnophelesModel R package that estimates species-specific vectorial capacity and intervention effects, demonstrating that An. gambiae (indoor night-biter) vs. An. farauti (outdoor evening-biter) have dramatically different ITN response profiles. The current MalariaSentinel suitability module applies a single Mordecai 2013 thermal response curve uniformly. It does not distinguish species, does not model species-specific intervention responses, and therefore cannot identify where species composition creates intervention blind spots.

**Testing approach:**
1. Acquire PMI vector survey data for Ghana: species composition (An. gambiae s.s., An. arabiensis, An. funestus, An. pharoensis), collection method (CDC light trap, human landing catch), and district-level abundance
2. Use AnophelesModel (R package) to estimate species-specific vectorial capacity and ITN/IRS response coefficients for each Ghana species
3. Build a multi-species suitability layer: generate species-specific habitat maps using existing environmental layers + species-specific thermal/breeding parameters
4. For each district, compute the species-weighted intervention response: ITN effectiveness = Σ(species_abundance × species_ITN_response) / total_abundance
5. Compare intervention recommendations: (a) single-species model (An. gambiae s.s. only), (b) multi-species model
6. Identify districts where the two models disagree on the optimal intervention mix (e.g., single-species says ITN is sufficient; multi-species says IRS or larval source management is needed)

**Expected impact:** If 25–35% of districts receive suboptimal intervention recommendations under single-species modeling, this represents a **systematic resource waste** in Ghana's malaria programme. Multi-species awareness would redirect interventions: ITN-heavy where An. gambiae s.s. dominates, IRS where An. arabiensis drives residual exposure, larval source management where An. funestus breeding sites are identifiable. This has direct operational value for Ghana's National Malaria Control Programme.

---

### H15: A spatial optimization model that allocates interventions subject to budget constraints achieves 15–25% greater prevalence reduction than uniform coverage allocation, using the U-Net as a fast forward model for scenario evaluation

**Knowledge bridge:** Gbaguidi et al. (2026) — data-driven resource optimization in Benin ↔ Churcher et al. (2024) — MINT (Malaria Intervention Tool) for budget-optimal allocation ↔ SNT Toolbox (2025) — budgeting module for resource-constrained planning ↔ current MalariaSentinel (no optimization capability)

**Supporting evidence:** The final gap in the Centinela's SDSS pipeline is the **decision output**. Kelly 2012's framework specifies that an SDSS must produce actionable recommendations, not just risk maps. Gbaguidi et al. (2026) demonstrated a data-driven approach to resource optimization in Benin using Bayesian spatial modeling, identifying where interventions would have the greatest marginal impact. Churcher et al. (2024) developed the MINT interface that allows national malaria programmes to explore budget-optimal intervention allocation across regions with different epidemiological profiles, validated against clinical trial data for pyrethroid-pyrrole nets. The SNT Toolbox (2025) includes a budgeting module that ensures resource-constrained feasibility of intervention plans. The current Centinela can generate risk maps and (once H7 is validated) run rapid scenario evaluations, but it cannot answer the question a programme officer would actually ask: **"Given a budget of $X, which districts should receive which interventions to minimize national prevalence?"** This is a constrained optimization problem that requires a fast forward model (the U-Net) and a spatial optimizer.

**Testing approach:**
1. Define the optimization problem: minimize national prevalence subject to: (a) total budget constraint, (b) per-district coverage bounds (0–100% ITN, 0–50% IRS, 0–80% SMC), (c) supply chain constraints (maximum deployment rate per quarter), (d) equity constraint (no district below minimum coverage threshold)
2. Train the U-Net surrogate on 10,000 ABM simulations (varying intervention mix across districts) to learn the district-intervention → prevalence transfer function
3. Implement a spatial optimizer using: (a) linear programming for the convex relaxation, (b) genetic algorithm or simulated annealing for the discrete allocation problem
4. Compare three allocation strategies: (a) uniform (equal coverage everywhere), (b) risk-proportional (higher coverage in higher-prevalence districts), (c) optimized (budget-constrained optimizer)
5. Measure: prevalence reduction, cost-effectiveness ratio ($ per percentage point reduction), geographic equity (Gini coefficient of coverage)
6. Validate optimized allocations against the SNT Toolbox's recommended packages for Ghana

**Expected impact:** If the optimizer achieves 15–25% greater prevalence reduction than uniform allocation at the same budget, this represents the **operational payoff** of the entire Centinela architecture. It transforms the SDSS from a descriptive tool ("here is where malaria is") into a prescriptive tool ("here is what you should do"). This is the capability that would drive adoption by Ghana's National Malaria Control Programme and international partners (PMI, WHO, Global Fund).

---

## Part IV: Cross-Cutting Analysis

### Hypothesis Dependency Graph

The 15 hypotheses form a directed acyclic graph where later hypotheses depend on infrastructure built by earlier ones:

```
H1 (lag dynamics) ─────────────────────────────┐
H2 (ITN/IRS layers) ──→ H9 (ITN cascade) ─────┤
H3 (multi-species thermal) ──→ H14 (multi-species intervention) ──→ H8 (joint risk)
H4 (backward bifurcation) ─────────────────────┤
H5 (human mobility) ──────────────────────────┤
H6 (hydrological suitability) ─────────────────┤
H7 (U-Net validation) ──→ H15 (spatial optimization)
H10 (agricultural calendar) ───────────────────┤
H11 (extreme weather) ────────────────────────┤
H12 (archetypes/SNT) ────────────────────────┤
H13 (DHIS2 calibration) ─────────────────────┘
                                                ↓
                                    OPERATIONAL SDSS
```

### Priority Matrix

| Hypothesis | Impact | Feasibility | Dependencies | Priority |
|---|---|---|---|---|
| **H13** (DHIS2 calibration) | **Critical** | High | None | **P0** — blocks all validation |
| **H2** (ITN/IRS layers) | Very High | High | None | **P0** — core SDSS capability |
| **H7** (U-Net validation) | Very High | High | H2 | **P1** — enables fast scenario eval |
| **H11** (extreme weather) | Very High | High | H1 | **P1** — addresses 79% of future burden |
| **H1** (lag dynamics) | High | High | None | **P1** — improves nowcast skill |
| **H9** (ITN cascade) | High | High | H2 | **P1** — improves intervention accuracy |
| **H12** (archetypes/SNT) | High | Medium | H2, H7 | **P2** — enables sub-national tailoring |
| **H14** (multi-species intervention) | High | Medium | H3 | **P2** — prevents resource waste |
| **H6** (hydrological suitability) | High | Medium | None | **P2** — changes hotspot predictions |
| **H8** (joint risk surfaces) | High | Medium | H3, H14 | **P2** — improves targeting |
| **H15** (spatial optimization) | High | Medium | H7, H2 | **P2** — operational payoff |
| **H10** (agricultural calendar) | Medium | Medium | None | **P3** — seasonal forecasting |
| **H5** (human mobility) | High | Low | None | **P3** — importation dynamics |
| **H3** (multi-species thermal) | Medium | Low | None | **P3** — species-aware suitability |
| **H4** (backward bifurcation) | Medium | Low | None | **P3** — theoretical, hard to validate |

### Recommended Testing Sequence

**Phase A (M1–M2, immediate — highest feasibility, highest impact):**
- H13 (DHIS2 data pipeline + calibration) — unblocks all downstream validation
- H2 (ITN/IRS intervention layers) — core SDSS capability
- H1 (lag-response climate forcing) — improves nowcast with existing data

**Phase B (M3–M4, near-term — requires new data layers but established methods):**
- H7 (U-Net validation against DHS) — enables real-time scenario evaluation
- H9 (ITN cascade modeling) — improves intervention accuracy
- H11 (extreme weather event detection) — addresses dominant future burden driver
- H6 (hydrological suitability) — changes hotspot predictions for Ghana

**Phase C (M5–M6, medium-term — requires new data collection or novel methods):**
- H12 (archetypes/SNT) — enables sub-national tailoring per WHO guidance
- H14 (multi-species intervention profiling) — prevents resource waste
- H8 (joint risk surfaces) — improves spatial targeting
- H15 (spatial optimization) — operational payoff, the SDSS decision engine
- H10 (agricultural calendar) — seasonal forecasting for northern Ghana

**Phase D (M7+, strategic — requires external data or partnerships):**
- H5 (human mobility / importation) — requires mobile phone CDR or migration survey data
- H3 (multi-species thermal decomposition) — requires comprehensive entomological surveys
- H4 (backward bifurcation) — theoretical, requires long time-series for validation

---

## Part V: Complete Reference List

- Aduvukha et al. (2026). Two-step MaxEnt-fuzzy model for malaria biting probability mapping in Cameroon.
- Angelakis et al. (2026). Assessing the impact of climate and control interventions on spatio-temporal malaria dynamics using a stochastic metapopulation model. *PLOS Computational Biology*.
- Bertozzi-Villa et al. (2024). An archetypes approach to malaria intervention impact mapping. *Figshare*.
- Champagne et al. (2025). Cascades of effectiveness of new-generation insecticide-treated nets against malaria. *bioRxiv*.
- Churcher et al. (2024). The epidemiological benefit of pyrethroid–pyrrole insecticide treated nets against malaria. *Lancet*.
- Eudaric et al. (2026). Geospatial mapping of malaria risk in flood-prone zones of Sub-Saharan Africa. *Scientific Reports*.
- Fernandez Montoya et al. (2021). Overlaying human and mosquito behavioral data to estimate residual exposure. *PLOS ONE*.
- Frake et al. (2020). Leveraging big data for public health: Mapping malaria vector suitability in Malawi with Google Earth Engine. *PLOS ONE*.
- García et al. (2022). Real-time, spatial decision support to optimize malaria vector control: The case of indoor residual spraying on Bioko Island. *PLOS Digital Health*.
- Gatore Sinigirira et al. (2025). SEIR-SEI malaria model integrating temperature, rainfall, and NDVI for Burundi.
- Gbaguidi et al. (2026). Guiding malaria elimination interventions: a data-driven approach to resource optimization in Benin. *Malaria Journal*.
- Golumbeanu et al. (2024). AnophelesModel: An R package to interface mosquito bionomics, human exposure and intervention effects. *PLOS Computational Biology*.
- Gwitira et al. (2020). Spatio-temporal clustering of malaria cases in Zimbabwe.
- Henyimana et al. (2026). Modelling the impact of adopting new-generation insecticide-treated nets on malaria transmission and insecticide resistance. EMOD, Tanzania.
- Ibrahim et al. (2024). Spatio-temporal characterization of phenotypic resistance in malaria vector species. *BMC Biology*.
- Kalonde et al. (2025). Defining health facility catchment areas for malaria microstratification using routine data.
- Kamau et al. (2021). Spatial-temporal clustering of malaria using routinely collected health facility data on the Kenyan Coast.
- Kelly et al. (2012). Spatial decision support systems for malaria elimination. Reference SDSS framework.
- Kelly et al. (2013). SDSS for malaria elimination, Solomon Islands / Vanuatu.
- Khelifa & El Saadi (2024). The impact of aquatic habitats on malaria parasite transmission: A view from an agent-based model. *Ecological Modelling*.
- Kleinschmidt et al. (2000). Kriging and logistic regression for spatial malaria mapping.
- Mfala et al. (2024). Developing an ABM for evaluating malaria interventions in Tanzania. *Indian J Sci Technol*.
- Mfala et al. (2026). Agent-based simulation of seasonal malaria chemoprevention strategy in Southern Tanzania. *Malaria Journal*.
- Mondal et al. (2025). Multitask deep learning emulation and calibration of an agent-based malaria model across 8 African sites.
- Mordecai et al. (2013). Optimal temperature for malaria transmission.
- Okiring et al. (2021). DLNM analysis of environmental drivers of malaria in high-transmission settings of Uganda.
- Onimisi et al. (2025). Integrating DHS/MIS Biomarkers with 34 Years of CHIRPS-NDVI Climate Data for Malaria Risk Prediction in Nigeria.
- PATH/CHAI/IDM/SwissTPH (2025). SNT Toolbox: Sub-National Tailoring for Malaria Elimination.
- Rakotoarison et al. (2025). Spatial modeling of the population dynamics of Anopheles mosquitoes in Madagascar. *Int J Health Geographics*.
- Sa-ngamuang et al. (2026). MoVe: an integrated tool to explore the relationship between human mobility and vector-borne disease. *Scientific Reports*.
- Selvaraj et al. (2020). Vector genetics, insecticide resistance and gene drives: An agent-based modeling approach. *PLOS Computational Biology*.
- Smith et al. (2024). Future malaria environmental suitability in Africa is sensitive to hydrology. *Science* 384, 697–703.
- Symons et al. (2026). Projected impacts of climate change on malaria in Africa. *Nature*.
- Vanhuysse et al. (2023). Fine-scale mapping of urban malaria exposure under data scarcity. *Malaria Journal*.
- Walker et al. (2026). Spatio-temporal agent-based modelling of malaria. *arXiv: 2505.16240*.
- Wangdi et al. (2016). SDSS for malaria elimination in Bhutan.

---

*Generated by MalariaSentinel Research Harness — Phase 4 (Hypothesize)*
*37+ papers synthesized · 15 hypotheses across 4 generations · 3 testing phases mapped*
