# Multiple blood meals as a reproductive strategy in *Anopheles* (Diptera: Culicidae)

**Authors:** Hans Briegel, E. Hörler
**Journal:** Journal of Medical Entomology | **Year:** 1993 | **DOI:** 10.1093/jmedent/30.6.975
**File:** papers/anopheles-dynamics/briegel-horler-1993-multiple-blood-meals-reproductive-strategy-anopheles.md

---

## Abstract (summary)

Laboratory study of feeding and egg maturation in nulliparous *Anopheles albimanus* (with
comparisons to *An. gambiae* and *An. stephensi*). Females were allowed to take repeated
blood meals within a single gonotrophic cycle, and the physiological consequences for
vitellogenesis, fecundity and maternal reserves were measured. It reframes multiple
feeding not as a failure but as a *reproductive strategy* driven by the female's energy
and lipid budget.

## Key Results (as used by the model)

- "Multiple blood meals within one gonotrophic cycle were taken readily at **6–24-hr
  intervals** by nulliparous female *Anopheles albimanus*."
- "**Up to five blood meals** were ingested and with each blood meal, more primary
  follicles matured as well as some secondary ones." → upper bound for the number of
  feeding bouts per gonotrophic cycle in the model.
- "The **first blood meal initiated limited vitellogenesis** and the maturation of few
  follicles. Instead, protein was diverted to the synthesis of maternal, extraovarian
  lipid and protein deposits; **fecundity increased with successive blood meals**."
- "In *An. albimanus*, a **critical female body size, approximately 0.25 cal of lipid per
  female, was necessary for the initiation of oogenesis; below this threshold at least
  two blood meals were required for follicle maturation**." → the explicit *threshold*
  concept: a female below a stored-energy threshold needs ≥2 meals to start the cycle.
- "***Anopheles gambiae* Giles and *An. stephensi* Liston also fed multiply**, but fecundity
  was less affected."
- "In general, **gonotrophic discordance** also was found routinely in these anopheline
  species." → the assumption that one meal ⇒ one clean batch is violated in the field.
- "In nonoogenic females, a replete blood meal increased total body protein and lipid by
  **17 % and 113 %**, respectively." (caloric/energetic cost of a full meal.)

## Relevance to MalariaSentinel (Centinela)

This is the closest published precedent for the mechanism the redesign implements:
a *threshold on the female's reserve state* (energy/lipid) below which the first meal does
not switch on oogenesis and the female keeps feeding. It also supplies the interval
(6–24 h between meals within a cycle) and the upper bound (5 meals) for the multi-meal
state machine.

Caveats: *An. albimanus* is a Neotropical species (proxy, not a *gambiae* s.l. species);
the "0.25 cal lipid" threshold is a body-size/reserve quantity, not a blood volume, so it
cannot be mapped onto `blood_meal_target_ul` without an explicit assumption. *An. gambiae*
"also fed multiply" but the abstract gives no number for it.

## License

© Oxford University Press, *Journal of Medical Entomology* (not open access; abstract read
via Europe PMC). Fair use for academic research.
