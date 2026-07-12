# Spatial analysis of malaria in Anhui province, China

**Authors:** Wenyi Zhang, Liping Wang, Liqun Fang, Jiaqi Ma, Youfu Xu, Jiafu Jiang, Fengming Hui, Jianjun Wang, Song Liang, Hong Yang, Wuchun Cao
**Journal:** Malaria Journal | **Year:** 2008 | **DOI:** 10.1186/1475-2875-7-206
**File:** papers/spatial-analysis/SpatialAnalysisOfMalariaInChina .md

---

## Abstract

Malaria has re-emerged in Anhui Province, China, making it the most seriously affected province during 2005–2006. Understanding the spatial distribution of malaria cases and identifying highly endemic areas is critical for public health planning and resource allocation. This study applied GIS-based spatial analyses including spatial smoothing and spatial cluster analysis (spatial scan statistics) to characterise the geographic distribution patterns of malaria at the county level using reported cases from 2000 to 2006. Data on 77,674 malaria cases from 78 counties and cities were obtained from the National Notifiable Disease Surveillance System (NNDSS). The annual average incidence at county level ranged from 0 to 138.37 per 100,000.

Spatial analysis revealed that malaria was not distributed randomly. Using a maximum spatial cluster size of <50% of the total population, the most likely cluster was identified in the north of the Huai River, encompassing 8 counties and 2 cities (8.31% of the population) with a relative risk of 39.75 (43,182 observed vs 2,443 expected cases, p<0.001). When the maximum cluster size was reduced to <25%, the same primary cluster and four secondary sub-clusters comprising 14 additional counties were identified, with all but one sub-cluster significant at p<0.001. The high-risk areas were located on low-lying lands along the Huai River where *Anopheles sinensis* is the principal vector and people habitually sleep outdoors in summer. This spatial pattern differed from historical foci in central Anhui where *Anopheles anthropophagus* was the principal vector. The study demonstrates that GIS and spatial statistical techniques provide a means to quantify explicit malaria risks and identify environmental factors responsible for re-emerged malaria risk, with implications for targeted prevention strategies.

## Methods

- Data: 77,674 malaria cases (2000–2006) from NNDSS, county-level polygon map at 1:1,000,000 scale
- Annualised average incidence per 100,000 calculated for each of 78 counties/cities
- Spatial rate smoothing using k-nearest neighbour criterion (k=6)
- Excess hazard mapping (ratio of observed to expected incidence)
- Spatial cluster analysis using Kulldorff's spatial scan statistic (SaTScan v6.0)
- Circular windows centred on county centroids, maximum cluster sizes: <50% and <25% of total population
- Demographic data from 2000 national census
- GIS software: ArcGIS 9.1

## Key Results

- 77,674 cases across 78 counties/cities; annualised incidence range: 0–138.37/100,000
- 11 counties/cities high-endemic (13.9% land, 19.7% population); 14 medium-endemic; 52 low-endemic; 1 non-endemic
- Most cases occurred on low-lying lands along the Huai River
- Primary cluster (50% threshold): 8 counties + 2 cities north of Huai River, RR=39.75 (p<0.001)
- Secondary clusters (25% threshold): 14 additional counties identified as sub-clusters
- All but one sub-cluster statistically significant at p<0.001
- Spatial smoothing and excess hazard maps confirmed elevated risk in northern Huai River region
- Shift from historical *An. anthropophagus*-dominated foci in central Anhui to *An. sinensis*-dominated foci in the north

## Relevance to MalariaSentinel (Centinela)

This study provides an early example of GIS-based spatial analysis for malaria risk stratification and cluster detection, directly relevant to the Centinela's analytical pipeline. The two-stage approach (spatial smoothing followed by cluster detection) informs the Centinela's methodology for identifying high-risk foci from routine surveillance data. The finding that spatial clustering patterns shifted over time (from central to northern Anhui) highlights the importance of temporal monitoring in the Centinela's framework. The integration of vector species distribution with cluster analysis demonstrates the value of the Centinela's multi-layer approach combining epidemiological, entomological, and environmental data.

---

## Full Text

