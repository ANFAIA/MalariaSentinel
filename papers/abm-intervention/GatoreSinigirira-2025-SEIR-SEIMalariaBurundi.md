# Mathematical Modelling of Malaria Integrating Temperature, Rainfall, and Vegetation Index

**Authors:** Kelly Joëlle Gatore Sinigirira, Wandera Ogana, Faraimunashe Chirove
**Journal:** Acta Applicandae Mathematicae | **Year:** 2025 | **DOI:** 10.1007/s10440-025-00740-y
**File:** papers/abm-intervention/GatoreSinigirira-2025-SEIR-SEIMalariaBurundi.md

---

## Abstract

Environmental factors such as temperature, rainfall, and vegetation index play a crucial role in malaria transmission dynamics, yet quantifying their combined effects remains challenging. This study develops a host-mosquito SEIR-SEI mathematical model that integrates temperature, rainfall, and Normalized Difference Vegetation Index (NDVI) as time-varying parameters affecting mosquito birth rate, larval survival, and adult mortality. Calibrated to Burundian case data, the model reveals that temperature and NDVI exert the most pronounced influence on transmission, with optimal conditions at 20–25°C and NDVI of 0.4–0.6. Crucially, the model demonstrates that backward bifurcation can occur — meaning endemic equilibria persist even when R₀ < 1 — and that R₀ is projected to increase through 2070 under climate change scenarios, threatening Burundi's elimination prospects.

## Methods

- **Model structure:** SEIR-SEI compartmental model: humans (S_H, E_H, I_H, R_H) and mosquitoes (S_V, E_V, I_V) with temperature-, rainfall-, and NDVI-dependent parameters.
- **Climate parameterization:**
  - Mosquito birth rate θ_v(T, R, η): function of temperature (T), rainfall (R), and NDVI (η), combining egg survival probability, larval survival probability, and pupal survival probability.
  - Larval survival probability S_L(T, R, η) = S_L1(T) × S_L2(R) × S_L3(η), where each component is a separate nonlinear function.
  - Adult mosquito mortality μ_v(T, η): temperature- and NDVI-dependent.
  - Biting rate a(T): temperature-dependent (Mordecai 2013 thermal response).
- **Threshold analysis:** Basic reproduction number R₀ computed via next-generation matrix method; backward bifurcation analysis using center manifold theory (Chavez & Song).
- **Sensitivity analysis:** Partial Rank Correlation Coefficients (PRCC) calculated at five time points (t = 100–500) to identify parameter sensitivity over time.
- **Calibration:** Fitted to Burundian malaria incidence data with temperature range 15–35°C, rainfall 5–50 mm, NDVI 0.2–0.8.

## Key Results

- **Optimal transmission conditions:** Temperature 20–25°C, NDVI 0.4–0.6, rainfall 10–30 mm/month. Temperature and NDVI exhibited more pronounced influence than rainfall alone.
- **Backward bifurcation:** The model exhibits backward bifurcation at R₀ = 1, meaning the disease-free equilibrium and an endemic equilibrium coexist for R₀ < 1. Initial conditions determine which equilibrium the system reaches — even when R₀ < 1, high initial infection prevalence can sustain endemic transmission.
- **R₀ threshold value (R₀ᶜ):** A critical threshold R₀ᶜ > 1 exists below which elimination is guaranteed; between R₀ᶜ and R₀ = 1, the system is bistable.
- **Climate change projection:** R₀ is projected to increase over time under current climate trends, suggesting that elimination windows may close without drastic control measures.
- **Sensitivity hierarchy:** Transmission bite rate (β₁), recovery rate (γ_h), biting rate a(T), and mosquito mortality μ_v(T, η) are the most sensitive parameters across all time points.

## Relevance to MalariaSentinel (Centinela)

This paper provides the theoretical foundation for H4 in the project's hypothesis set — the claim that backward bifurcation dynamics require elimination programmes to sustain 15–25% higher intervention coverage than classical R₀ > 1 thresholds predict. The SEIR-SEI model structure with climate-dependent parameters offers a template for the Centinela's transmission module: the mosquito birth rate function θ_v(T, R, η) can be directly adapted for Ghana by re-parameterising with local thermal and vegetation data. The backward bifurcation finding is operationally critical: if Ghana's transmission dynamics exhibit bistability (likely in areas with An. funestus-driven permanent breeding sites), the Centinela must flag districts where R₀ < 1 is insufficient for elimination — requiring sustained high intervention coverage and active monitoring for re-emergence. The PRCC sensitivity analysis identifies which parameters should be prioritised for empirical calibration in the Ghana ABM.

## Limitations

- The model is deterministic (ODE-based) and does not capture stochastic fadeout dynamics that are critical near elimination thresholds.
- The model assumes a single mosquito species; Ghana's multi-species vector complex (An. gambiae s.s., An. coluzzii, An. arabiensis, An. funestus) may exhibit different thermal responses and breeding habitat requirements.
- Calibration is against Burundian data; transferability to Ghana requires re-parameterisation with local epidemiological and entomological data.
- The NDVI effect is modelled as a multiplicative modifier on larval survival, which may oversimplify the relationship between vegetation and breeding site availability.
- Human immunity dynamics (temporary immunity with waning) are simplified; Ghana's holoendemic settings may require more complex immunity models.

## Future Directions

- Implement the backward bifurcation detection module in the Centinela ABM to identify bistable districts in Ghana.
- Extend the model to a multi-species framework with species-specific thermal responses (incorporating Mordecai 2013 and species-specific data from entomological surveys).
- Couple the deterministic SEIR-SEI model with the stochastic ABM to capture fadeout dynamics near elimination thresholds.
- Use the PRCC sensitivity results to design targeted parameter estimation studies (e.g., field measurements of adult mosquito mortality and biting rates in Ghana's ecological zones).
- Project R₀ under climate change scenarios for Ghana to identify which districts face closing elimination windows.

---

## References

- Gatore Sinigirira KJ, Ogana W, Chirove F. (2025). Mathematical Modelling of Malaria Integrating Temperature, Rainfall, and Vegetation Index. *Acta Applicandae Mathematicae*. doi:10.1007/s10440-025-00740-y.
- Gatore Sinigirira KJ, Ogana W, Nyandwi S, Kwizera JDD, Niyukuri D. (2024). A Mathematical Model Exploring the Impact of Climatic Factors on Malaria Transmission Dynamics in Burundi. *Journal of Applied Mathematics and Physics*, 12: 3728–3757.
- Mordecai EA, et al. (2013). Optimal temperature for malaria transmission is dramatically lower than previously predicted. *Ecology Letters*, 16: 22–30.
- Chavez CC, Song B. (2004). Bifurcation analysis of a two-stage model for malaria transmission. *Mathematical Biosciences*.
