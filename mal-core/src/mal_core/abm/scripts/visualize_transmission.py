#!/usr/bin/env python3
"""visualize_transmission.py — Animate SEIR-SEI malaria transmission dynamics into a dedicated GIF.

Produces a high-resolution 3-panel GIF:
  - Left panel:        Spatial Malaria Transmission Spread Map (Prevalence / Incidence / Risk)
  - Top-Right panel:   Human SEIR Compartments Dynamics (S_H, E_H, I_H, R_H counts)
  - Bottom-Right panel: Epidemiological Transmission Metrics (Daily Incidence, I_V Vectors, R_eff)
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


def load_transmission_tif(path: Path) -> tuple[dict[str, np.ndarray], float]:
    """Load transmission snapshot GeoTIFF bands and nodata."""
    band_names = ["prevalence", "incidence", "pressure", "focus"]
    result: dict[str, np.ndarray] = {}
    with rasterio.open(path) as src:
        nodata = src.nodata if src.nodata is not None else -9999.0
        for b_idx, b_name in enumerate(band_names, start=1):
            if b_idx <= src.count:
                arr = np.asarray(src.read(b_idx), dtype=np.float32)
                result[b_name] = arr
    return result, nodata


def find_transmission_files(run_dir: Path) -> list[tuple[Path, int]]:
    """Find transmission snapshot GeoTIFFs sorted by day number."""
    results = []
    for p in run_dir.glob("*transmission*.tif"):
        m = re.search(r"_day(\d+)\.tif$", p.name)
        if m:
            results.append((p, int(m.group(1))))
    results.sort(key=lambda x: x[1])
    return results


def find_transmission_jsons(run_dir: Path) -> dict[int, dict]:
    """Load all transmission sidecar JSONs indexed by day number."""
    results = {}
    for p in run_dir.glob("*transmission*.json"):
        m = re.search(r"_day(\d+)\.json$", p.name)
        if m:
            try:
                with open(p) as f:
                    results[int(m.group(1))] = json.load(f)
            except Exception:
                pass
    return results


def make_transmission_frame(
    map_arr: np.ndarray,
    nodata: float,
    current_day: int,
    all_days: list[int],
    time_series_data: dict[str, list[float]],
    band_name: str,
    map_norm: mcolors.Normalize,
    cmap: str = "YlOrRd",
) -> Image.Image:
    """Build a single high-resolution transmission dynamics frame."""
    fig = plt.figure(figsize=(16, 9), dpi=110)
    gs = fig.add_gridspec(2, 2, width_ratios=[1.0, 1.25], height_ratios=[1.0, 1.0], wspace=0.18, hspace=0.25)

    ax_map = fig.add_subplot(gs[:, 0])
    ax_seir = fig.add_subplot(gs[0, 1])
    ax_metrics = fig.add_subplot(gs[1, 1])

    # 1. Left Map: Spatial Transmission Heatmap
    land_mask = (map_arr != nodata) & np.isfinite(map_arr)
    valid_data = np.where(land_mask, map_arr, 0.0)

    # Convert to % for prevalence
    multiplier = 100.0 if band_name == "prevalence" else 1.0
    valid_data = valid_data * multiplier

    # Enhance visual clarity with slight dilation for isolated settlements
    d_vis = np.maximum(valid_data, maximum_filter(valid_data, size=4) * 0.8)
    d_vis[~land_mask | (d_vis <= 0)] = np.nan

    ax_map.set_facecolor("#0f172a")  # Dark slate background
    im = ax_map.imshow(d_vis, cmap=cmap, norm=map_norm, origin="lower")

    # Current snapshot metadata
    curr_meta_idx = all_days.index(current_day) if current_day in all_days else 0
    curr_prev = time_series_data["prevalence"][curr_meta_idx] * 100.0
    curr_inc = time_series_data["incidence"][curr_meta_idx]
    curr_iv = time_series_data["i_v"][curr_meta_idx]

    unit_lbl = "%" if band_name == "prevalence" else ""
    ax_map.set_title(
        f"Malaria {band_name.capitalize()} Map (Day {current_day})\n"
        f"[Prev: {curr_prev:.2f}% | New Cases: {curr_inc:.0f} | Infectious Vectors: {curr_iv:.0f}]",
        fontsize=12, fontweight="bold", pad=8
    )
    ax_map.set_xticks([])
    ax_map.set_yticks([])
    cbar = fig.colorbar(im, ax=ax_map, fraction=0.046, pad=0.03)
    cbar.set_label(f"{band_name.capitalize()} {unit_lbl}", fontsize=10)

    # 2. Top-Right: Human SEIR Compartments
    days = all_days
    s_h = time_series_data["s_h"]
    e_h = time_series_data["e_h"]
    i_h = time_series_data["i_h"]
    r_h = time_series_data["r_h"]

    ax_seir.plot(days, s_h, label=r"Susceptible ($S_H$)", color="#3b82f6", linewidth=1.8)
    ax_seir.plot(days, r_h, label=r"Recovered/Immune ($R_H$)", color="#10b981", linewidth=1.8)
    ax_seir.plot(days, i_h, label=r"Infectious ($I_H$)", color="#ef4444", linewidth=2.0)
    ax_seir.plot(days, e_h, label=r"Exposed ($E_H$)", color="#f59e0b", linewidth=1.5, linestyle=":")

    ax_seir.axvline(current_day, color="#dc2626", linestyle="--", alpha=0.85, linewidth=1.5)
    ax_seir.set_title("Human SEIR Compartments Trajectory", fontsize=12, fontweight="bold", pad=6)
    ax_seir.set_ylabel("Human Individuals", fontsize=10)
    ax_seir.set_xlim(0, max(days))
    ax_seir.grid(True, which="both", alpha=0.2, linewidth=0.6)
    ax_seir.legend(loc="right", fontsize=9, framealpha=0.9)

    # 3. Bottom-Right: Transmission Metrics & Vectors
    ax_metrics_twin = ax_metrics.twinx()

    p1 = ax_metrics.plot(days, time_series_data["prevalence_pct"], color="#dc2626", linewidth=2.0, label="Prevalence (%)")
    p2 = ax_metrics.plot(days, time_series_data["incidence"], color="#d97706", linewidth=1.4, linestyle="--", label="Daily Incidence")
    p3 = ax_metrics_twin.plot(days, time_series_data["i_v"], color="#8b5cf6", linewidth=1.8, label="Infectious Vectors ($I_V$)")

    ax_metrics.axvline(current_day, color="#dc2626", linestyle="--", alpha=0.85, linewidth=1.5)
    ax_metrics.set_title("Transmission Wave & Inoculation Risk", fontsize=12, fontweight="bold", pad=6)
    ax_metrics.set_xlabel("Simulation Day", fontsize=10)
    ax_metrics.set_ylabel("Prevalence (%) / New Cases", fontsize=10)
    ax_metrics_twin.set_ylabel("Infectious Mosq ($I_V$)", color="#8b5cf6", fontsize=10)
    ax_metrics.set_xlim(0, max(days))
    ax_metrics.grid(True, which="both", alpha=0.2, linewidth=0.6)

    lines = p1 + p2 + p3
    labels = [str(l.get_label()) for l in lines]
    ax_metrics.legend(lines, labels, loc="upper right", fontsize=8.5, framealpha=0.9)

    fig.canvas.draw()
    buf = fig.canvas.buffer_rgba()
    img = np.asarray(buf)[:, :, :3]
    plt.close(fig)
    return Image.fromarray(img)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Animate SEIR-SEI malaria transmission dynamics into a dedicated high-resolution GIF."
    )
    parser.add_argument(
        "--run-dir", type=Path, required=True,
        help="Directory containing transmission GeoTIFFs and sidecar JSONs.",
    )
    parser.add_argument(
        "--output", type=Path, required=True,
        help="Output GIF path.",
    )
    parser.add_argument(
        "--band", default="prevalence",
        choices=["prevalence", "incidence", "pressure", "focus"],
        help="Transmission band to display (default: prevalence).",
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
        help="Colormap for spatial transmission map (default: YlOrRd).",
    )
    args = parser.parse_args(argv)

    trans_files = find_transmission_files(args.run_dir)
    if not trans_files:
        print(f"error: no transmission_dayNNN.tif files found in {args.run_dir}", file=sys.stderr)
        sys.exit(1)

    trans_jsons = find_transmission_jsons(args.run_dir)
    sampled = trans_files[:: max(args.sample_every, 1)]
    print(f"Found {len(trans_files)} transmission snapshots, sampling every {args.sample_every} -> {len(sampled)} frames")

    # Build full time series from all available snapshots/sidecars
    all_days = [day_num for _, day_num in trans_files]
    ts_s_h: list[float] = []
    ts_e_h: list[float] = []
    ts_i_h: list[float] = []
    ts_r_h: list[float] = []
    ts_prev: list[float] = []
    ts_prev_pct: list[float] = []
    ts_inc: list[float] = []
    ts_iv: list[float] = []
    ts_reff: list[float] = []

    for d in all_days:
        meta = trans_jsons.get(d, {})
        ts_s_h.append(float(meta.get("total_susceptible", 0.0)))
        ts_e_h.append(float(meta.get("total_exposed", 0.0)))
        ts_i_h.append(float(meta.get("total_infectious", 0.0)))
        ts_r_h.append(float(meta.get("total_recovered", 0.0)))
        prev = float(meta.get("mean_prevalence", 0.0))
        ts_prev.append(prev)
        ts_prev_pct.append(prev * 100.0)
        ts_inc.append(float(meta.get("total_incidence", 0.0)))
        ts_iv.append(float(meta.get("vector_infectious", 0.0)))
        ts_reff.append(float(meta.get("r_eff_approx", 0.0)))

    time_series_data = {
        "s_h": ts_s_h,
        "e_h": ts_e_h,
        "i_h": ts_i_h,
        "r_h": ts_r_h,
        "prevalence": ts_prev,
        "prevalence_pct": ts_prev_pct,
        "incidence": ts_inc,
        "i_v": ts_iv,
        "r_eff": ts_reff,
    }

    # Load sampled rasters
    sampled_rasters: list[tuple[np.ndarray, float, int]] = []
    all_vals: list[float] = []

    for f, day_num in sampled:
        tbands, nodata = load_transmission_tif(f)
        arr = tbands.get(args.band, np.zeros((10, 10), dtype=np.float32))
        sampled_rasters.append((arr, nodata, day_num))

        valid = arr[(arr != nodata) & np.isfinite(arr) & (arr > 0)]
        if len(valid) > 0:
            multiplier = 100.0 if args.band == "prevalence" else 1.0
            all_vals.extend((valid * multiplier).tolist())

    if len(all_vals) > 0:
        vmax = max(0.01, float(np.percentile(all_vals, 99.5)))
    else:
        vmax = 10.0 if args.band == "prevalence" else 1.0

    map_norm = mcolors.PowerNorm(gamma=0.35, vmin=0.001, vmax=vmax)

    # Render frames
    frames: list[Image.Image] = []
    for i, (arr, nodata, day_num) in enumerate(sampled_rasters):
        frame = make_transmission_frame(
            map_arr=arr,
            nodata=nodata,
            current_day=day_num,
            all_days=all_days,
            time_series_data=time_series_data,
            band_name=args.band,
            map_norm=map_norm,
            cmap=args.cmap,
        )
        frames.append(frame)
        if (i + 1) % 10 == 0 or i + 1 == len(sampled_rasters):
            print(f"  rendered {i + 1}/{len(sampled_rasters)} frames")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    duration_ms = int(1000 / args.fps)
    frames[0].save(
        args.output,
        save_all=True,
        append_images=frames[1:],
        duration=duration_ms,
        loop=0,
    )
    print(f"Saved {len(frames)}-frame SEIR-SEI Transmission GIF -> {args.output}")


if __name__ == "__main__":
    main()
