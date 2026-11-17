# Comparison of the functional features of the pump organs of *Anopheles sinensis* and *Aedes togoi*

**Authors:** Yu-Ren Ha, Seung-Chan Lee, Seung-Jin Seo, Jae-Yun Ryu, Dae-Kyu Lee, Seung-Jae Lee
**Journal:** Scientific Reports | **Year:** 2015 | **DOI:** 10.1038/srep15148
**File:** papers/anopheles-dynamics/ha-2015-feeding-pump-organs-anopheles-sinensis-aedes-togoi.md

---

## Abstract (summary)

Synchrotron X-ray micro-CT reconstruction of the head of female *Aedes togoi* and
*Anopheles sinensis*, plus 2D X-ray micro-imaging of the pumping organs, to compare the
anatomy and the working cycle of the cibarial and pharyngeal pumps. Provides the
*mechanical* basis for the genus difference in how much blood is taken per sip.

## Key Results (as used by the model)

- "*An. sinensis*, a malarial vector mosquito, had a **larger feeding pump volume** than
  *Ae. togoi* in the static or resting position."
- Cibarial pump (CP) volume: "**4.77 ± 1.29 µm³**" for *Ae. togoi* vs
  "**38.94 ± 9.45 µm³**" for *An. sinensis* (≈8× larger).
- Pharyngeal pump (PP) volume: "**13.54 ± 2.99 µm³**" for *Ae. togoi* vs
  "**78.74 ± 37.52 µm³**" for *An. sinensis* (≈6× larger).
- "the volumes of the C-P in both mosquito species were comparable" (the connecting
  chamber is similar) → the difference is in the pump chambers themselves.
- "*Ae. togoi* had a **higher feeding frequency and expansion ratio** than *An. sinensis*";
  the two species therefore use different feeding strategies (many small strokes vs fewer
  larger ones).
- "the volume of the feeding pumps in the **expansion state** is not noticeably different
  in either mosquito species" → the anatomical advantage is the *resting* (suction)
  volume, which is what sets the per-sip volume `v`.

## Relevance to MalariaSentinel (Centinela)

Mechanistic justification for the genus asymmetry that the redesign has to respect:
*Anopheles* takes **larger sips** (bigger cibarial/pharyngeal pump volume), while *Aedes*
takes **more frequent, smaller sips**. This is the anatomical basis for the
`V_total = T·f·v` decomposition used in `konopka-2026-…` and for keeping
`blood_meal_size_ul` species-specific.

Caveats: *An. sinensis* is an Asian vector (proxy for the *Anopheles* genus, **not** a
*gambiae* s.l. species) and *Ae. togoi* is a Pacific species; measurements are on
reared mosquitoes. µm³ volumes are pump volumes, not blood volumes, and no blood volume
is reported in this paper.

## License

CC-BY 4.0 (Scientific Reports / Nature Portfolio open access).
