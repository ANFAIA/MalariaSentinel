"""Visualización: los dos focos del REACT y su contexto regional."""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from scipy.spatial import ConvexHull

REACT = "../data/react"
events = pd.read_csv(f"{REACT}/event.txt", sep="\t", low_memory=False)

village = events.groupby("locality").agg(
    n_events=("eventID", "count"),
    lat=("decimalLatitude", "mean"),
    lon=("decimalLongitude", "mean"),
    country=("country", "first"),
    n_sites=("locationID", "nunique"),
).reset_index()

fig = plt.figure(figsize=(17, 9))

import matplotlib
matplotlib.rcParams['axes.grid'] = False

ax1 = fig.add_subplot(1, 2, 1, projection=ccrs.PlateCarree())
ax1.set_extent([-17, 16, 4, 28], crs=ccrs.PlateCarree())
ax1.add_feature(cfeature.LAND, facecolor="#f0ece2")
ax1.add_feature(cfeature.OCEAN, facecolor="#a8c8e0")
ax1.add_feature(cfeature.COASTLINE, linewidth=0.5, color="#333")
ax1.add_feature(cfeature.BORDERS, linewidth=0.6, color="#666", linestyle=":")
ax1.add_feature(cfeature.RIVERS, linewidth=0.3, color="#3a78a8")
ax1.add_feature(cfeature.LAKES, facecolor="#a8c8e0", edgecolor="none")

ax1.add_patch(Rectangle((-5.81, 8.84), 2.69, 2.16, facecolor="#fdebd0",
    edgecolor="#e67e22", linewidth=2, linestyle="--", alpha=0.4,
    transform=ccrs.PlateCarree(), zorder=2, label="Bounding box REACT"))

otros = {
    "Senegal": (-14.5, 14.5), "Mali": (-8, 17), "Ghana": (-1.5, 7.5),
    "Nigeria": (8, 9.5), "Sierra Leona": (-12, 8.5), "Liberia": (-9, 6.5),
    "Guinea": (-10, 10), "Togo": (1, 8), "Benin": (2, 9), "Camerún": (12, 6),
}
for p, (lo, la) in otros.items():
    ax1.plot(lo, la, "o", color="#c0392b", markersize=7, alpha=0.5,
             transform=ccrs.PlateCarree(), zorder=3)
    ax1.text(lo, la + 0.7, p, fontsize=8.5, color="#7b241c", ha="center",
             transform=ccrs.PlateCarree())

ax1.scatter(-5.605, 9.254, s=500, c="#3498db", marker="^", edgecolor="white",
    linewidth=2.5, transform=ccrs.PlateCarree(), zorder=6)
ax1.text(-5.605, 8.6, "Korhogo\n(Côte d'Ivoire)", fontsize=11, weight="bold",
         ha="center", color="#1f618d", transform=ccrs.PlateCarree(),
         bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.9))
ax1.scatter(-3.356, 10.800, s=500, c="#e67e22", edgecolor="white",
    linewidth=2.5, transform=ccrs.PlateCarree(), zorder=6)
ax1.text(-3.356, 11.55, "Diébougou\n(Burkina Faso)", fontsize=11, weight="bold",
         ha="center", color="#a04000", transform=ccrs.PlateCarree(),
         bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.9))

ax1.annotate("", xy=(-3.356, 10.5), xytext=(-5.605, 9.55),
    arrowprops=dict(arrowstyle="<->", color="#c0392b", lw=2.5),
    transform=ccrs.PlateCarree())
ax1.text(-4.5, 10.45, "300 km\nsin muestreo", fontsize=12, weight="bold",
         color="#c0392b", ha="center",
         bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.95),
         transform=ccrs.PlateCarree())

ax1.set_title("Vista regional: 2 focos de 2.500 km² cada uno\nen 5.000 km de costa malárica",
              fontsize=12, pad=10)

ax2 = fig.add_subplot(1, 2, 2, projection=ccrs.PlateCarree())
ax2.set_extent([-6.5, -2.8, 8.5, 11.5], crs=ccrs.PlateCarree())
ax2.add_feature(cfeature.LAND, facecolor="#f0ece2")
ax2.add_feature(cfeature.OCEAN, facecolor="#a8c8e0")
ax2.add_feature(cfeature.COASTLINE, linewidth=0.5, color="#333")
ax2.add_feature(cfeature.BORDERS, linewidth=0.7, color="#555", linestyle=":")
ax2.add_feature(cfeature.RIVERS, linewidth=0.3, color="#3a78a8")

bf_rv = village[village.country == "Burkina Faso"]
ci_rv = village[village.country.str.contains("Côte")]
ax2.scatter(bf_rv["lon"], bf_rv["lat"], c="#e67e22", s=180, edgecolor="white",
    linewidth=1.5, transform=ccrs.PlateCarree(), zorder=5, alpha=0.9)
ax2.scatter(ci_rv["lon"], ci_rv["lat"], c="#3498db", s=180, edgecolor="white",
    linewidth=1.5, transform=ccrs.PlateCarree(), zorder=5, marker="^", alpha=0.9)

for cluster, color in [(bf_rv, "#e67e22"), (ci_rv, "#3498db")]:
    pts = cluster[["lon","lat"]].values
    if len(pts) >= 3:
        hull = ConvexHull(pts)
        hull_pts = pts[hull.vertices]
        poly = plt.Polygon(hull_pts, facecolor=color, edgecolor=color, alpha=0.18,
            linestyle="--", linewidth=2, transform=ccrs.PlateCarree(), zorder=2)
        ax2.add_patch(poly)

ax2.text(-3.356, 11.18, f"Diébougou (BF)\n{len(bf_rv)} aldeas",
         fontsize=11, ha="center", color="#a04000", weight="bold",
         transform=ccrs.PlateCarree(),
         bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.9))
ax2.text(-5.605, 8.75, f"Korhogo (CI)\n{len(ci_rv)} aldeas",
         fontsize=11, ha="center", color="#1f618d", weight="bold",
         transform=ccrs.PlateCarree(),
         bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.9))

ax2.set_title("Zoom: cada cluster SÍ es sistemático\n(aldeas elegidas por criterios, 4 sitios c/u)",
              fontsize=12, pad=10)

fig.suptitle(
    "REACT — patrón geográfico: 2 'islas' de muestreo separadas por 300 km",
    fontsize=14, y=0.99, weight="bold",
)
plt.tight_layout()
plt.savefig("../data/maps/dos_focos.png", dpi=150, bbox_inches="tight", facecolor="white")
print("Mapa guardado en data/maps/dos_focos.png")
print(f"Aldeas reales: {len(village)} (BF={len(bf_rv)}, CI={len(ci_rv)})")