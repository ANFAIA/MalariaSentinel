# Behavioral heterogeneity in host seeking and post-feeding suppression among disease vector mosquitoes

**Authors:** Takuya Uehara, Linhan Dong, Laura B. Duvall
**Journal:** Communications Biology | **Year:** 2026 | **Volume:** 9:1 | **Article no.:** 3495 | **DOI:** 10.1038/s42003-026-09987-z
**Open access URL:** https://pmc.ncbi.nlm.nih.gov/articles/PMC13234290/ (preprint: bioRxiv 10.1101/2025.06.18.660345)
**File:** papers/anopheles-dynamics/uehara-2026-post-feeding-host-seeking-suppression.md

---

## Abstract (summary)

Automated (machine-learning) video tracking of six mosquito species — *Aedes
aegypti*, *Aedes albopictus*, *Anopheles gambiae*, *Anopheles stephensi*, *Culex
tarsalis*, *Culex quinquefasciatus* — before and after a blood meal, with host
cues (CO₂ + human odour) delivered at each species' preferred time of day.
Measures the **onset and duration of post-blood-meal host-seeking
suppression** — the physiological state that the Centinela must represent when
a female becomes `BLOOD_FED` / `RESTING` / `EGG_MATURING`.

## Key Results (as used by the model)

- Blood meals repleted females to ≈ double body weight in all species; behaviour
  was recorded at 24, 48 and 72 h post-blood-meal.
- "*Aedes aegypti* females showed an overall **suppression of movement and
  probing with minimal levels at 24 hours** that gradually recover to
  intermediate levels at 72 hours".
- "*Aedes albopictus* females displayed a recovery pattern with levels of
  movement and probing reaching levels comparable to pre-feeding baseline by 72
  hours".
- "*Anopheles gambiae* females showed **prolonged suppression with low levels of
  movement and probing observed across all timepoints up to 72 hours**
  post-feeding".
- "*Anopheles stephensi* females followed a **recovery of probing and movement
  at 72 hours comparable to the non-fed state**".
- "*Culex tarsalis* females exhibited a **delayed suppression profile**, with
  moderate movement and probing at 24 hours post-feeding, followed by a decline
  at 48 and 72 hours" (i.e. abdominal distension alone did not suppress host
  seeking early).
- "*Culex quinquefasciatus* females showed a significant reduction in movement
  and probing 24 hours after feeding, which was followed by full recovery of
  movement by 72 hours, though probing remained at intermediate levels".
- "Overall, at **24 hours post-feeding, all species except for *Culex tarsalis*
  displayed maximal suppression** of both movement and probing … By **72 hours,
  several species showed partial or full recovery**."
- Mechanistic framing used by the authors (Introduction): "After consuming a
  full blood meal, females enter a transient period of host-seeking
  suppression, during which their responsiveness to host cues is reduced until
  eggs are laid"; "the act of blood feeding can be experimentally uncoupled
  from the nutritional content of the blood … **ATP as a key phagostimulant**
  that triggers engorgement"; the suppression "is thought to involve
  mechanosensory and reproductive signals".
- On the first-cycle multi-meal behaviour: "In *Anopheles gambiae*, some females
  undergo a **'pre-gravid' phase, requiring two blood meals on different nights
  to complete the first gonotrophic cycle**" (citing Gillies 1954).
- On the duration of suppression: "A comparative study of several *Aedes* and
  *Anopheles* species found that *Anopheles gambiae* females **resumed host
  seeking within 24 hours after a blood meal, prior to oviposition**, unlike
  *Aedes aegypti* and *Aedes albopictus* females"; "other research suggests
  that host-seeking behavior in blood-fed *Anopheles gambiae* is **suppressed
  for approximately 40 hours post feeding, until oocytes mature or eggs are
  laid**".
- Hormonal framing: "ecdysone release initiated after a blood meal suppresses
  host seeking in *Anopheles freeborni*" (Beach 1979); humoral inhibition of
  host seeking during oocyte maturation in *A. aegypti* (Klowden & Lea 1979).

## Relevance to MalariaSentinel (Centinela)

- Direct measured justification for a **postprandial refractory state** in the
  female state machine, and for its **species-specific duration**: the engine
  currently jumps from `BLOOD_FED` to `RESTING` (0.5 d) and then to
  `EGG_MATURING`; the evidence says the *behavioural* host-seeking refractory
  window is **≥ 24 h for every species tested**, **≥ 72 h for *An. gambiae***,
  and ~72 h for *A. stephensi*, i.e. the female is **not** host-seeking for
  most of the 2–3 day gonotrophic cycle. This is the physiological justification
  for the `PRE_GRAVID` / `RESTING` / `EGG_MATURING` ordering and for a
  "host-seeking gate" that is closed while the female digests the meal and
  matures eggs.
- The *Culex tarsalis* result is a warning against a purely mechanical
  "full abdomen ⇒ no host seeking" rule: distension alone did not suppress
  host seeking at 24 h, so the gate must be physiological (ovarian/ecdysone
  state), not geometric.
- Caveats: laboratory colonies (BEI resources), host-cue assay (CO₂ + human
  odour) in a small arena, and the "suppression" is measured as movement and
  probing under a host cue — a proxy for the field host-seeking rate. No
  *An. coluzzii* was tested; *An. gambiae* is the closest measured proxy.

## License

Creative Commons Attribution-NonCommercial-NoDerivatives 4.0
(CC BY-NC-ND 4.0) — https://creativecommons.org/licenses/by-nc-nd/4.0/
