# Question set — `training` stage (conceptual document)

This file is the question set for the conceptual document of the **training**
stage of the MalariaSentinel pipeline: the stage that fits the *surrogate* — a
U-Net that emulates one step of the agent-based model — so that the prediction
stage can produce a risk map without running the C++ ABM. The material read
before writing these questions was: `mal-core/src/mal_core/training/`
(`model.py`, `dataset.py`, `trainer.py`, `wrapper.py`, `__init__.py`), the
`train` subcommand of `mal-core/src/mal_core/cli.py`, the consumers
`mal-core/src/mal_core/prediction/{registry.py, predictor.py, state_loader.py,
env_loader.py}`, the ABM state-output contract
(`mal-core/src/mal_core/abm/include/mal_abm_fast/wire.hpp`,
`mal-core/src/mal_core/abm/src/output_contract.cpp`), the existing pytest file
`mal-core/tests/test_training_pipeline.py`, and the retired training
specification (its audit trail is now `docs/plans/in-process/spec-retirement-ledger.md`) as *material only* —
several of that specification's claims are contradicted by the code (it is cited
below only where it happens to agree, and every discrepancy is flagged
explicitly). Numbers quoted in this file are the
values the code actually uses; the document must generate them from the
configuration, not type them.

---

## (a) Question set

### A. Purpose, and the limits of what is being learned

1. **What question does the training stage exist to answer, and what would
   count as it having answered it?**
   Citation: `mal-core/src/mal_core/cli.py:782-793` (the stage's own CLI help:
   "enabling fast inference without full ABM runs");
   `mal-core/src/mal_core/prediction/registry.py:100-101` (the surrogate is
   what the prediction stage loads when a real checkpoint exists).
   Answer: the stage exists to replace "run the C++ ABM" with "apply a learned
   one-step state transition" at prediction time; it has answered it when a
   checkpoint exists that the prediction stage can load and apply.

2. **What is the surrogate's mapping, exactly — what is the input tensor and
   what is the target?**
   Citation: `mal-core/src/mal_core/training/model.py:1-5` (docstring: input
   `(state_t + env)`, target `state_{t+1}`); `mal-core/src/mal_core/training/model.py:29-30`
   (default `in_channels=6`, `out_channels=2`).
   Answer: the network maps the current ABM state stack concatenated with an
   environmental stack onto the *next* state stack; the channel counts are not
   fixed — they are inferred from the data at run time (see Q14).

3. **What is the temporal horizon of one training example?**
   Citation: `mal-core/src/mal_core/training/dataset.py:141-146` (pairs are
   built from *consecutive* days present in the directory: `sorted_days[i]` and
   `sorted_days[i+1]`).
   Answer: one simulated day — the pairs are the two consecutive daily
   snapshots present in the run directory, so the surrogate learns a one-day
   transition.
   Note: the retired training specification (INV-6) claimed a fixed 7-day
   step (`state_t → state_{t+7}`); the code pairs consecutive days
   (`mal-core/src/mal_core/training/dataset.py:136-141`). The specification was
   wrong here — the audit trail is `docs/plans/in-process/spec-retirement-ledger.md`.

4. **What can the surrogate not represent, and where is that stated?**
   Citation: `mal-core/src/mal_core/training/model.py:1-5`; the structural
   limitation follows from Q3 and Q15.
   Answer: it is a purely local, one-day, per-pixel transition approximator: it
   has no memory of history beyond the single input state, it is trained only
   on the ABM rollouts supplied in `run_dir`, and it cannot reproduce
   mechanisms the rollouts never exhibited (e.g. a different intervention
   regime, a different AOI, or an ABM version newer than the training data).
   The document must state this where the surrogate is first introduced, not
   only in a limitations appendix.

5. **Is the surrogate a *model of the ABM* or a *model of one ABM step*?**
   Citation: `mal-core/src/mal_core/prediction/predictor.py:89` (the
   prediction stage calls `model.predict(state, env)` exactly once, and then
   aggregates the output into a risk map).
   Answer: a model of one step. Nothing in the code rolls the surrogate
   forward over a horizon to produce a multi-day trajectory; the prediction
   stage applies it once per invocation.

6. **Is the surrogate's output the same quantity the ABM emits?**
   Citation: `mal-core/src/mal_core/abm/include/mal_abm_fast/wire.hpp:129`
   (state band names `adult_patch_count`, `adult_cell_count`);
   `mal-core/src/mal_core/abm/src/output_contract.cpp:273` (contract 4.0:
   the `k_max` key was removed; bands carry raw counts).
   Answer: yes — the training targets are the ABM's own raw per-cell adult
   counts under state-output contract 4.0, *not* normalised densities. The
   retired `K_MAX` normalisation is absent from the training path.

