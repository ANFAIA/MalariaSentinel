"""Mapa del dataset Colombia VectorLink (PMI)."""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature

CO = "../data/colombia_vl"
df = pd.read_csv(f"{CO}/occurrence.txt", sep="\t", low_memory=False)
df = df[(df["decimalLatitude"].between(-90, 90)) & (df["decimalLongitude"].between(-180, 180))]

events = df.groupby(["eventID", "locality", "municipality", "decimalLatitude",
                      "decimalLongitude", "eventDate", "samplingProtocol"]).agg(
    n_mosq=("individualCount", "sum"),
    n_species=("scientificName", "nunique"),
    species=("scientificName", lambda x: ", ".join(sorted(set(x)))),
).reset_index()

loc = df.groupby(["locality", "decimalLatitude", "decimalLongitude",
                   "municipality"]).agg(
    n_mosq=("individualCount", "sum"),
    n_captures=("occurrenceID", "count"),
).reset_index()

print(f"Total eventos de captura: {len(events):,}")
print(f"Total mosquitos: {int(df['individualCount'].sum()):,}")
print(f"Localidades: {len(loc)}")
print(f"Municipios: {df['municipality'].unique()}")

import matplotlib
matplotlib.rcParams["axes.grid"] = False

fig = plt.figure(figsize=(16, 9))

ax1 = fig.add_subplot(1, 2, 1, projection=ccrs.PlateCarree())
ax1.set_extent([-78.2, -77.4, 2.3, 3.0], crs=ccrs.PlateCarree())
ax1.add_feature(cfeature.LAND, facecolor="#f0ece2")
ax1.add_feature(cfeature.OCEAN, facecolor="#a8c8e0")
ax1.add_feature(cfeature.COASTLINE, linewidth=0.6, color="#333")
ax1.add_feature(cfeature.RIVERS, linewidth=0.3, color="#3a78a8")
ax1.add_feature(cfeature.LAKES, facecolor="#a8c8e0", edgecolor="none")

species_dominant = df.groupby(["locality", "scientificName"])["individualCount"].sum().reset_index()
dom = species_dominant.loc[species_dominant.groupby("locality")["individualCount"].idxmax()]
loc_full = loc.merge(dom[["locality", "scientificName"]], on="locality")

species_colors = {
    "Anopheles neivai": "#e74c3c",
    "Anopheles albimanus": "#3498db",
    "Anopheles apicimacula": "#f39c12",
}
for sp, color in species_colors.items():
    sub = loc_full[loc_full["scientificName"] == sp]
    ax1.scatter(sub["decimalLongitude"], sub["decimalLatitude"],
        c=color, s=80 + np.log1p(sub["n_mosq"]) * 25,
        edgecolor="white", linewidth=1.2, alpha=0.9,
        label=f"{sp} (n={int(sub['n_mosq'].sum()):,})",
        transform=ccrs.PlateCarree(), zorder=5)

for muni in df["municipality"].unique():
    sub = df[df["municipality"] == muni]
    lat_c = sub["decimalLatitude"].mean()
    lon_c = sub["decimalLongitude"].mean()
    ax1.text(lon_c, lat_c, muni, fontsize=10, weight="bold", color="#2c3e50",
             ha="center", transform=ccrs.PlateCarree(),
             bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.85))

ax1.text(-77.9, 2.55, "Pacífico\ncolombiano", fontsize=10, color="#0d4f3b",
         ha="center", style="italic", transform=ccrs.PlateCarree())

ax1.set_title(
    "Colombia VectorLink (PMI) — 25 localidades, 229,394 mosquitos\n"
    "HLC + indoor/outdoor, 2021-2023, CC BY-NC 4.0",
    fontsize=12, pad=10,
)
ax1.legend(loc="lower right", fontsize=8.5, framealpha=0.9, title="Especie dominante")

ax2 = fig.add_subplot(2, 2, 2)
sp_totals = df.groupby("scientificName")["individualCount"].sum().sort_values()
colors_sp = [species_colors[sp] for sp in sp_totals.index]
bars = ax2.barh(sp_totals.index.str.replace("Anopheles ", "An. "), sp_totals.values,
                color=colors_sp, edgecolor="white")
total = sp_totals.sum()
for i, v in enumerate(sp_totals.values):
    pct = 100 * v / total
    ax2.text(v + 3000, i, f"{int(v):,} ({pct:.1f}%)", va="center", fontsize=9.5)
ax2.set_xlim(0, sp_totals.max() * 1.18)
ax2.set_xlabel("Nº de mosquitos")
ax2.set_title("Total mosquitos por especie", fontsize=11)
ax2.grid(axis="x", alpha=0.3)

ax3 = fig.add_subplot(2, 2, 4)
df["eventDate"] = pd.to_datetime(df["eventDate"], errors="coerce", utc=True)
ts = df.dropna(subset=["eventDate"]).set_index("eventDate").resample("ME")["individualCount"].sum()
ax3.bar(ts.index, ts.values, width=20, color="#8e44ad", edgecolor="white", alpha=0.85)
ax3.set_title("Capturas mensuales (suma de mosquitos)", fontsize=11)
ax3.set_ylabel("Nº de mosquitos")
ax3.set_xlabel("Mes")
ax3.grid(axis="y", alpha=0.3)
plt.setp(ax3.xaxis.get_majorticklabels(), rotation=45, ha="right", fontsize=7)

fig.suptitle(
    "Dataset Colombia VectorLink (PMI) — Pacífico colombiano",
    fontsize=14, y=0.99, weight="bold",
)
plt.tight_layout()
plt.savefig("../data/maps/colombia_vl_map.png", dpi=150, bbox_inches="tight", facecolor="white")
print("Mapa guardado en data/maps/colombia_vl_map.png")