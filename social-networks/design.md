# Design: MalariaSentinel — LinkedIn Presentation

## What this is
6-scene LinkedIn video introducing the MalariaSentinel project (Spatial Decision Support System for malaria elimination, funded by ANFAIA). Format: vertical 4:5 (1080×1350), ~45s total. A linked PDF export reuses the same scene layouts for a LinkedIn carousel.

## Brand source
- **Repo identity:** `ANFAIA-MalariaSentinel` (the user is a research-engineer building an SDSS for malaria elimination, following Kelly et al. 2012).
- **Tone:** serious-but-accessible. The viewer is a professional on LinkedIn — a researcher, recruiter, or funder. Not a malaria specialist.
- **Voice:** Spanish (the user wrote the brief in Spanish; ANFAIA is the funder; LinkedIn audience likely LATAM + EU).

## Palette — "Scientific teal" (dark, premium, research briefing)

| Token             | Hex        | Use                                            |
|-------------------|------------|------------------------------------------------|
| `bg`              | `#0A1419`  | Primary canvas. Very dark blue-charcoal, hint of teal in undertone (NOT pure black). |
| `surface`         | `#0F1C25`  | Cards, panels, raised zones.                  |
| `fg`              | `#E8F1F4`  | Primary text. Cool off-white, not pure white.  |
| `fg-muted`        | `#8A9AA3`  | Secondary text, labels, captions.              |
| `fg-dim`          | `#5A6B73`  | Tertiary, dividers, monospace metadata.       |
| `accent`          | `#14B8A6`  | Brand accent — sophisticated teal. Hints at water / vector without malaria-red cliché. |
| `accent-bright`   | `#2DD4BF`  | Highlighted elements, current-state markers.   |
| `accent-glow`     | `rgba(20, 184, 166, 0.18)` | Atmospheric radial glows.        |
| `rule`            | `rgba(232, 241, 244, 0.10)` | Hairline rules, borders.         |
| `warn`            | `#F59E0B`  | Sparingly — "current" phase marker.            |

Tint rule: every neutral is pushed toward teal-cyan. Dead gray is forbidden — `fg-muted #8A9AA3` has a measurable cool tint, `fg-dim #5A6B73` has a slight blue-green cast.

## Typography

Two voices — sans for everything, mono for data/tech. No serif (renderer font list doesn't include one; a sans-italic accent is used for emphasis words instead).

| Role               | Family              | Weight       | Use                                              |
|--------------------|---------------------|--------------|--------------------------------------------------|
| **Display**        | `Space Grotesk`     | 600/700      | Headlines, scene titles, project name.           |
| **Italic accent**  | `Space Grotesk`     | 600 italic   | One emphasis word per scene (e.g., "*antes*", "*M3*"). |
| **Body**           | `Space Grotesk`     | 400/500      | Body, descriptions, supporting copy.             |
| **Mono**           | `JetBrains Mono`    | 400/500      | Milestone codes (M1–M6), coordinates, technical labels, GitHub handle. |

Sizes (vertical 4:5, 1080×1350):

| Element                  | Size  | Notes                                    |
|--------------------------|-------|------------------------------------------|
| Scene title (h1)         | 120px | Max 2 lines, weight 700                  |
| Section heading (h2)     | 64px  |                                          |
| Body                     | 32px  | line-height 1.3                          |
| Label / caption          | 22px  | `fg-muted`                               |
| Mono / metadata          | 18px  | uppercase, letter-spacing 0.18em        |
| Italic emphasis          | 64–96px | One word, Space Grotesk italic       |

Dark-background compensation: body uses weight 400 (not 350), `line-height` 1.3+, display headlines get `letter-spacing: -0.02em` to compensate for light halos.

## Layout primitives

- **Frame:** 1080×1350. Safe inset 80px from each edge.
- **Content anchor:** left-aligned at x=120. Right column for data/metadata.
- **Vertical rhythm:** top third for label/title zone; middle for primary content; bottom third for footer/status/ANFAIA.
- **Split frame** is the default layout — left column (60%) for prose/headline, right column (40%) for data/diagram/decorative.
- **Top hairline bar** in every scene at y=80: `mono` text + thin rule. Functions as a "running header" tying the deck together.

## Density rules (per scene, 1080×1350)

Every scene has 8–10 visual elements across 3 layers:

- **Background (2–5 decoratives):** radial teal glow (one per scene, varying position), faint oversized ghost-type word at 6% opacity, hairline rules, grid pattern (subtle, 60px cells at 4% opacity).
- **Midground (3–5 elements):** the actual content — headlines, stat cards, milestone bars, lists.
- **Foreground (2–3 accents):** current-state markers, "M3" callout, project mark, ANFAIA wordmark.

## Motion signature

- **Energy:** medium. Corporate research-briefing pacing. Not a hype reel.
- **Default entrance:** 0.4–0.6s, `power3.out` (responsive, decisive). Exits 0.25–0.35s `power2.in`.
- **Ambient decoratives:** one shared slow breathe (3–4s cycle, ±2% scale) on the radial glow per scene. Each scene also has one scene-specific ambient (drift, pulse, orbit).
- **Stagger:** 80–120ms between siblings. Never more than 500ms total stagger.
- **Transitions:** primary = blur crossfade (0.4s, `power2.inOut`). Accent = push-up slide at the title→scene-2 boundary (sets the visual language). Final scene = color dip to black.

## Recurring motifs

- **Top hairline bar** with the project mark `MALARIA·SENTINEL` (mono, 18px, `fg-dim`) on the left and scene number on the right. Present in every scene, never re-animated — it's the visual thread.
- **Teal radial glow** anchored bottom-right, breathing at 4s cycle.
- **Milestone code chip:** `font-family: JetBrains Mono; background: surface; border: 1px solid rule; padding: 4px 10px; border-radius: 4px;` — appears for every M1–M6 reference.
- **Current marker:** filled teal dot with a 1px teal ring expanding from it (pulse, 1.5s cycle) on the M2/M3 phase scene.

## Constraints / Don'ts

- No malaria-red. No medical-cross iconography. No mosquito emoji.
- No stock "AI brain" visuals.
- No "innovation" / "synergy" / generic SaaS language. Speak the project's own words: SDSS, suitability, U-Net surrogate, M2, M3.
- No Inter, Roboto, Open Sans, Poppins, Outfit, Sora, Playfair Display, Syne.
- No full-screen linear gradients on dark (H.264 banding). Use radial glow + solid surface.
- No `<br>` in body copy. Use `max-width` to wrap.
- No exit animations before transitions. Transitions are the exit.

## Reference text (used verbatim in scenes)

- Project name: `MalariaSentinel`
- Tagline: `SDSS para la eliminación de la malaria`
- Funder: `Con el apoyo de ANFAIA`
- Milestones (verbatim from the project's design doc):
  - M1 — Scaffolding
  - M2 — Ingesta de datos
  - M3 — Modelo de idoneidad
  - M4 — Simulador de propagación
  - M5 — Entrenamiento de la U-Net
  - M6 — Predicción y mapa de riesgo
- Status: `M2 completa · M3 en curso`
