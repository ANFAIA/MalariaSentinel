# 07 — Engine hygiene: dead paths, duplicated state, one type for one column

> **Status**: pending (2026-11-17). This document holds **only work that has not been
> done**. The parts already covered by other plans are not repeated here: the removal
> of the cell-attraction field, the retirement of `update_patch_id` and
> `dispersal.snap_radius_m`, and the per-cell aquatic registry live in
> `docs/plans/in-process/individualization-and-movement.md` (§4, §9), as does the
> retirement of `host_seeking_scale_m`, `host_seeking_radius_m`,
> `dispersal.host_flight_step_m`, `oviposition.scale_m` and
> `gonotrophic.feeding_success_rate` (§12).
> **Source**: ODD 2010 review notes
> (`.cache/odd-latex/odd-2010-malariasentinel-notes.tex`), packs 12, 03 (A.3), 05
> (state table, A.6).
> **ODD sections to amend when this is applied**: §3 "Process overview and scheduling",
> §5.2 "Mosquito seeding", §5.3, §7.6 "Seek hosts and feed", §2.2 "State variables",
> and the input-data section for the `dynamics` column.

## Objective

Remove the code paths that are dead, misleading or scientifically meaningless, and
make each field and each column mean exactly one thing.

## Index

| # | Item | Note |
|---|---|---|
| 7.1 | The no-host fallback must go: without hosts there is no malaria simulation | p.25, p.14 |
| 7.2 | A run with an empty initial population must stop, not simulate zero vectors | p.13 |
| 7.3 | Why is the number of days capped at 731? | p.5 |
| 7.4 | Is the `host-weighted` seeding mode useful? | p.13 |
| 7.5 | The round-robin submodel constructor | p.30 A.11 |
| 7.6 | The unused 12-hourly `multirate_scheduler` | p.29 A.3 |
| 7.7 | Duplicated state: `k_habitat` vs `K`, `dry_days` vs `habitat_dry_days`, copied forcing fields | p.4 |
| 7.8 | The GeoPackage `dynamics` column: string written, int read | p.29 A.6 |

---

## 7.1 The no-host fallback

**Note (verbatim)** — **p.25** (fallback feeding): "eliminate this option, there must
be humans, if no, there is no meaning for the simulation of malaria." — **p.14**:
"Host landscape must be compulsory without host no malaria."

