#!/usr/bin/env python3
"""visualize_state.py — Animate ABM mosquito vector spread and population dynamics.

Produces a high-resolution 2-panel GIF:
  - Left panel:  Mosquito Vector Spatial Spread (adult-count heatmap, log colour scale)
  - Right panel: Population Dynamics Line Chart (Adults & Aquatic Stages, Log Scale)

Data contract 4.0: state GeoTIFF bands are RAW COUNTS, not a normalized
density index. Band 1 is ``adult_patch_count`` and band 2 is
``adult_cell_count``; the heatmap colours band 1 on an explicit log scale
(1 adult .. global max) so sparse foci stay visible. The 5x5 max-filter
halo is a purely cosmetic glow and is never used for the colour scale.
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
    """Read a 2-band state GeoTIFF, return (adult_patch_count, adult_cell_count) raw counts."""
    with rasterio.open(path) as src:
        b1 = np.asarray(src.read(1), dtype=np.float32)
        b2 = np.asarray(src.read(2), dtype=np.float32)
    return b1, b2


def load_cohort(path: Path | None) -> dict | None:
    if path is None or not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def cohort_row_for_day(cohort: dict | None, day_idx: int) -> dict | None:
    """Return the cohort row matching a 1-based snapshot day (cohort logs are 0-based)."""
    if not cohort or "daily" not in cohort:
        return None
    target = day_idx - 1
    for row in cohort["daily"]:
        if row.get("day") == target:
            return row
    return None


def moving_average(values: list[int | float], window: int = 7) -> np.ndarray:
    """Return a trailing moving average (expanding window at the start, no zero padding)."""
    values_arr = np.asarray(values, dtype=float)
    n = len(values_arr)
    if n < 2 or window <= 1:
        return values_arr
    w = min(window, n)
    out = np.empty(n, dtype=float)
    # First w-1 points: expanding mean; from w on: true trailing mean.
    out[: w - 1] = np.cumsum(values_arr[: w - 1]) / np.arange(1, w)
    cumsum = np.cumsum(values_arr)
    out[w - 1 :] = (cumsum[w - 1 :] - np.concatenate(([0.0], cumsum[:-w]))) / w
    return out


def make_vector_frame(
    adult_count_map: np.ndarray,
    cohort: dict | None,
    day_idx: int,
    count_norm: mcolors.Normalize,
    cmap: str = "YlOrRd",
) -> Image.Image:
    """Build a 2-panel vector dynamics frame as a PIL Image.

    ``day_idx`` is the snapshot day number (1-based, from ``_dayNNN.tif``);
    the cohort log is 0-based, so the matching cohort row is ``day_idx - 1``.
    """
    fig = plt.figure(figsize=(16, 8.5), dpi=110)
    gs = fig.add_gridspec(1, 2, width_ratios=[1.0, 1.25], wspace=0.18)

    ax_map = fig.add_subplot(gs[0])
    ax_chart = fig.add_subplot(gs[1])

    # Left: raw adult counts with a cosmetic 5x5 max-filter glow (not part of the colour scale).
    d_vis = np.maximum(adult_count_map, maximum_filter(adult_count_map, size=5) * 0.75)
    d_vis[d_vis <= 0] = np.nan

    ax_map.set_facecolor("#0f172a")  # Dark slate background for maximum glow contrast
    # Raster row 0 is the northern edge; keep geographic north at top.
    im = ax_map.imshow(d_vis, cmap=cmap, norm=count_norm, origin="upper")

    active_foci = int(np.count_nonzero(adult_count_map > 0))
    adult_count = 0
    cohort_day = day_idx - 1
    row = cohort_row_for_day(cohort, day_idx)
    if row is not None:
        adult_count = row.get("n_adults", 0)

    ax_map.set_title(
        f"Mosquito Vector Spread (Day {day_idx})\n[Adults: {adult_count:,} | Active Cells: {active_foci}]",
        fontsize=13, fontweight="bold", pad=8
    )
    ax_map.set_xticks([])
    ax_map.set_yticks([])
    cbar = fig.colorbar(im, ax=ax_map, orientation="horizontal", fraction=0.046, pad=0.06, aspect=35)
    cbar.ax.tick_params(labelsize=8)
    cbar.set_label("Adults per cell (count, log colour scale)", fontsize=9, labelpad=4)

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
        ax_chart.axvline(cohort_day, color="#dc2626", linestyle="--", alpha=0.85, linewidth=1.8, label=f"Day {day_idx}")
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
    """Find state snapshot GeoTIFFs sorted by day number.

    Scans the run directory top level first; if nothing matches (e.g. a run
    that nests snapshots in a subfolder), falls back to a recursive scan.
    """
    def _scan(root: Path, recursive: bool) -> list[tuple[Path, int]]:
        candidates = root.rglob("*.tif") if recursive else root.glob("*.tif")
        found: list[tuple[Path, int]] = []
        for p in candidates:
            if "transmission" in p.name:
                continue
            m = re.search(r"_day(\d+)\.tif$", p.name)
            if m:
                found.append((p, int(m.group(1))))
        found.sort(key=lambda x: x[1])
        return found

    results = _scan(run_dir, recursive=False)
    return results or _scan(run_dir, recursive=True)


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
        help="Colormap for adult counts (default: YlOrRd).",
    )
    parser.add_argument(
        "--vmax-quantile", type=float, default=100.0,
        help="Percentile of positive raw adult counts used as colour-scale vmax (default: 100 = absolute max).",
    )
    parser.add_argument(
        "--max-width", type=int, default=None,
        help="Downscale rendered frames to this maximum width in pixels (default: no limit).",
    )
    args = parser.parse_args(argv)

    tif_files = find_state_files(args.run_dir)
    if not tif_files:
        print(f"error: no state *_dayNNN.tif files found in {args.run_dir}", file=sys.stderr)
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
    # Contract 4.0: raw counts. LogNorm keeps 1-adult cells visible next to 100+ foci.
    count_norm = mcolors.LogNorm(vmin=1.0, vmax=max(2.0, vmax_d))
    print(f"Colour scale: log, vmin=1 adults/cell, vmax={max(2.0, vmax_d):.1f} adults/cell")

    frames: list[Image.Image] = []
    for i, (d, day_num) in enumerate(zip(all_density, all_days)):
        frame = make_vector_frame(
            adult_count_map=d,
            cohort=cohort,
            day_idx=day_num,
            count_norm=count_norm,
            cmap=args.cmap,
        )
        if args.max_width and frame.width > args.max_width:
            height = int(round(frame.height * args.max_width / frame.width))
            frame = frame.resize((args.max_width, height), Image.LANCZOS)
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
        optimize=True,
    )
    print(f"Saved {len(frames)}-frame Vector ABM GIF -> {args.output}")


if __name__ == "__main__":
    main()
