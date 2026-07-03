"""Stage 4 — training-set assembly.

Generates param-randomized rollouts, builds (D_t + env) -> D_{t+T} pairs, and serves
patched training samples lazily (memory-light: full-frame rollouts stay in RAM, patches
are extracted per __getitem__). Split by AOI sub-region (west train / east val).
"""
from __future__ import annotations

import numpy as np
import torch
from torch.utils.data import Dataset

from . import config as C
from . import ingest, suitability, simulator


# --- static env feature stack (shared across all rollouts; v1 = static normals) ---
def env_feature_stack() -> np.ndarray:
    """Return (4, H, W) normalized env channels: water, rainfall, temp_suit, elev(inverted)."""
    stack, meta = ingest.build_stack(download=False)
    idx = {n: i for i, n in enumerate(meta["order"])}
    present = meta["present"]

    def norm(a):
        lo, hi = float(np.nanmin(a)), float(np.nanmax(a))
        return (a - lo) / (hi - lo) if hi - lo > 1e-9 else np.zeros_like(a)

    feats = []
    if "water_frac" in present:
        feats.append(("water", norm(stack[idx["water_frac"]])))
    if "rainfall" in present:
        feats.append(("rainfall", norm(stack[idx["rainfall"]])))
    if "temperature" in present:
        feats.append(("temp_suit", C.temp_suitability(stack[idx["temperature"]])))
    if "elevation" in present:
        feats.append(("elev", 1.0 - norm(stack[idx["elevation"]])))
    arr = np.stack([f[1].astype(np.float32) for f in feats], axis=0)
    return arr, meta


# --- rollout generation ---
def generate_rollouts(n: int, env=None, rng=None, save_dir=None):
    """Generate n param-randomized rollouts. Seed at random water-rich cells so the pop spreads."""
    env = env or env_feature_stack()
    env_feat, meta = env
    idx = {n_: i for i, n_ in enumerate(meta["order"])}
    suit = suitability.suitability_from_stack(
        ingest.build_stack(download=False)[0], meta["present"])
    water = ingest.build_stack(download=False)[0][idx["water_frac"]].astype(np.float32)
    T_grid = ingest.build_stack(download=False)[0][idx["temperature"]]
    rng = rng or np.random.default_rng(0)

    # candidate seed cells: water-rich (breeding possible) + reasonable K
    K_base = suitability.carrying_capacity(suit)
    cand = np.argwhere((water > 0.05) & (K_base > 0.3 * K_base.max()))
    if len(cand) == 0:
        cand = np.argwhere(K_base > 0)

    rollouts = []
    for i in range(n):
        # randomized params
        r_max = rng.uniform(*C.PARAM_RANGES["r_max"])
        mu = rng.uniform(*C.PARAM_RANGES["mu"])
        k_max = rng.uniform(*C.PARAM_RANGES["k_max"])
        wthr = rng.uniform(*C.PARAM_RANGES["water_thresh"])
        params = C.SimParams(r_max=r_max, mu=mu, k_max=k_max, water_thresh=wthr)
        K = K_base * (k_max / C.K_MAX)  # scale carrying capacity by this rollout's k_max
        seed = cand[rng.integers(0, len(cand))]
        seed_rc = [(int(seed[0]), int(seed[1]))]
        res = simulator.rollout(K, water, T_grid, seed_rc=seed_rc, params=params,
                                n_steps=C.N_STEPS, t_snap=C.T_SNAP, save_dir=None)
        # only keep rollouts that actually grew (avoid degenerate all-zero samples)
        if res["final"].max() < 0.05 * k_max:
            continue
        rollouts.append(dict(frames=res["frames"], k_max=k_max, params=params))
    return rollouts, env_feat, meta


