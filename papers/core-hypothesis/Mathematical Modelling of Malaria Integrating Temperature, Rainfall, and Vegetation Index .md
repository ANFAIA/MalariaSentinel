# Mathematical Modelling of Malaria Integrating Temperature, Rainfall, and Vegetation Index 

**Source PDF:** `Mathematical Modelling of Malaria Integrating Temperature, Rainfall, and Vegetation Index .pdf`  
**Path:** `papers/core-hypothesis/Mathematical Modelling of Malaria Integrating Temperature, Rainfall, and Vegetation Index .pdf`  

---

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
dynamicscalibratedwiththeBurundicase’sstudy.Mathematicalanalysisexploredtheequi-
libria, stability, and computation of the model’s threshold values. Numerical simulations
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
proximate population of 12,890,000, it is estimated that 80% of the Burundi’s population
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
behaviorarecausingshiftsinthedisease’sprevalence[8].
Inthepasttwodecades,analysisoftheuniversaldistributionofthediseaseshowsthatit
ismoreconcentratedinwarmregions.However,duetoclimatechangeandglobalwarming,
formerly sheltered areas are now being invaded. Climate plays a vital role in the increase
inmalariatransmissioninAfricabecausetemperatureandrainfalllevelsarepredominantly
high compared to other continents [10]. The increment in the number of mosquitoes de-
pends on the climatic conditions and the accessibility of oviposition sites, which in turn
are subordinate to natural and environmental factors [11]. Several authors have shown
thatenvironmentalandclimaticfactorssignificantlyinfluencethedynamictransmissionof
malaria[12–14].Duringhightemperatures,themosquitoes’digestivesystemsbecomeagile
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
between the electromagnetics spectrum’s near Infrared (NIR) and red bands. The NDVI
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
resultsshowedthatthemosquito’slifespanisacriticalfactorinthetransmissionofmalaria.
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
(ODE’s)wherehumansandmosquitoesinfecteachother.
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
as pupae are also found at the water’s surface. For all these reasons, the larvae stage is
highly affected by NDVI primarily by affecting the quality of their breeding habitats [34,
35].AreaswithhighNDVIvaluesindicatedenserandhealthiervegetationwhicharemore
likely to provide suitable conditions for mosquito larvae to develop and grow, including
cooler temperatures, food sources, and protection from predators. Conversely, areas with
lowerNDVIvaluesmayleadtolessfavorableconditions,potentiallyreducingthesurvival

--- Page 6 ---
5 Page6of39 K.J.GatoreSinigiriraetal.
probability of mosquito larvae [34, 35]. Hence, following all of these ideas, we included
the NDVI’s effect in the model by formulating a new mathematical function defining the
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
mosquito’smortalityandNDVIcanberepresentedinafunctionalformwhichdemonstrates
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
⎧
⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎨
d
d
d
E
d
d
d
S
I
t
t
H
H
H
t
=
=
=
α
λ
ρ
h
h
h
E
S
+
H
H
q
−
−
R
(
H
(
ρ
μ
h
−
h
+
+
λ
h
μ
γ
S
h
h
H
)
+
E
−
H
δ
μ
,
)I
h
H
S
,
H
,
dRH =γ I −(μ +q)R , (21)
⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎩
d
d
d
d
E
d
S
t
t
t
V
V
=
=
θ
λ
v
h
v
(
S
T
H
V
,
−
R,
(
η
μ
)
h
v
−
(T
(
,
μ
η
v
)
(
+
H
T,
ρ
η
v
)
)E
+
V
λ
,
v
)S
V
,
dIV =ρ E −μ (T,η)I ,
dt v v v V
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
Proof Given that the initial values of the model’s variable are nonnegative for t ≥0, we
first show that S (t) is positive. We assume that there exists an initial time t such that
H 1
S (t )=0,S′ (t )≤0and
H 1 H 1
E (t )>0,I (t )>0,R (t )>0,S (t )>0,E (t )>0,I (t )>0. (23)
H 1 H 1 H 1 V 1 V 1 V 1
⃓
⃓
Wehave d d S t H⃓ ⃓ =α h +qR H (t 1 )>0whichisacontradictiontoourassumption,hence
S (t)remainsn
t=
on
t1
-negativeforallt≥0.
H
Secondly,weshowthatE (t)isalsopositiveforallt ≥0.Supposethatthereexistan
H
initialtimet suchthatE (t )=0,E′ (t )<0and
2 H 2 H 2
S (t )>0,I (t )>0,R (t )>0,S (t )>0,E (t ),I (t )>0. (24)
H 2 H 2 H 2 V 2 V 2 V 2

