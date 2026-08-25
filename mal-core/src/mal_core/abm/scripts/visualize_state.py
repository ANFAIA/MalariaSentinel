#!/usr/bin/env python3
"""visualize_state.py — Animate ABM mosquito vector spread and population dynamics.

Produces a high-resolution 2-panel GIF:
  - Left panel:  Mosquito Vector Spatial Spread (Density Heatmap with visible foci)
  - Right panel: Population Dynamics Line Chart (Adults & Aquatic Stages, Log Scale)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
import rasterio
from scipy.ndimage import maximum_filter
from PIL import Image


def load_state_tif(path: Path) -> tuple[np.ndarray, np.ndarray]:
    """Read a 2-band state GeoTIFF, return (density, suitability) arrays."""
    with rasterio.open(path) as src:
        b1 = np.asarray(src.read(1), dtype=np.float32)
        b2 = np.asarray(src.read(2), dtype=np.float32)
    return b1, b2


def load_cohort(path: Path | None) -> dict | None:
    if path is None or not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def moving_average(values: list[int | float], window: int = 7) -> np.ndarray:
    """Return trailing moving average."""
    values_arr = np.asarray(values, dtype=float)
    if len(values_arr) < 2 or window <= 1:
        return values_arr
    kernel = np.ones(min(window, len(values_arr))) / float(min(window, len(values_arr)))
    return np.convolve(values_arr, kernel, mode="same")


def make_vector_frame(
    density: np.ndarray,
    cohort: dict | None,
    day_idx: int,
    density_norm: mcolors.Normalize,
    cmap: str = "YlOrRd",
) -> Image.Image:
    """Build a 2-panel vector dynamics frame as a PIL Image."""
    fig = plt.figure(figsize=(16, 8.5), dpi=110)
    gs = fig.add_gridspec(1, 2, width_ratios=[1.0, 1.25], wspace=0.18)

    ax_map = fig.add_subplot(gs[0])
    ax_chart = fig.add_subplot(gs[1])

    # Left: Enhanced spatial map with glowing foci
    d_vis = np.maximum(density, maximum_filter(density, size=5) * 0.75)
    d_vis[d_vis <= 0] = np.nan

    ax_map.set_facecolor("#0f172a")  # Dark slate background for maximum glow contrast
    im = ax_map.imshow(d_vis, cmap=cmap, norm=density_norm, origin="lower")

    active_foci = int(np.count_nonzero(density > 0))
    adult_count = 0
    if cohort and "daily" in cohort:
        matching = [d for d in cohort["daily"] if d.get("day") == day_idx]
        if matching:
            adult_count = matching[0].get("n_adults", 0)

    ax_map.set_title(
        f"Mosquito Vector Spread (Day {day_idx})\n[Adults: {adult_count:,} | Active Cells: {active_foci}]",
        fontsize=13, fontweight="bold", pad=8
    )
    ax_map.set_xticks([])
    ax_map.set_yticks([])
    cbar = fig.colorbar(im, ax=ax_map, fraction=0.046, pad=0.03)
    cbar.set_label("Relative Density Index", fontsize=10)

    # Right: Mosquito population dynamics
    if cohort and "daily" in cohort:
        daily = cohort["daily"]
        days = [d["day"] for d in daily]
        adults = [d["n_adults"] for d in daily]
        larvae = [d["n_larvae"] for d in daily]
        eggs = [d.get("n_eggs", 0) for d in daily]
        pupae = [d.get("n_pupae", 0) for d in daily]

        adult_color = "#1d4ed8"
        ax_chart.plot(days, adults, color=adult_color, alpha=0.25, linewidth=0.8)
        ax_chart.plot(days, moving_average(adults), label="Adults (7d mean)", color=adult_color, linewidth=2.2)

        aquatic = (("Eggs", eggs, "#d97706"), ("Larvae", larvae, "#16a34a"), ("Pupae", pupae, "#9333ea"))
        for label, values, color in aquatic:
            trend = moving_average(values)
            trend[trend <= 0] = np.nan
            ax_chart.plot(days, trend, label=f"{label} (7d mean)", color=color, linewidth=1.5)

        ax_chart.set_title("Population Dynamics (Aquatic & Adults)", fontsize=13, fontweight="bold", pad=8)
        ax_chart.set_ylabel("Mosquito Count (log scale)", fontsize=11)
        ax_chart.set_yscale("log")
        ax_chart.set_xlim(0, max(days))
        ax_chart.grid(True, which="both", alpha=0.22, linewidth=0.6)
        ax_chart.axvline(day_idx, color="#dc2626", linestyle="--", alpha=0.85, linewidth=1.8, label=f"Day {day_idx}")
        ax_chart.set_xlabel("Simulation Day", fontsize=11)
        ax_chart.legend(loc="upper left", fontsize=10, framealpha=0.92)
    else:
        ax_chart.text(0.5, 0.5, "No cohort log available", ha="center", va="center", transform=ax_chart.transAxes, fontsize=12, color="gray")
        ax_chart.set_axis_off()

    fig.canvas.draw()
    buf = fig.canvas.buffer_rgba()
    img = np.asarray(buf)[:, :, :3]
    plt.close(fig)
    return Image.fromarray(img)


def find_state_files(run_dir: Path) -> list[tuple[Path, int]]:
    """Find state snapshot GeoTIFFs sorted by day number."""
    results = []
    for p in run_dir.glob("*.tif"):
        if "transmission" in p.name:
            continue
        m = re.search(r"_day(\d+)\.tif$", p.name)
        if m:
            results.append((p, int(m.group(1))))
    results.sort(key=lambda x: x[1])
    return results


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Animate ABM mosquito vector spread and population dynamics into a 2-panel GIF."
    )
    parser.add_argument(
        "--run-dir", type=Path, required=True,
        help="Directory containing state_dayNNN.tif files.",
    )
    parser.add_argument(
        "--output", type=Path, required=True,
        help="Output GIF path.",
    )
    parser.add_argument(
        "--cohort-log", type=Path, default=None,
        help="Path to cohort JSON. Auto-detected if omitted.",
    )
    parser.add_argument(
        "--sample-every", type=int, default=1,
        help="Render every Nth snapshot (default: 1).",
    )
    parser.add_argument(
        "--fps", type=int, default=4,
        help="Frames per second in GIF (default: 4).",
    )
    parser.add_argument(
        "--cmap", default="YlOrRd",
        help="Colormap for mosquito density (default: YlOrRd).",
    )
    parser.add_argument(
        "--vmax-quantile", type=float, default=99.5,
        help="Percentile for non-zero vmax (default: 99.5).",
    )
    args = parser.parse_args(argv)

    tif_files = find_state_files(args.run_dir)
    if not tif_files:
        print(f"error: no state_dayNNN.tif files found in {args.run_dir}", file=sys.stderr)
        sys.exit(1)

    cohort_path = args.cohort_log
    if cohort_path is None:
        cohort_path = args.run_dir / "cohort.json"
        if not cohort_path.exists():
            matches = sorted(args.run_dir.glob("*_cohort.json"))
            if matches:
                cohort_path = matches[0]
    cohort = load_cohort(cohort_path) if cohort_path and cohort_path.exists() else None

    sampled = tif_files[:: max(args.sample_every, 1)]
    print(f"Found {len(tif_files)} state snapshots, sampling every {args.sample_every} -> {len(sampled)} frames")

    all_density: list[np.ndarray] = []
    all_days: list[int] = []

    for f, day_num in sampled:
        d, _ = load_state_tif(f)
        all_density.append(d)
        all_days.append(day_num)

    stack_d = np.concatenate([a[np.isfinite(a)].ravel() for a in all_density])
    pos_d = stack_d[stack_d > 0]
    vmax_d = float(np.percentile(pos_d, args.vmax_quantile)) if len(pos_d) > 0 else 1.0
    density_norm = mcolors.PowerNorm(gamma=0.30, vmin=0.001, vmax=max(0.01, vmax_d))

    frames: list[Image.Image] = []
    for i, (d, day_num) in enumerate(zip(all_density, all_days)):
        frame = make_vector_frame(
            density=d,
            cohort=cohort,
            day_idx=day_num,
            density_norm=density_norm,
            cmap=args.cmap,
        )
        frames.append(frame)
        if (i + 1) % 10 == 0 or i + 1 == len(all_density):
            print(f"  rendered {i + 1}/{len(all_density)} frames")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    duration_ms = int(1000 / args.fps)
    frames[0].save(
        args.output,
        save_all=True,
        append_images=frames[1:],
        duration=duration_ms,
        loop=0,
    )
    print(f"Saved {len(frames)}-frame Vector ABM GIF -> {args.output}")


if __name__ == "__main__":
    main()
