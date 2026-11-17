# Spec retirement ledger — the nine `docs/specs/*/spec.md` documents

**Status**: in-process (the audit trail of the spec retirement).
**Scope**: the nine per-domain specifications under `docs/specs/` — `abm`,
`data`, `download`, `ingest`, `scoring`, `training`, `prediction`,
`commonlib` and the shared `_template.md` — retired in favour of the
per-stage conceptual documents under `docs/concepts/`.

## How to read this ledger

Every assertion of every retired specification has exactly one row. The
columns are:

| Column | Meaning |
|---|---|
| `spec:line` | Where the assertion lived in the retired document. |
| The claim | The assertion, in the words of the specification. |
| Class | What happened to it. |
| Where it lives now | The code, test or document that now carries the fact. |
| Reason | **Only for `DROP`** — why the claim was dropped rather than migrated. |

### The four classes

- **ENFORCED** — a mechanical check already exists and enforces the
  assertion today (a pytest, a C++ test, or the concepts generator).
  Nothing new was written; the row records *where* the enforcement lives.
- **MIGRATE→test** — the assertion is a runnable fact about the code. It
  was rewritten as a test in one of the new files
  `mal-core/tests/test_spec_retirement_*.py` and
  `mal-commonlib/tests/test_spec_retirement_commonlib.py`.
- **MIGRATE→signal** — the assertion is about the *shape* of the code
  (a signature, a constant, a call order) rather than a runtime
  behaviour. It is pinned by a source-level assertion in the same new
  test files. A signal is weaker than a behavioural test and is labelled
  as such on purpose.
- **DROP** — the assertion is false, obsolete, unimplemented, or is a
  process rule rather than a runtime fact. The reason says which.

### What is *not* here

The specifications also carried prose (rationale, migration policy,
examples). Prose is not an assertion and is not rowed. The behavioural
content of the specifications lives on in the conceptual documents under
`docs/concepts/<stage>/`, which were written from the code.

### The migrated tests

| File | Covers |
|---|---|
| `mal-core/tests/test_spec_retirement_abm.py` | the ABM output contract |
| `mal-core/tests/test_spec_retirement_data.py` | the manifest and file-naming contract |
| `mal-core/tests/test_spec_retirement_download.py` | the loader/DOWNLOADER contract and the runner |
| `mal-core/tests/test_spec_retirement_ingest.py` | the env NC, the habitat gpkg, the host and mobility artefacts |
| `mal-core/tests/test_spec_retirement_scoring.py` | the scorer registry, the composite arithmetic, the LLM judge, the feedback report |
| `mal-core/tests/test_spec_retirement_training.py` | the U-Net, the dataset, the trainer and the wrapper |
| `mal-core/tests/test_spec_retirement_prediction.py` | the model registry, the aggregators and the emitted risk raster |
| `mal-commonlib/tests/test_spec_retirement_commonlib.py` | the AOI, the host NC, the CSR layout, the retired terrain layer |

---

## `abm/spec.md`

