# Design: MalariaSentinel — LinkedIn Presentation

## What this is

6-scene LinkedIn video introducing the **MalariaSentinel** project — a Spatial Decision Support System (SDSS) for malaria elimination, funded by ANFAIA. Source of truth: `docs/abm-status.md` (ABM Python v0.5.0, ABM C++ mal-abm-fast F1 complete, 71+60+5 tests passing).

Format: vertical 4:5 (1080×1350), ~45s total. A linked PDF export reuses the same scene layouts for a LinkedIn carousel.

## Brand source

- **Repo identity:** `ANFAIA/MalariaSentinel` — a research-engineering project by David Flórez M., following the SDSS framework of Kelly et al. (2012).
- **Tone:** serious, evidence-driven, technical but accessible. The viewer is a researcher, recruiter, funder, or program officer on LinkedIn — not necessarily a malaria specialist.
- **Voice:** Spanish (the user brief is in Spanish; ANFAIA is the funder; LinkedIn audience LATAM + EU).
- **Reference text** (verbatim from `docs/abm-status.md`):
  - Project name: `MalariaSentinel`
  - Tagline: `Sistema de Soporte de Decisiones Espacial`
  - Subtitle: `para la eliminación de la malaria`
  - Funder: `Con el apoyo de ANFAIA`
  - Stack: `ABM Python v0.5.0` · `ABM C++ mal-abm-fast F1`
  - Tests: `71/71 Python + 60/60 C++ + 5/5 parity`
  - Pipeline: `INGESTA → SUITABILIDAD → ABM → DATASET → U-NET → PREDICCIÓN`

## Palette — "Slate & sage" (cool, calm, evidence-led)

A four-color palette from the user, expanded with derived shades for depth.

| Token             | Hex        | Use                                            |
|-------------------|------------|------------------------------------------------|
| `bg`              | `#2F404F`  | Primary canvas. Deep slate, calm and grounded — not pure black. |
| `surface`         | `#3A4D5C`  | Raised zones, cards, panels. ~5% lighter than bg. |
| `surface-2`       | `#455A6A`  | Deeper raised (chips, callouts on top of surface). |
| `fg`              | `#F0F1EE`  | Primary text. Warm off-white, no pure white. |
| `fg-muted`        | `#C7DAD3`  | Secondary text, labels, captions. The pale sage is intentionally warm-leaning. |
| `fg-dim`          | `#8FA0A8`  | Tertiary, dividers, monospace metadata. Blended fg + bg. |
| `accent`          | `#3894A1`  | Brand accent — sophisticated teal. Used for headlines, current-state markers, the project mark. |
| `accent-bright`   | `#4FB0BC`  | Highlighted elements, animated dots, current pulses. |
| `accent-glow`     | `rgba(56, 148, 161, 0.20)` | Atmospheric radial glows. |
| `accent-glow-soft`| `rgba(56, 148, 161, 0.10)` | Subtle washes. |
| `sage`            | `#C7DAD3`  | "Done" state marker, secondary highlight, callouts. |
| `rule`            | `rgba(240, 241, 238, 0.10)` | Hairline rules, borders. |
| `rule-strong`     | `rgba(240, 241, 238, 0.20)` | Stronger dividers. |

**Tint rule:** every neutral sits on the slate→sage spectrum. The palette is intentionally cool-but-warm: slate bg + teal accent + sage secondary + warm off-white fg. No red, no orange — that palette is for warnings, not for a calm research briefing.

**Semantic mapping** (used in the timeline scene):
- **Done** (M0, M1, M2, M-perf F1) → `sage` chip + `accent` check
- **Current / live** (none in this presentation — M3 is the next target, not started) → `accent` chip + `accent-bright` dot
- **Pending** (M3–M6) → `fg-dim` chip, empty bar

## Typography

Two voices — sans for everything, mono for data/tech.

