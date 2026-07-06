# Spatial–temporal clustering of malaria using routinely collected health facility data on the Kenyan Coast 

**Source PDF:** `Spatial–temporal clustering of malaria using routinely collected health facility data on the Kenyan Coast .pdf`  
**Path:** `papers/spatial-analysis/Spatial–temporal clustering of malaria using routinely collected health facility data on the Kenyan Coast .pdf`  

---

--- Page 1 ---
Kamau et al. Malar J (2021) 20:227 Malaria Journal
https://doi.org/10.1186/s12936-021-03758-3
RESEARCH Open Access
Spatial–temporal clustering of malaria
using routinely collected health facility data
on the Kenyan Coast
Alice Kamau1,3* , Grace Mtanje1, Christine Mataza1,2, Philip Bejon1,3 and Robert W. Snow1,3
Abstract
Background: The over-distributed pattern of malaria transmission has led to attempts to define malaria “hotspots”
that could be targeted for purposes of malaria control in Africa. However, few studies have investigated the use of
routine health facility data in the more stable, endemic areas of Africa as a low-cost strategy to identify hotspots. Here
the objective was to explore the spatial and temporal dynamics of fever positive rapid diagnostic test (RDT) malaria
cases routinely collected along the Kenyan Coast.
Methods: Data on fever positive RDT cases between March 2018 and February 2019 were obtained from patients
presenting to six out-patients health-facilities in a rural area of Kilifi County on the Kenyan Coast. To quantify spatial
clustering, homestead level geocoded addresses were used as well as aggregated homesteads level data at enumera-
tion zone. Data were sub-divided into quarterly intervals. Kulldorff’s spatial scan statistics using Bernoulli probability
model was used to detect hotspots of fever positive RDTs across all ages, where cases were febrile individuals with a
positive test and controls were individuals with a negative test.
Results: Across 12 months of surveillance, there were nine significant clusters that were identified using the spatial
scan statistics among RDT positive fevers. These clusters included 52% of all fever positive RDT cases detected in 29%
of the geocoded homesteads in the study area. When the resolution of the data was aggregated at enumeration zone
(village) level the hotspots identified were located in the same areas. Only two of the nine hotspots were temporally
stable accounting for 2.7% of the homesteads and included 10.8% of all fever positive RDT cases detected.
Conclusion: Taking together the temporal instability of spatial hotspots and the relatively modest fraction of the
malaria cases that they account for; it would seem inadvisable to re-design the sub-county control strategies around
targeting hotspots.
Keywords: Malaria, Hotspots, Spatial clusters, Spatial–temporal dynamics, Heterogeneity
Background often over-distributed in space and time driven by varia-
The Pareto principle states that for many outcomes tions in local vector ecology, host susceptibility to infec-
approximately 80% of consequences come from only 20% tions or outcomes of infections [1, 4–12].
of the causes. The concept was developed under eco- The concept that malaria is over-distributed in space
nomic theory but has been applied to models of infec- has led to attempts to define “hotspots” in more stable,
tious disease epidemiology [1–3]. In malaria, events are endemic areas of Africa [13]. The active detection of
cases or infection linked to household coordinates of
*Correspondence: akamau@kemri-wellcome.org population censuses provides valuable insights on the
1 KEMRI-Wellcome Trust Research Programme, Nairobi, Kenya extent and frequency of definable hotspots of potential
Full list of author information is available at the end of the article
disproportionately high burden/clustered households.
© The Author(s) 2021. This article is licensed under a Creative Commons Attribution 4.0 International License, which permits use, sharing,
adaptation, distribution and reproduction in any medium or format, as long as you give appropriate credit to the original author(s) and
the source, provide a link to the Creative Commons licence, and indicate if changes were made. The images or other third party material
in this article are included in the article’s Creative Commons licence, unless indicated otherwise in a credit line to the material. If material
is not included in the article’s Creative Commons licence and your intended use is not permitted by statutory regulation or exceeds the
permitted use, you will need to obtain permission directly from the copyright holder. To view a copy of this licence, visit http:// creat iveco
mmons. org/ licen ses/ by/4. 0/. The Creative Commons Public Domain Dedication waiver (http:// creat iveco mmons. org/ publi cdoma in /
zero/1. 0/) applies to the data made available in this article, unless otherwise stated in a credit line to the data.

