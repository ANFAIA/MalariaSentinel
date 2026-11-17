# Audit of the numeric claims in the Gemini synthesis "Host detection at distance and directional movement modelling in *Anopheles coluzzii*"

**Audit of:** `papers/anopheles-dynamics/synthesis-gemini-2026-host-seeking-navigation-coluzzii.md`
(original at `.cache/investigacion-tmp.md`)
**Date of audit:** 2026-11-16 | **File:** papers/anopheles-dynamics/audit-gemini-synthesis-host-seeking-numeric-claims.md

Evidence tiers used throughout: **[M]** measured in *Anopheles coluzzii* ·
**[P]** measured in a close relative or genus proxy and transferred ·
**[EP]** engineering prior / no published value · **[NO-VERIFICADO]** could not
be confirmed from a primary source.

---

## A. Detection ranges (Q1)

| # | Synthesis claim | Verdict | Correct value / source |
|---|---|---|---|
| A1 | Olfactory orientation downwind up to **~30 m in the open field** | **VERIFIED** | Lorenz et al. 2013 Exp. 2 (*A. arabiensis*, open field, Ifakara): whole human odour attracted at 30 m (57 % vs 51 % control); **no effect beyond 30 m**. [P] |
| A2 | Olfactory orientation up to **50–70 m in semi-field** | **VERIFIED** | Lorenz et al. 2013 Exp. 1 (*A. gambiae* s.s., SFT): **blend+CO2 attracted at 70 m** (51 % vs 31 %); **CO2 alone attracted at 50 m** (65 % vs 36 %). [P] |
| A3 | Long-distance phase "**20–70 m**" | **VERIFIED** (as the tested grid) | Lorenz 2013 SFT distances were 20/50/70/100 m. [P] |
| A4 | Flight **activation up to 100 m** | **VERIFIED, exact** | Lorenz 2013: at 100 m CO2 activated 53 % (106/199) vs 39 % (80/203) control; **no directional attraction at 100 m**. [P] |
| A5 | Synthetic blend "attracted **20 % more** than control **up to 70 m**" | **VERIFIED but mis-scoped** | The "20 % more" wording is the *abstract*'s summary of the 20 m result ("All three stimuli were more than 20 % more attractive than the control at 20 metres"). At 70 m **only the blend** still attracted. Also: **whole human odour was NOT attracted at 50 m** (activated only) — the synthesis does not say this. Lorenz 2013. [P] |
| A6 | CO2 alone "significant attraction up to 50 m (65 % vs 36 %)" | **VERIFIED, exact** | Lorenz 2013. [P] |
| A7 | Field: "6–18 % more globally, 57 % vs 51 % at 30 m" | **VERIFIED** | Lorenz 2013 abstract (6–18 %) and Results (57 % vs 51 %). Note the 30 m difference is **6 percentage points**. [P] |
| A8 | Field: "no directional response to CO2 alone; nothing beyond 30 m" | **VERIFIED** | Lorenz 2013 Exp. 2. [P] |
| A9 | Visual response: "dark target 9.8 % clean air → 43.4 % with human odour, at ≤1.5 m, *A. coluzzii*, starlight" | **VERIFIED except the distance** | Hawkes & Gibson 2016: 9.8 % → 43.4 % (black tile), 6.8 % → 24.1 % (clear tile); **odour-gating confirmed** (clean-air black vs clear P = 0.721). **CORRECTION: the "≤1.5 m" is the arena/host-proximity envelope, not a measured visual detection radius** — the tile stood ~55 cm downwind of the host, the 3-D capture volume extended ~1 m from the host, and the responder criterion was coming within **0–15 cm** of the tile (mean turn distance **5.4 ± 0.85 cm**). [M] |
| A10 | Deceleration 40→30 cm/s in the 0.1 s before closest approach; ~80 cm/s² to 46 cm/s in 0.1 s; angular acceleration 12 500 °/s² | **VERIFIED, exact** | Hawkes & Gibson 2016. [M] |
| A11 | Clear tile 24.1 % vs 6.8 %; mean 4.5 ± 1.13 cm (P = 0.5 vs black) | **VERIFIED, exact** | Hawkes & Gibson 2016. [M] |
| A12 | Large target 80 % vs small 20 % of landings; density 1.0 vs 0.3 per 100 cm²; totals 4.7 ± 0.5 vs 2.5 ± 0.4 | **VERIFIED, exact** | Carnaghi et al. 2023 (*iScience*): 80.0 ± 4.9 % vs 20.0 ± 4.9 %, Wilcoxon W = 0, p = 0.002. [M] |
| A13 | Thermal target must cover **≥ 50 %** of the target surface for landing | **PARTIALLY CORRECTED — not a published rule** | Carnaghi et al. 2023: "landing is **directly proportional to the area of the thermal signature**"; the **half-heated** target matched the fully-heated positive control, while ¼- and ⅛-heated were significantly lower (fully/half ≈ **2×** the efficiency of ¼/⅛, ≈ **2.5×** the unheated control). There is **no hard 50 % threshold statement**; there is a **cluster break between ½ and ¼**. [M] |
| A14 | Thermal/landing range "< 0.15–0.30 m" | **VERIFIED (proxy)** | Spitzen et al. 2013 (*A. gambiae* s.s.): odour alone slows flight within **30 cm**; odour+heat keeps speed to within **15 cm**; max angular velocity **< 15 cm**. [P] |
| A15 | Thermal IR detection at ~0.70 m, demonstrated **only in *Ae. aegypti***; no *Anopheles* behavioural demonstration | **NOT VERIFIED** | The cited primary paper (PMC11410652) was **not read** in this pass. [NO-VERIFICADO] |
| A16 | *An. gambiae* expresses antennal TRPA1 | **NOT VERIFIED** | Cited primary (PMC13155204) not read. [NO-VERIFICADO] |
| A17 | **Is there a host-detection range measured in *A. coluzzii* itself?** | **NO — none found** | The only *A. coluzzii* range-like quantities are (a) the **eye-model visual resolution distances** of Carnaghi et al. 2023 (**~25–39 cm** horizontal, **~36–72 cm** vertical) — a *model* from published ommatidial optics, and (b) the ~1 m host-proximity envelope of Hawkes & Gibson 2016. **No *A. coluzzii* experiment measures a CO2/odour detection distance.** The 30/50/70/100 m numbers are all from *A. gambiae* s.s. (SFT) and *A. arabiensis* (field). **[P] for the config value; [M]-model for the eye-model alternative.** |

