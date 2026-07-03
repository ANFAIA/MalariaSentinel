"""M2 — build the 1 km env stack. Usage: uv run python scripts/01_ingest.py [--download]"""
import sys
from mal_ghana_sim import ingest

download = "--download" in sys.argv
stack, meta = ingest.build_stack(download=download)
print("order:", meta["order"])
print("present:", meta["present"])
print("shape:", stack.shape, "HxW:", meta["height"], "x", meta["width"])
print("per-layer stats:")
for i, name in enumerate(meta["order"]):
    a = stack[i]
    import numpy as np
    print(f"  {name:12s} min={float(np.nanmin(a)):.3f} mean={float(np.nanmean(a)):.3f} max={float(np.nanmax(a)):.3f}")
