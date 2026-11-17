# Experimental evidence of male-male interaction in laboratory swarms of *Anopheles gambiae* mosquitoes

**Authors:** Iacomelli G, Lombardi M, Parisi L, Fiorini M, Grucci F, Lavorgna A, Ligato M, Zarcone G, Peirce MJ, Melillo S, Spaccapelo R
**Journal:** Scientific Reports | **Year:** 2026 | **DOI:** 10.1038/s41598-026-59111-8
**File:** papers/anopheles-dynamics/iacomelli-2026-male-male-interaction-laboratory-swarms.md

---

## Abstract (summary)

Laboratory swarms of *Anopheles gambiae* (G3 strain) recorded with three synchronised
high-speed cameras and 3-D trajectory reconstruction (GReTA), testing explicitly
whether the swarm is a **collective** (inter-male interaction) or the product of
individual responses to the marker. 30 swarms of 80–400 individuals (plus 41 smaller
swarms of 10–80 in the SI) are analysed for spatial "localisation" and for
**speed synchronisation** between males.

## Key Results (as used by the model)

- **Swarm size in the laboratory:** 80–400 individuals in the main dataset (41 further
  swarms of 10–80 in SI); two campaigns, 170 fps / ~15 s (2020–2021) and 80 fps /
  ~30 s (2024).
- **Each mosquito loops around its own characteristic position.** Every individual
  performs consecutive horizontal loops around a position slightly different from
  every other member's; it therefore samples only a small part of the swarm volume.
- **"Speed localisation":** each mosquito flies at its own characteristic speed, the
  difference from the group mean is larger than statistical fluctuation, is
  **independent of its position in the swarm**, and **persists over time**; each
  individual samples only a narrow band of the swarm's speed distribution.
- **The interaction is in the SPEED domain, not the velocity domain:** the data show
  strong correlation in **speed**, but **no significant correlation in velocity
  (direction)**. The authors contrast this with bird flocks, fish schools and
  chironomid midge swarms, where the correlation is primarily in the velocity domain
  and accompanied by speed correlation.
- **Consequence for modelling, stated by the authors:** "Standard models assume an
  interaction acting on the velocity and homogeneity among individuals […] The two key
  features we identify—localization and speed correlation—**require the design of new
  models for swarm dynamics**."
- **Caveat stated by the authors:** laboratory conditions may inhibit interaction
  behaviours that occur in the field (the midge analogue behaves differently in
  laboratory vs field), and the result still has to be benchmarked against wild-type,
  field-derived *Anopheles*.

## Relevance to MalariaSentinel (Centinela)

Evidence tier **[P]** for the numbers (*A. gambiae* G3 strain, laboratory), **[EP]** for
the modelling implication.

This paper is the **counterweight** to
`cribellier-2026-coluzzii-swarm-behavioural-rules-agent-based-model.md` and it must be
cited as such: it provides *experimental* evidence of **male–male interaction** in
mosquito swarms, but the interaction it measures is **speed synchronisation**, not
attraction/alignment, and it is measured in laboratory cages. Its modelling conclusion
is stated by its own authors: the classical swarm models (which assume homogeneous
individuals interacting through velocity) are **inadequate** for mosquitoes.

For the Centinela this matters in a specific way: it means that *if* the project ever
models males as individuals, the interaction rule it needs is **not** the boids rule
(attraction + alignment + separation) but something that preserves **per-male speed
heterogeneity and per-male position**. It does **not**, however, change the aggregate
option, because the aggregate never represented individuals: the sufficient statistic
for a swarm is its (site, time, size) triple, whether or not the individuals inside it
are homogeneous.

**Caveats:** laboratory-adapted G3 strain (not wild, not *coluzzii*); swarms up to 400
individuals are far larger than the median field swarm; the authors explicitly flag the
laboratory-vs-field generalisation as open; the study is published in 2026 and has
**1 citation** (no independent replication yet).

## License

CC BY 4.0 (© 2026 Iacomelli et al; Scientific Reports open access).
Open-access copy: https://pmc.ncbi.nlm.nih.gov/articles/PMC13727671/
