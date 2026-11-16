# ingest — question set

This file is the question set for the conceptual document of the **ingest
stage** of the MalariaSentinel pipeline (the stage that turns raw, downloaded
layers into the three artefacts the C++ engine consumes: the daily
environment NetCDF, the static habitat-patch GeoPackage, the host-density
grid and the mobility operators). It was compiled by reading the
implementation: `mal-core/src/mal_core/ingest/` (`daily_nc.py`, `env.py`,
`hosts.py`, `mobility.py`, `_shared.py`), the habitat reference modules in
`mal-core/src/mal_core/habitat/` (`potential.py`, `availability.py`,
`capacity.py`, `aquatic_stress.py`, `config.py`, `constants.py`), the
constants file `mal-core/config/model_constants.yaml` and its validator
`mal-core/src/mal_core/config_validation.py`, the catalogue and manifest
(`mal-core/src/mal_core/download/catalog.py`, `manifest.py`), the ingest
subcommand of `mal-core/src/mal_core/cli.py`, the consumer side
(`mal-core/src/mal_core/abm/wrapper.py` and the C++ engine under
`mal-core/src/mal_core/abm/`), and the AOI registry
(`mal-commonlib/src/mal_commonlib/aois.yaml`, `aoi.py`). The retired specs
(`docs/specs/ingest/spec.md`, `docs/specs/data/spec.md`,
`docs/specs/commonlib/spec.md`) were used only as material: several of their
claims are already contradicted by the code, so every question below is
anchored on code, and where the two disagree the question says so. The stance
the document must answer is the one in `docs/concepts/README.md` (S1–S10);
contract names and versions come from `docs/concepts/contracts.yaml` and
`model_constants.yaml`, never from prose.

---

## (a) Question set

### Purpose and boundary

**1. What question does the ingest stage exist to answer, and what would
count as it having answered it? What is explicitly *not* its job?**

- Citation: `mal-core/src/mal_core/ingest/__init__.py:1-10` (the three public
  builders), `mal-core/src/mal_core/ingest/daily_nc.py:1-40` (module
  docstring: "the daily env NetCDF + static habitat patches for an AOI"),
  `mal-core/src/mal_core/ingest/env.py:1-13` (module docstring:
  "Contract v3.0 of the proxy-habitat redesign").
- Answer: it answers "on the AOI's own grid, what is the daily forcing
  (rain, air temperature), what is the static breeding-habitat offer per
  cell, where are the candidate oviposition cells, where are the people and
  the animals, and how do people and animals move between cells?" It is not
  the place where data is fetched (that is download), where the dynamics are
  simulated (that is the ABM), or where the run is scored. Ingest is a
  transform layer that ends with a manifest-registered, self-describing set
  of files on disk.

**2. What are the entry points into the stage, and what does each one
expose?**

- Citation: `mal-core/src/mal_core/cli.py:196-239` (the `ingest`
  subcommand), `mal-core/src/mal_core/ingest/__init__.py:1-10`,
  `mal-core/src/mal_core/ingest/env.py:112-118` (`build_env_tensor`),
  `mal-core/src/mal_core/ingest/hosts.py:36-48` (`build_host_dataset`),
  `mal-core/src/mal_core/ingest/mobility.py:37-48` (`build_mobility_dataset`),
  `mal-core/src/mal_core/ingest/daily_nc.py:150-158` (`build_daily_env_nc`).
- Answer: the CLI `malariasim ingest --aoi … [--year …] [--month …]
  [--output-dir …] [--data-dir …] [--what env|hosts|mobility|all]`, plus
  three Python builders. `--what` selects which of the three builders runs;
  `all` is the default. The three builders are independent of each other
  except that mobility consumes the host grid produced by hosts.

**3. Which artefacts does the stage produce, under which names, and which
manifest keys does it claim for them?**

- Citation: `mal-core/src/mal_core/download/catalog.py:55-92`
  (`INGEST_ARTIFACTS`: `env`, `habitat`, `host_static`, `host_manifest`,
  `mobility_day`, `mobility_night`, `livestock_mobility`,
  `mobility_manifest`),
  `mal-core/src/mal_core/ingest/daily_nc.py:466` (env NC name),
  `mal-core/src/mal_core/ingest/env.py:172` (gpkg name),
  `mal-core/src/mal_core/ingest/hosts.py:186` (host NC name),
  `mal-core/src/mal_core/ingest/mobility.py:104-117` (the three CSR names),
  `mal-core/src/mal_core/ingest/mobility.py:137` (mobility manifest name).
- Answer: eight artefact keys, of which five are marked
  `required_for_abm=True` (`env`, `habitat`, `host_static`, `mobility_day`,
  `mobility_night`, `livestock_mobility`). On-disk names:
  `<aoi>_regional_<y0>_<y1>_env.nc`, `<aoi>_habitat_patches.gpkg`,
  `<aoi>_host_static.nc`, `host_manifest.json`,
  `<aoi>_mobility_day.csr`, `<aoi>_mobility_night.csr`,
  `<aoi>_livestock_mobility.csr`, `mobility_manifest.json`.

**4. Does ingest ever download anything?**

- Citation: `mal-core/src/mal_core/ingest/daily_nc.py:87-98` and
  `:186-190` (env inputs resolved from the manifest via
  `catalog.resolve_inputs`), versus
  `mal-core/src/mal_core/ingest/hosts.py:74` (`load_worldpop_population`),
  `:92` (`load_glw_livestock`), `:111` (`load_ghsl_urban_class`),
  `:146` (`load_buildings_fraction`), `:169` (`load_wildlife_host_proxy`).
- Answer: **the env/habitat path never downloads** — it resolves four
  required manifest keys and raises when one is absent. **The host and
  mobility path does download**: `build_host_dataset` calls the loader
  functions directly, and those loaders fetch from their providers
  (WorldPop, GLW4, GHSL, Overture, and the derived wildlife proxy). The
  retired spec's claim that "ingest never downloads"
  (`docs/specs/ingest/spec.md:190`, INV-17) holds only for the env path.
  → part (c).

### The spatial frame

**5. What is the spatial frame of the stage, and who defines it?**

- Citation: `mal-commonlib/src/mal_commonlib/aois.yaml:16-23` (Ghana: bbox
  `-3.5, 4.5, 1.5, 11.5`, `EPSG:4326`, `resolution_m: 1000`, scale
  `regional`), `mal-commonlib/src/mal_commonlib/aoi.py:88-95` (the AOI
  schema), `mal-commonlib/src/mal_commonlib/aoi.py:195-199`
  (`cells_per_side`: `ceil(height_m / resolution_m)`,
  `ceil(width_m / resolution_m)`).
- Answer: the frame is the AOI: a bounding box, a CRS, and a nominal ground
  resolution in metres (`1000 m` for Ghana, i.e. a ~1 km grid). The cell
  count is derived by rounding the metric extent up to whole cells, so the
  grid is defined in *metres* but *written* in the AOI's CRS units (degrees
  for Ghana).

**6. Where is (H, W) — the grid height and width — actually computed, and
is there only one definition?**

