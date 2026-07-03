"""Stage 3 — mechanistic mosquito spread simulator (reaction-diffusion, Fisher-KPP).

    D[t+1] = growth(r(T), K) + dispersal(mu, laplacian) - mortality(m(T))

with temperature-gated reproduction (Mordecai et al. 2013). Seeds at occurrence
sites (or a random point); snapshots every T_SNAP steps saved as .npz + GeoTIFF.
"""
from __future__ import annotations

import pathlib

import numpy as np
import scipy.ndimage as ndi

from . import config as C


def seed_field(K: np.ndarray, seed_rows_cols: list[tuple[int, int]] | None = None,
               density_frac: float = C.SEED_DENSITY_FRAC,
               random_point: bool = False, rng=None) -> np.ndarray:
    H, W = K.shape
    D = np.zeros((H, W), dtype=np.float32)
    if rng is None:
        rng = np.random.default_rng()
    rcs = list(seed_rows_cols or [])
    if random_point:
        rcs.append((int(rng.integers(0, H)), int(rng.integers(0, W))))
    for r, c in rcs:
        if 0 <= r < H and 0 <= c < W:
            D[r, c] = density_frac * K[r, c]
    return D


def step(D: np.ndarray, K: np.ndarray, water: np.ndarray, T_grid: np.ndarray,
         params: C.SimParams) -> np.ndarray:
    # r(T) = r_max * temp_suitability(T): temperature-gated reproduction (Mordecai 2013).
    r_T = params.r_of(T_grid)
    # soft water factor: breeding scales with water fraction (continuous), not a hard mask.
    growth = r_T * D * (1.0 - D / np.maximum(K, 1e-6)) * water
    D = D + growth
    # 4-neighbour diffusion (kernel [[0,1,0],[1,-4,1],[0,1,0]]); stable for mu<=0.25
    D = D + params.mu * ndi.laplace(D, mode="nearest")
    # temperature-dependent mortality
    D = D * (1.0 - C.mortality_rate(T_grid))
    D = np.clip(D, 0, None)
    return D.astype(np.float32)


def rollout(K, water_mask, T_grid, seed_rc=None, params=None,
            n_steps=C.N_STEPS, t_snap=C.T_SNAP, save_dir=None, affine=None, crs=None,
            rng=None) -> dict:
    params = params or C.SimParams()
    rng = rng or np.random.default_rng()
    D = seed_field(K, seed_rc, random_point=False, rng=rng)
    frames = {}
    for t in range(1, n_steps + 1):
        D = step(D, K, water_mask, T_grid, params)
        if t % t_snap == 0:
            frames[t] = D.copy()
            if save_dir:
                _save_frame(D, pathlib.Path(save_dir) / f"frame_{t:03d}.npz", affine, crs)
    return dict(frames=frames, final=D, params=params)


def _save_frame(D, path, affine, crs):
    import rasterio
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, D=D)
    tif = path.with_suffix(".tif")
    if affine is not None:
        with rasterio.open(tif, "w", driver="GTiff", height=D.shape[0], width=D.shape[1],
                           count=1, dtype="float32", crs=crs or C.DST_CRS,
                           transform=affine) as dst:
            dst.write(D, 1)
