# Associations between environmental covariates and temporal changes in malaria incidence in high transmission settings of Uganda: a distributed lag nonlinear analysis
**Authors:** Jaffer Okiring, Isobel Routledge, Adrienne Epstein, Jane F. Namuganga, Emmanuel V. Kamya, Gloria Odei Obeng-Amoako, Catherine Maiteki Sebuguzi, Damian Rutazaana, Joan N. Kalyango, Moses R. Kamya, Grant Dorsey, Ronald Wesonga, Steven M. Kiwuwa, Joaniter I. Nankabirwa
**Journal:** BMC Public Health | **Year:** 2021 | **DOI:** 10.1186/s12889-021-11949-5
**File:** papers/core-hypothesis/Associations between environmental covariates and temporal changes in malaria incidence in high transmission settings of Uganda- a distributed lag nonlinear analysis .md

---

## Abstract

Environmental covariates such as temperature, rainfall, and vegetation cover are critical drivers of malaria transmission, yet their quantitative relationships with disease burden remain poorly characterized—especially in high-transmission sub-Saharan African settings. This study leverages data from seven Malaria Reference Centres (MRCs) in Uganda over a 24-month period (January 2019–December 2020) to quantify exposure-lag-response effects of environmental covariates on monthly malaria incidence. Remote-sensing environmental data (MODIS land surface temperature, CHIRPS rainfall, MODIS NDVI) were linked to health facility catchment-area incidence estimates, and a distributed lag nonlinear model (DLNM) was used to capture non-linear and temporally delayed associations.

The median monthly malaria incidence across sites was 790 per 1000 person-years, with substantial spatial heterogeneity (range 73–3973). Temperature of 35°C (vs. the median 30°C) was significantly associated with increased incidence at lag 2 months (IRR 2.00, 95% CI 1.42–2.83), with the cumulative IRR peaking at lag 4 months (IRR 8.16, 95% CI 3.41–20.26). Rainfall of 200mm (vs. median 133mm) increased incidence at lag 0 (IRR 1.24, 95% CI 1.01–1.52), with cumulative IRR peaking at lag 4 (IRR 1.99, 95% CI 1.22–2.27). High NDVI (0.72 vs. median 0.66) increased cumulative IRR at lags 2–4, peaking at lag 4 (IRR 1.57, 95% CI 1.09–2.25). Granger causality tests confirmed that all three covariates significantly affect the temporal distribution of malaria incidence across sites combined.

The study demonstrates that in high-transmission Ugandan settings, elevated temperature, rainfall, and NDVI are associated with increased malaria incidence at characteristic lag times. These quantified exposure-lag-response relationships provide an evidence base for designing early warning systems, targeting preventive interventions, and planning seasonal malaria control strategies. The DLNM framework proved effective for capturing the complex, nonlinear, and delayed nature of environment-malaria associations.

## Methods

- **Study design:** Ecological time-series analysis using health facility surveillance data from 7 MRCs in high-transmission Ugandan districts (Aduku, Lobule, Awach, Lalogi, Patongo, Padibe, Namokora) where indoor residual spraying was not implemented.
- **Outcome:** Monthly malaria incidence per 1000 person-years, derived from catchment-area population estimates (AfriPop database with 0.0029/unit population growth).
- **Environmental covariates:** Daytime land surface temperature (°C) from MODIS (1km, monthly), CHIRPS rainfall (0.05° resolution, monthly), NDVI from MODIS (1km, monthly, gap-filled for cloud cover using random forest).
- **Statistical analysis:** Cross-correlation to determine optimal lags; Granger causality Wald tests; Distributed Lag Nonlinear Model (DLNM) with second-order natural cubic splines for non-linear and lag effects; health facility random effects; seasonality controlled via 4 degrees of freedom per year; QAIC-based model selection.
- **Software:** R 3.6.0 with `dlnm` and `lme4` packages; QGIS for raster extraction.
- **Sensitivity analysis:** 1000 simulations (Barrera-Gomez & Basagana method) to rule out multi-collinearity confound.

## Key Results

- **Incidence:** Median 790/1000 PY (range 73–3973); highest at Patongo HC (1272/1000 PY), lowest at Namokora HC (337.5/1000 PY).
- **Temperature:** High temperature (35°C) increased IRR at lag 2 (IRR 2.00, 95% CI 1.42–2.83); cumulative IRR peaked at lag 4 (IRR 8.16, 95% CI 3.41–20.26). Low temperature (26°C) showed no significant effect at any lag.
- **Rainfall:** High rainfall (200mm) increased IRR at lag 0 (IRR 1.24, 95% CI 1.01–1.52); cumulative IRR peaked at lag 4 (IRR 1.99, 95% CI 1.22–2.27). Low rainfall (3mm) showed extreme cumulative effect at lag 4 (IRR 26.70, 95% CI 1.82–397.0) but with wide CIs.
- **NDVI:** High NDVI (0.72) increased IRR at lag 2 (IRR 1.31, 95% CI 1.04–1.65); cumulative IRR peaked at lag 4 (IRR 1.57, 95% CI 1.09–2.25).
- **Granger causality:** All-sites combined showed strong causal effects for temperature (F=8.00, p<0.0001), rainfall (F=8.96, p=0.003), and NDVI (F=8.42, p<0.0001).
- **Saturation effect:** Cumulative IRR increased more rapidly in lags 1–2 than lags 3–4 for all covariates, suggesting diminishing marginal impact once conditions are sufficient for mosquito cycle completion.

## Relevance to MalariaSentinel (Centinela)

This paper provides critical parameterization data for the Centinela's environmental covariate layer. The DLNM-derived lag-response relationships (temperature→IRR at lag 2, rainfall→IRR at lag 0, NDVI→IRR at lag 2) can directly inform the suitability overlay in the ABM/SDSS pipeline—quantifying how antecedent environmental conditions modulate transmission risk. The use of CHIRPS and MODIS data sources aligns with the project's existing data pipeline (already used in `mal-ghana-sim`). The finding that cumulative effects compound over months supports the need for multi-temporal environmental feature engineering (cf. the climate lag features used in Onimisi 2025). Uganda's bimodal seasonality pattern also validates the 4-df seasonal control approach for transmission models in East African settings.

## Full Text

