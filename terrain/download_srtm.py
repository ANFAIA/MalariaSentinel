"""Genera mapas SRTM (DEM + hillshade + contornos + puntos de presencia)
para cada uno de los datasets de malaria en data/.

Excluye Guyane Francesa (data/occurrence.txt) que ya fue procesada.

Fuente DEM: OpenTopography (OT.042013.4326.1) — API globaldem.
"""

from __future__ import annotations

import csv
import os
import pathlib
import sys

import matplotlib.pyplot as plt
import numpy as np
import rasterio
import requests
from matplotlib.colors import LightSource

API_KEY = os.environ.get("OPENTOPO_API_KEY")
if not API_KEY:
    sys.exit("ERROR: export OPENTOPO_API_KEY=<tu_key>")

DATA = pathlib.Path("/Users/davidflorezmazuera/Downloads/MalariaSentinel/data")
OUT_ROOT = pathlib.Path("/Users/davidflorezmazuera/Downloads/MalariaSentinel/terrain/srtm_maps")
OUT_ROOT.mkdir(exist_ok=True)

DEM_TYPE = "SRTMGL1"
PAD_DEG = 0.20

DATASETS = [
    ("ghana_idit",  DATA / "ghana_idit"  / "occurrence.txt",
     "Northern Ghana",          "SRTMGL1", None),
    ("colombia_vl", DATA / "colombia_vl" / "occurrence.txt",
     "Guapi, Cauca — Colombia", "SRTMGL1", None),
    ("react",       DATA / "react"       / "occurrence.txt",
     "Burkina Faso + Côte d'Ivoire (REACT)", "SRTMGL1", None),
    ("nigeria",     None,
     "Nigeria",                 "SRTMGL3", (4.27, 13.89, 2.68, 14.68)),
]


def read_occurrences(path: pathlib.Path):
    lats, lons = [], []
    with open(path, encoding="utf-8") as f:
        r = csv.DictReader(f, delimiter="\t")
        for row in r:
            try:
                la = float(row["decimalLatitude"]); lo = float(row["decimalLongitude"])
                if -90 <= la <= 90 and -180 <= lo <= 180:
                    lats.append(la); lons.append(lo)
            except (KeyError, ValueError, TypeError):
                continue
    return np.array(lats), np.array(lons)


def bbox_from_occurrences(lats, lons, pad=PAD_DEG):
    return (
        float(lats.min() - pad), float(lats.max() + pad),
        float(lons.min() - pad), float(lons.max() + pad),
    )


def download_dem(south, north, west, east, out_path: pathlib.Path, dem_type: str):
    if out_path.exists() and out_path.stat().st_size > 1024:
        return out_path
    url = "https://portal.opentopography.org/API/globaldem"
    params = dict(
        demtype=dem_type,
        south=south, north=north, west=west, east=east,
        outputFormat="GTiff", API_Key=API_KEY,
    )
    print(f"  Descargando {dem_type} {south:.2f},{north:.2f},{west:.2f},{east:.2f} ...")
    r = requests.get(url, params=params, timeout=600)
    r.raise_for_status()
    out_path.write_bytes(r.content)
    return out_path


def read_raster(path: pathlib.Path):
    with rasterio.open(path) as src:
        dem = np.asarray(src.read(1), dtype="float32")
        nodata = src.nodata
        bounds = src.bounds
        transform = src.transform
    if nodata is not None:
        dem = np.where(dem == nodata, np.nan, dem)
    return dem, bounds, transform


def plot_dem(dem, bounds, lats, lons, name: str, region_label: str,
             n_occ: int, dem_type: str):
    max_dim = 6000
    h, w = dem.shape
    if max(h, w) > max_dim:
        step = int(np.ceil(max(h, w) / max_dim))
        dem = dem[::step, ::step]
        shaded = LightSource(azdeg=315, altdeg=45).hillshade(dem, vert_exag=2)
    else:
        ls = LightSource(azdeg=315, altdeg=45)
        shaded = ls.hillshade(dem, vert_exag=2)
    extent = (bounds.left, bounds.right, bounds.bottom, bounds.top)

    fig, axes = plt.subplots(1, 2, figsize=(15, 7))

    im0 = axes[0].imshow(dem, cmap="terrain", extent=extent)
    if len(lats) > 0:
        axes[0].scatter(lons, lats, s=6, c="red", edgecolor="black",
                        linewidth=0.3, alpha=0.7)
    axes[0].set_title(f"DEM {dem_type} — {region_label}\n{n_occ} ocurrencias")
    axes[0].set_xlabel("Longitud"); axes[0].set_ylabel("Latitud")
    plt.colorbar(im0, ax=axes[0], shrink=0.8, label="Elevación (m)")

    axes[1].imshow(shaded, cmap="gray", extent=extent)
    n_levels = 12 if dem.shape[0] < 4000 else 8
    cs = axes[1].contour(dem, levels=n_levels, colors="brown",
                         linewidths=0.4, extent=extent)
    axes[1].clabel(cs, inline=True, fontsize=7, fmt="%d m")
    im1 = axes[1].imshow(dem, cmap="terrain", alpha=0.45, extent=extent)
    if len(lats) > 0:
        axes[1].scatter(lons, lats, s=6, c="red", edgecolor="black",
                        linewidth=0.3, alpha=0.85)
    axes[1].set_title("Relieve sombreado + contornos + ocurrencias")
    axes[1].set_xlabel("Longitud"); axes[1].set_ylabel("Latitud")
    plt.colorbar(im1, ax=axes[1], shrink=0.8, label="m s.n.m.")

    fig.suptitle(f"{name} · {dem_type} · BBOX {bounds.left:.2f},{bounds.right:.2f},{bounds.bottom:.2f},{bounds.top:.2f}")
    fig.tight_layout()
    out = OUT_ROOT / f"{name}_srtm.png"
    fig.savefig(out, dpi=180)
    plt.close(fig)
    return out


def main():
    for name, occ_path, label, dem_type, fixed_bbox in DATASETS:
        print(f"\n=== {name} ===")
        lats = np.array([]); lons = np.array([])

        if occ_path is not None:
            if not occ_path.exists():
                print(f"  No existe {occ_path}, salto.")
                continue
            lats, lons = read_occurrences(occ_path)
            if len(lats) == 0:
                print("  Sin coordenadas válidas, salto.")
                continue
            s, n, w, e = bbox_from_occurrences(lats, lons)
        else:
            s, n, w, e = fixed_bbox
            print(f"  Sin occurrence.txt, usando BBOX fijo: "
                  f"S{s:.3f} N{n:.3f} W{w:.3f} E{e:.3f}")

        print(f"  n={len(lats)}  BBOX=S{s:.3f} N{n:.3f} W{w:.3f} E{e:.3f}  "
              f"Δlat={n-s:.2f} Δlon={e-w:.2f}")

        dem_dir = OUT_ROOT / name
        dem_dir.mkdir(exist_ok=True)
        tif = dem_dir / f"{dem_type}_{w:.2f}_{e:.2f}_{s:.2f}_{n:.2f}.tif"
        try:
            download_dem(s, n, w, e, tif, dem_type)
        except requests.HTTPError as ex:
            print(f"  Falló descarga: {ex}")
            continue

        dem, bounds, _ = read_raster(tif)
        out = plot_dem(dem, bounds, lats, lons, name, label,
                       n_occ=len(lats), dem_type=dem_type)
        size_mb = tif.stat().st_size / 1e6
        print(f"  DEM: {tif} ({size_mb:.1f} MB)")
        print(f"  Mapa: {out}")


if __name__ == "__main__":
    main()