# M-perf F1.e parity test

`test_abm_fast_parity.py` runs the Python ABM (`mal_ghana_sim.abm`)
and the C++ ABM (`mal-abm-fast`) on the same synthetic (env,
habitat, seed, days) inputs and asserts the 2-band state COG
**per-band means** agree to within 1e-3. The 1e-3 tolerance — not
1e-5 — is the F1.e thin-slice target; the strict per-pixel
parity lives in F1.g.

Run from the monorepo root:

```bash
cd mal-ghana-sim && uv run pytest tests/test_abm_fast_parity.py -v
```

The C++ binary is built on demand by the `mal_abm_fast_binary`
session fixture in `conftest.py` if it isn't already at
`mal-abm-fast/build/src/mal_abm_fast`.
