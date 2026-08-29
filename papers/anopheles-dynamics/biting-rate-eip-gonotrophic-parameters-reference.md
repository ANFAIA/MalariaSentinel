# Biting rate (a), EIP, gonotrophic cycle and adult survival of *Anopheles gambiae* s.l. — Parameter reference note (web-sourced)

**Type:** Internal parameter reference note (no single-paper attribution; compiled from open-access sources)
**Compiled:** 2026-08-30 for MalariaSentinel / Centinela SDSS
**File:** papers/anopheles-dynamics/biting-rate-eip-gonotrophic-parameters-reference.md
**Sources:** Malaria Journal (Eckhoff 2011; Smith & McKenzie 2004; Ermert 2011; Bockarie 1995), PLoS ONE (Paaijmans 2013), PLoS Biology (Shapiro 2017), PLoS Medicine (Griffin 2010), Nature Communications (Müller et al. 2024), Parasites & Vectors (Ohm 2018), Proc R Soc B (Waite 2019), Water Resources Research (Bomblies 2008), BMC Infectious Diseases (Tchuinkam 2010), WHO/IRD field studies (Davidson & Draper 1953; Fontenille 1997; Noutcha 2009; Carnevale & Molinier 1982).

---

## 1. Biting rate a (bites per female per day)

**Definition convention:** a = inverse of the mean gonotrophic cycle length in days (Mordecai et al. 2013; Shapiro et al. 2017). With a 2.5–3 day cycle, a ≈ 0.33–0.40/day.

**Thermal performance curve (Brière, fit to *An. pseudopunctipennis* data of Lardeux et al. 2008; used by Mordecai 2013 and Paaijmans 2013):**

```
a(T) = 0.000203 · T · (T − 11.7) · sqrt(42.3 − T)   [bites/day]
```

| T (°C) | a (bites/female/day) |
|---|---|
| 22 | 0.21 |
| 25 | 0.28 |
| 27 | 0.33 |
| 30 | 0.39 |
| 34 | 0.44 (curve starts declining; Mordecai 2013: biting declines slightly above 30 °C) |

**Other values in use:**
- Smith & McKenzie 2004 (worked example, Malaria Journal 3:13): **a = 0.3/day** ("3 human bites every ten days"), with g = −ln p = 0.1/day.
- Carnevale & Molinier 1982 (Congo, Djoumouna): biting frequency L = **0.40** bites/parous female/day for *An. gambiae*; multiply by anthropophilic index for Macdonald's a.
- Centinela internal: cycle_duration_days = 2.65 → a ≈ 0.38/day (unconstrained; a on humans = a × HBI ≈ 0.34).

**Distinguish from man-biting rate (ma / HBR):** bites per HUMAN per night = a × m (mosquito density per human). Locality-specific, 0.5–100+; see §2.

## 2. Man-biting rate / HBR (bites per human per night, West African field data)

| Site | HBR (bites/human/night) | EIR | Source |
|---|---|---|---|
| Igbo-Ora, SW Nigeria (rural) | mean weekly 0.90 (2001), 1.6 (2002) | ~5/week; seasonal (6-mo) 129–131 | Noutcha & Anumdu 2009, J Vector Borne Dis |
| Ndiop, Senegal (Sahelian, seasonal) | peaks 11.3–12.5 (Sept); low off-season | annual 7–63 (year-dependent) | Fontenille et al. 1997, Trans R Soc Trop Med Hyg / IRD |
| Santchou lowland (750 m), Cameroon | *An. gambiae* 11.5; all spp. 14.9 | 90.5/year | Tchuinkam et al. 2010, BMC Infect Dis 10:119 |
| Bayama, Sierra Leone (high-rainfall forest) | very high (99.7% of 22,541 anophelines = *An. gambiae*) | **1,235** ibppy | Bockarie et al. 1995, Am J Trop Med Hyg 53:533 |

Typical modelling band: **5–30 bites/human/night during peak transmission season; <1 off-season in Sahelian sites**. Holoendemic forest sites reach 100+ (EIR 1000+).

## 3. Human blood index (HBI)

- **0.9–0.95+ for *An. gambiae* s.s.** — EMOD/Eckhoff 2011 uses **0.95** for *An. gambiae* s.s. and *An. funestus* (cites Gillies & De Meillon 1968).
- Field West Africa: 82–86% anthropophilic (Noutcha 2009, Nigeria); 74.2% (Fontenille 1997, Senegal — where *An. arabiensis* co-dominates at 74% HBI as well).
- Project-local: `papers/perplexity-investigations/Mosquitos de la Malaria…md` (line 64): HBI >0.95 for *An. gambiae* s.s.
- Davidson & Draper 1953 (Tanzania coast): "strongly anthropophilic", 48-h gonotrophic cycle confirmed.

