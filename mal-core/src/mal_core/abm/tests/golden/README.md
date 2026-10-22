# Committed golden fixtures

These files pin the engine's byte-level behaviour. They are generated from
the self-contained 8×8-cell AOI in `../fixtures/` — **not** from `data/`
(which is gitignored). Regenerate only when an intentional model change
alters the output:

```bash
uv run python mal-core/src/mal_core/abm/tests/fixtures/make_golden_fixtures.py
```

The generator builds `tiny_env.nc`, `tiny_habitat.gpkg` and
`tiny_hosts.nc`, then runs the real engine with seed 42.

Known limitation: `tiny_habitat.gpkg` is **not byte-reproducible** —
GeoPackage stores a creation timestamp in `gpkg_contents`, so regenerating
it produces a diff even when the geometry is identical. The `.nc` and
golden files are byte-stable. Review the `.gpkg` diff (timestamp only)
before committing a regeneration; `git diff --stat` should show no model
change.

| Golden file | Scenario |
|---|---|
| `state_seed42_day5.tif` + `state_seed42_day5.json` + `state_seed42_day5_aquatic.json` | 5 days, no transmission |
| `transmission_seed42_day90.json` | 90 days, `--enable-transmission`, `--initial-vector-infected-frac 0.2` |

The transmission scenario seeds infected vectors so the tiny AOI provably
exercises vector→human→vector (the C++ assertions require `E_V`, `I_V`,
`infectious_bites` and `E_H` to be non-zero). This is a test scenario, not
a model default.
