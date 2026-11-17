# A spatial statistical approach to malaria mapping

**Authors:** I Kleinschmidt, M Bagayoko, GPY Clarke, M Craig, D Le Sueur
**Journal:** International Journal of Epidemiology | **Year:** 2000 | **DOI:** 10.1093/ije/29.2.355
**File:** papers/spatial-analysis/SpatialStatisticalApproachToMalaria.md

---

## Abstract

Good maps of malaria risk have long been recognised as an important tool for malaria control, but their production relies on modelling to predict risk across unsampled locations from a limited number of prevalence surveys. Estimation is complicated by local variation in risk that cannot be fully accounted for by known covariates, and by the non-random spatial distribution of survey data points. This paper describes a two-stage statistical procedure for producing maps of predicted malaria risk, illustrated using data from Mali collected by the MARA/AMRA project. The first stage uses logistic regression modelling to determine approximate risk on a larger scale using climatic, population, and topographic variables as predictors. The second stage employs geostatistical kriging on the model residuals to improve prediction at the local level, accounting for spatial dependence over short distances.

The analysis used 101 childhood malaria prevalence surveys from Mali conducted since 1960, with predictor variables including monthly rainfall, temperature, NDVI, population density, and distance to water. The final logistic regression model contained four significant predictors: distance to water, average NDVI during the wet season, number of months with ≥60 mm rainfall, and average maximum temperature (March–May), explaining approximately 65% of total deviance. After regression, the D-statistic and variogram analysis confirmed residual spatial correlation over short ranges (≤20 km). Kriging of logit-scale residuals within an 18 km radius improved prediction accuracy: a weighted kappa statistic increased from 0.624 (regression only) to 0.727 (regression + kriging), and five additional surveys' observed prevalence fell within the correct predicted band. The two-stage approach offers a practical alternative to full universal kriging (not yet available for logistic models at the time), enabling local deviation from global predictions while maintaining covariate adjustment for non-stationarity.

## Methods

- Two-stage modelling procedure:
  1. Logistic regression for large-scale prediction using climatic, environmental, and topographic covariates
  2. Geostatistical kriging of model residuals for local-scale improvement
- Data: 101 childhood malaria prevalence surveys from Mali (post-1960) in the MARA/AMRA database
- Predictor variables: monthly rainfall, max/min temperature, NDVI, population density, distance to water body, number of months with ≥60 mm rainfall
- Variable selection: stepwise procedures, goodness-of-fit criteria, and residual spatial correlation minimisation
- Spatial pattern analysis: D-statistic (non-parametric, with binary neighbourhood and inverse distance weights) and semi-variogram
- Kriging: exponential model fitted to variogram (sill=0.7, nugget=0.4, range=18 km), implemented in GEO-EAS
- Overdispersion handled via deviance-based extra-dispersion parameter
- GIS software: IDRISI for image prediction map generation

## Key Results

- Final model explained ~65% of total deviance in malaria prevalence
- Four significant predictors: NDVI (wet season), distance to water, rainy season length, average max temperature (Mar–May)
- Strong spatial autocorrelation in observed prevalence (p<0.0005); residual spatial correlation still significant but reduced
- Residual spatial correlation range: ≤20 km (confirmed by both D-statistic and variogram)
- Kriging improvement: weighted kappa 0.624 → 0.727 (agreement between observed and predicted prevalence bands)
- Five additional surveys correctly classified after kriging
- Prediction range widened from 0–80% (regression only) to 0–92% (regression + kriging)
- Improvements concentrated near survey locations (within 18 km); sparse areas unchanged
- Model most accurate where prevalence is highest (where survey density is greatest)

## Relevance to MalariaSentinel (Centinela)

This paper establishes the foundational two-stage geostatistical methodology that directly informs the Centinela's spatial prediction framework — using environmental covariates for broad-scale risk estimation followed by local refinement accounting for residual spatial dependence. The approach of combining logistic regression with kriging on residuals offers a computationally tractable alternative to full Bayesian geostatistical models, relevant to the Centinela's need for scalable, operational prediction. The paper's honest discussion of limitations — data sparsity, non-random sampling, overdispersion, and the need for goodness-of-fit indicators — directly informs the Centinela's model validation framework. The MARA/AMRA mapping context also connects to the Centinela's focus on sub-Saharan Africa.

