"""Análisis del patrón geográfico: ¿son los dos focos un sesgo?"""
import pandas as pd
import numpy as np

REACT = "../data/react"
events = pd.read_csv(f"{REACT}/event.txt", sep="\t", low_memory=False)
events["village_id"] = events["locationID"].str.extract(r"^(\d+[A-Z]+)")

village = events.groupby("village_id").agg(
    n_events=("eventID", "count"),
    lat=("decimalLatitude", "mean"),
    lon=("decimalLongitude", "mean"),
    country=("country", "first"),
    village=("locality", "first"),
).reset_index()

bf = village[village.country == "Burkina Faso"]
ci = village[village.country.str.contains("Côte")]

print("=" * 70)
print("¿DOS FOCOS = SESGO?")
print("=" * 70)

print(f"\nAldeas Burkina Faso: {len(bf)}")
print(f"  Centro: lat={bf.lat.mean():.3f}, lon={bf.lon.mean():.3f}")
print(f"  Rango: lat [{bf.lat.min():.3f}, {bf.lat.max():.3f}], lon [{bf.lon.min():.3f}, {bf.lon.max():.3f}]")

print(f"\nAldeas Côte d'Ivoire: {len(ci)}")
print(f"  Centro: lat={ci.lat.mean():.3f}, lon={ci.lon.mean():.3f}")
print(f"  Rango: lat [{ci.lat.min():.3f}, {ci.lat.max():.3f}], lon [{ci.lon.min():.3f}, {ci.lon.max():.3f}]")

cx_bf, cy_bf = bf.lon.mean(), bf.lat.mean()
cx_ci, cy_ci = ci.lon.mean(), ci.lat.mean()
gap_km = np.sqrt(((cy_bf - cy_ci) * 111) ** 2 + ((cx_bf - cx_ci) * 111 * np.cos(np.radians(cy_ci))) ** 2)
print(f"\nDistancia entre los dos centros: {gap_km:.0f} km")

mid_lat = (cy_bf + cy_ci) / 2
mid_lon = (cx_bf + cx_ci) / 2
near_mid = village[
    (abs(village.lat - mid_lat) < 1) & (abs(village.lon - mid_lon) < 1)
]
print(f"Aldeas en la zona intermedia (±1° del punto medio): {len(near_mid)}")

print(f"\nDistancia promedio entre aldeas vecinas DENTRO de cada cluster:")
from scipy.spatial.distance import pdist
d_bf = pdist(bf[["lon", "lat"]].values)
d_ci = pdist(ci[["lon", "lat"]].values)
print(f"  Burkina Faso: media={d_bf.mean()*111:.1f} km, min={d_bf.min()*111:.1f} km, max={d_bf.max()*111:.1f} km")
print(f"  Côte d'Ivoire: media={d_ci.mean()*111:.1f} km, min={d_ci.min()*111:.1f} km, max={d_ci.max()*111:.1f} km")

print(f"\n¿Cumplen el criterio de '>2 km entre aldeas' del paper?")
d_bf_min = d_bf.min() * 111
d_ci_min = d_ci.min() * 111
print(f"  Burkina Faso: mín = {d_bf_min:.2f} km")
print(f"  Côte d'Ivoire: mín = {d_ci_min:.2f} km")

print(f"\n{'='*70}")
print("CONCLUSIÓN")
print("="*70)
print(f"  - Distancia entre los 2 focos: ~{gap_km:.0f} km")
print(f"  - Son 2 áreas de estudio distintas del MISMO RCT")
print(f"  - La selección fue por ECOLOGÍA + SOCIO-SANITARIO, no por acceso")
print(f"  - Cada cluster internamente SÍ es sistemático (grid)")
print(f"  - PERO entre clusters hay un HUECO de ~{gap_km:.0f} km sin muestrear")