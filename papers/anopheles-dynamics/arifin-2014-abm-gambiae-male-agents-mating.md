# An agent-based model of the population dynamics of *Anopheles gambiae* — how males are (and are not) modelled

**Authors:** Arifin S, Zhou Y, Davis J, Gentile G, et al.
**Journal:** Malaria Journal | **Year:** 2014 (13:424) | **DOI:** 10.1186/1475-2875-13-424
**File:** papers/anopheles-dynamics/arifin-2014-abm-gambiae-male-agents-mating.md

> **Attribution note:** the existing repository extract
> `greenwood-et-al-2014-abm-anopheles-gambiae-population.md` cites this paper as
> "Greenwood B, et al."; the first author of *Malaria Journal* 13:424 is **Arifin S**
> (verified from the publisher/PMC record). The older file was **not** modified (task
> rule: no edits outside `papers/anopheles-dynamics/`), so this file records the
> correct attribution.

---

## Abstract (summary)

A theoretical, object-oriented agent-based model of the complete *Anopheles gambiae*
life cycle (egg, larva, pupa, adult) with hourly time steps, used to compare eight
"hypothetical vector control interventions" (HVCI) acting on life-cycle stages and
activities. Its relevance here is the **male treatment**: males are individual
agents with their own life-cycle stage, but **mating has no dynamics at all**.

## Key Results (as used by the model)

- **Males are individual agents with a dedicated stage.** Adult stages are: Immature
  adult (IA) → **Mate seeking (MS)** → Blood meal seeking (BMS) → Blood meal digesting
  (BMD) → Gravid (G). "Note that **adult males, once reaching MS stage, remain
  forever in that stage until they die**; adult females cycle through obtaining blood
  meals (in BMS stage), developing eggs (in BMD stage), and ovipositing the eggs (in
  G stage) until they die."
- **Mating is an unconditional, instantaneous transition.** "After entering this stage
  from the immature adult stage, **female adults are assumed to always find males for
  mating**." Model assumptions repeat it: "**Female adults, once entering the mate
  seeking stage, are always assumed to successfully find males to mate with** (in the
  next time step)."
- **No swarm, no spatial male field, no mating competition.** The MS stage is a
  *placeholder* whose only function is to give interventions (outdoor spraying, SIT,
  sugar baits) a male stage to target: "This fixed-duration period is designed to
  capture various swarming and mating behaviour of anophelines, during which predators
  and interventions (e.g., outdoor spraying, genetically engineered mosquitoes through
  SIT, etc.) may cause additional mortality (to be modelled in the future)."
- **Sex ratio at initialisation:** "Each simulation starts with a prespecified initial
  number of eggs as agents, **typically consisting of a 50:50 male–female ratio**."
- **Cost:** hourly time step; ~25 000 adults and ~1 000 000 aquatic mosquitoes; a
  one-year run takes ~1 h on a 2.4 GHz Core 2 Duo with 2 GB RAM; each parameter sweep
  repeats the simulation ≥ 30 times.
- Other quantified adult parameters: **P_FindHost = 25 % per hour** (18:00–06:00),
  P_FindBloodMeal = 100 %, P_FindHabitat = 25 % per hour, first-cycle fecundity
  N(170, 30), daily mortality with baseline 10 % and age terms.

## Relevance to MalariaSentinel (Centinela)

This is **the reference precedent for option (A) — males as a trivial aggregate**:
a published, influential ABM in which males exist as individuals (so they can be
killed by interventions) but carry **no behaviour and no mating dynamics**; female
mating is a guaranteed, instantaneous transition.

Consequences of that choice for the Centinela:
- The model cannot represent a **male shortage**: if males were removed by an
  intervention, females would still mate.
- It cannot represent **spatial swarm structure**, seasonal swarm phenology, or
  species-specific swarm sites.
- It is *computationally* cheap, but the cost is not compute — it is that any
  intervention that removes males (ATSB, swarm spraying, SIT/GM male releases) has
  **no transmission effect in the model**, although field evidence (Zhu et al. 2017)
  and the SIT literature suggest it does.

**Caveats:** *An. gambiae* s.l. (the paper applies the framework to *An. coluzzii* and
*An. arabiensis* as well); no parasite or human side is modelled (PIF is only an
approximate index); parameters are "specified as constant values ... these values can
be calibrated".

## License

CC BY 4.0 (© Arifin et al; licensee BioMed Central Ltd; Malaria Journal open access).
Open-access copy: https://pmc.ncbi.nlm.nih.gov/articles/PMC4233045/