--- Page 1 ---
Okiringetal.BMCPublicHealth (2021) 21:1962
https://doi.org/10.1186/s12889-021-11949-5
RESEARCH ARTICLE Open Access
Associations between environmental
covariates and temporal changes in malaria
incidence in high transmission settings of
Uganda: a distributed lag nonlinear analysis
Jaffer Okiring1,2* , Isobel Routledge3, Adrienne Epstein3, Jane F. Namuganga2, Emmanuel V. Kamya2,
Gloria Odei Obeng-Amoako1, Catherine Maiteki Sebuguzi4, Damian Rutazaana4, Joan N. Kalyango1,
Moses R. Kamya2,5, Grant Dorsey6, Ronald Wesonga7, Steven M. Kiwuwa8 and Joaniter I. Nankabirwa1,2
Abstract
Background: Environmental factors such as temperature, rainfall, and vegetation cover play a critical rolein malaria
transmission. However, quantifying therelationships between environmentalfactors and measuresof disease
burden relevant for public health can be complex as effects are often non-linear and subjectto temporallags
between when changes in environmentalfactors lead to changes inmalaria incidence.The study investigated the
effect of environmentalcovariateson malaria incidence inhigh transmissionsettings ofUganda.
Methods: This study leveraged data from seven malaria reference centres (MRCs)located inhightransmission
settings ofUganda over a 24-month period. Estimates of monthly malaria incidence (MI) were derived from MRCs'
catchment areas.Environmental data including monthly temperature, rainfall, and normalized difference vegetation
index (NDVI) were obtained from remote sensing sources. A distributed lag nonlinear model was used to
investigate the effect of environmentalcovariateson malaria incidence.
Results: Overall, themedian (range) monthly temperature was 30°C (26–47), rainfall 133.0mm (3.0–247), NDVI 0.66
(0.24–0.80) and MIwas 790per 1000 person-years (73–3973).Temperature of35°C was significantly associated with
malaria incidence compared to themedian observed temperature (30°C) atmonth lag 2(IRR: 2.00, 95%CI: 1.42–
2.83) and the increased cumulative IRR ofmalaria atmonth lags1–4, with the highest cumulative IRR of 8.16 (95%
CI:3.41–20.26)at lag-month 4. Rainfall of 200mmsignificantly increased IRR ofmalaria compared to the median
observed rainfall (133mm) atlag-month0 (IRR: 1.24, 95% CI:1.01–1.52) and theincreased cumulative IRR of malaria
atmonth lags 1–4, withthehighest cumulativeIRRof1.99(95%CI:1.22–2.27) atlag-month 4. Average NVDI of 0.72
significantly increased thecumulative IRR ofmalaria compared to the median observed NDVI (0.66) at month lags
2–4,with the highest cumulativeIRR of1.57(95%CI: 1.09–2.25) at lag-month 4.
*Correspondence:okjaffer@gmail.com
1ClinicalEpidemiologyUnit,SchoolofMedicine,MakerereUniversityCollege
ofHealthSciences,Kampala,Uganda
2InfectiousDiseasesResearchCollaboration,2CNakaseroHillRoad,Kampala,
Uganda
Fulllistofauthorinformationisavailableattheendofthearticle
©TheAuthor(s).2021OpenAccessThisarticleislicensedunderaCreativeCommonsAttribution4.0InternationalLicense,
whichpermitsuse,sharing,adaptation,distributionandreproductioninanymediumorformat,aslongasyougive
appropriatecredittotheoriginalauthor(s)andthesource,providealinktotheCreativeCommonslicence,andindicateif
changesweremade.Theimagesorotherthirdpartymaterialinthisarticleareincludedinthearticle'sCreativeCommons
licence,unlessindicatedotherwiseinacreditlinetothematerial.Ifmaterialisnotincludedinthearticle'sCreativeCommons
licenceandyourintendeduseisnotpermittedbystatutoryregulationorexceedsthepermitteduse,youwillneedtoobtain
permissiondirectlyfromthecopyrightholder.Toviewacopyofthislicence,visithttp://creativecommons.org/licenses/by/4.0/.
TheCreativeCommonsPublicDomainDedicationwaiver(http://creativecommons.org/publicdomain/zero/1.0/)appliestothe
datamadeavailableinthisarticle,unlessotherwisestatedinacreditlinetothedata.

--- Page 2 ---
Okiringetal.BMCPublicHealth (2021) 21:1962 Page2of11
Conclusions: In high-malaria transmission settings, high values of environmentalcovariateswere associated with
increased cumulativeIRR ofmalaria, with IRR peaks atvariable lag times. The complex associations identifiedare
valuable for designing strategies for early warning, prevention, and control of seasonal malaria surges and
epidemics.
Keywords: Environmental, Covariates, Temporal, Effect, Malaria, Incidence,DLNM
Background the preceding lags. Additionally, the occurrence of ex-
Environmental covariates such as temperature, vegeta- treme environmental conditions in the recent past such
tion, and rainfall play a major role in malaria transmis- as prolonged rainfall seasons may have an impact on
sion [1–3], by changing the vector populations which malariaburden which isnotyetclear.
often lead to changes in malaria burden and yet the Climate change has had great impacts on infectious
quantitative relationships between changes in these co- diseases, with shifts in malaria transmission areas re-
variates and malaria incidence are not well characterized ported[16,17],asmaybereflectedinchangesofmalaria
inmanysettingsespeciallyinsubSaharanAfrica.Several burden provided through surveillance data. Routine mal-
factors complicate the characterization of these relation- aria surveillance focuses on measures of disease (rather
ships. Firstly, the effect of environmental covariates on than entomological measures) and measures of disease
mosquito and parasite populations may not be linear. are of greatest relevance from a public health perspec-
For instance, moderate increase in rainfall leads to in- tive. Recently Uganda has experienced extreme environ-
creased humidity which prolongs adult longevity of the mental conditions amidst a setting where malaria is
mosquitoes and a surge in their population while heavy already endemic in almost 95% of the country [18], and
rainfall reduces the populations by washing away the yet there is limited data on the quantitative relationship
mosquito larvae [4]. Similarly, temperature is a crucial between these covariates and malaria. Uganda Malaria
factor in the vector life-cycle. For instance, a rise in Surveillance Project (UMSP) in collaboration with Na-
temperature may also increase the blood meals taken tional Malaria Control Division (NMCD) have estab-
and eggs laid by the mosquito, increasing mosquito- lished an enhanced health facility-based malaria
population density affecting transmission. Lower tem- surveillance system at 70 public health facilities across
peratures, especially below 20°C, and too high tempera- the country referred to as the Malaria Reference Centers
tures may hamper the completion of mosquito growth (MRCs) [19]. At these MRCs, individual patient level
cycle [5, 6]. Vegetation may provide an outdoor resting data are collected and resources provided to maximize
habitant or shelter for mosquitoes from extreme condi- laboratory testing of all patients with suspected malaria.
tions unfavourable for mosquito-population growth. Data on village of residence of the patients is captured
Many studies have reported associations between and catchment areas around the MRCs identified, allow-
changes in malaria burden and patterns of environmental ing for the generation of estimates of malaria incidence
factors [7–13]. However, the associations reported (Program for resistance, immunology, surveillance, and
vary between settings. For example, a study from South modelling of malaria (prism) : Implementation Project
Africa found that an increase in temperature signifi- Pilot Study, Unpublished). In this study, the effect of en-
cantly raised malaria infections [12], while another in vironmental variability in rainfall, temperature and vege-
Ethiopia showed anegativecorrelation[13]. tation on malaria incidence in Uganda is quantified by
Environmental covariates may also show effects that investigating exposure-lag-response effects. Quantifying
are delayed in time, requiring examination of the tem- these relationships is a key step in producing useful sys-
poral dimension of the exposure–lag-response relation- tems to predict malaria incidence in the region and plan
ship. Most studies on the relationships between these for effective preventive strategies and sustainable long-
covariates and the malaria burden have relied on specific term malaria programming in the control of malaria
time lag, ignoring the cumulative effect of the environ- burden.
mental covariates which may last for a period longer
than the current time [7, 14, 15]. From the biological Methods
perspective, different periods including time for mos- Studysetting
quito to develop, period of parasites within the mos- This study leveraged data from UMSP derived from sen-
quito, and incubation period of the parasites within the tinel surveillance in level III and IV public outpatient fa-
human body makes the assumption of a specific time lag cilities that generally see between 1000 and 3000
unrealistic, as the observed effect of the environmental outpatients per month and have functioning laborator-
covariates in a given lag may be a cumulative effect from ies. These facilities provide care free of charge, including

--- Page 3 ---
Okiringetal.BMCPublicHealth (2021) 21:1962 Page3of11
diagnostic testing and medications. Full description of while high values were those greater than the median for
the MRCsand the data captured has been published else eachrespectiveenvironmentalcovariate.
where [20]. This study included data from seven of the
70 MRCs. MRCs were included if they met the following Outcome
criteria: 1) location in a high malaria burden area where The outcome was monthly malaria incidence defined as
indoor residual spraying of insecticide (IRS) was not be- total cases of malaria within a given health facility catch-
ing implemented, 2) had malaria incidence estimate data ment area divided by the population of the catchment
for the period between January 2019 to December 2020 area. Catchment areas were defined as villages where the
available. MRCs included in the analysis were Aduku MRC was located and adjacent villages with similar mal-
health centreIVinKwania District, Lobule health centre aria incidence to the village where the MRC is located.
III in Koboko District, Awach health centre IV in Gulu Details of how the catchment areas were estimated are
District, Lalogi health centre IV in Omoro District, published else where [20]. A given catchment area in-
Patongo health centre IV in Agago District, Padibe cluded 1–5 villages. The village level population esti-
health centre IV in Lamwo District, Namokora health mates for each catchment area were obtained from the
centre IV in Kitgum District. The location of these AfriPop database and included a fixed population
MRCs inUgandaisshown insupplementaryfileFig.S1. growth function of0.0029 perunittime[26].

