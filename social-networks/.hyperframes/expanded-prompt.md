# Expanded Prompt — MalariaSentinel LinkedIn Video

Source: `design.md` (Slate & sage, calm research-briefing, Space Grotesk + JetBrains Mono).
Source of truth: `docs/abm-status.md` (ABM Python v0.5.0, ABM C++ F1 complete, 71+60+5 tests).
Format: 1080×1350 vertical (4:5 LinkedIn). Total ≈45s, 6 scenes.

---

## Title block

`#2F404F` deep slate canvas. `Space Grotesk` 700 for project name + display, `Space Grotesk` italic 600 for one-word emphasis. `JetBrains Mono` for the running header, version strings, and code-flavoured chips. Teal accent `#3894A1` with `#4FB0BC` highlight. Sage `#C7DAD3` for "done" markers. Mood: research briefing — calm, evidence-led, no startup pitch energy.

## Rhythm declaration

`hold → KICKOFF → KICKOFF → PEAK → HERO → resolve`

- Scene 1 (hold): quiet title card. The project name lands first, then a single italic word, then the supporting line. 1.5s of "where am I" before any motion begins.
- Scene 2 (KICKOFF): the pipeline — the six-stage flow at a glance. The viewer sees the whole data flow in one frame.
- Scene 3 (KICKOFF): the state of the project — test counts + completed milestones. Numbers carry the scene.
- Scene 4 (PEAK): the C++ ABM engine — the technical core. Constants + 7 daily ops.
- Scene 5 (HERO): the U-Net surrogate — the architecture + the data flow. The conceptual climax.
- Scene 6 (resolve): ANFAIA + closing. Slowest tempo, simplest motion, then dip to black.

Transitions: push-up slide (0.5s, `power3.inOut`) for the title→scene-2 handoff. Blur crossfade (0.4s, `power2.inOut`) for all other scene-to-scene. Color dip to black (0.7s) for the final.

## Global rules

- One shared `tl` for the root composition, paused, registered on `window.__timelines["root"]`.
- Every scene uses entrance animations on every element. No element appears fully-formed.
- No exit animations except on the final scene (which may fade elements to black).
- 2–5 background decoratives per scene, each with ambient motion. Shared breathe on the radial glow.
- Top hairline bar in every scene — running header `MALARIA·SENTINEL · 0n/06`. Never re-animated.
- Use `tl.fromTo()` for elements (capture-engine safety).
- `font-variant-numeric: tabular-nums` on all number columns.
- All transitions are CSS-based. No shader transitions.

## Per-scene beats

### Scene 1 — Title (`0s → 6.0s`)

**Concept:** Calm slate canvas. The project name lands first, then a single italic word, then the supporting line. 1.5s of stillness before motion begins.

**Mood direction:** Cinematic title sequence. Not a startup ad.

**Depth layers (10 elements):**
- BG: full-canvas `#2F404F`. Faint oversized ghost word `SENTINEL` at 6% opacity, anchored bottom-right.
- BG: top hairline rule at y=100, 1px, `rule` color.
- BG: bottom hairline rule at y=1250, 1px, `rule` color.
- BG: teal radial glow centered at (700, 900), 500px radius, `accent-glow`, breathing 4s cycle.
- MG: running header `MALARIA·SENTINEL · 01/06` (mono 18px, fg-dim).
- MG: top-right section label `PROYECTO · 2026` (mono 18px uppercase, accent, 0.18em tracking).
- MG: `MalariaSentinel` (Space Grotesk 700, 110px, fg).
- MG: `para la` (Space Grotesk italic 600, 64px, accent-bright).
- MG: `eliminación de la malaria` (Space Grotesk 500, 30px, fg-muted, max-width 760px).
- FG: bottom-right vertical text `SDSS · 2026 · GHANA` (mono 18px, fg-dim, rotated 90°).

