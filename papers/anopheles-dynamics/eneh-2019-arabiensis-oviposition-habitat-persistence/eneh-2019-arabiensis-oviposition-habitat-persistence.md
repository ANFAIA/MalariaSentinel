# *Anopheles arabiensis* oviposition site selection in response to habitat persistence and associated physicochemical parameters, bacteria and volatile profiles

**Authors:** LK Eneh, U Fillinger, AK Borg Karlson, G Kuttuva Rajarao, J Lindh
**Journal:** Medical and Veterinary Entomology | **Year:** 2019 (33:709–716) | **DOI:** 10.1111/mve.12336
**File:** papers/anopheles-dynamics/eneh-2019-arabiensis-oviposition-habitat-persistence.md

---

## Abstract (summary)

Field-based choice experiment: wild **gravid *Anopheles arabiensis*** were offered a
set of similar **artificial ponds (0.8 m²)** that had been **aged for different lengths
before opening** — *freshly set up*, **4 days old**, or **17 days old** — so that the
female's preference for a *newly available* breeding site could be measured. The ponds
were characterised for physicochemistry, bacterial community and volatile organic
compounds over three experimental rounds.

## Key Results (as used by the model)

- **Freshness is the cue:** "Fresh ponds contained on average **twice as many
  *Anopheles arabiensis* instar larvae (mean 50, 95 % CI = 29–85)** as the ponds that
  had aged **4 days (mean = 24, 95 % CI = 14–42)** and **17 days (mean = 20, 95 % CI:
  12–34)**."
- **Physicochemical signature of a fresh pond:** "Fresh ponds were associated with a
  **significantly higher turbidity** combined with **higher water temperature, higher
  nitrite levels and a lower pH and chlorophyll level** than the older ponds."
- **Microbial/volatile signature:** "Round by round analyses suggested **bacteria
  communities differed between age groups** and also that **4-heptanone,
  2-ethylhexanal and an isomer of octenal were exclusively detected from the fresh
  ponds**."
- **Author's framing of the gap:** "the factors that guide the aquatic habitat
  selection of gravid females are **poorly understood**."

## Relevance to MalariaSentinel (Centinela)

Evidence tier **[P]** — *A. arabiensis* (sibling of *A. coluzzii*); the study is from
Kenya, not West Africa; **only the abstract was read**.

Why it is in this review despite being an "arousal" paper: it demonstrates that
**oviposition site choice in *Anopheles* is driven by the *current state of the
candidate habitat* (age, turbidity, temperature, nitrite, pH, chlorophyll, bacterial
community, VOC profile)** — a **property of the site**, evaluated at the moment of
choice. There is **no natal-history term anywhere in the model** the authors fit.

Consequences for the Centinela:

- It supports the **design principle** that the oviposition kernel must be a function
  of the **target cell's current aquatic state** — the same conclusion as Mwingira et
  al. 2020 (*A. coluzzii*: conspecific larval stage and density flip the sign of the
  response) and Asmare et al. 2017 (*A. coluzzii*: grass volatile hierarchy). Three
  independent studies, three independent cue classes, one mechanism.
- It gives the Centinela a concrete, measurable vocabulary for the "habitat
  persistence / freshness" axis that the `proxy_habitat_v1` design currently proxies
  with a binary "persistent water" class (`jrc_persistent`) plus a pluvial dynamic
  state. The measured larval yield (fresh ≈ 2× aged) is a **possible calibrated prior
  for a persistence/freshness weight**, if the team wants one.
- It gives **candidate volatile compounds** (4-heptanone, 2-ethylhexanal, an
  octenal isomer) if the engine ever wants a chemical dimension in the oviposition
  kernel.

**Caveats:** not open access; abstract only; *A. arabiensis*; artificial ponds;
the "twice as many larvae" ratio is an **outcome** (larval density in the pond) not a
direct measurement of the female's oviposition *choice* probability; no distances, no
natal-site test.

## License

**Not open access** (Wiley / Medical and Veterinary Entomology). **Only the abstract
was read.** PMID 30168151.
