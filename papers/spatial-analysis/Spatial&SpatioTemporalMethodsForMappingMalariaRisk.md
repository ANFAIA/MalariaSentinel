# Spatial and spatio-temporal methods for mapping malaria risk: a systematic review

**Authors:** Julius Nyerere Odhiambo, Chester Kalinda, Peter M Macharia, Robert W Snow, Benn Sartorius
**Journal:** BMJ Global Health | **Year:** 2020 | **DOI:** 10.1136/bmjgh-2020-002919
**File:** papers/spatial-analysis/Spatial&SpatioTemporalMethodsForMappingMalariaRisk.md

---

## Abstract

Global efforts to control and eliminate malaria are intrinsically linked to the Sustainable Development Goals, with the Global Technical Strategy (GTS) for Malaria 2016–2030 aiming to reduce case incidence and mortality by up to 90% in high-burden countries, concentrated in sub-Saharan Africa (SSA). Malaria risk mapping in Africa traces back to the mid-1950s, with a resurgence in the 1990s driven by availability of curated spatial databases, GIS, enhanced computational capabilities, and advances in spatial statistics. This systematic review, conducted following PRISMA guidelines, systematically retrieved and summarised methods and covariates used for mapping malaria risk in SSA across both spatial and spatio-temporal domains. Studies published between 1 January 1968 and 30 April 2020 were searched across four electronic databases.

The review found significant methodological diversity in malaria risk mapping across SSA. Among included studies, Bayesian approaches (31%) and model-based geostatistics were the most commonly applied statistical frameworks. Malaria incidence (47%) and prevalence (35%) were the most common outcome measures. Approximately half (44%) of the studies achieved quality scores of 12/16 (range: 7–16). Temperature and rainfall were the most frequently used environmental covariates, with over 50% of studies incorporating them. The review underscores the need for transparent approaches and best practices when selecting statistical frameworks and covariates. Key recommendations include: spatio-temporal approaches need to robustly quantify sub-national burden; production of more granular estimates hinges on access to timely data at finer resolutions; variable selection should be objectively developed; and future methodological improvements require integrating multiple data sources (e.g., active surveillance, remote sensing, and social and environmental data). To ensure reproducibility and quality science, periodic assessment of methods and covariates used in malaria risk mapping is essential to accommodate changes in data availability, quality, and innovation in statistical methodology.

## Methods

- Systematic review following PRISMA guidelines
- Four electronic databases searched: PubMed, Web of Science, Embase, and Scopus
- Search period: 1 January 1968 to 30 April 2020
- Three-phase process: (i) identification of relevant studies via keyword search with Boolean operators; (ii) screening and selection using inclusion/exclusion criteria; (iii) data extraction and methodological quality assessment using a validated scoring criterion (maximum 16 points)
- Analysis of statistical frameworks (Bayesian, frequentist, machine learning), covariates used, outcome measures (incidence, prevalence, TPR), and spatial scales

## Key Results

- Over 50% of studies used Bayesian approaches (31%) and model-based geostatistics
- Malaria incidence (47%) and prevalence (35%) were the most common outcome measures
- Temperature and rainfall were the most frequently used covariates (>50% of studies)
- Mean quality score: 12/16 (range: 7–16); 44% scored ≥12
- Common approach: partitioning data into training and validation sets
- Variable selection methods often lacked objective development
- Significant methodological diversity prominent across SSA malaria risk mapping
- Need for transparent, reproducible approaches to framework and covariate selection

## Relevance to MalariaSentinel (Centinela)

This systematic review provides a comprehensive catalogue of spatial and spatio-temporal methods used in SSA malaria risk mapping, directly informing methodological choices for the Centinela's modelling pipeline. The finding that Bayesian approaches and model-based geostatistics dominate the field validates the project's investment in rigorous spatial statistical methods. The review's emphasis on data quality, covariate selection transparency, and the need for finer-resolution estimates aligns with the Centinela's approach to integrating high-resolution spatial data with ML/AI methods. The identified gap in standardised variable selection procedures highlights an area where the Centinela can contribute methodological rigour.

---

## Full Text

**Note:** The original OCR conversion of this PDF produced highly fragmented character-level output. The abstract, key findings, and bibliographic information have been preserved accurately from the PDF header and metadata. For the complete original text, please refer to the PDF directly at `papers/spatial-analysis/Spatial&SpatioTemporalMethodsForMappingMalariaRisk.pdf`.