**Animation choreography (verbs per element):**
- Top hairline rule: DRAWS in via scaleX 0→1 from left, 0.6s, `power3.out`, at t=0.1.
- Bottom hairline rule: DRAWS in via scaleX 0→1 from right, 0.6s, `power3.out`, at t=1.9.
- Running header `01/06`: FADES in (opacity 0→1), 0.4s, `power2.out`, at t=0.2.
- Section label `PROYECTO · 2026`: FADES in, 0.4s, `power2.out`, at t=0.3.
- `MalariaSentinel` (display): SLAMS in from below (y 80→0, opacity 0→1), 0.7s, `expo.out`, at t=0.5.
- `para la` (italic accent): FADES in with x -20→0, 0.5s, `power3.out`, at t=1.2.
- `eliminación de la malaria`: FADES in with x -20→0, 0.6s, `power2.out`, at t=1.7.
- `SDSS · 2026 · GHANA` (vertical): FADES in, 0.4s, `power2.out`, at t=2.1.
- Radial glow: breathes scale 1.0→1.06, 4s cycle, `sine.inOut`, yoyo.

**Transition out:** Push-up slide. Scene 1 translates y:0→-1350 over 0.5s with blur 0→8→0 mid-flight, while scene 2 translates y:1350→0 with blur 8→0. Easing `power3.inOut`.

---

### Scene 2 — El pipeline SDSS (`6.5s → 13.5s`)

**Concept:** The six-stage data pipeline as a horizontal flow with arrows. The viewer sees the full path from raw satellite data to actionable risk maps in one frame. The headline carries the concept; the flow carries the evidence.

**Mood direction:** Architecture diagram. Engineering cadence. Calm, factual.

**Depth layers (12 elements):**
- BG: `#2F404F` carry-over. New radial glow centered at (540, 700), 500px, `accent-glow`, breathe 4s.
- BG: oversized ghost word `PIPELINE` at 5% opacity, anchored top-right.
- BG: subtle grid pattern, 80px cells, 3% opacity, fg.
- MG: section label `01 · PIPELINE` (mono 18px, accent, 0.18em tracking).
- MG: headline `Del satélite al mapa de riesgo.` (Space Grotesk 700, 60px, fg).
- MG: subhead `Seis etapas. Una decisión.` (Space Grotesk italic 500, 28px, fg-muted).
- MG: 6 stage chips in a 3×2 grid:
  - `01 INGESTA` — CHIRPS · ERA5 · DEM · JRC GSW · MODIS · WorldCover
  - `02 SUITABILIDAD` — TWI · idoneidad
  - `03 ABM` — C++20 · xoshiro256** · 7 ops/día
  - `04 DATASET` — (state_t + env) → state_{t+1}
  - `05 U-NET` — 32→64→128→256→512 · MSE + soft-Dice
  - `06 PREDICCIÓN` — risk maps · FastAPI
- FG: bottom-left meta `ABM ↔ U-Net · profesor y estudiante` (mono 16px, fg-dim, italic).

**Animation choreography:**
- Section label: FADES in, 0.4s, t=6.6.
- Headline: FADES in y 20→0, 0.5s, t=6.9.
- Subhead: FADES in, 0.4s, t=7.3.
- Stage 1: FADES in x -30→0, 0.4s, t=7.7.
- Stage 2: FADES in x -30→0, 0.4s, t=7.9.
- Stage 3: FADES in x -30→0, 0.4s, t=8.1.
- Stage 4: FADES in x -30→0, 0.4s, t=8.3.
- Stage 5: FADES in x -30→0, 0.4s, t=8.5.
- Stage 6: FADES in x -30→0, 0.4s, t=8.7.
- Meta bottom-left: FADES in, 0.4s, t=9.2.
- Radial glow breathes.

**Transition out:** Blur crossfade, 0.4s, `power2.inOut`.

---

### Scene 3 — Estado actual (`13.5s → 21.0s`)

**Concept:** Numbers as the carrier. Three test counts, four completed milestones, five pending. Restraint — the stats speak.

**Mood direction:** Status report. Test-greenhouse numbers. The proof of work.

