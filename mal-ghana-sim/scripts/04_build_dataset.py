"""M5 — generate rollouts and report dataset stats (numpy only, no torch). Usage: uv run python scripts/04_build_dataset.py [n]"""
import sys
import numpy as np
from mal_ghana_sim import config as C, dataset

n = int(sys.argv[sys.argv.index("n") + 1]) if "n" in sys.argv else C.N_ROLLOUTS
rng = np.random.default_rng(0)
rollouts, env_feat, meta = dataset.generate_rollouts(n, rng=rng)
print(f"generated {len(rollouts)}/{n} non-degenerate rollouts")
if rollouts:
    fkeys = sorted(rollouts[0]["frames"])
    print(f"frames per rollout: {len(fkeys)} (t={fkeys})")
    print(f"env_feat shape: {env_feat.shape}")
    # quick patch-count estimate
    from mal_ghana_sim.dataset import RolloutDataset
    tr = RolloutDataset(rollouts, env_feat, meta["affine"], val=False)
    va = RolloutDataset(rollouts, env_feat, meta["affine"], val=True)
    print(f"approx train patches: {len(tr)}   val patches: {len(va)}")
    print(f"sample rollout k_max: {rollouts[0]['k_max']:.0f}  final max: {rollouts[0]['frames'][fkeys[-1]].max():.1f}")
