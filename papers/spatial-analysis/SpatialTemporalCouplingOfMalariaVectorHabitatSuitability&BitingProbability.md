# SpatialTemporalCouplingOfMalariaVectorHabitatSuitability&BitingProbability

**Source PDF:** `SpatialTemporalCouplingOfMalariaVectorHabitatSuitability&BitingProbability.pdf`  
**Path:** `papers/spatial-analysis/SpatialTemporalCouplingOfMalariaVectorHabitatSuitability&BitingProbability.pdf`  

---

--- Page 1 ---
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
1. Introduction regions, particularly in Africa. Historically, the most preferred and
recommended malaria vector control methods have included
Malaria transmission in humans occurs through the bites of female long-lasting insecticidal nets (LLINs) and indoor residual spraying (IRS),
Anopheles mosquito infected with the Plasmodium parasite. Once in the both mainly targeting indoor-biting mosquitoes (WHO, 2023). However,
bloodstream, the parasite migrates to the liver, where it matures and the effectiveness of these interventions is increasingly threatened by
reproduces (NCEZID, 2024). The frequency of female Anopheles bites insecticide resistance and behavioural adaptations of mosquitoes,
significantly increases the likelihood of parasite transmission and ma- including outdoor biting and avoidance of treated surfaces (Afrane et al.,
laria infection. In 2022, approximately 249 million malaria cases were 2016; Fikadu and Ashenafi, 2023). In this context, residual transmission
recorded worldwide, marking a five million increase from 2021 (WHO, and malaria transmission occurrence, despite the implementation of
2023). The disease remains most frequent in tropical and subtropical these control measures, remain a persistent challenge.
* Corresponding author at: International Centre of Insect Physiology and Ecology (ICIPE), P. O. Box 30772, Nairobi 00100, Kenya.
E-mail address: gaduvukha@icipe.org(G.R. Aduvukha).
https://doi.org/10.1016/j.sste.2025.100777
Received 10 April 2025; Received in revised form 21 November 2025; Accepted 2 December 2025
Available online 3 December 2025
1877-5845/© 2025 Elsevier Ltd. All rights are reserved, including those for text and data mining, AI training, and similar technologies.

--- Page 2 ---
G.R. Aduvukha et al. S p a t i a l a n d S p a t i o - t e m p o r a l E p i d e m io l o g y 56 (2026) 100777
Understanding malaria vector behaviour is paramount for effective methods (LLINs), climatic, topographic, and remotely sensed (i.e.,
control and eventual eradication of the disease. Field entomological normalized difference vegetation index, NDVI) variables. This study
surveys play a crucial role in identifying mosquito occurrence and be- extends previous efforts by utilizing the limited available geolocated
haviours, such as breeding, feeding, and resting preferences. These biting evidence of malaria vectors to predict An. gambiae complex biting
surveys provide detailed information about mosquito bionomics at local risk probability as a malaria risk transmission indicator.
scales (Paaijmans and Thomas, 2011; Ekoko et al., 2019; Mmbando
et al., 2021). However, they are often time-consuming, labour-intensive, 2. Study area
and costly, especially when conducted across large spatial extents. To
address these challenges, various mathematical, machine learning and This study was conducted in Cameroon, located between latitude
statistical modelling techniques have become increasingly popular for 2–13◦N and longitude between 9–16◦E (Fig. 1), with a population of
predicting mosquito habitats, distribution, and abundance at regional approximately 27.2 million people and a surface area of 475,000 km2.
and continental scales (Iban˜ez-Justicia and Cianci 2015; Wiebe et al. The country is divided into 10 administrative regions: North-West, West,
2017; Gwitira et al. 2018). Specifically, techniques such as random South-West, Litoral, Central, East, South, Far North, North, and Ada-
forest (RF) (Liu et al., 2024), maximum entropy (MaxEnt) (Kulkarni mawa. These regions span five distinct climatic zones: Sahelian (Far
et al., 2016) and artificial neural networks (ANN) (Capinha et al., 2009) North), Soudanian (North), Sahelo-Guinea (Adamawa), Humid
have been applied to predict Anopheles habitat suitability. Moreover, Savannah (North-West and West), and Forest Zone (South-West,
ensemble modelling approaches have also been explored with additional Littoral, Centre, East and South) (Antonio-Nkondjio et al., 2019). Each
techniques such as support vector machines (SVM), decision trees (DT), zone exhibits varying levels of malaria endemicity (Chouakeu et al.,
generalized linear models (GLM), multivariate adaptive regression 2023). The primary malaria vector species in Cameroon are An. gambiae
splines (MARS), and generalized additive models (GAM) (Taheri et al., s.l., An. arabiensis and An. funestus. Other vectors include An. coustani,
2024). These models have incorporated entomological data (e.g., spe- An. coluzzi, and An. paulidis (Chouakeu et al., 2023). Despite the scale-up
cies type, presence, abundance, etc) and a range of climatic, environ- of malaria control interventions such as LLINs, the prevalence of Plas-
mental, and topographic variables. Additionally, modelling efforts have modium parasitemia continues to reflect the persistent risk of infective
extended to studying mosquito biting and resting behaviours. For mosquito bites (Antonio-Nkondjio et al., 2019). This study focused on
example, Mmbando et al. (2021)used generalised additive mixed-effect An. gambiae complex in Cameroon, as it remains the most extensively
models (GAMM) to examine factors affecting distribution of malaria studied vector species in the literature, hence its data availability and
vectors in Tanzanian villages, while Finda et al. (2019)explored human accessibility.
behaviours and vector biting risks using GLM, highlighting persistent
biting exposure outdoors, and during pre-bedtime hours in Tanzania. 3. Methodology
Furthermore, Soma et al. (2021)modelled hourly human exposure to
mosquito bites across different seasons in Burkina Faso, with a mathe- Fig. 2 illustrates the methodological framework employed in this
matical model demonstrating the protective effect of LLINs while noting study to assess the relationship between habitat suitability and biting
residual exposure risks. probability of An. gambiae complex in Cameroon as a case study. In
Despite advancements in species distribution modelling (SDM) and summary, MaxEnt, an SDM, was used to model the spatial distribution of
statistical approaches, mosquito behavioural aspects such as biting the An. gambiae complex, while a rule-based fuzzy logic algorithm was
probability and vector adaptation to control methods are rarely inte- employed to characterize the biting probability of the vector. A detailed
grated into large-scale models. Inclusion of behavioural changes, such as description of the datasets and analysis is presented herein.
avoidance of treated surfaces, further complicates predictive modelling
of mosquito-biting behaviour (Ekoko et al., 2019; Kreppel et al., 2020; 3.1. Data collation and preparation
Sanou et al., 2021; Tondossama et al., 2023). Such models require
detailed mosquito entomological data to enhance our understanding of 3.1.1. Anopheles gambiae complex occurrence and biting data
the vector behaviours, however these data are often limited by logistical Occurrence and biting data of the malaria vectors were obtained
constraints. Alternative methods, such as fuzzy logic models (Zadeh, from the Malaria Atlas Project (https://malariaatlas.org) and Vector
1965), are yet to be explored in handling scarce or imprecise mosquito Atlas (https://vectoratlas.icipe.org). The data were cleaned (e.g.,
behavioural data. These models have been successfully used for removing duplicates) to ensure viable locations of the occurrence points,
ecological niche modelling of Anopheles species in South America (Fuller resulting in An. gambiae complex n =83 sampled from 2000 – 2022, with
et al., 2014; Padilla et al., 2017), malaria disease prediction in South a georeferenced confidence level of 5 km per point (Table S1 in sup-
Korea (Buczak et al., 2015) and predicting mosquito larval habitat plementary). The geographic distribution of the occurrence points pre-
similarity and/or divergence in Kenya (Aduvukha et al., 2025). How- sent in the different climatic zones of Cameroon is summarized in
ever, there remains a gap in predicting mosquito biting behaviour by Table S2 in supplementary. Validation data for biting of An. gambiae
integrating multiple factors, including Anopheles habitat suitability, complex were available for the years 2017 (n =2), 2018 (n =7), 2019 (n
control methods, human population density, insecticide resistance, and =4), 2020 (n =10) and 2021 (n =2) (Menze et al., 2018; Doumbe--
environmental variables. Belisse et al., 2018; Mieguim et al., 2021; Kwi et al., 2022; Tepa et al.,
Accurate prediction of mosquito biting probability is essential for 2022; Fondjo et al., 2023; Chouakeu et al., 2023) (Table S3 in supple-
assessing malaria transmission risk and optimizing vector control stra- mentary). The biting data comprised positive observations of combined
tegies. Therefore, this study sought to assess the relationship between human biting rate, entomological inoculation rate (EIR) or sporozoite
the occurrence (habitat suitability) and behaviour (biting risk proba- rates. The combined human biting rate indicates the frequency of human
bility) of Anopheles gambiae complex, a malaria vector, in Cameroon bites by malaria vectors, the sporozoite rate represents the proportion of
using a 2-step modelling approach. Specifically, in step 1, MaxEnt, a malaria vectors that carry Plasmodium sporozoites, and the EIR repre-
machine learning technique, was employed to characterize the spatial sents the annual number of infectious bites from a malaria vector e.g.
distribution of habitat suitability of An. gambiae complex using climatic, An. gambiae complex. Therefore, these observations were a proxy for
environmental, topographic and remotely sensed predictor variables. biting.
Subsequently, in step 2, fuzzy logic rule-based techniques were
employed to demonstrate the biting risk probability of An. gambiae 3.1.2. Predictor variables and variable selection
complex, considering its habitat suitability, and critical variables such as Predictor variables influencing An. gambiae complex distribution and
human population, insecticide resistance, use of malaria vector control biting probability are described in Table 1. The variables were
2

--- Page 3 ---
G.R. Aduvukha et al. S p a t i a l a n d S p a t i o - t e m p o r a l E p i d e m io l o g y 56 (2026) 100777
Fig. 1. Study area map showing level 1 administrative regions in Cameroon 1 North-West, 2 West, 3 South-West, 4 Littoral, 5 Central, 6 East, 7 South, 8 Far North, 9
North and 10 Adamawa, with overlaid Anopheles gambiae complex occurrence points used in species distribution modelling/habitat suitability modelling, and
elevation (30 m resolution) obtained from shuttle radar topography mission (SRTM) and available on Google Earth Engine platform (Gorelick et al., 2017). “Map lines
delineate study areas and do not necessarily depict accepted national boundaries”.
resampled to a uniform spatial resolution of 5 km x 5 km for compati- complex used was n =74. Regularization parameter and feature class
bility in analysis. Thereafter, two techniques, variance inflation factor selection influences the prediction performance of MaxEnt, where the
(VIF) and cluster dendrogram, were employed in R (R Core Team, 2022) number of samples dictates the feature class(es) to be used (Phillips and
to diagnose multicollinearity and evaluate the clusters of ten predictor Dudík, 2008). Consequently, hinge and quadratic feature classes were
variables, respectively (Table 1). The ‘vifstep’ function in ‘usdm’ pack- used in this study. In addition, we employed a ‘regularization multiplier’
age in R was used to determine the VIF of the ten predictor variables, which usually establishes how much the model is penalized for having
eliminating the predictor variable with the highest VIF while repeating too many parameters or being too complicated (Phillips, 2017). In this,
the process until there were no more variables with VIF exceeding the we conducted a sensitivity analysis to search for the optimum regula-
threshold of 10 (Table S6 in supplementary) (Naimi et al., 2014). In rization multiplier. We experimented with several regularization mul-
addition, the cluster dendrogram was cut at a height of 1 (Fig. S1 in tipliers starting from 1, which is the default value (Phillips, 2017). We
supplementary). Here, we aimed to search and experiment with found that to some extent, the higher the values of the regularization
different dendrogram heights to identify the clusters that can select multiplier, the relatively lower the model accuracy and stability as
variables, which were selected by VIF, and at the same time, including functions of area under curve (AUC) and standard deviation, respec-
the ones that were not initially selected but play an important tively (Table S4 in supplementary). A multiplier of one resulted in an
bio-ecological role in mosquito developmental and behavioural traits, accurate (acceptable AUC) and stable or reliable (lower standard devi-
such as temperature. Thus, based on this collective variable selection ation) model. Thus, we used a multiplier of one in our MaxEnt experi-
approach that includes the two methods, the final selected variables ment. To establish a robust species distribution estimation, the replicate
were elevation, average temperature, NDVI, wind speed, solar radiation, runs of MaxEnt were set to 10 as noted by Makori et al. (2017). Addi-
soil moisture and precipitation (Fig. S1 in supplementary). Studies have tionally, An. gambiae complex occurrence outliers were eliminated using
also shown that these variables play critical biological and ecological a “ten percentile” training presence criterion, which declares the 10 %
roles in the vector development and behaviour processes (Gillies and most extreme location observations as absent (Cord et al., 2014).
Wilkes, 1963; Patz et al., 1998; Paaijmans et al., 2008; Souza et al., Furthermore, we used cross-validation replication type because of its
2010; Wu et al., 2017; Endo and Eltahir, 2018). Moreover, including robustness in most SDM techniques (Kohavi, 1995; Kouame et al., 2024).
variables that have important bio-ecological roles in insect develop- A jackknife method in MaxEnt was used to evaluate the importance of
ment, survival, and reproduction processes is a common practice in each predictor variable on the model’s performance by removing the
species distribution modelling (Elith et al., 2011). variables one at a time from the modelling experiment while tracking
the model accuracy (Phillips, 2017; Kyalo et al., 2018; Adeogun et al.,
3.2. Species distribution modelling of Anopheles gambiae complex 2023). By contrasting the model’s performance with and without each
variable, the essential variables for predictions are found (Phillips,
The MaxEnt model version 3.4.4 (Phillips and Dudık, 2008) was used 2017). The receiver operating characteristic (ROC)’s
to assess the habitat suitability of An. gambiae complex. Since the threshold-independent area under the curve (AUC), which ranges from
occurrence of An. gambiae complex was sampled in different months 0 to 1, was employed to evaluate the model performance (Merow et al.,
across the years (2000-2022), the mean climatic variables of the selected 2013). The AUC indicates whether the model accurately ranked the
variables (elevation, average temperature, NDVI, wind speed, solar ra- chance of presence (sensitivity) compared to absence (specificity). Ac-
diation, soil moisture and precipitation) were calculated in QGIS and cording to Araújo et al. (2005), values above 0.7 are considered
used in the MaxEnt modelling experiment of An. gambiae complex. appropriate for estimating the species’ likelihood of regional dispersion.
Among the n =83 samples, 9 samples had missing values of the pre-
dictor variables. Thus, the final number of samples of An. gambiae
3

--- Page 4 ---
G.R. Aduvukha et al. S p a t i a l a n d S p a t i o - t e m p o r a l E p i d e m io l o g y 56 (2026) 100777
Fig. 2. Methodology flow diagram adopted for spatial-temporal coupling of malaria vector i.e., Anopheles gambiae habitat suitability and biting probability. SDM =
species distribution modelling; NDVI =normalized difference vegetation index; IR=Confirmed insecticide resistance. PfPR =Plasmodium falciparum Prevalence Rate.
3.3. Anopheles gambiae complex biting probability modelling sensitivity analysis.
A 5km by 5 km grid was created for the study area and centroids 3.3.1. Defining predictor variable thresholds
generated for each grid cell. These centroids (23, 850) were used to Seven environmental predictor variables selected from the explor-
extract predictor variables (p =11) (Table 1) for the years under study atory data analysis, in addition to human population, bed net use,
(2000, 2005, 2010, 2015, and 2018). Specifically for April, consistent confirmed insecticide resistance and the modelled An. gambiae complex
with the main period of the field entomological data. Thereafter, we habitat suitability (thus, total predictor variables p =11) were used to
employed a fuzzy logic model to assess the An. gambiae complex biting define the thresholds for An. gambiae complex biting probability through
probability. As described by Zadeh (1965), the algorithm produces a fuzzy inference system. Due to scarce availability of universal
probabilities of truth and vagueness of a phenomenon (e.g., potential thresholds of most of the variables used in this study for An. gambiae
biting probability of An. gambiae complex) that range from 0 to 1. This complex biting, we assumed that conditions favouring the presence of
experiment was implemented in Python Jupyter Notebook environment An. gambiae complex also favour their biting. Thus, its presence points (n
(Version 6.4.8). The process involved the following steps i) defining the = 74) were used to extract variable thresholds for elevation, average
variable thresholds for none, low likely, optimal likely and high unlikely temperature, NDVI, wind speed, solar radiation, precipitation, and soil
for An. gambiae complex biting probability, ii) defining the membership moisture. A boxplot for each environmental variable was generated in R
functions and converting the environmental, modelled habitat suit- (version 4.2.2, R Core Team 2022) to estimate the thresholds for the
ability of An. gambiae complex, confirmed insecticide resistance, human seven selected variables (Fig. S2 in supplementary). Values between the
population and bed net use variables to fuzzy sets (e.g., conducive and minimum and maximum thresholds observed from the boxplots were
unconducive) through the fuzzification process iv) defining rules to be classified as optimal conditions for An. gambiae complex biting
subjected to the predictor variables for classifying An. gambiae complex (Table 2). The range from the minimum values in the global dataset to
biting probability, v) converting the fuzzy sets (linguistic variables) back the observed minimum values of average temperature, precipitation,
to quantitative values to provide biting probability scores (defuzzifica- solar radiation and soil moisture in the boxplot was classified as low
tion), v) training performance assessment and, vi) model validation and unconducive biting thresholds. Similarly, the range from the observed
4

