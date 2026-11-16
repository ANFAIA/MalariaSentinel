# Urgent fixes: eight defects the conceptual documentation layer uncovered

*   **Author:** david-fm
*   **Status:** Plan (in process) — URGENT
*   **Date:** 2026-11-16
*   **Origin:** the verification of the conceptual documents against the code,
    on the branch `docs/conceptual-documentation-layer` (commit `aa9d717`).
    Every finding below was checked against the code before it was written
    here; the documents that describe the behaviour are the ones that
    changed when a finding was confirmed.

--------------------------------------------------------------------------------

## Overview

Writing a description of what the pipeline does is a way of finding out what
it does. Six documents, each verified against the code, produced eight defects
that no test and no review had caught. None of them is a crash: every one of
them is a **silent** misbehaviour — a channel that becomes zero, a checkpoint
that is not the best one, a cell that is called urban when it is a field.

They are ordered here by how much they change the science, not by how hard
they are to fix.

| # | Defect | Where | Consequence |
|---|---|---|---|
| U1 | The environmental stack is discarded on load | `training/dataset.py:65-87` | The surrogate is trained with **zero** climate channels |
| U2 | Training and inference read the environment on different grids | `training/dataset.py:246-249`, `prediction/env_loader.py:69-83` | The two sides of the surrogate see different quantities |
| U3 | The channel order differs when the transmission raster is missing | `training/wrapper.py:80-88` | The network is fed the transmission bands in the env slots |
| U4 | The best checkpoint is the last epoch | `training/trainer.py:86` | The published model is the last one, not the best one |
| U5 | A missing checkpoint aborts the run | `prediction/predictor.py:81` | The stage does not degrade to the documented behaviour |
| U6 | `--model` defaults to `dummy` | `prediction/registry.py:96`, `cli.py:112` | A trained surrogate is **never** used unless it is named explicitly |
| U7 | The urban class is inverted, and water counts as urban | `ingest/hosts.py:122-128`, `abm/src/host_landscape.cpp:111-121` | **97.8%** of the Ghana area of interest is read as urban |
| U8 | Four configuration parameters have no effect | `mal-core/config/model_constants.yaml` | The operator believes four knobs exist that do not |

The work happens on another branch. This plan is the input, and the
verification that closes it is: for each item, the test that fails before the
fix and passes after it, named.

--------------------------------------------------------------------------------

## U1. The environmental stack is discarded on load

### Symptom

The training dataset reads the environment NetCDF and throws it away. The four
environmental channels of every patch are zeros. The surrogate is trained on
climate that is constant, and on static habitat that is constant.

### Evidence

`mal-core/src/mal_core/training/dataset.py:65-87`:

```python
with xr.open_dataset(self.env_path) as ds:
    vars_to_use = [v for v in ["rainfall", "air_temp_c", "jrc_persistent",
                               "lc_built", "lc_wetland", "lc_open_plus_water",
                               "lc_crop"] if v in ds]
    arrs = [ds[v].values.squeeze() for v in vars_to_use[:ENV_CHANNELS]]
    ...
    self._env_cache = np.stack(arrs[:ENV_CHANNELS], axis=0).astype(np.float32)
```

`ENV_CHANNELS` is 4 (`dataset.py:22`), so `vars_to_use[:4]` is
`["rainfall", "air_temp_c", "jrc_persistent", "lc_built"]`. The two daily
series carry a time axis — `(time, y, x)` — and the two static planes are
`(y, x)`. `np.stack` requires every input to have the same shape, so it
raises. The call is wrapped in

```python
except Exception:
    self._env_cache = None
```

and the cache becomes `None`. `__getitem__` then takes the fallback branch
(`dataset.py:246-249`) and builds `np.zeros((ENV_CHANNELS, ps, ps))`.

The inference side survives the same file because it never stacks: it reads
the first time step of the daily series
(`prediction/env_loader.py:57-62`). So the model is trained on zeros and
served on real values.

### Consequence

The surrogate learns nothing about rainfall, temperature or habitat. It is a
spatial smoother of the state bands. Every score that depends on the
surrogate's sensitivity to the environment (D15 persistence, D19 pool
persistence, D20 washout response) is measuring the scorer's own model, not
the surrogate's.

