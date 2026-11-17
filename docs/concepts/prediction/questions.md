# Question set — `prediction` conceptual document

This file is the question set for `docs/concepts/prediction/prediction.tex`, the
conceptual document of the sixth pipeline stage of MalariaSentinel. It was
written after reading the stage's material: the whole
`mal-core/src/mal_core/prediction/` package (`predictor.py`, `registry.py`,
`state_loader.py`, `env_loader.py`, `aggregator.py`, `aoi_resolver.py`),
the `predict` and `status` CLI commands in `mal-core/src/mal_core/cli.py`, the
FastAPI surface in `mal-core/src/mal_core/server.py`, the surrogate wrapper
`mal-core/src/mal_core/training/wrapper.py` and its trainer/dataset, the
upstream artefacts the stage consumes (the ABM state COG and its sidecar in
`mal-core/src/mal_core/abm/`, the transmission COG, and the ingest env
NetCDF), and the retired prediction specification (its audit trail is now
`docs/plans/in-process/spec-retirement-ledger.md`) — which was retired and was used **only as
material**: every claim below is cited to code, and where code and the
specification disagree the code wins (that specification's own drift table was
itself inaccurate in several rows). Questions are numbered; each carries at least
one `path:line` citation a reviewer can open. Where the code answers the
question unambiguously, an `Answer:` line records that answer so the drafter
can check the document against the code instead of re-deriving it. Questions
the code does **not** answer are marked **open** and repeated in part (c).

---

## Part (a) Question set

### A1. Purpose and negative purpose

