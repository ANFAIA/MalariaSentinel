"""M3-M4 — Dataset builder for U-Net training.

Reads ABM rollouts from runs/1year-50r/, tiles into 128x128 patches,
builds (state_t + env) -> state_{t+1} pairs.
Train/val split: west of 0° lon = train, east = val.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

import numpy as np
import rasterio
import torch
from torch.utils.data import Dataset


PATCH_SIZE = 128
STATE_CHANNELS = 2
ENV_CHANNELS = 4


class RolloutDataset(Dataset):
    def __init__(self, run_dir: str | Path, split: Literal["train", "val"] = "train",
                 patch_size: int = PATCH_SIZE, subsample: float = 1.0, preload: bool = False):
        self.run_dir = Path(run_dir)
        self.split = split
        self.patch_size = patch_size
        self.subsample = subsample
        self.preload = preload
        self.patches = []
        self._data_cache = {}
        self._build_patches()
        if preload:
            self._preload_data()

    def _build_patches(self):
        state_files = sorted(self.run_dir.glob("state_seed*_day*.npy"))
        if not state_files:
            state_files = sorted(self.run_dir.glob("state_seed*_day*.tif"))
            self._use_tiff = True
        else:
            self._use_tiff = False
        
        if not state_files:
            raise FileNotFoundError(f"No state files in {self.run_dir}")

        if self._use_tiff:
            import rasterio
            with rasterio.open(state_files[0]) as src:
                H, W = src.shape
        else:
            sample = np.load(state_files[0])
            H, W = sample.shape[1], sample.shape[2]

        n_patches_h = H // self.patch_size
        n_patches_w = W // self.patch_size

        mid_col = W // 2

        for state_file in state_files:
            if self._use_tiff:
                sidecar = state_file.with_suffix(".json")
                with open(sidecar) as f:
                    meta = json.load(f)
                day = int(state_file.stem.split("_day")[1])
                next_day = day + 7
                next_file = state_file.parent / f"state_seed{meta['seed']:04d}_day{next_day:03d}.tif"
            else:
                day = int(state_file.stem.split("_day")[1])
                seed = int(state_file.stem.split("_seed")[1].split("_")[0])
                next_day = day + 7
                next_file = state_file.parent / f"state_seed{seed:04d}_day{next_day:03d}.npy"

            if not next_file.exists():
                continue

            for r in range(n_patches_h):
                for c in range(n_patches_w):
                    is_east = (c * self.patch_size) >= mid_col
                    patch_split = "val" if is_east else "train"

                    if patch_split != self.split:
                        continue

                    self.patches.append({
                        "state_path": state_file,
                        "next_path": next_file,
                        "row": r * self.patch_size,
                        "col": c * self.patch_size,
                    })

        if self.subsample < 1.0:
            np.random.seed(42)
            n_keep = int(len(self.patches) * self.subsample)
            indices = np.random.choice(len(self.patches), n_keep, replace=False)
            self.patches = [self.patches[i] for i in indices]

    def _preload_data(self):
        print(f"Preloading {len(self.patches)} patches into memory...")
        for i, patch in enumerate(self.patches):
            state_key = str(patch["state_path"])
            next_key = str(patch["next_path"])
            
            if state_key not in self._data_cache:
                if self._use_tiff:
                    with rasterio.open(state_key) as src:
                        self._data_cache[state_key] = src.read()
                else:
                    self._data_cache[state_key] = np.load(state_key)
            
            if next_key not in self._data_cache:
                if self._use_tiff:
                    with rasterio.open(next_key) as src:
                        self._data_cache[next_key] = src.read()
                else:
                    self._data_cache[next_key] = np.load(next_key)
            
            if (i + 1) % 1000 == 0:
                print(f"  Preloaded {i + 1}/{len(self.patches)} patches")
        print(f"Preload complete. Cache size: {len(self._data_cache)} files")

    def __len__(self):
        return len(self.patches)

    def __getitem__(self, idx):
        patch = self.patches[idx]
        state_key = str(patch["state_path"])
        next_key = str(patch["next_path"])

        if self.preload and state_key in self._data_cache:
            state_full = self._data_cache[state_key]
            target_full = self._data_cache[next_key]
        else:
            if self._use_tiff:
                with rasterio.open(state_key) as src:
                    state_full = src.read()
                with rasterio.open(next_key) as src:
                    target_full = src.read()
            else:
                state_full = np.load(state_key)
                target_full = np.load(next_key)

        r, c = patch["row"], patch["col"]
        state = state_full[:, r:r+self.patch_size, c:c+self.patch_size]
        target = target_full[:, r:r+self.patch_size, c:c+self.patch_size]

        env = np.zeros((ENV_CHANNELS, self.patch_size, self.patch_size), dtype=np.float32)

        x = np.concatenate([state, env], axis=0)
        return torch.from_numpy(x), torch.from_numpy(target)


def get_dataloaders(run_dir: str | Path, batch_size: int = 16, num_workers: int = 0,
                    subsample: float = 1.0, preload: bool = False):
    train_ds = RolloutDataset(run_dir, split="train", subsample=subsample, preload=preload)
    val_ds = RolloutDataset(run_dir, split="val", subsample=subsample, preload=preload)

    train_loader = torch.utils.data.DataLoader(
        train_ds, batch_size=batch_size, shuffle=True, num_workers=num_workers
    )
    val_loader = torch.utils.data.DataLoader(
        val_ds, batch_size=batch_size, shuffle=False, num_workers=num_workers
    )

    return train_loader, val_loader
