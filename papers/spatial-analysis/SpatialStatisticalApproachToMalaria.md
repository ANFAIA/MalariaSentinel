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

---

## Full Text

### --- Page 1 ---
© International Epidemiological Association 2000 Printed in Great Britain International Journal of Epidemiology 2000;29:355–361
A spatial statistical approach
to malaria mapping
I Kleinschmidt,a M Bagayoko,b GPY Clarke,c M Craiga and D Le Sueura
Background Good maps of malaria risk have long been recognized as an important tool for
malaria control. The production of such maps relies on modelling to predict the
risk for most of the map, with actual observations of malaria prevalence usually
only known at a limited number of specific locations. Estimation is complicated
by the fact that there is often local variation of risk that cannot be accounted for
by the known covariates and because data points of measured malaria prevalence
are not evenly or randomly spread across the area to be mapped.
Method We describe, by way of an example, a simple two-stage procedure for producing maps
of predicted risk: we use logistic regression modelling to determine approximate
risk on a larger scale and we employ geo-statistical ('kriging') approaches to
improve prediction at a local level. Malaria prevalence in children under 10 was
modelled using climatic, population and topographic variables as potential pre-
dictors. After the regression analysis, spatial dependence of the model residuals
was investigated. Kriging on the residuals was used to model local variation in
malaria risk over and above that which is predicted by the regression model.
Results The method is illustrated by a map showing the improvement of risk prediction
brought about by the second stage. The advantages and shortcomings of this
approach are discussed in the context of the need for further development of
methodology and software.
Keywords Malaria risk, disease maps, geo-statistics, spatial analysis, kriging, climatic factors
Accepted 22 July 1999
Introduction
Malaria is a major cause of morbidity and mortality in Africa, and is a leading cause of death especially amongst children, in many African countries [1,2]. The MARA/AMRA project [3] has been set up recently to collate sources of data on malaria, and to model and map malaria risk across the continent. This paper describes the statistical methods used to produce a map of malaria risk for Mali. The production of malaria maps relies on modelling to predict the risk for most of the map, with actual observations of malaria prevalence usually only known at a limited number of specific locations.
Data Collection and Data Preparation
Malaria prevalence data were collated from surveys of childhood populations in Mali since 1960. Altogether 101 such surveys were identified. For each survey the total sample size and number of individuals testing positive was known. For each of the survey co-ordinates long-term climatic averages, NDVI and population density were obtained. Variables consisted of: monthly rainfall, monthly average maximum temperature, monthly average minimum temperature, monthly NDVI and population density, plus number of months with rainfall ≥60 mm and distance to nearest water body.
Methods and Results
The first stage involved ordinary logistic regression analysis. The final model contained four significant explanatory variables: distance to water (categorical), average NDVI during the wet season (categorical), number of months with ≥60 mm rainfall, and average maximum temperature during March–May. The final model explains about 65% of the total variation. For each variable an image covering the whole of Mali was produced in IDRISI.
Investigation of spatial pattern used the D-statistic and the variogram. The observed malaria prevalence was highly autocorrelated in space. The model residuals still showed evidence of spatial pattern. The semi-variogram of model residuals showed evidence of spatial correlation over short ranges ≤20 km.
Kriging on the residuals was performed using an exponential model fitted to the variogram (sill=0.7, nugget=0.4, range=18 km). Kriged logit-scale residual predictions were added to the logit-scale predicted values from the logistic model, then back-transformed to prevalence. The final map (Figure 4) shows improvement over the regression-only map (Figure 2), particularly where survey density is high. The difference map (Figure 5) confirms that kriging changes are concentrated near survey locations.
Discussion
The two-stage approach offers an appealing alternative to universal kriging. The non-spatial model provides covariate adjustment and prediction of mean risk; kriging of residuals allows for local deviation and spatial dependence. The final predictions make sense from the entomological perspective. However, a more systematic approach in future would be a full mixed model with universal kriging to take account of spatial pattern.
References
[Full reference list of 25 citations as published in International Journal of Epidemiology 2000.]