**Q1. What question does the `prediction` stage exist to answer, and what
counts as it having answered it?**
Citation: `mal-core/src/mal_core/prediction/predictor.py:1-9` (docstring: load
model → load state + env → `model.predict` → write GeoTIFF → return path);
`mal-core/src/mal_core/cli.py:120-131` (CLI help text: "produce a classified
risk map").
Answer: the stage runs a trained surrogate over one AOI's state and
environment tensors and writes a multi-band GeoTIFF plus a JSON sidecar, and
returns the raster path (`predictor.py:150`).

**Q2. What is explicitly *not* the purpose of this stage?**
Citation: `mal-core/src/mal_core/prediction/predictor.py:66-76` (the function
signature exposes only model selection, AOI/scale/date, scenario, output and
rollout directories — no training, no ABM execution).
Answer: training is in `mal-core/src/mal_core/training/trainer.py:14-25`; the
ABM itself is a separate stage; the stage neither trains nor runs the ABM.

**Q3. Is the stage's output a measurement, a forecast, or an emulation?**
Citation: `mal-core/src/mal_core/training/model.py:1-6` ("Input: (state_t +
env) → Target: state_{t+1}"); `mal-core/src/mal_core/training/dataset.py:242-252`
(target is the *next* snapshot's bands).
Answer: it is a **one-step-ahead emulation of the ABM** learned from ABM
snapshots — a surrogate of the simulator, not an epidemiological measurement
and not an independent forecast. The document must say so plainly.

**Q4. What is the relationship between the stage's output and the ABM
contract it consumes?**
Citation: `mal-core/src/mal_core/abm/include/mal_abm_fast/wire.hpp:139-146`
(contract "4.0" comment: bands are raw per-cell adult counts, `K_MAX`
retired); `mal-core/src/mal_core/prediction/predictor.py:144` (prediction's own
sidecar says `contract_version: "1.1"`).
Answer: two different, independent contracts; the prediction output is *not*
version-gated on the state contract.

**Q5. Which downstream consumers read what the stage writes?**
Citation: `mal-core/src/mal_core/prediction/predictor.py:153-168`
(`get_latest_prediction`, `get_prediction_metadata`);
`mal-core/src/mal_core/server.py:88-104` (`GET /aoi/{name}/risk`,
`GET /aoi/{name}/status`); `mal-core/src/mal_core/cli.py:866-877` (`status`
command).
Answer: within the repository the only consumers are the sidecar readers
(the `status` CLI command and the FastAPI status/risk endpoints). No map,
dashboard or intervention-planning consumer exists in the tree — the claim in
the retired prediction specification about "maps, dashboards, intervention
planning" is aspirational, not implemented.

### A2. Inputs: what the stage consumes

**Q6. What ABM artefact does the stage consume, and where is that consumption
first described in the document?**
Citation: `mal-core/src/mal_core/prediction/state_loader.py:19-36` (the
loader returns a `(C, H, W)` state tensor);
`mal-core/src/mal_core/prediction/predictor.py:54` (the predictor is the
caller, `include_transmission=True`).
Answer: the ABM **state COG** (per-day snapshots and/or the final state
raster) read from the runs tree. The document must name the consumed bands
and the contract version *at the point where the consumption is first
described*, not only in an appendix.

**Q7. Which bands does the consumed state COG carry, and what do they mean
numerically?**
Citation: `mal-core/src/mal_core/abm/include/mal_abm_fast/wire.hpp:124-133`
(`STATE_BAND_NAMES[2] = {"adult_patch_count", "adult_cell_count"}`; comment:
both are **raw per-cell adult counts**, band 1 = adults associated with the
cell via their patch, band 2 = adults at their current position);
`mal-core/src/mal_core/abm/include/mal_abm_fast/output_contract.hpp:36-56`
(`StateCogMetadata`, `band_names`, `contract_version`, `nodata`, `h`, `w`).
Answer: two bands, both raw counts of individuals (contract 4.0). Not
densities, not normalised, not bounded to [0, 1].

**Q8. How are the state bands read — positionally or by name — and is the
sidecar consulted at all?**
Citation: `mal-core/src/mal_core/prediction/state_loader.py:82-92` (the whole
raster is read; `nodata` cells are set to 0.0; the band *count* drives the
output channel count).
Answer: **positionally**; the sidecar JSON is never opened, so nothing
validates `contract_version`, `band_names` or `nodata` against the file's
declared metadata. A state COG from an older contract would be consumed
silently. This must be stated as an absence, not glossed.

**Q9. Which environment tensor does the stage consume, and which channels?**
Citation: `mal-core/src/mal_core/prediction/env_loader.py:17-18`
(`ENV_CHANNELS = 4`, `ENV_CHANNEL_ORDER = ["rainfall", "air_temp_c",
"jrc_persistent", "lc_wetland"]`).
Answer: four channels in that order.

**Q10. Where does the environment tensor come from, in what precedence, and
what is the fallback chain?**
Citation: `mal-core/src/mal_core/prediction/env_loader.py:36-49` (explicit
path → `data/<aoi>/*_env.nc` → `data/<aoi>/*.nc` → `*_env*.tif` → `*.tif`);
`mal-core/src/mal_core/prediction/env_loader.py:120-149` (`runs/env_stack.npz`
fallback, with a hardcoded default bounds `(-3.0, 4.0, 2.0, 12.0)`);
`mal-core/src/mal_core/prediction/env_loader.py:151` (all-zeros fallback).
Answer: NetCDF in `data/<aoi>/` first, then GeoTIFF, then the legacy
`runs/env_stack.npz`, then zeros. The NetCDF branch selects only variables
present in the file and takes the **first** four in `ENV_CHANNEL_ORDER`
(`env_loader.py:56-63`), zero-filling any missing ones.

**Q11. Which upstream stage produces the env NetCDF and under which variable
names?**
Citation: `mal-core/src/mal_core/ingest/daily_nc.py:404-435` (dataset
variables `rainfall`, `air_temp_c` (time series) and the statics
`jrc_persistent`, `lc_built`, `lc_wetland`, `lc_open_plus_water`, `lc_crop`);
`mal-core/src/mal_core/ingest/daily_nc.py:466` (output name
`<aoi>_regional_<y0>_<y1>_env.nc`); `mal-core/config/model_constants.yaml:9`
(`contracts.env_nc: "3.0"`).
Answer: the `ingest` stage, contract 3.0, seven variables of which the
prediction stage reads only four.

**Q12. Is the env tensor date-specific?**
Citation: `mal-core/src/mal_core/prediction/env_loader.py:60-62` (a 3-D
variable is reduced with `vals = vals[0]`).
Answer: **no** — for the time-varying variables (`rainfall`, `air_temp_c`)
the loader takes the *first* time step of the file, not the requested month.
This is a real behavioural fact the document must state (and the drafter
should flag it as a defect, since the stage's own `year`/`month` arguments
select a state snapshot but not an environment slice).

**Q13. How is the state snapshot for the requested month chosen?**
Citation: `mal-core/src/mal_core/prediction/state_loader.py:50` (`target_day =
min(730, max(1, month * 30))`); `mal-core/src/mal_core/prediction/state_loader.py:52-77`
(the candidate directories are searched in order, the first directory that
yields any candidate wins, and within it the snapshot whose `_dayNNN` is
closest to `target_day` is chosen).
Answer: `month × 30` days, clamped to [1, 730]; nearest available snapshot
wins; the search stops at the first directory that has candidates.

**Q14. Which directories are searched for snapshots, and is that list
data-driven or hardcoded?**
Citation: `mal-core/src/mal_core/prediction/state_loader.py:38-47`
(`runs/<aoi.slug>`, `runs/abm`, `runs/1year-50r`, `runs/<aoi>_2years`,
`runs/test_gif_14d`, plus an explicit `--rollout-dir` first).
Answer: hardcoded candidate list plus an explicit override
(`mal-core/src/mal_core/cli.py:116-119`, `--rollout-dir`).

**Q15. What are the names of the snapshot files the stage expects, and who
writes them?**
Citation: `mal-core/src/mal_core/abm/src/main.cpp:169-183`
(`rollout_day_path`: `<stem>_dayNNN.tif`); `mal-core/src/mal_core/abm/src/main.cpp:218-230`
(`rollout_transmission_day_path`: `<stem>_dayNNN.tif` for transmission);
`mal-core/src/mal_core/abm/src/main.cpp:1203-1216` (per-day state snapshots
are written only when `--snapshot-every > 0`, whose default is 0 —
`main.cpp:409`); `mal-core/src/mal_core/abm/src/main.cpp:806-809`
(`--transmission-snapshot-every` default 0 = final snapshot only).
Answer: with the default CLI flags the ABM writes **only the final** state
raster and the final transmission raster; the per-day files that the loader
prefers exist only if `--snapshot-every` was raised. The document must not
imply that day snapshots are the normal case.

**Q16. What does the transmission branch add, and which file does it
actually find?**
Citation: `mal-core/src/mal_core/prediction/state_loader.py:110-149` (three
attempts: `<stem>_transmission.tif`; `*transmission*day<NNN>.tif`; then *any*
`*transmission*.tif`, each re-projected and concatenated after the vector
bands); `mal-core/src/mal_core/abm/include/mal_abm_fast/transmission_output.hpp:21-25`
(the four transmission bands: `human_prevalence`, `human_incidence`,
`infectious_vector_pressure`, `active_focus`).
Answer: four extra channels, so the state tensor is `(6, H, W)` when a
transmission raster is found and `(2, H, W)` otherwise
(`state_loader.py:36`). **Open** as to whether the final transmission raster
(matched by the third fallback) is the temporally correct companion of the
chosen vector snapshot — see part (c).

**Q17. How are the state and env tensors brought onto the AOI grid, and what
is lost?**
Citation: `mal-core/src/mal_core/prediction/state_loader.py:91-107` and
`env_loader.py:67-83` (both `rasterio.warp.reproject` with
`Resampling.bilinear` onto `from_bounds(aoi.bbox, W, H)`); `mal-core/src/mal_core/abm/src/main.cpp:1203`
(the source is the ABM's own 1 km grid).
Answer: bilinear resampling onto the AOI grid defined by the AOI registry and
the scale's resolution. Bilinear interpolation of **raw adult counts**
produces fractional individuals; the document must say that what leaves this
step is no longer integer counts.

**Q18. What happens when an input is missing?**
Citation: `mal-core/src/mal_core/prediction/predictor.py:50-62`
(`FileNotFoundError` from the state loader → all-zero state; *any*
exception from the env loader → all-zero env), swallowed with a bare
`except Exception`.
Answer: the stage **degrades silently to zeros** and still writes a complete,
well-formed output raster with a sidecar. There is no warning, no sentinel
in the output, and no record in the sidecar that the inputs were absent.
This is the single most important negative fact in the stage.

### A3. Checkpoint selection and loading

**Q19. How is a checkpoint selected?**
Citation: `mal-core/src/mal_core/prediction/registry.py:53-71` (`scan()`
walks `runs/models/` **and** `runs/` recursively for `model.yaml`);
`mal-core/src/mal_core/prediction/registry.py:74-93` (`get()`: exact
`name@version` if a version is given, otherwise the **last** matching
`name@…` key in scan order, with a fallback to a bare name key);
`mal-core/src/mal_core/prediction/registry.py:95-117` (`load()`: the literal
name `"dummy"` short-circuits to a zero model; otherwise the checkpoint path
is `<manifest dir>/<manifest.checkpoint>`; a missing file raises
`FileNotFoundError`; an empty `checkpoint` field also yields the zero model).
Answer: selection is by directory scan of `model.yaml` manifests, keyed
`name@version`; the "latest" version is whichever key appears last in the
scan, not a semantic version comparison.

**Q20. What is in the manifest, and what are its defaults?**
Citation: `mal-core/src/mal_core/prediction/registry.py:24-31` (`name`,
`version="1.0"`, `contract_version="1.1"`, `in_channels=10`,
`out_channels=6`, `checkpoint=""`, `description`).
Answer: as listed; note the defaults are placeholders, and the manifest's
`contract_version` is *not* checked against the state contract the stage
consumes.

**Q21. Who writes the manifest, and with what values?**
Citation: `mal-core/src/mal_core/training/trainer.py:95-106` (`name` = output
directory name, `version` = "1.0", `contract_version` = "1.1",
`checkpoint` = "best_model.pt", `in_channels`/`out_channels` = the shapes
measured from the training sample at `trainer.py:51-54`).
Answer: the `training` stage.

**Q22. How is the checkpoint loaded, and how are the network's
input/output channel counts determined?**
Citation: `mal-core/src/mal_core/training/wrapper.py:39-49` (a `model.yaml`
next to the checkpoint can override `in_channels`/`out_channels`);
`mal-core/src/mal_core/training/wrapper.py:51-58` (otherwise the shapes are
inferred from `enc.0.block.0.weight` and `head.weight`);
`mal-core/src/mal_core/training/wrapper.py:60-65` (state dict loaded,
`model.eval()`); `mal-core/src/mal_core/training/wrapper.py:29-37` (device:
cuda → mps → cpu).
Answer: shapes are manifest-first, then inferred from tensor shapes.

**Q23. How are the stage's inputs assembled into the network's input
tensor?**
Citation: `mal-core/src/mal_core/training/wrapper.py:70-88` (state and env
are concatenated; if fewer channels than `in_channels`, **zeros are appended**;
if more, the tensor is **truncated**); `mal-core/src/mal_core/training/wrapper.py:90-104`
(the raster is padded up to a multiple of 16 with `replicate` and cropped
back after the forward pass).
Answer: `concat(state, env)`, zero-padded or truncated to `in_channels`,
padded to a 16-multiple. With the defaults (`in_channels=10`) a
`(6, H, W)` state plus a `(4, H, W)` env is exactly 10 and no padding
happens; a state of `(2, H, W)` (no transmission raster) makes the wrapper
zero-pad, i.e. the transmission channels become zeros.

**Q24. Does the order of the concatenated channels match the order the
surrogate was trained on?**
Citation: `mal-core/src/mal_core/training/dataset.py:242-252` (training
concatenates vector state + transmission state, then env);
`mal-core/src/mal_core/prediction/state_loader.py:149` (prediction
concatenates vector bands then transmission bands) and
`mal-core/src/mal_core/prediction/env_loader.py:56-63`.
Answer: the *state* channel order agrees. The *env* channel order does not:
training selects `["rainfall", "air_temp_c", "jrc_persistent", "lc_built"]`
(`dataset.py:72`) while prediction selects `["rainfall", "air_temp_c",
"jrc_persistent", "lc_wetland"]` (`env_loader.py:18`). See part (c).

### A4. Inference, aggregation and output

**Q25. What exactly is executed at inference time?**
Citation: `mal-core/src/mal_core/prediction/predictor.py:84-92` (load real
inputs → `model.predict(state, env)` → aggregate); `mal-core/src/mal_core/prediction/registry.py:41-45`
(the "dummy" model returns a zero tensor of `state.shape[0]` channels);
`mal-core/src/mal_core/training/wrapper.py:70-106` (the real path).
Answer: one forward pass of the U-Net over the whole AOI grid, then a
per-scale aggregation.

**Q26. Does the scenario/intervention configuration affect the output?**
Citation: `mal-core/src/mal_core/prediction/predictor.py:86-87` (`params =
interventions_to_params(scenario)`) and `predictor.py:89`
(`model.predict(state, env)` — `params` is never passed).
Answer: **no.** The scenario's interventions and climate anomalies are
converted to a parameter dict that is then discarded; only the scenario's
`aoi`, `scale`, `year` and `month` take effect
(`mal-core/src/mal_core/cli.py:133-140`). The document must not attribute
any intervention effect to the prediction.

**Q27. What are the per-scale grids and aggregations?**
Citation: `mal-core/src/mal_core/prediction/aggregator.py:25-29` (regional
1000 m, national 2000 m, continental 5000 m);
`mal-core/src/mal_core/prediction/aggregator.py:32-44` (`make_aoi` overrides
the AOI registry's resolution with the scale's);
`mal-core/src/mal_core/prediction/aggregator.py:51-53` (regional = identity);
`aggregator.py:56-66` (national: `n_rows = max(1, H//10)`, `n_cols =
max(1, W//10)`, block mean);
`aggregator.py:69-71` (continental: a single scalar, the mean of the whole
raster); `aggregator.py:74-79` (dispatch).
Answer: regional = unchanged raster; national = a 10×10-style block mean on
the *2 km* grid; continental = one number. Note that the national pooling is
a rectangular block mean, **not** a GADM-2 aggregation, despite the
`GridDef` description string at `aggregator.py:27`.

**Q28. What is the output file's name, location and format?**
Citation: `mal-core/src/mal_core/prediction/predictor.py:94-98` (default
directory `runs/predictions/`, name
`<aoi_slug>_<scale>_<year>_<month:02d>_risk.tif`);
`mal-core/src/mal_core/prediction/predictor.py:113-126` (GeoTIFF, float32,
tiled, deflate, 128×128 blocks, CRS = AOI CRS, transform = `from_bounds` of
the AOI bbox over the scale grid, `nodata` = the ingest sentinel);
`mal-core/src/mal_core/prediction/predictor.py:127-132` (bands written and
described).
Answer: as listed.

**Q29. What are the output band names, and what do they mean?**
Citation: `mal-core/src/mal_core/prediction/predictor.py:30-41`
(`BAND_NAMES_MAP`: 1 → `predicted_risk`; 2 → `predicted_adult_patch_count`,
`predicted_adult_cell_count`; 6 → the two adult-count bands plus
`predicted_human_prevalence`, `predicted_human_incidence`,
`predicted_infectious_pressure`, `predicted_transmission_focus`);
`mal-core/src/mal_core/prediction/predictor.py:129` (fallback `band_1…band_n`
when the band count is not in the map).
Answer: names are chosen by **band count**, and they mirror the surrogate's
*training target* order (2 adult-count bands then the 4 transmission bands),
not the ABM's own band names.

**Q30. What are the output's units, and is it bounded?**
Citation: `mal-core/src/mal_core/training/model.py:36-38` (the network head
is a bare convolution — no sigmoid on the output);
`mal-core/src/mal_core/training/model.py:63-73` (the sigmoid appears only
inside the Dice loss, as a soft thresholding device).
Answer: the written values are raw network outputs, in the units of the
training target (adult counts for the first two bands, and the
transmission quantities for the rest), **not** a [0, 1] probability and not
clamped. The `nodata` value written into the profile is the ingest sentinel
`ingest.nodata_sentinel = -9999.0`
(`mal-core/config/model_constants.yaml:137`), which never appears in the
data.

**Q31. What does the sidecar contain, and what is its suffix?**
Citation: `mal-core/src/mal_core/prediction/predictor.py:134-148` (keys
`crs`, `transform`, `aoi_slug`, `scale`, `year`, `month`, `bands`,
`model_name`, `model_version`, `contract_version` = "1.1",
`generator_version` = "mal-execution-0.1.0"; written as `<file>.tif.json`).
Answer: as listed; the unusual `.tif.json` suffix is deliberate and matches
the existing artefacts.

**Q32. Does the sidecar record which model was actually loaded?**
Citation: `mal-core/src/mal_core/prediction/predictor.py:81` and `:142-143`
(the loaded model comes from `registry.load(model_name, model_version)`, but
the sidecar writes `model_name` as given and `model_version` as
`model_version or "latest"`).
Answer: **no** — with no explicit version (the CLI never passes one:
`mal-core/src/mal_core/cli.py:107-119` has `--model` but no version option),
the sidecar always says `"latest"` regardless of which `name@version` the
registry actually resolved. There is also no checkpoint hash, no training
run reference and no input fingerprint. See part (c).

**Q33. How is the georeferencing of the written raster related to the
aggregated array's shape?**
Citation: `mal-core/src/mal_core/prediction/predictor.py:78` and `:100`
(`w, h` are the *scale grid* dimensions used to build the transform) versus
`predictor.py:112` and `:118-119` (`height`/`width` are taken from the
*aggregated* array's shape).
Answer: the transform's pixel size is derived from the scale grid while the
raster's dimensions come from the aggregated array — identical only for the
regional scale. See part (c) for national and continental.

**Q34. What is the "latest prediction" for an AOI?**
Citation: `mal-core/src/mal_core/prediction/predictor.py:153-158`
(`sorted(pred_dir.glob(f"{aoi_slug}_*_risk.tif"))[-1]`).
Answer: the lexicographically last matching filename. With the scale embedded
in the name (`regional`/`national`/`continental`), lexicographic order is
not chronological order and not a single-scale series.

**Q35. What is the order of operations, and what follows from that order?**
Citation: `mal-core/src/mal_core/prediction/predictor.py:77-98` (AOI → model
→ inputs → inference → aggregation → directory creation → filename);
`mal-core/src/mal_core/prediction/predictor.py:100` (the transform is
computed from the scale grid, before the aggregation result is inspected).
Answer: aggregation precedes writing, so the written raster's shape depends
on the aggregation, while its georeferencing was fixed earlier from the
pre-aggregation grid.

### A5. Provenance, versioning and evidence

**Q36. Where do the numeric constants of the stage come from, and which are
still literals in the code?**
Citation: `mal-core/src/mal_core/prediction/predictor.py:121` (the NoData
sentinel is read from the config, `CONFIG["ingest"]["nodata_sentinel"]` →
`mal-core/config/model_constants.yaml:137`); `mal-core/src/mal_core/prediction/predictor.py:144-145`
(the output contract and generator version are string literals);
`mal-core/src/mal_core/prediction/registry.py:27` (manifest contract default
literal); `mal-core/src/mal_core/prediction/env_loader.py:134` (the NPZ
fallback's default bounds literal); `mal-core/src/mal_core/prediction/aggregator.py:25-29`
(the per-scale resolutions are literals).
Answer: only the NoData sentinel comes from `model_constants.yaml`. The
output contract version "1.1", the generator version, the manifest contract
default, the NPZ default bounds and the per-scale resolutions are literals in
code — and `model_constants.yaml` currently defines only two contract
versions (`contracts.env_nc`, `contracts.cogs_state`,
`mal-core/config/model_constants.yaml:8-10`). The document must not
hand-type these numbers; they need a generated source. See part (c).

**Q37. What is the versioning story for the stage's own output?**
Citation: `mal-core/src/mal_core/prediction/predictor.py:144`
(`contract_version: "1.1"`); `mal-core/src/mal_core/prediction/registry.py:27`;
`mal-core/src/mal_core/abm/include/mal_abm_fast/output_contract.hpp:28-33`
(the state sidecar's own versioning discipline, including the retired
`k_max` key).
Answer: the prediction sidecar carries a version string that no consumer in
the tree validates, and which is not the state contract version. The
document must state both facts.

**Q38. What is the testing/verification status of the stage?**
Citation: `mal-core/tests/test_prediction_pipeline.py:23-35` (registry dummy
load), `:37-48` (state loader shape), `:50-55` (env loader shape),
`:57-86` (end-to-end run with the dummy model: file exists, sidecar exists
and parses, raster opens with CRS).
Answer: the stage is covered by an end-to-end shape test that uses the
**dummy** model; there is no test that a real checkpoint is loaded and
inferred correctly, none that exercises the national/continental
aggregators, and none that asserts the output's band names or sidecar
version. The retired prediction specification listed a "drift check" that was
not part of the test suite; the contract facts it listed are now pinned by
`mal-core/tests/test_spec_retirement_prediction.py`.

**Q39. Which spec claims are contradicted by the code (so the document must
not repeat them)?**
Citation: `mal-core/src/mal_core/prediction/registry.py:28` (`in_channels=10`,
`out_channels=6`) — the retired specification said `in_channels=5`;
`mal-core/src/mal_core/prediction/state_loader.py:36` (`C=6` with
transmission) — the retired specification said `(2,H,W)`;
`state_loader.py:50` (day clamped to `[1,730]`) — the retired specification
said `[7,360]`; `mal-core/src/mal_core/prediction/predictor.py:30-41` (the band
names are `predicted_*`, one per output channel) — the retired specification
said a single band named `risk`;
`predictor.py:121` (`nodata` read from config) — the retired specification said
`nodata=-9999.0` was hardcoded; and no `AOI_CATALOGUE` symbol exists in
`aggregator.py` — the AOI catalogue is
`mal-commonlib/src/mal_commonlib/aois.yaml`.
Answer: the spec is a set of drifts, not a description; the document must be
written from the code.

### A6. Declaration of absences

**Q40. What is implemented but never reached from the stage's entry point?**
Citation: `mal-core/src/mal_core/prediction/predictor.py:44-47`
(`_generate_dummy_inputs` has no caller in the repository);
`mal-core/src/mal_core/prediction/aoi_resolver.py:68-100` (`resolve_aoi`
resolves data paths from `data/<aoi>/manifest.json`, but the prediction
package never calls it — the env loader bypasses the manifest with its own
glob, `env_loader.py:42-49`).
Answer: two dead or bypassed paths. The document should state that the
manifest is not consulted for the env input, contradicting the project's
manifest-first convention.

**Q41. What inputs does the stage accept that it never uses?**
Citation: `mal-core/src/mal_core/prediction/state_loader.py:23` and `:32`
(the `seed` parameter is documented as "rollout seed to use" but is never
referenced in the body); `mal-core/src/mal_core/prediction/predictor.py:69-70`
(`year` and `month` are used only for the output file name, the sidecar, and
— for `month` — the snapshot selection).
Answer: `seed` is inert; `year` selects nothing.

**Q42. What states does the code never enter?**
Citation: `mal-core/src/mal_core/prediction/state_loader.py:129-151` (the
transmission branch is skipped when no transmission raster exists);
`mal-core/src/mal_core/prediction/predictor.py:86-87` (the scenario branch
computes a dict that is discarded); `mal-core/src/mal_core/prediction/registry.py:96-97`
(the `"dummy"` name short-circuit).
Answer: as listed.

**Q43. Which parts of the pipeline that a reader would expect are absent?**
Citation: `mal-core/src/mal_core/prediction/predictor.py:66-76` (the
signature — no ensemble, no uncertainty, no calibration, no
post-processing/thresholding, no re-projection to an administrative
boundary); `mal-core/src/mal_core/prediction/predictor.py:89` (raw network
output is written unchanged).
Answer: the stage writes the raw surrogate output. There is no risk
classification, no probability, no uncertainty band, no ensemble over
seeds — even though the CLI help says "produce a classified risk map"
(`mal-core/src/mal_core/cli.py:122`).

**Q44. What must the artefact not be used for?**
Citation: `mal-core/src/mal_core/prediction/predictor.py:89` and `:128` (the
network output is written as-is); `mal-core/src/mal_core/training/model.py:1-6`
(the network emulates one ABM step, it was never fitted to observations).
Answer: it is a model of a model. It is not a measurement of infection, not a
calibrated risk probability, and (see part (c)) not currently usable with a
checkpoint trained under the state contract the stage now consumes.

---

## Part (b) Done-checklist

Concrete, checkable items for "the `prediction` document is done":

**Inputs and the seam with `abm`**
1. The consumed bands are named where the consumption is first described:
   `adult_patch_count` and `adult_cell_count` (raw per-cell adult counts,
   state contract 4.0), plus the four transmission bands when a transmission
   raster is found.
2. The state contract version (4.0) and the prediction output's own contract
   version are stated as two separate things, with the statement that the
   prediction does not gate on the state version.
3. The sidecar's role in the upstream contract is described, and the fact
   that the stage reads the state raster **without** reading the sidecar is
   stated.
4. The env inputs are named with their source stage, contract version and
   variable names, and the four consumed channels are listed.
5. The date-selection behaviour of each input is stated: the state snapshot
   is chosen by nearest day to `month × 30` clamped to [1, 730]; the env
   time series contributes only its **first** time step.
6. The resampling operation (bilinear) and its consequence for count-valued
   bands are stated.

**Checkpoint selection and loading**
7. The selection mechanism is described: manifest scan (`model.yaml`) →
   key `name@version` → version resolution rule → checkpoint path → device
   selection → shape resolution.
8. The `"dummy"` path is described as a zero model with a distinct channel
   count behaviour, not as "a model".
9. The input assembly is described: `concat(state, env)`, zero-padding or
   truncation to `in_channels`, padding to a multiple of 16, and the
   consequence that a missing transmission raster means four zero channels.

**Inference and outputs**
10. The order of operations is written as pseudocode plus a table
    (step / actor / order / mode), with the consequences of that order.
11. The per-scale behaviour is described for all three scales, including the
    block size actually used and that the national pooling is a rectangular
    block mean.
12. The output contract is complete: file name, directory, driver, dtype,
    band count, band names and their order, tiling/compression, CRS,
    transform, NoData sentinel, and the sidecar's name and full key list.
13. The units of every output band are stated (raw surrogate output in the
    training target's units; not a probability; not clamped), and the
    NoData sentinel's irrelevance to the data is noted.
14. The consumption contract is stated: who reads the output in this
    repository (the `status` CLI command and the two FastAPI endpoints) and
    the explicit statement that no map/dashboard/planning consumer exists.
15. The scenario/intervention behaviour is stated truthfully: interventions
    and climate anomalies do **not** influence the output.

**The negative space**
16. The silent zero-fallback on missing inputs is stated in its own place.
17. The absences are declared: dead code paths (`_generate_dummy_inputs`,
    `aoi_resolver.resolve_aoi` not called, `seed` inert, `year` inert), the
    discarded scenario parameters, the absence of calibration/thresholding/
    uncertainty, and the absence of version gating on the consumed state.
18. The document says plainly that the output is an emulation of one ABM
    step learned from ABM snapshots — not a measurement, not an independent
    forecast — and lists what the artefact must not be used for.
19. The spec-vs-code drifts are not reproduced; where the retired spec
    disagrees, the code is authoritative.

**Form**
20. No number in the prose is hand-typed: every value is emitted by the
    generator (`\input{generated/…}` / `\mskey{…}`), and the constants that
    are currently literals in code — output contract version, generator
    version, manifest contract default, per-scale resolutions, the NPZ
    default bounds — are either given a generated source before the document
    lands, or explicitly flagged as literals pending that change.
21. Every claim carries a citation to a file and line a reviewer can open.
22. Code symbols are glossed in prose at first use; no call graphs and no
    test names in the body (evidence appendix only).

---

## Part (c) Open questions

1. **Env channel order mismatch between training and inference.**
   Training selects `["rainfall", "air_temp_c", "jrc_persistent",
   "lc_built"]` (`mal-core/src/mal_core/training/dataset.py:72`) while the
   prediction env loader selects `["rainfall", "air_temp_c",
   "jrc_persistent", "lc_wetland"]`
   (`mal-core/src/mal_core/prediction/env_loader.py:18`). A checkpoint
   trained with the training order will receive a different fourth channel
   at inference. Which is the intended order, and where should it live so
   that both stages read one list?

2. **Training-time environment input is often all zeros.**
   `mal-core/src/mal_core/training/dataset.py:245-249` uses zero env patches
   whenever no `env_path` was supplied, and the CLI's `--env-path` defaults
   to `None` (`mal-core/src/mal_core/cli.py:782`). What does a checkpoint
   trained that way mean at inference time, when the env stack is real?

3. **Checkpoint compatibility with the state contract.**
   The state bands are raw adult counts under contract 4.0
   (`mal-core/src/mal_core/abm/include/mal_abm_fast/wire.hpp:124-133`), and
   the redesign plan states that checkpoints trained against the retired
   normalised bands are not reusable without retraining
   (`docs/plans/completed/redesign/03-retirada-k-max-y-separacion-de-escalas.md:67-70`).
   Is there any trained checkpoint under contract 4.0, and what does the
   stage do if the only available checkpoint predates it? Nothing in
   `registry.py` checks this.

4. **Transmission raster vs. vector snapshot are not necessarily from the
   same day.** With the default `--transmission-snapshot-every 0`
   (`mal-core/src/mal_core/abm/src/main.cpp:806-809`) only the *final*
   transmission raster exists, and the loader's last-resort glob
   (`mal-core/src/mal_core/prediction/state_loader.py:124-127`) will pick it
   up while the vector snapshot is the nearest day to `month × 30`. Should
   the stage refuse to mix them, and should it record which day each channel
   came from in the sidecar?

5. **Georeferencing of the aggregated output.** The transform is computed
   from the scale grid (`mal-core/src/mal_core/prediction/predictor.py:100`)
   while the raster's height/width come from the aggregated array
   (`predictor.py:112`, `:118-119`). For the national and continental scales
   these disagree. Is this a defect to fix before the document is written,
   or is the current behaviour the intended contract?

6. **Model identity in the sidecar.** The sidecar records `"latest"` when no
   version is given (`mal-core/src/mal_core/prediction/predictor.py:143`),
   and the CLI offers no version flag (`mal-core/src/mal_core/cli.py:107-119`).
   Should the CLI gain `--model-version`, and should the sidecar record the
   resolved `name@version` and a checkpoint hash?

7. **"Latest prediction" ordering.**
   `mal-core/src/mal_core/prediction/predictor.py:157` takes the
   lexicographically last filename, which mixes scales and dates. Should
   selection be by (date, scale) explicitly, or should the output directory
   be partitioned per AOI/scale?

8. **Versioning home for the prediction output contract.** `"1.1"` is a
   literal in `predictor.py:144` and `registry.py:27`;
   `mal-core/config/model_constants.yaml:8-10` defines only `env_nc` and
   `cogs_state`. The documentation layer requires values to come from
   generated sources — where does the prediction output contract version
   live, and is a new `contracts.cogs_prediction` key needed?

9. **The `state` COG's own metadata is unused.** `h`, `w`, `nodata`,
   `band_names`, `contract_version` and `abm_params_hash` are all in the
   state sidecar (`mal-core/src/mal_core/abm/include/mal_abm_fast/output_contract.hpp:36-56`)
   and none are read by the prediction stage. Should the stage consult them
   (which would also close open question 3)?

10. **Manifest bypass for the env input.** The env loader globs
    `data/<aoi>/*_env.nc` (`mal-core/src/mal_core/prediction/env_loader.py:42-49`)
    while the package contains a manifest-aware resolver
    (`mal-core/src/mal_core/prediction/aoi_resolver.py:68-100`) that nothing
    calls. Should prediction consume the manifest (project convention) and
    drop the glob?

11. **Is the National scale's block mean the intended semantics?** The
    `GridDef` description says "GADM-2 mean-pool (district level)"
    (`mal-core/src/mal_core/prediction/aggregator.py:27`) but the code is a
    rectangular block mean on the 2 km grid
    (`aggregator.py:56-66`). Which is the truth for the document?

12. **What is the meaningful reading of a "risk" band?** The single-band
    name `predicted_risk` (`mal-core/src/mal_core/prediction/predictor.py:31`)
    is reachable only for a 1-channel model, and the produced values are
    unbounded network outputs. Should the document describe the file as a
    "risk" map at all, or as a surrogate state raster?

13. **How are AOIs with no AOI-registry entry handled?** `make_aoi` calls
    `AOI.from_slug` (`mal-core/src/mal_core/prediction/aggregator.py:34`)
    and the registry is `mal-commonlib/src/mal_commonlib/aois.yaml`; the
    failure mode for an unknown slug is not stated anywhere in the package.

14. **Absence of any epidemiological validation in the stage.** No metric,
    no held-out comparison against surveillance data and no skill statement
    exists in the package (`mal-core/src/mal_core/prediction/` has no
    validation module). Where should the document's statement about
    verification status come from — the `training` stage's Dice report, or a
    new artefact?