Environmentalvariables Statisticalanalysis
Average monthly environmental data for the period of Cumulative data for the characteristics of the study pop-
January 2019–December 2020 were processed from re- ulations over the 24-month observation period (January
mote sensing sources. Data processed by remote sensing 2019 – December 2020) were summarized and pre-
included temperature (defined as day time land surface sented as monthly medians with corresponding ranges.
temperature measured in degrees Celsius), Normalized A cross-correlation analysis was performed to ascertain
Difference Vegetation Index (NDVI) defined as a dimen- the magnitude and direction of time-lagged relationships
sionless index used to measure neighborhood greenness betweenenvironmentalcovariatesandmalariaincidence,
[21], and rainfall. Rainfall data was collected from cli- and estimate the optimal lags. Optimal lags were defined
mate hazards group infrared precipitation with station as the month corresponding to the highest significant
data (CHIRPS) database and was measured in millime- correlation coefficient. The Granger causality Wald test
ters. CHIRPS incorporate 0.05° resolution satellite im- was performed to determine the likely effect of lagged
agery with in-situ station data to create gridded rainfall environmental factors on the variability of malaria inci-
time series for trend analysis and seasonal drought mon- dence. Thedistributed lag nonlinearmodel(DLNM)was
itoring [22]. Temperature and NDVI data was obtained used to investigate non-linear and lagged (specific and
from moderate resolution imaging spectro-radiometer cumulative) effects of environmental covariates on the
(MODIS) aboard the National Aeronautics and Space malariaincidence.
Administration (NASA) satellites [23]. Global MODIS The DLNM is a modeling framework used to investi-
data areprovidedevery monthat1-kmspatialresolution gate associations with potentially non-linear and delayed
as a gridded level-3 product in the sinusoidal projection effects on time-series data [27]. This methodology is
and were gap-filled to correct for cloud cover using a based on the definition of a cross-basis, which is a func-
random forest model with interpolated values, elevation, tion expressed by the combination of two sets of basic
and time [24]. Satellite environmental covariates were functions that specify the relationships in the dimension
preferred over nationally available estimates since they of predictor and time lags, respectively. Second order
had been shown to have an even spatial distribution natural cubic spline for environmental factors that gen-
[25], and were available at a low administrative level erated a basis matrix of polynomials was used for non-
such as a village, enabling derivation of health facility linear effect and lag effect. The more flexible lag effects
catchment area-specific estimates. The downloaded at shorter delays were obtained by placing spline knots
raster files were transferred into quantum geographical at equalintervals in the range of environmental variables
Information system (QGIS) software and village corre- and in the lag scale. Seasonality of malaria transmission
sponding environmental covariates' centroid values were was controlled by including four degrees of freedom per
extracted using Point Sampling tool. To give MRC spe- year in the model, representing the bimodal malaria
cific estimates of environmental covariate in a given peak seasons in Uganda [28]. A health facility-specific
month, the centroid values corresponding to the villages random variable was added to the model to control for
that form the catchment area were averaged. Low values unmeasured differences between the facilities. The
of each covariate (temperature, rainfall, and vegetation model was selected on the basis of the Quasi-Akaike In-
cover) included any value below the observed median formation Criterion (QAIC). The median value for each

--- Page 4 ---
Okiringetal.BMCPublicHealth (2021) 21:1962 Page4of11
variable was defined as the baseline reference for calcu- environmental variables at the study sites between
lating the IRR of the separate effect (in a specific lag- January 2019 and December 2020.
month) and cumulative effect (in all months preceding a
specific lag-month) on the malaria incidence. All the Temporaltrendandseasonalityofmalariaincidenceand
analyses were performed using R software version 3.6.0 environmentalcovariates
with "dlnm" and "lme4" packages. Statistical significance Malaria incidence across all-sites was highest in June
was determined using confidence intervals that do not 2019 (1344.5 cases per 1000 PY, 713–2922) and lowest
include theRRofthenullhypothesis of1.0. in April 2019 (239.5 cases per 1000 PY, 103–1128) with
Athousandsimulationswereruntoruleoutthepossi- seasonal peak in incidence observed from April to Sep-
bility of the effects being solely an influence of multi- tember 2019 and accounting for 28.9% of the observed
collinearity between temperature, rainfall, and vegetation malaria incidence.Temporal changes in monthly malaria
cover using the methodology proposed by Jose Barrera- incidence over the 24-month observation period by
G'omez and Xavier Basagana in the "Collin" package in MRC are presented in the supplementary file Fig. S3.
R [29]. The results are presented in the supplementary Correlation analysis revealed a positive relationship be-
file Fig. S2 and the findings suggest the possibility of tween temperature and malaria incidence at month lag 4
otherexplanations forthis result thanmulti-collinearity. (0.452), and a negative correlation for both rainfall (−
0.160) and NDVI (−0.454) with malaria incidence at
Results month lag 4. Across MRCs, the correlation coefficients
Summarydataonlongitudinalmeasuresofmalaria for temperature with malaria incidence were negative at
incidenceandenvironmentalcovariatesinhigh month lag 1 and positive at month lag 4. This pattern
transmissionsettingsofUganda was reversed for both rainfall and NDVI at month lags 1
Over the 24-month study period, the overall median and 4. In addition, the optimal lags for the correlations
monthly malaria incidence was 790 (range 73–3973) between environmental covariates and malaria incidence
cases per 1000 person years (PY), with the catchment varied by site (Table 2). The results of the Granger caus-
area around Patongo health centre having the highest ality tests indicated that the temporal distribution of
incidence at 1272 (176–3973) cases per 1000 PY, and malaria incidence was strongly affected by temperature,
area around Namokora health centre having the low- rainfall, andNDVI amongall-sitescombined(Table3).
est incidence at 337.5 (73–1238) cases per 1000 PY.
The overall median temperature was 30.0°C with Non-linearandlaggedeffectsofenvironmentalcovariates
Padibe and Namokora health centre recording the onmalariaincidence
highest temperatures (30.5°C) and Lobule health Temperature
centre recording the lowest at 28.0°C. The median With all sites combined; the incidence rate ratio (IRR) of
monthly rainfall was 133.0mm with highest estimates malaria increased at month lags 0–1 for temperature ap-
around Lalogi health centre (148.5mm, 8-214mm) proximately 45–47°C compared to the median observed
and lowest around Padibe health centre (111.5mm, 6- temperature (30.0°C). Complete summary of the non-
227mm). NDVI was highest at Lobule health centre linear relationship between monthly temperature and
(0.74) and lowest at Patongo health centre (0.61) with malaria incidence over a four-month period is revealed
the median across all-sites estimated at 0.66. Table 1 in part a of Fig. 1. The separate effects of different tem-
provides the details of the longitudinal measures of peratures and 2 month lags (0 and 4months) on the IRR

Table1SummarydataonlongitudinalmeasuresofEnvironmentalvariablesinhightransmissionsettingsofUganda2019–2020
Site Monthlymedian(range)
Temperature(degreesCelsius) Rainfall(mm) NDVI(index)
AdukuHC 29.00(27.00–40.00) 142.00(8.00–247.00) 0.68(0.35–0.75)
AwachHC 29.00(27.00–42.00) 138.50(7.00–232.00) 0.68(0.41–0.74)
LalogiHC 28.50(26.00–40.00) 148.50(8.00–214.00) 0.72(0.39–0.77)
PatongoHC 30.00(28.00–47.00) 129.50(3.00–223.00) 0.61(0.25–0.69)
PadibeHC 30.50(27.00–44.00) 111.50(6.00–227.00) 0.62(0.28–0.72)
NamokoraHC 30.50(27.00–47.00) 112.00(4.00–226.00) 0.62(0.24–0.75)
LobuleHC 28.00(26.00–41.00) 122.00(15.00–231.00) 0.73(0.33–0.80)
All-sitescombined 30.00(26.00–47.00) 133.00(3.00–247.00) 0.66(0.24–0.80)
NDVINormalizeddifferencevegetationindex