## B. Navigation mechanism (Q2)

| # | Synthesis claim | Verdict | Correct value / source |
|---|---|---|---|
| B1 | Plume is intermittent/filamentary beyond ~1 m; a continuous gradient cannot be followed | **VERIFIED** | Hawkes & Gibson 2016: "broken-up packets of host odour that might be encountered **> 1 m downwind** of the host" (citing Murlis & Jones 1981). *Murlis & Jones 1981 itself was not read* → [P], primary [NO-VERIFICADO]. Dekker & Cardé 2011: a **broad filamentous** plume *lowered* activation and source finding vs a homogeneous plume. [P] |
| B2 | Casting latency **~2 s** after losing the plume | **NOT VERIFIED — no primary source** | The cited paper is Dekker & Cardé 2011 (***Aedes aegypti***), whose **abstract** gives a **~0.03 s** CO2 encounter and describes counterturning, but **no 2 s latency**; the full text is behind HTTP 403 with no repository copy. The only accessible latencies are **300 ms** upwind re-orientation on plume entry / 300 ms cast on exit (Dekker et al. 2005, quoted in Hawkes 2013 PhD thesis) — also *Aedes*. **Treat as [EP].** |
| B3 | Optomotor upwind anemotaxis is the long-range mechanism | **VERIFIED (named mechanism)** | Hawkes & Gibson 2016: "odour-mediated **opto-motor guided positive anemo-taxis**, the mechanism by which mosquitoes fly toward a host from a distance". Hawkes 2013 thesis: "mosquitoes … infer wind direction from the optical flow of ground features". Carnaghi 2023 places IR tiles on the floor explicitly "to allow **optomotor navigation**". [P] |
| B4 | Successful landers spend **61.4 %** of time outside the plume (30.5 % inside, 8.1 % transition); landers away from the target 88.9 % | **VERIFIED, exact** | Spitzen et al. 2013 Table 2 (odour+heat): on source n = 16 → 30.5 ± 3.5 / 8.1 ± 0.7 / **61.4 ± 3.9 %**; elsewhere n = 19 → 7.3 ± 2.9 / 3.8 ± 1.0 / **88.9 ± 3.8 %**. [P] |
| B5 | Inside the plume the mosquito makes upwind progress; outside it there is no directional bias (= casting) | **VERIFIED, exact** | Spitzen et al. 2013: upwind progress inside plume Wilcoxon Z = −6.921, P < 0.001; outside plume Z = −0.669, P = 0.504. [P] |
| B6 | "If ambient wind exceeds the mosquito's own airspeed, net upwind progress is blocked" | **PHYSICALLY TRUE but the number is not published** | Cummins et al. 2012 quote "a **typical mosquito flight speed is 1 m s⁻¹**" and that "wind speeds as low as **0.8 m s⁻¹** … drastically reduce the number of mosquito host-seeking flights, but no reduction … for speeds as high as 3–8 m s⁻¹". The synthesis's **"~0.30–0.45 m s⁻¹ airspeed"** is a conflation of the *A. coluzzii* **ground** speeds in a 0.1 m s⁻¹ laminar tunnel (0.225–0.451 m s⁻¹) with an airspeed. **Use airspeed ≈ ground speed + wind component; do not hard-code 0.30–0.45 m s⁻¹ as an airspeed.** [EP as used] |
| B7 | "If ambient wind exceeds … this matches the highest recorded aerial density when surface winds are weak" | **NOT VERIFIED** | No such measurement exists in Hawkes & Gibson 2016. The thesis (Hawkes 2013) says the opposite mechanism: "mosquitoes tend to fly **within the atmospheric boundary layer** and **fly faster than the wind speed**" — i.e. they are in the slow air near the ground, which is *why* they can progress upwind. [NO-VERIFICADO] |
| B8 | The hybrid agent architecture (random walk / casting outside the plume; upwind anemotaxis 70 m→1.5 m; visual vector ≤1.5 m; landing <0.15–0.30 m) | **NOT A PUBLISHED ARCHITECTURE — it is the synthesis's own design** | No primary source implements it. The pieces come from three different papers (Lorenz 2013 for the ranges, Hawkes & Gibson 2016 for the visual gating, Spitzen 2013 for the terminal zone), and the threshold-based *state machine* idea comes from Cummins et al. 2012 — which is a **generic mosquito modelled for *Culex quinquefasciatus* feeding on roosting birds**, not *Anopheles* and not *Aedes*. |
| B9 | "2012 spatial ABM of host-seeking with gradient thresholds 40 ppm/m and 7900 ppm/m and a 0.3 m/s flight speed — is it Aedes or Anopheles?" | **CORRECTED** | It is Cummins et al. 2012, *PLoS Comput Biol* 8:e1002500 — **neither**: a **generic mosquito** ("such as *Culex quinquefasciatus* feeding on roosting birds"). Gradient thresholds **40 ppm m⁻¹** and **7900 ppm m⁻¹** are **VERIFIED exactly** (also sensing threshold 40 ppm, saturation 4000 ppm; critical host-contact radius 0.5 m; crosswind segment 0.5–0.9 s; domain 10 m; wind 0.2 m s⁻¹ + 0.15 m s⁻¹ stochastic). **The "0.3 m s⁻¹ constant flight speed" does not exist**: the model uses **0.4 m s⁻¹ minimum / 1.5 m s⁻¹ maximum** with orthokinesis; **0.3 m is the host spacing (1 ft grid)**. |
| B10 | Odour field geometry: ~60 cm wide at the base, ~20 cm at head height, respiratory CO2 plume at 30–35 cm | **VERIFIED, exact** | Hawkes & Gibson 2016 methods: host odour "~60 cm wide at floor level to ~20 cm wide at the volunteer's head"; breath+CO2 plume "mean height of ~30 cm and ~30–50 cm in diameter"; mouth and artificial CO2 source at ~35 cm. [M] |
| B11 | "1 400–2 000 ppm at 50 cm downwind" | **PARTIALLY CORRECTED** | Hawkes & Gibson 2016 Fig. 2b caption: highest concentrations **1 400–2 000 ppm** at ~30 cm height ~50 cm downwind. But the **measured mean at the plume centre was 1 060 ± 30 ppm** (range 791–3 462 ppm) and the **background was 460 ± 5 ppm**. The synthesis quotes only the figure's maximum. [M] |
| B12 | "CO2 supplement at 4.8 % and 5 l/min" | **VERIFIED, exact** | Hawkes & Gibson 2016: "additional humidified CO2 roughly equivalent in concentration to a second person (4.8 %) … at a rate of 5 l min⁻¹". [M] |

