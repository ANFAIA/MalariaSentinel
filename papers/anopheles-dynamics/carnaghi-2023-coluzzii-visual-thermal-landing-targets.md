# Visual and thermal stimuli modulate mosquito-host contact with implications for improving malaria vector control tools

**Authors:** Manuela Carnaghi, Federica Mandelli, L. Feugère, J. Joiner, S. Young, S. Belmain, R. Hopkins, F. Hawkes
**Journal:** iScience | **Year:** 2024 (online 27 Nov 2023) 27(1):108578 | **DOI:** 10.1016/j.isci.2023.108578
**File:** papers/anopheles-dynamics/carnaghi-2023-coluzzii-visual-thermal-landing-targets.md
**Copy read:** PMC full text — https://pmc.ncbi.nlm.nih.gov/articles/PMC10753043/

---

## Abstract (summary)

Three wind-tunnel assays with **female *Anopheles coluzzii***, using 3-D
tracking, to determine how the **size** of a visual target and the **extent of
its thermal signature** change the probability of landing on it, in the
presence of human odour + CO2.

## Key Results (as used by the model)

### Setup  [M]
Flight arena 1.2 m tall × 1.2 m wide × 2 m long (same arena as Hawkes &
Gibson 2016); 25 ± 2 °C, 65 ± 5 % RH; **laminar airflow ≈ 0.2 m s⁻¹** from
upwind to downwind; laboratory lights off, illumination by warm white LEDs
under the floor giving a homogeneous **0.001 W m⁻²** at **420–680 nm**, which
the authors state is "comparable to the light level mosquitoes experience in
the field during **full moon** nights". Nine 10 × 10 cm and two 20 × 20 cm
black IR-transmitting plastic tiles placed randomly on the floor "to allow
**optomotor navigation**". Mosquitoes concurrently stimulated with human
odours and CO2 throughout.

### Target size  [M]
Targets: large 30 × 40 cm, small 15 × 20 cm (horizontal or vertical).
* Two targets of identical size: more mosquitoes landed on the large target
  (**4.7 ± 0.5**) than on the small one (**2.5 ± 0.4**), LMM F(1,65) = 10.38,
  p = 0.002.
* Density per 100 cm² was nevertheless higher on the small target
  (median 1.0 vs 0.3; Mann–Whitney U = 454.5, p < 0.001).
* **Competitive assay (large + small together): 80.0 % ± 4.9 % of landings on
  the large target (median 5.0) vs 20.0 % ± 4.9 % on the small target
  (median 1.5); Wilcoxon W = 0, p = 0.002, n = 12.**
* Tracks around small targets were **more tortuous** than around large targets
  (ANOVA F(2,103) = 13.65, p < 0.001) and the mosquitoes flew **slower**
  around targets than over the no-target area (F(2,103) = 30.41, p < 0.001).

### Maximum visual resolution distance — *A. coluzzii* eye model  [M, model output]
A software model of the proportion of stimulated **ommatidia** (200–300 per eye)
for high-contrast circular targets, parameterised on published mosquito
ommatidial optics: **interommatidial angle 8°, receptive field 40°, flight
height 15 cm** above the target.

| Target | Orientation | Maximum resolution distance |
|---|---|---|
| Large (30 cm) | horizontal | **~39 cm** (≈ 37 cm at 25 cm flight height) |
| Large (30 cm) | **vertical** | **~72 cm** (nearly double the horizontal case) |
| Small (15 cm) | horizontal | **~25 cm** |
| Small (15 cm) | vertical | **~36 cm** (30 % further than horizontal) |

"Target size is directly proportional to the distance at which it is resolved,
with larger targets resolved at a considerably greater distance than smaller
targets, while targets with comparable sizes are detected further away if
oriented vertically rather than horizontally." **Target orientation does not
affect the final landing rate** (only the resolvable distance).

### Extent of the thermal signature  [M]
One large horizontal target with high visual contrast; the heated fraction was
**fully heated (positive control) / half / one-quarter / one-eighth / none
(negative control)**. Heated water bags were held at **38 ± 2 °C**;
unheated margins were kept at ambient with water bags.
* Treatment had a significant effect on landing (GLM χ² = 42.79, df = 4,
  p < 0.001). **Results cluster in two groups: the fully heated and the
  half-heated target elicited a similar landing rate, while quarter- and
  eighth-heated targets elicited a significantly lower rate.**
* "A clear **linear relationship** was found between the mean number of
  mosquitoes that landed on the heated areas of the targets and the size of the
  thermal signature, indicating **landing is directly proportional to the area
  of the thermal signature**."
* Target efficiency (mean landing density over the whole surface) was
  **≈ 2× higher** for the fully/half-heated targets than for the
  quarter/eighth-heated ones, and **≈ 2.5× higher** than the unheated control.
* The number landing on the **unheated** area did not differ between
  treatments (LMM interaction F(2,44) = 4.40, p = 0.02).
* Flight speed, total duration, distance and tortuosity around the target were
  **not** significantly different between thermal treatments — the thermal
  signature changes *where* they land, not *how* they fly.

## Relevance to MalariaSentinel (Centinela)

Two directly usable *A. coluzzii* parameters:

1. `visual_preference` — **80 % of landings on the large target vs 20 % on the
   small** when both are offered. A visual attraction term in the movement law
   should therefore weight target **area** strongly (or be proportional to
   angular size), not treat any visual contrast as equally attractive. **[M]**
2. `visual_radius` — the **eye-model resolution distances** are the closest
   thing to a published *A. coluzzii* visual detection distance:
   **~39 cm** (large horizontal target, 30 cm), **~72 cm** (large vertical),
   **~25 cm** (small horizontal, 15 cm), **~36 cm** (small vertical). These are
   **model outputs from published ommatidial optics, not behavioural
   measurements**, but they are species-specific and they are an order of
   magnitude tighter than the "≤ 1.5 m" figure used in the synthesis.
   **[M]-model**
3. `landing_thermal_condition` — the **≥ 50 % heated-area** rule used in the
   synthesis is a **reasonable operationalisation but not a published
   threshold**. What the paper actually shows is (a) landing is *linearly
   proportional* to heated area, and (b) there is a **cluster break between
   the half-heated and the quarter-heated** treatments. The defensible
   formulation for the model is therefore: *"the thermal signal is a graded
   probability weighted by heated-area fraction, with a sharp efficiency drop
   below ~50 %"* — not a hard binary gate at 50 %. **[M]**

**Caveat:** the thermal cue here is a **surface** (water bags on the target,
38 ± 2 °C), not the convective plume of a living host; and the experiment was
run under **full-moon** illumination (0.001 W m⁻²), i.e. *brighter* than the
starlight regime of Hawkes & Gibson 2016, so the two papers are not directly
comparable on visual-gating thresholds.

## License

CC BY 4.0 (iScience / Cell Press open access).
