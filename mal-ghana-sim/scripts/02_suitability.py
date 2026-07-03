"""M3 — suitability field + AUC vs larval sites. Usage: uv run python scripts/02_suitability.py"""
import numpy as np
from mal_ghana_sim import config as C, ingest, suitability

stack, meta = ingest.build_stack(download=False)
suit = suitability.suitability_from_stack(stack, meta["present"])
K = suitability.carrying_capacity(suit)

lat, lon = suitability.load_occurrences()
in_aoi = suitability.in_aoi_mask(lat, lon)
print(f"occurrence sites: {len(lat)} total, {int(in_aoi.sum())} in-AOI")

res = suitability.auc_with_ci(suit, meta["affine"], lat[in_aoi], lon[in_aoi])
print(f"AUC={res['auc']:.3f}  95% CI=[{res['ci_low']:.3f}, {res['ci_high']:.3f}]  "
      f"(criterion: lower 95% > {C.AUC_CI_TARGET}; n_sites={res['n_sites']})")

# save first static risk map
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
fig, ax = plt.subplots(figsize=(8, 7))
im = ax.imshow(suit, cmap="YlOrRd")
ax.set_title(f"Ghana suitability (AUC={res['auc']:.2f}, n={res['n_sites']})")
plt.colorbar(im, ax=ax, label="suitability [0,1]")
fig.tight_layout(); fig.savefig(C.RUNS / "suitability_static.png", dpi=150)
print("saved ->", C.RUNS / "suitability_static.png")
