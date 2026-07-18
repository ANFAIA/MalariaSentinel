# Expanded Prompt — MalariaSentinel LinkedIn Video

Source: `design.md` (Scientific teal, dark, Bricolage Grotesque + Instrument Serif italic + JetBrains Mono).
Format: 1080×1350 vertical (4:5 LinkedIn). Total ≈45s, 6 scenes.

---

## Title block

`#0A1419` charcoal-teal canvas. `Bricolage Grotesque` 800 for project name, `Instrument Serif` italic 400 for one-word emphasis. `JetBrains Mono` for the running header. Teal accent `#14B8A6` with `#2DD4BF` highlight. Mood: research briefing — Bloomberg-meets-NASA. Not a startup pitch.

## Rhythm declaration

`hold → PUNCH → PEAK → PEAK → HERO → resolve`

- Scene 1 (hold): quiet title card. Energy low. Lets the eye land.
- Scene 2 (PUNCH): the "reactiva vs predictiva" hook arrives with energy.
- Scenes 3–4 (PEAK): objectives and impacto carry the message density.
- Scene 5 (HERO): the M1–M6 timeline — this is the visual centerpiece. Best transition lands here.
- Scene 6 (resolve): ANFAIA + closing. Slowest tempo, simplest motion.

Transitions: blur crossfade (primary, 0.4s) for scenes 2→3, 3→4, 4→5. Push-up slide (0.5s) for the title→scene-2 handoff — sets the visual language. Color dip to black (0.7s) for the final.

## Global rules

- One shared `tl` for the root composition, paused, registered on `window.__timelines["root"]`.
- Every scene uses entrance animations on every element. No element appears fully-formed.
- No exit animations except on the final scene (which may fade elements to black).
- 2–5 background decoratives per scene, each with ambient motion. Shared breathe on the radial glow.
- Top hairline bar in every scene — running header `MALARIA·SENTINEL · SCENE n/6`. Never re-animated.
- Use `tl.fromTo()` for elements inside `.clip` scenes (capture-engine safety).
- `font-variant-numeric: tabular-nums` on all number columns.
- All transitions are CSS-based. No shader transitions (keeps the file self-contained and lintable).

## Per-scene beats

### Scene 1 — Title (`0s → 6.0s`)
**Concept:** Black-and-teal title card. The project name lands first, then a single italic word lands on top of it, then the supporting line. We give the viewer 1.5s of "where am I" before any motion begins. Hold energy.

**Mood direction:** Cinematic title sequence. The opening of a serious documentary. Not a startup ad.

**Depth layers (10 elements):**
- BG: full-canvas `#0A1419`. Faint oversized ghost word "SENTINEL" at 6% opacity, drifting right-to-left at 0.04 em/s.
- BG: top hairline rule at y=80, 2px, `rule` color.
- BG: bottom hairline rule at y=1270, 1px, `rule` color.
- BG: teal radial glow centered at (700, 900), 500px radius, `accent-glow`, breathing 4s cycle.
- MG: top-left `MALARIA·SENTINEL · 01/06` (mono 18px, fg-dim).
- MG: scene label `PROYECTO` (mono 18px uppercase, fg-muted, 0.08em tracking) at top-right.
- MG: `MalariaSentinel` (Bricolage Grotesque 800, 140px, fg).
- MG: `para la` (Instrument Serif italic 400, 80px, accent-bright) overlapping the project name.
- MG: `eliminación de la malaria` (Bricolage Grotesque 500, 32px, fg-muted, max-width 700px).
- FG: bottom-right vertical rule + `SDSS · 2026` (mono 18px, fg-dim, rotated 90°).