### B. Training data: how it is found, assembled and split

7. **Which files are the training data, and how are they discovered?**
   Citation: `mal-core/src/mal_core/training/dataset.py:90-97` (all `*.tif` in
   `run_dir`; those with `_day` in the name and *not* `transmission` are the
   state series; `*_day*.npy` is the fallback; TIFF is preferred when the
   counts are equal or greater).
   Answer: the daily state snapshots of the ABM run, plus (optionally) the
   daily transmission snapshots, discovered by globbing `run_dir`.
   Note: the retired training specification (INV-7) described a narrower glob
   (`state_seed*_day*.{npy,tif}`) and band-name-based reading; the code globs
   more loosely and reads bands positionally
   (`mal-core/src/mal_core/training/dataset.py:92-97`).

8. **What are the ABM's own file-name conventions that this discovery relies
   on?**
   Citation: `mal-core/src/mal_core/abm/src/main.cpp:183` (`<stem>_dayNNN.tif`);
   `mal-core/src/mal_core/abm/src/main.cpp:228` (`<stem>_dayNNN.tif` for the
   transmission raster too).
   Answer: both the state and the transmission series are `<stem>_dayNNN.tif`;
   the two are told apart only by the substring `transmission` in the file name.

9. **How are series and seeds identified, and how are pairs formed?**
   Citation: `mal-core/src/mal_core/training/dataset.py:25-36` (seed and day
   parsed from the file name by regular expression);
   `mal-core/src/mal_core/training/dataset.py:99-113` (grouping per seed and
   per day); `mal-core/src/mal_core/training/dataset.py:141-146`.
   Answer: the seed and day are recovered from the file name; snapshots are
   grouped per seed into a day-indexed series, and the training pairs are
   consecutive days of the same seed. A file whose name carries neither
   `seedN` nor `_dayN` falls back to seed 1 / day 0
   (`dataset.py:27-31`).

10. **How is a raster turned into a training tile?**
    Citation: `mal-core/src/mal_core/training/dataset.py:19` (`PATCH_SIZE = 128`);
    `mal-core/src/mal_core/training/dataset.py:128-134` (patch grid counts
    `H // patch_size`, `W // patch_size`); `mal-core/src/mal_core/training/dataset.py:205-232`
    (crop, and zero-pad an edge tile if the raster is not an exact multiple).
    Answer: the raster is cut into 128×128 tiles on a regular grid; tiles at
    the right/bottom edge are zero-padded. Raster remainder (when
    `H % 128 != 0`) is therefore **not** represented in training.

11. **What is the train/validation split rule, and is it spatial or temporal?**
    Citation: `mal-core/src/mal_core/training/dataset.py:131` (`mid_col = W // 2`);
    `mal-core/src/mal_core/training/dataset.py:149-153` (a tile is `val` iff
    its first column index `c * patch_size >= mid_col`, else `train`).
    Answer: the split is **spatial and per-tile**: tiles west of the raster's
    mid-column are training, tiles east of it are validation. The same
    rollout (seed) contributes tiles to both splits, and adjacent tiles on
    either side of the boundary are spatially adjacent — the validation set is
    not independent of the training set in the usual sense.
    Note: the retired training specification (INV-8) stated the same rule but
    described it as "west of 0° longitude"; the code splits at the raster's
    mid-column (`mal-core/src/mal_core/training/dataset.py:129-151`), which is a
    geographic statement only if the raster happens to straddle the prime
    meridian.

12. **Are there any further defences against train/val leakage or overfitting?**
    Citation: `mal-core/src/mal_core/training/dataset.py:149-155` (the only
    split test); `mal-core/src/mal_core/training/trainer.py:57-93` (the loop).
    Answer: **open** — no shuffling-by-seed, no held-out seed, no
    geographically buffered split, no cross-validation and no early stopping
    were found; the only regularisation in the code is the split rule itself.
    The document must say plainly that the validation score is an in-region,
    adjacent-tile score.

13. **What is the training-set size and how does subsampling work?**
    Citation: `mal-core/src/mal_core/training/dataset.py:166-170`
    (`np.random.seed(42)`; keep `max(1, int(len(patches) * subsample))` tiles,
    sampled without replacement).
    Answer: `subsample < 1` keeps a random, reproducible fraction of the
    tiles; the RNG seed is fixed at 42, so the subsample is the same subset on
    every run for the same run directory.

