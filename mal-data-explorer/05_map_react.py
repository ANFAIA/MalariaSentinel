"""Mapa del dataset REACT (IRD) y comparación cuantitativa con otros datasets."""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from matplotlib.lines import Line2D

REACT = "../data/react"
events = pd.read_csv(f"{REACT}/event.txt", sep="\t", low_memory=False)
occ = pd.read_csv(f"{REACT}/occurrence.txt", sep="\t", low_memory=False)
emof = pd.read_csv(f"{REACT}/extendedmeasurementorfact.txt", sep="\t", low_memory=False)

events["village_id"] = events["locationID"].str.extract(r"^(\d+[A-Z]+)")

mosq_per_event = occ.groupby("eventID").size().rename("n_mosq")
events = events.merge(mosq_per_event, on="eventID", how="left")
events["n_mosq"] = events["n_mosq"].fillna(0).astype(int)

place = emof[emof["measurementType"] == "place of collection"][
    ["occurrenceID", "measurementValue"]
].rename(columns={"measurementValue": "place"})
occ = occ.merge(place, on="occurrenceID", how="left")

plasmo = emof[emof["measurementType"] == "plasmodium falciparum infection"][
    ["occurrenceID", "measurementValue"]
].rename(columns={"measurementValue": "plasmodium"})
occ = occ.merge(plasmo, on="occurrenceID", how="left")

village = events.groupby("village_id").agg(
    n_events=("eventID", "count"),
    n_mosq=("n_mosq", "sum"),
    lat=("decimalLatitude", "mean"),
    lon=("decimalLongitude", "mean"),
    village=("locality", "first"),
    country=("country", "first"),
).reset_index()
village["mosq_per_night"] = village["n_mosq"] / village["n_events"]

fig = plt.figure(figsize=(16, 10))
gs = fig.add_gridspec(2, 2, hspace=0.25, wspace=0.20, height_ratios=[1.5, 1])

ax1 = fig.add_subplot(gs[0, :], projection=ccrs.PlateCarree())
ax1.set_extent([-6.5, -2.8, 8.5, 11.5], crs=ccrs.PlateCarree())
ax1.add_feature(cfeature.LAND, facecolor="#f0ece2")
ax1.add_feature(cfeature.OCEAN, facecolor="#a8c8e0")
ax1.add_feature(cfeature.COASTLINE, linewidth=0.5, color="#333")
ax1.add_feature(cfeature.BORDERS, linewidth=0.7, color="#555", linestyle=":")
ax1.add_feature(cfeature.RIVERS, linewidth=0.3, color="#3a78a8")
ax1.add_feature(cfeature.LAKES, facecolor="#a8c8e0", edgecolor="none")

bf = village[village.country == "Burkina Faso"]
ci = village[village.country.str.contains("Côte")]
sc1 = ax1.scatter(
    bf["lon"], bf["lat"], c=bf["mosq_per_night"], cmap="YlOrRd",
    s=80, edgecolor="white", linewidth=0.7, transform=ccrs.PlateCarree(),
    vmin=0, vmax=village["mosq_per_night"].quantile(0.95), zorder=5,
)
sc2 = ax1.scatter(
    ci["lon"], ci["lat"], c=ci["mosq_per_night"], cmap="YlOrRd",
    s=80, edgecolor="white", linewidth=0.7, transform=ccrs.PlateCarree(),
    vmin=0, vmax=village["mosq_per_night"].quantile(0.95), zorder=5, marker="^",
)
cbar = plt.colorbar(sc1, ax=ax1, fraction=0.025, pad=0.01)
cbar.set_label("Mosquitos por noche-colector (biting rate)", fontsize=10)

ax1.set_title(
    "REACT dataset: biting rate de Anopheles en aldeas rurales\n"
    "Burkina Faso (●) + Côte d'Ivoire (▲) — 2016-2018 — IRD",
    fontsize=12,
)
gl = ax1.gridlines(draw_labels=True, linewidth=0.3, color="#999", alpha=0.5)
gl.top_labels = False
gl.right_labels = False

ax1.text(-5.5, 9.7, "KorhoGo\narea (CI)", transform=ccrs.PlateCarree(),
         fontsize=10, color="#333", ha="center",
         bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.7))
ax1.text(-3.3, 10.7, "Diébougou\narea (BF)", transform=ccrs.PlateCarree(),
         fontsize=10, color="#333", ha="center",
         bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.7))

ax2 = fig.add_subplot(gs[1, 0])
counts_place = occ["place"].value_counts()
colors_place = ["#3498db", "#e67e22"]
ax2.bar(
    ["Interior\nde la vivienda", "Exterior\nde la vivienda"],
    counts_place.values, color=colors_place, edgecolor="white", linewidth=1.5,
)
for i, v in enumerate(counts_place.values):
    ax2.text(i, v + 800, f"{v:,}\n({100*v/len(occ):.1f}%)", ha="center", fontsize=10)
ax2.set_title("Distribución indoor / outdoor\n(60,705 mosquitos)", fontsize=11)
ax2.set_ylabel("Nº de mosquitos")
ax2.set_ylim(0, counts_place.max() * 1.15)
ax2.grid(axis="y", alpha=0.3)

ax3 = fig.add_subplot(gs[1, 1])
events["eventDate"] = pd.to_datetime(events["eventDate"].str[:10], errors="coerce")
events["month_year"] = events["eventDate"].dt.to_period("M").astype(str)
ts = events.groupby("month_year").agg(
    n_mosq=("n_mosq", "sum"), n_events=("eventID", "count")
).reset_index()
ax3.bar(ts["month_year"], ts["n_mosq"], color="#16a085", edgecolor="white", alpha=0.85)
ax3.set_title("Capturas mensuales (mosquitos totales)", fontsize=11)
ax3.set_ylabel("Nº de mosquitos")
ax3.set_xlabel("Mes")
ax3.tick_params(axis="x", rotation=60, labelsize=7)
ax3.grid(axis="y", alpha=0.3)
n_lab = len(ts)
step = max(1, n_lab // 8)
ax3.set_xticks(range(0, n_lab, step))
ax3.set_xticklabels([ts["month_year"].iloc[i] for i in range(0, n_lab, step)], rotation=60, ha="right")

fig.suptitle(
    "Dataset REACT (IRD) — primera visualización: 421 aldeas, 60,705 mosquitos, GPS preciso",
    fontsize=13, y=1.0,
)
plt.savefig("../data/maps/react_map.png", dpi=150, bbox_inches="tight", facecolor="white")
print("Mapa guardado en data/maps/react_map.png")