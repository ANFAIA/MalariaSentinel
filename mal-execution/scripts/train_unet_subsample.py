#!/usr/bin/env python3
"""M3-M4 — Train U-Net surrogate on ABM rollouts (with subsample for speed)."""
import sys
from pathlib import Path

import numpy as np
import torch
from torch.optim import Adam
from torch.utils.data import Dataset, DataLoader

from mal_core.unet import UNet, combined_loss, eval_dice


class PreloadedRolloutDataset(Dataset):
    def __init__(self, states, targets, split="train", patch_size=128):
        self.states = states
        self.targets = targets
        self.patch_size = patch_size
        self.patches = []
        self._build_patches(split)

    def _build_patches(self, split):
        n_rollouts, C, H, W = self.states.shape
        n_patches_h = H // self.patch_size
        n_patches_w = W // self.patch_size
        mid_col = W // 2

        for i in range(n_rollouts):
            for r in range(n_patches_h):
                for c in range(n_patches_w):
                    is_east = (c * self.patch_size) >= mid_col
                    patch_split = "val" if is_east else "train"
                    if patch_split == split:
                        self.patches.append((i, r * self.patch_size, c * self.patch_size))

    def __len__(self):
        return len(self.patches)

    def __getitem__(self, idx):
        i, r, c = self.patches[idx]
        state = self.states[i, :, r:r+self.patch_size, c:c+self.patch_size]
        target = self.targets[i, :, r:r+self.patch_size, c:c+self.patch_size]
        env = np.zeros((4, self.patch_size, self.patch_size), dtype=np.float32)
        x = np.concatenate([state, env], axis=0)
        return torch.from_numpy(x), torch.from_numpy(target)


def train_unet_subsample(npy_dir, output_dir, epochs=50, batch_size=16, lr=1e-3, max_rollouts=None):
    npy_dir = Path(npy_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("Loading rollouts into memory...")
    state_files = sorted(npy_dir.glob("state_seed*_day*.npy"))
    
    if max_rollouts:
        state_files = state_files[:max_rollouts]
        print(f"Using {max_rollouts} rollouts (subsample)")
    
    states = []
    targets = []
    for state_file in state_files:
        seed = int(state_file.stem.split("_seed")[1].split("_")[0])
        day = int(state_file.stem.split("_day")[1])
        next_day = day + 7
        next_file = state_file.parent / f"state_seed{seed:04d}_day{next_day:03d}.npy"
        if not next_file.exists():
            continue
        states.append(np.load(state_file))
        targets.append(np.load(next_file))
    
    states = np.stack(states, axis=0)
    targets = np.stack(targets, axis=0)
    print(f"Loaded {len(states)} rollouts: states {states.shape}, targets {targets.shape}")

    train_ds = PreloadedRolloutDataset(states, targets, split="train")
    val_ds = PreloadedRolloutDataset(states, targets, split="val")
    print(f"Train patches: {len(train_ds)}, Val patches: {len(val_ds)}")

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False, num_workers=0)

    device = "cuda" if torch.cuda.is_available() else ("mps" if torch.backends.mps.is_available() else "cpu")
    print(f"Device: {device}")

    model = UNet().to(device)
    optimizer = Adam(model.parameters(), lr=lr)

    best_dice = 0.0
    for epoch in range(epochs):
        model.train()
        train_loss = 0.0
        for x, y in train_loader:
            x, y = x.to(device), y.to(device)
            pred = model(x)
            loss, mse_val, dice_val = combined_loss(pred, y)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            train_loss += loss.item()
        train_loss /= len(train_loader)

        model.eval()
        val_dice = 0.0
        with torch.no_grad():
            for x, y in val_loader:
                x, y = x.to(device), y.to(device)
                pred = model(x)
                val_dice += eval_dice(pred, y)
        val_dice /= len(val_loader)

        print(f"Epoch {epoch+1}/{epochs} - train_loss: {train_loss:.4f} - val_dice: {val_dice:.4f}")

        if val_dice > best_dice:
            best_dice = val_dice
            torch.save(model.state_dict(), output_dir / "best_model.pt")

        if (epoch + 1) % 10 == 0:
            torch.save(model.state_dict(), output_dir / f"model_epoch_{epoch+1}.pt")

    torch.save(model.state_dict(), output_dir / "final_model.pt")
    print(f"Training complete. Best val_dice: {best_dice:.4f}")
    return best_dice


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: train_unet_subsample.py <npy_dir> <output_dir> [--epochs N] [--max-rollouts M]")
        sys.exit(1)

    npy_dir = sys.argv[1]
    output_dir = sys.argv[2]
    epochs = 50
    max_rollouts = None
    if "--epochs" in sys.argv:
        idx = sys.argv.index("--epochs")
        epochs = int(sys.argv[idx + 1])
    if "--max-rollouts" in sys.argv:
        idx = sys.argv.index("--max-rollouts")
        max_rollouts = int(sys.argv[idx + 1])

    print(f"Training U-Net on {npy_dir} for {epochs} epochs...")
    if max_rollouts:
        print(f"Using {max_rollouts} rollouts (subsample)")
    print(f"Output: {output_dir}")

    best_dice = train_unet_subsample(npy_dir, output_dir, epochs=epochs, max_rollouts=max_rollouts)

    print(f"\nDone! Best validation Dice: {best_dice:.4f}")
    print(f"Model saved to: {output_dir}/best_model.pt")
