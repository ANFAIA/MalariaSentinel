# Multimodal synergisms in host stimuli drive landing response in malaria mosquitoes

**Authors:** Manuela Carnaghi, S. Belmain, R. Hopkins, F. Hawkes
**Journal:** Scientific Reports | **Year:** 2021 (11:7379) | **DOI:** 10.1038/s41598-021-86772-4
**File:** papers/anopheles-dynamics/carnaghi-2021-coluzzii-multimodal-landing-synergy.md
**Copy read:** PMC full text — https://pmc.ncbi.nlm.nih.gov/articles/PMC8016827/

---

## Abstract (summary)

Step-wise multimodal assays quantifying the individual and combined effect of
**visual, olfactory and thermal** host-associated stimuli on the **landing**
response of female ***Anopheles coluzzii***.

## Key Results (as used by the model)

Mean landing rate per assay (mosquitoes landing; ± SEM) from the Tukey
contrast table (Table 1). **O** = host odour, **N** = no odour,
**T** = thermal target, **B** = visual (black) target.

| Treatment | Mean landing (± SEM) |
|---|---|
| O + T + 25 °C (odour, no heat) | **4.8 ± 0.88** |
| N + T + 25 °C (neither) | 0.2 ± 0.13 |
| N + B + 25 °C (visual only) | 2.0 ± 0.82 |
| N + T + 35 °C (heat only) | **0.4 ± 0.16** |
| N + T + 45 °C (heat only) | **1.1 ± 0.59** |
| O + T + 35 °C (odour + heat) | **13.3 ± 1.41** |
| O + T + 45 °C (odour + heat) | 11.8 ± 1.24 |
| O + B + 25 °C (odour + visual) | 10.4 ± 1.77 |
| O + B + T + 35 °C (odour + visual + heat) | **15.9 ± 1.05** |
| O + B + T + 45 °C | 15.2 ± 1.00 |

Key contrasts (all P < 0.001 unless stated):
* Odour vs no odour at 25 °C: 4.8 vs 0.2 (z = 4.37).
* Odour vs no odour **in the presence of heat at 35 °C**: 13.3 vs 0.4
  (z = 6.79); at 45 °C: 11.8 vs 1.1 (z = 7.21).
* Odour vs no odour **in the presence of the visual cue**: 10.4 vs 2.0
  (z = 6.30).
* Heat vs no heat **in the presence of odour**: 4.8 (25 °C) → 13.3 (35 °C),
  z = 5.64; and 4.8 → 11.8 (45 °C), z = 4.92.
* **Visual vs thermal, in the presence of odour: no significant difference**
  (15.9 vs 13.3, z = −1.18, P = 0.99; 15.2 vs 11.8, z = −1.69, P = 0.84).
* **Heat alone does nothing** (0.4–1.1 landings): N + T + 25 °C vs 35 °C
  z = 0.80, P = 1; N + T + 25 °C vs 45 °C z = 2.20, P = 0.49.

The authors' own framing: "as thermal cues are hypothesised to only be
detectable within a close range from the host, and as **heat alone might not
effectively signal to mosquitoes the presence of a host**, where an inanimate
object heated by the sun may reach host-like temperatures, it might be more
advantageous for [the mosquito] to [rely on other cues]".

## Relevance to MalariaSentinel (Centinela)

This is the ***A. coluzzii* [M]** evidence for the **landing gate** of the
sensory cascade:

* `landing_requires_odour` — heat alone yields ~0.4–1.1 landings vs 13.3–15.9
  with odour; odour alone yields 4.8. **A thermal term without an olfactory
  term must not produce landings.** **[M]**
* `landing_probability` — the odour × heat interaction is the largest effect
  in the table (0.4 → 13.3, a > 30× increase), which justifies modelling
  landing as a **multiplicative (synergistic) gate** rather than a sum of
  independent probabilities. **[M]**
* `visual_or_thermal_sufficient_with_odour` — with odour present, visual and
  thermal cues are statistically interchangeable (P = 0.99 / 0.84): the
  model only needs *one* of them, not both. **[M]**

Target temperatures in this study are **25 / 35 / 45 °C** (surface), not the
34–35 °C convective core quoted elsewhere in the literature.

## License

CC BY 4.0 (Scientific Reports / Nature open access).
