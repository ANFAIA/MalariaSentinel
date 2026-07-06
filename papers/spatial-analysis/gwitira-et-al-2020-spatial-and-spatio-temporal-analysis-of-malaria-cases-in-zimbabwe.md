# gwitira-et-al-2020-spatial-and-spatio-temporal-analysis-of-malaria-cases-in-zimbabwe

**Source PDF:** `gwitira-et-al-2020-spatial-and-spatio-temporal-analysis-of-malaria-cases-in-zimbabwe.pdf`  
**Path:** `papers/spatial-analysis/gwitira-et-al-2020-spatial-and-spatio-temporal-analysis-of-malaria-cases-in-zimbabwe.pdf`  

---

--- Page 1 ---
Guoetal.InfectiousDiseasesofPoverty (2020) 9:136 Page10of10 Gwitira et al. Infect Dis Poverty (2020) 9:146
https://doi.org/10.1186/s40249-020-00764-6
37. ZhouXN.Implementationofprecisioncontroltoachievethegoalof RESEARCH ARTICLE Open Access
schistosomiasiseliminationinChina.ChinJSchistoControl.2016;28(1):1–4
(inChinese).
38. McManusDP,DunneDW,SackoM,UtzingerJ,VennervaldBJ,ZhouXN.
Spatial and spatio-temporal analysis
Schistosomiasis.NatRevDisPrimers.2018;4(1):13.
39. AbeEM,TamboE,XueJ,XuJ,EkpoUF,RollinsonD,etal.Approachesin
scalingupschistosomiasisinterventiontowardstransmissioneliminationin of malaria cases in Zimbabwe
Africa:leveragingfromtheChineseexperienceandlessons.ActaTrop.2020;
208:105379.
Isaiah Gwitira1* , Munashe Mukonoweshuro1, Grace Mapako1, Munyaradzi D. Shekede1, Joconiah Chirenda2
and Joseph Mberikunashe3
Abstract
Background: Although effective treatment for malaria is now available, approximately half of the global population
remain at risk of the disease particularly in developing countries. To design effective malaria control strategies there is
need to understand the pattern of malaria heterogeneity in an area. Therefore, the main objective of this study was to
explore the spatial and spatio-temporal pattern of malaria cases in Zimbabwe based on malaria data aggregated at
district level from 2011 to 2016.
Methods: Geographical information system (GIS) and spatial scan statistic were applied on passive malaria data col-
lected from health facilities and aggregated at district level to detect existence of spatial clusters. The global Moran’s
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
other third party material in this article are included in the article’s Creative Commons licence, unless indicated otherwise in a credit line
to the material. If material is not included in the article’s Creative Commons licence and your intended use is not permitted by statutory
regulation or exceeds the permitted use, you will need to obtain permission directly from the copyright holder. To view a copy of this
licence, visit http://creati vecom mons .org/licens es/by/4.0/. The Creative Commons Public Domain Dedication waiver (http://creati veco
mmons .org/public domai n/zero/1.0/) applies to the data made available in this article, unless otherwise stated in a credit line to the data.
45
page number not for citation purpose
Downloaded from mednexus.org on [June 20, 2026]. For personal use only.

--- Page 2 ---
Gwitira et al. Infect Dis Poverty (2020) 9:146 Page 2 of 14 Gwitira et al. Infect Dis Poverty (2020) 9:146 Page 3 of 14
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
treated nets [10, 12]. Zimbabwe experienced a substan- of China based on scan statistics [32]. In another study, it clustering of malaria at district level in Zimbabwe. The malaria transmission that is related to the country’s cli-
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

--- Page 3 ---
Gwitira et al. Infect Dis Poverty (2020) 9:146 Page 2 of 14 G witira et al. Infect Dis Poverty (2020) 9:146 Page 3 of 14
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
treated nets [10, 12]. Zimbabwe experienced a substan- of China based on scan statistics [32]. In another study, it clustering of malaria at district level in Zimbabwe. The malaria transmission that is related to the country’s cli-
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
47
page number not for citation purpose
Downloaded from mednexus.org on [June 20, 2026]. For personal use only.

