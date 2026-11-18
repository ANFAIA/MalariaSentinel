# Spatial and temporal characteristics of laboratory-induced *Anopheles coluzzii* swarms: Shape, structure, and flight kinematics

**Authors:** Poda BS, Cribellier A, Feugère L, Fatou M, Nignan C, Hien DFS, Müller P, Gnankiné O, Dabiré RK, Diabaté A, Muijres FT, Roux O
**Journal:** iScience | **Year:** 2024 (27:111164) | **DOI:** 10.1016/j.isci.2024.111164
**File:** papers/anopheles-dynamics/poda-2024-coluzzii-swarm-shape-structure-kinematics.md

---

## Abstract (summary)

The **primary coluzzii characterisation of swarm geometry and flight kinematics**:
3-D stereoscopic videography (near-infrared, two cameras) of laboratory swarms of male
*A. coluzzii* above a ground marker under simulated sunset, over the complete swarming
duration (start, peak, end phases). It quantifies the swarm's shape, volume, position
and the individual flight kinematics, and builds a **sensory-system-informed model** in
which swarming mosquitoes are shown to use **visual perception of both the ground
marker and the sunset horizon**.

## Key Results (as used by the model)

- **Swarm onset and temporal structure:** mosquitoes begin random flight ≈ **2 min before
  lights-off**; **2–3 min after lights-off a male starts flying repeatedly over the
  marker**; other mosquitoes join within **7–90 s** (t_start = **46 ± 8 s**, n = 5 of 6
  experiments); the number of swarming mosquitoes peaks **~10 min later**, the peak is
  stable for **~20 min**, then decays to zero. (In one experiment a single male swarmed
  alone for 233 s before leaving.)
- **Swarm participation:** during the recordings **18–73 %** of released mosquitoes
  showed flight activity and only **4–54 %** exhibited swarming behaviour. Phase
  contrasts: swarming mosquitoes start **4.0 ± 0.6**, peak **16.7 ± 2.1**, end
  **6.3 ± 1.4**; the proportion swarming among flying mosquitoes is **26 % (start) →
  71 % (peak) → 45 % (end)**.
- **Swarm geometry:** swarms are an **elliptical cone** above the marker; mean swarm
  centroid at **x̄ = 0.00, ȳ = 0.00, z̄ = 0.67 ± 0.01 m** (i.e. **~0.67 m above the
  marker**); spread σ̄(x) = 0.06 m, σ̄(y) = 0.10 m, σ̄(z) = 0.04 m.
- **Flight speeds (males):** swarming individuals **0.50 ± 0.00 m/s** (range
  **0.24–1.28 m/s**), accelerations **2.88 ± 0.02 m/s²** (range 0.29–7.33); **mean
  distance to nearest neighbour 0.11 ± 0.00 m**. Component speeds:
  **u = 0.24** (parallel to sunset horizon), **v = 0.38** (normal to it),
  **w = 0.08 m/s** (vertical) — v is **1.6×** u and **4.8×** w.
- **Flight speed of males NOT swarming** (in the same arena, mostly wall-hugging escape
  flight): **0.20 ± 0.00 m/s**, i.e. **57 % lower** speed and **67 % lower**
  acceleration than swarming males (0.78 ± 0.00 m/s²).
- **General flight-speed context:** the paper notes that swarming individuals "fly fast
  (about **0.2–2 m/s**)" in large aggregations of up to thousands of males.
- The swarm is **highly stereotypic** in shape and position and **consistent over the
  complete swarming duration**.

## Relevance to MalariaSentinel (Centinela)

Evidence tier **[M]** for the coluzzii measurements (laboratory; semi-field-like
illumination) and **[EP]** for the modelling conclusion.

Three direct consequences for the Centinela's male layer:

1. **The swarm is a small, rigid geometric object.** Centroid 0.67 m above the marker,
   spread of 4–10 cm, nearest-neighbour distance 0.11 m. Against a 1 km cell this is
   **three orders of magnitude below the resolution of the spatial layer**: the correct
   representation is a **point marker with a cell-level male count**, and any
   sub-cell swarm geometry is not merely unnecessary, it is unrepresentable at the
   model's resolution.
2. **The temporal envelope is quantitative and short**: onset 2–3 min after lights-off,
   peak ~10 min later, peak plateau ~20 min, total ≈ 27 min, with the *proportion* of
   swarming males rising 26 % → 71 % → 45 %. The draft's "swarm window" should be
   modelled with these three numbers rather than as a single flag.
3. **The only published male flight speed measured outside a swarm** is here:
   **0.20 ± 0.00 m/s** for non-swarming males in the flight arena (wall-hugging escape
   flight) versus **0.50 m/s** for swarming males. **This is a laboratory arena value,
   not a field dispersal speed** — but it is the closest thing in the literature to the
   missing number, and it is an order of magnitude below the 0.66–0.87 m/s used in
   `vielma-2026-coluzzii-swarm-flight-speed-burkina-faso.md`. The Centinela should
   state which regime its male movement law is in: **swarm flight (0.5 m/s)** or
   **dispersal flight (unknown; ≥ 0.2 m/s measured only in an arena)**.

**Caveats:** laboratory, single black 40×40 cm marker, 2.0 × 0.7 × 1.8 m plexiglass
arena; laboratory-reared males 4–6 days old; the non-swarming speed is contaminated by
wall-escape behaviour and by the small arena; the paper's own model is a
"sensory-system-informed" behavioural model, not a spatial population model.

## License

CC BY-NC 4.0 (© 2024 Poda et al; iScience — non-commercial reuse only).
Open-access copy: https://pmc.ncbi.nlm.nih.gov/articles/PMC11546533/