--- Page 2 ---
Kamau et al. Malar J (2021) 20:227 Page 2 of 13
Under stable endemic settings that remain under the Health facility‑based passive surveillance of fever
control phases, passive case detection (PCD) data from infections
routine health information systems is all that is typi- At each facility, the study included records of all
cally available to define households or local areas with patients 6 months of age that sought treatment
≥
the highest burdens. However, the use of routine health between March 2018 to February 2019 with a history
facility data for ‘hotspots’ detection remains underuti- of fever in the last 24 h or a measured axillary tempera-
lized in these areas due to their limitations in terms of ture 37.5 °C, hereafter referred as febrile patients. All
≥
representativeness and completeness [14]. Hence, far febrile patients were tested using a malaria rapid diag-
fewer studies have investigated the potential of passive nostic test (RDT) (CareStart™) to detect HRP2 specific
case detection in health facilities to identify hotspots to Plasmodium falciparum. If the RDT results were
[10, 15–21]. positive the patient received appropriate treatment as
As we move towards improving the use of routine data, per the Government of Kenya guidelines for malaria-
the use of spatial tools to detect malaria hotspots (i.e. sin- case management [24]. During the surveillance period,
gle villages or groups of households within villages with malaria test positivity rate (TPR) did not differ during
increased risk of malaria transmission) using routinely the wet (42.7%) versus dry season (43.5%) (p 0.173)
=
collected data would increase the value of local health [22].
information systems at district levels. Previous stud-
ies have tended to use geospatial data at the household
level, which is not available in routine reporting, where Spatial resolution
location data is usually restricted to village or enumera- To quantify spatial clustering of passively detected cases,
tion zone. Here the objective was to explore the spatial two spatial resolutions were considered. All health facil-
and temporal dynamics of fever positive rapid diagnostic ity attendees included in this study were linked to the
test (RDT) malaria cases routinely collected in six health KHDSS homestead level geospatial coordinates in order
facilities along the Kenyan Coast. to assess heterogeneity at very fine spatial scale (i.e. the
gold standard methodology). However, geospatial data at
this level would not be available routinely in health facili-
Methods ties. Since patient records generally do not include actual
Study area residential addresses, homesteads level data was aggre-
This is a secondary analysis of data collected from six gated at enumeration zone (EZ) (equivalent to village)
health facilities located in the southern part of Kilifi in order to explore the feasibility of hotspots detection
Health and Demographic Surveillance System (KHDSS) using village level information. The geographic coordi-
located along the Kenyan coast (Fig. 1). The study area nates of the centroid of each EZ was used.
has been described in detail elsewhere [22, 23]. Briefly,
malaria transmission is perennial but relatively higher
during the long (April-June) and short (October-Decem- Statistical analysis
ber) rains with an infection prevalence of approximately The focus of the analysis was across all ages ( 6 months)
≥
10% detectable among residents of all ages [22]. In this as these data are available from existing DHIS2 platforms
area, 29 peripheral private and public health facilities and because TPR across all ages was strongly associated
and one referral hospital (Kilifi county hospital) provide with infection prevalence in the community, suggest-
health care to the population. The six health facilities ing that passive surveillance does provide a reflection of
were selected on the basis that they were public health infection prevalence in the community [22]. Since geo-
facilities and were more likely to comply with govern- spatial coordinates (longitude and latitude) of home-
ment policies on diagnosis, treatment and participate in steads tended to have small number of patients resulting
routine reporting of data. They also had a high burden of in higher standard errors and therefore less precise TPR,
patients (a minimum of 10 patients per day) and were not smoothing was performed for visualization purposes
part of ongoing active surveillance. A catchment area for only on the maps. TPR was calculated as a simple propor-
the health facilities was defined as the enumeration zones tion of RDT positive homestead members within a radius
(EZs) within a 2 km radius of each health facility. The of < 1 km around each index patient. To explore different
catchment areas were estimated as the boundary within smoothed estimates of TPR, the radius was also altered
which the probability of attending these health facilities at < 0.2 km and < 0.5 km. TPR for each EZ was calculated
was relatively high. The area included an enumerated as the number of positive diagnostic tests as a proportion
mid-year population of 72,560 in 2018 and 36 EZs con- of the total tests performed among febrile patients aggre-
sisting of 9,596 homesteads. gated at the EZ level.

--- Page 3 ---
K amau et al. Malar J (2021) 20:227 Page 3 of 13
Fig. 1 Map showing the location of the health facilities and their catchment areas

--- Page 4 ---
Kamau et al. Malar J (2021) 20:227 Page 4 of 13
Local spatial cluster detection Temporal stability of hotspots
Local clustering detection was performed using Mar- There were no clear patterns between seasonality and
tin Kulldorff’s spatial scan statistic (SaTScan) [25]. The TPR [25]. Therefore, to test for temporal stability of
raw data, and not smoothed TPRs, were used for hot- spatial clusters, the data was sub-divided into quar-
spot detection. SaTScan imposes circular scanning win- terly intervals i.e. March to May 2018 (Q1), June to
dows across a study area with radius varying from zero August 2018 (Q2), September to November 2018 (Q3)
to a maximum of 50% of the population in the sampling and December 2018 to February 2019 (Q4). The spatial
frame. An elliptic window shape can be used as an alter- analysis was repeated for each interval rather than a spa-
native to the circular window, in which case a set of tial–temporal because the size of the database made sec-
ellipses with different shapes and angles are used as the ondary clusters very likely and the option for analysing
scanning window. This may provide higher power for true secondary clusters is not available for spatial–temporal
clusters that are elliptical in shape, but lower power for analysis but is validated for spatial-only analysis [26].
circular or other very compact clusters [25]. Each scan- Spatial cluster analysis was performed using SaTScan™
ning window is evaluated as a potential cluster by the cal- software version 9.6 (Information Management Services
culation of a log likelihood ratio (LLR) test statistic based Inc, Silver Spring, Maryland, USA). All other statisti-
on the observed, expected and total number of cases. cal analyses were performed in Stata, version 13 (Stata
To test the null hypothesis of complete spatial random- Corporation, College Station, TX) and R version 3.6.1 (R
ness, SaTScan employs Monte Carlo simulations where Core Team (2019), Vienna, Austria). Maps of hotspots
for each simulation run, the observed cases are randomly were produced in R.
permuted in space across the entire set of data locations.
The observed log likelihood is then compared with the
Results
simulated log likelihoods to determine significance. The
statistical significance of a cluster (or ‘‘hotspot’’) is then Description of the spatial data
evaluated taking into account the multiple tests for the Overall, the study comprised of 28,134 febrile health
many potential cluster locations and sizes assessed. facility attendees across all ages in 5,323 geocoded home-
Kulldorff’s spatial scan statistics using Bernoulli proba- steads between March 2018 and February 2019. Among
bility model was used to detect hotspots of fever positive all febrile patients, 12,143 (43%) tested positive for
RDTs, where cases were febrile individuals with a positive malaria using RDT. The number of febrile health facili-
test and controls were individuals with a negative test. ties attendees varied across the quarterly intervals rang-
The maximum spatial cluster size was set at a radius of ing between 4,284 and 9,119 (Table 1). The RDT fever
3 km. For each detected hotspot, a relative risk (RR) was test positivity rate was lowest between March and May
computed. The RR is the magnitude of the risk of malaria 2018 at 39% (1,651 cases) and highest between June and
for individuals residing within the hotspot compared to August 2018 at 45% (4,096 cases) (Table 1). A similar test
the estimated risk in the surrounding area. The circular positivity rate (45%) was observed between December
windows were used in line with common practice. They 2018 and February 2019 (Table 1). The overall smoothed
are computationally efficient, and it is easier to determine 1 km TPR ranged between 0% and 89.3% in 5,323 geo-
hotspot properties that are of interest (Radius, RR and coded homesteads located in 36 EZs (Additional file 1).
significance). The most likely cluster (hereafter referred The smoothed TPR was comparable when the radial
to primary cluster) was identified based on the maximum distance was altered which ranged between 0 and 100%
log likelihood ratio. In addition, other clusters with sta- for both 0.2 km and 0.5 km (Additional file 1). The 1 km
tistically significant log likelihood values were defined as radius was chosen over other radial distances as ‘noise’
secondary clusters. was minimized with greater stability.
Table 1 Summary of data routinely collected at six health facilities stratified by quarterly intervals
Summary measures March–may 2018 (Q1) June–august 2018 (Q2) September– December 2018– Overall
november 2018 february 2019 (Q4)
(Q3)
Number of geo-coded home- 2290 3532 3368 2890 5323
steads
Number of attendees (N) 4284 9119 8396 6335 28,134
Number of cases (n) 1651 4096 3554 2842 12,143
TPR, (95% CI) 38.5% (37.1%, 40.0%) 44.9% (43.9%, 45.9%) 42.3% (41.3%, 43.4%) 44.9% (43.6%, 46.1%) 43.2% (42.6%, 43.7%)