## C. Flight kinematics for *A. coluzzii* (Q3)

| # | Synthesis claim | Verdict | Correct value / source |
|---|---|---|---|
| C1 | Smooth flight 45.1 ± 1.63 cm/s, angular velocity 268.5 ± 33.03 °/s | **VERIFIED, exact** | Hawkes & Gibson 2016. [M] |
| C2 | Tortuous 29.0 ± 2.57 cm/s, 497.8 ± 52.22 °/s | **VERIFIED, exact** | Hawkes & Gibson 2016. [M] |
| C3 | Dipping: "the lowest of the three regimes (no figure given in the summary)" | **CORRECTED — the figure exists** | **22.5 ± 1.14 cm s⁻¹**, angular velocity **531.9 ± 25.71 ° s⁻¹** (turning almost exclusively vertical), tortuosity 0.8 ± 0.02. Hawkes & Gibson 2016. [M] |
| C4 | Flight height 11–14 cm mean; dipping below 3.5 cm | **VERIFIED** | Smooth 11.8 ± 0.22 → 13.0 ± 0.29 cm; tortuous 7.5 ± 0.20 → 13.6 ± 0.13 cm; dipping 3.2 ± 0.15 → 3.4 ± 0.16 cm, **never above 3.5 cm**. [M] |
| C5 | Dipping geometry: tortuosity 0.8 ± 0.02; descent 26.0 ± 2.03°; upward turn 70.5 ± 2.48°; initial ascent 50.7 ± 2.71° for 0.1 s; exit 26.4 ± 2.75°; duration 1.3 ± 0.12 → 1.9 ± 0.22 s | **VERIFIED, exact** (all seven values) | Hawkes & Gibson 2016. [M] |
| C6 | "*An. gambiae* s.s. 22.7–27.2 cm/s at 20 cm/s wind" | **TYPO CORRECTED** | Spitzen et al. 2013: control **22.5 ± 1.29 cm s⁻¹**, odour+heat **27.2 ± 1.2 cm s⁻¹** (pooled upwind 24.5 ± 0.6). The synthesis's "22,7" is a misreading of "22.5". [P] |
| C7 | "*An. gambiae* s.s. upwind angular velocity 553.0 ± 27.8 °/s vs 465.9 ± 31.3 °/s control" | **VERIFIED values, with a caveat** | Spitzen et al. 2013 Table 1 (upwind flight). The paper states the upwind angular velocity was **not significantly different between treatments** (GLM P = 0.057); the 553 vs 466 gap is not a demonstrated treatment effect. [P] |
| C8 | "*An. gambiae* s.s. flight duration 67.3 ± 8.9 s (odour+heat) vs 15.2 ± 9.8 s (control) and 18.8 ± 8.8 s (heat alone)" | **VERIFIED, exact** | Spitzen et al. 2013. [P] |
| C9 | "airspeed ~0.30–0.45 m/s" for the model | **CORRECTED (unit error)** | The *A. coluzzii* measurements are **GROUND speeds in a 0.1 m s⁻¹ laminar tunnel** (0.225–0.451 m s⁻¹). Airspeed = ground speed + wind component (for an upwind track, airspeed ≈ ground + 0.1 m s⁻¹). A second, independent *A. coluzzii* measurement — Cribellier et al. 2018, in a real odour+CO2 field around a trap — gives **ground speeds up to 0.5 m s⁻¹**, with a **speed minimum at 10–20 cm** from the source. **Recommend 0.30–0.50 m s⁻¹ ground for host-seeking females, with the wind vector added explicitly.** [M] |
| C10 | Compatibility with the repo's Vielma et al. 2026 swarm speeds (males, 0.66–0.87 m s⁻¹) | **NOT CONTRADICTORY — different quantity and different behaviour** | Vielma measures **male swarming** at a swarm marker (photonic fence), Burkina Faso. Hawkes & Gibson measure **female host-seeking** in a wind tunnel. **Use Vielma only for swarm/male behaviour; use Hawkes & Gibson (+ Cribellier) for female host-seeking.** Note the male swarm speed is 1.5–3× the female host-seeking ground speed, which is expected for a different task and a different flow field (no wind load in the swarm case, vs 0.1–0.2 m s⁻¹ in the tunnel). Neither is a *dispersal* speed. |

