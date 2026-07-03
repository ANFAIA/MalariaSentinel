"""Análisis del REACT dataset (Burkina Faso + Côte d'Ivoire)."""
import pandas as pd

REACT = "../data/react"

print("=" * 70)
print("REACT — IRD Burkina Faso + Côte d'Ivoire 2016-2018")
print("=" * 70)

events = pd.read_csv(f"{REACT}/event.txt", sep="\t", low_memory=False)
occ = pd.read_csv(f"{REACT}/occurrence.txt", sep="\t", low_memory=False)
emof = pd.read_csv(f"{REACT}/extendedmeasurementorfact.txt", sep="\t", low_memory=False)
mof = pd.read_csv(f"{REACT}/measurementorfacts.txt", sep="\t", low_memory=False)

print(f"\nEventos (sitios × noche):       {len(events):,}")
print(f"Ocurrencias (1 mosquito c/u):   {len(occ):,}")
print(f"Extended measurements (molecular + posición): {len(emof):,}")
print(f"Measurement or facts (variables ambientales):  {len(mof):,}")

print("\n--- Distribución por país ---")
print(events["country"].value_counts())

print("\n--- Rango temporal ---")
print(f"  Desde: {events['eventDate'].min()}")
print(f"  Hasta: {events['eventDate'].max()}")

print("\n--- Protocolo de muestreo ---")
print(events["samplingProtocol"].value_counts())

print("\n--- Especies identificadas (1 fila por mosquito) ---")
sp = occ["scientificName"].value_counts()
print(sp.head(15))

print("\n--- Total mosquitos por país (de occurrence) ---")
print(occ["countryCode"].value_counts())

print("\n--- ¿Cuántos mosquitos PCR-identificados vs morfológicos? ---")
print(occ["identificationReferences"].value_counts(dropna=False).head(10))
print(occ["nameAccordingTo"].value_counts(dropna=False).head(10))

print("\n--- Indoor vs outdoor (de extendedmeasurement) ---")
loc = emof[emof["measurementType"].str.contains("location|position|indoor|outdoor", case=False, na=False)]
print(loc["measurementType"].value_counts())
print(loc["measurementValue"].value_counts().head())

print("\n--- Tipos de mediciones moleculares ---")
mol = emof[emof["measurementType"].str.contains("Plasmodium|kdr|ace|Parity|mutation", case=False, na=False)]
print(mol["measurementType"].value_counts())

print("\n--- Variables ambientales disponibles ---")
print(mof["measurementType"].value_counts().head(20))

print("\n--- Aldeas únicas (locationID) ---")
n_ald = events["locality"].nunique()
print(f"  {n_ald} aldeas únicas")
print(events["locality"].unique()[:5], "...")

print("\n--- Coordenadas ---")
lat_min, lat_max = events["decimalLatitude"].min(), events["decimalLatitude"].max()
lon_min, lon_max = events["decimalLongitude"].min(), events["decimalLongitude"].max()
print(f"  Lat: {lat_min:.3f} a {lat_max:.3f}")
print(f"  Lon: {lon_min:.3f} a {lon_max:.3f}")