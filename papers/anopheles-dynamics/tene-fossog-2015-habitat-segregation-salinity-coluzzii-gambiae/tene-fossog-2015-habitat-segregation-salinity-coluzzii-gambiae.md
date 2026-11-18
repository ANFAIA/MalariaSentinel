# Habitat segregation and ecological character displacement in cryptic African malaria mosquitoes

**Authors:** Benjamin Tene Fossog, Diego Ayala, Pablo Acevedo, Pierre Kengne, Illona Ngomo Abeso Mebuy, Boris Makanga, John Magnus, Parfait Awono-Ambene, Frank Njiokou, Maurizio Pombi, Christophe Antonio-Nkondjio, Christine Paupy, Nora Besansky, Carlo Costantini
**Journal:** Evolutionary Applications | **Year:** 2015 (8(4):326–345) | **DOI:** 10.1111/eva.12242
**File:** papers/anopheles-dynamics/tene-fossog-2015-habitat-segregation-salinity-coluzzii-gambiae.md

---

## Abstract (summary)

Species-distribution modelling of *Anopheles gambiae* vs *An. coluzzii* across
their whole West/Central African sympatric range (1,140 georeferenced
localities; 45,834 molecularly identified *An. gambiae* s.l., 2001–2011)
combined with acute salinity-tolerance bioassays on ~15,800 larvae from 32
populations (coastal and inland Cameroon, Equatorial Guinea, Gabon). The
study links a continental-scale habitat-segregation pattern to a measurable
physiological trait (larval tolerance of salinity) and finds evidence of
ecological character displacement.

## Key Results (as used by the model)

- **Bimodal distribution of *An. coluzzii*.** Relative frequency of *An.
  coluzzii* vs *An. gambiae* along the distance-to-coast gradient: **0.62 ±
  0.05 within 5 km of the sea**, falling to a minimum of **0.06 ± 0.04 at
  350–450 km** from the coast, then rising to **0.88 ± 0.04 beyond 900 km**.
  The model has **R² = 0.99** between predicted and observed relative frequency
  (calibration plot). This is the empirical support for a **coastal
  coluzzii-rich band along the Gulf of Guinea**, i.e. for the AOI
  `accra-coastal-test` being coluzzii-dominated.
- **Elevation control:** *An. coluzzii* predominates at sea level and is
  replaced by *An. gambiae* **above ≈ 430 m** on the Cameroon Volcanic Line;
  it is absent above 800–1000 m except in strictly urban settings.
- **Salinity tolerance (LC50, in % sea water; 35 g/L NaCl = 100 % SW):**
  *An. coluzzii* rural coastal **31.2 ± 2.8 %SW**, urban coastal
  **30.1 ± 3.6 %SW**, urban inland **35.9 ± 4.1 %SW**;
  *An. gambiae* rural coastal **25.2 ± 2.8 %SW**, rural inland
  **23.6 ± 2.9 %SW**, urban coastal **30.8 ± 3.6 %SW**, urban inland
  **35.6 ± 4.2 %SW**. *An. coluzzii* is significantly more tolerant than
  *An. gambiae* in sympatry (rural), the difference disappearing when
  *An. gambiae* occurs in urban habitats.
- **Stability of the trait:** coefficient of variation of LC50 across
  populations is **9.5 % for *An. coluzzii*** vs **19.0 % for *An.
  gambiae***; the LC50–conductivity relationship is positive and asymptotic
  with an **asymptote at 36.2 % sea water**.
- **Hard physiological ceiling (quoted from Bradley 1987):** even at its most
  salt-tolerant, *An. coluzzii* "must be considered an obligate freshwater
  taxon, confined to water whose osmotic concentration is less than larval
  haemolymph (~300 mOsm/kg or ~30 % sea water)". At 35 g/L NaCl = 100 % SW,
  30 % SW ≈ **10.5 g/L ≈ 10.5 ppt**.
- **Habitat segregation mechanisms:** larval habitats exclusive to *An.
  coluzzii* in the field were "fishermen pirogues stranded on the beach or
  emerging water table pools along the beach or river estuaries, which
  contained much greater amounts of salts".

## Relevance to MalariaSentinel (Centinela)

The reference for the **salinity dimension of the habitat contract**: it gives
the measured *coluzzii* > *gambiae* salinity ranking (→ `salinity_slope` and
`salinity_hi_tol_ppt` ordering), the physiological ceiling (~30 % SW ≈ 10.5
ppt, i.e. the upper bound of what the YAML calls `salinity_hi_tol_ppt: 30`
if the unit is ppt rather than %SW), and the coastal-distance abundance
gradient that justifies coluzzii as the pilot species for the coastal AOI.
**Caveats:** the LC50 is an **acute 24 h larval** bioassay on field larvae
(Central Africa), not a chronic exposure or a full life-cycle threshold;
"% sea water" and "ppt" are not the same unit (35 g/L NaCl = 100 %SW, so
10.5 ppt ≈ 30 %SW); no Ghanaian populations were assayed.

## License

CC BY 4.0 (open access, Wiley / Evolution, Medicine, and Public Health).
