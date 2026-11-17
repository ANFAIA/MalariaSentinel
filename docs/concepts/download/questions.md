# download — question set

This file is the question set for the conceptual document of the **download
stage** of the MalariaSentinel pipeline (the stage that brings raw external
data into `data/<aoi>/` and registers it in the AOI manifest). It was
compiled by reading the implementation: `mal-core/src/mal_core/download/`
(`catalog.py`, `manifest.py`, `registry.py`, `runner.py`, `writer.py`), the
loader plugins in `mal-commonlib/src/mal_commonlib/data/loaders/`, the
`download` and `datasets` subcommands of `mal-core/src/mal_core/cli.py`, the
consumer side (`mal-core/src/mal_core/ingest/daily_nc.py`,
`mal-core/src/mal_core/abm/wrapper.py`), the AOI registry
(`mal-commonlib/src/mal_commonlib/aois.yaml`) and the constants file
(`mal-core/config/model_constants.yaml`). The retired download and data specifications (their audit trail is now
`docs/plans/in-process/spec-retirement-ledger.md`) were used only as
material: several of their claims are already contradicted by the code, so
every question below is anchored on code, and where the two disagree the
question says so. The stance the document must answer is the one in
`docs/concepts/README.md` (S1–S10).

---

## (a) Question set

### Purpose and boundary

**1. What question does the download stage exist to answer, and what would
count as it having answered it? What is explicitly *not* its job?**

- Citation: `mal-core/src/mal_core/download/runner.py:69` (the single
  orchestrator), `mal-core/src/mal_core/download/writer.py:12` (the single
  save point), `mal-core/src/mal_core/download/catalog.py:1-31` (module
  docstring: "the single place where dataset identity lives").
- Answer: it answers "do the external datasets this AOI needs exist on this
  machine, in the AOI's grid, and are they recorded in the manifest?" It is
  not the place where data is interpreted, resampled into the env tensor, or
  modelled — that is ingest. The runner is the only writer of `data/<aoi>/`
  products and the only registrar of manifest entries.

**2. What are the entry points into the stage, and what does each one expose?**

- Citation: `mal-core/src/mal_core/cli.py:157-193` (`download` subcommand),
  `mal-core/src/mal_core/cli.py:809-841` (`datasets` subcommand),
  `mal-core/src/mal_core/download/__init__.py:1-27` (public re-exports).
- Answer: the CLI subcommand `malariasim download --aoi … [--datasets …]
  [--outputs …] [--years …] [--months …] [--output-dir …]`, the inspection
  command `malariasim datasets --aoi … [--missing]`, and the Python API
  `run_download(...)` plus the manifest/catalog functions re-exported from
  `mal_core.download`.

