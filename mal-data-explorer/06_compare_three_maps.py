"""Comparación de los 3 mapas de datasets GIS de Anopheles."""
import pandas as pd
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import numpy as np
import matplotlib
matplotlib.rcParams["axes.grid"] = False

REACT = "../data/react"
events_r = pd.read_csv(f"{REACT}/event.txt", sep="\t", low_memory=False)
occ_r = pd.read_csv(f"{REACT}/occurrence.txt", sep="\t", low_memory=False)
emof_r = pd.read_csv(f"{REACT}/extendedmeasurementorfact.txt", sep="\t", low_memory=False)
events_r["village_id"] = events_r["locationID"].str.extract(r"^(\d+[A-Z]+)", expand=False)
mosq_per_event = occ_r.groupby("eventID").size().rename("n_mosq")
ev_r = events_r.merge(mosq_per_event, on="eventID", how="left")
village_simple = ev_r.groupby("locality").agg(
    n_events=("eventID", "count"),
    n_mosq=("n_mosq", "sum"),
    lat=("decimalLatitude", "mean"),
    lon=("decimalLongitude", "mean"),
    country=("country", "first"),
).reset_index()
village_simple["br"] = village_simple["n_mosq"] / village_simple["n_events"]

g = pd.read_csv("../data/ghana_idit/occurrence.txt", sep="\t", low_memory=False)
g = g[(g["decimalLatitude"].between(-90,90)) & (g["decimalLongitude"].between(-180,180))]
village_g = g.groupby(["locality", "decimalLatitude", "decimalLongitude"]).size().reset_index(name="n_larvae")

c = pd.read_csv("../data/colombia_vl/occurrence.txt", sep="\t", low_memory=False)
c = c[(c["decimalLatitude"].between(-90,90)) & (c["decimalLongitude"].between(-180,180))]
village_c = c.groupby(["locality", "decimalLatitude", "decimalLongitude",
                       "municipality"]).agg(
    n_mosq=("individualCount", "sum"),
).reset_index()

fig = plt.figure(figsize=(18, 10))
gs = fig.add_gridspec(2, 3, hspace=0.30, wspace=0.20, height_ratios=[1.4, 0.8])

ax1 = fig.add_subplot(gs[0, 0], projection=ccrs.PlateCarree())
ax1.set_extent([-6.5, -2.8, 8.5, 11.5], crs=ccrs.PlateCarree())
ax1.add_feature(cfeature.LAND, facecolor="#f0ece2")
ax1.add_feature(cfeature.OCEAN, facecolor="#a8c8e0")
ax1.add_feature(cfeature.COASTLINE, linewidth=0.5, color="#333")
ax1.add_feature(cfeature.BORDERS, linewidth=0.7, color="#555", linestyle=":")
ax1.add_feature(cfeature.RIVERS, linewidth=0.3, color="#3a78a8")
bf_r = village_simple[village_simple.country == "Burkina Faso"]
ci_r = village_simple[village_simple.country.str.contains("Côte")]
ax1.scatter(bf_r["lon"], bf_r["lat"], c=bf_r["br"], cmap="YlOrRd",
    s=30+bf_r["br"]*0.4, edgecolor="white", linewidth=0.5,
    vmin=0, vmax=200, transform=ccrs.PlateCarree(), zorder=5)
sc1 = ax1.scatter(ci_r["lon"], ci_r["lat"], c=ci_r["br"], cmap="YlOrRd",
    s=30+ci_r["br"]*0.4, edgecolor="white", linewidth=0.5,
    vmin=0, vmax=200, transform=ccrs.PlateCarree(), zorder=5, marker="^")
ax1.set_title("REACT (Burkina Faso + CI, 2016-2018)\n60,705 mosquitos • 59 aldeas • HLC",
              fontsize=11)

