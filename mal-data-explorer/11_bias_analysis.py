"""Análisis cuantitativo de sesgos del dataset Anopheles GBIF."""
import pandas as pd
import numpy as np

OCC_PATH = "../data/guf/occurrence.txt"
df = pd.read_csv(OCC_PATH, sep="\t", low_memory=False)

df = df[(df["decimalLatitude"].between(-90, 90)) & (df["decimalLongitude"].between(-180, 180))]
df = df.dropna(subset=["decimalLatitude", "decimalLongitude"])

print("=" * 75)
print("ANÁLISIS DE SESGOS")
print("=" * 75)

print("\n1. SESGO TEMPORAL — Registros por año y década")
print("-" * 75)
df["decade"] = (df["year"] // 10) * 10
dec_counts = df.groupby("decade").size()
total = len(df)
print(dec_counts.to_string())
print(f"\nDécadas vacías (gaps): 1920s, 1930s?")
print(f"Densidad de muestreo desigual: 1947 tiene {df[df.year==1947].shape[0]} registros en un año")

y1947 = df[df.year == 1947].shape[0]
y_total_decada = df[(df.year >= 1940) & (df.year < 1960)].shape[0]
print(f"  → 1947 = {y1947} registros, representa {100*y1947/y_total_decada:.1f}% de la década 1940-1959")

print("\n2. SESGO GEOGRÁFICO — Distancias a la costa y zonas urbanas")
print("-" * 75)
cayenne_lat, cayenne_lon = 4.937, -52.326
df["dist_cayenne_km"] = np.sqrt(
    ((df["decimalLatitude"] - cayenne_lat) * 111) ** 2
    + ((df["decimalLongitude"] - cayenne_lon) * 111 * np.cos(np.radians(cayenne_lat))) ** 2
)

bins = [0, 25, 50, 100, 200, 500, 1000]
labels = ["<25 km", "25-50", "50-100", "100-200", "200-500", ">500 km"]
df["dist_bin"] = pd.cut(df["dist_cayenne_km"], bins=bins, labels=labels)
print("Distancia a Cayenne (capital, ~90% población costera):")
print(df["dist_bin"].value_counts().sort_index())
print(f"\n  → {100 * (df['dist_cayenne_km'] < 50).mean():.1f}% de registros a menos de 50 km de Cayenne")
print(f"  → {100 * (df['dist_cayenne_km'] > 200).mean():.1f}% a más de 200 km (interior, selva)")

print("\n3. SESGO POR INSTITUCIÓN RECOLECTORA")
print("-" * 75)
print(df["institutionCode"].value_counts())

print("\n4. SESGO POR PROTOCOLO DE MUESTREO")
print("-" * 75)
print(df["samplingProtocol"].value_counts())
print("\nNota: 'Human' = capturas de aterrizaje en humano (HLC, mide picadura real)")
print("      'Larvae capture' = recolección de larvas en agua (hábitats de cría)")
print("      'Light' = trampa de luz CDC (atrae hembras que buscan sangre)")
print("      'Mosquito Magnet' = trampa cebada con olor (Octenol)")

print("\n5. ESTADO DE DESARROLLO DEL MOSQUITO")
print("-" * 75)
print(df["lifeStage"].value_counts(dropna=False))
print("Adult = mosquito completo (vector real de malaria)")
print("Larvae = cría (indica presencia de hábitat reproductivo)")

print("\n6. ¿QUÉ ES LO QUE SE MUESTRA? Especie, año e institución")
print("-" * 75)
print("Cada registro = 1 espécimen preservado de Anopheles recolectado y ")
print("  morfológicamente identificado en algún sitio y año concreto.")
print()
print("NO es: registro de picadura con malaria, ni de caso humano, ni de ")
print("  encuesta epidemiológica. El dataset contiene el MOSQUITO, no la enfermedad.")
print()
print("Los métodos que capturan adultos hembra (Human, Light, Mosquito Magnet)")
print("  sí miden potencial de transmisión: HLC es el gold standard para medir")
print("  tasa de picadura en humano (biting rate).")

print("\n7. ¿DESDE CUÁNDO HAY DATOS FIABLES GEOLOCALIZADOS?")
print("-" * 75)
pre2000 = df[df.year < 2000]
post2000 = df[df.year >= 2000]
print(f"Pre-2000 (coordenadas a veces inferidas por GEONAME/localidad): {len(pre2000)} ({100*len(pre2000)/len(df):.1f}%)")
print(f"Post-2000 (coordenadas GPS precisas según el paper): {len(post2000)} ({100*len(post2000)/len(df):.1f}%)")
print()
print("Esto significa que ~una cuarta parte de los registros históricos")
print("(1934-1999) tienen coordenadas aproximadas (a nivel de poblado),")
print("mientras que los modernos son GPS preciso.")

print("\n8. SESGO DE ESPECIE: ¿se muestrean todas por igual?")
print("-" * 75)
print("Top 5 especies y su peso:")
top5 = df["scientificName"].value_counts().head(5)
print(top5)
print(f"\nLas 5 principales = {100*top5.sum()/len(df):.1f}% del total.")
print("Esto refleja abundancia real + esfuerzo de identificación,")
print("no significa que el resto no exista. *A. darlingi* es el vector")
print("principal de malaria y por tanto se prioriza su captura.")

print("\n9. ¿QUÉ INFORMACIÓN FALTANTE HAY?")
print("-" * 75)
print("Campos vacíos en TODO el dataset:")
for col in df.columns:
    pct = 100 * df[col].isna().mean()
    if pct == 100:
        print(f"  - {col}: 100% vacío (ningún dato)")
    elif pct > 50:
        print(f"  - {col}: {pct:.0f}% vacío")

print("\n10. ¿HAY SESGO TEMPORAL EN LAS ESPECIES?")
print("-" * 75)
print("Distribución temporal de las 3 especies principales:")
for sp in df["scientificName"].value_counts().head(3).index:
    sub = df[df["scientificName"] == sp]
    decades = sub.groupby("decade").size()
    print(f"\n  {sp}:")
    print(f"    Primer registro: {sub['year'].min()}")
    print(f"    Último registro: {sub['year'].max()}")
    print(f"    Décadas con presencia: {decades.to_dict()}")