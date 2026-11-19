# mal-commonlib — Shared Library

Zero-dependency shared code for every MalariaSentinel package: configuration,
paths, the AOI registry, and data/terrain utilities. Nothing here contains
pipeline logic — stable pipeline code belongs in `mal-core`.

## Layout

| Path | Purpose |
|---|---|
| `src/mal_commonlib/aoi.py` | `AOI` model (pydantic) + `Scale` enum + `AOI.from_slug()` — bbox, CRS, resolution, geometry helpers |
| `src/mal_commonlib/aois.yaml` | **AOI registry** — single source of truth for slug → AOI mappings (add a new AOI here, no code changes) |
| `src/mal_commonlib/model_constants.py` | The shared py⇄C++ model constants, read from `mal-core/config/model_constants.yaml` |
| `src/mal_commonlib/config.py` | Repo paths, the deprecated AOI/grid constants, the env layer file names, the legacy v1 rollout knobs (`SimParams`) and the training constants |
| `src/mal_commonlib/data/` | Data utilities: host loaders (`loaders/`), `host_utils.py`, generic utils |
| `tests/` | pytest suites (chirps, coastline, host loaders) |

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
