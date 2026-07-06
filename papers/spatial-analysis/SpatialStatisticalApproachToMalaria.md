# SpatialStatisticalApproachToMalaria

**Source PDF:** `SpatialStatisticalApproachToMalaria.pdf`  
**Path:** `papers/spatial-analysis/SpatialStatisticalApproachToMalaria.pdf`  

---

--- Page 1 ---
© International Epidemiological Association 2000 Printed in Great Britain International Journal of Epidemiology 2000;29:355–361
A spatial statistical approach
to malaria mapping
I Kleinschmidt,a M Bagayoko,b GPY Clarke,c M Craiga and D Le Sueura
Background Good maps of malaria risk have long been recognized as an important tool for
malaria control. The production of such maps relies on modelling to predict the
risk for most of the map, with actual observations of malaria prevalence usually
only known at a limited number of specific locations. Estimation is complicated
by the fact that there is often local variation of risk that cannot be accounted for
by the known covariates and because data points of measured malaria prevalence
are not evenly or randomly spread across the area to be mapped.
Method We describe, by way of an example, a simple two-stage procedure for producing maps
of predicted risk: we use logistic regression modelling to determine approximate
risk on a larger scale and we employ geo-statistical (‘kriging’) approaches to
improve prediction at a local level. Malaria prevalence in children under 10 was
modelled using climatic, population and topographic variables as potential pre-
dictors. After the regression analysis, spatial dependence of the model residuals
was investigated. Kriging on the residuals was used to model local variation in
malaria risk over and above that which is predicted by the regression model.
Results The method is illustrated by a map showing the improvement of risk prediction
brought about by the second stage. The advantages and shortcomings of this
approach are discussed in the context of the need for further development of
methodology and software.
Keywords Malaria risk, disease maps, geo-statistics, spatial analysis, kriging, climatic factors
Accepted 22 July 1999
Malaria is a major cause of morbidity and mortality in Africa, prevalence usually only known at a limited number of specific
and is a leading cause of death especially amongst children, in locations. Accurate prediction of risk is dependent on know-
many African countries.1,2 The MARA/AMRA project3 has ledge of a number of environmental and climatic factors that are
been set up recently to collate sources of data on malaria, and related to malaria transmission.6–8 However, the estimation is
to model and map malaria risk across the continent. Accurate complicated by the fact that there is often local variation of risk
maps of malaria have been recognized as an important tool in that cannot easily be accounted for by the known covariates.
the hands of control programme managers.4,5 This paper de- A further complication arises from the fact that data points of
scribes the statistical methods used to produce a map of malaria measured malaria prevalence are not evenly or randomly spread
risk for Mali and discusses the methodological issues that are across a country, but are often closely clustered in areas of high
raised. A companion paper discusses in detail the substantive risk. Any modelling of risk has to take account of spatial auto-
aspects of the results of this work and its policy implications correlation of the data, and allow for local deviation from pre-
(Bagayoko M, Kleinschmidt I, Sogoba N, Craig M, Le Seur D, dictions that are based on the known climatic covariates.
Toure YTT. Mapping malaria risk in Mali. [in preparation]). In this project a two-stage procedure was followed: (1) gen-
The production of malaria maps relies on modelling to predict eralized linear regression modelling was applied to determine
the risk for most of the map, with actual observations of malaria approximate risk on a larger scale by identifying important
climatic and environmental determinants and (2) the geo-
aMedical Research Council (South Africa), 771 Umbilo Road, Congella, statistical kriging method was used to improve prediction at a
Durban 4001, South Africa. local level.
bMalaria Research and Training Center DEAP/FMPOS, Université du Mali,
Bamako, Mali.
c Department of Statistics and Biometry, University of Natal, Pietermaritzburg, Data Collection and Data Preparation
South Africa.
Malaria prevalence data were collated from surveys of child-
Reprint requests to: Immo Kleinschmidt, Medical Research Council (South
hood populations in Mali since 1960. Altogether 101 such
Africa), 771 Umbilo Road, Congella, Durban 4001, South Africa. E-mail:
kleinsci@mrc.ac.za surveys were identified yielding suitable estimates of malaria
355

