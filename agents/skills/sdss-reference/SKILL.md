---
name: sdss-reference
description: Domain knowledge for the MalariaSentinel SDSS (Sentinel/Centinela). Covers the Kelly et al. 2012 framework, malaria elimination concepts, the decision pipeline, intervention modeling, and how the codebase maps to the SDSS components. Use when you need domain context to make informed development decisions.
---

# SDSS Reference — MalariaSentinel Domain Knowledge

## 1. What the Centinela Is

The **Centinela** (Sentinel) is the engineering realisation of the Spatial Decision Support System (SDSS) for malaria elimination proposed by **Kelly et al. (2012)** in *Trends in Parasitology*. The original paper argues that as malaria programmes transition from control to elimination, they need integrated spatial decision support that combines:

- **Surveillance** — high-resolution location-based case detection and monitoring
- **Targeted interventions** — focal IRS, universal LLIN distribution, active case detection
- **Service delivery** — risk maps, real-time dashboards, supply chain visibility

The Centinela extends this framework with modern methods: agent-based modelling, neural network surrogates, and a knowledge graph for accumulating project decisions across sessions.

**Reference**: `papers/spatial-analysis/MalariaEliminationWithSpatialDecisionSupportSystems.md`

---

## 2. Core Concepts

### Malaria Elimination vs Control

| Phase | Goal | Surveillance mode |
|---|---|---|
| **Control** | Reduce burden to manageable levels | Passive case reporting at health facilities |
| **Pre-elimination** | Push incidence below a threshold | Enhanced surveillance, active case detection begins |
| **Elimination** | Zero local transmission in a defined area | Case investigation, focal response, importation monitoring |
| **Prevention of reintroduction** | Maintain zero transmission post-elimination | Importation surveillance, rapid response |

Elimination is **not** eradication. Elimination is regional zero transmission; eradication is global.

### Spatial Decision Support

A SDSS provides computerised support for decisions with a geographic component (Keenen 2003). The Kelly 2012 conceptual framework (Figure 2) has four key elements:

1. **Data inputs** — routine HIS data, field surveys (GR), baseline GIS layers, expert knowledge
2. **Automated outputs** — tabular reports, statistical/spatial analysis, graphical maps
3. **Cyclical re-entry** — intervention outcomes feed back into the SDSS
4. **Expert knowledge** — integrated throughout all stages

### Surveillance-to-Action Pipeline

Malaria risk is spatially heterogeneous. The pipeline:

```
Data ingestion → Spatial analysis → Risk mapping → Targeted intervention → Impact assessment → (loop)
```

Each stage requires location awareness — household-level mapping, georeferenced cases, and high-resolution environmental layers.

---

## 3. The Decision Pipeline

The Centinela implements a 5-stage pipeline:

```
┌─────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  Ingest &   │ →  │  Suitability │ →  │  Simulation  │ →  │  Prediction  │ →  │  Risk Maps & │
│  Curate     │    │  Modeling    │    │  (ABM / KPP) │    │  (U-Net)     │    │  Dashboards  │
└─────────────┘    └──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
     ↑                                                                              │
     └──────────────────── Feedback (new cases, intervention outcomes) ──────────────┘
```

| Stage | SDSS element | What it does |
|---|---|---|
| **Ingest** | Data inputs | Reproject & resample environmental rasters (DEM, water, rainfall, temperature, NDVI) to a common grid |
| **Suitability** | Spatial analysis | Weighted overlay + Mordecai thermal curve → carrying-capacity field K |
| **Simulation** | Modeling | Agent-based model or Fisher-KPP reaction-diffusion simulator predicts population spread |
| **Prediction** | Automated outputs | U-Net surrogate approximates ABM for fast scenario exploration |
| **Risk maps** | Decision support | Side-by-side simulator vs U-Net risk-expansion maps; intervention coverage maps |

---

## 4. Key Domain Terms

### Vector Biology

