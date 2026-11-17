# Biting behaviour, spatio-temporal dynamics, and the insecticide resistance status of malaria vectors in different ecological zones in Ghana

**Authors:** Osei K. Akuoko, Shittu B. Dhikrullahi, Isaac A. Hinne, Abdul R. Mohammed, Christopher M. Owusu-Asenso, Sylvester Coleman, Samuel K. Dadzie, Rosina Kyerematen, et al.
**Journal:** Parasites & Vectors | **Year:** 2024 | **DOI:** 10.1186/s13071-023-06065-9
**File:** papers/anopheles-dynamics/akuoko-2024-biting-behaviour-ghana.md

---

## Abstract (summary)

The study characterised the spatio-temporal dynamics, biting behaviour and
insecticide-resistance status of malaria vectors across different ecological
zones in Ghana, in a context of high LLIN/IRS coverage and widespread
pyrethroid resistance. Hourly human-landing and indoor/outdoor collections
were used to describe when and where the main vectors bite.

## Key Results (as used by the model)

- **Species composition of the *An. gambiae* complex** (PCR-RFLP on a random
  subsample of 1,670 *An. gambiae* s.l. from all study sites): *An. coluzzii*
  **55.9 % (935/1670)**, *An. gambiae* s.s. **39.5 % (659/1670)**,
  *An. arabiensis* **2.3 % (39/1670)**, *An. melas* **2.2 % (37/1670)**. This
  is the evidence for choosing *A. coluzzii* as the pilot species.
- **Biting-time bins used by the study** (human landing catch, hourly,
  18:00–06:00): early evening **EE = 18:00–22:00**, late evening
  **LE = 22:00–04:00**, early morning **EM = 04:00–06:00**.
- **Hourly profile of *An. coluzzii*** (n = 935): **LE 48.0 % (449/935)**,
  **EM 26.5 % (248/935)**, **EE 25.5 % (238/935)**.
- **Hourly profile of *An. gambiae* s.l. (aggregate)** (n = 31,055): LE 66.6 %,
  EM 20.1 %, EE 13.3 % — i.e. *coluzzii* bites **earlier and has a much larger
  early-morning component** than the complex aggregate, which is what the
  per-species `activity_weights` rows must encode.
- **Derivation used by the engine** (engine phases: DAY 06:00–18:00,
  EVENING 18:00–21:00, NIGHT 21:00–05:00, DAWN 05:00–06:00), assuming a
  uniform rate inside each study bin:
  EE = 25.5 %/4 h = 6.375 %/h; LE = 48.0 %/6 h = 8.0 %/h; EM = 26.5 %/2 h =
  13.25 %/h ⇒ EVENING = 3 h x 6.375 = **19.1 %**; NIGHT = 1 h EE + 6 h LE +
  1 h EM = **67.6 %**; DAWN = 1 h EM = **13.3 %**; DAY = **not measured**
  (collections started at 18:00) ⇒ normalised row
  **[0.00, 0.191, 0.676, 0.133]**.
- It documents differences between ecological zones and vector species, which
  is why the YAML keeps one activity row per species.

## Relevance to MalariaSentinel (Centinela)

Source for the phase-level `activity_weights` in `model_constants.yaml`.
The model does not reproduce the paper's entomological rates; it only uses the
relative hourly activity shape. The current `species.coluzzii.activity_weights`
row `[0.02, 0.10, 0.80, 0.08]` does **not** follow from these numbers (it is
close to the *gambiae* s.l. aggregate, not to the *coluzzii* profile) and
should be replaced by the derived row above, with DAY kept at 0 and flagged as
unmeasured.

Numbers re-verified against the article's own full text (Europe PMC
PMC10775458) on 2026-11.

## License

CC-BY 4.0 (BMC Open Access).