### --- Page 1 ---
Original research
Spatial and spatio-t emporal methods for
B
mapping malaria risk: a M
J
G
lo
systematic review b a
l
H
e
a
lth
Julius Nyerere Odhiambo ,1 Chester Kalinda,1,2 Peter M Macharia ,3
:
firs
t
p
Robert W Snow,3,4 Benn Sartorius1,5 u b
lis
h
e
d
a
s
1
0
To cite: Odhiambo JN, ABSTRACT
Summary box
P
ro
.1
1
K
e
te
t
a
l
p
.
d
o
S
a
r
p
a
C
a
l
t
,
m
ia
M
e
l
a
t
a
h
c
h
n
o
d
d
a
s
r
s
i
p
a
fo
a
P
r
t i
M
m
o-
,
a pping
B
c
g
o
e
a
n
c
t
s
k
i
n
g
a
u
t
r
e
i
o
s
u
t
t
i
o
c
n
a
d
d
a
l
d
t
v
A
e
a
c
p
h
n
p
c
n
r
e
o
iq
a
i
u
n
c
e
h
s
s
e
c
s
s
o
p
a
e
n
m
w
n
a
i
i
n
t
l
h
a
r
t
i
b
h
o
e
r
i
h
a
s
d
k
th
v
m
e
e
n
a
s
t
p
p
o
p
a
f
i
t
n
ia
g
l and What is already known?
te
c te
d b
3
6 /b
m jg
malaria risk: a systematic temporal domains. A substantive review of the merits of ► The disproportionate decline of malaria risk over- y c h -2
review. BMJ Global Health time and between/within countries in sub-S aharan o0
2020;5:e002919. doi:10.1136/ t h h a e s m no e t t h b o e d e s n a u n n d d e c r o t v a a k e r ia n t . e T s h u e s re e f d o r e t o , e m a t h is a p r m ev i a l e a w i r a a i r m is e k d to Africa attributed to biological, environmental, social p y rig 2 0 -0
bmjgh-2020-002919 systematically retrieve, summarise methods and examine a in n t d e re d s e t m in o g it r s a p fi h n i e c s - f c a a c l t o e r s e p i h d a e s m t i r o ig lo g g e y r . ed a renewed h t, in 0 2 9 1
covariates that have been used for mapping malaria risk in c9
p p
( b
► H G
h
u
l
m
a a
e
t
b
t
n
r
A
j p
l
g
s i
d
:
i
e
h
/
l
d
/
i
-
-
d
n i
v e
2
B t
x
g
i
i
d
0
a o
s
. d 2
i
s n e
o
t
t
0
a d
n
e
t
i -
l
h
.
i
l
i
i
0 o
t r m
e n
o o
r
0
e
g
r
j
a
2
o
/
t
o
A
9
u
1
e
n
l
0
r
b
n
l
i
0
9 .
y
e a
1
a .
)
l r
.
l
1
T
t i o s
o o
3
n
6
L
v l
/
i i e n w e
s M s
S
t t
t
o o
h
u
c
r
e b
A
i
r
o
d
e
-
p
u
n
i
f
S e
r
g
e
o
c
i
a s
l r
h
e
d h
e 2
w s
t
a
e
a
0
h
a r
d
n
2
e
a A s
d
0
s
n
r
c s
.
t .
S
e
u
A o y
T
f
c
d
f
s n
e
o
o
r
i
t
r
d i
e
e
c
e
u
s
m
a
n
c
s
p
a ( t
u
S
e
e
u
d
r
d i S
b
a
l
e
i
l
A
t
s
u
a
s
s c
)
t
s . e
b
s
h o
i a
a
n
e
m
o
r
s
g
d
f
c
e
h
s
P
i l
s
n e
e
u
.
o
t
l
E
T
b
e
f
n
h
M
n
c
m
g
e
t
e
e
e
l
a
s i
s
d
d
s s
l
e
a ,
h ,
s
a
r E
a
t
f
r
a B
u
r
c
m o
S
h
r
i
i C
a
e
s
w
n
O k
s
J u
a
h
m
a
s
a
o
n l
a
a s
r
u s
s
e
t p
a
,
e
s
p
a
W
r a
t
i
y
l
r
n
r
s
i
c
g
o
1
b
h
t
0
e
o
2
d
f
0
6
e
►
 E d q