--- Page 5 ---
K amau et al. Malar J (2021) 20:227 Page 5 of 13
Spatial hotspot detection age groups (Fig. 2). The primary cluster with a radius of
Across 12 months of surveillance, there were nine sig- 3.0 km was detected in the west of the study area among
nificant clusters that were identified using the purely patients attending Chasimba health centre, composed of
spatial scan statistics among RDT positive fevers of all 289 (5.4%) homesteads accounting for 16.0% (1939) of all
Fig. 2 Spatial distribution of smoothed mean TPR across 12 months of surveillance at homesteads level aggregated at 1 km radius and the spatial
hotspots of fever positive RDT cases, analysed without smoothing. Each plotted point represents an individual homestead, where red shading
indicates high TPR and green shading indicates lower TPR. The large black circles indicate the significant hotspots (analysed without smoothing)
where 1 indicates the primary cluster located in Chasimba health centre and clusters 2–9 are the secondary hotspots located in Ziani, Kadzinuni,
Bomani and Jaribuni dispensaries

--- Page 6 ---
Kamau et al. Malar J (2021) 20:227 Page 6 of 13
fever test positive cases detected (cluster 1 in Fig. 2). The second quarter. The fourth quarter showed a similar pat-
homesteads within this cluster were 1.75 (p < 0.001) times tern to what was observed in the first and second quarter.
more at risk of testing positive for malaria than home- The highest-risk hotspot was detected in the same loca-
steads outside the cluster. In addition, secondary hot- tion with a RR of 1.75 (p < 0.001) and represented 7.4% of
spots were identified among patients attending three of the homesteads and accounted for 18.9% of all fever test
the five remaining health facilities (i.e. Ziani (cluster 2, 3, positive cases in that period (Fig. 4).
and 9), Kadzinuni (cluster 4), Bomani (cluster 5) and Jar- There were several secondary hotspots identified across
ibuni (cluster 6 and 7) dispensaries, Fig. 2). There were no all the quarterly intervals (Table 2 and Fig. 4). The sec-
clusters detected using data obtained from Mavueni dis- ondary clusters were characterized in Jaribuni, Kadzinuni
pensary. Cumulatively, in both the primary and second- and Bomani dispensaries. However, the spatial location
ary hotspots, there were 1520/5323 (28.6%) homesteads and size varied across the intervals. There were neither
that accounted for 51.8% (6293/12,143) of all fever test primary nor secondary clusters detected using data
positive cases detected in the study area. When data were obtained from Mavueni dispensary. Cumulatively, all the
aggregated at EZ level, a spatial resolution equivalent to hotspots detected in the first quarter represented 17.7%
what might be available through routine health informa- (405/2290) of all the homesteads accounting for 41.7%
tion systems, the primary and secondary hotspots iden- (689/1651) of all fever test positive cases detected. In
tified were generally located in the same areas as those the second quarter 27.3% (965/3532) of the homesteads
identified using the homestead level data (Fig. 3). accounted for 45.0% (1843/4096) of the case, in the third
quarter 32.6% (1098/3368) of the homesteads accounted
Temporal stability of hotspot detection for 56.0% (1988/3554) of the cases and in the fourth
To test for temporal stability of spatial clusters, the data quarter 25.3% (732/2890) of the homesteads accounted
was sub-divided into quarterly intervals. When the spa- for 44.3% (1259/2842) of the cases detected (Table 2).
tial analysis was repeated for each quarter, several hot- In the two temporally stable hotspots, 142/5323 (2.7%)
spots were detected. The relative risk of infection within homesteads were consistently identified in these hot-
these clusters was significantly higher in comparison to spots across the four-time intervals accounting for 10.8%
the population outside of these clusters (Table 2). The (1311/12,143) of all fever test positive cases detected,
radius of the spanning windows ranged from 0.66 km to 353 (6.6%) were identified three times and accounted
3.0 km and four, six, four and five clusters were detected for 17.5% (2122) of the cases, 218 (4.1%) identified twice
in the first, second, third and four quarters, respectively accounting for 5.3% (643) of the cases and 306 (5.8%)
(Table 2). These spatial clusters represented between were identified once accounting for 9.0% (1095) of the
17.7% (405) and 32.6% (1,098) of all the geocoded home- cases while 4,304 (80.9%) homesteads were in the unsta-
steads (Table 2). Only two clusters seemed temporally ble hotspots or were never identified in a hotspot area.
stable across the quarterly intervals (Fig. 4). Again, when data was aggregated at EZ (village) level,
The primary cluster in the first quarter was 2.9 km the primary and secondary hotspots identified across the
radius west of the study area, composed of 106 (4.6%) quarterly intervals (Fig. 5) were roughly located in the
homesteads accounting for 17.3% (287) of all fever test same areas as those identified using the homestead level
positive cases identified in that period. The homesteads data (Fig. 4).
within this cluster attended Chasimba health centre and
Discussion
were 2.29 (p < 0.001) times more at risk of testing posi-
tive for malaria than homesteads outside the cluster. In The results presented demonstrate that information
the second quarter, the primary cluster had the highest- obtained through routine testing of febrile patients for
risk (1.66; p < 0.001) and overlapped with the cluster malaria can identify spatial and temporal heterogenei-
detected in the first quarter. This cluster represented ties of malaria risk at very fine spatial scales, where
8.5% of the homesteads accounting for 14.2% of all fever homestead coordinates are available and importantly at
test positive cases (Table 2). The primary cluster detected lower resolutions where village names might be available
in the third quarter had a radius of 2.28 km with a risk (Fig. 2, 3).
of 1.62 (p < 0.001), but was located in the central part of Fever positive RDTs cases exhibited spatial heteroge-
the study area among patients attending Ziani dispen- neity as evidenced by the existence of statistically sig-
sary. This cluster represented 15.9% of the homesteads nificant (p < 0.05) spatial clusters in groups of homesteads
and 22.9% of all fever test positive cases detected in among residence of six catchment areas of six health
that period (Table 2). The cluster with the highest risk facilities. Across the 12-month surveillance period, these
(RR 1.75; p < 0.001) in the third quarter was in a similar clusters included 52% of all fever positive RDT cases
=
location as the primary clusters detected in the first and detected in 29% of the geocoded homesteads in the study

