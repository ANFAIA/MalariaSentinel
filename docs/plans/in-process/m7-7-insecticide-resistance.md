# M7.7 — Insecticide Resistance (STUB)

> **Status**: Stub (2026-08-05). Full plan to be drafted when M7.5 (host layer) ships.
>
> **Predecessor**: M7.5 — Host layer (`docs/plans/in-process/` or completed).
>
> **Scope (preview only)**: three resistance mechanisms — target-site (kdr), metabolic, behavioral. Detail deferred to M7.7 full plan when M7.5 acceptance criteria are met.

## Goal

Model the three main insecticide resistance mechanisms in *Anopheles*. The ABM has no resistance layer today; interventions are also future work (H2).

## Resistance mechanisms (preview)

1. **Target-site (kdr)** — Vgsc mutations (L995F, L995S, N1570Y). Reduces pyrethroid binding. Allele frequency tracked per population. Mendelian inheritance.
2. **Metabolic** — Overexpression of CYP6M2, CYP6P3, CYP9K1, GSTs. Detoxifies pyrethroids faster. Continuous trait.
3. **Behavioral** — Shift in biting time / outdoor biting. Reduces ITN/IRS exposure. Categorical: indoor / outdoor / early biter.

## Data source (preview)

- **Allele frequencies**: IR Mapper (https://www.irmapper.com) — country-level.
- For Ghana: PMI vector surveillance data (annual updates).
- Default: 60% L995F in *An. gambiae* s.s. (West Africa literature average).

## Why this exists as a stub now

1. M7.3 species field is required to attach kdr allele frequencies per species.
2. M7.4 SEIR-SEI is required to model selection pressure (intervention efficacy drives allele dynamics).
3. Future H2 intervention layer (ITN/IRS) is the *consumer* — M7.7 must land before H2 ships.

## Acceptance criteria (preview)

- New resistance unit tests pass (Mendelian inheritance verified).
- Kdr allele frequencies track over generations (Hardy-Weinberg equilibrium).
- Metabolic factor distributes per population.
- Behavioral types partition per species (*An. arabiensis* more outdoor).
- Resistance combinable with intervention layer (H2 future work).

## Reference

- Issue: ANFAIA/MalariaSentinel#21 (M7.7: Insecticide resistance)
- Papers: `papers/perplexity-investigations/` §8.

## Files (target, when promoted)

- `mal-abm-fast/include/mal_abm_fast/resistance.hpp` (new)
- `mal-abm-fast/src/resistance.cpp` (new)
- `mal-abm-fast/include/mal_abm_fast/mosquito_state.hpp` (new fields)
- `mal-abm-fast/src/mosquito_submodel.cpp` (inheritance in birth)
- `mal-abm-fast/tests/test_resistance.cpp` (new)