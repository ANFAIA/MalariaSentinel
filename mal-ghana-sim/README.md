# MalariaSentinel

## *Artificial Intelligence System for Predictive Malaria Surveillance*

---

## 1. The Problem or Challenge to Address

Malaria remains one of the leading causes of mortality in tropical regions, exacerbated by climate change, which alters the breeding patterns of the *Anopheles* mosquito. The main challenge lies in the **reactive** nature of current health systems: interventions (spraying, supply distribution) are typically launched only after clinical cases are detected, when the outbreak is already in its expansion phase.

A critical gap exists between the availability of satellite environmental data (climate, humidity, vegetation) and its practical application in local health decision-making. The lack of accessible predictive tools prevents authorities from prioritizing limited resources in the micro-zones that will actually become infection hotspots in the weeks ahead.

---

## v1 Demo Status & Known Limitations (Ghana, 2026-07)

The v1 pipeline runs end-to-end: **env-raster ingestion → habitat suitability → reaction-diffusion simulator (teacher) → U-Net transition surrogate → risk-expansion map.** This is a proof-of-pipeline, not a validated predictor. Honest limitations:

**Data layers (M2).** 4 of 5 env layers downloaded and reprojected to a common EPSG:32630 @1 km grid: SRTM elevation, WorldClim 2.1 BIO1 (temperature) + BIO12 (rainfall), JRC Global Surface Water (occurrence). **MODIS NDVI was not fetched** — MOD13A2 / the new ECOSTRESS ECO_L2T_STARS NDVI both require a (free) NASA Earthdata login; with no NDVI, its 0.15 suitability weight is auto-redistributed. To enable NDVI: set `EARTHDATA_USER`/`EARTHDATA_PASS` and wire AppEEARS in `malariasim/ingest.py:fetch_modis_ndvi`.

**Habitat suitability (M3) — AUC 0.334, 95% CI [0.19, 0.50]** (criterion was lower-95% > 0.65). The model ranks wet/vegetated lowlands highest, but the 24 larval survey sites are mostly in a drier seasonal-savanna transect (Tolon/Accra corridor) where breeding happens in **small, sub-1 km water bodies the 1 km water layer cannot resolve.** This is the documented v1 resolution limit, not a code bug (per-layer AUC confirmed elevation was correctly inverted, water ≈ random at 1 km). **v1.5 fix:** MaxEnt (via `elapid`) with spatial thinning + a finer water layer (JRC at 30 m aggregated to ~250 m, or a flow-accumulation hydrography proxy).

**Simulator (M4) — works.** Fisher-KPP reaction-diffusion with temperature-gated reproduction `r(T)=r_max·max(0,1−((T−25)/8)²)` (Mordecai 2013), temperature-dependent mortality, soft water factor, 4-neighbour diffusion (μ=0.2, stable). Seeded from the larval sites + a point source; produces visible spreading fronts (12 frames/rollout saved). **Dynamics are NOT validated against reality** — v1 env is static climatological normals and dynamics vary only by parameter randomization. Real grounding requires temporal malaria-incidence field data (the v1.5 calibration hook).

**U-Net surrogate (M5) — learns, but weak: best val Dice 0.24** (criterion was > 0.6). The loop trains and the Dice rises (0 → 0.24), but it is data- and compute-limited on this workstation: only ~70 training presence-patches from 20 rollouts (the spread is sparse/local, so presence-filtered patches are few), and CPU/MPS conv training is slow (MPS was ~4 s/batch for a BatchNorm U-Net; CPU used instead). Scaling to the design's ≥100 rollouts + a real GPU + the larger (32,64,128,256) U-Net is the straightforward path to the 0.6 bar.

**Unrolled inference (M6) — diverges.** Rolling the trained U-Net forward step-by-step over the full image over-spreads (sim: ~9 occupied cells from a single seed; U-Net: ~6000) → front-overlap Dice ≈ 0. Patch-based training does not constrain full-image unrolled rollout. **v1.5 fix:** train with recurrent/teacher-forcing on unrolled sequences, or add a stability constraint (mass conservation / normalization) to the rollout; or use the U-Net only for single-step `t→t+T` prediction, not multi-step rollout.

**Artifacts.** `runs/suitability_static.png` (v1 risk map), `runs/sim_rollout.png` (spreading fronts), `runs/risk_expansion.png` (sim vs U-Net, side-by-side), `runs/unet_best.pt` (checkpoint, Dice 0.24).

**How to run.** `uv run python scripts/01_ingest.py --download` (one-time) → `02_suitability.py` → `03_simulate.py` → `05_train.py [n_rollouts] [epochs]` → `06_predict_and_map.py`. Full design: `DESIGN.md`.


