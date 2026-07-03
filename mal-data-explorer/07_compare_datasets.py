"""Comparación cuantitativa de 3 datasets de mosquitos vectores de malaria."""
import urllib.request, json
import pandas as pd
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature

REACT = "../data/react"
events = pd.read_csv(f"{REACT}/event.txt", sep="\t", low_memory=False)
occ = pd.read_csv(f"{REACT}/occurrence.txt", sep="\t", low_memory=False)
emof = pd.read_csv(f"{REACT}/extendedmeasurementorfact.txt", sep="\t", low_memory=False)
events["village_id"] = events["locationID"].str.extract(r"^(\d+[A-Z]+)")

mosq_per_event = occ.groupby("eventID").size().rename("n_mosq")
ev = events.merge(mosq_per_event, on="eventID", how="left")
village = ev.groupby("village_id").agg(
    n_events=("eventID","count"), n_mosq=("n_mosq","sum"),
    lat=("decimalLatitude","mean"), lon=("decimalLongitude","mean"),
    country=("country","first"),
).reset_index()
village["br"] = village["n_mosq"] / village["n_events"]

datasets = {
    "REACT (IRD)": dict(
        pais="Burkina Faso + Côte d'Ivoire",
        n_occs=60705, n_sites=421, n_years=2,
        license="CC BY 4.0", bias=9, color="#27ae60",
        syst="Sí", gps="Sí", mol="Sí PCR+kdr", inout="Sí", amb="Sí",
    ),
    "Colombia VectorLink (PMI)": dict(
        pais="Pacífico colombiano",
        n_occs=1502, n_sites=25, n_years=2,
        license="CC BY-NC 4.0", bias=8, color="#3498db",
        syst="Sí", gps="Sí", mol="Sí Plasmodium", inout="Sí", amb="No",
    ),
    "Ghana IDIT (Univ. Ghana)": dict(
        pais="Ghana (multi-ecozona)",
        n_occs=1008, n_sites=22, n_years=2,
        license="CC0 1.0", bias=9, color="#16a085",
        syst="Sí", gps="Sí", mol="Sí kdr", inout="No", amb="No",
    ),
    "Kinshasa (Univ. Kinshasa)": dict(
        pais="Kinshasa, RD Congo",
        n_occs=3839, n_sites=39, n_years=1,
        license="CC0 1.0", bias=8, color="#9b59b6",
        syst="Sí", gps="Sí", mol="Sí gambiae", inout="No", amb="No",
    ),
    "An. stephensi (MAP)": dict(
        pais="Mundial (especie invasora)",
        n_occs=1126, n_sites="compilado", n_years=35,
        license="CC BY-NC 4.0", bias=5, color="#95a5a6",
        syst="No", gps="Mixto", mol="Sí PCR", inout="No", amb="No",
    ),
    "Pasteur (Guayana Fr.)": dict(
        pais="Guayana Francesa + Amapá",
        n_occs=3917, n_sites="compilado", n_years=113,
        license="CC BY-NC 4.0", bias=3, color="#e74c3c",
        syst="No", gps="Mixto", mol="No", inout="No", amb="No",
    ),
}

fig = plt.figure(figsize=(16, 10))
gs = fig.add_gridspec(2, 3, hspace=0.35, wspace=0.30, height_ratios=[1.0, 1.0])

ax1 = fig.add_subplot(gs[0, :2], projection=ccrs.PlateCarree())
ax1.set_extent([-6.5, -2.8, 8.5, 11.5], crs=ccrs.PlateCarree())
ax1.add_feature(cfeature.LAND, facecolor="#f0ece2")
ax1.add_feature(cfeature.OCEAN, facecolor="#a8c8e0")
ax1.add_feature(cfeature.COASTLINE, linewidth=0.5, color="#333")
ax1.add_feature(cfeature.BORDERS, linewidth=0.7, color="#555", linestyle=":")
ax1.add_feature(cfeature.RIVERS, linewidth=0.3, color="#3a78a8")
bf = village[village.country == "Burkina Faso"]
ci = village[village.country.str.contains("Côte")]
sc1 = ax1.scatter(bf["lon"], bf["lat"], c=bf["br"], cmap="YlOrRd",
    s=25+bf["br"]*0.4, edgecolor="white", linewidth=0.5,
    vmin=0, vmax=200, transform=ccrs.PlateCarree(), zorder=5)
