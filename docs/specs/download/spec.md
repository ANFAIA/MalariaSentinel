# download Spec

> Owns the **plugin system** for fetching raw datasets: the `DOWNLOADER`
> dict convention, the registry, the runner, and the auth gate.
> Returns data in memory; the runner is the single save point.

---

```yaml
# Machine-readable affects block — parsed by the drift-check agent.
# Bidirectional: if A affects B, B must declare affected_by A.
# `target` is the folder name under docs/specs/ (stable across KG migrations).
affects:
  - target: data
    direction: bidirectional
    reason: download writes files under data/<aoi>/ following the naming spec; manifest updates routed through data spec API
    severity: breaking
  - target: ingest
    direction: upstream
    reason: ingest relies on download for the raw inputs (rainfall, water_temp, ndvi, jrc_gsw, dem, wind, hosts)
    severity: breaking
  - target: abm
    direction: upstream
    reason: ABM wrapper calls validate_completeness before start; downloaded files feed the manifest the ABM reads
    severity: non-breaking
  - target: commonlib
    direction: bidirectional
    reason: loaders live in mal_commonlib.data.loaders; AOI param flows from commonlib
    severity: breaking
# Cross-references to the knowledge graph (names only, no UUIDs — survives KG migrations).
kg_refs:
  adrs: [adr-spec-design-2026-07-30]
  patterns: []
  pitfalls: []
  tools: []
```

## Metadata

| Field | Value |
|---|---|
| Component | `mal-core/src/mal_core/download/` + `mal-commonlib/src/mal_commonlib/data/loaders/` |
| Version | `v1.0` (DOWNLOADER convention); `v1.0` (runner API) |
| Status | `stable` |
| Owner | David Flórez-Mazuera |
| Last drift check | `2026-07-30` |

## 1. Objective

The download layer is the **only path raw data enters the system**.
It exists to (1) keep authentication and source-specific logic
encapsulated per dataset, (2) make adding a new dataset a one-file
change, and (3) guarantee that whatever lands on disk matches the
naming and manifest conventions in `data/spec.md`.

Without this spec, every new dataset would reimplement the same
registry/auth/manifest plumbing, and the manifest would diverge.

## 2. In scope

- `DOWNLOADER` dict convention (`name`, `description`, `requires_auth`, `outputs`, `manifest_keys`, `is_time_series`).
- The plugin registry (`LOADER_MODULES`, `discover_downloaders`, `DownloaderSpec`).
- The runner (`run_download`) — orchestrator that discovers, filters, calls, saves, registers.
- Auth vocabulary (`"cds"`, `"earthdata"`, `"planetary_computer"`, `"none"`).
- CLI surface: `malariasim download --aoi <aoi> [--datasets ...] [--outputs ...] [--years ...] [--months ...]`.
- Per-loader implementations in `mal-commonlib/src/mal_commonlib/data/loaders/*.py`.

## 3. Out of scope

- File naming on disk → `docs/specs/data/spec.md` §5.1.
- Manifest schema and read/write API → `docs/specs/data/spec.md` §5.2.
- Auth credential storage (e.g. `~/.cdsapirc`, env vars) — those are deployment concerns.
- AOI definition → `docs/specs/commonlib/spec.md`.

## 4. Public API

| Symbol | Where | Notes |
|---|---|---|
| `run_download(aoi, datasets=None, outputs=None, years=None, months=None, output_dir=None, **kwargs)` | `mal_core.download.runner` | Returns `dict[str, dict]` where keys are downloader names and values are `{"status": "ok"|"skipped"|"error", ...}`. |
| `discover_downloaders()` | `mal_core.download.registry` | Returns `dict[name, DownloaderSpec]`. |
| `list_downloaders()` | `mal_core.download.registry` | Returns `list[{name, description, outputs}]`. |
| `LOADER_MODULES` | `mal_core.download.registry` | Hardcoded list of loader module names to import. Adding a name here is the only step required after creating the loader module. |
| `DownloaderSpec` | `mal_core.download.registry` | Dataclass with `name`, `description`, `requires_auth`, `outputs`, `manifest_keys`, `module_name`, `is_time_series`. |
| `DOWNLOADER` (per-module dict) | `mal_commonlib.data.loaders.<name>` | Loader module's self-description. See §5. |

