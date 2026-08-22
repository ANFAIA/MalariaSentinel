# MalariaSentinel — ABM flow video

**Format:** 1080 x 1350, vertical 4:5, 60 seconds.
**Purpose:** Explain how environmental data becomes mosquito ecology output and, later, malaria risk intelligence.
**Audience:** Researchers, public-health practitioners, funders, and builders.

## Visual language

- `bg`: #15222E (slate dark blue)
- `bg-deep`: #0D1720
- `surface`: rgba(27, 43, 57, 0.9)
- `fg`: #F1F5F9
- `muted`: #CBD5E1
- `dim`: #94A3B8
- `accent`: #0EA5E9 (cyan blue)
- `bright`: #38BDF8 (electric sky)
- `neon`: #5EE2E6 (glow active)
- `mint`: #34D399 (verified state)
- Font: Space Grotesk (local WOFF2)
- Monospace: system monospace

## Story

1. 0-7s: Stage 01 · Multi-Source Signals. 6 heterogeneous environmental streams (ERA5 Climate, DEM Topography, Copernicus Land, Hydrology, WorldPop Hosts, DHIS2 Surveillance) converge into the Ingestion Engine conduit.
2. 7-17s: Stage 02 · Ingestion Pipeline & Standardization. Connection to the Ingestion Engine: manifest integrity validation, 10km standard grid tensor resampling, and dynamic breeding suitability index $S(x,y,t)$.
3. 17-45s: Stage 03 · Simulation Engine. Hero ABM run across 731 days in Ghana (2024–2025).
   - Top: 6 mechanistic physical & biological model drivers (Thermal development Brière-1, Pool hydrology Penman-Monteith, Gonotrophic cycle, Wind dispersal, Host preference, Washout & mortality).
   - Video with Vox-style callout annotations (Map, Aquatic development, Adult population) that highlight the components, then fade out for clean simulation run.
   - Bottom: Simple direct explanation for non-experts.
4. 45-54s: Stage 04 · Surrogate AI. Distilling 731 days of synthetic ABM data into fast spatial neural surrogates (<50ms, 10,000x acceleration).
5. 54-60s: Stage 05 · Active Roadmap & Horizons.
   - Immediate next step: SEI vector sporogony + SEIR human transmission model coupling.
   - Neural operator integration (U-Net, FNO).
   - Multi-species expansion (*An. funestus*, *An. gambiae s.s.*) and field validation.

## Motion

One oversized horizontal rail carries logical blocks. The camera travels left to right instead of cutting between slides. Input packets converge into INGEST, then continue through the pipeline. Each stop is a single vertical mobile-safe panel without an outer slide frame. The ABM asset is a full-width video clip layered over its slot; the camera settles and zooms into it before continuing.

## Honest framing

Current ABM models mosquito ecology and spatial population dynamics. Full vector infection + human SEIR coupling and field validation remain next steps.
