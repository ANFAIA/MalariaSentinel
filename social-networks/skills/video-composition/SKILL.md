---
name: video-composition
description: Build LinkedIn carousel/video presentations for MalariaSentinel using HyperFrames. Covers design system, HTML composition, GSAP animation, rendering, and PDF generation. Use when user says "make a LinkedIn video", "create a carousel", "generate a presentation for LinkedIn", or wants to update an existing presentation.
---

# Skill: LinkedIn Presentation Builder

Build LinkedIn carousel/video presentations for MalariaSentinel (and future projects) using HyperFrames. This skill captures David's preferences, known pitfalls, and the proven workflow.

## When to use

- User says "make a LinkedIn video", "create a carousel", "generate a presentation for LinkedIn"
- User wants to update the existing MalariaSentinel presentation
- User has new content to present on social media

## Workflow

### 1. Gather content

Before touching HyperFrames, get clear answers on:
- **What** — the message, the audience, the goal
- **Who** — LinkedIn audience (non-technical by default)
- **Format** — vertical 4:5 (1080×1350), ~45s video + PDF carousel
- **Language** — English (default for LinkedIn global audience)

### 2. Design system (design.md)

Create or update `design.md` in the project folder with:
- Palette (hex values for every token)
- Typography (font families, weights, sizes)
- Layout rules (inset, padding, vertical rhythm)
- Scene content (verbatim text for each scene)
- Constraints (what NOT to do)

### 3. Write index.html

Follow the HyperFrames skill for the HTML composition. Key rules:
- `data-composition-id="root"` on the root div
- `data-width="1080" data-height="1350" data-duration="45"`
- GSAP timeline: `paused: true`, registered on `window.__timelines["root"]`
- No `repeat: -1` — calculate exact repeat count
- No exit animations except final scene
- Every scene has entrance animations on every element

### 4. Validate

```bash
npx hyperframes check   # lint + layout + motion + contrast
```

Must pass with 0 errors. Fix contrast warnings by brightening text colors.

### 5. Render

```bash
npx hyperframes render
mv renders/<output>.mp4 render.mp4
```

### 6. Generate PDF carousel

Extract hero frames (mid-scene, when all elements visible) and build PDF:

```python
from reportlab.pdfgen import canvas
# Extract frames at scene midpoints
# Build PDF: one page per scene, 1080×1350 each
```

### 7. Clean up

Before commit:
- Remove `renders/` directory (intermediate files)
- Remove `snapshots/` directory (verification frames)
- Keep `frames/` (useful for PDF + user reference)
- Keep `render.mp4` and `carouselpdf.pdf`

---

## Palette — MalariaSentinel

User-provided: `2F404F`, `3894A1`, `F0F1EE`, `C7DAD3`

| Token | Hex | Use |
|---|---|---|
| `bg` | `#2F404F` | Primary canvas (deep slate) |
| `surface` | `#3A4D5C` | Cards, panels (~5% lighter than bg) |
| `fg` | `#F0F1EE` | Primary text (warm off-white) |
| `fg-muted` | `#C7DAD3` | Secondary text (pale sage) |
| `fg-dim` | `#B0BCC2` | Tertiary, metadata (passes WCAG on bg+glow) |
| `accent` | `#3894A1` | Brand teal — DECORATIVE ONLY (borders, glows, fills) |
| `accent-bright` | `#6EC8D4` | Text on bg — USE THIS for all text labels |
| `sage` | `#C7DAD3` | "Done" markers, stage numbers on cards |

### Critical contrast rule

