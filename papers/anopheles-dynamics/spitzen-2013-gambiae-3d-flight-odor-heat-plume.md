# A 3D Analysis of Flight Behavior of *Anopheles gambiae* sensu stricto Malaria Mosquitoes in Response to Human Odor and Heat

**Authors:** J. Spitzen, C. Spoor, F. Grieco, C. ter Braak, J. Beeuwkes, S. van Brugge, S. Kranenbarg, L. Noldus, J. van Leeuwen, W. Takken
**Journal:** PLoS ONE | **Year:** 2013 (8(5):e62995) | **DOI:** 10.1371/journal.pone.0062995
**File:** papers/anopheles-dynamics/spitzen-2013-gambiae-3d-flight-odor-heat-plume.md
**Copy read:** PMC full text — https://pmc.ncbi.nlm.nih.gov/articles/PMC3642193/

---

## Abstract (summary)

3-D tracking of female ***Anopheles gambiae* sensu stricto** in a wind tunnel
(flow 20 cm s⁻¹) under four treatments: clean air (control), heat alone,
human odour alone, and human odour + heat. Quantifies flight path, ground
speed, crosswind ("tangent") behaviour, and the time spent inside vs outside
the odour plume.

## Key Results (as used by the model)

### Setup  [P]
Wind tunnel 160 cm long × 60 × 60 cm; 27 ± 1 °C; 70 ± 3 % RH; **wind speed
20.0 ± 1.0 cm s⁻¹**; odour plume from a glass funnel (4.3 cm tube → 10.5 cm
open top) at the upwind end, approximated as a **cone of 20°** (13° relative to
the floor when the 34 °C heat element was on); a **2.5 cm transition zone**
around the cone was defined and excluded; heat source = 34 °C brass element;
"landing on the source" = within a 5 cm-diameter circle on the upwind screen.

### Terminal-zone distances (the "< 0.15–0.30 m" band)  [P]
* **Odour alone** reduced flight speed only when the mosquito was **within
  30 cm** of the source.
* **Odour + heat** kept the elevated speed up to **within 15 cm** of the
  source; a strong speed decrease occurred **only below 15 cm**, where the
  mean upwind flight speed was **23 % lower** than in the 15–30 cm section.
* Maximum angular velocity magnitude occurred **< 15 cm** from the source
  (Kruskal–Wallis P < 0.001).

### Speeds  [P]
Pooled upwind ground speed **24.5 ± 0.6 cm s⁻¹** (n = 135); downwind
**25.1 ± 0.8 cm s⁻¹** (n = 94). Odour+heat **27.2 ± 1.2 cm s⁻¹** vs control
**22.5 ± 1.29 cm s⁻¹** (GLM P < 0.05). Odour+heat at 15–30 cm:
**27.6 ± 14 cm s⁻¹** vs odour only 22.1 ± 1.6 cm s⁻¹ (P < 0.05).

### Angular velocity  [P]
Pooled mean magnitude of angular velocity: upwind **524.8 ± 14.9 ° s⁻¹**,
downwind **653.4 ± 19.7 ° s⁻¹** (Mann–Whitney P < 0.001). Table 1,
**upwind flight**: odour+heat **553.0 ± 27.8 ° s⁻¹** vs control
**465.9 ± 31.3 ° s⁻¹** (both lettered "a", i.e. *not* significantly different
from each other; the paper states the mean magnitude of angular velocity for
upwind flight "was not different between any of the treatments", GLM P = 0.057).

### Flight duration  [P]
Control **15.2 ± 9.8 s**; heat alone **18.8 ± 8.8 s**; human odour
**112 s**; odour+heat **67.3 ± 8.9 s**. 46.5 % of odour+heat mosquitoes landed
near the source.

### Time spent inside vs outside the plume (Table 2)  [P]

| Landing outcome | inside plume | transition zone | **outside plume** |
|---|---|---|---|
| on the source (n = 16) | 30.5 ± 3.5 % | 8.1 ± 0.7 % | **61.4 ± 3.9 %** |
| elsewhere on upwind screen (n = 19) | 7.3 ± 2.9 % | 3.8 ± 1.0 % | **88.9 ± 3.8 %** |

### The casting mechanism, measured  [P]
* Mosquitoes **did make upwind progress while inside the plume** (Wilcoxon
  Z = −6.921, P < 0.001).
* **Outside the plume there was no directional bias** toward re-contacting it
  (Wilcoxon Z = −0.669, P = 0.504) — i.e. the characteristic moth-like
  **casting** (crosswind back-and-forth with counterturning, in both the xy and
  xz planes) that re-acquires the plume.
* Odour+heat produced **more crosswind movement outside than inside** the
  plume, and the increase in crosswind movement at close range was **additive
  between odour and heat** for the vertical component.
* "When odor is lost during upwind flight, insects generally exhibit casting
  behaviour, which is described as back and forth movements across the wind
  without making much progress upwind."

## Relevance to MalariaSentinel (Centinela)

This is the source of the two structural numbers the movement law needs for the
near-field regime, both of them **proxy values from *A. gambiae* s.s., not
*A. coluzzii***:

1. `plume_occupancy` — even mosquitoes that **successfully landed** spent
   **61.4 % of their flight time outside the theoretical plume boundary**
   (88.9 % for those that landed away from the source). A model that keeps the
   mosquito glued to a continuous concentration contour will therefore
   produce the wrong trajectory statistics; the correct architecture is
   plume-acquisition (stochastic contact) + upwind surge inside + casting
   outside. **[P]**
2. `terminal_radius` — the last **15 cm** (odour+heat) to **30 cm** (odour
   alone) is where speed and angular velocity change qualitatively, i.e. where
   the mosquito switches from searching to terminal scanning. **[P]**

Note also that heat alone produced only brief, direct flights (18.8 ± 8.8 s)
and **no sustained landing** — the paper's conclusion is that the mosquito
needs the *combination* of odour and heat. **[P]**

**Caveats:** the wind tunnel is only 60 cm wide and the source is ~5 cm across,
so this is a near-field study; it contains **no** information about
detection range in the open field, and the 20 cm s⁻¹ tunnel wind is an order of
magnitude below realistic nocturnal surface winds.

## License

CC BY 4.0 (PLOS ONE open access).