# --- lazy patched dataset ---
class RolloutDataset(Dataset):
    def __init__(self, rollouts, env_feat, affine, patch=C.PATCH, stride=C.STRIDE,
                 val=False, val_lon=C.VAL_SPLIT_LON, augment=False, seed=0):
        self.rollouts = rollouts
        self.env = env_feat
        self.patch = patch
        self.augment = augment
        self.rng = np.random.default_rng(seed)
        H, W = env_feat.shape[1:]
        # transform val_lon (degrees lon) -> UTM x at the AOI mid-latitude, then -> column
        from pyproj import Transformer
        mid_lat = 0.5 * (C.AOI_S + C.AOI_N)
        x_split, _ = Transformer.from_crs("EPSG:4326", C.DST_CRS, always_xy=True).transform(val_lon, mid_lat)
        col_split = int((x_split - affine.c) / affine.a)
        col_split = max(0, min(W, col_split))
        # patch grid
        rows = list(range(0, max(1, H - patch + 1), stride))
        cols = list(range(0, max(1, W - patch + 1), stride))
        # build (rollout_idx, t, r, c) items; split by patch center column
        self.items = []
        ts = sorted(rollouts[0]["frames"]) if rollouts else []
        pairs_t = [(ts[k], ts[k + 1]) for k in range(len(ts) - 1)]
        for ri, ro in enumerate(rollouts):
            fkeys = sorted(ro["frames"])
            pairs = [(fkeys[k], fkeys[k + 1]) for k in range(len(fkeys) - 1)]
            for (t0, t1) in pairs:
                for r in rows:
                    for c in cols:
                        center_c = c + patch // 2
                        is_val = center_c >= col_split
                        if val == is_val:
                            self.items.append((ri, t0, t1, r, c))
        # reflect-pad helper extents handled in __getitem__ via clip

    def __len__(self):
        return len(self.items)

    def __getitem__(self, i):
        ri, t0, t1, r, c = self.items[i]
        ro = self.rollouts[ri]
        kmax = ro["k_max"]
        H, W = self.env.shape[1:]
        p = self.patch

        def extract(arr):
            out = np.zeros((p, p), dtype=np.float32)
            r0, c0 = max(0, r), max(0, c)
            r1, c1 = min(H, r + p), min(W, c + p)
            sub = arr[r0:r1, c0:c1]
            out[:r1 - r0, :c1 - c0] = sub
            # reflect-pad the missing edge
            if r1 - r0 < p or c1 - c0 < p:
                out = _reflect_pad_to(out, p)
            return out

        D_t = extract(ro["frames"][t0]) / kmax
        D_tgt = extract(ro["frames"][t1]) / kmax
        env_patches = np.stack([extract(self.env[k]) for k in range(self.env.shape[0])], axis=0)
        X = np.concatenate([D_t[None], env_patches], axis=0).astype(np.float32)  # (C, p, p)
        Y = D_tgt[None].astype(np.float32)  # (1, p, p)
        if self.augment:
            X, Y = _augment(X, Y, self.rng)
        return torch.from_numpy(X), torch.from_numpy(Y)


def _reflect_pad_to(a, p):
    return np.pad(a, ((0, p - a.shape[0]), (0, p - a.shape[1])), mode="reflect")[:p, :p]


def _extract(arr, r, c, p, H, W):
    out = np.zeros((p, p), dtype=np.float32)
    r0, c0 = max(0, r), max(0, c)
    r1, c1 = min(H, r + p), min(W, c + p)
    out[:r1 - r0, :c1 - c0] = arr[r0:r1, c0:c1]
    if r1 - r0 < p or c1 - c0 < p:
        out = _reflect_pad_to(out, p)
    return out