--- Page 7 ---
K amau et al. Malar J (2021) 20:227 Page 7 of 13
Fig. 3 Spatial pattern of annual malaria RDT positivity rate by enumeration zones and spatial hotspots of fever test positive cases. The red shading
in the choropleth map indicates very high TPR ( 60%), brown indicated high TPR (40–59%), dark green is low-moderate TPR regions (20–39%) and
≥
light green shading indicating lower TPR (< 20%). The large black circles indicate the location of high-risk clusters detected by purely spatial scan
statistics using geographic coordinates of the centroid of each EZ. Cluster 1 indicates the primary cluster located in Chasimba health centre and
clusters 2—9 are the secondary hotspots located in Ziani (clusters 2 and 3), Kadzinuni (clusters 4 and 8) and Bomani (cluster 6) dispensaries. The
additional secondary clusters 5, 7 and 9 were located in Chasimba health centre
area. In addition, the power to detect clusters of fever impacted the ability to more accurately determine the
positive RDT cases did not diminish when data were spa- exact spatial location of the clusters.
tially aggregated at EZ (village) level (Fig. 3) as demon- These results support the hypothesis that malaria tends
strated previously [27]. However, aggregations negatively to significantly cluster within certain geographic units [1,
5–7, 10, 11, 20, 21, 28].

