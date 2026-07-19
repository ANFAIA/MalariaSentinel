#!/usr/bin/env python3
"""M3-M4 — Validate U-Net on held-out eastern third.

Usage:
    uv run python mal-execution/scripts/validate_unet.py runs/1year-50r runs/m3-m4-model/best_model.pt runs/m3-m4-validation
"""
import sys
from pathlib import Path

import numpy as np
import rasterio
import torch
from torch.utils.data import DataLoader

from mal_core import UNet, RolloutDataset, eval_dice


def main():
    if len(sys.argv) < 4:
        print("Usage: validate_unet.py <run_dir> <model_path> <output_dir>")
        sys.exit(1)

    run_dir = Path(sys.argv[1])
    model_path = Path(sys.argv[2])
    output_dir = Path(sys.argv[3])
    output_dir.mkdir(parents=True, exist_ok=True)

    device = "cuda" if torch.cuda.is_available() else ("mps" if torch.backends.mps.is_available() else "cpu")
    print(f"Loading model from {model_path} on {device}...")

    model = UNet().to(device)
    model.load_state_dict(torch.load(model_path, map_location=device, weights_only=True))
    model.eval()

    val_ds = RolloutDataset(run_dir, split="val")
    val_loader = DataLoader(val_ds, batch_size=8, shuffle=False)

    all_dice = []
    for x, y in val_loader:
        x, y = x.to(device), y.to(device)
        with torch.no_grad():
            pred = model(x)
            dice = eval_dice(pred, y)
            all_dice.append(dice)

    mean_dice = np.mean(all_dice)
    print(f"\nValidation Dice: {mean_dice:.4f} (target: > 0.6)")

    if mean_dice > 0.6:
        print("✓ PASS: Dice > 0.6")
    else:
        print("✗ FAIL: Dice ≤ 0.6")

    with open(output_dir / "validation_results.txt", "w") as f:
        f.write(f"Validation Dice: {mean_dice:.4f}\n")
        f.write(f"Target: > 0.6\n")
        f.write(f"Status: {'PASS' if mean_dice > 0.6 else 'FAIL'}\n")

    print(f"Results saved to: {output_dir}/validation_results.txt")


if __name__ == "__main__":
    main()
