# Continuous mark-release recapture to improve estimates of movement and survival of the African malaria mosquitoes

**Authors:** Moussa Diallo, Adama Dao, Zana L. Sanogo, Kadiatou Cissé, B. Coulibaly, Djibril Samaké, et al.
**Journal:** bioRxiv preprint | **Year:** 2026 | **DOI:** 10.64898/2026.06.24.734339
**File:** papers/anopheles-dynamics/diallo-2026-continuous-mrr-mali.md

---

## Abstract

Despite extensive efforts to understand the population biology and ecology of the African malaria mosquitoes, questions regarding their movement pattern, survival, and population size persist, reflecting methodological limitations. Site fidelity, in which mosquitoes return to feeding sites, resting sites, or oviposition sites remain debated. Mark release recapture (MRR) studies are vital to address such questions. Using locality- and date-specific DNA tags in fluorescent spray, we carried out a **continuous MRR in a Malian village from September to December 2019 with three days interval between capture and release across seven zones.** A total of 12,937 *Anopheles gambiae* s.l. (7,455 females) were captured during 35 indoor collections. Handling related mortality was 3.4 %. *A. coluzzii* predominated (89.7 %), followed by *A. gambiae* (9.4 %), and *A. arabiensis* (0.9 %). Overall recapture rate was 1.05 % (N = 129). **The corrected probability of daily survival (PDS) was 94 % and the daily increase in sporozoite rate was 4.9 %.** The average days post release (minimum age of wild captured mosquitoes) for recaptures was 6.4 d with the longest being 30 d.

## Methods

- **Innovation:** Continuous MRR — DNA-tagged fluorescent marking at locality-and-date resolution, allowing multiple cohorts to be tracked simultaneously.
- **Site:** Malian village (Sahel zone).
- **Duration:** September – December 2019 (~4 months, 35 indoor collections).
- **Species:** *Anopheles gambiae* s.l. (*A. coluzzii* 89.7 %, *A. gambiae* 9.4 %, *A. arabiensis* 0.9 %).
- **Survival model:** Exponential with correction for recapture duration (PDS increased from 74 % at 12-day recapture to 86 % at 30-day recapture, uncorrected → 94 % corrected).

## Key Results

- **Daily survival probability (PDS):** **0.94** (corrected); 0.74–0.86 uncorrected depending on recapture duration.
- **Mean minimum age:** 6.4 days; longest recaptured mosquito = **30 days** (an An. gambiae s.l. maximum observed age in the field).
- **Daily increase in sporozoite rate:** 4.9 %/day — confirming high EIP completion in this high-transmission setting.
- **No site fidelity:** 70 % of recaptured mosquitoes were in a different zone from where they were released (r = 0.97, P < 0.001 vs capture distribution).
- **Average movement distance:** Similar for males and females; females' distance did NOT increase over time (in contrast to males).

## Relevance to MalariaSentinel (Centinela)

This is the **most recent and methodologically sophisticated** MRR estimate for *An. gambiae* s.l. in West Africa. Key contributions:

1. **Daily survival = 0.94** (corrected) is **at the upper end of the field range** and consistent with Midega 2007 (Kenya coast, 0.95). Combined with the 30-day maximum age, this confirms that **some An. gambiae females live ~30 days in the field** — the lower-bound of the "2–4 weeks in field, up to 2 months in lab" range from the perplexity-investigations review.

2. **The Centinela's `ADULT_DAILY_MORT_BASAL = 0.93` is consistent** with this corrected estimate, giving a mean adult lifespan of ~14 days (1/(1-0.93) = 14.3 days). This is sufficient for **at least 4 gonotrophic cycles** (cycle_duration_days = 2.65 → 4 cycles = 10.6 days minimum).

3. **No site fidelity** simplifies the dispersal model — mosquitoes don't preferentially return to their release site, supporting the isotropic Gaussian kernel in the Centinela.

4. **30-day maximum age** sets a useful upper bound for any population collapse analysis: a sustained population with adults living 30 days can produce ~10 generations of offspring if development is fast enough (~3 days per generation, not realistic) or ~1.5 generations with realistic 20-day development.

## Limitations

- Preprint (2026); not yet peer-reviewed.
- Single Malian Sahel site; generalisability to forest or urban Ghana unclear.
- Indoor-resting collections under-sample exophilic species.
- The "corrected" PDS depends on assumptions about emigration rates that are hard to verify.
- 4-month window during the late rainy / early dry season; full seasonal cycle not characterised.

## Future Directions

- Apply the continuous-MRR methodology to Ghanaian field sites for country-specific survival estimates.
- Couple with the dispersal-kernel-calibration.md methodology to validate the Centinela's spatial spread predictions.
- Extend to *An. funestus* (the secondary Ghanaian vector) which has different survival dynamics.

## References

- Diallo M, Dao A, Sanogo ZL, Cissé K, Coulibaly B, Samaké D, et al. (2026). Continuous mark-release recapture to improve estimates of movement and survival of the African malaria mosquitoes. *bioRxiv* preprint. doi:10.64898/2026.06.24.734339
- Midega JT, et al. (2007). Estimating dispersal and survival of *Anopheles gambiae* and *Anopheles funestus* along the Kenyan coast. *Journal of Medical Entomology*, 44(6): 923–929.
- Costantini C, et al. (1996). Density, survival and dispersal of *Anopheles gambiae* complex mosquitoes in a West African Sudan savanna village. *Medical and Veterinary Entomology*, 10(3): 203–219.
- Saarman NP, et al. (2019). The development and evaluation of a self-marking unit to estimate malaria vector survival and dispersal distance. *Malaria Journal*, 18: 442.