14. **What are the channels of the input tensor and of the target tensor, and
    how are they decided?**
    Citation: `mal-core/src/mal_core/training/dataset.py:20-22` (constants
    `VECTOR_CHANNELS=2`, `TRANSMISSION_CHANNELS=4`, `ENV_CHANNELS=4`);
    `mal-core/src/mal_core/training/dataset.py:236-252` (state ⊕ transmission ⊕
    env concatenation); `mal-core/src/mal_core/training/trainer.py:50-54`
    (`in_channels`/`out_channels` are read off a sample of the dataset, not
    fixed).
    Answer: the input is `state (2) ⊕ transmission (4, optional) ⊕ env (4)`
    and the target is `state (2) ⊕ transmission (4, optional)`. With
    transmission enabled the shapes are 10→6; without it, 6→2. The channel
    counts are *derived from the data*, so a run whose rasters have an
    unexpected band count produces a model with that count.
    Note: `VECTOR_CHANNELS` and `TRANSMISSION_CHANNELS` are declared but never
    used anywhere in the package (only `ENV_CHANNELS` is used) — the state and
    transmission band counts are in fact taken from the rasters themselves
    (`dataset.py:211-213`, `dataset.py:238`).

15. **Where does the environmental stack come from, and which variables does it
    contain?**
    Citation: `mal-core/src/mal_core/training/dataset.py:66-88` (NetCDF path:
    variables drawn in the order `rainfall, air_temp_c, jrc_persistent,
    lc_built, lc_wetland, lc_open_plus_water, lc_crop`, then **truncated to the
    first `ENV_CHANNELS = 4`**; GeoTIFF path: the first four bands, zero-padded
    if fewer); `mal-core/src/mal_core/training/dataset.py:246-250` (a tile
    outside the environmental raster's extent gets all-zero environmental
    channels).
    Answer: the environmental context is read **once**, at dataset
    construction, from a NetCDF or GeoTIFF given by `--env-path`; it is a
    static stack of four planes. When the file cannot be read, the whole
    environmental stack is silently discarded and every environmental channel
    is zero (`dataset.py:87-88`) — the network then trains without any
    environmental context, and nothing reports this.

16. **Does the environmental stack vary in time, and is that a limitation?**
    Citation: `mal-core/src/mal_core/training/dataset.py:66-88` (one static
    cache for the whole dataset, `self._env_cache`);
    `mal-core/src/mal_core/training/dataset.py:57` (`self._env_cache`).
    Answer: no — one environmental snapshot serves every training pair, even
    though the real rainfall plane is daily. The surrogate therefore cannot
    learn the effect of a rainfall event on the next day's state.
    Note: the "env zero-fill" known limitation of the retired training
    specification is stale: the zero-fill still exists as a *fallback*
    (`dataset.py:246-249`), but with `--env-path` supplied the real planes are
    used (`dataset.py:66-88`).

17. **Does the training environmental channel order match the one the
    prediction stage uses at inference?**
    Citation: training — `mal-core/src/mal_core/training/dataset.py:72-73`
    (first four of `rainfall, air_temp_c, jrc_persistent, lc_built, …`);
    inference — `mal-core/src/mal_core/prediction/env_loader.py:17-18`
    (`ENV_CHANNEL_ORDER = ["rainfall", "air_temp_c", "jrc_persistent",
    "lc_wetland"]`).
    Answer: **no — the fourth plane differs** (`lc_built` when training,
    `lc_wetland` when predicting). A checkpoint trained with `--env-path`
    therefore receives, at inference time, a channel it was never trained on
    and omits one it was trained on. This is a defect at the training↔prediction
    seam and the document must state it.

18. **How is the transmission state handled when it is absent?**
    Citation: `mal-core/src/mal_core/training/dataset.py:119-127`
    (transmission files are indexed per seed/day);
    `mal-core/src/mal_core/training/dataset.py:150-153` and
    `dataset.py:236-243` (the transmission channels are concatenated only if
    both the current and the next day's transmission rasters exist for that
    pair).
    Answer: transmission channels are attached to a pair only when *both* days
    have a transmission raster; otherwise the pair is trained as a
    state-only pair. This makes the input width of a dataset non-uniform in
    principle, although in practice it is uniform per run directory because
    the series are generated together.

19. **What happens to no-data values and to dtype?**
    Citation: `mal-core/src/mal_core/training/dataset.py:183-186` (rasters are
    read as float32 and cells equal to the file's declared no-data value are
    set to 0.0); `mal-core/src/mal_core/training/dataset.py:211-213` (the
    `.npy` fallback is cast to float32 and given a channel axis if 2-D).
    Answer: no-data becomes 0.0, which is the same value as "no adults" — the
    surrogate cannot distinguish "no data" from "no mosquitoes".

20. **Is there any data provenance recorded for the training set?**
    Citation: `mal-core/src/mal_core/training/trainer.py:96-105` (the
    `model.yaml` manifest records the run directory only inside a free-text
    `description`).
    Answer: **open** — the manifest does not record the ABM version, the
    AOI, the number of seeds, the number of days, the patch size, the split
    rule, the data contract version, or the date of training. The document
    must record which of these the checkpoint does *not* carry.