--- Page 4 ---
Gwitira et al. Infect Dis Poverty (2020) 9:146 Page 4 of 14 Gwitira et al. Infect Dis Poverty (2020) 9:146 Page 5 of 14
Data sources 2012 data was based on the 2012 National Census. The each district (n 59) from 2011 to 2016; a coordinate Cluster frequency analysis
=
Malaria case data population for intercensal years for example 2013 to 2015 file representing geographic coordinates of the centroid To understand the persistence or emergence of poten-
The positive malaria cases recorded from 2011 to 2016 were determined using the projected annual growth rate of each district; and a population file representing the tial malaria hotspots cluster frequency analysis was
were obtained from geocoded health facilities in Zimba- of 1.2% based on the 2012 national census [53]. The pop- projected total population for each year from 2011 to performed in a GIS environment. Specifically, the clus-
bwe and aggregated by month and year at district level. ulation of intercensal years is based on projected growth 2016 for the respective district. ter frequency analysis was performed through counting
The country has over 1780 health facilities strategi- rates because the country conducts a population census The program identified statistically significant retro- the number of times a district was detected as part of
cally placed within a 10-km radius in villages and urban after every 10 years. spective clusters based on annual malaria cases aggre- a cluster using overlay analysis. This procedure yielded
areas [13]. The health facilities are ranked into central, gated per district in Zimbabwe from 2011 to 2016. the number of times a district coincided with detected
provincial, and district hospitals, as well as clinics/rural Statistical data analysis SaTscan tests whether the number of malaria cases clusters whether primary or secondary.
health centres (RHCs). Data on malaria incidence at dis- Testing for spatial autocorrelation within any spatial window exceeds the number expected
trict level from 2011 to 2016 were collected based on Moran’s I [54], a global autocorrelation statistic was used by a random process [57]. To achieve this, the centroid of Results
the annual submission from health centres to DHIS 2. to detect spatial pattern of malaria in the country. Using each district was first determined and extracted in a GIS Variation in monthly malaria incidence
The data includes province, district, and centre name, this technique, significant positive spatial autocorrelation environment. The spatial join function in a GIS was then Figure 2 illustrates the variation in average monthly
date of diagnosis, age and gender. The data is for cases of malaria cases imply that the distribution of malaria used to link the annual malaria cases for each year to the malaria incidence from 2011 to 2016 in Zimbabwe.
based on diagnostics using either rapid diagnostic tests cases is more spatially aggregated than a random under- centroid of the districts. From 2011 to 2016, a total of 1 877 794 malaria cases
(RDTs) or microscopy reported in each year [13]. Zim- lying spatial process. Next, the annual malaria cases per district were con- were recorded throughout the country. It can be
babwe, like most developing countries in sub-Saharan The Moran’s Index takes the form; verted to SaTscan format for use in the detection and observed that malaria incidence start to increase from
Africa, adopted the District Health Information System analysis of clusters. For determining clusters, a cylin- December and reach the highest peak in February. In
(DHIS2) in 2010 to harmonise health data management I = n (cid:31)n i=1 (cid:31)n j=1 w i,j z i z j drical window with a circular geographic base centred contrast, the lowest incidence is recorded during the
[45]. The malaria cases at district level were plotted using S o (cid:31)n i=1 z i 2 (1) on each district centroid and with height correspond- dry months such as August and cold month such as
ArcGIS 10.3 (ArcGIS Desktop: Release 10. Redlands, CA, ing to time was applied [57]. The default value of 50% of July.
USA) [46] by month and year to assess the distribution of where Zi is the deviation of an attribute for feature i from the population at risk was adopted as recommended in
¯
malaria cases in the country. its mean (x – X ), w is the spatial weight between feature literature [37, 58, 59]. Thus, clusters with statistical sig- Annual incidence of malaria
i i,j
For the Ministry of Health and Child Care, two main i and j, n is equal to the total number of features and S o is nificance of P < 0.05 were classified as significant clus- An analysis of annual malaria cases shows that over the
sources are used to feed the national surveillance system the aggregate of all spatial weights. ters. As previously mentioned, the space-time clusters 6 years, the northern, north-eastern, eastern and south-
with routine malaria data i.e., the Health Management Moran’s index ranges from − 1 to + 1 with a score of of malaria with high rates were detected using the retro- eastern districts of the country were characterised by
Information System (HMIS) and the Rapid Disease Noti- zero indicating the null hypothesis of no clustering. A spective space-time analysis based on the discrete Pois- high malaria incidence (Fig. 3). In contrast, the west-
fication System (RDNS) [47]. The RDNS, weekly short positive score indicates clustering of malaria cases while son model. To do this, data was arranged at a monthly ern, central and south western regions had low malaria
message service (SMS) is used to report malaria cases for a negative value shows that neighbouring areas are char- scale from 2011 to 2016 and hence the time aggregation incidence during the same period. In fact, more dis-
approximately 95% of the health facilities. In addition, the acterised by dissimilar malaria cases [55]. To perform length was set to one month in SaTscan software. The tricts in the eastern districts of the country experienced
HMIS obtains its data from monthly aggregated malaria spatial autocorrelation, the Queen Contiguity method space-time scan statistic was defined by a cylindrical win- high malaria incidence in any other year compared with
cases and deaths from all health facilities [47]. In most was applied to define a weight matrix specifying the spa- dow with a circular geographic base and whose height other districts where malaria occurs.
developing countries in sub-Saharan Africa including tial relationships among the districts of Zimbabwe. This corresponded to a time interval i.e., a month in this case.
Zimbabwe, routine health information systems are weak method was adopted since malaria is not directionally The space-time analysis was applied to detect the sea- Spatial autocorrelation of malaria cases
and there are widespread concerns about the quality and restricted and the districts are highly irregular in shape sonal pattern in malaria in the country. This technique is
Spatial autocorrelation results based on the annual
utility of malaria data generated from these systems [48, and size [56]. The significance of Moran’s I was assessed more robust as it combines exploratory and confirmatory
malaria cases showed that there was significant over-
49]. Despite concerns about data quality, Zimbabwe has by employing Monte Carlo randomization where a sta- capabilities which enable explicit statistical assessment
all spatial autocorrelation in Zimbabwe across all the
made great strides on this aspect through government tistically significant (Z score > 1.96) indicated that neigh- of spatial patterns across the landscape [39] compared to
study years (Table 1). The results demonstrate that
initiatives and international support. To improve data bouring districts have similar malaria cases at county Getis-Ord G*.To detect significant space-time clusters,
i malaria cases highly cluster at country level for all the
quality, the government adopted the Global Technical level. 999 Monte Carlo replications were performed under the
years under study.
Strategy for Malaria 2016–2030 which stresses the need null hypothesis of random distribution of malaria cases
for adequate investment in the management and use of Detecting malaria clusters using SaTScan [32]. In this case, statistical significance was tested using Spatial clusters of malaria from 2011 to 2016
data from routine health information systems to support a Poisson generalized log likelihood ratio test based on
In this study, scan statistics [42] was applied in SaTScan The results for the statistically significant (P < 0.05)
programme planning, implementation and evaluation Monte-Carlo inference [32, 60].
v9.6 (https ://www.satsc an.org/) software to detect high primary and secondary spatial clusters as well as the
[50]. The relative risk was calculated by comparing the
cluster rate of malaria. In this case, spatial scan statis- corresponding relative risk for high rates of malaria
observed number of cases of malaria within each window
tic, based on the discrete Poisson model, was applied occurrence identified by purely spatial scan statistic
to the expected number, using a Poisson model. The most
to identify purely spatial clusters of malaria cases by based on the discrete Poisson model are illustrated in
Population data likely cluster (hereinafter, primary cluster) was identi-
year. On the other hand, the space-time scan statis- Fig. 4. The results illustrate that there was significant
Population data used in this study were obtained from the fied based on the maximum log likelihood ratio [61]. In
tic, based on Space-Time Poisson model was adopted spatial clustering of malaria cases in specific districts
Zimbabwe National Statistical Agency (ZimStat) based addition, other clusters with statistically significant log
to determine the presence of space-time clusters of from the years 2011 to 2016 (Fig. 4, Table 2). Over the
on the 2012 National population census [51]. The 2010 likelihood values were defined as secondary clusters. The
malaria cases by month over the study period. Three six years, primary clusters of malaria were concen-
and 2011 population data was based on a 1.1% projected criterion of no geographical overlap was used to report
datasets were prepared for use in SaTScan and these trated in the eastern region of the country. The number
growth rate from the 2002 National census [52] while the secondary clusters.
were: a case file representing annual malaria cases per
48
page number not for citation purpose
Downloaded from mednexus.org on [June 20, 2026]. For personal use only.

--- Page 5 ---
Gwitira et al. Infect Dis Poverty (2020) 9:146 Page 4 of 14 G witira et al. Infect Dis Poverty (2020) 9:146 Page 5 of 14
Data sources 2012 data was based on the 2012 National Census. The each district (n 59) from 2011 to 2016; a coordinate Cluster frequency analysis
=
Malaria case data population for intercensal years for example 2013 to 2015 file representing geographic coordinates of the centroid To understand the persistence or emergence of poten-
The positive malaria cases recorded from 2011 to 2016 were determined using the projected annual growth rate of each district; and a population file representing the tial malaria hotspots cluster frequency analysis was
were obtained from geocoded health facilities in Zimba- of 1.2% based on the 2012 national census [53]. The pop- projected total population for each year from 2011 to performed in a GIS environment. Specifically, the clus-
bwe and aggregated by month and year at district level. ulation of intercensal years is based on projected growth 2016 for the respective district. ter frequency analysis was performed through counting
The country has over 1780 health facilities strategi- rates because the country conducts a population census The program identified statistically significant retro- the number of times a district was detected as part of
cally placed within a 10-km radius in villages and urban after every 10 years. spective clusters based on annual malaria cases aggre- a cluster using overlay analysis. This procedure yielded
areas [13]. The health facilities are ranked into central, gated per district in Zimbabwe from 2011 to 2016. the number of times a district coincided with detected
provincial, and district hospitals, as well as clinics/rural Statistical data analysis SaTscan tests whether the number of malaria cases clusters whether primary or secondary.
health centres (RHCs). Data on malaria incidence at dis- Testing for spatial autocorrelation within any spatial window exceeds the number expected
trict level from 2011 to 2016 were collected based on Moran’s I [54], a global autocorrelation statistic was used by a random process [57]. To achieve this, the centroid of Results
the annual submission from health centres to DHIS 2. to detect spatial pattern of malaria in the country. Using each district was first determined and extracted in a GIS Variation in monthly malaria incidence
The data includes province, district, and centre name, this technique, significant positive spatial autocorrelation environment. The spatial join function in a GIS was then Figure 2 illustrates the variation in average monthly
date of diagnosis, age and gender. The data is for cases of malaria cases imply that the distribution of malaria used to link the annual malaria cases for each year to the malaria incidence from 2011 to 2016 in Zimbabwe.
based on diagnostics using either rapid diagnostic tests cases is more spatially aggregated than a random under- centroid of the districts. From 2011 to 2016, a total of 1 877 794 malaria cases
(RDTs) or microscopy reported in each year [13]. Zim- lying spatial process. Next, the annual malaria cases per district were con- were recorded throughout the country. It can be
babwe, like most developing countries in sub-Saharan The Moran’s Index takes the form; verted to SaTscan format for use in the detection and observed that malaria incidence start to increase from
Africa, adopted the District Health Information System analysis of clusters. For determining clusters, a cylin- December and reach the highest peak in February. In
(DHIS2) in 2010 to harmonise health data management I = n (cid:31)n i=1 (cid:31)n j=1 w i,j z i z j drical window with a circular geographic base centred contrast, the lowest incidence is recorded during the
[45]. The malaria cases at district level were plotted using S o (cid:31)n i=1 z i 2 (1) on each district centroid and with height correspond- dry months such as August and cold month such as
ArcGIS 10.3 (ArcGIS Desktop: Release 10. Redlands, CA, ing to time was applied [57]. The default value of 50% of July.
USA) [46] by month and year to assess the distribution of where Zi is the deviation of an attribute for feature i from the population at risk was adopted as recommended in
¯
malaria cases in the country. its mean (x – X ), w is the spatial weight between feature literature [37, 58, 59]. Thus, clusters with statistical sig- Annual incidence of malaria
i i,j
For the Ministry of Health and Child Care, two main i and j, n is equal to the total number of features and S o is nificance of P < 0.05 were classified as significant clus- An analysis of annual malaria cases shows that over the
sources are used to feed the national surveillance system the aggregate of all spatial weights. ters. As previously mentioned, the space-time clusters 6 years, the northern, north-eastern, eastern and south-
with routine malaria data i.e., the Health Management Moran’s index ranges from − 1 to + 1 with a score of of malaria with high rates were detected using the retro- eastern districts of the country were characterised by
Information System (HMIS) and the Rapid Disease Noti- zero indicating the null hypothesis of no clustering. A spective space-time analysis based on the discrete Pois- high malaria incidence (Fig. 3). In contrast, the west-
fication System (RDNS) [47]. The RDNS, weekly short positive score indicates clustering of malaria cases while son model. To do this, data was arranged at a monthly ern, central and south western regions had low malaria
message service (SMS) is used to report malaria cases for a negative value shows that neighbouring areas are char- scale from 2011 to 2016 and hence the time aggregation incidence during the same period. In fact, more dis-
approximately 95% of the health facilities. In addition, the acterised by dissimilar malaria cases [55]. To perform length was set to one month in SaTscan software. The tricts in the eastern districts of the country experienced
HMIS obtains its data from monthly aggregated malaria spatial autocorrelation, the Queen Contiguity method space-time scan statistic was defined by a cylindrical win- high malaria incidence in any other year compared with
cases and deaths from all health facilities [47]. In most was applied to define a weight matrix specifying the spa- dow with a circular geographic base and whose height other districts where malaria occurs.
developing countries in sub-Saharan Africa including tial relationships among the districts of Zimbabwe. This corresponded to a time interval i.e., a month in this case.
Zimbabwe, routine health information systems are weak method was adopted since malaria is not directionally The space-time analysis was applied to detect the sea- Spatial autocorrelation of malaria cases
and there are widespread concerns about the quality and restricted and the districts are highly irregular in shape sonal pattern in malaria in the country. This technique is
Spatial autocorrelation results based on the annual
utility of malaria data generated from these systems [48, and size [56]. The significance of Moran’s I was assessed more robust as it combines exploratory and confirmatory
malaria cases showed that there was significant over-
49]. Despite concerns about data quality, Zimbabwe has by employing Monte Carlo randomization where a sta- capabilities which enable explicit statistical assessment
all spatial autocorrelation in Zimbabwe across all the
made great strides on this aspect through government tistically significant (Z score > 1.96) indicated that neigh- of spatial patterns across the landscape [39] compared to
study years (Table 1). The results demonstrate that
initiatives and international support. To improve data bouring districts have similar malaria cases at county Getis-Ord G*.To detect significant space-time clusters,
i malaria cases highly cluster at country level for all the
quality, the government adopted the Global Technical level. 999 Monte Carlo replications were performed under the
years under study.
Strategy for Malaria 2016–2030 which stresses the need null hypothesis of random distribution of malaria cases
for adequate investment in the management and use of Detecting malaria clusters using SaTScan [32]. In this case, statistical significance was tested using Spatial clusters of malaria from 2011 to 2016
data from routine health information systems to support a Poisson generalized log likelihood ratio test based on
In this study, scan statistics [42] was applied in SaTScan The results for the statistically significant (P < 0.05)
programme planning, implementation and evaluation Monte-Carlo inference [32, 60].
v9.6 (https ://www.satsc an.org/) software to detect high primary and secondary spatial clusters as well as the
[50]. The relative risk was calculated by comparing the
cluster rate of malaria. In this case, spatial scan statis- corresponding relative risk for high rates of malaria
observed number of cases of malaria within each window
tic, based on the discrete Poisson model, was applied occurrence identified by purely spatial scan statistic
to the expected number, using a Poisson model. The most
to identify purely spatial clusters of malaria cases by based on the discrete Poisson model are illustrated in
Population data likely cluster (hereinafter, primary cluster) was identi-
year. On the other hand, the space-time scan statis- Fig. 4. The results illustrate that there was significant
Population data used in this study were obtained from the fied based on the maximum log likelihood ratio [61]. In
tic, based on Space-Time Poisson model was adopted spatial clustering of malaria cases in specific districts
Zimbabwe National Statistical Agency (ZimStat) based addition, other clusters with statistically significant log
to determine the presence of space-time clusters of from the years 2011 to 2016 (Fig. 4, Table 2). Over the
on the 2012 National population census [51]. The 2010 likelihood values were defined as secondary clusters. The
malaria cases by month over the study period. Three six years, primary clusters of malaria were concen-
and 2011 population data was based on a 1.1% projected criterion of no geographical overlap was used to report
datasets were prepared for use in SaTScan and these trated in the eastern region of the country. The number
growth rate from the 2002 National census [52] while the secondary clusters.
were: a case file representing annual malaria cases per
49
page number not for citation purpose
Downloaded from mednexus.org on [June 20, 2026]. For personal use only.

--- Page 6 ---
Gwitira et al. Infect Dis Poverty (2020) 9:146 Page 6 of 14 Gwitira et al. Infect Dis Poverty (2020) 9:146 Page 7 of 14
Fig. 2 Average monthly malaria incidence from 2011 to 2016
of districts covered by the primary clusters increased spatio-temporal clusters consisted of one primary clus-
from four in 2011 to 12 in 2016. In general, second- ter and three secondary clusters. The primary cluster
ary clusters are characteristic of the eastern, northern, was located in the north eastern region and covers eight
south-western and south-eastern regions of the coun- administrative districts (Fig. 6).
try. However, the spatial location and size of these sec- The primary cluster was detected from the 1st of
ondary clusters varied by year (Fig. 4). December 2012 to the 31st of May 2014. The primary
Further, results illustrate that the lowest number of cluster persisted in this region for three seasons and cov-
malaria cases within a cluster was 5414 (2011) while the ered eight districts (Table 3).
highest was 92 324 (2012). Across all the years under
Discussion
study, the most likely clusters had higher than expected
malaria cases (Table 2). In this study, Geographic Information System coupled
with a spatial scan statistical method were success-
Frequency of cluster occurrence from 2011 to 2016 fully applied to explore spatial and temporal patterns of
The frequency of occurrence of malaria clusters within malaria clusters between 2011 and 2016 at district level
districts based on scan statistics is illustrated in Fig. 5. in Zimbabwe. The results of this study showed signifi-
It is observed that districts in the northern, north-east- cant global spatial autocorrelation of malaria cases from
ern, eastern and south-eastern regions of the country 2011 to 2016 which indicates that the spatial distribu-
had the highest frequency of malaria clusters. Districts tion of malaria followed a clustered pattern. The results
at the margins of high malaria cluster districts had low confirm findings from previous studies that observed the
frequency of cluster occurrence. In contrast the central, tendency of malaria to cluster in particular geographic
western and south western districts had no malaria clus- regions mostly derived by the spatial heterogeneity in
ters during the period under consideration. the factors that drive transmission of the disease [20, Fig. 3 Spatial distribution of annual malaria incidence for a 2011, b 2012, c 2013, d 2014, e 2015 and f 2016
31]. Based on previous studies, the spatial heterogeneity
Space‑time clusters of malaria in malaria is largely attributed to variation in environ-
Results of space-time Poisson model show four spatial– mental risk factors at the macro (e.g., temperature, pre- the variation in malaria cases coincide with the distribu- parasite [21]. Thus, our study further provides evidence
temporal malaria clusters that were detected from 2011 cipitation) and the micro (e.g., local elevation, land use) tion of the preferred habitat of the Anopheles mosquitoes of spatial heterogeneity in the occurrence of malaria in
to 2016 (Fig. 6, Table 3). The four statistically significant spatial scales [21]. From the observed detected pattern, which are the main vectors that transmit P. falciparum the affected regions.
50
page number not for citation purpose
Downloaded from mednexus.org on [June 20, 2026]. For personal use only.

--- Page 7 ---
Gwitira et al. Infect Dis Poverty (2020) 9:146 Page 6 of 14 G witira et al. Infect Dis Poverty (2020) 9:146 Page 7 of 14
Fig. 2 Average monthly malaria incidence from 2011 to 2016
of districts covered by the primary clusters increased spatio-temporal clusters consisted of one primary clus-
from four in 2011 to 12 in 2016. In general, second- ter and three secondary clusters. The primary cluster
ary clusters are characteristic of the eastern, northern, was located in the north eastern region and covers eight
south-western and south-eastern regions of the coun- administrative districts (Fig. 6).
try. However, the spatial location and size of these sec- The primary cluster was detected from the 1st of
ondary clusters varied by year (Fig. 4). December 2012 to the 31st of May 2014. The primary
Further, results illustrate that the lowest number of cluster persisted in this region for three seasons and cov-
malaria cases within a cluster was 5414 (2011) while the ered eight districts (Table 3).
highest was 92 324 (2012). Across all the years under
Discussion
study, the most likely clusters had higher than expected
malaria cases (Table 2). In this study, Geographic Information System coupled
with a spatial scan statistical method were success-
Frequency of cluster occurrence from 2011 to 2016 fully applied to explore spatial and temporal patterns of
The frequency of occurrence of malaria clusters within malaria clusters between 2011 and 2016 at district level
districts based on scan statistics is illustrated in Fig. 5. in Zimbabwe. The results of this study showed signifi-
It is observed that districts in the northern, north-east- cant global spatial autocorrelation of malaria cases from
ern, eastern and south-eastern regions of the country 2011 to 2016 which indicates that the spatial distribu-
had the highest frequency of malaria clusters. Districts tion of malaria followed a clustered pattern. The results
at the margins of high malaria cluster districts had low confirm findings from previous studies that observed the
frequency of cluster occurrence. In contrast the central, tendency of malaria to cluster in particular geographic
western and south western districts had no malaria clus- regions mostly derived by the spatial heterogeneity in
ters during the period under consideration. the factors that drive transmission of the disease [20, Fig. 3 Spatial distribution of annual malaria incidence for a 2011, b 2012, c 2013, d 2014, e 2015 and f 2016
31]. Based on previous studies, the spatial heterogeneity
Space‑time clusters of malaria in malaria is largely attributed to variation in environ-
Results of space-time Poisson model show four spatial– mental risk factors at the macro (e.g., temperature, pre- the variation in malaria cases coincide with the distribu- parasite [21]. Thus, our study further provides evidence
temporal malaria clusters that were detected from 2011 cipitation) and the micro (e.g., local elevation, land use) tion of the preferred habitat of the Anopheles mosquitoes of spatial heterogeneity in the occurrence of malaria in
to 2016 (Fig. 6, Table 3). The four statistically significant spatial scales [21]. From the observed detected pattern, which are the main vectors that transmit P. falciparum the affected regions.
51
page number not for citation purpose
Downloaded from mednexus.org on [June 20, 2026]. For personal use only.

--- Page 8 ---
Gwitira et al. Infect Dis Poverty (2020) 9:146 Page 8 of 14 Gwitira et al. Infect Dis Poverty (2020) 9:146 Page 9 of 14
Table 1 Spatial autocorrelation test on malaria cases during this period is not surprising as the country
from 2011 to 2016 receives most of its rainfall between December and
Year Moran’s index Z score P‑value March which dissipates towards April and May [13].
The high amount of rainfall coupled with relatively high
2011 0.53 20.00 0.00
temperatures during this period provides optimal con-
2012 0.56 21.45 0.00
ditions for mosquito breeding and subsequent malaria
2013 0.41 15.67 0.00
transmission [13]. Previous studies have shown that
2014 0.45 17.27 0.00
this period coincides with the malaria epidemic season
2015 0.57 21.48 0.00
in Zimbabwe and offers favourable climatic conditions
2016 0.25 112.09 0.00
in high risk months for malaria transmission [7, 13, 44].
When combined with location specific information on
malaria clustering, results of space-time clustering fur-
ther points to the importance of incorporating these
Results of purely spatial analysis based on the pois-
two aspects in order to fully understand malaria trans-
son model showed that primary and secondary clusters
mission dynamics. Such insights would not have been
of malaria persisted in the northern, north-eastern,
generated had the study only adopted either purely spa-
eastern and south-eastern districts of Zimbabwe. The
tial or purely temporal approach in modelling cluster-
results show that consistently over the study period,
ing of malaria. The results of space-time analysis can
malaria clusters occur in different sizes and at different
then be utilised to plan timing of control interventions
locations. This is important in identifying stable cluster
by targeting those months where clusters are common.
areas which persist in areas of high malaria burden [20].
This would require deviation from the usual practice
The results support the hypothesis that malaria cases
where indoor residual spraying is done well before the
tend to significantly cluster within certain geographic
malaria season.
units albeit with observable shifts over time. This may
What makes this study different from other previous
indicate that the occurrence of malaria in Zimbabwe is
studies is that, unlike previous studies, this study used
characterised by spatial heterogeneity as high-risk areas
malaria case data for a relatively long period (six years)
still exist particularly in the north north-east, east and
which provides important insights in the persistence of
south eastern districts of the country [31]. The high risk
clusters (stable clusters) in certain geographic regions.
areas detected in this study are consistent with malaria
In addition, this study integrated space and time in one
hotspots detected through Getis G* statistic analysis
i analytical framework which provides new insights into
and were closely related to high vector habitat suit-
the evolution of malaria not only in the spatial but also in
ability [2]. In addition, the high risk areas coincide with
the temporal domain. This study utilised one of the most
the high and perennial malaria risk zones delineated
robust methods of cluster detection to understand the
through malaria risk stratification in Zimbabwe [62].
pattern of malaria clusters unlike previous studies which
As the country moves towards malaria elimination [13],
have mostly utilised hotspot analysis techniques such the
there is need to prioritise control efforts by focussing
Getis G* statistic [2]. The technique used in this study
on high risk areas as these are possible reservoirs of i
has both high specificity and sensitivity hence provides a
malaria transmission [63]. The detection of statistically
balance in terms of committing at type 1 or type 2 errors.
significant malaria clusters is a critical step towards
Furthermore, the high risk areas identified in this study
spatial targeting and selection of appropriate popula-
may serve as important starting points for future dis-
tion level interventions as these clusters are potential
ease surveillance in resource limited environments such
reservoirs for future infection [20, 27]. Through the
as Zimbabwe. Apart from providing disease surveillance
detection of clusters, affected countries can shift from
targets, such high risk areas could be prioritised during
malaria control to malaria elimination which is one of
resource allocation to achieve effective disease control.
the key goals of the WHO Global Technical Strategy
However, further research should be focussed in these
for Malaria 2016–2030 [14]. The targeting of high risk
areas to fully understand disease etiology and local fac-
areas for malaria control aligns with the United Nations
tors that support elevated malaria risk.
Sustainable Development Goal (SDG) number three
Data quality related to use of retrospective data may Fig. 4 Spatial distribution of malaria clusters detected by purely spatial for a 2011, b 2012, c 2013, d 2014, e 2015 and f 2016. (The primary cluster is
which is seeks to promote good health and well-being illustrated by a darker outline)
have affected the results of this study. Most develop-
through scaling up of malaria interventions [4, 64].
ing countries are characterised by incomplete reporting
Results of space-time analysis showed that malaria
of routine data, non-reporting, missing data and poor
clusters tend to occur in particular months e.g. Decem-
data aggregation frameworks [65]. Nonetheless, malaria
ber to May. The fact that most clusters were detected
case-management and data quality have greatly improved
52
page number not for citation purpose
Downloaded from mednexus.org on [June 20, 2026]. For personal use only.

--- Page 9 ---
Gwitira et al. Infect Dis Poverty (2020) 9:146 Page 8 of 14 G witira et al. Infect Dis Poverty (2020) 9:146 Page 9 of 14
Table 1 Spatial autocorrelation test on malaria cases during this period is not surprising as the country
from 2011 to 2016 receives most of its rainfall between December and
Year Moran’s index Z score P‑value March which dissipates towards April and May [13].
The high amount of rainfall coupled with relatively high
2011 0.53 20.00 0.00
temperatures during this period provides optimal con-
2012 0.56 21.45 0.00
ditions for mosquito breeding and subsequent malaria
2013 0.41 15.67 0.00
transmission [13]. Previous studies have shown that
2014 0.45 17.27 0.00
this period coincides with the malaria epidemic season
2015 0.57 21.48 0.00
in Zimbabwe and offers favourable climatic conditions
2016 0.25 112.09 0.00
in high risk months for malaria transmission [7, 13, 44].
When combined with location specific information on
malaria clustering, results of space-time clustering fur-
ther points to the importance of incorporating these
Results of purely spatial analysis based on the pois-
two aspects in order to fully understand malaria trans-
son model showed that primary and secondary clusters
mission dynamics. Such insights would not have been
of malaria persisted in the northern, north-eastern,
generated had the study only adopted either purely spa-
eastern and south-eastern districts of Zimbabwe. The
tial or purely temporal approach in modelling cluster-
results show that consistently over the study period,
ing of malaria. The results of space-time analysis can
malaria clusters occur in different sizes and at different
then be utilised to plan timing of control interventions
locations. This is important in identifying stable cluster
by targeting those months where clusters are common.
areas which persist in areas of high malaria burden [20].
This would require deviation from the usual practice
The results support the hypothesis that malaria cases
where indoor residual spraying is done well before the
tend to significantly cluster within certain geographic
malaria season.
units albeit with observable shifts over time. This may
What makes this study different from other previous
indicate that the occurrence of malaria in Zimbabwe is
studies is that, unlike previous studies, this study used
characterised by spatial heterogeneity as high-risk areas
malaria case data for a relatively long period (six years)
still exist particularly in the north north-east, east and
which provides important insights in the persistence of
south eastern districts of the country [31]. The high risk
clusters (stable clusters) in certain geographic regions.
areas detected in this study are consistent with malaria
In addition, this study integrated space and time in one
hotspots detected through Getis G* statistic analysis
i analytical framework which provides new insights into
and were closely related to high vector habitat suit-
the evolution of malaria not only in the spatial but also in
ability [2]. In addition, the high risk areas coincide with
the temporal domain. This study utilised one of the most
the high and perennial malaria risk zones delineated
robust methods of cluster detection to understand the
through malaria risk stratification in Zimbabwe [62].
pattern of malaria clusters unlike previous studies which
As the country moves towards malaria elimination [13],
have mostly utilised hotspot analysis techniques such the
there is need to prioritise control efforts by focussing
Getis G* statistic [2]. The technique used in this study
on high risk areas as these are possible reservoirs of i
has both high specificity and sensitivity hence provides a
malaria transmission [63]. The detection of statistically
balance in terms of committing at type 1 or type 2 errors.
significant malaria clusters is a critical step towards
Furthermore, the high risk areas identified in this study
spatial targeting and selection of appropriate popula-
may serve as important starting points for future dis-
tion level interventions as these clusters are potential
ease surveillance in resource limited environments such
reservoirs for future infection [20, 27]. Through the
as Zimbabwe. Apart from providing disease surveillance
detection of clusters, affected countries can shift from
targets, such high risk areas could be prioritised during
malaria control to malaria elimination which is one of
resource allocation to achieve effective disease control.
the key goals of the WHO Global Technical Strategy
However, further research should be focussed in these
for Malaria 2016–2030 [14]. The targeting of high risk
areas to fully understand disease etiology and local fac-
areas for malaria control aligns with the United Nations
tors that support elevated malaria risk.
Sustainable Development Goal (SDG) number three
Data quality related to use of retrospective data may Fig. 4 Spatial distribution of malaria clusters detected by purely spatial for a 2011, b 2012, c 2013, d 2014, e 2015 and f 2016. (The primary cluster is
which is seeks to promote good health and well-being illustrated by a darker outline)
have affected the results of this study. Most develop-
through scaling up of malaria interventions [4, 64].
ing countries are characterised by incomplete reporting
Results of space-time analysis showed that malaria
of routine data, non-reporting, missing data and poor
clusters tend to occur in particular months e.g. Decem-
data aggregation frameworks [65]. Nonetheless, malaria
ber to May. The fact that most clusters were detected
case-management and data quality have greatly improved
53
page number not for citation purpose
Downloaded from mednexus.org on [June 20, 2026]. For personal use only.

--- Page 10 ---
Gwitira et al. Infect Dis Poverty (2020) 9:146 Page 10 of 14 Gwitira et al. Infect Dis Poverty (2020) 9:146 Page 11 of 14
Table 2 Significant malaria clusters detected using the purely spatial clustering
Year Cluster type Cluster areas Observed Expected RR Radius(km) LLR P‑value
(n)
A 3 48 569 9569 6.38 74 44 198 0.00
B 6 58 222 22 305 3.27 126 23 850 0.00
2011 B 2 13 937 4520 3.24 55 6 506 0.00
B 7 47 530 36 405 1.40 152 1 937 0.00
B 2 5414 5015 1.08 32 16 0.00
A 3 92 324 17 148 6.94 74 89 397 0.00
B 2 74 241 22 710 3.88 60 40 668 0.00
2012 B 5 44 030 25 085 1.86 73 6 386 0.00
B 3 42 155 28 805 1.53 113 2 982 0.00
B 5 34 236 31 941 1.08 122 89 0.00
A 12 247 572 108 723 3.78 152 97 033 0.00
2013 B 2 41 339 10 382 4.28 74 27 258 0.00
B 3 52 771 37 524 1.46 113 3 026 0.00
A 3 52 868 12 087 5.28 74 40 965 0.00
B 4 36 004 14 553 2.72 69 12 175 0.00
2014 B 2 16 088 5243 3.21 55 7 438 0.00
B 3 17 509 14 423 1.23 69 329 0.00
A 1 28 145 5788 5.47 114 23 439 0.00
2015 B 2 13 261 5885 2.34 74 3 533 0.00
A 12 211 251 88 565 3.88 152 88 392 0.00
Fig. 5 Frequency of cluster occurrence from 2011 to 2016
B 2 79 698 23 800 3.92 60 44 713 0.00
2016 B 3 77 507 30 514 2.90 113 28 321 0.00
B 2 31 355 12 709 2.59 74 10 118 0.00
A primary cluster, B secondary, RR relative risk; LLR log likelihood ratio
particularly parasitological testing as well as the adoption [73, 74]. Imported cases could have influenced the size
of electronic databases such as DHIS2. Although routine and location of high rates of malaria clusters detected
data from health facilities is known to underestimate in this study. Migration related malaria remains a major
malaria burden due to the above mentioned factors, the problem for Zimbabwe especially in the eastern parts of
data is still useful in understanding the spatial distribu- the country. The occurrence of malaria due to migration
tion of malaria in endemic regions [66, 67]. Thus, the could be as a result of locals travelling to neighbouring
results of this study provide an important basis for plan- Mozambique during the day and contracting malaria
ning and implementation of malaria control strategies. which is then reported in eastern districts. Addition-
Although spatial and spatio-temporal clusters of ally, populations from neighbouring country may access
malaria were successfully detected using data from 2011 treatment in Zimbabwe’s eastern districts where the
to 2016, one limitation is that the malaria cases used in treatment is free to patients. Usually these cases are not
this study did not differentiate local and imported cases. reported in the DHIS2 database despite receiving treat-
It is important to differentiate local and imported malaria ment. The use of genomic surveillance may address the
cases particularly given the observation that most of the first challenge of locals contracting malaria from the
high rates of malaria clusters tend to be concentrated neighbouring country. Introducing a data point recording
along borderline areas [68, 69]. The challenge is that non-resident malaria patients would allow an accurate
a greater part of the borders of the country are porous characterisation of the burden of malaria in the eastern
making it difficult to monitor movement. For example, to border districts. There is therefore need for national data
the east Zimbabwe shares a 730 km border with Mozam- collection systems to incorporate imported cases in their
bique which is also known to have high malaria cases systems. To achieve this, there is need for closer collabo-
while to the south-east the country borders with South ration with neighbouring countries.
Africa along the Limpopo valley (a malaria endemic The information generated in this study could be
Fig. 6 Spatial distribution of detected space-time clusters of malaria from 2011 to 2016
region) [70–72] and to the North it borders with Zambia important in strengthening cross border collaboration
54
page number not for citation purpose
Downloaded from mednexus.org on [June 20, 2026]. For personal use only.

--- Page 11 ---
Gwitira et al. Infect Dis Poverty (2020) 9:146 Page 10 of 14 G witira et al. Infect Dis Poverty (2020) 9:146 Page 11 of 14
Table 2 Significant malaria clusters detected using the purely spatial clustering
Year Cluster type Cluster areas Observed Expected RR Radius(km) LLR P‑value
(n)
A 3 48 569 9569 6.38 74 44 198 0.00
B 6 58 222 22 305 3.27 126 23 850 0.00
2011 B 2 13 937 4520 3.24 55 6 506 0.00
B 7 47 530 36 405 1.40 152 1 937 0.00
B 2 5414 5015 1.08 32 16 0.00
A 3 92 324 17 148 6.94 74 89 397 0.00
B 2 74 241 22 710 3.88 60 40 668 0.00
2012 B 5 44 030 25 085 1.86 73 6 386 0.00
B 3 42 155 28 805 1.53 113 2 982 0.00
B 5 34 236 31 941 1.08 122 89 0.00
A 12 247 572 108 723 3.78 152 97 033 0.00
2013 B 2 41 339 10 382 4.28 74 27 258 0.00
B 3 52 771 37 524 1.46 113 3 026 0.00
A 3 52 868 12 087 5.28 74 40 965 0.00
B 4 36 004 14 553 2.72 69 12 175 0.00
2014 B 2 16 088 5243 3.21 55 7 438 0.00
B 3 17 509 14 423 1.23 69 329 0.00
A 1 28 145 5788 5.47 114 23 439 0.00
2015 B 2 13 261 5885 2.34 74 3 533 0.00
A 12 211 251 88 565 3.88 152 88 392 0.00
Fig. 5 Frequency of cluster occurrence from 2011 to 2016
B 2 79 698 23 800 3.92 60 44 713 0.00
2016 B 3 77 507 30 514 2.90 113 28 321 0.00
B 2 31 355 12 709 2.59 74 10 118 0.00
A primary cluster, B secondary, RR relative risk; LLR log likelihood ratio
particularly parasitological testing as well as the adoption [73, 74]. Imported cases could have influenced the size
of electronic databases such as DHIS2. Although routine and location of high rates of malaria clusters detected
data from health facilities is known to underestimate in this study. Migration related malaria remains a major
malaria burden due to the above mentioned factors, the problem for Zimbabwe especially in the eastern parts of
data is still useful in understanding the spatial distribu- the country. The occurrence of malaria due to migration
tion of malaria in endemic regions [66, 67]. Thus, the could be as a result of locals travelling to neighbouring
results of this study provide an important basis for plan- Mozambique during the day and contracting malaria
ning and implementation of malaria control strategies. which is then reported in eastern districts. Addition-
Although spatial and spatio-temporal clusters of ally, populations from neighbouring country may access
malaria were successfully detected using data from 2011 treatment in Zimbabwe’s eastern districts where the
to 2016, one limitation is that the malaria cases used in treatment is free to patients. Usually these cases are not
this study did not differentiate local and imported cases. reported in the DHIS2 database despite receiving treat-
It is important to differentiate local and imported malaria ment. The use of genomic surveillance may address the
cases particularly given the observation that most of the first challenge of locals contracting malaria from the
high rates of malaria clusters tend to be concentrated neighbouring country. Introducing a data point recording
along borderline areas [68, 69]. The challenge is that non-resident malaria patients would allow an accurate
a greater part of the borders of the country are porous characterisation of the burden of malaria in the eastern
making it difficult to monitor movement. For example, to border districts. There is therefore need for national data
the east Zimbabwe shares a 730 km border with Mozam- collection systems to incorporate imported cases in their
bique which is also known to have high malaria cases systems. To achieve this, there is need for closer collabo-
while to the south-east the country borders with South ration with neighbouring countries.
Africa along the Limpopo valley (a malaria endemic The information generated in this study could be
Fig. 6 Spatial distribution of detected space-time clusters of malaria from 2011 to 2016
region) [70–72] and to the North it borders with Zambia important in strengthening cross border collaboration
55
page number not for citation purpose
Downloaded from mednexus.org on [June 20, 2026]. For personal use only.

--- Page 12 ---
Gwitira et al. Infect Dis Poverty (2020) 9:146 Page 12 of 14 Gwitira et al. Infect Dis Poverty (2020) 9:146 Page 13 of 14
Table 3 Spatial–temporal high risk clusters of malaria cases detected using space-time Poisson model from 2011 to 2017 Ethics approval and consent to participate 17. Ernst KC, Adoka SO, Kowuor DO, Wilson ML, John CC. Malaria hotspot
Although human data was used in this study, it was only the aggregate total areas in a highland Kenya site are consistent in epidemic and non-epi-
Cluster # # of Location Start date End date LLR P value RR Radius not individual subjects therefore “Not applicable”. demic years and are associated with ecological factors. Malar J. 2006;5:78.
18. Hundessa SH, Williams G, Li S, Guo J, Chen L, Zhang W, et al. Spatial and
*1 8 01/12/2012 31/05/2014 331 605 0.001 6.10 137 Consent for Publication space–time distribution of Plasmodiumvivax and Plasmodiumfalciparum
2 9 01/03/2014 31/05/2014 148 263 0.001 10.89 114 Not applicable. malaria in China, 2005–2014. Malar J. 2016;15:1–11.
19. Landier J, Rebaudet S, Piarroux R, Gaudart J. Spatiotemporal analysis of
3 6 01/01/2016 31/05/2016 83 074 0.001 7.74 113
Competing interests malaria for new sustainable control strategies. BMC Med. 2018;16:226.
4 3 01/04/2014 31/05/2014 313 0.001 1.38 99 The authors declare that they have no competing interests. 20. Bousema T, Kreuels B, Gosling R. Adjusting for heterogeneity of malaria
transmission in longitudinal studies. J Infect Dis. 2011;204:1–3.
*Primary cluster Author details 21. Stresman GH. Beyond temperature and precipitation: ecological risk fac-
RR relative risk, LLR Log likelihood ratio 1 Department of Geography Geospatial Sciences and Earth Observation, tors that modify malaria transmission. Acta Trop. 2010;116:167–72.
University of Zimbabwe, P. O. Box MP 167, Mount Pleasant, Harare, Zimbabwe. 22. Mclafferty S. Disease cluster detection methods: recent developments
2 Department of Community Medicine, University of Zimbabwe, 3rd Floor and Public health implications. Ann GIS. 2015;21:127–33.
given that the country has joined other Southern Afri- malaria occurrence. The study is helpful in prioritiz- New Health Sciences Building, College of Health Sciences, P O Box A178, 23. Hasyim H, Nursafingi A, Haque U, Montag D, Groneberg DA, Dhimal M,
Avondale, Harare, Zimbabwe. 3 National Malaria Control Program, Ministry et al. Spatial modelling of malaria cases associated with environmental
can countries to achieve malaria elimination [13, 73]. ing resource allocation in high-risk areas for effective
of Health and Child Care, 4th Floor, Kaguvi Building, Central Avenue (Between factors in South Sumatra, Indonesia. Malar J. 2018;17:87.
This will be achieved through alliances such as Elimina- disease control. Although results are based on histori- 4th and 5th Street), Harare, Zimbabwe. 24. Carter R, Mendis KN, Roberts D. Spatial targeting of interventions against
tion8 (E8) comprising Angola, Botswana, Mozambique, cal data, they are useful in tracking progress the country malaria. Bull World Health Organ. 2000;78:1401–11.
Received: 11 May 2020 Accepted: 14 October 2020 25. Magalhaes RJS, Langa A, Sousa-Figueiredo JC, Clements ACA, Nery SV.
Namibia, South Africa Swaziland, Zambia and Zimba- has made in reducing malaria incidence. In addition, the
Finding malaria hot-spots in northern Angola: the role of individual,
bwe. Closer collaboration in malaria elimination could results can be used as a baseline to evaluate the impacts household and environmental factors within a meso-endemic area. Malar
be achieved through the ZAMZIM (Zambia and Zimba- of malaria programmes implemented during this period J. 2012;11:385.
26. Coleman M, Coleman M, Mabuza AM, Kok G, Coetzee M, Durrheim DN.
bwe), and the MOZAZI (Mozambique, Zambia and Zim- which is important in informing current and future con-
Using the SaTScan method to detect local malaria clusters for guiding
babwe), and the MOZIZA (Mozambique, Zimbabwe and trol strategies. malaria control programmes. Malar J. 2009;8:68.
References
South Africa) initiatives [3, 13, 73]. 1. Feng X, Levens J, Zhou XN. Protecting the gains of malaria elimination in 27. Loha E, Lunde TM, Lindtjørn B. Effect of bednets and indoor residual
spraying on spatio-temporal clustering of malaria in a village in South
Nevertheless, insights generated in this study are use- China. Infect Dis of Poverty. 2020;9:43.
Abbreviations 2. Gwitira I, Murwira A, Zengeya FM, Shekede MD. Application of GIS to pre- Ethiopia: a longitudinal study. PLoS ONE. 2012;7(10):e47354.
ful in guiding further research on tightening cross border DHIS: District Health Information System; GIS: Geographic Information System; dict malaria hotspots based on Anopheles arabiensis habitat suitability in 28. Gaudart J, Poudiougou B, Dicko A, Ranque S, Toure O, Sagara I, et al.
migration to malaria transmission and strengthening col- IRS: Indoor residual spraying; MOZAZI: Mozambique, Zambia and Zimba- Southern Africa. Int J Appl Earth Obs Geoinf. 2018;64:12–21. Space-time clustering of childhood malaria at the household level: a
laboration among neighbouring countries in the control bwe; MOZIZA: Mozambique, Zimbabwe and South Africa; SDG: Sustainable 3. Deng T, Huang Y, Yu S, Gu J, Huang C. Spatial-temporal clusters and risk dynamic cohort in a Mali village. BMC Publ Health. 2006;6:286.
Development Goal; WHO: World Health Organisation; ZAMZIM: Zambia and factors of hand, foot, and mouth disease at the district level in Guang- 29. Wen L, Li C, Lin M, Yuan Z, Huo D, Li S, et al. Spatio-temporal analysis of
of malaria. This is because without collaboration, malaria Zimbabwe; ZIMSTAT : Zimbabwe National Statistics. dong Province, China. PLoS ONE. 2013;8(2):e56943. malaria incidence at the village level in a malaria-endemic area in Hainan,
elimination is bound to fail as malaria occurrence due the 4. WHO. World malaria report 2019. Geneva: World Health Organisation; China. Malar J. 2011;10:1–7.
influence of imported cases. Another potential limitation Acknowledgements 2019. 30. Alemu K, Worku A, Berhane Y. Malaria infection has spatial, temporal and
The authors would like to thank the government of Zimbabwe through the 5. Campillo A, Daily J, Gonzalez IJ. International survey to identify diagnostic spatiotemporal heterogeneity in unstable malaria transmission areas in
of the study is that although Kulldorff’s scan statistic has Ministry of Health and Child Care, Malaria Control Program for approving needs to support malaria elimination: guiding the development of com- Northwest Ethiopia. PLoS ONE. 2013;8(11):e79966.
been successfully used to detect circular clusters, it does accessing to data and other valuable documents used in the write-up of this bination highly sensitive rapid diagnostic tests. Malar J. 2017;16:385. 31. Manyangadze T, Chimbari MJ, Macherera M, Mukaratirwa S. Micro-spatial
not have the same success rate when detecting irregu- manuscript. 6. Masendu HT, Hunt RH, Koekemoer LL, Brooke BD, Govere J, Coetzee M, distribution of malaria cases and control strategies at ward level in
Gwanda district, Matabeleland South, Zimbabwe. Malar J. 2017;16:476.
et al. Spatial and temporal distributions and insecticide susceptibility of
lar clusters [75]. Despite these potential limitations, the Authors’ contributions malaria vectors in Zimbabwe. Afr Entomol. 2005;13:25–34. 32. Xia J, Cai S, Zhang H, Lin W, Fan Y, Qiu J, et al. Spatial, temporal and spati-
results of this study are still important and may be useful IG conceptualised the study and did the manuscript write-up. MM and GM 7. Taylor P, Mutambu SL. A review of the malaria situation in Zimbabwe with otemporal analysis of malaria in Hubei Province, China from 2004–2011.
for planning disease surveillance, particularly in areas of analysed the data and presented the results. MDS was involved in manuscript special reference to the period 1972–l981. Trans R Soc Trop Med Hyg. Malar J. 2015;14:145.
integration. JC provided the epidemiological significance of the study while 1986;80:12–9. 33. Gwitira I, Murwira A, Mberikunashe J, Masocha M. Spatial overlaps in
limited resources by focussing on high risk areas. JM facilitated access to data used in this study. All authors read and approved 8. Khagayi S, Desai M, Amek N, Were V, Onyango ED, Odero C, et al. the distribution of HIV/AIDS and malaria in Zimbabwe. BMC Infect Dis.
the final manuscript. Modelling the relationship between malaria prevalence as a measure of 2018;18:1.
Conclusions transmission and mortality across age groups. Malar J. 2019;18:247. 34. Wheeler DC. A comparison of spatial clustering and cluster detection
Authors’ information 9. Mfueni E, Devleesschauwer B, Aguirre AR, Malderen CV, Brandt PT, Ogutu techniques for childhood leukaemia incidence in Ohio, 1996–2003. Int J
This study explored whether there is spatial heterogene- IG is a senior lecturer in the Department of Geography Geospatial Sciences B, et al. True malaria prevalence in children under five: Bayesian estima- Health Geogr. 2007;6:13.
ity in the distribution of malaria, one of the diseases of and Earth Observation at the University of Zimbabwe and specialises in geo- tion using data of malaria household surveys from three subSaharan 35. Yamada I, Rogerson PA, Lee G. GeoSurveillance: a GIS-based system
global public health concern. This was achieved through spatial health i.e., application of GIS and remote sensing to understand human countries. Malar J. 2018;17:65. for the detection and monitoring of spatial clusters. J Geogr Syst.
and animal diseases in space. He currently leads the Geospatial research group 10. WHO. World malaria report 2016. Geneva: World Health Organisation; 2009;11:155–73.
the detection of spatial and space-time clusters using in the department. MDS is a senior lecturer in the Geography Geospatial Sci- 2016. 36. Robertson C, Nelson TA. Review of software for space-time disease
scan statistics. The results indicated that high risk areas ences and Earth Observation at the University of Zimbabwe specialising in the 11. Yakob L, Cameron M, Lines J. Combining indoor and outdoor methods surveillance. Int J Health Geogr. 2010;9:16.
for malaria are concentrated in the northern, eastern, application of GIS and remote sensing to various fields including health. MM for controlling malaria vectors: an ecological model of endectocide- 37. Wand H, Ramjee G. Targeting the hotspots: investigating spatial and
and GM are graduate students from the University of Zimbabwe with speciali- treated livestock and insecticidal bed nets. Malar J. 2017;11:1–13. demographic variations in HIV infection in small communities in South
and south-eastern part of the country. The results of this sations in geospatial health. JC is a lecturer in the College of Health Sciences 12. Sande S, Zimba M, Chinwada P, Masendu HT, Mberikunshe J, Makuwaza Africa. J Int AIDS Soc. 2010;13:41.
study could be used to design malaria control strategies and has special interest in community medicine and infectious diseases. JM is A. A review of new challenges and prospects for malaria elimination in 38. Tango T, Takahashi K. A flexible spatial scan statistic with a restricted likeli-
aimed at reducing malaria incidence in high risk areas the current director of the National Malaria Control Program in the Ministry of Mutare and Mutasa Districts. Zimbabwe Malar J. 2016;15:1. hood ratio for detecting disease clusters. Stat Med. 2012;31:4207–18.
Health and Child Care, Zimbabwe. 13. Sande S, Zimba M, Mberikunashe J, Tangwena A, Chimusoro A. Progress 39. Barro AS, Kracalik IT, Malania L, Tsertsvadze N, Manvelyan J, Imnadze P,
particularly those along border areas. In addition, the et al. Identifying hotspots of human anthrax transmission using three
towards malaria elimination in Zimbabwe with special reference to the
results could be used to guide optimal resource alloca- Funding period 2003–2015. Malar J. 2017;16:295. local clustering techniques. Appl Geogr. 2015;60:29–36.
tion by giving priority to the regions in greatest need. The No funding was received for this research. 14. WHO. Global technical strategy for malaria 2015. Geneva: World Health 40. Song C, Kulldorff M. Power evaluation of disease clustering tests. Int J
Health Geogr. 2003;2:9.
Organization; 2015a.
results of this study highlight the spatial heterogeneity in Availability of data and material 15. Alegana VA, Okiro EA, Snow RW. Routine data for malaria morbidity 41. Huang L, Pickle LW, Das B. Evaluating spatial methods for investigat-
malaria occurrence with several high-risk areas detected The statistical methods presented in this manuscript were implemented in a estimation in Africa: challenges and prospects. BMC Med. 2020;18:121. ing global clustering and cluster detection of cancer cases. Stat Med.
across the country. Based on this retrospective study, sig- freely downloadable software SaTScan version 9.4.2 available at (https ://www. 16. Mosha JF, Sturrock HJ, Greenwood BM, Sutherland CJ, Gadalla NB, Atwal 2008;27:5111–42.
satsc an.org/). The data used and/or analysed during the current study are S. Hot spot or not: a comparison of spatial statistical methods to predict 42. Kulldorff M. A spatial scan statistic. Commun Stat. 1997;26:1481–96.
nificant attention need to be directed to high risk areas available from the corresponding author on reasonable request. prospective malaria infections. Malar J. 2014;13:53. 43. Ndhlovu F, Ndhlovu DN, Chikerema SM, Masocha M, Nyagura M, Pfukenyi
as these may act as reservoirs for the current and future DM. Spatio-temporal patterns of clinical bovine dermatophilosis in
56
page number not for citation purpose
Downloaded from mednexus.org on [June 20, 2026]. For personal use only.

--- Page 13 ---
Gwitira et al. Infect Dis Poverty (2020) 9:146 Page 12 of 14 G witira et al. Infect Dis Poverty (2020) 9:146 Page 13 of 14
Table 3 Spatial–temporal high risk clusters of malaria cases detected using space-time Poisson model from 2011 to 2017 Ethics approval and consent to participate 17. Ernst KC, Adoka SO, Kowuor DO, Wilson ML, John CC. Malaria hotspot
Although human data was used in this study, it was only the aggregate total areas in a highland Kenya site are consistent in epidemic and non-epi-
Cluster # # of Location Start date End date LLR P value RR Radius not individual subjects therefore “Not applicable”. demic years and are associated with ecological factors. Malar J. 2006;5:78.
18. Hundessa SH, Williams G, Li S, Guo J, Chen L, Zhang W, et al. Spatial and
*1 8 01/12/2012 31/05/2014 331 605 0.001 6.10 137 Consent for Publication space–time distribution of Plasmodiumvivax and Plasmodiumfalciparum
2 9 01/03/2014 31/05/2014 148 263 0.001 10.89 114 Not applicable. malaria in China, 2005–2014. Malar J. 2016;15:1–11.
19. Landier J, Rebaudet S, Piarroux R, Gaudart J. Spatiotemporal analysis of
3 6 01/01/2016 31/05/2016 83 074 0.001 7.74 113
Competing interests malaria for new sustainable control strategies. BMC Med. 2018;16:226.
4 3 01/04/2014 31/05/2014 313 0.001 1.38 99 The authors declare that they have no competing interests. 20. Bousema T, Kreuels B, Gosling R. Adjusting for heterogeneity of malaria
transmission in longitudinal studies. J Infect Dis. 2011;204:1–3.
*Primary cluster Author details 21. Stresman GH. Beyond temperature and precipitation: ecological risk fac-
RR relative risk, LLR Log likelihood ratio 1 Department of Geography Geospatial Sciences and Earth Observation, tors that modify malaria transmission. Acta Trop. 2010;116:167–72.
University of Zimbabwe, P. O. Box MP 167, Mount Pleasant, Harare, Zimbabwe. 22. Mclafferty S. Disease cluster detection methods: recent developments
2 Department of Community Medicine, University of Zimbabwe, 3rd Floor and Public health implications. Ann GIS. 2015;21:127–33.
given that the country has joined other Southern Afri- malaria occurrence. The study is helpful in prioritiz- New Health Sciences Building, College of Health Sciences, P O Box A178, 23. Hasyim H, Nursafingi A, Haque U, Montag D, Groneberg DA, Dhimal M,
Avondale, Harare, Zimbabwe. 3 National Malaria Control Program, Ministry et al. Spatial modelling of malaria cases associated with environmental
can countries to achieve malaria elimination [13, 73]. ing resource allocation in high-risk areas for effective
of Health and Child Care, 4th Floor, Kaguvi Building, Central Avenue (Between factors in South Sumatra, Indonesia. Malar J. 2018;17:87.
This will be achieved through alliances such as Elimina- disease control. Although results are based on histori- 4th and 5th Street), Harare, Zimbabwe. 24. Carter R, Mendis KN, Roberts D. Spatial targeting of interventions against
tion8 (E8) comprising Angola, Botswana, Mozambique, cal data, they are useful in tracking progress the country malaria. Bull World Health Organ. 2000;78:1401–11.
Received: 11 May 2020 Accepted: 14 October 2020 25. Magalhaes RJS, Langa A, Sousa-Figueiredo JC, Clements ACA, Nery SV.
Namibia, South Africa Swaziland, Zambia and Zimba- has made in reducing malaria incidence. In addition, the
Finding malaria hot-spots in northern Angola: the role of individual,
bwe. Closer collaboration in malaria elimination could results can be used as a baseline to evaluate the impacts household and environmental factors within a meso-endemic area. Malar
be achieved through the ZAMZIM (Zambia and Zimba- of malaria programmes implemented during this period J. 2012;11:385.
26. Coleman M, Coleman M, Mabuza AM, Kok G, Coetzee M, Durrheim DN.
bwe), and the MOZAZI (Mozambique, Zambia and Zim- which is important in informing current and future con-
Using the SaTScan method to detect local malaria clusters for guiding
babwe), and the MOZIZA (Mozambique, Zimbabwe and trol strategies. malaria control programmes. Malar J. 2009;8:68.
References
South Africa) initiatives [3, 13, 73]. 1. Feng X, Levens J, Zhou XN. Protecting the gains of malaria elimination in 27. Loha E, Lunde TM, Lindtjørn B. Effect of bednets and indoor residual
spraying on spatio-temporal clustering of malaria in a village in South
Nevertheless, insights generated in this study are use- China. Infect Dis of Poverty. 2020;9:43.
Abbreviations 2. Gwitira I, Murwira A, Zengeya FM, Shekede MD. Application of GIS to pre- Ethiopia: a longitudinal study. PLoS ONE. 2012;7(10):e47354.
ful in guiding further research on tightening cross border DHIS: District Health Information System; GIS: Geographic Information System; dict malaria hotspots based on Anopheles arabiensis habitat suitability in 28. Gaudart J, Poudiougou B, Dicko A, Ranque S, Toure O, Sagara I, et al.
migration to malaria transmission and strengthening col- IRS: Indoor residual spraying; MOZAZI: Mozambique, Zambia and Zimba- Southern Africa. Int J Appl Earth Obs Geoinf. 2018;64:12–21. Space-time clustering of childhood malaria at the household level: a
laboration among neighbouring countries in the control bwe; MOZIZA: Mozambique, Zimbabwe and South Africa; SDG: Sustainable 3. Deng T, Huang Y, Yu S, Gu J, Huang C. Spatial-temporal clusters and risk dynamic cohort in a Mali village. BMC Publ Health. 2006;6:286.
Development Goal; WHO: World Health Organisation; ZAMZIM: Zambia and factors of hand, foot, and mouth disease at the district level in Guang- 29. Wen L, Li C, Lin M, Yuan Z, Huo D, Li S, et al. Spatio-temporal analysis of
of malaria. This is because without collaboration, malaria Zimbabwe; ZIMSTAT : Zimbabwe National Statistics. dong Province, China. PLoS ONE. 2013;8(2):e56943. malaria incidence at the village level in a malaria-endemic area in Hainan,
elimination is bound to fail as malaria occurrence due the 4. WHO. World malaria report 2019. Geneva: World Health Organisation; China. Malar J. 2011;10:1–7.
influence of imported cases. Another potential limitation Acknowledgements 2019. 30. Alemu K, Worku A, Berhane Y. Malaria infection has spatial, temporal and
The authors would like to thank the government of Zimbabwe through the 5. Campillo A, Daily J, Gonzalez IJ. International survey to identify diagnostic spatiotemporal heterogeneity in unstable malaria transmission areas in
of the study is that although Kulldorff’s scan statistic has Ministry of Health and Child Care, Malaria Control Program for approving needs to support malaria elimination: guiding the development of com- Northwest Ethiopia. PLoS ONE. 2013;8(11):e79966.
been successfully used to detect circular clusters, it does accessing to data and other valuable documents used in the write-up of this bination highly sensitive rapid diagnostic tests. Malar J. 2017;16:385. 31. Manyangadze T, Chimbari MJ, Macherera M, Mukaratirwa S. Micro-spatial
not have the same success rate when detecting irregu- manuscript. 6. Masendu HT, Hunt RH, Koekemoer LL, Brooke BD, Govere J, Coetzee M, distribution of malaria cases and control strategies at ward level in
Gwanda district, Matabeleland South, Zimbabwe. Malar J. 2017;16:476.
et al. Spatial and temporal distributions and insecticide susceptibility of
lar clusters [75]. Despite these potential limitations, the Authors’ contributions malaria vectors in Zimbabwe. Afr Entomol. 2005;13:25–34. 32. Xia J, Cai S, Zhang H, Lin W, Fan Y, Qiu J, et al. Spatial, temporal and spati-
results of this study are still important and may be useful IG conceptualised the study and did the manuscript write-up. MM and GM 7. Taylor P, Mutambu SL. A review of the malaria situation in Zimbabwe with otemporal analysis of malaria in Hubei Province, China from 2004–2011.
for planning disease surveillance, particularly in areas of analysed the data and presented the results. MDS was involved in manuscript special reference to the period 1972–l981. Trans R Soc Trop Med Hyg. Malar J. 2015;14:145.
integration. JC provided the epidemiological significance of the study while 1986;80:12–9. 33. Gwitira I, Murwira A, Mberikunashe J, Masocha M. Spatial overlaps in
limited resources by focussing on high risk areas. JM facilitated access to data used in this study. All authors read and approved 8. Khagayi S, Desai M, Amek N, Were V, Onyango ED, Odero C, et al. the distribution of HIV/AIDS and malaria in Zimbabwe. BMC Infect Dis.
the final manuscript. Modelling the relationship between malaria prevalence as a measure of 2018;18:1.
Conclusions transmission and mortality across age groups. Malar J. 2019;18:247. 34. Wheeler DC. A comparison of spatial clustering and cluster detection
Authors’ information 9. Mfueni E, Devleesschauwer B, Aguirre AR, Malderen CV, Brandt PT, Ogutu techniques for childhood leukaemia incidence in Ohio, 1996–2003. Int J
This study explored whether there is spatial heterogene- IG is a senior lecturer in the Department of Geography Geospatial Sciences B, et al. True malaria prevalence in children under five: Bayesian estima- Health Geogr. 2007;6:13.
ity in the distribution of malaria, one of the diseases of and Earth Observation at the University of Zimbabwe and specialises in geo- tion using data of malaria household surveys from three subSaharan 35. Yamada I, Rogerson PA, Lee G. GeoSurveillance: a GIS-based system
global public health concern. This was achieved through spatial health i.e., application of GIS and remote sensing to understand human countries. Malar J. 2018;17:65. for the detection and monitoring of spatial clusters. J Geogr Syst.
and animal diseases in space. He currently leads the Geospatial research group 10. WHO. World malaria report 2016. Geneva: World Health Organisation; 2009;11:155–73.
the detection of spatial and space-time clusters using in the department. MDS is a senior lecturer in the Geography Geospatial Sci- 2016. 36. Robertson C, Nelson TA. Review of software for space-time disease
scan statistics. The results indicated that high risk areas ences and Earth Observation at the University of Zimbabwe specialising in the 11. Yakob L, Cameron M, Lines J. Combining indoor and outdoor methods surveillance. Int J Health Geogr. 2010;9:16.
for malaria are concentrated in the northern, eastern, application of GIS and remote sensing to various fields including health. MM for controlling malaria vectors: an ecological model of endectocide- 37. Wand H, Ramjee G. Targeting the hotspots: investigating spatial and
and GM are graduate students from the University of Zimbabwe with speciali- treated livestock and insecticidal bed nets. Malar J. 2017;11:1–13. demographic variations in HIV infection in small communities in South
and south-eastern part of the country. The results of this sations in geospatial health. JC is a lecturer in the College of Health Sciences 12. Sande S, Zimba M, Chinwada P, Masendu HT, Mberikunshe J, Makuwaza Africa. J Int AIDS Soc. 2010;13:41.
study could be used to design malaria control strategies and has special interest in community medicine and infectious diseases. JM is A. A review of new challenges and prospects for malaria elimination in 38. Tango T, Takahashi K. A flexible spatial scan statistic with a restricted likeli-
aimed at reducing malaria incidence in high risk areas the current director of the National Malaria Control Program in the Ministry of Mutare and Mutasa Districts. Zimbabwe Malar J. 2016;15:1. hood ratio for detecting disease clusters. Stat Med. 2012;31:4207–18.
Health and Child Care, Zimbabwe. 13. Sande S, Zimba M, Mberikunashe J, Tangwena A, Chimusoro A. Progress 39. Barro AS, Kracalik IT, Malania L, Tsertsvadze N, Manvelyan J, Imnadze P,
particularly those along border areas. In addition, the et al. Identifying hotspots of human anthrax transmission using three
towards malaria elimination in Zimbabwe with special reference to the
results could be used to guide optimal resource alloca- Funding period 2003–2015. Malar J. 2017;16:295. local clustering techniques. Appl Geogr. 2015;60:29–36.
tion by giving priority to the regions in greatest need. The No funding was received for this research. 14. WHO. Global technical strategy for malaria 2015. Geneva: World Health 40. Song C, Kulldorff M. Power evaluation of disease clustering tests. Int J
Health Geogr. 2003;2:9.
Organization; 2015a.
results of this study highlight the spatial heterogeneity in Availability of data and material 15. Alegana VA, Okiro EA, Snow RW. Routine data for malaria morbidity 41. Huang L, Pickle LW, Das B. Evaluating spatial methods for investigat-
malaria occurrence with several high-risk areas detected The statistical methods presented in this manuscript were implemented in a estimation in Africa: challenges and prospects. BMC Med. 2020;18:121. ing global clustering and cluster detection of cancer cases. Stat Med.
across the country. Based on this retrospective study, sig- freely downloadable software SaTScan version 9.4.2 available at (https ://www. 16. Mosha JF, Sturrock HJ, Greenwood BM, Sutherland CJ, Gadalla NB, Atwal 2008;27:5111–42.
satsc an.org/). The data used and/or analysed during the current study are S. Hot spot or not: a comparison of spatial statistical methods to predict 42. Kulldorff M. A spatial scan statistic. Commun Stat. 1997;26:1481–96.
nificant attention need to be directed to high risk areas available from the corresponding author on reasonable request. prospective malaria infections. Malar J. 2014;13:53. 43. Ndhlovu F, Ndhlovu DN, Chikerema SM, Masocha M, Nyagura M, Pfukenyi
as these may act as reservoirs for the current and future DM. Spatio-temporal patterns of clinical bovine dermatophilosis in
57
page number not for citation purpose
Downloaded from mednexus.org on [June 20, 2026]. For personal use only.

--- Page 14 ---
Gwitira et al. Infect Dis Poverty (2020) 9:146 Page 14 of 14 Wang and Tang Infect Dis Poverty (2020) 9:148
https://doi.org/10.1186/s40249-020-00770-8
Zimbabwe 1995–2014. Onderstepoort J Vet Res. 2017. https ://doi. 63. Bannister-Tyrrell M, Verdonck K, Hausmann-Muela S, Gryseels C, Ribera RESEARCH ARTICLE Open Access
org/10.4102/ojvr.v4184 i4101 .1386. JM, Grietens KP. Defining micro-epidemiology for malaria elimination:
44. Mabaso MLH, Vounatsou MP, Smith T. Towards empirical description of systematic review and meta-analysis. Malar J. 2017;16:164.
malaria seasonality in southern Africa: the example of Zimbabwe. Trop 64. UNDESA. Sustainable Development Goal 3: Ensuring Health Lives and
Perceived psychosocial health and its
Med Int Health. 2005;10:909–18. Promote Well-Being for All at All Ages. 2015: https ://susta inabl edeve
45. Dehnavieh R, Haghdoost A, Khosravi A, Hoseinabadi F, Rahimi H, lopme nt.un.org/sdg3. Accessed on 15 September 2019.
Poursheikhali A, et al. The District Health Information System (DHIS2): 65. Okello G, Molyneux S, Zakayo S, Gerrets R, Jones C. Producing routine
sociodemographic correlates in times of
a literature review and metasynthesis of its strengths and operational malaria data: an exploration of the micro-practices and processes shap-
challenges based on the experiences of 11 countries. Health Inf Manage ing routine malaria data quality in frontline health facilities in Kenya.
J. 2018;48:62–75. Malar J. 2019;18:420.
the COVID-19 pandemic: a community-based
46. ESRI. ArcGIS Desktop. Release 10.3. 2011, Environmental Systems 66. Byass P. Making sense of long-term changes in malaria. Lancet.
Research Institute: Redlands CA. 2008;372:1523–5.
47. USAID. President’s malaria initiative Zimbabwe: Malaria operational plan 67. Manyangadze T, Chimbari MJ, Gebreslasie M, Mukaratirwa S. Risk factors online study in China
FY 2017. Washington: USAID 2016. and micro-geographical heterogeneity of Schistosoma haematobium in
48. Rowe A, Kachur SP, Yoon SS, Lnych M, Sluster L, Steketee RW. Caution is Ndumo area, uMkhanyakude district, KwaZulu-Natal. South Africa Acta
required when using health facility-based data to evaluate the health Tropica. 2016;159:176–84.
impact of malaria control efforts in Africa. Malar J. 2009;8:209. 68. Saita S, Silawan T, Parker DM, Sriwichai P, Phuanukoonnon S, Sudathip P, Gan‑Yi Wang1 and Shang‑Feng Tang2,3*
49. Gerrets R. Charting the road to eradication: Health facility data and et al. Spatial heterogeneity and temporal trends in malaria on the Thai-
malaria indicator generation in rural Tanzania. In: Rottenburg R, editor. Myanmar Border (2012–2017): a retrospective observational study. Trop
The world of indicators: the making of governmental knowledge through Med Infect Dis. 2019;4:62.
quantification. Cambridge: Cambridge University Press; 2015. p. 36. 69. Xu X, Zhou G, Wang Y, Hu Y, Ruan Y, Fan Q, et al. Microgeographic hetero-
50. WHO. Global technical strategy for malaria elimination 2016–2030. geneity of border malaria during elimination phase, Yunnan Province,
Abstract
Geneva: World Health Organization; 2015b. China, 2011–2013. Emerg Infect Dis. 2016;22:8.
51. ZIMSTAT. Zimbabwe Population Census 2012. Harare: ZIMSTAT 2012. 70. Prashanthi DM, Manickiam B, Balasubramanian S. Use of of Remote Background: Coronavirus disease 2019 (COVID‑19) pandemic has been affecting people’s psychosocial health and
52. CSO. Zimbabwe National Population Census 2002. Harare: CSO 2002. Sensing and GIS for monitoring the Environmental factors associated
well‑being through various complex pathways. The present study aims to investigate the perceived psychosocial
53. ZIMSTAT. Zimbabwe Population Projections Thematic Report. Harare: with Vector-borne Disease (Malaria). Third International Conference on
ZIMSTAT 2015. Environment and Health. Chennai: Department of Geography. University health and its sociodemographic correlates among Chinese community‑dwelling residents.
54. Pfeiffer DU, Robinson TP, Stevenson M, Stevens KB, Rogers DJ, Clements of Madras and Faculty of Environmental Studies 2003.
Methods: This cross‑sectional survey was carried out online and using a structured questionnaire during April 2020.
AAC. Spatial analysis in epidemiology. New York: Oxford University Press; 71. Muchena G, Dube B, Chikodzore R, Pasipamire J, Murugasampillay S,
2008. Mberikunashe J. A review of progress towards sub-national malaria In total, 4788 men and women with the age range of 11–98 years from eight provinces in eastern, central and western
55. Poh-Chin L, Fun-Mun So KWC. Spatial epidemiological approaches in elimination in Matabeleland South Province, Zimbabwe (2011–2015): a China were included in the analysis. We adopted a tactical approach to capture three key domains of perceived psy‑
disease mapping and analysis. New York: CRC Press; 2009. qualitative study. Malar J. 2018;17:146.
chosocial health that are more likely to occur during a pandemic including hopelessness, loneliness, and depression.
56. Chowdhury AI, Abdullah AYM, Haider R, Alam A, Billah SM, Bari S, et al. 72. Adeola A, Ncongwane K, Abiodun G, Makgoale T, Rautenbach H, Botai J,
Analyzing spatial and space-time clustering of facility-based deliveries in et al. Rainfall trends and malaria occurrences in Limpopo Province, South Multiple regression method, binary logistic regression model and variance inflation factor (VIF) were used to conduct
Bangladesh. Trop Med Health. 2019;47:44. Africa. Int J Environ Res Publ Health. 2019;16:5156. data analysis.
57. Cheung YTD, Spittal MJ, Williamson MK, Tung SJ, Pirkis J. Application 73. SADC. SADC Malaria Elimination Eight Initiative: Annual Report 2019.
of scan statistics to detect suicide clusters in Australia. PLoS ONE. Windhoek: Elimination8 2019. Results: Respectively 34.8%, 32.5% and 44.8% of the participants expressed feeling more hopeless, lonely, and
2013;8(1):e54168. 74. Kamuliwo M, Chanda E, Haque U, Mwanza-Ingwe M, Sikaala C, Katebe- depressed during the pandemic. The percentage of all three indicators was comparatively higher among women
58. Kulldorff M. Commentary: geographical distribution of sporadic Sakala C, et al. The changing burden of malaria and association with
than among men: hopelessness (50.7% vs 49.3%), loneliness (52.4% vs 47.6%), and depression (56.2% vs 43.8%). Being
Creutzfeldt-Jakob disease in France. Int J Epidemiol. 2002;31:495–6. vector control interventions in Zambia using district-level surveillance
59. Chen J, Roth RE, Naito AT, Lengerich EJ, MacEachren AM. Geovisual data, 2006–2011. Malar J. 2013;12:437. married was associated with lower odds of loneliness among men (odds ratio [OR] 0.63, 95% CI: 0.45–0.90). Loneli‑
=
analytics to enhance spatial scan statistic interpretation: an analysis of US 75. Aamodt G, Samuelsen SO, Skrondal A. A simulation study of three meth- ness was negatively associated with smoking (OR 0.67, 95% CI: 0.45–0.99) and positively associated with drinking
Cervical cancer mortality. Int J Health Geogr. 2008;7:57. ods for detecting disease clusters. Int J Health Geogr. 2006;5:15. =
(OR 1.45, 95% CI: 1.04–2.02). Compared with those in the lowest income bracket (< CNY 10 000), men (OR 0.34,
60. Zhang W, Wang L, Fang L, Ma J, Xu Y, Jiang J, et al. Spatial analysis of = =
malaria in Anhui province, China. Malar J. 2008;7:206. 95% CI: 0.21–0.55) and women (OR 0.36, 95% CI: 0.23–0.56) in the highest level of annually housed income (> CNY
Publisher’s Note =
61. Liu Y, Wang X, Liu Y, Sun D, Ding S, Zhang B, et al. Detecting spatial-tem- 40 000) had the lowest odds of reporting perceived hopelessness (OR 0.35, 95% CI: 0.25–0.48). Smoking also showed
poral clusters of HFMD from 2007 to 2011 in Shandong Province, China. Springer Nature remains neutral with regard to jurisdictional claims in pub- =
PLoS ONE. 2013;8(5):e63447. lished maps and institutional affiliations. negative association with depression only among men (OR = 0.63, 95% CI: 0.43–0.91).
62. Gwitira I, Murwira A, Masocha M, Zengeya FM, Shekede MD, Chirenda J, Conclusions: More than one‑third of the participants reported worsening in the experience of hopelessness and
et al. GIS-based stratification of malaria risk zones for Zimbabwe. Geo-
loneliness, with more than two‑fifth of worsening depression during the pandemic compared with before the
carto Int. 2019;34:1163–76.
outbreak. Several socioeconomic and lifestyle factors were found to be associated with the outcome variables, most
notably participants’ marital status, household income, smoking, alcohol drinking, existing chronic conditions. These
findings may be of significance to treat patients and help them recover from the pandemic.
Ready to submit your research ? Choose BMC and benefit from:
• fast, convenient online submission *Correspondence: sftang2018@hust.edu.cn
• thorough peer review by experienced rese archers in your field 2 School of Medicine and Health Management, Tongji Medical College,
Huazhong University of Science and Technology, 13 Hangkong Road,
• rapid publication on acceptance
Wuhan 430030, Hubei, China
• support for research data, including large and complex data types Full list of author information is available at the end of the article
• gold Open Access which fosters wider collaboration and increased citations
• maximum visibility for your research: over 100M website views per year © The Author(s) 2020. Open Access This article is licensed under a Creative Commons Attribution 4.0 International License, which
permits use, sharing, adaptation, distribution and reproduction in any medium or format, as long as you give appropriate credit to the
At BMC, research is always in progress. original author(s) and the source, provide a link to the Creative Commons licence, and indicate if changes were made. The images or
other third party material in this article are included in the article’s Creative Commons licence, unless indicated otherwise in a credit line
Learn more biomedcentral.com/submissions to the material. If material is not included in the article’s Creative Commons licence and your intended use is not permitted by statutory
regulation or exceeds the permitted use, you will need to obtain permission directly from the copyright holder. To view a copy of this
licence, visit http://creati vecom mons .org/licens es/by/4.0/. The Creative Commons Public Domain Dedication waiver (http://creati veco
mmons .org/public domai n/zero/1.0/) applies to the data made available in this article, unless otherwise stated in a credit line to the data.
58
page number not for citation purpose
Downloaded from mednexus.org on [June 20, 2026]. For personal use only.