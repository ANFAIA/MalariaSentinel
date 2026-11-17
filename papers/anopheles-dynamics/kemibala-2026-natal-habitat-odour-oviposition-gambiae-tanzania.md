# Effects of natal habitat odour on oviposition site selection by *Anopheles gambiae* sensu lato

**Authors:** E E Kemibala, M Shayo, IL Swai, BH Kilagwile, DH Abdiel, A Munishi, N Adam, J Rutayagi, R Bofu, JT Mbise, F Lyimo, S O Laizer, T Dekker
**Journal:** Research Square preprint | **Year:** 2026 (posted 5 October 2026) | **DOI:** 10.21203/rs.3.rs-10515996/v1
**File:** papers/anopheles-dynamics/kemibala-2026-natal-habitat-odour-oviposition-gambiae-tanzania.md

---

## Abstract (summary)

Direct test of the **natal habitat preference induction** (NHPI) hypothesis in the
*An. gambiae* complex: laboratory colonies of *Anopheles gambiae* s.s. and *Anopheles
arabiensis* were reared **separately** in water from two natural breeding habitats in
Muheza District, Tanzania (Genge, Kilimantengwe) and in dechlorinated tap water. Gravid
females from each rearing group were then offered **three oviposition substrates
simultaneously** (the three water types), in laboratory cage bioassays and in semi-field
"mosquito sphere" experiments. Oviposition preference = proportion of eggs deposited in
each substrate.

## Key Results (as used by the model)

- **Sample size:** "A total of **1,080 gravid mosquitoes** were evaluated under
  laboratory conditions and **3,600 under semi-field conditions**."
- **Direction of the effect:** "Both *An. gambiae* s.s. and *An. arabiensis* demonstrated
  a tendency to oviposit **preferentially in water resembling their natal habitat**."
  "exposure to natal habitat odours during larval development influences subsequent
  oviposition site selection in adult mosquitoes."
- **Quantified proportions (laboratory assays, *An. arabiensis* reared in Genge water,
  483 eggs total):** "the highest proportion **37.5 % (n = 181)** were oviposit in
  **Genge water**, 113 (23.4 %) in Kilimantengwe water, 102 (21.1 %) in laboratory
  rearing water, and 87 (18.0 %) in laboratory clean water."
- ***An. arabiensis* reared in Kilimantengwe water:** all preferred Kilimantengwe
  substrate water (**31.6 %** for *A. gambiae* s.s., **34.5 %** for *A. arabiensis*).
- ***An. gambiae* s.s. reared in Genge water (303 eggs total):** **86 (28.4 %)** in
  Kilimantengwe water, **41 (13.5 %)** in Genge water, **98 (32.3 %)** in laboratory
  rearing water, **78 (25.7 %)** in clean laboratory water — i.e. *A. gambiae* s.s.
  did **not** show a natal-water preference when reared in Genge.
- **Significance (two-sample tests of proportions, 95 % CI):** *A. arabiensis* reared in
  Genge preferred Genge over Kilimantengwe (**p = 0.012**), laboratory rearing water
  (**p = 0.004**) and clean laboratory water (**p = 0.001**); reared in Kilimantengwe
  it preferred it over Genge (**p = 0.020**), lab water (**p = 0.025**) and clean lab
  water (**p = 0.032**); **reared in laboratory water it showed no significant
  preference at all**.
- **Semi-field replication was weaker:** "Semi-field experiments showed similar
  behavioural trends, although the **responses were less consistent because of increased
  environmental variability**." Statistical analysis in the semi-field arm used
  Scheirer–Ray–Hare + Kruskal–Wallis + Dunn (Bonferroni) on non-normal egg counts.

## Relevance to MalariaSentinel (Centinela)

This is **the single most on-point paper in the entire literature for the question
"do *Anopheles* females return to oviposit where they were born?"** — and its answer
is: **there is a measurable natal-habitat *preference*, but it is a preference for the
*odour* of the natal water, mediated by larval olfactory learning, not a navigational
return to the natal coordinates.** Evidence tier **[P]**: the species tested are *A.
gambiae* s.s. and *A. arabiensis* (siblings of *A. coluzzii* in the same complex), in
Tanzania, **not** *A. coluzzii*, and the paper is a **non-peer-reviewed preprint**.

What the Centinela may legitimately take from it:

- A **mechanism** (larval olfactory imprinting → adult preference for natal-habitat
  odours) that is independent of the adult having to *remember a coordinate*. It
  supports an **odour/vegetation-cue-driven** oviposition kernel, which is what the
  engine already implements (`oviposition.scale_m`, habitat affinity weights, the
  Dynamic-World / JRC habitat proxies), and it does **not** support a `home_x/home_y`
  coordinate-memory mechanism.
- The effect size is **modest and conditional**: the natal substrate took only
  **31.6–37.5 %** of eggs, it required the female to have been reared in a *natural*
  habitat (reared in lab water → no preference at all), it was **not** present in *A.
  gambiae* s.s. in one of the three rearing treatments, and it **attenuated in the
  semi-field**. A model parameter built on it must therefore be a *weak, optional*
  bias, not a dominant attraction.
- A **direct warning against the field under review**: the paper's own framing is
  "natal habitat **odour**", i.e. a **cue**, not a place.

**Caveats:** preprint (not peer reviewed); laboratory-reared colonies of the two
sibling species; the assay offers three *water types* side by side, so it cannot
measure any distance, radius, or return probability; eggs were attributed to substrate,
never to a natal site; the semi-field arm (the more realistic one) was the *less*
consistent.

## License

CC BY 4.0 (Research Square preprint). Full text read from the author PDF
(https://www.researchsquare.com/article/rs-10515996/latest.pdf).