**Model-plausible: HBI = 0.9 (default), 0.95 for pure *An. gambiae* s.s./coluzzii villages, lower (0.5–0.74) where *An. arabiensis* co-dominates or livestock present.**

## 4. Adult daily survival p and p^EIP

Local field estimates (see also `dispersal-kernel-calibration.md`, `costantini-1996…md`, `midega-2007…md`, `saarman-2019…md`, `diallo-2026…md`):

| Study | Site | p (daily) |
|---|---|---|
| Costantini 1996 | Burkina Faso savanna | 0.80–0.88 |
| Thomas 2013 | The Gambia | 0.80 |
| Saarman 2019 | Tanzania (self-marking) | 0.87 (CI 0.69–1.10) |
| Midega 2007 | Kenya coast | 0.83–0.95 |
| Diallo 2026 | Mali (corrected PDS) | 0.94 |
| Bockarie 1995 | Sierra Leone | 0.85 (survival per 3-d cycle 0.59) |
| Davidson & Draper 1953 | Tanzania coast | ~0.93 (7%/day natural mortality) |
| Depinay 2004 (model) | — | 0.911 |
| Ermert LMM2010 (review) | — | observed range 0.80–0.95 |
| Smith & McKenzie 2004 (example) | — | p = e^(−0.1) ≈ 0.905 (mean lifespan ~10 d) |
| Centinela | — | ADULT_DAILY_MORT_BASAL = 0.93 |

**p^EIP (probability of surviving sporogony):**
- p=0.905, n=10 d (Smith & McKenzie example) → p^n ≈ **0.37**
- p=0.93, n=10 → 0.48; p=0.87, n=10 → 0.25; p=0.85, n=12.3 (EIP@25 °C) → 0.135; p=0.94, n=10 → 0.54
- Typical band **0.10–0.55, central value ~0.3–0.4** with p≈0.9, n≈10 — matches classic expectation.

## 5. EIP (extrinsic incubation period, *P. falciparum*)

**Degree-day (Detinova/Moshkovsky/Nikolaev) model — canonical form:**

```
EIP(days) = 111 / (T − 16)   for T > 16 °C
```

(111 cumulative degree-days, lower threshold 16 °C. Source: Detinova 1962, WHO Monograph 47; re-derived in Ohm et al. 2018 Parasites & Vectors 11:187 and Waite et al. 2019 Proc R Soc B 286:20190275.)

**Variants:** several modelling studies assume an 18 °C threshold with the same 111 DD (EIP = 111/(T−18)): Bomblies' MIT thesis (2008) states 18 °C, while the corresponding WRR paper states 16 °C; Craig et al. 1999 and Martens et al. used 18 °C. Ohm 2018 documents the 16 °C threshold derives from Moshkovsky's regression; Waite 2019 finds the true requirement is nonlinear (fewer DD needed at 17–20 °C: 38–43 DD at 17 °C vs 111 predicted).

| T (°C) | EIP, Detinova 16 °C | EIP, 18 °C variant | Empirical (EIP50 unless noted) |
|---|---|---|---|
| 22 | 19.8 | 27.8 | 13 d (EIP90, Paaijmans 2013) |
| 25 | 12.3 | 15.9 | 10–12 d (project-local perplexity note); ~11 d (Shapiro 2017, *An. stephensi*) |
| 27 | 10.1 | 12.3 | ~9–10 d (Shapiro 2017); degree-day model "reasonable" 24–28 °C (Nature Comms 2024) |
| 28 | 9.25 | 11.1 | — |
| 30 | 7.9 | 9.25 | 7.6 d (EIP10, *An. gambiae*, Müller et al. 2024 Nature Comms 15:3216); ~7–8 d (Shapiro 2017) |
| 34 | 6.2 | 7.4 | 6.1 d (EIP10, Shapiro 2017) |
| 17 | 111 | 55.5 | 59 d (EIP50, *An. gambiae*; Müller 2024) — degree-day model overestimates at cold end |

Supporting data: Paaijmans et al. 2013 (PLoS ONE 8:e55777) reports EIP90 = 13, 11, 8 d at 22, 24, 26 °C. Shapiro et al. 2017 (PLoS Biology 15:e2003489) gives EIP10/50/90 distributions (21–34 °C). Müller et al. 2024 re-measured EIP in *An. gambiae* — degree-day model adequate for 24–28 °C, overestimates below 21 °C.