--- Page 2 ---
356 INTERNATIONAL JOURNAL OF EPIDEMIOLOGY
prevalence. The surveys represent historical data whose approximately to the dry season (December–May) and the wet
screening for inclusion in the MARA/AMRA database has been season (June–November), respectively.
documented elsewhere.3 For example surveys carried out
amongst non-representative samples of respondents were
Methods and Results
excluded. Similarly, surveys conducted during known malaria
epidemics were also excluded. In the absence of large-scale The first stage of this analysis involved ordinary logistic regres-
intervention or climatic change it was assumed that malaria sion analysis to determine the relationship between malaria
endemicity in Mali has remained reasonably stable. All the sur- prevalence and ecological predictors of malaria. From this a first
veys were carried out in a confined locality so that the survey prediction map for the whole of Mali was produced. In the
results collectively could be regarded as a cross-section of point- second stage we investigated spatial pattern in the residuals of
referenced malaria prevalence observations. the model and used residual spatial dependence in the data to
For each survey the total sample size and number of improve prediction at local level.
individuals testing positive was known. The geographical co-
ordinates of each survey were established using paper maps, Regression analysis
electronic maps and global positioning systems. The distribution The relationship between malaria parasite prevalence and each
of surveys across Mali was uneven, with higher concentrations individual potential explanatory variable was first investigated
of surveys in more densely populated areas and in areas where by inspection of scatter-plots and by single variable regression
malaria risk was perceived to be high. The location of each analysis. Since parasite prevalence data are binomial fractions, a
survey is shown in Figure 1. logistic regression model for grouped (blocked) data was used as
For each of the survey co-ordinates long-term climatic is standard practice for the analysis of such data.12 Predictions
averages, normalized difference vegetation index (NDVI)9 and of prevalence made from the logistic model will always fall
population density were obtained. A number of published data within the interval 0 to 1. Larger surveys are implicitly accorded
sets were available for this purpose.10,11The resultant array of more weight than the smaller ones. The glm command in the
variables consisted of: monthly rainfall, monthly average max- statistical package STATA13was used for the analysis.
imum temperature, monthly average minimum temperature, Each of the explanatory variables was adjusted for all of the
monthly NDVI and population density. In addition, the number others by performing multiple regression in the usual way. Non-
of months with rainfall (cid:46)60 mm (regarded as suitable for linearity in the relationship between parasite prevalence and
malaria transmission) was computed for each location. Using a predictor variable was explored by adding polynomial terms
Geographic Information Systems (GIS), the distance to the and then grouping the values of continuous variables into
nearest water body was also calculated. categorical ones. Variable selection for the multiple logistic
All climatic variables were available as long-term averages for regression model was carried out by a combination of automatic
each calendar month, but not by individual year. The individual (stepwise) procedures, goodness-of-fit criteria and by using
monthly averages of the climatic variables are highly correlated judgement in selecting variables that explain malaria prevalence
within climatic seasons. The question arises over what period in terms of vector, host and parasite dynamics of malaria. An
climatic variables should be sensibly averaged. The shorter the additional criterion for selection of the final model was the
aggregation period the stronger the likelihood of a high degree degree of spatial correlation of the model residuals (see below).
of serial autocorrelation in the values. For the purpose of select- The final multiple logistic regression model contained four
ing climatic variables for explaining the variation in malaria significant explanatory variables for the prediction of malaria
prevalence it was decided to average monthly climatic data over prevalence. These were distance to water (categorical), average
climatic seasons in order to reflect the variation in weather. NDVI during the wet season (June–November, also categorical),
Temperature and rainfall were averaged over 3-month periods, number of months with (cid:46)60 mm rainfall, and average max-
with the first quarter starting in December to coincide with imum temperature during the quarter March–May. The detailed
the beginning of the dry season. The vegetation index NDVI results are discussed in the companion paper. Table 1 sum-
was aggregated over two 6-month periods corresponding marizes these results.
The final model explains about 65% of the total variation
in malaria if one takes the reduction in deviance as a measure
of variation. It must be noted that the final model is ‘overdis-
persed’, i.e. the residual deviance is larger than would be ex-
pected for the number of degrees of freedom. This has been
taken into account in the model by using a deviance-based extra
dispersion parameter, which results in inflating the standard
errors of the model parameters by the square root of the dis-
persion factor.14The inclusion criteria for the variables selected
for the final model can therefore be regarded as conservative.
For each variable used in the model an image covering the
whole of Mali was produced in the GIS package IDRISI.15In the
case of categorical variables this entailed creating the equivalent
Boolean indicator variables as used in the statistical model. The
prediction formula of the model was then used with the IDRISI
Figure 1 Map showing survey sites image calculator to produce a prediction image. The predicted

