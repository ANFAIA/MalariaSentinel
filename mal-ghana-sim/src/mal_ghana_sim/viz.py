"""Stage 6 — visualization: SRTM-style risk-expansion map, simulator vs U-Net side-by-side."""
from __future__ import annotations

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LightSource

from . import config as C


def hillshade(elev_1km, az=315, alt=45):
    ls = LightSource(azdeg=az, altdeg=alt)
    return ls.hillshade(elev_1km, vert_exag=2)


def risk_expansion_map(elev, K, sim_frames, unet_frames, sim_final, unet_final,
                       seed_rc, occ_rc=None, affine=None, out=None):
    out = out or (C.RUNS / "risk_expansion.png")
    fig, axes = plt.subplots(2, 2, figsize=(13, 11))
    hs = hillshade(elev)

    def draw(ax, field, title, seed=True):
        ax.imshow(hs, cmap="gray", extent=None)
        im = ax.imshow(field, cmap="YlOrRd", alpha=0.75)
        ax.set_title(title); plt.colorbar(im, ax=ax, shrink=0.7, label="density")
        if seed:
            for r, c in seed_rc:
                ax.plot(c, r, "c*", markersize=12, markeredgecolor="k")
        if occ_rc is not None:
            rr, cc = occ_rc
            ax.plot(cc, rr, ".", color="blue", markersize=2)

    draw(axes[0, 0], K, "Carrying capacity K (habitat)")
    draw(axes[0, 1], sim_final, f"Simulator final D (t={C.N_STEPS})")
    draw(axes[1, 0], unet_final, f"U-Net final D (t={C.N_STEPS})")
    # final-step front overlay: sim red, unet cyan
    ax = axes[1, 1]
    ax.imshow(hs, cmap="gray")
    s = np.ma.masked_where(sim_final < 0.1 * K.max(), sim_final)
    u = np.ma.masked_where(unet_final < 0.1 * K.max(), unet_final)
    ax.imshow(s, cmap="Reds", alpha=0.6)
    ax.imshow(u, cmap="cool", alpha=0.6)
    ax.set_title("Front overlay (sim=red, U-Net=cyan)")
    for r, c in seed_rc:
        ax.plot(c, r, "g*", markersize=12, markeredgecolor="k")

    fig.suptitle("MalariaSentinel — mosquito spread: simulator vs U-Net surrogate (Ghana demo)", fontsize=13)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out
