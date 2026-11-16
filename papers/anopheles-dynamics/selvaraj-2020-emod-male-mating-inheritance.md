# EMOD vector genetics (Selvaraj et al. 2020) — the one modern malaria ABM in which males are individual agents that actually mate

**Authors:** Selvaraj P, Wenger EA, Bridenbecker D, Windbichler N, Russell JR, Gerardin J, et al. (Institute for Disease Modeling)
**Journal:** PLoS Computational Biology | **Year:** 2020 (16(8):e1008121) | **DOI:** 10.1371/journal.pcbi.1008121
**File:** papers/anopheles-dynamics/selvaraj-2020-emod-male-mating-inheritance.md

---

## Abstract (summary)

A stochastic, agent-based **vector-genetics model embedded in EMOD** (an agent-based
mechanistic model of *Plasmodium falciparum* transmission with a vector life cycle),
used to evaluate insecticide resistance, gene drives and population replacement. Its
relevance to the male question is that it is the only malaria transmission ABM found
in this survey in which **males and females are separate agents that mate, and the
mating produces offspring with inherited genotypes**.

## Key Results (as used by the model)

- **Males and females are modelled explicitly and mating is mechanistic.** "When
  mating occurs in the model, **the male and female produce offspring with a
  combination of genes and alleles obtained from the gametes of the parents via
  Mendelian inheritance**." Traits that can be attached to male genotypes include
  "generate progeny biased towards a specific gender, confer fitness costs such as
  reduced fecundity or increased mortality".
- **Vector life cycle:** four stages — eggs, larvae, **immature adults**, host-seeking
  adults — with adult sex as an explicit attribute; ~100 000 adult males and females
  per location in the demonstrations, and 1 000 released males.
- **Male survival is a model parameter** (e.g. a genotype with "reduced mortality of
  male mosquitoes by half"), and male-mediated gene flow is the mechanism of spread:
  "**male mosquitoes are unaffected by ITNs and reseed the vector population** with the
  drive until the drive establishes".
- **Computational cost of individual males:** single location, ~200 000 male and
  female mosquitoes for 6 years → **~4 s per simulation**; gene-drive scenarios with
  1.5 M mosquitoes and full human immunity → **~8 min**; spatial runs with
  ~6 000 000 male and female mosquitoes over 150 nodes → **~14 min on 5 compute
  cores**.

## Relevance to MalariaSentinel (Centinela)

- It demonstrates that **individual males in a malaria transmission ABM are
  computationally affordable** — 6 M mosquitoes over 150 km² nodes in 14 minutes —
  provided the male state is small (no swarm geometry, no inheritance of the
  Centinela's kind). This is the strongest counter-argument to "males as individuals
  are too expensive".
- It also shows the *reason* EMOD keeps males: not swarms, but **mating as the
  mechanism of inheritance and of male-mediated gene flow**. If the Centinela's
  decision is taken because the pilot species is *coluzzii* and the model is about
  spatial transmission, the EMOD precedent says: individual males are affordable, but
  they earn their place by doing something (inheritance, SIT competitiveness), not by
  being present.

**Caveats:** EMOD's vector mating is a genetic-inheritance device, not a swarming
model; the paper is about gene drives and insecticide resistance, not about male
behaviour; it does not model swarms, markers, or male movement.

## License

CC BY 4.0 (© 2020 Selvaraj et al; PLoS Computational Biology open access).
Open-access copy: https://pmc.ncbi.nlm.nih.gov/articles/PMC7449459/