**Depth layers (11 elements):**
- BG: `#2F404F` carry-over. Radial glow centered at (200, 800), 500px, breathe 4s.
- BG: oversized ghost word `71/71` at 6% opacity, anchored top-right.
- MG: section label `02 · ESTADO` (mono 18px, accent, 0.18em tracking).
- MG: headline `Cuatro hitos cumplidos.` (Space Grotesk 700, 60px, fg).
- MG: stat 1 — `71/71` (Space Grotesk 800, 96px, fg) + unit `tests Python` (Space Grotesk 500, 24px, fg-muted) + gloss `ABM v0.5.0` (mono 18px, fg-dim).
- MG: stat 2 — `60/60` (Space Grotesk 800, 96px, fg) + unit `tests C++` (Space Grotesk 500, 24px, fg-muted) + gloss `mal-abm-fast F1` (mono 18px, fg-dim).
- MG: stat 3 — `5/5` (Space Grotesk 800, 96px, accent) + unit `parity tests` (Space Grotesk 500, 24px, fg-muted) + gloss `Python ↔ C++` (mono 18px, fg-dim).
- MG: milestone strip — 4 sage chips for done: `M0 · M1 · M2 · M-perf F1` and 5 dim chips for pending: `M3 · M4 · M5 · M6 · M7`.
- FG: bottom-right meta `ABM Python v0.5.0 · C++ F1` (mono 16px, fg-dim, uppercase).

**Animation choreography:**
- Section label: FADES in, 0.4s, t=13.6.
- Headline: FADES in y 20→0, 0.5s, t=13.9.
- Stat 1 number: COUNTS UP from 0 to 71 (obj.val 0→71, 0.8s, `power2.out`), t=14.4.
- Stat 1 gloss FADES in, 0.4s, t=15.0.
- Stat 2 number: COUNTS UP from 0 to 60, 0.7s, `power2.out`, t=15.4.
- Stat 2 gloss FADES in, 0.4s, t=15.9.
- Stat 3 number: COUNTS UP from 0 to 5, 0.5s, `power2.out`, t=16.3.
- Stat 3 gloss FADES in, 0.4s, t=16.7.
- Milestone strip: FADES in with stagger 60ms per chip, total ~0.5s, t=17.2.
- Meta bottom-right: FADES in, 0.4s, t=17.8.
- Radial glow breathes.

**Transition out:** Blur crossfade, 0.4s, `power2.inOut`.

---

### Scene 4 — El motor ABM (`21.5s → 29.5s`)

**Concept:** The C++ engine, exposed. Left column: the four key constants. Right column: the seven daily operations as a list. Mono dominates — this is the technical core.

**Mood direction:** Source code presented as design. Technical, precise.

**Depth layers (12 elements):**
- BG: `#2F404F` carry-over. Radial glow centered at (900, 600), 500px, breathe 4s.
- BG: oversized ghost word `mal-abm-fast` at 5% opacity, anchored top-left.
- MG: section label `03 · MOTOR` (mono 18px, accent, 0.18em tracking).
- MG: headline `El motor ABM en C++.` (Space Grotesk 700, 60px, fg).
- MG: subhead `mal-abm-fast · C++20 · black-box equivalente al ABM Python` (Space Grotesk italic 500, 24px, fg-muted).
- MG: constants grid (left column):
  - `K_MAX = 1000`
  - `EIP_BASE_C = 16.0`
  - `EIP_THRESHOLD_GD = 110.0`
  - `ADULT_DISPERSE_SIGMA_M = 300.0`
  - `ADULT_DAILY_MORT_BASE = 0.90`
- MG: 7 ops list (right column):
  - `larva_mortality_inactive`
  - `larva_mortality_density` *(Beverton-Holt)*
  - `larva_growth` *(eip += max(0, T-16°C))*
  - `larva_to_adult` *(eip ≥ 110 GD)*
  - `adult_dispersal` *(10%, Gaussiana σ=300m)*
  - `adult_mortality` *(Lardeux thermo-dep.)*
  - `birth` *(binomial(n/2, 0.10))*
- FG: bottom-left meta `PRNG xoshiro256** · determinista` (mono 16px, fg-dim).
- FG: bottom-right meta `60/60 ctest · 5/5 parity` (mono 16px, accent).