**3. Does the CLI expose a `--all` flag, and what happens if a user passes
one (as the runner's own error message and the CLI docstring both suggest)?"

- Citation: `mal-core/src/mal_core/cli.py:157-165` (the option list of
  `download`: no `--all`), `mal-core/src/mal_core/cli.py:171-173` (docstring
  example `malariasim download --aoi ghana --all`),
  `mal-core/src/mal_core/abm/wrapper.py:118-121` (error text "Run:
  malariasim download --aoi {aoi} --all").
- Answer: **the flag does not exist**; the documented invocation is wrong and
  the ABM's remediation hint is therefore not executable. "Download
  everything" is expressed by passing no `--datasets` and no `--outputs`
  (see Q8). → also listed in part (c).

**4. Is the "load-or-download" API (manifest check → load if present →
download and register if absent) actually implemented?**

- Citation: repository-wide search finds no `load_or_download` symbol;
  the closest code is `mal-core/src/mal_core/download/catalog.py:155-268`
  (manifest-only resolution) and
  `mal-core/src/mal_core/download/runner.py:69-278` (download + register).
- Answer: **no**. The loaders in `mal_commonlib.data.loaders` always fetch
  from the provider; the manifest is only *written* by the runner and *read*
  by consumers. The convention described in `AGENTS.md` ("Load-or-download
  API: public functions `load_<dataset>_<product>` check manifest → load if
  exists → download+register if missing") is not reflected in the code.
  → part (c).

### The loader registry

**5. How is the set of datasets determined, and what happens to a loader
module that is added, moved or retired?**

- Citation: `mal-core/src/mal_core/download/registry.py:12-25`
  (`pkgutil.iter_modules` over `mal_commonlib.data.loaders`), `:47-107`
  (`discover_downloaders`), `mal-commonlib/src/mal_commonlib/data/loaders/_legacy/`
  (packages are skipped by the scan), `mal-core/src/mal_core/download/registry.py:102-106`
  (per-module exception tolerance).
- Answer: every non-package module in the loaders package that exports a
  `DOWNLOADER` dict is a plugin; `_legacy/` is a subpackage and therefore
  invisible to the scan. A module that raises on import is logged as a
  warning and skipped, not fatal.

**6. What fields does a loader's `DOWNLOADER` dict declare, and what does the
registry add on top of it?**

- Citation: `mal-core/src/mal_core/download/registry.py:31-45`
  (`DownloaderSpec` fields), `:63-101` (profile defaults and formats keyed
  by loader name).
- Answer: the loader declares `name`, `description`, `requires_auth`,
  `outputs` (output name → callable), `manifest_keys` (output name → manifest
  key), `is_time_series`, optionally `formats` (per output: `"monthly"`,
  `"daily"`, `"monthly_nc"`), `required_for_abm`, `reductions`, `license`,
  `attribution`. The registry supplies fallbacks for `formats` and
  `abm_default_outputs` from a hard-coded profile table keyed by loader name.

**7. List every loader that the registry discovers, with its provider,
authentication requirement and manifest keys.**

- Citation (each loader's `DOWNLOADER` dict):
  `era5.py:478-508` (CDS, `cds`), `chirps.py:331-352` (CHIRPS v2.0, no auth),
  `jrc_gsw.py:345-363` (JRC GSW via Microsoft Planetary Computer, no auth),
  `dynamic_world.py:486-501` (Google Dynamic World V1 via Earth Engine,
  `earthengine`), `worldpop.py:459-473` (WorldPop, no auth),
  `glw.py:251-274` (FAO GLW4, five species, no auth),
  `ghsl.py:274-290` (GHS-SMOD, no auth), `buildings.py:225-240` (Overture
  Maps on S3, no auth), `wildlife.py:275-293` (derived, no auth),
  `coastline.py:395-415` (GSHHG, no auth), `smap.py:421-439` (SMAP RSS L3,
  `earthdata`), `modis.py:436-452` (MOD13A3, `earthdata`).
- Answer: twelve live loaders. Providers and credentials are as listed
  above; the manifest key for each output comes from that loader's
  `manifest_keys` and nowhere else.

**8. What does "download everything" mean, and how is it distinguished from
an explicit selection?**

- Citation: `mal-core/src/mal_core/download/runner.py:104-108`
  (`use_abm_profile = datasets is None and outputs is None`),
  `:110-116` (per-loader auth gate and skip),
  `:118-121` (output filtering against `abm_default_outputs`).
- Answer: with neither `--datasets` nor `--outputs`, the runner takes every
  registered loader but keeps only the outputs listed in the loader's
  `abm_default_outputs` (from the registry profile table when the loader
  does not declare its own). Naming `--datasets` or `--outputs` disables the
  profile entirely and selects exactly what was named.

**9. Which outputs are in the ABM profile, and is the profile table
consistent with what the loaders themselves declare?**

- Citation: `mal-core/src/mal_core/download/registry.py:63-91`
  (profile table: chirps→`rainfall_daily`, era5→`air_temp_daily`,
  `wind_6hourly`, jrc_gsw→`habitat_features`, dynamic_world→`class_fractions`,
  worldpop→`population`, glw→five species, ghsl→`urban_class`,
  buildings→`building_fraction`, wildlife→`wildlife_host_proxy`,
  coastline→`land_mask`, hydrorivers→`[]`, smap→`[]`),
  `mal-commonlib/src/mal_commonlib/data/loaders/modis.py:436-452` (the
  `modis` loader declares no `abm_default_outputs` and is absent from the
  profile table).
- Answer: **`modis` has no entry in the profile table and declares none of
  its own, so its `abm_default_outputs` is `None`, which the runner treats
  as "no filtering"** (`runner.py:119-121`): the NDVI product is therefore
  downloaded by a default (unfiltered) `download` run even though the
  retired spec listed it as "not an ABM default". `smap` and the retired
  `hydrorivers` are explicitly excluded. → part (c).

**10. Which datasets are declared `required_for_abm`, and where does that
flag live?**

- Citation: `mal-commonlib/src/mal_commonlib/data/loaders/dynamic_world.py:500`,
  `mal-commonlib/src/mal_commonlib/data/loaders/era5.py:502`,
  `mal-core/src/mal_core/download/registry.py:44` (field),
  `mal-core/src/mal_core/download/runner.py:117` (propagation into the
  manifest), `mal-core/src/mal_core/download/catalog.py:292-328`
  (`catalog_status` surfaces it).
- Answer: only the Dynamic World fractions and the ERA5 outputs set it in
  the loaders; the flag is per output, propagated into the manifest entry
  and shown by `malariasim datasets`. It is *not* the gate the ABM actually
  uses (see Q39).

### Manifest: schema and authority

**11. Where does the manifest live, what are its top-level keys, and which
code writes it?**

- Citation: `mal-core/src/mal_core/download/manifest.py:16-27` (`DATA_ROOT`
  and repo-root discovery), `:30-36` (`read_manifest`, empty skeleton
  `{"aoi", "datasets", "expected_files"}`), `:116-186` (`update_dataset`,
  the only writer), `data/ghana/manifest.json:1` (a real manifest: keys
  `aoi`, `datasets`, `expected_files`).
- Answer: `data/<aoi>/manifest.json`, three top-level keys: `aoi`,
  `datasets`, `expected_files`. Only `update_dataset` writes it; the runner
  calls it after every successful save.

**12. What is the schema of a dataset entry, field by field?**

- Citation: `mal-core/src/mal_core/download/manifest.py:116-186`
  (`update_dataset`: `type`, `format`, `required_for_abm`, `files`,
  optional `variables`, `period`, `license`, `attribution`),
  `data/ghana/manifest.json` (a populated example, including `period` and
  `license`/`attribution`).
- Answer: `type` ∈ {"time-series", "static"}; `format` (e.g. `nc`, `tif`,
  `gpkg`); `required_for_abm` (bool); `files` — a map whose key is the year
  for per-year products and the dataset key itself for single-file
  products; optional `variables` (list), `period` (`{start, end}` for
  multi-year NetCDF), `license` (identifier from
  `mal_commonlib.data.licenses.KNOWN_LICENSES`), `attribution` (literal
  credit line).

**13. What is the manifest authoritative for, and what is it *not*
authoritative for?**

- Citation: `mal-core/src/mal_core/download/catalog.py:1-31` (module
  docstring), `mal-core/src/mal_core/download/manifest.py:39-114`
  (`resolve_dataset_file`, strict by default), `mal-core/src/mal_core/download/catalog.py:196-201`
  (comment: "NO fallback").
- Answer: it is authoritative for **which files exist for which AOI and
  under which key**, and for the completeness check. It is *not* the place
  where dataset identity is defined (that lives in each loader's
  `manifest_keys` and in `INGEST_ARTIFACTS`) nor a place where metadata may
  be silently re-derived.

**14. What are the on-disk naming conventions, and are they enforced
anywhere in code?**

- Citation: `mal-core/src/mal_core/download/runner.py:49-54`
  (`_standard_path`: `<aoi>_<product>_<year>.<ext>` and
  `<aoi>_<product>.<ext>`), `:56-60` (`_standard_path_daily`:
  `<aoi>_<product>_<start>_<end>_daily.nc`), `:62-66`
  (`_standard_path_monthly_nc`),
  `mal-core/src/mal_core/download/catalog.py:330-331` (the two regexes used
  by the migration path only).
- Answer: three patterns, produced by the runner's naming helpers. The file
  name uses the **output name**, not the manifest key (e.g. the Dynamic
  World fractions land in `ghana_class_fractions_2024_2024_daily.nc` under
  the manifest key `dw_class_fractions`). The naming regexes exist only in
  `register_existing`; the runner never validates a name against them.

**15. What is `expected_files`, and how is it maintained?**

- Citation: `mal-core/src/mal_core/download/manifest.py:172-180` (rebuilt as
  the sorted union of all `files` values on every write),
  `mal-core/src/mal_core/download/manifest.py:224-236` (also checked
  independently by `validate_completeness`).
- Answer: a flat, sorted list of every declared file name in the manifest;
  it is recomputed from scratch on every `update_dataset` call and is
  redundant with the per-dataset `files` maps.

**16. What does `validate_completeness` actually check, and what does it
miss?**

- Citation: `mal-core/src/mal_core/download/manifest.py:190-240`.
- Answer: for every dataset entry it checks that each declared file exists
  under `data/<aoi>/`; for entries carrying a `period` **and** a requested
  year list it additionally checks that the period covers each requested
  year. It then re-checks the `expected_files` union. It is a *declared
  files exist* check: it does **not** know which datasets a given consumer
  requires, so an AOI with a manifest missing `dw_class_fractions`
  entirely passes this check.

### The catalogue and the Slot system

**17. What is a `Slot`, and what is the rule for a consumer's dependency
declaration?**

- Citation: `mal-core/src/mal_core/download/catalog.py:98-109` (`Slot`
  dataclass), `:176-268` (`resolve_inputs`).
- Answer: a `Slot` is `(key, required, per_year)` where `key` is a manifest
  key. A consumer declares `{slot_name: Slot(...)}` and receives
  `{slot_name: Path | dict[year, Path] | None}`. `None` is the signal for
  "optional input absent"; the consumer's dataset knowledge is only the
  manifest key.

**18. What is `INGEST_ARTIFACTS`, and why is it a separate table from the
loader keys?**

- Citation: `mal-core/src/mal_core/download/catalog.py:44-95`
  (`IngestArtifact`, `INGEST_ARTIFACTS` with `env`, `habitat`,
  `host_static`, `host_manifest`, `mobility_day`, `mobility_night`,
  `livestock_mobility`, `mobility_manifest`), `:270-290`
  (`downloadable_datasets` derives the loader rows from the registry).
- Answer: derived products (built by ingest, not fetched) need keys that no
  loader declares, so their identity lives in this one table, with the
  producing function and the `required_for_abm` flag. Loader-derived keys
  are *not* duplicated in any table: they are read from the registry.

**19. What are the exact resolution semantics of `resolve` and
`resolve_inputs`, including the failure modes?**

- Citation: `mal-core/src/mal_core/download/catalog.py:155-173` (`resolve`),
  `:196-268` (`resolve_inputs` body),
  `mal-core/src/mal_core/download/manifest.py:85-107` (per-year miss raises,
  stale manifest raises).
- Answer: three outcomes — (i) no manifest entry → `None` for an optional
  slot, `FileNotFoundError` for a required one, with the message telling the
  user to run `malariasim download`; (ii) entry present but the file is
  missing on disk → `FileNotFoundError` (a stale manifest is an error, never
  a silent fallback); (iii) per-year entry lacking the requested year →
  `FileNotFoundError`, because silently substituting another year's file
  would be a data-integrity bug. `explicit` overrides always win and are
  validated to exist.

**20. Is there any conventional-filename fallback inside a consumer, and
what is the migration path for directories that predate the manifest?**

- Citation: `mal-core/src/mal_core/download/catalog.py:196-201` ("There is NO
  conventional-name fallback inside consumers"),
  `mal-core/src/mal_core/download/catalog.py:334-427` (`register_existing`,
  with `dry_run`).
- Answer: no fallback exists. Legacy directories are migrated **once** by
  `register_existing`, which derives the conventional names from the
  loaders' own `formats` plus the runner's naming rules, and registers what
  it finds (never overwriting an existing entry).

**21. What does `malariasim datasets` report, and what does it not tell
you?**

- Citation: `mal-core/src/mal_core/download/catalog.py:292-328`
  (`catalog_status`), `mal-core/src/mal_core/cli.py:809-841` (rendering,
  `--missing` filter).
- Answer: one row per known key (download rows from the registry, artifact
  rows from `INGEST_ARTIFACTS`), with `in_manifest`, `on_disk` and the
  declared path. It shows the *first* declared file of an entry only, so a
  multi-year entry is not fully described by one row.

### The runner: order of operations

**22. What is the exact order of operations for one dataset, and what are
the consequences of that order?**

- Citation: `mal-core/src/mal_core/download/runner.py:69-278`.
- Answer: (1) select loaders by name; (2) auth gate per loader — a missing
  credential skips the **whole loader**, not the output;
(3) per output: filter by `--outputs` and by the ABM profile; (4) branch on
`is_time_series` and on the output's format; (5) call the loader;
(6) if the loader returns `None`, skip silently; (7) write the file;
(8) register it in the manifest. Consequences: a loader that fails partway
  leaves earlier outputs registered and later ones absent; the manifest is
  updated **per output**, not per dataset, so a partially failed dataset is
  visible as such only through the manifest.

**23. How is the auth gate implemented for each credential type, and what
happens when a credential is absent?**

- Citation: `mal-core/src/mal_core/download/runner.py:20-46` (`_check_auth`),
  `:110-113` (skip and status `"skipped"` with reason `"auth missing"`).
- Answer: `cds` → the file `~/.cdsapirc` (or `$CDSAPI_RC`) must exist;
  `earthdata` → the environment variable `EARTHDATA_TOKEN` must be set;
  `earthengine` → `~/.config/earthengine/credentials` must exist;
  `"none"` → no check. A missing credential produces a warning and a
  `skipped` status, never an exception. The `cds` probe catches `OSError`
  as well as a missing file, so a sandboxed home directory reads as "no
  auth".

**24. What happens inside a loader when the credential is missing but the
loader is called directly (bypassing the runner)?**

- Citation: `mal-commonlib/src/mal_commonlib/data/loaders/dynamic_world.py:120-158`
  (`_ensure_ee` raising a `RuntimeError` with the one-line fix),
  `mal-commonlib/src/mal_commonlib/data/loaders/era5.py:196-215` (the CDS
  client and its message).
- Answer: the Earth Engine loader raises a `RuntimeError` naming the
  project and the `earthengine authenticate` command; it never triggers an
  interactive browser flow. The Earth Engine loader also installs a shim so
  that a probe of the Google Cloud application-default credentials file
  cannot abort initialisation when that path is unreadable.

**25. How does the runner decide the output format and the file name for
each write path?**

- Citation: `mal-core/src/mal_core/download/runner.py:125-138` (format
  selection, default `"monthly"`), `:139-180` (the `daily` path),
  `:181-219` (the `monthly_nc` path), `:220-262` (the per-year/monthly
  path), `:263-282` (the static path).
- Answer: the output's declared `formats` value selects the path:
  `"daily"` → one multi-year NetCDF covering the whole requested year span,
  with a `period` recorded from the first and last timestamps; `"monthly_nc"`
  → one multi-year NetCDF with monthly steps (SMAP salinity); anything else
  → per-year GeoTIFF; static outputs → GeoTIFF or NetCDF depending on
  whether the loader returned a `Dataset`.

**26. What reduction is applied when a monthly product is collapsed to a
year, and is that reduction configurable in practice?**

- Citation: `mal-core/src/mal_core/download/runner.py:203-212` (`reduction`
  from `spec.reductions`, default `"mean"`; `"sum"` and `"first"` are the
  alternatives), `mal-core/src/mal_core/download/registry.py:96`
  (`reductions` read from the loader), repository search: **no loader
  currently declares a `reductions` dict**.
- Answer: the mean over the time dimension is the effective rule for every
  product; the `"sum"`/`"first"` branches are unreachable with the current
  loader set. → part (c).

**27. How is the NetCDF variable name chosen, and why does that matter to
the consumer?**

- Citation: `mal-core/src/mal_core/download/runner.py:143-149` (the DataArray
  name wins; otherwise the output name with the `_daily` suffix stripped),
  `mal-core/src/mal_core/download/writer.py:45-53` (`to_dataset(name=…)`),
  `mal-core/src/mal_core/download/runner.py:186` (the `monthly_nc` path
  strips `_salinity`).
- Answer: the NetCDF variable name is a contract with the ingest stage
  (e.g. `rainfall`, `air_temp_c`); the runner derives it from the loader's
  own DataArray name when it has one.

**28. What does the writer do, and what does it refuse to do?**

- Citation: `mal-core/src/mal_core/download/writer.py:12-53`.
- Answer: `save_product` infers `nc` for a `Dataset` and `tif` otherwise,
  writes GeoTIFF via the `rio` accessor and NetCDF via `xarray`, and raises
  `ValueError` for a 3-D `DataArray` sent to the TIF writer. It is the
  single save point: loaders return data in memory and never write files.

**29. What happens to a dataset whose loader raises, and what does the
runner return overall?**

- Citation: `mal-core/src/mal_core/download/runner.py:265-278`.
- Answer: the exception is caught per loader, logged, and reported as
  `{"status": "error", "error": str(e)}`; the run continues with the next
  loader and the CLI prints one status line per dataset. The summary is
  therefore a per-dataset status map, not a pass/fail for the AOI.

### AOI reduction: where the aggregation actually happens

**30. Where is the "areal fraction before reduction" rule implemented, and
is it a rule or a per-loader accident?**

- Citation: `mal-commonlib/src/mal_commonlib/data/loaders/dynamic_world.py:273-334`
  (per-class fraction planes, `Resampling.average` of a binary class layer
  onto the AOI grid, divided by the valid-pixel count),
  `mal-commonlib/src/mal_commonlib/data/loaders/jrc_gsw.py:200-240` and
  `:300-335` (threshold then average resampling).
- Answer: it is **per loader, not a framework guarantee**: each loader
  reduces the native product to the AOI grid itself and the runner never
  resamples. The Dynamic World loader implements the stated rule
  explicitly (class label → binary layer → areal fraction on the AOI grid,
  with the `nodata_sentinel` where no valid pixel exists); the JRC loader
  thresholds occurrence at a fixed percentage and then averages.

**31. What exactly is the Dynamic World reduction, and what is lost in it?**

- Citation: `mal-commonlib/src/mal_commonlib/data/loaders/dynamic_world.py:56-60`
  (the 100 m request scale and its rationale), `:209-263` (per-year modal
  label from the Earth Engine image collection), `:273-334` (fraction
  planes), `:92-99` (`FEATURE_CLASSES` mapping),
  `mal-core/config/model_constants.yaml:137-138` (NoData sentinels),
  `:158` (`valid_count_epsilon`).
- Answer: for each run year the modal label over the year's Sentinel-2
  passes is requested at 100 m; the label raster is then reduced to the
  AOI grid as an **areal fraction per feature column**
  (`lc_built`, `lc_wetland`, `lc_crop`, `lc_open_plus_water`). What is lost:
  the sub-100 m composition of each cell, the identity of the minority
  class, and the distinction between a class that is dominant because it is
  persistent and one that won a close annual vote.

**32. What is the target grid the reduction aims at, and who defines it?**

- Citation: `mal-commonlib/src/mal_commonlib/aois.yaml:15-24` (Ghana: bbox,
  `EPSG:4326`, `resolution_m: 1000`), `mal-commonlib/src/mal_commonlib/aoi.py:195-199`
  (`cells_per_side`), `mal-core/src/mal_core/download/runner.py:100-102`
  (the AOI object is built from the slug and passed to every loader).
- Answer: the AOI grid, defined in the AOI registry: bounding box, CRS and
  ground resolution in metres; the cell count is derived by rounding the
  bbox extent up to whole cells.

**33. Which resampling does each product use, and what are the consequences
for categorical products?**

- Citation: `mal-commonlib/src/mal_commonlib/data/loaders/chirps.py:230-241`
  (nearest, with an explicit comment on why), `:296-330` (daily reprojection
  to the AOI grid),
  `mal-commonlib/src/mal_commonlib/data/loaders/era5.py:148` (bilinear
  `reproject_match`),
  `mal-commonlib/src/mal_commonlib/data/loaders/ghsl.py:199-210`
  (nearest, "categorical data MUST be nearest-neighbor"),
  `mal-commonlib/src/mal_commonlib/data/loaders/worldpop.py:141-200`
  (sum-preserving aggregation of population counts).
- Answer: continuous fields are resampled bilinearly (ERA5) or by nearest
  (CHIRPS, with the reason documented in the loader), categorical settlement
  classes by nearest, and population by a sum-preserving rectangle sum so
  that the per-cell value remains a **count of people**, not a density.
  The building fraction is not an area fraction at all: it is 1.0 in any cell
  containing at least one footprint centroid
  (`mal-commonlib/src/mal_commonlib/data/loaders/buildings.py:18-25`).

**34. Which values are the products' native resolutions, and which of them
are stated in code rather than in a docstring?**

- Citation: `mal-commonlib/src/mal_commonlib/data/loaders/chirps.py:6`
  (0.05°, one file per day), `mal-commonlib/src/mal_commonlib/data/loaders/jrc_gsw.py:34-70`
  (JRC occurrence, threshold semantics),
  `mal-commonlib/src/mal_commonlib/data/loaders/ghsl.py:15-25` (Mollweide
  ~1 km, 2030 epoch), `mal-commonlib/src/mal_commonlib/data/loaders/glw.py:252-258`
  (GLW4, 5 arc-min), `mal-commonlib/src/mal_commonlib/data/loaders/smap.py:12-24`
  (SMAP 0.25°), `mal-commonlib/src/mal_commonlib/data/loaders/era5.py:51-56`
  (ERA5-Land daily statistics, CDS padding of half a degree).
- Answer: as stated per loader above. The document must generate any number
  it quotes from `model_constants.yaml` and treat loader docstrings as
  evidence, not as generated values.

### Caches, state and restart

**35. What is cached where, and what is the difference between the cache
and the data directory?**

- Citation: `mal-commonlib/src/mal_commonlib/data/loaders/era5.py:69-72`,
  `chirps.py` (`_default_cache_dir`), `worldpop.py:105-107`,
  `glw.py:97-99`, `buildings.py:52-54`, `dynamic_world.py:170-176`
  (all under `~/.cache/mal_commonlib/<dataset>`), and
  `mal-core/src/mal_core/download/runner.py:100-101` (`cache_dir` argument,
  defaulting to each loader's own location).
- Answer: the network-fetched artefacts (per-month NetCDFs, per-day
  GeoTIFFs, Dynamic World tiles, rasterised `.npz` results) live in a
  per-dataset cache under the user's cache directory; the reduced AOI-grid
  products live in `data/<aoi>/` and are registered in the manifest. The
  cache is a pure cache: deleting it changes nothing about the manifest, and
  a run that is interrupted can be resumed with the cache intact (the
  manifest is what makes the *output* state restart-safe).

**36. What would the stage need on disk to restart identically after an
interruption?**

- Citation: `mal-core/src/mal_core/download/manifest.py:116-186` (the
  manifest is rewritten after each output), `:172-180` (`expected_files`
  rebuilt on every write), `mal-core/src/mal_core/download/runner.py:213-262`
  (each output is registered as it is written).
- Answer: the manifest plus the files it names. Because the manifest is
  updated after every single output, an interrupted run leaves a consistent
  (if incomplete) manifest; re-running the same command re-downloads the
  missing outputs. The runner does **not** skip outputs that are already
  registered — it always re-fetches.

### Licensing and attribution

**37. How are licence and attribution recorded, and what is the aggregated
warning?**

- Citation: `mal-core/src/mal_core/download/registry.py:100-101` (fields
  from the loader), `mal-core/src/mal_core/download/runner.py:145-166`
  (passed to `update_dataset`),
  `mal-core/src/mal_core/download/manifest.py:166-172` (stored on the
  entry; `None` leaves an existing value untouched),
  `mal-core/src/mal_core/download/runner.py:272-274` (`warn_manifest_limits`,
  wrapped so a warning never breaks a download),
  `mal-commonlib/src/mal_commonlib/data/licenses.py:25-146`
  (`KNOWN_LICENSES`, `collect_limits`, `warn_limits`, `warn_manifest_limits`).
- Answer: each loader declares a licence identifier and a literal
  attribution line; both are copied into the manifest entry; at the end of
  a run the licences of all entries are aggregated and any usage limits are
  warned about. The warning is advisory and never fails the run.

### Downstream consumption

**38. Which manifest keys does the ingest stage require, and how are they
resolved?**

- Citation: `mal-core/src/mal_core/ingest/daily_nc.py:84-97`
  (`ENV_INPUT_SLOTS`: `chirps_rainfall_daily`, `era5_air_temp_daily`,
  `jrc_habitat_features`, `dw_class_fractions` required;
  `coastline_land_mask`, `host_static`, `smap_salinity` optional),
  `:113-122` and `:187-190` (`resolve_inputs` calls),
  `mal-core/src/mal_core/ingest/daily_nc.py:126-148` (`read_static_tif`
  resamples a static GeoTIFF to the target shape bilinearly).
- Answer: the ingest stage declares *only manifest keys*; four are required
  (absence is a hard error) and three are optional (absence disables the
  corresponding behaviour). The static rasters are re-read at the target
  shape at ingest time, so the download-stage grid is a convention rather
  than an enforced contract for those products.

**39. What does the ABM require, and what does it actually check?**

- Citation: `mal-core/src/mal_core/abm/wrapper.py:112-121`
  (`validate_completeness`, then the error message),
  `:141-165` (resolution of `env`, `habitat`, `host_static`, `wind`,
  `mobility_day`, `mobility_night`, `livestock_mobility`),
  `:167-178` (hard error only when `env` or `habitat` is missing),
  `:212-222` (the optional flags).
- Answer: the ABM first requires that every file *declared* in the manifest
  exists, then resolves seven paths. Only `env` and `habitat` are
  mandatory; hosts and the three mobility artefacts are passed to the binary
  only when present. The `wind` key is resolved specially (see Q40).

**40. Why is `wind` resolved under a different manifest key from the other
ERA5 outputs?**

- Citation: `mal-core/src/mal_core/abm/wrapper.py:149-152` (the comment
  "era5 manifest key (\"wind\" = wind_6hourly output)"),
  `mal-commonlib/src/mal_commonlib/data/loaders/era5.py:498-500`
  (the `manifest_keys` of the ERA5 loader).
- Answer: the wind output's manifest key is `wind`, not a
  `era5_`-prefixed name. It is the one place where a consumer hard-codes a
  key rather than referring to the loader's declaration.

**41. Which products does the stage itself consume, and how?**

- Citation: `mal-commonlib/src/mal_commonlib/data/loaders/wildlife.py:14-22`
  (Dynamic World label mode + JRC GSW occurrence + Overture buildings),
  `:168-186` (`load_wildlife_host_proxy`), `:30-40` (neutral defaults of 0.5
  and 1.0 when a component fails to load).
- Answer: the wildlife proxy is a *derived* product computed inside the
  download stage from three other layers, with per-class suitability weights
  read from `model_constants.yaml` (`wildlife` section) and a documented
  failure mode in which a missing component silently becomes a neutral
  constant. This is the only loader that consumes other download outputs.

**42. What is the ordering constraint between the download stage and the
rest of the pipeline?**

- Citation: `mal-core/src/mal_core/cli.py:32` (the pipeline order
  "download → ingest → abm → score → train → predict"),
  `mal-core/src/mal_core/cli.py:665-693` (the automatic download+ingest step
  in the `abm` command), `mal-core/src/mal_core/abm/wrapper.py:116-121`.
- Answer: the env tensor and the habitat GeoPackage must exist before the
  ABM can start; they are *ingest* products registered in the same manifest
  under the keys `env` and `habitat`. The download stage therefore produces
  raw layers, and the same manifest later carries the derived artefacts.

### Numbers and constants

**43. Which constants of the download stage must be generated from
`model_constants.yaml` rather than typed into the document?**

- Citation: `mal-core/config/model_constants.yaml:137-138`
  (`ingest.nodata_sentinel`, `ingest.nodata_sentinel_int`),
  `:158` (`ingest.valid_count_epsilon`), `:162` (`wildlife` block),
  `mal-commonlib/src/mal_commonlib/data/loaders/dynamic_world.py:107-110`
  (the sentinels read through the read-only accessor),
  `mal-commonlib/src/mal_commonlib/data/loaders/jrc_gsw.py:78`,
  `mal-commonlib/src/mal_commonlib/data/loaders/chirps.py:46`,
  `mal-commonlib/src/mal_commonlib/data/loaders/buildings.py:49`.
- Answer: the NoData sentinels, the valid-count epsilon and the wildlife
  suitability table and weights are the values that live in the constants
  file; the loader's own constants (the JRC threshold percentage, the
  Dynamic World request scale, the ERA5 padding) are module-level constants
  and are *not* in the constants file — the document must say which is
  which, and must not type a hand-copied number for either.

**44. What does the stage *not* do — the declaration of absences?**

- Citation: `mal-core/src/mal_core/download/runner.py:139-141` and `:126-127`
  (a loader returning `None` writes nothing),
  `mal-core/src/mal_core/download/registry.py:63-91` (the profile table),
  `mal-core/src/mal_core/download/runner.py:119-121` (the profile filter),
  `mal-commonlib/src/mal_commonlib/data/loaders/_legacy/` (retired loaders).
- Answer: the stage does not transform data into model inputs (ingest
  does), does not resample to a common grid for the consumer, does not
  validate the *scientific* content of a layer, does not skip already
  downloaded outputs, has no retry/back-off policy at the runner level, and
  has no load-or-download fast path.

---

## (b) Done-checklist

The download document is done when a reviewer who has never opened the code
can check each of the following against the cited file:

1. **Every loader is named** with its provider, its authentication
   requirement, the credential artefact that must exist, and the manifest key
   it produces (12 loaders; `_legacy/` excluded).
2. **The registry mechanism is explained**: the package scan, the
   `DOWNLOADER` dict fields, the registry's profile table, and the fact that
   a loader module is registered merely by existing.
3. **The manifest schema is described field by field** (`aoi`, `datasets`,
   `expected_files`; per entry `type`, `format`, `required_for_abm`, `files`,
   `variables`, `period`, `license`, `attribution`), with an example entry
   taken from a real manifest.
4. **The manifest's authority is stated precisely**: authoritative for
   existence and completeness; not authoritative for dataset identity
   (which lives in `manifest_keys` and `INGEST_ARTIFACTS`).
5. **The Slot/`resolve`/`resolve_inputs` contract is stated**, including the
   three failure modes (no entry, stale entry, missing year) and the
   explicit-override rule; the absence of any conventional-name fallback is
   stated.
6. **The three on-disk naming patterns are stated**, and the fact that the
   file name uses the output name rather than the manifest key is stated.
7. **The order of operations is given as pseudocode plus a table**, and the
   consequences of that order are stated (per-output registration, partial
   failure, whole-loader auth skip).
8. **The auth gate is described per credential type**, and the behaviour on
   a missing credential (skip, not error) and inside a directly-called
   loader (raise with a fix message) are distinguished.
9. **The AOI reduction seam is stated**: the target grid comes from the AOI
   registry, the reduction happens inside the loaders (not in the runner),
   the areal-fraction rule is stated for the Dynamic World and JRC layers
   with the resampling used, and the categorical-versus-continuous and
   count-preserving cases are distinguished (GHSL nearest, WorldPop
   sum-preserving, buildings centroid-based).
10. **What the aggregation loses is stated** for at least the land-cover
    planes and the population layer.
11. **The cache/state distinction is stated**: what lives under the cache
    directory, what lives in `data/<aoi>/`, what the manifest guarantees for
    an interrupted run.
12. **Completeness validation is described exactly**, including what it does
    *not* check (it does not know which datasets a consumer needs).
13. **The consumption contract is stated**: which manifest keys the ingest
    stage requires and which are optional, which paths the ABM resolves, and
    that the `wind` key is special.
14. **Every dataset is listed with its provider and credential requirement**,
    and every loader is named in prose at least once.
15. **The licence/attribution handling is stated**, including that the
    aggregated warning never fails a run.
16. **No number appears in the prose that is not generated** from
    `model_constants.yaml` or `docs/concepts/contracts.yaml`; loader-local
    constants are either cited as module constants or moved to the
    constants file, and the choice is stated.
17. **Every claim carries a file-and-line citation**, and no citation
    points at a retired specification as authority.
18. **The declaration of absences is present** (Q44) and the document does
    not claim a load-or-download API, a `--all` flag, or a reduction
    configuration that the code does not have.

---

## (c) Open questions

1. **The "load-or-download" API does not exist.** `AGENTS.md` describes
   public `load_<dataset>_<product>` functions that check the manifest and
   download only when missing; the code has no such path. Either the
   convention is aspirational and should be retired, or it should be
   implemented. Until then the document must describe what exists.
2. **`--all` is advertised but not defined.** Both the `download` docstring
   (`cli.py:171-173`) and the ABM's remediation message
   (`wrapper.py:118-121`) tell the user to run a command that the CLI will
   reject. The document should describe the real invocation ("omit
   `--datasets` and `--outputs`"), and the two messages should be fixed.
3. **The ABM profile is not fully described by its table.** `modis` is
   absent from `registry.py:63-91` and declares no `abm_default_outputs` of
   its own, so `abm_default_outputs is None` and the runner's filter does
   not exclude it — a default download run fetches MODIS NDVI even though
   the retired spec called it "not an ABM default". Is that intended?
4. **The `reductions` mechanism is dead code.** No loader declares a
   `reductions` dict, so the `"sum"`/`"first"` branches of
   `runner.py:203-212` are unreachable and the year-aggregation rule for
   monthly products is hard-wired to the mean. Should the mechanism be
   removed, or should a loader start using it?
5. **`required_for_abm` is declared but not enforced as a gate.** It is
   set only by the Dynamic World and ERA5 loaders, is copied into the
   manifest, and is displayed by `malariasim datasets`, but the ABM gate is
   `validate_completeness` plus the presence of `env`/`habitat`. It is
   unclear whether `required_for_abm` should drive the gate.
6. **`catalog_status` reports only the first declared file of a multi-year
   entry**, so a per-year product is not fully described by its row in
   `malariasim datasets`; the `--missing` filter therefore hides partially
   complete entries.
7. **`register_existing` embeds a second copy of the artifact naming
   rules** (`catalog.py:392-402`: the ingest-artifact patterns) that are not
   derived from the producers themselves — the loaders' names are derived,
   the ingest artefacts' are hard-coded. Which is authoritative when the
   ingest builder changes a file name?
8. **The CHIRPS loader resamples rainfall with nearest-neighbour** onto the
   AOI grid (`chirps.py:230-241`), while ERA5 uses bilinear. Whether this
   asymmetry is a measured decision or a leftover is not documented in the
   code beyond a comment about the regridding helper.
9. **The ERA5 request area is padded by half a degree**
   (`era5.py:56`, `:161-175`) with the rationale given only in a comment
   about coverage; the document cannot state the consequence for the AOI
   boundary cells without more evidence.
10. **`era5_wind_6hourly` is declared `formats: "daily"`** (`era5.py:490-493`),
    which routes it through the runner's multi-year daily NetCDF path even
    though the underlying product is 6-hourly; the effective temporal
    resolution of the stored file is therefore a question for the code
    (the loader returns a 6-hourly `Dataset` and the runner writes it
    as-is under a `_daily` file name).
