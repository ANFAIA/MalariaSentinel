# The influence of larval stage and density on oviposition site-selection behavior of the Afrotropical malaria mosquito *Anopheles coluzzii*

**Authors:** VS Mwingira, J Spitzen, LEG Mboera, JL Torres-Estrada, W Takken
**Journal:** Journal of Medical Entomology | **Year:** 2020 (57(6):1909–1915) | **DOI:** 10.1093/jme/tjz172
**File:** papers/anopheles-dynamics/mwingira-2020-larval-stage-density-oviposition-coluzzii.md

---

## Abstract (summary)

Dual-choice and no-choice laboratory bioassays with **gravid *Anopheles coluzzii***
(Kisumu strain, Kenya) to determine how the **presence, developmental stage and density
of conspecific larvae** in an oviposition cup modify the female's oviposition response.
Treatments: (1) cups containing conspecific larvae of different developmental stages,
(2) cups containing **larvae-conditioned water (LCW)**, (3) cups where the **visual cues
of conspecific larvae were absent** (larvae hidden from view).

## Key Results (as used by the model)

- **Stage-dependent sign:** "**Early-stage conspecific larvae had a positive effect on
  the oviposition response. By contrast, late stages of conspecific larvae had a
  negative effect.**"
- **Density dependence:** "**Oviposition choice was dependent on larval density.**"
- **The cue is olfactory, not visual:** "in oviposition cups where **larvae were hidden
  from view, late-stage larvae had a significant negative effect** on oviposition
  suggesting the involvement of **olfactory cues**."
- **The signal is in vivo, not water-soluble:** "**LCW had no effect on oviposition
  response**, indicating involvement of chemicals produced by larvae **in vivo**."
- **Author's conclusion:** "the presence of larvae in a breeding site affects the
  oviposition response depending on the development stage of the larvae. These
  responses appear to be mediated by **olfactory cues emitted by the larval habitat
  containing live larvae**, resulting in the enhanced reproductive fitness of the
  females."

## Relevance to MalariaSentinel (Centinela)

**The only measured, *A. coluzzii*-specific oviposition-site-selection behaviour
paper** in this review. Evidence tier **[M]** — the species matches the Centinela's
target exactly.

What it licenses:

- The Centinela's oviposition decision must be a function of the **state of the
  aquatic cohort at the target cell**, not of the mosquito's origin. Specifically, the
  engine already tracks per-cohort larval development stage and density (aquatic
  cohort bank, `larva_mortality_density`, developmental staging) — and those two
  variables are exactly the ones this paper identifies as the oviposition cue. This
  is the mechanistic justification for **coupling oviposition to the target cell's
  cohort state** rather than to anything the adult carries.
- **Early larvae attract, late larvae repel.** A model that only rewards "water is
  present" (as a naive habitat-availability proxy does) will place gravid females
  into cells whose cohort is about to pupate — precisely the wrong site. The engine
  needs the **stage sign flip**.
- **Density matters**, so a single scalar "habitat suitability" per cell is
  insufficient; the oviposition response must see the local cohort density.
- **Crucially for the field under review:** the paper identifies *no* natal-site
  component whatsoever. Every effect is mediated by the **current** contents of the
  candidate site. Nothing here supports storing an adult-side origin coordinate.

**Caveats:** laboratory dual/no-choice assays, one laboratory colony (*Kisumu* strain,
Kenya) — behaviour of a colonised strain in a cage is not field behaviour; no
distances, no spatial scale, no field semi-field validation; "late stage" and "early
stage" are not resolved to L2/L3/L4 in the abstract (the full text was not read for
this extract — only the abstract and publisher metadata).

## License

CC BY-NC (Oxford University Press / Journal of Medical Entomology). PMID 31630193.
