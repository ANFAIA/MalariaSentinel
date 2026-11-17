# Frequency of multiple blood meals taken in a single gonotrophic cycle by *Anopheles arabiensis* mosquitoes in Macha, Zambia

**Authors:** Laura C. Norris, Chris M. Fornadel, Wei-Chen Hung, Francisco J. Pineda, Don E. Norris
**Journal:** The American Journal of Tropical Medicine and Hygiene | **Year:** 2010 | **DOI:** 10.4269/ajtmh.2010.09-0296
**File:** papers/anopheles-dynamics/norris-2010-multiple-blood-meals-arabiensis-zambia.md

---

## Abstract (summary)

Field study in four village areas of southern Zambia, over two seasons. Human blood meals
were identified by PCR at four microsatellite loci; mosquitoes carrying **≥3 alleles at any
locus** were scored as having taken multiple blood meals (the "three-allele method").
The aim was to obtain an unbiased estimate of multiple human blood meals per gonotrophic
cycle, because EIR calculations usually assume one meal per cycle.

## Key Results (as used by the model)

- "the overall frequency of multiple blood meals was **18.9 %**, which was higher than
  rates reported for *An. gambiae* in Kenya and *An. funestus* in Tanzania."
- "Computer simulations showed that the **three-allele method underestimates the true
  multiple blood meal proportion by 3–5 %**." → the field rate is a lower bound; add
  3–5 % when converting to a model parameter.
- "Although *P. falciparum* infection status was not shown to influence the frequency of
  multiple blood feeding, the **high multiple feeding rate found in this study increased
  predicted malaria risk by increasing EIR**."
- Field setting is *An. arabiensis* (a member of the *An. gambiae* complex) — the
  sibling of the *coluzzii* row used by the engine; **not** *coluzzii* itself.

## Relevance to MalariaSentinel (Centinela)

Provides the field-anchored magnitude for `meals_per_cycle_mean` / the probability that a
female takes more than one meal in a cycle: roughly one in five females takes a second
human meal in the same cycle, i.e. a per-meal hazard of second-meal acquisition of about
0.19–0.24 divided by the number of cycles. It also documents the epidemiological
consequence (EIR underestimated when one meal per cycle is assumed), which is exactly the
transmission multiplier the redesign introduces.

Caveats: *An. arabiensis* (proxy for *coluzzii*/*gambiae* s.l.), Zambia (not Ghana);
the three-allele method detects only *human* multi-host meals and only when the hosts
differ genetically; the paper does not report the volume of blood ingested, so it cannot
constrain `blood_meal_size_ul`.

## License

© American Society of Tropical Medicine and Hygiene (not open access; abstract read via
Europe PMC). Fair use for academic research.