ax1.scatter(ci["lon"], ci["lat"], c=ci["br"], cmap="YlOrRd",
    s=25+ci["br"]*0.4, edgecolor="white", linewidth=0.5,
    vmin=0, vmax=200, transform=ccrs.PlateCarree(), zorder=5, marker="^")
cbar = plt.colorbar(sc1, ax=ax1, fraction=0.025, pad=0.01)
cbar.set_label("Biting rate (mosquitos/noche-colector)", fontsize=10)
ax1.set_title("REACT — IRD (Burkina Faso + Côte d'Ivoire, 2016-2018)\n60,705 mosquitos, 421 aldeas, GPS preciso, indoor + outdoor",
              fontsize=12)
gl = ax1.gridlines(draw_labels=True, linewidth=0.3, color="#999", alpha=0.5)
gl.top_labels = False; gl.right_labels = False

ax_score = fig.add_subplot(gs[0, 2])
names = list(datasets.keys())
scores = [datasets[n]["bias"] for n in names]
colors_b = [datasets[n]["color"] for n in names]
bars = ax_score.barh(range(len(names)), scores, color=colors_b, edgecolor="white")
ax_score.set_yticks(range(len(names)))
ax_score.set_yticklabels([n.replace(" (IRD)","").replace(" (Univ. Ghana)","").replace(" (Univ. Kinshasa)","") for n in names], fontsize=9)
ax_score.set_xlim(0, 10)
ax_score.set_xlabel("Score (1=muy sesgado, 10=robusto)")
ax_score.set_title("Calidad metodológica", fontsize=11)
ax_score.invert_yaxis()
for i, b in enumerate(bars):
    ax_score.text(b.get_width() + 0.2, b.get_y() + b.get_height()/2,
                  f"{scores[i]}/10", va="center", fontsize=9, weight="bold")

ax_tab = fig.add_subplot(gs[1, :])
ax_tab.axis("off")

headers = ["Dataset", "País / zona", "Ocurrencias", "Sitios únicos", "Años",
           "Sist.\nmuestreo", "GPS", "Molecular", "Indoor/\noutdoor",
           "Ambiental", "Licencia"]
rows = []
for name, d in datasets.items():
    rows.append([
        name, d["pais"], f"{d['n_occs']:,}", str(d["n_sites"]), str(d["n_years"]),
        d["syst"], d["gps"], d["mol"], d["inout"], d["amb"],
        d["license"].replace("http://creativecommons.org/licenses/","").replace("/legalcode","").replace("publicdomain/zero/1.0","CC0 1.0"),
    ])
table = ax_tab.table(cellText=rows, colLabels=headers, cellLoc="left", loc="center")
table.auto_set_font_size(False)
table.set_fontsize(9)
table.scale(1, 1.6)
for i in range(len(headers)):
    table[(0, i)].set_facecolor("#2c3e50")
    table[(0, i)].set_text_props(weight="bold", color="white")
for i in range(len(rows)):
    if "REACT" in rows[i][0]:
        for j in range(len(headers)):
            table[(i+1, j)].set_facecolor("#d4efdf")
    elif "Pasteur" in rows[i][0]:
        for j in range(len(headers)):
            table[(i+1, j)].set_facecolor("#fadbd8")
ax_tab.set_title("Comparación de 6 datasets de Anopheles vectores de malaria",
                 fontsize=12, pad=12, loc="left")

fig.suptitle("Datasets GIS de mosquitos vectores de malaria — comparación",
             fontsize=14, y=0.99, weight="bold")
plt.savefig("../data/maps/datasets_comparacion.png", dpi=150, bbox_inches="tight", facecolor="white")
print("Comparación guardada en data/maps/datasets_comparacion.png")