# overlay_hosts.py — M7.4.1 debug visualisation.
#
# Renders a per-snapshot animated GIF overlaying, on one map:
#   green  = human population (log)
#   brown  = livestock (cattle+goats+sheep+pigs, log)
#   blue   = adult mosquito occupancy (per-frame normalised)
#   red    = infectious vector pressure (I_V)
# Purpose: eyeball WHERE vectors live relative to hosts — the spatial
# co-localisation question that drove the M7.4.1 iterations. Surfaced
# as `malariasim abm --debug` and also runnable standalone:
#   uv run python -m mal_core.abm.scripts.overlay_hosts \
#       --run-dir runs/ghana/2024/hostweighted_s11 --aoi ghana
from __future__ import annotations

import argparse
import glob
import json
import re
from pathlib import Path

import numpy as np
import rasterio
import xarray as xr
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import animation  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402


def _norm_log(a: np.ndarray, q: float = 99.0) -> np.ndarray:
    v = np.log1p(np.clip(a, 0.0, None))
    pos = v[v > 0]
    hi = float(np.percentile(pos, q)) if pos.size else 1.0
    return np.clip(v / (hi or 1.0), 0.0, 1.0)


def _static_layers(aoi: str) -> tuple[np.ndarray, np.ndarray]:
    host_nc = Path(f"data/{aoi}/{aoi}_host_static.nc")
    ds = xr.open_dataset(host_nc)
    human = np.asarray(ds["human"].squeeze(), dtype=float)
    livestock = (
        np.asarray(ds["cattle"].squeeze())
        + np.asarray(ds["goats"].squeeze())
        + np.asarray(ds["sheep"].squeeze())
        + np.asarray(ds["pigs"].squeeze())
    )
    return _norm_log(human), _norm_log(livestock)


def render_overlay(run_dir: str | Path, aoi: str, output: str | Path,
                   fps: int = 2) -> Path:
    run_dir = Path(run_dir)
    H, L = _static_layers(aoi)
    base = np.clip(
        np.stack([H * 0.15, H * 0.85, H * 0.35], -1)
        + np.stack([L * 0.75, L * 0.55, L * 0.20], -1),
        0.0, 1.0,
    )

    day_tifs = sorted(
        glob.glob(str(run_dir / f"{aoi}_abm_seed*_day0[0-9][0-9].tif")),
        key=lambda p: int(re.search(r"day(\d+)", p).group(1)),
    )
    frames = []
    for path in day_tifs:
        day = int(re.search(r"day(\d+)", p := path).group(1))
        ts_path = path.replace("_day", "_transmission_day")
        with rasterio.open(path) as src:
            occ = np.asarray(src.read(1), dtype=float).reshape(base.shape[:2])
        ih, press = 0.0, np.zeros_like(occ)
        if Path(ts_path).exists():
            with rasterio.open(ts_path) as ts:
                ih = float(ts.read(1).sum())
                press = np.asarray(ts.read(3), dtype=float).reshape(
                    base.shape[:2])
        occ_n = np.clip(occ / max(occ.max(), 1e-9), 0, 1)
        pr_n = (np.clip(press / max(press.max(), 1e-9), 0, 1)
                if press.max() > 0 else np.zeros_like(press))
        img = base.copy()
        img[..., 2] = np.clip(img[..., 2] + occ_n * 0.9, 0, 1)
        img[..., 1] = np.clip(img[..., 1] * (1 - 0.5 * occ_n), 0, 1)
        img[..., 0] = np.clip(img[..., 0] + pr_n * 0.95, 0, 1)
        img[..., 1] = np.clip(img[..., 1] * (1 - 0.6 * pr_n), 0, 1)
        frames.append((day, img, ih))

    if not frames:
        raise FileNotFoundError(f"no day snapshots in {run_dir}")

    fig, ax = plt.subplots(figsize=(6.5, 9))
    im = ax.imshow(frames[0][1], interpolation="nearest")
    ttl = ax.set_title("d000", fontsize=11, loc="left")
    ax.set_xticks([]), ax.set_yticks([])
    leg = [
        Line2D([0], [0], marker="s", color="w",
               markerfacecolor=(0.15, 0.85, 0.35), ms=10, label="Humanos"),
        Line2D([0], [0], marker="s", color="w",
               markerfacecolor=(0.75, 0.55, 0.20), ms=10, label="Ganado"),
        Line2D([0], [0], marker="s", color="w",
               markerfacecolor=(0.2, 0.2, 0.95), ms=10, label="Mosquitos"),
        Line2D([0], [0], marker="s", color="w",
               markerfacecolor=(0.95, 0.1, 0.1), ms=10, label="Mosquitos I_V"),
    ]
    ax.legend(handles=leg, loc="lower right", fontsize=8, framealpha=0.8)

    def _update(i: int):
        day, img, ih = frames[i]
        im.set_data(img)
        ttl.set_text(f"d{day:03d}  —  I_H={ih:,.0f}")
        return [im, ttl]

    ani = animation.FuncAnimation(fig, _update, len(frames), interval=500)
    out = Path(output)
    ani.save(out, writer=animation.PillowWriter(fps=fps))
    plt.close(fig)
    print(f"overlay GIF ({len(frames)} frames) -> {out}")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--aoi", required=True)
    ap.add_argument("--output", default=None)
    ap.add_argument("--fps", type=int, default=2)
    args = ap.parse_args()
    out = args.output or str(
        Path(args.run_dir) / f"{Path(args.run_dir).name}_overlay_hosts.gif")
    render_overlay(args.run_dir, args.aoi, out, args.fps)


if __name__ == "__main__":
    main()