--- Page 8 ---
Kamau et al. Malar J (2021) 20:227 Page 8 of 13
Table 2 Spatial clusters of fever positive RDT cases detected by SaTScan, ordered from the cluster with the highest LLR, stratified by
quarterly intervals
Period Cluster order Radius (km) Number of Cumulative Expected cases Number of Cumulative RR p‑value
cases in cluster cases/total HMs in cluster HMs/total
(n) cases (n) HMs
Q1 1 2.90 287 287/1651 139.12 106 106/2290 2.29 < 0.001
2 2.31 270 557/1651 174.58 216 322/2290 1.65 < 0.001
3 1.13 44 601/1651 21.2 23 345/2290 2.11 < 0.001
4 0.66 88 689/1651 59.74 60 405/2290 1.50 0.03
Q2 1 3.00 583 583/4096 371.51 220 220/3532 1.66 < 0.001
2 1.72 289 872/4096 197.21 143 363/3532 1.50 < 0.001
3 2.09 363 1235/4096 270.88 227 590/3532 1.37 < 0.001
4 2.52 103 1338/4096 64.69 40 630/3532 1.61 < 0.001
5 2.49 222 1560/4096 163.97 84 714/3532 1.37 < 0.001
6 2.32 283 1843/4096 229.1 251 965/3532 1.25 0.02
Q3 1 2.28 815 815/3554 550.29 546 546/3368 1.62 < 0.001
2 2.78 503 1318/3554 306.47 177 723/3368 1.75 < 0.001
3 2.97 537 1855/3554 400.44 306 1029/3368 1.40 < 0.001
4 1.24 133 1988/3554 89.74 69 1,098/3368 1.50 < 0.001
Q4 1 2.75 538 538/2842 334.22 216 216/2890 1.75 < 0.001
2 1.51 226 764/2842 157.47 188 404/2890 1.47 < 0.001
3 1.74 134 898/2842 84.34 74 478/2890 1.62 < 0.001
4 1.82 247 1145/2842 183.04 178 656/2890 1.38 < 0.001
5 2.70 114 1259/2842 73.12 76 732/2890 1.58 < 0.001
When the temporal stability of the hotspots was exam- transmission periods [19]. In areas of moderate malaria
ined, the hotspots varied greatly across the intervals transmission in coastal Kenya [10, 17], very low transmis-
(Fig. 4). The clusters of fever positive RDT cases moved sion in a highland area of Kenya [21] and Nanoro DSS,
in space across the quarterly intervals and often did not Burkina Faso [20], hotspots of malaria were not con-
recur in the same location. This has also been noted in sistently identified over time. At much lower transmis-
other clustering studies [10, 20, 21]. Only two temporally sion health facility sites, authors were unable to identify
stable hotspots were identified with 2.7% of the home- any statistically significant clustering of cases [31, 32],
steads consistently located in these areas across all the although this may reflect diminished power due to the
intervals and included 10.8% of all fever positive RDT lower number of cases at lower transmission, as meta-
cases detected. analysis suggests that the effect size of clustering of cases
Most studies that have mapped the spatial distribu- becomes more marked at lower transmission [13].
tion of malaria burden have relied upon surveys of well- The use of passively collected routine health facility
defined demographic and spatial distributions of the data does offer opportunities to detect clusters down to
at-risk population [6, 10, 17, 20, 21, 26, 29, 30]. Few stud- the village level at an affordable cost. However, appro-
ies have examined the use of routine PCD data in defin- priately structured and defined health facility data will
ing clusters of disease risks [10, 15–21, 31, 32]. Of these be needed. In many areas, routinely collected health
PCD studies, variable patterns of spatial clustering have facility data generally do not include accurate residen-
been reported. Some studies support consistent hot- tial address. Therefore, to tap the full potential of these
spots [19, 33] while others suggest greater variability [10, data, it will be important to refine the current surveil-
17, 20, 21]. For example, in a highland area in Kenya the lance tools such that they have the potential of collect-
risk of malaria was consistently higher between 2001 and ing information at sufficiently precise scales (at individual
2004 among individuals living in a hotspot area however, level and ‘village’ scales). Closing these gaps could result
the number of households within the cluster varied and in health information systems that have the potential of
included between 29.3% and 49.3% of all cases detected becoming scalable, integral, and sustainable components
[33]. In Ouagadougou, Burkina Faso the location of of control programmes, which can then target interven-
clusters identified as high risk varied little across three tions to clusters of elevated risk [18, 21].

--- Page 9 ---
K amau et al. Malar J (2021) 20:227 Page 9 of 13
Fig. 4 Spatial distribution of smoothed mean TPR across all ages at homesteads level aggregated at 1 km radius and the spatial hotspots of fever
positive RDT cases stratified into quarterly monthly periods, analysed without smoothing. Each plotted point represents an individual homestead,
where red shading indicating high TPR and green shading indicating lower TPR. The large black circles indicate the significant hotspots (analysed
without smoothing) where 1 indicates the primary cluster and clusters 2–6 are the secondary hotspots

--- Page 10 ---
Kamau et al. Malar J (2021) 20:227 Page 10 of 13
Fig. 5 Spatial pattern of annual malaria RDT positivity rate by enumeration zones and spatial hotspots of fever test positive cases stratified into
quarterly monthly periods. The red shading in the choropleth map indicates very high TPR ( 60%), brown indicated high TPR (40–59%), dark green
≥
is low-moderate TPR regions (20–39%) and light green shading indicating lower TPR (< 20%). The large black circles indicate the location of high-risk
clusters detected by purely spatial scan statistics using geographic coordinates of the centroid of each EZ. Cluster 1 indicates the primary cluster
located and clusters 2–7 are the secondary hotspots

