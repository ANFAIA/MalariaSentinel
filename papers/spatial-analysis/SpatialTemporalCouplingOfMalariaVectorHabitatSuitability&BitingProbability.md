# Spatial-temporal coupling of malaria vector habitat suitability and biting probability

**Authors:** Grace R. Aduvukha, Elfatih M. Abdel-Rahman, Onisimo Mutanga, John Odindi, Henri E.Z. Tonnang
**Journal:** Spatial and Spatio-temporal Epidemiology | **Year:** 2026 | **DOI:** 10.1016/j.sste.2025.100777
**File:** papers/spatial-analysis/SpatialTemporalCouplingOfMalariaVectorHabitatSuitability&BitingProbability.md

---

## Abstract

Effective control of malaria vectors is crucial for achieving successful malaria elimination. Despite advances in species distribution modelling (SDM), the behavioural dynamics of malaria vectors — particularly biting probability — have not been fully integrated into these models. This study presents a novel two-step modelling approach that couples habitat suitability with biting probability of *Anopheles gambiae* complex in Cameroon. In Step 1, MaxEnt (maximum entropy) SDM was used to assess spatial distribution of habitat suitability using climatic, environmental, topographic, and remotely sensed variables (n=74 occurrence points). In Step 2, fuzzy logic rule-based techniques integrated modelled vector presence, human population density, confirmed insecticide resistance, bed net usage, and environmental variables to assess spatio-temporal biting risk probability from 2000 to 2018.

MaxEnt modelling achieved an AUC of 0.747 (±0.049), with NDVI (96.1%), elevation (2.9%), wind speed (0.4%), and solar radiation (0.4%) as the most influential predictors. Medium-to-high habitat suitability was identified along Cameroon's Atlantic coastline (South-West, Littoral, South regions). The fuzzy logic model was validated against independent biting observation data (n=25, 2017–2021), achieving 91% mean accuracy for both flexible (Model 1: OR-based) and strict (Model 2: AND-based) rule configurations. Sensitivity analysis identified bed net use, human presence, and vector presence as the most influential predictors of biting probability. Both models showed reduced biting probability with increased bed net usage, a pattern consistent with declining *P. falciparum* prevalence rates from 2000 to 2018. Regions of persistent high biting probability were observed in North-West, West, South-West, and Littoral regions. The results highlight the significance of integrating modelled vector presence, ecological conditions, human availability, and control methods for assessing malaria transmission risk as an early warning system under changing climate and intervention scenarios.

## Methods

- **Step 1 — Habitat suitability**: MaxEnt v3.4.4 with 10-fold cross-validation, hinge and quadratic feature classes, regularization multiplier=1
- **Step 2 — Biting probability**: Fuzzy logic rule-based model with triangular membership functions, 50% overlap between classifications
- Two model scenarios: Model 1 (flexible/OR conditions) and Model 2 (strict/AND conditions)
- Variable selection: Variance Inflation Factor (VIF < 10) and cluster dendrogram analysis
- Predictors: elevation, average temperature, NDVI, wind speed, solar radiation, soil moisture, precipitation, human population, bed net use, confirmed insecticide resistance, modelled habitat suitability
- Rule weighting: bed net use 0.3, human presence 0.1, vector presence 0.1, environmental variables 0.0625 each (91 rules per model)
- Validation: independent biting observations (n=25, 2017–2021), binary classification accuracy
- Sensitivity analysis: Sobol' indices (first-order S1 and total-order ST) with 212,992 model evaluations
- Spatial resolution: 5 km × 5 km grid (23,850 centroids)
- Data sources: Malaria Atlas Project, Vector Atlas, TerraClimate, MODIS, WorldClim, GEE

## Key Results

- MaxEnt AUC: 0.747 (±0.049); NDVI contributed 96.1% of model gain
- Medium-to-high habitat suitability: coastal South-West, Littoral, South regions of Cameroon
- Low suitability: Adamawa, East, southern South regions
- Fuzzy logic mean validation accuracy: 91% (both models)
- High biting risk: 70.83% (Model 1) and 37.78% (Model 2) of study area in 2000
- Reduced high biting risk by 2018: 31.78% (Model 1) and 4.56% (Model 2)
- Ensemble map: persistent high biting in North-West, West, South-West, Littoral regions (2000–2010)
- Sensitivity: bed net use (highest S1), human presence, vector presence most influential
- Biting risk reduction trend aligned with *P. falciparum* prevalence rate decline (2000–2018)
- Variable importance (MaxEnt): NDVI 96.1%, elevation 2.9%, wind speed 0.4%, solar radiation 0.4%

## Relevance to MalariaSentinel (Centinela)

This paper provides a methodological template for the Centinela's integrated risk modelling approach, combining species distribution modelling (habitat suitability) with behavioural risk assessment (biting probability). The two-step framework — ML-based SDM followed by rule-based risk assessment — directly parallels the Centinela's planned pipeline for integrating entomological, environmental, and intervention data. The use of MaxEnt for habitat suitability and fuzzy logic for uncertainty handling under data scarcity offers practical methodologies for the Centinela's modeller component. The finding that bed net use is the dominant predictor of biting probability underscores the importance of incorporating intervention coverage data into transmission risk models.

---

## Full Text

