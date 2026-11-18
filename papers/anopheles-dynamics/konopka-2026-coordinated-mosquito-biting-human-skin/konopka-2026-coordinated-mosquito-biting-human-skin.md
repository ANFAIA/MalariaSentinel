# Coordinated mosquito biting dynamics at the human skin interface

**Authors:** James K. Konopka, Dhananjay Poinapen, Sangeeta S. Chitnis, Chase M. Morrow, Georgia M. Card, Craig J. Potter
**Journal:** Science Advances | **Year:** 2026 | **DOI:** 10.1126/sciadv.aec2023
**File:** papers/anopheles-dynamics/konopka-2026-coordinated-mosquito-biting-human-skin.md

---

## Abstract (summary)

High-speed videography, deep-learning tracking and electrophysiology of biting by
*Anopheles coluzzii* (the West African malaria vector; the sibling species of *An. gambiae*
used by the same engine) on human skin in real time. Five below-skin sub-behaviours are
resolved: piercing, vessel searching, blood ingestion, retraction, withdrawal. Comparative
analysis against *Aedes aegypti* shows genus-specific biting strategies.

## Key Results (as used by the model)

- **Blood-meal volume: "…resulting in Anopheles acquiring 20 to 60 % larger blood meal
  (∼3 to 4 μl versus ∼2.5 μl) compared to Aedes during the same feeding period."**
  The ~3–4 µL figure is the value attributed to *Anopheles*; ~2.5 µL is the *Aedes*
  value (which coincides with the Klowden & Lea 1978 host-seeking threshold).
  → `blood_meal_size_ul` for a *coluzzii*-matched engine.
- "Under natural conditions, **Anopheles females usually feed to repletion (i.e., engorge
  fully) on a single host**, while Aedes females can take partial blood meals from multiple
  hosts." → the direction of the bias in our model must be conservative: *Anopheles* are
  more likely to complete a meal in one bite than to be interrupted.
- Median time for *An. coluzzii* to obtain a blood meal was **160 s**, of which **128 s was
  blood ingestion** and 21 s vessel searching.
- *Anopheles* blood-fed on a mouse host at reduced frequency (~50 %) compared with human
  skin (~100 %), and engorgement was slower on mouse (median ~240 s) than on human
  (median ~116 s).
- Mechanistic explanation for the larger *Anopheles* meal: larger cibarial and pharyngeal
  pumps and a wider proboscis (see `ha-2015-…` and `lee-2016-…` extracts), i.e. larger
  per-sip volume `v` at equal feeding duration and sipping frequency `f`
  (`V_total = T·f·v`).

## Relevance to MalariaSentinel (Centinela)

Species-matched (coluzzii) and on human skin, but laboratory-cage and human-volunteer
setting — not a Ghana field population. The paper itself flags that the µL values are
*not measured in this study* (they are attributed to ref. 41, Choumet et al. 2012) and
states that "experiments measuring blood meals taken from the same host are needed"; the
value should therefore be treated as the best available literature estimate rather than a
measurement from this paper. Note the internal tension with `lee-2016-…` (Aedes togoi
siphons faster than *An. sinensis*); both are recorded here rather than reconciled.

## License

CC-BY-NC 4.0 (Science Advances / AAAS open access).