- Citation: `mal-core/src/mal_core/ingest/daily_nc.py:199-204`
  (`n_days, h, w = rainfall_raw.shape` — the env grid is taken from the
  CHIRPS file that the download stage already wrote on the AOI grid),
  `mal-core/src/mal_core/ingest/env.py:42-44` (`_read_static` asserts the
  static plane's shape equals `aoi.cells_per_side()`),
  `mal-core/src/mal_core/ingest/env.py:69-73` (the gpkg transform is built
  from `aoi.bbox` and `aoi.cells_per_side()`), versus
  `mal-core/src/mal_core/ingest/daily_nc.py:310-313` (the statics' shape is
  only checked against the *rainfall* grid `h, w`, not against the AOI).
- Answer: there are two definitions that must agree. The env NC's (H, W) is
  inherited from the CHIRPS input file; the gpkg's (H, W) comes from
  `aoi.cells_per_side()`. The link between them is the shape assertion in
  `_read_static` (which raises if they differ). The document must state
  this and the fact that the frame is thus owned jointly by the download
  stage (which built the CHIRPS file on the AOI grid) and the AOI record.
  → part (c) for the resulting failure mode.

**7. What are the units, the native resolution and the target resolution of
each input, and what does the reduction cost?**

- Citation: `mal-commonlib/src/mal_commonlib/data/loaders/chirps.py:6-7`
  (CHIRPS v2.0 daily, 0.05°, one file per day), `:230-242` (reprojection to
  the AOI grid with **nearest** neighbour, with the reason documented),
  `mal-commonlib/src/mal_commonlib/data/loaders/era5.py:107` (ERA5-Land
  source grid 0.1°), `mal-commonlib/src/mal_commonlib/data/loaders/jrc_gsw.py:7-12`
  (JRC GSW: per-cell **fraction** of ≥80 %-occurrence water pixels),
  `mal-commonlib/src/mal_commonlib/data/loaders/dynamic_world.py:63`
  (Dynamic World requested at 100 m), `:98-103` (the four feature columns
  and the DW label classes behind them), `:273-334` (areal-fraction
  reduction per cell), `mal-commonlib/src/mal_commonlib/data/loaders/coastline.py:246-261`
  (GSHHG land fraction and distance-to-land on the AOI grid).
- Answer: rainfall is mm/day on a 0.05° daily grid; air temperature is °C
  on a 0.1° daily grid; `jrc_persistent` is a per-cell fraction in [0, 1];
  the four `lc_*` planes are per-cell areal fractions in [0, 1]; the
  coastline plane is a per-cell land fraction in [0, 1]. All are delivered
  already reduced to the AOI grid by the download stage's loaders; ingest
  itself resamples only the coastline GeoTIFF
  (`mal-core/src/mal_core/ingest/daily_nc.py:126-148`, bilinear when the
  shape differs). What the reduction loses: the sub-cell composition of
  each cell, and — for rainfall — the ability to distinguish a cell that is
  mostly dry from one that is mostly nodata-ocean.

**8. Is the cell area of the frame computed correctly, and by which
formula?**

- Citation: `mal-core/src/mal_core/habitat/capacity.py:39-46`
  (`cell_area_km2`: `resolution_m² · cos(lat) / 1e6`),
  `mal-core/src/mal_core/abm/include/mal_abm_fast/habitat_availability.hpp:188-194`
  (the C++ mirror, same formula),
  `mal-core/src/mal_core/abm/src/coordinator.cpp:130-134` (the engine uses
  the **row-centre** latitude and `aoi_.resolution_m`),
  `mal-core/src/mal_commonlib/aoi.py:157-170` (`_m_per_unit`: degrees are
  converted to metres at the AOI **centroid** latitude).
- Answer: the cell area is the approximation
  `resolution_m² · cos(lat_row) / 1e6`, applied per grid row, and the same
  formula exists in Python and C++. The true area of the cell that
  `from_bounds(bbox, w, h)` actually produces in degrees is
  `(Δlon·111195·cos φ) × (Δlat·111195)`, which differs from the
  approximation because (i) `cells_per_side` rounds the metric extent up
  with `ceil`, so the cell edges do not fall on whole kilometres, and
  (ii) the approximation assumes the north-south extent is exactly
  `resolution_m`, while the degrees-based grid gives a constant
  `Δlat·111195`. Measured for Ghana (`bbox [-3.5, 4.5, 1.5, 11.5]`,
  `resolution_m 1000`, grid 779 × 551 = 429 229 cells): the geometric total
  is 428 274 km² against the approximation's 424 787 km², i.e. the
  approximation is 0.82 % low, and the per-cell error at the centroid row
  is 0.9984 km² (true) against 0.9903 km² (approximated). Both the Python
  and the C++ side use the same approximation, so the two agree with each
  other; the ~0.8 % is a small systematic bias in `K` (which is
  proportional to cell area), not a disagreement between the mirrors. The
  document must state the approximation and the magnitude, not present the
  area as exact.

**9. What are the coordinates written into the env NetCDF, and how is the
file georeferenced?**

- Citation: `mal-core/src/mal_core/ingest/daily_nc.py:200-201` (`times`,
  `y`, `x` taken from the rainfall file), `:432` (the dataset coordinates
  are `time`, `y`, `x` as inherited), `:468-494` (CF-1.8 2-D `lat`/`lon`
  coordinate variables and a `crs` grid-mapping variable are added **only
  when the axis step is a degree grid** below `ingest.grid_degrees_step_max`).
- Answer: the env NC inherits the CHIRPS file's `y`/`x` coordinate vectors
  (degrees for Ghana) and its `time` axis; it adds CF-1.8 `lat`/`lon` 2-D
  variables and a `crs` variable when the grid is in degrees, so that older
  GDAL NetCDF drivers expose the 2-D statics as sub-datasets.

### Inputs: what is required, what is optional, and how it is resolved

**10. Which inputs does the env builder consume, and which are mandatory?**

- Citation: `mal-core/src/mal_core/ingest/daily_nc.py:87-98`
  (`ENV_INPUT_SLOTS`: required `chirps_rainfall_daily`,
  `era5_air_temp_daily`, `jrc_habitat_features`, `dw_class_fractions`;
  optional `coastline_land_mask`, `host_static`, `smap_salinity`),
  `:186-190` (resolution through `catalog.resolve_inputs`),
  `mal-core/src/mal_core/download/catalog.py:176-268` (`resolve_inputs`
  semantics), `mal-core/src/mal_core/download/manifest.py:39-114`
  (`resolve_dataset_file`, strict).
- Answer: four required slots, three optional. A missing required slot is
  a hard error naming the download command; a missing optional slot is
  simply `None` and the corresponding behaviour is skipped. There is **no**
  conventional-filename fallback inside the consumer.

**11. What does the `host_static` slot do inside the env builder?**

- Citation: `mal-core/src/mal_core/ingest/daily_nc.py:96` (the slot
  declaration) versus `mal-core/src/mal_core/ingest/daily_nc.py:186-260`
  (the builder body: `resolved["host_static"]` is never read).
- Answer: nothing — it is declared as an optional dependency and never
  consumed by `build_daily_env_nc`. The only consumer of the host grid is
  the mobility builder. → part (c).

**12. What are the two temporal channels, and how is each prepared?**

- Citation: `mal-core/src/mal_core/ingest/daily_nc.py:197-223`
  (rainfall: read, NoData filled from the nearest valid donor cell via an
  EDT, negatives clamped to zero), `:262-289` (air temperature: read,
  **re-indexed onto the rainfall day axis**; a missing day raises), `:291-293`
  (open-sea cells set to `0.0` rather than NaN, with the reason given).
- Answer: `rainfall` (mm/day, CHIRPS) and `air_temp_c` (°C, ERA5-Land
  daily mean). The time axis is the **rainfall** axis; the temperature
  series must cover every one of those days or the build fails loudly
  (the retired annual-raster-to-daily broadcast path is gone). Open-sea
  cells receive rainfall `0.0` and temperature `0.0` — the sentinel the
  C++ climate engine and the renderer already understand, chosen so that
  `impute_temp_nans` does not fill sea pixels with plausible land
  temperatures.

**13. How is rainfall NoData handled, and what does that choice assume?**

- Citation: `mal-core/src/mal_core/ingest/daily_nc.py:206-223`
  (`nodata_mask = rainfall_raw == NODATA_SENTINEL`; a cell is a valid donor
  when its NoData time-fraction is below `ingest.fill_frac_valid_max`;
  `distance_transform_edt` gives each invalid cell its nearest valid donor),
  `mal-core/config/model_constants.yaml:137` (`nodata_sentinel`),
  `:155` (`fill_frac_valid_max`).
- Answer: NoData is replaced, per day, by the value of the spatially
  nearest *always-valid* cell. A cell whose NoData fraction is ≥ the
  threshold is not eligible to donate. If no cell is eligible, NoData
  becomes `0.0`. The assumption is that the nearest valid cell is a
  plausible donor for that day — an assumption the code states but does not
  test.

**14. What is the open-sea rule, and what happens when the coastline
artefact is absent?**

- Citation: `mal-core/src/mal_core/ingest/daily_nc.py:58-69` (the rule in
  prose: open sea ⇔ `land_frac < sea_water_floor` **and**
  `distance_to_land > coast_band_m`), `:225-258` (the implementation,
  with `COASTLINE_BUFFER_M` overridable by environment variable),
  `mal-commonlib/src/mal_commonlib/data/loaders/coastline.py:264-294`
  (`sea_mask`), `:246-261` (`distance_to_land_m`),
  `mal-core/src/mal_core/ingest/daily_nc.py:357-362` (the "no coastline
  artefact found" warning).
- Answer: a cell is open sea when it is water by land fraction and farther
  than the coastal band from land; the band is a **distance query, not a
  mask dilation** (the comment records that a former dilation moved the
  coast kilometres inland). When the coastline artefact is absent the
  saltwater filter is skipped with a printed warning — the build continues
  and the statics keep their open-ocean cells. That is a silent-ish
  degradation: only a printed note, not an error.

**15. What does the open-sea rule do to the habitat statics, and why?**

- Citation: `mal-core/src/mal_core/ingest/daily_nc.py:340-356` (all five
  static planes are multiplied by the `keep` mask), `:326-339` (the
  rationale: Dynamic World reports "water" at 1.0 over the ocean, which
  would otherwise make every ocean cell a breeding candidate),
  `mal-core/src/mal_core/ingest/daily_nc.py:365-374` (the printed
  coastline census).
- Answer: all five static planes — `jrc_persistent` **and** the four `lc_*`
  planes — are zeroed on open sea; the coastal band keeps them, because
  lagoons, estuaries and the shallow plume are real habitat. The build
  prints an auditable one-line census of land / mixed / coastal-water /
  open-sea cells and the before→after sums.

**15-bis. Are the artefacts actually in `data/ghana/` consistent with the
code as it stands today?**

- Citation: `git log -- mal-core/src/mal_core/ingest/daily_nc.py` (the open-
  sea rule landed in `36bedbf`, 2026-10-29); the artefact timestamps
  (`data/ghana/ghana_regional_2024_2024_env.nc` and
  `ghana_habitat_patches.gpkg`, both 2026-10-18); the current rule
  (`mal-core/src/mal_core/ingest/daily_nc.py:57-69`, `:248-251`);
  `mal-commonlib/src/mal_commonlib/data/loaders/coastline.py:297-390` (the
  loader now returns a *fraction*, sub-pixel rasterised at 30 m).
- Answer: **no — the checked-in Ghana artefacts predate the fix and carry
  the exact pathology it fixed.** Three independent pieces of evidence:
  (i) the env NC has **no `land_frac` plane**, and that plane was added by
  `36bedbf`; (ii) `data/ghana/ghana_land_mask.tif` holds only the values
  {0.0, 1.0}, i.e. a *binary* mask, while the current coastline loader
  returns a fractional land cover, so the file was produced by the older
  loader; (iii) the artefact was built on 2026-10-18, eleven days before
  the fix. The consequence is measurable on the artefact itself: applying
  the **current** open-sea rule to the stored statics
  (`land_frac < 0.05` and `distance_to_land > 2 km`) marks **45 674 cells**
  as open sea, of which **45 674 are currently candidates** in the
  GeoPackage and 45 399 carry `lc_open_plus_water = 1.0`; re-running the
  static-potential computation with the current mask applied reduces the
  candidate count from **382 127 to 336 453**. The stored NC nevertheless
  shows rainfall zeroed on exactly the 46 776 cells with `land_frac < 0.05`,
  which is the *old* rule (`land_mask <= ocean_mask_threshold`) — the
  binary-mask semantics of the pre-fix code. The document must therefore
  describe the rule as implemented **and** state that the Ghana artefacts
  in the repository were produced by the previous implementation, so a
  reader comparing the document against the files will not be misled.
  → part (c).

**16. How are the static planes assembled from the source files, and what
happens to a multi-year land-cover stack?**

- Citation: `mal-core/src/mal_core/ingest/daily_nc.py:296-315`
  (`_static_from_ds`: a 3-D variable is averaged over the time axis,
  NaN → 0), `:317-323` (the JRC and Dynamic World reads),
  `mal-commonlib/src/mal_commonlib/data/loaders/dynamic_world.py:336-409`
  (the loader returns one **modal-label composite per year**, with the
  contract attribute `habitat-v3.0-statics`).
- Answer: the Dynamic World file carries one frame per year; ingest
  averages the per-year areal fractions into the single static plane.
  The JRC plane is a single 2-D frame. A shape mismatch against the
  rainfall grid raises; a missing variable raises with the list of
  variables actually present.

**17. Is the salinity channel part of the contract, and how is it
broadcast?**

- Citation: `mal-core/src/mal_core/ingest/daily_nc.py:390-402` (monthly
  SMAP salinity is broadcast to every day of the month),
  `:452-457` (the `salinity_ppt` variable, units `psu`),
  `mal-core/src/mal_core/ingest/daily_nc.py:550-578` (`_read_salinity_monthly`,
  bilinear reprojection onto the env grid),
  `mal-core/src/mal_core/abm/src/env_reader.cpp:255-271` (the engine reads
  it when present, and treats its absence as "no salinity data").
- Answer: optional. When the `smap_salinity` slot resolves, a monthly
  field is reprojected onto the env grid and copied to each day of its
  month; land and no-data cells stay NaN and become `0.0`. The engine
  applies it as a hard gate: a patch whose salinity exceeds the species'
  high tolerance cannot breed
  (`mal-core/src/mal_core/abm/src/coordinator.cpp:220-226`).

### The habitat model

**18. Where is the static breeding-habitat potential H computed, and what
exactly is it?**

- Citation: `mal-core/src/mal_core/habitat/potential.py:50-80`
  (`static_potential`: the six H values from the five feature planes),
  `mal-core/src/mal_core/habitat/potential.py:18-23` (the mapping in
  prose), `mal-core/src/mal_core/habitat/potential.py:82-90`
  (`total_potential`), `mal-core/src/mal_core/habitat/potential.py:103-111`
  (NaN → 0, clipped to [0, 1]).
- Answer: in Python, in one pure function of five feature planes, producing
  six per-cell values in [0, 1]:
  `surface_persistent = jrc_persistent`,
  `wetland_persistent = lc_wetland`,
  `urban_persistent = beta_urban · lc_built`,
  `wetland_pluvial = lc_wetland`,
  `open_pluvial = lc_open_plus_water + rain_pools_built_damage · lc_built`,
  `crop_pluvial = lc_crop`.
  The total is the sum of the six, clipped to [0, 1]. H is an **index of
  relative offer**, not a measured pool count, depth or volume — the
  docstring says so explicitly, and the contract table repeats it
  (`docs/concepts/contracts.yaml`, artefact `habitat`).

**19. Which constants enter H, and what provenance tier do they carry?**

- Citation: `mal-core/config/model_constants.yaml:42-45`
  (`urban.beta_urban`, `urban.rain_pools_built_damage`),
  `mal-core/src/mal_core/habitat/potential.py:44-49` (the two constants read
  from `CONFIG`), `mal-core/src/mal_core/habitat/README.md:1-12` (the
  "single source of shared model constants" rule), `tools/check_no_constants.sh`
  (the anti-hardcode guard).
- Answer: `beta_urban` and `rain_pools_built_damage` come from the shared
  constants file and are the same numbers the C++ engine uses
  (`mal-core/src/mal_core/abm/include/mal_abm_fast/habitat_availability.hpp:66-84`).
  Neither carries a documented measurement or a literature anchor — they are
  engineering priors / model definitions and the document must say so on
  their face (S5).

**20. Where is the species affinity w[s,g] defined, and what are the six
habitat types and their temporal classes?**

- Citation: `mal-core/config/model_constants.yaml:12-21`
  (`habitat_types.types` and the `dynamics` map: three `persistent`, three
  `pluvial`), `:63-126` (the per-species `weights` rows),
  `mal-core/src/mal_core/habitat/config.py:114-135` (`habitat_names`,
  `dynamics_map`, `persistent_names`, `pluvial_names`),
  `mal-core/src/mal_core/config_validation.py:410-424` (every weight row's
  keys must equal the frozen type list, and `wetland_pluvial` is forced to
  `0.00`).
- Answer: the six types and their dynamics are frozen in the constants
  file, and every species row lists an affinity per type summing to 1.
  `wetland_pluvial` carries weight `0.00` in every row, and the validator
  *enforces* that, because the engine has no separate zone for it. The
  active row is `species.default_species` (`coluzzii`).

**21. Where are the two shared temporal responses A[i,k,t] computed?**

- Citation: `mal-core/src/mal_core/habitat/availability.py:1-30` (the two
  responses in prose), `:38-56` (`update_pluvial_state`:
  `z_dry = z·exp(−Δt/τ)`, `z = z_dry + (1 − z_dry)(1 − exp(−rain/rain_scale))`),
  `:59-77` (`warm_up_pluvial`),
  `mal-core/src/mal_core/abm/include/mal_abm_fast/habitat_availability.hpp:98-113`
  (the C++ mirror `update_z_step`),
  `mal-core/src/mal_core/abm/src/coordinator.cpp:73-90` (the engine's
  warm-up over the NC bands preceding the simulation start),
  `mal-core/config/model_constants.yaml:28-32` (`pluvial.rain_scale_mm`,
  `dry_memory_days`, `delta_days`, `cold_start_z`), `:128-129`
  (`capacity.persistent_availability`).
- Answer: **not in ingest.** A has two members: `persistent` is the
  constant `capacity.persistent_availability` (1.0), and `pluvial` is the
  state z integrated day by day from the **rainfall channel that ingest
  writes**. The Python module `availability.py` is a reference mirror
  (its only production consumer is the calibration scorer
  `mal-core/src/mal_core/scoring/scorers/d19_pool_persistence.py`); the live
  integration is the C++ `update_z_step` inside the coordinator. The
  persistent response is deliberately insensitive to drought — that is a
  documented MVP limitation, not an accident.

**22. Where are S and K computed, and with which constant?**

- Citation: `mal-core/src/mal_core/abm/src/coordinator.cpp:139-148`
  (`S = species_accuracy(h, weights, z)`; `K_cell_ = k_habitat(S,
  row_area_km2)`),
  `mal-core/src/mal_core/abm/include/mal_abm_fast/habitat_availability.hpp:159-181`
  (`species_accuracy`: `Σ_g w[g]·H[g]·A[g]`, clipped to [0,1]),
  `:183-185` (`k_habitat = species.k_ref · cell_area_km2 · max(0, S)`),
  `mal-core/config/model_constants.yaml:47-52` (`species.k_ref = 50.0`),
  versus `mal-core/src/mal_core/habitat/capacity.py:30` and `:79-95`
  (the Python diagnostic path uses `K_REF_DIAG_PER_KM2 = 0.143 · 9.3 · 1e6`,
  a different constant, explicitly documented as *not* the engine's).
- Answer: **not in ingest.** S and K are computed by the ABM every day.
  The engine's `k_ref` is `species.k_ref` (50, in `ind·km⁻²·d⁻¹`), giving
  `K[i,t] = 50 · cell_area_km2[i] · S[i,t]` as an absolute per-cell
  capacity in individuals per day. The Python `capacity.py` mirror uses a
  *different* diagnostic constant (≈1.33 × 10⁶) for the scorer path; the two
  are distinct concepts and the document must not present them as one
  number. → part (c).

**23. Do the Python and C++ habitat models compute the same H, and the same
total?**

- Citation: `mal-core/src/mal_core/habitat/potential.py:71-79` (Python's six
  H values, including `wetland_pluvial = lc_wetland`) versus
  `mal-core/src/mal_core/abm/include/mal_abm_fast/habitat_availability.hpp:56-85`
  (C++: `JRC_PERSISTENT`, `URBAN_PERSISTENT`, `WETLAND`, `OPEN_PLUVIAL`,
  `CROP`, `FOREST = 0`), `:87-96` (`habitat_total_potential`),
  `mal-core/src/mal_core/abm/include/mal_abm_fast/zone_id.hpp:13-21` (the six
  C++ zones), `mal-core/src/mal_core/abm/src/config.cc:472-483`
  (`zone_id_of_habitat`: `wetland_pluvial` has **no** zone),
  `mal-core/src/mal_core/config_validation.py:417-424` (`wetland_pluvial`
  weight forced to 0).
- Answer: the two sides agree on the five living H values but not on the
  *set*: Python has six types including `wetland_pluvial`, while the engine
  has six zones including a permanently-zero `FOREST`. Consequently
  Python's `total_potential` adds `lc_wetland` a second time (as
  `wetland_pluvial`) while the engine's total does not, so
  `H_total` — the value that drives the ingest candidate census and the
  gpkg amplitude — is **not** the same quantity as the engine's
  `habitat_total_potential`. The difference is bounded by `lc_wetland`
  (≤ 1). S is unaffected, because the `wetland_pluvial` weight is zero
  everywhere. → part (c).

**24. What is the candidate-cell rule, and is it the same rule in ingest
and in the engine?**

- Citation: `mal-core/src/mal_core/ingest/daily_nc.py:76`
  (`HABITAT_CANDIDATE_MIN = ingest.candidate_min_ingest`),
  `:376-387` (the census `h_total > HABITAT_CANDIDATE_MIN`, and a
  `RuntimeError` when the census is empty) versus
  `mal-core/src/mal_core/ingest/env.py:70` (the gpkg keeps cells with
  `h_total > 0.0`), versus
  `mal-core/src/mal_core/abm/src/habitat_engine.cpp:214-219` (the engine
  drops patches with `potential < habitat_candidate_min_engine`) and
  `mal-core/src/mal_core/abm/src/coordinator.cpp:167-175` (the engine also
  adds every cell whose own total passes `candidate_min_engine`).
- Answer: **three different floors** — `1e-6` for the ingest census, `0.0`
  for the gpkg membership test, and `habitat.candidate_min_engine`
  (`0.01`) for the engine's own candidate union. The constants file states
  that the ingest floor and the engine floor have *different roles* and are
  deliberately not mirrors
  (`mal-core/config/model_constants.yaml:151-153`). The document must
  state all three and their distinct roles.

**25. What is written into the habitat GeoPackage, field by field?**

- Citation: `mal-core/src/mal_core/ingest/env.py:87-97` (the columns:
  `hab_type`, `dynamics`, `habitat_potential`, `row`, `col`, `aoi_slug`,
  plus one `hab_<type>` column per habitat type),
  `:81-86` (`hab_type` is the **argmax** of the six H values),
  `:69-73` (the point geometry: the cell centre, in the AOI CRS),
  `:99-105` (the GeoPackage write), `mal-core/src/mal_core/ingest/env.py:55-60`
  (the docstring: no `twi_value`, no `urban_capacity_factor`).
- Answer: one Point feature per candidate cell, positioned at the cell
  centre, in the AOI's CRS; `hab_type` is the dominant habitat type and
  `dynamics` its temporal class (`persistent` / `pluvial`); `habitat_potential`
  is the clipped total H; `row`/`col` are the cell identity the engine
  indexes by. The `hab_<type>` columns carry the six per-type H values.
  Verified against the real artefact (`data/ghana/ghana_habitat_patches.gpkg`):
  382 127 Point features on the 779 × 551 Ghana grid — 89 % of the cells —
  with `hab_type` distributed as `open_pluvial` 326 608, `urban_persistent`
  26 696, `surface_persistent` 15 069, `crop_pluvial` 13 316,
  `wetland_persistent` 438, and `dynamics` split 339 924 `pluvial` /
  42 203 `persistent`. `habitat_potential` ranges 3 × 10⁻⁶ … 1.0 with
  median 0.725. The count matches the `n_candidate_cells` attribute of the
  env NC (382 127), so the census and the gpkg agree in this run. The
  dominance of `open_pluvial` is a direct consequence of the DW mapping:
  `lc_open_plus_water` includes the `water` class, so nearly every
  non-ocean cell scores some open-pluvial potential.

**26. Which columns of the GeoPackage does the engine actually read, and
is the GeoPackage versioned?**

- Citation: `mal-core/src/mal_core/abm/src/habitat_engine.cpp:167-176`
  (fields resolved: `hab_type`, `habitat_potential`, `dynamics`, `row`,
  `col`), `:186-226` (the read loop: `hab_type` is accepted but **not used
  as a filter**; `potential` is clamped and floored),
  `mal-core/src/mal_core/abm/src/wire.hpp:203-217` (`HabitatPatch`: the
  per-type H features are "carried at the coordinator level … not here"),
  versus `mal-core/src/mal_core/ingest/env.py:56-60` (the claim that "the
  C++ gpkg parser requires the H columns"), and
  `mal-core/src/mal_core/ingest/env.py:99-105` (no metadata is written to
  the file).
- Answer: the engine reads `row`, `col`, `habitat_potential` and, for
  diagnostics, `hab_type`/`dynamics`; it does **not** read the `hab_<type>`
  columns, because it recomputes H from the env NC statics
  (`mal-core/src/mal_core/abm/src/climate.cpp:193-215`,
  `habitat_availability.hpp:56-85`). The GeoPackage carries **no
  `contract_version` and no generator version** — verified on the real
  artefact: `data/ghana/ghana_habitat_patches.gpkg` has no
  `gpkg_metadata` table at all, and `gpkg_contents` carries only the layer
  name, type and identifier. Only the env NC is versioned. → part (c).

**27. What are the type and the version of the `dynamics` column, and does
the engine's reader agree with it?**

- Citation: `mal-core/src/mal_core/ingest/env.py:88-90` (`dynamics` is
  written as the **string** `persistent` / `pluvial`) versus
  `mal-core/src/mal_core/abm/src/habitat_engine.cpp:220` (the engine reads
  it with `GetIntField`, an integer accessor) and `:88-100` (`GetIntField` /
  `GetDoubleField` on a string field).
- Answer: the writer produces a string column and the reader expects an
  integer; `OGR_F_GetFieldAsInteger` on a string field yields 0, so the
  engine's `dynamics` flag is 0 ("persistent") for every patch, including
  the pluvial ones. Verified on the real artefact: geopandas reports the
  column dtype as `str` in `data/ghana/ghana_habitat_patches.gpkg`. The
  field is documented as diagnostic only, so the consequence is a wrong
  diagnostic, not a wrong simulation — but the document must not describe
  the field as if it round-tripped. → part (c).

### The env NetCDF contract

**28. What exactly is the env NetCDF — dimensions, variables, attributes,
encoding?**

- Citation: `mal-core/src/mal_core/ingest/daily_nc.py:404-441` (the
  dataset: `rainfall(time,y,x)`, `air_temp_c(time,y,x)`, and the five
  statics `(y,x)`), `:443-457` (the optional `land_frac` and
  `salinity_ppt`), `:433-440` (attributes: `Conventions: CF-1.8`, `title`,
  `aoi_slug`, `scale: regional`, `contract_version`, `generator_version`,
  `n_candidate_cells`), `:459-464` (encoding: float32, zlib, compression
  level from constants), `:498-503` (the `variables` list returned to the
  caller).
- Answer: a CF-1.8 NetCDF with two daily channels and five static planes,
  float32, compressed. The statics are 2-D and are never broadcast onto the
  time axis; rain and temperature never enter the static planes. Verified
  on the real artefact `data/ghana/ghana_regional_2024_2024_env.nc`:
  `rainfall` and `air_temp_c` are `(366, 779, 551)` float32, the five
  statics are `(779, 551)` float32, the attributes are exactly
  `{Conventions: CF-1.8, title, aoi_slug, scale: regional,
  contract_version: 3.0, generator_version: proxy-habitat-v1-0.1.0,
  n_candidate_cells: 382127}`. The file carries **no** `land_frac` and no
  `salinity_ppt` plane — the two optional channels were absent for this
  run even though the manifest declares the `coastline_land_mask` input
  (so the open-sea filter ran, but the display basemap did not reach the
  NC), and no SMAP salinity was registered.

**29. What is the env NC's contract version, and where does it come from?**

- Citation: `mal-core/src/mal_core/ingest/daily_nc.py:53`
  (`_ENV_NC = CONFIG["contracts"]["env_nc"]`),
  `mal-core/config/model_constants.yaml:8-10` (`contracts.env_nc: "3.0"`,
  `contracts.cogs_state: "4.0"`), `mal-core/src/mal_core/ingest/daily_nc.py:438`
  (the attribute), `:524` (the value returned in the build result),
  `mal-core/src/mal_core/config_validation.py:368-373` (contract values must
  match `mayor.menor`).
- Answer: `contracts.env_nc = "3.0"`, generated, never typed. The state
  contract (`4.0`) is separate and belongs to the ABM stage, not to ingest.
  The env-NC and gpkg versions are independent of each other.

**30. Is the generator version generated or hard-coded?**

- Citation: `mal-core/src/mal_core/ingest/daily_nc.py:439`
  (`"generator_version": "proxy-habitat-v1-0.1.0"` — a literal in code) and
  `mal-core/config/model_constants.yaml` (no such key).
- Answer: it is a literal string in the builder, not a constants-file key.
  The document must either generate it from a new constants key or state it
  as a code literal with its citation — it cannot be emitted through the
  normal `\mskey` mechanism today. → part (c).

**31. Does the env NC have a NoData convention, and what is the sentinel?**

- Citation: `mal-core/src/mal_core/ingest/daily_nc.py:55`
  (`NODATA_SENTINEL = ingest.nodata_sentinel`), `:459-464` (the encoding
  sets dtype and compression but no `_FillValue`),
  `mal-core/config/model_constants.yaml:137-138`, `:160`
  (`nc_compression_level`).
- Answer: the sentinel is `-9999.0` and it is the pipeline-wide NoData
  value, but the env NC does **not** write an explicit `_FillValue`;
  xarray's float32 default (NaN) is what lands in the file. The sentinel is
  used during the build (rainfall NoData detection) rather than stored.

**32. What time span does the env NC cover, and how is the retention rule
justified?**

- Citation: `mal-core/src/mal_core/ingest/daily_nc.py:1-40` (the retention
  paragraph: the whole available daily series is written, because the days
  before the simulation start are the causal warm-up window the C++
  coordinator integrates z over),
  `:465-466` (the file name carries the first and last year of the
  rainfall axis), `:203` (`n_days` from the rainfall file).
- Answer: the whole daily series of the rainfall input, multi-year, named
  `<aoi>_regional_<y0>_<y1>_env.nc` with the years inferred from the
  rainfall axis. The `scale` in the name and in the attributes is hard-coded
  `regional`.

### Hosts, buildings and mobility

**33. What goes into the host-density grid, and from which providers?**

- Citation: `mal-core/src/mal_core/ingest/hosts.py:73-107` (WorldPop
  population, sum-preserving aggregation; GLW4 livestock for cattle,
  goats, sheep, pigs, chickens), `:110-136` (GHS-SMOD urban class with the
  reclassification `30→30`, `20–29→50`, `0–19→20`), `:138-159` (Overture
  building footprint fraction), `:166-182` (the wildlife host proxy),
  `:186-212` (the NetCDF and its companion JSON manifest).
- Answer: nine 2-D variables on the same AOI grid — `human`, `cattle`,
  `goats`, `sheep`, `pigs`, `chickens`, `urban_class` (int32: 30 urban /
  50 rural / 20 water), `building_fraction`, `wildlife_host_proxy` — plus a
  `host_manifest.json` with per-variable statistics and the grid spec.

**34. What are the aggregation rules for the host layers, and what is lost
in them?**

- Citation: `mal-commonlib/src/mal_commonlib/data/host_utils.py:33-80`
  (`aggregate_to_grid`: `Resampling.sum` for counts, `Resampling.nearest`
  for categorical), `mal-core/src/mal_core/ingest/hosts.py:75-88`
  (population: sum), `:92-105` (livestock: sum), `:112-120` (urban class:
  nearest), `:147-155` (building fraction: sum), `:170-178` (wildlife proxy:
  nearest), `mal-commonlib/src/mal_commonlib/data/loaders/glw.py:224-227`
  (GLW4 is a **density** in heads/km², so a "sum" aggregation of a density
  is a sum of densities, not a head count),
  `mal-commonlib/src/mal_commonlib/data/loaders/buildings.py:187-189`
  (the building fraction is 1.0 in any cell containing at least one
  footprint centroid), `mal-core/src/mal_core/ingest/hosts.py:122-128` (the
  GHS-SMOD reclassification), `mal-commonlib/src/mal_commonlib/data/loaders/ghsl.py:76-80`
  (the class-code comment), against the product's own definition
  (`GHSL_Data_Package_2023.pdf` §2.6.2, L2 classes: 30 urban centre,
  23 dense urban cluster, 22 semi-dense urban cluster, 21 suburban /
  per-urban, 13 rural cluster, 12 low-density rural, 11 very-low-density
  rural, 10 water; and the product's own `.clr` colour map, which lists
  exactly 10, 11, 12, 13, 21, 22, 23, 30).
- Answer: population is count-preserving; the urban class and the wildlife
  proxy are categorical and use nearest; the livestock layer is aggregated
  by *summing a density*, so the resulting per-cell value is not a head
  count; the building "fraction" is a centroid-presence indicator, not an
  area fraction. These are distinctions the document must make, because the
  engine consumes the numbers as counts
  (`mal-core/src/mal_core/abm/src/host_landscape.cpp:230-262`).

  **The urban-class reclassification is wrong and the document must say so.**
  `hosts.py:122-128` reclassifies `30 → 30 (urban)`, `20–29 → 50 (rural)`,
  `0–19 → 20 (water)`. The product's L2 scheme (PDF §2.6.2, confirmed by
  the shipped `.clr` colour map) is `30/23/22/21 = urban`,
  `13/12/11 = rural`, `10 = water`. The two disagree on **every class
  except 30**: the three urban-cluster classes (21, 22, 23) are mapped to
  *rural*, and the three rural classes (11, 12, 13) are mapped to *water*.
  The loader's own comment (`ghsl.py:76-80`, "20–29: rural,
  30: urban centres") encodes the same error. Measured on the real AOI
  (raw `load_ghsl_urban_class` output vs the stored
  `data/ghana/ghana_host_static.nc`): raw classes are 11 (299 511 cells),
  10 (57 490), 12 (51 101), 13 (7 457), 21 (6 850), 30 (3 803), 23 (1 990),
  22 (594), 0 (433) — and the stored `urban_class` plane is 415 992 × 20,
  9 434 × 50, 3 803 × 30, i.e. every rural cell became "water" and every
  urban-cluster cell became "rural".

  **Mechanistic consequence** (the engine reads the stored plane, not the
  raw codes): `urban_class_to_indoor_fraction`
  (`mal-core/src/mal_core/abm/src/host_landscape.cpp:111-122`) treats any
  value ≤ 40 as **urban** and ≥ 40 as **rural**. So all 415 992 "water"
  cells — which are, per the product, *rural* land — receive
  `indoor_fraction_urban = 0.72` and `urbanicity = 1.0`, while the 9 434
  genuinely-urban-cluster cells receive `indoor_fraction_rural = 0.30` and
  `urbanicity = 0.0`. The urban/rural signal is **inverted** for 97 % of
  the grid: 32.9 % of Ghana's population (10.5 M of 32.0 M) is labelled
  urban-endophilic, and 24.3 % (7.8 M, the peri-urban belt) is labelled
  rural. The consequence reaches the transmission loop:
  `host_seeking.cpp:43-50` and `coordinator.cpp:276-280` multiply the
  biting rate by `1 + indoor_fraction × (endophilic_ratio − 1)` and by
  `1 + urbanicity_add × urbanicity`, so the per-cell host-seeking
  multiplier is systematically wrong over most of the AOI.
  → part (c).

**35. What are the fallback values when a host layer fails, and are they
declared?**

- Citation: `mal-core/src/mal_core/ingest/hosts.py:133-136` (GHSL failure
  → all cells `urban_class = 50`), `:156-159` (buildings failure →
  `0.6` if urban else `0.1`), `:180-182` (wildlife failure → constant
  `0.3`).
- Answer: three silent-ish degradations, each announced on stderr and each
  substituting a constant for a real layer. The constants `0.6`, `0.1` and
  `0.3` are literals in the module, not constants-file keys.

**36. How is the mobility operator built, and what are its parameters?**

- Citation: `mal-core/src/mal_core/ingest/mobility.py:37-48` (the
  signature and its defaults: `cell_size_km=1.0`, `beta_day=0.05`,
  `beta_night=0.5`, `beta_livestock=0.1`, `max_distance_km=50.0`,
  `sparsity_threshold=5e-4`), `:84-102` (one matrix built and written at a
  time, to bound memory), `:104-117` (day, night and livestock; an
  identity matrix if there is no livestock), `mal-commonlib/src/mal_commonlib/data/mobility.py:21-60`
  (the gravity model `P(i→j) ∝ H(j)·exp(−β·d(i,j))`, row-normalised,
  sparsified and renormalised), `:161-180` (the CSR binary layout).
- Answer: a row-stochastic gravity model on the same grid: human
  attractiveness = population, livestock attractiveness = the sum of the
  five livestock layers; three CSR operators (day, night, livestock) with
  three different friction parameters and a 50 km hard cutoff. The
  parameters are **literals in the module's signature**, not constants-file
  keys, so the document must generate or cite them explicitly and assign
  them a provenance tier. Verified on the real manifest
  (`data/ghana/mobility_manifest.json`): `n_cells` 429 229, grid 779 × 551,
  `cell_size_km` 1.0, `beta_day` 0.05, `beta_night` 0.5,
  `beta_livestock` 0.1, `max_distance_km` 50.0,
  `sparsity_threshold` 5 × 10⁻⁴, `human_total` 32 048 206,
  `livestock_total` 150 902 080, with 96.2 M / 21.9 M / 197.7 M non-zeros
  in the day / night / livestock operators — the sparsity threshold keeps
  22 % of the day matrix and 5 % of the night matrix, so the "operator"
  is a sparse transport graph, not a dense matrix.

**37. Where do the human and livestock attractiveness values come from,
and what happens to the NoData sentinel?**

- Citation: `mal-core/src/mal_core/ingest/mobility.py:25-34` (loading the
  host NetCDF), `:76-88` (`NODATA_SENTINEL` → 0 for the human layer and
  for each livestock layer), `:88`/`:108-117` (the livestock total decides
  whether the gravity model or the identity fallback is used).
- Answer: they are read back out of the host NetCDF that the previous step
  wrote, with the `-9999` sentinel mapped to zero. When the AOI has no
  livestock at all, the livestock operator degenerates to the identity.

### Manifest integration

**38. How does the stage write to the manifest, and what does it record?**

- Citation: `mal-core/src/mal_core/ingest/_shared.py:7-33`
  (`register_dataset` → `manifest.update_dataset`),
  `mal-core/src/mal_core/download/manifest.py:116-186` (the entry fields:
  `type`, `format`, `required_for_abm`, `files`, and the optional
  `variables`, `period`, `license`, `attribution`; `expected_files` is
  rebuilt as the union of all declared files),
  `mal-core/src/mal_core/ingest/env.py:147-162` and `:174-187` (the two env
  registrations), `mal-core/src/mal_core/ingest/hosts.py:219-236`,
  `mal-core/src/mal_core/ingest/mobility.py:141-161`.
- Answer: eight registrations, each adding or updating one manifest entry
  with a file name, a format, the ABM-required flag, the variable list and
  a `+`-joined compound licence id with the literal attribution line.
  `expected_files` is recomputed from scratch on every write.

**39. Under which year key are the env and habitat artefacts registered,
and what does that imply for a multi-year NetCDF?**

- Citation: `mal-core/src/mal_core/ingest/env.py:148` and `:175`
  (both register with the `year` argument),
  `mal-core/src/mal_core/download/manifest.py:174-177` (`files[str(year)]`
  when a year is given, `files[dataset_name]` otherwise),
  `mal-core/src/mal_core/ingest/daily_nc.py:465-466` (the file covers
  `<y0>–<y1>`), `mal-core/src/mal_core/abm/wrapper.py:137-146` (the ABM
  resolves `env` **with** a year and `habitat` **without** one).
- Answer: the env NC, which physically spans several years, is registered
  under a single year key (the `--year` the CLI was given). Resolving it
  for a different year therefore fails, even though the file contains that
  year's data. The habitat gpkg is registered under a year key too, but is
  resolved without one, so the fallback (first declared file) applies.
  → part (c).

**40. Does the manifest's declared variable list match what the files
actually contain?**

- Citation: `mal-core/src/mal_core/ingest/env.py:183-185` (the habitat
  registration lists `hab_{g}` for `g` in the **five feature planes**:
  `hab_jrc_persistent`, `hab_lc_built`, …) versus
  `mal-core/src/mal_core/ingest/env.py:96-97` (the file actually carries
  `hab_<habitat type>`: `hab_surface_persistent`, `hab_wetland_persistent`,
  `hab_urban_persistent`, `hab_wetland_pluvial`, `hab_open_pluvial`,
  `hab_crop_pluvial`), and `mal-core/src/mal_core/ingest/env.py:87-90` (the
  `dynamics` column, which the registration does not list).
- Answer: it does not match, and the mismatch is **visible in the real
  manifest**: `data/ghana/manifest.json` lists the habitat entry's
  variables as `["hab_type", "habitat_potential", "row", "col",
  "hab_jrc_persistent", "hab_lc_built", "hab_lc_wetland",
  "hab_lc_open_plus_water", "hab_lc_crop"]`, while the file it names
  (`data/ghana/ghana_habitat_patches.gpkg`, read with geopandas) carries
  `hab_surface_persistent`, `hab_wetland_persistent`, `hab_urban_persistent`,
  `hab_wetland_pluvial`, `hab_open_pluvial`, `hab_crop_pluvial` — and also
  `dynamics` and `aoi_slug`, which the manifest omits. The manifest
  advertises five `hab_*` names that are not in the file and omits the six
  that are. The env NC's registration, by contrast, is derived from the
  built file's own variable list (`daily_nc.py:498-503`), and the real
  manifest's env entry matches its file exactly. → part (c).

**41. Where does the CLI actually put the files, and where does it put
the manifest?**

- Citation: `mal-core/src/mal_core/cli.py:220-222` (env: `output_dir` is
  used as the *input* directory too, and `data_root = chosen_data_dir.parent`),
  `:224-226` (hosts: `output_dir`, default `runs/ingest`),
  `:227-237` (mobility: output hard-coded to `data/<aoi>`, input looked up
  in `output_dir` then `data/<aoi>`), versus
  `mal-core/src/mal_core/ingest/hosts.py:219-236` and
  `mal-core/src/mal_core/ingest/mobility.py:141-161` (both register with
  the **default** data root, `data/`), and
  `mal-core/src/mal_core/download/manifest.py:149-151` (the manifest path
  is `data_root/<aoi>/manifest.json`).
- Answer: the CLI's defaults are mutually inconsistent, and the failure is
  observable, not theoretical. Running
  `malariasim ingest --aoi ghana --what env` with the default
  `--output-dir runs/ingest` fails with
  `FileNotFoundError: required input 'chirps_rainfall_daily' not found in
  manifest for AOI 'ghana' (runs/ingest)` — because the env builder reads
  the manifest from **its own output directory** (`cli.py:221` passes
  `output_dir` as the builder's `data_dir`, and `daily_nc.py:186-190`
  resolves against `data_dir/manifest.json` via
  `catalog.load_local_manifest`), and `runs/ingest/manifest.json` does not
  exist. Three separate inconsistencies follow from the defaults:
  (i) the env NetCDF is written to `runs/ingest/` while its manifest entry
  is written to `runs/ghana/manifest.json` (the parent of the output
  directory, `cli.py:222` → `env.py:161` → `manifest.py:149-151`);
  (ii) the host grid is written to `runs/ingest/` but registered in
  `data/ghana/manifest.json`, because `build_host_dataset` registers
  without a `data_root` and therefore uses the default `DATA_ROOT`
  (`hosts.py:219-236`); (iii) the mobility operators are written to
  `data/<aoi>/` (`cli.py:233`). A completed run therefore leaves the
  manifest declaring files that are not where the manifest says they are,
  which `validate_completeness` reports as missing. → part (c).

### The seam with the ABM

**42. What does the ABM take from ingest, and how does it resolve it?**

- Citation: `mal-core/src/mal_core/abm/wrapper.py:112-121`
  (`validate_completeness` first), `:137-165` (the seven resolutions:
  `env` with a year, `habitat`, `host_static`, `wind`, `mobility_day`,
  `mobility_night`, `livestock_mobility`), `:183-195` and `:210-222` (the
  flags the wrapper hands the binary: `env`, `habitat`, `year`, `month`,
  `days`, `seed`, `output`, and, only when resolved, `hosts`, the three
  mobility flags and `wind_field`), `:166-178` (only `env` and `habitat`
  are hard errors).
- Answer: the engine takes the env NetCDF (mandatory), the habitat
  GeoPackage (mandatory), the host grid, the wind field (from the download
  stage, not from ingest) and the three mobility operators (all optional at
  the flag level). The ABM first requires that every file *declared* in the
  manifest exists.

**43. How does the engine read the env NetCDF, and what does it do with
each plane?**

- Citation: `mal-core/src/mal_core/abm/src/env_reader.cpp:204-271`
  (`rainfall`, `air_temp_c`, the five statics, optional `land_frac`,
  optional `salinity_ppt`), `mal-core/src/mal_core/abm/src/climate.cpp:160-215`
  (the load: NaN temperature imputation at load time, the five static
  planes bound only if their size matches the grid), `:196-215` (a missing
  or mis-shaped static plane is treated as zero, with a printed note),
  `mal-core/src/mal_core/abm/src/coordinator.cpp:66-70` (the engine's own
  complaint when the static planes are absent: "check the env NC
  contract_version (v3.0 expected)").
- Answer: the engine reads the daily channels and the five static planes;
  `land_frac` is a display basemap and is explicitly **not** part of the
  habitat feature bundle; `salinity_ppt` is optional and its absence means
  "no salinity data", which the engine answers with a configured freshwater
  anchor. A static plane of the wrong size is silently treated as zero.

**44. How does the engine build its candidate patch set from the GeoPackage
and the statics?**

- Citation: `mal-core/src/mal_core/abm/src/coordinator.cpp:156-175`
  (the union: the gpkg patches plus every cell whose recomputed total
  passes `candidate_min_engine`), `:200-224` (the per-patch state:
  `habitat_avail = species_accuracy(...)`, `activated` when it passes
  `activation_min_engine`, `k_habitat`, the salinity hard gate),
  `mal-core/src/mal_core/abm/src/habitat_engine.cpp:208-219` (the gpkg
  patches are floored by `candidate_min_engine` too).
- Answer: the engine's patch set is the **union** of the ingest GeoPackage
  and its own recomputed candidate cells, so the GeoPackage is a
  conservative starting set rather than the authoritative one. The daily
  activation of a patch is decided by S against
  `habitat.activation_min_engine`, and a patch whose salinity exceeds the
  species' tolerance is deactivated regardless of S.

**45. What does ingest *not* pass to the engine, and what does the engine
recompute itself?**

- Citation: `mal-core/src/mal_core/abm/src/climate.cpp:200-215` (the statics
  are re-bound from the NC), `mal-core/src/mal_core/abm/include/mal_abm_fast/habitat_availability.hpp:56-85`
  (H is recomputed in C++ from the same five planes), `:98-113` (z),
  `:159-194` (S and K), `mal-core/src/mal_core/ingest/env.py:56-60` (the
  claim that the gpkg's H columns are needed by the parser).
- Answer: the engine recomputes H, A, S and K from the env NetCDF every
  day; it uses the GeoPackage for cell identity, candidate membership and
  the amplitude. Consequently the Python-side H in the GeoPackage and the
  C++-side H are two implementations of the same idea, and the ingest
  census and the engine's candidate floor are not the same filter. → part
  (c).

### Declaration of absences

**46. What does the stage explicitly *not* do?**

- Citation: `mal-core/src/mal_core/ingest/daily_nc.py:36-40` (the removal
  note: `water_frac`, `ndvi`, `twi`, `catchment_ratio`,
  `k_capacity_mult`, `permanent_water_mask`, `wetland_mask`, the OpenM12
  enrichment path are all gone), `mal-core/src/mal_core/habitat/constants.py:9-16`
  (the tombstone: the module raises for every name),
  `mal-core/src/mal_core/ingest/daily_nc.py:376-377` ("pure statics, no DEM,
  no NDVI thresholds"), `mal-core/src/mal_core/ingest/env.py:56-60`
  (no `twi_value`, no `urban_capacity_factor` columns).
- Answer: there is **no** DEM, no TWI, no terrain criterion of any kind;
  no per-cell millimetre water balance; no annual temperature suitability
  surface; no NDVI channel; no alpha/theta weighting matrix; no species
  selection at ingest time (the engine applies one species row); no
  per-cell capacity computation at ingest (K is the engine's); no
  climatology or trend analysis; no interpolation of gaps other than the
  rainfall donor fill.

**47. What is the order of operations of the env build, and what are the
consequences of that order?**

- Citation: `mal-core/src/mal_core/ingest/daily_nc.py:197-499` (rainfall →
  rainfall NoData fill → coastline/open-sea → air temperature and its
  re-indexing → static planes → open-sea zeroing → coastline census →
  candidate census → optional salinity → dataset assembly → georeferencing →
  write), `mal-core/src/mal_core/ingest/env.py:143-173` (the NC is written
  **first**, then the statics are read back out of it and the GeoPackage is
  derived from them).
- Answer: the order matters in three places. (i) The rainfall axis is
  established before the temperature is read, because the temperature is
  re-indexed onto it — hence the loud failure when it does not cover the
  axis. (ii) The open-sea mask is computed before the statics are zeroed,
  so the mask must exist; without the coastline artefact the filter is
  skipped with a warning rather than failing. (iii) The GeoPackage is
  derived from the env NC **after** it is written, by re-reading the static
  planes from it (`env.py:164-171`) — so the gpkg cannot disagree with the
  NC's statics, but the gpkg's candidate set is computed from the NC's
  already-filtered statics.

**48. Which numbers of the stage must be generated rather than typed, and
which are code literals?**

- Citation: `mal-core/config/model_constants.yaml:136-160` (the `ingest`
  block: the sentinel, the coastal band, the sea-water floor, the cell-size
  hint, the candidate floor, the fill-fraction threshold, the degree-step
  maximum, the compression level), `:42-45` (the urban constants),
  `:28-32` (pluvial), `:128-129` (capacity), versus the code literals:
  `mal-core/src/mal_core/ingest/daily_nc.py:439` (generator version),
  `mal-core/src/mal_core/ingest/hosts.py:141`/`:159`/`:182` (0.6, 0.1, 0.3),
  `mal-core/src/mal_core/ingest/mobility.py:42-47` (the six mobility
  parameters), `mal-core/src/mal_core/habitat/capacity.py:30`
  (`K_REF_DIAG_PER_KM2`).
- Answer: the constants-file keys are the generated ones (the existing
  `docs/concepts/generated/params-ingest.tex` already emits them); the
  generator version, the three host fallbacks, the six mobility parameters
  and the Python diagnostic K constant are **not** in the constants file and
  must either be cited as code literals or promoted to keys before the
  document can quote them.

---

## (b) Done-checklist

The ingest document is done when a reviewer who has never opened the code
can check each of the following against the cited file:

1. **The purpose is stated** with what the stage is *not* for (Q1), and the
   download/ingest boundary is stated honestly — including that the host
   path downloads (Q4).
2. **The three entry points and the `--what` switch are described**, and
   the eight artefact keys and their file names are listed (Q2, Q3).
3. **The spatial frame is stated**: the AOI record, the CRS, the nominal
   1 km resolution, the derived cell count, and — explicitly — where (H, W)
   comes from (the CHIRPS file for the NC, `aoi.cells_per_side()` for the
   GeoPackage) and how the two are reconciled (Q5, Q6).
4. **Every input is named with its provider, manifest key, native
   resolution, target resolution, units and reduction**, and what the
   reduction loses is stated (Q7).
5. **The cell-area formula is stated as an approximation** with its
   magnitude, in both the Python and the C++ mirror (Q8).
6. **The georeferencing of the env NC is described** — inherited
   coordinates, the conditional CF `lat`/`lon`/`crs` variables (Q9).
7. **The required/optional input table is complete** (four required, three
   optional), with the failure mode of each, and the dead `host_static`
   slot is declared (Q10, Q11).
8. **The two daily channels are described end to end**: preparation, units,
   the time-axis ownership, the coverage check, the open-sea treatment and
   the reason for the `0.0` rather than NaN sentinel (Q12, Q13).
9. **The open-sea rule is stated with its formula**, the coastal band is
   described as a distance query rather than a dilation, and the
   degradation when the coastline artefact is missing is declared (Q14, Q15).
   The document must also state whether the artefacts in `data/ghana/` were
   produced by the rule as described, and say so plainly when they were
   not (Q15-bis).
10. **The static assembly is described**, including the multi-year land
    cover average and the salinity broadcast (Q16, Q17).
11. **The habitat model is stated**: the five feature planes, the six H
    values with their formulas, the clip and the NaN rule, and the
    explicit statement that H is an **index**, not a measurement (Q18).
12. **Every constant carries a provenance tier**, and the constants-file
    keys are generated rather than typed (Q19, Q48).
13. **The six habitat types and their persistent/pluvial split are stated**,
    with the `wetland_pluvial` weight rule and the validator that enforces
    it (Q20).
14. **The two shared temporal responses are stated, with the explicit
    statement that they are computed by the ABM, not by ingest**, and that
    the persistent response is insensitive to drought by design (Q21).
15. **S and K are stated with their units, their formula and their
    constant**, and the distinction between the engine's `species.k_ref`
    and the Python diagnostic constant is made (Q22).
16. **The Python-vs-C++ H discrepancy is disclosed** (six types versus six
    zones, `wetland_pluvial` versus `FOREST`, and the resulting difference
    in `H_total`) — it is not hidden behind "the two are mirrors"
    (Q23).
17. **The three candidate floors are stated and distinguished**, with their
    distinct roles, and the *measured* candidate count of the real Ghana
    artefact is quoted alongside the rule that produced it (Q24, Q25).
18. **The GeoPackage is described field by field**, including what the
    engine does not read, the absence of any contract version on the file,
    and the string-versus-integer `dynamics` mismatch (Q25, Q26, Q27).
19. **The env NC contract is stated**: variables, dimensions, attributes,
    encoding, contract version (generated), and the retention rule with its
    warm-up justification (Q28, Q29, Q31, Q32).
20. **The host grid is described** with its nine variables, the
    per-layer aggregation rule, the count-versus-density and
    centroid-versus-area distinctions, and the three fallback constants
    (Q33, Q34, Q35).
21. **The mobility operators are described** with the gravity model, the
    three friction parameters, the cutoff, the sparsification, and the
    identity fallback (Q36, Q37).
22. **The manifest integration is described**: the eight registrations, the
    fields recorded, the licence and attribution convention, and the
    year-key consequence for the multi-year env NC (Q38, Q39).
23. **The mismatch between the declared variable list and the actual file
    content is disclosed** (Q40).
24. **The CLI's output and manifest locations are described as they
    actually are**, including the inconsistency (Q41).
25. **The seam with the ABM is described**: what is resolved, what is
    mandatory, what the engine recomputes, how the candidate union is
    formed, and how salinity gates breeding (Q42–Q45).
26. **The declaration of absences is present and explicit** — no DEM, no
    TWI, no mm balance, no NDVI, no theta matrix, no ingest-time capacity
    (Q46).
27. **The order of operations is given as pseudocode plus a table**, with
    the three places where the order changes the result (Q47).
28. **Every claim carries a file-and-line citation**, and no citation
    points at `docs/specs/` as authority.

---

## (c) Open questions

1. **The host/mobility path downloads, the env path does not.**
   `build_host_dataset` calls the provider loaders directly
   (`hosts.py:74`, `:92`, `:111`, `:146`, `:170`), so a "run ingest" on a
   machine with an empty cache fetches WorldPop, GLW4, GHSL, Overture and
   the wildlife proxy from the network. The env path is strictly
   manifest-resolved (`daily_nc.py:186-190`). Is the asymmetry intended, and
   should the host path also become manifest-only (its inputs are already
   downloaded and registered by the download stage)?
2. **Two different `H_total`s.** Python's `total_potential` sums six
   types including `wetland_pluvial = lc_wetland`
   (`potential.py:71-79`); the engine's `habitat_total_potential` sums six
   zones including a permanently-zero `FOREST`
   (`habitat_availability.hpp:56-96`). The ingest candidate census, the
   gpkg's `habitat_potential` amplitude and the engine's own candidate
   floor therefore use different quantities, differing by up to
   `lc_wetland`. Which is the intended definition of "total habitat
   potential"? The gpkg's amplitude is also written from the Python value
   while the engine's patch amplitude is the C++ value.
3. **The GeoPackage carries no version.** The env NC carries
   `contract_version` and `generator_version` attributes; the gpkg carries
   neither, and `docs/concepts/contracts.yaml` records the `habitat`
   artefact with no `version_from` key. A reader of the gpkg has no way to
   know which mapping produced it. Should a `contract_version` be stamped
   on the gpkg?
4. **The `dynamics` column type mismatch.** Written as the string
   `persistent`/`pluvial` (`env.py:88-90`), read as an integer
   (`habitat_engine.cpp:220`). The engine's per-patch dynamics flag is
   therefore always 0. The field is diagnostic only, so the simulation is
   unaffected — but the diagnostic is wrong.
5. **The manifest's habitat variable list does not match the file**
   (`env.py:183-185` versus `:87-97`). The names should be derived from the
   written columns, as the env NC's list already is
   (`daily_nc.py:498-503`).
6. **The CLI's output and manifest locations disagree**
   (`cli.py:220-237`), and the disagreement is observable: the documented
   invocation `malariasim ingest --aoi ghana --what env` raises
   `FileNotFoundError: required input 'chirps_rainfall_daily' not found in
   manifest for AOI 'ghana' (runs/ingest)` because the env builder reads
   the manifest from its own output directory. Beyond that: the env NC is
   written under `runs/ingest/` but registered in `runs/ghana/manifest.json`;
   the host grid is written under `runs/ingest/` but registered in
   `data/ghana/manifest.json`; the mobility operators go to `data/<aoi>/`.
   A completed run leaves a manifest whose declared files are not all where
   it says they are, which `validate_completeness` reports as missing.
7. **The env NetCDF is registered under a single year key** although it
   spans several years (`env.py:148`; `manifest.py:174-177`). The ABM
   resolves `env` *with* a year (`wrapper.py:137-140`), so a run for a year
   the ingest was not told about fails even though the data is present.
   Should the env artefact be registered per year, or registered with a
   `period`?
8. **`generator_version` is a code literal** (`daily_nc.py:439`), as are the
   three host fallback constants, the six mobility parameters and the
   Python diagnostic `K_REF_DIAG_PER_KM2`. Which of these should be
   promoted to `model_constants.yaml` so that the document can generate
   them?
9. **`species.k_ref = 50` and `K_REF_DIAG_PER_KM2 = 0.143·9.3·1e6` are two
   different K scales in the same codebase** (`model_constants.yaml:51`
   versus `capacity.py:30`). The Python one is documented as a scorer
   diagnostic and not the engine's, but the document will state one
   capacity formula; which is the one the reader should carry?
10. **The three candidate floors** (`1e-6` ingest census, `0.0` gpkg
    membership, `0.01` engine floor) are documented as having distinct
    roles, but nothing prevents the gpkg from carrying patches the engine
    immediately drops, or the ingest census from reporting a count the
    engine will not reproduce. Should the gpkg membership test use the
    engine's floor so the two counts agree?
11. **The open-sea filter degrades silently** when the coastline artefact
    is missing (`daily_nc.py:357-362`): a printed note, no error, and the
    statics keep their open-ocean cells. Given that the failure mode
    (thousands of mid-ocean breeding candidates) is exactly what the filter
    exists to prevent, should a missing coastline artefact be an error
    rather than a note?
12. **`ENV_INPUT_SLOTS` declares a `host_static` slot that the env builder
    never reads** (`daily_nc.py:96`). Dead dependency declaration, or a
    remnant of an intended env↔host coupling?
13. **The frame has two owners.** The env grid's shape comes from the
    rainfall file, the GeoPackage's from `aoi.cells_per_side()`, and the
    reconciliation is a shape assertion inside `_read_static`
    (`env.py:42-44`) that only fires on the gpkg path. Nothing checks that
    the CHIRPS file was built on *this* AOI's grid. Should the env builder
    assert the AOI shape directly?
14. **The cell-area approximation is off by roughly `1/cos(lat_centroid)`**
    (~1 % for Ghana) plus the `ceil` rounding. Is that acceptable as
    stated, or should the area be computed from the actual axis vectors?
15. **No download of the `wind` product from ingest.** The ABM consumes a
    wind field (`wrapper.py:149-152`) that the download stage provides
    directly; the ingest document should say so explicitly rather than
    leaving it as an unexplained gap in the chain.
16. **The checked-in Ghana artefacts predate the open-sea fix.** The env
    NC in `data/ghana/` has no `land_frac` plane, `ghana_land_mask.tif`
    holds only {0.0, 1.0} instead of a fraction, and the file dates are
    2026-10-18 against the fix's 2026-10-29 (`36bedbf`). Applying the
    current rule to the stored statics marks 45 674 cells as open sea, all
    of them currently candidates; masking them would take the candidate
    count from 382 127 to 336 453. Should the artefacts be rebuilt (and
    the `coastline_land_mask` entry re-downloaded through the current
    loader) before the conceptual document is written, or should the
    document describe the current code and flag the artefacts as stale?
17. **`data/ghana/ghana_land_mask.tif` is a binary mask but the manifest
    key is `coastline_land_mask`** and the loader now returns a
    fraction. Any consumer that reads the file directly (rather than
    through the loader) will assume binary semantics. Is the file's
    contract "binary land mask" or "land fraction", and does the manifest
    entry record which?
18. **The GHS-SMOD reclassification inverts the urban/rural signal.**
    `hosts.py:122-128` maps the product's L2 classes `30/23/22/21` (urban)
    and `13/12/11` (rural) and `10` (water) onto `30/50/20` with the urban
    and rural ranges swapped, and `ghsl.py:76-80` documents the same
    wrong scheme. The effect on the built artefact is that 415 992 of
    429 229 cells (97 %) are labelled 20, of which 358 069 are product-rural
    land, and the 9 434 genuine urban-cluster cells are labelled 50. Since
    the engine reads the *stored* plane and treats ≤ 40 as urban
    (`host_landscape.cpp:111-122`), the indoor-fraction and urbanicity
    modifiers are inverted over almost the whole AOI, which propagates into
    the biting rate (`host_seeking.cpp:43-50`, `coordinator.cpp:276-280`).
    The correction is a one-line remap, but it changes the urban/rural
    endophily of 32.9 % of the population and the classification of the
    peri-urban belt (24.3 %) — so it invalidates any run calibrated
    against the current host grid. Should the fix be applied before the
    conceptual document is written, and should the affected ABM runs be
    re-scored?
19. **The `urban_class` fallback constant is also affected.** The
    building-fraction fallback (`hosts.py:141`, `:159`) uses
    `urban_class == 30 → 0.6 else 0.1`, so it inherits the same
    inversion: with the current mapping, the "urban" default is applied
    only to the 3 803 true urban-centre cells. Is `urban_class == 30` the
    intended test, or should it be the product's urban-domain classes
    (`30/23/22/21`)?
20. **The wildlife proxy uses two different "water" definitions inside one
    product.** The habitat term is a Dynamic-World-class suitability sum
    whose `water` class scores 0.0 (`model_constants.yaml:162-176`, keyed by
    the DW class *name*), while the water term is
    `jrc_persistent` passed through `_water_presence`
    (`mal-commonlib/src/mal_commonlib/data/loaders/wildlife.py:208-220`),
    and the third term is remoteness from the Overture building fraction
    (`:222-235`), combined linearly with the `wildlife.weights` priors.
    So "water" means "not a DW water pixel" in one term and "JRC
    persistent surface water" in the other. Is that intentional, and does
    the document need to state which water surface the proxy actually
    responds to? (Note also that the loader's comments still say
    "WorldCover" in places — `wildlife.py:240-242` — while the product
    switched to Dynamic World on 2026-10-20.)
