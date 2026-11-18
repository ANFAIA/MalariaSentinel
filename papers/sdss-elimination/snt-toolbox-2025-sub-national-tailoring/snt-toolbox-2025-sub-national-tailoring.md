# SNT Toolbox: Sub-National Tailoring for Malaria Elimination

**Authors:** PATH, CHAI, AHADI, IDM, SwissTPH consortium
**Journal:** Institutional (Tool) | **Year:** 2025 | **URL:** https://www.snt-toolbox.org/
**File:** papers/sdss-elimination/snt-toolbox-2025-sub-national-tailoring.md

---

## Abstract

The SNT Toolbox is a country-owned digital platform for optimising intervention allocation through Sub-National Tailoring (SNT), a WHO-recommended approach for stratifying malaria transmission heterogeneity within countries. The platform integrates epidemiological simulations, budgeting logic, and stratification data to support national malaria control programmes in designing sub-national intervention packages. It consists of the SNT Pipeline Library (automated data processing) and SNT Explorer (interactive planning interface).

## Methods

- Modular architecture: SNT Pipeline Library (data processing) + SNT Explorer (user interface)
- Epidemiological simulation engine for intervention impact projection
- Budgeting logic for resource-constrained optimisation
- Integration of routine surveillance data, survey data, and environmental covariates
- Stratification framework for sub-national transmission heterogeneity
- Open-source development with country ownership model

## Key Results

- Enables data-driven stratification of transmission heterogeneity within countries
- Supports evidence-based selection of intervention packages per stratum
- Interactive planning interface allows scenario comparison and sensitivity analysis
- Budgeting module ensures resource-constrained feasibility of intervention plans
- Adopted by multiple national malaria control programmes in Africa

## Relevance to MalariaSentinel (Centinela)

State-of-the-art SDSS framework directly relevant to MalariaSentinel's decision support capabilities. The SNT Toolbox demonstrates the operational architecture for a national-scale SDSS: modular pipeline + interactive explorer. The Centinela could extend this approach by adding ABM-based transmission simulation and real-time data integration. The stratification framework is directly applicable to Ghana's sub-national heterogeneity. The country-owned model provides a deployment strategy template.

## Limitations

- Primarily designed for national-level planning; may not support village-level targeting
- Epidemiological simulation engine may be simpler than full ABM
- Requires substantial data infrastructure for input data quality
- Interactive interface may have steep learning curve for field staff

## Future Directions

- Integrate ABM-based simulation for higher-fidelity intervention impact projection
- Add real-time data feeds from mobile surveillance systems
- Develop API for integration with other national health information systems
- Extend to cross-border coordination scenarios

---

*Paper condensed from Phase 1 research findings. 2025-07-17.*