| Role               | Family              | Weight       | Use                                              |
|--------------------|---------------------|--------------|--------------------------------------------------|
| **Display**        | `Space Grotesk`     | 600/700      | Headlines, scene titles, project name, big numbers. |
| **Italic accent**  | `Space Grotesk`     | 600 italic   | One emphasis word per scene (e.g., "*abierto*", "*100×*"). |
| **Body**           | `Space Grotesk`     | 400/500      | Body, descriptions, supporting copy.             |
| **Mono**           | `JetBrains Mono`    | 400/500      | Milestone codes (M1–M6), constants, technical labels, version strings, GitHub handle. |

**Sizes** (vertical 4:5, 1080×1350):

| Element                  | Size    | Notes                                    |
|--------------------------|---------|------------------------------------------|
| Scene title (h1)         | 110–120px | Max 2 lines, weight 700                |
| Section heading (h2)     | 56–64px |                                          |
| Body                     | 28–32px | line-height 1.3                          |
| Stat number (hero)       | 96–120px | The focal element of a stat scene      |
| Label / caption          | 20–22px | `fg-muted`                               |
| Mono / metadata          | 16–20px | uppercase, letter-spacing 0.16–0.20em   |
| Italic emphasis          | 64–72px | One word, Space Grotesk italic          |

**Dark-bg compensation:** body uses weight 400 (not 350), `line-height` 1.3+, display headlines get `letter-spacing: -0.025em` to compensate for light halos. Since the bg is medium-dark (not deep black), fg weights can be a touch lighter.

## Layout primitives

- **Frame:** 1080×1350. Safe inset 80px from each edge.
- **Content anchor:** left-aligned at x=120. Right column for data/metadata.
- **Vertical rhythm:** top third for label/title zone; middle for primary content; bottom third for footer/status/ANFAIA.
- **Split frame** is the default layout — left column (60%) for prose/headline, right column (40%) for data/diagram/decorative.
- **Top hairline bar** in every scene at y=80: `mono` text + thin rule. Functions as a "running header" tying the deck together.

## Density rules (per scene, 1080×1350)

Every scene has 8–10 visual elements across 3 layers:

- **Background (2–5 decoratives):** radial teal glow (one per scene, varying position), faint oversized ghost-type word at 5–6% opacity, hairline rules, grid pattern (subtle, 80px cells at 3% opacity).
- **Midground (3–5 elements):** the actual content — headlines, stat cards, milestone bars, pipeline chips, code blocks.
- **Foreground (2–3 accents):** current-state markers, "M3" callout, project mark, ANFAIA wordmark.

## Motion signature

- **Energy:** medium. Research-briefing pacing. Not a hype reel.
- **Default entrance:** 0.4–0.6s, `power3.out` (responsive, decisive). Stat number count-ups: 0.6–0.8s `power2.out`.
- **Ambient decoratives:** one shared slow breathe (3–4s cycle, ±2% scale) on the radial glow per scene. Each scene also has one scene-specific ambient (drift, pulse).
- **Stagger:** 80–120ms between siblings. Never more than 500ms total stagger.
- **Transitions:**
  - Scene 1 → 2: push-up slide (0.5s, `power3.inOut`) — sets the visual language.
  - Scene 2 → 3 → 4 → 5: blur crossfade (0.4s, `power2.inOut`) with dark overlay peak at 55%.
  - Scene 5 → 6: blur crossfade.
  - Final scene 6: dip to black (0.7s) — exit animation allowed only here.

## Recurring motifs

- **Top hairline bar** with the project mark `MALARIA·SENTINEL` (mono, 18px, `fg-dim`) on the left and scene counter `01/06` on the right. Present in every scene, never re-animated — it's the visual thread.
- **Teal radial glow** anchored bottom-right (or rotating position per scene), breathing at 4s cycle.
- **Milestone code chip:** `font-family: JetBrains Mono; background: surface; border: 1px solid rule; padding: 4px 10px; border-radius: 4px;` — appears for every M1–M6 reference.
- **Stat number** is always Space Grotesk 700 with a unit in 48% size and `fg-muted` color, `letter-spacing: -0.045em`.
- **Sage (`C7DAD3`) checkmark** for completed items — the only use of the pale sage in the timeline.

