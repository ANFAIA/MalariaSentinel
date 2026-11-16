# Pack 11 — Transmission semantics and Ross–Macdonald coherence

> Source: ODD 2010 review notes. Status: initial plan — to be detailed later.

## Objective

Resolve the transmission-layer semantics questions: same-day death bites,
EIP feasibility under current survival, human `E_H` infectiousness to
vectors, and coherence with the Ross–Macdonald reference.

## Notes (verbatim)

- **p.7** (schedule consequence) — "Mosquitoes that transmit the same day that die, should affect."
- **p.7** (basic principles) — "Ensure truly coherence with the paper"
- **p.10** (vector–host contact) — "It should? Effect of malaria on human behaviour."
- **p.27** (EIP) — "Very unlikely females survive until it gets infectious with current values → analyze this."
- **p.28** (human incubation) — "is human infectious in E_H phase for mosquito"
- Cross-ref **p.28** — "find paper support for it." (EIP base 16 °C / threshold 110 degree-days) → pack 08.

## Initial steps

1. Quantify EIP feasibility: mean adult lifetime ~7.2 d at optimum vs
   EIP 12.2 d at 25 °C — compute the fraction of infected females that
   ever become infectious; analyze and report. Use for this a test scenario,
   using a toy input, where there will be normal conditions on a small
   area, but there will be a limited amount of population (animals,
   mosquitoes and humans).
2. Specify same-day-death semantics: do bites recorded before death today
   contribute to today's transmission update? (Ledger currently survives
   death; the EIP/SEIR block runs after mortality.)
3. Audit the implementation against Ross–Macdonald (Macdonald 1957;
   Smith & McKenzie 2004) equation-by-equation and document coherence.
4. Scope (future): host behavioural response to malaria / to biting,
   for example, as a baseline of this expected changed behavioural,
   take this 2 papers: <https://www.science.org/doi/10.1126/science.aah4563>,
   <https://journals.plos.org/plosbiology/article?id=10.1371/journal.pbio.0030298>.

## Dependencies / open points

- Findings may change `beta_hv`/`beta_vh`/EIP parameters → pack 08.
- Interaction with pack 02: individuals change how bites aggregate.