| Term | Definition | Relevance |
|---|---|---|
| **EIP (Extrinsic Incubation Period)** | Time for *Plasmodium* to develop from ingested oocysts to infectious sporozoites in the mosquito. Temperature-dependent; ~110 growing-degree-days (T > 16°C). | Gates whether a mosquito becomes infectious. Longer EIP = fewer infectious mosquitoes. |
| **Gonotrophic cycle** | Blood-feeding cycle: gonotrophic discordance affects biting frequency and adult mortality. | Calibrates biting rate and survival parameters in the ABM. |
| **Biting rate (a)** | Average number of human bites per mosquito per day. Typically 0.3–0.5 for *An. gambiae*. | Core transmission parameter; drives R₀. |
| **Sporozoite rate (SR)** | Fraction of dissected mosquitoes with salivary gland sporozoites. | Empirical measure of transmission intensity. |
| **OIR (Entomological Oocyst Rate)** | Fraction of mosquitoes with oocysts in the midgut. | Intermediate measure of parasite development. |
| **Adult mortality rate (μ)** | Daily probability of adult mosquito death. ~0.1–0.3/day for *An. gambiae*. | High mortality truncates EIP; reduces transmission potential. |

### Epidemiological Parameters

| Term | Definition |
|---|---|
| **R₀ (Basic Reproduction Number)** | Average secondary infections from one infected person in a fully susceptible population. R₀ > 1 → epidemic. |
| **R_eff (Effective R₀)** | R₀ adjusted for immunity, interventions, and population structure. |
| **Incidence** | New cases per unit population per unit time. |
| **Prevalence** | Proportion of population infected at a point in time. |

### Spatial / Environmental

| Term | Definition |
|---|---|
| **Carrying capacity (K)** | Maximum mosquito density per grid cell, set by environmental suitability. |
| **Reaction-diffusion (Fisher-KPP)** | PDE model: local logistic growth + spatial diffusion. Approximates population spread. |
| **Environmental suitability** | Composite score from water fraction, rainfall, temperature, NDVI, elevation. |
| **Mordecai thermal response** | Parabolic temperature suitability curve: s(T) = max(0, 1 − ((T−25)/8)²). Optimal ~25°C. |

---

## 5. How the Code Maps to SDSS

### Monorepo → SDSS components

| SDSS component | Monorepo package | Role |
|---|---|---|
| **Data inputs** | `mal-ghana-sim/scripts/01_ingest.py` | Reproject & resample env rasters |
| **Baseline GIS layers** | `data/`, `terrain/`, `runs/layers/` | SRTM DEM, JRC water, CHIRPS rainfall, WorldClim temperature, MODIS NDVI |
| **Expert knowledge** | `agents/`, `AGENTS.md`, knowledge graph | Accumulated conventions, patterns, pitfalls |
| **Spatial analysis** | `mal-ghana-sim/scripts/02_suitability.py` | Weighted overlay + thermal curve |
| **Modeling (ABM)** | `mal-ghana-sim/src/mal_ghana_sim/abm/` + `mal-abm-fast/` | Agent-based mosquito simulation |
| **Modeling (KPP)** | `mal-ghana-sim/scripts/03_simulate.py` | Fisher-KPP reaction-diffusion |
| **ML surrogate** | `mal-ghana-sim/scripts/05_train.py` + `06_predict_and_map.py` | U-Net transition model |
| **Automated outputs** | `mal-execution/scripts/` | CLI entrypoints, batch jobs |
| **Cyclical re-entry** | Calibration framework | Scorers feed outcomes back into parameter tuning |
| **Risk maps** | `mal-ghana-sim/scripts/06_predict_and_map.py` | Side-by-side risk-expansion visualisation |

### Data flow

