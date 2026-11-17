# Male motion coordination in anopheline mating swarms

**Authors:** Shishika D, Manoukis NC, Butail S, Paley DA
**Journal:** Scientific Reports | **Year:** 2014 (4:6318) | **DOI:** 10.1038/srep06318
**File:** papers/anopheles-dynamics/shishika-2014-male-motion-coordination-anopheline-swarms.md

---

## Abstract (summary)

The first quantitative analysis of **male–male interaction** in anopheline mating
swarms: 8 swarms of *Anopheles gambiae* and 3 swarms of *Anopheles coluzzii* filmed in
the field in Donéguébougou, Mali (2010–2011) are analysed with a unit-velocity
cross-correlation of flight direction to build **interaction graphs** between
mosquitoes. This paper is the historical source of the "boids" reading of anopheline
swarms (cited as such by later authors).

## Key Results (as used by the model)

- **Field data:** 8 *A. gambiae* swarms and 3 *A. coluzzii* swarms, Donéguébougou
  (Mali); **~450 000 data points** from the 8 *A. gambiae* swarms.
- **Method:** cross-correlation of flight direction with a 10-frame lag window
  (chosen from the ≈3 Hz frequency at which mosquitoes change direction);
  pairs whose correlation exceeds a threshold of **0.75** (Bayes-rule intersection of
  the "no interaction" simulation with the real male–female coupling distribution) are
  labelled **interacting**; a non-zero optimal lag gives the *following* direction.
- **Real swarms show an elevated probability of high correlation values** compared with
  a simulation of a swarming model **without** interaction (although the
  no-interaction simulation already reproduces much of the real correlation
  distribution); the male–female coupling flight shows high probability at **zero lag**.
- **Conceptual framing:** "Crepuscular swarms of *An. gambiae* and *An. coluzzii* […]
  can be described as **three-dimensional leks** with characteristics of **scramble
  competition** by numerous males for a few females."
- The interaction network is **intermittent and time-varying**: periods of parallel
  flight occur between otherwise uncorrelated individuals.

## Relevance to MalariaSentinel (Centinela)

Evidence tier **[P]** (field, Mali, mixed species; *A. coluzzii* swarms are only 3 of
the 11).

This is the paper that the **"boids" claim** in the malaria-vector literature rests
on, and the Centinela must cite it *together with*
`cribellier-2026-coluzzii-swarm-behavioural-rules-agent-based-model.md`, which
re-analyses the same class of data with a stricter model and concludes that the
apparent long-range interactions are **by-products of synchronised responses to
environmental cues**, with the only genuine interaction being collision avoidance at
**< 2.5 body lengths**.

Two facts from this paper survive the reconciliation and are usable:
1. the swarm is a **lek with scramble competition** — many males, few females, and
   pairing is decided largely by chance (consistent with the ~7 % of males pairing per
   night, Diabaté 2011);
2. the male–male interaction that does exist is **intermittent and short-ranged** —
   it does not require a spatial interaction kernel at the scale of the Centinela's
   cells.

**Caveats:** the interaction threshold (0.75) is a modelling choice; the paper analyses
field swarms but its conclusion is correlational; the 3 *A. coluzzii* swarms are a
small subset; it does not quantify female attendance.

## License

CC BY-NC-ND 4.0 (© 2014 Shishika et al; Scientific Reports — non-commercial,
no-derivatives reuse only).
Open-access copy: https://pmc.ncbi.nlm.nih.gov/articles/PMC4161964/