--- Page 11 ---
K amau et al. Malar J (2021) 20:227 Page 11 of 13
Hotspot-targeted interventions have been hypothesized using records of all cases (Additional file 2). Although
to be a highly efficient method of reducing malaria trans- Kulldorff’s scan statistic was successfully used to detect
mission not only inside these hotspots but also in adja- circular clusters, it may ignore more subtle small-scale
cent areas [7, 10]. While biologically plausible, there has spatial clusters that do not fit within circular windows
been mixed evidence to support this concept. For exam- [38, 39]. Arguably, clusters that require specific window
ple, a trial conducted in western Kenya failed to observe shapes are relatively subtle and therefore unlikely to be of
any sustained reduction in transmission [34]. Despite primary importance to routine malaria control. Many of
achieving high coverage of interventions in hotspot the limitations of this study would apply to routine health
areas, the interventions resulted in a modest and tran- facility data in many settings, and this study was set out
sient reduction in transmission inside targeted hotspots to test the utility of such data for hotspot detection.
and failed to influence malaria transmission dynamics
outside the targeted areas [34]. In a more recent study in
Conclusion and programme implications
Rufiji District, southern Tanzania, the implementation of
In this study, approximately a third of the homesteads
a locally tailored surveillance-response strategy contrib-
in the study area fell within identified hotspots and
uted convincingly to the reduction of malaria burden in
accounted for half of all health facility fever positive
hotspot villages (with the highest malaria incidence ratio)
RDTs cases. These hotspots varied over time, with only
using health facility-based data [35]. This study offered
two temporally stable hotspots which accounted for
the first example of surveillance as an intervention in
10.8% of malaria cases in the 2.7% of homesteads.
areas with high malaria burden, which is in line with
The operational question is whether these areas are
the current World Health Organization-recommended
detectable with routine data and, if so, whether they are
strategies for district-level malaria information systems
‘hot enough’ to re-design district level control strategies
[35–37].
from one of universal coverage of interventions, assum-
ing no heterogeneity, to one of a more tailored, nuanced
Limitations
approach based on local data. The temporal instabil-
The data presented here does not represent the uni- ity of the hotspots suggests that the use of local data
verse of all the health facilities in the study area, febrile would require real-time analysis and intervention. The
patients may have elected to use home-based treatment, complexity of these analyses in time and space suggests
private facilities or formal health services more distal to that hotspot-targeted interventions may at this stage be
their home. The data do however represent information unnecessary in this part of Kilifi county.
from busy public health facilities and were used here to The results presented continue to demonstrate that
demonstrate the potential value of information obtained information obtained through routine testing of febrile
through routine testing of febrile patients for malaria in patients for malaria can describe local malaria epide-
describing the local malaria epidemiology at fine spatial miology at fine spatial scales. The challenge remains
scales. The spatial and temporal coverage of observa- to develop programmatically affordable and scalable
tions in this study is likely to have had an impact on the approaches using routine data that allows for the identi-
stability of the hotspots detected. However, PCD data fication of local spatial heterogeneity to consider targeted
needs analysis over short temporal resolutions to insti- supplementary control efforts.
gate immediate intervention requiring real-time analy-
sis. In the present analysis, hotspots stability was based
Abbreviations
on the fraction of homesteads that fell within clusters
RDT: Rapid diagnostic test; KHDSS: Kilifi health and demographic surveil-
that occurred across all the four-time intervals. Lack of lance system; EZ: Enumeration zones; TPR: Test positivity rate; SaTScan: Martin
longer-term data in this study limits the ability to exam- Kulldorff’s spatial scan statistic; LLR: Log likelihood ratio; RR: relative risk; PCD:
Passive case detection; WHO: World Health Organization; HRP2: Histidine-rich
ine stability of hotspots beyond a year. It is possible that
protein 2; DHIS2: District health information system version 2; DSS: Demo-
the spatial heterogeneity observed may have been due to graphic surveillance syste.
measurement bias of how fever positive RDTs cases were
defined. For example, there is a possibility that a fever test Supplementary Information
positive case was from a single infectious bite or repeated The online version contains supplementary material available at https:// doi.
inoculations within the same individual because all cases org/ 10. 1186/ s12936- 021- 03758-3.
testing RDT positive including re-attendance were used.
To evaluate the degree of potential measurement bias as Additional file 1: Panel A shows the distribution of yearly smoothed
mean TPR aggregated at a 1 km radius for all ages. Panel b shows the
an alternative explanation, SaTScan analysis was rerun
distribution of yearly smoothed mean TPR aggregated at a 0.5 km radius
using records of first cases only of RDT positive patients.
The results were generally similar to the results obtained

