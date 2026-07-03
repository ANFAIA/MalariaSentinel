"""Visualizaciones de los sesgos del dataset Anopheles GBIF."""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

OCC_PATH = "../data/guf/occurrence.txt"
df = pd.read_csv(OCC_PATH, sep="\t", low_memory=False)
df = df[(df["decimalLatitude"].between(-90, 90)) & (df["decimalLongitude"].between(-180, 180))]
df = df.dropna(subset=["decimalLatitude", "decimalLongitude"])

cayenne_lat, cayenne_lon = 4.937, -52.326
df["dist_cayenne_km"] = np.sqrt(
    ((df["decimalLatitude"] - cayenne_lat) * 111) ** 2
    + ((df["decimalLongitude"] - cayenne_lon) * 111 * np.cos(np.radians(cayenne_lat))) ** 2
)

fig = plt.figure(figsize=(15, 10))
gs = fig.add_gridspec(2, 2, hspace=0.35, wspace=0.28)

ax1 = fig.add_subplot(gs[0, 0])
year_counts = df["year"].value_counts().sort_index()
colors = ["#c0392b" if y < 2000 else "#2980b9" for y in year_counts.index]
ax1.bar(year_counts.index, year_counts.values, color=colors, edgecolor="white", linewidth=0.4)
ax1.set_title("Registros por año (rojo < 2000, azul ≥ 2000 con GPS preciso)", fontsize=11)
ax1.set_xlabel("Año")
ax1.set_ylabel("Nº de registros")
ax1.set_xlim(1900, 2015)
ax1.grid(axis="y", alpha=0.3)
ax1.axvline(2000, color="black", linestyle=":", linewidth=1)
ax1.text(2000.5, ax1.get_ylim()[1] * 0.9, "GPS preciso desde aquí",
         fontsize=8, color="black")

ax2 = fig.add_subplot(gs[0, 1])
bins = np.linspace(0, 600, 25)
ax2.hist(df["dist_cayenne_km"], bins=bins, color="#16a085", edgecolor="white", alpha=0.85)
ax2.set_title("Distancia a Cayenne (capital, ~90% de la población)", fontsize=11)
ax2.set_xlabel("Distancia (km)")
ax2.set_ylabel("Nº de registros")
ax2.axvline(50, color="#c0392b", linestyle="--", label="50 km")
ax2.axvline(200, color="#e67e22", linestyle="--", label="200 km")
ax2.legend()
ax2.grid(axis="y", alpha=0.3)

ax3 = fig.add_subplot(gs[1, 0])
df["decade"] = (df["year"] // 10) * 10
top_inst = df["institutionCode"].value_counts().head(5).index.tolist()
inst_dec = df[df["institutionCode"].isin(top_inst)].groupby(
    ["decade", "institutionCode"]
).size().unstack(fill_value=0)
inst_dec = inst_dec.reindex(columns=top_inst)
inst_dec.plot(kind="bar", stacked=True, ax=ax3,
              colormap="tab10", edgecolor="white", linewidth=0.4, legend=False)
ax3.set_title("Registros por década según institución", fontsize=11)
ax3.set_xlabel("Década")
ax3.set_ylabel("Nº de registros")
ax3.tick_params(axis="x", rotation=45)
ax3.legend(top_inst, loc="upper left", fontsize=7, framealpha=0.9)
ax3.grid(axis="y", alpha=0.3)

ax4 = fig.add_subplot(gs[1, 1])
top_sp = df["scientificName"].value_counts().head(5).index.tolist()
sp_dec = df[df["scientificName"].isin(top_sp)].groupby(
    ["decade", "scientificName"]
).size().unstack(fill_value=0)
sp_dec = sp_dec.reindex(columns=top_sp)
short_names = [s.split(" ")[1] for s in top_sp]
sp_dec.columns = short_names
sp_dec.plot(ax=ax4, marker="o", linewidth=1.6, markersize=5)
ax4.set_title("Especies más comunes por década", fontsize=11)
ax4.set_xlabel("Década")
ax4.set_ylabel("Nº de registros")
ax4.legend(fontsize=8)
ax4.grid(alpha=0.3)

fig.suptitle(
    "Análisis de sesgos del dataset Anopheles (Guayana Francesa + Amapá, 1902–2014)",
    fontsize=13, y=1.0,
)
plt.savefig("../data/maps/sesgos_anopheles.png", dpi=150, bbox_inches="tight", facecolor="white")
print("Gráfico guardado en data/maps/sesgos_anopheles.png")