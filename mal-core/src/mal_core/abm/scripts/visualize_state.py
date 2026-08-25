#!/usr/bin/env python3
"""visualize_state.py — Animate ABM rollout state and transmission into a 4-panel GIF.

Panels:
  [0, 0] Mosquito Density Spatial Heatmap (B1) with country silhouette
  [0, 1] Biting / Host-Seeking Pressure Heatmap (B2)
  [1, 0] Mosquito Dynamics Line Chart (Aquatic & Adults, log-scale)
  [1, 1] Malaria Transmission Expansion Heatmap (SEIR Prevalence / Incidence)
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
from PIL import Image


def load_tif(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Load bands 1 and 2 and land mask from a state snapshot GeoTIFF."""
    with rasterio.open(path) as src:
        b1 = src.read(1).astype(np.float32)
        b2 = src.read(2).astype(np.float32)
        nodata = src.nodata

    if nodata is not None:
        land_mask = np.isfinite(b1) & (b1 != nodata)
        b1[~land_mask] = np.nan
        b2[~land_mask] = np.nan
    else:
        land_mask = np.isfinite(b1)
    return b1, b2, land_mask


def load_transmission_tif(path: Path) -> tuple[dict[str, np.ndarray], np.ndarray]:
    """Load transmission snapshot bands: 1=prevalence, 2=incidence, 3=pressure, 4=focus."""
    band_names = ["prevalence", "incidence", "pressure", "focus"]
    result: dict[str, np.ndarray] = {}
    with rasterio.open(path) as src:
        nodata = src.nodata
        for b_idx, b_name in enumerate(band_names, start=1):
            if b_idx <= src.count:
                arr = src.read(b_idx).astype(np.float32)
                if nodata is not None:
                    mask = np.isfinite(arr) & (arr != nodata)
                    arr[~mask] = np.nan
                result[b_name] = arr

    land_mask = np.isfinite(result["prevalence"]) if "prevalence" in result else np.ones((10, 10), dtype=bool)
    return result, land_mask


