# Pathogens spread by high-flying wind-borne mosquitoes

**Authors:** R. Bamou, A. Dao, A. S. Yaro, C. Kouam, K. Ergunay, B. P. Bourke, M. Diallo, Z. L. Sanogo, D. Samaké, A. Y. K. Pambit-Zong, B. J. Krajacich, R. Faiman, M. A. Pacheco, A. A. Escalante, W. E. Weaver, S. J. Nartey, J. W. Chapman, D. R. Reynolds, Y. M. Linton, T. Lehmann
**Journal:** Proceedings of the National Academy of Sciences of the United States of America | **Year:** 2025 | **Volume/Pages:** 122(48): e2513739122 | **DOI:** 10.1073/pnas.2513739122
**Open access URL:** https://pmc.ncbi.nlm.nih.gov/articles/PMC12685058/
**File:** papers/anopheles-dynamics/bamou-2025-high-flying-windborne-mosquito-pathogens.md

---

## Abstract (summary)

Companion to Huestis et al. 2019 (Nature) on the aerial catches of Sahelian malaria
mosquitoes. Identifies 994 specimens to species at altitude, records their
**gonotrophic state**, and tests them for *Plasmodium*, arboviruses and filariae.
Provides the operational definition of the Sella score used to bin females into
bloodfed / semigravid / gravid, and the blood-state composition of windborne
catches — the field evidence that the long-distance dispersal channel carries
mostly *already-fed* (mostly gravid) females.

## Key Results (as used by the model)

- Gonotrophic state was scored with the **Sella scale**, operationalised as:
  "gonotrophic state observed and recorded according to Sella scores: **1-2 for
  bloodfed, 3-5 for semigravid, and 6-7 for gravid**" (Methods, Specimen
  Processing and DNA/RNA Extraction).
  → direct provenance for a `blood_state` enum with three bins
  (`BLOOD_FED`, `SEMI_GRAVID`, `GRAVID`) plus `UNFED`, and for the mapping
  "semi-gravid" ≡ "Sella 3–5" (the fed-parous / sub-gravid state).
- Sex and blood-state composition of the altitude catches: "Females comprised
  **81%** of identified specimens, with no evidence for interspecies
  heterogeneity in the sex composition ( *P* = 0.065 …). Overall, **gravid
  females consisted of 43%** of identified species with fractions varying
  between 28% ( *Aedes circumluteolus* , *N* = 10) to 65% ( *An. squamosus* ,
  *N* = 17, among-species heterogeneity *P* = 0.001 …)"
  (Results). The wording "43% of identified species" is the authors'; read as
  43 % of identified **specimens** were gravid females. Species-level gravid
  fractions span 28–65 %.
- Exposure to blood was computed as "the fraction of gravid, semigravid, and
  blood-fed females combined as opposed to unfed females" (Methods) — i.e. the
  same "has fed at least once" accounting as the Centinela's
  `feeding_success`/blood-volume accumulator.
- The windborne cohort is enriched for blood-fed females relative to
  ground-caught populations, which is the mechanism by which migrants carry
  pathogens: "the migrants were dominated by gravid females that had fed on
  vertebrate blood before engaging in migratory flight".

## Relevance to MalariaSentinel (Centinela)

- Gives the field-measured **composition of blood states in airborne catches**
  for the Sahelian *Anopheles* assemblage (dominant species *An. coluzzii* and
  *An. gambiae* s.s.), i.e. the empirical prior for "a female that leaves as a
  windborne migrant is usually already gravid, not unfed".
- Gives the **operational definition of `SEMI_GRAVID`** (Sella 3–5) that the
  redesigned state machine needs for the `PRE_GRAVID` state, and the
  blood-state bins to use in the state-output contract.
- Caveats: the catches are aerial (altitude 40–290 m above ground) in Mali,
  November–December 2013 and 2014; the "43 %" figure is for all mosquito
  species pooled, and species-specific fractions for *Anopheles* are 28–65 %.
  The paper scores the state from the external abdominal appearance after
  freezing/ethanol storage, not from ovarian dissection.

## License

Creative Commons Attribution-NonCommercial-NoDerivatives 4.0
(CC BY-NC-ND 4.0) — https://creativecommons.org/licenses/by-nc-nd/4.0/