--- Page 5 ---
G.R. Aduvukha et al. S p a t i a l a n d S p a t i o - t e m p o r a l E p i d e m io l o g y 56 (2026) 100777
Table 1
Potential predictor variables used to model the habitat suitability and biting probability of Anopheles gambiae complex.
Variable Spatial Year Source and reference Rationale
resolution
Occurrence data 5 km 2000-2022 (apart from 2004, 2008, 2015, Malaria Atlas Project (https://malariaa Vector presence increases biting probability
2016 and 2017). Biting data present in tlas.org) and Vector Atlas (https://ve
occurrence data for the year 2010, 2013and ctoratlas.icipe.org).
2014
Biting data for 5 km 2017, 2018, 2019, 2020 and 2021 Malaria Atlas Project (https://malariaa Positive observations of combined human
validation tlas.org) and Vector Atlas (https://ve biting rate, entomological inoculation rate
ctoratlas.icipe.org). (EIR) or sporozoite rates
NDVI a,b,c 1 km 2000- 2022 The Moderate Resolution Imaging Provides resting, breeding and plant sugars
Spectroradiometer available in GEE for energy (Souza et al., 2010)
EVIa 1km 2000- 2022 The Moderate Resolution Imaging Similar role to NDVI but with better
Spectroradiometer available in GEE sensitivity in high biomass regions (Huete,
2002)
Average 4 km 2000-2022 (Abatzoglou et al., 2018) Affects metabolic activity of malaria vectors (
temperaturea,b,c Gillies and Wilkes, 1963)
Precipitationa,b,c 4 km 2000-2022 (Abatzoglou et al., 2018) Affects breeding of the malaria vectors (Wu
et al., 2017)
Wind speeda, b,c 4 km 2000-2022 (Abatzoglou et al., 2018) Affects the flight of the malaria vectors into
households (Endo and Eltahir, 2018)
Solar radiationa, b,c 4 km 2000 - 2022 (Abatzoglou et al., 2018) Affects temperature which later affects the
activity of malaria vectors (Paaijmans et al.,
2008)
Soil moisturea, b,c 4 km 2000 - 2022 (Abatzoglou et al., 2018) Affects breeding of malaria vectors (Patz
et al., 1998)
Vapour pressurea 4 km 2000 - 2022 (Abatzoglou et al., 2018) Affects mosquito thermal performance which
can influence their biting (Brown et al., 2023)
Vapour pressure 4 km 2000 -2022 (Abatzoglou et al., 2018) Can cause evaporative stress affecting
deficita malaria vector survival and desiccation thus
affecting biting (Brown et al., 2023)
Elevationa,b,c 1 km N/A (Fick and Hijmans, 2017) Affects presence of malaria vectors hence
influencing the biting risk probability
Human populationc 1 km 2000 - 2020 Global population available in GEE Host attraction (blood meal source) for biting
(Soma et al., 2021)
Confirmed 5 km 2000 - 2018 (Ibrahim et al., 2024) Affect biting of malaria vectors by ensuring
insecticide persistence of the existence of the vectors (
resistancec Fikadu and Ashenafi, 2023)
Mosquito control N/A 2000 - 2018 Malaria Atlas Project (https:// Affects malaria vector biting probability by
method (LLINs)c malariaatlas.org) providing a barrier in reaching the host (
Sanou et al., 2021)
a Variables subjected to exploratory data analysis. b Variables selected after exploratory data analysis. c Variables included in the biting probability analysis. NDVI=
normalized difference vegetation index, EVI=enhanced vegetation index, GEE=Google Earth Engine platform, N/A =not applicable.
maximum values in the boxplots to the maximum values in the global
Table 2
dataset for average temperature, precipitation, solar radiation and soil
Predictor variable thresholds of Anopheles gambiae complex biting probability.
moisture was classified as high unconducive biting thresholds. For wind
Variable Low Moderate/ High speed and elevation, the value zero to their respective observed
Optimal maximum values in the boxplot were classified as conducive, while their
An. gambiae complex habitat 0 – 0.01d 0.01 – 0.1f 0.1 – 1f observed maximum values in the boxplot, to their respective maximum
suitability score value in the global dataset were classified as high unconducive thresh-
Normalized difference -1– 0.19d 0.19 – 0.67f 0.67 – 1d
olds (Endo and Eltahir, 2018). On the other hand, thresholds for bed net
vegetation index (NDVI)
Average temperature (◦C) -77 – 22.44d 22.08 – 28.97f 28.97 – use, human population and confirmed insecticide resistance were esti-
57.6d mated and/or implied from the literature and presented (Table 2).
Precipitation (mm) 0 – 2.14d 2.14 – 207.25f 207 – 7245d Specifically, the ecology of the anthropophilic An. gambiae complex
Wind speed (m/s) 0 – 0.99f 0.99 – 2.46f 2.46 – dictates that adult female Anopheles mosquitoes seek blood meals
29.23d
Solar radiation (W/m2) 0 – 173.26d 173.26 – 253.89 – (humans) for their egg laying (NCEZID, 2024). Thus, the availability of a
253.89f 547.7d human population ≥1 provided the lowest threshold for optimum vector
Soil moisture (mm) 0 –18.99d 18.99 – 292.76 – biting. Furthermore, presence of confirmed insecticide resistance also
292.76f 888.2d
alters the response of the vector to the available control measures e.g.,
Elevation (m) 0 – 3f 3 – 1202.0f 1202 –
indoor residual spraying and poor condition of bed net (e.g. torn bed
8848.60d
Human population Absence =0d - Presence =1f nets) (Lindblade et al., 2015). In addition, zero probability of occurrence
(no biting) of the An. gambiae complex was assumed to cause no biting risk while the
Bed net use coverage 0 - 0.5fh 0.50 – 0.80fm 0.80 – 1fl target for effective coverage of LLINs to reduce biting probability is
Confirmed insecticide 0d - 1f estimated ≥80% (Antonio-Nkondjio et al., 2019). An. gambiae complex
resistance (IR)
habitat suitability score for optimum biting was established to avoid
d =low or high unconducive thresholds for biting generalization and ensure model practicality. Human population and
f =optimal condition thresholds for biting confirmed insecticide resistance data were transformed to binary (1, 0)
fh =high biting risk when other optimal condition thresholds are met
data. Bed net use data below 10% for the years 2000, 2005 and 2010
fm =moderate biting risk when other optimal conditions thresholds are met
were converted to the minimum double-digit percentage i.e., 10% for
fl =low biting risk when other optimal condition thresholds are met
realistic model functioning.
5

