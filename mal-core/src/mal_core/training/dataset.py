"""M3-M4 & M7.4 — Dataset builder for U-Net surrogate training.

Reads ABM rollout snapshots (vector state + SEIR transmission state),
tiles into 128x128 patches, builds (state_t + env) -> state_{t+1} pairs.
Spatial train/val split: west of center longitude = train, east = val.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Literal

import numpy as np
import rasterio
import torch
from torch.utils.data import Dataset

PATCH_SIZE = 128
VECTOR_CHANNELS = 2
TRANSMISSION_CHANNELS = 4
ENV_CHANNELS = 4


def _extract_seed_and_day(path: Path) -> tuple[int, int]:
    """Extract seed and simulation day from snapshot filename."""
    seed = 1
    day = 0
    m_seed = re.search(r"seed(\d+)", path.stem)
    if m_seed:
        seed = int(m_seed.group(1))
    m_day = re.search(r"_day(\d+)", path.stem)
    if m_day:
        day = int(m_day.group(1))
    return seed, day


class RolloutDataset(Dataset):
    def __init__(
        self,
        run_dir: str | Path,
        split: Literal["train", "val"] = "train",
        patch_size: int = PATCH_SIZE,
        subsample: float = 1.0,
        preload: bool = False,
        include_transmission: bool = True,
        env_path: str | Path | None = None,
    ):
        self.run_dir = Path(run_dir)
        self.split = split
        self.patch_size = patch_size
        self.subsample = subsample
        self.preload = preload
        self.include_transmission = include_transmission
        self.env_path = Path(env_path) if env_path else None

        self.patches: list[dict] = []
        self._data_cache: dict[str, np.ndarray] = {}
        self._env_cache: np.ndarray | None = None

        self._load_env_if_available()
        self._build_patches()
        if preload:
            self._preload_data()

    def _load_env_if_available(self) -> None:
        if self.env_path and self.env_path.exists():
            try:
                if self.env_path.suffix in (".nc", ".nc4"):
                    import xarray as xr
                    with xr.open_dataset(self.env_path) as ds:
                        vars_to_use = [v for v in ["water_frac", "rainfall", "water_temp_c", "ndvi", "temperature"] if v in ds]
                        arrs = [ds[v].values.squeeze() for v in vars_to_use[:ENV_CHANNELS]]
                        if len(arrs) < ENV_CHANNELS:
                            H, W = arrs[0].shape[-2:]
                            while len(arrs) < ENV_CHANNELS:
                                arrs.append(np.zeros((H, W), dtype=np.float32))
                        self._env_cache = np.stack(arrs[:ENV_CHANNELS], axis=0).astype(np.float32)
                elif self.env_path.suffix in (".tif", ".tiff"):
                    with rasterio.open(self.env_path) as src:
                        data = src.read().astype(np.float32)
                        if data.shape[0] < ENV_CHANNELS:
                            padded = np.zeros((ENV_CHANNELS, data.shape[1], data.shape[2]), dtype=np.float32)
                            padded[:data.shape[0]] = data
                            data = padded
                        self._env_cache = data[:ENV_CHANNELS]
            except Exception:
                self._env_cache = None

    def _build_patches(self) -> None:
        # 1. Discover all state snapshot files (excluding transmission files)
        candidate_tifs = sorted(self.run_dir.glob("*.tif"))
        state_tifs = [p for p in candidate_tifs if "_day" in p.name and "transmission" not in p.name]
        state_npys = sorted(self.run_dir.glob("*_day*.npy"))

        use_tiff = len(state_tifs) >= len(state_npys)
        state_files = state_tifs if use_tiff else state_npys

        if not state_files:
            raise FileNotFoundError(f"No ABM state snapshot files (*_day*.tif/npy) found in {self.run_dir}")

        # Group by seed/rollout
        series_by_seed: dict[int, dict[int, Path]] = {}
        for p in state_files:
            seed, day = _extract_seed_and_day(p)
            if seed not in series_by_seed:
                series_by_seed[seed] = {}
            series_by_seed[seed][day] = p

        # Check for matching transmission snapshots
        trans_by_seed: dict[int, dict[int, Path]] = {}
        if self.include_transmission:
            trans_files = [p for p in candidate_tifs if "_day" in p.name and "transmission" in p.name]
            for p in trans_files:
                seed, day = _extract_seed_and_day(p)
                if seed not in trans_by_seed:
                    trans_by_seed[seed] = {}
                trans_by_seed[seed][day] = p

        # Get raster dimensions
        first_file = state_files[0]
        if use_tiff:
            with rasterio.open(first_file) as src:
                H, W = src.shape
        else:
            sample = np.load(first_file)
            H, W = sample.shape[-2], sample.shape[-1]

        n_patches_h = max(1, H // self.patch_size)
        n_patches_w = max(1, W // self.patch_size)
        mid_col = W // 2

        # Build consecutive temporal pairs (day_t, day_{t+1})
        for seed, days_dict in series_by_seed.items():
            sorted_days = sorted(days_dict.keys())
            for i in range(len(sorted_days) - 1):
                day_cur = sorted_days[i]
                day_next = sorted_days[i + 1]

                state_cur = days_dict[day_cur]
                state_next = days_dict[day_next]

                trans_cur = trans_by_seed.get(seed, {}).get(day_cur)
                trans_next = trans_by_seed.get(seed, {}).get(day_next)

                has_trans = bool(self.include_transmission and trans_cur and trans_next)

                for r in range(n_patches_h):
                    for c in range(n_patches_w):
                        is_east = (c * self.patch_size) >= mid_col
                        patch_split = "val" if is_east else "train"

                        if patch_split != self.split:
                            continue

                        self.patches.append({
                            "state_path": state_cur,
                            "next_path": state_next,
                            "trans_path": trans_cur if has_trans else None,
                            "trans_next_path": trans_next if has_trans else None,
                            "row": r * self.patch_size,
                            "col": c * self.patch_size,
                            "use_tiff": use_tiff,
                        })

        if self.subsample < 1.0 and self.patches:
            np.random.seed(42)
            n_keep = max(1, int(len(self.patches) * self.subsample))
            indices = np.random.choice(len(self.patches), n_keep, replace=False)
            self.patches = [self.patches[i] for i in indices]

    def _read_raster(self, path: Path | str, is_tiff: bool) -> np.ndarray:
        p_str = str(path)
        if p_str in self._data_cache:
            return self._data_cache[p_str]

        if is_tiff:
            with rasterio.open(path) as src:
                arr = src.read().astype(np.float32)
                nodata = src.nodata
                if nodata is not None:
                    arr[arr == nodata] = 0.0
        else:
            arr = np.load(path).astype(np.float32)
            if arr.ndim == 2:
                arr = arr[np.newaxis]

        if self.preload:
            self._data_cache[p_str] = arr
        return arr

    def _preload_data(self) -> None:
        for patch in self.patches:
            self._read_raster(patch["state_path"], patch["use_tiff"])
            self._read_raster(patch["next_path"], patch["use_tiff"])
            if patch["trans_path"]:
                self._read_raster(patch["trans_path"], True)
            if patch["trans_next_path"]:
                self._read_raster(patch["trans_next_path"], True)

    def __len__(self) -> int:
        return len(self.patches)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, torch.Tensor]:
        patch = self.patches[idx]
        use_tiff = patch["use_tiff"]
        r, c = patch["row"], patch["col"]
        ps = self.patch_size

        state_full = self._read_raster(patch["state_path"], use_tiff)
        next_full = self._read_raster(patch["next_path"], use_tiff)

        state_patch = state_full[:, r:r+ps, c:c+ps]
        next_patch = next_full[:, r:r+ps, c:c+ps]

        # Pad if edge patch is smaller than patch_size
        if state_patch.shape[-2] != ps or state_patch.shape[-1] != ps:
            ch = state_patch.shape[0]
            padded_s = np.zeros((ch, ps, ps), dtype=np.float32)
            padded_s[:, :state_patch.shape[-2], :state_patch.shape[-1]] = state_patch
            state_patch = padded_s

            padded_n = np.zeros((next_patch.shape[0], ps, ps), dtype=np.float32)
            padded_n[:, :next_patch.shape[-2], :next_patch.shape[-1]] = next_patch
            next_patch = padded_n

        # Append transmission channels if available
        if patch["trans_path"] and patch["trans_next_path"]:
            trans_cur = self._read_raster(patch["trans_path"], True)[:, r:r+ps, c:c+ps]
            trans_nxt = self._read_raster(patch["trans_next_path"], True)[:, r:r+ps, c:c+ps]

            if trans_cur.shape[-2] != ps or trans_cur.shape[-1] != ps:
                tch = trans_cur.shape[0]
                pt_c = np.zeros((tch, ps, ps), dtype=np.float32)
                pt_c[:, :trans_cur.shape[-2], :trans_cur.shape[-1]] = trans_cur
                trans_cur = pt_c

                pt_n = np.zeros((trans_nxt.shape[0], ps, ps), dtype=np.float32)
                pt_n[:, :trans_nxt.shape[-2], :trans_nxt.shape[-1]] = trans_nxt
                trans_nxt = pt_n

            state_patch = np.concatenate([state_patch, trans_cur], axis=0)
            next_patch = np.concatenate([next_patch, trans_nxt], axis=0)

        # Environmental channels
        if self._env_cache is not None and self._env_cache.shape[-2] >= r+ps and self._env_cache.shape[-1] >= c+ps:
            env_patch = self._env_cache[:, r:r+ps, c:c+ps]
        else:
            env_patch = np.zeros((ENV_CHANNELS, ps, ps), dtype=np.float32)

        x = np.concatenate([state_patch, env_patch], axis=0)
        return torch.from_numpy(x), torch.from_numpy(next_patch)


def get_dataloaders(
    run_dir: str | Path,
    batch_size: int = 16,
    num_workers: int = 0,
    subsample: float = 1.0,
    preload: bool = False,
    include_transmission: bool = True,
    env_path: str | Path | None = None,
) -> tuple[torch.utils.data.DataLoader, torch.utils.data.DataLoader]:
    train_ds = RolloutDataset(
        run_dir,
        split="train",
        subsample=subsample,
        preload=preload,
        include_transmission=include_transmission,
        env_path=env_path,
    )
    val_ds = RolloutDataset(
        run_dir,
        split="val",
        subsample=subsample,
        preload=preload,
        include_transmission=include_transmission,
        env_path=env_path,
    )

    train_loader = torch.utils.data.DataLoader(
        train_ds, batch_size=batch_size, shuffle=True, num_workers=num_workers
    )
    val_loader = torch.utils.data.DataLoader(
        val_ds, batch_size=batch_size, shuffle=False, num_workers=num_workers
    )

    return train_loader, val_loader