--- Page 5 ---
Okiringetal.BMCPublicHealth (2021) 21:1962 Page5of11
Table2Crosscorrelationcoefficientsbetweenenvironmentfactorsandthemalariaincidenceamonghightransmissionsettingsof
Uganda2019–2020
Site Environmentalvariables
Temperature Rainfall NDVI
Optimal Lag1 Lag4 optimal Lag1 Lag4 optimal Lag1 Lag4
AdukuHC −0.417(−1)* −0.417 0.366 0.511(−1)* 0.511 −0.113 0.620(−1)* 0.620 −0.299
AwachHC 0.496(−4)* −0.301 0.496 0.416(−1)* 0.416 −0.335 0.471(−1)* 0.471 −0.617
LalogiHC 0.613(−4)* −0.274 0.613 0.458(−1)* 0.458 −0.510 −0.717(−4)* 0.243 −0.717
PatongoHC 0.481(−4)* −0.424 0.481 0.485(−1)* 0.485 −0.205 0.453(−1)* 0.453 −0.559
PadibeHC −0.566(−1)* −0.566 0.477 0.731(−1)* 0.731 −0.120 0.426(−1)* 0.426 −0.555
NamokoraHC −0.668(−1)* −0.668 0.411 0.651(−1)* 0.617 −0.009 0.609(−1)* 0.609 −0.460
LobuleHC −0.466(−1)* −0.466 0.334 0.526(−1)* 0.551 −0.195 0.534(−1)* 0.525 −0.336
All-sitescombined 0.452(−4)* −0.302 0.452 0.403(−1)* 0.403 −0.160 −0.454(−4)* 0.275 −0.454
NDVINormalizeddifferencevegetationindex
togetherwiththe95%confidenceintervalsareprovidedin month period is revealed in part a of Fig. 2. The IRR of
partbofFig.1.TemperatureincreasedtheIRRsteadilyat malaria incidence increased at low rainfall in lag-month
monthlag0andincreasedtheIRRtoapeakatmonthlag 4 and for rainfall approximately above 200mm inmonth
4.Atlowtemperature,theIRRincreasedto1.22(95%CI, lags 1–4 compared to the median observed rainfall (133
0.68–2.16) at approximately 26.0°C in month lag 4 as mm). The separate effects of different rainfall values and
compared to the median observed temperature (30.0°C). two-month lags (0 and 4months) on the IRR together
At temperatureof approximately35°C, the IRR increased with the 95% confidence intervals are provided in part b
significantly to 2.00 (95% CI, 1.42–2.83) in month lag 2 of Fig. 2. Increase in rainfall increased the IRR steadily
compared to the median observed temperature (30.0°C) to a peak at approximately 200mm. While at month lag
(Table 4). The effect of temperature on the cumulative 4, increase in rainfall reduced the IRR drastically for
IRRofmalariaisshowninpartcofFig.1.Temperatureof values below 50mm and flattened at IRR of 1.0 for
approximately 35°C increased the cumulative IRR signifi- values approximately 50-200m. Overall at low rainfall,
cantly at month lags 1–4 compared to the median ob- the IRR increased significantly to 4.05 (95% CI, 1.40–
servedtemperature(30.0°C)and theIRRof8.16(95%CI, 11.54) at approximately 3mm in month lag 4 compared
3.41–20.26)wasthehighestatmonthlag4(Table4). to the median observed rainfall (133mm). At high rain-
fall, the IRR increased significantly to 1.24 (95% CI,
1.01–1.52) as compared to the median observed rainfall
Rainfall (133mm) at approximately 200mm in month lag 0
A summary of the non-linear relationship between (Table 4). The effect of rainfall on the cumulative IRR of
monthly rainfall and malaria incidence over a four- malaria is shown in part c of Fig. 2. Rainfall of

Table3Grangercasualitytestsforenvironmentalfactors(variables)andmonthlymalariaincidenceinhightransmissionsettingsof
Uganda2019–2020
Site Environmentalvariables
Temperature Rainfall NDVI
F-statistics(pvalue) F-statistics(pvalue) F-statistics(pvalue)
AdukuHC 0.0004(0.9839) 4.3100(0.051) 1.2388(0.2789)
AwachHC 0.8251(0.536) 3.2346(0.0872) 3.8258(0.0646)
LalogiHC 1.2804(0.3356) 1.8236(0.1920) 4.9558(0.0157)
PatongoHC 1.1143(0.3982) 3.6732(0.0697) 0.8423(0.3697)
PadibeHC 0.0732(0.7895) 8.8014(0.0076) 0.7569(0.3946)
NamokoraHC 1.8881(0.1846) 2.0669(0.1660) 0.6985(0.4131)
LobuleHC 3.2905(0.0847) 6.0919(0.0227) 5.3309(0.0318)
All-sitescombined 7.9999(<0.0001)a 8.9646(0.0032)a 8.4206(<0.0001)a
aTemporaldistributionofmalariaincidenceisstronglyaffectedbytherespectiveenviromentalfactors
NDVINormalizeddifferencevegetationindex