**Model-plausible: EIP = 10–12 d at 25 °C, 8–10 d at 27 °C, 7–8 d at 30 °C. Use Detinova 111/(T−16) for temperature-dependence; treat EIP as a distribution (EIP50) rather than fixed.**

## 6. Gonotrophic cycle duration

| Source | Value | Setting |
|---|---|---|
| Gillies 1953 / Davidson & Draper 1953 | **2 days (48 h)** | Tanzania coast, holoendemic |
| Tchuinkam 2010 | **2–3 d** lowland; 3–4 d at 1400 m; 6–7 d at 1965 m | Cameroon altitudinal transect |
| Bockarie 1995 | **3 d** | Sierra Leone |
| Eckhoff 2011 (EMOD) | **3 d** (range 2–4 d, citing Gillies & De Meillon 1968) | Model default |
| Project-local (perplexity note, line 51) | 2–4 d at ~28 °C, lengthens when cooler | — |
| Centinela internal | 2.65 d | cycle_duration_days |
| Mordecai 2013 | a = 1/GC; Brière thermal fit (see §1) | — |

**Model-plausible: 2.5–3 d at 25–30 °C (2 d possible at high T in classic East African data; 2.65 d Centinela default is within range).**

## 7. Parameter values USED by published ABMs / transmission models

| Model | a (biting) | p / lifespan | EIP | GC / feeds | HBI | Notes |
|---|---|---|---|---|---|---|
| **Smith & McKenzie 2004** (Malar J 3:13) — formal statics/dynamics review | 0.3/day (example) | g = 0.1/day (lifespan ~10 d, p ≈ 0.905) | n from sporozoite rate; classic 10–12 d | — | a from HBI via Eq. 5 | 7-parameter minimal set; b = c = 0.5, r = 0.01 |
| **Griffin 2010** (PLoS Med 7:e1000324) | from fitted seasonal EIR profiles | aggregated vectors, literature params | implicit (EIR forced) | seasonal driver fitted | used for vector infectivity | Fitted to 34 African sites incl. **Kassena-Nankana, Ghana** |
| **Eckhoff 2011 EMOD** (Malar J 10:303) | feeds every **3 d** (2–4 d) | Adult_Life_Expectancy **10 d**; Martens-form temp mortality ≈ .001·e^(T−32); max 14 feeds/field | Arrhenius fit a1=1.17e11, a2=8.4e3 ("traditional curve"); max 56 d at 18 °C | 3 d between feeds | **0.95** (*An. gambiae* s.s., *funestus*) | Tanzania site (−8.5, 36.5); 3 vector spp. |
| **Bomblies 2008 HYDREMATS** (WRR 44:W12445 + MIT thesis) | event-driven bites | Martens 1997 temp-dependent daily survivability; lethal > 40–41 °C | **111 degree-days above 16 °C** (Detinova; thesis text says 18 °C) | egg maturation via Depinay 2004 model | — | Niger Sahel (Banizoumbou, Zindarou); closest West African ABM analog |
| **Depinay 2004** (local file) | — | **0.911/day** non-ovipositing | — | thermal fit to Bayoh & Lindsay 2003 | — | First ABM of *An. gambiae* lifecycle |
| **LMM2010 Ermert 2011** (Malar J 10:35) | — | observed p_d 0.80–0.95 (review) | unchanged from LMM2004 (sporogonic GDD) | — | reassessed from literature; b = 0.30 | West Africa calibration (part 2: Bobo-Dioulasso, Burkina Faso) |

## 8. Recommended model-plausible values (Centinela, Ghana)

| Parameter | Value | Range | Primary sources |
|---|---|---|---|
| a (bites/female/day, on any host) | 0.30 (a(T) via Brière above) | 0.21–0.39 at 22–30 °C | Lardeux 2008 via Mordecai 2013/Paaijmans 2013; Smith & McKenzie 2004 |
| a_human = a × HBI | 0.27 (HBI 0.9) | 0.19–0.37 | Eckhoff 2011 (HBI 0.95); Noutcha 2009 |
| HBR (man-biting rate) | site-driven: 5–30/night peak season; <1 off-season | 0.5–100+ | Fontenille 1997; Tchuinkam 2010; Noutcha 2009; Bockarie 1995 |
| HBI | 0.9 | 0.74–0.95 (lower with *An. arabiensis*/livestock) | Eckhoff 2011; perplexity note line 64 |
| p (daily survival) | 0.90–0.93 | 0.80–0.95 | Costantini 1996; Diallo 2026 (Mali, 0.94); Midega 2007; LMM2010 review |
| Mean adult lifespan | ~10–14 d (1/(1−p)) | 4.5–20 d | Smith & McKenzie 2004; Eckhoff 2011 (10 d); Diallo 2026 |
| p^EIP | ~0.3–0.4 (p=0.905, n=10) | 0.10–0.55 | Smith & McKenzie 2004; derived |
| EIP (n) | 10–12 d @25 °C; 8–10 @27 °C; 7–8 @30 °C | 6.2 d @34 °C — ∞ @≤16 °C | Detinova 1962; Ohm 2018; Shapiro 2017; Müller 2024 |
| Gonotrophic cycle | 2.5–3 d (Centinela 2.65 d ✓) | 2–4 d field; up to 6–7 d at altitude | Gillies 1953; Bockarie 1995; Tchuinkam 2010; Eckhoff 2011 |