### Options

| Option | What it costs | What it risks |
|---|---|---|
| **A. Take the last time step of the daily series, as the inference side does** | The training set is static in time: every patch of every day gets the same climate | The model cannot learn a daily response; it learns the climatology |
| **B. Build the patch's time window** — the dataset yields pairs `(t, t+1)`, so the env of day `t` is available | The dataset must know which day each patch belongs to, and the env loader must index the time axis | The env NC and the state snapshots must agree on the calendar; the day index has to come from the run, not from a guess |
| **C. Drop the environmental channels from the model** and document that the surrogate is spatial-only | The network's input halves; the manifest's channel contract changes | The whole point of the surrogate (predicting a state that depends on the environment) is given up |

### Recommendation

**B**, with **A** as the fallback for a run whose env NC has no time axis.
Option B is the only one that makes the training data consistent with the
inference data, and consistency between the two sides is the property that
U2 and U3 also break. The day index is not a guess: the run's state snapshots
are named `*_dayNNN.tif` and the dataset already globs them
(`dataset.py:90-93`).

The change is confined to `_load_env_if_available` (keep the time axis, index
it per patch) and to `__getitem__` (pass the day's index).

### Acceptance

- A test that builds a dataset over a synthetic run with a synthetic env NC
  whose `rainfall` varies in time, and asserts that the environmental block of
  two patches on different days differs.
- A test that asserts the environmental channels are **not** all zero when an
  env NC is present (the assertion that would have caught this).
- The existing test `mal-core/tests/test_training_pipeline.py` still passes.

### Risk

Medium. The env NC's time axis is daily (`era5_air_temp_daily`,
`chirps_rainfall_daily`); the run's day numbering must be mapped onto it.
That mapping is a new piece of knowledge and it has to be written down, not
inferred.

--------------------------------------------------------------------------------

## U2. Training and inference read the environment on different grids

### Symptom

The training side crops the environment at the **ABM patch index**; the
inference side reprojects it onto the **AOI grid**. Two different numbers
mean the same word.

### Evidence

`training/dataset.py:246-249`:

```python
if self._env_cache is not None and self._env_cache.shape[-2] >= r+ps and self._env_cache.shape[-1] >= c+ps:
    env_patch = self._env_cache[:, r:r+ps, c:c+ps]
```

`r` and `c` are the row and column of the patch in the state COG. The
environment NC is on the AOI grid (`1 km`), and the state COG is on the ABM
grid; when they coincide, this crop is correct; when they do not, it reads a
window of the wrong size at the wrong place — and the guard
`shape[-2] >= r+ps` silently falls back to zeros instead of failing.

`prediction/env_loader.py:69-83` takes the other route: it reads the env NC
and resamples it onto the AOI grid, then the aggregator works on the AOI
grid.

### Consequence

The surrogate is fitted on one quantity and applied to another. Its
predictions at the seams of the AOI are the product of two different
resamplings, neither of which the model ever saw.

### Options

| Option | What it costs | What it risks |
|---|---|---|
| **A. Make the training side resample like the inference side** — read the env NC on the AOI grid and crop it with the AOI index of the patch | The dataset must know the AOI index of each patch, i.e. the mapping between the ABM grid and the AOI grid | The mapping must be exact: an off-by-one here is a silent spatial shift |
| **B. Make the inference side crop like the training side** | The inference side would need the ABM grid | The ABM grid is not part of the prediction contract (the prediction products are declared on the AOI grid) |
| **C. Declare the AOI grid as the only grid** and make the engine's state COG and the env NC agree | A change to the state output contract | The ABM runs on its own grid; the state COG is a downsampling of it |

### Recommendation

**A.** The prediction products are declared on the AOI grid, so the AOI grid
is the contract's grid; the training side must be brought to it. The
alternative — making the training side agree with the inference side by
construction — is the same fix seen from the other end.

Whichever is chosen, the guard that falls back to zeros has to become a loud
failure: a shape that does not match is a bug in the caller, not a reason to
train on silence.

### Acceptance

- A test that trains on a synthetic run and predicts from the same run, and
  asserts that the environmental tensor the model sees at training time is
  the tensor it sees at inference time, element for element.