```
GBIF occurrences ──┐
REACT survey data ──┤
VectorLink data ────┤──→ mal-ghana-sim ──→ suitability map
SRTM DEM ───────────┤                    ──→ ABM / KPP simulation
JRC water ──────────┤                    ──→ U-Net training data
CHIRPS rainfall ────┤                    ──→ U-Net surrogate
WorldClim temp ─────┤                    ──→ risk expansion map
MODIS NDVI ─────────┘
```

---

## 6. Intervention Modeling

The SDSS supports planning and evaluating five intervention types:

### Long-Lasting Insecticidal Nets (LLINs)

- **Mechanism**: Physical barrier + insecticidal kill during evening biting
- **Parameters**: coverage fraction, attrition rate, insecticide decay
- **In ABM**: Reduces effective biting rate proportional to coverage; kills a fraction of mosquitoes that contact nets

### Indoor Residual Spraying (IRS)

- **Mechanism**: Insecticide applied to interior walls kills resting mosquitoes
- **Parameters**: coverage fraction, residual activity duration, insecticide resistance
- **In ABM**: Increases daily adult mortality rate μ for sprayed structures

### Larviciding

- **Mechanism**: Chemical or biological agents kill larvae in aquatic habitats
- **Parameters**: coverage of breeding sites, kill efficacy, application frequency
- **In ABM**: Reduces carrying capacity K or increases larval mortality

### Case Management (Drug Campaigns)

- **Mechanism**: Treating infected individuals reduces the human infectious reservoir
- **Parameters**: treatment coverage, drug efficacy, resistance profile
- **In ABM**: Removes infectious humans from the transmission cycle

### Vaccines (RTS,S / R21)

- **Mechanism**: Pre-erythrocytic vaccines reduce infection probability; transmission-blocking vaccines reduce parasite development in mosquitoes
- **Parameters**: efficacy, duration, coverage, age group targeted
- **In ABM**: Reduces infection probability per bite or blocks sporozoite development (extends effective EIP)

### Parameterization conventions

All intervention parameters live in `mal-ghana-sim/src/mal_ghana_sim/config.py` (suitability/simulation parameters) or are passed as CLI flags to the ABM engine. The calibration framework (`mal-abm-fast/tests/calibration/`) validates that parameterized interventions produce realistic population dynamics.

---

## 7. Environmental Drivers

The suitability model combines five environmental layers via weighted overlay:

| Layer | Source | Weight | Biological meaning |
|---|---|---|---|
| **Water fraction** | JRC Global Surface Water | 0.35 | Breeding habitat availability. Above threshold (0.10), larvae can develop. |
| **Rainfall** | CHIRPS v2.0 annual mean | 0.20 | Replenishes breeding sites; too little → desiccation, too much → flushing. |
| **Temperature** | WorldClim BIO1 | 0.20 | Drives Mordecai thermal response s(T) = max(0, 1−((T−25)/8)²). Also gates EIP development. |
| **NDVI** | MODIS MOD13A2 | 0.15 | Vegetation proxy; correlates with humidity and breeding site proximity. |
| **Elevation** | SRTMGL1 (30m) | 0.10 | Altitude-temperature relationship; higher elevation → cooler → less suitable. |

**Mordecai thermal curve**: mosquito population peaks at ~25°C. Below ~18°C or above ~34°C, suitability drops to zero. The curve is parabolic: `s(T) = max(0, 1 - ((T-25)/8)²)`.

**EIP temperature dependence**: EIP shortens with temperature. Growing degree-days = sum of max(0, T - 16) per day. Mosquito becomes infectious when EIP ≥ 110 GDD.

**Water threshold**: cells with water fraction ≥ 0.10 are classified as potential breeding habitat. This is a v1 simplification; finer resolution water data improves accuracy.

---

## 8. The Ghana Case Study

### Why Ghana

- **High burden region**: Northern Ghana has intense seasonal malaria transmission
- **Data availability**: GBIF occurrence records (Ghana IDIT dataset), REACT survey data, VectorLink entomological data
- **Existing infrastructure**: Ghana Health Service has well-documented malaria surveillance systems
- **Climate gradients**: Sahel-to-forest gradient provides natural variation in transmission intensity
- **Strategic importance**: WHO EMRO / AFRO elimination target regions