**Animation choreography:**
- Section label: FADES in, 0.4s, t=21.6.
- Headline: FADES in y 20→0, 0.5s, t=21.9.
- Subhead: FADES in, 0.4s, t=22.3.
- Constant 1: FADES in x -20→0, 0.3s, t=22.7.
- Constant 2: FADES in x -20→0, 0.3s, t=22.85.
- Constant 3: FADES in x -20→0, 0.3s, t=23.0.
- Constant 4: FADES in x -20→0, 0.3s, t=23.15.
- Constant 5: FADES in x -20→0, 0.3s, t=23.3.
- Op 1: FADES in x 20→0, 0.3s, t=23.6.
- Op 2: FADES in x 20→0, 0.3s, t=23.75.
- Op 3: FADES in x 20→0, 0.3s, t=23.9.
- Op 4: FADES in x 20→0, 0.3s, t=24.05.
- Op 5: FADES in x 20→0, 0.3s, t=24.2.
- Op 6: FADES in x 20→0, 0.3s, t=24.35.
- Op 7: FADES in x 20→0, 0.3s, t=24.5.
- Meta PRNG: FADES in, 0.4s, t=25.0.
- Meta 60/60: FADES in, 0.4s, t=25.2.
- Radial glow breathes.

**Transition out:** Blur crossfade, 0.4s, `power2.inOut`.

---

### Scene 5 — U-Net sustituta (`29.5s → 38.5s`)

**Concept:** The conceptual climax. Two columns: the U-Net architecture (left) and the data flow it learns (right). The number 100× is the punchline.

**Mood direction:** Architecture diagram + value proposition. Calm but assertive.

**Depth layers (12 elements):**
- BG: `#2F404F` carry-over. Radial glow centered at (540, 1000), 600px, breathe 4s. Stronger alpha.
- BG: oversized ghost word `U-NET` at 5% opacity, anchored bottom-right.
- MG: section label `04 · U-NET` (mono 18px, accent, 0.18em tracking).
- MG: headline `La sustituta *100× más rápida.*` (Space Grotesk 700, 60px, fg, with `100×` in italic accent-bright).
- MG: subhead `mal-core · malariasim CLI · FastAPI REST` (Space Grotesk 500, 22px, fg-muted).
- MG: architecture diagram (left column):
  - Input: `(state_t + env) = (6, 128, 128)`
  - Encoder: `32 → 64 → 128 → 256`
  - Bottleneck: `512`
  - Decoder: `256 → 128 → 64 → 32`
  - Output: `state_{t+1} = (2, 128, 128)`
  - Loss: `MSE + 0.5 × soft-Dice`
- MG: data flow (right column):
  - `env 4-canales` → `state COG 2-band` → `U-Net` → `risk map`
  - bands: `water_frac · rainfall · temp_suitability · ndvi`
  - state bands: `density · suitability`
- FG: bottom-left meta `mismo input → misma predicción` (mono 16px, fg-dim, italic).
- FG: bottom-right meta `M3 → M4 → M5 → M6` (mono 16px, accent, uppercase).

**Animation choreography:**
- Section label: FADES in, 0.4s, t=29.6.
- Headline: FADES in y 20→0, 0.5s, t=29.9.
- Subhead: FADES in, 0.4s, t=30.3.
- Architecture row 1 (Input): FADES in x -20→0, 0.3s, t=30.7.
- Architecture row 2 (Encoder): FADES in x -20→0, 0.3s, t=30.9.
- Architecture row 3 (Bottleneck): FADES in x -20→0, 0.3s, t=31.1.
- Architecture row 4 (Decoder): FADES in x -20→0, 0.3s, t=31.3.
- Architecture row 5 (Output): FADES in x -20→0, 0.3s, t=31.5.
- Architecture row 6 (Loss): FADES in x -20→0, 0.3s, t=31.7.
- Data flow row 1: FADES in x 20→0, 0.3s, t=32.0.
- Data flow row 2: FADES in x 20→0, 0.3s, t=32.2.
- Data flow row 3: FADES in x 20→0, 0.3s, t=32.4.
- Meta bottom-left: FADES in, 0.4s, t=33.0.
- Meta bottom-right: FADES in, 0.4s, t=33.2.
- Radial glow breathes stronger (scale 1.0→1.08).