def load_cohort(path: Path | None) -> dict | None:
    if path is None or not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def load_transmission_log(path: Path | None) -> dict | None:
    if path is None or not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def moving_average(values: list[int | float], window: int = 7) -> np.ndarray:
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
    land_mask: np.ndarray,
    transmission_map: np.ndarray | None,
    transmission_band_name: str,
    cohort: dict | None,
    trans_meta: dict | None,
    day_idx: int,
    density_norm: mcolors.Normalize,
    suit_norm: mcolors.Normalize,
    trans_norm: mcolors.Normalize | None,
    density_cmap: str,
    suit_cmap: str,
    trans_cmap: str,
) -> Image.Image:
    """Build a single frame as a PIL Image (optimized 4-panel layout)."""
    fig = plt.figure(figsize=(16, 11), dpi=100)
    gs = fig.add_gridspec(2, 2, width_ratios=[1.0, 1.0], height_ratios=[1.20, 0.95], wspace=0.14, hspace=0.20)

    ax_d = fig.add_subplot(gs[0, 0])
    ax_s = fig.add_subplot(gs[0, 1])
    ax_a = fig.add_subplot(gs[1, 0])
    ax_t = fig.add_subplot(gs[1, 1])

    # Base silhouette of the country
    land_bg = np.where(land_mask, 1.0, np.nan)
    bg_cmap = mcolors.ListedColormap(["#edf2f7"])

    # 1. Mosquito Density Heatmap
    ax_d.imshow(land_bg, cmap=bg_cmap, origin="lower")
    d_pos = np.ma.masked_where(~land_mask | (density <= 0) | np.isnan(density), density)
    im_d = ax_d.imshow(d_pos, cmap=density_cmap, norm=density_norm, origin="lower")
    ax_d.set_title(f"Mosquito Density  (Day {day_idx})", fontsize=12, fontweight="bold", pad=8)
    ax_d.set_xticks([])
    ax_d.set_yticks([])
    cbar_d = fig.colorbar(im_d, ax=ax_d, fraction=0.038, pad=0.02)
    cbar_d.ax.tick_params(labelsize=9)

    # 2. Host-Seeking / Biting Pressure Heatmap
    ax_s.imshow(land_bg, cmap=bg_cmap, origin="lower")
    s_pos = np.ma.masked_where(~land_mask | (suitability <= 0) | np.isnan(suitability), suitability)
    im_s = ax_s.imshow(s_pos, cmap=suit_cmap, norm=suit_norm, origin="lower")
    ax_s.set_title(f"Biting / Host-Seeking Pressure  (Day {day_idx})", fontsize=12, fontweight="bold", pad=8)
    ax_s.set_xticks([])
    ax_s.set_yticks([])
    cbar_s = fig.colorbar(im_s, ax=ax_s, fraction=0.038, pad=0.02)
    cbar_s.ax.tick_params(labelsize=9)

    # 3. Population Dynamics Line Chart
    if cohort and "daily" in cohort:
        daily = cohort["daily"]
        days = [d["day"] for d in daily]
        adults = [d["n_adults"] for d in daily]
        larvae = [d["n_larvae"] for d in daily]
        eggs = [d.get("n_eggs", 0) for d in daily]
        pupae = [d.get("n_pupae", 0) for d in daily]

        adult_color = "#1565c0"
        ax_a.plot(days, adults, color=adult_color, alpha=0.25, linewidth=0.8)
        ax_a.plot(days, moving_average(adults), label="Adults (7d mean)", color=adult_color, linewidth=2.0)

        aquatic = (("Eggs", eggs, "#d97706"), ("Larvae", larvae, "#238636"), ("Pupae", pupae, "#7c3aed"))
        for label, values, color in aquatic:
            trend = moving_average(values)
            trend[trend <= 0] = np.nan
            ax_a.plot(days, trend, label=f"{label} (7d mean)", color=color, linewidth=1.4)

        ax_a.set_title("Mosquito Dynamics (Aquatic & Adults)", fontsize=12, fontweight="bold", pad=8)
        ax_a.set_ylabel("Count (log scale)", fontsize=10)
        ax_a.set_yscale("log")
        ax_a.set_xlim(0, max(days))
        ax_a.grid(True, which="both", alpha=0.18, linewidth=0.6)
        ax_a.axvline(day_idx, color="#dc2626", linestyle="--", alpha=0.75, linewidth=1.5)
        ax_a.set_xlabel("Simulation Day", fontsize=10)
        ax_a.legend(loc="upper left", fontsize="small", framealpha=0.9)
    else:
        ax_a.text(0.5, 0.5, "No cohort log", ha="center", va="center", transform=ax_a.transAxes, fontsize=12, color="gray")
        ax_a.set_axis_off()

    # 4. Malaria Transmission Expansion Heatmap
    if transmission_map is not None:
        ax_t.imshow(land_bg, cmap=bg_cmap, origin="lower")
        t_pos = np.ma.masked_where(~land_mask | (transmission_map <= 0) | np.isnan(transmission_map), transmission_map)
        norm = trans_norm or mcolors.Normalize(vmin=0.0, vmax=max(0.01, float(np.nanmax(transmission_map))))
        im_t = ax_t.imshow(t_pos, cmap=trans_cmap, norm=norm, origin="lower")

        title_suffix = ""
        if trans_meta:
            prev_pct = trans_meta.get("mean_prevalence", 0.0) * 100.0
            inc = trans_meta.get("total_incidence", 0.0)
            v_i = trans_meta.get("vector_infectious", 0)
            title_suffix = f" [Prev={prev_pct:.1f}%, New={inc:.0f}, I_V={v_i}]"

        ax_t.set_title(f"Malaria {transmission_band_name.capitalize()} (Day {day_idx}){title_suffix}", fontsize=12, fontweight="bold", pad=8)
        ax_t.set_xticks([])
        ax_t.set_yticks([])
        cbar_t = fig.colorbar(im_t, ax=ax_t, fraction=0.038, pad=0.02)
        cbar_t.ax.tick_params(labelsize=9)
    else:
        ax_t.text(0.5, 0.5, "Transmission outputs absent\n(Use --enable-transmission)", ha="center", va="center", transform=ax_t.transAxes, fontsize=11, color="gray")
        ax_t.set_axis_off()

    fig.canvas.draw()
    buf = fig.canvas.buffer_rgba()
    img = np.asarray(buf)[:, :, :3]
    plt.close(fig)
    return Image.fromarray(img)