--- Page 3 ---
MALARIA MAPPING 357
Table 1 Factors associated with malaria parasite prevalence. Adjusted odds ratios (and 95% CI) obtained by multiple logistic regression
Unadjusted Adjusted
Variable Odds ratio 95% CI Odds ratio 95% CI
Vegetation index (NDVI) in rainy season (relative to NDVI of (cid:60)0.50)
0.50 (cid:46)NDVI (cid:60)0.7 16.17 4.96–52.74 4.13 1.37–12.47
NDVI (cid:46) 0.7 36.30 11.00–119.74 4.90 1.29–18.55
Distance to water (relative to (cid:44)4 km)
4–40 km 2.63 2.52–2.74 2.55 1.90–3.423
(cid:46)40 km 0.19 0.17–0.23 0.70 0.24–2.11
Average maximum temperature, March–May, change per °C 0.75 0.63–0.88 1.40 1.14–1.72
Length of rainy season (months), change for each month of season length 1.62 1.59–1.64 1.76 1.33–2.34
Figure 2 Map of predicted malaria risk based on regression model only
risks were then grouped into four categories: (cid:44)10%, 10–30%, We used two separate methods to investigate spatial pattern: the
30–70% and (cid:46)70%. As an additional validation exercise, the D-statistic and the variogram.
predicted frequencies in these four categories were compared The non-parametric D-statistic16 is a weighted average of
with those of the known values. Of the 101 survey results, 70 rank differences in the values of observations, with the average
fall within their predicted group. The resulting map of malaria taken over all pairs of points. If y refers to the rank of the value
i
risk is shown in Figure 2. at any point i, then D is defined by
Investigation of spatial pattern (cid:229) (cid:229) (cid:119) (cid:41)(cid:121) - (cid:121) (cid:41)
(cid:68)= (cid:105)(cid:106) (cid:105) (cid:106)
For geographical data of the type of the malaria survey data, it (cid:229) (cid:229) (cid:119)
(cid:105)(cid:106)
is of interest to know whether the data display any spatial auto-
correlation, i.e. do surveys that are near in space have values Weights w refer to pairs of points. Weights can be chosen in
ij
(of malaria prevalence) that are similar, in contrast to surveys different ways, but should be large for points that are near
that are far apart. Put another way, does nearness in space go in space and small or zero for points that are distant in space. In
together with nearness in value? This is important because this analysis two approaches to assigning weights were used: (a)
spatially correlated data cannot be regarded as independent all pairs of points that were within a particular distance of each
observations. If the analysis does not take account of the cor- other were assigned a weight of 1, all other points were assigned
relation structure of the data, the estimates obtained from a weight of zero (binary neighbourhood weights); and (b) the
modelling may be inaccurate. weight for each pair of points was assigned the inverse of the
The malaria prevalence data and the residuals of the regres- distance between them. If there is spatial autocorrelation, rank
sion model were analysed for the presence of spatial pattern. differences for nearby pairs of points will be small values, whilst

