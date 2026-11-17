# 06 — Observation and output: one artifact, honest fields, one source of truth

> **Status**: pending (2026-11-17). This document holds **only work that has not been
> done**. The shape of the run's artifacts — the individual state (per mosquito and
> per person), the bite and mating ledgers, the aquatic sidecar, the state COG with a
> single band (contract 5.0), the band deprecation at 4.1, and the rule that a reader
> rejects unknown contract versions — is designed in
> `docs/plans/in-process/individualization-and-movement.md` (§10, §11, NFR-6, NFR-7).
> What remains here is the **closure** of the observation layer: the duplicated
> diagnostics, two fields that do not say what they mean, and the triplication of the
> configuration schema.
> **Source**: ODD 2010 review notes
> (`.cache/odd-latex/odd-2010-malariasentinel-notes.tex`), pack 10.
> **ODD sections to amend when this is applied**: §4.11 "Observation", §2.2 "State
> variables", Appendix A.7/A.8, Appendix B.1 "Constants and contracts".

## Objective

Finish the observation layer: one artifact instead of two overlapping diagnostics,
fields whose names match their content, and one source of truth for the configuration
schema.

## Index

| # | Question | Note |
|---|---|---|
| 6.1 | "Aquatic diagnostics" and "Cohort log": two artifacts or one? Should the aquatic diagnostics live in the state COG? | p.12 |
| 6.2 | What is `abm_params_hash` for — and why is it `"sha256:pending"`? | p.29 A.7 |
| 6.3 | `eip_frac` does not measure EIP. What does it measure, and what should it be called? | p.29 A.8 |
| 6.4 | One source of truth for the YAML schema, or three copies with a parity test? | p.30 B.1 |

---

## 6.1 One artifact, and where the aquatic diagnostics belong

**Note (verbatim)** — **p.12** (brace over *Aquatic diagnostics* + *Cohort log*):
"should be one" — **p.12** (Aquatic diagnostics): "include in state COG".

**Current state.** The ODD's §4.11 lists two JSON artifacts: **Aquatic diagnostics**
(total aquatic count, counts by stage) and **Cohort log** (daily adult, larva, egg and
pupa counts). The engine writes `<run>_aquatic.json` as a reserved sidecar
(`output_contract.cpp:93`) next to the state sidecar and `<run>_foci.json`; the
redesign keeps the aquatic sidecar but changes its content (it writes `cell_id` and
the cohort with the mother's position).

**Decision needed.**

1. Do the two artifacts merge into one, and what is it called?
2. Do the aquatic diagnostics become **bands of the state COG** (which implies a
   contract bump, more bands, and a change in every reader of the COG: the surrogate
   training dataset, the prediction loader, the renderers) or stay in the sidecar with
   an explicit name?
3. The "Cohort log" is described as optional — what makes it optional today, and
   should that remain true?

**Done when.** The ODD's §4.11 lists exactly the artifacts the engine writes, each
with its schema, and the sidecar/COG split is a decision, not a legacy.

---

## 6.2 `abm_params_hash`

**Note (verbatim)** — **p.29 A.7**: "What is its use? Eliminate?"

**Current state.** The state sidecar carries `abm_params_hash` with the literal
value `"sha256:pending"` (`output_contract.hpp:60`, written in
`output_contract.cpp:261`). Nothing consumes it; the placeholder is a promise nobody
kept.

**Decision needed.**

1. Compute it for real — of what? The natural candidate is the **configuration dump**
   (`config_dump.cpp`), which is the surface the calibration consumes, not the raw
   YAML.
2. Or eliminate the key from the contract.
3. Or document it as reserved.

**Done when.** The sidecar either carries a real, reproducible hash (same
configuration ⇒ same hash, in every run and on every platform) or does not carry the
key; and the value `"sha256:pending"` no longer appears anywhere.

---

## 6.3 `eip_frac`

**Note (verbatim)** — **p.29 A.8**: "resolve this."

**Current state.** The field is named as the fraction of adults that reached the EIP
threshold, but it is filled as
`post_mort_n_alive / n_alive_before_mortality`
(`mosquito_submodel.cpp:904`), emitted in `main.cpp:1318`, and the ODD's Appendix A
already says: "The cohort log's `eip_frac` is not an EIP fraction."

**Decision needed.**

1. Rename it to what it measures (`adult_alive_frac`) and re-document it, **or**
2. compute the fraction it claims to be (adults whose EIP has been reached) — which
   needs the EIP clock on the vector side and is a real change.
3. Either way: the name is a contract (it is read by the sidecar consumers), so the
   change is a contract bump with a rejection rule in the readers.

**Done when.** The name matches the quantity, the ODD's Appendix A note is deleted,
and every consumer of the sidecar is updated.

---

## 6.4 One source of truth for the configuration schema

**Note (verbatim)** — **p.30 B.1**: "what if only C++ version + Python reads (C++
version)".

**Current state.** The configuration schema lives in **four** places: the YAML
(`mal-core/config/model_constants.yaml`), the pydantic model
(`mal-core/src/mal_core/config_validation.py`), the C++ structs
(`mal-core/src/mal_core/abm/include/mal_abm_fast/config.hpp`) and the dump
(`mal-core/src/mal_core/abm/src/config_dump.cpp`). The redesign accepts the
triplication and covers it with a parity test (NFR-8: "a schema change that touches
only one copy fails CI").

**Decision needed.**

1. Keep the three copies with the parity test (cost: every key change is three
   edits; benefit: the C++ side keeps a typed struct and the Python side keeps
   validation), **or**
2. generate the C++ struct from the YAML (the C++ side reads the YAML at run time
   anyway — there is no compiled constant, `load_config()` is the single access path),
   **or**
3. generate the Python model from the YAML.

**Done when.** The decision is written down, and if generation is chosen, the
generator exists and the parity test becomes a build step.

## Dependencies / open points

- 6.1–6.3 change the output contract and therefore every consumer:
  `mal-core/src/mal_core/prediction/state_loader.py`,
  `mal-core/src/mal_core/training/dataset.py`, the renderers, the surrogate
  checkpoints (which are **not** reusable across contract versions) and the
  calibration scorers. Apply them **after** the contract 4.1/5.0 bump of the
  redesign, each with its own bump.
- 6.4 overlaps with document 05 (provenance table) and with the ODD's generator
  (`tools/gen_concepts_values.py`): if the C++ struct is generated, the same
  generator probably should emit it.
