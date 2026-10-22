"""Visualize ABM input data: static host density + animated climate layers.

Produces:
  1. Static PNG: host density panel (human, cattle, goats, sheep, pigs, chickens, wildlife)
  2. Static PNG: v3.0 habitat statics panel (jrc_persistent, built, wetland, open, crop)
  3. Animated GIF: daily drivers (rainfall, air_temp_c over time)

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

from mal_commonlib.model_constants import model_constant

_NODATA = float(model_constant("ingest", "nodata_sentinel"))


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
        arr = np.where(arr == _NODATA, np.nan, arr)

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
    air_temp: np.ndarray,
    day_label: str,
    rain_norm: mcolors.Normalize,
    temp_norm: mcolors.Normalize,
) -> Image.Image:
    """Build a single 1x2 daily-driver frame (contract v3.0: rainfall +
    air_temp_c are the only daily channels; statics are not animated)."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 8), dpi=100)

    panels = [
        (axes[0], rainfall, "Rainfall (mm)", "Blues", rain_norm),
        (axes[1], air_temp, "Air temperature (°C)", "RdYlBu_r", temp_norm),
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


HABITAT_STATICS = [
    ("jrc_persistent", "JRC persistent water frac", "YlGnBu"),
    ("lc_built", "Built-up frac", "Greys"),
    ("lc_wetland", "Wetland frac", "PuBu"),
    ("lc_open_plus_water", "Open + water frac", "Oranges"),
    ("lc_crop", "Cropland frac", "YlOrBr"),
]


def plot_habitat_statics(env_nc: Path, output: Path) -> None:
    """Static 5-panel of the contract-v3.0 habitat static planes."""
    ds = xr.open_dataset(env_nc)
    fig, axes = plt.subplots(1, len(HABITAT_STATICS), figsize=(5 * len(HABITAT_STATICS), 6),
                             dpi=110)
    for ax, (var, title, cmap) in zip(np.atleast_1d(axes), HABITAT_STATICS):
        if var not in ds:
            ax.text(0.5, 0.5, f"{var}\nnot found",
                    ha="center", va="center", transform=ax.transAxes,
                    fontsize=13, color="gray")
            ax.set_title(title)
            ax.set_axis_off()
            continue
        arr = ds[var].values.astype(np.float64)
        arr = np.where(arr == _NODATA, np.nan, arr)
        im = ax.imshow(arr, cmap=cmap, origin="upper",
                       norm=mcolors.Normalize(vmin=0, vmax=max(1e-6, np.nanmax(arr))))
        ax.set_title(title, fontsize=12)
        fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        ax.set_axis_off()
    fig.suptitle("ABM Static Habitat Potential (contract v3.0)", fontsize=15, y=1.02)
    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, bbox_inches="tight")
    plt.close(fig)
    ds.close()
    print(f"Saved habitat statics panel -> {output}")


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
    temp_stack = []

    for idx in indices:
        rain_stack.append(ds["rainfall"].isel(time=idx).values)
        temp_stack.append(ds["air_temp_c"].isel(time=idx).values)

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
    temp_norm = safe_norm(temp_stack)

    # generate frames
    frames = []
    for i, idx in enumerate(indices):
        ts = np.datetime_as_string(times[idx], unit="D")
        frame = make_climate_frame(
            rain_stack[i], temp_stack[i],
            ts, rain_norm, temp_norm,
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
    parser.add_argument("--skip-statics", action="store_true",
                        help="Skip habitat statics panel")
    args = parser.parse_args(argv)

    if not args.skip_static:
        print("Loading host static data...")
        ds_host = xr.open_dataset(args.host_nc)
        plot_host_panel(ds_host, args.output_dir / "host_density_panel.png")

    if not args.skip_statics:
        plot_habitat_statics(args.env_nc,
                             args.output_dir / "habitat_statics_panel.png")

    if not args.skip_climate:
        animate_climate(args.env_nc, args.output_dir / "climate_animation.gif",
                        args.sample_every)


if __name__ == "__main__":
    main()