--- Page 4 ---
358 INTERNATIONAL JOURNAL OF EPIDEMIOLOGY
Table 2 Results of tests for autocorrelation by non-parametric D (P-values)
Autocorrelation of Autocorrelation of
Type of weight for pairs of points observed malaria prevalence model residuals
Binary neighbourhood weights, 50km (cid:44)0.0005 0.05
Binary neighbourhood weights, 15km (cid:44)0.0005 0.001
Inverse distance weights (cid:44)0.0005 0.006
the weights for these pairs of points will be large values. Distant
pairs of points on the other hand would be expected to display
large differences in rank, but these would be multiplied by low
or zero values of weights. The overall effect is that D will be a
smaller value if there is spatial pattern in the data than if the
ranks of points were randomly distributed, i.e. near and far pairs
of points showing no significant differences in rank difference.
A significance test was obtained by simulation. The simulation
consists of randomly assigning ranks to the data points and then
calculating D assuming the particular pattern of weights given by
the spatial layout of the data. This process is repeated many
times over, and the distribution of the simulated D is then com-
pared to the actual value of D calculated from the observed Figure 3 Variogram of model residuals (lag = 8 km)
data. This directly yields a P-value for significant evidence of
spatial autocorrelation. For mutual binary weights an analytical residuals (Figure 3) shows that there is some evidence of spatial
test was used,17which is computationally less demanding. correlation over short ranges (cid:44)20 km.
Since it is based on the ranks of the data rather than the
actual values, the D-statistic is not dependent on normality of Geo-statistical prediction (kriging)
the data. In the malaria data (and generally) negative auto- Prediction by kriging18–21 is based on the assumption that
correlation is not likely, since this would assume distant points covariance between points is entirely a function of distance
to be more similar than near ones. Therefore, a one-sided sig- between them as modelled by means of the variogram. A
nificance test was used, rejecting the null hypothesis of random further assumption is that the underlying mean of the quantity
spatial pattern if the value of D is sufficiently small. that is being predicted is constant (the assumption of station-
The semi-variogram18–20(often simply called the variogram) arity).
also measures spatial dependency, but there is no significance Since the variogram describes the spatial dependence between
test associated with this measure. It is normally used to obtain the observed measurements as a function of the distance between
a spatial model for kriging, but it also serves to examine spatial them, it allows us to estimate the value of malaria prevalence
pattern. The semi-variance g (h) measures half the average at any point from the observed data. The value of prevalence, Z,
squared difference between pairs of data values separated by the at the coordinates(x , y ) can be estimated from the n nearest
0 0
so-called lag distance, h. sampling values Z (x , y ), Z (x , y ), … Z (x , y ) by the
obs 1 1 obs 2 2 obs n n
linear formula
(cid:78)(cid:40)(cid:104)(cid:41)
g(cid:40)(cid:104)(cid:41)= (cid:50)(cid:78) (cid:49) (cid:40)(cid:104)(cid:41) (cid:229) (cid:105) (cid:40)(cid:121) (cid:105) - (cid:121) (cid:106) (cid:41)(cid:50) (cid:90)(cid:195)(cid:40)(cid:120) (cid:48) (cid:44)(cid:121) (cid:48) (cid:41)= (cid:229) (cid:110) (cid:97) (cid:105) (cid:90) (cid:111)(cid:98)(cid:115) (cid:40)(cid:120) (cid:105) (cid:44)(cid:121) (cid:105) (cid:41)
(cid:105)=(cid:49)
where N(h)is the number of pairs of sample points at a distance
in the range h ± h/2 from each other. Computations of g (h) The a are found by introducing a Lagrange multiplier l and
i
are repeated for 2h, 3h, 4h… etc. The semi-variogram is a plot solving the system:
of the semi-variance g (h) against lag distance h. If the semi-
(cid:110)
variance is markedly small for low values of hit is taken as an (cid:229) (cid:97)g(cid:40)(cid:104) (cid:41)+l =g (cid:40)(cid:104) (cid:41)(cid:44)(cid:106)=(cid:49)(cid:44)(cid:46)(cid:46)(cid:46)(cid:44)(cid:110)
(cid:105) (cid:105)(cid:44)(cid:106) (cid:105)(cid:44)(cid:48)
indication of spatial autocorrelation, i.e. values at short distance
(cid:105)=(cid:49)
from each other are more alike (less variable) than those at
large distances. under the constraint
Table 2 shows that the observed malaria prevalence for Mali
(cid:110)
is highly autocorrelated in space, as one would expect on account (cid:229) (cid:97) =(cid:49)
(cid:105)
of its strong link with climatic factors. The model residuals
(cid:105)=(cid:49)
still show evidence of spatial pattern, but some of this has been
removed by the modelling process. This result holds whether where h is the distance between two points located at (x,y)
i,j i i
spatial pattern is assessed using the D-statistic with inverse and (x,y), at which malaria prevalence has been measured,
j j
distance weights or binary neighbourhood weights. It can be and h is the distance between a measured point and the point
j,0
seen from the P-value for binary weights, that the spatial pat- (x ,y ) at which the prediction is to be made. g (h) is the semi-
0 0
tern is more distinct over short distances. The semi-variogram of variance as previously defined.

