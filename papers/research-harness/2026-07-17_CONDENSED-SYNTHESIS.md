# Condensed Synthesis: Malaria ABM, Geospatial Analysis & SDSS

**Generated**: 2026-07-17  
**Harness Phase**: Condense (Phase 2/4)  
**Input**: 25+ papers across 5 subtopics from Phase 1 Search  

---

## Executive Summary

The 2020–2026 literature reveals three convergent trends that directly shape MalariaSentinel's architecture: **(1) ABMs are becoming spatio-temporal and climate-forced**, integrating household GPS data, suitability maps, and intervention cascades; **(2) risk mapping is shifting from purely environmental to hazard-vulnerability decomposition**, combining vector ecology with population exposure; and **(3) operational SDSS platforms are proving value at scale**, but no single system unifies suitability mapping, transmission dynamics, and intervention optimization. MalariaSentinel is positioned to fill this gap for Ghana.

---

## Theme 1: Spatio-Temporal ABMs with Climate Forcing

**State of the art**: The field has moved from compartmental ODEs to stochastic, spatially explicit ABMs that embed mosquito climatic suitability maps (Brown et al. 2024), household GPS data, and multi-species vector dynamics. Walker et al. (2026) demonstrated this in Vietnam; Angelakis et al. (2026) in western Kenya; Mfala et al. (2024, 2026) in Tanzania.

**Key advance**: Mondal et al. (2025) trained a neural network emulator on 160,000 EMOD simulations across 8 African sites, achieving transferability to unseen sites. This makes computationally expensive ABMs tractable for real-time decision support.

**Implication for MalariaSentinel**: The Centinela should adopt a **hybrid architecture** — mechanistic ABM for ground-truth simulation + ML emulator for rapid scenario evaluation. The U-Net surrogate already in the Ghana sim package is aligned with this direction.

**Reference implementations**:
- EMOD (Institute for Disease Modeling) — gold standard for calibrated ABMs
- AnyLogic — multi-paradigm ABM with GIS integration (Mfala et al.)
- AnophelesModel R package (Golumbeanu et al. 2024) — species-specific vectorial capacity estimation

---

## Theme 2: Hazard-Vulnerability Risk Decomposition

**State of the art**: Morlighem et al. (2025) decomposed malaria risk into **hazard** (infected vector presence — climate/land use) and **vulnerability** (population predisposition — health access, housing quality). Their Bayesian geostatistical model at 1km resolution achieved R²=0.64 using open-source covariates. Vanhuysse et al. (2023) extended this to urban settings at 100m resolution using expert-driven MCDA.

**Key advance**: Gbaguidi et al. (2026) jointly modeled vector abundance and human malaria incidence using Gaussian spatial processes — the first study to couple entomological and epidemiological risk surfaces. An. funestus showed stronger spatial correlation with incidence than An. gambiae.

**Implication for MalariaSentinel**: The Centinela's risk layer should implement the **hazard-vulnerability decomposition** as its conceptual foundation. Hazard = vector suitability (environmental); Vulnerability = population exposure (demographic/access). Joint risk surfaces should be the target, not separate layers.

**Data sources validated**:
- Sentinel-10m satellite data for vector habitat mapping
- DHS/MIS parasitemia biomarkers for ground truth
- CHIRPS rainfall + MODIS NDVI for climate layers
- OpenStreetMap for health facility access

---

## Theme 3: Intervention Cascade Modeling

**State of the art**: Champagne et al. (2025) quantified the loss of ITN impact from entomological efficacy to population-level effectiveness across 5 factors: entomological efficacy, functional survival, usage at distribution, insecticidal durability, and in-bed exposure. Usage gaps (10–12 point drop) and exposure timing (8–10 point drop) are the largest sources of loss.

**Key advance**: Henyimana et al. (2026) modeled ITN transition (pyrethroid → PBO → IG2) using EMOD, showing that IG2 nets reduce homozygous-resistant An. funestus by 62.2% and incidence by 94%. The cascade from tool efficacy to population impact is non-linear and species-dependent.

