# Optimal temperature for malaria transmission is dramatically lower than previously predicted

**Authors:** Erin A. Mordecai, Krijin P. Paaijmans, Leah R. Johnson, Christian Balzer, Tal Ben-Horin, Emily de Moor, Amy McNally, Samraat Pawar, Sadie J. Ryan, Thomas J. Smith, Kevin D. Lafferty
**Journal:** Ecology Letters | **Year:** 2013 | **DOI:** 10.1111/ele.12015
**File:** papers/anopheles-dynamics/Mordecai-2013-OptimalTemperatureMalariaTransmission.md

---

## Abstract

Most malaria transmission models to date assume constant or linear responses of mosquito and parasite life-history traits to temperature, predicting optimal transmission at 31°C — a figure at odds with nearly a century of field observations. This study builds a mechanistic model incorporating empirically derived nonlinear (unimodal) thermal responses for all key mosquito and parasite traits involved in transmission, including biting rate, adult mortality, larval development, egg production, egg-to-adult survival, and parasite development rate. The model predicts optimal malaria transmission at 25°C (6°C lower than previous estimates), with transmission occurring between 16°C and 34°C and declining dramatically above 28°C. A large independent dataset on malaria transmission risk in Africa (Entomological Inoculation Rate vs. mean seasonal temperature) validates both the 25°C optimum and the steep decline above 28°C.

## Methods

- **Model type:** Mechanistic temperature-sensitive R₀ model based on the Ross-Macdonald framework, extended with nonlinear thermal performance curves for all component life-history traits.
- **Thermal response fitting:** Unimodal curves (Brière or quadratic) fitted to published laboratory data for Anopheles mosquito species and Plasmodium falciparum at constant temperatures. Parameters include: biting rate (a), adult mortality rate (l), parasite development rate (PDR), eggs laid per female per day (EFD), larval development rate (MDR), and probability of egg-to-adult survival (pEA).
- **R₀ formulation:** Square-root R₀ formula incorporating all temperature-sensitive parameters: R₀ = (ma² × pEA × EFD × PDR) / (l × MDR × r), where m is vector density and r is human recovery rate.
- **Validation:** Compared model predictions against a compiled dataset of EIR measurements across Africa plotted against mean transmission-season temperature.
- **Sensitivity analysis:** Examined the contribution of each life-history trait to the temperature sensitivity of R₀.

## Key Results

- **Optimal transmission temperature:** 25°C — 6°C lower than the 31°C predicted by models assuming linear/constant thermal responses.
- **Transmission range:** 16°C (CTmin) to 34°C (CTmax); transmission declines dramatically above 28°C.
- **Sensitivity hierarchy:** Adult mosquito mortality rate (l) had the strongest effect on R₀ temperature sensitivity, followed by biting rate and parasite development rate.
- **Validation:** The highest observed EIR values in Africa occurred at mean temperatures of 24–26°C, with steep declines below 20°C and above 28°C, consistent with model predictions.
- **Implication for climate change:** Previous models (predicting 31°C optimum) suggested warming would expand malaria range; the 25°C optimum and >28°C decline predict that warming in already-warm regions may reduce transmission.

## Relevance to MalariaSentinel (Centinela)

This paper provides the foundational thermal-response parameterization for the Centinela's environmental suitability layer. The Mordecai 2013 nonlinear thermal curves are the basis for the suitability model currently used in `mal-ghana-sim` — the suitability overlay converts MODIS land surface temperature into transmission suitability scores using these empirically derived unimodal functions. The finding that transmission peaks at 25°C and declines sharply above 28°C is critical for predicting how climate variability affects transmission intensity in Ghana's ecological zones, which span temperatures from ~22°C (highland zones) to ~33°C (northern savanna). The sensitivity analysis identifying adult mortality as the dominant temperature-sensitive parameter also informs which ABM parameters should be prioritised for calibration against field data.

## Limitations

- Thermal responses were fitted from laboratory data at constant temperatures; field temperatures fluctuate diurnally and seasonally, which may shift effective optima.
- The model assumes a single Anopheles vector species; Ghana harbours multiple species (An. gambiae s.s., An. coluzzii, An. arabiensis, An. funestus) with potentially different thermal tolerances.
- The model does not incorporate humidity, which covaries with temperature in the field and may independently affect mosquito survival.
- The validation dataset (EIR vs. temperature in Africa) represents aggregated data across diverse ecological and intervention contexts.

## Future Directions

- Extend the thermal-response framework to species-specific curves for the dominant Anopheles species in target regions (An. gambiae s.s., An. coluzzii, An. funestus).
- Incorporate diurnal temperature range (DTR) effects, which can shift effective thermal optima for both mosquito and parasite traits.
- Couple the temperature-sensitive R₀ model with rainfall and NDVI drivers (as in Gatore Sinigirira 2025) for a fully climate-driven transmission model.
- Validate against entomological surveillance data from Ghana's ecological zones to calibrate regional thermal parameters.

---

## References

- Mordecai EA, Paaijmans KP, Johnson LR, et al. (2013). Optimal temperature for malaria transmission is dramatically lower than previously predicted. *Ecology Letters*, 16: 22–30.
- Paaijmans KP, Mordecai EA, et al. (2019). Temperature dependence of Plasmodium development in mosquitoes and parasite infection in the mosquito. *Parasites & Vectors*.
- Martens WJM, Jetten TH, Focks DA. (1997). Sensitivity of malaria, schistosomiasis and dengue to global warming. *Climatic Change*, 35: 145–156.
