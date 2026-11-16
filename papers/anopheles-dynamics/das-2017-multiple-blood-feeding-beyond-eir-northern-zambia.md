# Beyond the entomological inoculation rate: characterizing multiple blood feeding behavior and *Plasmodium falciparum* multiplicity of infection in *Anopheles* mosquitoes in northern Zambia

**Authors:** Subhash Das, M. Muleba, James C. Stevenson, John C. Pringle, Don E. Norris
**Journal:** Parasites & Vectors | **Year:** 2017 | **DOI:** 10.1186/s13071-017-1993-z
**File:** papers/anopheles-dynamics/das-2017-multiple-blood-feeding-beyond-eir-northern-zambia.md

---

## Abstract (summary)

Field study in Nchelenge District, northern Zambia (2013 wet season). *Anopheles* were
collected by light trap and pyrethroid spray catch and tested for blood-meal host,
*P. falciparum* sporozoites (CSP-ELISA) and parasite multiplicity of infection (MOI), with
microsatellite analysis used to detect multiple blood feeding (MBF). The paper quantifies
the two quantities that the classic EIR ignores: meals per cycle and parasites per
mosquito.

## Key Results (as used by the model)

- "The dominant malaria vectors collected in Nchelenge were ***Anopheles funestus* (sensu
  stricto) and *An. gambiae* (s.s.)**."
- "…and took **multiple human blood meals at high rates, 23.2 % and 25.7 % respectively**"
  (*An. funestus* s.s. = 23.2 %, *An. gambiae* s.s. = 25.7 %).
  → the highest field MBF rates reported for sub-Saharan Africa; both species are in the
  engine.
- "A basic assumption of the HBR component of the EIR is that **a mosquito bites (or
  probes) once and takes a single blood meal per gonotrophic cycle**." → the assumption
  the redesign removes.
- "However, if mosquitoes exhibit multiple blood feeding (MBF) behavior, taking more than
  one blood meal per gonotrophic cycle, then the **HBR increases and subsequently the
  unadjusted EIR is underestimated**."
- "…*An. arabiensis* MBF rate **decreased from 18.9 % pre-ITN distribution to 9.1 %
  post-distribution**, which was attributed to heterogeneity in biting behavior."
  → the multi-meal rate is *intervention-dependent*: insecticide-treated nets reduce the
  number of completed (and of interrupted) meals, so `meals_per_cycle_mean` should be
  treated as a scenario-dependent quantity, not a constant.
- "The overall *P. falciparum* MOI was **6.4** in infected vectors" — a mosquito can carry
  many parasite genotypes, i.e. it has fed on several infectious hosts.

## Relevance to MalariaSentinel (Centinela)

Best available field anchor for `meals_per_cycle_mean` in the two species the engine
models (*gambiae* s.s. ≈ *coluzzii*, and *funestus*), and the explicit statement of the
EIR bias that a single-meal-per-cycle engine produces. Also documents that the rate is
sensitive to vector control, so the model must be able to run with and without nets.

Caveats: northern Zambia (not Ghana); *funestus* is a secondary species for the engine
(the active row is `coluzzii`); MBF is detected only for *human* meals via
microsatellites, so multi-host meals involving livestock are invisible to this estimator.

## License

CC-BY 4.0 (Parasites & Vectors / BMC open access).
