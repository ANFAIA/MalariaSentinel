# habitat — single source of shared model constants

**The single source is `mal-core/config/model_constants.yaml`** (contract
version in `version:`; contracts frozen: `contracts.env_nc = "3.0"`,
`contracts.cogs_state = "4.0"`).

Rules (plan `constants-yaml-plan` §1, enforced by the loader and the tests):

- **No silent fallbacks.** A missing key raises listing ALL missing keys; an
  unknown key raises; a wrong type raises. Both loaders (py:
  `mal_core.habitat.config`, C++: `mal_abm_fast::load_config()`) do this.
- **No duplicated defaults in code.** `habitat/constants.py` is a tombstone —
  module `__getattr__` raises for every name. The py-diagnostic constant
  `K_REF_DIAG_PER_KM2` lives in `mal_core.habitat.capacity` (0.143·9.3·1e6
  ind·km⁻²·d⁻¹; NOT the engine's `species.k_ref = 50.0` — different concepts,
  plan §9.1).
- **Calibration PRs touch the YAML ONLY** — plus a version bump if a
  frozen sub-contract changes (6 habitat types order, dynamics split,
  contracts keys, rng seed names).
- Override for experiments: `MAL_MODEL_CONSTANTS=/path/to/override.yaml`
  (loader logs every load).
- Parity: py⇄C++ raw dump equality is tested key-by-key
  (`test_config_loader.py::test_cxx_dump_raw_parity`, `config_dump` tool).
- Anti-hardcode: `tools/check_no_constants.sh` greps the forbidden
  identifiers/literals out of migrated sources.

The engine reads the same YAML at startup via the yaml-subset parser
(`abm/src/config.cc`, NO yaml-cpp): weights/pref-like rows are parsed BY
NAME (habitat type name → internal ZoneId; host types), pre-transformed so
the day-loop consumes pure arrays; `num_persistent` is DERIVED from
`habitat_types.dynamics` (no positional rule).
