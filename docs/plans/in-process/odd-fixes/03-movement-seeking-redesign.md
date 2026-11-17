# Pack 03 — Movement and seeking redesign (direction vectors, pheromones)

> Source: ODD 2010 review notes.
**Document sections invalidated (CUJ-4):** `docs/concepts/abm/odd-2010-malariasentinel.tex` → §4.7 "Sensing", §4.8 "Interaction", §7.6 "Seek hosts and feed", §7.7 "Disperse adults", §5.4 "Randomness and reproducibility".
When this pack is decided and applied, these are the passages that
must change; the document is amended in the commit that applies the
pack, not in the pack itself.
 Status: initial plan — to be detailed later.

## Objective

Replace the current mixture of fixed-step directed movement and random
Gaussian jumps with a single daily movement: one step along a resultant
**direction vector** built from attraction/repulsion cues, with a
species-dependent distance (capacity of movement of each species, based on papers).
Sensing reframed as individual/pheromone-based rather than cell-based.
Which makes this pack dependent on 02.

## Notes (verbatim)

- **p.23** (whole seeking section) — "Change point of view, add a direction vecotr. Mosquitoes move ones and in a singles step in the direction given by the combination of vectors. Distance of moving depend s on species, no fixed param of the type of movement + depends on the resulting vector of movement. This vector magnitude informs of attraction factor + lack of attraction near the mosquitoe. In other words, it may need blood or can't breed where it is."
- **p.23** (attraction equation) — "As mentioned before seek has meaning when there are individuals, and not cells. Every mosquito looks phermones searching for individual preys"
- **p.25** (Disperse adults) — "only one movement and not random but guided." / (wind formula) "this keeps the same"
- **p.25** (2 km/day consequence) — "no, as stated before in other comments"
- **p.24** (parameter table) — `dispersal.host_flight_step_m` (500 m) "recommended to be deleted, because it implies a fixed movement for all mosquitoes per day, not realistic"
- **p.6** (directed host movement) — "depend on cell size and density, not on actual mosquito biology."
- **p.6** (starvation rule) — "without knowing if hosts are not ABMs"
- **p.9** (dispersal kernel) — "Review its possible deletion for simplification"
- **p.17** (wildlife proxy) — "Think of it as a low pheromone in whole area → if human around → more attraction depending on species (natural behavior)"
- **p.29 A.3** — "Eliminate this complicated and unused system, change to vectorized version of movement mentioned before." *(the unused 12-hourly `multirate_scheduler`)*

## Initial steps

1. Design the vector-based movement model: attraction cues (hosts,
   animals, including wildlife ones) combine into one resultant
   vector; step length is species-dependent and emergent, not a fixed
   parameter per movement type. Which means it depends on species qualities
   plus attraction.
2. Delete `host_flight_step_m` and the unused `multirate_scheduler.hpp` /
   `MultirateDayState` machinery; replace with the vectorized movement.
3. Decide the fate of the Gaussian dispersal kernel (delete vs. keep as
   a residual random component).
   Human answer: Delete, it is no useful anymore, as now movement is
   dependent on attraction.
4. Keep the windborne migration formula unchanged ("this keeps the same").
5. Re-examine the 7-day starvation rule under hosts-as-ABMs (cross-ref 02).

## Dependencies / open points

- Feeds into pack 04 (feeding/oviposition interactions) and pack 12
  (round-robin constructor removal → "new mosquito movement submodel").
- Golden fixtures and calibration scorers will change — plan regeneration.
