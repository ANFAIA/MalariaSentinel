"""M6 — predict spread from a seed (sim + U-Net) and render the SRTM-style risk-expansion map.
Usage: uv run python scripts/06_predict_and_map.py
"""
import numpy as np

from mal_ghana_sim import config as C, ingest, suitability, predict, viz

stack, meta = ingest.build_stack(download=False)
idx = {n: i for i, n in enumerate(meta["order"])}
suit = suitability.suitability_from_stack(stack, meta["present"])
K = suitability.carrying_capacity(suit)
water = stack[idx["water_frac"]].astype(np.float32)
T_grid = stack[idx["temperature"]]
elev = stack[idx["elevation"]]
env_feat, _ = (lambda e: (e, None))(None)  # placeholder; fetch below
from mal_ghana_sim.dataset import env_feature_stack
env_feat, _ = env_feature_stack()

seed_rc = [predict.pick_seed(water, K)]
print("seed cell:", seed_rc)

# simulator ground truth (uses a single k_max for fair comparison with the U-Net)
params = C.SimParams()
sim_frames, sim_final = predict.simulator_rollout(K, water, T_grid, seed_rc, params=params)
print(f"sim final: max={sim_final.max():.1f} occupied={int((sim_final>0.1*K.max()).sum())}")

# U-Net rollout (same k_max so densities are comparable)
unet_frames, unet_final = predict.unet_rollout(env_feat, K, params.k_max, seed_rc, n_unet_steps=12)
print(f"unet final: max={unet_final.max():.1f} occupied={int((unet_final>0.1*K.max()).sum())}")

dice = predict.front_dice(sim_final, unet_final, K)
print(f"front-overlap Dice(sim,unet) = {dice:.3f}  (criterion > {C.DICE_TARGET})")

# occurrence site rowcols for overlay
lat, lon = suitability.load_occurrences(); m = suitability.in_aoi_mask(lat, lon); lat, lon = lat[m], lon[m]
pts = np.unique(np.stack([lat, lon], axis=1), axis=0)
occ_rc = suitability._points_to_grid(pts[:, 0], pts[:, 1], meta["affine"], crs=meta.get("crs", C.DST_CRS)).T

out = viz.risk_expansion_map(elev, K, sim_frames, unet_frames, sim_final, unet_final,
                             seed_rc, occ_rc=occ_rc, affine=meta["affine"])
print("saved ->", out)
