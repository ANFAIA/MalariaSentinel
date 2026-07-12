# Spatial and spatio-temporal analysis of malaria cases in Zimbabwe

**Authors:** Isaiah Gwitira, Munashe Mukonoweshuro, Grace Mapako, Munyaradzi D. Shekede, Joconiah Chirenda, Joseph Mberikunashe
**Journal:** Infectious Diseases of Poverty | **Year:** 2020 | **DOI:** 10.1186/s40249-020-00764-6
**File:** papers/spatial-analysis/gwitira-et-al-2020-spatial-and-spatio-temporal-analysis-of-malaria-cases-in-zimbabwe.md

---

## Abstract

Malaria remains a serious public health problem in developing countries despite effective treatment availability. Understanding the spatial heterogeneity of malaria is critical for designing effective control strategies, particularly in resource-limited settings. This study explored the spatial and spatio-temporal pattern of malaria cases in Zimbabwe based on district-level aggregated data from 2011 to 2016, using GIS and spatial scan statistics. The study used passive malaria case data collected from health facilities (over 1,780 facilities across the country) and aggregated at district level (n=59 districts). Global Moran's I was used to detect spatial autocorrelation, while purely spatial and space-time retrospective analyses based on the discrete Poisson model were performed in SaTScan to identify clusters of high malaria rates.

Results showed significant positive spatial autocorrelation in malaria cases across all study years, confirming that malaria distribution follows a clustered rather than random pattern. The eastern region of Zimbabwe consistently contained primary clusters throughout the six-year study period, with the number of districts in primary clusters increasing from 4 in 2011 to 12 in 2016. The lowest number of cases within a cluster was 5,414 (2011) while the highest was 92,324 (2012). Space-time analysis detected four significant spatio-temporal clusters, with one primary cluster in the north-eastern region covering eight districts from December 2012 to May 2014, persisting for three transmission seasons. The temporal pattern of malaria reflected disease seasonality, with clusters detected within particular months (peak February–April). Cluster frequency analysis showed that northern, north-eastern, eastern, and south-eastern districts had the highest frequency of malaria clusters, while central, western, and south-western districts had none.

## Methods

- Global Moran's I test for spatial autocorrelation using Queen Contiguity weight matrix
- Purely spatial scan statistic (SaTScan v9.6) based on discrete Poisson model for high-rate cluster detection
- Retrospective space-time analysis with cylindrical scanning windows (circular geographic base, height = time interval of 1 month)
- Cluster frequency analysis via GIS overlay: counting how many times each district was detected as part of a cluster
- 999 Monte Carlo replications for significance testing (P < 0.05)
- Data sources: passive case data from DHIS2, population data from Zimbabwe National Statistical Agency (2012 census with intercensal projections)
- Maximum spatial cluster size: 50% of population at risk

## Key Results