**Animation choreography (verbs per element):**
- Top hairline rule: DRAWS in via scaleX 0→1 from left, 0.6s, `power3.out`, at t=0.1.
- `MALARIA·SENTINEL · 01/06`: FADES in (opacity 0→1), 0.4s, `power2.out`, at t=0.2.
- `PROYECTO`: FADES in, 0.4s, `power2.out`, at t=0.3.
- `MalariaSentinel` (display): SLAMS in from below (y 80→0, opacity 0→1), 0.7s, `expo.out`, at t=0.5. Slight overshoot at end.
- `para la` (serif italic): TYPE-WRITES via clip-path inset reveal (0% → 100% from left), 0.5s, `power3.out`, at t=1.2.
- `eliminación de la malaria`: FADES in with letter-spacing 0.2em → 0 (slight squeeze), 0.6s, `power2.out`, at t=1.7.
- Bottom hairline rule: DRAWS scaleX 0→1 from right, 0.6s, `power3.out`, at t=1.9.
- `SDSS · 2026`: FADES in, 0.4s, `power2.out`, at t=2.1.
- Ghost `SENTINEL`: drifts continuously via `tl.to()` with yoyo, 8s cycle.
- Radial glow: breathes scale 1.0→1.06, 4s cycle, `sine.inOut`, yoyo.

**Transition out:** Push-up slide. The scene container translates y:0→-1350 over 0.5s with blur 0→30→0 in the middle, while the next scene container translates y:1350→0 with blur 30→0. Velocity-matched. Easing `power3.inOut`. Effect: "page turn" feel — the next scene enters from below as this one leaves upward.

### Scene 2 — The hook / reactive vs predictive (`6.5s → 13.0s`)
**Concept:** State the problem. Malaria surveillance is reactive (interventions launch after cases appear). MalariaSentinel flips that to predictive. Two short sentences, the contrast carried by a single italic emphasis word.

**Mood direction:** Editorial calm. A research brief stating its case. No drama — just clarity.