## Constraints / Don'ts

- No malaria-red. No medical-cross iconography. No mosquito emoji.
- No stock "AI brain" visuals.
- No "innovation" / "synergy" / generic SaaS language. Speak the project's own words: SDSS, suitability, U-Net surrogate, mal-abm-fast, xoshiro256**, M2, M-perf F1.
- No Inter, Roboto, Open Sans, Poppins, Outfit, Sora, Playfair Display, Syne.
- No full-screen linear gradients on dark (H.264 banding). Use radial glow + solid surface.
- No `<br>` in body copy. Use `max-width` to wrap.
- No exit animations before transitions. Transitions are the exit.
- Never use `warn`/orange — the palette is calm. Use `sage` for "done" and `accent` for "current/highlight".

## Scene content (audience: LinkedIn — non-technical)

### Scene 1 — Title
- `MalariaSentinel`
- `Sistema de Soporte de Decisiones Espacial`
- `para la eliminación de la malaria`
- Meta: `v0.5.0 Python · F1 C++ · Open Source`

### Scene 2 — El pipeline SDSS
Headline: `Del satélite al mapa de riesgo.`
Six-stage flow (kept technical — this is the bridge to scenes 3-5):
1. `INGESTA` — CHIRPS, ERA5, MERIT DEM, JRC GSW, MODIS, WorldCover
2. `SUITABILIDAD` — TWI, modelo de idoneidad
3. `ABM` — motor C++ (xoshiro256**, 7 ops/día)
4. `DATASET` — pares (state_t + env) → state_{t+1}
5. `U-NET` — 32→64→128→256→512, MSE + soft-Dice
6. `PREDICCIÓN` — risk maps mensuales, FastAPI

### Scene 3 — El sistema en 3 capas
Headline: `Tres piezas que trabajan juntas.`
Three cards with connectors (no technical jargon):
- **01 — El satélite mira.** Imágenes del espacio, clima, mapas de agua. Lo que ya sabemos del terreno.
- **02 — La simulación piensa.** Un programa imagina cómo se mueven los mosquitos. Lento pero preciso.
- **03 — El mapa avisa.** Un mapa mensual que dice dónde puede haber riesgo. En minutos.
Connectors: `alimenta` (1→2), `enseña a` (2→3).

### Scene 4 — A dónde vamos
Headline: `Le das una región. Te devuelve un mapa de riesgo.`
Three points (the value proposition, no cifras):
- Cualquier país, cualquier zona endémica. El sistema se adapta.
- Cada mes, un mapa nuevo con la expansión probable del mosquito.
- Listo para el personal de salud, antes de que llegue el brote.

### Scene 5 — Dónde estamos
Honest admission: `Hoy tenemos algo. Todavía no lo que queremos.`
Two columns (HOY / AHORA) connected by an arrow:
- **HOY**: Una primera versión que funciona con datos reales de Ghana. La simulación es básica — solo dos etapas de vida del mosquito. Las señales son simples: lluvia y agua. Solo sirve para una región.
- **AHORA**: Mejorando la simulación para que el sistema funcione de verdad. Ciclo de vida completo del mosquito. El mosquito que busca comida, pone huevos, transmite. Para que sirva en cualquier sitio, no solo Ghana.

### Scene 6 — Cierre
- Section: `05 · APOYO`
- Lead: `Este proyecto es posible gracias a`
- Wordmark: `ANFAIA`
- Tagline: `Ciencia abierta para la eliminación de la malaria.`
- Foot:
  - `github.com/ANFAIA/MalariaSentinel`
  - `SDSS · Open Source · 2026`
  - `Sistema construido con ayuda de sistemas agénticos` (italic, fg-dim)
