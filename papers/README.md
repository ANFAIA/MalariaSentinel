# Papers

Research papers that ground the MalariaSentinel project.

## ⚠️ Recovery Notice

The original PDFs were lost (2026-07-03). Re-download from the original sources.

## Structure

```
papers/
  core-hypothesis/        Environmental drivers of malaria (DLNM, ML, mathematical modelling)
  spatial-analysis/       Spatial & spatio-temporal methods (kriging, scan statistics, SDSS)
  abm-geospatial/         Agent-based models with geospatial integration
  abm-intervention/       ABMs for intervention evaluation (gene drives, SMC, metapopulation)
  anopheles-dynamics/     Vector population dynamics and thermal response
  outbreak-dynamics/      Malaria reintroduction mechanisms (airport malaria, imported cases)
  risk-mapping/           Geospatial risk mapping and climate projections
  sdss-elimination/       SDSS implementations for malaria elimination
  perplexity-investigations/  Internal research notes (Anopheles biology, habitat data)
  research-harness/       Output from the research harness search phase
  hypotheses.md           Testable hypotheses bridging knowledge gaps
  REFERENCES.md           Attribution and license tracking
  README.md               This file
```

## Re-downloading Papers

| Folder | Papers | Source |
|--------|--------|--------|
| `core-hypothesis/` | Okiring 2021 (Uganda DLNM), Onimisi 2025 (Nigeria ML), Gatore Sinigirira 2025 (Burundi SEIR-SEI) | Journal websites |
| `spatial-analysis/` | Kleinschmidt 2000, Zhang 2008, Kelly 2012, Githinji 2016, Kamau 2021, Gwitira 2020, Odhiambo 2020, Aduvukha 2026 | Journal websites |
| `abm-geospatial/` | Walker 2026 (Vietnam ABM), Mfala 2026 (Tanzania SMC), Sa-ngamuang 2026 (MoVe mobility), Mondal 2025 (EMOD emulator) | Journal/arXiv |
| `abm-intervention/` | Selvaraj 2020 (gene drives), Angelakis 2026 (Kenya metapopulation), Bertozzi-Villa 2024 (archetypes), Gatore Sinigirira 2025 (Burundi SEIR-SEI), Landscape 2015 (ABM-GIS) | Journal/Figshare |
| `anopheles-dynamics/` | Mordecai 2013 (thermal response), Greenwood 2014 (An. gambiae ABM), Rakotoarison 2025 (Madagascar), Bissett 2026 (Glasgow thesis), Sabtiu 2025 (Accra larval habitats), Osae 2015 (southern Ghana vectors), Tene Fossog 2015 (habitat segregation/salinity), Kengne 2019 (brackish-water osmoregulation), Kudom 2015 (A. coluzzii Cape Coast), Nwaefuna 2019 (A. coluzzii salt water, Ghana), Epopa 2017 (coluzzii MRR Burkina Faso), Wickramasooriya 2026 (coluzzii MRR São Tomé/Príncipe), Vielma 2026 (coluzzii swarm kinematics), Nkahe 2020 (coluzzii life traits), Zuo 2026 (flight/CO2 proxy), Takken 2024 (adult behaviour review), Konopka 2026 (biting on human skin), Klowden & Briegel 1994, Briegel & Hörler 1993, Klowden & Lea 1978, Xue/Edman/Scott 1995, Norris 2010, Scott 2006, Das 2017, Conway & McBride 1991, Choumet 2012, Wu 2020 (MBITES), Dahlin 2025, Hauser 2019, Johnson 2023, Ha 2015, Lee 2016, Charlwood 2003, Brackney 2021 (blood meal size, multiple feeding, gonotrophic cycle), **synthesis-gemini-2026** (secondary synthesis on host detection and directional movement in *coluzzii* — NOT a paper, all claims pending verification against the primary sources), Lorenz 2013 (taxis assays: detection ranges), Hawkes & Gibson 2016 (*coluzzii* 3D flight), Hawkes 2013 (thesis), Spitzen 2013 (*gambiae* 3D plume flight), Carnaghi 2021/2024 (*coluzzii* visual-thermal landing), Cribellier 2018 (*coluzzii* flight around odour traps), Majeed 2017 (*coluzzii* CO₂ ORN), Cummins 2012 (spatial host-seeking ABM), Dekker & Cardé 2011 (*Aedes* casting), Ekechukwu & Tripet 2019 (*coluzzii* sperm transfer), Diabaté 2011 (swarm mating success), Bimbilé Somda 2018 (*arabiensis* swarming), Charlwood 2003 (*funestus* swarming), Shaw 2014 (HPX15 fertility), Arifin 2014 (ABM with males), Zhu 2017 (IBM male mating), Selvaraj 2020 (EMOD), Bamou 2025 (high-flying wind-borne), Uehara 2026 (post-feeding suppression), Takken 2001 (post-meal suppression), Mamai 2026 (*coluzzii* dry-season arrest), Yaro 2012 (dry-season reproductive depression), Lehmann 2010 (aestivation), Dao 2014 (aestivation/migration signatures), Rossi 2026 (female brain), Fritz 2013 (Sella stages) | Journal/thesis + internal synthesis |
| `risk-mapping/` | Senegal 2025 (hazard-vulnerability), Symons 2026 (climate change), Gbaguidi 2026 (Benin), Smith 2024 (hydrology), Aduvukha 2025 (biting probability), Eudaric 2026 (flood zones) | Journal websites |
| `sdss-elimination/` | Kelly 2013 (Solomon Islands), Wangdi 2016 (Bhutan), Cambodia 2025 (CIMS), SNT Toolbox 2025 | Journal/institutional |
| `outbreak-dynamics/` | CDC 2026 (MMWR), Slimani 2026 (Libya EID), Alemayehu 2024 (Florida EID), Hallmaier-Wacker 2024 (Eurosurveillance), Nkemka 2021 (MDPI) | CDC/Eurosurveillance/MDPI |

## Paper Categories

### Foundational (full-text papers with OCR)
- `core-hypothesis/` — environmental driver evidence
- `spatial-analysis/` — spatial methodology foundation
- `anopheles-dynamics/Mordecai-2013` — thermal response parameterization
- `outbreak-dynamics/` — malaria reintroduction mechanisms and airport malaria

### Condensed (structured summaries from research harness)
- `abm-geospatial/`, `abm-intervention/`, `risk-mapping/`, `sdss-elimination/`, `anopheles-dynamics/` (non-Mordecai)

### Internal
- `perplexity-investigations/` — Perplexity AI-generated research notes
- `research-harness/` — search-phase output