- The zeros fallback disappears from the code path that a present env NC
  takes.

### Risk

Medium-high: this is the change with the most spatial subtlety. It should
land together with U1, because both touch the same function.

--------------------------------------------------------------------------------

## U3. The channel order differs when the transmission raster is missing

### Symptom

The network's input is `[state, transmission, env]` in training and
`[state, env, transmission]` in inference. When the transmission raster is
absent, the inference side pads with zeros **at the end**, so the
environmental bands land in the transmission slots.

### Evidence

`training/dataset.py:245` builds `x = np.concatenate([state_patch, env_patch], axis=0)`
— the state COG already carries the transmission bands as its second plane
pair, so the training layout is `[vector(2), transmission(2), env(4)]`.

`training/wrapper.py:80-88`:

```python
total_ch = state.shape[0] + env.shape[0]
if total_ch < self.in_channels:
    missing = self.in_channels - total_ch
    pad_ch = np.zeros((missing, state.shape[1], state.shape[2]), dtype=np.float32)
    x = np.concatenate([state, env, pad_ch], axis=0)
```

With no transmission raster, `state` is the vector bands only (2 channels),
`env` is 4 channels, and the wrapper pads to 8 by appending zeros — the
network's channel 2 and 3 (which it was trained to read as transmission) get
the **environmental** values, and the real environment (channels 4-7) gets
zeros.

### Consequence

The surrogate is asked to predict a state change from a vector plus weather,
using weights that expect a vector plus transmission. The failure is silent
and produces plausible-looking numbers.

### Options

| Option | What it costs | What it risks |
|---|---|---|
| **A. Pad in the middle** — build the full tensor `[state, transmission, env]` with the missing block zeroed where it belongs | The wrapper needs to know which band is missing | None, if the model's manifest declares the band order |
| **B. Declare the channel order in the manifest** and have both sides read it | The manifest's `in_channels` becomes a list, not a count | A manifest change ripples into the registry and the scorecard |
| **C. Always require the transmission raster** | Nothing | The prediction stage would refuse to run without a transmission file, which is exactly the fallback the pipeline needs |

### Recommendation

**A and B together.** The manifest should declare the band order (the plan's
own "flag-and-file contract" idea applied to the model), and both sides
should build the tensor from that declaration. Then a missing band is a zero
**in its own slot**, and the network is never fed a permuted tensor.

### Acceptance

- A test that builds the input tensor twice — once with a transmission
  raster, once without — and asserts that the non-transmission bands occupy
  the same slots in both, with zeros only in the transmission slots.
- The manifest states the order, and both sides read it.

### Risk

Low-medium. It touches the model manifest's schema.

--------------------------------------------------------------------------------

## U4. The best checkpoint is the last epoch

### Symptom

When the validation Dice is zero in every epoch — which is what happens when
the environment channels are zero (U1) — the checkpoint named `best_model.pt`
holds the **last** epoch's weights.

### Evidence

`training/trainer.py:86`:

```python
if val_dice >= best_dice or epoch == 0:
    best_dice = val_dice
    torch.save(model.state_dict(), output_dir / "best_model.pt")
```

With `val_dice == 0.0` and `best_dice == 0.0`, `0.0 >= 0.0` is true in every
epoch. The comparison is also non-strict where it should be strict: a tie
should keep the earlier checkpoint, not replace it with a later one.

### Consequence

The published model is the last one. With a constant validation set (all
zeros) every epoch is equally good, so the choice is arbitrary — but it is
arbitrary in the direction of "the last thing that ran", and it is
undetectable because the file is called `best_model.pt`.

### Options

| Option | What it costs | What it risks |
|---|---|---|
| **A. Use `>`** | Nothing | With a constant Dice, only the first epoch is kept — the file then means "the first", not "the best" |
| **B. Break ties on the training loss** | One more number to carry | The loss is not comparable across epochs in a way that matters here |
| **C. Save every epoch and select afterwards** | Disk | None |
| **D. Say what the file means**: rename it to `selected_model.pt` and document the selection rule | A name change that touches the registry and the CLI | A rename is a contract change |

### Recommendation

