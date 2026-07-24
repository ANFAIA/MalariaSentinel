"""Animate ABM rollout state snapshots (state_dayNNN.tif) and population dynamics (cohort.json).

Produces a 3-panel GIF:
  - Left:   adult density heatmap  (band 1)
  - Right:  suitability heatmap    (band 2)
  - Bottom: population dynamics line chart from cohort.json

Dynamic vmin/vmax are computed from non-zero values so small densities
(0.001-0.13) are visible.

Usage:
    cd mal-abm-fast && uv run python scripts/visualize_state.py \
        --run-dir /tmp/invasion \
        --output /tmp/invasion/animation.gif \
        --sample-every 5
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
from PIL import Image


def load_tif(path: Path) -> tuple[np.ndarray, np.ndarray]:
    """Read a 2-band GeoTIFF, return (band1, band2) as float32 arrays."""
    try:
        import rasterio
    except ImportError:
        # fall back to GDAL via CLI (unlikely on dev machines)
        raise ImportError("rasterio is required: uv pip install rasterio")
    with rasterio.open(path) as ds:
        b1 = ds.read(1).astype(np.float32)
        b2 = ds.read(2).astype(np.float32)
    return b1, b2


def load_cohort(path: Path) -> dict:
    """Read cohort.json produced by --emit-cohort-log."""
    with open(path) as f:
        return json.load(f)


def dynamic_vmax(arr: np.ndarray, percentile: float = 99.0) -> float:
    """Compute a vmax from non-zero values at the given percentile."""
    nz = arr[arr > 0]
    if len(nz) == 0:
        return 1.0
    return float(np.percentile(nz, percentile))


def make_frame(
    density: np.ndarray,
    suitability: np.ndarray,
    cohort: dict | None,
    day_idx: int,
    density_norm: mcolors.Normalize,
    suit_norm: mcolors.Normalize,
    density_cmap: str,
    suit_cmap: str,
) -> Image.Image:
    """Build a single frame as a PIL Image."""
    fig = plt.figure(figsize=(14, 7), dpi=100)
    gs = fig.add_gridspec(2, 2, height_ratios=[3, 1], hspace=0.3, wspace=0.25)

    ax_d = fig.add_subplot(gs[0, 0])
    ax_s = fig.add_subplot(gs[0, 1])
    ax_p = fig.add_subplot(gs[1, :])

    # density heatmap
    im_d = ax_d.imshow(density, cmap=density_cmap, norm=density_norm, origin="lower")
    ax_d.set_title(f"Density  (day {day_idx})")
    fig.colorbar(im_d, ax=ax_d, fraction=0.046, pad=0.04)

    # suitability heatmap
    im_s = ax_s.imshow(suitability, cmap=suit_cmap, norm=suit_norm, origin="lower")
    ax_s.set_title(f"Suitability  (day {day_idx})")
    fig.colorbar(im_s, ax=ax_s, fraction=0.046, pad=0.04)

    # population dynamics
    if cohort and "daily" in cohort:
        daily = cohort["daily"]
        days = [d["day"] for d in daily]
        alive = [d["n_alive"] for d in daily]
        adults = [d["n_adults"] for d in daily]
        larvae = [d["n_larvae"] for d in daily]

        ax_p.plot(days, alive, label="alive", color="#1f77b4")
        ax_p.plot(days, adults, label="adults", color="#ff7f0e")
        ax_p.plot(days, larvae, label="larvae", color="#2ca02c")

        # vertical line at current day
        if 1 <= day_idx <= len(days):
            ax_p.axvline(day_idx, color="red", linestyle="--", alpha=0.6)

        ax_p.set_xlabel("Day")
        ax_p.set_ylabel("Population")
        ax_p.legend(loc="upper left", fontsize="small")
        ax_p.set_title("Population dynamics")
    else:
        ax_p.text(0.5, 0.5, "No cohort.json", ha="center", va="center",
                  transform=ax_p.transAxes, fontsize=12, color="gray")
        ax_p.set_axis_off()

    fig.tight_layout()

    fig.canvas.draw()
    buf = fig.canvas.buffer_rgba()
    img = np.asarray(buf)[:, :, :3]  # drop alpha channel → RGB
    plt.close(fig)
    return Image.fromarray(img)


def find_snapshot_files(run_dir: Path) -> list[tuple[Path, int]]:
    """Find state_dayNNN.tif files, sorted by day number.

    Returns list of (path, day_number) tuples.
    """
    import re
    results = []
    for p in run_dir.glob("state_day*.tif"):
        m = re.search(r"state_day(\d+)", p.name)
        if m:
            results.append((p, int(m.group(1))))
    results.sort(key=lambda x: x[1])
    return results


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Animate ABM rollout state snapshots into a GIF."
    )
    parser.add_argument(
        "--run-dir", type=Path, required=True,
        help="Directory containing state_dayNNN.tif files and optionally cohort.json.",
    )
    parser.add_argument(
        "--output", type=Path, required=True,
        help="Output GIF path.",
    )
    parser.add_argument(
        "--sample-every", type=int, default=1,
        help="Only render every Nth snapshot (default: 1 = all).",
    )
    parser.add_argument(
        "--fps", type=int, default=4,
        help="Frames per second in the GIF (default: 4).",
    )
    parser.add_argument(
        "--density-cmap", default="YlOrRd",
        help="Colormap for density (default: YlOrRd).",
    )
    parser.add_argument(
        "--suit-cmap", default="viridis",
        help="Colormap for suitability (default: viridis).",
    )
    parser.add_argument(
        "--vmin-quantile", type=float, default=1.0,
        help="Percentile for non-zero vmin (default: 1).",
    )
    parser.add_argument(
        "--vmax-quantile", type=float, default=99.0,
        help="Percentile for non-zero vmax (default: 99).",
    )
    args = parser.parse_args(argv)

    tif_files = find_snapshot_files(args.run_dir)
    if not tif_files:
        print(f"error: no state_dayNNN.tif files found in {args.run_dir}", file=sys.stderr)
        sys.exit(1)

    cohort_path = args.run_dir / "cohort.json"
    cohort = load_cohort(cohort_path) if cohort_path.exists() else None
    if cohort is None:
        print(f"warning: {cohort_path} not found; population panel will be empty", file=sys.stderr)

    # sample — tif_files is list of (path, day_number)
    sampled = tif_files[:: max(args.sample_every, 1)]
    print(f"Found {len(tif_files)} snapshots, sampling every {args.sample_every} -> {len(sampled)} frames")

    # load all sampled frames to compute global dynamic range
    all_density: list[np.ndarray] = []
    all_suit: list[np.ndarray] = []
    all_days: list[int] = []
    for f, day_num in sampled:
        d, s = load_tif(f)
        all_density.append(d)
        all_suit.append(s)
        all_days.append(day_num)

    # stack for global percentile computation
    stack_d = np.concatenate([a.ravel() for a in all_density])
    stack_s = np.concatenate([a.ravel() for a in all_suit])

    vmin_d = np.percentile(stack_d[stack_d > 0], args.vmin_quantile) if np.any(stack_d > 0) else 0.0
    vmax_d = np.percentile(stack_d[stack_d > 0], args.vmax_quantile) if np.any(stack_d > 0) else 1.0
    vmin_s = np.percentile(stack_s[stack_s > 0], args.vmin_quantile) if np.any(stack_s > 0) else 0.0
    vmax_s = np.percentile(stack_s[stack_s > 0], args.vmax_quantile) if np.any(stack_s > 0) else 1.0

    # Use LogNorm when data spans > 1 order of magnitude, else linear
    if vmax_d / max(vmin_d, 1e-10) > 10:
        density_norm = mcolors.LogNorm(vmin=max(vmin_d, 1e-6), vmax=vmax_d)
    else:
        density_norm = mcolors.Normalize(vmin=vmin_d, vmax=vmax_d)
    if vmax_s / max(vmin_s, 1e-10) > 10:
        suit_norm = mcolors.LogNorm(vmin=max(vmin_s, 1e-6), vmax=vmax_s)
    else:
        suit_norm = mcolors.Normalize(vmin=vmin_s, vmax=vmax_s)

    print(f"Density range:  vmin={vmin_d:.6f}  vmax={vmax_d:.6f}")
    print(f"Suitability range:  vmin={vmin_s:.6f}  vmax={vmax_s:.6f}")

    # generate frames
    frames: list[Image.Image] = []
    for i, (d, s) in enumerate(zip(all_density, all_suit)):
        day_num = all_days[i]  # actual day from filename
        frame = make_frame(d, s, cohort, day_num, density_norm, suit_norm,
                           args.density_cmap, args.suit_cmap)
        frames.append(frame)
        if (i + 1) % 10 == 0 or i + 1 == len(all_density):
            print(f"  rendered {i + 1}/{len(all_density)} frames")

    if not frames:
        print("error: no frames to render", file=sys.stderr)
        sys.exit(1)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    duration_ms = int(1000 / args.fps)
    frames[0].save(
        args.output,
        save_all=True,
        append_images=frames[1:],
        duration=duration_ms,
        loop=0,
    )
    print(f"Saved {len(frames)}-frame GIF -> {args.output}")


if __name__ == "__main__":
    main()