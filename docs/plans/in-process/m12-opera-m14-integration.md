# M12 — OPERA DSWX-S1 Integration (Superseded)

> **Status:** superseded and removed from runtime.

OPERA DSWX-S1 was evaluated as an optional dynamic-water observation for
M12/M14. It is not part of current download, ingest, water-stack, or ABM
contracts.

## Decision

Do not use OPERA as runtime dependency. Ghana coverage was irregular, with
available acquisitions covering partial windows instead of reliable complete
months. This made reproducible monthly bundles and two-month validation runs
unreliable.

## Current replacement

- JRC Global Surface Water supplies water-occurrence baseline.
- HydroLAKES and HydroRIVERS supply permanent-water context.
- CHIRPS remains M14 daily rainfall forcing.
- ERA5 remains M14 temperature/evaporation forcing.
- M14 pool state remains stateful and independent of satellite cadence.

## Removal scope

- OPERA loader deleted from `mal-commonlib`.
- OPERA removed from download registry and manifest contract.
- OPERA dynamic-water ingest path deleted.
- OPERA integration test deleted.
- `docs/specs/download/spec.md` records removal rationale.

M14 behavior is unchanged by this decision.
