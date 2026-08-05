# M7.3 — Multi-Species Support (STUB)

> **Status**: Stub (2026-08-05). Full plan to be drafted when M7.2 (gonotrophic cycle) ships.
>
> **Predecessor**: M7.2 — Gonotrophic cycle (`docs/plans/completed/m7-2-gonotrophic-cycle-plan.md` if present; otherwise `docs/plans/`).
>
> **Scope (preview only)**: 4 Anopheles species (gambiae, coluzzii, arabiensis, funestus) with species-specific HBI, thermal optimum, habitat, exo/endo, and EIP. Detail deferred to M7.3 full plan when M7.2 acceptance criteria are met.

## Goal

Support 4 Anopheles species with species-specific parameters. M1.5 currently only models *An. gambiae s.s.*

## Species parameters (preview)

| Species | HBI | Thermal opt | Habitat | Exo/Endo | EIP |
|---|---|---|---|---|---|
| *An. gambiae* s.s. | 0.95 | 25°C | ephemeral puddles | endophilic | 12d@25°C |
| *An. coluzzii* | 0.90 | 26°C | permanent water | endophilic | 12d@25°C |
| *An. arabiensis* | 0.50 | 27°C | arid pools | exophilic | 11d@25°C |
| *An. funestus* | 0.85 | 25°C | permanent/semi-permanent | endophilic | 13d@25°C |

## Why this exists as a stub now

1. M7.2 (gonotrophic cycle) defines host-seeking + oviposition hooks that M7.3 species logic will read from (HBI per species).
2. Calibration scorers (D-series) need species-tagged outputs to split per-species deltas vs the composite.
3. M7.5 host layer assumes species-specific biting times — the M7.3 species field is required for M7.5 to compile.

## Acceptance criteria (preview)

- All 4 species co-exist in a single simulation.
- Species-specific thermal response curves verified against Mordecai 2013.
- HBI consumed by M7.5 host selection.
- Species-specific biting times and exo/endo behavior.

## Reference

- Issue: ANFAIA/MalariaSentinel#17 (M7.3: Multi-species support)
- KB ref (if present): `inv-m7-3-multi-species` (placeholder; promote when promoted).
- Papers: `papers/anopheles-dynamics/`, `papers/perplexity-investigations/` §1.3.

## Files (target, when promoted)

- `mal-abm-fast/include/mal_abm_fast/species.hpp` (new)
- `mal-abm-fast/include/mal_abm_fast/mosquito_state.hpp` (species field)
- `mal-abm-fast/src/mosquito_submodel.cpp` (species-aware operators)
- `mal-abm-fast/tests/test_species.cpp` (new)