**Depth layers (9 elements):**
- BG: `#0A1419` carry-over. New radial glow centered at (200, 1100), 450px, `accent-glow`, breathe 4s.
- BG: oversized ghost word "PREDICT" at 5% opacity, anchored bottom-right, drifting up.
- BG: top hairline bar carries over.
- MG: section label `01 · EL PROBLEMA` (mono 18px, accent, 0.08em tracking).
- MG: headline `La vigilancia de malaria es` (Bricolage 700, 56px, fg).
- MG: emphasis word `*reactiva.*` (Instrument Serif italic 700 weight via selection, 72px, `warn` color #F59E0B, with a single 3px underline rule appearing under it).
- MG: connector `Nosotros la hacemos` (Bricolage 500, 48px, fg-muted).
- MG: emphasis word `*predictiva.*` (Instrument Serif italic 700, 72px, accent-bright, with the same 3px underline rule but in accent).
- FG: small data callout bottom-left: `24 sitios larvales en Ghana · 1 región piloto` (mono 18px, fg-dim, two lines).

**Animation choreography:**
- Top hairline: instant (already there from scene 1, never re-animated).
- `01 · EL PROBLEMA`: FADES in + slides x -20 → 0, 0.4s, `power2.out`, t=6.6.
- Headline: FADES in, 0.5s, `power2.out`, t=6.9.
- `reactiva.`: SLIDES in x 60→0 with opacity 0→1, 0.5s, `power3.out`, t=7.4. Underline rule scaleX 0→1 underneath, 0.4s, t=7.7.
- `Nosotros la hacemos`: FADES in, 0.4s, t=7.9.
- `predictiva.`: SLIDES in x 60→0 with opacity 0→1, 0.5s, `power3.out`, t=8.3. Underline rule scaleX 0→1, 0.4s, t=8.6.
- Data callout: FADES in, 0.4s, t=9.0.
- Ghost `PREDICT`: drifts via tl.to yoyo, 10s cycle.
- Radial glow: breathes, 4s cycle.

**Transition out:** Blur crossfade. Both scene containers cross-blur via a single shared black overlay that scales opacity 0→1→0 while both scenes are at full opacity, with `filter: blur(20px)` applied during the peak. Duration 0.4s, `power2.inOut`.

### Scene 3 — Objetivos (`13.5s → 21.0s`)
**Concept:** Four objective chips, each with a tiny mono icon, fill the lower 2/3 of the frame. Top of the frame carries the section label. Each chip enters with a different easing to vary the choreography.

**Mood direction:** Spec sheet. Clean, scannable, research-grade. The viewer can read it in 3 seconds.

**Depth layers (10 elements):**
- BG: `#0A1419`. Radial glow centered at (900, 400), 400px, breathe 4s.
- BG: top hairline bar carries.
- MG: section label `02 · OBJETIVOS` (mono 18px, accent, 0.08em tracking).
- MG: heading `Cuatro metas para el primer año` (Bricolage 700, 52px, fg).
- MG: chip 1 — `[01]` mono + `Predecir focos antes del brote` (Bricolage 500, 30px) — surface card.
- MG: chip 2 — `[02]` + `Mapear idoneidad de hábitat` — surface card.
- MG: chip 3 — `[03]` + `Simular la propagación del vector` — surface card.
- MG: chip 4 — `[04]` + `Entrenar una U-Net sustituta` — surface card.
- FG: bottom-right meta: `M1–M6 · 6 fases` (mono 18px, fg-dim).
- FG: thin vertical rule between the heading zone and chip zone (1px, `rule`, 60% height).

**Animation choreography:**
- Section label: FADES in, 0.4s, t=13.6.
- Heading: FADES in with y 20→0, 0.5s, `power2.out`, t=13.9.
- Vertical rule: scaleY 0→1 from top, 0.5s, `power3.out`, t=14.3.
- Chip 1: CASCADES in — slides y 30→0, opacity 0→1, 0.5s, `back.out(1.1)`, t=14.6.
- Chip 2: CASCADES in — slides x -40→0, opacity 0→1, 0.5s, `power3.out`, t=14.9.
- Chip 3: CASCADES in — scale 0.92→1, opacity 0→1, 0.5s, `expo.out`, t=15.2.
- Chip 4: CASCADES in — slides y 30→0, opacity 0→1, 0.5s, `power2.out`, t=15.5.
- Meta `M1–M6 · 6 fases`: FADES in, 0.4s, t=16.0.
- Radial glow breathes.

**Transition out:** Blur crossfade, 0.4s, `power2.inOut`.

### Scene 4 — Impacto (`21.5s → 29.0s`)
**Concept:** Three large stat callouts in a vertical stack. Each is one number + one short label. The "number" is the carrier — it lands with impact. The label that follows is small and supportive. The numbers are illustrative ("lo que perseguimos"), not claims.

**Mood direction:** Bloomberg-data. Three big numbers, three short interpretations. Restraint.

**Depth layers (10 elements):**
- BG: `#0A1419`. Radial glow centered at (200, 800), 500px, breathe 4s.
- BG: top hairline bar carries.
- MG: section label `03 · IMPACTO` (mono 18px, accent, 0.08em tracking).
- MG: heading `Lo que perseguimos medir` (Bricolage 700, 52px, fg).
- MG: stat 1 — `↓ antes` (Bricolage 500, 30px, fg-muted) + `30 días` (Bricolage 800, 96px, fg) + `de anticipación sobre el brote clínico` (Bricolage 500, 28px, fg-muted).
- MG: stat 2 — `↓ costo` (Bricolage 500, 30px, fg-muted) + `40%` (Bricolage 800, 96px, accent) + `menos rociado innecesario por zonificación` (Bricolage 500, 28px, fg-muted).
- MG: stat 3 — `↑ cobertura` (Bricolage 500, 30px, fg-muted) + `4 capas` (Bricolage 800, 96px, fg) + `ambientales en el modelo de idoneidad` (Bricolage 500, 28px, fg-muted).
- FG: footnote `cifras objetivo del proyecto, sujetas a validación con datos de incidencia` (mono 16px, fg-dim, italic via Bricolage 500 italic not mono).
- FG: bottom-right: `Sentinel + SDSS` (mono 18px, fg-dim).

**Animation choreography:**
- Section label: FADES in, 0.4s, t=21.6.
- Heading: FADES in y 20→0, 0.5s, t=21.9.
- Stat 1 number `30 días`: COUNTS UP from 0 to 30 (use `obj = { val: 0 }` and `tl.to(obj, { val: 30, ... })` writing to textContent), 0.8s, `power2.out`, t=22.5. Label and gloss FADE in around it.
- Stat 2 number `40%`: SLIDES in y 40→0, opacity 0→1, 0.5s, `power3.out`, t=23.7. Label and gloss FADE in.
- Stat 3 number `4 capas`: SCALES in 0.7→1, opacity 0→1, 0.5s, `expo.out`, t=24.9. Label and gloss FADE in.
- Footnote: FADES in, 0.4s, t=26.0.
- `Sentinel + SDSS`: FADES in, 0.4s, t=26.2.
- Radial glow breathes.

**Transition out:** Blur crossfade, 0.4s, `power2.inOut`.

### Scene 5 — Fases + status (HERO) (`29.5s → 38.0s`)
**Concept:** The M1–M6 timeline as a horizontal row of six bars. Each bar is labeled with a code chip (M1…M6) and a short title. M2 has a filled teal bar (complete). M3 has a filled teal bar with a pulsing dot and a "EN CURSO" tag. M1 has a partial fill (done before M2). M4–M6 are empty skeletons with the title in fg-dim. This is the visual centerpiece — gets the strongest transition in.

**Mood direction:** Project tracker. Engineering cadence. The viewer's eye lands on M2/M3 and reads outward.

**Depth layers (10 elements):**
- BG: `#0A1419`. Radial glow centered at (540, 1000), 500px, breathe 4s. Stronger alpha this scene.
- BG: top hairline bar carries.
- BG: subtle grid pattern, 80px cells, 4% opacity, fg-dim. Sits behind the timeline.
- MG: section label `04 · FASES` (mono 18px, accent, 0.08em tracking).
- MG: heading `Seis hitos, doce meses` (Bricolage 700, 52px, fg).
- MG: timeline row 1 (M1) — code chip `M1` (mono 18px, surface bg, rule border) + bar (40% fill, accent, partial) + label `Scaffolding` (Bricolage 500, 24px, fg-muted).
- MG: timeline row 2 (M2) — code chip `M2` (mono 18px, surface bg, accent border) + bar (100% fill, accent) + label `Ingesta de datos` (Bricolage 600, 24px, fg) + completion check.
- MG: timeline row 3 (M3) — code chip `M3` (mono 18px, surface bg, accent-bright border) + bar (animated filling, accent-bright) + label `Modelo de idoneidad` (Bricolage 700, 24px, fg) + pulsing dot + `EN CURSO` mono tag.
- MG: timeline row 4 (M4) — code chip `M4` (mono 18px, surface bg, rule border) + empty bar (1px rule outline) + label `Simulador` (Bricolage 500, 24px, fg-dim).
- MG: timeline row 5 (M5) — code chip `M5` + empty bar + label `U-Net` (Bricolage 500, 24px, fg-dim).
- MG: timeline row 6 (M6) — code chip `M6` + empty bar + label `Predicción y mapa` (Bricolage 500, 24px, fg-dim).
- FG: top-right status callout: `Estado` (mono 14px, fg-dim) + `M2 completa · M3 en curso` (Bricolage 600, 22px, fg, with M2 and M3 in mono accent).
- FG: connecting line from M2 to M3 (1px, accent, scaleX 0→1 from M2 endpoint to M3 endpoint, 0.6s).

**Animation choreography:**
- Section label: FADES in, 0.4s, t=29.6.
- Heading: FADES in y 20→0, 0.5s, t=29.9.
- Connecting line M2→M3: scaleX 0→1, 0.6s, `power3.out`, t=30.4.
- M1 row: bar scaleX 0→0.4, 0.5s, label FADES, 0.4s, t=30.8. Stagger 0.06s between siblings.
- M2 row: bar scaleX 0→1, 0.5s, label FADES, 0.4s, completion check FILLS in (scale 0→1, 0.4s `back.out(1.4)`), t=31.0.
- M3 row: chip border draws, bar scaleX 0→0.6 (live progress feel), 0.5s, label FADES, pulsing dot starts (1.5s cycle, infinite via `tl.to` with `repeat: 1, yoyo: true` mapped to scene duration — but the rule says no `repeat: -1`; for ambient pulse on a finite scene, use `repeat: Math.ceil(7/1.5) - 1`), `EN CURSO` tag FADES in with x 10→0, 0.4s, t=31.2.
- M4–M6 rows: each FADES in with stagger 0.15s. Bar outline scaleX 0→1, 0.4s. Label FADES, 0.4s. t=31.4, 31.55, 31.7.
- Status callout top-right: FADES in y -10→0, 0.4s, t=32.2.
- Radial glow breathes stronger this scene (scale 1.0→1.08).

**Transition out:** Blur crossfade, 0.4s, `power2.inOut`.

### Scene 6 — ANFAIA + closing (`38.5s → 45.0s`)
**Concept:** Quiet, resolved. Center the funder word. One short sentence. The GitHub link at the bottom. A final slow ambient. Then color dip to black over 0.7s.

**Mood direction:** Closing credit of a documentary. Restrained, sincere.

**Depth layers (8 elements):**
- BG: `#0A1419`. Radial glow centered at (540, 600), 600px, breathe 4s.
- BG: top hairline bar carries.
- MG: section label `05 · APOYO` (mono 18px, accent, 0.08em tracking).
- MG: small heading `Este proyecto es posible gracias a` (Bricolage 500, 32px, fg-muted, max-width 700px).
- MG: `ANFAIA` (Bricolage 800, 160px, accent) — center anchor.
- MG: small descriptor `Asociación Nacional de Físicos, [etc — placeholder, to confirm]` (Bricolage 500, 26px, fg-muted).
- FG: divider rule under ANFAIA, 80% width, 2px, accent, scaleX 0→1.
- FG: GitHub handle at bottom: `github.com/[user]/MalariaSentinel` (mono 20px, fg).
- FG: final tagline: `Ciencia abierta para la eliminación de la malaria.` (Bricolage 500 italic 28px, fg-muted, centered).

**Animation choreography:**
- Section label: FADES in, 0.4s, t=38.6.
- Small heading: FADES in y 10→0, 0.4s, t=38.9.
- `ANFAIA`: SLAMS in scale 0.85→1, opacity 0→1, 0.7s, `expo.out`, t=39.3. Stronger than other entries — this is the final anchor.
- Descriptor: FADES in, 0.4s, t=40.0.
- Divider rule: scaleX 0→1 from center, 0.5s, t=40.4.
- GitHub handle: FADES in, 0.4s, t=40.8.
- Final tagline: FADES in with letter-spacing 0.1em → 0, 0.5s, t=41.2.
- **Final scene allowed exits:** At t=44.3, all elements FADE to opacity 0 (0.6s `power2.in`). A black overlay `tl.to` opacity 0→1, 0.7s `power2.inOut` at t=44.5. Ends on black.
- Radial glow breathes.

## Recurring motifs (global)

- Top hairline bar: `MALARIA·SENTINEL · {n}/6` left, scene label right. Always visible. Drawn in once at t=0.1 on scene 1, present unchanged thereafter.
- Bottom hairline bar: present in scene 1 only (decorative anchor for the title).
- Radial teal glow: every scene. One per scene, position varies. Breathing 4s `sine.inOut` yoyo.
- Ghost word: every scene. Position + word varies (`SENTINEL`, `PREDICT`, `IDONEIDAD`, `M3`, `ANFAIA`).

## Negative prompt

- No mosquito emoji. No DNA helix. No "AI brain" or "neural network" visual clichés.
- No "innovation" / "synergy" / "leverage" / "ecosystem" language.
- No Inter, Roboto, Open Sans, Poppins, Outfit, Sora, Syne.
- No pure black `#000000` or pure white `#FFFFFF`. Use `#0A1419` and `#E8F1F4`.
- No centered-and-floating layouts. Anchor to edges.
- No full-screen linear gradients. Use radial glow + solid surface.
- No `<br>` in body copy. Use `max-width`.
- No exit animations before transitions. Transitions are the exit.
- No exit animations on the title card before the push-up transition.
