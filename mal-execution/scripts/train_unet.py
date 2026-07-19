#!/usr/bin/env python3
"""M3-M4 — Train U-Net surrogate on ABM rollouts.

Usage:
    uv run python mal-execution/scripts/train_unet.py runs/1year-50r runs/m3-m4-model --epochs 50

Note: Training is GPU-intensive. Use the Maps GPU or a machine with CUDA.
"""
import sys
from pathlib import Path

import torch

from mal_core import train_unet


def main():
    if len(sys.argv) < 3:
        print("Usage: train_unet.py <run_dir> <output_dir> [--epochs N] [--subsample F]")
        sys.exit(1)

    run_dir = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])

    epochs = 50
    subsample = 1.0
    preload = False
    if "--epochs" in sys.argv:
        idx = sys.argv.index("--epochs")
        epochs = int(sys.argv[idx + 1])
    if "--subsample" in sys.argv:
        idx = sys.argv.index("--subsample")
        subsample = float(sys.argv[idx + 1])
    if "--preload" in sys.argv:
        preload = True

    device = "cuda" if torch.cuda.is_available() else ("mps" if torch.backends.mps.is_available() else "cpu")
    print(f"Device: {device}")
    if device == "cuda":
        print(f"GPU: {torch.cuda.get_device_name(0)}")
    elif device == "mps":
        print(f"GPU: Apple MPS")

    print(f"Training U-Net on {run_dir} for {epochs} epochs...")
    print(f"Subsample: {subsample}")
    print(f"Preload: {preload}")
    print(f"Output: {output_dir}")

    best_dice = train_unet(run_dir, output_dir, epochs=epochs, subsample=subsample, preload=preload)

    print(f"\nDone! Best validation Dice: {best_dice:.4f}")
    print(f"Model saved to: {output_dir}/best_model.pt")


if __name__ == "__main__":
    main()
