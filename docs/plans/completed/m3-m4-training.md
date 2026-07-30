# M3-M4: U-Net Surrogate Training

## Overview

Train a U-Net surrogate on the M2 ABM rollouts (50 rollouts × 53 snapshots = 2650 state files).

**Architecture**: 4 down/up blocks, channels (32, 64, 128, 256), BN+ReLU, concat skip connections
**Loss**: MSE + soft-Dice (weighted 0.5)
**Input**: (state_t + env) = (6, 128, 128) → **Output**: state_{t+1} = (2, 128, 128)
**Train/val split**: west of 0° lon = train, east = val (geographic split)

## Training on Mac (MPS)

```bash
# Full training (all patches, 50 epochs) — ~80h on M-series Mac
uv run python mal-execution/scripts/train_unet.py runs/1year-50r runs/m3-m4-model --epochs 50

# Quick test (1% subsample, 5 epochs) — ~5 min
uv run python mal-execution/scripts/train_unet.py runs/1year-50r runs/m3-m4-test --epochs 5 --subsample 0.01

# Medium test (10% subsample, 10 epochs) — ~30 min
uv run python mal-execution/scripts/train_unet.py runs/1year-50r runs/m3-m4-test --epochs 10 --subsample 0.1
```

**Expected runtime on MPS (M-series Mac)**:
- 1% subsample: ~1 min/epoch
- 10% subsample: ~3 min/epoch
- 100% dataset: ~30 min/epoch

**Expected runtime on CUDA GPU**: ~30 min for full training

## Validation

```bash
uv run python mal-execution/scripts/validate_unet.py runs/1year-50r runs/m3-m4-model/best_model.pt runs/m3-m4-validation
```

**Acceptance criteria**: Dice > 0.6 on eastern third (held-out)

## Integration with M5

The trained U-Net can be registered in the M5 model registry:

```yaml
# runs/models/unet-v1/model.yaml
name: unet-v1
version: "1.0"
contract: "arch-abm-output-contract@v1.1"
checkpoint: runs/m3-m4-model/best_model.pt
wrapper: mal_core.UNetWrapper
```

Then use via M5 CLI:

```bash
malariasim predict --aoi ghana --scale regional --year 2026 --model unet-v1
```

## Code location

- **U-Net architecture**: `mal-core/src/mal_core/unet.py`
- **Dataset builder**: `mal-core/src/mal_core/dataset.py`
- **Training loop**: `mal-core/src/mal_core/train.py`
- **M5 wrapper**: `mal-core/src/mal_core/unet_wrapper.py`
- **Training script**: `mal-execution/scripts/train_unet.py`
- **Validation script**: `mal-execution/scripts/validate_unet.py`