- 1,877,794 malaria cases recorded across Zimbabwe (2011–2016)
- Significant positive global spatial autocorrelation (Moran's I) across all study years
- Primary clusters consistently concentrated in eastern region: 4 districts (2011) → 12 districts (2016)
- Cluster size range: 5,414 cases (2011) to 92,324 cases (2012)
- Four significant spatio-temporal clusters detected
- Primary space-time cluster: north-eastern region, 8 districts, Dec 2012–May 2014 (3 seasons)
- Highest incidence: peak February, lowest: July–August (dry/cold months)
- Northern, north-eastern, eastern, south-eastern districts = highest cluster frequency
- Central, western, south-western districts = no clusters detected

## Relevance to MalariaSentinel (Centinela)

This study demonstrates the operational application of spatial scan statistics (SaTScan) for malaria cluster detection at district level using routine health facility data — directly relevant to the Centinela's planned surveillance-response module. The finding that high-risk clusters concentrate in specific ecological zones (eastern Zimbabwe highlands) supports the Centinela's approach to stratified risk targeting. The use of DHIS2 data as input mirrors the Centinela's planned data pipeline. The study's limitations around data quality in routine HIS systems are directly relevant to the Centinela's data quality assessment framework.

---

## Full Text

### --- Page 1 ---
Gwitira et al. Infect Dis Poverty (2020) 9:146
https://doi.org/10.1186/s40249-020-00764-6
RESEARCH ARTICLE Open Access
Spatial and spatio-temporal analysis
of malaria cases in Zimbabwe
Isaiah Gwitira1* , Munashe Mukonoweshuro1, Grace Mapako1, Munyaradzi D. Shekede1, Joconiah Chirenda2
and Joseph Mberikunashe3
Abstract
Background: Although effective treatment for malaria is now available, approximately half of the global population
remain at risk of the disease particularly in developing countries. To design effective malaria control strategies there is
need to understand the pattern of malaria heterogeneity in an area. Therefore, the main objective of this study was to
explore the spatial and spatio-temporal pattern of malaria cases in Zimbabwe based on malaria data aggregated at
district level from 2011 to 2016.
Methods: Geographical information system (GIS) and spatial scan statistic were applied on passive malaria data col-
lected from health facilities and aggregated at district level to detect existence of spatial clusters. The global Moran's
I test was used to infer the presence of spatial autocorrelation while the purely spatial retrospective analyses were
performed to detect the spatial clusters of malaria cases with high rates based on the discrete Poisson model. Further-
more, space-time clusters with high rates were detected through the retrospective space-time analysis based on the
discrete Poisson model.
Results: Results showed that there is significant positive spatial autocorrelation in malaria cases in the study area.
In addition, malaria exhibits spatial heterogeneity as evidenced by the existence of statistically significant (P < 0.05)
spatial and space-time clusters of malaria in specific geographic regions. The detected primary clusters persisted in
the eastern region of the study area over the six year study period while the temporal pattern of malaria reflected the
seasonality of the disease where clusters were detected within particular months of the year.
Conclusions: Geographic regions characterised by clusters of high rates were identified as malaria high risk areas.
The results of this study could be useful in prioritizing resource allocation in high-risk areas for malaria control and
elimination particularly in resource limited settings such as Zimbabwe. The results of this study are also useful to
guide further investigation into the possible determinants of persistence of high clusters of malaria cases in particular
geographic regions which is useful in reducing malaria burden in such areas.
Keywords: Malaria, GIS, SaTscan, Spatial pattern, Spatial heterogeneity, Cluster analysis, Zimbabwe
Background
Compared with other human diseases, malaria remains
one of the most serious public health problem associ-
ated with high morbidity and mortality in most develop-
ing countries [1–3]. In 2018 alone, 228 million malaria
*Correspondence: gwitsakuely@gmail.com; gwitirai@gis.uz.ac.zw cases and 405 000 deaths were recorded worldwide with
1 Department of Geography Geospatial Sciences and Earth Observation, the World Health Organisation (WHO) African Region
University of Zimbabwe, P. O. Box MP 167, Mount Pleasant, Harare,
contributing 93% of the cases and 94% of the deaths [4].
Zimbabwe
Full list of author information is available at the end of the article Although malaria has been successfully eradicated in
© The Author(s) 2020. Open Access This article is licensed under a Creative Commons Attribution 4.0 International License, which
permits use, sharing, adaptation, distribution and reproduction in any medium or format, as long as you give appropriate credit to the
original author(s) and the source, provide a link to the Creative Commons licence, and indicate if changes were made. The images or
other third party material in this article are included in the article's Creative Commons licence, unless indicated otherwise in a credit line
to the material. If material is not included in the article's Creative Commons licence and your intended use is not permitted by statutory
regulation or exceeds the permitted use, you will need to obtain permission directly from the copyright holder. To view a copy of this
licence, visit http://creati vecom mons .org/licens es/by/4.0/. The Creative Commons Public Domain Dedication waiver (http://creati veco
mmons .org/public domai n/zero/1.0/) applies to the data made available in this article, unless otherwise stated in a credit line to the data.
45
page number not for citation purpose
Downloaded from mednexus.org on [June 20, 2026]. For personal use only.

