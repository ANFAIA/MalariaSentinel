# mal-commonlib — Shared Library

Zero-dependency shared code for every MalariaSentinel package: configuration,
paths, the AOI registry, and data/terrain utilities. Nothing here contains
pipeline logic — stable pipeline code belongs in `mal-core`.

## Layout

| Path | Purpose |
|---|---|
| `src/mal_commonlib/aoi.py` | `AOI` model (pydantic) + `Scale` enum + `AOI.from_slug()` — bbox, CRS, resolution, geometry helpers |
| `src/mal_commonlib/aois.yaml` | **AOI registry** — single source of truth for slug → AOI mappings (add a new AOI here, no code changes) |
| `src/mal_commonlib/config.py` | Simulation parameters (`SimParams`), thermal responses (`temp_suitability`, `mortality_rate`), repo paths |
| `src/mal_commonlib/data/` | Data utilities: host loaders (`loaders/`), `host_utils.py`, mobility helpers, generic utils |
| `src/mal_commonlib/terrain/` | TWI (topographic wetness index) helpers |
| `tests/` | pytest suites (chirps, coastline, host loaders, mobility) |

## Adding a new AOI

1. Edit `src/mal_commonlib/aois.yaml` — add an entry with `slug`, `name`,
   `bbox [W,S,E,N]`, `crs`, `resolution_m`, `scale`, and `iso3` (required for
   country-scoped loaders: WorldPop, GADM, livestock).
2. `AOI.from_slug("<slug>")` picks it up at runtime; every `malariasim`
   command accepts `--aoi <slug>`.
3. Add a test if the AOI exercises a new code path.

## Tests

```bash
cd mal-commonlib && uv run pytest -v
```
