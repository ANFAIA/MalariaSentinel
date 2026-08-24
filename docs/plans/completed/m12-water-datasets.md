# M12 — Water Datasets

> **Status:** active baseline scope; OPERA DSWX-S1 explicitly removed.

## Scope

M12 supplies static water context for ingest and M14:

- JRC Global Surface Water: water occurrence baseline.
- HydroLAKES: permanent lakes.
- HydroRIVERS: permanent rivers.
- Optional WorldCover wetland/permanent-water cross-check.

## Excluded Dataset

OPERA DSWX-S1 is excluded from the download and runtime contracts. Ghana
acquisition coverage was irregular and available scenes covered partial
monthly windows. OPERA therefore made reproducible monthly bundles and
two-month validation runs unreliable. Removal rationale and breaking contract
change are recorded in `docs/specs/download/spec.md`.

## M14 Boundary

M14 behavior remains unchanged. M14 receives:

- `water_frac` from JRC and static permanent-water enrichment.
- Daily `rainfall` from CHIRPS.
- Daily temperature forcing from ERA5.

M14 owns stateful pool accumulation, evaporation, activation, desiccation,
and washout. M12 datasets do not replace or redefine those rules.

## Acceptance

- Static water sources align to AOI grid and preserve provenance.
- Missing optional static layers do not break ingest.
- No OPERA loader, registry entry, manifest key, or dynamic-water ingest path
  exists.
- M14 tests and behavior remain unchanged.
