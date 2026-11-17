# 01 — Habitat and environment: species coherence, potential terms, sea and salinity

> **Status**: pending (2026-11-17). This document holds **only work that has not been
> done**. The parts already covered by other plans are not repeated here: they live in
> `docs/plans/in-process/individualization-and-movement.md` (§9 — the aquatic state
> becomes a per-cell registry, "patch" becomes an eligibility filter, one source of
> habitat potential) and in `docs/plans/completed/per-stage-conceptual-documentation.md`
> (the ODD's generated parameter table).
> **Source**: ODD 2010 review notes
> (`.cache/odd-latex/odd-2010-malariasentinel-notes.tex`), packs 05 and 06.
> **ODD sections to amend when this is applied**: §6 "Input data" (the coastal band),
> §7.1 "Update habitat availability and capacity", and the generated parameter table
> for `habitat.*`.

## Objective

Make the habitat offer **species-aware**, give a defensible account of the two
contested terms of the potential equation, model the sea as something that is *not*
habitat but *does* affect its neighbours, and make the salinity channel actually
bite.

## Index

| # | Question | Note |
|---|---|---|
| 1.1 | The habitat is computed with the neutral species row — should it be species-specific? | p.29 A.1 |
| 1.2 | Why `0.75 × lc_built`? Why does built land add suitability to open areas? | p.18 (eq. 2) |
| 1.3 | Is human water storage behind the urban term? | p.19 |
| 1.4 | Is the candidate patch set rebuilt on every run? | p.16 |
| 1.5 | Urban class versus building fraction, from Dynamic World | p.17 |
| 1.6 | Open-sea cells are candidate habitat; the sea must still affect coastal cells | p.17, p.30 A.14 |
| 1.7 | Does the salinity channel gate habitat and larval survival end-to-end? | p.17 |

---

## 1.1 Species-aware habitat

**Note (verbatim)** — **p.29 A.1**: "The habitat must be adapted to mosquito species,
so each mosquito species is more or less adapted to it".

**Current state.** `CoordinatorModel::update_habitat_day()` computes the habitat with
the **neutral** species row, not the row of the species in play:
`coordinator.cpp:117` (`default_species_weights()`) and `coordinator.cpp:216`
(`species_accuracy(h, default_species_weights(), z_[idx])`). The six habitat types
(`surface_persistent`, `wetland_persistent`, `urban_persistent`, `wetland_pluvial`,
`open_pluvial`, `crop_pluvial`) and the six species rows are all present in
`model_constants.yaml` (`habitat_types.types`, `species.*`), but the per-species
affinity is not applied to S or to K.

**Decision needed.**

1. Which of S and K becomes species-dependent, and which stays a property of the
   cell? (S = Σ_g w[s,g]·H[i,g]·A[k(g)] is defined per species; K_gt_habitat =
   `k_ref`·cell_area_km2·S is derived from it, so the choice propagates.)
2. Which cells hold which species in a run — is the species a property of the AOI
   (one species per run) or something that varies per cell (a species mix)?
3. What happens to the species that do not occur in the AOI: their rows stay in the
   YAML as data, but nothing consumes them.

**Done when.** The habitat of a run is computed with the weights of the species it
simulates, the C++ mirror (`habitat_availability.hpp`) and the Python reference
(`mal_core/habitat/`) agree, and the parity test
(`test_habitat_python_contract.py`) covers the species-specific path.

---

## 1.2 The two contested terms of the potential equation

**Note (verbatim)** — **p.18 (eq. 2)**: "why 0.75 multiplied to B_i?" / "buildings add
suitability to open areas?" / (forest) "why? If zero? why keeping it?"

**Current state.** The potential is computed in
`mal-core/src/mal_core/habitat/potential.py::static_potential()`:

| Term | Code | Constant |
|---|---|---|
| `urban_persistent` | `_clip(_BETA_URBAN * u)` | `habitat.beta_urban = 0.75` (`model_constants.yaml:43`) |
| `open_pluvial` | `_clip(o + _RAIN_POOLS_BUILT_DAMAGE * u)` | `habitat.rain_pools_built_damage = 0.3` (`model_constants.yaml:44`) |

The `forest` type **no longer exists** in the contract v3.0 habitat set (six types,
above), so that part of the note is a question about the *document*, not the code:
either the ODD must stop mentioning a forest term, or the type comes back.

**Decision needed.**

1. What does `0.75 × lc_built` represent physically, and what published value backs
   it? (Urban as persistent breeding habitat — anophelines are urban vectors, but the
   factor is a number without a source.)
2. Is `+0.3 × lc_built` on the open pluvial type the same mechanism as (1) (rainwater
   held on impervious surfaces) or a different one? If the same, it should be one
   parameter, not two.
3. Does the forest term return, and with what data source (Dynamic World label
   `trees`)?

**Done when.** Each of the three has either a published anchor in `papers/REFERENCES.md`
or is explicitly marked as an engineering prior with its tier `[EP]`, and the ODD's
equation matches the code.

---

## 1.3 Human water storage behind the urban term

**Note (verbatim)** — **p.19**: "review how is human water storage modelled?"

**Current state.** There is **no** storage term: water availability is computed from
the climate planes (rainfall, temperature) and the habitat types. What the note
probably points at is that the urban term stands in for a *human-made* water body
(tanks, drums, rooftops) that the model represents only as a fraction of built
surface.

**Decision needed.** Is human water storage a separate habitat type (its own H plane
and its own dynamic response), a sub-term of `urban_persistent`, or out of scope?
If it is a separate type, it needs a data source (Dynamic World cannot see a water
tank).

**Done when.** The decision is written down in the habitat contract and, if a new type
is added, the contract version is bumped and the ingest pipeline produces it.

---

## 1.4 Is the candidate patch set rebuilt on every run?

**Note (verbatim)** — **p.16**: "Reveiew if they are constantly recalculated in the ABM."

**Current state.** The habitat GeoPackage is a **static** input: it is loaded once per
run by `HabitatEngine::load_from_gpkg()` and the candidate set (features above the
`habitat_potential ≥ 0.01` floor, `habitat_engine.cpp:216`) is a property of the
file, not of the day. The per-day part is the availability `A[k]` (persistent = 1,
pluvial = z) and the capacity `K`.

**Decision needed.** Is the question about (a) the *cost* of rebuilding the candidate
set on every run — in which case the answer is "it is not rebuilt, and that is
correct" — or (b) the *correctness* of a candidate set that never changes, when the
habitat may dry out and come back?

**Done when.** The answer is recorded in the ODD (which currently describes the
candidate set as static) and, if (b), the dynamic part is specified.

---

## 1.5 Urban class versus building fraction, from Dynamic World

**Note (verbatim)** — **p.17**: "build land, Dynamic World V1, if can be extracted from
it, be careful with redundancies".

**Current state.** The contract v3.0 statics are `jrc_persistent` + four Dynamic
World fraction planes: `lc_built`, `lc_wetland`, `lc_open_plus_water`, `lc_crop`
(DW label 6 → `lc_built`; 3 → `lc_wetland`; 2, 5, 7, 0 → `lc_open_plus_water`; 4 →
`lc_crop`). "Urban class" and "building fraction" are therefore **the same plane**
today; if a second urban quantity is wanted (e.g. a class-level "urban" label rather
than a built-area fraction), it would be redundant with `lc_built`.

**Decision needed.** Is there a distinct quantity to extract, or is the note a
warning against double-counting the built fraction in two terms (see 1.2)?

**Done when.** The decision is recorded and, if a new plane is added, the contract
version is bumped and the ingest produces it.

---

## 1.6 Open sea is not habitat, but it affects its neighbours

**Note (verbatim)** — **p.17** (open-sea limitation): "Mosquitoes cannot be born on
the sea but it must affect near coastal cells." — **p.30 A.14**: "Remove them from
suitability, but affect surrounding."

**Concrete case.** Gulf of Guinea cell row 745, col 275: `lc_open_plus_water = 1`,
`H_total = 1`, `S ≈ 0.40` at z = 1 — it is a **candidate patch**. Sea temperature is
the 0.0 sentinel, so development is zero, but adults still survive at the 0.60
floor: the cell is dead habitat that is not obviously dead.

**Decision needed.**

1. How is the sea masked out of the candidate set: at ingest (a sea mask on the
   `lc_open_plus_water` plane, or the `land_frac` plane already carried by
   `ClimateEngine`), or at run time (the engine drops cells whose land fraction is
   below a threshold)?
2. What is the coastal influence mechanism — sea-surface temperature buffering,
   a salinity gradient, wind, or a combination? Which of them has a source?
3. How far does the influence reach (one cell, a distance)?

**Done when.** The mask exists and the coastal influence has a specified mechanism
with a published anchor, and the row 745 / col 275 cell is no longer a candidate
patch but still influences its neighbours.

---

## 1.7 Does salinity actually gate anything?

**Note (verbatim)** — **p.17** (salinity limitation): "Review that salinity has effect
on watters, and that the see is properly identify".

**Current state.** The salinity response exists in the configuration (per-species
`salinity_opt_ppt`, `salinity_hi_tol_ppt`, `salinity_slope` — six rows in
`model_constants.yaml`) and the C++ side applies the factor
`s = (1−frac)·exp(−slope·(psu−opt))`, hard-capped at 0 above `hi_tol`. But the
**delivered Ghana product has no salinity channel**: `salinity_missing_psu = 0.0`
("sin datos ⇒ agua dulce (UNA clave para 6 sitios)"), so everything in Ghana today is
freshwater, and the code path is untested against real data.

**Decision needed.** Is the salinity channel (a) sourced for the AOIs the project
targets, or (b) explicitly declared "not available in the current products, therefore
always freshwater", with the salinity response left as a documented capability?

**Done when.** Either the products carry a salinity plane and the end-to-end gate is
verified, or the ODD says plainly that the current products are freshwater and the
salinity response is inert.

## Dependencies / open points

- 1.2, 1.5 and 1.6 touch the same ingest pipeline: do the ingest change **once**.
- 1.1 changes the habitat numbers and therefore the calibration baseline; it should
  land with the provenance audit (document 05) or right after it.
- 1.6 is an ingest-side change → a new env-NC product (contract 3.0 bump?).
- Changing the potential shifts the calibration: rerun the scorers.
- For 1.6, the sea detection is meant to be validated by generating images and
  having them reviewed by an external subagent (the original step).
