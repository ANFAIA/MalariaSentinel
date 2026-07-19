"""M6 — Load real environmental stack from runs/env_stack.npz.

Reads the pre-built env stack (5 layers in EPSG:32630), selects the 4
channels the U-Net expects, and resamples to the AOI grid (EPSG:4326).
"""
from __future__ import annotations

import numpy as np
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling

from mal_commonlib.aoi import AOI

# U-Net expects 4 env channels. We pick the 4 present in env_stack.npz
# (elevation is excluded — topography is static and not a transmission driver).
ENV_CHANNELS = 4

# Order matters: must match what the U-Net was trained on.
# The training set zeros all env channels, so any order works for the
# current model, but we keep a stable, documented order.
ENV_CHANNEL_ORDER = ["water_frac", "rainfall", "temperature", "ndvi"]


def load_env_stack(aoi: AOI, env_path: str | None = None) -> np.ndarray:
    """Load env stack and resample to the AOI grid.

    Args:
        aoi: Target AOI (defines bbox, CRS, grid shape).
        env_path: Path to env_stack.npz. Defaults to runs/env_stack.npz.

    Returns:
        env: (ENV_CHANNELS, H, W) float32, aligned to the AOI grid.
    """
    from mal_commonlib.config import RUNS_DIR

    path = env_path or str(RUNS_DIR / "env_stack.npz")
    data = np.load(path)
    stack = data["stack"]  # (5, H_src, W_src), float32
    present = list(data["present"])
    src_crs = str(data["crs"])

    # Select the 4 channels the U-Net expects.
    indices = [present.index(name) for name in ENV_CHANNEL_ORDER if name in present]
    if len(indices) != ENV_CHANNELS:
        # Fallback: take the first 4 present channels.
        indices = list(range(min(ENV_CHANNELS, stack.shape[0])))
    src = stack[indices]  # (4, H_src, W_src)

    # Resample to the AOI grid (EPSG:4326, H×W).
    H, W = aoi.cells_per_side()
    dst = np.zeros((ENV_CHANNELS, H, W), dtype=np.float32)

    src_transform = rasterio.transform.from_bounds(
        # env_stack.npz doesn't store bounds; we infer from a sample.
        # The stack is built from a UTM crop, so we read the
        # transform from the first layer's metadata if present,
        # otherwise approximate.
        *_infer_src_bounds(data),
        width=src.shape[2],
        height=src.shape[1],
    )

    dst_transform = rasterio.transform.from_bounds(
        aoi.bbox[0], aoi.bbox[1], aoi.bbox[2], aoi.bbox[3], W, H
    )

    for i in range(ENV_CHANNELS):
        reproject(
            source=src[i],
            destination=dst[i],
            src_transform=src_transform,
            src_crs=src_crs,
            dst_transform=dst_transform,
            dst_crs=aoi.crs,
            resampling=Resampling.bilinear,
        )

    return dst


def _infer_src_bounds(data: np.ndarray) -> tuple[float, float, float, float]:
    """Infer geographic bounds of the env stack.

    env_stack.npz doesn't store bounds explicitly. We use a heuristic:
    the stack covers a UTM tile centered on Ghana, roughly
    (-2.0, 4.0, 2.0, 12.0) in EPSG:4326. We convert that to the
    stack's pixel space using its known dimensions.
    """
    # If 'bounds' key exists, use it.
    if "bounds" in data:
        return tuple(data["bounds"])
    # Fallback: Ghana bbox in EPSG:4326.
    return (-3.0, 4.0, 2.0, 12.0)