## D. CO2 sensing by *A. coluzzii* (Q4)

| # | Synthesis claim | Verdict | Correct value / source |
|---|---|---|---|
| D1 | Maxillary-palp neuron threshold **≤ 350–400 ppm** | **VERIFIED, exact** | Majeed, Hill, Dekker & Ignell 2017, *R. Soc. Open Sci.* 4:170189: "the dynamic range of their CO2-sensitive ORNs is wide, with a **threshold at or below ambient concentration (350–400 ppm)**, and the neurons **do not reach their maximal response at the highest dose tested (4800 ppm)**". *An. coluzzii* had the **lowest** threshold of the three species. [M] |
| D2 | Tracks pulsed CO2 from **600 to 4 800 ppm without saturation** | **VERIFIED** | Majeed et al. 2017: pulses 600/1200/2400/4800 ppm; at 600 and 1200 ppm **all three** species tracked; at higher concentrations only *Ae. aegypti* and *An. coluzzii* tracked (*Cx. quinquefasciatus* adapted). [M] |
| D3 | "*Cx. quinquefasciatus* saturates above **1 200 ppm**" | **CORRECTED** | 1200 ppm is where *Cx. quinquefasciatus* still tracked; the paper attributes its saturation/adaptation to **high (≥ 2400 ppm)** concentrations. [M] |
| D4 | At 4 800 ppm *A. coluzzii* takes longer than *Ae. aegypti* to reach the tube midpoint, **p = 0.0248** | **VERIFIED, exact** | Majeed et al. 2017: "4800 ppm: t-ratio −3.16, **p = 0.0248**". [M] |
| D5 | 87–100 % contact with the source | **VERIFIED** | Majeed et al. 2017: 93–100 % reached halfway, **87–100 %** made source contact (both *Ae. aegypti* and *An. coluzzii*, all concentrations). [M] |
| D6 | Background CO2 in the tunnel | **VERIFIED (added)** | Majeed et al. 2017: **385.4 ± 6.28 ppm**; Hawkes & Gibson 2016: **460 ± 5 ppm** (439–511). Both ≈ the 350–400 ppm threshold, i.e. *A. coluzzii* is at threshold in ambient air. [M] |