### --- Page 1 ---
Malaria Journal
BioMed Central
Research Open Access
Spatial analysis of malaria in Anhui province, China
Wenyi Zhang†1, Liping Wang†2, Liqun Fang†1, Jiaqi Ma2, Youfu Xu1,
Jiafu Jiang1, Fengming Hui1, Jianjun Wang3, Song Liang4, Hong Yang1 and
Wuchun Cao*1
Address: 1Beijing Institute of Microbiology and Epidemiology, State Key Laboratory of Pathogen and Biosecurity, Beijing, PR China, 2Center for
Public Health Information, National Center for Disease Control and Prevention, Beijing, PR China, 3Anhui Center for Disease Control and
Prevention, Hefei, PR China and 4College of Public Health, The Ohio State University, Columbus, Ohio, USA
Email: WenyiZhang-zwy0419@126.com; LipingWang-wanglp@chinacdc.cn; LiqunFang-fang_lq@163.com; JiaqiMa-majq@chinacdc.cn;
YoufuXu-xuyoufu2006_th@yahoo.com.cn; JiafuJiang-jiafujiang2008@yahoo.com.cn; FengmingHui-fmhfm@126.com;
JianjunWang-wjj@ahcdc.com.cn; SongLiang-sliang@cph.oso.edu; HongYang-anni_yang@163.com; WuchunCao*-caowc@nic.bmi.ac.cn
* Corresponding author †Equal contributors
Published: 10 October 2008 Received: 22 July 2008
Accepted: 10 October 2008
Malaria Journal 2008, 7:206 doi:10.1186/1475-2875-7-206
Abstract
Background: Malaria has re-emerged in Anhui Province, China, and this province was the most
seriously affected by malaria during 2005–2006. It is necessary to understand the spatial distribution
of malaria cases and to identify highly endemic areas for future public health planning and resource
allocation in Anhui Province.
Methods: The annual average incidence at the county level was calculated using malaria cases
reported between 2000 and 2006 in Anhui Province. GIS-based spatial analyses were conducted to
detect spatial distribution and clustering of malaria incidence at the county level.
Results: The spatial distribution of malaria cases in Anhui Province from 2000 to 2006 was mapped
at the county level to show crude incidence, excess hazard and spatial smoothed incidence. Spatial
cluster analysis suggested 10 and 24 counties were at increased risk for malaria (P < 0.001) with
the maximum spatial cluster sizes at < 50% and < 25% of the total population, respectively.
Conclusion: The application of GIS, together with spatial statistical techniques, provide a means
to quantify explicit malaria risks and to further identify environmental factors responsible for the
re-emerged malaria risks. Future public health planning and resource allocation in Anhui Province
should be focused on the maximum spatial cluster region.
Background
Malaria is one of the leading causes of morbidity and mortality in the world. Indeed, more than 2.4 billion people are exposed to the risk of malaria [1]. Malaria is one of major parasitic diseases with a wide distribution in China. The prevalence gradually decreases from south to north. Since 2000, a malaria resurgence has occurred in China. Anhui Province is the most seriously affected area in China, with the highest number of malaria cases in 2006. The use of GIS with spatial statistics, including spatial smoothing and cluster analysis, has been applied to other diseases to analyse and characterise spatial patterns [4-8].
Materials and methods
The study site is Anhui Province (114.85°~119.69°E, 29.38°~34.74°N). The area has a population of 58,358,232 and encompasses 139,600 square kilometres. Records on malaria cases between 2000 and 2006 were obtained from the National Notifiable Disease Surveillance System (NNDSS). Malaria cases were geo-coded and matched to county-level layers. Spatial smoothing was performed using k-nearest neighbour criterion (k=6). Spatial cluster analysis was performed using SaTScan v6.0 with circular windows, testing for clusters at <50% and <25% of total population.
Results
A total of 77,674 malaria cases were reported. Annualized average incidence ranged from 0 to 138.37 per 100,000. The four type areas were displayed in a thematic map. The excess hazard map showed distribution of excess risk. Spatial cluster analysis identified a most likely cluster including 8 counties and 2 cities in the north of Huai River (RR = 39.75, p < 0.001). Using <25% population threshold, four secondary sub-clusters were identified including 14 counties.
Discussion
The investigation of infectious disease clustering is receiving renewed interest because of advances in GIS and spatial statistics. Using GIS and spatial statistics, the spatial distribution of confirmed malaria cases and increased risk regions were identified. Prevention strategies are recommended that focus on these high epidemic areas. Future research should investigate landscape attributes and environmental variables characteristic of high-risk areas. The use of spatial analysis tools should become an integral component in epidemiology research and risk assessment of malaria.
References
[Full reference list of 21 citations as published in Malaria Journal 2008.]
