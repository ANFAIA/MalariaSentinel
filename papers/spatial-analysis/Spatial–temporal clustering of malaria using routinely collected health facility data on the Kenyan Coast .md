# Spatial-temporal clustering of malaria using routinely collected health facility data on the Kenyan Coast

**Authors:** Alice Kamau, Grace Mtanje, Christine Mataza, Philip Bejon, Robert W. Snow
**Journal:** Malaria Journal | **Year:** 2021 | **DOI:** 10.1186/s12936-021-03758-3
**File:** papers/spatial-analysis/Spatial–temporal clustering of malaria using routinely collected health facility data on the Kenyan Coast .md

---

## Abstract

The over-dispersed pattern of malaria transmission has led to attempts to define malaria "hotspots" for targeted control in Africa. However, few studies have investigated the use of routine health facility data in stable, endemic areas as a low-cost strategy for hotspot identification. This study explored the spatial and temporal dynamics of fever-positive RDT malaria cases routinely collected along the Kenyan Coast. Data on febrile patients presenting to six out-patient public health facilities in Kilifi County were obtained between March 2018 and February 2019, with 28,134 attendees geocoded to homestead level (5,323 homesteads) in 36 enumeration zones (EZs). Kulldorff's spatial scan statistics using the Bernoulli probability model were used to detect hotspots of fever-positive RDTs across all ages.

Across 12 months of surveillance, nine significant clusters were identified, encompassing 52% (6,293/12,143) of all fever-positive RDT cases in just 29% (1,520/5,323) of geocoded homesteads. When data were aggregated at enumeration zone (village) level — the resolution typically available through routine health information systems — the identified hotspots were located in the same areas, demonstrating that coarser-resolution data can still detect spatial heterogeneity. However, temporal stability was limited: only two clusters remained stable across quarterly intervals, representing just 2.7% of homesteads and 10.8% of cases. The primary cluster (3 km radius, RR=1.75, p<0.001) was located in the west of the study area around Chasimba health centre. Cumulatively, 80.9% of homesteads were either in unstable hotspots or never identified as a hotspot. The authors conclude that the temporal instability of spatial hotspots and the modest fraction of cases they account for suggests it would be inadvisable to redesign sub-county control strategies around targeting hotspots in this setting.

## Methods

- Passive case detection from six public health facilities in Kilifi Health and Demographic Surveillance System (KHDSS)
- Inclusion: all patients ≥6 months with fever (history or measured axillary temperature ≥37.5°C) between March 2018–February 2019
- Malaria diagnosis: CareStart HRP2 *P. falciparum* RDT
- Spatial resolution: homestead-level geocoordinates (gold standard) and enumeration zone (EZ) centroid aggregation
- Kulldorff's spatial scan statistic (SaTScan v9.6) with Bernoulli probability model (cases = RDT+, controls = RDT−)
- Maximum spatial cluster size: 3 km radius; circular scanning windows
- Temporal stability analysis: data sub-divided into quarterly intervals (Q1: Mar–May 2018, Q2: Jun–Aug 2018, Q3: Sep–Nov 2018, Q4: Dec 2018–Feb 2019)
- Smoothing for visualisation: 1 km radius for TPR mapping
- 999 Monte Carlo simulations for significance testing
- Analysis in Stata v13 and R v3.6.1

## Key Results

- 28,134 febrile attendees; 12,143 (43%) RDT positive; 5,323 geocoded homesteads
- Nine significant clusters detected over 12 months: 52% of cases in 29% of homesteads
- Primary cluster: Chasimba health centre, 3 km radius, RR=1.75, 16% of all cases
- Secondary clusters: Ziani, Kadzinuni, Bomani, Jaribuni dispensaries
- Overall TPR remained stable across seasons (wet 42.7% vs dry 43.5%, p=0.173)
- Quarterly analysis: 4–6 clusters per quarter, representing 17.7–32.6% of homesteads
- Only 2 temporally stable hotspots across all 4 quarters: 2.7% of homesteads, 10.8% of cases
- 80.9% of homesteads: unstable hotspots or never in a hotspot
- EZ-level aggregation produced hotspots in the same areas as homestead-level data
- No clusters detected from Mavueni dispensary data

## Relevance to MalariaSentinel (Centinela)

