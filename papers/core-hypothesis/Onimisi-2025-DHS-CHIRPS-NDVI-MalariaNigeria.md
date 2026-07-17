# Integrating DHS/MIS Biomarkers with 34 Years of CHIRPS-NDVI Climate Data for Malaria Risk Prediction in Nigeria: A Machine Learning and Spatial Mapping Approach

**Authors:** Daniel Onimisi
**Journal:** medRxiv (preprint) | **Year:** 2025 | **DOI:** 10.64898/2025.12.14.25342244
**File:** papers/core-hypothesis/Onimisi-2025-DHS-CHIRPS-NDVI-MalariaNigeria.md

---

## Abstract

Nigeria bears one of the highest malaria burdens globally, yet national-scale studies integrating long-term environmental trends with survey-confirmed biomarker data remain scarce. This study presents a hybrid machine learning framework that combines Demographic and Health Survey/Malaria Indicator Survey (DHS/MIS) rapid diagnostic test (RDT) biomarkers from 2010, 2015, and 2021 with 34 years (1990–2024) of CHIRPS rainfall and MODIS-NDVI vegetation data to predict malaria risk at the Local Government Area (LGA) level across Nigeria. A Random Forest classifier trained on 139,407 geo-referenced survey records achieves cross-year validation accuracies of 62.2% (2010), 36.8% (2015), and 40.2% (2021), with SHAP interpretability revealing ITN coverage, lagged climate means, temperature, and population density as dominant predictors.

## Methods

- **Data sources:** DHS/MIS biomarker datasets (2010, 2015, 2021) with RDT-confirmed malaria status; CHIRPS rainfall (0.05° resolution, 1990–2024); MODIS-NDVI (16-day composites); Google Earth Engine for scalable satellite data processing.
- **Feature engineering:** 11-dimensional feature space including rainfall, NDVI, temperature, ITN coverage, fever prevalence, population density, long-term climate mean, 1-month lagged climate, 3-month rolling mean climate, climate baseline, and climate anomaly.
- **Model:** Random Forest classifier (scikit-learn) with cross-year temporal validation — train on N-1 survey years, test on the held-out year.
- **Interpretability:** SHAP (SHapley Additive exPlanations) values to identify dominant predictors and their contribution to risk classification.
- **Spatial output:** LGA-level risk maps by aggregating cluster-level predictions to Nigeria's 774 administrative units, with climate anomaly overlays.

## Key Results

- **Cross-year accuracy:** 62.2% (2010), 36.8% (2015), 40.2% (2021) — accuracy declines across survey years, indicating temporal non-stationarity in the climate–prevalence relationship.
- **Top predictors (feature importance):** ITN coverage (0.1285), 3-year climate lag mean (0.1061), temperature (0.1059), rainfall (0.1013), population density (0.1004), previous prevalence (0.0972).
- **SHAP analysis:** ITN coverage is the single most important predictor of malaria risk, exceeding all climate variables. Lagged climate features (3-year rolling mean) rank highly, confirming the importance of multi-year environmental memory.
- **Temporal non-stationarity:** The drop in accuracy from 62% to 37% between validation years suggests that intervention coverage dynamics (ITN scale-up) drive regime shifts that climate-only models cannot capture.
- **Spatial patterns:** Generated LGA-level risk maps consistent with known malaria geography — highest risk in north-eastern and south-south zones, lowest in south-western urban areas.

## Relevance to MalariaSentinel (Centinela)

This paper provides a methodological template for the Centinela's risk-prediction layer. The feature engineering approach — combining long-term climate climatologies, lagged effects, anomalies, and intervention covariates — directly informs the data pipeline design in `mal-commonlib`. The finding that ITN coverage dominates all climate predictors reinforces H2 in the project's hypothesis set: the ABM must incorporate intervention coverage as a dynamic parameter, not just environmental suitability. The temporal non-stationarity finding (accuracy degradation across years) validates the need for the Centinela's adaptive model retraining capability. The use of CHIRPS and MODIS data sources aligns with the existing data pipeline in `mal-ghana-sim`, confirming that the same satellite products can be reused for Ghana.

## Limitations

- Cross-year validation accuracy is low (36–40% for later years), suggesting the model struggles with temporal generalization — likely because intervention coverage changes faster than climate signals.
- The model uses cluster-level aggregation, which may smooth over fine-scale spatial heterogeneity in transmission.
- DHS/MIS surveys are conducted every 5 years, creating temporal gaps that the model must bridge through interpolation.
- The study covers Nigeria only; transferability to Ghana (different ecological zones, intervention history) is untested.
- No entomological data (vector species composition, biting rates) were incorporated — the model is purely environmental/survey-based.

## Future Directions

- Incorporate entomological covariates (vector species composition, EIR) as additional predictors to bridge the gap between environmental suitability and actual transmission.
- Develop ensemble models combining Random Forest with gradient boosting (XGBoost) or deep learning for improved temporal generalization.
- Apply the framework to Ghana using the same CHIRPS/MODIS pipeline to generate LGA-level risk maps for the Centinela's first working case.
- Integrate real-time CHIRPS/NDVI feeds for near-real-time risk updating rather than relying on periodic survey data.
- Explore the use of mobile phone mobility data as an additional predictor to capture importation dynamics.

---

## References

- Onimisi D. (2025). Integrating DHS/MIS Biomarkers with 34 Years of CHIRPS-NDVI Climate Data for Malaria Risk Prediction in Nigeria. *medRxiv*, doi:10.64898/2025.12.14.25342244.
- DHS Program. Malaria Indicator Surveys for Nigeria (2010, 2015, 2021). Available at: dhsprogram.com.
- Funk C, et al. (2015). The climate hazards infrared precipitation with stations — a new environmental record for monitoring extremes. *Scientific Data*, 2: 150066. (CHIRPS dataset).
- Didan K. (2015). MODIS Vegetation Index Products (13Q1 & 13A1). NASA EOSDIS Land Processes DAAC.