--- Page 6 ---
G.R. Aduvukha et al. S p a t i a l a n d S p a t i o - t e m p o r a l E p i d e m io l o g y 56 (2026) 100777
3.3.2. Defining membership functions and fuzzification the first order index (S1) that shows the effect of one input alone on
Membership functions were used in the fuzzy logic model to assess output variance, and the total order index (ST), which indicates the ef-
the uncertainty in modelling the biting risk probability of An. gambiae fect of one input including all its interactions using Eqs. (2) and (3),
complex. The functions provide graphical representations that define respectively. The Saltelli method sampling scheme was used in gener-
the degree of truth for each data point ranging from 0 to 1 in the given ating the samples for the two indices and computing confidence in-
data space (Zadeh, 1965). The triangular membership function was tervals of the indices. This sampling scheme requires a total of N ×(p+2)
selected due to its effectiveness in optimizing the introduced categories model evaluations, where N is the number of base samples which should
(Pedrycz, 1993). This function is defined by three key parameters: the be power of 2 for optimal performance, and p is number the predictor
lower bound, the upper bound, and the middle point, which represents variables used. Thus, the number of base samples used was 16,384, and
the peak degree of membership (Zadeh, 1965). In this model, the total model evaluations were 212,992 to ensure better convergence and
triangular membership functions exhibit a 50% overlap between fuzzy precision (Saltelli et al., 2010).
logic classifications: low (conducive & unconducive), optimum/ mod-
M(C(Y|Xi))
erate (conducive & unconducive), and high (conducive & unconducive) S1= (2)
M(Y)
predictor variable thresholds for An. gambiae complex biting risk prob-
ability (Fig. S3 in supplementary). This was followed by fuzzification i. Where C(Y∣Xi) is the conditional expectation of the output, given a fixed
e., transforming crisp (numeric) values into linguistic terms (e.g. low value of variable Xi, M(C(Y∣Xi)) is the variance of this conditional
unconducive, moderate/high unconducive and optimum conducive)
expectation, which measures how much the mean output changes as the
representing An. gambiae complex biting conditions.
value of Xi is varied across its range, and M(Y) is the total variance of the
model output.
3.3.3. Fuzzy logic rules formulation, application and defuzzification
Fuzzy logic rules were constructed for the eleven predictor variables. ST=1(cid:0) M(C(Y|X∼i)) (3)
The rules entailed a logical combination of ANDs and ORs (flexibility M(Y)
and strictness). The fuzzy logic rules were incorporated in two models
(Model 1: flexibility in the optimal climatic and environmental condi- Where X~i are all input predictor variables except for Xi, C(Y∣X~i) is the
tions (ORs) and Model 2: strictness in the optimal climatic and envi- conditional expectation of the output, given fixed values for all predictor
ronmental conditions (ANDs)). This is after ensuring the most critical variables except Xi, M(C(Y∣X~i)) is the variance of this conditional
criteria are met in both models i.e., availability of human and presence expectation, which measures the remaining output variance when all
of the vector for there to be biting, while presence of bed net use predictor variables except Xi are fixed and M(Y) is the total variance of
regulated the level of biting risk depending on the percentage of their the model output.
usage. Weighting of the variables was also incorporated to ensure proper Maps were created to visualize the An. gambiae complex biting risk
model prioritization of predictor variables for improved prediction probability from the two models across the studied years. An ensemble
(Marchini, 2011). The weights given were as follows; bed net use 0.3, map showcasing the intersecting result from the two models was also
human presence 0.1 and vector presence (modelled An. gambaie complex included. The trend of biting risk probability maps for 2000 and 2018
habitat suitability) 0.1 while average temperature, precipitation, wind were qualitatively validated with the trend of Plasmodium prevalence
speed, elevation, solar radiation, soil moisture, NDVI, and confirmed patterns for 2000 and 2018 (U.S. President’s Malaria Initiative, 2023).
insecticide resistance were weighted 0.0625 each. A total of 91 rules for
each model were developed. A summary of the rules employed for the 4. Results
two models is presented in Table S5 in supplementary. The distinction in
Model 1 (flexible) and Model 2 (strict) is shown from Rule 29 to Rule 46. 4.1. Species distribution model (SDM) output
Thereafter, the linguistic outputs were then defuzzified by converting
them back into crisp numeric values to provide An. gambiae complex The results showed fairly acceptable SDM outputs of AUC of 0.747
biting probability scores (0-1). Various methods of defuzzification exist and a standard deviation ±0.049 for assessing the habitat suitability of
including centre of gravity (COG)/centroid, weighted average, and An. gambiae complex (Fig. 3a). The four most influential variables on the
maxima methods. The centroid method was selected since it considers distribution of An. gambiae complex were NDVI (96.1%), elevation
all the active rules, in addition to its ease of interpretation and broad (2.9%), wind speed (0.4%) and solar radiation (0.4%) (Fig. 3b, Table 3).
applicability (Landmann et al., 2023). The model revealed a medium to high probability of distribution of An.
gambiae complex along the coastal regions near the Atlantic Ocean,
3.3.4. Fuzzy logic model validation, sensitivity analysis and visualization particularly in the South-West, Littoral, and South administrative re-
Binary biting probability risk of An. gambiae complex was validated gions of Cameroon (Fig. 4). In contrast, medium to low probability
using the independent validation dataset (n = 25) employing Eq. (1) scores were observed in the East, North, Far-North, and North-West
(Bartholomew, 2011). Additionally, the pattern/ trend of biting risk regions. Low distribution probability was evident in the Adamawa and
intensity probability over the studied years was qualitatively validated East regions. The habitat suitability score was rescaled from 0 – 0.04 to
using the P. falciparum Prevalence Rate (PfPR) patterns for 2000 and 0 – 1 respectively, for practical application.
2018 (U.S. President’s Malaria Initiative, 2023).
( )
a
Binarybitingvalidationaccuracy= ∗100 (1) 4.2. Fuzzy logic model
b
where a is the number of biting observations in the An. gambiae complex 4.2.1. Training rules performance of An. gambiae complex biting
validation dataset correctly classified by the fuzzy logic model as true probability
positive for biting and b is the total number of An. gambiae complex The results of the fuzzy logic rules across the two models in pre-
biting dataset considered for validation for the years 2017, 2018, 2019, dicting An. gambiae complex biting probability is summarized (Table 4).
2020 and 2021 (n =25). High biting risk were persistently observed in 2000, 2005 and 2010 for
Sensitivity analysis of the two models was implemented using the both Model 1 (flexible) and Model 2 (strict) in different intensities.
Sobol’ Indices tool in Python jupyter notebook. Sobol’ indices are a Additionally, reduced high biting risks were observed in 2015 and 2018
global sensitivity analysis that illustrates how input variables contribute in both Model 1 and Model 2 (Table 4). Similar patterns are observed in
to the variance of a model’s output (Todorov et al., 2021). We calculated the ensemble model (Table 5).
6