--- Page 6 ---
Okiringetal.BMCPublicHealth (2021) 21:1962 Page6of11
approximately 200mm increased the cumulative IRR surveillance data has been used to monitor trends
from month lags 1–4 compared to the median observed in malaria burden and visualization of prior seasonal
rainfall (133mm) andtheRRof1.99 (95%CI,1.22–2.27) peaks in different transmission settings. The addition of
wasthehighest atmonth lag4(Table4). place of residence as part of routine surveillance data
collection tool has enabled estimation of health facility
Normalizeddifferencevegetationindex catchment areas and generation of malaria incidence es-
Part a of Fig. 3 presents a summary of the non-linear re- timates to derive a direct measure of disease burden.
lationshipbetweenmonthlyNDVIandmalariaincidence Combining health facility surveillance data with envi-
over a four-month period. The IRR of malaria incidence ronmental covariates such as rainfall, temperature and ve-
increased at high NDVI values in month lags 2–4 at ap- getation coverage available through remote-sensing
proximately0.72–0.80comparedtothemedian observed sources may benefit malaria control efforts, as environ-
NDVI (0.66). The separate effects of different NDVI mental covariates are reported to facilitate malaria trans-
valuesand2monthlags(0and4months)ontheIRRto- mission [31].
gether with the 95% confidence intervals are provided in The relationship between environmental covariates
part b of Fig. 3. Increase in NDVI increased the IRR and malaria incidence may form a strong basis for mal-
drastically for values below approximately 0.5 to a peak aria early warning systems, as such prediction tools may
at month lag 0. While at month lag 4, increase in NDVI guide planning and control of malaria outbreaks. For in-
reducedtheIRRdrasticallyforvaluesbelow0.3andthen stance rainfall and sea surface temperature have been
increased at approximately above 0.70. Overall at low used for monitoring malaria early warnings in Botswana
NDVI, the IRR increased to 1.80 (95% CI, 0.35–9.43) at with the success of the malaria control program in redu-
approximately 0.24 in month lag 2 compared to the me- cing malaria incidence attributed to the early warnings
dian observed NDVI (0.66). At high NDVI, the IRR in- [25]. Similarly in South Africa, prediction of malaria
creased significantly to 1.31 (95% CI, 1.04–1.65) based on the seasonal climate forecasts showed that
compared to the median observed NDVI (0.66) at ap- short-term predictions coincided closely with the ob-
proximately 0.72 in month lag 2 (Table 4). The effect of served malaria cases, which may also benefit the malaria
NDVI on the cumulative IRR of malaria is shownin part
c of Fig. 3. High NDVI increased the cumulative IRR of early warning system [32]. In this study, high
malaria significantly within month lags 2–4 compared to temperature increased the IRR of malaria at month lag
the median observed NDVI (0.66) and the IRR of 1.57 4. Knowing temperature as a key parameter in mosquito
(95% CI, 1.09–2.25) was the highest at approximately development, biting and survival with warmer tempera-
0.72inmonth lag4(Table4). tures increasing the infection rates as the vector repro-
duces faster, the likelihood of infection after a mosquito
Discussion bite is amplified [33]. Even if the specific effect of
The relationship between environmental covariates and temperature on the IRR of malaria increased in month
malaria burden is complex, as the effect is not only de- lag 2, the cumulative IRR increased significantly at
termined in the current period but may also be influ- month lags 1–4. The increased cumulative IRR could
enced by preceding time points. This study investigated possibly be explained by the increased multiplication
the quantitative effect of environmental covariates on rate presented by global warming increasing the length
malaria incidence in high malaria transmission areas in of mosquito breeding season [33]. The month lagged ef-
Uganda. In these settings, temperature, rainfall and fectsoftemperaturewouldavailtimelongenoughtode-
NDVI significantly affected the temporal distribution of sign interventions to interrupt malaria transmission,
malaria incidence. High (greater than the observed me- despite temperature values used in the current study be-
dian) temperature values increased the IRR of malaria ing high as compared to the optimal temperature for
significantly in month lag 4 and the cumulative IRR at malaria transmission of 29°C [34]. However, this finding
month lags 1–4 compared to the median observed
temperature. Similarly, high rainfall increased the IRR of
malaria significantly at the month lag 0 and the cumula-
tive IRR at month lags 1–4 compared to the median ob-
served rainfall. High values of NDVI increased the
cumulative IRR of malaria significantly at month lags 2–
4comparedtothemedianobservedNDVI.
Malaria control remains a priority in the national
healthagenda,requiringplanningandefficientallocation
of the limited resources available [30]. Efficient alloca-
tions of resources rely not only on current measures of
malaria burden but also predicting future malaria bur-
den. Surveillance data has been used to monitor trends
in malaria burden and visualization of prior seasonal
peaks in different transmission settings. The addition of
place of residence as part of routine surveillance data
collection tool has enabled estimation of health facility
catchment areas and generation of malaria incidence es-
timates to derive a direct measure of disease burden.
Combining health facility surveillance data with envi-
ronmental covariates such as rainfall, temperature and ve-
getation coverage available through remote-sensing
sources may benefit malaria control efforts, as environ-
mental covariates are reported to facilitate malaria trans-
mission [31].
The relationship between environmental covariates
and malaria incidence may form a strong basis for mal-
aria early warning systems, as such prediction tools may
guide planning and control of malaria outbreaks. For in-
stance rainfall and sea surface temperature have been
used for monitoring malaria early warnings in Botswana
with the success of the malaria control program in redu-
cing malaria incidence attributed to the early warnings
[25]. Similarly in South Africa, prediction of malaria
based on the seasonal climate forecasts showed that
short-term predictions coincided closely with the ob-
served malaria cases, which may also benefit the malaria
early warning system [32]. In this study, high
temperature increased the IRR of malaria at month lag
4. Knowing temperature as a key parameter in mosquito
development, biting and survival with warmer tempera-
tures increasing the infection rates as the vector repro-
duces faster, the likelihood of infection after a mosquito
bite is amplified [33]. Even if the specific effect of
temperature on the IRR of malaria increased in month
lag 2, the cumulative IRR increased significantly at
month lags 1–4. The increased cumulative IRR could
possibly be explained by the increased multiplication
rate presented by global warming increasing the length
of mosquito breeding season [33]. The month lagged ef-
fectsoftemperaturewouldavailtimelongenoughtode-
sign interventions to interrupt malaria transmission,
despite temperature values used in the current study be-
ing high as compared to the optimal temperature for
malaria transmission of 29°C [34]. However, this finding

--- Page 7 ---
Okiringetal.BMCPublicHealth (2021) 21:1962 Page7of11

Table4DLNMmodelresultsforseparateandcumulativeeffectsofenvironmentalvariablesontheRRofmalariaburdeninhigh
transmissionsettingsofUganda
Effecttype Specification Statistic Variable
Temperature Rainfall NDVI
Separateeffect Low Variablevalue 26 3 0.24
Peakmonth 4 4 2
IRRatpeakmonth 1.22(0.68–2.16) 4.05(1.40–11.54)a 1.80(0.35–9.43)
High Variablevalue 35 200 0.72
Peakmonth 2 0 2
IRRatpeakmonth 2.00(1.42–2.83)a 1.24(1.01–1.52)a 1.31(1.04–1.65)a
Cumulativeeffect Monthlag1 Variablevalue 26 3 0.24
IRR 0.69(0.31–1.62) 2.52(0.72–8.56) 0.44(0.08–2.36)
Variablevalue 35 200 0.72
IRR 2.19(1.21–3.89)a 1.50(1.12–2.00)a 1.09(0.87–1.38)
Monthlag2 Variablevalue 26 3 0.24
IRR 0.43(0.14–1.42) 3.16(0.57–17.41) 0.79(0.13–4.78)
Variablevalue 35 200 0.72
IRR 4.39(2.09–9.21)a 1.87(1.31–2.69)a 1.42(1.06–1.89)a
Monthlag3 Variablevalue 26 3 0.24
IRR 0.36(0.10–1.55) 6.73(0.64–68.29) 0.54(0.06–4.68)
Variablevalue 35 200 0.72
IRR 8.08(3.41–20.26)a 1.95(1.28–2.97)a 1.42(1.04–1.95)a
Monthlag4 Variablevalue 26 3 0.24
IRR 0.44(0.10–2.19) 26.70(1.82–397.00)a 0.83(0.09–7.18)
Variablevalue 35 200 0.72
IRR 8.16(3.41–20.26)a 1.99(1.22–2.27)a 1.57(1.09–2.25)a
PeakmonthisthemonthcorrespondingtothehighestIRRofmalaria
astatisticallysignificant
IRRIncidenceriskratio
NDVINormalizeddifferencevegetationindex
was consistent with previous studies which have demon- Rainfall provides avenues that facilitate mosquito breed-
strated how temporal disease risk shifts in response to ing suggesting that these areas retain water after rains
temperature changes and increase in maximum presenting suitable places for mosquito fertilization and
temperature increases the incidence rate of malaria sig- increasing the risk of malaria infections and transmis-
nificantly of thecurrent month andlater [35–37]. sion. Although not all mosquitoes need stagnant water,
The current study also found high values of rainfall to they require at least some form of water to hatch eggs
significantly increase the IRR of malaria at month lag 0 increasingthe risk inpreceding time points. The preced-
in these settings. Comparable to the specific rainfall ef- ing time points' malaria IRR is increased by the trans-
fect, the cumulative IRR of malaria was increased signifi- cended adult mosquitoes. This finding was consistent
cantly at month lag 1–4 at approximately 200mm. with earlier studies. For instance a study conducted in

--- Page 8 ---
Okiringetal.BMCPublicHealth (2021) 21:1962 Page8of11
Fig.1aContourplotsofthecombinedeffectoftimelagsand
Temperatureontheincidenceriskratioofmalaria.bEffectof
specificTemperatureandtimelagsontheincidenceriskratioof
malaria.Thebluelinesarethemeanrelativerisks,andthegraylines
are95%CI.cEffectsofspecificTemperatureandtimelagsonthe
cumulativeincidenceriskratioofmalaria.Theredlinesarethemean
incidenceriskratio,andthegrayareasare95%CI

Fig.2aContourplotsofthecombinedeffectoftimelagsand
rainfallamountsontheincidenceriskratioofmalaria.bEffectof
specificrainfallamountsandtimelagsontheincidenceriskratioof
malaria.Thebluelinesarethemeanincidenceriskratio,andthe
graylinesare95%CI.cEffectsofspecificrainfallamountsandtime
lagsonthecumulativeincidenceriskratioofmalaria.Theredlines
arethemeanincidenceriskratio,andthegrayareasare95%CI

