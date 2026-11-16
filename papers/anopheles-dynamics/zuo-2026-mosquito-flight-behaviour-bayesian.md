# Predicting mosquito flight behavior using Bayesian dynamical systems learning

**Authors:** Chunpeng Zuo, Chuangfei Fei, Avinash Cohen, Seungmoon Kim, Roger Cardé, John Dunkel, Daqi Hu
**Journal:** Science Advances | **Year:** 2026 (12(12):eadz7063) | **DOI:** 10.1126/sciadv.adz7063
**File:** papers/anopheles-dynamics/zuo-2026-mosquito-flight-behaviour-bayesian.md

---

## Abstract (summary)

3D trajectory tracking of free-flying mosquitoes around controlled stimuli
(visual target, CO₂ plume, combined) in a 2 m flight chamber, with Bayesian
dynamical-systems inference of the individual flight state model. The paper
resolves the mosquito into an "active" (controlled cruising) and an "idle"
(projectile) state and derives the force law governing approach to a host
cue.

## Key Results (as used by the model)

- **Active-state flight speed: ~0.7 m/s**, consistent with experimental values
  of **0.4–1.8 m/s** measured for other mosquito species.
- **CO₂ cue range:** "up to distances of **10 m downwind**, emitted carbon
  dioxide triggers mosquito flight toward the host, lowers their threshold of
  detecting skin odors, and enhances their navigation toward visual targets"
  (the paper's own summary of the wind-tunnel literature); visual stimuli
  guide flight "to within meters of the host".
- **Deceleration near the source:** the inferred force produces a slowdown
  from 0.7 m/s to **0.2 m/s when the distance to the CO₂ source drops below
  0.4 m**; with a combined visual + CO₂ target, mosquitoes maintained
  ~0.5 m/s and orbited the target.
- Suction traps capture only **10–50 %** of incoming mosquitoes — cited as
  evidence that mosquito flight is not predictable from classical models.

## Relevance to MalariaSentinel (Centinela)

This is the mechanistic anchor for the **shape** of the host-seeking
attraction used by the engine (`species.<row>.host_seeking_scale_m`,
`host_seeking_radius_m`): the sensory evidence base for a host cue is
**~10 m of CO₂ detection (and a few metres of visual/thermal resolution)**,
not the 1,500 m radius currently encoded as an engineering prior. The
0.7 m/s active cruising speed is also the reference value for converting a
metre-scale dispersal budget into flight time (≈ 1 h of active flight per
daily dispersal of 0.5–0.7 km).
**Caveats:** the study species is ***Aedes aegypti*, not *Anopheles*** — this
is a **congeneric-order proxy only**; the chamber is 2 m wide, so nothing
here measures the spatial scale of the plume at 100 m–1 km; the 10 m CO₂
figure is the paper's summary of prior wind-tunnel work, not a new
measurement.

## License

Science Advances / AAAS article reuse licence (open access, CC BY-NC per
Science Advances policy — verify per-article terms before redistribution).
