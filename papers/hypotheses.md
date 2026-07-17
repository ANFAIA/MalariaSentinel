# Research Hypotheses for MalariaSentinel

This document presents five testable hypotheses that bridge identified knowledge gaps in the MalariaSentinel spatial decision support system. Each hypothesis connects existing empirical evidence to a specific architectural extension of the framework, with concrete testing approaches using the current ABM, U-Net surrogate, and data pipeline.

---

## H1: Encoding DLNM-derived lag-response dynamics into the ABM climate module improves short-term transmission forecasting accuracy by at least 15%

**Knowledge bridge:** Environmental lag dynamics (Okiring 2021) ↔ ABM climate parameterization (current MalariaSentinel ABM)

**Supporting evidence:** Okiring 2021's distributed lag nonlinear model (DLNM) analysis in Uganda demonstrates that temperature effects on malaria incidence peak at lag 2 weeks (IRR 2.00, 95% CI 1.53–2.61), with cumulative IRR reaching 8.16 at lag 4. Rainfall peaks at lag 0 (IRR 1.24) but NDVI effects peak at lag 2 (IRR 1.31, cumulative 1.57 at lag 4). The current ABM uses instantaneous climate values in its suitability-to-carrying-capacity calculation, ignoring these well-characterized delayed responses. Granger causality tests confirmed that all three covariates have predictive power for IRR, establishing that lag structure carries genuine signal rather than mere correlation.

**Testing approach:** Extend the ABM's `SuitabilityModel` class to accept lagged climate rasters (1–4 week offsets). Run parallel 52-week simulations: (a) baseline with instantaneous climate, (b) with 2-week temperature lag + 0-week rainfall lag, (c) with full Okiring lag structure (temp lag 2, rain lag 0, NDVI lag 2). Evaluate against CHIRPS/MODIS-derived hindcasts using RMSE and skill score relative to persistence. Retrain the U-Net surrogate on lagged-input simulation data to test whether the surrogate can learn lag dynamics more efficiently than the ABM encodes them.

**Expected impact:** If confirmed, lag-aware climate forcing would produce actionable 2–4 week nowcasts of transmission intensity, enabling targeted reactive interventions (e.g., focal MDA or reactive case detection) timed to peak risk windows rather than current conditions.

---

## H2: Adding ITN/IRS intervention layers as dynamic ABM parameters reduces simulated prevalence by 30–60%, aligning model outputs with DHS-observed prevalence declines in Ghana

**Knowledge bridge:** Intervention coverage as dominant predictor (Onimisi 2025) ↔ ABM intervention dynamics (currently absent)

**Supporting evidence:** Onimisi 2025's machine learning framework across 34 years of DHS/MIS data in Nigeria identifies ITN coverage as the single most important predictor of malaria prevalence (feature importance 0.1285), exceeding all climate variables. Cross-year validation reveals temporal non-stationarity (accuracy drops from 62% to 37% to 40% across validation years), suggesting that intervention coverage drives regime shifts that climate alone cannot explain. Aduvukha 2026 independently finds that bed net use is the most influential predictor of biting probability in Cameroon, reinforcing the centrality of vector-control interventions. The current ABM has no mechanism to model these dynamics.

**Testing approach:** Introduce a `CoverageLayer` module that ingests DHS/MIS-derived ITN and IRS coverage rasters (available from the MalariaAtlas R package and PMI datasets). Parameterize species-specific bite-rate reductions: An. gambiae s.s. (high endophily → strong ITN effect), An. arabiensis (zoophilic/exophagic → weak ITN effect). Run counterfactual simulations: (a) zero coverage, (b) Ghana 2015 coverage (~50% ITN), (c) Ghana 2020 coverage (~65% ITN). Compare simulated prevalence trajectories against DHS observed values. Use the U-Net to learn the coverage→prevalence transfer function from ABM sweeps.

**Expected impact:** A validated intervention module would allow the Centinela to forecast the impact of coverage gaps and target distribution campaigns to areas where coverage falls below the effective threshold for transmission suppression.

---

## H3: Splitting the vector suitability model into species-specific thermal response curves improves spatial prediction accuracy for high-biodiversity regions

**Knowledge bridge:** Multi-species vector ecology (Perplexity investigations, An. gambiae complex) ↔ environmental suitability modeling (current MalariaSentinel suitability module)

**Supporting evidence:** The An. gambiae complex comprises at least 8 cryptic species (including An. gambiae s.s., An. coluzzii, and An. arabiensis) with distinct thermal optima, habitat preferences, and behavioral profiles. An. funestus produces up to 90% of infective bites in East/Southern Africa and has different breeding habitat requirements (permanent/semi-permanent water bodies) compared to An. gambiae s.s. (ephemeral puddles). An. arabiensis is more zoophilic and exophagic, making it less affected by indoor interventions. The current suitability model applies a single Mordecai 2013 thermal response curve uniformly, treating the vector community as monospecific. Gatore Sinigirira 2025 further demonstrates that optimal transmission occurs within T = 20–25°C, but this range likely differs across species.

**Testing approach:** Decompose the suitability model into species-specific components using published thermal response parameters: An. gambiae s.s. (lower thermal limit ~18°C, optimum ~25°C, upper ~34°C), An. arabiensis (wider thermal tolerance, optimum ~27°C), An. funestus (narrower breeding habitat filter). Generate species-specific suitability maps using the existing environmental layers. Validate against entomological survey data (Ifakara Health Institute and PMI vector surveillance datasets) where species composition is known. Measure whether multi-species suitability improves AUC over monospecific suitability for districts with known mixed-species populations.