--- Page 9 ---
Okiringetal.BMCPublicHealth (2021) 21:1962 Page9of11
Kenya showed positive associations between rainfall and the freedom needed to stock commodities required to
malaria burden at lags of 2 to 4months at rainfall ap- dealwith impending surgesorepidemics.
proximately 100–200mm in both lowland and highland This study has several limitations. First, as this study
[38]. was a population level study which involved environ-
Thisstudyalsofoundasignificantincreasedcumulative mental covariates and malaria, it is possible that some
IRRofmalariaatmonthlags2–4forhighvaluesofNDVI confounders may not have been considered which may
approximately 0.72 indicating dense vegetation. Vegeta- have influenced the results such as socio-economic and
tion around household residences may serve as refuge for community practices [44, 45]. Second, the data available
outdoor resting of mosquitoes [39]. Conversely, sparse was limited to a 24-month period, as data from previous
vegetation may limit the biting rates reducing the likeli- years wasonly health facility casesofmalaria rather than
hood of malaria transmission. Deforestation which is an incidence as catchment areas were not available. This
indicator of low vegetation cover has been shown to re- limited the ability to control for long-term trends. Such
duce malaria transmission significantly [40]. This study long-term trends in rainfall have been shown to influ-
was implemented in Amazon basin which is well known ence malaria burden [46]. Third, this study was unable
tobedrainedbytheAmazonRiveranditstributaries.The to encompass the entirety of environmental covariates,
possible explanation is that in the current month, defor- for instance because altitude did not vary over time, it
estationreducestheoutdoorrestingplacesformosquitoes was not considered as a covariate in this analysis. How-
driving the mosquitoes away reducing the risk of malaria ever, adding a health facility random variable in the
burden. Contrary with a study conducted in Kenya that model catered for the variability that was site-specific.
have demonstrated the associations betweenNDVIvalues Fourth, the study was conducted around health facilities
of 0.35 and malaria burden, the current study used 0.24 whose data is prone to missingness may have influenced
which are all in the same range of 0.2–0.5 and did the result. Health facilities with less than 5% missing
not realize any specific effect significant association at data on the village of residence for each month were in-
any month lags [41, 42]. The possible explanation cluded. Finally, the current study explored the associa-
could be the difference in the transmission intensities tions between environmental covariates with malaria
between the current study and the former study in incidenceinhightransmissionsettingsandtheidentified
Kenya. The current study only considered high month-lag time points may only be applicable and
transmission settings while the former study compared generalizable to these settings. Therefore, the data
lowlands and highlands. Ofnote highlands are prone should be interpreted with caution. For instance a study
to low mosquito population as the conditions are not conducted in China showed that minimum temperature
friendly resulting to low infection rates. had a longer lag ranges and larger correlation coeffi-
In the present study, despite the increasing cumulative cients for hot weather counties compared to cold wea-
IRR for high values of environmental covariates in ther counties. While maximum temperature was only
month lags 0–4, the rate of increase in the cumulative associatedwithmalariacasesat earlylags[47].
IRR was more in month lags 1–2 as compared to 3–4.
For instance the cumulative IRR more than doubled in Conclusion
month lags 1–3 as compared to month lags 3–4 at In the present study, high temperature increased the cu-
temperature approximately 35°C, more than doubled in mulative IRR of malaria significantly at month lags 1–4
month lags 0–2 as compared to 2–4 at rainfall approxi- compared to observed median of 30°C. High rainfall in-
mately 200mm, and more than doubled in month lags creased the IRR of malaria significantly at month lag 0
0–2 as compared to 2–4 at NDVI of approximately 0.72. and cummulative IRR at month lags 1–4 compared to
This may be well explained by the saturation effect, as the observed median of 133mm. High NDVI increased
when environmental conditions are sufficient for mos- the cumulative IRR significantly at month lags 2–4 com-
quito cycle completion, any additional value of the co- pared to the observed median of 0.66. The results high-
variates may have little impact on the development of light the relevance of incorporating the effects of
mosquito or parasite. This seems to suggest that inter- environmental covariates in predicting malaria when de-
ventions may be more effective if implemented in the veloping early warning systems. These identified com-
earliest time as much as possible in order to interrupt plex associations are useful for designing accurate
the mosquito cycle supporting the current World Health strategies for early warning, prevention, and control of
Organization recommendations on early accurate diag- seasonalmalaria epidemics.
nosis and treatment of malaria [43]. The current study
had practical implications as the advance warnings of Abbreviations
CI:ConfidenceIntervals;CHIRPS:ClimateHazardsGroupInfraRed
approaching situations advantageous to malaria epi-
PrecipitationwithStationdata;DLNM:Distributedlagnonlinearmodels;
demics will afford national malaria control programmes IRR:IncidenceRateRatio;MODIS:ModerateResolutionImaging