`accent` (#3894A1) on `bg` (#2F404F) = 3.01:1 — **fails WCAG AA** for text.
`accent-bright` (#6EC8D4) on `bg` = ~5.0:1 — **passes**.

**Always use `var(--accent-bright)` for text on the dark bg.** Reserve `var(--accent)` for decorative elements (borders, fills, glows, divider lines).

---

## Typography

- **Display:** Space Grotesk 600/700 — headlines, project name
- **Body:** Space Grotesk 400/500 — descriptions
- **Mono:** JetBrains Mono 400/500 — metadata, labels, codes
- Font files in `fonts/` directory (woff2)

---

## Content preferences (David's rules)

### Audience

LinkedIn = **non-technical**. The viewer is a researcher, recruiter, funder, or program officer — NOT a malaria specialist, NOT an engineer.

### Tone

- Honest about limitations. "Today we have something. Not what we want yet."
- No hype. No "game-changer", no "thrilled to announce".
- Technical details only when they serve the story.
- First person when appropriate.

### ANFAIA

ANFAIA = **Asociación Nacional Faro, para la Aceleración de la Inteligencia Artificial**

- Tagline: **"Driving Progress with Artificial Intelligence"**
- NOT "asociación contra la malaria" — that's wrong
- NOT "Open science for malaria elimination" as the ANFAIA tagline
- MalariaSentinel is one of their Summer Scholarships projects
- Focus areas: Culture · Health · Robotics · Sustainability · Ethics
- Closing should say: "This project is made possible by ANFAIA"

### Countries

- Don't mention specific countries (Ghana, etc.) as the sole target
- The system is designed for **any endemic region**
- If mentioning a country, frame it as "we started here" not "this is for here"

### Status / metrics

- The system is **green** — don't show cifras of improvement
- Don't show M0/M1/M2/M-perf F1 milestone codes — the audience doesn't know them
- Don't show C++ constants, code operations, or architecture details
- DO show: what the system does, how it works conceptually, where it's going

### Ghost words (background decoration)

- Must be in **English** (FLOW, not FLUJO)
- 5-6% opacity, oversized, positioned at canvas edge
- Different word per scene (SENTINEL, PIPELINE, FLOW, REGION, NOW, THANKS)

---

## Pitfalls we hit (and how to avoid them)

### 1. Ghost word language mismatch
**Problem:** Ghost word was "FLUJO" (Spanish) in an English presentation.
**Fix:** Always match ghost word language to presentation language. Check ALL ghost words before render.

### 2. ANFAIA subtitle wrong
**Problem:** Used "Open science for malaria elimination" as ANFAIA's tagline.
**Fix:** ANFAIA's tagline is "Driving Progress with Artificial Intelligence". Their full name is "Asociación Nacional Faro, para la Aceleración de la Inteligencia Artificial". Always verify funder identity from their website.

### 3. "PREDICCIÓN" left in Spanish
**Problem:** One pipeline stage name was missed during translation.
**Fix:** After translation, grep for ALL remaining non-English text: `grep -rn '[áéíóúñ¿¡]' index.html`

### 4. WCAG contrast failures on accent color
**Problem:** `accent` (#3894A1) on `bg` (#2F404F) = 3.01:1 — fails AA for text.
**Fix:** Use `accent-bright` (#6EC8D4) for all text. Reserve `accent` for decorative only. Run `npx hyperframes check` — it reports contrast warnings.

### 5. Footer text clipped at canvas edge
**Problem:** Footer elements with `left: 0; right: 0` rendered outside the padded content area.
**Fix:** Use `left: 120px; right: 120px` on all absolute-positioned footer elements to respect the 120px padding.

### 6. Country mentioned as sole target
**Problem:** "Ghana" appeared in scene descriptions — misleading, the system is for any region.
**Fix:** Remove country-specific references. Frame as "any endemic region" or "any country".

### 7. Technical content for non-technical audience
**Problem:** Showing M0/M1/M2 milestones, C++ constants, U-Net architecture — meaningless to LinkedIn audience.
**Fix:** Translate to concepts: "satellite watches → simulation thinks → model learns → prediction warns". No code, no constants, no architecture diagrams.

### 8. "Monthly maps" vs actual capability
**Problem:** Said "monthly maps" but the system generates daily time series.
**Fix:** Say "time series, day by day. As far into the future as you want to look." Be accurate about capabilities.

### 9. Missing "model learns" step
**Problem:** Original flow was 3 pieces (satellite → simulation → map). Missing the crucial step where simulation trains the model.
**Fix:** 4 pieces: satellite watches → simulation thinks → **model learns** → prediction warns. The simulation generates data that trains the fast model.

### 10. Render not updated after HTML change
**Problem:** Changed HTML but forgot to re-render — old video/PDF still shown.
**Fix:** Always re-render AND regenerate PDF after any content change. `npx hyperframes render` then extract frames + reportlab.

### 11. Overlapping GSAP tweens on bg-glow
**Problem:** Duplicate `tl.to()` calls for the same element at different times caused motion warnings.
**Fix:** Search for duplicate selectors in the timeline. Remove the older one.

### 12. Running header counter not updated
**Problem:** Scene counter timestamps in the GSAP timeline didn't match actual scene start times after re-timing.
**Fix:** When moving scene boundaries, update BOTH the transition tweens AND the counter `stages` array.

---

## Scene structure (MalariaSentinel)

| # | Title | Content |
|---|---|---|
| 1 | Title | MalariaSentinel — Spatial Decision Support System — for malaria elimination |
| 2 | Pipeline | 6 stages: INGESTA → SUITABILITY → ABM → DATASET → U-NET → PREDICTION |
| 3 | The System | 4 cards: satellite watches → simulation thinks → model learns → prediction warns |
| 4 | Where We're Going | Headline: "You give it a region. It gives you a risk map." + 3 points |
| 5 | Where We Are | Honest: TODAY (basic, one region) → NOW (improving, full life cycle) |
| 6 | Closing | ANFAIA + "Driving Progress with AI" + GitHub + "Built with agentic AI" |

---

## Reference files

- `Carousel Base Idea/index.html` — the HyperFrames composition
- `Carousel Base Idea/design.md` — the full design system
- `Carousel Base Idea/render.mp4` — the rendered video (45s, 1080×1350)
- `Carousel Base Idea/carouselpdf.pdf` — the LinkedIn carousel PDF (6 pages)
- `linkedin-post` skill — template for the accompanying LinkedIn text post

---

## Future projects

When building a new presentation for a different project:
1. Copy the palette and typography from this skill (or let user define new ones)
2. Follow the same content preferences: non-technical, honest, no hype
3. Verify funder/partner identity from their website
4. Run the full check pipeline: `npx hyperframes check` -> render -> PDF -> clean -> commit
5. Update this skill with any new pitfalls discovered