**Expected impact:** Species-aware suitability mapping would enable targeted intervention design: ITN-heavy strategies where An. gambiae s.s. dominates, larval source management where An. funestus breeding sites are identifiable, and IRS or livestock-associated approaches where An. arabiensis predominates.

---

## H4: Incorporating backward bifurcation dynamics into the ABM's transmission model reveals that sub-R₀ elimination targets require 15–25% higher intervention coverage than classical thresholds predict

**Knowledge bridge:** Backward bifurcation theory (Gatore Sinigirira 2025) ↔ elimination threshold modeling (MalariaSentinel SDSS elimination targeting)

**Supporting evidence:** Gatore Sinigirira 2025's SEIR-SEI model for Burundi demonstrates that backward bifurcation can occur in malaria transmission dynamics — a regime where R₀ < 1 does not guarantee disease elimination because endemic equilibria persist below the classical threshold. Their model, integrating temperature, rainfall, and NDVI, shows R₀ is projected to increase through 2070, meaning elimination windows may close. The Centinela currently uses classical R₀ > 1 as its elimination threshold criterion, with no mechanism to detect or model bistable dynamics. Kleinschmidt 2000's spatial logistic regression framework and Gwitira 2020's spatio-temporal clustering analysis both implicitly assume monotonic dose-response between environmental risk and prevalence, which backward bifurcation violates.

**Testing approach:** Implement a bistable transmission module in the ABM that tracks both the disease-free equilibrium and the endemic equilibrium. Parameterize using the Gatore Sinigirira formulation: extend the current SIS/SEI compartmental model to include a nonlinear force of infection that permits two stable states. Sweep intervention coverage (0–100%) and measure the "hysteresis width" — the gap between the coverage needed to eliminate from endemic equilibrium vs. the coverage at which reintroduction causes re-emergence. Compare against classical single-threshold predictions. Use the U-Net to learn the bistable transfer function and identify spatial regions where hysteresis is most pronounced in Ghana.

**Expected impact:** If backward bifurcation is relevant in Ghana (likely in areas with An. funestus-driven transmission), elimination programs would need to sustain higher coverage than current targets specify, and "elimination achieved" status would require monitoring for re-emergence even after R₀ dips below 1.

---

## H5: Coupling human mobility data with the ABM quantifies importation risk and identifies which districts require cross-border surveillance coordination for sustained elimination

**Knowledge bridge:** Human mobility and importation risk (Kelly 2012 SDSS framework) ↔ ABM population dynamics (currently absent)

**Supporting evidence:** Kelly 2012's reference SDSS framework explicitly identifies human movement as a critical input for malaria elimination decision-making, noting that cross-border migration drives reintroduction in settings approaching elimination. In Ghana, internal migration between northern savanna zones (higher transmission) and southern urban areas creates importation corridors that sustain low-level transmission even where local vector capacity is declining. The current ABM models mosquito populations and environmental suitability but contains no human agents, making it structurally incapable of capturing importation dynamics. Onimisi 2025's finding that temporal non-stationarity in prevalence (62%→37%→40%) may partly reflect mobile populations moving between high- and low-transmission zones further motivates this gap.

**Testing approach:** Integrate mobile phone mobility data (MalariaSIM consortium or Ghana Statistical Service migration surveys) as a human movement layer in the ABM. Define districts as nodes and movement volumes as edge weights. Introduce infected agents entering from high-prevalence source districts at empirically calibrated rates. Measure: (a) the prevalence threshold below which importation becomes the dominant transmission sustainer, (b) which origin-destination pairs pose the highest reintroduction risk, (c) whether reactive case detection at mobility hubs (markets, transport nodes) outperforms uniform surveillance. Validate against Ghana Health Service district-level incidence data where importation events are documented.

**Expected impact:** An importation-aware model would enable the Centinela to prioritize cross-district and cross-border coordination, target surveillance at mobility corridors rather than just high-prevalence zones, and set realistic elimination timelines that account for reintroduction pressure.

---

## References

- Aduvukha et al. (2026). Two-step MaxEnt-fuzzy model for malaria biting probability mapping in Cameroon.
- Gatore Sinigirira et al. (2025). SEIR-SEI malaria model integrating temperature, rainfall, and NDVI for Burundi. Includes backward bifurcation analysis.
- Gwitira et al. (2020). Spatio-temporal clustering of malaria cases in Zimbabwe.
- Kamau et al. (2021). Spatial-temporal clustering of malaria using routine facility data in Kenya.
- Kelly et al. (2012). Spatial decision support systems for malaria elimination. Reference SDSS framework.
- Kleinschmidt et al. (2000). Kriging and logistic regression for spatial malaria mapping.
- Mordecai et al. (2013). Thermal response curves for Anopheles mosquito transmission.
- Okiring et al. (2021). DLNM analysis of environmental drivers of malaria in Uganda.
- Onimisi et al. (2025). ML framework integrating DHS/MIS biomarkers with CHIRPS-NDVI for malaria prevalence prediction in Nigeria.
- Perplexity investigations (2026). Anopheles gambiae complex species biology, habitat preferences, and intervention response profiles.