### Available data

| Dataset | Source | Coverage | Resolution |
|---|---|---|---|
| Ghana IDIT occurrences | GBIF DwC-A | Northern Ghana | Point records |
| REACT survey data | GBIF DwC-A | Ghana | Household surveys |
| VectorLink entomological | GBIF DwC-A | Ghana | Trap catches |
| SRTM DEM | NASA/OpenTopography | Global | 30 m → 1 km |
| JRC Global Surface Water | EC JRC | Global | 30 m → 1 km |
| CHIRPS rainfall | UCSB/CHC | Global | ~5 km → 1 km |
| WorldClim temperature | WorldClim | Global | ~1 km |
| MODIS NDVI | NASA LP DAAC | Global | 1 km |

### What the simulation shows

The Ghana simulation models mosquito population expansion from seed points (observed occurrence locations) across northern Ghana. The suitability field determines where mosquitoes can establish; the ABM or KPP simulator models how they spread over time. The U-Net surrogate then learns this transition function for fast prediction.

**Known limitations** (v1):
- Static climatological normals (no seasonal/temporal variation)
- 1 km grid cannot resolve sub-km breeding sites
- Dynamics unvalidated against temporal incidence data

---

## 9. References

| Paper | Year | Key contribution |
|---|---|---|
| Kelly et al. "Malaria elimination: moving forward with spatial decision support systems" | 2012 | SDSS framework for malaria elimination (reference framework) |
| Mordecai et al. "Optimal temperature for malaria transmission is dramatically lower than previously predicted" | 2013 | Parabolic thermal response curve for *Plasmodium* development |
| Thomas et al. "Robust links between mosquito thermophysiology and climate predict malaria transmission potential" | 2013 | Temperature-dependent mosquito physiology and transmission |
| Fisher-KPP (Fisher 1937, Kolmogorov et al. 1937) | 1937 | Reaction-diffusion model for population spread |
| Hay et al. "A world malaria map: *Plasmodium falciparum* endemicity in 2007" | 2009 | Global geostatistical malaria risk mapping |
| Feachem et al. "Shrinking the Malaria Map" | 2009 | Global strategy for progressive elimination |
| GMAP (Roll Back Malaria Partnership) | 2008 | Global Malaria Action Plan — phased control-to-elimination strategy |
| Bousema et al. "Hitting hotspots: spatial targeting of malaria for control and elimination" | 2012 | Spatial heterogeneity and hotspot-targeted interventions |
| WHO "Geographical Reconnaissance For Malaria Eradication Programmes" | 1965 | Historical GR methods from GMEP era |
| Keenen "Spatial decision support systems" | 2003 | SDSS definition and framework |

---

## 10. Related Skills

| Skill | When to use |
|---|---|
| `ghana-pipeline` | Running the end-to-end Ghana simulation pipeline (Stages 1–6) |
| `abm-engine` | Running, building, or deploying the agent-based model engines (Python or C++) |
| `calibration-framework` | Validating biological parameterization of the ABM against empirical targets |
| `data-explorer` | Exploring, mapping, and bias-analysing input datasets |
| `cesga` | Deploying simulation jobs to CESGA FinisTerrae III HPC |
| `project-memory` | Querying or recording domain knowledge in the project knowledge graph |
| `monorepo-dev` | Monorepo conventions, promotion flow, package structure |
| `project-setup` | First-time project setup and verification |
| `memory-setup` | Setting up the knowledge graph for domain knowledge storage. |
| `subagents-loops` | Using agent loops for domain research and review. |
| `mal-execution-api` | Running production CLI commands and training scripts. |
| `agent-onboarding` | Complete onboarding guide for new agents. |

Load these with `skill({ name: "<skill-name>" })` when the task requires their specific guidance.
