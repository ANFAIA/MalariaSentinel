"""Visualisation of M12-fix water pipeline for Ghana.

Three figures:
  1. ``m12_water_pipeline.png`` — 3-panel:
        a) JRC GSW water occurrence raw (before filter)
        b) GSHHG coastline land mask (5 km buffer)
        c) Final water_frac after saltwater filter + permanent_water_mask
  2. ``m12_habitat_patches.png`` — habitat patches coloured by hab_type
  3. ``m12_water_frac_histogram.png`` — distribution of water_frac over cells
"""
from __future__ import annotations

import pathlib

import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import rasterio
import xarray as xr
import geopandas as gpd

DATA = pathlib.Path("../data/ghana")
OUT = pathlib.Path("../runs/visualisations/m12_water")
OUT.mkdir(parents=True, exist_ok=True)

GHANA_EXTENT = (-3.5, 1.0, 4.5, 11.5)


def _read_tif(path: pathlib.Path) -> tuple[np.ndarray, dict]:
    with rasterio.open(path) as src:
        arr = src.read(1).astype(np.float32)
        transform = src.transform
        nodata = src.nodata
    if nodata is not None:
        arr = np.where(arr == nodata, np.nan, arr)
    return arr, {
        "transform": transform,
        "width": arr.shape[1],
        "height": arr.shape[0],
    }


def _extent_from_transform(t, w, h) -> tuple[float, float, float, float]:
    """Convert rasterio Affine + shape to matplotlib extent (lon/lat)."""
    return rasterio.transform.array_bounds(h, w, t)


def _overlay_cartopy(ax, extent):
    """Minimal Ghana basemap. No gridlines, no NaturalEarth features.
    Some cartopy installations crash on both (self-intersecting polygons +
    broken gridliner). Just draw a frame.
    """
    pass


# ---------------------------------------------------------------------------
# 1. Three-panel pipeline
# ---------------------------------------------------------------------------

def plot_pipeline():
    jrc, jrc_meta = _read_tif(DATA / "ghana_water_occurrence.tif")
    land, land_meta = _read_tif(DATA / "ghana_land_mask.tif")

    ds = xr.open_dataset(DATA / "ghana_regional_2024_2025_env.nc")
    wf = ds["water_frac"].isel(time=0).values
    pwm = ds["permanent_water_mask"].isel(time=0).values
    ds.close()

    fig, axes = plt.subplots(
        1, 3, figsize=(20, 7),
        subplot_kw={"projection": ccrs.PlateCarree()},
    )

    # Panel A: raw JRC
    extent_a = _extent_from_transform(
        jrc_meta["transform"], jrc_meta["width"], jrc_meta["height"]
    )
    im_a = axes[0].imshow(
        jrc, cmap="Blues", vmin=0, vmax=100, origin="upper",
        extent=extent_a, transform=ccrs.PlateCarree(),
    )
    _overlay_cartopy(axes[0], extent_a)
    axes[0].set_title(
        f"(a) JRC GSW water occurrence (raw)\n"
        f"{int(np.nansum(jrc > 0)):,} cells with water, "
        f"{int(np.nansum(jrc >= 80)):,} permanent (>=80%)",
        fontsize=10, loc="left",
    )
    cb_a = plt.colorbar(im_a, ax=axes[0], fraction=0.046, pad=0.04)
    cb_a.set_label("Occurrence [%]", fontsize=9)

    # Panel B: coastline land mask
    extent_b = _extent_from_transform(
        land_meta["transform"], land_meta["width"], land_meta["height"]
    )
    im_b = axes[1].imshow(
        land, cmap="RdYlGn", vmin=0, vmax=1, origin="upper",
        extent=extent_b, transform=ccrs.PlateCarree(),
    )
    _overlay_cartopy(axes[1], extent_b)
    axes[1].set_title(
        "(b) GSHHG coastline land mask\n"
        "1 = land (kept) / 0 = open ocean (dropped)",
        fontsize=10, loc="left",
    )
    cb_b = plt.colorbar(im_b, ax=axes[1], fraction=0.046, pad=0.04)
    cb_b.set_label("Land mask", fontsize=9)
    cb_b.set_ticks([0, 1])

    # Panel C: final water_frac + permanent_water_mask overlay
    extent_c = _extent_from_transform(
        jrc_meta["transform"], jrc_meta["width"], jrc_meta["height"]
    )
    im_c = axes[2].imshow(
        np.where(wf > 0.05, 1.0, 0.0), cmap="Blues", vmin=0, vmax=1,
        origin="upper",
        extent=extent_c, transform=ccrs.PlateCarree(),
    )
    # Permanent cells in red on top of the viable mask.
    pwm_bin = np.where(pwm == 1, 1, np.nan)
    axes[2].imshow(
        pwm_bin, cmap="Reds_r", vmin=0, vmax=1, origin="upper",
        extent=extent_c, transform=ccrs.PlateCarree(), alpha=0.85,
    )
    _overlay_cartopy(axes[2], extent_c)
    n_perm = int((pwm == 1).sum())
    n_pluvial = int(((wf > 0.05) & (pwm == 0)).sum())
    axes[2].set_title(
        f"(c) water_frac after saltwater filter\n"
        f"{n_perm:,} permanent (red contour) + {n_pluvial:,} pluvial > 0.05",
        fontsize=10, loc="left",
    )
    cb_c = plt.colorbar(im_c, ax=axes[2], fraction=0.046, pad=0.04)
    cb_c.set_label("water_frac", fontsize=9)

    plt.suptitle(
        "MalariaSentinel — Ghana water pipeline (M12-fix, 2026-08-26)",
        fontsize=13, y=1.0,
    )
    plt.tight_layout()
    out = OUT / "m12_water_pipeline.png"
    plt.savefig(out, dpi=120, bbox_inches="tight")
    plt.close()
    print(f"  -> {out}")


