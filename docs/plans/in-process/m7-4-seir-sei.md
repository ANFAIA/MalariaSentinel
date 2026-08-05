# M7.4 — SEIR-SEI Malaria Transmission Cycle (STUB)

> **Status**: Stub (2026-08-05). Full plan to be drafted when M7.3 (multi-species) ships.
>
> **Predecessor**: M7.3 — Multi-species support (`docs/plans/in-process/m7-3-multi-species.md`).
>
> **Scope (preview only)**: full transmission cycle — mosquito S→E→I, human S→E→I→R. Ross-Macdonald force of infection. Detail deferred to M7.4 full plan when M7.3 acceptance criteria are met.

## Goal

Implement the full malaria transmission cycle. M1.5 has EIP for sporozoite accumulation but no human-side dynamics.

## Compartments (preview)

- **Mosquito**: S_V (susceptible), E_V (exposed/latent), I_V (infective/sporozoite+).
- **Human**: S_H (susceptible), E_H (exposed/latent), I_H (infective/gametocyte+), R_H (recovered, temporary immunity).

## Transitions (preview)

- Mosquito S→E: susceptible mosquito bites infectious human (prob = host infectiousness × bite rate).
- Mosquito E→I: after EIP (temperature-dependent, Mordecai 2013).
- Human S→E: susceptible human bitten by infective mosquito (prob = bite rate × sporozoite rate).
- Human E→I: after intrinsic incubation (~10–14 days).
- Human I→R: after recovery (~21 days for *P. falciparum*).
- Human R→S: immunity wanes (configurable, default 180 days).

## Why this exists as a stub now

1. M7.3 multi-species feeds species-specific biting rates into the force-of-infection term.
2. M7.5 host layer defines human census grid that M7.4 transitions operate on.
3. Calibration scorers (D-series) need a closed-population SIR test (R₀ < 1 dies out, R₀ > 1 sustains) — that test belongs to M7.4.

## Acceptance criteria (preview)

- New transmission unit tests pass (R₀, force of infection).
- Closed-population SIR test: outbreak dies out if R₀ < 1, sustains if R₀ > 1.
- Temperature-dependent EIP matches Mordecai 2013 curve.
- Integration with gonotrophic cycle (M7.2): infected females remain infective.

## Reference

- Issue: ANFAIA/MalariaSentinel#18 (M7.4: SEIR-SEI malaria transmission cycle)
- Papers: `papers/abm-intervention/GatoreSinigirira-2025-SEIR-SEIMalariaBurundi.md`, `papers/perplexity-investigations/` §7.

## Files (target, when promoted)

- `mal-abm-fast/include/mal_abm_fast/human_state.hpp` (new)
- `mal-abm-fast/src/transmission.cpp` (new)
- `mal-abm-fast/include/mal_abm_fast/seir.hpp` (new)
- `mal-abm-fast/tests/test_transmission.cpp` (new)