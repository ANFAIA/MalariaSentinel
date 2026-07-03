"""Stage 6 — inference: rollout from a seed via the simulator (ground truth) AND the trained U-Net.

The U-Net runs on the full image (padded to a multiple of 16 for the 4-pool architecture),
one forward pass per T-step. Compares the two rollouts (front-overlap Dice).
"""
from __future__ import annotations

import numpy as np
import torch

from . import config as C
from . import ingest, suitability, simulator
from .dataset import env_feature_stack
from .unet import UNet, eval_dice


def pick_seed(water, K, rng=None) -> tuple[int, int]:
    """Pick the highest K * water cell (a strong point-source breeding site)."""
    rng = rng or np.random.default_rng(0)
    score = water * K
    r, c = np.unravel_index(np.nanargmax(score), score.shape)
    return int(r), int(c)


def simulator_rollout(K, water, T_grid, seed_rc, params=None, n_steps=C.N_STEPS, t_snap=C.T_SNAP):
    res = simulator.rollout(K, water, T_grid, seed_rc=seed_rc, params=params or C.SimParams(),
                            n_steps=n_steps, t_snap=t_snap, save_dir=None)
    return res["frames"], res["final"]


def unet_rollout(env_feat, K, k_max, seed_rc, n_unet_steps=12, device=None, ckpt=None):
    """Roll the U-Net forward n_unet_steps times from D_0. Returns frames dict + final (normalized)."""
    device = device or ("mps" if torch.backends.mps.is_available() else "cpu")
    in_ch = 1 + env_feat.shape[0]
    model = UNet(in_channels=in_ch).to(device).eval()
    ckpt = ckpt or C.RUNS / "unet_best.pt"
    model.load_state_dict(torch.load(ckpt, map_location=device))

    H, W = K.shape
    D = np.zeros((H, W), dtype=np.float32)
    for r, c in seed_rc:
        if 0 <= r < H and 0 <= c < W:
            D[r, c] = C.SEED_DENSITY_FRAC * K[r, c]
    D_norm = D / k_max

    env = torch.from_numpy(env_feat.astype(np.float32)).to(device)
    # pad to multiple of 16
    ph = (16 - H % 16) % 16
    pw = (16 - W % 16) % 16

    frames = {}
    D_t = torch.from_numpy(D_norm)[None, None].to(device)  # (1,1,H,W)
    with torch.no_grad():
        for k in range(1, n_unet_steps + 1):
            x = torch.cat([D_t, env[None]], dim=1)  # (1, C, H, W)
            x = torch.nn.functional.pad(x, (0, pw, 0, ph), mode="reflect")
            pred = model(x)
            pred = pred[:, :, :H, :W]
            D_t = pred.clamp(0, 1)
            if k % 1 == 0:  # record every step (12 steps ~ 60 sim steps / T=5)
                frames[k * C.T_SNAP] = D_t[0, 0].cpu().numpy()
    final = D_t[0, 0].cpu().numpy() * k_max  # back to raw density
    return frames, final


def front_dice(sim_final, unet_final, K, thresh_frac=0.1):
    s = (sim_final > thresh_frac * K.max()).astype(np.float32)
    u = (unet_final > thresh_frac * K.max()).astype(np.float32)
    inter = (s * u).sum(); union = s.sum() + u.sum()
    return float((2 * inter + 1e-6) / (union + 1e-6))