## 5. Invariants

### §5.1 Loader signature

- **INV-1.** Public loader function signature depends on `is_time_series`:
  - **Time-series** (`is_time_series=True`): `load_<dataset>_<product>(aoi: AOI, *, years: Sequence[int], months: Sequence[int] | None = None, cache_dir: Path | None = None) -> xr.DataArray | xr.Dataset`.
  - **Static** (`is_time_series=False`): `load_<dataset>_<product>(aoi: AOI, *, cache_dir: Path | None = None) -> xr.DataArray`. Some static loaders accept an optional `year: int` (e.g. worldpop) but it is not required.
  - Runner calls `func(aoi=aoi_obj, years=years, months=months, cache_dir=cache)` for time-series and `func(aoi=aoi_obj, cache_dir=cache)` for static.
- **INV-2.** `aoi` is the first positional arg, no exceptions.
- **INV-3.** Time-series loaders declare `year` (and often `month`) without defaults. Static loaders omit them.
- **INV-4.** Loaders **never** accept `output_path`. They return data in memory; the runner calls `save_product()`.

### §5.2 `DOWNLOADER` dict

- **INV-5.** Every loader module exports a `DOWNLOADER` dict with keys `name` (string), `description` (string), `requires_auth` (list[str] from {`"cds"`,`"earthdata"`,`"planetary_computer"`,`"none"`}), `outputs` (dict[str, callable]), `manifest_keys` (dict[str, str]), `is_time_series` (bool, default false).
- **INV-6.** Every key in `outputs` is a real callable (the loader function). Every value in `manifest_keys` is a unique key under `manifest.json`'s `datasets` block.

### §5.3 Runner behaviour

- **INV-7.** Runner discovers `DOWNLOADER`s via `importlib` from `LOADER_MODULES` (no hardcoded registry; one source of truth in `registry.py`).
- **INV-8.** Runner filters by `--datasets` (match `name`) and `--outputs` (match output key inside the dict).
- **INV-9.** Runner uses `spec.is_time_series` (from the DOWNLOADER dict) to branch: time-series loaders get `years` + `months`; static loaders get only `aoi` + `cache_dir`. Signature inspection is not used.
- **INV-10.** Runner passes only kwargs the loader accepts (`accepted = set(sig.parameters)`); unknown kwargs are silently dropped (logged).
- **INV-11.** Runner saves `xr.DataArray` → GeoTIFF, `xr.Dataset` → NetCDF. The runner is the **only** save point.
- **INV-12.** After each successful save, runner calls `update_dataset(aoi, manifest_key, year, path.name)` — see `data/spec.md` §4.
- **INV-13.** Auth gate: if `requires_auth` is non-empty and credentials are missing, the runner reports `{"status": "skipped"}` and does **not** raise.

### §5.4 Registered loaders (current)

| Loader | Auth | Outputs | Manifest keys |
|---|---|---|---|
| `era5` | `cds` | `temp_suitability`, `water_temp`, `wind_6hourly` | `era5_temp`, `era5_water_temp`, `wind` |
| `chirps` | `none` | `rainfall`, `rainfall_daily` | `chirps_rainfall`, `chirps_rainfall_daily` |
| `dem` | `none` | `elevation` | `dem` |
| `jrc_gsw` | `none` | `water_occurrence` | `jrc_water` |
| `modis` | `earthdata` | `ndvi` | `modis_ndvi` |
| `worldpop` | `none` | `population` | `worldpop` |
| `glw` | `none` | `cattle`, `goats`, `sheep`, `pigs`, `chickens` | `glw_cattle`, `glw_goats`, `glw_sheep`, `glw_pigs`, `glw_chickens` |
| `ghsl` | `none` | `urban_class` | `ghsl_urban` |
| `wildlife` | `none` | `wildlife_host_proxy` | `wildlife_proxy` |
| `buildings` | `none` | `building_fraction` | `buildings` |

