# Pack 05 — Habitat species-coherence and state duplication

> Source: ODD 2010 review notes. Status: initial plan — to be detailed later.

## Objective

Make the habitat offer species-aware, justify (or remove) the questionable
H-equation terms, remove duplicated state variables, and fix the
GeoPackage/driver redundancies. This pack is made up of questions more than
detected errors, so an initial systematic review phase is needed to be done
before changing anything.

## Notes (verbatim)

- **p.29 A.1** — "The habitat must be adapted to mosquito species, so each mosquito species is more or less adapted to it"
  *(today `update_habitat_day()` uses `default_species_weights()` — the neutral row — not the active species row)*
- **p.18** (eq. 2) — "why 0.75 multiplied to B_i?" / "buildings add suitability to open areas?" / (forest) "why? If zero? why keeping it?"
- **p.19** (urban rationale) — "review how is human water storage modelled?"
- **p.4** (state table) — "!! repeated (it seems that variables repeated int the class)" (`k_habitat`, `habitat_dry_days`, `dry_days`)
- **p.4** — "why having them? Duplicated info? (review)" (`rain_d`, `temp_d`, `salinity_ppt` copied into patch state)
- **p.16** (input table) — "Reveiew if they are constantly recalculated in the ABM." (habitat patches)
- **p.17** (urban class + building fraction) — "build land, Dynamic World V1, if can be extracted from it, be careful with redundancies"
- **p.29 A.6** — GeoPackage `dynamics` column is a string but the loader calls `GetIntField()` (field is 0 for every patch) — "review."

## Initial steps

1. Consume `species.<name>.weights` in `CoordinatorModel::update_habitat_day()`
   / `to_dataframe()` so S and K are species-specific. This is related to m7-3.
2. Justify or remove: `beta_urban = 0.75`, the `+0.30·B` open term, and the
   dormant `forest` type.
3. Review how human water storage is represented behind the urban term.
4. Deduplicate patch/cell state (`k_habitat` vs cell `K`, `dry_days` vs
   `habitat_dry_days`, copied forcing fields).
5. Audit whether the candidate patch set is rebuilt every run (p.16) and
   consolidate urban-class vs building-fraction inputs from Dynamic World.
6. Fix the `dynamics` field type mismatch in `HabitatEngine::load_from_gpkg()`.

## Dependencies / open points

- Species-aware habitat interacts with calibration (pack 08, k_ref) and
  with the species rows already loaded for salinity/host preference.