## E. Out-of-scope claims (not checked in this pass)

| # | Claim | Verdict |
|---|---|---|
| E1 | Local dispersal 112 m (females) / 136 m (all) / max 623 m; 70 % recaptured elsewhere; r² = 94 % (Thierola, Mali) | **NOT VERIFIED** — cited source not read. The repo already has `diallo-2026-continuous-mrr-mali.md`; cross-check before use. [NO-VERIFICADO] |
| E2 | Huestis et al. 2019 windborne migration numbers (40–290 m altitude, 617 nights, 235 anophelines, ~6 million *A. coluzzii*/yr, 87.5 % gravid, night winds 5.1 m s⁻¹ (10–90 %: 2.4–8.0), 2 h / 9 h flights → 30 / 120 km mean, 70–295 km max) | **NOT RE-VERIFIED in this pass** — the repo already has `huestis-2019-windborne-migration-sahel.md`; that extract covers the wind-advection channel, not the per-night numbers above. [NO-VERIFICADO] |
| E3 | Effective dispersal ~3 km/generation (CNN), up to ~7 km (spatial autocorrelation), São Tomé & Príncipe | **NOT VERIFIED** — source not read. [NO-VERIFICADO] |
| E4 | HBI values (80 % continental, 4 % São Tomé n = 1227, 79 % Príncipe n = 17), biting-time profiles, Burkina Faso plasticity (21:00–04:00) | **NOT VERIFIED** in this pass — outside the movement-law scope. [NO-VERIFICADO] |
| E5 | CO2 traps capturing 9 % of *An. gambiae* s.l. vs 27 % → 69 % for *A. funestus* at 1 500 ml/min (Tanzania) | **NOT VERIFIED** — source not read. [NO-VERIFICADO] |
| E6 | "*Ae. aegypti* ommatidial diameter 17.2 µm, interommatidial angle 6.2°, resolvable angle 12.3°, resolves a person at ~5 m" | **NOT VERIFIED as stated** — and **irrelevant**: the *A. coluzzii* eye model of Carnaghi et al. 2023 uses **interommatidial angle 8°, receptive field 40°**, giving **25–72 cm** resolution distances. Use the latter. [NO-VERIFICADO] for the *Ae. aegypti* numbers; [M]-model for the *A. coluzzii* ones. |

