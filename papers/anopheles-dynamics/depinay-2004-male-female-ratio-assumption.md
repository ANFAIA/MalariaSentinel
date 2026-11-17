# A simulation model of African *Anopheles* ecology and population dynamics — the male is a 1:1 assumption

**Authors:** Depinay JMO, Mbogo CM, Killeen G, Knols B, Beier J, Carlson J, Dushoff J, Billingsley P, Mwambi H, Githure J, Touré AM, McKenzie FE
**Journal:** Malaria Journal | **Year:** 2004 (3:29) | **DOI:** 10.1186/1475-2875-3-29
**File:** papers/anopheles-dynamics/depinay-2004-male-female-ratio-assumption.md

---

## Abstract (summary)

The foundational individual-based simulation of the complete *Anopheles gambiae* life
cycle (egg, larva, pupa, adult), with thermal development rates fitted to Bayoh &
Lindsay (2003), larval nutrient competition, density-dependent predation, and a
20-month validation run against Kilifi (Kenya) field data. It is the ancestor of most
later African vector ABMs, including the Centinela.

## Key Results (as used by the model)

- **Males are not modelled as individuals and mating is not modelled.** The single
  male-related assumption in the model-description section is:
  "**The male-female ratio at emergence from the pupa stage is assumed to be 1:1.**"
  There is no mating stage, no swarm, no insemination probability, no male movement
  law anywhere in the model description.
- Everything else is female-side: adult daily survival **0.911/day** on
  non-ovipositing days (reduced on ovipositing days by a predation/host-seeking lag),
  larval mortality 25 % (density-dependent), egg mortality 5 % of the batch plus 0.99
  daily survivorship, egg-to-adult ~11–13 d at 25 °C, first blood meal at one day of
  adult age.

## Relevance to MalariaSentinel (Centinela)

The canonical **"males as a fixed sex ratio"** precedent (option A in its purest
form): the male enters the model only as a 1:1 ratio at emergence; fertilisation is
implicit and unlimited, and the *population-growth* consequence of a female that never
mates is never represented.

Read together with `arifin-2014-abm-gambiae-male-agents-mating.md` (males as
individuals but mating guaranteed) and `zhu-2017-outdoor-control-ibm-male-mating.md`
(males simulated, mating still assumed successful), the three papers show that
**60 years of malaria ABM practice contains no explicit male mating dynamics** —
which is precisely the gap the Centinela's redesign is being asked to close (or to
justify closing).

**Caveats:** the model has no spatial landscape, no transmission module, and several
parameters were "arbitrarily set" because of data scarcity; species is *An. gambiae*
s.l.

## License

CC BY 2.0 (© 2004 Depinay et al; licensee BioMed Central Ltd; open access).
Open-access copy: https://pmc.ncbi.nlm.nih.gov/articles/PMC514565/
