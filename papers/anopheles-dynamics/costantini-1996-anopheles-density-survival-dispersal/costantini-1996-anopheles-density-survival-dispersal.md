# Density, survival and dispersal of Anopheles gambiae complex mosquitoes in a West African Sudan savanna village

**Authors:** C. Costantini, S. Li, A. della Torre, N. F. Sagnon, M. Coluzzi, C. E. Taylor
**Journal:** Medical and Veterinary Entomology | **Year:** 1996 | **DOI:** 10.1111/j.1365-2915.1996.tb00733.x
**File:** papers/anopheles-dynamics/costantini-1996-anopheles-density-survival-dispersal.md

---

## Abstract

To obtain information on adult populations of Afrotropical malaria vector mosquitoes, mark-release-recapture experiments were performed with *Anopheles* females collected from indoor resting-sites in a savanna area near Ouagadougou, Burkina Faso, during September 1991 and 1992. Results were used to estimate the absolute population densities, daily survival rates, and dispersal parameters of malaria vectors in that area. In 1991 a total of 7,260 female *Anopheles* were marked and released, of which 106 were recaptured in the release village and 6 in the neighbouring villages (1.5 % total recapture). The following year 13,854 female *Anopheles* were released and 116 recaptured in Goundri and 8 in the neighbouring villages (0.9 % total recapture). Population densities were estimated using the Lincoln Index, Fisher-Ford and Jolly's methods (consensus value 150,000–350,000 female *An. gambiae* s.l.). **Survival was estimated at 0.80–0.88 per day.** Mean distance moved by individual mosquitoes ranged **350–650 m/day**, depending on the dispersal model and the year.

## Methods

- **Site:** Goundri village, 30 km south of Ouagadougou, Burkina Faso (Sudan savanna).
- **Years:** September 1991 and September 1992.
- **Release:** Female *Anopheles* collected from indoor resting sites, marked with fluorescent powder, released at a central point.
- **Recapture:** Indoor pyrethrum spray catches in release village and 8 neighbouring villages.
- **Analysis:** Lincoln Index, Fisher-Ford, and Jolly's method for population size; Gillies exponential model for daily survival; least-squares fitting of two dispersal models (random and gradient-dependent).

## Key Results

- **Daily survival probability:** **0.80–0.88/day** (two-year range, depends on statistical method).
- **Mean life expectancy:** 4.5–8.3 days.
- **Mean daily dispersal distance:** **350–650 m/day** (model-dependent).
- **Female population size estimate:** 150,000–350,000 mosquitoes in the release village (consensus value).
- **Species composition:** *An. gambiae* s.s. and *An. arabiensis* in ~2:3 ratio.

## Relevance to MalariaSentinel (Centinela)

This is the **key field reference for the daily survival and dispersal parameters** used in the Centinela. From `papers/anopheles-dynamics/dispersal-kernel-calibration.md`:

- `ADULT_DISPERSE_SIGMA_M = 450` is the midpoint of Costantini's 350–650 m/day range.
- `ADULT_DAILY_MORT_BASAL = 0.93` is at the upper edge of the field MRR range (0.80–0.88) but consistent with later studies (Midega 2007: 0.83–0.95; Saarman 2019: 0.87; Diallo 2026: 0.94 corrected).
- The Burkina Faso savanna is the closest ecological proxy for northern Ghana (Sudan/Guinea savanna transition zone).

The Centinela's Ghana ABM does not have a Ghana-specific MRR study to calibrate against — this paper is the best-available proxy.

## Limitations

- Indoor-resting collections bias the sample toward endophilic *An. gambiae* s.s.; exophilic *An. arabiensis* may be under-represented.
- Dispersal estimates conflate survival with emigration (mosquitoes lost from the recapture area could have died OR emigrated beyond the search radius).
- Single-village site; results may not generalise to urban or forest environments.
- Two-year window during rainy season; dry-season dynamics not characterised.

## Future Directions

- Cross-validate with newer MRR methods (e.g. self-marking unit, Saarman 2019) to separate mortality from emigration.
- Extend to Ghanaian sites with concurrent host availability data (the Centinela's HostLandscape module).
- Couple dispersal estimates with the landscape ABM for spatial spread forecasting.

## References

- Costantini C, Li S, della Torre A, Sagnon N, Coluzzi M, Taylor CE (1996). Density, survival and dispersal of *Anopheles gambiae* complex mosquitoes in a West African Sudan savanna village. *Medical and Veterinary Entomology*, 10(3): 203–219. doi:10.1111/j.1365-2915.1996.tb00733.x
- Midega JT, Mbogo CM, Mwambi H, et al. (2007). Estimating dispersal and survival of *Anopheles gambiae* and *Anopheles funestus* along the Kenyan coast by using mark-release-recapture methods. *Journal of Medical Entomology*, 44(6): 923–929.
- Saarman NP, Pombi M, Torr S, et al. (2019). The development and evaluation of a self-marking unit to estimate malaria vector survival and dispersal distance. *Malaria Journal*, 18: 442.