---

## Summary of the corrections that matter for the plan

1. **The 30 m / 50 m / 70 m / 100 m figures are all proxy values from
   *A. gambiae* s.s. (semi-field) and *A. arabiensis* (open field). There is no
   *A. coluzzii* measurement of a host-detection range.** If the per-species
   `perception_radius` must be a coluzzii value, the only coluzzii-specific
   range-like numbers available are the **eye-model visual resolution
   distances (25–72 cm)** and the **~1 m host-proximity envelope** of
   Hawkes & Gibson 2016.
2. **"≤ 1.5 m" is not a measured visual detection distance.** The
   odour-gated visual response was measured at ≤ ~1 m from the host with a
   responder criterion of 0–15 cm to the target.
3. **The "≥ 50 % thermal area" rule is not in the source.** The source states
   proportionality plus a break between ½ and ¼.
4. **The "~2 s casting latency" has no primary source** and must be flagged
   [EP]; the only accessible latencies are 300 ms (*Aedes*).
5. **"0.30–0.45 m/s airspeed" is a ground-speed/air-speed conflation.**
   Use ground speed + explicit wind vector; corroborate with Cribellier 2018
   (up to 0.5 m s⁻¹).
6. **Cummins et al. 2012 is neither *Anopheles* nor *Aedes*** (generic
   mosquito modelled for *Culex*), and has **no 0.3 m s⁻¹ constant speed**
   (0.4–1.5 m s⁻¹, orthokinetic).