| spec:line | The claim | Class | Where it lives now | Reason |
|---|---|---|---|---|
| 88 | The state output has shape `(C=2, T, H, W)` and dtype float32. | ENFORCED | `mal-core/src/mal_core/abm/tests/test_state_cog.cpp` (2 bands, float32, exact round-trip); `mal-core/tests/test_spec_retirement_abm.py::test_the_state_cog_has_exactly_two_bands_and_the_pinned_names` | |
| 88 | Channel 0 is `density`, channel 1 is `suitability`. | DROP | The bands were renamed by state contract 4.0: `adult_patch_count`, `adult_cell_count` (`mal-core/src/mal_core/abm/include/mal_abm_fast/wire.hpp:159`). | The claim names bands that no longer exist; renaming it would have re-introduced the retired vocabulary. |
| 89 | The state contract is v4.0; both bands are raw per-cell adult counts; the `density / K_max` normalisation is retired. | ENFORCED | `mal-core/tests/test_config_loader.py:87`; `docs/concepts/contracts.yaml` (`state_cog`, `version_from: contracts.cogs_state`) cross-checked by `tools/gen_concepts_values.py:410-421`; `mal-core/tests/test_spec_retirement_abm.py::test_the_contract_version_is_4_0` | |
| 89 | The sidecar `k_max` key was removed. | MIGRATE→test | `mal-core/tests/test_spec_retirement_abm.py::test_the_retired_k_max_key_is_gone_from_the_sidecar` | |
| 90 | `suitability` semantics per version (v1 binary map, v2 density, v2.1 per-adult density, v4.0 raw counts). | DROP | The current semantics are the two band names in `wire.hpp:159` and the `state_cog` entry of `docs/concepts/contracts.yaml`. | Version history of a renamed band is not a runtime fact; keeping it would preserve the retired vocabulary. |
| 90 | Readers read the state bands by band name, not by index. | DROP | The trainer reads the bands positionally (`mal-core/src/mal_core/training/dataset.py:178-186`). | The claim describes a reader that does not exist; the band *names* remain contractual through `contracts.yaml`. |
| 91 | The NoData sentinel is `-9999.0`; any other sentinel is a P0 bug. | ENFORCED | `docs/concepts/contracts.yaml` (`sentinel: -9999.0` for every artefact) cross-checked by `tools/gen_concepts_values.py`; `mal-core/tests/test_spec_retirement_abm.py::test_the_state_nodata_sentinel_is_minus_9999` | |
| 91 | The state raster carries a mask band with the value `255`. | DROP | The state COG has two bands and no mask (`mal-core/src/mal_core/abm/src/output_contract.cpp:98-240`); `255` survives only as the RGBA alpha of the visualisation images (`mal-core/src/mal_core/abm/src/viz_common.cpp`). | The mask band does not exist in any artefact. |
| 92 | The state file is named `{aoi_slug}_{scale}_{year}_{month:02d}_seed{seed:04d}.tif`. | DROP | The engine writes `{aoi}_abm_seed{seed:04d}.tif` (`mal-core/src/mal_core/abm/wrapper.py:180`) and the per-day snapshots `{stem}_day{NNN}.tif` (`mal-core/src/mal_core/abm/src/main.cpp:173-183`); pinned by `mal-core/tests/test_spec_retirement_abm.py::test_the_state_file_naming_follows_the_engine_convention`. | The naming in the specification has never been the one the engine writes. |
| 92 | The tiled state files carry a `_r{row:04d}_c{col:04d}` suffix. | DROP | The engine does not tile (`mal-core/src/mal_core/abm/src/main.cpp:168-215`). | No tiled artefact exists. |
| 96 | The env input is a CF-1.8 daily NetCDF, the only accepted format; dims `(time, y, x)`; daily `rainfall`, `air_temp_c` and the 2-D statics `jrc_persistent, lc_built, lc_wetland, lc_open_plus_water, lc_crop`. | ENFORCED | `docs/concepts/contracts.yaml` (the `env` artefact, `version_from: contracts.env_nc`) cross-checked by `tools/gen_concepts_values.py`; the variables themselves are pinned by `mal-core/tests/test_spec_retirement_ingest.py::test_env_nc_carries_the_pinned_variable_set` | |
| 96 | A non-`.nc` env path raises a hard error. | MIGRATE→signal | `mal-core/tests/test_spec_retirement_abm.py::test_the_env_nc_is_the_only_accepted_env_format` | |
| 96 | The env NetCDF `_FillValue` is `-9999.0`. | DROP | The env NC uses the xarray NaN default for float32 (`mal-core/src/mal_core/ingest/daily_nc.py:171-176` in the retired spec's own wording; `daily_nc.py:434-461` in the code). | The env NC carries no explicit `_FillValue`; the NoData rule for it is the NaN default. |
| 97 | The env file is named `{aoi}_{product}_{year_start}_{year_end}_env.nc` or `{aoi}_{scale}_{year}_{month:02d}_env.nc`. | MIGRATE→test | `mal-core/tests/test_spec_retirement_ingest.py::test_env_nc_filename_follows_the_regional_multi_year_convention` (the builder writes the `_regional_<start>_<end>_env.nc` form; the single-month form no longer exists) | |
| 101 | Every state `.tif` ships a same-basename `.json` sidecar with the keys `crs, transform, aoi_slug, scale, year, month, seed, generator_version, abm_params_hash`. | MIGRATE→test | `mal-core/tests/test_spec_retirement_abm.py::test_the_sidecar_carries_every_required_key` and `::test_the_sidecar_key_order_is_frozen` | |
| 102 | `contract_version` is an optional sidecar key, `"4.0"` since v4. | MIGRATE→test | `mal-core/tests/test_spec_retirement_abm.py::test_the_sidecar_carries_every_required_key` | |
| 103 | The sidecar `transform` is the affine 6-tuple `[a, b, c, d, e, f]`. | ENFORCED | `mal-core/src/mal_core/abm/tests/test_state_cog.cpp:245-248` | |
| 107 | The CRS is `EPSG:4326` or a UTM zone, and the writer must auto-reproject. | DROP | The grid is always lon/lat degrees (`mal-core/src/mal_core/abm/include/mal_abm_fast/aoi.hpp:9`); the writer writes the CRS it is given and fails loudly when it cannot be parsed (`mal-core/src/mal_core/abm/src/output_contract.cpp:174-190`). | There is no auto-reprojection in the writer; a silent mis-CRS is impossible because an unparseable CRS raises, but the claim as written is false. |
| 108 | The state COG band descriptions are `["adult_patch_count", "adult_cell_count"]`. | ENFORCED | `docs/concepts/contracts.yaml` (`state_cog.bands`) cross-checked against `wire.hpp:159` by `tools/gen_concepts_values.py`; `mal-core/tests/test_spec_retirement_abm.py::test_the_state_cog_has_exactly_two_bands_and_the_pinned_names` and `::test_the_cpp_state_cog_test_pins_the_band_descriptions_and_the_transform` | |
| 108 | The legacy band aliases are `["density", "suitability"]`. | DROP | The aliases were removed with contract 4.0 (`wire.hpp:159`). | The aliases no longer exist; keeping them would re-introduce retired vocabulary. |
| 112 | The U-Net input patch is `H = W = 128`; a smaller AOI is zero-padded, a larger one is tiled. | DROP | 128 is the *training* patch size (`mal-core/src/mal_core/training/dataset.py:19`); the ABM grid comes from `AOI.cells_per_side()` (`mal-commonlib/src/mal_commonlib/aoi.py`). | The ABM does not emit 128×128 patches and does not tile. |
| 113 | The tile suffix matches a shared `tile_index.json` in the run directory. | DROP | No tiling and no `tile_index.json` exist (`mal-core/src/mal_core/abm/src/main.cpp:168-215`). | The artefact does not exist. |
| 117 | The contract is pinned at v4.0; a change of shape, dtype, channel order, naming, NoData, units or `H/W` is MAJOR, an additive change is MINOR. | ENFORCED | `mal-core/tests/test_config_loader.py:87` (`CONFIG["contracts"]["cogs_state"] == "4.0"`); the versioning policy is in `mal-core/config/model_constants.yaml` | The MAJOR/MINOR policy is a process rule, but the pinned version it protects is mechanically enforced. |
| 117 | The version history v1.0 → v1.1 → v2.0 → v3.0 → v4.0. | DROP | The current version and its artefact set live in `mal-core/config/model_constants.yaml` (`contracts:`) and `docs/concepts/contracts.yaml`. | History of a retired contract; the code carries only the current one. |
| 118 | Readers must refuse a sidecar whose `contract_version` major is newer than the supported one. | DROP | No such symbol or check exists in the tree (the readers are `mal-core/src/mal_core/training/dataset.py`, `mal-core/src/mal_core/prediction/state_loader.py`; neither inspects `contract_version`). | The claim describes an unimplemented guard; dropping it records the gap rather than pretending it is enforced. |
| 125 (drift check) | The state `contract_version` starts with `"2."`. | DROP | The contract is `"4.0"` (`mal-core/config/model_constants.yaml`, `contracts.cogs_state`). | The check itself was wrong. |
| 131 (drift check) | There are 13 composite dimensions and 6 gates, and every composite dimension has a weight. | MIGRATE→test | `mal-core/tests/test_spec_retirement_scoring.py::test_registry_has_exactly_the_13_composite_dims_and_6_gates` and `::test_composite_weights_are_exactly_the_pinned_table` | |

---

## `data/spec.md`

| spec:line | The claim | Class | Where it lives now | Reason |
|---|---|---|---|---|
| 93 | A time-series file is `data/<aoi>/<aoi>_<product>_<year>.<ext>`, one per year. | MIGRATE→test | `mal-core/tests/test_spec_retirement_data.py::test_time_series_and_static_names_follow_the_convention` and `::test_standard_paths_match_the_documented_naming_regex` | |
| 94 | A static file is `data/<aoi>/<aoi>_<product>.<ext>`, one per AOI. | MIGRATE→test | `mal-core/tests/test_spec_retirement_data.py::test_time_series_and_static_names_follow_the_convention` | |
| 95 | `<aoi>` matches `[a-z0-9]+(-[a-z0-9]+)*`. | MIGRATE→test | `mal-core/tests/test_spec_retirement_data.py::test_slug_pattern_matches_the_conventional_aoi_names`; the validator itself is `mal-commonlib/src/mal_commonlib/aoi.py` | |
| 96 | The manifest lives at `data/<aoi>/manifest.json`. | MIGRATE→test | `mal-core/tests/test_spec_retirement_data.py::test_manifest_lives_at_data_aoi_manifest_json` | |
| 100 | The manifest's top-level keys are `aoi` (required), `name`, `grid`, `datasets` (required), `expected_files` (required). | MIGRATE→test | `mal-core/tests/test_spec_retirement_data.py::test_manifest_has_the_required_top_level_keys` | |
| 101 | A dataset entry carries `type` ∈ {time-series, static}, `format` ∈ {nc, gpkg, csr, json, tif}, a `files` map, `required_for_abm` (default false), optional `variables` and `period`. | MIGRATE→test | `mal-core/tests/test_spec_retirement_data.py::test_dataset_entry_schema`; the writer is `mal-core/src/mal_core/download/manifest.py:118-189` | |
| 102 | `expected_files` is the sorted union of all `files` values; `validate_completeness` checks each against `data/<aoi>/`. | MIGRATE→test | `mal-core/tests/test_spec_retirement_data.py::test_expected_files_is_the_sorted_union_of_the_declared_files` and `::test_validate_completeness_reports_the_missing_files` | |
| 103 | There is a single on-disk schema (v3.1); writes always produce v3.1; the legacy v1 flat-`files` migration was removed. | MIGRATE→test | `mal-core/tests/test_spec_retirement_data.py::test_a_flat_v1_manifest_is_not_migrated_and_resolves_to_nothing`; `mal-core/src/mal_core/download/manifest.py:1-6` | |
| 103 | A flat v1 manifest **fails loudly** on read. | DROP | `read_manifest` returns the file as parsed (`mal-core/src/mal_core/download/manifest.py:30-36`); a flat manifest simply has no `datasets` block, and the resolution layer treats the dataset as absent. | Nothing raises on a flat manifest; the loud failure is downstream (the dataset resolves to `None`), which is what the migrated test pins. |
| 104 | A dataset missing from the manifest is not available to consumers. | MIGRATE→test | `mal-core/tests/test_spec_retirement_data.py::test_a_missing_manifest_entry_means_not_available`; also `mal-core/tests/test_manifest.py::TestResolveDatasetFile::test_no_entry_returns_none` | |
| 108 | The env NetCDF carries `rainfall`, `air_temp_c` and the five static planes under contract `"3.0"`. | ENFORCED | `docs/concepts/contracts.yaml` (the `env` artefact) cross-checked by `tools/gen_concepts_values.py`; `mal-core/tests/test_spec_retirement_ingest.py::test_env_nc_carries_the_pinned_variable_set` | |
| 108 | The env NetCDF `contract_version` is `"2.0"`. | DROP | The env contract is `"3.0"` (`mal-core/src/mal_core/ingest/daily_nc.py:438`, `mal-core/config/model_constants.yaml` `contracts.env_nc`). | The value in the specification was two versions behind. |
| 112 | The env NetCDF `_FillValue` is `-9999.0`. | DROP | The env NC carries the xarray NaN default for float32 (`mal-core/src/mal_core/ingest/daily_nc.py:434-461`); the `-9999.0` sentinel belongs to the raster artefacts (`ingest.nodata_sentinel`). | The claim does not describe the file that exists. |
| 116 | Every loader returns `xr.DataArray` or `xr.Dataset` in memory and takes no `output_path`. | MIGRATE→test | `mal-core/tests/test_spec_retirement_data.py::test_loaders_return_in_memory_objects_and_take_no_output_path` and `::test_load_or_download_api_exists_on_the_public_loaders` | |
| 117 | The canonical loader signature is `load_<dataset>_<product>(aoi, *, years, months=None, cache_dir=None)`; some static loaders take `year: int` instead. | MIGRATE→test | `mal-core/tests/test_spec_retirement_download.py::test_time_series_loaders_accept_years_and_months_keywords_only` and `::test_every_loader_takes_aoi_first_and_never_output_path` | |
| 118 | The load-or-download semantics: try the manifest first, and if the dataset is missing, download it, save it, register it and return it. | DROP | No loader consults the manifest: the loaders fetch from their providers directly (`mal-commonlib/src/mal_commonlib/data/loaders/worldpop.py:408-433` and its siblings) and the runner — not the loader — is the save point (`mal-core/src/mal_core/download/runner.py:69-277`). | The API does not exist; the manifest is written by the runner after the download, never read by the loader. |
| 130 (loader table) | `era5_temp_suitability` and `chirps_rainfall` are loaders. | DROP | The loaders package holds no `era5` temp-suitability or CHIRPS-rainfall module (`mal-commonlib/src/mal_commonlib/data/loaders/`); the catalogue is ERA5 air temperature + wind, CHIRPS rainfall daily, JRC, Dynamic World, WorldPop, GLW, GHSL, buildings, wildlife, coastline, SMAP (`mal-core/src/mal_core/download/registry.py:56-75`). | The two loaders were retired with contract v3.0. |
| 132 (loader table) | `era5_temp_suitability` / `water_frac` / `ndvi` channels and the COG env variant. | DROP | The channels were dropped with contract v3.0 (`docs/concepts/contracts.yaml`, the `env` artefact). | Retired channels. |
| 137 (drift check) | Every downloader declares a `license` and an `attribution`. | ENFORCED | `mal-commonlib/tests/test_licenses.py:47-74` | |
| 143 (drift check) | The manifest's `datasets` block holds `era5_wind` and `chirps_rainfall` for Ghana. | DROP | The Ghana manifest holds `era5_air_temp_daily`, `chirps_rainfall_daily`, `dw_class_fractions`, `jrc_habitat_features` and the host/mobility artefacts (`data/ghana/manifest.json`). | The keys in the specification were renamed by contract v3.0. |

---

## `download/spec.md`

| spec:line | The claim | Class | Where it lives now | Reason |
|---|---|---|---|---|
| 95 | The public loader signature depends on `is_time_series`: time-series loaders take `years` (+ `months`), static loaders do not. | MIGRATE→test | `mal-core/tests/test_spec_retirement_download.py::test_years_is_present_exactly_for_time_series_loaders` and `::test_runner_branches_on_is_time_series` | |
| 99 | `aoi` is the first positional argument of every loader. | MIGRATE→test | `mal-core/tests/test_spec_retirement_download.py::test_every_loader_takes_aoi_first_and_never_output_path` | |
| 100 | Time-series loaders declare `years` (and often `months`) without defaults; static loaders omit them. | MIGRATE→test | `mal-core/tests/test_spec_retirement_download.py::test_time_series_loaders_accept_years_and_months_keywords_only` | |
| 101 | Loaders never accept `output_path`; they return data in memory and the runner calls `save_product()`. | MIGRATE→test | `mal-core/tests/test_spec_retirement_download.py::test_every_loader_takes_aoi_first_and_never_output_path`; the single save point is `mal-core/src/mal_core/download/runner.py:142, 173, 211, 251` | |
| 105 | Every loader module exports a `DOWNLOADER` dict with `name`, `description`, `requires_auth`, `outputs`, `manifest_keys`, and optionally `is_time_series` and `formats`. | ENFORCED | `mal-core/tests/test_download_contract.py:30-52` | |
| 105 | The `requires_auth` vocabulary is {cds, earthdata, planetary_computer, none}. | ENFORCED | `mal-core/tests/test_download_contract.py:13` — the vocabulary now also contains `earthengine`, which the Dynamic World loader needs (`mal-core/src/mal_core/download/runner.py:38-45`). | |
| 106 | Every key in `outputs` is a real callable and every value in `manifest_keys` is a unique manifest key. | ENFORCED | `mal-core/tests/test_download_contract.py:54-77` | |
| 110 | The runner discovers the downloaders by scanning the loaders package. | MIGRATE→test | `mal-core/tests/test_spec_retirement_download.py::test_discovery_covers_every_loader_module_on_disk`; the scan is `mal-core/src/mal_core/download/registry.py:12-27` | |
| 111 | The runner filters by `--datasets` (the downloader name) and `--outputs` (the output key). | MIGRATE→test | `mal-core/tests/test_spec_retirement_download.py::test_runner_filters_by_dataset_and_output` | |
| 112 | The runner branches on `spec.is_time_series` and reads `spec.formats[output_name]` to choose the monthly / daily / monthly_nc write path. | MIGRATE→test | `mal-core/tests/test_spec_retirement_download.py::test_runner_branches_on_is_time_series` and `::test_runner_uses_the_daily_and_monthly_nc_write_paths` | |
| 113 | The runner passes only the kwargs the loader accepts; unknown kwargs are silently dropped. | DROP | The runner passes a fixed kwarg set per branch — `{aoi, years, months, cache_dir}` for a time series, `{aoi, cache_dir}` for a static one (`mal-core/src/mal_core/download/runner.py:128, 165, 194, 244`); there is no signature inspection and no silent dropping. | The claim contradicts INV-9 of the same specification and the code; the runner never inspects a signature. |
| 114 | The runner is the only save point; `xr.DataArray` → GeoTIFF and `xr.Dataset` → NetCDF; a 3D DataArray cannot be saved as a TIF; the daily write path uses `<aoi>_<product>_<start>_<end>_daily.nc` and the monthly_nc path `<aoi>_<product>_<start>_<end>_monthly.nc`; the NetCDF variable name drops the `_daily` / `_salinity` suffix. | MIGRATE→test | `mal-core/tests/test_spec_retirement_download.py::test_runner_uses_the_daily_and_monthly_nc_write_paths`, `::test_standard_paths_follow_the_canonical_naming`, `::test_writer_refuses_a_3d_dataarray_as_tif`; the writer itself is `mal-core/src/mal_core/download/writer.py:12-45` | |
| 115 | After each successful save the runner calls `update_dataset(aoi, manifest_key, year, path.name, type=..., required_for_abm=..., format=..., period=...)`; for a daily NC, `year=None` and the period is derived from the time axis. | MIGRATE→test | `mal-core/tests/test_spec_retirement_download.py::test_runner_registers_the_dataset_in_the_manifest` | |
| 116 | The auth gate reports `{"status": "skipped"}` when the credentials are missing and does not raise. | MIGRATE→test | `mal-core/tests/test_spec_retirement_download.py::test_auth_gate_reports_skipped_and_does_not_raise` | |
| 128 (loader table) | `dynamic_world` is a loader and `worldcover` is not. | ENFORCED | `mal-core/tests/test_download_contract.py:79-90` | |
| 128 (loader table) | The `wc_class_fractions` manifest key is retired. | MIGRATE→test | `mal-core/tests/test_spec_retirement_download.py::test_no_loader_exports_the_retired_worldcover_manifest_key` | |
| 144 (example) | A loader is called with `years=[2024], months=[6]` and a `cache_dir`. | MIGRATE→test | `mal-core/tests/test_spec_retirement_download.py::test_runner_branches_on_is_time_series` | |
| 145 (example) | A download writes `data/ghana/ghana_era5_wind_2024.tif`. | DROP | The ERA5 write path is the daily multi-year NetCDF `ghana_wind_6hourly_<start>_<end>_daily.nc`; the per-year GeoTIFF form belongs to the monthly path (`mal-core/src/mal_core/download/runner.py:126-224`). | The example names a file the runner no longer writes for ERA5. |

---

## `ingest/spec.md`

| spec:line | The claim | Class | Where it lives now | Reason |
|---|---|---|---|---|
| 167 | The habitat patches are the candidate-cell union (`total_potential(H) > HABITAT_CANDIDATE_MIN`) written as GeoPackage Points with the columns `hab_type, habitat_potential, dynamics, row, col, aoi_slug, geometry` and one numeric column per habitat type. | MIGRATE→test | `mal-core/tests/test_spec_retirement_ingest.py::test_habitat_gpkg_carries_the_documented_columns`; the writer is `mal-core/src/mal_core/ingest/env.py:48-107` | |
| 167 | The gpkg contains only cells whose summed potential exceeds `HABITAT_CANDIDATE_MIN`. | MIGRATE→signal | `mal-core/src/mal_core/ingest/env.py:70` selects `h_total > 0.0`, while the census in `daily_nc.py:380` uses `HABITAT_CANDIDATE_MIN` (`1e-6`). | The two thresholds differ in the code; the specification named one of them. The divergence is recorded rather than silently harmonised (harmonising would be a behaviour change). |
| 171 | The env NC is CF-1.8 with dims `(time, y, x)`, the daily `rainfall` / `air_temp_c` and the 2-D statics, all float32, zlib-compressed at level 4, the statics carried once on the `(y, x)` grid. | MIGRATE→test | `mal-core/tests/test_spec_retirement_ingest.py::test_env_nc_statics_are_2d_float32_and_never_broadcast` and `::test_env_nc_uses_zlib_compression_level_four` | |
| 172 | The `time` axis covers the whole multi-year range of the CHIRPS daily input. | MIGRATE→test | `mal-core/tests/test_spec_retirement_ingest.py::test_env_nc_time_axis_covers_every_rainfall_day` | |
| 173 | The env NC carries `contract_version: "3.0"` and `generator_version: "proxy-habitat-v1-0.1.0"`. | MIGRATE→test | `mal-core/tests/test_spec_retirement_ingest.py::test_env_nc_is_cf18_with_the_pinned_contract_and_generator` | |
| 174 | The env file is named `{aoi}_regional_{start}_{end}_env.nc`; the scale is hardcoded to `regional` and the years are inferred from the CHIRPS input. | MIGRATE→test | `mal-core/tests/test_spec_retirement_ingest.py::test_env_nc_filename_follows_the_regional_multi_year_convention` | |
| 175 | A cell enters the patch union when its summed potential exceeds `1e-6`; zero candidate cells raise a `RuntimeError`. | MIGRATE→test + ENFORCED | The constant: `mal-core/tests/test_spec_retirement_ingest.py::test_habitat_candidate_min_is_the_configured_floor`; the raise: `mal-core/tests/test_m12_integration.py:100-115` (already existed) | |
| 176 | The static planes are 2-D and never broadcast; the ERA5-Land daily NC must cover every rainfall day or the build raises. | MIGRATE→test | `mal-core/tests/test_spec_retirement_ingest.py::test_env_nc_statics_are_2d_float32_and_never_broadcast` and `::test_env_nc_requires_air_temperature_for_every_rainfall_day` | |
| 180 | The host static file is `{aoi_slug}_host_static.nc` with the variables `human, cattle, goats, sheep, pigs, chickens, urban_class (int32), building_fraction, wildlife_host_proxy`, all 2-D `(H, W)`. | MIGRATE→test | `mal-commonlib/tests/test_spec_retirement_commonlib.py::test_the_host_static_nc_carries_the_nine_documented_variables`; the ingest-side declaration is `mal-core/tests/test_spec_retirement_ingest.py::test_host_manifest_declares_the_nine_host_variables` | |
| 181 | The companion manifest is `{aoi_slug}_host_manifest.json` with the human total, the livestock totals, the urban/rural cell counts and the grid spec. | MIGRATE→test | `mal-commonlib/tests/test_spec_retirement_commonlib.py::test_the_host_manifest_companion_is_written` | |
| 182 | The GHSL SMOD reclassification is `30 → 30`, `20-29 → 50`, `0-19 → 20`; a failure falls back to all-50. | MIGRATE→signal | `mal-core/tests/test_spec_retirement_ingest.py::test_ghsl_reclassification_and_fallback_constants_are_pinned`; the code is `mal-core/src/mal_core/ingest/hosts.py:121-136` | |
| 183 | The building-fraction fallback is `0.6` urban / `0.1` rural and the wildlife proxy fallback is `0.3`. | MIGRATE→signal | `mal-core/tests/test_spec_retirement_ingest.py::test_ghsl_reclassification_and_fallback_constants_are_pinned`; the code is `mal-core/src/mal_core/ingest/hosts.py:141, 159, 164, 182` | |
| 187 | The three mobility CSRs are `{aoi}_mobility_day.csr`, `{aoi}_mobility_night.csr` and `{aoi}_livestock_mobility.csr`, built with `cell_size_km=1.0`, `beta_day=0.05`, `beta_night=0.5`, `beta_livestock=0.1`, `max_distance_km=50.0`. | MIGRATE→test | `mal-core/tests/test_spec_retirement_ingest.py::test_mobility_writes_the_three_csr_files_with_the_gravity_parameters` | |
| 188 | `build_mobility_dataset` raises `FileNotFoundError` when the host static NC is missing. | MIGRATE→test | `mal-core/tests/test_spec_retirement_ingest.py::test_mobility_requires_the_host_static_file` | |
| 192 | Ingest never downloads; a missing input raises `FileNotFoundError`. | MIGRATE→signal | `mal-core/tests/test_spec_retirement_ingest.py::test_the_ingest_package_never_calls_the_download_runner` | The claim holds for the env path only: the host builder imports provider loaders (`mal-core/src/mal_core/ingest/hosts.py:24-33`). |
| 192 | Ingest never downloads. (host path) | DROP | The host builder fetches WorldPop, GLW4, GHSL, Overture and the wildlife proxy through the loaders (`mal-core/src/mal_core/ingest/hosts.py:75-183`). | The claim is false for the host path; the migrated signal narrows it to the env path. |
| 193 | `NODATA_SENTINEL = -9999.0` is the single NoData value of the ingest outputs. | MIGRATE→test | `mal-core/tests/test_spec_retirement_ingest.py::test_nodata_sentinel_is_the_configured_value` | |
| 197 | Each builder registers its outputs in the manifest through `register_dataset` → `update_dataset`, with the kwargs `type`, `required_for_abm`, `variables` and `format`. | MIGRATE→test | `mal-core/tests/test_spec_retirement_download.py::test_runner_registers_the_dataset_in_the_manifest`; the kwargs are honoured by `mal-core/src/mal_core/download/manifest.py:118-189` | |
| 197 | The kwargs are ignored today (the "known kwargs-ignored drift"). | DROP | The kwargs reach the manifest (`mal-core/src/mal_core/download/manifest.py:161-174`); the migrated download test pins the stored `type`, `format`, `required_for_abm` and `period`. | The drift it described was fixed; keeping the row would document a defect that no longer exists. |
| 210 (drift check) | The env NC `contract_version` is `"2.0"` and the `generator_version` is `"m2-daily-0.4.0"`. | DROP | The env NC carries `"3.0"` / `"proxy-habitat-v1-0.1.0"` (`mal-core/src/mal_core/ingest/daily_nc.py:438-439`). | Both values were stale. |

---

## `scoring/spec.md`

| spec:line | The claim | Class | Where it lives now | Reason |
|---|---|---|---|---|
| 111 | `run_scoring` writes `scorecard.json` inside the run directory, and a scorer that raises is reported as skipped rather than sinking the run. | MIGRATE→test | `mal-core/tests/test_spec_retirement_scoring.py::test_scorecard_json_is_written_inside_the_run_dir` and `::test_a_raising_scorer_becomes_skipped_not_a_crash` | |
| 114 | A skipped scorer is excluded from the composite *and* from its weight sum. | MIGRATE→test | `mal-core/tests/test_spec_retirement_scoring.py::test_skipped_dimensions_are_excluded_from_the_weight_sum`; the arithmetic is `mal-core/src/mal_core/scoring/runner.py:108-118` | |
| 120 | The composite scorers live at `mal_core/scoring/scorers/d<id>_<name>.py`. | MIGRATE→test | `mal-core/tests/test_spec_retirement_scoring.py::test_each_composite_scorer_has_a_d_module_and_gates_live_in_gates_py` and `::test_list_scorers_reports_kind_weight_and_manual_flag` | |
| 123 | The scorer ID set is stable: 13 composite dimensions (D1, D2, D3, D4, D5, D8, D11, D15, D16, D19, D20, D21, D25) and 6 gates (G6, G7, G10, G12, G14, G24). | MIGRATE→test | `mal-core/tests/test_spec_retirement_scoring.py::test_scorer_id_set_is_stable` and `::test_registry_has_exactly_the_13_composite_dims_and_6_gates` | |
| 135 | Missing required data makes the scorer return a `skipped` status rather than a zero score. | MIGRATE→test | `mal-core/tests/test_spec_retirement_scoring.py::test_missing_data_yields_a_skipped_status_not_a_zero`; the contract is `mal-core/src/mal_core/scoring/scorers/base.py:26-53` | |
| 143 | Adding a scorer = a new file in `scorers/` plus an entry in the registry, with a weight. | DROP | The rule is a process, not a runtime fact; the file↔registry correspondence is what the migrated test pins. | A process rule cannot be executed; the executable part (the registry ↔ file set) is migrated. |
| 145 | Removing a scorer is a MAJOR change because historical scorecards become incomparable. | DROP | Same as above: a versioning policy with no runtime expression. | |
| 150 | The composite is the weighted geometric mean over the "ok" composite dimensions, and it is 0 if any dimension is ≤ 0. | MIGRATE→test | `mal-core/tests/test_spec_retirement_scoring.py::test_composite_is_the_weighted_geometric_mean` and `::test_a_zero_dimension_collapses_the_composite` | |
| 154 | `COMPOSITE_WEIGHTS` is the single source of truth for the weights, with the exact table the specification listed. | MIGRATE→test | `mal-core/tests/test_spec_retirement_scoring.py::test_composite_weights_are_exactly_the_pinned_table` | |
| 157 | The composite handles a variable number of dimensions. | MIGRATE→test | `mal-core/tests/test_spec_retirement_scoring.py::test_skipped_dimensions_are_excluded_from_the_weight_sum` | |
| 164 | The LLM judge never gates a run; it only appends an optional `verdict_llm` key. | MIGRATE→test | `mal-core/tests/test_spec_retirement_scoring.py::test_llm_judge_is_not_gating_when_the_key_is_absent` | |
| 169 | The prompts live in `mal_core/scoring/prompts/`. | MIGRATE→test | `mal-core/tests/test_spec_retirement_scoring.py::test_llm_prompt_file_exists` | |
| 172 | The judge uses OpenRouter (`https://openrouter.ai/api/v1`), reads `OPENROUTER_KEY` and defaults to the `minimax/minimax-m3` model. | MIGRATE→test + ENFORCED | `mal-core/tests/test_spec_retirement_scoring.py::test_llm_judge_uses_openrouter_and_the_pinned_model`; the call path is `mal-core/tests/test_scoring_llm.py:79` | |
| 180 | `get_feedback` takes the canonical scorecard shape and reports the composite, the failed gates, the skipped scorers, the regressions against a baseline and the weakest dimensions. | MIGRATE→test | `mal-core/tests/test_spec_retirement_scoring.py::test_feedback_reports_composite_verdict_failed_gates_and_regressions` | |
| 188 | The CLI dispatches `malariasim score --run-dir <dir>` (with `--only`, `--skip`, `--baseline`) and `malariasim feedback --run-dir <dir>`. | MIGRATE→test | `mal-core/tests/test_spec_retirement_scoring.py::test_cli_exposes_score_feedback_and_the_validation_wrappers`; the commands are `mal-core/src/mal_core/cli.py:409` and `:841` | |

---

## `training/spec.md`

| spec:line | The claim | Class | Where it lives now | Reason |
|---|---|---|---|---|
| 98 | The input channels are `STATE_CHANNELS + ENV_CHANNELS = 6` and the output channels are 2. | DROP | The packaged pipeline is 10 in / 6 out — 6 state channels (2 vector + 4 transmission) plus 4 env channels (`mal-core/src/mal_core/training/dataset.py:19-22`, `mal-core/tests/test_training_pipeline.py:39-50`), and the registry defaults match (`mal-core/src/mal_core/prediction/registry.py:28-29`). | The channel arithmetic in the specification was already false when it was written; keeping it would have pinned the wrong contract. |
| 99 | The encoder/decoder channel widths are `(32, 64, 128, 256)` and the bottleneck doubles the deepest width. | MIGRATE→test | `mal-core/tests/test_spec_retirement_training.py::test_unet_channel_widths_are_frozen` | |
| 100 | `PATCH_SIZE = 128`; the batches are `(B, 6, 128, 128)` → `(B, 2, 128, 128)`. | MIGRATE→test | `mal-core/tests/test_spec_retirement_training.py::test_unet_forward_keeps_the_spatial_shape` (the shape) and the dataset constants (`mal-core/src/mal_core/training/dataset.py:19`) | The channel counts of the batch are covered by the row above. |
| 101 | The loss is `mse + 0.5 * soft_dice`. | MIGRATE→test | `mal-core/tests/test_spec_retirement_training.py::test_combined_loss_is_mse_plus_half_the_soft_dice` | |
| 101 | The soft Dice uses `tau=0.1, thresh=0.01`. | DROP | The code uses `tau=0.5, thresh=0.5` — adult counts under state contract 4.0 (`mal-core/src/mal_core/training/model.py:63-74`); pinned by `mal-core/tests/test_spec_retirement_training.py::test_soft_dice_thresholds_are_the_contract_4_ones`. | The thresholds were a fraction of an adult; the specification predates contract 4.0. |
| 105 | The input state bands are `{state, suitability}` and the env bands come from the ABM env tensor. | DROP | The bands are `adult_patch_count` / `adult_cell_count` and the reader is positional (`mal-core/src/mal_core/training/dataset.py:178-186`); the env is the four-channel tensor (`dataset.py:19-22`). | The band names were retired with contract 4.0. |
| 106 | The training pairs are `(state_t, state_{t+7})`, the target file being `state_seed{seed:04d}_day{day+7:03d}.{tif,npy}`. | DROP | The dataset pairs *consecutive* days (`mal-core/src/mal_core/training/dataset.py:134-141`); pinned by `mal-core/tests/test_spec_retirement_training.py::test_pairs_are_consecutive_days`. | The specification states a 7-day step the code never implemented. |
| 107 | The state files are found by the glob `state_seed*_day*.{npy,tif}` and read by band name. | DROP | The discovery is `*.tif` with `_day` in the name plus `*_day*.npy` (`mal-core/src/mal_core/training/dataset.py:92-97`), and the bands are read positionally (`dataset.py:178-186`); pinned by `mal-core/tests/test_spec_retirement_training.py::test_state_snapshots_are_discovered_by_the_day_infix`. | Both halves of the claim are false against the code. |
| 108 | The train/val split is per patch on the mid-column: `col * patch_size >= W // 2` ⇒ val. | MIGRATE→test | `mal-core/tests/test_spec_retirement_training.py::test_train_and_val_split_on_the_mid_column` | |
| 109 | Subsampling below 1.0 uses `np.random.seed(42)` and is reproducible. | MIGRATE→test | `mal-core/tests/test_spec_retirement_training.py::test_subsampling_is_reproducible`; the code is `mal-core/src/mal_core/training/dataset.py:166-170` | |
| 113 | The defaults are `Adam(lr=1e-3)`, 50 epochs and a batch size of 16. | MIGRATE→test | `mal-core/tests/test_spec_retirement_training.py::test_training_defaults` and `::test_the_optimizer_is_adam_and_the_device_order_is_cuda_mps_cpu` | |
| 114 | The device is resolved as `cuda` → `mps` → `cpu`. | MIGRATE→signal | `mal-core/tests/test_spec_retirement_training.py::test_the_optimizer_is_adam_and_the_device_order_is_cuda_mps_cpu`; the code is `mal-core/src/mal_core/training/trainer.py:29-35` | |
| 115 | `model_epoch_{N}.pt` is written every 10 epochs and `final_model.pt` at the end; `best_model.pt` is overwritten on improvement. | MIGRATE→signal | `mal-core/tests/test_spec_retirement_training.py::test_the_checkpoint_cadence_and_file_names`; the code is `mal-core/src/mal_core/training/trainer.py:85-93` | |
| 115 | `best_model.pt` is overwritten only on a *strictly greater* `val_dice`. | DROP | The comparison is `>=` (`mal-core/src/mal_core/training/trainer.py:85-91`). | The claim is off by one operator. |
| 116 | `subsample` and `preload` pass through to the dataloaders and do not change the loss or the Dice. | MIGRATE→test | `mal-core/tests/test_spec_retirement_training.py::test_subsampling_is_reproducible` and `::test_dataloaders_return_a_train_and_a_val_loader` (the pass-through is `mal-core/src/mal_core/training/dataset.py:255-287`) | |
| 120 | `UNetWrapper.predict(state (2,H,W), env (4,H,W)) -> (2,H,W)`; the output has the two state channels. | DROP | The wrapper is generic in the channel count and returns the model's output channels (`mal-core/src/mal_core/training/wrapper.py:68-106`); in the transmission configuration that is 6; pinned by `mal-core/tests/test_spec_retirement_training.py::test_the_wrapper_is_generic_in_the_channel_count`. | The fixed 2-channel shape is false for the shipped configuration. |
| 121 | The wrapper loads the checkpoint eagerly and a missing checkpoint raises `FileNotFoundError` at construction. | MIGRATE→test | `mal-core/tests/test_spec_retirement_training.py::test_the_wrapper_raises_file_not_found_at_construction` | |
| 141 (§7) | The env tensor is zero-filled by the trainer — a known limitation. | DROP | The env is loaded when a path is given (`mal-core/src/mal_core/training/dataset.py:66-88`); the zero-fill survives only as the fallback when no path is given (`dataset.py:246-249`); pinned by `mal-core/tests/test_spec_retirement_training.py::test_the_env_tensor_is_loaded_into_the_input`. | The limitation was fixed; the migrated test pins the fixed behaviour. |
| 165 (drift check) | The trainer contains `env = np.zeros`. | DROP | The zero-fill is the fallback branch (`mal-core/src/mal_core/training/dataset.py:246-249`), not the normal path. | The check flagged a fallback as if it were the behaviour. |

---

## `prediction/spec.md`

| spec:line | The claim | Class | Where it lives now | Reason |
|---|---|---|---|---|
| 101 | `model.predict(state (2,H,W), env (4,H,W)) -> (1,H,W)`. | DROP | The model output has one band per output channel — 6 in the transmission configuration (`mal-core/src/mal_core/prediction/registry.py:28-29`, `mal-core/src/mal_core/prediction/predictor.py:30-41`). | The `(1,H,W)` shape is false for the shipped configuration. |
| 102 | `load_env_stack` selects the channels `["rainfall", "air_temp_c", "jrc_persistent", "lc_wetland"]`. | MIGRATE→test | `mal-core/tests/test_spec_retirement_prediction.py::test_env_channel_order_is_the_contract_v3_set`; the constant is `mal-core/src/mal_core/prediction/env_loader.py:18` | |
| 103 | `load_abm_state` picks `state_seed{seed:04d}_day{min(360,max(7,month*30)):03d}.{npy,tif}` and raises `FileNotFoundError` when no snapshot exists. | DROP | The loader clamps the day to `[1, 730]` and picks the closest *available* snapshot, whatever its name (`mal-core/src/mal_core/prediction/state_loader.py:38-79`); pinned by `mal-core/tests/test_spec_retirement_prediction.py::test_the_prediction_state_loader_day_is_clamped_to_the_code_range`. | The day range and the file-naming rule are both different in the code. |
| 107 | The models live under `runs/models/<name>_<version>/model.yaml` with the schema `name, version, contract_version, in_channels, out_channels, checkpoint, description`. | MIGRATE→test | `mal-core/tests/test_spec_retirement_prediction.py::test_registry_discovers_model_yaml_manifests` | |
| 108 | `ModelRegistry.load(name, version=None)` picks the latest `<name>@<version>`, returns a `DummyModel` when `checkpoint=""` and otherwise builds a `UNetWrapper`. | MIGRATE→test | `mal-core/tests/test_spec_retirement_prediction.py::test_registry_picks_the_latest_version` and `::test_dummy_model_returns_zeros_with_the_state_channel_count` | |
| 109 | `ModelManifest.contract_version` defaults to `"1.1"`. | MIGRATE→test | `mal-core/tests/test_spec_retirement_prediction.py::test_model_manifest_defaults` | |
| 113 | `RegionalAggregator` returns the input unchanged; the regional grid is 1000 m with a tile size of 128. | MIGRATE→test | `mal-core/tests/test_spec_retirement_prediction.py::test_regional_aggregator_is_a_passthrough`, `::test_scale_grids_are_the_documented_resolutions`, `::test_get_aggregator_maps_every_scale` and `::test_grid_shape_comes_from_the_aoi` | |
| 114 | `NationalAggregator` pools by `(H//10, W//10)` blocks, trims and takes the mean over the block axes. | MIGRATE→test | `mal-core/tests/test_spec_retirement_prediction.py::test_national_aggregator_pools_by_ten`; the code is `mal-core/src/mal_core/prediction/aggregator.py:56-66` | |
| 115 | `ContinentalAggregator` returns a single scalar, `np.array([float(raster.mean())])`. | MIGRATE→test | `mal-core/tests/test_spec_retirement_prediction.py::test_continental_aggregator_returns_one_scalar` | |
| 116 | `AOI_CATALOGUE` is the source of truth for the slugs `make_aoi` accepts. | DROP | There is no `AOI_CATALOGUE` symbol; the catalogue is `mal-commonlib/src/mal_commonlib/aois.yaml`, read by `AOI.from_slug` (`mal-commonlib/src/mal_commonlib/aoi.py`). | The named symbol does not exist. |
| 120 | The pipeline specification hardcodes `scale=Scale.REGIONAL` when dispatching the prediction stage. | DROP | The pipeline specification was deleted on 2026-07-31; `run_prediction` defaults to `scale=Scale.REGIONAL` (`mal-core/src/mal_core/prediction/predictor.py:68`). | The specification this row constrains no longer exists. |
| 121 | The output is named `{aoi_slug}_{scale}_{year}_{month:02d}_risk.tif` and the sidecar keeps the `.tif.json` suffix. | MIGRATE→test | `mal-core/tests/test_spec_retirement_prediction.py::test_output_file_name_follows_the_convention` and `::test_the_sidecar_uses_the_tif_json_suffix` | |
| 125 | The GeoTIFF is float32, tiled, deflate-compressed, with block size 128, `nodata=-9999.0` and the AOI CRS/transform. | MIGRATE→test | `mal-core/tests/test_spec_retirement_prediction.py::test_the_risk_raster_carries_the_documented_profile`; the writer is `mal-core/src/mal_core/prediction/predictor.py:113-131` | The `count=1` part of the claim is dropped — the band count is the number of model output channels. |
| 126 | The band description is `["risk"]`, a single band. | DROP | The band names are the `predicted_*` family, one per output channel (`mal-core/src/mal_core/prediction/predictor.py:30-41, 129-132`). | The single-band description is false for the shipped model. |
| 127 | The sidecar carries `crs, transform, aoi_slug, scale, year, month, model_name, model_version, contract_version, generator_version`. | MIGRATE→test | `mal-core/tests/test_spec_retirement_prediction.py::test_the_sidecar_uses_the_tif_json_suffix` (the key set also includes `bands`) | |
| 128 | Every emitted file carries `contract_version: "1.1"`. | MIGRATE→test | `mal-core/tests/test_spec_retirement_prediction.py::test_the_sidecar_uses_the_tif_json_suffix` | |
| 137 (drift table) | The env channel name is `temperature` while the specification says `temp_suitability` — P0 drift. | DROP | The channels are the contract-v3.0 set (`mal-core/src/mal_core/prediction/env_loader.py:18`); `temp_suitability` was retired with contract v3.0. | The drift no longer exists. |
| 138 (drift table) | The env loader reads `runs/env_stack.npz` instead of the ingest NetCDF — P1 drift. | DROP | The loader tries the AOI's NetCDF/GeoTIFF first and only then the legacy NPZ stack (`mal-core/src/mal_core/prediction/env_loader.py:36-148`). | The row described a P1 fallback that is now a last resort, not the primary source. |
| 139 (drift table) | `in_channels` defaults to 5 while the specification says 6 — P1 drift. | DROP | The default is 10 (state 6 + env 4) and 6 out (`mal-core/src/mal_core/prediction/registry.py:28-29`). | The "6" of the specification was itself wrong; the code now carries the real shape. |
| 140 (drift table) | The sidecar suffix is `.tif.json` while the ABM readers expect `.json` — P0 drift. | DROP | The `.tif.json` suffix is the emitted convention (`mal-core/src/mal_core/prediction/predictor.py:147`) and the readers were aligned to it; the migration row in the same table ("switching the suffix is BREAKING") was never executed. | The drift was closed by aligning the readers, not by changing the suffix. |
| 141 (drift table) | The `scenario` parameter is converted to params and then never passed to the model — P1 drift. | DROP | The conversion is still there (`mal-core/src/mal_core/prediction/predictor.py:86-88`) and the params are still not passed to `model.predict`. | The drift is real and still open; it is recorded as a known limitation of the code, not as a fact the retirement could migrate. |
| 142 (drift table) | The `aoi_resolver` module is implemented but undocumented. | DROP | The module is documented by its own docstring and by `mal-core/src/mal_core/prediction/aoi_resolver.py:1-14`; the ABM CLI uses it. | The "undocumented" state it described was resolved by the module's own docstring. |
| 143 (drift table) | `UNetWrapper` lives in `mal_core.training.wrapper`, not in `prediction.registry`. | DROP | The import site is `mal-core/src/mal_core/prediction/registry.py:104`; the module is where the specification's own §4 table said it was. | The claim described a documentation gap that the row itself resolves. |

---

## `commonlib/spec.md`

| spec:line | The claim | Class | Where it lives now | Reason |
|---|---|---|---|---|
| 172 | `AOI` is frozen; mutating `aoi.bbox` raises. | ENFORCED | `mal-commonlib/tests/test_aoi.py:130` | |
| 173 | `AOI.slug` always matches `[a-z0-9]+(-[a-z0-9]+)*`. | ENFORCED | `mal-commonlib/tests/test_aoi.py:30-48` | |
| 174 | `AOI.bbox` always satisfies `west < east ∧ south < north`. | ENFORCED | `mal-commonlib/tests/test_aoi.py:50-60` | |
| 175 | `AOI.crs` is always parseable by `pyproj.CRS.from_user_input`. | ENFORCED | `mal-commonlib/tests/test_aoi.py:62-71` | |
| 176 | The habitat-contract static planes are float32 in [0, 1] with NoData `-9999.0` and carry `contract = "habitat-v3.0-statics"`. | ENFORCED | `mal-commonlib/tests/test_dynamic_world.py:159` and `mal-commonlib/tests/test_jrc_gsw.py:113, 232, 302` | |
| 177 | `AOI.cells_per_side()` is the single source of truth for the ABM output `(H, W)`; a hardcoded `H = W = 128` outside commonlib is a drift bug. | MIGRATE→test + ENFORCED | `mal-core/tests/test_spec_retirement_abm.py::test_no_code_outside_commonlib_hardcodes_a_128_grid`; the source of truth itself is `mal-commonlib/tests/test_aoi.py:89` | |
| 178 | `RUNS_DIR` exists after importing `mal_commonlib.config`. | MIGRATE→test | `mal-commonlib/tests/test_spec_retirement_commonlib.py::test_runs_dir_exists_after_import` and `::test_the_repo_paths_are_repo_relative` | |
| 179 | `build_host_static_nc` writes CF-1.8 NetCDF with a CRS coordinate variable. | MIGRATE→test | `mal-commonlib/tests/test_spec_retirement_commonlib.py::test_the_host_static_nc_is_cf18_with_a_crs_coordinate_variable` | |
| 180 | `write_csr` writes a little-endian binary layout compatible with the C++ `SparseOD::load_from_csr()`. | MIGRATE→test + ENFORCED | `mal-commonlib/tests/test_spec_retirement_commonlib.py::test_the_csr_binary_layout_matches_the_cpp_reader`; the existing round-trip is `mal-commonlib/tests/test_mobility.py:165` | |
| 181 | All loaders return an `xr.DataArray` with dims `(y, x)` and dtype float32. | ENFORCED | `mal-commonlib/tests/test_host_loaders.py:284-285` (and the sibling loader tests) | |
| 195 (retired block) | `mal_commonlib.terrain` with `compute_twi` and `NODATA_OUT`, and a `dem` loader. | DROP | Both are gone: there is no `mal_commonlib/terrain` package and no `data/loaders/dem.py`. | The layer was retired by the proxy-habitat redesign (plan 01); its absence is now pinned by `mal-commonlib/tests/test_spec_retirement_commonlib.py::test_the_twi_terrain_module_is_gone` and `::test_the_dem_loader_is_gone`. |
| 199 (retired block) | `K_MAX` is a configured constant of the state output. | DROP | `K_MAX` was retired with state contract 4.0; the comment that says so is `mal-commonlib/src/mal_commonlib/config.py:60`. | The constant no longer exists; the absence is pinned by `::test_k_max_is_not_a_configured_constant`. |
| 205 (drift check) | The AOI JSON payload carries `slug, name, bbox, crs, resolution_m, scale, gadm_id, iso3`. | MIGRATE→test | `mal-commonlib/tests/test_spec_retirement_commonlib.py::test_aoi_to_file_writes_the_documented_keys` | |

---

## `_template.md`

| spec:line | The claim | Class | Where it lives now | Reason |
|---|---|---|---|---|
| 6-20 | Every specification carries a machine-readable `affects` block naming the other specifications it touches, and the drift-check agent parses it. | DROP | No such parser or agent exists in the tree; the dependency direction is now expressed by the conceptual documents (`docs/concepts/`) and by the imports themselves. | The block was consumed by a tool that does not exist. |
| 25-40 | A specification pins the component, version, status, owner and the date of the last drift check. | DROP | The version of each contract lives in `mal-core/config/model_constants.yaml` and `docs/concepts/contracts.yaml`; the ownership and the drift-check date were bookkeeping for a process that no longer runs. | The metadata had no mechanical consumer. |
| 45-70 | The invariants are numbered and each has a matching runnable check in the "Drift check" section. | DROP | The invariants are the rows of this ledger; the runnable checks are the new `test_spec_retirement_*.py` files. | The template's requirement was satisfied by the retirement itself. |
| 62 | "Reference `docs/specs/data/spec.md` for the canonical format." | DROP | The canonical manifest format is `mal-core/src/mal_core/download/manifest.py` and `mal-core/tests/test_manifest.py`. | The reference pointed at a document that no longer exists. |

---

## Summary

| Specification | Rows | ENFORCED | MIGRATE→test | MIGRATE→signal | DROP |
|---|---|---|---|---|---|
| `abm/spec.md` | 27 | 7 | 5 | 1 | 14 |
| `data/spec.md` | 20 | 2 | 11 | 0 | 7 |
| `download/spec.md` | 18 | 4 | 12 | 0 | 2 |
| `ingest/spec.md` | 20 | 1 | 13 | 4 | 3 |
| `scoring/spec.md` | 15 | 1 | 13 | 0 | 2 |
| `training/spec.md` | 19 | 0 | 8 | 2 | 9 |
| `prediction/spec.md` | 23 | 0 | 11 | 0 | 12 |
| `commonlib/spec.md` | 13 | 8 | 5 | 0 | 2 |
| `_template.md` | 4 | 0 | 0 | 0 | 4 |
| **Total** | **159** | **23** | **78** | **7** | **55** |

Four rows are `MIGRATE→test + ENFORCED` — a runnable assertion whose
mechanical enforcement already existed. They are counted in both columns,
so the column sums exceed the row count by four.

Every row carries the line number it occupied in the retired document, and
every migrated row names the test that now guards it, so a reviewer can
walk from a row to the test and back to the retired text.
