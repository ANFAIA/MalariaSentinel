# Landscape movements of Anopheles gambiae malaria vector mosquitoes in rural Gambia

**Authors:** C. J. Thomas, D. E. Cross, C. Bøgh
**Journal:** PLOS ONE | **Year:** 2013 | **DOI:** 10.1371/journal.pone.0068679
**File:** papers/anopheles-dynamics/thomas-2013-anopheles-gambiae-gambia-dispersal.md

---

## Abstract

[Full abstract from PLOS ONE — rural Gambia MRR study of An. gambiae s.l. landscape movements]

## Methods

- **Site:** Rural Gambia (village in the Central River Region).
- **Release:** Wild *Anopheles gambiae* sensu lato marked with fluorescent powder.
- **Recapture:** Indoor pyrethrum spray catches across multiple villages within a 5 km radius.
- **Dispersal modelling:** Two probability density functions fitted — negative exponential and half-Cauchy.
- **Random walk validation:** Simulated daily displacement (350 m/day, 0.8/day survival) and compared to empirical recapture distributions.

## Key Results

| Distribution | Median dispersal | 90th percentile | 95th percentile |
|---|---|---|---|
| Negative exponential | **386 m** | 1.28 km | 1.67 km |
| Half-Cauchy | **295 m** | 1.64 km | 2.83 km |

- **Daily survival (concurrent estimate):** 0.80/day.
- **Random walk validation:** A simple 350 m/day step with 0.8/day survival reproduces both empirical distributions — confirming that isotropic daily movement with stochastic survival is sufficient to generate realistic population-level dispersal.

## Relevance to MalariaSentinel (Centinela)

This paper is **directly cited in `papers/anopheles-dynamics/dispersal-kernel-calibration.md`** as the key reference for the Centinela's dispersal parameters:

- **`ADULT_DISPERSE_SIGMA_M = 450`**: midpoint of Costantini et al. 1996 range (350–650 m/day), consistent with Thomas et al. 2013 median (386 m).
- **`ADULT_DISPERSE_MAX_M = 2000`**: matches Thomas et al. 2013 95th percentile (1.67–2.83 km).
- **`ADULT_DISPERSE_PROB = 0.05`**: lower than the original 0.10; aligned with the documented "daily survival 0.80–0.88 implies mean adult lifespan 4–5 days" reasoning.

The random walk validation is particularly important: it demonstrates that **the Centinela's isotropic Gaussian dispersal kernel is theoretically sound** — it can reproduce empirical recapture distributions without requiring explicit path integration or memory. This justifies the choice of a simple kernel over more complex movement models.

## Limitations

- Single rural Gambia site; urban or forest populations may disperse differently.
- Indoor-resting recapture underestimates exophilic *An. arabiensis*.
- The 5 km recapture radius truncates long-distance dispersal events.
- Half-Cauchy vs exponential selection affects tail estimates significantly.

## Future Directions

- Validate the Centinela's Gaussian kernel against Thomas et al.'s empirical distributions.
- Test whether the kernel reproduces the spatial spread rate observed in M7+ U-Net emulators.
- Couple with landscape connectivity (river networks, forest patches) for heterogeneous dispersal.

## References

- Thomas CJ, Cross DE, Bøgh C (2013). Landscape movements of *Anopheles gambiae* malaria vector mosquitoes in rural Gambia. *PLOS ONE*, 8(7): e68679. doi:10.1371/journal.pone.0068679
- Costantini C, et al. (1996). Density, survival and dispersal of *Anopheles gambiae* complex mosquitoes in a West African Sudan savanna village. *Medical and Veterinary Entomology*, 10(3): 203–219.
- Saarman NP, et al. (2019). The development and evaluation of a self-marking unit to estimate malaria vector survival and dispersal distance. *Malaria Journal*, 18: 442.