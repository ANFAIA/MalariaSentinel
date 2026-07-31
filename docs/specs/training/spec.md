# training Spec

> Owns the **U-Net surrogate** that learns to emulate one ABM step.
> Reads ABM rollouts (per `abm/spec.md`), produces a checkpoint
> consumable by `prediction/spec.md`.

---

```yaml
# Machine-readable affects block — parsed by the drift-check agent.
# Bidirectional: if A affects B, B must declare affected_by A.
# `target` is the folder name under docs/specs/ (stable across KG migrations).
affects:
  - target: abm
    direction: upstream
    reason: training reads ABM rollout files; channel order, naming, dtype, NoData pinned by abm spec
    severity: breaking
  - target: prediction
    direction: downstream
    reason: prediction loads the trained checkpoint via UNetWrapper; checkpoint shape is binding
    severity: breaking
  - target: ingest
    direction: upstream
    reason: training expects env tensor per AOI/year/month (the ingest output); channel ordering matters
    severity: breaking
  - target: data
    direction: upstream
    reason: env tensor naming convention comes from data spec
    severity: non-breaking
  - target: commonlib
    direction: upstream
    reason: training reads paths under RUNS_DIR defined in commonlib
    severity: non-breaking
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
| Component | `mal-core/src/mal_core/training/` |
| Version | `v1.0` |
| Status | `stable` |
| Owner | David Flórez-Mazuera |
| Last drift check | `2026-07-30` |

## 1. Objective

The ABM is too slow to run at continental scale. Training produces a
**fast surrogate**: a U-Net that maps `(state_t, env) → state_{t+1}`
given a fixed 7-day step. Without training, every prediction would
require running the C++ ABM, which does not scale.

The trained checkpoint is the load-bearing artefact for
`prediction/spec.md`. Without it the prediction stage can only emit
zeros (`DummyModel`).

## 2. In scope

- `UNet` architecture (DoubleConv encoder/decoder, 4 down-blocks, channels `(32, 64, 128, 256)`, BN+ReLU, concat skips).
- `combined_loss(pred, target) = mse + 0.5 * soft_dice`.
- `eval_dice(pred, target)` (binary Dice at threshold `0.01`).
- `RolloutDataset(run_dir, split, patch_size=128, subsample=1.0, preload=False)` — reads state and state_{t+7} from `run_dir`.
- `get_dataloaders(run_dir, batch_size=16, num_workers=0, subsample=1.0, preload=False)`.
- `train_unet(run_dir, output_dir, *, epochs=50, batch_size=16, lr=1e-3, device=None, subsample=1.0, preload=False) -> float` (best val_dice).
- Train/val split rule: **west of 0° lon ⇒ train, east ⇒ val** (per-patch, mid-column decision).
- Checkpoint outputs: `best_model.pt` (best val_dice), `model_epoch_{N}.pt` (every 10 epochs), `final_model.pt`.
- `UNetWrapper(ckpt_path)` consumed by prediction.

## 3. Out of scope

- ABM rollout generation → `docs/specs/abm/spec.md`.
- Inference / risk map emission → `docs/specs/prediction/spec.md`.
- Data layout → `docs/specs/data/spec.md`.
- Loss-function search / hyperparameter sweeps (out of scope for v1.0; see §7).

## 4. Public API

| Symbol | Where | Notes |
|---|---|---|
| `UNet(in_channels=6, out_channels=2, channels=(32,64,128,256))` | `mal_core.training.model` | `torch.nn.Module`. Forward `(B, in_channels, 128, 128) → (B, out_channels, 128, 128)`. |
| `combined_loss(pred, target) -> (loss, mse_value, dice_value)` | `mal_core.training.model` | `mse + 0.5 * soft_dice`. |
| `eval_dice(pred, target, thresh=0.01) -> float` | `mal_core.training.model` | Binary Dice in `[0, 1]`. |
| `RolloutDataset(run_dir, split, patch_size=128, subsample=1.0, preload=False)` | `mal_core.training.dataset` | `torch.utils.data.Dataset`. |
| `get_dataloaders(run_dir, batch_size=16, num_workers=0, subsample=1.0, preload=False)` | `mal_core.training.dataset` | Returns `(train_loader, val_loader)`. |
| `train_unet(run_dir, output_dir, *, epochs=50, batch_size=16, lr=1e-3, device=None, subsample=1.0, preload=False) -> float` | `mal_core.training.trainer` | Returns best `val_dice`. |
| `UNetWrapper(ckpt_path)` | `mal_core.training.wrapper` | `ModelProtocol` for `prediction.spec.md`. `predict(state, env) -> (1, H, W)`. |
| `TRAINING_FLAGS_SCHEMA` | `mal_core.training.flags` | Pydantic-style flag dict. |
- Pipeline position: stage 5 (after scoring).

## 5. Invariants

### §5.1 Architecture

- **INV-1.** Input channels = `STATE_CHANNELS + ENV_CHANNELS = 2 + 4 = 6`. Output channels = `STATE_CHANNELS = 2`.
- **INV-2.** Encoder/decoder channel widths: `(32, 64, 128, 256)` (frozen). The bottleneck doubles the deepest width.
- **INV-3.** Patch size `PATCH_SIZE = 128`. Batches are `(B, 6, 128, 128)` input → `(B, 2, 128, 128)` target.
- **INV-4.** Loss = `mse + 0.5 * soft_dice`. Soft Dice uses `tau=0.1, thresh=0.01`.

### §5.2 Dataset & split

- **INV-5.** Inputs are state tensors from the ABM (`{state, suitability}` bands, see `abm/spec.md` §5.1 INV-1) and env tensors (see `abm/spec.md` §5.2 INV-6).
- **INV-6.** `(state_t, state_{t+7})` pairs: target file is `state_seed{seed:04d}_day{day+7:03d}.{tif,npy}`. Missing `next_file` is **silently skipped** (today).
- **INV-7.** State files are detected by glob `state_seed*_day*.{npy,tif}`. If `.tif` files exist, the reader switches to `rasterio` and reads by band name (`density`, `suitability`).
- **INV-8.** Train/val split: `mid_col = W // 2`. For each patch `(row, col)`, if `col * patch_size >= mid_col` ⇒ val; else train. Split is **per-patch, not per-rollout** (so a single rollout contributes to both splits).
- **INV-9.** Subsampling (`subsample < 1.0`) uses `np.random.seed(42)` for reproducibility.