--- Page 7 ---
G.R. Aduvukha et al. S p a t i a l a n d S p a t i o - t e m p o r a l E p i d e m io l o g y 56 (2026) 100777
Fig. 3. (a) Mean area under the curve (AUC) for predicting habitat suitability of Anopheles gambiae complex in Cameroon (b) Jackknife method regularized training
gain. NDVI=Normalized difference vegetation index.
uncertainty showed small confidence interval values for S1 and ST in
Table 3
Model 1 and Model 2 for bed net use, human presence and vector
Percentage contribution of variables to Anopheles gambiae complex distribution
presence predictor variables (Table 7). The confidence interval of other
in Cameroon using jackknife method in maximum entropy (MaxEnt) model.
variables had near zero indices (Table 7).
Variable Percent contribution
Normalized difference vegetation index (NDVI) 96.1
Elevation 2.9 4.3. Time series spatial visualization of Anopheles gambiae complex biting
Wind speed 0.4 probability
Solar radiation 0.4
Average temperature 0.1
The ensemble map showcased persistent biting probability in
Precipitation 0
Soil moisture 0 different thresholds throughout the study period, with reduced high risk
in 2015 and 2018 compared to 2000, 2005 and 2010 (Fig. 6). Regions of
persistent high probability of biting risk were observed in the North-
4.2.2. Fuzzy logic model rule validation for binary biting risk and biting West, West, South-West and Littoral regions for the year 2000, 2005
intensity probability and 2010. Similar biting probability risk thresholds in both Model 1
Both Model 1 (flexible) and Model 2 (strict) showed a mean accuracy (flexible) and Model 2 (strict) were observed in West, South-West and
of 91% (Table 6). The validation results across the two models within Littoral regions, while dissimilar outputs in Model 1 (flexible) and Model
the studied years are summarized in Table 6. The An. gambiae complex 2 (strict) were majorly observed in Adamawa, North, East and South
biting intensity probability showed a reduced trend from 2000 and region, with some smaller portions in Far North, North-West and Central
2018, in comparison with the reduced Plasmodium falciparum prevalence regions.
rate in 2000 and 2018 (Fig. 7).
5. Discussion
4.2.3. Sensitivity analysis
The sensitivity analysis revealed that bed net use, human presence
5.1. Habitat suitability of Anopheles gambiae complex and its biting risk
and vector presence contributed significantly to the performance of
probability
Model 1(flexible) and Model 2 (strict) (Fig. 5). The most influential
variable on both models was bed net use, which had a higher S1 value.
The study identified medium to highly suitable habitats of An.
The impact of human presence and vector presence varied inter-
gambiae complex along the Coastline of the Atlantic Ocean in South-
changeably in the two models (Fig. 5). In addition, the measure of
West, Littoral and South administrative regions of Cameroon. In
7

--- Page 8 ---
G.R. Aduvukha et al. S p a t i a l a n d S p a t i o - t e m p o r a l E p i d e m io l o g y 56 (2026) 100777
Fig. 4. Habitat suitability score of Anopheles gambiae complex in Cameroon predicted using the maximum entropy (MaxEnt) model. Orange regions highlight the
highly suitable areas. 1 North-West, 2 West, 3 South-West, 4 Littoral, 5 Central, 6 East, 7 South, 8 Far-North, 9 North, 10 Adamawa regions of Cameroon.
Table 4
Summary of fuzzy logic model training performance evaluation of Anopheles gambiae complex binary biting risk and biting intensity probability for Model 1(flexible)
and Model 2 (strict).
[0, No Biting] (1, Biting)
[None: <0.1] [Low: 0.1 ≥& <0.3] (%) [Moderate: 0.3 ≥& <0.5] (%) High: 0.5 ≥& ≤1] (%)
Year Model 1 (%) Model 2 (%) Model 1 (%) Model 2 (%) Model 1 (%) Model 2 (%) Model 1 (%) Model2 (%)
2000 0.06 27.93 11.53 14.11 17.57 20.16 70.83 37.78
2005 0.06 24.03 6.84 9.78 19.91 26.53 73.17 39.64
2010 0.06 23.73 11.26 13.46 18.12 23.74 70.54 39.06
2015 0.44 29.44 24.31 27.49 30.73 30.52 44.50 12.52
2018 0.71 29.13 35.52 38.06 31.98 28.23 31.78 4.56
Table 5 Table 6
Summary of fuzzy logic model training performance evaluation as a measure of Validation of fuzzy logic rules for Anopheles gambiae complex binary biting risk
the percentage of none biting and biting probability risk thresholds of the probability using Model 1 (flexible) and 2 (strict).
ensemble of Model 1 (flexible) and Model 2 (strict) to (2 decimal places). Biting data <0.1 [0, No Biting] ≥0.1 & ≤1 [1,
Year [0, No [1, Biting] Biting]
biting]
Year Total occurrence Model Model Model 1 Model 2
[None: < [Low: 0.1 ≥& [Moderate: 0.3 ≥& [High: 0.5 ≥&
biting data 1 2
0.1] (%) <0.3] (%) <0.5] (%) ≤1] (%)
2017 2 0 0 2 2
2000 0.05 10.76 16.18 37.62
(100%) (100%)
2005 0.05 6.15 18.92 39.44
2018 7 0 0 7 7
2010 0.05 10.75 16.72 38.86
(100%) (100%)
2015 0.38 23.68 28.20 12.39
2019 4 1 1 3(75%) 3 (75%)
2018 0.47 34.74 26.39 4.35
2020 10 2 2 8(80%) 8 (80%)
2021 2 0 0 2 2
(100%) (100%)
contrast, medium to low distribution was observed in the East, North, Mean ​ ​ ​ 91% 91%
Far North, and North-West regions, while low distribution occurred in accuracy
the Adamawa, East, and southern parts of the South regions. However,
these results differ slightly from those of Wiebe et al. (2017) who
used being sparse due to challenges such as sampling bias (Barker and
assessed the geographic distribution of malaria vectors in Africa. They
MacIsaac, 2022), studies have illustrated the good performance of
found low habitat suitability of An. gambiae complex species i.e., An.
MaxEnt model across varied sample sizes (Wisz et al., 2008).
coluzzii, An. arabiensis, and An. melas in most parts of Cameroon, and low
The fuzzy logic algorithm demonstrated high performance >90% in
to high suitability of An. gambiae s.s. in the country. This discrepancy can
predicting binary biting probability risk of An. gambiae complex in both
be attributed to variations in the number of malaria vector occurrence
models. Furthermore, the patterns of the biting risk intensity in the two
data points and species diversity modelled in the two studies (Kouame
models revealed temporal variations closely aligning with P. falciparum
et al., 2024). Additionally with the possibility of the occurrence data
8

--- Page 9 ---
G.R. Aduvukha et al. S p a t i a l a n d S p a t i o - t e m p o r a l E p i d e m io l o g y 56 (2026) 100777
Prevalence Rate (PfPR) patterns for 2000 and 2018 (U.S. President’s
Malaria Initiative, 2023). PfPR, representing the proportion of in-
dividuals infected with malaria parasites, offers insight into the actual
malaria burden and risk of infective bites. Comparison of patterns of
modelled biting risk with patterns of PfPR for 2000 and 2018 (U.S.
President’s Malaria Initiative, 2023) depicted similar reducing trends
due to the increased bed net usage, particularly in 2015 and 2018.
Consequently, the findings suggest that biting risk reduces with increase
in bed net use, corroborating the impact of targeted LLIN distribution
campaigns during peak transmission periods (U.S. President’s Malaria
Initiative, 2023).
The robust performance of the models can be attributed to the in-
clusion of cluster predictor variables effectively mimicking the ecolog-
ical and behavioural factors influencing An. gambiae complex biting risk
probability (Gatton et al., 2013). Predictor variables such as human
presence, vector habitat suitability, and bed net use emerged as the most
consistent predictors of An. gambiae complex biting probability from the
sensitivity analysis. As much as the contribution of these variables may
have been influenced by the weighting factor in the fuzzy logic model,
the weighting was necessary to ensure realistic model interpretability.
Moreover, sufficient model evaluations i.e., 212, 992 were utilized for
the sensitivity analysis to ensure better convergence and improved
precision (Saltelli et al., 2010). Nonetheless, future studies can consider
conducting sensitivity analysis of the predictor variable thresholds with
availability of extensive data.
5.2. Key ecological and behavioural insights for modelling Anopheles
gambiae complex biting probability
Malaria vectors, including An. gambiae complex, are attracted to
hosts e.g. humans, primarily through exhaled carbon dioxide (CO₂) and
skin odours, which are detected via specialized neuron receptors (Tauxe
et al., 2013). Consequently, female Anopheles mosquitoes depend on
blood meals for proteins acquisition necessary for egg production and
population propagation (Tauxe et al., 2013). This biological mechanism
underscores the critical role of host availability in sustaining mosquito
Fig. 5. Sobol’ indices first order (S1) and total order (ST) for a) Model 1 populations and malaria transmission cycles. Human presence, behav-
(flexible) and b) model 2 (strict). NDVI= normalized difference vegetation iour and social activities significantly influence mosquito exposure risk.
index, IR= Confirmed insecticide resistance. Vector presence= modelled An. Activities such as nighttime social gatherings and fishing often occur
gambiae habitat suitability. during peak mosquito biting hours, increasing the risk of bites, partic-
ularly in the absence of effective control measures like LLINs (Nzioki
et al., 2023). Behavioural patterns thus play a pivotal role in deter-
Table 7
mining exposure to mosquito bites and, consequently, malaria trans-
Confidence intervals of first order (S1) and total order (ST) of the predictor
variables to 5 decimal places from the Sobol’ indices analysis of Model 1 (flex- mission risk. While LLINs remain an effective tool for reducing mosquito
ible) and Model 2 (strict). bites, their efficacy can be compromised by insecticide resistance
(Djamouko-Djonkam et al., 2020). However, studies have shown that
Model 1 (flexible) Model 2 (strict)
the proper use of LLINs, even in areas with confirmed insecticide resis-
Parameter S1 ST S1 ST tance, still provides significant protection by acting as a physical barrier
confidence confidence confidence confidence
between humans and mosquitoes (Ototo et al., 2015). This highlights the
interval interval interval interval
importance of consistent and proper usage of LLINs in malaria control
Bed net use 0.01523 0.01398 0.01638 0.01607
strategies. Changes in mosquito behaviour, such as shifts in biting time
Average 0.0007 0.0004 0.00035 0.00005
and location (from indoors to outdoors), pose additional challenges to
temperature
Human 0.01002 0.00837 0.00877 0.00719 malaria control. These behavioural shifts reduce the efficacy of LLINs
presence and IRS interventions (Fikadu and Ashenafi, 2023). However, these
Vector 0.00879 0.00723 0.01321 0.01254 challenges can be mitigated with mosquito repellents and protective
presence
clothing, especially in outdoor settings (Maia et al., 2013).
NDVI 0.00086 0.00059 0.00035 0.00004
Precipitation 0.00045 0.00015 0.00036 0.00005
Wind speed 0.00060 0.00056 0.00037 0.00004 5.3. Climatic and environmental factors influencing biting probability
Elevation 0.00065 0.00073 0.00037 0.00004
IR 0.00147 0.00096 0 0
While the Sobol analysis depicted little contribution of other vari-
Soil moisture 0.00075 0.00068 0.00031 0.00005
Solar 0.00087 0.00059 0.00041 0.00003 ables to the biting risk probability, temperature, precipitation, wind
radiation speed, soil moisture, elevation, solar radiation, and NDVI collectively
NDVI= normalized difference vegetation index, IR= confirmed insecticide played a critical role in influencing mosquito biting behaviour since
resistance, Vector presence =modelled An. gambiae habitat suitability. vector presence is largely also dependant on climatic and environmental
conditions. For instance, temperature and solar radiation play critical
roles in influencing mosquito survival and parasite development.
9

