# INV — Malaria Incidence Data Source for External Validation (STUB)

> **Status**: Stub (2026-08-05). Investigation. Re-scoped 2026-07-22 to M7+ (not blocking M2, M3-M4, M5, M6, M7.0–M7.7).
>
> **Not a milestone** — this is an investigation tied to the M7+ end-state. No M-number. Labels: `investigation`, `M7+`, `blocked`.
>
> **Scope (preview only)**: identify a malaria-incidence data source for external validation of the U-Net risk-map output. The 24 larval sites validate *habitat*, not *malaria risk*. Detail deferred until Ghana ABM is calibrated.

## Problem

The 24 larval sites validate habitat, not malaria risk. Without incidence data (DHMIS, MAP, NMCP case reports), the U-Net predicts habitat surfaces, not risk surfaces.

## Candidates (preview)

- **DHMIS** (District Health Management Information System) — Ghana.
- **MAP** (Malaria Atlas Project) — incidence estimates.
- **NMCP case reports** — national malaria control programme.

## Why this exists as a stub now

1. **Not blocking**: M2 / M3-M4 / M5 / M6 / M7.0–M7.7 all validate against larval sites (habitat), not incidence. Unblocking M2 does not need this.
2. **M7+ end-state**: external validation is the *last* step of M7+, after the ABM is calibrated to Ghana. Per user: "cuando Ghana esté dominado pasaremos a otras regiones con otros datasets".
3. **KB reference**: `inv-incidence-data-source` (matches filename slug).

## Acceptance criteria (preview)

- Selected data source with documented access path (API, download portal, request form).
- Spatial resolution compatible with the ABM output grid (1 km Ghana AOI, 5 km Africa).
- Temporal resolution compatible with the validation window (monthly / annual).
- License permits scientific use + redistribution in published results.

## Reference

- Issue: ANFAIA/MalariaSentinel#10 (Investigation: Malaria incidence data source for external validation)
- KB ref: `inv-incidence-data-source`.

## Files (target, when promoted)

- `docs/research/incidence-data-source.md` (comparison of candidates, when investigation moves out of stub)