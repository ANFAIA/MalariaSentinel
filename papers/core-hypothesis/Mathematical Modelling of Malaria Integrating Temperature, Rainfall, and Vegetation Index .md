# Mathematical Modelling of Malaria Integrating Temperature, Rainfall, and Vegetation Index
**Authors:** Kelly Joëlle Gatore Sinigirira, Wandera Ogana, Faraimunashe Chirove
**Journal:** Acta Applicandae Mathematicae | **Year:** 2025 | **DOI:** 10.1007/s10440-025-00740-y
**File:** papers/core-hypothesis/Mathematical Modelling of Malaria Integrating Temperature, Rainfall, and Vegetation Index .md

---

## Abstract

Environmental factors—temperature, rainfall, and vegetation index—are critical drivers of malaria transmission dynamics, yet most mathematical models incorporate them in isolation or oversimplify their interactions. This study develops a host-mosquito deterministic compartmental model (SEIR-SEI structure for humans and mosquitoes, respectively) that integrates all three factors through temperature-dependent biting rates, rainfall- and NDVI-dependent mosquito recruitment, and a novel combined temperature-NDVI mosquito mortality function. The model is calibrated with monthly data from Burundi (2010–2022), including confirmed malaria cases, temperature (from IGEBU), rainfall, and MODIS NDVI (500m, via Google Earth Engine).

Mathematical analysis establishes the disease-free equilibrium (DFE), its local and global asymptotic stability (when R₀ < 1), the existence of endemic equilibria, and a bifurcation analysis using center manifold theory—revealing the possibility of backward bifurcation where disease can persist even when R₀ < 1. Numerical simulations identify the optimal temperature range for transmission as [20–25°C], the most favorable NDVI range as [0.4–0.6], while rainfall below 50mm had relatively minor impact in Burundi. Sensitivity analysis (Latin Hypercube Sampling with PRCC) shows that the mosquito biting rate a(T) and mosquito mortality rate μ_v(T,η) are the most influential temperature- and NDVI-dependent parameters, with the former positively correlated and the latter negatively correlated with infectious human prevalence.

Critically, the study uses SARIMA-forecasted climate variables (temperature, rainfall, NDVI) to predict the reproduction number R₀ through 2070. Results indicate a progressive increase in R₀ over time, suggesting rising transmission potential in Burundi if drastic control measures are not implemented. The reproduction number shows distinct seasonal peaks in January, April, and December, consistent with observed malaria seasonality. This work is among the first to mathematically model the joint influence of temperature, rainfall, and NDVI on malaria transmission using a single integrated ODE framework, providing a quantitative tool for assessing future malaria risk under climate change scenarios.

## Methods

- **Model structure:** Compartmental SEIR-SEI ODE model: susceptible-exposed-infectious-recovered humans (S_H, E_H, I_H, R_H) and susceptible-exposed-infectious mosquitoes (S_V, E_V, I_V). Total human population ~12.89M (Burundi), calibrated from 2010–2022 malaria case data.
- **Environmental parameterization:** Mosquito birth rate θ_v(T,R,η) depends on temperature-dependent larval stage duration, rainfall-dependent egg/larvae/pupae survival (quadratic function with washout limit R_w=50mm), and a novel NDVI modulation function H(η) on larval survival. Mosquito mortality μ_v(T,η) combines a quadratic temperature term centered on optimal T*_M=16°C with a saturation-function NDVI term. Biting rate a(T) is temperature-dependent.
- **Data sources:** Monthly temperature and rainfall from IGEBU (Burundi Geographical Institute, 2010–2022); NDVI from MODIS/006/MCD43A4 (500m, monthly, via GEE); confirmed malaria cases from Integrated National Malaria Control Program (INMCP).
- **Analysis:** Disease-free equilibrium (DFE) stability via Routh-Hurwitz criteria; global stability via Castillo-Chavez method; endemic equilibrium existence via polynomial root analysis; bifurcation direction via center manifold theory (Castillo-Chavez & Song). Sensitivity via LHS/PRCC across temperature [15–35°C], rainfall [5–50mm], NDVI [0.2–0.8].
- **Forecasting:** SARIMA models for temperature, rainfall, and NDVI projected through 2070; R₀ computed from next-generation matrix as function of forecasted climate variables.

## Key Results

- **Optimal transmission conditions:** Temperature [20–25°C], NDVI [0.4–0.6]; temperatures below 16°C insufficient for parasite development.
- **Temperature effect:** Strong positive correlation with I_H; peak at ~25°C; combination with rainfall or NDVI yields significant changes; alone most influential factor.
- **Rainfall effect:** Minimal impact on transmission dynamics in Burundi within the 5–50mm range; once above threshold, additional rainfall has little effect; lower sensitivity than temperature or NDVI.
- **NDVI effect:** NDVI [0.4–0.6] most favorable; NDVI influence increases over time (PRCC time analysis); more consistent predictor than rainfall as vegetation buffers inconsistent precipitation.
- **Sensitivity (PRCC):** β₁ (transmission from vector to human) positively correlated with I_H; γ_h (human recovery rate) and μ_v(T,η) (mosquito mortality) negatively correlated. Mosquito biting rate a(T) and mortality μ_v(T,η) are top-ranked climate-dependent parameters.
- **Bifurcation:** Backward bifurcation possible (if A > 0), meaning endemic equilibrium and DFE can coexist when R₀ < 1—initial conditions determine outcome.
- **R₀ projection:** Progressive increase from 2010–2070; seasonal peaks in January, April, December; aligns with observed case seasonality from statistical analyses.
- **Combined effects:** When all three variables increase simultaneously, infection classes increase monotonically, reaching maximum at T=35°C, rainfall=45mm, NDVI=0.8.

## Relevance to MalariaSentinel (Centinela)

