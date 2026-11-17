# Mosquito sound communication: are male swarms loud enough to attract females?

**Authors:** Feugère L, Gibson G, Manoukis NC, Roux O
**Journal:** Journal of the Royal Society Interface | **Year:** 2021 (18(177):20210121) | **DOI:** 10.1098/rsif.2021.0121
**File:** papers/anopheles-dynamics/feugere-2021-mosquito-sound-swarm-attraction-coluzzii.md

---

## Abstract (summary)

The first quantitative test of whether a female *Anopheles* can detect the **sound of a
whole male swarm** at a distance. Free-flying *A. coluzzii* females were exposed to
playbacks of recorded male-swarm sounds at four sound-pressure levels, with males
exposed to female-swarm sound as a positive control; acoustic propagation theory was
then used to extrapolate to swarms of 10²–10⁴ males and to field swarm dimensions.
The answer is **no**: a female cannot hear a swarm as a whole before she reaches its
periphery.

## Key Results (as used by the model)

- **Measured swarm sound:** a station-keeping swarm of ~**70 male *A. coluzzii*** produced
  a first-harmonic SPL of **20 ± 3 dB** at **0.9 m** from the swarm centre (0.6 m high).
- **Female response: none.** Free-flying females exposed to swarm sound at up to
  **48 ± 3 dB SPL** did **not** change median angular speed (LRT χ²₃₁ = 3.81, P = 0.051)
  nor median wingbeat frequency (LRT χ²₃₁ = 3.19, P = 0.074); the loudest
  distribution was not different from the intercept (angular speed: mean change
  0.3 rad s⁻¹ on a mean of 4.6 rad s⁻¹, P = 0.31; wingbeat: mean change 1 Hz on a
  mean of 487 Hz, P = 0.64). No effect on linear velocity, height or distance to the
  speaker.
- **Positive control works:** males exposed to female-swarm sound **did** respond
  (angular speed LRT χ²₃₁ = 16.5, P < 0.001; wingbeat frequency LRT χ²₃₁ = 24.6,
  P < 0.001; +22 Hz on a mean of 803 Hz at 45 dB). Male hearing threshold is
  **below 33 ± 3 dB SPL**; the female threshold is **above 48 ± 3 dB SPL** (not
  measured beyond).
- **Distance accounting:** the distance at which the sound of a 70-male swarm modelled
  as a point source reaches 48 dB is **0.04 ± 0.01 m** (far-field) and **< 0.15 m**
  without the far-field assumption — **less than the swarm radius (0.2 m)**. For
  **1 000 males** the equivalent distance is **≤ 0.15 ± 0.05 m**; for **10 000 males**
  **≤ 0.5 ± 0.2 m**.
- **Conclusion:** "there is **no chance that a female can hear a swarm at a distance
  less than 0.8 m** from its centre for a number of males up to 10 000", and "there is
  no chance for a female to hear a swarm **before reaching the peripheral males** if
  the swarm is less than a couple of thousands of males". Predicted *coluzzii* swarm
  radius: **0.5 ± 0.1 m** for 95 % of 1 000 males (0.20 ± 0.05 m for 50 %), and
  **0.6 ± 0.1 m** for 95 % of 10 000 males (0.21 ± 0.05 m for 50 %).
- **Field acoustics:** "mosquito sounds stand out against ambient noise at least
  **3 m** from the swarm" (Burkina Faso field recordings).
- Species-specific swarm cues are **weak**: the fourth-harmonic amplitudes of the two
  species differed but were above mosquito audibility; mean swarm wingbeat frequencies
  differed by only **21 Hz** (857 Hz *coluzzii*, 836 Hz *gambiae* s.s.) with a
  **47 Hz** harmonic-peak overlap at −3 dB.

## Relevance to MalariaSentinel (Centinela)

Evidence tier **[M]** (species measured directly; the playback and the propagation
model are laboratory + theory).

This paper is decisive for one specific question the brief asks: **does a female's
probability of encountering a swarm depend on swarm density in a way that requires the
geometry of the swarm field, or is an aggregate sufficient?**

- The **acoustic** channel cannot be the one by which a female locates a swarm from a
  distance: the swarm is not audible before the female is essentially inside it. So
  there is **no "swarm beacon radius"** to model, and no published attenuation
  function that would justify a distance-dependent attendance probability based on
  sound.
- What remains is **close-range visual detection** (and the marker), i.e. the female
  must *be* in the neighbourhood of the swarm. The measured swarm radius is
  **0.2–0.6 m** — two orders of magnitude below the Centinela's 1 km cells.
  **Consequence: a per-cell aggregate of swarm sites plus a within-cell random draw is
  sufficient; no sub-cell swarm geometry is needed.**
- The **acoustic-channel claim is contradicted for females but supported for males**
  (males respond from 33 dB), which matters for any future male–female interaction
  module: the male's detection of the female is a **contact-range** event
  (cm), so the D5 slot formula's "insemination" must be modelled as a *contact
  process*, not as a long-range attraction.

**Caveats:** the female hearing threshold was not measured above 48 dB; the
playback used a laboratory swarm sound scaled to a 70-male source and the field
extrapolation uses a point-source model; the swarm-radius extrapolation is linear and
"should be taken with caution for the highest number of males"; the conclusion
concerns the acoustic channel only — a visual search radius for females is **not**
measured here.

## License

CC BY 4.0 (© 2021 Feugère et al; Journal of the Royal Society Interface open access).
Open-access copy: https://pmc.ncbi.nlm.nih.gov/articles/PMC8086941/
