# Pack 09 — Single master seed for all randomness

> Source: ODD 2010 review notes.
**Document sections invalidated (CUJ-4):** `docs/concepts/abm/odd-2010-malariasentinel.tex` → §5.4 "Randomness and reproducibility" and Appendix A.5 (already named by the pack).
When this pack is decided and applied, these are the passages that
must change; the document is amended in the commit that applies the
pack, not in the pack itself.
 Status: initial plan — to be detailed later.

## Objective

All random executions derive from one master seed defined in
`model_constants.yaml` (or `--seed`), including the aquatic mortality
streams that today use fixed, day-re-seeded constants.

## Notes (verbatim)

- **p.11** (random streams) — "There should be a unique seed defined in the yaml"
- **p.14** (randomness and reproducibility) — "all should be from master seed."
- **p.29 A.5** — "As said before only one seed must be used shared between all random executions"
  *(today `washout()`, `stage_mortality()`, `larva_mortality_density()` each build a
  fresh `std::mt19937_64` with fixed seeds 789/42/123 on every call)*

## Initial steps

1. Inventory every RNG construction in the C++ engine and the Python side.
2. Derive all substreams (coordinator, submodel, transmission, aquatic
   mortality, phase flows) from the master seed via splitmix64-style
   hashing — no hardcoded seeds left.
3. Move any remaining seed constants into `model_constants.yaml` (schema bump).
4. Update the reproducibility docs (ODD §5.4, Appendix A.5) and regenerate
   golden fixtures (draw sequences will change).

## Dependencies / open points

- Cross-ref pack 10: `seed` already appears in the state sidecar — keep
  byte-identical reproducibility guarantees after the change.