--- Page 9 ---
MathematicalModellingofMalariaIntegratingTemperature,Rainfall... Page9of39 5
Table1 Descriptionofstatesvariablesandparametersofthebasicmalariamodel
Variable Description Unit
SH SusceptibleHumanspopulation people
EH Exposedhumanspopulation people
IH Infectedhumanspopulation people
RH Recoveredhumanspopulation people
SV Susceptiblemosquitopopulation mosquitoes
EV Exposedmosquitopopulation mosquitoes
IV Infectedmosquitopopulation mosquitoes
Parameter Description Unit
αh Recruitmentrateofhumanpopulations people/time
q Rateoflossofimmunity time
−1
β1 Probabilityoftransmissionofmalariafromaninfectiousvector dimensionless
toasusceptiblehumanpercontact.
a(T) Mosquitobitingrate time
−1
μh Naturalmortalityrateofhumanpopulation time
−1
μv(T,η) Mortalityrateofmosquitoes time
−1
ρh ProgressionrateofhumanpopulationfromEH toIH time
−1
γh ProgressionrateofhumanpopulationfromIH toRH time
−1
δ Diseaseinduceddeathrate time
−1
θv(T,R,η) Recruitmentrateofmosquitoes mosquito/time
β2 Probabilityoftransmissionofmalariafromaninfectioushuman dimensionless
toasusceptiblevectorpercontact.
ρv ProgressionrateofmosquitopopulationfromEV toIV time
−1
⃓
⃓
Wehave d d E t H⃓ ⃓ =λ h (t 2 )S H (t 2 )>0 whichisacontradiction toourassumption,hence
E (t)remainsn
t
o
=
n
t2
-negativeforallt≥0.Usingasimilarapproach,itcanbeshownthatthe
H
model’sotherstatevariablesremainpositiveforallt≥0. □
Theorem2 (Boundedness)Giventheinitialvaluesofthevariablesofthemodelsystem(21)
that are S0 >0, E0 ≥0, I0 ≥0, R0 ≥0, S0 >0, E0 ≥0, I0 ≥0. The solution of the
H H H H V V V
model(21)areuniformlyboundedwithintheregion
Ω={(S (t),E (t),I (t),R (t),S (t),E (t),R (t))
H H H H V V V
α θ
∈ℝ7|0≤N (t)≤ h,N (t)≤ v }.
+ H μ V μ
h v
Proof Toprovethatthesolutionofmodelsystem(21)areuniformlyboundedwithinΩlet
assumethat((S (t),E (t),I (t),R (t),S (t),E (t),I (t))isthesolutionofthemodel.
H H H H V V V
IfN (t)=S (t)+E (t)+I (t)+R (t)andN (t)=S (t)+E (t)+I (t)then
H H H H H V V V V
dN (t)
H =α−μ N (t)−δI (t)
dt h H H
≤α−μ N (t), sinceI (t)≥0, (25)
h H H

--- Page 10 ---
5 Page10of39 K.J.GatoreSinigiriraetal.
and
dN (t)
V =θ −μ N (t). (26)
dt v V V
Usingtheintegratingfactortosolvethedifferentialinequality(25)andequation(26)we
foundthat
(︃ )︃
α α
N (t)≤ h + N0 − h e−μht, (27)
H μ H μ
h h
(︃ )︃
θ θ
N (t)= v + N0− v e−μvt. (28)
V μ v μ
v v
If
α
• N
H
(t)=S
H
(t)+E
H
(t)+I
H
(t)+R
H
(t)then,lim t→∞supN
H
(t)≤
μ
h.
h
θ
• N
V
(t)=S
V
(t)+E
V
(t)+I
V
(t)then,lim t→∞supN
V
(t)≤
μ
v .
v
ASt→∞,
α
N approaches h,
H μ
h
and
θ
N = v .
V μ
v
Then,
α
N (t)=S (t)+E (t)+I (t)+R (t)≤ h,
H H H H H μ
h
and
θ
N =S (t)+E (t)+I (t)= v .
V V V V μ
v
Att=0,
N (0)≥0andN (0)≥0.
H V
α θ
Therefore,0≤N (t)≤ h,0≤N (t)≤ v andsinceallsolutionsinℝ7 areuniformly
H μ V μ +
h v
bounded,Ωisafeasibleregionforthemodel(21). □
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
Let f representstherateofnewinfections,while v denotesthetransitiontermsinour
model. Their corresponding Jacobian matrices, F and V, are derived by linearizing the
systemaroundtheDFEE .
0
Specifically,wehave:
⎛ ⎞ ⎛ ⎞
λ S (ρ +μ )E
h H h h H
f = ⎜ ⎜ ⎝ λ 0 S ⎟ ⎟ ⎠ ; v= ⎜ ⎜ ⎝ (μ h + ( δ μ + + γ h ρ )I H )E −ρ h E H ⎟ ⎟ ⎠. (30)
v V v v V
0 μ I −ρ E
v V v V
F andV aregivenby:
⎛ ⎞ ⎛ ⎞
0 0 0 β 1 a ρ +μ 0 0 0
F = ⎜ ⎜ ⎜ ⎝ 0 0 β 2 a 0 θ v μ h 0 0 0 0 ⎟ ⎟ ⎟ ⎠ andV = ⎜ ⎜ ⎝ h − 0 ρ h h μ h + 0 δ+γ h μ + 0 ρ 0 0 ⎟ ⎟ ⎠(.31)
μ v α h 0 0 v −ρ v μ
0 0 0 0 v v
TheinverseofV is:
⎛ ⎞
1
⎜ ⎜ ρ h +μ h 0 0 0 ⎟ ⎟
⎜ ρ 1 ⎟
⎜ h 0 0 ⎟
V−1= ⎜ ⎜(ρ h +μ h )(μ h +δ+γ h ) μ h +δ+γ h ⎟ ⎟, (32)
⎜ 1 ⎟
⎜ 0 0 0 ⎟
⎜ μ +ρ ⎟
⎝ v v ⎠
ρ 1
0 0 v
μ (μ +ρ ) μ
v v v v
⎛ ⎞
β aρ β a
0 0 1 v 1
⎜ ⎜ μ v b 3 μ v ⎟ ⎟
FV−1= ⎜ ⎜ 0 0 0 0 ⎟ ⎟, (33)
⎜β aρ θ μ β aθ μ ⎟
⎝ 2 h v h 2 v h 0 0 ⎠
μ α b b μ α b
v h 1 2 v h 2
0 0 0 0

--- Page 12 ---
5 Page12of39 K.J.GatoreSinigiriraetal.
and,
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
LocalStabilityoftheDFE Thelocalstabilityofthediseasefreeequilibriumpoint(DFE)can
beshowntroughthelinearizedformof(21)evaluatedatE .
0
Theorem3 TheDFEE islocallyasymptoticallystableifR <1andunstableifR >1
0 0 0
Proof TheJacobianmatrixofthemodelatE isgivenby
0
⎛ ⎞
−μ 0 0 q 0 0 −β a
h 1
⎜ ⎜ 0 −b 1 0 0 0 0 β 1 a ⎟ ⎟
⎜ ⎜ 0 ρ h −b 2 0 0 0 0 ⎟ ⎟
⎜ ⎜ 0 0 γ h −(μ h +q) 0 0 0 ⎟ ⎟
J(E )=⎜ −β aθ μ ⎟ (35)
0 ⎜ 0 0 2 v h 0 −μ 0 0 ⎟
⎜ ⎜ α h μ v v ⎟ ⎟
⎜ β aθ μ ⎟
⎝ 0 0 2 v h 0 0 −b 0 ⎠
α μ 3
h v
0 0 0 0 0 ρ −μ
v v
TheJacobianmatrixhastwocolumnswithdiagonalentriesHence,−μ and −μ are
h v
twooftheeigenvaluesofthematrix(35)withnegativerealparts.Tofindotherslet’sreduce
theJacobianmatrixbyeliminatingthefirstandfifthcolumnsandthecorrespondingrowsto
thesediagonalentries,Wefind
⎛ ⎞
−b 0 0 0 β a
1 1
⎜ ρ −b 0 0 0 ⎟
⎜ h 2 ⎟
J (E )= ⎜ ⎜ 0 γ h −(μ h +q) 0 0 ⎟ ⎟ (36)
1 0 ⎜ β aθ μ ⎟
⎝ 0 2 v h 0 −b 0 ⎠
α μ 3
h v
0 0 0 ρ −μ
v v
Usingthesameapproachforthethirdcolumnwefindanothereigenvalue−(μ +q)with
h
negativerealpartsand(36)becomes:
⎛ ⎞
−b 0 0 β a
1 1
⎜ ρ −b 0 0 ⎟
⎜ h 2 ⎟
J 2 (E 0 )=⎜ ⎝ 0 β 2 aθ v μ h −b 0 ⎟ ⎠ (37)
α μ 3
h v
0 0 ρ −μ
v v

--- Page 13 ---
MathematicalModellingofMalariaIntegratingTemperature,Rainfall... Page13of39 5
To check if the remaining eigenvalues have the negative real parts and ensure the local
stability when R <1, we will use Routh-Hurwitz conditions to see if they are sufficient
0
andnecessary[43].Thepolynomialcharacteristicequationof(37)is
λ4+(b +b +b +μ )λ3+(b b +b b +b b +b μ +b μ +b μ )λ2
1 2 3 v 1 2 1 3 2 3 1 v 2 v 3 v
β β a2ρ ρ θ μ
+(b b b +b b μ +b b μ +b b μ )λ+b b b μ − 1 2 v h v h =0 (38)
1 2 3 1 2 v 1 3 v 2 3 v 1 2 3 v α μ
h v
Weset
J =b +b +b +μ ,
3 1 2 3 v
J =b b +b b +b b +b μ +b μ +b μ ,
2 1 2 1 3 2 3 1 v 2 v 3 v
J =b b b +b b μ +b b μ +b b μ ,
1 1 2 3 1 2 v 1 3 v 2 3 v
β β a2ρ ρ θ μ
J =b b b μ − 1 2 v h v h,
0 1 2 3 v α μ
h v
=b b b μ (1−R2),
1 2 3 v 0
whereJ >0,J >0,J >0andJ >0iffR <1.TheHurwitzdeterminantsaregivenby:
3 2 1 0 0
det(H )=J =b +b +b +μ >0,
1 3 1 2 3 v
⃓ ⃓
⃓ ⃓
det(H 2 )=⃓ ⃓ J J 3 J 1 ⃓ ⃓ =J 3 J 2 −J 1
1 2
=b2(b +b +μ )+b2(b +b +μ )+b2(b +b +μ )+μ2(b +b +b )
1 2 3 v 2 1 3 v 3 1 2 v v 1 2 3
+2b b b +2μ (b b +b b +b b )>0
1 2 3 v 1 2 1 3 2 3
⃓ ⃓
⃓ ⃓
⃓J 3 1 0 ⃓
det(H 3 )=⃓ ⃓ ⃓ J 1 J 2 J 3 ⃓ ⃓ ⃓ =J 1 (J 3 J 2 −J 1 )−J 3 2J 0
0 J J
0 1
=(b +b +b +μ )[(b2(b +b +μ )+b2(b +b +μ )+b2(b +b +μ )
1 2 3 v 1 2 3 v 2 1 3 v 3 1 2 v
+μ2(b +b +b )+2μ (b b +b b +b b )+2b b b )
v 1 2 3 v 1 2 1 3 2 3 1 2 3
+((b +b +b +μ )(b b b μ (1−R2)))]>0 iffR <1
1 2 3 v 1 2 3 v 0 0
⃓ ⃓
⃓ ⃓
⃓J 3 1 0 0 ⃓
⃓ ⃓
det(H 4 )=⃓ ⃓ ⃓ J 0 1 J J 2 0 J J 3 1 J 1 2 ⃓ ⃓ ⃓ =J 0 H 3 >0.
⃓ ⃓
0 0 0 J
0
AllofthedeterminantsoftheHurwitzmatricesarepositiveimplyingthatalltheeigen-
values have a negative real part. Thus, the DFE E is local asymptotically stable (LAS)
0
whenR <1andunstableR >1. □
0 0
GlobalStabilityoftheDFE The Global stability of the DFE can be established using the
approachdescribedbyChavezin[44].AstheDFEislocallyasymptoticallystablewhenever
R <1 and unstable when R >1, we provide two requirements that must be satisfied to
0 0
ensurethatthedisease-freestateisgloballyasymptoticallystable.

--- Page 14 ---
5 Page14of39 K.J.GatoreSinigiriraetal.
Thus,were-write(21)intheform
⎧
⎪⎪⎨ dX
=F(X,Y)
dt
(39)
⎪⎪⎩
dY
=G(X,Y), G(X,0)
dt
whereX∈ℝ2 representsthenumberofsusceptibleindividualsandsusceptiblemosquitoes
+
and Y ∈ℝ4 isthenumberofexposedhumans,infected humans,exposedmosquitoes,in-
+
fected mosquitoes. U =(u ,0) denotes the DFE. To guarantee the global stability of the
0 0
DFE,theconditions(A )and(A )belowmustbesatisfied:
1 2
dX
(A ) For =F(x,0), U isgloballyasymptoticallystable(GAS).
1 dt 0
(A ) G(X,Y)=AY −G ˆ (X,Y), G ˆ (X,Y)≥0for(X,Y)∈Ωthefeasibleregionofthe
2
model.
dG(u ,0)
A= 0 isaM−matrix.AM-matrixisamatrixwithalltheoff-diagonalelements
dy
thatarenon-negativeandtherealpartofeveryoneofitseigenvaluesisgreaterthanorequal
tozero.
Corollary1 [44]Theequilibriumpointu of (39)isGASequilibriumifR ≤1.
0 0
Theorem4 Thesteady-stateE isGASifR <1
0 0
(︃ )︃
α θ
Proof X=(S ,S )T,Y =(E ,I ,E ,I )T and,u = h, v .
H V H H V V 0 μ μ
h v
α
For the first requirement, from (27) and (28) as t →∞, we have S (t)→ h and
H μ
h
θ
S (t)→ v .
V μ
v
dS (t)
Then, u is a globally asymptotically equilibrium point as the solution of H and
0 dt
dS (t)
v convergetothispoint.
dt
(︃ )︃
dX α −μ S
=F(X,0)= h h H , (40)
dt θ v −μ v S V
and
⎛ ⎞
λ S −(ρ +μ )E
h H h h H
d d Y t =G(X,Y)= ⎜ ⎜ ⎝ ρ h λ E v H S V − − (μ (μ h v + + γ h ρ v + )E δ) V I H ⎟ ⎟ ⎠, (41)
ρ E −μ I
v V v V
⎛ ⎞
−(ρ +μ ) 0 0 β a
h h 1
⎜ ρ −(μ +γ +δ) 0 0 ⎟
dG(u ,0) ⎜ h h h ⎟
A= dt 0 =⎜ ⎝ 0 β 2 α aθ μ v μ h −(μ v +ρ v ) 0 ⎟ ⎠ , (42)
h v
0 0 ρ −μ
v v

--- Page 15 ---
MathematicalModellingofMalariaIntegratingTemperature,Rainfall... Page15of39 5
ClearlyAisaM−matrixandG ˆ (X,Y)=AY −G(X,Y)
So,
⎛ ⎞ ⎛ ⎞
G ˆ (X,Y)= ⎛ ⎜ ⎜ ⎝ G G G G ˆ ˆ ˆ ˆ 1 2 3 4 ( ( ( ( X X X X , , , , Y Y Y Y ) ) ) ) ⎞ ⎟ ⎟ ⎠ = ⎜ ⎜ ⎜ ⎜ ⎜ ⎜ ⎝β β 2 a 1 a I H I V ( ( S S 1 0 H V 0 0 − − N S N H S H V H ) ) ⎟ ⎟ ⎟ ⎟ ⎟ ⎟ ⎠ ≥ ⎜ ⎜ ⎜ ⎜ ⎜ ⎝ β β 2 1 S a a H 0 I I H V ( ( 1 S 0 V − 0 − N S S H H V ) ) ⎟ ⎟ ⎟ ⎟ ⎟ ⎠ ≥0 (43)
0 0
S α
Note that β aI (1− H )≥0 since 0<S ≤ h and (S0 −S )≥0 since S ≤N ≤
1 V N H μ V V V V
H h
θ
S0 = v andasaresult,theconditions(A )and(A )aremet.Theglobalstabilityofthe
V μ 1 2
v
DFEisproven. □
ExistenceoftheEndemicEquilibriumPoint TheendemicequilibriumpointEE∗ isdefined
as the steady solution when the disease persists in the population. For the model (21) the
endemicequilibriumpointisgivenbyEE∗=(S∗,E∗,I∗,R∗,S∗,E∗,I∗)computedby
H H H H V V V
settingtheright-handsidesofthemodeltozero,theequationsofthesystem(21)aresolved
attheendemicequilibriumpointsintermsoftheforceofinfectionsλ∗ andλ∗toobtain
h v
⎧
⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎨
⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎩
E
E I
R S
I
S
N
H
V
∗
∗
H
V
∗
∗ H
H
V
∗
H
∗
∗
∗
= = =
= =
=
=
=
[︁ [︁ [︁
[︁ λ
(︁
μ α
( ( (
(
λ
∗ v
h v
μ μ μ
μ
∗ v
[
θ +
(︁
(
h h h
h
+
v
λ ρ
+ + +
+ μ
∗ v h
μ
v
+ +
λ
q q q
q
v
λ
, ∗
v
) ) )
)
)︁
∗
v
μ μ
( ( (
(
θ
α
(
ρ
λ λ λ
λ
V
v
μ
h
h
v
∗ h ∗ h ∗ h
∗ h
)︁
)
v
(
θ
( (
+ + +
+
μ α
v
μ μ
+
h h
[︁h
μ μ μ
μ
v
λ
(
ρ
+ h h h
h
+ + μ
∗ h
v
) ) )
)
h
)
( ρ α ( ( (
(
γ ρ
μ
,
μ μ μ
μ
h h
+ h v
h ) h h h
h
λ
) +
α
(
q
∗ h +
,
+ + +
+
μ
h
)
ρ
δ
γ
(
h q h γ γ γ
γ
) λ
h
(
) h h h
h
+ (
∗ h
λ
μ
( μ + + +
+
∗
h
δ
+ h
q h
ρ
+ )
+
δ δ δ
δ
μ
h
+ ( ) ) )
)
δ γ
h
( ( (
(
q
q ρ ρ ρ
ρ
h
)
+
) (
) h h h
h
+
+ μ
γ + + +
+
h
h μ
λ
μ μ μ
μ
+ ∗ h
+ h
(
h h h
h
)
γ ρ
μ ) ) )
)
h h
− − −
−
h
+ +
) q q q
q
δ μ
γ γ γ
γ
)
h h h
h
h (
λ λ λ
λ
ρ )(
∗ h ∗ h ∗ h
∗ h
h μ
ρ ρ ρ
ρ
+ h
h h h
h
]︁ ]︁ ]︁
]︁
+ μ
, , ,
,
h q ) ) − + q λ γ ∗ h h ρ λ h ∗ h ( ρ μ h h]︁ +q)+λ ∗ h ρhγh ]
(
.
44)
Substituting λ∗, I∗ and N∗ into the expression of the force of infection λ∗ we obtain an
v V H h
equationforλ∗
h
g(λ∗)=λ∗(φ λ∗2+φ λ∗+φ ), (45)
h h 2 h 1 h 0
where
φ =b α μ (b (b +ρ )+ρ )(ρ (b (aβ +μ )+μ )+b b μ ),
2 3 h v 4 2 h h h 4 2 v v 2 4 v
φ =a2β β b qγ ρ2θ ρ −a2b b β β b2ρ θ ρ
1 1 2 4 h h v v 1 2 1 2 4 h v v
+ab b b β b2α ρ μ +2b b b b2α λ ρ μ2
1 2 3 2 4 h h v 1 2 3 4 h h h v
+2b b b b α ρ μ2+2b b2b b2α μ2,
1 2 3 4 h h v 1 2 3 4 h v

--- Page 16 ---
5 Page16of39 K.J.GatoreSinigiriraetal.
Table2 Possiblenumberof
positiverootsofequationof(46) φ2 φ1 φ0 Numberofpositiveroots
+ + + 0
+ + - 1
+ - + 2or0
+ - - 1
φ =b2b2b b2α μ2(1−R2).
0 1 2 3 4 h v 0
From(45),wegetλ∗=0,whichcorrespondstothediseasefreeequilibriumpoint,otherwise
h
φ λ∗2+φ λ∗+φ =0, (46)
2 h 1 h 0
correspondingtothesolutionoftheendemicpoint.Theexistenceoftheendemicequilibria
isdeterminedbythenumberofpositiverootsof(46).
Solvingforλ∗,wehavetworoots
h
√︂ √︂
−φ + φ2−4φ φ −φ − φ2−4φ φ
λ∗ = 1 1 2 0 , λ∗ = 1 1 2 0 .
h1 2φ h2 2φ
2 2
Wenotethatthecoefficientsof(46),φ >0,φ canbeeitherpositiveornegativeandφ can
2 1 0
bepositiveandnegativedependingonthevalueofR ,that’sifR <1,thenφ >0andif
0 0 0
R >1,thenφ <0.
0 0
Lemma1 (i) ThemodelhasauniqueendemicequilibriumpointifR >1(φ <0),
0 0
(ii) TwoendemicequilibriumpointsifR <1,andΔ=φ2−4φ φ >0,
0 1 2 0
(iii) Noendemicequilibriumpointotherwise.
HavingR lessthanoneisusuallythoughttomeanthatthediseasecanbeeliminated.
0
However,inourmodelthepossibilityoftheexistenceofmultipleendemicequilibriawhen
R <1 suggests that a backward bifurcation may occur. In epidemic models, a backward
0
bifurcation meansthatwehavetwostablesituationshappeningatthesametime.Sothat,
evenwhenwehave R lessthanone,thediseasecanstillpersist.Inthesecases,itiscru-
0
cialtoconsidernotonlytheR valuebutalsothethresholdvalueoftheR parameterthat
0 0
playsasignificantroleindetermininghowandwhenthediseasecanbecontrolledoreradi-
cated[45].Wedeterminethethresholdvalueofthereproductionnumber,denotedasRc,by
0
solvingtheequationΔ=0,wefind
φ2
Rc=1− 1 . (47)
0 4φ b2b2b b2α μ2
2 1 2 3 4 h v
BifurcationAnalysis We performed the center manifold theory developed by Chavez and
Song in [46] to investigate the Bifurcation analysis. This theory is used to investigate the
presenceofbothbackwardandforwardbifurcations.Forwardbifurcationoccurswhenthe
endemicequilibriumislocallyasymptoticallystableforR >1butR approaches1.
0 0
Let us rewrite the variables S , E , I , R , S , E , I as S = x , E = x ,
H H H H V V V H 1 H 2
I =x , R =x , S =x , E =x , I =x and let X=(x ,x ,x ,...x )T, the ex-
H 3 H 4 V 5 V 6 V 7 1 2 3 7
pressions of X in vector notation. The model system (21) can be rewritten in terms of

--- Page 17 ---
MathematicalModellingofMalariaIntegratingTemperature,Rainfall... Page17of39 5
dX
=(f ,f ,f ,...f )T where
dt 1 2 3 7
⎧
⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎨ d
d
d
d
d
d
x
x
x
t
t
t
1
2
3
=
=
=
α
λ
ρ
h
h
h
x
x
+
2
1
−
−
qx
(
(
4
μ
ρ
−
h
h
+
+
λ
h
μ
γ
x
h
h
1
)
+
−
x
2
δ
μ
=
)
h
x
x
f
3
1
2
=
=
,
f
f
3
1
,
,
dx
4 =γ x −(μ +q)x =f , (48)
⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎩d
d
d
d
d
d
x
x
x
t
t
t
5
6
7
=
=
=
θ
λ
ρ
v
h
v
x
x
−
3
5
(
−
−
μ
μ
(
v
μ
+
h
v
x
λ
+
v
=
)
ρ
x
v
f
5
)x
=
4
,
6
f
=
5
,
f
4
6
,
dt v 6 v 7 7
β ax β ax
withλ = 1 7,λ = 2 3 andN =x +x +x +x ,N =x +x +x .
h N v N H 1 2 3 4 V 6 7 8
Letusintro H ducethebifu H rcationparameterβ =β∗whenR =1.Itfollowsthat
1 1 0
α μ (ρ +μ )(μ +δ+γ )(μ +ρ )
β∗=β = h v h h h h v v (49)
1 1 β a2ρ ρ θ μ
2 h v v h
TheJacobianmatrixJ(E ,β∗)of(48)attheDFEE whenR =1isgivenby
0 1 0 0
⎛ ⎞
−μ 0 0 q 0 0 −β∗a
h 1
⎜ ⎜ 0 −b1 0 0 0 0 β 1 ∗a ⎟ ⎟
⎜ ⎜ 0 ρ h −b 2 0 0 0 0 ⎟ ⎟
⎜ ⎜ 0 0 γ h −b 4 0 0 0 ⎟ ⎟
J(E ,β∗)=⎜ β aθ μ ⎟, (50)
0 1 ⎜ 0 0 − 2 v h 0 −μ 0 0 ⎟
⎜ ⎜ α h μ v v ⎟ ⎟
⎜ β aθ μ ⎟
⎝ 0 0 2 v h 0 0 −b 0 ⎠
α μ 3
h v
0 0 0 0 0 ρ −μ
v v
with
b =ρ +μ ,b =μ +δ+γ ,b =μ +ρ ,b =μ +q.
1 h h 2 h h 3 v v 4 h
Sincethejacobianmatrix(50)hasasimplezeroeigenvalue,wecanusethecenterman-
ifold theory to describe the dynamics of the system near β∗ when R =1. We compute
1 0
w=(w ,w ,w ,...,w )T,therighteigenvectorofthejacobianmatrixassociatedwiththe
1 2 3 8

--- Page 18 ---
5 Page18of39 K.J.GatoreSinigiriraetal.
zeroeigenvalueasfollows:
⎧
⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎨
−
ρ
−
h
μ
b
w
1
h
w
2
w
−
2
1
+
+
b
2
β
w
q
1
∗
w
3
a
4
=
w
−
7
0
=
,
β
1
∗
0
a
,
w
7
=0,
w
w
w
1
2
3
=
=
=
β
β
α
2
2
h
α
α
a
a
γ
h
h
μ
μ
h
μ
μ
μ
h
h
2
v
2
v
θ
θ
2
v
b
b
q
v
v
3
2
ρ
ρ
β
b
b
v
v
3
2
3
ρ
a
,
−
h
μ
,
β
2
h
θ
1
∗
v
β
ρ
2
v
a
b
2
4
μ
h
θ
v
ρ
v
b
4,
α γ μ2b (51)
⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎩
−
γ
β
h
2
α
β
w
a
h
2
α
θ
3
μ
a
v
h
−
θ
μ
v
μ
v
h
b
μ
v
w
4
h
w
3
w
4
−
3
=
−
b
0
3
μ
w
,
v
6
w
=
5
=
0,
0, w
w
w
4
5
6
=
=
=
−
β
μ
ρ
2
v
v
ρ
b
a
,
h
3
v
μ
,
h
h
θ
v
v
ρ
v
3
b
4
,
ρ w −μ w =0, w =1.
v 6 v 7 7
Consider v=(v ,v ,...,v ) as a left eigenvector associated with the zero eigenvalue,
1 2 8
whichsatisfiesv·w=1.Thisisdeterminedbysolvingthesystem
⎧
⎪⎪⎪⎪⎪⎪⎪⎪⎪⎨
−
−
−
b
b
μ
1
h
v
v
v
2
1
+
+
=
ρ
γ
0
h
,
v
v
3
−
=0
β
,
2
aθ
v
μ
hv +
β
2
aθ
v
μ
hv =0,
2 3 h 4 α μ 5 α μ 6
⎪⎪⎪⎪⎪⎪⎪⎪⎪⎩
−
−
qv
μ
b
1
3
v
−
v
v
6
5
b
+
=
4
v
ρ
0
4
v
,
=
v
7
0
=
,
0,
h v h v (52)
−β∗av +β∗av −μ v =0.
1 1 1 2 v 7
Clearly,v =v =v =0andv.w=1impliesthat
1 4 5
b v α μ2 b b v α μ2 v μ
3 3 h v + 2 3 2 h v + 6 v +v =1 (53)
aβ μ θ ρ aβ μ ρ θ ρ ρ 7
2 h v v 2 h h v v v
From(52)and(53),wehave
⎧
⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎨
v
v
v
1
2
=
=
=
0
a
,
2
v
β
4
1
β
=
2
μ
0,
h
v
ρ
5
h
θ
=
v
ρ
0
v
+
a
a
b
β
b
1
2
1
b
μ
β
2
α
2
h
μ
h
ρ
μ
h
h
θ
θ
3
v
v
v
+
μ
μ
v
v
b
ρ
ρ
1
v
v
b
3
α
h
μ3
v
+b
2
b
3
α
h
μ3
v
,
,
⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎩
v
v
3
6
=
=
a
a
2
2
β
β
1
1
β
β
2
2
μ
μ
h
h
ρ
ρ
h
h
θ
θ
v
v
ρ
ρ
v
v
+
+
a
b
b
2
1
1
β
b
b
b
1
1
2
2
b
β
α
α
2
2
h
h
α
μ
μ
μ
h
h
μ
3 v
3
v
ρ
+
+
2
v
h
ρ
θ
v
v
b
b
ρ
1
1
b
b
v
3
3
α
α
h
h
μ
μ
3 v
3
v
+
+
b
b
2
2
b
b
3
3
α
α
h
h
μ
μ
3 v
3
v
,
.
(54)
7 a2β β μ ρ θ ρ +b b α μ3+b b α μ3+b b α μ3
1 2 h h v v 1 2 h v 1 3 h v 2 3 h v

--- Page 19 ---
MathematicalModellingofMalariaIntegratingTemperature,Rainfall... Page19of39 5
We computed A and B coefficients, in order to determine the existence possibility of a
bifurcation
∑︂7
∂2f (E )
∑︂7
∂2f (E )
A= v ww k 0 ,B= v w k 0 (55)
k i j ∂x∂x k i ∂x∂β
k,i,j=1 i j k,i i 1
Since v =v =v =0 andaftercomputingtheassociatednon-zeropartialderivatives
1 4 5
off atE ,weobtain
0
β aθ μ2 β aμ
A=−2v w w 2 v h +2v w w 2 h (56)
6 1 3 μ α2 6 3 5 α
v h h
a2β μ ρ θ μ ρ
B= 2 h h v v v (57)
a2β β μ ρ θ ρ +b b α μ3+b b α μ3+b b α μ3
1 2 h h v v 1 2 h v 1 3 h v 2 3 h v
From(57),weclearlyseethatB>0.Todeterminethedirectionofthebifurcationwhen
R =1,weneedtoknowthesignofA.Aftersubstitutingv ,w ,w ,andw into(56),let
0 6 1 3 5
uswriteA=A −A .
1 2
where
β b α γ μ2qb
A = 1,A = 3 + h h v 3
1 μ 2 ρ β aμ2θ ρ b
h v 2 h v v 4
• IfA >A ,wehaveA>0andB>0thensystem(21)willundergoabackwardbifurca-
1 2
tionatR =1.
0
• IfA <A ,wehaveA<0andB>0thensystem(21)willundergoaforwardbifurcation
1 2
atR =1.
0
WhiletheconditionsA >A andA <A indicatespecifictypesofbifurcations,itisim-
1 2 1 2
portanttorecognizethattheprecisesignofAcannotbeconclusivelyestablishedbasedonly
ontheinformationathand.Ifbackwardbifurcationoccurs,theDFEandanendemicequilib-
riumcancoexistevenwhenR <1.Twostableequilibria(theDFEandtheendemicstate)
0
exist under the same conditions. Whether the system ends up at the DFE or the endemic
equilibriumdependsoninitialconditions,specificallyhowwidespreadthediseaseisatthe
start.
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
Fig.3 Modelfittodatafor
MalariainBurundi
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
Table4 Temperature,rainfall,andNDVI-dependentparameterranges
Temperature Rainfall NDVI θv(T,R,η) μv(T,η) a(T) Scenarios
[16-25°C] [5-25mm] [0.2-0.4] [10.2-2.16.102] [0.014-0.035] [0.07162-0.28074] (a)
[0.4-0.8] [11.2-2.16.102] [0.0093-0.021] [0.07162-0.28074] (b)
[25-50mm] [0.2-0.4] [0−1.82.102] [0.014-0.035] [0.07162-0.28074] (c)
[0.4-0.8] [0−1.71.102] [0.0093-0.021] [0.07162-0.28074] (d)
[25-35°C] [5-25mm] [0.2-0.4] [5.6−1.82.102] [0.021-0.036] [0.2807-0.4472] (e)
[0.4-0.8] [5.8−1.82.102] [0.0093-0.022] [0.2807-0.4472] (f)
[25-50mm] [0.2-0.4] [0−1.82.102] [0.01-0.42] [0.2807-0.4472] (g)
[0.4-0.8] [0−1.71.102] [0.0093-0.022] [0.2807-0.4472] (h)
Thisinvolvesevaluatingthemodel’stemperature,rainfall,andNDVI-dependentparameters
across a defined range of temperatures from 15 °C to 35 °C, rainfall values ranging from
5 mm to 50 mm, and NDVI values ranging from 0.2 to 0.8. We include these ranges in
our simulations because a temperature of 16 °C is recognized as the minimum threshold
necessaryformalariaparasitestomaturewithinmosquitoes[33],and35°Crepresentsthe
maximum temperature for the region under consideration (Burundi, in this case). Subse-
quently, the range of rainfall is set from 5 mm to 50 mm, as rainfall exceeding 50 mm is
considered as the maximum limit for flushing out mosquitoes [13]. Regarding NDVI, we
considerboththeminimumandmaximumNDVIvaluesforBurunditoincludethefullspec-
trumofvegetationdynamicswithintheregion.WeusetheinfectedclassI astheresponse
H
function.
Secondly, we performed the sensitivity analysis when the temperature(T), Rainfall(R)
andNDVI(η)areconsideredasparametersintherangesof[15-35°C],[5-50mm]and[0.2-
0.8]respectively.Wealsousedtheinfectedhumanclassastheoutput.It’simportanttonote
thatthePRCCvalueswascalculatedatfivedistincttimepoints:100,200,300,400,and500.
Thisanalysisovertimehelpsusunderstandhowthemodelparameters’sensitivitychange
overthecourseofthetime,givingusabettergraspofthesystem’sdynamicbehavior.
UsingthepopulationofinfectioushumansI astheresponsefunction,parameters β ,
H 1
γ ,a(T),andμ (T,η)arethetopcommonPRCCrankedparametersforallrangesofthe
h v

--- Page 23 ---
MathematicalModellingofMalariaIntegratingTemperature,Rainfall... Page23of39 5
Fig.4 PRCCsforIH fordifferentrangesofclimate-dependentparametersinthescenarios(a)and(b)of
Table4
Fig.5 PRCCsforIH fordifferentrangesofclimate-dependentparametersinthescenarios(c)and(d)of
Table4
climatedependentparametersasestablishedinTable4.ThePRCCvaluesfortheseparame-
tersmayfluctuatealittlebitindicatingtemporalvariabilityinthesensitivityofthemodelto
theseparameters.β anda(T)arepositivelycorrelatedtoI andthusincreasetheburden
1 H
ofmalariainfectioninthehumanpopulationwhereasγ andμ (T,η)arenegativelycorre-
h v
latedto I anddecreasetheburdenofmalariainfectioninthehumanpopulation(Figs.4
H
to7).Forscenarios(a),(b),(c),and(d),weobserveaslightreductioninβ ,γ ,anda(T)
1 h
overtimewhilethereisasignificantriseinμ (T,η)overtime.However,inscenarios(e)
v
and(h),β decreasesuntilitisnearlyzero.Thiscoincidestotherangeofhightemperature
1
andhighNDVI.
Parametersthatexhibitrelationshipswithtemperature,rainfallandNDVIoverdifferent
timeperiods,sensitivetothemodelarespecificallythemosquitobitingrate a(T) andthe
mosquito mortality rate μ (T,η). An increase in the mosquito biting rate a(T) leads to
v
a higher rate of malaria infection in the human population. Conversely, an increase in the
mosquito mortality rate μ (T,η) has a negative effect on the infection rate, meaning that
v

--- Page 24 ---
5 Page24of39 K.J.GatoreSinigiriraetal.
Fig.6 PRCCsforIH fordifferentrangesofclimate-dependentparametersinthescenarios(e)and(f)of
Table4
Fig.7 PRCCsforIH fordifferentrangesofclimate-dependentparametersinthescenarios(g)and(h)of
Table4
ahigher μ reducestheinfectionburden.Additionally,weobservethat μ increasesover
v v
time, suggesting that the effects of temperature and NDVI on mosquito mortality become
morepronouncedafterseveralmonths.Thisvariabilityunderscoresthecomplexnatureof
malaria’sreactiontoenvironmentalchanges.Acomprehensiveunderstandingofthesetem-
poral dynamics is pivotal for precise disease prognosis and the development of effective
interventionapproaches.Consequently,integratingassessmentsofenvironmentalvariabil-
ityintomalariaresearchisimperativeforenhancingourcomprehensionandmanagement
ofthedisease.
Figure8illustratesthePRCCanalysisformalariadisease,consideringvariationsincli-
matevariablessuchastemperature,rainfall,andNDVI.Theanalysisspanstheentiredataset
andconsidersvariationsintheseclimatefactors.Thetemperaturerangeinvestigatedliesbe-
tween 15 °C and 35 °C, the rainfall range considered is 5 mm to 50 mm and the NDVI

--- Page 25 ---
MathematicalModellingofMalariaIntegratingTemperature,Rainfall... Page25of39 5
Fig.8 PRCCsforIH when
temperature,rainfall,andNDVI
areconsideredasparameters
varyingwithinthesystem(21)
rangeexploredspansfrom0.2to0.8.Twokeyparametersinmalariatransmissiondynam-
ics,denotedasβ andγ ,exhibithighsensitivitytothevariableI ,withβ beingpositively
1 h H 1
correlatedtoI andγ beingnegativelycorrelatedtoI .Anincreaseinβ willleadtoan
H h H 1
increaseinI ,whereasanincreaseinγ willleadtoadecreaseinI .
H h H
TemperatureandNDVIarepositivelycorrelatedwithI .Thismeansthatastemperature
H
andNDVIincrease,thenumberofinfectiousI increases.Fromtheanalysisoverdifferent
H
timepoints,weobserveinterestingtrends:
• Initially,temperaturehasasignificantimpactonI .However,astimeprogresses,itssen-
H
sitivitydecreasesslightly.Thissuggeststhatotherfactorsmightbecomemoreinfluential.
• NDVI’simpactonI increasesovertime.Thisimpliesthatvegetationhealth(asindicated
H
byNDVI)becomesmorerelevantinunderstandingmalariadynamics.
• Thesensitivityofrainfalltotheoutputfunctionmaynothaveanimpactontheinfectious
humanclassforBurundi.
3.3 SimulationResults
3.3.1 Temperature,RainfallandNDVIEffectsontheModel
Figure9presentsthebaselinegraphsderivedfromthemathematicalmodel(21).Thesim-
ulations are conducted under specific conditions where climate parameters remain fixed.
Specifically,thetemperature(T)issetat25°C,rainfallat30mm,andtheNormalizedDif-
ferenceVegetationIndex(η)at0.4.Thesesimulationswerecarriedoutoveraperiodof100
months.
Wethenillustratetheeffectsoftemperature,rainfallandNDVIonthemalariatransmis-
siondynamics.Thisapproachwillprovidevaluableinsightsintothefactorsdrivingmalaria
propagation.Bysystematicallyexaminingeachfactorwhilekeepingtheothersconstant,we
cangainabetterunderstandingoftheirindividualcontributionstomalariatransmission.We
utilizedclimateparametervalueswithintherangesthatweusedinSect.3.2.
To begin, we study the impact of temperature on malaria transmission while keeping
rainfallandNDVIconstant.Next,weinvestigatedtheinfluenceofrainfallonmalariaprop-
agationwhilemaintainingconstanttemperatureandNDVI.Afterward,weexploredtheef-
fects of NDVI on malaria transmission while keeping temperature and rainfall constants
(SeeFigs.10to12)
Figure 10 reveal the trends concerning temperature variations and their impact on the
dynamicsofmalariatransmissionwithintheinfectedhumanandinfectedmosquitoindivid-
uals.Temperaturesbelow16°Careregardedasinsufficientforthedevelopmentofmalaria
parasite [52]. 16 °C is considered as the minimum temperature for parasite development

--- Page 26 ---
5 Page26of39 K.J.GatoreSinigiriraetal.
Fig.9 Baselinegraphsshowsthedynamicsofvariousstatevariableswithinmodel(21)withR0>1overa
periodof100months
ofPlasmodiumfalciparumandPlasmodiumvivax,limitingthespreadofmalariaincooler
regions[53].
As shown in Fig. 10, the number of infected humans (I ) peaks and then gradually
H
decreasesatatemperatureofT=25°C(consistentwiththefindingsin[14,32]),suggesting
that this temperature represents an optimal condition for malaria transmission dynamics.
ThesamefigurealsoindicatesthatT=25°Cisoptimalforthegrowthandactivityofthe
infectedmosquitopopulation.
Thisrelationshiphighlightsthatthesignificantincreaseinhumaninfectionsisdirectly
linked to the growth of mosquito populations at T = 25 °C. When environmental condi-
tionsarefavorableformosquitoes,theirbreeding,survival,andfeedingratesareenhanced,
resultinginhighermalariatransmissiontothehumanpopulation.
Figure11demonstrateshowrainfallaffectsmodel(21).Itappearsthatvariationsinpop-
ulationsduetotemperaturechangesaremoresignificantcomparedtovariationscausedby
rainfall.Theinsensitivityofmalariatransmissiondynamicstovaryingrainfalllevelswithin
thespecifiedrangeinBurundisuggeststhatoncerainfallexceedsacertainthreshold,itdoes
notsignificantlyimpactthedynamicaltransmissionofmalariainBurundi(Fig.11).Thisis
inlinewithwhatwefoundinSect.3.2.
InFig.12,wewereexaminingtheimpactofNDVI.WefoundthatNDVIhasagreaterin-
fluenceonthemodelcomparedtorainfall.ThiscanbeexplainedbythefactthatVegetation

--- Page 27 ---
MathematicalModellingofMalariaIntegratingTemperature,Rainfall... Page27of39 5
Fig.10 Graphicalillustrationofmodel(21)fordifferenttemperatureswhenNDVIandrainfallareconstant
Fig.11 Graphicalillustrationofmodel(21)fordifferentrainfallwhentemperatureandNDVIareconstant
influencesnotonlytheavailabilityofbreedingsitesbutalsothemicroclimate(humidityand
temperature), which can affect mosquito survival and reproduction. In regions with dense
vegetation,evenifrainfallisinconsistent,mosquitoescanstillfindsuitableconditionsfor
reproduction [54]. This might make NDVI a more consistent and powerful predictor than
rainfallinthemodel.WhenNDVIincreasesfrom0.2to0.8,weobserveanincreaseinin-
fectiousindividuals,bothhumansandmosquitoesrespectively.Weobservedahighnumber
in the infected individuals in the range of [0.4-0.6]. The level of vegetation (NDVI) in an
areaseemstohaveastrongerimpactonthemodel’spredictionsthantheamountofrainfall.

--- Page 28 ---
5 Page28of39 K.J.GatoreSinigiriraetal.
Fig.12 Graphicalillustrationofmodel(21)fordifferentvaluesofNDVIwhentemperatureandrainfallare
constant
Fig.13 Graphicalillustrationofmodel(21)fordifferentvaluesoftemperatureandrainfallwhenNDVIis
constant
Aftershowingthevariationofasingleparameterwhilemaintainingtheothersconstants,
weproceededtosimultaneouslymodifytwoparameterswhilekeepingoneconstant.From
thesimulations,wemadeinterestingobservations.Whencombiningtemperaturewithrain-
fallorNDVI(seeFig.13andFig.14),weobservesignificantchangesinthetransmission
dynamicsofmalaria.ButwhenrainfallwascombinedwithNDVI(Fig.15),thealterations
intransmissiondynamicsofmalariawererelativelysmall.Withlowtemperaturescombined
tolowrainfallorlowNDVI,theinfectedpopulationsremainnearlyconstant.Thiscanbe
attributedtothefactthatthegrowthrateofparasitesinmosquitoesisconsideredtobemini-

--- Page 29 ---
MathematicalModellingofMalariaIntegratingTemperature,Rainfall... Page29of39 5
Fig.14 Graphicalillustrationofmodel(21)fordifferentvaluesoftemperatureandNDVIwhenrainfallis
constant
Fig.15 Graphicalillustrationofmodel(21)fordifferentvaluesofrainfallandNDVIwhentemperatureis
constant
malwhenthetemperatureisbelow16°C.Asthetemperaturerises,boththeinfectedhuman
and mosquitopopulations begin to decrease. The number of cases in the infection classes
reachedtheirpeakatatemperaturevaluerangeof[20-25°C],inconjunctionwithamean
monthlyrangeof[20-30mm]andNDVIrangeof[0.4-0.6].Whenwecombinerainfalland
NDVI,weobserveonlyminorchangesinthepopulations.
In the scenario where temperature, rainfall, and NDVI are all fluctuating, we observed
that where all three variables are low, the infection classes remain relatively constant, but
they begin to increase as the values of temperature, rainfall, and NDVI increase. This in-

--- Page 30 ---
5 Page30of39 K.J.GatoreSinigiriraetal.
Fig.16 Graphicalillustrationofmodel(21)fordifferentvaluesofTemperature,RainfallandNDVI
creasebecomesmorepronounced,ultimatelyreachingamaximumatatemperatureof35,
rainfallof45mm,andanNDVIvalueof0.8(Fig.16).
3.4 ForecastingTemporalTrendsintheReproductionNumber
Mathematicalmodelsarevaluabletoolsforunderstandingandpredictingdiseaserisks,in-
cluding malaria. A key parameter in these models is the basic reproduction number (R ),
0
whichquantifiesthepotentialriskfordiseasetransmission.Thereproductionnumber(R )
0
isacriticalfactorinunderstandingdiseasespreadandevaluatingtheeffectivenessofcon-
trolmeasures[55].Itcanprovideanumericalbasisforpredictinghowclimatefluctuations
canimpactdiseasetransmission.Inthecontextofmalaria,R isinfluencedbyclimateand
0
environmentalfactors.BycalculatingR undervariousclimateconditions,researcherscan
0
qualitativelyassessfuturemalariariskandinformcontrolstrategies.Weuseprojectedtem-
perature,rainfall,andNDVIdataforBurunditopredictmalariainfection.
To illustrate the evolution of climate variables over time, we present future outcomes
incomparisontothereferenceperiod(2010-2020).Bycarefullyanalyzingthedifferences
between future climate patterns and those recorded during the reference period, we can
determinetheextentandcharacteristicsoflong-termclimatefluctuationsandtheirimpacts.
Here we used three future climate periods, period 2021 to 2050, period of 2031 to 2060
andperiodof2041to2070.Wechoosetheseperiodsfollowingtherecommandationsofthe
WorldMeteorologicalOrganization(WMO)[56].
WeobservedthatwhenusingR asariskindexformalariatransmissiondynamicsun-
0
der the influence of temperature, rainfall, and NDVI, malaria severity in Burundi exhibits
distinctpeaksinJanuary,April,andDecember.AfterJanuary,thereisaslightdecreasebe-
foreariseleadingtothepeakinApril,followedbyanotherincreaseinAugust,culminating
in the peak in December. In [57], statistical descriptive analysis of malaria cases showed
thatmalariainfectionspeakinJanuary,decreaseinFebruary,risefromMarchtoJune,drop
sharplyinAugust,andthenincreaseagainfromSeptembertoDecember.Weobservedthat
bothresultshighlightthesignificantseasonalvariationsinmalariatransmission,emphasiz-
ingsomesimilarperiodsofincreasedanddecreasedmalariacasesthroughouttheyear.

--- Page 31 ---
MathematicalModellingofMalariaIntegratingTemperature,Rainfall... Page31of39 5
Fig.17 Basicreproduction
numberbasedontemperature,
rainfallandNDVIclimatedata
Figure 17 shows an increase in R over time from 2010 to 2070, indicating that the
0
diseaseisbecomingmoretransmissibleovertime.Thisisconcerningbecauseahigherre-
production number means that more people are likely to be infected, leading to a larger
outbreakorepidemicifeffectivecontrolmeasuresarenotputinplace.
3.5 DiscussionofResults
We presented a mathematical model that explores the influence of temperature, rainfall,
andNDVIonmalariatransmission.Themodelisformulatedandisthoroughlyexamined.
Weemployedmathematicaltechniquestodetermineboththelocalstabilityofthedisease-
freeandendemicequilibrium andtheglobalstability ofthedisease-freeequilibrium.Our
analysis produced mathematical expressions that describe the conditions under which the
diseasewilleithercontinuetospreadorbebroughtundercontrol.
TheanalysisconductedbyPRCCssuggestedthatthemosquito-humancontactratehas
a positive effect on malaria incidence, implying that any factor reducing this contact rate
couldhelpmitigatethespreadofmalaria.Conversely,themortalityrateofmosquitoeshasa
negativecorrelationwiththemalariaincidence,indicatingthatanythingincreasingthisrate
couldlowermalariacases.InBurundi,distributionoflong-lastinginsecticidalnets(LLINs)
startedintheyear2003[58]butLLINsarereportedtoprovideeffectiveprotectionagainst
malariaforonlyoneyear.Thislimiteddurationofefficacyiscrucialforunderstandingthe
frequency and timing of distribution campaigns needed to maintain high levels of protec-
tion within the population [59]. Interventions such as intermittent preventive treatment in
pregnancy and bed nets distributed during antenatal care visits and delivery started in the
year2006helpedinthereductionofcasesinmalariatransmissionforpregnantwomen[58].
So,otherinterventionssuchasindoorandoutdoorresidualsprayingmaderegularly,have
the potential to reduce malaria transmission in the population of Burundi. It also showed
that temperature and NDVI appears to increase malaria incidence compared to rainfall in
Burundi.
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
Innumerousstudies,theoptimalconducivetemperaturerangeformalariatransmission
hasbeenidentifiedas20-32°C[32,60,62].However,ourmodelindicatesthatwhenaddi-
tionalvariablessuchasNDVIandrainfallareincorporated,theeffectivetemperaturerange
mayshift,whereevenathighertemperaturethan32°C,thelevelofinfectionmaycontinue
to increase. This was the observation when the model was calibrated with the informa-
tionfromBurundi.Mathematicalmodelsshouldintegratetheeffectsofmultiplevariables,
including NDVI and rainfall, to provide a more comprehensive understanding of malaria
transmissiondynamics.
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
WehavepresentedabasicmodelcapturingthescenariosforBurundiandthisisoneof
thefewstudiesonmalariatransmissiondynamicsinfluencedbythethreeclimacticfactors.
Thestudyisnotallencompassingandthereisaroomforimprovementonfutureresearch
whichshouldincorporateseasonalityintothemodeltogetamorecomprehensiveevaluation
as certain climate factors exhibiting stronger connections with malaria transmission over
longer time frames. This approach will enable capturing the impacts that unfold over ex-
tendedperiods,ratherthanbeingconfinedtoshort-termfluctuationswithinasinglemonth.
Throughtheadoptionofthismoreprecisemethodology,wecandiscernclearerpatternsand
obtainadeeperunderstandingofthecomplexrelationshipbetweenclimatevariablesandthe
dynamicsofmalaria.Byalsousingprovincial-leveldatainsteadofnational-leveldata,we
canpinpointregionswheremalariaislikelytoincreaseinthefutureandconcentratecontrol
effortsaccordingly.
AppendixA: CorrelationAnalysis
UsingtheSpearmanmethod,weaimtodiscernanysignificantassociationsbetweentem-
perature, rainfall, and NDVI, which can provide valuable insights into potential climatic
relationships with vegetation health and density. The analysis indicates that while there
arediscernibleassociationsbetweenthesevariables,theytendtoberelativelyweak.Mean

--- Page 33 ---
MathematicalModellingofMalariaIntegratingTemperature,Rainfall... Page33of39 5
Fig.18 Correlationmatrix
betweenmeanmonthly
temperature,meanmonthly
rainfallandNDVI
monthlytemperatureexhibitsaslightpositivecorrelationwithmeanmonthlyrainfall,im-
plyingthatareasexperiencinghighertemperaturesmayalsoseeslightlyincreasedrainfall,
though this connection is not strong. Conversely, the mean monthly temperature displays
amodestnegativecorrelationwithNDVI,indicatingthatregionswithhighertemperatures
mayhaveslightlylowervegetationdensity,thoughagain,thisassociationisnotsubstantial.
The most notable relationship emerges between mean monthly rainfall and NDVI, with a
positive correlation indicating that areas with greater rainfall tend to exhibit higher vege-
tationdensity.Thisresultalignswithexpectations,asincreasedrainfalltypicallysupports
morelushvegetationgrowth.
AppendixB: ForecastingData:NormalizedVegetationIndex
The process of projecting with a SARIMA model involves utilizing historical NDVI val-
uestoforecastfuturevalues,capturingpatternssuchasseasonalityandautocorrelationfor
predictions.TodosoweusedNDVIdatafrom2010to2022Fig.2c
TheSARIMAmodelwasthenemployedtoanalyzeandforecastseasonalandtemporal
patterns inherent in the NDVI data. This robust technique accounts for both seasonal and
non-seasonal variations, crucial for accurately capturing underlying trends. Model fitting
involved selecting appropriate parameters including autoregressive (AR), differencing (I),
movingaverage(MA),andseasonalcomponentsbasedonNDVItimeseriescharacteristics.
TheSARIMAmodelextendsARIMAbyincorporatingseasonalcomponentslikeseasonal
autoregressive(SAR)andseasonalmovingaverage(SMA)components.Theautoregressive
componentcapturesthelinearrelationshipbetweencurrentandpreviousobservations,while
differencingaccountsfornon-stationarity.Themodel’sparametersareestimatedbasedon
observed data to make future forecasts while considering seasonal fluctuations. Rigorous
validation procedures, including statistical metrics and graphical analyses, evaluated the
model’seffectivenessincapturingNDVIseasonalityandtemporaldynamics,providingre-
liableforecastscrucialforenvironmentalandecologicalapplications.
B.1 ModelIdentification
WefoundthattheMeanAbsoluteError(MAE)ofapproximately0.01675andtheR-squared
(rsquare)valueofapproximately0.9344provideinsightfulmetricsforassessingtheperfor-
manceoftheSARIMAmodelonthevalidatedsetspanningfromJanuary2020toDecember
2022.TheseresultscollectivelyindicatethattheSARIMAmodelperformswellinforecast-
ingNDVIvalues.

--- Page 34 ---
5 Page34of39 K.J.GatoreSinigiriraetal.
Fig.19 ACFandPACFofthetransformedseries
Fig.20 Decompositionanalysis
oftheNDVI
B.2 ValidationoftheModel
Validation of the SARIMA model’s performance was conducted using a separate dataset
fromJanuary2020toDecember2022,assessingitsabilitytogeneralizedataandforecasting
accuracy.
TheSARIMAresultsprovideacomprehensiveinsightintotheNDVItimeseriesdynam-
ics. Notably, the parameter estimates reveal significant relationships between the current
NDVI values and their lagged counterparts, as well as the residual errors from previous
forecasts. For instance, the coefficient of ar.L1 (−0.6165) suggests a negative correlation
betweenthecurrentNDVIvalueanditslaggedvalue,whilethecoefficientofar.L2(0.7379)
indicates a positive correlation with the value two time periods ago. After estimating the
parametersoftheSARIMA(4,1,3)(2,0,3,12)model,weevaluatedtheiradequacybyexam-
iningtheresiduals.
Measuresofmodelfitsuchastheloglikelihood(−614.852),AIC(−578.723),BIC,and
HQICindicateawell-fittedSARIMAmodeltotheNDVIdata,withlowervaluessuggesting
superiorperformance.Diagnostictestsforautocorrelation,normality,andheteroskedastic-
ity validate the model’s adequacy in capturing temporal dependencies and distributional
assumptions.Withthehighp-valuesassociatedwiththestatistics,wefailtorejectthenull

--- Page 35 ---
MathematicalModellingofMalariaIntegratingTemperature,Rainfall... Page35of39 5
Fig.21 Thegraphical
representationofthevalidation
processoftheseasonal
autoregressiveintegratedmoving
average(SARIMA)model
Fig.22 GraphicaldiagnosticsforassessingtheSARIMA(4,1,3)(2,0,3,12)modelfit
Fig.23 NDVIforecasted
hypothesis of independence in this residual series. Thus, we conclude that the SARIMA
model(4,1,3)(2,0,3,12)adequatelyfitsthedata.Figure20showstheforecastedNDVIdata
(inred)fromJanuary2023toDecember2070
Followingthesameprocedure,weforecastrainfallandTemperature.

--- Page 36 ---
5 Page36of39 K.J.GatoreSinigiriraetal.
Fig.24 Forecastedtemperatureandrainfall
Acknowledgements The authors express their gratitude to the Department of Mathematics and Applied
MathematicsattheUniversityofJohannesburgfortheirmaterialsupportincompletingthisproject.KJGS
particularlyappreciatesthesupportfromtheOrganizationforWomeninSciencefortheDevelopingWorld
(OWSD).KJGSalsothankstheinterdisciplinaryresearchprogramoftheDoctoralSchooloftheUniversity
ofBurundiforthekindcollaboration.
FundingInformation OpenaccessfundingprovidedbyUniversityofJohannesburg.Thisworkwascarried
outwiththesupportofOWSDandtheSwedishInternationalDevelopmentCooperationAgency(SIDA).
DataAvailability TheNDVIdatawereextractedusingGoogleEarthEngine[63].Boththemalariadata(from
INMCP)andthetemperatureandrainfalldata(fromIGEBU)comefrominhousedataforthewideproject
onMalariaepidemiologyinBurundiledbytheDoctoralschoolattheUniversityofBurundi.Thedataare
availableforresearchersbutnotforpublic.
Declarations
CompetingInterests Theauthorsdeclarethatthereisnoconflictofinterestregardingthepublicationofthis
paper.
OpenAccess ThisarticleislicensedunderaCreativeCommonsAttribution4.0InternationalLicense,which
permitsuse,sharing,adaptation,distributionandreproductioninanymediumorformat,aslongasyougive
appropriatecredittotheoriginalauthor(s)andthesource,providealinktotheCreativeCommonslicence,
andindicateifchangesweremade.Theimagesorotherthirdpartymaterialinthisarticleareincludedinthe
article’sCreativeCommonslicence,unlessindicatedotherwiseinacreditlinetothematerial.Ifmaterialis
notincludedinthearticle’sCreativeCommonslicenceandyourintendeduseisnotpermittedbystatutory
regulationorexceedsthepermitteduse,youwillneedtoobtainpermissiondirectlyfromthecopyrightholder.
Toviewacopyofthislicence,visithttp://creativecommons.org/licenses/by/4.0/.
References
1. Djihinto,O.Y.,Medjigbodo,A.A.,Gangbadja,A.R.A.,Saizonou,H.M.,Lagnika,H.O.,Nanmede,D.,
Djossou,L.,Bohounton,R.,Sovegnon,P.M.,Fanou,M.-J.,etal.:Malaria-transmittingvectorsmicro-
biota:overviewandinteractionswithanophelesmosquitobiology.Front.Microbiol.13,891573(2022)
2. Zongo,P.:Modélisationmathématiquedeladynamiquedelatransmissiondupaludisme.PhDthesis,
UniversitédeOuagadougou(2009)
3. Sato,S.:Plasmodium—abriefintroductiontotheparasitescausinghumanmalariaandtheirbasicbiol-
ogy.J.Physiol.Anthropol.40(1),1–13(2021)
4. WorldHealthOrganization:WorldMalariaReport2022.WorldHealthOrganization,Geneva,Switzer-
land(2022).https://www.who.int/publications/i/item/9789240064898

--- Page 37 ---
MathematicalModellingofMalariaIntegratingTemperature,Rainfall... Page37of39 5
5. Venkatesan,P.:The2023WHOWorldmalariareport.TheLancetMicrobe(2024)
6. Lok,P.,Dijk,S.:MalariaoutbreakinBurundireachesepidemiclevelswith5.7millioninfectedthisyear.
Br.Med.J.(2019)
7. Mohanan,P.,Islam,Z.,Hasan,M.M.,Adedeji,O.J.,SantosCosta,A.C.,Aborode,A.T.,Ahmad,S.,
Essar,M.Y.:Malariaandcovid-19:adoublebattleforburundi.Afr.J.Emerg.Med.12(1),27–29(2022)
8. WorldVisionInternational:EightfactsaboutBurundi’smalariaepidemic(2017).Retrievedfromhttps://
www.wvi.org/article/8-facts-about-burundis-malaria-epidemic
9. Moise,I.K.,Roy,S.S.,Nkengurutse,D.,Ndikubagenzi,J.:Seasonalandgeographicvariationofpediatric
malariainBurundi:2011to2012.Int.J.Environ.Res.PublicHealth13(4),425(2016)
10. LaPointe,D.A.,Atkinson,C.T.,Samuel,M.D.:Ecologyandconservationbiologyofavianmalaria.Ann.
N.Y.Acad.Sci.1249(1),211–226(2012)
11. Tolle,M.A.:Mosquito-bornediseases.Curr.Prob.Pediatr.Adolesc.HealthCare39(4),97–140(2009)
12. Martens,W.J.M.,Jetten,T.H.,Rotmans,J.,Niessen,L.W.:Climatechangeandvector-bornediseases:a
globalmodellingperspective.Glob.Environ.Change5(3),195–209(1995)
13. Parham,P.E.,Michael,E.:Modelingtheeffectsofweatherandclimatechangeonmalariatransmission.
Environ.HealthPerspect.118(5),620–626(2010)
14. Yiga,V.,Nampala,H.,Tumwiine,J.:AnalysisoftheModelontheEffectofSeasonalFactorsonMalaria
TransmissionDynamics.J.Appl.Math.(2020).Hindawi
15. Githeko,A.K.,Lindsay,S.W.,Confalonieri,U.E.,Patz,J.A.:Climatechangeandvector-bornediseases:
aregionalanalysis.Bull.WorldHealthOrgan.78(9),1136–1147(2000).SciELOPublicHealth
16. Gubler, D.J., Reiter, P., Ebi, K.L., Yap, W., Nasci, R., Patz, J.A.: Climate variability and change in
the United States: potential impacts on vector-and rodent-borne diseases. Environ. Health Perspect.
109(Suppl2),223–233(2001)
17. Mabaso,M.L.H.,Craig,M.,Ross,A.,Smith,T.:Environmentalpredictorsoftheseasonalityofmalaria
transmissioninAfrica:thechallenge.Am.J.Trop.Med.Hyg.76(1),33–38(2007).AmericanSociety
ofTropicalMedicineandHygiene
18. Ezeakacha,N.F.,Yee,D.A.:Theroleoftemperatureinaffectingcarry-overeffectsandlarvalcompetition
inthegloballyinvasivemosquitoAedesalbopictus.ParasitesVectors12,1–11(2019).Springer
19. Couper,L.I.,Farner,J.E.,Caldwell,J.M.,Childs,M.L.,Harris,M.J.,Kirk,D.G.,Nova,N.,Shocket,
M.,Skinner,E.B.,Uricchio,L.H.,Exposito-Alonso,M.,Mordecai,E.A.:Howwillmosquitoesadaptto
climatewarming?eLife10,e69630(2021)
20. Eisele,T.P.,Keating,J.,Swalm,C.,Mbogo,C.M.,Githeko,A.K.,Regens,J.L.,Githure,J.I.,Andrews,L.,
Beier,J.C.:Linkingfield-basedecologicaldatawithremotelysenseddatausingageographicinformation
systemintwomalariaendemicurbanareasofKenya.Malar.J.2(1),1–17(2003).BioMedCentral
21. Wayant,N.M.,Maldonado,D.,deArias,A.R.,Cousiño,B.,Goodin,D.G.:Correlationbetweennormal-
izeddifferencevegetationindexandmalariainasubtropicalrainforestundergoingrapidanthropogenic
alteration.Geosp.Health4(2),179–190(2010)
22. Gaudart,J.,Touré,O.,Dessay,N.,Dicko,A.L.,Ranque,S.,Forest,L.,Demongeot,J.,Doumbo,O.K.:
ModellingmalariaincidencewithenvironmentaldependencyinalocalityofSudanesesavannaharea,
Mali.Malar.J.8,1–12(2009).Springer
23. McKenzie,F.E.:Whymodelmalaria?Parasitol.Today16(12),511–516(2000).Elsevier
24. Abboubakar,H.,Buonomo,B.,Chitnis,N.:Modellingtheeffectsofmalariainfectiononmosquitobiting
behaviourandattractivenessofhumans.Ric.Mat.65(1),329–346(2016).Springer
25. Kouchérè,A.,Abboubakar,H.,Damakoa,I.:Analysisofamosquitolifecyclemodel.ARIMA34(2021).
Episciences.org
26. Koella,J.C.:Ontheuseofmathematicalmodelsofmalariatransmission.ActaTrop.49(1),1–25(1991).
Elsevier
27. Ross,R.:ThePreventionofMalaria.JohnMurray,London(1911)
28. Anderson,R.M.,May,R.M.:InfectiousDiseasesofHumans:DynamicsandControl.OxfordUniversity
Press,Oxford(1992)
29. Koella,J.C.,Boete,C.:Amodelforthecoevolutionofimmunityandimmuneevasioninvector-borne
diseaseswithimplicationsfortheepidemiologyofmalaria.Am.Nat.161(5),698–707(2003).TheUni-
versityofChicagoPress
30. Kribs-Zaleta,C.M.,Martcheva,M.:Vaccinationstrategiesandbackwardbifurcationinanage-since-
infectionstructuredmodel.Math.Biosci.177,317–332(2002).Elsevier
31. Macdonald,G.:TheEpidemiologyandControlofMalaria.OxfordUniversityPress,London(1957)
32. Abiodun,G.J.,Njabo,K.Y.,Witbooi,P.J.,Adeola,A.M.,Fuller,T.L.,Okosun,K.O.,Makinde,O.S.,
Botai,J.O.:Exploringtheinfluenceofdailyclimatevariablesonmalariatransmissionandabundanceof
AnophelesarabiensisoverNkomazilocalmunicipality,Mpumalangaprovince,SouthAfrica.J.Environ.
PublicHealth(2018).Hindawi

--- Page 38 ---
5 Page38of39 K.J.GatoreSinigiriraetal.
33. Abdelrazec, A., Gumel, A.B.: Mathematical assessment of the role of temperature and rainfall on
mosquitopopulationdynamics.J.Math.Biol.74,1351–1395(2017)
34. DanturJuri,M.J.,Estallo,E.,Almirón,W.,Santana,M.,Sartor,P.,Lamfri,M.,Zaidenberg,M.:Satellite-
derivedNDVI,LST,andclimaticfactorsdrivingthedistributionandabundanceofanophelesmosquitoes
inaformermalariousareainnorthwestArgentina.J.VectorEcol.40(1),36–45(2015)
35. Amadi,J.A.,Olago,D.O.,Ong’amo,G.O.,Oriaso,S.O.,Nanyingi,M.,Nyamongo,I.K.,Estambale,
B.B.A.:SensitivityofvegetationtoclimatevariabilityanditsimplicationsformalariariskinBaringo,
Kenya.PLoSONE13(7)(2018)
36. Ferraccioli, F., Riccetti, N., Fasano, A., Mourelatos, S., Kioutsioukis, I., Stilianakis, N.I.: Effects of
climaticandenvironmentalfactorsonmosquitopopulationinferredfromWestNilevirussurveillancein
Greece.Sci.Rep.13(1),18803(2023).NaturePublishingGroupUKLondon
37. Graumans,W.,Jacobs,E.,Bousema,T.,Sinnis,P.:Whenisaplasmodium-infectedmosquitoaninfec-
tiousmosquito?TrendsParasitol.36(8),705–716(2020)
38. Diekmann,O.,Heesterbeek,J.A.P.,Metz,J.A.J.:Onthe definition andthe computation ofthebasic
reproduction ratio R0 inmodels forinfectious diseasesinheterogeneous populations. J.Math.Biol.
28(4),365–382(1990)
39. vandenDriessche,P.,Watmough,J.:Reproductionnumbersandsub-thresholdendemicequilibriafor
compartmentalmodelsofdiseasetransmission.Math.Biosci.180(1–2),29–48(2002)
40. Mandal,S.,Sarkar,R.R.,Sinha,S.:Mathematicalmodelsofmalaria-areview.Malar.J.10(1),1–19
(2011).BioMedCentral
41. Chowell,G.,Diaz-Duenas,P.,Miller,J.C.,Alcazar-Velazco,A.,Hyman,J.M.,Fenimore,P.W.,Castillo-
Chavez,C.:EstimationofthereproductionnumberofDenguefeverfromspatialepidemicdata.Math.
Biosci.208(2),571–589(2007)
42. vandenDriessche,P.:Reproductionnumbersofinfectiousdiseasemodels.Infect.Dis.Model.2(3),
288–303(2017).https://doi.org/10.1016/j.idm.2017.06.002
43. Bavafa-Toosi, Y.: Introduction toLinearControl Systems, pp. 265–331. AcademicPress, San Diego
(2019).https://doi.org/10.1016/B978-0-12-812748-3.00003-3
44. Castillo-Chavez,C.,Feng,Z.,Huang,W.:OnthecomputationofR0anditsroleonglobalstability.In:
MathematicalApproachesforEmergingandRe-EmergingInfectionDiseases:AnIntroduction,vol.125,
pp.31–65(2002)
45. Juga,M.L.,Nyabadza,F.,Chirove,F.:AnEbolavirusdiseasemodelwithfearandenvironmentaltrans-
missiondynamics.Infect.Dis.Model.6,545(2021)
46. Castillo-Chavez,C.,Song,B.:Dynamicalmodelsoftuberculosisandtheirapplications.Math.Biosci.
Eng.1(2),361–404(2004)
47. Bari,E.,Nipa,N.J.,Roy,B.:Associationofvegetationindiceswithatmospheric&biologicalfactors
usingMODIStimeseriesproducts.Environ.Chall.5,100376(2021)
48. Abraham,B.O.,Ledolter,J.:Seasonalautoregressiveintegratedmovingaveragemodels.In:Statistical
MethodsforForecasting(2008)
49. WorldPopulationReview:BurundiPopulation2024(Live)(n.d.).Accessedon:2024-05-17.Available
athttps://worldpopulationreview.com/countries/burundi
50. Blayneh,K.,Cao,Y.,Kwon,H.D.:Optimalcontrolofvector-bornediseases:treatmentandprevention.
DiscreteContin.Dyn.Syst.,Ser.B11(3),587–611(2009)
51. Gomero,B.:LatinHypercubeSamplingandPartialRankCorrelationCoefficientAnalysisAppliedtoan
OptimalControlProblem.Master’sThesis,UniversityofTennessee(2012).https://trace.tennessee.edu/
utk_gradthes/1278
52. Waite,J.L.,Suh,E.,Lynch,P.A.,Thomas,M.B.:Exploringthelowerthermallimitsfordevelopmentof
thehumanmalariaparasite,plasmodiumfalciparum.Biol.Lett.15(6),20190275(2019)
53. Patz,J.A.,Olson,S.H.:Malariariskandtemperature:influencesfromglobalclimatechangeandlocal
landusepractices.Proc.Natl.Acad.Sci.USA103(15),5635–5636(2006)
54. Smith,D.C.,Schäfer,S.M.,Golding,N.,Nunn,M.A.,White,S.M.,Callaghan,A.,Purse,B.V.:Veg-
etationstructuredrivesmosquitocommunitycompositioninUK’slargestmanagedlowlandwetland.
ParasitesVectors17(1),201(2024)
55. Greene,J.A.,Vargha,D.:Endsofepidemics.In:COVID-19andWorldOrder:TheFutureofConflict,
Competition,andCooperation,pp.23–39(2020)
56. Fathauer,T.:Aglimpseintoachangingclimate:new1981–2010climatenormalstakeeffect.Weather-
wise64(6),34–36(2011)
57. Mfisimana,L.D.,Nibayisabe,E.,Badu,K.,Niyukuri,D.:Exploringpredictiveframeworksformalaria
inBurundi.Infect.Dis.Model.7(2),33–44(2022)
58. Sinzinkayo,D.,Baza,D.,Gnanguenon,V.,Koepfli,C.:Thelead-uptoepidemictransmission:malaria
trendsandcontrolinterventionsinBurundi2000to2019.Malar.J.20(1),298(2021)

--- Page 39 ---
MathematicalModellingofMalariaIntegratingTemperature,Rainfall... Page39of39 5
59. VanBortel,W.,Mariën,J.,Jacobs,B.K.M.,Sinzinkayo,D.,Sinarinzi,P.,Lampaert,E.,D’hondt,R.,
Mafuko,J.-M.,DeWeggheleire,A.,Vogt,F.,etal.:Long-lastinginsecticidalnetsprovideprotection
against malaria for only a single year in Burundi, an African highland setting with marked malaria
seasonality.BMJGlob.Health7(12),e009674(2022)
60. Ngarakana-Gwasira,E.T.,Bhunu,C.P.,Mashonjowa,E.:Assessingtheimpactoftemperatureonmalaria
transmissiondynamics.Afr.Math.25(4),1095–1112(2014)
61. Okiring,J.,Routledge,I.,Epstein,A.,Namuganga,J.F.,Kamya,E.V.,Obeng-Amoako,G.O.,Sebuguzi,
C.M.,Rutazaana,D.,Kalyango,J.N.,Kamya,M.R.,etal.:Associationsbetweenenvironmentalcovari-
atesandtemporalchangesinmalariaincidenceinhightransmissionsettingsofUganda:adistributedlag
nonlinearanalysis.BMCPublicHealth21,1–11(2021)
62. Okuneye,K.,Gumel,A.B.:Analysisofatemperature-andrainfall-dependentmodelformalariatrans-
missiondynamics.Math.Biosci.287,72–92(2017)
63. Google Earth Engine: Google Earth Engine (n.d.). Accessed on: 2024-07-19. Available at https://
earthengine.google.com/
Publisher’sNote SpringerNatureremainsneutralwithregardtojurisdictionalclaimsinpublishedmapsand
institutionalaffiliations.