--- Page 5 ---
MALARIA MAPPING 359
The extreme variation in the Mali malaria prevalence data residuals)/[1 + exp(Xb + kriged residuals)]} to produce a new
invalidates the assumption that a common mean exists. There is prediction map (Figure 4). This map takes into account local
clearly a need to take covariates into account due to the strong spatial dependence and allows local deviation from the pre-
association between malaria risk and climatic factors, and due to diction of the logistic model.
the wide variation of the latter across Mali. Residuals from the To see how much improvement was achieved by local kriging,
logit model should be free of covariate effects and the logit another map was produced showing the difference betweenthe
transformation will moderate any non-homogeneity in vari- final map (Figure 4), and the original map produced by regres-
ance of the residuals. sion only (Figure 2). This difference map is shown in Figure 5.
Inspection of the variogram based on the residuals (Figure 3) The new map results in an improvement of FIVE additional
shows that there is spatial dependence (not taken into account surveys whose observed prevalence falls within the predicted
by the model) over short distances up to about 15 or 20 km. prevalence bands of the map. (We would expect that this can
A variogram of logit scale model residuals was constructed, be improved upon with a higher grid resolution.) A weighted
confirming a short range spatial pattern up to distances of about inter-rater kappa statistic23 for agreement between observed
18 km, although the relatively small number of pairs of points and predicted map values for the surveys shows an improve-
that are less than this distance apart makes the variogram less ment from 0.624 for the map based on regression only to 0.727
reliable in this region. This means that there is small area for the map based on the two-stage procedure. This takes into
variation in malaria prevalence which cannot be modelled well account not only agreement/non-agreement between observed
by climatic factors presumably because these do not vary much and expected prevalence bands, but also the seriousness of dis-
over this short distance. cordance, if any.
Kriging performed on residuals is equivalent to kriging a
variable which has an underlying (stationary) mean of zero.
Discussion
To carry out this process residuals for all observed points were
calculated on the logit (ln(p/1 – p)) scale of the logistic model. The final malaria prediction map is in agreement with eco-
Spatial dependence of these was modelled using the previously geographical descriptive epidemiology of malaria in Mali.24
constructed variogram. An exponential model was fitted to the Kriging has significantly improved the prediction of malaria risk
variogram using a sill and nugget of 0.7 and 0.4, respectively, in parts of the map, particularly where the density of surveys is
and a range of 18 km. This geo-statistical model was then used high, which coincides with areas of high risk. However, given that
in the kriging procedure of the package GEO-EAS22to map pre- the data used for obtaining the model are not a random sample
dictions of residuals in an 18 km radius around each obser- of the population or a spatially well-distributed set of sampling
vation. These logit scale ‘kriged’ residual predictions were then points, one needs to be cautious in extrapolating the predicted
added to the logit scale predicted values produced from the orig- risk to points outside the data set as has been done here.
inal logistic model. The resultant map predictions were trans- A concern with spatial data is the potential for spatial
formed back to prevalences in the usual way {exp(Xb + kriged correlation in the observations, which could lead to incorrect
Figure 4 Map of predicted malaria risk using regression model plus kriging

--- Page 6 ---
360 INTERNATIONAL JOURNAL OF EPIDEMIOLOGY
Figure 5 Map showing difference in predicted malaria risk as a result of kriging
estimates. Spatial clustering of disease is almost inevitable since approach. The non-spatial model provides the covariate adjust-
human populations generally live in spatial clusters rather than ment and prediction of mean risk in an area. It thereby allows
random distribution of space. An infectious disease that is heavily for non-stationarity in the data by modelling the long range
associated with climatic variables is likely to be spatially clustered differentials in the malaria risk pattern. Kriging of the resulting
even if population distribution was not clustered. The model residuals allows for local deviation from the predicted mean and
derived here explains some of the spatial pattern of malaria risk, for spatial dependence in points that are close together. In the
but there is still significant spatial correlation, particularly over MARA project it is unlikely that local predictors affecting
short distances (cid:44)20 km. (This result holds for differing ways of malaria risk over and above what is predicted by climatic factors
defining ‘nearness’ in the D-statistic and is confirmed by the will ever be available. For this reason local variation from the
variogram method.) The reduction in spatial structure in the more global area prediction has to be taken into account by
residuals lends credence to the correctness of the model. spatial modelling.
Overdispersion in the logistic model does indicate that there Whilst the kriging process will give minimized unbiased
may be important covariates missing from the model. Some of prediction error (of residuals) on the logit scale, this cannot be
these unknown predictors are likely to be spatially distributed, guaranteed for the backtransformed predictions.25 However,
particularly at a local level. the kriged logit scale residuals are only a component (in most
Kriging with a non-stationary mean (‘universal kriging’) is a cases a small component) of the linear predictor which is back-
refinement of ordinary kriging in that it allows for covariate transformed to produce the final prediction for the point on the
adjustment by means of regression modelling.20This would be map.
more appropriate in the case of malaria risk where we know Prediction based on regression alone has a tendency to
that climatic factors are strong predictors. Since the mean pre- produce predicted values that are pulled towards the mean. For
valence is now a function of the covariates, rather than a con- example, two observations in different parts of the country with
stant, the model assumptions would not be violated as in the very similar climatic data may differ in their observed malaria
case of ordinary kriging. Universal kriging offers the most com- prevalence value. Regression modelling would predict for these
prehensive approach to the mapping of malaria risk: it uses the two places a value close to the mean prevalence of the two
values of the covariates (climate data) at the point at which the points. This would result in large residuals. Kriging the residuals
prediction has to be made, as well as the position of the point in and adding the predicted residuals to the model predictions will
relation to points at which observed values of malaria risk are produce predictions that are closer to the observed prevalences
available. Universal kriging applied to generalized linear models in each neighbourhood, particularly if the deviation from the
such as the logistic model, is currently not available and we model prediction is supported by other points in the neigh-
have therefore not been able to apply it as such. bourhood.
The two-stage approach that we used offers an appealing As one might expect therefore, the range of final predictions
alternative to universal kriging and it is somewhat similar in from the two-stage method is wider than that produced by the

--- Page 7 ---
MALARIA MAPPING 361
regression model alone, with predictions ranging from about 2Binka FN. Impact and Determinants of Permethrin Impregnated Bednets on
0% to 92% (compared to a range of 0% to 80% for the logistic Child Mortality in Northern Ghana. Phd thesis. Swiss Tropical Institute,
model alone). As can be seen from the new prediction map Basel, 1997.
(Figure 4) and the difference map (Figure 5), the changes brought 3Towards an Atlas of Malaria Risk in Africa. First technical report of the
about by this process are confined to areas around most of the MARA/ARMA collaboration. MARA/AMRA, 771 Umbilo Road,
survey locations. For the rest of the map the data are too sparse Congella, Durban, South Africa. December 1998.
to be affected by this process, i.e. most places are more than 18 4Snow RW, Marsh K, Le Sueur D. The need for maps of transmission
km removed from the nearest survey. intensity to guide malaria control in Africa. Parasitol Today1996;12:
455–57.
A problem with this approach is that often there are
5Kitron U, Pener H, Costin C, Orshan L, Greenberg Z, Shalom U.
insufficient data points to give us a good basis for estimating the
Geographic information systems in malaria surveillance: mosquito
local variability. In the case of malaria maps this problem is
breeding and imported cases in Israel, 1992. Am J Trop Med Hyg1994,
less serious in those areas where malaria prevalence is highest,
50:550–56.
simply because the frequency of surveys is greatest in these 6Craig MH, Snow RW, Le Sueur D. A climate-based distribution model
areas. The map is therefore likely to be at its most accurate of malaria transmission in Africa. Parasitol Today1999 (In Press).
where it matters most: in places where malaria prevalence is 7Snow RW, Gouws E, Omumbo JA et al. Models to predict the intensity
high. of Plasmodium falciparumtransmission: applications to the burden of
It should be noted that universal kriging might have resulted disease in Kenya. Trans R Soc Trop Med Hyg1998;92:601–06.
in a different model to the one obtained here, since it attempts 8Beck LR, Rodriguez MH, Dister SWet al. Remote sensing as a land-
to simultaneously obtain good estimation of covariate effects scape epidemiologic tool to identify villages at high risk for malaria
and allow for residual spatial pattern. In this particular example, transmission. Am J Trop Med Hyg1994;51:271–80.
however, the residual spatial correlation was weak and there- 9NDVI Image Bank Africa 1981–1991 (CD-ROM). Food and Agriculture
fore we would not expect that universal kriging would have Organization (FAO) of the United Nations Remote Sensing Centre;
Africa Real Time Environmental Monitoring Information System
produced a model that differs much from the present one.
(ARTEMIS), NASA Goddard Space Flight Centre, Greenbelt, MD
We are currently investigating an iterative approach that would
20771, USA, 1991.
be applicable in situations were the residual spatial pattern is
10Hutchinson MF, Nix HA, McMahon JP, Ord KD. Climate Data: A
substantial.
Topographic and Climate Database (CD-Rom). Centre for Resource and
The specification of a nugget variance makes allowance for Environmental Studies, The Australian National University, Canberra,
measurement error at a location. This avoids the prediction ACT 0200, Australia, 1995.
‘honouring’ every observation, which would result in a very 11African Data Sampler (CD-ROM). World Resources Institute (WRI). 1709
spiky map. Future development in this area should include a New York Ave, NW, Washington, DC 20006, USA, 1995.
method of weighting the observations in such a way that large 12Hosmer DW, Lemshow S.Applied Logistic Regression. New York: John
surveys draw the map prediction closer to their observed value Wiley & Sons, 1989.
than small surveys. 13Stata Corp. Stata®Statistical Software: Release 5.0. College Station, TX:
Additional further work in this area would be to develop Stata Corporation, 1997.
‘goodness-of-fit’ indicators for this two-stage method. For 14Littell RC, Milliken GA, Stroup WW, Wolfinger RD. SAS®System for
example, how much of the overdispersion in the model has been Mixed Models.Cary, NC: SAS Institute Inc., 1996.
taken up by local kriging? What proportion of variation 15Clark Labs. Idrisi for Windows Version 2.008. The Idrisi Project, Clark
in the data is ‘explained’ by kriging? It would also be important University, Worcester, MA, 1998.
to produce combined prediction errors for the whole map, taking 16Walter SD. The analysis of regional patterns in health data, Part 1.
into account both components of the process of prediction. Am J Epidemiol1992;136:730–41.
In conclusion, our view is that the model produced here is a 17Walter SD. A simple test for spatial pattern in regional health data. Stat
reasonable representation of malaria risk in Mali. The reduction Med1994;13:1037–44.
of residual spatial pattern enhances our confidence in the 18Oliver MA, Muir KR, Webster R et al.. A geostatistical approach to the
fidelity of the model and residual spatial dependence has been analysis of pattern in rare disease. J Public Health Med 1992;14:280–89.
modelled by kriging wherever the density of observed points 19Carrat F, Valleron AJ. Epidemiologic mapping using the ‘kriging’
method: application to an influenza-like illness epidemic in France.
allows for this. Kriging has been made possible by ‘levelling’
Am J Epidemiol1992;135:1293–300.
the map through the regression model, and applying the
20Diggle PJ, Tawn JA, Moyeed RA. Model based geostatistics. J R Statist
kriging process to the residuals. The final predictions make
Soc C1998;47:299–350.
sense from the entomological perspective. However, a more
21Krige, DG. Two dimensional weighted moving average trend surfaces
systematic approach to this work in future would be a full
for ore-evaluation. J S Afr Inst Mining Metall1966;66:13–38.
mixed model with universal kriging to take account of spatial
22Geostatistical Environmental Assessment Software. GEO-EAS 1.2.1. Las
pattern.
Vegas, NV: US Environmental Protection Agency, 1991.
23Altman DG. Practical Statistics for Medical Research. London: Chapman &
Hall, 1991.
24Doumbo O, Ouattara NI, Koita O et al. Approche eco-geographique
References
du paludisme en milieu urbain: ville de Bamako au Mali. Ecol Hum
1Snow RW, Craig MH, Deichmann U, Le Sueur D. A continental risk 1989;8:3–15.
map for malaria mortality among African children. Parasitol Today 25Cressie NAC. Statistics for Spatial Data. New York: John Wiley & Sons,
1999 (In Press). Inc., 1991. Section 3.2.2.