--- Page 12 ---
Kamau et al. Malar J (2021) 20:227 Page 12 of 13
Author details
for all ages. Panel c shows the distribution of yearly smoothed mean TPR 1 KEMRI-Wellcome Trust Research Programme, Nairobi, Kenya. 2 Ministry
aggregated at a 0.2 km radius for all ages. of Health, Kilifi County Government, Kilifi, Kenya. 3 Centre for Tropical Medicine
Additional file 2: Spatial distribution of smoothed mean TPR across all and Global Health, Nuffield Department of Clinical Medicine, University
ages using records of first cases only of RDT positive patients at home- of Oxford, Oxford, UK.
steads level aggregated at 1 km radius, the spatial hotspots of fever test
positive cases and the location of the health facilities. Received: 1 February 2021 Accepted: 9 May 2021
Acknowledgements
We are grateful to the study team fieldworkers, sub-county health manage-
ment teams, dispensary health committees, and KEMRI community repre- References
sentatives’ teams for the support during data collection in the health facilities. 1. Woolhouse MEJ, Dye C, Etard JF, Smith T, Charlwood JD, Garnett GP, et al.
We are specifically grateful to Benjamin Tsofa for his support during the imple- Heterogeneities in the transmission of infectious agents: implications for
mentation phase of this study, and to Janet Musembi and Omar Ngoto for the the design of control programs. Proc Natl Acad Sci USA. 1997;94:338–42.
clinical support of the study. We would also like to appreciate David Walumbe, 2. Galvani AP, May RM. Dimensions of superspreading. Nature.
Mark Otiende and David Amadi for their assistance with DSS related queries 2005;438:293–5.
and to Edward Mundia for developing the data entry systems. This paper is 3. Lloyd-Smith JO, Schreiber SJ, Kopp PE, Getz WM. Superspreading
published with the permission of the director of KEMRI. This research was and the effect of individual variation on disease emergence. Nature.
funded in whole by the Wellcome Trust [103602 and 212176]. For the purpose 2005;438:355–9.
of Open Access, the author has applied a CC-BY public copyright licence to 4. Carter R, Mendis KN, Roberts D. Spatial targeting of interventions against
any author accepted manuscript version arising from this submission. malaria. Bull World Health Organ. 2000;78:1401–11.
5. Gaudart J, Poudiougou B, Dicko A, Ranque S, Toure O, Sagara I, et al.
Authors’ contributions Space-time clustering of childhood malaria at the household level: a
AK oversaw the implementation of field studies, analysed and interpreted dynamic cohort in a Mali village. BMC Public Health. 2006;6:286.
the data and drafted the manuscript. GM and CM coordinated the data 6. Bousema T, Drakeley C, Gesase S, Hashim R, Magesa S, Mosha F, et al.
collection process for the field studies. AK, PB and RWS conceived the study, Identification of hot spots of malaria transmission for targeted malaria
reviewed and revised the manuscript. All authors read and approved the final control. J Infect Dis. 2010;201:1764–74.
manuscript. 7. Bousema T, Griffin JT, Sauerwein RW, Smith DL, Churcher TS, Takken W,
et al. Hitting hotspots: spatial targeting of malaria for control and elimina-
Funding tion. PLoS Med. 2012;9:e1001165.
This work was supported through support to RWS as part of his Wellcome 8. Sturrock HJ, Hsiang MS, Cohen JM, Smith DL, Greenhouse B, Bousema
Trust Principal Fellowship (103602 and 212176) and support to AK through T, et al. Targeting asymptomatic malaria infections: active surveillance in
the DELTAS Africa Initiative [DEL-15–003]. The DELTAS Africa Initiative is an control and elimination. PLoS Med. 2013;10:e1001467.
independent funding scheme of the African Academy of Sciences (AAS)’s 9. Mosha JF, Sturrock HJ, Greenwood B, Sutherland CJ, Gadalla NB, Atwal
Alliance for Accelerating Excellence in Science in Africa and supported by the S, et al. Hot spot or not: a comparison of spatial statistical methods to
New Partnership for Africa’s Development Planning and Coordinating Agency predict prospective malaria infections. Malar J. 2014;13:53.
with funding from the Wellcome Trust [107769] and the UK government. All 10. Bejon P, Williams TN, Nyundo C, Hay SI, Benz D, Gething PW, et al. A micro-
authors are grateful to the support of the Wellcome Trust to the Kenya Major epidemiological analysis of febrile malaria in Coastal Kenya showing
Overseas Programme (203077). The funders had no role in study design, data hotspots within hotspots. Elife. 2014;3:e02130.
collection and analysis, decision to publish, or preparation of the manuscript. 11. Stresman GH, Mwesigwa J, Achan J, Giorgi E, Worwui A, Jawara M, et al.
Do hotspots fuel malaria transmission: a village-scale spatio-temporal
Availability of data and materials analysis of a 2-year cohort study in the Gambia. BMC Med. 2018;16:160.
Data cannot be shared publicly because it includes homestead level coor- 12. Shaffer JG, Touré MB, Sogoba N, Doumbia SO, Gomis JF, Ndiaye M, et al.
dinates as an essential component, and these are personal identifiable data. Clustering of asymptomatic Plasmodium falciparum infection and the
Data that support the findings of this study are available from the KEMRI Insti- effectiveness of targeted malaria control measures. Malar J. 2020;19:33.
tutional Data Access/Ethics Committee. Details of the guideline can be found 13. Mogeni P, Omedo I, Nyundo C, Kamau A, Noor A, Bejon P. Effect of
in the KEMRI-Wellcome data sharing guidelines (https:// kemri- wellc ome. org/ transmission intensity on hotspots and micro-epidemiology of malaria in
about- us/# Child Verti calTab_ 15). Access to data is provided via the KEMRI sub-Saharan Africa. BMC Med. 2017;15:121.
Wellcome Data Governance Committee: dgc@kemri-wellcome.org. 14. Alegana VA, Okiro EA, Snow RW. Routine data for malaria morbidity
estimation in Africa: challenges and prospects. BMC Med. 2020;18:121.
15. Bisanzio D, Mutuku F, LaBeaud AD, Mungai PL, Muinde J, Busaidy H, et al.
Declarations
Use of prospective hospital surveillance data to define spatiotemporal
heterogeneity of malaria risk in coastal Kenya. Malar J. 2015;14:482.
Ethical approval and constent for participate
16. Ndiath MM, Cisse B, Ndiaye JL, Gomis JF, Bathiery O, Dia AT, et al. Applica-
The health facility surveillance did not impose any changes in the national
tion of geographically-weighted regression analysis to assess risk factors
treatment guidelines and data used in the analysis were gathered as part
for malaria hotspots in Keur Soce health and demographic surveillance
of routine care. Consent was waived by the ethics committee; therefore,
site. Malar J. 2015;14:463.
individual patient consent was not sought. All the records were pseudo-
17. Kangoye DT, Noor A, Midega J, Mwongeli J, Mkabili D, Mogeni P, et al.
anonymized at the point of data capture in the healthcare facilities but linked
Malaria hotspots defined by clinical malaria, asymptomatic carriage, PCR
to the demographic surveillance by an ID number. This study was approved
and vector numbers in a low transmission area on the Kenyan Coast.
by the Kenya Medical Research Institute Scientific Ethics Review Unit (KEMRI/
Malar J. 2016;15:213.
SERU/CGMR-C/106/3592) and the Oxford tropical research ethics committee
18. Mlacha YP, Chaki PP, Mwakalinga VM, Govella NJ, Limwagu AJ, Paliga JM,
(OxTREC Reference: 511-18).
et al. Fine scale mapping of malaria infection clusters by using routinely
collected health 1 facility data in urban Dar Es Salaam Tanzania. Geospa-
Consent for publication
tial Health. 2017;12:294.
Not applicable.
19. Ouedraogo B, Inoue Y, Kambiré A, Sallah K, Dieng S, Tine R, et al. Spatio-
temporal dynamic of malaria in Ouagadougou, Burkina Faso, 2011–2015.
Competing interests
Malar J. 2018;17:138.
The authors declare no competing interests.
20. Rouamba T, Nakanabo-Diallo S, Derra K, Rouamba E, Kazienga A, Inoue Y,
et al. Socioeconomic and environmental factors associated with malaria

--- Page 13 ---
K amau et al. Malar J (2021) 20:227 Page 13 of 13
hotspots in the Nanoro demographic surveillance area Burkina Faso. BMC 32. Rulisa S, Kateera F, Bizimana JP, Agaba S, Dukuzumuremyi J, Baas L, et al.
Public Health. 2019;19:249. Malaria prevalence, spatial clustering and risk factors in a low endemic
21. Hamre KE, Hodges JS, Ayodo G, John CC. Lack of consistent malaria area of Eastern Rwanda: a cross sectional study. PLoS One. 2013;8:e69443.
incidence hotspots in a Highland Kenyan Area during a 10-year 33. Ernst KC, Adoka SO, Kowuor DO, Wilson ML, John CC. Malaria hotspot
period of very low and unstable transmission. Am J Trop Med Hyg. areas in a highland Kenya site are consistent in epidemic and non-epi-
2020;103:2198–207. demic years and are associated with ecological factors. Malar J. 2006;5:78.
22. Kamau A, Mtanje G, Mataza C, Malla L, Bejon P, Snow RW. The relationship 34. Bousema T, Stresman G, Baidjoe AY, Bradley J, Knight P, Stone W, et al.
between facility-based malaria test positivity rate and community-based The impact of hotspot-targeted interventions on malaria transmission
parasite prevalence. PLoS One. 2020;15:e0240058. in Rachuonyo South District in the Western Kenyan Highlands: a cluster-
23. Kamau A, Mtanje G, Mataza C, Mwambingu G, Mturi N, Mohammed S, randomized controlled trial. PLoS Med. 2016;13:e1001993.
et al. Malaria infection, disease and mortality among children and adults 35. Mlacha YP, Wang D, Chaki PP, Gavana T, Zhou Z, Michael MG, et al. Effec-
on the coast of Kenya. Malar J. 2020;19:210. tiveness of the innovative 1,7-malaria reactive community-based testing
24. MoPHS. National guidelines for the diagnosis, treatment and prevention and response (1,7-mRCTR) approach on malaria burden reduction in
of malaria in Kenya. : Division of Malaria Control, Ministry of Public Health Southeastern Tanzania. Malar J. 2020;19:292.
and Sanitation; 2010. https:// www. theco mpass forsbc. org/ sites/ defau lt/ 36. WHO. Global technical strategy for malaria 2016–2030: Geneva, World
files/ proje ct_ exampl es/ Kenya_ Malar ia_ Tx_ Guide line_ 2010. pdf. Health Organization; 2015. https:// www. who. int/ malar ia/ areas/ global_
25. Kulldorff M. A spatial scan statistic. Commun Stat Theory Methods. techn ical_ strat egy/ en/
1997;26:1481–96. 37. WHO. World malaria report 2020: Geneva, World Health Organization;
26. Bejon P, Williams TN, Liljander A, Noor AM, Wambua J, Ogada E, et al. 2020. https:// www. who. int/ publi catio ns/i/ item/ 97892 40015 791
Stable and unstable malaria hotspots in longitudinal cohort studies in 38. Jackson MC, Huang L, Luo J, Hachey M, Feuer E. Comparison of tests for
Kenya. PLoS Med. 2010;7:e1000304. spatial heterogeneity on data with global clustering patterns and outliers.
27. Jones SG, Kulldorff M. Influence of spatial resolution on space-time Int J Health Geogr. 2009;8:55.
disease cluster detection. PLoS One. 2012;7:e48036. 39. Cramb SM, Duncan EW, White NM, Baade PD, Mengersen KL. Spatial Mod-
28. Mirghani SE, Nour BY, Bushra SM, Elhassan IM, Snow RW, Noor AM. The elling Methods. Brisbane: Cancer CouncilQueensland and Queensland
spatial-temporal clustering of Plasmodium falciparum infection over University of Technology. 2016. https:// eprin ts. qut. edu. au/ 204103/.
eleven years in Gezira State the Sudan. Malar J. 2010;9:172. Accessed 03 Dec2020.
29. Clark TD, Greenhouse B, Njama-Meya D, Nzarubara B, Maiteki-Sebuguzi
C, Staedke SG, et al. Factors determining the heterogeneity of malaria
Publisher’s Note
incidence in children in Kampala Uganda. J Infect Dis. 2008;198:393–400.
30. Mogeni P, Williams TN, Omedo I, Kimani D, Ngoi JM, Mwacharo J, et al. Springer Nature remains neutral with regard to jurisdictional claims in pub-
Detecting malaria hotspots: a comparison of rapid diagnostic test, lished maps and institutional affiliations.
microscopy, and polymerase chain reaction. J Infect Dis. 2017;216:1091–8.
31. Yeshiwondim AK, Gopal S, Hailemariam AT, Dengela DO, Patel HP. Spatial
analysis of malaria incidence at the village level in areas with unstable
transmission in Ethiopia. Int J Health Geogr. 2009;8:5.
RReeaaddyy ttoo ssuubbmmiitt yyoouurr rreesseeaarrcchh ?? CChhoooossee BBMMCC aanndd bbeenneeffiitt ffrroomm::
• fast, convenient online submission
• thorough peer review by experienced rese archers in your field
• rapid publication on acceptance
• support for research data, including large and complex data types
• gold Open Access which fosters wider collaboration and increased citations
• maximum visibility for your research: over 100M website views per year
At BMC, research is always in progress.
Learn more biomedcentral.com/submissions