"""Mapa del dataset Ghana IDIT (larvas Anopheles, multi-ecozona, 2023-2025)."""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature

GHANA = "../data/ghana_idit"
df = pd.read_csv(f"{GHANA}/occurrence.txt", sep="\t", low_memory=False)
df = df[(df["decimalLatitude"].between(-90, 90)) & (df["decimalLongitude"].between(-180, 180))]

loc = df.groupby(["locality", "decimalLatitude", "decimalLongitude"]).size().reset_index(name="n_larvae")
print(f"Localidades: {len(loc)}")
print(f"Total larvas: {len(df):,}")

fig = plt.figure(figsize=(16, 9))
import matplotlib
matplotlib.rcParams["axes.grid"] = False

ax1 = fig.add_subplot(1, 2, 1, projection=ccrs.PlateCarree())
ax1.set_extent([-3.5, 1.0, 4.5, 11.5], crs=ccrs.PlateCarree())
ax1.add_feature(cfeature.LAND, facecolor="#f0ece2")
ax1.add_feature(cfeature.OCEAN, facecolor="#a8c8e0")
ax1.add_feature(cfeature.COASTLINE, linewidth=0.6, color="#333")
ax1.add_feature(cfeature.BORDERS, linewidth=0.7, color="#555", linestyle=":")
ax1.add_feature(cfeature.RIVERS, linewidth=0.3, color="#3a78a8")
ax1.add_feature(cfeature.LAKES, facecolor="#a8c8e0", edgecolor="none")

sc = ax1.scatter(
    loc["decimalLongitude"], loc["decimalLatitude"],
    c=loc["n_larvae"], cmap="YlGnBu", s=60+loc["n_larvae"]*3,
    edgecolor="white", linewidth=1, vmin=0, vmax=loc["n_larvae"].max(),
    transform=ccrs.PlateCarree(), zorder=5,
)
cbar = plt.colorbar(sc, ax=ax1, fraction=0.04, pad=0.04)
cbar.set_label("Nº de larvas colectadas", fontsize=10)

ax1.text(-0.2, 10.5, "Savana\nSudaniana", fontsize=9, ha="center", color="#7b241c",
         bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.7),
         transform=ccrs.PlateCarree())
ax1.text(-2.5, 7.5, "Bosque\nhúmedo", fontsize=9, ha="center", color="#1b4d3e",
         bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.7),
         transform=ccrs.PlateCarree())
ax1.text(-1.5, 5.5, "Bosque\ncostero", fontsize=9, ha="center", color="#0d4f3b",
         bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.7),
         transform=ccrs.PlateCarree())

capitals = {
    "Accra": (-0.20, 5.55), "Kumasi": (-1.62, 6.69),
    "Tamale": (-0.84, 9.40), "Wa": (-2.50, 10.06),
    "Bolgatanga": (-0.85, 10.78), "Ho": (0.47, 6.61),
}
for name, (lo, la) in capitals.items():
    ax1.plot(lo, la, "s", color="#34495e", markersize=5, transform=ccrs.PlateCarree(), zorder=4)
    ax1.text(lo + 0.1, la, name, fontsize=7.5, color="#34495e", transform=ccrs.PlateCarree())

ax1.set_title(
    "Ghana IDIT — Larvas de Anopheles gambiae s.l. por localidad\n"
    "20 sitios, 1,008 larvas, 2023-2025, CC0 1.0",
    fontsize=12, pad=10,
)

ax2 = fig.add_subplot(2, 2, 2)
top = loc.sort_values("n_larvae", ascending=True).tail(10)
colors_bar = plt.cm.YlGnBu(np.linspace(0.3, 0.9, len(top)))
ax2.barh(top["locality"].str[:25], top["n_larvae"], color=colors_bar, edgecolor="white")
for i, (idx, row) in enumerate(top.iterrows()):
    ax2.text(row["n_larvae"] + 2, i, f"{row['n_larvae']}", va="center", fontsize=9)
ax2.set_xlabel("Nº de larvas")
ax2.set_title("Top 10 localidades con más larvas", fontsize=11)
ax2.set_xlim(0, top["n_larvae"].max() * 1.12)
ax2.grid(axis="x", alpha=0.3)

ax3 = fig.add_subplot(2, 2, 4)
year_counts = df["year"].value_counts().sort_index()
ax3.bar([str(int(y)) for y in year_counts.index], year_counts.values,
        color="#16a085", edgecolor="white", alpha=0.85)
for i, v in enumerate(year_counts.values):
    ax3.text(i, v + 15, f"{v}", ha="center", fontsize=10)
ax3.set_title("Capturas por año", fontsize=11)
ax3.set_ylabel("Nº de larvas")
ax3.set_xlabel("Año")
ax3.set_ylim(0, year_counts.max() * 1.15)
ax3.grid(axis="y", alpha=0.3)

fig.suptitle(
    "Dataset Ghana IDIT (Univ. Ghana Medical School) — primera visualización",
    fontsize=14, y=0.99, weight="bold",
)
plt.tight_layout()
plt.savefig("../data/maps/ghana_idit_map.png", dpi=150, bbox_inches="tight", facecolor="white")
print("Mapa guardado en data/maps/ghana_idit_map.png")