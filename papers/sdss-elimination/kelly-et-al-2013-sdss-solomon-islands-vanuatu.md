# A high-resolution geospatial surveillance-response system for malaria elimination in Solomon Islands and Vanuatu

**Authors:** Gerard C. Kelly, Erick Hale, et al.
**Journal:** Malaria Journal | **Year:** 2013 | **DOI:** 10.1186/1475-2875-12-108
**File:** papers/sdss-elimination/kelly-et-al-2013-sdss-solomon-islands-vanuatu.md

---

## Abstract

This paper presents a GIS-based spatial decision support system (SDSS) developed for malaria elimination in Solomon Islands and Vanuatu, capable of automatically locating and mapping malaria cases, classifying transmission foci, and guiding targeted responses. The system achieved 82.5% household-level geo-referencing of cases. The SDSS framework integrates routine health information system data, field surveys, baseline GIS layers, and expert knowledge to produce automated analytical outputs for vector control, surveillance-response, and monitoring and evaluation.

## Methods

- GIS-based SDSS built on Microsoft Access and MapInfo Professional
- Field-based geographical reconnaissance (GR) using handheld PDA and GPS technology
- Automated case mapping and transmission focus classification
- Integration of routine HIS data, field survey data, baseline GIS layers, expert knowledge
- Household-level data collection across 20,485 households and 90,292 people
- Cyclical feedback from intervention outcomes to SDSS refinement

## Key Results

- 82.5% of malaria cases successfully geo-referenced at household level
- GR operations achieved average 42.5 households and population of 180 per PDA/GPS unit per day
- Automated transmission focus classification enabled targeted intervention deployment
- SDSS supported LLIN coverage monitoring, focal IRS targeting, case management, drug supply management
- Demonstrated feasibility in remote, logistically constrained island settings

## Relevance to MalariaSentinel (Centinela)

Foundational SDSS framework for surveillance-response systems. This paper is the primary reference framework for the Centinela project (see AGENTS.md). The four-element SDSS architecture (multi-source data inputs → automated outputs → cyclical feedback → expert knowledge) directly informs the Centinela's system design. The Solomon Islands/Vanuatu implementation demonstrates operational feasibility in resource-limited settings. The Centinela extends this with modern ML/AI methods and Python/Neo4j stack for Ghana application.

## Limitations

- Built on legacy technology (Microsoft Access, MapInfo) — modern alternatives needed
- Limited to island epidemiological contexts
- Manual GR process is labour-intensive and difficult to sustain
- Limited quantification of SDSS impact on elimination outcomes

## Future Directions

- Modernise platform to open-source web-based architecture
- Integrate with mobile health (mHealth) data collection
- Add ABM-based transmission prediction
- Validate SDSS impact on elimination outcomes through controlled studies

---

*Paper condensed from Phase 1 research findings. 2013 (foundational).*
