"""Stage 5 — training loop for the U-Net transition surrogate (materialized-tensor, no DataLoader)."""
from __future__ import annotations

import time

import numpy as np
import torch

from . import config as C
from .dataset import env_feature_stack, generate_rollouts, materialize_patches
from .unet import UNet, combined_loss, eval_dice


def train(n_rollouts=C.N_ROLLOUTS, epochs=C.TRAIN_EPOCHS, lr=C.TRAIN_LR, device=None, seed=0):
    torch.manual_seed(seed); np.random.seed(seed)
    if device is None:
        # MPS is catastrophically slow for this BatchNorm U-Net (~4s/batch); CPU is faster here.
        device = "cpu"
    print(f"device={device}", flush=True)

    print(f"generating {n_rollouts} rollouts...", flush=True)
    rollouts, env_feat, meta = generate_rollouts(n_rollouts, rng=np.random.default_rng(seed))
    print(f"  kept {len(rollouts)} non-degenerate rollouts", flush=True)

    Xtr, Ytr = materialize_patches(rollouts, env_feat, meta["affine"], val=False)
    Xva, Yva = materialize_patches(rollouts, env_feat, meta["affine"], val=True)
    print(f"  train patches={len(Xtr)}  val patches={len(Xva)}", flush=True)
    Xtr = torch.from_numpy(Xtr).to(device); Ytr = torch.from_numpy(Ytr).to(device)
    Xva = torch.from_numpy(Xva).to(device); Yva = torch.from_numpy(Yva).to(device)

    in_ch = Xtr.shape[1]
    model = UNet(in_channels=in_ch).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    print(f"  U-Net in_channels={in_ch}  params={sum(p.numel() for p in model.parameters()):,}", flush=True)

    n = len(Xtr); bs = C.TRAIN_BATCH; best_dice = 0.0
    g = torch.Generator(device="cpu").manual_seed(seed)
    for ep in range(1, epochs + 1):
        model.train(); t0 = time.time(); running = 0.0; nb = 0
        perm = torch.randperm(n, generator=g).tolist()
        for i in range(0, n, bs):
            idx = perm[i:i + bs]
            xb = Xtr[idx]; yb = Ytr[idx]
            # on-GPU augmentation (flips/rot) -- cheap, keeps compute on-device
            if torch.rand(1, generator=g).item() < 0.5: xb = torch.flip(xb, [2]); yb = torch.flip(yb, [2])
            if torch.rand(1, generator=g).item() < 0.5: xb = torch.flip(xb, [3]); yb = torch.flip(yb, [3])
            k = int(torch.randint(0, 4, (1,), generator=g).item())
            xb = torch.rot90(xb, k, [2, 3]); yb = torch.rot90(yb, k, [2, 3])
            pred = model(xb)
            loss, _, _ = combined_loss(pred, yb)
            opt.zero_grad(); loss.backward(); opt.step()
            running += loss.item(); nb += 1
        model.eval(); vd = 0.0; nv = 0
        with torch.no_grad():
            for i in range(0, len(Xva), bs):
                pred = model(Xva[i:i + bs])
                vd += eval_dice(pred, Yva[i:i + bs]); nv += 1
        vd = vd / max(1, nv)
        if vd > best_dice:
            best_dice = vd; torch.save(model.state_dict(), C.RUNS / "unet_best.pt")
        print(f"  ep{ep:02d} loss={running/max(1,nb):.4f}  val_dice={vd:.3f}  best={best_dice:.3f}  ({time.time()-t0:.1f}s)", flush=True)
    torch.save(model.state_dict(), C.RUNS / "unet_last.pt")
    print(f"DONE. best val Dice={best_dice:.3f}  (criterion > {C.DICE_TARGET})  -> {C.RUNS}/unet_best.pt", flush=True)
    return model, best_dice