### §5.3 Training loop

- **INV-10.** Default optimiser: `Adam(lr=1e-3)`. Default epochs `50`. Default batch size `16`.
- **INV-11.** Device resolution: `cuda` if available, else `mps` (Apple silicon), else `cpu`. **Logged but not pinned.**
- **INV-12.** `best_model.pt` is overwritten on every epoch with strictly greater `val_dice`. `model_epoch_{N}.pt` is written every 10 epochs (i.e. at `epoch ∈ {10, 20, 30, 40, 50}`). `final_model.pt` is written at the end regardless.
- **INV-13.** `subsample` and `preload` flags pass through to `get_dataloaders`. They affect memory and runtime, not the loss/dice values for the same data.

### §5.4 UNetWrapper contract

- **INV-14.** `UNetWrapper(ckpt_path).predict(state: (2,H,W) float32, env: (4,H,W) float32) -> (1,H,W) float32`. The wrapper is the contract for `prediction/spec.md` §4.
- **INV-15.** The wrapper is initialised with a checkpoint path; loading is lazy (inside `predict`). A missing checkpoint raises `FileNotFoundError` at first `predict()` call.

## 6. Data contracts

- **Input:** ABM rollouts under `run_dir` matching `state_seed*_day*.{tif,npy}`. GeoTIFF sidecars (`.json`) carry `seed`, `transform`, etc.
- **Env tensor:** produced by `ingest/spec.md` §5.1 (COG). The trainer's `RolloutDataset.__getitem__` currently zeros all env channels (known limitation — see §7).
- **Output:** PyTorch checkpoints (`.pt`) under `output_dir`. Architecture is implicit in `model.state_dict()` shape; consumers must use the matching `UNet` definition.

## 7. Migration & deprecation

- **Bumping `UNet` architecture** (channels, depth, BN placement) is a MAJOR change. Existing checkpoints become incompatible. A migration path is required (re-train or convert).
- **Bumping loss / metric** is MINOR unless it changes the optimisation landscape (in which case it's MAJOR).
- **Env channel zero-fill in `RolloutDataset.__getitem__`** (line 149) is a known limitation: the trainer does not actually load the env tensor today. Fixing this is a MAJOR change to the dataset (re-enables real env context for the U-Net). Tracked under `training/spec.md` drift check.
- Deprecation policy: 1 MINOR spec version carries the warning; removed in the next MAJOR.

## 8. Drift check

```bash
# INV-1/2: U-Net shape
uv run python -c "
import torch
from mal_core.training.model import UNet
m = UNet()
x = torch.zeros(1, 6, 128, 128)
y = m(x)
assert y.shape == (1, 2, 128, 128), f'bad shape: {y.shape}'
"

# INV-4: loss is mse + 0.5*dice
uv run python -c "
import torch
from mal_core.training.model import combined_loss
p = torch.randn(2, 2, 128, 128)
t = torch.randn(2, 2, 128, 128)
loss, mse, dice = combined_loss(p, t)
assert torch.isclose(loss, mse + 0.5 * dice), f'loss mismatch: {loss} vs {mse + 0.5 * dice}'
"

# §7 known drift: env tensor is zero-filled
rg "env = np.zeros" mal-core/src/mal_core/training/dataset.py && echo "DRIFT: env zero-fill" || echo "OK"

# INV-8: train/val split by mid-column (smoke test)
uv run python -c "
import torch
from mal_core.training.dataset import RolloutDataset
from pathlib import Path
ds = RolloutDataset(Path('runs/1year-50r'), split='train', subsample=0.01)
val_ds = RolloutDataset(Path('runs/1year-50r'), split='val', subsample=0.01)
# patches split by mid_col, so train and val are disjoint
assert set((p['row'],p['col']) for p in ds.patches) & set((p['row'],p['col']) for p in val_ds.patches) == set()
" 2>/dev/null

# INV-12: checkpoint files appear
uv run python -c "
from pathlib import Path
out = Path('runs/training')
assert (out / 'final_model.pt').exists()
"
```

## 9. Examples

```python
from pathlib import Path
from mal_core.training import train_unet

best_dice = train_unet(
    run_dir=Path("runs/1year-50r"),
    output_dir=Path("runs/training"),
    epochs=50,
    batch_size=16,
)
assert best_dice > 0.0
```

```python
# Use the trained wrapper for inference (see prediction/spec.md)
from pathlib import Path
from mal_core.training import UNetWrapper

model = UNetWrapper(Path("runs/training/best_model.pt"))
state = ...  # (2, H, W) float32 from ABM
env = ...    # (4, H, W) float32 from ingest
risk = model.predict(state, env)  # (1, H, W)
```

## 10. References

- KG ADR: `adr-spec-design-2026-07-30`.
- Specs (by folder): `abm`, `prediction`, `ingest`, `data`, `commonlib`, `pipeline`.
- External: Ronneberger et al. 2015 (U-Net original); Dice loss (Milletari et al. 2016).