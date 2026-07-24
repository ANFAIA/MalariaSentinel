"""M6 — Load real ABM state from rollout snapshots.

Picks the snapshot closest to the target month from runs/1year-50r/,
crops to the AOI bbox, and returns the (2, H, W) state tensor.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling

from mal_commonlib.aoi import AOI
from mal_commonlib.config import RUNS_DIR


def load_abm_state(
    aoi: AOI,
    month: int = 1,
    rollout_dir: str | None = None,
    seed: int = 0,
) -> np.ndarray:
    """Load ABM state for the given month, cropped to the AOI.

    Args:
        aoi: Target AOI.
        month: Target month (1-12). Picks snapshot at day = month*30.
        rollout_dir: Path to rollout directory. Defaults to runs/1year-50r/.
        seed: Rollout seed to use.

    Returns:
        state: (2, H, W) float32, aligned to the AOI grid.
    """
    rdir = Path(rollout_dir or (RUNS_DIR / "1year-50r"))

    # Pick the snapshot closest to the target month.
    target_day = min(360, max(7, month * 30))
    state_file = rdir / f"state_seed{seed:04d}_day{target_day:03d}.npy"
    if not state_file.exists():
        state_file = rdir / f"state_seed{seed:04d}_day{target_day:03d}.tif"

    if not state_file.exists():
        # Fallback: first available snapshot.
        candidates = sorted(rdir.glob(f"state_seed{seed:04d}_day*.npy"))
        if not candidates:
            candidates = sorted(rdir.glob(f"state_seed{seed:04d}_day*.tif"))
        if not candidates:
            raise FileNotFoundError(f"No ABM snapshots found in {rdir}")
        state_file = candidates[0]

    # Load the snapshot.
    if state_file.suffix == ".npy":
        state_full = np.load(state_file)  # (2, H_src, W_src)
    else:
        with rasterio.open(state_file) as src:
            state_full = src.read()
            src_crs = str(src.crs)
            src_transform = src.transform
            src_h, src_w = src.shape

    # Resample to the AOI grid.
    H, W = aoi.cells_per_side()
    dst = np.zeros((2, H, W), dtype=np.float32)

    if state_file.suffix == ".npy":
        # npy files don't carry CRS/transform. We use the parent TIFF's
        # metadata via sidecar if present, or assume the state is already
        # in the AOI's grid.
        # For now, if the npy matches the AOI shape, copy directly;
        # otherwise reproject from EPSG:4326 with a coarse transform.
        if state_full.shape[1] == H and state_full.shape[2] == W:
            return state_full.astype(np.float32)
        src_crs = "EPSG:4326"
        src_h, src_w = state_full.shape[1], state_full.shape[2]
        src_transform = rasterio.transform.from_bounds(
            aoi.bbox[0], aoi.bbox[1], aoi.bbox[2], aoi.bbox[3], src_w, src_h
        )

    dst_transform = rasterio.transform.from_bounds(
        aoi.bbox[0], aoi.bbox[1], aoi.bbox[2], aoi.bbox[3], W, H
    )

    for i in range(2):
        reproject(
            source=state_full[i],
            destination=dst[i],
            src_transform=src_transform,
            src_crs=src_crs,
            dst_transform=dst_transform,
            dst_crs=aoi.crs,
            resampling=Resampling.bilinear,
        )

    return dst
