"""M4 — run the reaction-diffusion simulator from the larval sites; save frames + rollout viz.

Usage: uv run python scripts/03_simulate.py
"""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from mal_ghana_sim import config as C, ingest, suitability, simulator


def main():
    stack, meta = ingest.build_stack(download=False)
    idx = {n: i for i, n in enumerate(meta["order"])}
    suit = suitability.suitability_from_stack(stack, meta["present"])
    K = suitability.carrying_capacity(suit)
    water = stack[idx["water_frac"]].astype(np.float32)   # soft water factor (continuous)
    T_grid = stack[idx["temperature"]]

    # seed from the unique in-AOI occurrence sites (lon/lat -> UTM rowcol)
    lat, lon = suitability.load_occurrences()
    in_aoi = suitability.in_aoi_mask(lat, lon)
    lat, lon = lat[in_aoi], lon[in_aoi]
    pts = np.unique(np.stack([lat, lon], axis=1), axis=0)
    rc = suitability._points_to_grid(pts[:, 0], pts[:, 1], meta["affine"], crs=meta.get("crs", C.DST_CRS))
    seed_rc = [(int(r), int(c)) for r, c in rc if 0 <= r < K.shape[0] and 0 <= c < K.shape[1]]
    # also seed at the highest-K water cell (a "point source" demo of spread from a water body),
    # since the larval sites fall in dry cells (water_frac=0) where breeding can't start at 1 km.
    ww = water * (K > 0)
    if np.isfinite(ww).any() and ww.max() > 0:
        ps = np.unravel_index(np.nanargmax(ww), ww.shape)
        seed_rc.append((int(ps[0]), int(ps[1])))
    print(f"K field: mean={K.mean():.1f} max={K.max():.1f}  water_cells={int((water>0).sum())}  "
          f"seed_sites={len(seed_rc)}")

    save_dir = C.RUNS / "sim" / "rollout_000"
    res = simulator.rollout(K, water, T_grid, seed_rc=seed_rc,
                            params=C.SimParams(), n_steps=C.N_STEPS, t_snap=C.T_SNAP,
                            save_dir=save_dir, affine=meta["affine"], crs=meta.get("crs", C.DST_CRS))
    frames = res["frames"]
    print(f"rollout done: {len(frames)} frames saved -> {save_dir}")
    print(f"final D: sum={res['final'].sum():.0f}  max={res['final'].max():.1f}  "
          f"occupied_cells={int((res['final'] > 0.1 * K).sum())}")

    # --- viz: K | seed | final | 3 frames ---
    fig, axes = plt.subplots(2, 3, figsize=(15, 9))
    axes[0, 0].imshow(K, cmap="viridis"); axes[0, 0].set_title("Carrying capacity K")
    D0 = np.zeros_like(K)
    for r, c in seed_rc:
        D0[r, c] = 0.1 * K[r, c]
    axes[0, 1].imshow(D0, cmap="YlOrRd"); axes[0, 1].set_title("Seed D_0 (sites)")
    axes[0, 2].imshow(res["final"], cmap="YlOrRd"); axes[0, 2].set_title(f"Final D (t={C.N_STEPS})")
    ft = sorted(frames)
    for ax, t in zip(axes[1, :3], ft[::max(1, len(ft) // 3)][:3]):
        ax.imshow(frames[t], cmap="YlOrRd"); ax.set_title(f"t={t}")
    fig.suptitle(f"M4 reaction-diffusion rollout (r(T) temp-gated, μ={C.MU}, T_snap={C.T_SNAP})", fontsize=13)
    fig.tight_layout()
    out = C.RUNS / "sim_rollout.png"
    fig.savefig(out, dpi=150)
    print("saved ->", out)


if __name__ == "__main__":
    main()