def find_snapshot_files(run_dir: Path) -> list[tuple[Path, int]]:
    """Find state_dayNNN.tif / ghana_abm_dayNNN.tif files, sorted by day number."""
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


def find_transmission_json_files(run_dir: Path) -> dict[int, Path]:
    """Find transmission_dayNNN.json sidecars indexed by day number."""
    results = {}
    for p in run_dir.glob("*transmission*.json"):
        m = re.search(r"_day(\d+)\.json$", p.name)
        if m:
            results[int(m.group(1))] = p
    return results


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Animate ABM rollout state and transmission snapshots into an optimized 4-panel GIF."
    )
    parser.add_argument(
        "--run-dir", type=Path, required=True,
        help="Directory containing snapshot GeoTIFFs.",
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
        "--vmax-quantile", type=float, default=99.5,
        help="Percentile for non-zero vmax (default: 99.5).",
    )
    args = parser.parse_args(argv)

    tif_files = find_snapshot_files(args.run_dir)
    if not tif_files:
        print(f"error: no state_dayNNN.tif files found in {args.run_dir}", file=sys.stderr)
        sys.exit(1)

    trans_files = find_transmission_files(args.run_dir)
    trans_jsons = find_transmission_json_files(args.run_dir)

    cohort_path = args.cohort_log
    if cohort_path is None:
        cohort_path = args.run_dir / "cohort.json"
        if not cohort_path.exists():
            matches = sorted(args.run_dir.glob("*_cohort.json"))
            if matches:
                cohort_path = matches[0]
    cohort = load_cohort(cohort_path) if cohort_path and cohort_path.exists() else None

    sampled = tif_files[:: max(args.sample_every, 1)]
    print(f"Found {len(tif_files)} snapshots ({len(trans_files)} transmission rasters), sampling every {args.sample_every} -> {len(sampled)} frames")

    all_density: list[np.ndarray] = []
    all_suit: list[np.ndarray] = []
    all_masks: list[np.ndarray] = []
    all_trans: list[np.ndarray | None] = []
    all_trans_meta: list[dict | None] = []
    all_days: list[int] = []

    for f, day_num in sampled:
        d, s, mask = load_tif(f)
        all_density.append(d)
        all_suit.append(s)
        all_masks.append(mask)
        all_days.append(day_num)

        if day_num in trans_files:
            tbands, _ = load_transmission_tif(trans_files[day_num])
            all_trans.append(tbands.get(args.transmission_band))
        else:
            all_trans.append(None)

        if day_num in trans_jsons:
            with open(trans_jsons[day_num]) as jf:
                all_trans_meta.append(json.load(jf))
        else:
            all_trans_meta.append(None)

    # Compute global normalization limits
    stack_d = np.concatenate([a[np.isfinite(a)].ravel() for a in all_density])
    stack_s = np.concatenate([a[np.isfinite(a)].ravel() for a in all_suit])

    vmax_d = np.percentile(stack_d[stack_d > 0], args.vmax_quantile) if np.any(stack_d > 0) else 1.0
    vmax_s = np.percentile(stack_s[stack_s > 0], args.vmax_quantile) if np.any(stack_s > 0) else 1.0

    density_norm = mcolors.PowerNorm(gamma=0.35, vmin=0.0, vmax=max(0.01, vmax_d))
    suit_norm = mcolors.PowerNorm(gamma=0.35, vmin=0.0, vmax=max(0.01, vmax_s))

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
    for i in range(len(all_density)):
        day_num = all_days[i]
        frame = make_frame(
            all_density[i],
            all_suit[i],
            all_masks[i],
            all_trans[i],
            args.transmission_band,
            cohort,
            all_trans_meta[i],
            day_num,
            density_norm,
            suit_norm,
            trans_norm,
            args.density_cmap,
            args.suit_cmap,
            args.transmission_cmap,
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
    print(f"Saved {len(frames)}-frame optimized 4-panel GIF -> {args.output}")


if __name__ == "__main__":
    main()