--- Page 10 ---
Okiringetal.BMCPublicHealth (2021) 21:1962 Page10of11
Spectroradiometer;MRCs:MalariaReferenceCentres;NMCD:NationalMalaria Availabilityofdataandmaterials
ControlDivision;NDVI:NormalizedDifferenceVegetationIndex;PY:Person Thedatasetsusedforthisstudyareavailablefromthecorrespondingauthor
Years;QAIC:QuasiAkaikeInformationCriterion;QGIS:QuatuamGeographical onreasonablerequest.
InformationSystem;REC:ResearchEthicsCommittee;UMSP:UgandaMalaria
SurveillanceProject;WHO:WorldHealthOrganization
Declarations
Supplementary Information Ethicsapprovalandconsenttoparticipate
Theonlineversioncontainssupplementarymaterialavailableathttps://doi. Ethicalapprovalforstudyprocedureswasprovidedbyethicscommitteeof
org/10.1186/s12889-021-11949-5. theSchoolofMedicineCollegeofHealthSciences,MakerereUniversity
(#RECP.EF2019–122),andUgandaNationalCouncilofScienceand
Technology(HS1033ES).Writteninformedconsentwasnotrequiredbythe
Additionalfile1:Fig.S1.MapofUgandashowingthestudydistricts ethicalreviewcommitteesduetotheroutine,de-identifiednatureofthe
andmalariareferencecentres. data.
Additionalfile2:Fig.S2.a.Estimatedincidenceriskratios(IRR)for
malariaasafunctionoftemperatureobtainedfromdistributedlag
Consentforpublication
models,over1000simulations.Estimatesfromthesamesimulationrun
Notapplicable.
areconnectedwithgraylines.TheredthicklinerepresentstheIRRs
observedintherealdataset.Resultsarepresentedfortemperatures26°C,
35°C,45°C,taking30°Casareference.Theresultswereobtainedwhen Competinginterests
simulatingdatawiththefollowingIRRs:Attemperature26°C:IRR=1at Theauthorsdeclarethattheyhavenocompetinginterests.
lags0and2,IRR=1.31atlag1,IRR=1.27atlag3,andIRR=1.24atlag4;
attemperature35°C:IRR=1.28forlags0,IRR=1.45forlags1,IRR=1.24 Authordetails
forlags2,IRR=1.70atlag3,IRR=1.24atlag4;attemperature45°C:IRR 1ClinicalEpidemiologyUnit,SchoolofMedicine,MakerereUniversityCollege
=1.29atlag0,IRR=1forlags1andlag4,IRR=1.07atlag2,IRR=1.48at ofHealthSciences,Kampala,Uganda.2InfectiousDiseasesResearch
lag3.b.EstimatedIRRformalariaasafunctionofrainfallobtainedfrom Collaboration,2CNakaseroHillRoad,Kampala,Uganda.3Departmentof
distributedlagmodels,over1000simulations.Estimatesfromthesame EpidemiologyandBiostatistics,UniversityofCalifornia,SanFrancisco,USA.
simulationrunareconnectedwithgraylines.Theredthickline 4NationalMalariaControlDivision,MinistryofHealth,Kampala,Uganda.
representstheRRsobservedintherealdataset.Resultsarepresentedfor 5SchoolofMedicine,MakerereUniversityCollegeofHealthSciences,
rainfall3mm,200mm,and247mm,taking133mmasareference.The Kampala,Uganda.6DepartmentofMedicine,UniversityofCalifornia,San
resultswereobtainedwhensimulatingdatawiththefollowingIRRs:At Francisco,USA.7DepartmentofStatistics,CollegeofScience,SultanQaboos
rainfall3mm:IRR=1atlags0,2and3,IRR=1.15atlag1,andIRR=1.60 University,Muscat,Oman.8DepartmentofChildHealthandDevelopment
atlag4;atrainfall200mm:IRR=1.12forlags0,IRR=1atlags1,3and4, Centre,SchoolofMedicine,MakerereUniversityCollegeofHealthSciences,
IRR=1.03atlag2;atrainfall247mm:IRR=1atlag0,IRR=2.13atlag1, Kampala,Uganda.
IRR=1.46atlag2,IRR=1.95atlag3,IRR=2.20atlag4.c.EstimatedIRR
formalariaasafunctionofNDVIobtainedfromdistributedlagmodels, Received:2May2021Accepted:8October2021
over1000simulations.Estimatesfromthesamesimulationrunare
connectedwithgraylines.TheredthicklinerepresentstheRRsobserved
intherealdataset.ResultsarepresentedforNDVIvaluesof0.24,0,50,0.72,
taking0.66asareference.Theresultswereobtainedwhensimulating
datawiththefollowingIRRs:AtNDVI0.24:IRR=1atlags0and1,IRR=
1.04atlag2,IRR=1.98atalg3,andIRR=1.37atlag4;atNDVI0.50:IRR=
1.13forlags0,IRR=1.01atlag1,IRR=1atlag2,IRR=1.22atlag3,and
IRR=1.34atlag4;atNDVI0.72:IRR=1.17atlag0,IRR=1atlag1and3,
IRR1.12atlag2,IRR=1.07atlag4.

Additionalfile3:Fig.S3.Temporalchangesinmonthlymalaria
incidenceoverthe24-monthobservationperiodaroundeachMRCand
all-sitescombined.

Acknowledgements
WewouldliketothanktheentireUMSPstudyteamandtheadministration
oftheInfectiousDiseasesResearchCollaborationforalltheircontributions.

Authors'contributions
Conceptualization:JO,GD,SMK,JIN;Fundingacquisition:MRK,GD;
Methodology:JO,IR,AE,JFN,VK,MRK,GD,RW,JIN;Investigation:JO,IR,MRK,
GD,SMK,JIN;Datacuration:JO,AE,VK,GD,JIN;Formalanalysis:JO,IR,GD,
RW,SMK,JIN,Writing–originaldraft:JO,GD,JIN;Writing–review&editing:
JO,IR,AE,JFN,VK,GAOOA,CMS,DM,JNK,MRK,GD,RW,SMK,JIN.Allauthors
readandapprovedthefinalmanuscript.

Funding
ResearchreportedinthispublicationwassupportedbytheNational
InstitutesofHealthaspartoftheInternationalCentersofExcellencein
MalariaResearch(ICMER)programme(U19AI089674)andtheFogarty
InternationalCenter(D43TW010526).JINissupportedbytheNational
Institutes,FogartyInternationalCenter(EmergingGlobalLeaderAwardgrant
numberK43TW010365).Thecontentissolelytheresponsibilityofthe
authorsanddoesnotnecessarilyrepresenttheofficialviewsoftheNational
InstitutesofHealth.

References
1. EndoN,EltahirEAB.Environmentaldeterminantsofmalariatransmission
aroundtheKokareservoirinEthiopia.GeoHealth.2018;2(3):104–15.https://
doi.org/10.1002/2017GH000108.
2. KibretS,LautzeJ,McCartneyM,NhamoL,YanG.Malariaaroundlarge
damsinAfrica:effectofenvironmentalandtransmissionendemicityfactors.
MalarJ.2019;18(1):303.https://doi.org/10.1186/s12936-019-2933-5.
3. AbiodunGJ,WitbooiPJ,OkosunKO,MaharajR.Exploringtheimpactof
climatevariabilityonmalariatransmissionusingadynamicmosquito-
humanmalariamodel.OpenInfectDisJ.2018;10(1):88–100.https://doi.
org/10.2174/1874279301810010088.
4. AbiodunGJ,MaharajR,WitbooiP,OkosunKO.Modellingtheinfluenceof
temperatureandrainfallonthepopulationdynamicsofAnopheles
arabiensis.MalarJ.2016;15(1):364.https://doi.org/10.1186/s12936-016-1411-
6.
5. CDC:Wheremalariaoccurs[Internet].Availablefrom:https://www.cdc.gov/
malaria/about/distribution.html
6. PaaijmansKP,BlanfordS,BellAS,BlanfordJI,ReadAF,ThomasMB.Influence
ofclimateonmalariatransmissiondependsondailytemperaturevariation.
ProcNatlAcadSci.2010;107(34):15135–9.https://doi.org/10.1073/pnas.1
006422107.
7. KigoziR,ZinszerK,MpimbazaA,SserwangaA,KigoziSP,KamyaM.
Assessingtemporalassociationsbetweenenvironmentalfactorsandmalaria
morbidityatvaryingtransmissionsettingsinUganda.MalarJ.2016;15(1):
511.https://doi.org/10.1186/s12936-016-1549-2.
8. MohammadkhaniM,KhanjaniN,BakhtiariB,TabatabaiSM,SheikhzadehK.
TherelationbetweenclimaticfactorsandmalariaincidenceinSistanand
Baluchestan,Iran.SAGEOpen.2019;9(3):215824401986420.https://doi.org/1
0.1177/2158244019864205.
9. FletcherIK,Stewart-IbarraAM,SippyR,Carrasco-EscobarG,SilvaM,Beltran-
AyalaE,etal.Therelativeroleofclimatevariationandcontrolinterventions
onmalariaeliminationeffortsinElOro,Ecuador:AModelingStudy.Front
EnvironSci.2020;8:135.https://doi.org/10.3389/fenvs.2020.00135.
10. OkunlolaOA,OyeyemiOT.Spatio-temporalanalysisofassociationbetween
incidenceofmalariaandenvironmentalpredictorsofmalariatransmission
inNigeria.SciRep.2019;9(1):17500.https://doi.org/10.1038/s41598-019-53814-x.
11. ChiromboJ,CeccatoP,LoweR,TerlouwDJ,ThomsonMC,GumboA,etal.
ChildhoodmalariacaseincidenceinMalawibetween2004and2017:
spatio-temporalmodellingofclimateandnon-climatefactors.MalarJ.2020;
19(1):5.https://doi.org/10.1186/s12936-019-3097-z.
12. MakindeOS,AbiodunGJ.Theimpactofrainfallandtemperatureonmalaria
dynamicsintheKwaZulu-Natalprovince,SouthAfrica.CommunStatCase
StudDataAnalAppl.2019;6:97–108.
13. BrhanieTW.TheroleoftemperatureformalariatransmissioninGongi
KolelaDistrict,Amhararegionalstate,NorthWestEthiopia.EpidemiolOpen
Access.2016;06.Availablefrom:https://www.omicsonline.org/open-access/
the-role-of-temperature-for-malaria-transmission-in-gongi-kolela-districtamha
ra-regional-state-north-west-ethiopia-2161-1165-1000281.php?aid=83884(06).
https://doi.org/10.4172/2161-1165.1000281.
14. AdeolaA,NcongwaneK,AbiodunG,MakgoaleT,RautenbachH,BotaiJ,
etal.RainfalltrendsandmalariaoccurrencesinLimpopoProvince,South
Africa.IntJEnvironResPublicHealth.2019;16(24):5156.https://doi.org/10.33
90/ijerph16245156.
15. SiyaA,KaluleBJ,SsentongoB,LukwaAT,EgeruA.Malariapatternsacross
altitudinalzonesofmountElgonfollowingintensifiedcontroland
preventionprogramsinUganda.BMCInfectDis.2020;20(1):425.https://doi.
org/10.1186/s12879-020-05158-5.
16. MoukamKakmeniFM,GuimapiRYA,NdjomatchouaFT,PedroSA,Mutunga
J,TonnangHEZ.SpatialpanoramaofmalariaprevalenceinAfricaunder
climatechangeandinterventionsscenarios.IntJHealthGeogr.2018;17(1):2.
https://doi.org/10.1186/s12942-018-0122-3.
17. RyanSJ,LippiCA,ZermoglioF.ShiftingtransmissionriskformalariainAfrica
withclimatechange:aframeworkforplanningandintervention.MalarJ.
2020;19(1):170.https://doi.org/10.1186/s12936-020-03224-6.
18. UgandaMinistryofHealth;NationalMalariaControlProgram.Available
from:https://www.health.go.ug/programs/national-malaria-control-program/
19. SserwangaA,HarrisJC,KigoziR,MenonM,BukirwaH,GasasiraA,etal.
Improvedmalariacasemanagementthroughtheimplementationofa
healthfacility-basedsentinelsitesurveillancesysteminUganda.PLoSOne.
2011;6(1):e16316.https://doi.org/10.1371/journal.pone.0016316.
20. OkiringJ,EpsteinA,NamugangaJF,KamyaV,SserwangaA,KapisiJ,etal.
Relationshipsbetweentestpositivityrate,totallaboratoryconfirmedcases
ofmalaria,andmalariaincidenceinhighburdensettingsofUganda:an
ecologicalanalysis.MalarJ.2021;20(1):42.https://doi.org/10.1186/s12936-
021-03584-7.
21. RhewIC,VanderStoepA,KearneyA,SmithNL,DunbarMD.Validationof
thenormalizeddifferencevegetationindexasameasureofneighborhood
greenness.AnnEpidemiol.2011;21(12):946–52.https://doi.org/10.1016/j.a
nnepidem.2011.09.001.
22. FunkC,PetersonP,LandsfeldM,PedrerosD,VerdinJ,ShuklaS,etal.The
climatehazardsinfraredprecipitationwithstations—anewenvironmental
recordformonitoringextremes.SciData.2015;2(1):150066.https://doi.org/1
0.1038/sdata.2015.66.
23. NationalAeronauticsandSpaceAdministration(NASA).Moderate
ResolutionImagingSpectroradiometer.Availablefrom:https://modis.gsfc.na
sa.gov/data/
24. Gapfillingalgorithm:Gapfillingrasterdata.Availablefrom: https://github.
com/disarm-platform/gapfilling_rasters.Accessed15Mar2021.
25. ThomsonMC,MasonSJ,PhindelaT,ConnorSJ.Useofrainfallandseasurface
temperaturemonitoringformalariaearlywarninginBotswana.AmJTrop
MedHyg.2005;73(1):214–21.https://doi.org/10.4269/ajtmh.2005.73.214.
26. TheAfriPopproject,startedinJune2009.Availablefrom:http://ghdx.hea
lthdata.org/series/afripop.Accessed10June2020.
27. GasparriniA,ArmstrongB,KenwardMG.Distributedlagnon-linearmodels.
StatMed.2010;29(21):2224–34.https://doi.org/10.1002/sim.3940.
28. SimpleO,MindraA,ObaiG,OvugaE,Odongo-AginyaEI.Influenceof
climaticfactorsonmalariaepidemicinGuluDistrict,northernUganda:a10-
yearretrospectivestudy.MalarResTreat.2018;2018:5482136–8.https://doi.
org/10.1155/2018/5482136.
29. Barrera-GomezJ,BasaganaX.UsingtheRpackagecollintovisualizethe
effectsofcollinearityindistributedlagmodels;2021.
30. MinistryofHealth.TheUgandaMalariaReductionStrategicPlan2014–2020,
MinistryofHealth,Kampala,Uganda.2014.
31. CastroMC.Malariatransmissionandprospectsformalariaeradication:the
roleoftheenvironment.ColdSpringHarbPerspectMed.2017;7(10).https://
doi.org/10.1101/cshperspect.a025601.
32. KimY,RatnamJV,DoiT,MoriokaY,BeheraS,TsuzukiA,etal.Malaria
predictionsbasedonseasonalclimateforecastsinSouthAfrica:atime
seriesdistributedlagnonlinearmodel.SciRep.2019;9(1):17882.https://doi.
org/10.1038/s41598-019-53838-3.
33. LePVV,KumarP,RuizMO,MbogoC,MuturiEJ.Predictingthedirectand
indirectimpactsofclimatechangeonmalariaincoastalKenya.PLOSONE.
2019;14:e0211258.
34. ShapiroLLM,WhiteheadSA,ThomasMB.Quantifyingtheeffectsof
temperatureonmosquitoandparasitetraitsthatdeterminethe
transmissionpotentialofhumanmalaria.PLOSBiol.2017;15:e2003489.
35. Beck-JohnsonLM,NelsonWA,PaaijmansKP,ReadAF,ThomasMB,
BjørnstadON.Theimportanceoftemperaturefluctuationsinunderstanding
mosquitopopulationdynamicsandmalariarisk.RSocOpenSci.2017;4(3):
160969.https://doi.org/10.1098/rsos.160969.
36. ChuangT-W,SobleA,NtshalintshaliN,MkhontaN,SeyamaE,MthethwaS,
etal.Assessmentofclimate-drivenvariationsinmalariaincidencein
Swaziland:towardmalariaelimination.MalarJ.2017;16(1):232.https://doi.
org/10.1186/s12936-017-1874-0.
37. MohammadkhaniM,KhanjaniN,BakhtiariB,SheikhzadehK.Therelation
betweenclimaticfactorsandmalariaincidenceinKerman,southeastof
Iran.ParasiteEpidemiolControl.2016;1(3):205–10.https://doi.org/10.1016/j.
parepi.2016.06.001.
38. Matsushita,Kim,Ng,Moriyama,Igarashi,Yamamoto,etal.Differencesof
Rainfall–MalariaAssociationsinLowlandandHighlandinWesternKenya.Int
JEnvironResPublicHealth.2019;16:3693.
39. RicottaEE,FreseSA,ChoobweC,LouisTA,ShiffCJ.Evaluatinglocal
vegetationcoverasariskfactorformalariatransmission:anewanalytical
approachusingImageJ.MalarJ.2014;13(1):94.https://doi.org/10.1186/14
75-2875-13-94.
40. MacDonaldAJ,MordecaiEA.Amazondeforestationdrivesmalaria
transmission,andmalariaburdenreducesforestclearing.ProcNatlAcadSci.
2019;116(44):22212–8.https://doi.org/10.1073/pnas.1905315116.
41. AmadiJA,OlagoDO,Ong'amoGO,OriasoSO,NanyingiM,NyamongoIK,
etal.Sensitivityofvegetationtoclimatevariabilityanditsimplicationsfor
malariariskinBaringo,Kenya.PLOSONE.2018;13:e0199357.
42. NationalCenterforAtmosphericResearchStaff.'TheClimateDataGuide:
NDVI:Normalized-difference-vegetation-index:NOAAAVHRR.'Retrieved
fromhttps://climatedataguide.ucar.edu/climate-data/ndvi-normalized-
difference-vegetation-index-noaa-avhrr.
43. WorldHealthOrganization.Guidelinesfortreatmentofmalaria.2nded;
2010.p.210.
44. ZinszerK,KigoziR,CharlandK,DorseyG,BrewerTF,BrownsteinJS,etal.
Forecastingmalariainahighlyendemiccountryusingenvironmentaland
clinicalpredictors.MalarJ.2015;14(1):245.https://doi.org/10.1186/s12936-01
5-0758-4.
45. SsempiiraJ,KissaJ,NambuusiB,MukooyoE,OpigoJ,MakumbiF,etal.
Interactionsbetweenclimaticchangesandinterventioneffectsonmalaria
spatio-temporaldynamicsinUganda.ParasiteEpidemiolControl.2018;3(3):
e00070.https://doi.org/10.1016/j.parepi.2018.e00070.
46. GebrechorkosSH,HülsmannS,BernhoferC.Long-termtrendsinrainfalland
temperatureusinghigh-resolutionclimatedatasetsinEastAfrica.SciRep.
2019;9(1):11376.https://doi.org/10.1038/s41598-019-47933-8.
47. ZhaoX,ChenF,FengZ,LiX,ZhouX-H.Thetemporallaggedassociation
betweenmeteorologicalfactorsandmalariain30countiesinsouth-West
China:amultileveldistributedlagnon-linearanalysis.MalarJ.2014;13(1):57.
https://doi.org/10.1186/1475-2875-13-57.
Publisher'sNote
SpringerNatureremainsneutralwithregardtojurisdictionalclaimsin
publishedmapsandinstitutionalaffiliations.
