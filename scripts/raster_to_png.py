"""Render ABM simulation rasters to PNG + animated GIF.

Usage:
    uv run python scripts/raster_to_png.py runs/fast-2year
    uv run python scripts/raster_to_png.py runs/fast-2year --fps 2 --out runs/fast-2year/images

Reads only from the run directory.  Writes only to --out (default: <run_dir>/images/).

Per-band PNGs (aspect-corrected) + animated GIF per band (configurable fps).
"""
from __future__ import annotations

import io
import json
import re
import sys
from argparse import ArgumentParser
from pathlib import Path

import numpy as np
import rasterio
from matplotlib import colormaps
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.colors import LogNorm, Normalize
from matplotlib.figure import Figure
from PIL import Image

# ── band colormaps / stretch ─────────────────────────────────────────────────
RECIPES: dict[str, dict] = {
    "density":     dict(cmap="magma",   stretch="auto",  vmin=None, vmax=None),
    "suitability": dict(cmap="viridis", stretch="linear", vmin=0.0, vmax=1.0),
}

NODATA_COLOR = (0.88, 0.88, 0.88)

# inches per 100 pixels at a reference DPI — used to compute figure sizes
IMG_TARGET_H_INCHES = 7.0   # aim for ~7 inches tall for a 779-row raster
CBAR_W_INCHES = 0.45
PAD_INCHES = 0.08


# ── helpers ──────────────────────────────────────────────────────────────────

def _cmap(name: str):
    return colormaps[name]


def _parse_filename(name: str):
    """Return (year, month, seed) or (day, 0, 0) from various filename formats.
    
    Supported formats:
    - 'abm_YYYY_MM_seedSSSS' → (year, month, seed) for monthly snapshots
    - 'abm_YYYY_MM_seedSSSS_dayNNN' → (year, month, seed, day) for daily snapshots
    - 'state_dayNNN' → (day, 0, 0) for daily snapshots
    - 'state' → (0, 0, 0) for final snapshot
    """
    # Format: abm_YYYY_MM_seedSSSS_dayNNN (daily snapshot within monthly run)
    m = re.match(r"abm_(\d{4})_(\d{2})_seed(\d+)_day(\d+)", name)
    if m:
        return int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))
    
    # Format: abm_YYYY_MM_seedSSSS (monthly snapshot)
    m = re.match(r"abm_(\d{4})_(\d{2})_seed(\d+)", name)
    if m:
        return int(m.group(1)), int(m.group(2)), int(m.group(3)), 0
    
    # Format: state_dayNNN
    m = re.match(r"state_day(\d+)", name)
    if m:
        return int(m.group(1)), 0, 0, 0
    
    # Format: state (final snapshot)
    if name == "state":
        return 0, 0, 0, 0
    
    return None


def _masked(arr: np.ndarray, nodata) -> np.ma.MaskedArray:
    a = arr.astype("float64")
    if nodata is not None:
        return np.ma.masked_where(a == nodata, a)
    return np.ma.masked_invalid(a)


def _stretch(valid: np.ndarray, vmin, vmax, mode: str):
    if mode == "log":
        pos = valid[valid > 0]
        if pos.size == 0:
            return 1.0, 10.0
        lo = max(1.0, float(np.percentile(pos, 1)))
        hi = float(np.percentile(pos, 99.5))
        if hi <= lo:
            hi = lo * 10
        return lo, hi
    if vmin is None:
        vmin = float(np.percentile(valid, 1))
    if vmax is None:
        vmax = float(np.percentile(valid, 99))
    if vmax <= vmin:
        vmax = vmin + 1e-9
    return float(vmin), float(vmax)


def _compute_norm(valid, recipe):
    """Build a matplotlib Normalize for the given data + recipe."""
    all_zero = (valid.size > 0) and np.all(valid == 0)
    all_nodata = valid.size == 0
    if all_nodata:
        return Normalize(0, 1), True, False
    if all_zero:
        return Normalize(0, recipe.get("vmax") or 1.0), False, True

    stretch = recipe["stretch"]
    if stretch == "auto":
        vmax_data = float(valid.max())
        p1 = float(np.percentile(valid, 1))
        p99 = float(np.percentile(valid, 99))
        use_log = (vmax_data > 10) and (p99 / max(p1, 1e-10) > 10)
        stretch = "log" if use_log else "linear"

    if stretch == "log":
        lo, hi = _stretch(valid, recipe["vmin"], recipe["vmax"], "log")
        return LogNorm(vmin=lo, vmax=hi), False, False
    lo, hi = _stretch(valid, recipe["vmin"], recipe["vmax"], "linear")
    return Normalize(lo, hi), False, False