### --- Page 1 ---
Spatial and Spatio-temporal Epidemiology 56 (2026) 100777
Contents lists available at ScienceDirect
Spatial and Spatio-temporal Epidemiology
journal homepage: www.elsevier.com/locate/sste
Spatial-temporal coupling of malaria vector habitat suitability and
biting probability
Grace R. Aduvukhaa,b,*, Elfatih M. Abdel-Rahmana,b, Onisimo Mutangab, John Odindib,
Henri E.Z. Tonnanga,b,c
aInternational Centre of Insect Physiology and Ecology (ICIPE), P. O. Box 30772, Nairobi 00100, Kenya
bSchool of Agriculture and Science, University of KwaZulu-Natal, Pietermaritzburg 3209, South Africa
cInternational Institute of Tropical Agriculture (IITA), PMB, Oyo Road, Idi-Oshe, Ibadan 5320, Nigeria
A R T I C L E I N F O A B S T R A C T
Keywords: Effective control of malaria vectors is crucial for achieving successful malaria elimination. Modelling techniques
Anopheles play a key role in understanding the behaviour and distribution of Anopheles mosquito, the vector responsible for
Bionomics malaria transmission upon infection with the Plasmodium parasite. Despite advances in species distribution
Machine learning
modelling (SDM), the behavioural dynamics of malaria vectors, particularly biting probability, have not been
Prediction
fully integrated into these models. This study aimed to model both the habitat suitability and biting probability of
Rule-based
malaria vectors. Specifically, relevant remotely sensed data, climatic and topographic variables, and presence-
only malaria vector data were integrated into MaxEnt (maximum entropy), an SDM to assess the distribution
of malaria vectors. Subsequently, additional variables such as the modelled malaria vector presence, human
availability, confirmed insecticide resistance and bed net usage were incorporated in fuzzy logic rule-based
techniques to assess the spatial and temporal biting risk probability of these vectors from 2000 to 2018. Two
different rule-based model scenarios with distinct rule combinations (Model 1: flexible optimal climatic and
environmental conditions (i.e., ORs) and Model 2: strict optimal climatic and environmental conditions (i.e.,
ANDs)) were evaluated. An independent set of validation data with An. gambiae complex biting observations (n
=25) for the years (2017-2021) was used. Validation of the models yielded a mean accuracy of 91% for both
models. The models showed reduced biting probability with increased bed net usage amid optimal conditions for
biting. This pattern was also comparable to the reduced Plasmodium falciparum prevalence rate from 2000 to
2018 due to an increase in intervention measures. The results highlight the significance of integrating modelled
malaria vector presence, ecological conditions, human availability/presence and control methods in the
assessment of malaria transmission risk as an early warning system in changes to climate and control methods
usage. These findings are pivotal for optimizing targeted malaria vector management and malaria elimination
strategies, providing essential insights for public health and disease control stakeholders.
1. Introduction
Malaria transmission in humans occurs through the bites of female Anopheles mosquito infected with the Plasmodium parasite. In 2022, approximately 249 million malaria cases were recorded worldwide. The disease remains most frequent in tropical and subtropical regions, particularly in Africa. Understanding malaria vector behaviour is paramount for effective control and eventual eradication. Despite advancements in SDM and statistical approaches, mosquito behavioural aspects such as biting probability and vector adaptation to control methods are rarely integrated into large-scale models. Therefore, this study sought to assess the relationship between the occurrence (habitat suitability) and behaviour (biting risk probability) of An. gambiae complex in Cameroon using a 2-step modelling approach.
2. Study area
This study was conducted in Cameroon (2–13°N, 9–16°E), with a population of approximately 27.2 million and surface area of 475,000 km². The country spans five climatic zones: Sahelian, Soudanian, Sahelo-Guinea, Humid Savannah, and Forest Zone. The primary malaria vector species are An. gambiae s.l., An. arabiensis, and An. funestus.
3. Methodology
A two-step methodological framework was employed. Step 1: MaxEnt v3.4.4 was used to model habitat suitability of An. gambiae complex using 74 occurrence points after cleaning. Step 2: A fuzzy logic model assessed biting risk probability using 11 predictor variables. Variable selection used VIF (<10) and cluster dendrogram analysis. The fuzzy logic model incorporated triangular membership functions with 50% overlap and 91 rules per model. Sobol' sensitivity analysis with 212,992 model evaluations was performed.
4. Results
The MaxEnt model produced an AUC of 0.747 (±0.049). NDVI (96.1%) dominated variable importance. The fuzzy logic models achieved 91% validation accuracy. High biting risk was persistently observed in 2000, 2005, and 2010, with reduction in 2015 and 2018. Bed net use was the most influential variable in sensitivity analysis. Biting risk patterns aligned with P. falciparum prevalence rate trends.
5. Discussion
The study identified medium to highly suitable habitats along the Atlantic coastline. The fuzzy logic algorithm demonstrated high performance in predicting binary biting probability. The robust performance can be attributed to inclusion of predictor variables mimicking ecological and behavioural factors. Human presence, vector habitat suitability, and bed net use emerged as the most consistent predictors.
6. Conclusions
This study developed a methodology for modelling biting risk probability under data scarcity using rule-based methods. Human population/presence, vector presence, and bed net use were the most consistent variables. The study recognises the importance of entomological surveys while emphasising the necessity of robust open data repositories for malaria vectors.
References
[Full reference list as published in Spatial and Spatio-temporal Epidemiology 2026.]