**A and D together**: `>` for the comparison, and a name that states the
rule. A tie keeps the earlier checkpoint, which is the reproducible choice.

### Acceptance

- A test that trains for three epochs with a constant validation score and
  asserts that the selected checkpoint is the **first** epoch's weights.
- The selection rule is stated in the manifest that the trainer writes.

### Risk

Low.

--------------------------------------------------------------------------------

## U5. A missing checkpoint aborts the run

### Symptom

The prediction stage's documented behaviour is to fall back to zeros when the
model's inputs are unavailable. A missing checkpoint file raises an
uncaught `FileNotFoundError` instead.

### Evidence

`prediction/predictor.py:81`:

```python
registry = ModelRegistry()
model = registry.load(model_name, model_version)     # outside the try
state, env = _load_real_inputs(aoi, month, rollout_dir=rollout_dir)
```

and `prediction/registry.py:103-109` raises the `FileNotFoundError` when the
checkpoint named by the manifest is absent. The call is outside the
`try`/`except` that guards the state and the environment.

### Consequence

A prediction run whose model directory was moved or not copied fails with a
traceback instead of producing the product the stage promises.

### Options

| Option | What it costs | What it risks |
|---|---|---|
| **A. Catch it and fall back to the dummy** | Nothing | A typo in a model name produces zeros instead of an error — a silent wrong answer |
| **B. Catch it, warn loudly, and fall back** | Nothing | The same |
| **C. Fail fast with a clear message** | Nothing | The stage no longer produces a product when a model was requested |

### Recommendation

**B**, with the warning naming the checkpoint and the path. The difference
between A and B is the difference between a silent zero map and a zero map
that says why. A model that was **named explicitly** and is missing should
still fail (C): the user asked for that model.

### Acceptance

- A test that requests a model whose checkpoint is absent and asserts that
  the run either completes with zeros and a warning naming the checkpoint, or
  fails with a message naming it — and that the two cases are distinguishable.

### Risk

Low.

--------------------------------------------------------------------------------

## U6. `--model` defaults to `dummy`

### Symptom

A trained surrogate is never applied unless its name is typed on the command
line. The pipeline's default path is the dummy model, whatever the run
contains.

### Evidence

`prediction/registry.py:95-97`:

```python
def load(self, name: str, version: str | None = None) -> ModelProtocol:
    if name == "dummy":
        return DummyModel()
```

and the CLI's default is `model_name: str = "dummy"`
(`prediction/predictor.py:71`, exposed at `cli.py:112`).

### Consequence

A user who trains a model and then predicts gets the dummy's output — which
is not an error, and looks like a result. The surrogate is dead code unless
you know to ask for it.

### Options

| Option | What it costs | What it risks |
|---|---|---|
| **A. Default to the newest registered model, and fall back to the dummy when there is none** | The registry has to define "newest" | A stale model could be picked over the intended one |
| **B. Default to the model of the run directory** — the run's manifest names the model it was produced with | The run manifest has to carry the model's name | The run was produced by the ABM, which has no model: the coupling is backwards |
| **C. Keep `dummy` as the default, but make the pipeline's entry point (`malariasim predict`) resolve the model** | The CLI's default stays | Two entry points with different behaviour |

### Recommendation

**A**, with the resolution printed. The registry knows every model it has
registered; "the most recent one" is a question it can answer. The command
must say which model it used, on every run: a silent default is the defect
this item is about.

### Acceptance

- A test that registers two models and asserts that the default resolution
  picks the most recent and names it in the output.
- The prediction's manifest records the model it used.

### Risk

Low.

--------------------------------------------------------------------------------

## U7. The urban class is inverted, and water counts as urban

This is the one with a consequence in the science: it changes what the engine
believes about the landscape it is simulating.

### Symptom

The delivered Ghana area of interest is 97.8% "urban" to the engine, and its
genuine urban cells are read as rural.

### Evidence

**The reclassification is inverted with respect to the product.** The
GHS-SMOD data package documentation that ships inside the product's own ZIP
(`GHSL_Data_Package_2023.pdf`, §2.6.3) states:

> "Classes 30 – 23 – 22 – 21 if aggregated form the 'urban domain', 13 – 12
> – 11 – 10 form the 'rural domain'."