7. **The male swarm speeds (Vielma 2026, 0.66–0.87 m s⁻¹) and the female
   host-seeking speeds (0.225–0.45 m s⁻¹) are not in conflict** — different
   behaviour, sex, and flow field. Use each only for its own behaviour.

---

## F. Addendum (2026-11): latencies and temporal resolution

| # | Claim / question | Verdict |
|---|---|---|
| F1 | "Casting latency **~2 s**" | **CONFIRMED UNSOURCED.** An exhaustive search of the primary literature (Europe PMC, full texts) for an *Anopheles* olfactory-memory window or cast duration returned **no primary measurement in *Anopheles***. The nearest numbers remain: **300 ms** surge/cast on plume entry/exit (*Aedes*, Dekker et al. 2005, quoted in Hawkes 2013), **~0.03 s** CO2 encounter (*Aedes*, Dekker & Cardé 2011 abstract), and — new, *A. coluzzii* — **Majeed et al. 2017**: the CO₂ ORN tracks **1 s pulses separated by 1 s gaps**, and pulsed CO₂ **shortens the time to activation and to the tube midpoint** (absolute latencies only in Fig. 3a → **[NR]** in seconds). Keep the 2 s value **[EP]** or drop it. |
| F2 | Micro-simulator tick of **1 s** | **CONTRADICTED.** (a) Every primary *Anopheles* host-seeking trajectory study resolves behaviour at **25–90 Hz**: Hawkes & Gibson 2016 **50 Hz** (displacement per 20 ms), Spitzen et al. 2013 **25 fps / 0.04 s**, Cribellier et al. 2018 **90 fps**, Hinze et al. 2021 **60 fps**, Batista et al. 2019 **68 fps**. (b) The fastest documented manoeuvre is Hawkes & Gibson's **0.08 s** turning event (angular acceleration between 0.04 s before and after closest approach); the dipping cycle is **0.43–0.51 s**. (c) Geometry: at **1 s** the step is **22–45 cm**, i.e. **larger than the whole 10–20 cm terminal radius**, so the host can never be "reached" — the terminal approach is unresolvable. The coarsest defensible tick is **0.1 s**, recommended **0.05 s**. |
| F3 | Reaction time to a **wind gust / plume filament** | **NO PUBLISHED MEASUREMENT FOUND.** The wind literature in the repo is about *rates* (wind speed thresholds suppressing host-seeking; anemotaxis direction; passive windborne dispersal), not latencies. Consequence: the integrator does **not** need sub-second resolution to capture a gust response; the wind field may be treated as slowly varying at the mosquito's scale. |
| F4 | Published mosquito **agent-based model** with an integration step | **FOUND (precedent).** Cribellier, Poda, Dabiré, Diabaté, Roux & Muijres 2026 (*PLoS Comput. Biol.* 21:e1014685) build an *A. coluzzii* swarm IBM that "**simulations were run at a temporal resolution of 50 Hz, which is the same as the empirical video frame rate**", with **Δt = 0.02 s**, and whose dynamics are **event-triggered** (straight ballistic segment at 0.5 m s⁻¹ + discrete saccade event, saccade = angular-speed prominence ≥ 300 ° s⁻¹). New extract: `cribellier-2026-coluzzii-swarm-behavioural-rules-agent-based-model.md`. |
| F5 | Published **Anopheles** landing criterion that does not depend on geometry | **FOUND.** Hinze et al. 2021 (*Front. Behav. Neurosci.* 15:643693) declare landing as "the mean speed over 60 frames below **50 mm s⁻¹ for three consecutive seconds**" (60 fps ⇒ 1 s window), i.e. a **speed-and-persistence** rule rather than a radius rule. New extract: `hinze-2021-gambiae-3d-host-seeking-wind-tunnel.md`. |