--- Page 10 ---
G.R. Aduvukha et al. S p a t i a l a n d S p a t i o - t e m p o r a l E p i d e m io l o g y 56 (2026) 100777
Fig. 6. Anopheles gambiae complex biting probability risk for (i) Model 1 (flexible), Model 2 (strict) and Ensemble for the years 2000, 2005, 2010, 2015 and 2018.
Dark red colour illustrates regions of high biting probability, light red colour illustrates regions of moderate biting probability, green colour illustrates regions of low
biting probability and grey colour illustrates regions of non-biting probability. White regions on the ensemble maps show areas of biting and no-biting variability
within the study periods as observed from Model 1 (flexible) and model 2 (strict). Cameroon administrative boundaries; 1 North-West, 2 West, 3 South-West, 4
Littoral, 5 Central, 6 East, 7 South, 8 Far North, 9 North, and 10 Adamawa.
Warmer temperatures have been shown to accelerate parasite develop- subsequently elevate malaria risk (Souza et al., 2010; Boussari et al.,
ment within mosquitoes, shortening the time required for the parasite to 2014).
become infectious (Takken et al., 2024). Additionally, precipitation and Regions with humid savannah and forest zones, such as the North-
soil moisture are essential for creating and sustaining larval breeding West, South-West, Littoral, Central, and South regions, exhibited high
habitats. However, excessive rainfall can sometimes wash away mos- biting risk probabilities, illustrating the resilient favourable climatic
quito larvae, disrupting breeding cycles and reducing mosquito pop- conditions. These areas are characterized by favourable temperatures
ulations (Koenraadt et al., 2004). Furthermore, wind speed affects ranging from 20–30◦C and extended rainy seasons from April to
mosquito dispersal and biting behaviour. High wind speeds can disperse November, which create suitable conditions for mosquito breeding and
mosquitoes across larger areas, making it difficult for them to focus on survival. In the Far North region, biting probability showed low to
biting humans, while strong winds can dry out breeding habitats, further moderate biting risk probability throughout the study period. This
disrupting mosquito activity (Endo and Eltahir, 2018). NDVI represents Sahelian zone experiences short rainy seasons (June–September) and
vegetation density and health, which provide mosquitoes with essential extreme temperatures, which influence mosquito breeding, but high
sugar resources for energy and metabolic processes. Vegetation also temperatures can reduce survival of the vectors. High biting probability
creates shaded breeding habitats that support mosquito survival. risk to no biting risk variability observed in the East and some parts of
Changes in NDVI, often driven by human activities such as farming and North, South and Far North regions showcased regions of possible biting
irrigation, can increase mosquito breeding opportunities and when any optimal conditions of the climatic and environmental
10

--- Page 11 ---
G.R. Aduvukha et al. S p a t i a l a n d S p a t i o - t e m p o r a l E p i d e m io l o g y 56 (2026) 100777
climatic, and environmental conditions that influence malaria vector
behaviour across regions. Predictor variables such as temperature, pre-
cipitation, wind speed, solar radiation, soil moisture, NDVI, elevation,
human population density, vector presence and bed net usage are uni-
versally relevant in determining mosquito biting probability and malaria
transmission dynamics across Africa.
However, a significant challenge to achieving broader applicability
lies in the availability and accessibility of key datasets, particularly
concerning insecticide resistance profiles. These datasets are often
incomplete, fragmented, or outdated, varying greatly across different
countries and regions. While some countries have robust malaria control
monitoring systems, others face logistical, infrastructural, and financial
challenges that limit the collection and reporting of high-quality data.
To address these challenges, there is a pressing need for standardized
data collection frameworks, open-access repositories, and cross-border
collaborations to ensure data harmonization and integration across Af-
rican countries. Investing in capacity-building initiatives, field surveys,
and entomological studies will also strengthen data availability and
quality, enabling the refinement and validation of such predictive
models across diverse ecological and epidemiological settings. While the
model is scientifically robust and adaptable to broader African contexts,
its full potential can only be realized through improved data availability,
continuous updates, and collaborative efforts across malaria-endemic
regions.
5.6. Limitations
This study assumed proper usage and good condition of LLINs, which
may not always reflect real-world scenarios. Misuse, alternate use, or
poor maintenance of bed nets could affect their protective efficacy.
Furthermore, the study focussed on nighttime biting risk when majority
Fig. 7. Comparison of (i) Model 1 (flexible) and (ii) Model 2 (strict) for 2000 of the population is asleep, and thus we acknowledge the possibilities of
and 2018 Anopheles gambiae complex biting risk intensity pattern with iii) daytime, outdoor and early morning biting, especially when the vectors
Plasmodium falciparum prevalence rate in 2000 and 2018 (U.S. President’s modify their behaviour. Data constraints, such as the lack of fine-scale
Malaria Initiative, 2023). PfPR is the proportion of individuals in a population datasets, limited the inclusion of important factors such as social be-
infected with malaria parasites, expressed as a percentage or per 1,000 people haviours and housing designs. These factors are critical for developing a
(U.S. President’s Malaria Initiative, 2023). Cameroon administrative bound-
granular understanding of malaria risk dynamics. Additionally, the
aries; 1 North-West, 2 West, 3 South-West, 4 Littoral, 5 Central, 6 East, 7 South,
resolution of spatial datasets (5 km resampling) may have missed
8 Far North, 9 North, and 10 Adamawa.
microclimatic variations that influence mosquito biting behaviour and
habitat suitability. These fine-scale conditions are essential for precise
variables are met, as observed in Model 1 (flexible). This alludes to the
malaria risk modelling. Despite these limitations, the study effectively
possible adaptability of these vectors to changing climatic conditions
demonstrated the integration of An. gambiae complex occurrence data,
(Olabimi et al., 2021), and hence a persistent risk of malaria
readily available datasets on control measures and other ecological
transmission.
variables in modelling the biting probability risk, providing valuable
insights into spatial-temporal malaria transmission risks and impact of
5.4. Asymptomatic malaria and biting risk probability control interventions under data scarcity.
Modelling of Anopheles biting risk is crucial in estimating possibilities 6. Conclusions
of infective biting and infection with Plasmodimum falciparum, especially
in cases of asymptomatic cases. Asymptomatic malaria poses a signifi- This study focussed on developing a methodology for modelling the
cant public health challenge in Cameroon, contributing to chronic ma- biting risk probability of An. gambiae complex in Cameroon under data
laria transmission risks despite the absence of visible symptoms (Ali scarcity using rule-based methods. The results also showcased the
et al., 2024; Chen et al., 2016). Individuals with asymptomatic malaria contribution of the human population/presence, bed net use and vector
remain infectious to mosquitoes, perpetuating the malaria transmission presence, insecticide resistance, climatic, environmental, topographic
cycle. Effective approaches such as mass drug administration, targeted and remotely sensed derived variables in influencing the biting proba-
screening and treatment, and consistent proper LLIN use are essential for bility of An. gambiae complex. Human population/presence, vector
managing asymptomatic cases and reducing transmission risks (Agaba presence and bed net use were the most consistent variables influencing
et al. 2022). Additionally, leveraging community health workers for An. gambiae complex biting probability. Additionally, this study recog-
targeted interventions can significantly improve the identification and nizes the importance of entomological surveys while emphasizing the
treatment of asymptomatic malaria cases. necessity of a robust open data repositories of malaria vectors to enable
future robust modelling. Future studies can also incorporate house de-
5.5. Scaling our modelling methodology across Africa signs and distance to breeding sites at a fine scale to evaluate their
impact on the biting probability of An. gambiae complex and incorporate
The developed model for predicting the biting risk probability of An. other species in malaria modelling to obtain a comprehensive outlook on
gambiae complex demonstrates significant potential for generalization the biting risk of malaria vectors and possible malaria transmission for
across the African continent and beyond, given the shared ecological, effective control.
11

