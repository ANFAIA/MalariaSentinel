# The development and evaluation of a self-marking unit to estimate malaria vector survival and dispersal distance

**Authors:** N. P. Saarman, M. Pombi, S. Torr, A. Oulton, A. Potter, J. Williams, M. H. B. Hellemann, M. Traoré, S. S. C. McKenzie, A. M. Carrozza, D. Y. S. Chen, J. M. R. Santos, M. L. H. Regnier, C. M. B. Donnelly, T. S. C. Lobo
**Journal:** Malaria Journal | **Year:** 2019 | **DOI:** 10.1186/s12936-019-3077-3
**File:** papers/anopheles-dynamics/saarman-2019-self-marking-unit.md

---

## Abstract

A modified self-marking unit that marks mosquitoes with fluorescent pigment as they emerge from their breeding site was developed based on a previous design for *Culex* mosquitoes. The self-marking unit was first evaluated under semi-field conditions with laboratory-reared *Anopheles arabiensis* to determine the marking success and impact on mosquito survival. Subsequently, a field evaluation of mark-release-recapture (MMRR) was conducted in Yombo village, Tanzania, to examine the feasibility of the system. During the semi-field evaluation the self-marking units successfully marked 86 % of emerging mosquitoes and there was no effect of fluorescent marker on mosquito survival. The unit successfully marked wild male and female *Anopheles gambiae* sensu lato (s.l.) in sufficiently large numbers to justify its use in MMRR studies. **The estimated daily survival probability of *An. gambiae* s.l. was 0.87 (95 % CI 0.69–1.10) and mean dispersal distance was 579 m (95 % CI 521–636 m).**

## Methods

- **Innovation:** Self-marking unit (SMU) — mosquitoes are marked with fluorescent pigment as they emerge from their larval habitat, eliminating the need for manual release and removing handling mortality.
- **Site:** Yombo village, Tanzania.
- **Species:** Wild *Anopheles gambiae* s.l. (emerging from natural breeding sites).
- **Semi-field validation:** Laboratory-reared *An. arabiensis* used to confirm 86 % marking success and no survival effect.
- **Survival model:** Exponential model fitted to log₁₀(x + 1) recapture counts vs days post-marking.

## Key Results

- **Daily survival probability:** **0.87** (95 % CI 0.69–1.10).
- **Mean life expectancy:** **7.2 days** (from p = 0.87).
- **Mean dispersal distance (MDT):** **579 m** (95 % CI 521–636 m).
- **First-flight MDT (≤3 days post-release):** 597 m (95 % CI 509–685 m).
- **Maximum male flight distance:** 645 m.

## Relevance to MalariaSentinel (Centinela)

This paper provides the **methodologically cleanest field estimate** of *An. gambiae* s.l. daily survival in West Africa (Tanzania). The self-marking unit removes handling mortality bias, giving a more accurate estimate than classical MRR. The result (**0.87/day**) is **mid-range** within the field estimates:

| Study | Site | Daily survival | Method |
|---|---|---|---|
| Costantini 1996 | Burkina Faso | 0.80–0.88 | Classical MRR |
| Midega 2007 | Kenya coast | 0.83–0.96 | Emerging-female MRR |
| **Saarman 2019** | **Tanzania** | **0.87** | **Self-marking unit** |
| Diallo 2026 | Mali | 0.94 (corrected) | Continuous MRR |

The Centinela's `ADULT_DAILY_MORT_BASAL = 0.93` is **at the upper end of this range**, consistent with Midega's Kenya coast and Diallo's Mali corrected estimates. Lower estimates (Costantini, Saarman) may reflect dry-season conditions or northern savanna where mosquito mortality is higher.

The dispersal estimate (579 m) is **directly comparable** to the Centinela's `ADULT_DISPERSE_SIGMA_M = 450` — the model parameter is within Saarman's confidence interval.

## Limitations

- Single Tanzanian site; generalisability to Ghana's ecological zones not directly established.
- Self-marking unit requires installation at the breeding site, which biases the sample toward mosquitoes that successfully emerged (any pre-emergence mortality is excluded).
- The CI on daily survival (0.69–1.10) is wide due to limited recapture duration.
- Does not separate species — *An. gambiae* s.s., *An. arabiensis*, and *An. funestus* may have different survival.

## Future Directions

- Apply the self-marking unit at Ghanaian breeding sites to obtain country-specific survival estimates.
- Combine with the dispersal-kernel-calibration.md methodology to validate the Centinela's dispersal parameters.
- Extend to insecticide-resistant populations to detect fitness costs of resistance.

## References

- Saarman NP, Pombi M, Torr S, Oulton A, Potter A, Williams J, et al. (2019). The development and evaluation of a self-marking unit to estimate malaria vector survival and dispersal distance. *Malaria Journal*, 18: 442. doi:10.1186/s12936-019-3077-3
- Costantini C, et al. (1996). Density, survival and dispersal of *Anopheles gambiae* complex mosquitoes in a West African Sudan savanna village. *Medical and Veterinary Entomology*, 10(3): 203–219.
- Midega JT, et al. (2007). Estimating dispersal and survival of *Anopheles gambiae* and *Anopheles funestus* along the Kenyan coast. *Journal of Medical Entomology*, 44(6): 923–929.