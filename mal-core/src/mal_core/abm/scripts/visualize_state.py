"""Animate ABM rollout state snapshots (state_dayNNN.tif), transmission snapshots (transmission_dayNNN.tif), and population dynamics (cohort.json).

Produces a 4-panel GIF (M7.4):
  - Top-Left:     adult mosquito density heatmap  (band 1)
  - Top-Right:    suitability heatmap             (band 2)
  - Bottom-Left:  population dynamics line chart from cohort.json
  - Bottom-Right: malaria transmission expansion from transmission_dayNNN.tif

Dynamic vmin/vmax are computed from non-zero values so small densities/prevalences
are visible.

Usage:
    cd mal-abm-fast && uv run python scripts/visualize_state.py \
        --run-dir /tmp/invasion \
        --output /tmp/invasion/animation.gif \
        --sample-every 5
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
from PIL import Image


def load_tif(path: Path) -> tuple[np.ndarray, np.ndarray]:
    """Read a 2-band GeoTIFF, return (band1, band2) as float32 arrays."""
    try:
        import rasterio
    except ImportError:
        raise ImportError("rasterio is required: uv pip install rasterio")
    with rasterio.open(path) as ds:
        b1 = np.asarray(ds.read(1), dtype=np.float32)
        b2 = np.asarray(ds.read(2), dtype=np.float32)
    return b1, b2


def load_transmission_tif(path: Path) -> dict[str, np.ndarray]:
    """Read a 4-band transmission GeoTIFF, return dict of float32 arrays."""
    try:
        import rasterio
    except ImportError:
        raise ImportError("rasterio is required: uv pip install rasterio")
    with rasterio.open(path) as ds:
        count = ds.count
        bands = {}
        names = ["prevalence", "incidence", "pressure", "focus"]
        for b in range(1, min(count + 1, 5)):
            arr = np.asarray(ds.read(b), dtype=np.float32)
            # Mask nodata (-9999)
            arr[arr == -9999.0] = np.nan
            bands[names[b - 1]] = arr
    return bands


def load_cohort(path: Path) -> dict:
    """Read cohort.json produced by --emit-cohort-log."""
    with open(path) as f:
        return json.load(f)


def load_transmission_log(path: Path) -> dict:
    """Read transmission log JSON produced by --emit-transmission-log."""
    with open(path) as f:
        return json.load(f)


def dynamic_vmax(arr: np.ndarray, percentile: float = 99.0) -> float:
    """Compute a vmax from non-zero values at the given percentile."""
    valid = arr[np.isfinite(arr) & (arr > 0)]
    if len(valid) == 0:
        return 1.0
    return float(np.percentile(valid, percentile))


def moving_average(values: list[int], window: int = 7) -> np.ndarray:
    """Return trailing mean, preserving one value per simulation day."""
    values_arr = np.asarray(values, dtype=float)
    if len(values_arr) < 2 or window <= 1:
        return values_arr
    kernel = np.ones(min(window, len(values_arr)))
    return np.convolve(values_arr, kernel, mode="same") / np.convolve(
        np.ones(len(values_arr)), kernel, mode="same"
    )


def make_frame(
    density: np.ndarray,
    suitability: np.ndarray,
    transmission_map: np.ndarray | None,
    transmission_band_name: str,
    cohort: dict | None,
    trans_log: dict | None,
    day_idx: int,
    density_norm: mcolors.Normalize,
    suit_norm: mcolors.Normalize,
    trans_norm: mcolors.Normalize | None,
    density_cmap: str,
    suit_cmap: str,
    trans_cmap: str,
) -> Image.Image:
    """Build a single frame as a PIL Image (4-panel layout)."""
    fig = plt.figure(figsize=(15, 9), dpi=100)
    gs = fig.add_gridspec(2, 2, height_ratios=[1.2, 1.0], hspace=0.38, wspace=0.28)

    ax_d = fig.add_subplot(gs[0, 0])
    ax_s = fig.add_subplot(gs[0, 1])
    ax_a = fig.add_subplot(gs[1, 0])
    ax_t = fig.add_subplot(gs[1, 1])

    # 1. Mosquito Density Heatmap
    im_d = ax_d.imshow(density, cmap=density_cmap, norm=density_norm, origin="lower")
    ax_d.set_title(f"Mosquito Density  (day {day_idx})")
    fig.colorbar(im_d, ax=ax_d, fraction=0.046, pad=0.04)

    # 2. Suitability Heatmap
    im_s = ax_s.imshow(suitability, cmap=suit_cmap, norm=suit_norm, origin="lower")
    ax_s.set_title(f"Biting / Host-Seeking Pressure  (day {day_idx})")
    fig.colorbar(im_s, ax=ax_s, fraction=0.046, pad=0.04)

    # 3. Population Dynamics Line Chart
    if cohort and "daily" in cohort:
        daily = cohort["daily"]
        days = [d["day"] for d in daily]
        adults = [d["n_adults"] for d in daily]
        larvae = [d["n_larvae"] for d in daily]
        eggs = [d.get("n_eggs", 0) for d in daily]
        pupae = [d.get("n_pupae", 0) for d in daily]

        adult_color = "#1565c0"
        ax_a.plot(days, adults, color=adult_color, alpha=0.28, linewidth=0.8)
        ax_a.plot(days, moving_average(adults), label="adults (7d mean)",
                  color=adult_color, linewidth=2.0)
        
        aquatic = (("eggs", eggs, "#d97706"), ("larvae", larvae, "#238636"),
                   ("pupae", pupae, "#7c3aed"))
        for label, values, color in aquatic:
            trend = moving_average(values)
            trend[trend <= 0] = np.nan
            ax_a.plot(days, trend, label=f"{label} (7d mean)", color=color, linewidth=1.4)

        ax_a.set_title("Mosquito Dynamics (Aquatic & Adults)")
        ax_a.set_ylabel("Count (log scale)")
        ax_a.set_yscale("log")
        ax_a.set_xlim(days[0], days[-1])
        ax_a.grid(True, which="both", alpha=0.18, linewidth=0.6)
        ax_a.axvline(day_idx, color="#dc2626", linestyle="--", alpha=0.65, linewidth=1.2)
        ax_a.set_xlabel("Simulation Day")
        ax_a.legend(loc="upper left", fontsize="x-small", framealpha=0.9)
    else:
        ax_a.text(0.5, 0.5, "No cohort log", ha="center", va="center",
                  transform=ax_a.transAxes, fontsize=12, color="gray")
        ax_a.set_axis_off()

    # 4. Malaria Transmission Expansion Heatmap (M7.4)
    if transmission_map is not None:
        masked_t = np.ma.masked_invalid(transmission_map)
        norm = trans_norm or mcolors.Normalize(vmin=0.0, vmax=max(0.01, float(np.nanmax(transmission_map))))
        im_t = ax_t.imshow(masked_t, cmap=trans_cmap, norm=norm, origin="lower")
        title_suffix = ""
        if trans_log and "daily" in trans_log:
            daily_t = trans_log["daily"]
            matching = [d for d in daily_t if d.get("day") == day_idx]
            if matching:
                m = matching[0]
                prev_pct = m.get("prevalence", 0.0) * 100.0
                inc = m.get("incidence", 0.0)
                v_i = m.get("I_V", 0)
                title_suffix = f" (Prev={prev_pct:.1f}%, New={inc:.0f}, I_V={v_i})"
        ax_t.set_title(f"Malaria Expansion: {transmission_band_name.capitalize()}{title_suffix}")
        fig.colorbar(im_t, ax=ax_t, fraction=0.046, pad=0.04)
    else:
        ax_t.text(0.5, 0.5, "Transmission outputs absent\n(Use --enable-transmission)",
                  ha="center", va="center", transform=ax_t.transAxes,
                  fontsize=11, color="gray")
        ax_t.set_axis_off()

    fig.tight_layout()
    fig.canvas.draw()
    buf = fig.canvas.buffer_rgba()
    img = np.asarray(buf)[:, :, :3]
    plt.close(fig)
    return Image.fromarray(img)


def find_snapshot_files(run_dir: Path) -> list[tuple[Path, int]]:
    """Find state_dayNNN.tif files, sorted by day number."""
    results = []
    for p in run_dir.glob("*.tif"):
        if "transmission" in p.name:
            continue
        m = re.search(r"_day(\d+)\.tif$", p.name)
        if m:
            results.append((p, int(m.group(1))))
    results.sort(key=lambda x: x[1])
    return results


def find_transmission_files(run_dir: Path) -> dict[int, Path]:
    """Find transmission_dayNNN.tif files indexed by day number."""
    results = {}
    for p in run_dir.glob("*transmission*.tif"):
        m = re.search(r"_day(\d+)\.tif$", p.name)
        if m:
            results[int(m.group(1))] = p
    return results


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Animate ABM rollout state and transmission snapshots into a 4-panel GIF."
    )
    parser.add_argument(
        "--run-dir", type=Path, required=True,
        help="Directory containing state_dayNNN.tif and transmission_dayNNN.tif files.",
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
        "--transmission-log", type=Path, default=None,
        help="Path to transmission log JSON. Auto-detected if omitted.",
    )
    parser.add_argument(
        "--transmission-band", default="prevalence",
        choices=["prevalence", "incidence", "pressure", "focus"],
        help="Transmission band to display (default: prevalence).",
    )
    parser.add_argument(
        "--sample-every", type=int, default=1,
        help="Only render every Nth snapshot (default: 1).",
    )
    parser.add_argument(
        "--fps", type=int, default=4,
        help="Frames per second in GIF (default: 4).",
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
        "--transmission-cmap", default="magma",
        help="Colormap for transmission expansion (default: magma).",
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

    trans_files = find_transmission_files(args.run_dir)

    # Auto-detect cohort log
    cohort_path = args.cohort_log
    if cohort_path is None:
        cohort_path = args.run_dir / "cohort.json"
        if not cohort_path.exists():
            matches = sorted(args.run_dir.glob("*_cohort.json"))
            if matches:
                cohort_path = matches[0]
    cohort = load_cohort(cohort_path) if cohort_path and cohort_path.exists() else None

    # Auto-detect transmission log
    trans_log_path = args.transmission_log
    if trans_log_path is None:
        trans_log_path = args.run_dir / "transmission.json"
        if not trans_log_path.exists():
            matches = sorted(args.run_dir.glob("*transmission*.json"))
            if matches:
                trans_log_path = matches[0]
    trans_log = load_transmission_log(trans_log_path) if trans_log_path and trans_log_path.exists() else None

    sampled = tif_files[:: max(args.sample_every, 1)]
    print(f"Found {len(tif_files)} snapshots ({len(trans_files)} transmission rasters), sampling every {args.sample_every} -> {len(sampled)} frames")

    # Load sampled frames to compute global scale
    all_density: list[np.ndarray] = []
    all_suit: list[np.ndarray] = []
    all_trans: list[np.ndarray | None] = []
    all_days: list[int] = []

    for f, day_num in sampled:
        d, s = load_tif(f)
        all_density.append(d)
        all_suit.append(s)
        all_days.append(day_num)
        if day_num in trans_files:
            tbands = load_transmission_tif(trans_files[day_num])
            all_trans.append(tbands.get(args.transmission_band))
        else:
            all_trans.append(None)

    stack_d = np.concatenate([a.ravel() for a in all_density])
    stack_s = np.concatenate([a.ravel() for a in all_suit])

    vmin_d = np.percentile(stack_d[stack_d > 0], args.vmin_quantile) if np.any(stack_d > 0) else 0.0
    vmax_d = np.percentile(stack_d[stack_d > 0], args.vmax_quantile) if np.any(stack_d > 0) else 1.0
    vmin_s = np.percentile(stack_s[stack_s > 0], args.vmin_quantile) if np.any(stack_s > 0) else 0.0
    vmax_s = np.percentile(stack_s[stack_s > 0], args.vmax_quantile) if np.any(stack_s > 0) else 1.0

    if vmax_d / max(vmin_d, 1e-10) > 10:
        density_norm = mcolors.LogNorm(vmin=max(vmin_d, 1e-6), vmax=vmax_d)
    else:
        density_norm = mcolors.Normalize(vmin=vmin_d, vmax=vmax_d)
    if vmax_s / max(vmin_s, 1e-10) > 10:
        suit_norm = mcolors.LogNorm(vmin=max(vmin_s, 1e-6), vmax=vmax_s)
    else:
        suit_norm = mcolors.Normalize(vmin=vmin_s, vmax=vmax_s)

    # Transmission global scale
    trans_valid = [t for t in all_trans if t is not None]
    trans_norm = None
    if trans_valid:
        stack_t = np.concatenate([t[np.isfinite(t)].ravel() for t in trans_valid if len(t[np.isfinite(t)]) > 0])
        if len(stack_t) > 0 and np.any(stack_t > 0):
            t_max = max(0.01, float(np.percentile(stack_t[stack_t > 0], args.vmax_quantile)))
            trans_norm = mcolors.Normalize(vmin=0.0, vmax=t_max)
        else:
            trans_norm = mcolors.Normalize(vmin=0.0, vmax=1.0)

    # Render frames
    frames: list[Image.Image] = []
    for i, (d, s, t) in enumerate(zip(all_density, all_suit, all_trans)):
        day_num = all_days[i]
        frame = make_frame(
            d, s, t, args.transmission_band,
            cohort, trans_log, day_num,
            density_norm, suit_norm, trans_norm,
            args.density_cmap, args.suit_cmap, args.transmission_cmap,
        )
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
    print(f"Saved {len(frames)}-frame 4-panel GIF -> {args.output}")


if __name__ == "__main__":
    main()