# ---------------------------------------------------------------------------
# 2. Habitat patches by hab_type
# ---------------------------------------------------------------------------

def plot_habitat_patches():
    gdf = gpd.read_file(DATA / "ghana_habitat_patches.gpkg")
    gdf_web = gdf.to_crs("EPSG:4326")
    counts = gdf_web["hab_type"].value_counts().to_dict()

    fig, ax = plt.subplots(
        1, 1, figsize=(11, 9),
        subplot_kw={"projection": ccrs.PlateCarree()},
    )
    _overlay_cartopy(ax, GHANA_EXTENT)

    colors = {"permanent_water": "#1f6f9c", "pluvial_pool": "#a8324a"}
    sizes = {"permanent_water": 18, "pluvial_pool": 10}
    for ht in ["permanent_water", "pluvial_pool"]:
        sub = gdf_web[gdf_web["hab_type"] == ht]
        if sub.empty:
            continue
        ax.scatter(
            sub.geometry.x, sub.geometry.y,
            c=colors.get(ht, "#888"), s=sizes.get(ht, 8),
            alpha=0.7, edgecolor="white", linewidth=0.2,
            label=f"{ht} (n={len(sub):,})",
            transform=ccrs.PlateCarree(),
        )

    ax.legend(loc="lower left", fontsize=10, framealpha=0.9)
    ax.set_title(
        "Ghana habitat patches (TWI>8 AND water_frac>0.05)\n"
        f"total = {len(gdf_web):,} patches "
        f"({counts.get('permanent_water', 0):,} permanent, "
        f"{counts.get('pluvial_pool', 0):,} pluvial)",
        fontsize=11, loc="left",
    )

    out = OUT / "m12_habitat_patches.png"
    plt.savefig(out, dpi=120, bbox_inches="tight")
    plt.close()
    print(f"  -> {out}")


# ---------------------------------------------------------------------------
# 3. water_frac distribution histogram
# ---------------------------------------------------------------------------

def plot_water_frac_histogram():
    ds = xr.open_dataset(DATA / "ghana_regional_2024_2025_env.nc")
    wf = ds["water_frac"].isel(time=0).values.flatten()
    ds.close()
    wf = wf[~np.isnan(wf)]
    bins = [0.0, 0.001, 0.05, 0.5, 0.95, 0.999, 1.001]
    labels = ["dry (==0)", "trace (<0.05)", "low JRC (0.05-0.5)",
              "high JRC (0.5-0.95)", "near-permanent (0.95-1.0)",
              "permanent (==1.0)"]
    counts, _ = np.histogram(wf, bins=bins)
    pct = counts / counts.sum() * 100

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    # Linear histogram
    ax1.bar(range(len(labels)), counts,
            color=["#cccccc", "#fee5a0", "#fdc066", "#f88a3a", "#d04a2c", "#1f6f9c"])
    ax1.set_xticks(range(len(labels)))
    ax1.set_xticklabels(labels, rotation=30, ha="right", fontsize=9)
    ax1.set_ylabel("N cells")
    ax1.set_title("water_frac distribution (linear)", fontsize=11)
    for i, (c, p) in enumerate(zip(counts, pct)):
        if c > 0:
            ax1.text(i, c, f"{c:,}\n({p:.2f}%)", ha="center", va="bottom", fontsize=8)
    ax1.set_ylim(0, max(counts) * 1.18)

    # Log histogram
    ax2.bar(range(len(labels)), np.maximum(counts, 1),
            color=["#cccccc", "#fee5a0", "#fdc066", "#f88a3a", "#d04a2c", "#1f6f9c"])
    ax2.set_xticks(range(len(labels)))
    ax2.set_xticklabels(labels, rotation=30, ha="right", fontsize=9)
    ax2.set_yscale("log")
    ax2.set_ylabel("N cells (log)")
    ax2.set_title("water_frac distribution (log scale)", fontsize=11)

    plt.suptitle(
        f"Ghana water_frac histogram — {wf.size:,} cells total",
        fontsize=12,
    )
    plt.tight_layout()
    out = OUT / "m12_water_frac_histogram.png"
    plt.savefig(out, dpi=120, bbox_inches="tight")
    plt.close()
    print(f"  -> {out}")


if __name__ == "__main__":
    print("Generating M12-fix water visualisations...")
    plot_pipeline()
    plot_habitat_patches()
    plot_water_frac_histogram()
    print("done.")