This paper is highly relevant as it provides a principled mathematical framework for integrating temperature, rainfall, and NDVI into a single transmission model—directly applicable to the Centinela's ABM core. Key contributions for the project: (1) The functional form for NDVI-modulated mosquito larval survival (H(η) quadratic) can be adopted for the suitability layer in `mal-core`; (2) the temperature-NDVI mosquito mortality function μ_v(T,η) provides a mechanistic alternative to purely statistical lag models—useful for ABM parameterization in `mal-ghana-sim`; (3) the R₀ forecasting framework using SARIMA-projected climate variables demonstrates a pathway from environmental data to long-term risk projections, which the Centinela could replicate for Ghana using CMIP6 climate projections; (4) the finding that NDVI can buffer rainfall inconsistency supports the inclusion of both variables in the suitability overlay rather than rainfall alone; (5) the backward bifurcation result (R₀ < 1 but endemic persistence) is a critical insight for elimination planning—reducing R₀ below 1 may not suffice without addressing initial prevalence conditions. The study's Burundi calibration also serves as a useful comparison case for the Ghana-focused simulations, testing model generalizability across East and West African eco-epidemiological settings.

## Full Text

--- Page 1 ---
ActaApplicandaeMathematicae(2025)199:5
https://doi.org/10.1007/s10440-025-00740-y
MathematicalModellingofMalariaIntegratingTemperature,
Rainfall,andVegetationIndex
KellyJoëlleGatoreSinigirira1,2·WanderaOgana3·FaraimunasheChirove4
Received:29July2024/Accepted:23August2025/Publishedonline:4September2025
©TheAuthor(s)2025
Abstract
Environmentalfactorssuchastemperature,rainfall,andvegetationindexplayacrucialrole
inthetransmissiondynamicsofmalaria.Accuratelyquantifyingthecomplexrelationships
betweenthesevariablesandthemalariaburdenposesasignificantchallenge.Inthisstudy,
we developed a host-mosquito mathematical model to investigate the impact of tempera-
ture,rainfall,andnormalizeddifferencevegetationindex(NDVI)onmalariatransmission
dynamicscalibratedwiththeBurundicase'sstudy.Mathematicalanalysisexploredtheequi-
libria, stability, and computation of the model's threshold values. Numerical simulations
suggestthattemperature,rainfall,andvegetationindexaffectthetransmissiondynamicsof
malaria.TemperatureandNDVIappeartoexhibitamorepronouncedinfluenceamongthese
factors.Theconditionsconducivetomalariatransmissionincludeameanmonthlytemper-
ature range of [20-25 °C], an averaged monthly NDVI range of approximately [0.4-0.6].
Thereproductionnumberwasusedasaquantitativemeasuretopredicttheimpactoftem-
perature,rainfall,andNDVIonmalariatransmissiondynamicsacrossBurundi.Theresults
suggestaprogressiveincreaseinthereproductionnumberovertime,suggestingathreatof
therisingnumberofcasesinBurundiifdrasticcontrolmeasuresarenotimplemented.
Keywords Mathematicalmodel·Malaria·Reproductionnumber·Temperature·Rainfall·
NDVI
1 Introduction
Theeffectsofenvironmentalfactorsonhumanhealthhaveraisedsignificantconcerns.The
directeffectsofrapidfluctuationsinenvironmentalparameterssuchastemperature,rainfall,
✉
F.Chirove
fchirove@uj.ac.za
K.J.GatoreSinigirira
kelly.gatore@ub.edu.bi
W.Ogana
wogana@uonbi.ac.ke
1 DoctoralschoolofBurundi,UniversityofBurundi,Bujumbura,Burundi
2 DepartmentofMathematicalSciences,UniversityofBurundi,Bujumbura,Burundi
3 SchoolofMathematics,UniversityofNairobi,Nairobi,Kenya
4 DepartmentofAppliedMathematics,UniversityofJohannesburg,Johannesburg,SouthAfrica

--- Page 2 ---
5 Page2of39 K.J.GatoreSinigiriraetal.
andvegetationindexonmalariatransmissionhavebeenofparticularinterestastheychal-
lenge current control and eradication strategies. Malaria is one of the major public health
problems globally. It is an infectious disease caused by plasmodium protozoan parasites
thatistransmittedbetweenhumansthroughthebiteofthefemaleanophelesmosquito.Fe-
maleanophelesmosquitoestransmitmalariabycollectingplasmodiumparasiteswhenthey
biteaninfectedperson.Theparasitesdevelopandmultiplywithinthemosquitoandmigrate
to its salivary glands. Throughout this study, the term mosquito is used to refer to the fe-
maleanophelesmosquito.Whenthemosquitobitesanewperson,theparasitesareinjected
into their bloodstream, causing a malaria infection [1–3]. Millions of people are infected
bymalariaeveryyear.Sub-SaharanAfricacontinuestobeartheheaviestburdenofmalaria
globally,accountingfor95%ofallmalariacasesintheworld[4].Recentmalariastatistics
revealthatapproximately223millioncaseswererecordedin2022,representing94%ofthe
globalburden.Theregionaccounted for95%ofallmalariadeathsgloballyin2022,with
about78%ofthesedeathsoccurringamongchildrenundertheageoffive[5].
Burundi, an East African country experienced an increase in the malaria epidemic in
recent years andnotably from2.6 million in2013to8.3million in2016[6].With an ap-
proximate population of 12,890,000, it is estimated that 80% of the Burundi's population
is susceptible to malaria infection [7]. Approximately 56% of the population live in po-
tentially epidemic areas, while 23% live in hyper-endemic areas [8]. Each year, around 2
millioncasesofmalariaonaverageareidentifiedthroughoutthecountry.Pregnantwomen
andchildrenbelowtheageof5representthedemographicmostafflictedcategory.Inthese
agegroups,48%ofdeathsinhealthfacilitiesareattributabletomalaria[8].Onrecord,about
50%oftheoutpatientconsultationsareduetomalaria[9].Initialassessmentssuggestthat
severalprimaryfactorscontributetothecurrentincreaseinmalariatransmission.Thesefac-
tors include reduced utilization of preventive measures, diminished population immunity,
andlowersocioeconomicstatus.Additionally,heightenedmobility,especiallyamongresi-
dentsofmountainousregions,playsasignificantrole.Usually,malariaincidenceremains
lowintheseregions,butchangesinclimatepatternsandalterationsinvectorecologyand
behaviorarecausingshiftsinthedisease'sprevalence[8].
Inthepasttwodecades,analysisoftheuniversaldistributionofthediseaseshowsthatit
ismoreconcentratedinwarmregions.However,duetoclimatechangeandglobalwarming,
formerly sheltered areas are now being invaded. Climate plays a vital role in the increase
inmalariatransmissioninAfricabecausetemperatureandrainfalllevelsarepredominantly
high compared to other continents [10]. The increment in the number of mosquitoes de-
pends on the climatic conditions and the accessibility of oviposition sites, which in turn
are subordinate to natural and environmental factors [11]. Several authors have shown
thatenvironmentalandclimaticfactorssignificantlyinfluencethedynamictransmissionof
malaria[12–14].Duringhightemperatures,themosquitoes'digestivesystemsbecomeagile
whichincreasesthenumberofbitesandtheincreaseofthedisease[15].Variationsintem-
perature,humidity,rainfall,andwindspeedimpacttheoccurrenceofmalaria.Thesechanges
can either affect the lifespan of mosquitoes or influence the behaviors of humans, vectors
(mosquitoes),orparasites,therebyinfluencingthetransmissionofthedisease[16,17].The
mosquito population is very sensitive to climatic conditions; a small temperature change
canaffectthelifespanofmosquitoes.Mosquitoes,asectothermicorganisms,haveabody
temperaturethatisdependentontheexternalenvironment.Thisrelationshipbetweentheir
body temperature and the environment significantly impacts their metabolic rate. Warmer
temperaturestendtospeeduptheirmetabolism,leadingtoquickerdevelopmentandshorter
lifespans. In contrast, cooler temperatures have the opposite effect, slowing down their
metabolism and extending their life cycle [18, 19]. This forms the basis for its perpetual

