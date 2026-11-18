# Population size and dispersal of Anopheles coluzzii on São Tomé and Príncipe Islands based on mark-release-recapture experiments

**Authors:** Sanjeewa Wickramasooriya, Marcos Campos, Landmark Chamberland, Rejecte Ditter, Martin Corrêa, Brian Morgan, Donatien Mabuka, Innocent Mugeni, Lurdes Nazaré, Carlos Sousa, Colm Egan, Richard Oriango, António Fernandes da Moura, João Viegas, João Pinto, Andrew Cornel, Gabriela Lanzaro
**Journal:** Journal of Medical Entomology | **Year:** 2026 (63(3):tjag067) | **DOI:** 10.1093/jme/tjag067
**File:** papers/anopheles-dynamics/wickramasooriya-2026-coluzzii-mrr-saotome-principe.md

---

## Abstract (summary)

Four mark-release-recapture experiments with **female *Anopheles coluzzii***
(3,750–6,830 marked females per experiment) on São Tomé and Príncipe
(Atlantic Ocean, ~300 km off the West African coast, Gulf of Guinea), one dry
and one wet season per island, 2022–2023. Releases were made shortly before
sunset; recaptures by human landing catch at 21:00–02:00 on alternate nights
from day 1 to day 11 (Príncipe) or day 15 (São Tomé), at stations 236–5,349 m
from the release point. Dispersal was quantified with annulus-based
**mean distance travelled per day (MDTpD)**, flight range (**FR50, FR90**),
composite net dispersal (ND) and directional statistics against ERA5 wind.

## Key Results (as used by the model)

- **MDTpD (coluzzii females): Príncipe 695 m/day (dry) and 486 m/day (wet);
  São Tomé 559 m/day (dry) and 623 m/day (wet)** — no significant island
  (P = 0.22 / 0.31) or seasonal (P = 0.68 / 0.23) difference.
- **Flight range FR50 / FR90:** Príncipe dry **1,128 / 2,606 m**, Príncipe wet
  **399 / 1,242 m**; São Tomé wet **721 / 1,208 m**, São Tomé dry
  **465 / 902 m** (regression R² = 0.78–0.90).
- **Composite net dispersal (ND):** Príncipe dry **1,459.84 m**, Príncipe wet
  **618.39 m**; São Tomé dry **539.39 m**, São Tomé wet **686.80 m**.
  (Note: the Results prose attributes 1,459.84 m to São Tomé; the value is
  the Príncipe dry-season ND in Table 3 — the paper's own text is
  inconsistent, so only the Table 3 values are used here.)
- **Farthest recapture distances:** 1,190 m (São Tomé dry), 1,563 m (São Tomé
  wet), **3,243 m (Príncipe dry)**, 1,384 m (Príncipe wet).
- **Wind alignment:** on São Tomé, movement was strongly directional
  (Watson P < 0.01 wet, < 0.001 dry) and **aligned with the prevailing wind**
  (Rayleigh V-test **P = 0.0005 wet, P < 0.0001 dry**); on Príncipe neither
  directional structure nor wind alignment was detected (P > 0.05 / > 0.9).
  The authors attribute the contrast to the valley topography of Santo António
  and to coarse ERA5 wind fields.
- **Survival:** median survival stayed above 0.5 until ~day 10–11 in Príncipe
  (both seasons) and until ~day 7–8 in São Tomé in the wet season (no
  daily-survival point estimate is reported).
- **Population size:** São Tomé **3.35 × 10⁵ (dry) vs 2.26 × 10⁶ (wet)** — a
  6.72-fold seasonal increase; Príncipe 1.95 × 10⁵ (dry) vs 2.16 × 10⁵ (wet).
  Recapture rates were **0.24–0.93 %** (the authors flag this as low).
- Interpretation offered by the authors: **resting-site and oviposition-site
  seeking** are the probable drivers of dispersal; roads may act as movement
  corridors; the *forest form* of *An. coluzzii* can disperse between
  forest fragments.

## Relevance to MalariaSentinel (Centinela)

The **only *A. coluzzii* female MRR dataset that yields a daily movement
rate** (MDTpD ≈ 0.5–0.7 km/day) and a heavy-tailed flight range (FR90 up to
2.6 km), i.e. the empirical anchor for a movement law that must exceed the
0.45 km σ used by the engine. It is also the only source found that shows
**wind-aligned (downwind) long-range dispersal in *A. coluzzii***, which is
directly relevant to the `wind_migration_prob` / `wind_self_speed_ms`
parameters, and it argues that dispersal is **goal-directed toward
oviposition/resting sites** rather than a pure random walk.
**Caveats:** island populations (FOREST chromosomal form, São Tomé), not
mainland coastal Ghana; marked lab-reared females; recapture rate < 1 %;
terrain-driven wind effects may not transfer to the Accra coastal plain; the
text/table inconsistency on ND.

## License

CC BY-NC 4.0 (Oxford University Press open access) — non-commercial reuse only.