**Transition out:** Blur crossfade, 0.4s, `power2.inOut`.

---

### Scene 6 — Cierre ANFAIA (`39.0s → 45.0s`)

**Concept:** Quiet, resolved. Center the funder word. One short sentence. The GitHub link at the bottom. A final slow ambient. Then color dip to black over 0.7s.

**Mood direction:** Closing credit of a documentary. Restrained, sincere.

**Depth layers (8 elements):**
- BG: `#2F404F` carry-over. Radial glow centered at (540, 600), 700px, breathe 4s.
- BG: oversized ghost word `gracias` at 6% opacity, anchored bottom-left.
- MG: section label `05 · APOYO` (mono 18px, accent, 0.18em tracking).
- MG: small lead `Este proyecto es posible gracias a` (Space Grotesk 500, 30px, fg-muted, max-width 720px).
- MG: `ANFAIA` (Space Grotesk 700, 180px, accent) — center anchor.
- MG: divider rule under ANFAIA, 60% width, 2px, accent, scaleX 0→1.
- MG: tagline `Ciencia abierta para la eliminación de la malaria.` (Space Grotesk italic 500, 28px, fg-muted, max-width 760px).
- FG: GitHub handle at bottom: `github.com/ANFAIA/MalariaSentinel` (mono 20px, fg).
- FG: final small `SDSS · Open Source · 2026` (mono 16px, fg-dim, uppercase).

**Animation choreography:**
- Section label: FADES in, 0.4s, t=39.0.
- Lead: FADES in y 10→0, 0.4s, t=39.3.
- `ANFAIA`: SLAMS in scale 0.85→1, opacity 0→1, 0.7s, `expo.out`, t=39.7. The strongest entry of the deck.
- Divider rule: scaleX 0→1 from center, 0.5s, t=40.4.
- Tagline: FADES in, 0.5s, t=40.8.
- GitHub handle: FADES in y 10→0, 0.4s, t=41.4.
- `SDSS · Open Source · 2026`: FADES in, 0.4s, t=41.7.
- Radial glow breathes.
- **Final dip to black (exit allowed):** black overlay opacity 0→1, 0.7s, `power2.inOut`, at t=43.8. All elements fade to 0 as the overlay rises.

---

## Recurring motifs (global)

- **Top hairline bar:** running header `MALARIA·SENTINEL · 0n/06` (left, mono 18px, fg-dim) + scene counter accent. Visible in every scene. Drawn in once at t=0.1 on scene 1, present unchanged thereafter. Counter updates via `tl.call()` at scene boundaries.
- **Radial teal glow:** every scene. Position varies per scene. Breathing 4s `sine.inOut` yoyo.
- **Ghost word:** every scene. Position + word varies (`SENTINEL`, `PIPELINE`, `71/71`, `mal-abm-fast`, `U-NET`, `gracias`).
- **Mono chips for milestones:** `M0 · M1 · M2 · M-perf F1` rendered with sage bg; `M3–M6` rendered with rule outline and fg-dim text.

## Negative prompt

- No mosquito emoji. No DNA helix. No "AI brain" or "neural network" visual clichés.
- No "innovation" / "synergy" / "leverage" / "ecosystem" language.
- No Inter, Roboto, Open Sans, Poppins, Outfit, Sora, Syne.
- No pure black `#000000` or pure white `#FFFFFF`. Use `#2F404F` and `#F0F1EE`.
- No centered-and-floating layouts. Anchor to edges.
- No full-screen linear gradients. Use radial glow + solid surface.
- No `<br>` in body copy. Use `max-width`.
- No exit animations before transitions. Transitions are the exit.
- No exit animations on the title card before the push-up transition.
- No warm "warn" colors (orange/red). Use sage for "done", accent teal for "current/highlight".