def _figsize_for(data_h: int, data_w: int, dpi: int) -> tuple[float, float]:
    """Return (fig_width, fig_height) inches so the image is aspect-correct."""
    scale = IMG_TARGET_H_INCHES / data_h
    img_w = data_w * scale
    img_h = IMG_TARGET_H_INCHES
    return img_w + CBAR_W_INCHES + PAD_INCHES, img_h


# ── single-panel renderer ────────────────────────────────────────────────────

def _render_band(band: np.ndarray, recipe: dict, nodata,
                  title: str, out_path: Path, dpi: int = 130) -> Image.Image:
    """Render one band to a PNG.  Returns the PIL Image (for reuse in animations)."""
    a = _masked(band, nodata)
    valid = a.compressed()
    norm, all_nodata, all_zero = _compute_norm(valid, recipe)
    cmap_obj = _cmap(recipe["cmap"]).with_extremes(bad=NODATA_COLOR)

    rows, cols = a.shape
    fig_w, fig_h = _figsize_for(rows, cols, dpi)
    fig = Figure(figsize=(fig_w, fig_h), dpi=dpi)
    FigureCanvasAgg(fig)

    # image axes: fill everything except the rightmost strip for the colorbar
    img_frac = fig_w / (fig_w - CBAR_W_INCHES - PAD_INCHES) if False else \
               (fig_w - CBAR_W_INCHES - PAD_INCHES) / fig_w
    ax_img = fig.add_axes([0, 0, img_frac, 0.95])  # leave room for title + stats
    ax_cb  = fig.add_axes([img_frac + PAD_INCHES / fig_w, 0.05,
                           CBAR_W_INCHES / fig_w, 0.88])

    im = ax_img.imshow(a, cmap=cmap_obj, norm=norm, origin="upper",
                       interpolation="nearest", aspect="equal")
    ax_img.set_title(title, fontsize=10, pad=4)
    ax_img.set_xlabel("col", fontsize=8)
    ax_img.set_ylabel("row", fontsize=8)
    ax_img.tick_params(labelsize=7)
    fig.colorbar(im, cax=ax_cb)

    # stats banner
    if all_nodata:
        banner = f"ALL NODATA  (sentinel={nodata})"
        col = "#a00000"
    elif all_zero:
        banner = f"ALL ZERO  ({valid.size:,} valid cells)"
        col = "#a06500"
    else:
        pcts = np.percentile(valid, [1, 50, 99])
        banner = (f"n={valid.size:,}  min={valid.min():.3g}  "
                  f"p1={pcts[0]:.3g}  med={pcts[1]:.3g}  "
                  f"p99={pcts[2]:.3g}  max={valid.max():.3g}")
        col = "#333"
    fig.text(0.5, 0.01, banner, ha="center", fontsize=7.5, color=col,
             family="monospace",
             bbox=dict(facecolor="#ffe" if col != "#a00000" else "#fdd",
                       edgecolor=col, boxstyle="round,pad=0.2", alpha=0.9))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=dpi)

    # also return as PIL Image for animation reuse
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi)
    buf.seek(0)
    pil_img = Image.open(buf).copy()
    buf.close()
    return pil_img


# ── animated GIF ─────────────────────────────────────────────────────────────

