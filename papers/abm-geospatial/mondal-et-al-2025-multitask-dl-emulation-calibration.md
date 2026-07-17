# Multitask deep learning for the emulation and calibration of an agent-based malaria transmission model

**Authors:** Mondal A, Anirudh R, Selvaraj P
**Journal:** PLOS Computational Biology | **Year:** 2025 | **DOI:** 10.1371/journal.pcbi.1013330
**File:** papers/abm-geospatial/mondal-et-al-2025-multitask-dl-emulation-calibration.md

---

## Abstract

This paper develops a neural network emulator for the complex EMOD individual-based malaria transmission model, trained on 160,000 simulations across eight sub-Saharan African sites. The multitask deep learning approach provides a scalable alternative to traditional calibration techniques (MCMC, particle filters) for rapid parameter space exploration. The emulator achieves high fidelity in reproducing EMOD outputs while reducing computational cost by several orders of magnitude.

## Methods

- Multitask deep learning architecture with shared representations across geographic sites
- Training data: 160,000 EMOD simulations spanning eight sub-Saharan African sites
- Neural network emulator trained to predict model outputs from input parameter vectors
- Comparison with traditional calibration methods (MCMC, particle filters, ABC)
- Validation against held-out EMOD simulations and real-world epidemiological data
- Uncertainty quantification via ensemble predictions

## Key Results

- Neural emulator reproduces EMOD outputs with high fidelity across diverse settings
- Computational speedup of ~10,000x compared to full EMOD simulation
- Multitask learning across sites improves generalisation to unseen parameter combinations
- Calibration accuracy comparable to MCMC but with dramatically reduced compute time
- Emulator enables real-time parameter sensitivity analysis and uncertainty quantification

## Relevance to MalariaSentinel (Centinela)

Offers scalable calibration approaches for MalariaSentinel's ABM components. The EMOD emulator demonstrates that complex transmission models can be approximated by neural networks for rapid scenario testing — directly applicable to the Centinela's Ghana ABM calibration pipeline. The multitask learning approach across sites could be used to transfer knowledge from other African settings to Ghana. The 10,000x speedup enables real-time decision support, a core requirement for the SDSS.

## Limitations

- Emulator fidelity depends on training data coverage of parameter space
- May not capture extreme or novel parameter combinations outside training distribution
- Requires significant upfront investment in simulation data generation
- Black-box nature of neural emulator limits interpretability

## Future Directions

- Extend to multi-output emulation (clinical cases, severe cases, mortality)
- Incorporate temporal dynamics for time-series prediction
- Develop online learning pipeline for continuous emulator updating
- Validate against Ghana-specific EMOD configurations

---

*Paper condensed from Phase 1 research findings. 2026-07-17.*