--- Page 12 ---
G.R. Aduvukha et al. S p a t i a l a n d S p a t i o - t e m p o r a l E p i d e m io l o g y 56 (2026) 100777
Funding Afrane, Y.A., Bonizzoni, M., Yan, G., Afrane, Y.A., Bonizzoni, M., Yan, G., 2016.
Secondary malaria vectors of Sub-Saharan Africa: threat to malaria elimination on
the continent? Current Topics in Malaria. IntechOpen. https://doi.org/10.5772/
The authors gratefully acknowledge the financial support of the 65359.
Swedish International Development Cooperation Agency (Sida); the Agaba, B.B., Rugera, S.P., Mpirirwe, R., Atekat, M., Okubal, S., Masereka, K., Erionu, M.,
Swiss Agency for Development and Cooperation (SDC); the Australian Adranya, B., Nabirwa, G., Odong, P.B., Mukiibi, Y., Ssewanyana, I., Nabadda, S.,
Muwanguzi, E., 2022. Asymptomatic malaria infection, associated factors and
Centre for International Agricultural Research (ACIAR); the Government
accuracy of diagnostic tests in a historically high transmission setting in Northern
of Norway; the German Federal Ministry for Economic Cooperation and Uganda. Malar. J. 21 (1), 392. https://doi.org/10.1186/s12936-022-04421-1.
Development (BMZ); and the Government of the Republic of Kenya. The Ali, I.M., Manga, I.A., Nji, A.M., Tchuenkam, V.P., Neba, P.T.N., Achu, D.F., Bigoga, J.D.,
Faye, B., Roper, C., Sutherland, C.J., Mbacham, W.F., 2024. Asymptomatic
views expressed herein do not necessarily reflect the official opinion of
Plasmodium falciparum infections and determinants of carriage in a seasonal
the donors. malaria chemoprevention setting in Northern Cameroon and south Senegal
(Kedougou). Malaria Journal 23 (1), 386. https://doi.org/10.1186/s12936-02
4-05150-3.
Disclosure statement
Antonio-Nkondjio, C., Ndo, C., Njiokou, F., Bigoga, J.D., Awono-Ambene, P., Etang, J.,
Ekobo, A.S., Wondji, C.S., 2019. Review of malaria situation in Cameroon: technical
No potential conflict of interest was reported by the author(s). viewpoint on challenges and prospects for disease elimination. Parasites Vectors 12
(1), 501. https://doi.org/10.1186/s13071-019-3753-8.
Araújo, M.B., Pearson, R.G., Thuiller, W., Erhard, M., 2005. Validation of species–climate
CRediT authorship contribution statement impact models under climate change. Glob. Change Biol. 11 (9), 1504–1513. https://
doi.org/10.1111/j.1365-2486.2005.01000.x.
Grace R. Aduvukha: Writing – review & editing, Writing – original Barker, J.R., MacIsaac, H.J., 2022. Species distribution models applied to mosquitoes:
Use, quality assessment, and recommendations for best practice. Ecological
draft, Visualization, Validation, Software, Methodology, Investigation, Modelling 472, 110073. https://doi.org/10.1016/j.ecolmodel.2022.110073.
Formal analysis, Data curation, Conceptualization. Elfatih M. Abdel- Bartholomew, E.C., 2011. Accuracy Assessment of Fuzzy Classification. University of
Rahman: Writing – review & editing, Visualization, Validation, Super- Twente, Enschede, Netherlands. Master’s Thesis.
Boussari, O., Subtil, F., Moiroux, N., Dj`enontin, A., Iwaz, J., Corbel, V., Fonton, N.,
vision, Methodology, Investigation, Conceptualization. Onisimo Garcia, A., Etard, J.F., Ecochard, R., 2014. Modeling the seasonality of Anopheles
Mutanga: Writing – review & editing, Visualization, Validation, Su- gambiae s.s. Biting rates in a South Benin sanitary zone. Trans. R. Soc. Trop. Med.
pervision, Methodology, Investigation, Conceptualization. John Odi- Hyg. 108 (4), 237–243. https://doi.org/10.1093/trstmh/tru027.
ndi: Writing – review & editing, Visualization, Validation, Supervision, Brow – n t , h J e . J o ., v e P r a l s o c o u k a e l d , M va ., r W iab im le b i e n r l t y h , e M th .C e . r , m Jo a h l n b s io o l n o , g L y . R o . f , M mo u s r q d u o i c t k o , - b C o .C rn ., e 2 d 0 i 2 s 3 ea . s H e u . m Ec i o d l i . t y
Methodology, Investigation, Conceptualization. Henri E.Z. Tonnang: Lett. 26 (7), 1029–1049. https://doi.org/10.1111/ele.14228.
Writing – review & editing, Visualization, Validation, Supervision, Re- Buczak, A.L., Baugher, B., Guven, E., Ramac-Thomas, L.C., Elbert, Y., Babin, S.M.,
Lewis, S.H., 2015. Fuzzy association rule mining and classification for the prediction
sources, Project administration, Methodology, Investigation, Funding
of malaria in South Korea. BMC Med. Inform. Decis. Mak. 15 (1), 47. https://doi.
acquisition, Conceptualization. org/10.1186/s12911-015-0170-6.
Capinha, C., Gomes, E., Reis, E., Rocha, J., Sousa, C.A., Ros´ario, V.E., Almeida, A.P,
2009. Present habitat suitability for Anopheles atroparvus (Diptera, Culicidae) and
Declaration of competing interest
its coincidence with former malaria areas in mainland Portugal. Geospat. Health 3
(2), Article 2. https://doi.org/10.4081/gh.2009.219.
The authors declare that they have no known competing financial Chen, I., Clarke, S.E., Gosling, R., Hamainza, B., Killeen, G., Magill, A., O’Meara, W.,
Price, R.N., Riley, E.M., 2016. Asymptomatic” Malaria: a chronic and debilitating
interests or personal relationships that could have appeared to influence
infection that should be treated. PLoS Med. 13 (1), e1001942. https://doi.org/
the work reported in this paper. 10.1371/journal.pmed.1001942.
Chouakeu, N.A.K., Tchuinkam, T., Bamou, R., Bindamu, M.M., Talipouo, A., Kopya, E.,
Awono-Ambene, P., Antonio-Nkondjio, C., 2023a. Malaria transmission pattern
Acknowledgment
across the Sahelian, humid savanna, highland and forest eco-epidemiological
settings in Cameroon. Malar. J. 22 (1), Article 1. https://doi.org/10.1186/s12936-
We extend our gratitude to Brian Kanji and Wisdom Kipkemboi for 023-04544-z.
assisting with code troubleshooting, Raphael Mong’are for data prepa- Cord, A.F., Klein, D., Gernandt, D.S., la Rosa, J.A.P., Dech, S., McGeoch, M., 2014.
Remote sensing data can improve predictions of species richness by stacked species
ration, Eric Ali Ibrahim for brainstorming sessions and ICIPE ICT team distribution models: a case study for Mexican pines. J. Biogeogr. https://agris.fao.or
for support. We are also grateful to the anonymous reviewers for their g/agris-search/search.do?recordID=US201400091183.
constructive feedback. Djamouko-Djonkam, L., Nkahe, D.L., Kopya, E., Talipouo, A., Ngadjeu, C.S., Doumbe-
Belisse, P., Bamou, R., Awono-Ambene, P., Tchuinkam, T., Wondji, C.S., Antonio-
Nkondjio, C., 2020. Implication of Anopheles funestus in malaria transmission in the
Supplementary materials city of Yaound´e, Cameroon. Parasite 27, 10. https://doi.org/10.1051/parasite/
2020005.
Doumbe-Belisse, P., Ngadjeu, C.S., Sonhafouo-Chiana, N., Talipouo, A., Djamouko-
Supplementary material associated with this article can be found, in
Djonkam, L., Kopya, E., Bamou, R., Toto, J.C., Mounchili, S., Tabue, R., Awono-
the online version, at doi:10.1016/j.sste.2025.100777. Ambene, P., Wondji, C.S., Njiokou, F., Antonio-Nkondjio, C., 2018. High malaria
transmission sustained by Anopheles gambiae s.l. Occurring both indoors and
outdoors in the city of Yaound´e, Cameroon. Wellcome Open Res. 3, 164. https://doi.
Data availability
org/10.12688/wellcomeopenres.14963.1.
Ekoko, W.E., Awono-Ambene, P., Bigoga, J., Mandeng, S., Piameu, M., Nvondo, N.,
All datasets presented in this study are included in the article and can Toto, J.C., Nwane, P., Patchoke, S., Mbakop, L.R., Binyang, J.A., Donelly, M.,
Kleinschmidt, I., Knox, T., Mbida, A.M., Dongmo, A., Fondjo, E., Mnzava, A.,
be made available upon request.
Etang, J., 2019. Patterns of anopheline feeding/resting behaviour and Plasmodium
infections in North Cameroon, 2011–2014: implications for malaria control.
References Parasites Vectors 12 (1), 297. https://doi.org/10.1186/s13071-019-3552-2.
Elith, J., Phillips, S.J., Hastie, T., Dudík, M., Chee, Y.E., Yates, C.J., 2011. A statistical
explanation of MaxEnt for ecologists. Divers. Distrib. 17 (1), 43–57. https://doi.org/
Abatzoglou, J.T., Dobrowski, S.Z., Parks, S.A., Hegewisch, K.C., 2018. TerraClimate, a
10.1111/j.1472-4642.2010.00725.x.
high-resolution global dataset of monthly climate and climatic water balance from
1958–2015. Sci. Data 5 (1), Article 1. https://doi.org/10.1038/sdata.2017.191. Endo, N., Eltahir, E.A.B, 2018. Modelling and observing the role of wind in Anopheles
population dynamics around a reservoir. Malar. J. 17, 48. https://doi.org/10.1186/
Adeogun, A., Babalola, A.S., Okoko, O.O., Oyeniyi, T., Omotayo, A., Izekor, R.T.,
s12936-018-2197-5.
Adetunji, O., Olakiigbe, A., Olagundoye, O., Adeleke, M., Ojianwuna, C., Adamu, D.,
Fick, S.E., Hijmans, R.J., 2017. WorldClim 2: New 1-km spatial resolution climate
Daskum, A., Musa, J., Sambo, O., Adedayo, O., Inyama, P.U., Samdi, L., Obembe, A., surfaces for global land areas. Int. J. Climatol. 37 (12), 4302–4315. https://doi.org/
Salako, B., 2023. Spatial distribution and ecological niche modeling of geographical
10.1002/joc.5086.
spread of Anopheles gambiae complex in Nigeria using real time data. Sci. Rep. 13
Fikadu, M., Ashenafi, E., 2023. Malaria: an overview. Infect. Drug Resist. 16, 3339.
(1), Article 1. https://doi.org/10.1038/s41598-023-40929-5.
https://doi.org/10.2147/IDR.S405668.
Aduvukha, G.R., Abdel-Rahman, E.M., Mudereri, B.T., Mutanga, O., Odindi, J.,
Finda, M.F., Moshi, I.R., Monroe, A., Limwagu, A.J., Nyoni, A.P., Swai, J.K., Ngowo, H.S.,
Tonnang, H.E.Z., 2025. Spatiotemporal trends in Anopheles funestus breeding
Minja, E.G., Toe, L.P., Kaindoa, E.W., Coetzee, M., Manderson, L., Okumu, F.O.,
habitats. Int. J. Appl. Earth Obs. Geoinf. 136, 104351. https://doi.org/10.1016/j.
2019. Linking human behaviours and malaria vector biting risk in south-eastern
jag.2024.104351.
12

--- Page 13 ---
G.R. Aduvukha et al. S p a t i a l a n d S p a t i o - t e m p o r a l E p i d e m io l o g y 56 (2026) 100777
Tanzania. PLoS One 14 (6), e0217414. https://doi.org/10.1371/journal. Menze, B.D., Wondji, M.J., Tchapga, W., Tchoupo, M., Riveron, J.M., Wondji, C.S., 2018.
pone.0217414. Bionomics and insecticides resistance profiling of malaria vectors at a selected site
Fondjo, E., Toto, J.C., Tchouakui, M., Eyisap, W.E., Patchoke, S., Menze, B., for experimental hut trials in central Cameroon. Malar. J. 17 (1), 317. https://doi.
Njeambosay, B., Zeukeug, F., Ngomdjum, R.T., Mandeng, E., Elanga-Ndille, E., org/10.1186/s12936-018-2467-2.
Kopya, E., Binyang, J.A., Ndo, C., Tene-Fossog, B., Tedjou, A., Nchoutpouen, E., Merow, C., Smith, M.J., Silander, J.A., 2013. A practical guide to MaxEnt for modeling
Tchouine, F., Achu, D., Chabi, J., 2023. High vector diversity and malaria species’ distributions: What it does, and why inputs and settings matter. Ecography
transmission dynamics in five sentinel sites in Cameroon. Malar. J. 22 (1), 123. 36 (10), 1058–1069. https://doi.org/10.1111/j.1600-0587.2013.07872.x.
https://doi.org/10.1186/s12936-023-04552-z. Mieguim Ngninpogni, D., Ndo, C., Ntonga Akono, P., Nguemo, A., Nguepi, A., Metitsi, D.
Fuller, D.O., Troyo, A., Alimi, T.O., Beier, J.C., 2014. Participatory risk mapping of R., Tombi, J., Awono-Ambene, P., Bilong Bilong, C.F., 2021. Insights into factors
malaria vector exposure in northern South America using environmental and sustaining persistence of high malaria transmission in forested areas of sub-Saharan
population data. Appl. Geogr. 48, 1–7. https://doi.org/10.1016/j. Africa: The case of Mvoua, South Cameroon. Parasites Vectors 14 (1), 2. https://doi.
apgeog.2014.01.002. org/10.1186/s13071-020-04525-0.
Gatton, M.L., Chitnis, N., Churcher, T., Donnelly, M.J., Ghani, A.C., Godfray, H.C.J., Mmbando, A.S., Kaindoa, E.W., Ngowo, H.S., Swai, J.K., Matowo, N.S.,
Gould, F., Hastings, I., Marshall, J., Ranson, H., Rowland, M., Shaman, J., Lindsay, S. Kilalangongono, M., Lingamba, G.P., Mgando, J.P., Namango, I.H., Okumu, F.O.,
W., 2013. The importance of mosquito behavioural adaptations to malaria control in Nelli, L., 2021. Fine-scale distribution of malaria mosquitoes biting or resting outside
Africa. Evolution 67 (4), 1218–1230. https://doi.org/10.1111/evo.12063. human dwellings in three low-altitude Tanzanian villages. PLoS One 16 (1),
Gillies, M.T., Wilkes, TJ., 1963. Observations on nulliparous and parous rates in a e0245750. https://doi.org/10.1371/journal.pone.0245750.
population of Anopheles funestus in East Africa. Ann. Trop. Med. Parasitol. 57, National Center for Emerging and Zoonotic Infectious Diseases (NCEZID) (2024).
204–213. https://doi.org/10.1080/00034983.1963.11686175. Malaria. Retrieved from https://www.cdc.gov/dpdx/malaria/index.html.
Gorelick, N., Hancher, M., Dixon, M., Ilyushchenko, S., Thau, D., Moore, R., 2017. Naimi, B., Hamm, N.A.S., Groen, T.A., Skidmore, A.K., Toxopeus, A.G., 2014. Where is
Google earth engine: planetary-scale geospatial analysis for everyone. Remote Sens. positional uncertainty a problem for species distribution modelling? Ecography 37
Environ. 202, 18–27. https://doi.org/10.1016/j.rse.2017.06.031. (2), 191–203. https://doi.org/10.1111/j.1600-0587.2013.00205.x.
Gwitira, I., Murwira, A., Zengeya, F.M., Shekede, M.D., 2018. Application of GIS to Nzioki, I., Machani, M.G., Onyango, S.A., Kabui, K.K., Githeko, A.K., Ochomo, E.,
predict malaria hotspots based on Anopheles arabiensis habitat suitability in Yan, G., Afrane, Y.A., 2023. Differences in malaria vector biting behavior and
Southern Africa. Int. J. Appl. Earth Obs. Geoinf. 64, 12–21. https://doi.org/ changing vulnerability to malaria transmission in contrasting ecosystems of western
10.1016/j.jag.2017.08.009. Kenya. Parasites Vectors 16 (1), 376. https://doi.org/10.1186/s13071-023-05944-5.
Huete, A., Didan, K., Miura, T., Rodriguez, E.P., Gao, X., Ferreira, L.G., 2002. Overview Olabimi, I.O., Ileke, K.D., Adu, B.W., Arotolu, T.E., 2021. Potential distribution of the
of the radiometric and biophysical performance of the MODIS vegetation indices. primary malaria vector Anopheles gambiae Giles [Diptera: Culicidae] in Southwest
Remote Sens. Environ. 83 (1), 195–213. https://doi.org/10.1016/S0034-4257(02) Nigeria under current and future climatic conditions. J. Basic Appl. Zool. 82 (1), 63.
00096-2. https://doi.org/10.1186/s41936-021-00261-8.
Iban˜ez-Justicia, A., Cianci, D., 2015. Modelling the spatial distribution of the nuisance Ototo, E.N., Mbugi, J.P., Wanjala, C.L., Zhou, G., Githeko, A.K., Yan, G., 2015.
mosquito species Anopheles plumbeus (Diptera: Culicidae) in the Netherlands. Surveillance of malaria vector population density and biting behaviour in western
Parasites Vectors 8 (1), 258. https://doi.org/10.1186/s13071-015-0865-7. Kenya. Malar. J. 14 (1), 244. https://doi.org/10.1186/s12936-015-0763-7.
Ibrahim, E.A., Wamalwa, M., Odindi, J., Tonnang, H.E.Z., 2024. Spatio-temporal Paaijmans, K.P., Takken, W., Githeko, A.K., Jacobs, A.F.G., 2008. The effect of water
characterization of phenotypic resistance in malaria vector species. BMC Biol. 22 (1), turbidity on the near-surface water temperature of larval habitats of the malaria
117. https://doi.org/10.1186/s12915-024-01915-z. mosquito Anopheles gambiae. Int. J. Biometeorol. 52 (8), 747–753. https://doi.org/
Kohavi, R., 1995. A study of cross-validation and bootstrap for accuracy estimation and 10.1007/s00484-008-0167-2.
model selection. In: Proceedings of the 14th International Joint Conference on Paaijmans, K.P., Thomas, M.B., 2011. The influence of mosquito resting behaviour and
Artificial Intelligence - Volume 2, pp. 1137–1143. associated microclimate for malaria risk. Malar. J. 10 (1), 183. https://doi.org/
Kouame, R.M.A., Edi, A.V.C., Cain, R.J., Weetman, D., Donnelly, M.J., Sedda, L., 2024. 10.1186/1475-2875-10-183.
Joint spatial modelling of malaria incidence and vector’s abundance shows Padilla, O., Rosas, P., Moreno, W., Toulkeridis, T., 2017. Modeling of the ecological
heterogeneity in malaria-vector geographical relationships. J. Appl. Ecol. 61 (2), niches of the anopheles spp in Ecuador by the use of geo-informatic tools. Spat.
365–378. https://doi.org/10.1111/1365-2664.14565. SpatiotempOral Epidemiol. 21, 1–11. https://doi.org/10.1016/j.sste.2016.12.001.
Kreppel, K.S., Viana, M., Main, B.J., Johnson, P.C.D., Govella, N.J., Lee, Y., Maliti, D., Patz, J.A., Strzepek, K., Lele, S., Hedden, M., Greene, S., Noden, B., Hay, S.I.,
Meza, F.C., Lanzaro, G.C., Ferguson, H.M., 2020. Emergence of behavioural Kalkstein, L., Beier, J.C., 1998. Predicting key malaria transmission factors, biting
avoidance strategies of malaria vectors in areas of high LLIN coverage in Tanzania. and entomological inoculation rates, using modelled soil moisture in Kenya. Trop.
Sci. Rep. 10 (1), 14527. https://doi.org/10.1038/s41598-020-71187-4. Med. Int. Health TM IH 3 (10), 818–827. https://doi.org/10.1046/j.1365-
Kulkarni, M.A., Desrochers, R.E., Kajeguka, D.C., Kaaya, R.D., Tomayer, A., Kweka, E.J., 3156.1998.00309.x.
Protopopoff, N., Mosha, F.W., 2016. 10 years of environmental change on the slopes Pedrycz, W., 1993. Why triangular membership functions? Fuzzy Set. Syst. 64 (1), 21–30.
of mount Kilimanjaro and its associated shift in malaria vector distributions. Front. Phillips, S.J., Dudík, M., 2008. Modeling of species distributions with Maxent: new
Public Health 4. https://www.frontiersin.org/articles/10.3389/fpubh.2016.00281. extensions and a comprehensive evaluation. Ecography 31 (2), 161–175. https://doi.
Kwi, P.N., Ewane, E.E., Moyeh, M.N., Tangi, L.N., Ntui, V.N., Zeukeng, F., Sofeu- org/10.1111/j.0906-7590.2008.5203.x.
Feugaing, D.D., Achidi, E.A., Cho-Ngwa, F., Amambua-Ngwa, A., Bigoga, J.D., Phillips, S.J. 2017. A brief tutorial on maxent. Available from url: https://biodive
Apinjoh, T.O., 2022. Diversity and behavioral activity of Anopheles mosquitoes on rsityinformatics.amnh.org/open_source/maxent/Maxent_tutorial2017.pdf.
the slopes of Mount Cameroon. Parasites Vectors 15 (1), 344. https://doi.org/ R Core Team, 2022. R: A Language and Environment For Statistical Computing. R
10.1186/s13071-022-05472-8. Foundation for Statistical Computing, Vienna, Austria. URL. https://www.R-project.
Kyalo, R., Abdel-Rahman, E.M., Mohamed, S.A., Ekesi, S., Borgemeister, C., org/.
Landmann, T., 2018. Importance of remotely-sensed vegetation variables for Sanou, A., Nelli, L., Guelb´eogo, W.M., Ciss´e, F., Tapsoba, M., Ou´edraogo, P., Sagnon, N.,
predicting the spatial distribution of African citrus triozid (Trioza erytreae) in Kenya. Ranson, H., Matthiopoulos, J., Ferguson, H.M., 2021. Insecticide resistance and
ISPRS Int. J. Geoinf. 7 (11), Article 11. https://doi.org/10.3390/ijgi7110429. behavioural adaptation as a response to long-lasting insecticidal net deployment in
Landmann, T., Agboka, K.M., Klein, I., Abdel-Rahman, E.M., Kimathi, E., Mudereri, B.T., malaria vectors in the Cascades region of Burkina Faso. Sci. Rep. 11 (1), 17569.
Malenge, B., Mohamed, M.M., Tonnang, H.E.Z., 2023. Towards early response to https://doi.org/10.1038/s41598-021-96759-w.
desert locust swarming in eastern Africa by estimating timing of hatching. Ecological Saltelli, A., Annoni, P., Azzini, I., Campolongo, F., Ratto, M., Tarantola, S., 2010.
Modelling 484, 110476. https://doi.org/10.1016/j.ecolmodel.2023.110476. Variance based sensitivity analysis of model output. Design and estimator for the
Lindblade, K.A., Mwandama, D., Mzilahowa, T., Steinhardt, L., Gimnig, J., Shah, M., total sensitivity index. Comput. Phys. Commun. 181 (2), 259–270. https://doi.org/
Bauleni, A., Wong, J., Wiegand, R., Howell, P., Zoya, J., Chiphwanya, J., 10.1016/j.cpc.2009.09.018.
Mathanga, D.P., 2015. A cohort study of the effectiveness of insecticide-treated bed Soma, D.D., Zogo, B., Taconet, P., Som´e, A., Coulibaly, S., Baba-Moussa, L.,
nets to prevent malaria in an area of moderate pyrethroid resistance. Malawi. Ou´edraogo, G.A., Koffi, A., Pennetier, C., Dabir´e, K.R., Moiroux, N., 2021.
Malaria Journal 14 (1), 31. https://doi.org/10.1186/s12936-015-0554-1. Quantifying and characterizing hourly human exposure to malaria vectors bites to
Liu, Q., Wang, M., Du, Y.T., Xie, J.W., Yin, Z.G., Cai, J.H., Zhao, T.Y., Zhang, H.D., 2024. address residual malaria transmission during dry and rainy seasons in rural
Possible potential spread of Anopheles stephensi, the Asian malaria vector. BMC Southwest Burkina Faso. BMC Public Health 21 (1), 251. https://doi.org/10.1186/
Infect. Dis. 24 (1), 333. https://doi.org/10.1186/s12879-024-09213-3. s12889-021-10304-y.
Maia, M.F., Onyango, S.P., Thele, M., Simfukwe, E.T., Turner, E.L., Moore, S.J., 2013. Do Souza, D.de, Kelly-Hope, L., Lawson, B., Wilson, M., Boakye, D., 2010. Environmental
topical repellents divert mosquitoes within a community? – Health equity Factors Associated with the Distribution of Anopheles gambiae s.s in Ghana; an
implications of topical repellents as a mosquito bite prevention tool. PLoS One 8 Important Vector of Lymphatic Filariasis and Malaria. PLOS ONE 5 (3), e9927.
(12), e84875. https://doi.org/10.1371/journal.pone.0084875. https://doi.org/10.1371/journal.pone.0009927.
Makori, D.M., Fombong, A.T., Abdel-Rahman, E.M., Nkoba, K., Ongus, J., Irungu, J., Taheri, S., Gonz´alez, M.A., Ruiz-Lo´pez, M.J., Magallanes, S., Delacour-Estrella, S.,
Mosomtai, G., Makau, S., Mutanga, O., Odindi, J., Raina, S., Landmann, T., 2017. Lucientes, J., Bueno-Marí, R., Martínez-de la Puente, J., Bravo-Barriga, D.,
Predicting spatial distribution of key honeybee pests in Kenya using remotely sensed Frontera, E., Polina, A., Martinez-Barciela, Y., Pereira, J.M., Garrido, J., Aranda, C.,
and bioclimatic variables: key honeybee pests distribution models. ISPRS Int. J. Marzal, A., Ruiz-Arrondo, I., Oteo, J.A., Ferraguti, M., Figuerola, J., 2024. Modelling
Geoinf. 6 (3), 66. https://doi.org/10.3390/ijgi6030066. the spatial risk of malaria through probability distribution of Anopheles
Marchini, A., 2011. Modelling ecological processes with fuzzy logic approaches. In: maculipennis s.l. And imported cases. Emerg. Microbes. Infect. 13 (1), 2343911.
Jopp, F., Reuter, H., Breckling, B. (Eds.), Modelling Complex Ecological Dynamics. https://doi.org/10.1080/22221751.2024.2343911.
Springer, Berlin Heidelberg, pp. 133–145. https://doi.org/10.1007/978-3-642- Takken, W., Charlwood, D., Lindsay, S.W., 2024. The behaviour of adult Anopheles
05029-9_10. gambiae, sub-Saharan Africa’s principal malaria vector, and its relevance to malaria
13

--- Page 14 ---
G.R. Aduvukha et al. S p a t i a l a n d S p a t i o - t e m p o r a l E p i d e m io l o g y 56 (2026) 100777
control: a review. Malar. J. 23 (1), 161. https://doi.org/10.1186/s12936-024- U.S. President’s Malaria Initiative, 2023. Cameroon Malaria Operational Plan FY 2020.
04982-3. In: .
Tauxe, G.M., MacWilliam, D., Boyle, S.M., Guda, T., Ray, A., 2013. Targeting a dual Wiebe, A., Longbottom, J., Gleave, K., Shearer, F.M., Sinka, M.E., Massey, N.C.,
detector of skin and CO2 to modify mosquito host seeking. Cell 155 (6), 1365–1379. Cameron, E., Bhatt, S., Gething, P.W., Hemingway, J., Smith, D.L., Coleman, M.,
https://doi.org/10.1016/j.cell.2013.11.013. Moyes, C.L., 2017. Geographical distributions of African malaria vector sibling
Tepa, A., Kengne-Ouafo, J.A., Djova, V.S., Tchouakui, M., Mugenzi, L.M.J., Djouaka, R., species and evidence for insecticide resistance. Malar. J. 16 (1), 85. https://doi.org/
Pieme, C.A., Wondji, C.S., 2022. Molecular drivers of multiple and elevated 10.1186/s12936-017-1734-y.
resistance to insecticides in a population of the malaria vector anopheles gambiae in Wisz, M.S., Hijmans, R.J., Li, J., Peterson, A.T., Graham, C.H., Guisan, A., Group, N.P.S.
agriculture hotspot of west Cameroon. Genes 13 (7). https://doi.org/10.3390/ D.W., 2008. Effects of sample size on the performance of species distribution models.
genes13071206 (Basel)Article 7. Diversity and Distributions 14 (5), 763–773. https://doi.org/10.1111/j.1472-
Todorov, V., Dimov, I., Ostromsky, T., Apostolov, S., Georgieva, R., Dimitrov, Y., 4642.2008.00482.x.
Zlatev, Z., 2021. Advanced stochastic approaches for Sobol’ sensitivity indices Wu, Y., Qiao, Z., Wang, N., Yu, H., Feng, Z., Li, X., Zhao, X., 2017. Describing interaction
evaluation. Neural Comput. Appl. 33 (6), 1999–2014. https://doi.org/10.1007/ effect between lagged rainfalls on malaria: an epidemiological study in south–west
s00521-020-05074-4. China. Malar. J. 16 (1), 53. https://doi.org/10.1186/s12936-017-1706-2.
Tondossama, N., Virgillito, C., Coulibaly, Z.I., Pichler, V., Dia, I., della Torre, A., Zadeh, L.A., 1965. Fuzzy sets. Inf. Control 8 (3), 338–353. https://doi.org/10.1016/
Tour´e, A.O., Adja, A.M., Caputo, B., 2023. A high proportion of Malaria vector biting S0019-9958(65)90241-X.
and resting indoors despite extensive LLIN coverage in Coˆte d’Ivoire. Insects 14 (9),
Article 9. https://doi.org/10.3390/insects14090758.
14