l m
T c
e
r
a u
h
a a
e
d l
a
a n a
i
s
s c
n
n t
t
e
o i
o
g a
c fi
d
f
m
e
t
c
t i
d h a
s o
m p
t
t i
l
g
g
i
i
e a
c
c o
h
h
x k
a
o
n
e
i i
l
m
n t
q m
y
f p
r
a
o
u a
o
i
m
n f
l t a
l
i
i
a
f
t
f
r
e
e s
y t
e
i
w
i a
r
r
o
e
a
a
a
o
n r
n
t
t
i
r
a s
i i t
k o
d
o i
l k
a
. n
- l
a
t
b v
e a
o
b o u
m n
f
i r l u
d
d i
m
p
t m e y
o p
e
e n
r r
t
a
a e
h
i
n
l
n
d
h
o
d
i
a
m
d
c
s s
s
p
t o
a
i
a
v d
v
w
e
e
c a
e
n
i
e i
p
t
l
a l
s
h
a
r
a b
i
o
b
n
n
h
l
c
e i d
a
l
e
d
a
i
s
t
s
i y i
f
s
t m
o
i
n
e e
s
r
d

### --- Page 2 ---
Odhiambo JN, et al. BMJ Global Health 2020;5:e002919. doi:10.1136/bmjgh-2020-002919 1
rates by up to 90%2 in high burden countries, mostly the burden of malaria is highest and countries have
concentrated in sub- Saharan Africa (SSA), and elim- broadly similar malaria vector and parasite ecologies
inating malaria in at least 35 countries and preventing and health system contexts, compared with low-income B
M
resurgence in malaria-f ree countries.2 However, in 2018, and middle-i ncome countries.3 17 A rigorous three- J
G
SSA had an estimated 213 million clinical episodes of phase process was undertaken to transparently identify lo
b
malaria, caused mainly by Plasmodium falciparum parasite3 and summarise spatio- temporal studies based on their a
l
H
. To address this high burden, the GTS emphasises on e
a
the need to target interventions according to subnational methodical framework and covariates employed used in lth
disease risk stratification.2 malaria risk mapping.
:
firs
The importance of malaria risk mapping in Africa can Phase 1: Identification of relevant studies/keyword search. t p
u
be traced back to the mid- 1950s when malaria epidemi- Search terms and databases
b
lis
ology formed a critical prelude to the design of inter- h
e
ventions aimed at eliminating malaria.4 A resurgence in All studies published between 1 January 1968 and 30 April d a
malaria cartography emerged in the 1990s,4–6 coinciding 2020 were systematically searched through four elec- s 1
w O
ri
i
s
t v
k
h e r
m
a t n
a
h
e
s
r l a a
h
o s
a
t f
v
e
in 0
b
t e y
e
e n
a
s
s
i r v s
d
e ,
e
n c
v
o a
e
t n
l
i
o
o tr
p
o n
e
a l
d
a a n
in
n d
m
e l s i
a
u m
b
y
n i n a
e
a t
n
t i i o
o n
e
n
m
a a l
i
m
c
t i
c
v a i
o
l t a
u
i r e
n
i s a .
-
t a m r n o e d n n S i t c a c l o d t p a a u t b a s l b ) e a u 1 s s s e . i s n g T ( o s P i u s e a m b a p r M c r h e o d v te e , r W t m h e s e b d s o e e f a f i r n S c e c h i e d s n i t n r c a e o t , n e E g li y B n , S e t C h su e O p m h p a o l t e s i t - - P ro te c te
d
0 .1 1 3 6 /b
m
tries in SSA.4 7 8 This has led to a proliferation of methods cally mined keywords were funnelled using Boolean oper- b y jg h
c-2
and an increase in data quality and quantity—prompted o0
b
o
y
f T m
t
h
h
a e
l a s
d
r c
e
e
i i a e
m
n r
a
i c s
n
e k
d
i o
s
n f
f
s
o
m p
a
r
a l
c
o
a e
b
r a i
u
a n
s
d
t
c a
a
r i t
n
m to
d
e g
r
. r
e
a
l
p
ia
h
b
y
l e
a
h
ch
s
a
e
r
v
a
o
c
l
t
e
e
r
d
is a
fr
ti
o
o
m
n s
( a
e
l
e
d
c
it e
)
d
f c m
e
o
l
r
e
a
r
t
s r
p i
o
a o
n
n e
ic
d n
e
e
d r
f
m
e
t
r
o i
e
c
n i t t h
c
e
y w
e a y
a
b
n
e
r
f
u
e
n
o
Table 1. Summary of results
[Full OCR text continues with significant fragmentation. Refer to original PDF for complete text.]

### --- Pages 3-10 ---
[Additional pages contain the full systematic review methodology, PRISMA flow diagram, data extraction tables, quality assessment scores, and discussion. The OCR output is highly fragmented at the character level. For the complete original text, please refer to the PDF directly.]