---

## References (web-sourced, in addition to papers already in this directory)

1. Smith DL, McKenzie FE (2004). Statics and dynamics of malaria infection in *Anopheles* mosquitoes. *Malaria Journal* 3:13. doi:10.1186/1475-2875-3-13
2. Eckhoff PA (2011). A malaria transmission-directed model of mosquito life cycle and ecology. *Malaria Journal* 10:303. doi:10.1186/1475-2875-10-303
3. Griffin JT, et al. (2010). Reducing *Plasmodium falciparum* malaria transmission in Africa. *PLoS Medicine* 7:e1000324. doi:10.1371/journal.pmed.1000324
4. Bomblies A, Duchemin JB, Eltahir EAB (2008). Hydrology of malaria: model development and application to a Sahelian village. *Water Resources Research* 44:W12445. doi:10.1029/2008WR006917 (+ Bomblies 2008 MIT thesis, hdl:1721.1/47729)
5. Ohm JR, et al. (2018). Rethinking the extrinsic incubation period of malaria parasites. *Parasites & Vectors* 11:187. doi:10.1186/s13071-018-2761-4
6. Waite JL, Suh E, Lynch PA, Thomas MB (2019). Exploring the lower thermal limits for development of the human malaria parasite, *P. falciparum*. *Proc R Soc B* 286:20190275. doi:10.1098/rsbl.2019.0275
7. Müller R, et al. (2024). Estimating the effects of temperature on transmission of the human malaria parasite, *P. falciparum*. *Nature Communications* 15. doi:10.1038/s41467-024-47265-w
8. Shapiro LLM, Whitehead SA, Thomas MB (2017). Quantifying the effects of temperature on mosquito and parasite traits that determine the transmission potential of human malaria. *PLoS Biology* 15:e2003489. doi:10.1371/journal.pbio.2003489
9. Paaijmans KP, Cator LJ, Thomas MB (2013). Temperature-dependent pre-bloodmeal period and temperature-driven asynchrony between parasite development and mosquito biting rate reduce malaria transmission intensity. *PLoS ONE* 8:e55777. doi:10.1371/journal.pone.0055777
10. Tchuinkam T, et al. (2010). Bionomics of anopheline species and malaria transmission dynamics along an altitudinal transect in Western Cameroon. *BMC Infectious Diseases* 10:119. doi:10.1186/1471-2334-10-119
11. Bockarie MJ, Service MW, Barnish G, Touré YT (1995). Vectorial capacity and entomological inoculation rates of *Anopheles gambiae* in a high rainfall forested area of southern Sierra Leone. *Am J Trop Med Hyg* 53:533. doi:10.4269/ajtmh.1995.53.533 (PMID 8533019)
12. Fontenille D, et al. (1997). Four years' entomological study of the transmission of seasonal malaria in Senegal (Ndiop). *Trans R Soc Trop Med Hyg* (IRD archive: horizon.documentation.ird.fr 010012524)
13. Noutcha AEG, Anumdu CI (2009). Entomological indices of *Anopheles gambiae* s.l. at Igbo-Ora, SW Nigeria. *J Vector Borne Dis* 46:213 (UI repository)
14. Davidson G, Draper CC (1953). Field studies of some basic factors concerned in malaria transmission. *Trans R Soc Trop Med Hyg* 47:522. doi:10.1016/s0035-9203(53)80005-2
15. Carnevale P, Molinier M (1982). The gonotrophic cycle and the daily rhythm of bites of *Anopheles gambiae* and *An. nili*. (PMID 6895549)
16. Ermert V, et al. (2011). Development of a new version of the Liverpool Malaria Model (LMM2010). *Malaria Journal* 10:35. doi:10.1186/1475-2875-10-35
17. Detinova TS (1962). Age-grouping methods in Diptera of medical importance. *WHO Monograph Series* 47:13–91.