ax2 = fig.add_subplot(gs[0, 1], projection=ccrs.PlateCarree())
ax2.set_extent([-3.5, 1.0, 4.5, 11.0], crs=ccrs.PlateCarree())
ax2.add_feature(cfeature.LAND, facecolor="#f0ece2")
ax2.add_feature(cfeature.OCEAN, facecolor="#a8c8e0")
ax2.add_feature(cfeature.COASTLINE, linewidth=0.5, color="#333")
ax2.add_feature(cfeature.BORDERS, linewidth=0.7, color="#555", linestyle=":")
ax2.add_feature(cfeature.RIVERS, linewidth=0.3, color="#3a78a8")
sc2 = ax2.scatter(village_g["decimalLongitude"], village_g["decimalLatitude"],
    c=village_g["n_larvae"], cmap="YlGnBu", s=70+village_g["n_larvae"]*4,
    edgecolor="white", linewidth=1, vmin=0, vmax=110,
    transform=ccrs.PlateCarree(), zorder=5)
ax2.set_title("Ghana IDIT (2023-2025)\n1,008 larvas • 24 sitios • Larval sampling",
              fontsize=11)

ax3 = fig.add_subplot(gs[0, 2], projection=ccrs.PlateCarree())
ax3.set_extent([-78.2, -77.4, 2.3, 3.0], crs=ccrs.PlateCarree())
ax3.add_feature(cfeature.LAND, facecolor="#f0ece2")
ax3.add_feature(cfeature.OCEAN, facecolor="#a8c8e0")
ax3.add_feature(cfeature.COASTLINE, linewidth=0.5, color="#333")
ax3.add_feature(cfeature.RIVERS, linewidth=0.3, color="#3a78a8")
species_colors = {"Anopheles neivai": "#e74c3c", "Anopheles albimanus": "#3498db"}
species_dominant = c.groupby(["locality", "scientificName"])["individualCount"].sum().reset_index()
dom = species_dominant.loc[species_dominant.groupby("locality")["individualCount"].idxmax()]
village_c_dom = village_c.merge(dom[["locality", "scientificName"]], on="locality")
for sp, color in species_colors.items():
    sub = village_c_dom[village_c_dom["scientificName"] == sp]
    ax3.scatter(sub["decimalLongitude"], sub["decimalLatitude"], c=color,
        s=80+np.log1p(sub["n_mosq"])*25, edgecolor="white", linewidth=1.2,
        alpha=0.9, label=f"{sp.split()[1]}",
        transform=ccrs.PlateCarree(), zorder=5)
ax3.set_title("Colombia VectorLink (2021-2023)\n229,394 mosquitos • 25 localidades • HLC",
              fontsize=11)
ax3.legend(loc="lower right", fontsize=9, framealpha=0.9, title="Especie")

ax_tab = fig.add_subplot(gs[1, :])
ax_tab.axis("off")

datasets = [
    ["REACT (IRD)", "Burkina Faso + Côte d'Ivoire",
     f"{len(occ_r):,}", "59 aldeas", "HLC indoor+outdoor",
     "Sí (PCR + kdr)", "60+ campos", "CC BY 4.0"],
    ["Ghana IDIT", "Ghana (multi-ecozona)",
     f"{len(g):,}", "24 sitios", "Larval sampling",
     "Sí (kdr)", "20", "CC0 1.0"],
    ["Colombia VL (PMI)", "Pacífico colombiano",
     f"{int(c['individualCount'].sum()):,}", "25 localidades", "HLC indoor+outdoor",
     "Sí (Plasmodium)", "68", "CC BY-NC 4.0"],
]
headers = ["Dataset", "Región", "Total mosquitos", "Sitios", "Método captura",
           "Identificación", "Nº columnas", "Licencia"]
table = ax_tab.table(cellText=datasets, colLabels=headers, cellLoc="left", loc="center")
table.auto_set_font_size(False)
table.set_fontsize(10)
table.scale(1, 1.8)
for i in range(len(headers)):
    table[(0, i)].set_facecolor("#2c3e50")
    table[(0, i)].set_text_props(weight="bold", color="white")
colors_rows = ["#d4efdf", "#d4efdf", "#d4efdf"]
for i in range(len(datasets)):
    for j in range(len(headers)):
        table[(i+1, j)].set_facecolor(colors_rows[i])

fig.suptitle(
    "3 datasets GIS de mosquitos vectores de malaria — mapas comparados",
    fontsize=15, y=0.995, weight="bold",
)
plt.savefig("../data/maps/tres_mapas.png", dpi=150, bbox_inches="tight", facecolor="white")
print("Comparación guardada en data/maps/tres_mapas.png")