### C. Model and loss

21. **What is the architecture?**
    Citation: `mal-core/src/mal_core/training/model.py:14-25` (double
    convolution block: 3×3 convolution without bias → batch norm → ReLU,
    twice); `mal-core/src/mal_core/training/model.py:28-46` (four encoder
    stages with widths 32/64/128/256, a 2×2 max-pool, a bottleneck of double
    width, transposed-convolution upsampling, concatenation skip connections,
    and a 1×1 output head).
    Answer: a standard U-Net with four resolution levels, batch normalisation
    and ReLU activations, and skip connections by concatenation.

22. **How are the skip connections and the output assembled, and what happens
    if the input size is not a multiple of the pooling factor?**
    Citation: `mal-core/src/mal_core/training/model.py:48-60` (encoder
    features are popped in reverse order and concatenated; a spatial mismatch
    is resolved by bilinear interpolation to the skip's size);
    `mal-core/src/mal_core/training/wrapper.py:93-104` (at inference the
    input is padded with replicate padding to a multiple of 16 and the result
    is cropped back).
    Answer: mismatched sizes are repaired by interpolation (forward) or
    replicate padding to a multiple of 16 (inference wrapper). With
    128×128 training tiles and four pooling stages the two agree, so the
    interpolation branch is not exercised in training.

23. **What is the loss, and what does each term see?**
    Citation: `mal-core/src/mal_core/training/model.py:77-83` (the loss is
    the MSE over **all** channels plus `0.5 ×` a soft-Dice term computed on
    **channel 0 only**).
    Answer: `loss = MSE(pred, target) + 0.5 · soft_dice(pred[:, 0], target[:, 0])`;
    the Dice term is deliberately restricted to the first (adult-count) channel
    because it is the sparse one.

24. **How is the soft-Dice term computed, and what are its temperature and
    threshold?**
    Citation: `mal-core/src/mal_core/training/model.py:63-74`
    (`p = sigmoid((pred − thresh)/tau)`, `t = sigmoid((target − thresh)/tau)`,
    `tau = 0.5`, `thresh = 0.5`, a `1e-6` stabiliser in numerator and
    denominator).
    Answer: a sigmoid-smoothed Dice over the whole batch and the whole tile,
    with temperature 0.5 and a decision threshold of 0.5 — which, under
    contract 4.0, means "one adult or more in the cell".
    Note: the retired training specification stated `tau=0.1, thresh=0.01`
    (INV-4) and `eval_dice(thresh=0.01)`. The code uses `tau=0.5, thresh=0.5`
    (`mal-core/src/mal_core/training/model.py:63`) — the specification was stale
    on both.

25. **How is the validation metric defined, and in what units is its
    threshold?**
    Citation: `mal-core/src/mal_core/training/model.py:86-95` (hard Dice on
    channel 0 with `thresh = 0.5`, i.e. cells with at least one adult).
    Answer: hard Dice on the first channel at 0.5 adults per cell, averaged
    over the validation batches.
    Note: the retired training specification claimed `thresh=0.01`, which
    under contract 4.0 raw counts would mean a fraction of an adult; the code
    (`mal-core/src/mal_core/training/model.py:86`) is the authority.

26. **What does the metric not measure?**
    Citation: `mal-core/src/mal_core/training/model.py:80` and
    `mal-core/src/mal_core/training/model.py:91` (both operate on channel 0
    only).
    Answer: the Dice score says nothing about the second state band
    (`adult_cell_count`) nor about the four transmission bands; those are
    trained only through the MSE term, and their accuracy is never measured.
    The document must say that the reported "best val_dice" characterises one
    band of one output, not the surrogate.

27. **Is the model output bounded or activated in any way?**
    Citation: `mal-core/src/mal_core/training/model.py:46` (the head is a bare
    1×1 convolution — no sigmoid or softplus); `mal-core/src/mal_core/training/model.py:69-70`
    (the sigmoid is applied inside the loss, not on the output).
    Answer: the network emits unbounded real numbers; a "predicted adult
    count" can therefore come out negative or fractional. Nothing clamps it,
    in training or at inference (`mal-core/src/mal_core/training/wrapper.py:106`
    returns the raw float32 array).

### D. Optimisation, and what stands in for early stopping

28. **What optimiser and learning rate are used?**
    Citation: `mal-core/src/mal_core/training/trainer.py:55` (`Adam(model.parameters(), lr=lr)`);
    `mal-core/src/mal_core/training/trainer.py:14-24` (default `lr = 1e-3`);
    `mal-core/src/mal_core/cli.py:778` (CLI default `1e-3`).
    Answer: Adam at 1e-3, with no learning-rate schedule, no weight decay and
    no momentum configuration beyond Adam's defaults.

29. **Is there a learning-rate schedule, an early-stopping criterion, or a
    patience setting?**
    Citation: `mal-core/src/mal_core/training/trainer.py:57-93` (the epoch
    loop; the only conditionals are the checkpoint writes).
    Answer: **no**. There is no scheduler, no early stopping, no patience
    counter, and no gradient clipping. The loop always runs the full number of
    epochs.

30. **How is "the best model" chosen, and what is the selection rule's exact
    form?**
    Citation: `mal-core/src/mal_core/training/trainer.py:57` (`best_dice = 0.0`);
    `mal-core/src/mal_core/training/trainer.py:86-88` (`if val_dice >= best_dice
    or epoch == 0:` — the checkpoint is written and `best_dice` updated).
    Answer: the checkpoint is rewritten whenever the validation Dice is **at
    least** the best seen so far (so ties also overwrite), and unconditionally
    at the first epoch. Because the loop never stops, "best" is a running
    maximum over all epochs, not an early-stopped model.
    Note: the retired training specification (INV-12) said "strictly greater";
    the comparison is `>=`
    (`mal-core/src/mal_core/training/trainer.py:85-91`).

31. **What is reported to the operator during and after training?**
    Citation: `mal-core/src/mal_core/training/trainer.py:84` (per-epoch line
    with mean training loss and validation Dice);
    `mal-core/src/mal_core/training/trainer.py:108-109` (final line and the
    returned value — the best validation Dice).
    Answer: one line per epoch, and the best validation Dice as the function's
    return value, echoed by the CLI (`mal-core/src/mal_core/cli.py:806`).

32. **Is training reproducible?**
    Citation: `mal-core/src/mal_core/training/dataset.py:167` (only the
    subsampling RNG is seeded); `mal-core/src/mal_core/training/trainer.py:57-93`
    (no seeding of torch, numpy or the data loader).
    Answer: **no, not end-to-end.** Only the tile subsample is seeded; torch's
    global RNG is never seeded, the training loader shuffles
    (`mal-core/src/mal_core/training/dataset.py:281-284`) with an unseeded
    generator, and the weights are initialised from torch's default RNG. Two
    runs on the same data will differ.

33. **On which device does training run, and how is it chosen?**
    Citation: `mal-core/src/mal_core/training/trainer.py:29-35` (CUDA, else
    Apple MPS, else CPU); the same resolution is repeated in the inference
    wrapper at `mal-core/src/mal_core/training/wrapper.py:31-38`.
    Answer: CUDA if available, otherwise Apple MPS, otherwise CPU; the choice
    is not recorded in any artefact.

34. **What happens if the training directory contains no usable snapshots?**
    Citation: `mal-core/src/mal_core/training/dataset.py:100-101`
    (`FileNotFoundError` when no `*_day*.tif/npy` file exists);
    `mal-core/src/mal_core/training/trainer.py:47-48` (`ValueError` when the
    training split is empty).
    Answer: an explicit error in both cases; an empty **validation** split is
    not an error — it silently produces `val_dice = 0.0` for every epoch
    (`trainer.py:75-82`), so `best_model.pt` is then simply the first epoch's
    weights.

### E. Checkpoints, manifest, and how a checkpoint is loaded

35. **What files does the training stage write?**
    Citation: `mal-core/src/mal_core/training/trainer.py:88` (`best_model.pt`);
    `mal-core/src/mal_core/training/trainer.py:90-91` (`model_epoch_{N}.pt`
    every 10th epoch); `mal-core/src/mal_core/training/trainer.py:93`
    (`final_model.pt`); `mal-core/src/mal_core/training/trainer.py:96-106`
    (`model.yaml`).
    Answer: three kinds of PyTorch checkpoint (best, periodic, final) plus one
    YAML manifest in the output directory.

36. **What is the format of a checkpoint?**
    Citation: `mal-core/src/mal_core/training/trainer.py:88` (all three are
    `torch.save(model.state_dict(), …)`).
    Answer: a bare `state_dict` — parameters and buffers only. No optimiser
    state, no epoch counter, no metric history, no RNG state, no architecture
    description, no scaler. Resuming training from a checkpoint is therefore
    impossible; a checkpoint can only be used for inference.

37. **What does the manifest contain, and what is its version?**
    Citation: `mal-core/src/mal_core/training/trainer.py:96-105` (keys:
    `name` — the output directory's own name, `version` "1.0",
    `contract_version` "1.1", `in_channels`, `out_channels`,
    `checkpoint` "best_model.pt", `description`).
    Answer: a small YAML manifest identifying the model by directory name and
    version. Two things it does **not** carry: the ABM state-contract version
    (the checkpoints were trained on contract-4.0 raw counts, and nothing
    records that) and the training-data provenance.

38. **How is a checkpoint loaded for inference, and how are the channel counts
    recovered?**
    Citation: `mal-core/src/mal_core/training/wrapper.py:39-46` (the manifest
    beside the checkpoint is read first for `in_channels`/`out_channels`);
    `mal-core/src/mal_core/training/wrapper.py:51-59` (otherwise the shapes
    are inferred from the first encoder convolution's weights and the head's
    weights, with fallbacks 6 and 2);
    `mal-core/src/mal_core/training/wrapper.py:64-67` (the model is rebuilt and
    the state dict loaded strictly, then put in evaluation mode).
    Answer: the wrapper reads the manifest next to the checkpoint, falls back
    to inferring the shapes from the tensors themselves, rebuilds the U-Net and
    loads the weights with `load_state_dict` (strict). The load is eager: a
    missing or mismatched checkpoint raises at construction.

39. **What happens if the channels presented at inference do not match the
    trained model?**
    Citation: `mal-core/src/mal_core/training/wrapper.py:76-86` (missing
    channels are zero-padded, surplus channels are truncated).
    Answer: the wrapper silently adapts — padding with zeros or truncating —
    rather than refusing. A mismatch therefore produces a prediction from a
    network that was never trained for that input, with no warning.

40. **How does the prediction stage obtain the model?**
    Citation: `mal-core/src/mal_core/prediction/registry.py:61-64` (the
    registry scans `runs/models/` and `runs/` for `model.yaml`);
    `mal-core/src/mal_core/prediction/registry.py:96-118` (`load()` returns a
    `DummyModel` for the name "dummy" or when the manifest declares no
    checkpoint, otherwise it builds a `UNetWrapper` from
    `manifest.checkpoint`).
    Answer: through a directory scan for `model.yaml` files, keyed by
    `name@version`; the checkpoint path is resolved relative to the manifest's
    directory. Without a trained model the prediction stage emits zeros
    (`registry.py:41-46`).

### F. The seam with the prediction stage

41. **What exactly does the prediction stage hand to the surrogate, and what
    does it do with the answer?**
    Citation: `mal-core/src/mal_core/prediction/predictor.py:84-91` (real ABM
    state via `load_abm_state`, environmental stack via `load_env_stack`, one
    call to `model.predict`, then aggregation by scale);
    `mal-core/src/mal_core/prediction/predictor.py:28-40` (band names of the
    emitted risk map).
    Answer: the state stack (2 vector bands ⊕ 4 transmission bands when
    available) and a 4-plane environmental stack are given to the surrogate
    once; the returned channels are aggregated to the requested scale and
    written as a risk GeoTIFF with a sidecar.

42. **Do the training-time and inference-time state stacks have the same
    channel semantics?**
    Citation: training — `mal-core/src/mal_core/training/dataset.py:236-243`
    (state ⊕ transmission); inference —
    `mal-core/src/mal_core/prediction/state_loader.py:36` and
    `state_loader.py:99-140` (the state raster is bilinearly reprojected to
    the AOI grid and the transmission raster is appended when present).
    Answer: the same two vector bands and the same optional four transmission
    bands, but the inference path resamples to the AOI grid with bilinear
    interpolation while the training path crops raw ABM pixels. The surrogate
    is therefore applied to an interpolated grid it was never trained on.

43. **Is the prediction-stage input channel count the one the model was
    trained with?**
    Citation: `mal-core/src/mal_core/prediction/predictor.py:54-66`
    (the state stack is loaded with `include_transmission=True`, giving 6
    channels, and falls back to zeros of 6 channels on failure);
    `mal-core/src/mal_core/prediction/registry.py:112-118` (the wrapper is
    built with the manifest's channel counts).
    Answer: only if the checkpoint was trained with transmission enabled and
    the transmission raster was found at inference time; the registry's
    explicit `in_channels`/`out_channels` are passed to the wrapper, which
    then pads or truncates the input to fit (Q39).

44. **Is the surrogate ever validated against the ABM it replaces?**
    Citation: `mal-core/src/mal_core/prediction/predictor.py:89` (the
    surrogate's output goes straight into the risk map);
    `mal-core/tests/test_training_pipeline.py:92-113` (the end-to-end test
    asserts that files exist and that the wrapper returns a tensor of the
    right shape).
    Answer: **no**. There is no comparison of surrogate output against a
    subsequent ABM step, no accuracy floor, and no regression test that a
    retrained checkpoint stays within a Dice tolerance. The pytest file for
    this stage checks shapes, file presence and end-to-end plumbing only.
    The document must say that the surrogate's fidelity is not gated anywhere.

45. **What is the surrogate not allowed to be used for?**
    Citation: `mal-core/src/mal_core/prediction/predictor.py:28-40` (the output
    is a "predicted risk" map); `mal-core/src/mal_core/training/model.py:1-5`
    (one-step state transition).
    Answer: the surrogate's output is a risk map, not a population
    projection: it is a single one-day local transition applied to a snapshot,
    and it does not yield trajectories, prevalence over time, or intervention
    scenarios unless the ABM rollouts it learned from contained them.

### G. What is not implemented

46. **Is there a calibration or acceptance harness for the surrogate?**
    Citation: `mal-core/tests/test_training_pipeline.py:1-113` (the whole file:
    shape, loss, dataset and end-to-end plumbing);
    `mal-core/src/mal_core/training/` (no threshold constants, no
    `thresholds.yaml`, no scorer registry).
    Answer: no. There is no scorer, no Dice floor, no tolerance band and no
    scorecard for the surrogate — the calibration framework of the ABM
    (`mal-core/src/mal_core/abm/tests/calibration/`) has no training-side
    counterpart. The only "best" concept is the running maximum of the
    validation Dice.

47. **Are the hyperparameters of this stage generated from the shared
    configuration?**
    Citation: `mal-core/config/model_constants.yaml` (no key mentions
    training, the surrogate, the U-Net, Dice or epochs — verified by
    searching the file);
    `mal-core/src/mal_core/training/trainer.py:14-24` and
    `mal-core/src/mal_core/training/dataset.py:19-22` (the values are literals
    in the source).
    Answer: no. Every hyperparameter of this stage — patch size, channel
    widths, learning rate, epochs, batch size, loss weight 0.5, `tau` 0.5,
    `thresh` 0.5, the Dice stabiliser 1e-6, the subsample seed 42, the
    checkpoint period 10 — is a literal in the code. The document must source
    each of them from a generated table, and the reviewer must be told that
    today those numbers have no single source of truth.

48. **Which CLI options exist, and which function parameters are unreachable
    from the CLI?**
    Citation: `mal-core/src/mal_core/cli.py:773-808` (`--run-dir`,
    `--output-dir`, `--epochs`, `--batch-size`, `--lr`,
    `--include-transmission/--no-transmission`, `--env-path`);
    `mal-core/src/mal_core/training/trainer.py:14-24` (`device`, `subsample`,
    `preload` are parameters of `train_unet` but are not exposed by the CLI).
    Answer: the CLI exposes seven options; `subsample`, `preload` and `device`
    are reachable only from the Python API.

49. **Do the standalone execution scripts differ from the packaged trainer?**
    Citation: `mal-execution/scripts/train_unet.py`,
    `mal-execution/scripts/train_unet_subsample.py`,
    `mal-execution/scripts/validate_unet.py`.
    Answer: **open** — these scripts were not read line by line for this
    question set; they are noted here because the retired training
    specification described them (and described `train_unet_subsample.py` as
    using "an older import path"), which needs checking before the document
    claims anything about them.

50. **Are the retired spec's claims safe to reuse?**
    Citation: `mal-core/src/mal_core/training/model.py:63` (`tau=0.5,
    thresh=0.5`), `:86` (`eval_dice` threshold 0.5),
    `dataset.py:136-141` (consecutive-day pairs), `dataset.py:92-97` (the
    discovery glob), `dataset.py:66-88` (the env is loaded when a path is
    given), `trainer.py:85-91` (the ">= best" comparison).
    Answer: no — five of its invariants are contradicted by the code as cited
    above. The document must be written against the code, and must not cite
    the retired specification as authority. The full audit trail is
    `docs/plans/in-process/spec-retirement-ledger.md`.

---

## (b) Done-checklist

- [ ] The surrogate's purpose (fast one-step emulation of the ABM for the
      prediction stage) and its explicit limits (one day, one step, per-tile,
      learned only from the rollouts supplied) are stated **at the point where
      the surrogate is first introduced**, not only in a closing section.
      (§A Q1–Q6)
- [ ] The mapping `(state_t ⊕ env) → state_{t+1}` is stated with the channel
      composition in both configurations (with and without transmission) and
      with the fact that the channel counts are derived from the data, not
      fixed. (Q2, Q14)
- [ ] The data assembly is stated end to end: file discovery, seed/day
      parsing, pairing rule, 128×128 tiling, edge zero-padding, no-data
      handling, dtype. (Q7–Q10, Q19)
- [ ] The split is stated as spatial and per-tile at the raster mid-column,
      with its exact rule, with the explicit warning that a single rollout
      contributes to both splits and that validation tiles are adjacent to
      training tiles. (Q11, Q12)
- [ ] The environmental stack is stated with its four variables, their
      ordering, its static (non-temporal) nature, the silent fallback to zeros
      when unreadable, and the mismatch with the prediction stage's fourth
      channel. (Q15–Q17)
- [ ] The model is stated in prose: four resolution levels, widths, batch
      norm + ReLU, concatenation skips, transposed-convolution upsampling,
      bottleneck, output head, and the unbounded (unactivated) output. (Q21,
      Q22, Q27)
- [ ] The loss is stated with its exact composition (MSE over all channels
      plus 0.5 × soft-Dice on the first channel only) and with the units of
      the thresholds under state contract 4.0 raw adult counts. (Q23–Q25)
- [ ] The metric's coverage is stated honestly: Dice characterises one band of
      one output; the second state band and the four transmission bands are
      never evaluated. (Q26)
- [ ] Optimisation is stated: Adam, learning rate, no schedule, no early
      stopping, and the exact "best" rule including that ties overwrite the
      checkpoint. (Q28–Q31)
- [ ] Reproducibility is stated: only the subsample is seeded; weights,
      shuffling and initialisation are not. (Q32)
- [ ] Device resolution and the silent-empty-validation-set behaviour are
      stated. (Q33, Q34)
- [ ] Checkpoint contents and format are stated: three files, bare
      `state_dict`, no optimiser state, no architecture, no provenance, and
      therefore no resume. (Q35–Q37)
- [ ] The manifest's keys and its two missing facts (ABM state-contract
      version, training-data provenance) are stated, including that the
      manifest names the model after its own output directory. (Q37, Q20)
- [ ] Checkpoint loading is stated: manifest first, shape inference as
      fallback, strict `load_state_dict`, eager load, and the silent
      zero-pad/truncate adaptation to mismatched channel counts. (Q38, Q39)
- [ ] The seam with the prediction stage is stated: how the prediction stage
      finds the model, what it passes in (with the bilinear reprojection the
      surrogate never saw in training), what it does with the answer, and the
      fact that it applies the surrogate exactly once. (Q40–Q45)
- [ ] The absence of any accuracy gate — no scorer, no Dice floor, no
      ABM-versus-surrogate comparison, no regression band — is stated. (Q46)
- [ ] Every hyperparameter is generated from a configuration table, not typed
      in the document, and the document states that today these values live as
      literals in the code. (Q47)
- [ ] The absence of a calibration harness for this stage, in contrast with the
      ABM's, is stated explicitly. (Q46)
- [ ] No claim in the document is sourced from the retired training
      specification; where it is mentioned, it is only to mark a contradiction
      with the code. (Q50)
- [ ] Every value that appears in the document is generated from
      `model_constants.yaml` or a generated contract table, with the
      training-stage constants added to the generation source (today they are
      absent from `model_constants.yaml`). (Q47)

---

## (c) Open questions

1. **Q12** — No mechanism prevents train/val leakage beyond the mid-column
   rule: is the intended design that the validation score is a regional
   in-sample score, or is spatial buffering expected? The code answers "no
   buffering"; the intent is not recorded anywhere.
2. **Q20** — Is the absence of training-data provenance in `model.yaml`
   deliberate, or an oversight? The manifest records only the run directory
   inside a free-text description.
3. **Q29** — The absence of early stopping, a learning-rate schedule and a
   patience rule is unambiguous in the code; whether one is *wanted* is not.
4. **Q32** — Whether end-to-end reproducibility is a requirement is not
   recorded; the code provides only partial seeding.
5. **Q37** — Whether the manifest should carry the ABM state-contract version
   (contract 4.0 raw counts) is not recorded anywhere.
6. **Q40/Q42** — Whether the training-time and inference-time environmental
   channel order (Q17) and the inference-time bilinear reprojection of the
   state stack (Q42) are known defects is not stated in the repository; they
   are visible in the code but no issue or note claims them.
7. **Q44** — Whether the surrogate's fidelity is meant to be gated against the
   ABM at some point, or whether the stage is knowingly ungated, is not
   recorded.
8. **Q47** — Whether the training hyperparameters are intended to move into
   `model_constants.yaml` (the file currently mentions nothing about training)
   is a decision that has not been taken; the document must state where the
   numbers come from as the code stands.
9. **Q49** — The three standalone scripts under `mal-execution/scripts/`
   (`train_unet.py`, `train_unet_subsample.py`, `validate_unet.py`) were not
   read for this question set. Whether they duplicate, diverge from, or
   contradict the packaged trainer is unverified; the retired training
   specification described them but it is not authoritative (its audit trail
   is `docs/plans/in-process/spec-retirement-ledger.md`).
10. **Q45** — The set of uses the surrogate must not be put to (long-horizon
    projection, intervention planning, anything requiring the mechanisms the
    rollouts did not exhibit) is inferred from the code's one-step, one-call
    structure. No written prohibition exists in the repository.
