# The behaviour of adult *Anopheles gambiae*, sub-Saharan Africa's principal malaria vector, and its relevance to malaria control: a review

**Authors:** Wouter Takken, David Charlwood, Steve W. Lindsay
**Journal:** Malaria Journal | **Year:** 2024 | **DOI:** 10.1186/s12936-024-04982-3
**File:** papers/anopheles-dynamics/takken-2024-adult-anopheles-gambiae-behaviour-review.md

---

## Abstract (summary)

Open-access review of adult *Anopheles gambiae* (s.l.) behaviour for sub-Saharan Africa:
emergence at dusk, 24 h teneral period, swarming and mating, host finding by CO2/odour,
nocturnal and indoor blood feeding, gonotrophic concordance, oviposition and dispersal.
The review is the current canonical source for the behavioural constants used in
African malaria-vector models and it contains explicit statements on blood-meal volume,
pre-gravid behaviour and gonotrophic timing.

## Key Results (as used by the model)

- **Blood-meal volume: "Once blood has been detected, on average, 3 µl of blood is
  ingested."** (section *Blood feeding behaviour*). Direct statement for *An. gambiae*.
  → candidate value for `blood_meal_size_ul` (mean of a full meal).
- "When a suitable site for biting has been found, blood feeding can begin, **taking up to
  3 min to complete**." → the ingestion event is a multi-minute process, not instantaneous.
- "During feeding, diuresis of the watery parts of blood occurs, considerably reducing
  excess bodyweight from the blood meal" → blood weight is shed before the female flies.
- **Pre-gravid behaviour:** "…*gambiae* complex females may exhibit 'pre-gravid' behaviour
  in which a proportion of the females require **two blood meals before they can complete
  egg maturation**." → direct support for a *volume/threshold* mechanism and for a
  two-meal sub-population.
- "With the exception of the first feed, females are gonotrophically concordant and a blood
  meal gives rise to a complete egg batch." → the "one meal ⇒ one complete batch" rule
  applies from the **second** cycle onwards; the first cycle is the exception.
- "After taking a blood meal, most female mosquitoes will **rest indoors for two to three
  days** while the blood meal is digested and eggs are developed."
- "Eggs mature in blood-fed females within **two to three days** after a blood meal."
- People infected with gametocytes are more attractive to *An. gambiae* (raised aldehyde
  concentrations); mosquitoes with sporozoites in the salivary glands probe more
  frequently (uninfected 44 % vs infected 86 % probing in Choumet et al. 2012).

## Relevance to MalariaSentinel (Centinela)

The 3 µL figure is the closest thing to a species-matched (West African *An. gambiae*
complex) blood-meal volume available for Ghana. It is a review-level synthesis, not a
primary measurement in Ghana, so it should be used as the *central value* with a range,
not as a hard constant. The "two blood meals before egg maturation" statement is the
published basis for the multi-meal design; it also justifies keeping a distinct
first-cycle (pre-gravid) branch in the state machine.

Caveats: the review aggregates data from across sub-Saharan Africa (no Ghana-specific
blood-meal-volume measurement is reported); "3 µl" is a mean over feeding events, not a
per-observation distribution.

## License

CC-BY 4.0 (Malaria Journal / BMC open access).
