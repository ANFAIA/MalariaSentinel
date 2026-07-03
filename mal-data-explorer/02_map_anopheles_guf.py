"""Mapa de ocurrencias de Anopheles en Guayana Francesa y Amapá."""
import pandas as pd
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature

OCC_PATH = "../data/guf/occurrence.txt"

print("Cargando datos...")
df = pd.read_csv(OCC_PATH, sep="\t", low_memory=False)
print(f"Total registros: {len(df)}")

df = df.dropna(subset=["decimalLatitude", "decimalLongitude"])
df = df[(df["decimalLatitude"].between(-90, 90)) & (df["decimalLongitude"].between(-180, 180))]
print(f"Registros con coordenadas válidas: {len(df)}")

print(f"Rango latitudes: {df['decimalLatitude'].min():.3f} a {df['decimalLatitude'].max():.3f}")
print(f"Rango longitudes: {df['decimalLongitude'].min():.3f} a {df['decimalLongitude'].max():.3f}")
print(f"Rango años: {df['year'].min()} a {df['year'].max()}")

print("\nEspecies más frecuentes:")
print(df["scientificName"].value_counts().head(10))

print("\nGenerando mapa...")

lat_min, lat_max = df["decimalLatitude"].min() - 0.5, df["decimalLatitude"].max() + 0.5
lon_min, lon_max = df["decimalLongitude"].min() - 0.5, df["decimalLongitude"].max() + 0.5

fig = plt.figure(figsize=(14, 12))
ax = plt.axes(projection=ccrs.PlateCarree())
ax.set_extent([lon_min, lon_max, lat_min, lat_max], crs=ccrs.PlateCarree())

ax.add_feature(cfeature.LAND, facecolor="#f0ece2")
ax.add_feature(cfeature.OCEAN, facecolor="#a8c8e0")
ax.add_feature(cfeature.COASTLINE, linewidth=0.6, color="#333333")
ax.add_feature(cfeature.BORDERS, linewidth=0.5, color="#555555", linestyle=":")
ax.add_feature(cfeature.RIVERS, linewidth=0.3, color="#3a78a8")

species = df["scientificName"].value_counts().head(10).index.tolist()
cmap = plt.colormaps["tab10"].resampled(len(species))
colors = [cmap(i) for i in range(len(species))]

for i, sp in enumerate(species):
    sub = df[df["scientificName"] == sp]
    ax.scatter(
        sub["decimalLongitude"], sub["decimalLatitude"],
        s=22, c=[colors[i]], edgecolor="white", linewidth=0.3, alpha=0.85,
        label=f"{sp} (n={len(sub)})", transform=ccrs.PlateCarree(), zorder=5,
    )

other = df[~df["scientificName"].isin(species)]
if len(other) > 0:
    ax.scatter(
        other["decimalLongitude"], other["decimalLatitude"],
        s=10, c="#888888", alpha=0.4, label=f"Otros (n={len(other)})",
        transform=ccrs.PlateCarree(), zorder=4,
    )

ax.set_title(
    "Registros de presencia de Anopheles en Guayana Francesa y Amapá (1902–2014)\n"
    "Fuente: Institut Pasteur de la Guyane — GBIF",
    fontsize=13, pad=14,
)
leg = ax.legend(loc="lower left", fontsize=8, frameon=True, framealpha=0.9, title="Especies", title_fontsize=9)
leg.get_frame().set_edgecolor("#cccccc")
out = "../data/guf/mapa_anopheles.png"
plt.savefig(out, dpi=150, bbox_inches="tight", facecolor="white")
print(f"Mapa guardado en: {out}")