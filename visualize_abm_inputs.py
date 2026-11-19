"""Visualize all ABM inputs for Ghana 2024-2025.

Outputs:
  - abm_inputs/01_host_density.png        (static host grids)
  - abm_inputs/02_env_snapshot_day001.png  (env tensor day 1)
  - abm_inputs/03_rainfall_timeseries.gif  (animated rainfall)
  - abm_inputs/04_water_temp_timeseries.gif (animated water temp)
  - abm_inputs/05_water_frac_timeseries.gif (animated water fraction)
  - abm_inputs/07_habitat_patches.png      (habitat from GPKG)
  - abm_inputs/08_cohort_log.png           (simulation output)
"""
from __future__ import annotations

import json
import struct
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
import xarray as xr
from matplotlib.gridspec import GridSpec
from PIL import Image

from mal_commonlib.model_constants import model_constant

_NODATA = float(model_constant("ingest", "nodata_sentinel"))

OUT = Path("runs/abm/abm_inputs")
OUT.mkdir(parents=True, exist_ok=True)
DATA = Path("data/ghana")

# ── 1. Host density grids ──────────────────────────────────────────
def plot_host_density():
    print("[1/8] Host density grids...")
    ds = xr.open_dataset(DATA / "ghana_host_static.nc")
    y = ds["y"].values
    x = ds["x"].values

    vars_to_plot = [
        ("human", "Human Population", "YlOrRd"),
        ("cattle", "Cattle", "YlGn"),
        ("goats", "Goats", "YlGn"),
        ("sheep", "Sheep", "YlGn"),
        ("pigs", "Pigs", "YlGn"),
        ("chickens", "Chickens", "YlGn"),
        ("wildlife_host_proxy", "Wildlife Host Proxy", "Purples"),
        ("urban_class", "Urban Class", "Greys"),
        ("building_fraction", "Building Fraction", "Blues"),
    ]

    fig, axes = plt.subplots(3, 3, figsize=(20, 22))
    fig.suptitle("ABM Input: Host Density Grids (Ghana)", fontsize=16, fontweight="bold", y=0.98)

    for ax, (var, title, cmap) in zip(axes.flat, vars_to_plot):
        data = ds[var].values
        data = np.where(data == _NODATA, np.nan, data)
        if var == "urban_class":
            im = ax.pcolormesh(x, y, data, cmap=cmap, vmin=0, vmax=1)
        elif var == "building_fraction":
            im = ax.pcolormesh(x, y, data, cmap=cmap, vmin=0, vmax=1)
        else:
            masked = np.ma.masked_invalid(data)
            im = ax.pcolormesh(x, y, masked, cmap=cmap)
        ax.set_title(title, fontsize=11)
        ax.set_xlabel("Lon")
        ax.set_ylabel("Lat")
        plt.colorbar(im, ax=ax, fraction=0.03, pad=0.02)

    plt.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(OUT / "01_host_density.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    ds.close()

# ── 2. Env snapshot (day 1) ────────────────────────────────────────
def plot_env_snapshot():
    print("[2/8] Env tensor snapshot (day 1)...")
    ds = xr.open_dataset(DATA / "ghana_regional_2024_2025_env.nc")
    day0 = ds.isel(time=0)
    y = ds["y"].values
    x = ds["x"].values

    env_vars = [
        ("rainfall", "Rainfall (mm/day)", "Blues"),
        ("water_temp_c", "Water Temperature (°C)", "RdYlBu_r"),
        ("ndvi", "NDVI", "YlGn"),
        ("water_frac", "Water Fraction", "Blues"),
        ("permanent_water_mask", "Permanent Water Mask", "Blues"),
    ]

    fig, axes = plt.subplots(2, 3, figsize=(20, 12))
    fig.suptitle("ABM Input: Environmental Tensor — Day 001 (2024-01-01)", fontsize=14, fontweight="bold")
    axes_flat = axes.flat

    for ax, (var, title, cmap) in zip(axes_flat, env_vars):
        data = day0[var].values
        data = np.where(data == _NODATA, np.nan, data)
        masked = np.ma.masked_invalid(data)
        im = ax.pcolormesh(x, y, masked, cmap=cmap)
        ax.set_title(title, fontsize=11)
        ax.set_xlabel("Lon")
        ax.set_ylabel("Lat")
        plt.colorbar(im, ax=ax, fraction=0.03, pad=0.02)

    axes_flat[-1].axis("off")
    plt.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(OUT / "02_env_snapshot_day001.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    ds.close()

# ── 3-5. Animated time-series GIFs ────────────────────────────────
def make_timeseries_gif(var_name: str, label: str, cmap: str, filename: str, step: int = 7):
    print(f"[gif] {label}...")
    ds = xr.open_dataset(DATA / "ghana_regional_2024_2025_env.nc")
    y = ds["y"].values
    x = ds["x"].values
    times = ds["time"].values
    n_days = len(times)

    frames = []
    for t_idx in range(0, n_days, step):
        data = ds[var_name].isel(time=t_idx).values
        data = np.where(data == _NODATA, np.nan, data)
        masked = np.ma.masked_invalid(data)
        t_str = str(times[t_idx])[:10]

        fig, ax = plt.subplots(figsize=(10, 8))
        im = ax.pcolormesh(x, y, masked, cmap=cmap)
        ax.set_title(f"{label} — {t_str}", fontsize=13)
        ax.set_xlabel("Lon")
        ax.set_ylabel("Lat")
        plt.colorbar(im, ax=ax, fraction=0.03, pad=0.02)

        fig.canvas.draw()
        buf = np.frombuffer(fig.canvas.buffer_rgba(), dtype=np.uint8).reshape(
            fig.canvas.get_width_height()[1], fig.canvas.get_width_height()[0], 4
        )
        img = Image.fromarray(buf[:, :, :3])
        frames.append(img)
        plt.close(fig)

    if frames:
        frames[0].save(
            OUT / filename,
            save_all=True,
            append_images=frames[1:],
            duration=120,
            loop=0,
        )
    ds.close()
    return len(frames)

# ── 7. Habitat patches ────────────────────────────────────────────
def plot_habitat():
    print("[7/8] Habitat patches...")
    import geopandas as gpd

    gdf = gpd.read_file(DATA / "ghana_habitat_patches.gpkg")
    fig, ax = plt.subplots(figsize=(12, 10))
    gdf.plot(ax=ax, column="suitability" if "suitability" in gdf.columns else None,
             legend=True, cmap="YlGn", edgecolor="black", linewidth=0.3)
    ax.set_title("ABM Input: Habitat Patches (Ghana)", fontsize=14, fontweight="bold")
    ax.set_xlabel("Lon")
    ax.set_ylabel("Lat")
    plt.tight_layout()
    fig.savefig(OUT / "07_habitat_patches.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

# ── 8. Cohort log from simulation output ──────────────────────────
def plot_cohort_log():
    print("[8/8] Cohort log...")
    cohort_path = Path("runs/abm/2024-2025-seed0001/ghana_abm_seed0001_cohort.json")
    if not cohort_path.exists():
        print("  cohort.json not found, skipping")
        return
    with open(cohort_path) as f:
        cohort = json.load(f)

    daily = cohort.get("daily", cohort) if isinstance(cohort, dict) else cohort
    days = [c["day"] for c in daily]
    sample = daily[0]
    pop_keys = [k for k in sample.keys() if k not in ("day", "time")]
    if not pop_keys:
        print("  no population keys in cohort, skipping")
        return

    fig, ax = plt.subplots(figsize=(14, 6))
    for k in pop_keys:
        vals = [c.get(k, 0) for c in daily]
        ax.plot(days, vals, label=k, linewidth=1.2)
    ax.set_title("ABM Output: Cohort Population Over Time", fontsize=14, fontweight="bold")
    ax.set_xlabel("Day")
    ax.set_ylabel("Count")
    ax.legend(fontsize=8, ncol=2)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    fig.savefig(OUT / "08_cohort_log.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

# ── Main ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    plot_host_density()
    plot_env_snapshot()
    make_timeseries_gif("rainfall", "Rainfall (mm/day)", "Blues", "03_rainfall_timeseries.gif", step=7)
    make_timeseries_gif("water_temp_c", "Water Temperature (°C)", "RdYlBu_r", "04_water_temp_timeseries.gif", step=7)
    make_timeseries_gif("water_frac", "Water Fraction", "Blues", "05_water_frac_timeseries.gif", step=7)
    plot_habitat()
    plot_cohort_log()
    print(f"\nDone! All outputs in: {OUT}/")
    print("Files:")
    for f in sorted(OUT.iterdir()):
        size_mb = f.stat().st_size / 1e6
        print(f"  {f.name}  ({size_mb:.1f} MB)")