This study provides critical evidence on the temporal instability of malaria hotspots detected from routine health facility data — a key consideration for the Centinela's surveillance-response module. The finding that only 2.7% of homesteads were consistently in hotspots across all four quarters challenges the assumption that hotspot-targeted interventions are a straightforward strategy in moderate-endemic settings. The demonstration that village-level (EZ) aggregation produces comparable results to homestead-level analysis validates the Centinela's use of routinely-available spatial resolutions. The study's methodological rigour in comparing spatial resolutions and assessing temporal stability directly informs the Centinela's cluster detection and risk stratification approach.

---

## Full Text

### --- Page 1 ---
Kamau et al. Malar J (2021) 20:227 Malaria Journal
https://doi.org/10.1186/s12936-021-03758-3
RESEARCH Open Access
Spatial-temporal clustering of malaria
using routinely collected health facility data
on the Kenyan Coast
Alice Kamau1,3* , Grace Mtanje1, Christine Mataza1,2, Philip Bejon1,3 and Robert W. Snow1,3
Abstract
Background: The over-distributed pattern of malaria transmission has led to attempts to define malaria "hotspots"
that could be targeted for purposes of malaria control in Africa. However, few studies have investigated the use of
routine health facility data in the more stable, endemic areas of Africa as a low-cost strategy to identify hotspots. Here
the objective was to explore the spatial and temporal dynamics of fever positive rapid diagnostic test (RDT) malaria
cases routinely collected along the Kenyan Coast.
Methods: Data on fever positive RDT cases between March 2018 and February 2019 were obtained from patients
presenting to six out-patients health-facilities in a rural area of Kilifi County on the Kenyan Coast. To quantify spatial
clustering, homestead level geocoded addresses were used as well as aggregated homesteads level data at enumera-
tion zone. Data were sub-divided into quarterly intervals. Kulldorff's spatial scan statistics using Bernoulli probability
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
Keywords: Malaria, Hotspots, Spatial clusters, Spatial-temporal dynamics, Heterogeneity
Background
The Pareto principle states that for many outcomes approximately 80% of consequences come from only 20% of the causes. The concept was developed under economic theory but has been applied to models of infectious disease epidemiology [1–3]. In malaria, events are often over-distributed in space and time driven by variations in local vector ecology, host susceptibility to infections or outcomes of infections [1, 4–12]. The concept that malaria is over-distributed in space has led to attempts to define "hotspots" in more stable, endemic areas of Africa [13]. However, far fewer studies have investigated the potential of passive case detection in health facilities to identify hotspots [10, 15–21]. Here the objective was to explore the spatial and temporal dynamics of fever positive RDT malaria cases routinely collected in six health facilities along the Kenyan Coast.
Methods
This is a secondary analysis of data collected from six health facilities located in the southern part of Kilifi Health and Demographic Surveillance System (KHDSS) along the Kenyan coast. Malaria transmission is perennial but relatively higher during the long (April-June) and short (October-December) rains with infection prevalence of approximately 10%. The area included an enumerated mid-year population of 72,560 in 2018 and 36 EZs consisting of 9,596 homesteads.
Local spatial cluster detection was performed using Kulldorff's spatial scan statistic [25]. SaTScan imposes circular scanning windows across a study area with radius varying from zero to a maximum of 50% of the population in the sampling frame. The Bernoulli probability model was used to detect hotspots of fever positive RDTs. The maximum spatial cluster size was set at a radius of 3 km. To test for temporal stability of spatial clusters, the data was sub-divided into quarterly intervals.
Results
Overall, 28,134 febrile health facility attendees across all ages in 5,323 geocoded homesteads. Among all febrile patients, 12,143 (43%) tested positive. Across 12 months, nine significant clusters were identified. Cumulatively, 1,520/5,323 (28.6%) homesteads accounted for 51.8% (6,293/12,143) of all fever test positive cases. When data were aggregated at EZ level, hotspots were located in the same areas. Only two clusters were temporally stable across quarterly intervals, with 2.7% of homesteads consistently in hotspots accounting for 10.8% of cases.
Discussion and Conclusions
These results demonstrate that information obtained through routine testing of febrile patients can identify spatial and temporal heterogeneities at fine spatial scales. The power to detect clusters did not diminish when data were aggregated at EZ level. However, hotspots varied greatly across quarterly intervals. Only two temporally stable hotspots were identified. These results support the hypothesis that malaria tends to significantly cluster within certain geographic units. Taking together the temporal instability of spatial hotspots and the relatively modest fraction of malaria cases that they account for, it would seem inadvisable to re-design sub-county control strategies around targeting hotspots. The challenge remains to develop programmatically affordable and scalable approaches using routine data for identification of local spatial heterogeneity.
References
[Full reference list of 39 citations as published in Malaria Journal 2021.]