with the class names: 30 "Urban Centre grid cell", 23 "Dense Urban Cluster
grid cell", 22 "Semi-dense Urban Cluster grid cell", 21 "Suburban or
per-urban grid cell", 13 "Rural cluster grid cell", 12 "Low Density Rural
grid cell", 11 "Very low density rural grid cell", 10 "Water grid cell".

The loader's own comment reads the scheme the other way round
(`mal-commonlib/src/mal_commonlib/data/loaders/ghsl.py:76-79`):

```python
# GHS-SMOD class codes (R2023A scheme)
#   0, 10–19: water / no data
#   20–29:    rural (21=low, 22=medium, 23=high density)
#   30:       urban centres
```

and the reclassification follows that reading
(`mal-core/src/mal_core/ingest/hosts.py:122-128`):

```python
reclassified = np.where(urban_class == 30, 30, np.where(
    (urban_class >= 20) & (urban_class < 30), 50,
    np.where((urban_class >= 0) & (urban_class < 20), 20, 50)
))
```

So the urban clusters (21, 22, 23) become "rural" (50) and the rural classes
(11, 12, 13) become "water" (20).

**The numbers, on the Ghana grid** (429,229 cells). The source product's
classes on that grid, and the delivered `urban_class` plane of
`data/ghana/ghana_host_static.nc`:

| Source class | Meaning | Cells on the grid | Reclassified to | The engine reads it as |
|---|---|---|---|---|
| 30 | Urban Centre | 3,803 | 30 (urban) | urban |
| 23 | Dense Urban Cluster | 1,990 | 50 (rural) | rural |
| 22 | Semi-dense Urban Cluster | 594 | 50 (rural) | rural |
| 21 | Suburban or per-urban | 6,850 | 50 (rural) | rural |
| 13 | Rural cluster | 7,457 | 20 (water) | **urban** |
| 12 | Low density rural | 51,101 | 20 (water) | **urban** |
| 11 | Very low density rural | 299,511 | 20 (water) | **urban** |
| 10 | Water | 57,490 | 20 (water) | **urban** |
| 0 | No data | 433 | 50 (rural) | rural |

**The engine's test cannot tell water from urban.**
`mal-core/src/mal_core/abm/src/host_landscape.cpp:111-121`:

```cpp
// Treat any value <= 40 as urban, >= 40 as rural.
return (urban_class <= 40.0f) ? indoor_fraction_urban : ...;
```

The vocabulary the plane uses is {20 water, 30 urban, 50 rural}. A test of
`<= 40` therefore calls the water cells urban. The delivered grid's
415,992 cells labelled 20 — the rural cells and the water — are read as
urban: **419,795 of 429,229 cells (97.8%)**. The 9,434 genuine urban-cluster
cells are read as rural.

The comment in the same place is contradictory with the code: it says
"`<= 40` as urban, `>= 40` as rural", and 40 satisfies both.

### Consequence

The indoor fraction, the host landscape and therefore the human biting
fraction are computed from an inverted urban/rural signal. A field of 358,069
rural cells is read as densely built-up; the four urban clusters of the
AOI's towns are read as countryside.

### Options

| Option | What it costs | What it risks |
|---|---|---|
| **A. Fix the reclassification to the product's scheme** — urban domain {30, 23, 22, 21} → 30, rural {13, 12, 11} → 50, water {10} → 20 | A one-line change plus the loader's comment | None, once the scheme is written down |
| **B. Also fix the engine's test** to `urban_class == 30` | A change in `host_landscape.cpp` | The C++ has no test for this branch today: one has to be written |
| **C. Keep three labels and give the engine the label it needs** — the engine asks for "is this cell urban?", the plane answers | A change to the contract of the plane | The plane's contract (state/host static NC) is read by other consumers |
| **D. Re-run the ingest and re-deliver the Ghana artefacts** | A full ingest run | The delivered artefacts are stale until it happens |

### Recommendation

**A + B + D.** The reclassification follows the product's documented scheme
(A); the engine's urban test becomes an equality with the urban label (B);
and the Ghana artefacts are re-ingested, because the ones in `data/ghana/`
carry the inverted plane (D).