--- Page 3 ---
MathematicalModellingofMalariaIntegratingTemperature,Rainfall... Page3of39 5
prevalence in the tropical climate because there are enough breeding sites and conducive
temperatures.
Vegetation is a climatic environmental factor that influences the behavior of mosquito
vectorsbothdirectlyandindirectly[20].Thevegetationindexisusedtoassessthedensityof
vegetationinaparticularareaandthemostfrequentlyusedasvegetationindicesistheNDVI
(Normalized Difference vegetation indices). It is calculated as the normalized difference
between the electromagnetics spectrum's near Infrared (NIR) and red bands. The NDVI
scalerunsfrom−1to+1wherehighvaluesindicatemoredensevegetationandvaluesnear
−1representswaterorbarrenland[21].NDVIisoftenassociatedwithrainfallpatterns,it
canindicateregionswithhighrainfallandthensuitablebreedingsitesformosquitoes.NDVI
influencesboththebirthrateandmortalityrateofmosquitoesandthus,hasgreatinfluence
onthemosquitodensity[22].
Malaria transmission models have a crucial role in understanding the transmission dy-
namicsofthediseases[23–25].Thesemodels,intheirdifferentforms,havebeenutilized
toidentifythemosteffectiveinterventionstrategiesforeradicatingthedisease[26].Mod-
elsonvectorshavebeenshownthatTheinitialfundamentalmalariamodel,introducedby
Ross [27], was a simplistic susceptible-infective-susceptible (SIS) model. It aimed to de-
scribe the link between the mosquito population and the incidence of malaria in humans.
Thestudyshowedthatmalariapersistenceissubjecttocertainmosquitopopulationthresh-
olds.SeveralauthorshaveproposedmanyimprovementstothemodelbyRoss[28–31].In
[31], the authors assumed that the population of infectious mosquitoes is constant, and it
canbeshownthatloweringthenumberofmosquitoeswillnotreducemalariadisease.The
resultsshowedthatthemosquito'slifespanisacriticalfactorinthetransmissionofmalaria.
ParhamandMichael[13]developedamodelfortheeffectoftemperatureandprecipitation
ontheadultemergencerateofmosquitoes,whichwewilluseinourresearchtodetermine
the impact of weather on the reproduction number in terms of temperature, rainfall, and
extendtheworkbyincludingthevegetationindex.In[13],demographicfactorshavebeen
consideredinordertopredictthenumberoffatalitiesthatmayoccurasaresultofillnesses.
They also discovered that the influence of temperature on vector abundance had a strong
physiologicalbasis,suggestingthatthedeterministicpopulationmodelmaybesignificantly
favored. Understanding and quantifying the relationship between anopheles mortality and
NDVI,canleadtogaininginsightsintohowenvironmentalfactorsinfluencemosquitopop-
ulationsandpotentiallyinformstrategiesformosquitocontrolanddiseaseprevention.
This study introduces a model for malaria transmission, which assesses the impact of
temperature, rainfall, and NDVI on the dynamics of malaria transmission in Burundi. It
focusesonhowthesefactorsinfluencetheoccurrenceofmalaria,thestudyoffersinsights
into future malaria trends by utilizing the reproduction number as a predictive tool. The
diseasetransmissiondynamicsaremodeledusingnon-linearordinarydifferentialequations
(ODE's)wherehumansandmosquitoesinfecteachother.
Thisworkisstructuredasfollows:Sect.2presentsanoverviewofthemodelformulation,
itsepidemiologicalvalidity,andthedomaininwhichitismathematically wellposed.We
analyzetheexistenceofequilibriaandprovidecalculationsforthefundamentalreproduction
number,aswellasanassessmentofthestabilityoftheequilibria.Additionally,wedescribe
thestudyareaandthedataprocessing.InSect.3,weconductnumericalsimulationsofthe
modelandforecasttemporaltrendsinthereproductionnumberandobservations.Wefinally
discusstheresultsobtainedfromouranalysis.

--- Page 4 ---
5 Page4of39 K.J.GatoreSinigiriraetal.
2 MaterialsandMethods
2.1 ModelFormulation
The total human population is subdivided into four classes. The susceptible class S (t),
H
thosewhoareexposedtomalariaparasitesbutnotinfectiousE (t),individualswithmalaria
H
symptoms I (t) and the class of recovered individuals R (t) to get an SEIR model. We
H H
assume that temporary immunity is gained when one has recovered from the disease and
hasimmunityagainstthemalariaparasiteforacertainperiodbeforeloosingtheimmunity.
Susceptibleindividualsareintroducedintothepopulationatabirthrateα andacquire
h
themalariaparasitethroughabiteofaninfectiousmosquito.Theyprogresstotheexposed
β a(T)I (t)
classthroughaforceofinfectiongovernedbythefunction λ = 1 V ,definedas
h N (t)
H
therateatwhichsusceptiblehumansbecomeinfectedbyinfectiousanophelesmosquitoes.
Theexpressiona(T)isthebitingrateofthemosquitoes,andβ representstheprobability
1
thatasusceptibleindividualcanbeinfectedbyaninfectiousmosquito,with0<β ≤1.The
1
susceptibleindividualsalsorecruitsrecoveredindividualfromR (t),thoseareindividuals
H
wholosetheirimmunityatarateq.Theyalsodieduetoanaturaldeathrateμ (t).Therate
h
atwhichthesusceptibleindividualschangesovertimeisdeterminedby
dS
H =α +qR −λ S −μ S . (1)
dt h H h H h H
Afterbeingbittenbyinfectiousmosquitoes,susceptibleindividualsprogresstotheex-
posedclassthroughtherateλ .Thisclassisexposedtothemalariaparasiteforafewdays
h
beforebecominginfectiousandmovingtotheinfectiousclass.Thenumberofindividuals
intheexposedclasscanalsodecreaseduetothenaturalmortalityrateμ (t).Thus,therate
h
ofchangeofexposedindividualsovertimeisgivenby
dE
H =λ S −(ρ +μ )E . (2)
dt h H h h H
Exposedindividualstransition to theinfectious classat arate denoted by ρ .Oncein-
h
fected,theyeitherrecoveratarateγ orsuccumbtothedisease,withmortalityoccurring
h
at rates δ and μ , respectively. Here, the parameter δ represents the death rate attributed
h
specificallytothedisease.Thus,weobtainthedifferentialequation
dI
H =ρ E −(μ +γ +δ)I . (3)
dt h H h h H
IndividualswhoareinfectioustransitiontotherecoveredclassR (t)ataratedenoted
H
byγ ,andthosewhohaverecoveredlosetheirimmunityatarateofq.Theyalsodiedueto
h
naturalmortalityrateμ (t)
h
dR
H =γ I −(μ +q)R . (4)
dt h H h H
The total mosquito populations N (t) are subdivided into three classes: S (t) suscep-
V V
tible, E (t) exposedandI (t) infectiousmosquitoes.Susceptiblemosquitoes(S (t)) are
V V V
recruitedintomosquitopopulationatarateθ (T,R,η).Thefunctionθ (T,R,η)represents
v v
the birth rate of the mosquitoes, we consider it as a function of temperature, rainfall and

--- Page 5 ---
MathematicalModellingofMalariaIntegratingTemperature,Rainfall... Page5of39 5
NDVI. In [13, 32], the mosquito birth rate is considered as a function of temperature and
rainfallanditisdefinedas
N S (R)S (T,R)S (R)
θ (T,R)= E E L P , (5)
v χ +χ (T)+χ
E L P
where
• N isthenumberofeggslaidperadultfemalemosquito.
E
• S (R),S (T,R)andS (R),thesurvivalprobabilityofeggs,larvae,andpupaerespec-
E L P
tively.
• χ ,χ (T),χ ,arethedurationofeggs,larva,andpupaestages.Thedurationoflarvae
E L P
1
stagevarieswithtemperature[32,33]andcanberepresentedasχ (T)= where
L ξ T +ξ
1 2
ξ andξ areconstant.
1 2
Thesurvivalprobabilityofeggs,larvaeandpupaeisaquadraticrelationshipbetweentheir
densityandrainfall[13].
[︂ ]︂
4P∗
S (R)= E R(R −R), (6)
E R2 w
w
[︂ ]︂
4P∗
S (R)= L R(R −R), (7)
L2 R2 w
w
[︂ ]︂
4P∗
S (R)= P R(R −R). (8)
P R2 w
w
P∗,P∗,P∗ arethemaximumsurvivalprobabilityofeggs,larvae,andpupae,whichcorre-
E L P
spondtothemaximumrainfallproliferationandR isthewashoutlimit.
w
The authors in [13, 32] also defined the survival probability of larvae as a function of
temperatureandrainfall,and
S (T,R)=S (T)S (R), (9)
L L1 L2
whereS (T)andS (R)arethesurvivalprobabilityoflarvaedependingontemperature
L1 L2
andrainfallrespectivelysothat
S (T)=e−αT+β, (10)
L1
with α and β constants. The quadratic function of S (R) is given in the equation (7).
L2
Rainfallhastwosideeffectsonthesurvivalprobabilityofeggs,larvaeandpupae.Eitherit
canraisethefrequencyofmalariabyprovidingadequatehabitatformosquitoesordecrease
theprevalencebyflushingawaymosquitobreedingsites[32].
NDVI can affect the aquatic stages by providing suitable breeding sites. However, the
directinfluenceoneggsislimitedaseggsarelaiddirectlyinwaterandaresubjecttoaquatic
conditions. Similar to the eggs stage, the impact of NDVI is limited at the pupae stage
as pupae are also found at the water's surface. For all these reasons, the larvae stage is
highly affected by NDVI primarily by affecting the quality of their breeding habitats [34,
35].AreaswithhighNDVIvaluesindicatedenserandhealthiervegetationwhicharemore
likely to provide suitable conditions for mosquito larvae to develop and grow, including
cooler temperatures, food sources, and protection from predators. Conversely, areas with
lowerNDVIvaluesmayleadtolessfavorableconditions,potentiallyreducingthesurvival

--- Page 6 ---
5 Page6of39 K.J.GatoreSinigiriraetal.
probability of mosquito larvae [34, 35]. Hence, following all of these ideas, we included
the NDVI's effect in the model by formulating a new mathematical function defining the
survivalprobabilityofmosquitolarvaeintermsoftemperature(T),rainfall(R),andNDVI
(η).Themathematicalexpressionmaybethenrepresentedas
S (T,R,η)=S (T)S (R)S (η),
L L1 L2 L3
=S (T)S (R)(1+H(η)). (11)
L1 L2
Here,H(η)representsaquadraticfunctionoftheNDVI.H(η)hasitsrootsatη=η
Min
and η=η . In equation (11), the term 1+H(η) modulates the survival probability of
Max
mosquitolarvaeand
H(η)=−(η−η )(η−η ). (12)
Min Max
TheuseofNDVIasafactorreflectsanecologicalunderstandingoftherelationshipbe-
tweenvegetation,environmentalconditions,andmosquitolarvaesurvival.Theformulation
isconsistentwiththeideathatNDVIservesasanindicatorofhabitatqualityformosquitoes
duringthelarvaestage[36].
Themosquitobirthrate(5)isthendefinedintermsoftemperature,rainfall,andNDVIas
N S (R)S (T,R,η)S (R)
θ (T,R,η)= E E L P ,
v χ +χ (T)+χ
E L P
64N P∗P∗P∗R3(R −R)3(e−αT+β)(1−(η−η )(η−η ))
= E E L P W Min Max .(13)
R6 (χ +χ (T)+χ )
W E L P
Thereductioninthenumberofindividualsintheclassofsusceptiblemosquitoesisdue
β a(T)I (t)
to the force of infection governed by the function λ = 2 H which occurs when
v N (t)
H
thereisabitefromsusceptiblemosquitotoaninfectioushumanpopulationI (t)andtothe
H
naturalmortalityrateofmosquitoesμ (T,η).Thenaturalmortalityrateisthenconsidered
v
asafunctionoftemperatureandvegetationindexinthismodel,wheretheformulationof
μ (T,η) is presented in (20). Hence, susceptible mosquitoes become exposed at λ rate.
v v
Theparameterλ denotestherateatwhichsusceptiblemosquitoesaregettinginfectedby
v
infectioushumanpopulationandβ istheprobabilitythataninfectedhumanwillinfecta
2
susceptiblemosquito.Therateofchangeofsusceptiblemosquitoesovertimeis
dS
V =θ (T,R,η)−(μ (T,η)+λ )S . (14)
dt v v v V
Afteraperiodt,theexposedmosquitoesprogresstotheclassofinfectedmosquitoesat
arateρ anddieduetonaturaldeathatarateμ (T,η).Hence,
v v
dE
V =λ S −(μ (T,η)+ρ )E . (15)
dt v V v v V
TheexposedmosquitoesprogresstotheclassofinfectedmosquitoesI (t)andtheclass
V
ofinfectedmosquitoesdecreasesduetothenaturaldeathofmosquitoesand
dI
V =ρ E −μ (T,η)I . (16)
dt v v v V

--- Page 7 ---
MathematicalModellingofMalariaIntegratingTemperature,Rainfall... Page7of39 5
AsNDVIincreases,itindicates healthier vegetation, whichcouldprovidemorebreed-
ingsitesandresourcesformosquitoes.Thismightleadtoanincreaseinmosquitopopula-
tions,potentiallyresultinginlowermortalityrates,thentherelationshipbetweenAnopheles
mosquito'smortalityandNDVIcanberepresentedinafunctionalformwhichdemonstrates
slowmortalitydecreaseasNDVIvaluesincrease[22].Asaresult,themathematicalfunction
definingthemortalityrateμ (T,η)is
v
μ (T,η)=p(T)∗q(η), (17)
v
where p(T) and q(η) accountfortheeffectoftemperatureandNDVIrespectivelyonthe
mortalityofmosquitoes.Wehavethat
[︁ ]︁
p(T)= C (T −T∗)2+d , (18)
T M
and
[︃ ]︃
C
q(η)= η , (19)
C +α η
η η
withC beingtheamplitudeofthemortalityfunctionandcontrollinghowmuchmortality
T
rate can vary with temperature, T∗ is the minimum temperature at which mosquitoes are
M
mostlikelytosurviveandhavethelowestmortalityrate[33],distheminimumvalueofthe
function,C isthesaturationparameterandα isaconstant.Thisyields,
η η
[︃ ]︃
[︁ ]︁ C C (d+C (T −T∗)2)
μ (T,η)= C (T −T∗)2+d η = η T M . (20)
v T M C +α η C +α η
η η η η
Wedenotethetotalpopulationforhumansandmosquitoesby N (t)=S (t)+E (t)+
H H H
I (t)+R (t)andN (t)=S (t)+E (t)+I (t)respectively.Furthermore,weassume
H H V V V V
that all newbornhumansandmosquitoesaresusceptibletotheinfection. Wealsoassume
thatinfectedmosquitoesremaininfectedalltheirlife[37].Weillustratethemodelsystem
inFig.1.
Thedynamicsoftransmissionofmalariabetweenhumansandmosquitoesarethende-
scribedbythefollowingsystemofnonlinearordinarydifferentialequations.
...
withthefollowinginitialconditions:
S (0)=S0 >0,E (0)=E0 ≥0,I (0)=I0 ≥0,R (0)=R0 ≥0,
H H H H H H H H

--- Page 8 ---
5 Page8of39 K.J.GatoreSinigiriraetal.
Fig.1 Flowdiagramforthetransmissiondynamicsofmalaria.Thediagramshowsthecompartmentalrela-
tionsbetweenthehumanhostandmosquitopopulations
S (0)=S0 >0,E (0)=E0 ≥0,I (0)=I0 ≥0. (22)
V V V V V V
ThevariablesandparametersusedinthemodelaredescribedinTable1.
2.2 ModelProperties
Inthissection,wecarryoutmathematicalmodelanalysiswithoutincorporatingparameters
thatrelyonclimateconditions.Weshowthatthemodelismathematicallyandbiologically
meaningful.Todothis,wedefineθ (T,R,η),μ (T,η),anda(T)asfunctionswithmaxi-
v v
mumvaluesrepresentedbyθ ,μ ,anda,respectivelyand,θ (T,R,η)≤θ ,μ (T,η)≤μ ,
v v v v v v
anda(T)≤a.
2.2.1 FeasibleRegion
Theorem1 (Positivity)ThesolutionsS (t),E (t),I (t),R (t),S (t),E (t),I (t)ofthe
H H H H V V V
model(21)arenon-negativeforallt≥0giventheinitialconditions(22).
...
2.2.2 ModelAnalysis
Here,weexamineandanalyzethemodelstabilityofequilibriumpoints.
Disease-FreeEquilibrium(DFE)Points TheDFEexistswhenthereisnodiseaseinthehuman
andmosquitopopulations.Forthemodelsystemunderanalysis,themalariafreeequilibrium
pointE is
0
(︃ )︃
α θ
E = h,0,0,0, v ,0,0 . (29)
0 μ μ
h v

--- Page 11 ---
MathematicalModellingofMalariaIntegratingTemperature,Rainfall... Page11of39 5
ReproductionNumber We use the next-generation matrix approach described in [38, 39]
to find the reproduction number R . The reproduction number is defined as the average
0
numberofsecondaryinfectionscausedbyasingleinfectiousindividualinapopulationof
susceptibleindividuals.Thebasicreproductionnumberdetermineshowsevereadiseasecan
become,whetheritcanleadtoanepidemicorpandemic,orifitwilldieout.Itcanalsobe
consideredasameasureofthestrengthoftransmissionintensityforthedisease[40],and
hasbeenestimatedfrombothmathematicalmodelsanddatabymanyresearchersoverthe
years[41,42]
ItcanbeshownthatifR >1,anepidemicoccurswhichsuggeststhatthediseasecan
0
sustain transmission in the population. On the other hand, if R <1 then no epidemic is
0
likelytooccur.Consequently,reducingR below1iskeytomalariacontroleffortstopre-
0
ventandmanageoutbreaks.
TheNGMisthematrixproductofthenewinfectionmatrix(F)andtheinverseofthe
transitionmatrix(V).Thespectralradius(ρ)oftheNGMisthedominanteigenvalue,which
isequaltoR .
0
...
√︄
β β a2ρ ρ θ μ √︁
R =ρ(FV−1)= 1 2 h v v h = R ∗R (34)
0 μ2α b b b 0h 0h
v h 1 2 3
where
b =ρ +μ ,b =μ +γ +δ,b =μ +ρ .
1 h h 2 h h 3 v v
and
β aρ μ β aρ θ
R = 1 h h,R = 2 v v
0h α b b 0v μ2b
h 1 2 v 3

--- Page 13 ---
MathematicalModellingofMalariaIntegratingTemperature,Rainfall... Page13of39 5
LocalStabilityoftheDFE Thelocalstabilityofthediseasefreeequilibriumpoint(DFE)can
beshownthroughthelinearizedformof(21)evaluatedatE .
0
Theorem3 TheDFEE islocallyasymptoticallystableifR <1andunstableifR >1
0 0 0
...
GlobalStabilityoftheDFE The Global stability of the DFE can be established using the
approachdescribedbyChavezin[44].AstheDFEislocallyasymptoticallystablewhenever
R <1 and unstable when R >1, we provide two requirements that must be satisfied to
0 0
ensurethatthedisease-freestateisgloballyasymptoticallystable.

--- Page 15 ---
MathematicalModellingofMalariaIntegratingTemperature,Rainfall... Page15of39 5
ExistenceoftheEndemicEquilibriumPoint TheendemicequilibriumpointEE∗ isdefined
as the steady solution when the disease persists in the population. For the model (21) the
endemicequilibriumpointisgivenbyEE∗=(S∗,E∗,I∗,R∗,S∗,E∗,I∗)computedby
H H H H V V V
settingtheright-handsidesofthemodeltozero...

--- Page 17 ---
MathematicalModellingofMalariaIntegratingTemperature,Rainfall... Page17of39 5
BifurcationAnalysis We performed the center manifold theory developed by Chavez and
Song in [46] to investigate the Bifurcation analysis. This theory is used to investigate the
presenceofbothbackwardandforwardbifurcations.Forwardbifurcationoccurswhenthe
endemicequilibriumislocallyasymptoticallystableforR >1butR approaches1.
0 0
...
• IfA >A ,wehaveA>0andB>0thensystem(21)willundergoabackwardbifurca-
1 2
tionatR =1.
0
• IfA <A ,wehaveA<0andB>0thensystem(21)willundergoaforwardbifurcation
1 2
atR =1.
0

--- Page 19 ---
MathematicalModellingofMalariaIntegratingTemperature,Rainfall... Page19of39 5
2.3 StudyAreaandDataProcessing
Burundi,alandlockedcountryinEastAfrica,isborderedbyRwandatothenorth,Tanzania
to the east and south, and the Democratic Republic of the Congo to the west. Positioned
between latitudes 2.3°S and 4.5°S, and longitudes 29°E and 31°E, Burundi exhibits a di-
verseclimate,rangingfromtemperatehighlandstotropicallowlands.Thedatautilizedin
thisstudyincludethreemainsources.Firstly,theclimatedataemployedforanalysisinthis
studyweresourcedfromtheIGEBU(BurundiGeographicalinstitute)database,from2010
to2022.Thisdataset,consistingofmonthlyrecords,providedcrucialinformationregarding
climaticparameterssuchastemperatureandRainfall.Theutilizationofdataoverthistime
periodallowedforacomprehensiveexaminationoflong-termclimatetrendsandpatterns,
enablingadeeperunderstandingofthedynamicsandfluctuationswithinBurundi.Secondly,
thereisacollectionoftimeseriesdataderivedfromthemoderate-resolutionImagingSpec-
troradiometer(Modis).NDVIdatawasgeneratedusingtheGoogleEarthEngine(GEE),a

--- Page 20 ---
5 Page20of39 K.J.GatoreSinigiriraetal.
Fig.2 Country-levelmeanmonthlytemperature,meanmonthlyrainfall,NDVIdata,andconfirmedmalaria
casespermonthfrom2010to2022
platform for satellite data collection from the MODIS/006/MCD43A4 surface reflectance
compositesonamonthlybasiswithaspatialresolutionof500meters,spanningfrom2010
to2022[47].Figures2ato2cdisplaythetemperature,rainfallandNDVIdistributionacross
Burundi.ThedataofconfirmedmalariacasesusedareobtainedfromtheIntegratedNational
MalariaControlProgram(INMCP).
Correlation analysis is a statistical technique used to measure the strength and direc-
tionoftherelationshipbetweentwoormorevariables.Inthiscontext,correlationanalysis
was applied to assessthe relationship between NDVI,precipitation, and temperature. The
results are developed in the appendix Sect. A. To predict the reproduction number accu-
rately, we utilized forecasting data for temperature, rainfall, and NDVI. This forecasting
was conducted using the Seasonal Autoregressive Integrated Moving Average (SARIMA)
model [48]. SARIMA is a statistical technique used for time series analysis, particularly
forforecastingfuturevaluesbasedonhistoricaldata.ByapplyingSARIMAtothehistor-
ical data of temperature, rainfall, and NDVI, we were able to project their future trends,
whichareessentialinputsforpredictingthereproductionnumberinourmodel(Detailsare
inappendixSect.B).

--- Page 21 ---
MathematicalModellingofMalariaIntegratingTemperature,Rainfall... Page21of39 5
3 NumericalSimulationoftheModelwithClimate-Dependent
Parameters
3.1 ParameterEstimation
Estimatingtheparametersinourmodeliscrucialforconductingeffectivenumericalanal-
ysis,ensuringthatourresultsarebothmeaningfulandreliable.Thisinvolvesdetermining
thespecificvaluesofthevariableswithinthemodelsothatwhennumericalanalysisisper-
formed,theoutcomesaccuratelyreflectrealworldconditions.Toachievethis,weemployed
modelcalibrationtechniquestoestablishidealrepresentationcurvesforeachstatevariable,
aiming to closely approximate their values. In our study, we focus on a scenario where
thepopulationofhumansinBurundihasstabilized,withapopulation-to-mortalityratioof
α /μ =12,890,000,andanaveragelifeexpectancyof62.37yearsforhumansinBurundi.
h h
Accordingly, the mortality rate and recruitment rate are calculated as 1/(62.37∗12) and
α =0.0013∗12,890,000permonth,respectively[49].Foroursimulations,wesetinitial
h
conditionsasfollows:
S (0)=12,590,000,E (0)=0,I (0)=200,000,R (0)=100,000,
H H H H
S (0)=15,000,000,E (0)=0,I (0)=250,000.
V V V
Weappliedtheleastsquaresmethodtofitthecumulativeincidenceequationofthemodel
tothecumulativemalariadatafrom2010to2022(Fig.3),initializingtheparameterswith
theinitialvaluesderivedfromthebaselinegraphs(seeFig.9).
AllparametersusedinthesimulationsaredetailedinTable3.
3.2 SensitivityAnalysis
The Latin Hypercube Sampling method(LHS) and Partial Rank Correlation Coeffi-
cients(PRCC)areusedtocarryouttheglobalsensitivityanalysis[51].Sensitivityanalysisis
indeedacrucialtoolinunderstandinghowuncertaintyinmodelinputsaffectstheoutputof
asystem.Initially,weperformsensitivityanalysisusingdatacoveringthespecifiedranges
and baseline values for temperature, rainfall, and NDVI-dependent parameters (Table 4).

--- Page 22 ---
5 Page22of39 K.J.GatoreSinigiriraetal.
Table3 Parametervaluesand
references Parameter Value Reference Parameter values Reference
αh 17,635 calculated χP 1 [13]
1 ∗
q [50] T 16 [33]
20∗12 M
β1 0.45 estimated PE 0.93 [32]
μh 0.001336 calculated PL 0.25 [32]
ρh 0.89 estimated PP 0.75 [32]
γh 0.20 estimated α 0.05547 [33]
δ 0.005 estimated β 0.06773 [33]
β2 0.35 estimated Rw 50mm [13]
ρv 0.025 estimated CT 0.0009 estimated
NE 200 [13] d 0.05 estimated
χE 1 [13] Cη 0.0007 estimated
αη 0.06 estimated
...
3.3 SimulationResults
3.3.1 Temperature,RainfallandNDVIEffectsontheModel
Figure9presentsthebaselinegraphsderivedfromthemathematicalmodel(21).Thesim-
ulations are conducted under specific conditions where climate parameters remain fixed.
Specifically,thetemperature(T)issetat25°C,rainfallat30mm,andtheNormalizedDif-
ferenceVegetationIndex(η)at0.4.Thesesimulationswerecarriedoutoveraperiodof100
months.
...
As shown in Fig. 10, the number of infected humans (I ) peaks and then gradually
H
decreasesatatemperatureofT=25°C(consistentwiththefindingsin[14,32]),suggesting
that this temperature represents an optimal condition for malaria transmission dynamics.

--- Page 26 ---
5 Page26of39 K.J.GatoreSinigiriraetal.
...
InFig.12,wewereexaminingtheimpactofNDVI.WefoundthatNDVIhasagreaterin-
fluenceonthemodelcomparedtorainfall.ThiscanbeexplainedbythefactthatVegetation

--- Page 27 ---
MathematicalModellingofMalariaIntegratingTemperature,Rainfall... Page27of39 5
influencesnotonlytheavailabilityofbreedingsitesbutalsothemicroclimate(humidityand
temperature), which can affect mosquito survival and reproduction. In regions with dense
vegetation,evenifrainfallisinconsistent,mosquitoescanstillfindsuitableconditionsfor
reproduction [54]. This might make NDVI a more consistent and powerful predictor than
rainfallinthemodel.WhenNDVIincreasesfrom0.2to0.8,weobserveanincreaseinin-
fectiousindividuals,bothhumansandmosquitoesrespectively.Weobservedahighnumber
in the infected individuals in the range of [0.4-0.6]. The level of vegetation (NDVI) in an
areaseemstohaveastrongerimpactonthemodel'spredictionsthantheamountofrainfall.

--- Page 28 ---
5 Page28of39 K.J.GatoreSinigiriraetal.
...
Whencombiningtemperaturewithrain-
fallorNDVI(seeFig.13andFig.14),weobservesignificantchangesinthetransmission
dynamicsofmalaria.ButwhenrainfallwascombinedwithNDVI(Fig.15),thealterations
intransmissiondynamicsofmalariawererelativelysmall.Withlowtemperaturescombined
tolowrainfallorlowNDVI,theinfectedpopulationsremainnearlyconstant.
...
Asthetemperaturerises,boththeinfectedhuman
and mosquitopopulations begin to decrease. The number of cases in the infection classes
reachedtheirpeakatatemperaturevaluerangeof[20-25°C],inconjunctionwithamean
monthlyrangeof[20-30mm]andNDVIrangeof[0.4-0.6].

--- Page 30 ---
5 Page30of39 K.J.GatoreSinigiriraetal.
Inthe scenariowheretemperature, rainfall, and NDVI are all fluctuating, we observed
that where all three variables are low, the infection classes remain relatively constant, but
they begin to increase as the values of temperature, rainfall, and NDVI increase. This in-
creasebecomesmorepronounced,ultimatelyreachingamaximumatatemperatureof35,
rainfallof45mm,andanNDVIvalueof0.8(Fig.16).
3.4 ForecastingTemporalTrendsintheReproductionNumber
...
Figure 17 shows an increase in R over time from 2010 to 2070, indicating that the
0
diseaseisbecomingmoretransmissibleovertime.Thisisconcerningbecauseahigherre-
production number means that more people are likely to be infected, leading to a larger
outbreakorepidemicifeffectivecontrolmeasuresarenotputinplace.

--- Page 31 ---
MathematicalModellingofMalariaIntegratingTemperature,Rainfall... Page31of39 5
3.5 DiscussionofResults
...
Numericalsimulationswerecarriedoutonthemodeltoinvestigatetheinfluenceoftem-
perature,rainfallandNDVIonmalariatransmission.Weusedmonthlyscaleaschangesin
vegetationcannotbeseendailyorweekly.Meanmonthlytemperaturerangesfrom15°Cto
35°Cwereused,revealingthatmalariatransmissionismosteffectiveintherangeof[20-
25°C],aligningwithpreviousresearch[32,60],whenrainfallandNDVIareconstant.Mean
monthlyrainfallvaluesbelow50mmwereexamined,consideringthatmosquitobreeding
sitesareflushedoutwithrainfallexceeding50mm[13].Despitechangesinrainfalllevels,
onlyminordifferencesinpopulationsareobserved.Thesimulationresultsshowedthatrain-
fallhaslittleimpactonmalariatransmissiondynamicsinBurundi.MonthlyNDVIvalues

--- Page 32 ---
5 Page32of39 K.J.GatoreSinigiriraetal.
from 0.2 to 0.8 were considered in simulations whereas temperature and rainfall are con-
stants. The results showed that NDVI range of [0.4-0.6] is the most favorable to malaria
transmission. A study in Uganda showed that the average NDVI of 0.72 significantly in-
creasedthecumulativeincidencerateratio(IRR)ofmalaria[61].Ourstudyseemstosug-
gest that the addition of temperature and rainfall in the model would require slightly less
NDVIlevelstoincreasethetransmissionofmalaria.Theincreaseofallthethreevariables
temperature,rainfallandNDVIledtoanincreaseininfectioncases.Thiscouldpotentially
indicateacorrelationbetweenenvironmentalconditionsandthespreadofinfections.
...
We also used the reproduction number (R ) as a fundamental measure to assess how
0
climate variations affect the dynamics of malaria transmission. Specifically, we examined
theimpactoftemperature,rainfall,andNDVIonR andsubsequentlyonthetransmission
0
of malaria dynamics. Through the analysis of climate projections for the period between
2021 and 2070, our aim was to predict potential changes in the severity of malaria using
the values of R . Our results indicated a significant increase in R over time, suggesting
0 0
a rise in the ability of the disease to spread in future. Interventions such as spraying and
utilizingtreatedbednets,whichaidinreducingmosquitopopulations,shouldbepromoted,
particularlyinthetimewhenreproductionnumberishighandwhenclimaticconditionsare
conduciveformosquitobreeding.Theseresultsunderscorethethreatoflargeroutbreaksor
epidemicsinthefuture,emphasizingtheurgentnecessityforeffectivestrategiestomitigate
malariatransmissioninresponsetoevolvingclimateconditions.
...
AppendixA: CorrelationAnalysis
...
AppendixB: ForecastingData:NormalizedVegetationIndex
...
B.1 ModelIdentification
WefoundthattheMeanAbsoluteError(MAE)ofapproximately0.01675andtheR-squared
(rsquare)valueofapproximately0.9344provideinsightfulmetricsforassessingtheperfor-
manceoftheSARIMAmodelonthevalidatedsetspanningfromJanuary2020toDecember
2022.TheseresultscollectivelyindicatethattheSARIMAmodelperformswellinforecast-
ingNDVIvalues.

--- Page 36 ---
5 Page36of39 K.J.GatoreSinigiriraetal.
Acknowledgements ...
References
1. Djihinto,O.Y.,Medjigbodo,A.A.,Gangbadja,A.R.A.,Saizonou,H.M.,Lagnika,H.O.,Nanmede,D.,
Djossou,L.,Bohounton,R.,Sovegnon,P.M.,Fanou,M.-J.,etal.:Malaria-transmittingvectorsmicro-
biota:overviewandinteractionswithanophelesmosquitobiology.Front.Microbiol.13,891573(2022)
...
61. Okiring,J.,Routledge,I.,Epstein,A.,Namuganga,J.F.,Kamya,E.V.,Obeng-Amoako,G.O.,Sebuguzi,
C.M.,Rutazaana,D.,Kalyango,J.N.,Kamya,M.R.,etal.:Associationsbetweenenvironmentalcovari-
atesandtemporalchangesinmalariaincidenceinhightransmissionsettingsofUganda:adistributedlag
nonlinearanalysis.BMCPublicHealth21,1–11(2021)
...
Publisher'sNote SpringerNatureremainsneutralwithregardtojurisdictionalclaimsinpublishedmapsand
institutionalaffiliations.
(Full 39-page OCR text available in the original source PDF.)