**Current state.** When no host is found, the feeding path falls back to a
deterministic meal on a default host (`mosquito_submodel.cpp:771`: "Fallback:
deterministic feeding with default host (HUMAN)"), and the cell search falls back to
the original binary check at the current cell (`mosquito_submodel.cpp:682`).

**Decision needed.** Make the host landscape **compulsory**: error out when the
simulation is asked to transmit without hosts, instead of inventing a meal. The
error has to distinguish "no hosts in the landscape" (a configuration error) from "no
host reachable tonight" (a legitimate state).

**Done when.** The fallback branch does not exist, and the CLI fails with a clear
message and a non-zero exit code.

---

## 7.2 Empty initial population

**Note (verbatim)** — **p.13**: "Without population simulation must stop."

**Current state.** A run whose seeding produces no mosquitoes continues and produces
a full set of artifacts with zero vectors everywhere — indistinguishable, downstream,
from a run where transmission failed.

**Decision needed.** Abort with a clear error (message, exit code) when the initial
population is empty. Decide whether the check happens after seeding only or also
after a seeding mode that is expected to fail (e.g. `random-viable` with no viable
foci).

**Done when.** The run aborts, and the scenario harness has a case that asserts it.

---

## 7.3 The 731-day cap

**Note (verbatim)** — **p.5**: "why limit?"

**Current state.** The CLI accepts 1..731 days: `--days` and `--rollout-days` are
checked with `CLI::Range(1, 731)` / `CLI::Range(0, 731)` (`main.cpp:510, 520`); the
number is the length of 2024 + 2025, i.e. it is a **data-availability** artefact
rather than a modelling one.

**Decision needed.** Remove the cap, or justify it (as "the length of the climate
product") and make the check a *warning* against the actual data length instead of a
magic number.

**Done when.** The cap is gone or documented with its real reason, and the error
message (if any) names the data, not a number.

---

## 7.4 The `host-weighted` seeding mode

**Note (verbatim)** — **p.13**: "review the usefulness of this last mode."

**Current state.** `build_seed_instructions_host_weighted()` (`seeding.hpp:167`) is a
third seeding mode alongside the random and the explicit one; the mode list is
selected by `--seeding-mode`.

**Decision needed.** Does the mode still have a use after the redesign (which makes
seeding per-individual and derives the population from the manifest)? If not, remove
it together with its tests; if yes, state for which scenario it is the right tool.

**Done when.** The mode list has a reason for each entry, and the removed ones leave
no dead code.

---

## 7.5 The round-robin constructor

**Note (verbatim)** — **p.30 A.11**: "Is the movement of mosquito? if so remove and
change by new mosquito movement submodel".

**Current state.** The submodel has an explicit per-patch round-robin constructor
(`mosquito_submodel.hpp:104`, test `ConstructionSeedsRoundRobin`).

**Decision needed.** With the new movement law, is the round-robin placement still a
meaningful way to initialise adults? If not, remove it (constructor, test, and the
call site).

**Done when.** The constructor is gone or has a documented role, with its test
updated accordingly.

---

## 7.6 The unused 12-hourly `multirate_scheduler`

**Note (verbatim)** — **p.29 A.3**: "Eliminate this complicated and unused system,
change to vectorized version of movement mentioned before."

**Current state.** `multirate_scheduler.hpp` implements a daily outer step with
twelve hourly night sub-steps, and it is **not** unused in the strict sense:
`mosquito_submodel.hpp:41` includes it and `mosquito_submodel.hpp:274` holds a
`MultirateDayState night_state_` member; tests reference it (`test_config.cpp:16`,
`test_gonotrophic.cpp:3`). It is the scaffold of the temporal base that the redesign
replaces with its two-band micro-integrator.

**Decision needed.** Delete the module, the member and the test references once the
micro-integrator has landed — or keep it, with the reason (e.g. the hourly night
sub-steps are still used for the wind window).

**Done when.** The module is gone from the build, or the ODD says what still uses the
hourly sub-steps.

---

## 7.7 Duplicated state

**Note (verbatim)** — **p.4** (state table): "why having them? Duplicated info?
(review)" and "!! repeated (it seems that variables repeated in the class)".

**Current state.** The per-cell state carries both the capacity (`k_habitat`) and the
derived suitability (`habitat_avail`), both the dry streak (`dry_days`) and the
habitat's own dry flag (`habitat_dry_days`), and a copy of the forcing fields
(`rain_d`, `temp_d`, `salinity_ppt`) that the climate engine already owns.

**Decision needed.** For each pair, which one is the state and which one is a derived
view? Then: does the state object hold the forcing fields at all, or does it query
the climate engine when it needs them?

**Done when.** No field in the state carries a value that another field already
implies, and the ODD's state table lists each quantity once.

---

## 7.8 The `dynamics` column: string written, int read

**Note (verbatim)** — **p.29 A.6**: "review."

**Current state.** Python writes `dynamics` as the string `persistent|pluvial`
(`ingest/env.py:88`); the C++ engine reads it as an integer
(`habitat_engine.cpp:220`) and therefore always gets 0. It is harmless today because
the persistent/pluvial split is recomputed from the H planes, but it is a type lie in
a contract file.

**Decision needed.** Pick one: the producer writes the int, or the consumer reads the
string. The redesign's synthetic harness already writes the int
(`individualization-and-movement.md` §13.5) and notes that this is a contract
change; the production pair has to be fixed too.

**Done when.** The producer and the consumer agree, and a round-trip test writes and
reads the column.

## Dependencies / open points

- 7.1, 7.2 and 7.3 change the CLI contract (error messages, exit codes): decide the
  UX once, together.
- 7.4 and 7.5 touch the seeding, which the redesign changes (per-individual seeding,
  §13.3): apply them **after** it, or in the same pull request.
- 7.6 must wait for the redesign's micro-integrator (step 4).
- 7.7 touches the same state object that the redesign rewrites (§9): apply it after,
  or in the same pull request.
- 7.8 is a producer/consumer contract change → contract bump, and the GeoPackage
  schema has to change with it.
