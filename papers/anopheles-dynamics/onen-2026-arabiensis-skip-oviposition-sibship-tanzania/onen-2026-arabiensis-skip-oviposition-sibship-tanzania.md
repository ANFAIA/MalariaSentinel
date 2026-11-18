# Semi-field experiments and sibship analyses reveal larval habitat size preferences and skip oviposition behaviour in female *Anopheles arabiensis*

**Authors:** H Onen, EW Kaindoa, P Akite, JK Kayondo, MA Kaddumukasa, AM Akol, F Tripet
**Journal:** Parasites & Vectors | **Year:** 2026 (19(1), art. 336) | **DOI:** 10.1186/s13071-026-07482-2
**File:** papers/anopheles-dynamics/onen-2026-arabiensis-skip-oviposition-sibship-tanzania.md

---

## Abstract (summary)

Semi-field experiment in south-central Tanzania quantifying **how many breeding
sites a single gravid female uses** (skip oviposition vs. site fidelity), using
**sibship reconstruction** (microsatellite genotyping + Bayesian likelihood, COLONY
software) of the resulting larvae — i.e. individual-level tracking of which mother laid
eggs in which habitat. Twelve artificial larval habitats (alternating small = 30 cm
diameter / 20 L and large = 60 cm diameter / 40 L) were placed in two compartments of a
semi-field mosquito sphere system; **40 wild gravid *An. arabiensis*** were released per
compartment, in quadruplicated experiments. Third-instar larvae were collected, counted
and genotyped.

## Key Results (as used by the model)

- **Skip-oviposition rate: "Sibship analysis showed that 49.2% of females
  skip-oviposited across two to four habitats, while others deposited eggs in only
  one."** So **~49 % of females spread their eggs over 2–4 distinct habitats**; the
  remainder used a **single** habitat.
- **Site fidelity is therefore the minority behaviour** (~51 % single-site) — and even
  that single site is not necessarily the natal site (the females were wild-caught
  adults of unknown origin; no natal-site test was performed).
- **Habitat size preference is inverted:** "Rather than distributing eggs in proportion
  to habitat size, *An. arabiensis* females significantly preferred **smaller**
  habitats." (small = 30 cm/20 L vs large = 60 cm/40 L).
- **Egg-budget trade-off:** "Skip-ovipositing females laid **more eggs overall, but
  fewer eggs per habitat**, and were **more likely to alternate between small and
  large habitats** than to use habitats of the same size, consistent with a potential
  **bet-hedging strategy**."
- Design detail relevant to a spatial model: the 12 habitats were in a **single
  semi-field compartment**; skip-ovipositing here is **oviposition-site diversity at
  the scale of one enclosure**, not dispersal across a landscape.

## Relevance to MalariaSentinel (Centinela)

This is **the only primary measurement in the whole literature reviewed of how many
breeding sites one *Anopheles* female actually uses**, and it is the direct empirical
counterweight to any "female returns to her natal site" assumption. Evidence tier
**[P]** — measured in *A. arabiensis* (a sibling of *A. coluzzii* in the *An. gambiae*
complex, same sub-Saharan African savannah setting), not in *A. coluzzii* itself.

Consequences for the Centinela's oviposition model:

- A **binary "lay here or lay there" oviposition decision is empirically wrong**: the
  measured behaviour is a **split of one egg batch across 2–4 sites in ~half of the
  females**, with the remaining half laying in one site. If the engine keeps a single
  oviposition event per female, it should at minimum be flagged as a simplification.
- The measured rate (**49.2 %**) is the natural candidate for a
  `skip_oviposition_prob` parameter *if* the team decides to model site diversity —
  but note it is **measured for habitat size, not for natal-site fidelity**, so it must
  not be reused as a "leaves the natal site" probability.
- The **bet-hedging** finding (more eggs overall, fewer per site) is a mechanism the
  engine currently lacks: an oviposition decision that trades per-site yield against
  the number of distinct sites used.

**Caveats:** *A. arabiensis*, not *A. coluzzii*; one semi-field system in Tanzania;
artificial containers, not natural larval habitats; the 12 habitats were physically
co-located so the "distance between successive oviposition sites" is not quantified;
the experiment cannot distinguish "skipped the natal site" from "never had a natal
site" (wild-caught gravid females).

## License

CC BY 4.0 (Parasites & Vectors / BMC open access). PMID 42265785.
