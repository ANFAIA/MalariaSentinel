"""Visualize all ABM inputs for Ghana 2024-2025.

Outputs:
  - abm_inputs/01_host_density.png        (static host grids)
  - abm_inputs/02_env_snapshot_day001.png  (env tensor day 1)
  - abm_inputs/03_rainfall_timeseries.gif  (animated rainfall)
  - abm_inputs/04_water_temp_timeseries.gif (animated water temp)
  - abm_inputs/05_water_frac_timeseries.gif (animated water fraction)
  - abm_inputs/06_mobility_matrices.png    (sparse OD matrices)
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
        data = np.where(data == -9999.0, np.nan, data)
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
        data = np.where(data == -9999.0, np.nan, data)
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
        data = np.where(data == -9999.0, np.nan, data)
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

# ── 6. Mobility matrices (sparse heatmap subsample) ────────────────
def read_csr(path: Path):
    """Read binary CSR: [int32 nrows, int32 ncols, int32 nnz, row_ptr(nrows+1), col_idx(nnz), values(nnz)]."""
    with open(path, "rb") as f:
        nrows = struct.unpack("i", f.read(4))[0]
        ncols = struct.unpack("i", f.read(4))[0]
        nnz = struct.unpack("i", f.read(4))[0]
        row_ptr = np.frombuffer(f.read(4 * (nrows + 1)), dtype=np.int32)
        col_ind = np.frombuffer(f.read(4 * nnz), dtype=np.int32) if nnz > 0 else np.array([], dtype=np.int32)
        values = np.frombuffer(f.read(4 * nnz), dtype=np.float32) if nnz > 0 else np.array([], dtype=np.float32)
    return nrows, ncols, nnz, row_ptr, col_ind, values

def csr_to_dense_sample(path: Path, max_dim: int = 200):
    """Load CSR and subsample to max_dim x max_dim for visualization."""
    nrows, ncols, nnz, row_ptr, col_ind, values = read_csr(path)
    step_r = max(1, nrows // max_dim)
    step_c = max(1, ncols // max_dim)
    small_r = nrows // step_r
    small_c = ncols // step_c
    mat = np.zeros((small_r, small_c), dtype=np.float32)
    for r in range(nrows):
        sr = r // step_r
        if sr >= small_r:
            continue
        start, end = int(row_ptr[r]), int(row_ptr[r + 1])
        for idx in range(start, end):
            c = int(col_ind[idx])
            sc = c // step_c
            if sc < small_c:
                mat[sr, sc] += values[idx]
    return mat

def plot_mobility():
    print("[6/8] Mobility matrices...")
    csr_files = [
        ("ghana_mobility_day.csr", "Human Daytime Mobility"),
        ("ghana_mobility_night.csr", "Human Nighttime Mobility"),
        ("ghana_livestock_mobility.csr", "Livestock Mobility"),
    ]

    fig, axes = plt.subplots(1, 3, figsize=(22, 7))
    fig.suptitle("ABM Input: Mobility OD Matrices (CSR sparse, subsampled)", fontsize=14, fontweight="bold")

    for ax, (fname, title) in zip(axes, csr_files):
        path = DATA / fname
        mat = csr_to_dense_sample(path, max_dim=200)
        mat_log = np.log1p(mat)
        im = ax.imshow(mat_log, cmap="viridis", aspect="auto", origin="lower")
        ax.set_title(f"{title}\n({fname})", fontsize=10)
        ax.set_xlabel("Destination cell")
        ax.set_ylabel("Origin cell")
        plt.colorbar(im, ax=ax, fraction=0.03, pad=0.02)

    plt.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(OUT / "06_mobility_matrices.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

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
    plot_mobility()
    plot_habitat()
    plot_cohort_log()
    print(f"\nDone! All outputs in: {OUT}/")
    print("Files:")
    for f in sorted(OUT.iterdir()):
        size_mb = f.stat().st_size / 1e6
        print(f"  {f.name}  ({size_mb:.1f} MB)")