def _render_animation(frames: list[Image.Image], out_path: Path, fps: float):
    """Save a list of PIL Images as an animated GIF."""
    if len(frames) < 2:
        return
    duration_ms = int(1000 / fps)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        out_path,
        save_all=True,
        append_images=frames[1:],
        duration=duration_ms,
        loop=0,
        optimize=True,
    )


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    ap = ArgumentParser(description="Render ABM rasters to PNG + animated GIF.")
    ap.add_argument("run_dir", type=Path,
                    help="Path to run directory (contains .tif + .json)")
    ap.add_argument("--out", type=Path, default=None,
                    help="Output directory (default: <run_dir>/images/)")
    ap.add_argument("--fps", type=float, default=1.0,
                    help="Frames per second for animated GIFs (default: 1.0)")
    args = ap.parse_args()

    run_dir = args.run_dir.resolve()
    out_dir = (args.out or run_dir / "images").resolve()

    if not run_dir.is_dir():
        print(f"not a directory: {run_dir}", file=sys.stderr)
        return 1

    tifs = sorted(run_dir.glob("*.tif"))
    if not tifs:
        print(f"no .tif files in {run_dir}", file=sys.stderr)
        return 1

    # parse filenames
    parsed = []
    for tif in tifs:
        info = _parse_filename(tif.stem)
        if info is None:
            print(f"skipping (can't parse): {tif.name}")
            continue
        year, month, seed, day = info
        parsed.append((tif, year, month, seed, day))
    
    # Detect if this is a daily snapshot run (has day numbers > 0)
    has_daily = any(p[4] > 0 for p in parsed)
    
    # Sort: daily snapshots by year/month/seed/day, monthly by year/month/seed
    if has_daily:
        parsed.sort(key=lambda x: (x[1], x[2], x[3], x[4]))
    else:
        parsed.sort(key=lambda x: (x[1], x[2], x[3]))

    # band names from first file
    first_meta = json.loads(parsed[0][0].with_suffix(".json").read_text())
    band_names: list[str] = first_meta["band_names"]
    nodata = first_meta.get("nodata")

    # collect frames per band for animation
    band_anim: dict[str, list[Image.Image]] = {b: [] for b in band_names}
    n_frames = len(parsed)
    n_bands = len(band_names)

    for idx, (tif, year, month, seed, day) in enumerate(parsed):
        meta = json.loads(tif.with_suffix(".json").read_text())
        with rasterio.open(tif) as src:
            arr = src.read()
        for i, bname in enumerate(band_names):
            recipe = RECIPES.get(bname, dict(cmap="viridis", stretch="linear",
                                              vmin=None, vmax=None))
            # Generate title based on filename format
            if day > 0:
                tag = f"{year}-{month:02d} Day {day}"
            else:
                tag = f"{year}-{month:02d}"
            out = out_dir / bname / f"{tif.stem}_{bname}.png"
            pil_img = _render_band(arr[i], recipe, nodata,
                                    title=f"{tag}  ·  {bname}", out_path=out)
            band_anim[bname].append(pil_img)
            print(f"  [{idx+1}/{n_frames}] {out.name}")

    # animated GIFs
    for bname in band_names:
        gif_path = out_dir / f"anim_{bname}.gif"
        _render_animation(band_anim[bname], gif_path, fps=args.fps)
        print(f"  GIF: {gif_path.name}  ({len(band_anim[bname])} frames, {args.fps} fps)")

    # README
    readme = out_dir / "README.txt"
    readme.write_text(
        "MalariaSentinel ABM raster previews\n"
        f"Run:  {run_dir.name}\n"
        f"Months: {parsed[0][1]}-{parsed[0][2]:02d} → {parsed[-1][1]}-{parsed[-1][2]:02d}  "
        f"({n_frames} frames, {len(set(p[3] for p in parsed))} seed(s))\n"
        f"FPS: {args.fps}\n\n"
        "Layout:\n"
        "  <band>/abm_YYYY_MM_seedSSSS_<band>.png   per-frame PNG (aspect-corrected)\n"
        "  anim_<band>.gif                           animated time-series (configurable fps)\n\n"
        "Stretch:\n"
        "  density     : log (magma), clipped at p99.5\n"
        "  suitability : linear 0..1 (viridis)\n\n"
        "Re-run:\n"
        f"  uv run python scripts/raster_to_png.py {run_dir.relative_to(Path.cwd())}\n"
        f"  uv run python scripts/raster_to_png.py {run_dir.relative_to(Path.cwd())} --fps 0.5\n"
    )
    print(f"\nDone: {n_frames * n_bands} PNGs + {n_bands} GIFs → {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
