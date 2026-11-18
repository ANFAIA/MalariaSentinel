# Phenotypic changes in natural populations of *Anopheles gambiae* s.l. at the onset of the long dry season in tropical savannahs of Burkina Faso, West Africa

**Authors:** Wadaka Mamai, Karine Mouline, David Renault, Kevin Hidalgo, Kounbobr Roch Dabiré, Frédéric Simard
**Journal:** Parasite (Paris) | **Year:** 2026 | **Volume:** 33 | **Article no.:** 9 | **DOI:** 10.1051/parasite/2026010 | **PMID:** 41738614
**Open access URL:** https://pmc.ncbi.nlm.nih.gov/articles/PMC12934212/
**File:** papers/anopheles-dynamics/mamai-2026-coluzzii-dry-season-gonotrophic-dissociation.md

---

## Abstract (summary)

Late-instar *Anopheles gambiae* s.l. were collected at two ecologically distinct sites in
Burkina Faso — **Bama** (a large permanent larval habitat available year-round) and
**Soumousso** (temporary breeding habitats) — during the rainy season and during the
transition into the long dry season; larvae were reared to adulthood under natural
conditions and the adults were blood-fed and dissected 14 days later. Traits measured:
ovarian development (gonotrophic dissociation), sub-cuticular fat-body hypertrophy,
body size (geometric morphometrics) and energy reserves (proteins, lipids,
carbohydrates). This is the most direct **field** evidence that ***An. coluzzii* enters
a reproductive arrest at the onset of the dry season** while *An. gambiae* and
*An. arabiensis* do not.

## Key Results (as used by the model)

- Framing of the aestivation hypothesis for the complex: "Several studies conducted
  on *Anopheles* mosquitoes … support the hypothesis that population persistence
  during the dry season occurs primarily via **aestivation in the form of adult
  females, particularly in *An. coluzzii***, as opposed to long-distance migration to
  and from areas with suitable breeding sites in *An. gambiae* and *An. arabiensis*."
- Definition used for the arrest: "When the ovaries or follicles of female
  mosquitoes that have taken a full blood meal **fail to develop**, the arrested
  ovarian development is termed **gonotrophic dissociation**"; ovarian development
  "comprises two distinct phases (previtellogenic and vitellogenic stages), with
  ovarian development being triggered by the ingestion of a blood meal. In the
  absence of a blood meal, there is no progression beyond the pre-vitellogenic
  stage."
- Dry-season environment: "In the West African savannah, **the dry season can last
  for up to nine months**, during which most standing water bodies and other
  surface water sources suitable for oviposition and larval development may
  completely dry up … temperatures frequently exceeding 35 °C and relative humidity
  dropping below 10%".
- Species composition of the blood-fed females: at Bama **100 % *An. coluzzii***
  (n = 803); at Soumousso *An. gambiae* 48.47 % (n = 554), *An. arabiensis* 29.66 %
  (n = 339), *An. coluzzii* 21.87 % (n = 250). Insemination rate 98 % (n = 300
  dissected) — so the arrested ovaries are not explained by failed mating.
- **Ovarian development by species (all seasons):** "Regardless of the season,
  *An. coluzzii* was the species that most efficiently developed eggs beyond
  **ovarian stage 2 (ranging from 65.15 to 80.77%)** compared to both
  *An. arabiensis* (51.02–59.91%) and *An. gambiae* (31.36–31.88%)."
- **Gonotrophic dissociation (the arrest):** "Despite multiple blood meals being
  provided, **19.23 to 68.64% of female mosquitoes collected at both localities
  failed to develop their ovaries beyond Christopher's stage 2**, indicating a
  physiological state of gonotrophic dissociation. Interestingly, *An. coluzzii*
  from both sites showed **significantly higher proportions of females in
  gonotrophic dissociation at the onset of the dry season than during the rainy
  season** (χ² = 3.953, df = 1, p = 0.004 and χ² = 5.584, df = 1, p = 0.018 for
  Soumousso and Bama populations, respectively). By contrast, **no significant
  seasonal variation** in gonotrophic dissociation was evidenced in *An. gambiae*
  (χ² = 0.00066, df = 1, p = 0.979) and *An. arabiensis* (χ² = 1.846, df = 1,
  p = 0.17) from Soumousso."
- Link to the dry-season strategy of the two habitats: "The capacity to colonise
  permanent water bodies may enable *An. coluzzii* to maintain reproductive activity
  even during the dry season. Thus, in areas where permanent breeding sites are
  present year-round, this species could invest either in **survival by
  accumulating nutrient reserves** or continued reproduction. Conversely, in areas
  where oviposition sites disappear during the dry season, a significant proportion
  of individuals may **shift their physiology towards a state of gonotrophic
  discordance**".
- Energetics: "Newly emerged *An. coluzzii* accumulated significantly higher levels
  of **lipids, sugars, glycogen, and protein** during the transitional period (i.e.
  at the onset of the dry season) compared to the rainy season." All three species
  increased body size and cuticular fat deposits at the transition.
- Attribution to prior work: "These findings are consistent with previous studies
  reported by **Yaro et al.**, who documented gonotrophic dissociation in
  *An. coluzzii* collected indoors during the dry season in an arid region of
  Mali. In that study, reproductive arrest was not limited to arrested ovarian
  development, but also involved **suppressed oviposition, even in females with
  fully developed eggs**."

## Relevance to MalariaSentinel (Centinela)

- **Direct evidence for a dry-season reproductive-arrest state in *An. coluzzii***
  (M tier): a blood meal does **not** guarantee egg maturation. Between 19 % and
  69 % of blood-fed females failed to develop oocytes past Christophers stage 2,
  and the fraction is significantly higher at the onset of the dry season.
  → The engine's implicit assumption "blood meal ⇒ eggs mature in
  `cycle_duration_days`" is wrong for a dry-season *coluzzii*. The redesigned
  state machine needs a branch where a blood-fed female **remains in a
  gonotrophic-arrest / `AESTIVATING`** state (eggs not maturing) instead of
  advancing to `GRAVID`, and her blood volume is consumed while the reproductive
  clock stops.
- **Provenance for a dry-season (or habitat-dependent) arrest probability**: the
  measured 19.23–68.64 % arrest fraction (site- and season-dependent) is the
  natural candidate for a `dry_season_arrest_prob` / `gonotrophic_arrest_prob`
  parameter, with the *coluzzii* > *arabiensis* > *gambiae* ordering.
- **Provenance for the energy-reserve axis** (fat body hypertrophy, lipids,
  glycogen): the paper shows that surviving the dry season costs energy, i.e. a
  survival penalty for arrested females is mechanistically expected (and
  measurably paid in *coluzzii*), which supports the "a dry habitat is not lethal
  for the adult female, she postpones" semantics.
- Caveats: the arrest was assayed **14 days after blood feeding**, at the *onset*
  of the dry season (transitional period), not through the whole dry season;
  females were reared from field-collected larvae; Bama vs Soumousso contrast
  (permanent vs temporary breeding sites) means the arrest rate is
  habitat-dependent; *coluzzii* was the only species at Bama.

## License

Creative Commons Attribution 4.0 (CC BY 4.0) —
https://creativecommons.org/licenses/by/4.0/