- **DEPRECATED**: `worldcover` — archived to `_legacy/worldcover.py`. Use `jrc_gsw` for `water_frac`.

## 6. Data contracts

- Output on disk: `data/<aoi>/<aoi>_<product>_<year>.<ext>` or `data/<aoi>/<aoi>_<product>.<ext>` — see `data/spec.md` §5.1.
- In-memory return: `xr.DataArray` (raster) or `xr.Dataset` (multi-var, typically wind or env daily).
- Manifest update via `data/spec.md` §4.

## 7. Migration & deprecation

- Adding a loader: create `mal-commonlib/.../loaders/<name>.py`, export `DOWNLOADER`, append `"<name>"` to `LOADER_MODULES` in `registry.py`. Non-breaking (MINOR).
- Renaming a manifest key: BREAKING (MAJOR). Requires updating the ABM wrapper, ingest builders, and any consumer that calls `get_dataset_files(aoi, "<old_key>")`.
- Deprecating a loader: move to `_legacy/`, keep the module importable but drop from `LOADER_MODULES`. Document the replacement in §5.4.
- Deprecation policy: 1 MINOR spec version carries the warning; removed in the next MAJOR.

## 8. Drift check

```bash
# INV-5/6: every registered module exports DOWNLOADER with the required keys
uv run python -c "
from mal_core.download.registry import discover_downloaders, LOADER_MODULES
for name, spec in discover_downloaders().items():
    assert spec.name and spec.requires_auth is not None and spec.outputs and spec.manifest_keys, f'bad DOWNLOADER for {name}'
"

# INV-1/2: loader signatures have aoi as first positional, no output_path
rg "def\s+load_\w+\(" mal-commonlib/src/mal_commonlib/data/loaders/ -A 2 | rg -v "aoi(: AOI)?\s*," && echo "FAIL: loader missing aoi as first arg" || echo "OK"
rg "output_path" mal-commonlib/src/mal_commonlib/data/loaders/ && echo "FAIL: loader accepts output_path" || echo "OK"

# INV-7: registry discovery imports only from LOADER_MODULES
uv run python -c "
from mal_core.download.registry import discover_downloaders
from mal_commonlib.data import loaders
import os
on_disk = {f[:-3] for f in os.listdir(os.path.dirname(loaders.__file__)) if f.endswith('.py') and not f.startswith('_')}
on_disk -= {'__init__'}
registered = set(discover_downloaders().keys())
extra = on_disk - registered - {'_legacy'}
assert not extra, f'unregistered loader modules: {extra}'
"

# INV-9: is_time_series flag matches loader signature
uv run python -c "
import inspect
from mal_core.download.registry import discover_downloaders
for name, spec in discover_downloaders().items():
    for out_name, fn in spec.outputs.items():
        sig = inspect.signature(fn)
        has_years = 'years' in sig.parameters
        if spec.is_time_series:
            assert has_years, f'{name}.{out_name}: is_time_series=True but no years param'
        else:
            assert not has_years, f'{name}.{out_name}: is_time_series=False but has years param'
"
```

## 9. Examples

```python
# Programmatic usage
from mal_core.download import run_download
result = run_download(
    aoi="ghana",
    datasets=["era5", "chirps"],
    outputs=["temp_suitability", "rainfall"],
    years=[2024],
)
assert result["era5"]["status"] == "ok"
```

```python
# Loader (in-memory; runner does the save)
from mal_commonlib.data.loaders.era5 import load_era5_temp_suitability
from mal_commonlib.aoi import AOI

aoi = AOI.from_slug("ghana")
da = load_era5_temp_suitability(aoi, years=[2024], months=[7])
assert da.shape == aoi.cells_per_side()
```

CLI:

```bash
malariasim download --aoi ghana --datasets era5,chirps --outputs temp_suitability,rainfall --years 2024
malariasim download --aoi ghana --all
```

## 10. References

- KG ADR: `adr-spec-design-2026-07-30`.
- Specs (by folder): `commonlib`, `data`, `ingest`, `abm`, `pipeline`.
- External: Copernicus CDS API docs, NASA Earthdata Login, Microsoft Planetary Computer.