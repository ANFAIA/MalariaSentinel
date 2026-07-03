"""
Visualización SRTM GL1 para Guayana Francesa
Fuente: OpenTopography (https://portal.opentopography.org/datasetMetadata?otCollectionID=OT.042013.4326.1)
"""

import os
import math
import pathlib
import numpy as np
import rasterio
from rasterio.merge import merge
import matplotlib.pyplot as plt
from matplotlib.colors import LightSource
import requests

API_KEY = os.environ["OPENTOPO_API_KEY"]  # export OPENTOPO_API_KEY=xxxxx
OUT = pathlib.Path("/Users/davidflorezmazuera/Downloads/MalariaSentinel/terrain/srtm_guf")
OUT.mkdir(exist_ok=True)

S, N, W, E = 2.11, 5.75, -54.60, -51.64
DEM_TYPE = "SRTMGL1"


def download_bbox(south, north, west, east, demtype=DEM_TYPE):
    url = "https://portal.opentopography.org/API/globaldem"
    params = dict(
        demtype=demtype,
        south=south, north=north, west=west, east=east,
        outputFormat="GTiff",
        API_Key=API_KEY,
    )
    r = requests.get(url, params=params, timeout=300)
    r.raise_for_status()
    out = OUT / f"{demtype}_{west}_{east}_{south}_{north}.tif"
    out.write_bytes(r.content)
    return out


def hillshade(path, azimuth=315, altitude=45):
    with rasterio.open(path) as src:
        dem = src.read(1).astype("float32")
        nodata = src.nodata
        transform = src.transform
        crs = src.crs
        bounds = src.bounds
    if nodata is not None:
        dem = np.where(dem == nodata, np.nan, dem)
    ls = LightSource(azdeg=azimuth, altdeg=altitude)
    shaded = ls.hillshade(dem, vert_exag=2)
    return dem, shaded, transform, crs, bounds


def main():
    tif = download_bbox(S, N, W, E)
    print(f"Descargado: {tif}  ({tif.stat().st_size/1e6:.1f} MB)")

    dem, shaded, transform, crs, bounds = hillshade(tif)

    fig, axes = plt.subplots(1, 2, figsize=(14, 7))

    im0 = axes[0].imshow(dem, cmap="terrain")
    axes[0].set_title("DEM SRTM GL1 — Guayana Francesa (m)")
    plt.colorbar(im0, ax=axes[0], shrink=0.7, label="Elevación (m)")

    im1 = axes[1].imshow(shaded, cmap="gray")
    axes[1].set_title("Hillshade (az=315°, alt=45°)")
    plt.colorbar(im1, ax=axes[1], shrink=0.7)

    for ax in axes:
        ax.set_xlabel(f"lon [{bounds.left:.2f} → {bounds.right:.2f}]")
        ax.set_ylabel(f"lat [{bounds.bottom:.2f} → {bounds.top:.2f}]")
    fig.suptitle(f"CRS: {crs}  ·  {os.path.basename(tif)}")
    fig.tight_layout()
    fig.savefig(OUT / "srtm_guf_overview.png", dpi=150)
    print(f"Mapa: {OUT/'srtm_guf_overview.png'}")

    fig2, ax2 = plt.subplots(figsize=(9, 8))
    ax2.imshow(shaded, cmap="Greys_r", alpha=0.6)
    cs = ax2.contour(dem, levels=15, colors="brown", linewidths=0.4)
    ax2.clabel(cs, inline=True, fontsize=7, fmt="%d m")
    im2 = ax2.imshow(dem, cmap="terrain", alpha=0.5)
    plt.colorbar(im2, ax=ax2, shrink=0.8, label="m s.n.m.")
    ax2.set_title("Guayana Francesa — relieve SRTM con curvas de nivel")
    fig2.tight_layout()
    fig2.savefig(OUT / "srtm_guf_contour.png", dpi=200)
    print(f"Curvas: {OUT/'srtm_guf_contour.png'}")


if __name__ == "__main__":
    main()