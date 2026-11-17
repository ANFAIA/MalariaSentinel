# Entomological baseline data collection and power analyses in preparation of a mosquito swarm-killing intervention in south-western Burkina Faso

**Authors:** Niang A, Sawadogo SP, Millogo AA, Akpodiete NO, Dabiré RK, Tripet F, Diabaté A
**Journal:** Malaria Journal | **Year:** 2021 (20:346) | **DOI:** 10.1186/s12936-021-03877-x
**File:** papers/anopheles-dynamics/niang-2021-swarm-killing-baseline-burkina-faso.md

---

## Abstract (summary)

Baseline entomological survey and **statistical power analysis** for the swarm-killing
intervention trial run in 10 villages of western Burkina Faso (two areas of five
villages, humid savannah). It is the quantitative description of **how many swarms
exist per village, how big they are, where the markers are, and how much insecticide a
marker-based intervention needs** — i.e. the field statistics that any Centinela
male/swarm module must be dimensioned against.

## Key Results (as used by the model)

- **Swarm abundance per village:** mean **35 swarms per village**, range **25–70**
  (one-way ANOVA, P = 0.25). The 35 swarms were typically distributed over only
  **10–15 compounds**.
- **Swarm size:** **5 to 150 mosquitoes per swarm**, mean **50**, varying
  significantly between villages (ANOVA, P < 0.05).
- **Swarm height:** mean **2 m** above ground, varying significantly between villages
  (P < 0.05) — consistent with the **2.87 ± 0.20 m** of
  `ouedraogo-2025-coluzzii-swarm-dynamics-mating-efficiency-burkina-faso.md`.
- **Markers:** swarms were observed above waste, manure heaps, wood piles, wells,
  walls, grass, toilets, and above bare ground; the distribution of potential markers
  and of observed swarms shows that **swarms cluster across space**, which is what
  makes the intervention feasible.
- **Power analysis:** the high mean number of swarms collected (n = 35) provided
  statistical power equivalent to **≥ 0.8** even assuming a low intervention impact
  (20 %); to detect a **70 % population reduction or higher** the sampling effort
  would need to be increased.
- **Insecticide load:** because the mean swarm size is only ~50 mosquitoes, "it was not
  necessary to use a high quantity of insecticide to kill mosquitoes and to stop
  mating"; mean swarm height 2 m means swarms can be sprayed with **hand sprayers**.
- **Baseline female state:** parity rate was **very high** and the **insemination rate
  was high** at all sites, and did not differ between villages — i.e. in the baseline
  population a large fraction of females are already inseminated.

## Relevance to MalariaSentinel (Centinela)

Evidence tier **[P]** (*A. gambiae* s.l., western Burkina Faso; swarm markers and
swarms are not species-diagnostic in the survey).

This extract supplies the **dimensional constraints** for the Centinela's swarm layer:

1. **Scale:** 25–70 swarms per village, 10–15 compounds, swarms 5–150 mosquitoes
   (mean 50). For a 1 km-cell grid, this is the **magnitude of the male population
   the swarm layer must account for**: a village of a few km² with tens of swarms of
   ~50 males is a **few thousand males**, not a per-cell continuum.
2. **The "swarm marker density" free number has an empirical bracket**: ~**35 swarms
   per village** and ~**50 males per swarm** are the published values; the draft should
   calibrate against these rather than leave the number free.
3. **The intervention is hand-sprayer scale at 2 m height** — which means the male
   layer must expose the *height* of the swarm (2–2.9 m) as a modellable property if
   the Centinela is ever to represent swarm-targeting.
4. **The high baseline insemination rate** is the counterfactual the D5 formula must
   reproduce: a model that lets too many females go uninseminated will not match the
   observed baseline, and the field data give a check (insemination rate high, parity
   rate high) independent of any transmission output.

**Caveats:** species not resolved per swarm; the insemination rate was measured once
per village (no power analysis for it); swarm counts are observer-effort dependent;
the power analysis concerns the trial, not the model; *A. gambiae* s.l.

## License

CC BY 4.0 (© 2021 Niang et al; Malaria Journal, BMC open access).
Open-access copy: https://pmc.ncbi.nlm.nih.gov/articles/PMC8381508/
