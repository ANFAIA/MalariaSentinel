"""Análisis de metodología y sesgos del dataset Anopheles GBIF."""
import pandas as pd

OCC_PATH = "../data/guf/occurrence.txt"

df = pd.read_csv(OCC_PATH, sep="\t", low_memory=False)
print(f"Total registros: {len(df)}")
print(f"Columnas: {list(df.columns)}\n")

print("=" * 70)
print("1. basisOfRecord (tipo de registro)")
print("=" * 70)
print(df["basisOfRecord"].value_counts(dropna=False))

print("\n" + "=" * 70)
print("2. samplingProtocol (método de muestreo)")
print("=" * 70)
print(df["samplingProtocol"].value_counts(dropna=False).head(20))

print("\n" + "=" * 70)
print("3. lifeStage (estado de vida del mosquito)")
print("=" * 70)
print(df["lifeStage"].value_counts(dropna=False))

print("\n" + "=" * 70)
print("4. sex (sexo)")
print("=" * 70)
print(df["sex"].value_counts(dropna=False))

print("\n" + "=" * 70)
print("5. institutionCode (institución que custodia el espécimen)")
print("=" * 70)
print(df["institutionCode"].value_counts(dropna=False).head(15))

print("\n" + "=" * 70)
print("6. recordedBy (quién recolectó) - top 15")
print("=" * 70)
print(df["recordedBy"].value_counts(dropna=False).head(15))

print("\n" + "=" * 70)
print("7. Distribución temporal de registros (por año)")
print("=" * 70)
year_counts = df["year"].value_counts().sort_index()
print(year_counts.to_string())

print("\n" + "=" * 70)
print("8. Distribución por mes (1-12)")
print("=" * 70)
print(df["month"].value_counts().sort_index())

print("\n" + "=" * 70)
print("9. georeferenceSources (cómo se obtuvieron las coordenadas)")
print("=" * 70)
print(df["georeferenceSources"].value_counts(dropna=False).head(20))

print("\n" + "=" * 70)
print("10. coordinatePrecision (precisión coord.)")
print("=" * 70)
print(df["coordinatePrecision"].value_counts(dropna=False).head(10))

print("\n" + "=" * 70)
print("11. habitat")
print("=" * 70)
print(df["habitat"].value_counts(dropna=False).head(15))

print("\n" + "=" * 70)
print("12. eventRemarks (notas) - muestra aleatoria")
print("=" * 70)
_remarks = df["eventRemarks"].dropna() if "eventRemarks" in df.columns else None
if _remarks is not None and len(_remarks) > 0:
    print(_remarks.sample(min(10, len(_remarks)), random_state=1).to_string())
else:
    print("(no hay datos en eventRemarks)")

print("\n" + "=" * 70)
print("13. waterBody (cuerpo de agua)")
print("=" * 70)
print(df["waterBody"].value_counts(dropna=False).head(10))

print("\n" + "=" * 70)
print("14. typeStatus (tipo de espécimen)")
print("=" * 70)
print(df["typeStatus"].value_counts(dropna=False))

print("\n" + "=" * 70)
print("15. geodeticDatum (datum geodésico)")
print("=" * 70)
print(df["geodeticDatum"].value_counts(dropna=False).head(10))