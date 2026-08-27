"""Visualize ABM input data: static host density + animated climate layers.

Produces:
  1. Static PNG: host density panel (human, cattle, goats, sheep, pigs, chickens, wildlife)
  2. Animated GIF: climate layers (rainfall, water_frac, water_temp, ndvi) over time

Usage:
    uv run python mal-core/src/mal_core/abm/scripts/visualize_inputs.py \
        --host-nc data/ghana/ghana_host_static.nc \
        --env-nc data/ghana/ghana_regional_2024_2025_env.nc \
        --output-dir runs/abm_2024_2025/inputs \
        --sample-every 7
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
import xarray as xr
from PIL import Image


HOST_VARS = [
    ("human", "Human density", "YlOrRd"),
    ("cattle", "Cattle density", "YlOrBr"),
    ("goats", "Goats density", "Oranges"),
    ("sheep", "Sheep density", "PuBu"),
    ("pigs", "Pigs density", "RdPu"),
    ("chickens", "Chickens density", "Greens"),
    ("wildlife_host_proxy", "Wildlife proxy", "Purples"),
    ("urban_class", "Urban class", "tab10"),
    ("building_fraction", "Building fraction", "Greys"),
]


def plot_host_panel(ds: xr.Dataset, output: Path) -> None:
    """Static 3x3 panel of host density layers."""
    fig, axes = plt.subplots(3, 3, figsize=(18, 18), dpi=120)
    axes = axes.ravel()

    for i, (var, title, cmap) in enumerate(HOST_VARS):
        ax = axes[i]
        if var not in ds:
            ax.text(0.5, 0.5, f"{var}\nnot found", ha="center", va="center",
                    transform=ax.transAxes, fontsize=14, color="gray")
            ax.set_title(title)
            ax.set_axis_off()
            continue

        arr = ds[var].values.astype(np.float64)
        arr = np.where(arr == -9999, np.nan, arr)

        if var == "urban_class":
            # categorical
            im = ax.imshow(arr, cmap=cmap, origin="upper", interpolation="nearest")
        else:
            # continuous, log scale if range > 1 order of magnitude
            nz = arr[~np.isnan(arr) & (arr > 0)]
            if len(nz) > 0 and np.max(nz) / max(np.min(nz), 1e-10) > 10:
                norm = mcolors.LogNorm(vmin=max(np.percentile(nz, 1), 1e-6),
                                       vmax=np.percentile(nz, 99))
            else:
                norm = mcolors.Normalize(vmin=np.nanpercentile(arr, 1),
                                         vmax=np.nanpercentile(arr, 99))
            im = ax.imshow(arr, cmap=cmap, origin="upper", norm=norm)

        ax.set_title(title, fontsize=13)
        fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        ax.set_axis_off()

    fig.suptitle("ABM Input — Host Density Layers", fontsize=16, y=0.98)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved host panel -> {output}")


def make_climate_frame(
    rainfall: np.ndarray,
    water_frac: np.ndarray,
    water_temp: np.ndarray,
    ndvi: np.ndarray,
    day_label: str,
    rain_norm: mcolors.Normalize,
    wf_norm: mcolors.Normalize,
    wt_norm: mcolors.Normalize,
    ndvi_norm: mcolors.Normalize,
) -> Image.Image:
    """Build a single 2x2 climate frame."""
    fig, axes = plt.subplots(2, 2, figsize=(14, 12), dpi=100)

    panels = [
        (axes[0, 0], rainfall, "Rainfall (mm)", "Blues", rain_norm),
        (axes[0, 1], water_frac, "Water fraction", "YlGnBu", wf_norm),
        (axes[1, 0], water_temp, "Water temp (°C)", "RdYlBu_r", wt_norm),
        (axes[1, 1], ndvi, "NDVI", "RdYlGn", ndvi_norm),
    ]

    for ax, data, title, cmap, norm in panels:
        im = ax.imshow(data, cmap=cmap, origin="upper", norm=norm)
        ax.set_title(title, fontsize=13)
        fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        ax.set_axis_off()

    fig.suptitle(f"Climate — {day_label}", fontsize=15, y=0.98)
    fig.tight_layout(rect=[0, 0, 1, 0.96])

    fig.canvas.draw()
    buf = fig.canvas.buffer_rgba()
    img = np.asarray(buf)[:, :, :3]
    plt.close(fig)
    return Image.fromarray(img)


def animate_climate(env_nc: Path, output: Path, sample_every: int = 1) -> None:
    """Animated GIF of climate layers over time."""
    print(f"Loading {env_nc}...")
    ds = xr.open_dataset(env_nc)
    times = ds.time.values
    n_days = len(times)
    print(f"  {n_days} days loaded")

    # sample
    indices = list(range(0, n_days, max(sample_every, 1)))
    print(f"  Sampling every {sample_every} -> {len(indices)} frames")

    # load all sampled data to compute global ranges
    rain_stack = []
    wf_stack = []
    wt_stack = []
    ndvi_stack = []

    for idx in indices:
        rain_stack.append(ds["rainfall"].isel(time=idx).values)
        wf_stack.append(ds["water_frac"].isel(time=idx).values)
        wt_stack.append(ds["water_temp_c"].isel(time=idx).values)
        ndvi_stack.append(ds["ndvi"].isel(time=idx).values)

    def safe_norm(arrays, pct_lo=2, pct_hi=98):
        all_vals = np.concatenate([a.ravel() for a in arrays])
        all_vals = all_vals[~np.isnan(all_vals)]
        all_vals = all_vals[all_vals > 0] if len(all_vals[all_vals > 0]) > 0 else all_vals
        if len(all_vals) == 0:
            return mcolors.Normalize(vmin=0, vmax=1)
        lo = float(np.percentile(all_vals, pct_lo))
        hi = float(np.percentile(all_vals, pct_hi))
        if hi / max(lo, 1e-10) > 10:
            return mcolors.LogNorm(vmin=max(lo, 1e-6), vmax=hi)
        return mcolors.Normalize(vmin=lo, vmax=hi)

    rain_norm = safe_norm(rain_stack)
    wf_norm = safe_norm(wf_stack)
    wt_norm = safe_norm(wt_stack)
    ndvi_norm = safe_norm(ndvi_stack)

    # generate frames
    frames = []
    for i, idx in enumerate(indices):
        ts = np.datetime_as_string(times[idx], unit="D")
        frame = make_climate_frame(
            rain_stack[i], wf_stack[i], wt_stack[i], ndvi_stack[i],
            ts, rain_norm, wf_norm, wt_norm, ndvi_norm,
        )
        frames.append(frame)
        if (i + 1) % 10 == 0 or i + 1 == len(indices):
            print(f"  rendered {i + 1}/{len(indices)} frames")

    output.parent.mkdir(parents=True, exist_ok=True)
    duration_ms = int(1000 / 4)  # 4 fps
    frames[0].save(
        output,
        save_all=True,
        append_images=frames[1:],
        duration=duration_ms,
        loop=0,
    )
    print(f"Saved {len(frames)}-frame climate GIF -> {output}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Visualize ABM input data.")
    parser.add_argument("--host-nc", type=Path, required=True,
                        help="Host static NetCDF (ghana_host_static.nc)")
    parser.add_argument("--env-nc", type=Path, required=True,
                        help="Climate env NetCDF (ghana_regional_2024_2025_env.nc)")
    parser.add_argument("--output-dir", type=Path, default=Path("runs/abm_inputs"),
                        help="Output directory")
    parser.add_argument("--sample-every", type=int, default=7,
                        help="Sample every N days for climate animation (default: 7)")
    parser.add_argument("--skip-static", action="store_true",
                        help="Skip host density panel")
    parser.add_argument("--skip-climate", action="store_true",
                        help="Skip climate animation")
    args = parser.parse_args(argv)

    if not args.skip_static:
        print("Loading host static data...")
        ds_host = xr.open_dataset(args.host_nc)
        plot_host_panel(ds_host, args.output_dir / "host_density_panel.png")

    if not args.skip_climate:
        animate_climate(args.env_nc, args.output_dir / "climate_animation.gif",
                        args.sample_every)


if __name__ == "__main__":
    main()
