# Vector genetics, insecticide resistance and gene drives: An agent-based modeling approach

**Authors:** Prashanth Selvaraj, Edward A. Wenger, et al.
**Journal:** PLOS Computational Biology | **Year:** 2020 | **DOI:** 10.1371/journal.pcbi.1008121
**File:** papers/abm-intervention/selvaraj-et-al-2020-vector-genetics-gene-drives.md

---

## Abstract

This paper presents the first multi-locus agent-based model of vector genetics embedded within a large-scale individual-based malaria transmission model. The model demonstrates that even small numbers of insecticide-resistant vectors can dominate local populations through competitive advantage, and that gene drives combined with insecticide-treated nets (ITNs) can bring high-transmission settings close to elimination. The work provides a framework for evaluating genetic vector control interventions.

## Methods

- Multi-locus agent-based model of vector genetics (kdr, metabolic resistance, etc.)
- Embedded within large-scale individual-based malaria transmission model (EMOD framework)
- Population genetics: inheritance, selection, drift, migration of resistance alleles
- Gene drive modelling: gene drive mechanism, fitness costs, resistance allele generation
- Intervention combinations: gene drives + ITNs + IRS
- Sensitivity analysis across transmission settings and resistance allele frequencies

## Key Results

- Even small initial numbers of insecticide-resistant vectors can dominate local populations
- Competitive advantage of resistant vectors accelerates resistance spread
- Gene drives combined with ITNs can bring high-transmission settings close to elimination
- Gene drive effectiveness depends on fitness costs and resistance allele generation
- Combined interventions (gene drives + ITNs + IRS) outperform single interventions
- Model captures evolutionary dynamics of resistance under intervention pressure

## Relevance to MalariaSentinel (Centinela)

Advanced ABM framework for evaluating genetic interventions. The multi-locus genetics model provides a template for incorporating insecticide resistance dynamics into the Centinela's vector sub-model. The finding on competitive advantage of resistant vectors is critical for Ghana where kdr resistance is prevalent. The gene drive evaluation framework could support Ghana's assessment of novel vector control tools. The EMOD embedding demonstrates how to integrate vector genetics with transmission dynamics.

## Limitations

- Computationally expensive; may require significant compute resources
- Parameterisation of fitness costs and gene drive mechanisms is uncertain
- Real-world gene drive behaviour may differ from model assumptions
- Does not capture spatial structure of resistance spread

## Future Directions

- Add spatial structure for landscape-level resistance dynamics
- Incorporate Ghana-specific resistance allele frequencies
- Validate against insecticide resistance monitoring data
- Extend to evaluate next-generation vector control tools

---

*Paper condensed from Phase 1 research findings. 2026-07-17.*