### --- Page 2 ---
Gwitira et al. Infect Dis Poverty (2020) 9:146 Page 2 of 14
high income and most middle income countries, the dis- undirected control [23]. Such targeted interventions choice of a cluster detection technique can be guided by longitudes 25° 00″ and 33° 10″ E (Fig. 1). The altitude of
ease remains a major health problem and is a top killer ultimately reduce malaria mortality and morbidity [24]. its sensitivity and specificity in addition to the power to the study area ranges from 300 to 2590 m above mean sea
infectious disease in low income countries [5]. In most Focussing malaria control in high risk areas is recom- detect clusters [39, 40]. In this study, SaTscan was applied level. Mean annual rainfall ranges from below 400 mm in
parts of Zimbabwe, Plasmodium falciparum is the most mended by WHO in both elimination and post elimina- since results from previous studies indicated that it has the southern and north-western parts to over 1000 mm
common and efficient malaria parasite that accounted tion settings [25]. the highest overall sensitivity compared to other meth- in the eastern and central parts of the country. The coun-
for 99.7% of the estimated cases in 2018 [4] while P. ovale Although previous studies assessed the spatial and ods such as Local Indicators of Spatial Autocorrelation try records its lowest minimum temperatures in June or
and P. malariae account for the remainder. The primary temporal variation in malaria occurrence, most of these (LISA) and Getis [39] hence its ability to detect true clus- July while the maximum temperatures occur in October.
vector mosquito species responsible for most malaria studies lacked the appropriate spatial scale that enables ters. Moreso, the technique maintains reasonably high Mean monthly temperatures vary from 15 °C in July to
transmission in Zimbabwe are Anopheles arabiensis and optimal planning at the national level [26–29]. In addi- power for detecting clusters compared to methods such 24 °C in November, while the mean annual temperature
Anopheles funestus sensu stricto [6, 7]. tion, most of the studies were either based on longitu- as LISA which are influenced by neighbours [41]. Tech- varies from 18 °C in the high-altitude areas to 23 °C in
In the past few years, malaria incidence and mortal- dinal cohort studies or limited in temporal duration [2, niques such as Getis-Ord G* statistic suffer from multi- the low altitude areas. The study area is characterised
i
ity have declined significantly across the globe [8, 9]. For 30]. For example, some studies observed clustering of ple testing which is inherently accounted for in SaTscan by a subtropical climate with three recognisable sea-
instance, mortality rate decreased by 62% while malaria malaria cases at micro-geographic scale such as ward [42]. In this way, SaTscan combines exploratory and con- sons which are the hot wet season or summer stretch-
incidence decreased by 41% between 2000 and 2015 [10, level in Gwanda district of Zimbabwe [31]. Similarly, it firmatory capabilities which enable explicit statistical ing from mid-November to March; the cold dry season
11]. The decline in malaria incidence and mortality is was also established that malaria exhibited spatio-tem- assessment of spatial pattern across the landscape [39]. or winter stretching from April to July; and the hot dry
mainly attributed to malaria control interventions such poral clusters at village level in China [29]. In addition, In this study, the main objective was to test whether season or spring from August to mid-November [43].
as indoor residual spraying (IRS) and use of insecticide high malaria risk areas were identified in Hubei Province there is statistically significant spatial and space-time Zimbabwe experiences seasonal and spatial variation in
treated nets [10, 12]. Zimbabwe experienced a substan- of China based on scan statistics [32]. In another study, it clustering of malaria at district level in Zimbabwe. The malaria transmission that is related to the country's cli-
tial decline in malaria cases of up to 81% from 2003 to was found that malaria case distribution is characterised main hypothesis was that malaria tends to occur in clus- mate especially rainfall pattern [13, 44]. The malaria peak
2015 across all age groups [13]. As a result of the sub- by spatial, temporal and spatiotemporal heterogeneity in ters and that these clusters have both spatial and tempo- transmission season in Zimbabwe is between February
stantial decline in malaria cases in Zimbabwe, the coun- unstable transmission areas in North-west Ethiopia [30]. ral characteristics. and April [13]. According WHO, there were close to 14
try adopted the global and regional agenda for malaria Although these studies provide useful insights in under- million people in the country, and four million were at
Methods
elimination by 2030 [14]. The target for the country is to standing the spatial and temporal pattern of malaria, risk of malaria with close to 1 million confirmed cases in
reduce malaria incidence to 5/1000 by end of 2020 [15]. knowledge on the spatial and temporal pattern of malaria Study area 2018. The country is landlocked and shares the border
As malaria transmission continue to decline, prevention at a level where malaria interventions are commonly The study was carried out in Zimbabwe located in south- with Mozambique, Botswana, Zambia and South Africa
and control interventions will increasingly rely on accu- planned remain patchy. This is despite the fact that spa- ern Africa between latitudes 15° 30″ and 22° 30″ S and (Fig. 1).
rate knowledge of the spatial distribution of high-risk tial analysis becomes much more meaningful when the
geographic areas to support malaria elimination. This spatial unit at which analysis is performed is representa-
could be useful in optimal allocation of limited resources tive of the expected epidemiological dynamics [21]. This
to ensure that areas with the highest malaria burden are will then mean the resulting national-level maps from
given priority [16, 17]. Despite the declining burden of such analysis will be justifiably utilized to prioritize high
malaria, there still exist periodic outbreaks of malaria risk areas [21].
which exhibit spatial heterogeneity across different Despite the fact that effective malaria intervention war-
regions through time and space. Mapping malaria spatial rants understanding of malaria heterogeneity at larger
heterogeneity is important to better understand trans- spatial scales for the purposes of resource allocation
mission dynamics [18, 19]. before focussing on microgeographic regions, studies
The spatial heterogeneity in malaria transmission has at this scale remain largely limited. To fill this gap, this
resulted in malaria occurring in transmission clusters study utilised relatively long term malaria case data at
[19, 20]. The spatial heterogeneity in malaria is largely district level, that is, the spatial epidemiological admin-
attributed to variation in environmental risk factors istrative unit at which malaria interventions and control
at the macro (e.g., temperature, precipitation) and the are planned to determine not only persistent and stable
micro (e.g., local elevation, land use) spatial scales [21]. clusters but emerging clusters as well [33]. The determi-
In this case, a malaria cluster is an area characterised by nation of spatial pattern of malaria at district level is also
unusually high number of cases than expected within a important in understanding possible interactions among
population at a particular place at a given time [22]. As neighbouring districts which is fundamental during
malaria occurrence exhibit spatial heterogeneity, strate- malaria elimination.
gies aimed at reducing or controlling the disease hinge To determine the spatial pattern of malaria cluster-
upon objective and accurate characterisation of its clus- ing, it is important to adopt or even develop methods
ters as a first step towards identifying areas with elevated that can reliably and accurately detect malaria clusters
malaria risk for prioritisation of interventions [18, 19]. in space and time. To date, several methods have been
Evidence from previous studies suggest that targeting used to detect spatial and space-time clusters and these
malaria control interventions at high risk areas is cost include, ClusterSeer [34], GeoSurveillance [35], ker-
Fig. 1 Location of the study area
effective and is bound to increase equity compared with nel density [36], SaTScan [37] and Flex Scan [38]. The
46
page number not for citation purpose
Downloaded from mednexus.org on [June 20, 2026]. For personal use only.

### --- Page 3 ---
[Page 3 data sources section, continuing Methods with data sources, population data, statistical analysis methods including Moran's I formula, SaTScan cluster detection with discrete Poisson model, space-time Poisson model, cluster frequency analysis. See pages 4-8 for complete methods and results with Tables 1-3 and Figures 2-6 documenting annual incidence maps, monthly incidence patterns, spatial clusters by year, cluster frequencies, and space-time clusters.]

[Full OCR text continues. Refer to original PDF at papers/spatial-analysis/gwitira-et-al-2020-spatial-and-spatio-temporal-analysis-of-malaria-cases-in-zimbabwe.pdf for complete text.]