**Implication for MalariaSentinel**: The intervention module must model the **full effectiveness cascade**, not just entomological impact. This means parameterizing: (1) tool efficacy per species, (2) usage rates from survey data, (3) durability over time, and (4) exposure timing relative to biting behavior.

**Operational precedent**: CIMS on Bioko Island (García et al. 2022) achieved 37.7% optimal coverage (vs. 17% in 2017) using 100×100m grid-based real-time SDSS for IRS.

---

## Theme 4: Multi-Species Vector Reality

**State of the art**: Rakotoarison et al. (2025) modeled 4 Anopheles species in Madagascar with mechanistic ODEs, integrating agricultural calendars (rice cultivation) as a first-class driver. Ibrahim et al. (2024) mapped insecticide resistance dynamics across the An. gambiae complex using cellular automata.

**Key advance**: The agricultural calendar integration reduced overestimation of host-seeking females by accounting for temporary habitat creation during rice cultivation. This is the first study to couple agricultural practices with mechanistic mosquito population models.

**Implication for MalariaSentinel**: The vector dynamics module must support **multi-species parameterization** with distinct thermal optima, habitat requirements, and behavioral profiles. Agricultural calendars should be a first-class input for Ghana (rice cultivation in northern regions).

**Species priority for Ghana**:
- An. gambiae s.s. — primary vector, high endophily, strong ITN response
- An. arabiensis — zoophilic/exophagic, weak ITN response, outdoor biting
- An. funestus — permanent water breeder, strong indoor biter, high vectorial capacity

---

## Theme 5: Hydrological Process Modeling

**State of the art**: Smith et al. (2024, Science) demonstrated that precipitation-based suitability estimates are fundamentally limited. Process-based hydrology gives different, more complex transmission patterns and greater sensitivity to climate scenarios. Net decrease in malaria-suitable areas predicted from 2025 onward when hydrology is properly modeled.

**Implication for MalariaSentinel**: The environmental suitability module should integrate **hydrological process modeling** (flow accumulation, soil moisture, groundwater) rather than relying on precipitation thresholds alone. This is a critical methodological advance that changes projected transmission patterns.

---

## Gap Analysis: What No Existing System Does

| Capability | Existing Systems | Gap | MalariaSentinel Opportunity |
|---|---|---|---|
| Household-level ABM with suitability maps | Walker 2026 (Vietnam) | Not applied to Ghana; no intervention cascades | Build on Walker framework + add intervention module |
| Hazard-vulnerability risk decomposition | Morlighem 2025 (Senegal) | No real-time update; no intervention targeting | Integrate with DHIS2 for dynamic risk surfaces |
| Full ITN effectiveness cascade | Champagne 2025 (preprint) | Not integrated into SDSS platforms | Embed cascade in intervention optimization |
| Agricultural calendar integration | Rakotoarison 2025 (Madagascar) | Only Madagascar; not Ghana | Adapt rice/vanilla calendar to Ghana crops |
| Hydrological suitability | Smith 2024 (Science) | Global scale; not operational | Implement process-based hydrology at district scale |
| Unified SDSS platform | CIMS (Bioko), eSPT (3 countries) | No ABM integration; no risk mapping | Combine all layers in one framework |

---

## Cross-References to MalariaSentinel Architecture

| MalariaSentinel Component | Relevant Literature | Action |
|---|---|---|
| `mal-ghana-sim/` ABM | Walker 2026, Mondal 2025, Mfala 2024/2026 | Add household GPS layer, intervention cascade, multi-species |
| `mal-core/` suitability module | Smith 2024, Rakotoarison 2025, Frake 2020 | Integrate hydrology, agricultural calendar, species-specific thermal curves |
| `mal-core/` risk mapping | Morlighem 2025, Gbaguidi 2026, Onimisi 2025 | Implement hazard-vulnerability decomposition, joint risk surfaces |
| `mal-execution/` CLI scripts | García 2022 (CIMS), eSPT 2025 | Add real-time update capability, mobile-friendly output |
| `mal-data-explorer/` | Onimisi 2025, Frake 2020 | Add SHAP interpretability, GEE integration |

---

*Generated by MalariaSentinel Research Harness — Phase 2 (Condense)*