def _patch_items(rollouts, env_feat, affine, patch, stride, val, val_lon):
    H, W = env_feat.shape[1:]
    from pyproj import Transformer
    mid_lat = 0.5 * (C.AOI_S + C.AOI_N)
    x_split, _ = Transformer.from_crs("EPSG:4326", C.DST_CRS, always_xy=True).transform(val_lon, mid_lat)
    col_split = max(0, min(W, int((x_split - affine.c) / affine.a)))
    rows = list(range(0, max(1, H - patch + 1), stride))
    cols = list(range(0, max(1, W - patch + 1), stride))
    items = []
    for ri, ro in enumerate(rollouts):
        fkeys = sorted(ro["frames"])
        for k in range(len(fkeys) - 1):
            t0, t1 = fkeys[k], fkeys[k + 1]
            for r in rows:
                for c in cols:
                    is_val = (c + patch // 2) >= col_split
                    if val == is_val:
                        items.append((ri, t0, t1, r, c))
    return items, H, W


def materialize_patches(rollouts, env_feat, affine, val=False, patch=C.PATCH,
                        stride=C.STRIDE, val_lon=C.VAL_SPLIT_LON, presence_only=True):
    """Pre-materialize all (X,Y) patch pairs into arrays (no DataLoader needed).

    presence_only: keep only patches whose TARGET (D_{t+T}) has presence > thresh. The spread
    is sparse/local, so most patches are empty and would teach the model to predict nothing;
    training on presence-containing patches focuses learning on the actual transition.
    """
    items, H, W = _patch_items(rollouts, env_feat, affine, patch, stride, val, val_lon)
    nC = 1 + env_feat.shape[0]
    Xs, Ys = [], []
    for ri, t0, t1, r, c in items:
        ro = rollouts[ri]; kmax = ro["k_max"]
        D_tgt = _extract(ro["frames"][t1] / kmax, r, c, patch, H, W)
        if presence_only and (D_tgt > C.PRESENCE_THRESH).sum() < 1:
            continue
        D_t = _extract(ro["frames"][t0] / kmax, r, c, patch, H, W)
        env = np.stack([_extract(env_feat[k], r, c, patch, H, W) for k in range(env_feat.shape[0])], axis=0)
        Xs.append(np.concatenate([D_t[None], env], axis=0))
        Ys.append(D_tgt[None])
    if not Xs:
        return np.zeros((0, nC, patch, patch), dtype=np.float32), np.zeros((0, 1, patch, patch), dtype=np.float32)
    X = np.stack(Xs, axis=0).astype(np.float32)
    Y = np.stack(Ys, axis=0).astype(np.float32)
    return X, Y


class RolloutDataset(Dataset):
    """Lazy dataset (kept for reference); training uses materialize_patches for speed."""
    def __init__(self, rollouts, env_feat, affine, patch=C.PATCH, stride=C.STRIDE,
                 val=False, val_lon=C.VAL_SPLIT_LON, augment=False, seed=0):
        self.rollouts = rollouts; self.env = env_feat; self.patch = patch; self.augment = augment
        self.rng = np.random.default_rng(seed)
        self.items, self.H, self.W = _patch_items(rollouts, env_feat, affine, patch, stride, val, val_lon)

    def __len__(self):
        return len(self.items)

    def __getitem__(self, i):
        ri, t0, t1, r, c = self.items[i]
        ro = self.rollouts[ri]; kmax = ro["k_max"]
        D_t = _extract(ro["frames"][t0] / kmax, r, c, self.patch, self.H, self.W)
        D_tgt = _extract(ro["frames"][t1] / kmax, r, c, self.patch, self.H, self.W)
        env = np.stack([_extract(self.env[k], r, c, self.patch, self.H, self.W) for k in range(self.env.shape[0])], axis=0)
        X = np.concatenate([D_t[None], env], axis=0).astype(np.float32)
        Y = D_tgt[None].astype(np.float32)
        if self.augment:
            X, Y = _augment(X, Y, self.rng)
        return torch.from_numpy(X), torch.from_numpy(Y)


def _augment(X, Y, rng):
    k = rng.integers(0, 4)
    X = np.rot90(X, k, axes=(1, 2)).copy(); Y = np.rot90(Y, k, axes=(1, 2)).copy()
    if rng.random() < 0.5: X = X[:, ::-1].copy(); Y = Y[:, ::-1].copy()
    if rng.random() < 0.5: X = X[:, :, ::-1].copy(); Y = Y[:, :, ::-1].copy()
    if rng.random() < 0.3: X = X + rng.normal(0, 0.01, X.shape).astype(np.float32)
    return X, Y


def make_loaders(rollouts, env_feat, affine, batch=C.TRAIN_BATCH, seed=0):
    train_ds = RolloutDataset(rollouts, env_feat, affine, val=False, augment=True, seed=seed)
    val_ds = RolloutDataset(rollouts, env_feat, affine, val=True, augment=False, seed=seed)
    tloader = torch.utils.data.DataLoader(train_ds, batch_size=batch, shuffle=True, num_workers=0)
    vloader = torch.utils.data.DataLoader(val_ds, batch_size=batch, shuffle=False, num_workers=0)
    return tloader, vloader, len(train_ds), len(val_ds)