A alone is not enough: with the correct reclassification the water cells
(57,490) would still be read as urban by the `<= 40` test. B alone is not
enough either: with the correct test the urban clusters would still be
mislabelled rural. The two defects are independent, and each masks the other.

The scheme must be recorded where the next reader will find it: in the
loader's comment, with the citation to the data package.

### Acceptance

- A unit test over the reclassification: 30, 23, 22 and 21 → 30; 13, 12 and
  11 → 50; 10 → 20; 0 → the rural default.
- A unit test for the engine's urban test: 30 → urban, 50 → rural, 20 →
  rural (water is not built-up).
- The delivered Ghana `urban_class` plane has the rural majority, and the
  engine's urban fraction on the Ghana grid is a plausible number, stated in
  the ingest document.

### Risk

Medium. It changes the engine's landscape, so every run produced before the
fix is not comparable with a run produced after it. The re-run of the
calibration baseline is implied.

--------------------------------------------------------------------------------

## U8. Four configuration parameters have no effect

### Symptom

Four entries of `model_constants.yaml` reach the code and change nothing.
An operator who tunes them sees no change, and the documentation layer's
"Read by" column says so.

### Evidence

The generated parameter table marks each constant with the files that act on
it, distinguishing *loaded* from *used*. Three of the four are loaded into the
C++ engine's configuration struct (`mal-core/src/mal_core/abm/include/mal_abm_fast/config.hpp`)
and never read:

- `ingest.land_mask_threshold`
- `ingest.ocean_mask_threshold`
- `ingest.min_dilation_radius_cells`

The fourth, `contracts.env_nc`, is declared in the configuration and read by
the Python validator (`mal-core/src/mal_core/config_validation.py:369`), but
nothing compares the environment NetCDF's `contract_version` attribute
against it. The ingest writer stamps the attribute
(`ingest/daily_nc.py:438, 513, 524`) and the engine's reader
(`abm/src/env_reader.cpp`) ignores it. **The version gate the contract
describes does not exist in code.**

### Consequence

Three of the four are promises the configuration makes and the code does not
keep. The fourth is worse: two environment NetCDFs with different contract
versions are read by the same engine without complaint.

### Options

| Option | What it costs | What it risks |
|---|---|---|
| **A. Delete the three inert parameters** | Nothing | A caller that sets them gets a configuration error instead of silence — which is the point |
| **B. Implement them** | The behaviour they describe has to be decided | The semantics are unknown: what does "land mask threshold" threshold? |
| **C. Keep them and document them as reserved** | Nothing | The operator still believes a knob exists |
| **D. Implement the contract gate** (compare the env NC's `contract_version` with `contracts.env_nc` and fail on a mismatch) | A check in the env reader | The gate has to know where the version comes from on both sides |

### Recommendation

**A + D.** The three inert parameters are removed: their semantics are
unknown, and a parameter that does nothing is worse than no parameter,
because it is a promise. `contracts.env_nc` is kept and made real (D): the
ingest already stamps the version, so the gate is one comparison in the
engine's env reader, and it is the gate that makes the contract versioning
worth anything.

If the three parameters are wanted rather than removed, B is the alternative,
and it needs a decision about their semantics first — which is a design
question, not a bug fix.

### Acceptance

- The generated parameter table contains no constant whose "Read by" cell says
  "(loaded, never used)".
- A test that writes an environment NetCDF with a contract version that does
  not match `contracts.env_nc` and asserts that the engine refuses to run
  with a message naming both versions.

### Risk

Low for A, medium for D (the engine's failure mode changes).

--------------------------------------------------------------------------------

## What the verification of this plan is

The plan closes when, for each item, the test named in its *Acceptance*
section exists and fails on the parent commit and passes on the branch.

The order matters: **U1 and U2 together** (they touch the same function and
U1 is what makes U2 visible), **U3** (the same model contract), **U4** (the
same trainer), then **U5 and U6** (the prediction stage's entry points),
**U7** (which invalidates the calibration baseline), **U8** (which touches
the configuration the other items read).

The documents in `docs/concepts/` are the specification for this work: each
one describes the behaviour this plan corrects. When an item lands, the
document's paragraph changes with it — the documents are not a snapshot of a
defect, they are a statement about what the code should do.
