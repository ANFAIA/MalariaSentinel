# Datasets, APIs y Arquitectura para Simulación Geoespacial de Hábitats de *Anopheles stephensi* — Capa de Cría y ABM
## Resumen
Este documento define la estrategia completa de datos geoespaciales, climatológicos y socioeconómicos necesarios para construir: **(1)** una capa de probabilidad de hábitat larvario de *Anopheles stephensi* (el vector invasivo urbano más prioritario), y **(2)** un Modelo Basado en Agentes (ABM) espacio-temporal que integre dicha capa como input dinámico. La arquitectura propuesta es completamente open-source, ejecutable en Python, e integra datos satelitales, hidrológicos, climáticos y de población humana.

***
## 1. Justificación de la Especie: ¿Por qué *Anopheles stephensi*?
*An. stephensi* es la prioridad número uno para el modelado prospectivo porque:[^1][^2][^3]

- **Es un vector urbano**: a diferencia de los vectores africanos tradicionales, se reproduce en **depósitos artificiales de agua** (cisternas, barriles, contenedores abandonados, tanques de agua de azoteas, bebederos de animales). Esto lo hace detectar y modelar con datos de urbanización, que son mucho más granulares que los hábitats rurales.
- **Está en expansión activa**: detectado en Djibouti en 2012, ya está presente en Etiopía, Sudán, Somalia, Kenia, Nigeria, Ghana y otros países en 2025.[^4][^3]
- **Sus variables de hábitat están bien caracterizadas** en estudios de idoneidad (MaxEnt, BRT, ensemble models).[^5][^6][^4]
- Los modelos de idoneidad a escala global proyectan su expansión potencial hacia Europa meridional (costas ibéricas y mediterráneas), Medio Oriente y Sudamérica.[^6][^1]

La misma arquitectura de datos es válida para *An. gambiae s.l.* y otros vectores; basta con cambiar los umbrales de las variables de hábitat.

***
## 2. Capas de Datos Geoespaciales para Detectar Zonas de Cría Potencial
### 2.1 Capa Hidrológica: Cuerpos de Agua, Ríos y Depresiones Topográficas
Esta es la capa más crítica. Se construye fusionando cuatro fuentes complementarias a distintas escalas espaciales:

#### A. JRC Global Surface Water (GSW) — Landsat 1984–2021
- **Qué es**: El dataset de referencia para superficie de agua global, generado por la Comisión Europea a partir de 4,7 millones de escenas Landsat.[^7][^8]
- **Resolución**: 30 m (1 pixel ≈ 30×30 m).
- **Capas clave**:
  - `occurrence`: % de tiempo que un pixel ha sido agua (1984–2021) → identifica agua permanente vs. estacional.
  - `seasonality`: número de meses al año detectado como agua.
  - `change`: expansión/contracción de la lámina de agua.
  - `YearlyHistory`: historial anual de clasificación (seasonal/permanent water).
- **Acceso Python (via Google Earth Engine)**:
  ```python
  import ee
  ee.Initialize()
  gsw = ee.Image('JRC/GSW1_4/GlobalSurfaceWater')
  occurrence = gsw.select('occurrence')
  # Filtrar pixeles con agua estacional (10-99% del tiempo):
  seasonal_water = occurrence.gt(10).And(occurrence.lt(100))
  ```
- **Relevancia para mosquitos**: Los hábitats estacionales (30–80% de ocurrencia) son los más productivos para *Anopheles*, ya que tienen menos depredadores acuáticos y temperaturas más cálidas.[^9][^10]

#### B. Copernicus Water Bodies — Sentinel-2, mensual global 300 m
- **Qué es**: Producto mensual de la Agencia Espacial Europea derivado de Sentinel-2, usando el índice MNDWI.[^11][^12]
- **Resolución**: 300 m (global) y 100 m (versión reciente), **actualización mensual**.
- **Acceso**: Copernicus Data Space Ecosystem API (OData), Sentinel Hub API con colección BYOC.[^13][^14]
- **Ventaja frente a JRC**: Es dinámico en tiempo real → permite actualizar la capa de hábitats mes a mes, fundamental para la componente temporal del ABM.
  ```python
  # Sentinel Hub Python SDK
  from sentinelhub import SentinelHubRequest, DataCollection, BBox, CRS, bbox_to_dimensions
  # Configurar usando collection ID de Water Bodies
  collection_id = "69577a6b-80e0-4507-8b99-57b5ef167d41"  # WB CLMS
  ```

#### C. NDWI Calculado de Sentinel-2 (10 m) — Para Detección de Agua Fina
Para zonas urbanas y pequeñas charcas no detectables a 30–300 m, se calcula el **Normalized Difference Water Index** desde bandas Sentinel-2 (resolución de 10 m):[^15][^16][^17]

\[ NDWI = \frac{B3_{Green} - B8_{NIR}}{B3_{Green} + B8_{NIR}} \]

Valores NDWI > 0 indican agua. En Google Earth Engine:
```javascript
// GEE JavaScript
var s2 = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
  .filterDate('2024-01-01', '2024-12-31')
  .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 10))
  .median();
var ndwi = s2.normalizedDifference(['B3', 'B8']).rename('NDWI');
var water_mask = ndwi.gt(0.1);  // umbral típico
```
En 2024, estudios con Sentinel-1 SAR (que penetra nubes) en GEE obtuvieron 96.1% de precisión en detección de hábitats de *Anopheles* con el **Sentinel-1 Water Index (SWI)**.[^18]

#### D. DEM Hidrológico + Acumulación de Flujo — Detección de Micro-Depresiones

Esta es la capa más innovadora y compleja. Las micro-depresiones del terreno (que acumulan agua de lluvia en charcas temporales) no son cuerpos de agua permanentes y no aparecen en ningún dataset óptico; solo se pueden modelar **hidrológicamente** a partir del DEM.[^19][^20]

**Datasets de DEM recomendados**:

| Dataset | Resolución | Características |
|---|---|---|
| **MERIT DEM** | 90 m global | Elimina errores de SRTM (stripe noise, bias, tree height); el mejor para hidrología plana[^21] |
| **HydroSHEDS DEM (v1)** | 3, 15, 30 arc-sec | Ya hidrológicamente condicionado; incluye dirección y acumulación de flujo pre-calculada[^22][^23] |
| **SRTM 30 m** | 30 m (60°N–56°S) | Base de NASA; funciona bien en zonas de relieve |
| **CopDEM / TanDEM-X** | 30 m global | Próxima base de HydroSHEDS v2; mayor precisión en terreno plano |
| **LiDAR local** | 1 m (cobertura limitada) | Mejor resolución para microtopografía urbana; disponible en USGS 3DEP para EE.UU. y portales europeos[^24] |

**Pipeline de análisis hidrológico con `pysheds` (Python)**:

`pysheds` es la librería Python open-source más adecuada para este propósito. El flujo de trabajo es:[^25][^26][^20]

```python
from pysheds.grid import Grid
import numpy as np
import rasterio

# 1. Cargar DEM
grid = Grid.from_raster('merit_dem_study_area.tif')
dem = grid.read_raster('merit_dem_study_area.tif')

# 2. Rellenar hoyos (pits)
pit_filled = grid.fill_pits(dem)

# 3. Detectar y rellenar depresiones (sinks)
#    IMPORTANTE: ANTES de rellenar, guardar máscara de depresiones
depressions = grid.detect_depressions(pit_filled)
# → "depressions" es la máscara de todas las micro-depresiones del terreno
# → son los potenciales hábitats larvarios de la lluvia

flooded_dem = grid.fill_depressions(pit_filled)

# 4. Resolver áreas planas
inflated_dem = grid.resolve_flats(flooded_dem)

# 5. Calcular dirección de flujo D8
dirmap = (64, 128, 1, 2, 4, 8, 16, 32)
fdir = grid.flowdir(inflated_dem, dirmap=dirmap)

# 6. Calcular acumulación de flujo
acc = grid.accumulation(fdir, dirmap=dirmap)
# → Píxeles de alta acumulación = ríos y zonas de drenaje convergente

# 7. Calcular Topographic Wetness Index (TWI)
# TWI = ln(a / tan(β)) donde a = área de captación, β = pendiente
slope = grid.cell_slopes(inflated_dem, fdir)
twi = np.log(acc / (np.tan(slope) + 1e-10))
# → TWI alto → zonas propensas a encharcamiento crónico
```

El **TWI** (Topographic Wetness Index) es uno de los predictores más robustos de presencia de hábitats larvarios de *Anopheles* en estudios entomológicos de campo. Combina la capacidad de captación del área con la pendiente local.[^27][^28]

**HydroSHEDS** ofrece las capas pre-computadas de dirección de flujo y acumulación de flujo a escala global, disponibles también en Google Earth Engine, lo que evita el procesamiento del DEM desde cero para estudios a gran escala.[^22][^23][^29][^30]
### 2.2 Capa Climática y Temporal
#### ERA5-Land (ECMWF/Copernicus) — Temperatura y Precipitación Horaria
- **Resolución**: 0.1° (~9 km) para ERA5-Land; 0.25° (~27 km) para ERA5 global.[^31][^32]
- **Cobertura temporal**: 1950–present (ERA5-Land desde 1950; ERA5 global desde 1940).[^32]
- **Variables clave para mosquitos**:
  - `2m_temperature` (T2m)
  - `total_precipitation` (TP)
  - `2m_dewpoint_temperature` → para calcular humedad relativa
  - `evaporation` → para modelar el secado de los hábitats larvarios
- **API Python**:
  ```python
  import cdsapi
  c = cdsapi.Client()  # requiere ~/.cdsapirc con API key de CDS
  c.retrieve('reanalysis-era5-land', {
      'variable': ['2m_temperature', 'total_precipitation',
                   '2m_dewpoint_temperature'],
      'year': '2024',
      'month': ['01', '02', ..., '12'],
      'day': [str(d).zfill(2) for d in range(1, 32)],
      'time': ['00:00', '06:00', '12:00', '18:00'],
      'format': 'netcdf',
      'area': [15, 35, -5, 55],  # Norte, Oeste, Sur, Este
  }, 'era5_land_2024.nc')
  ```
  La librería `cdsapi` (pip) gestiona la autenticación y la descarga directamente en Python.[^33][^34]

#### CHIRPS — Precipitación Diaria 0.05° (África, regiones tropicales)
- **Qué es**: Climate Hazards Group InfraRed Precipitation with Station data; resolución de ~5 km, diaria desde 1981.[^35][^36]
- **Ventaja sobre ERA5**: Mayor resolución espacial y mejor captura de eventos de lluvia convectivos locales (cruciales para la formación de charcas).
- **Acceso Python (descarga directa)**:
  ```python
  import xarray as xr
  chirps = xr.open_dataset('https://data.chc.ucsb.edu/products/CHIRPS-2.0/global_monthly/netcdf/chirps-v2.0.monthly.nc')
  # Recorte por área de interés (ej. Etiopía):
  rain = chirps['precip'].sel(longitude=slice(33,48), latitude=slice(3,15))
  ```

#### WorldClim v2 — Variables Bioclimáticas (BIO1–BIO19)
- **Qué es**: Variables climáticas históricas (1970–2000) a resolución de 30 arc-segundos (~1 km).[^37]
- **Uso específico**: Modelado de idoneidad de hábitat estático (MaxEnt, ENMeval) para *An. stephensi*. Los estudios identifican como variables más importantes: temperatura media del trimestre más húmedo (BIO8), precipitación del mes más seco (BIO14), isothermality (BIO3) y estacionalidad de precipitación (BIO15).[^5]
### 2.3 Capa de Vegetación (NDVI/EVI)
La vegetación (NDVI) es un predictor relevante por dos razones: (1) las plantas peridomésticas son fuente de néctar (azúcar) para los mosquitos adultos, y (2) la presencia de vegetación densa mantiene humedad y crea micro-hábitats sombreados.[^28][^37]

- **MODIS NDVI (MOD13A3)**: Resolución 1 km, mensual, disponible en GEE desde 2000.[^38]
- **Sentinel-2 NDVI**: Resolución 10 m, cada 5 días (dos satélites), sin coste en GEE/CDSE.
- **MAP EVI (Malaria Atlas Project)**: MODIS EVI gap-filled específicamente para malaria, disponible en GEE como `MODIS/MOD13A2` y en la colección MAP del Earth Engine Data Catalog.[^39][^38]

```python
# NDVI desde Sentinel-2 en GEE
ndvi = s2.normalizedDifference(['B8', 'B4']).rename('NDVI')
```
### 2.4 Capa de Uso del Suelo / Cobertura Terrestre (LULC)
El tipo de cobertura terrestre determina qué tipo de hábitats larvarios son plausibles:[^40][^37]

| Dataset | Resolución | Período | Acceso |
|---|---|---|---|
| **ESA WorldCover** | 10 m | 2020, 2021 | GEE: `ESA/WorldCover/v200`; descarga directa |
| **Copernicus LULC Global** | 100 m | 2015–2019 | GEE: `COPERNICUS/Landcover/100m/Proba-V-C3/Global` |
| **ESA CCI Land Cover** | 300 m | 1992–2020 anual | CDS API; usado en modelos de *An. stephensi*[^37] |
| **OpenStreetMap (OSM)** | Vector | Actualización continua | overpass-api + osmnx en Python |

**OSM para infraestructura urbana**: Los contenedores de agua artificiales (depósitos en azoteas, tanques, fuentes, albercas) no aparecen en datasets satelitales, pero sí en OSM como puntos o polígonos. Para *An. stephensi* esto es fundamental:[^41][^40]

```python
import osmnx as ox
# Descargar cuerpos de agua y elementos de agua artificial en Addis Abeba
tags = {"natural": ["water", "wetland", "spring"],
        "water": True,
        "man_made": ["reservoir", "water_tower", "water_tap"],
        "leisure": "swimming_pool"}
water_features = ox.features_from_place("Addis Ababa, Ethiopia", tags=tags)
```
### 2.5 Capa de Población Humana
La densidad de población humana determina:
1. La disponibilidad de hospedadores (densidad de fuentes de sangre).
2. La escala de riesgo epidemiológico.
3. La distribución de agua artificial (correlación con urbanización).[^37]

- **WorldPop**: Dataset de densidad de población a 100 m y 1 km; anual 2000–2020; API REST y STAC.[^42][^43][^44]
  ```python
  import requests
  # WorldPop REST API
  url = "https://api.worldpop.org/v1/wopr/pointestimate"
  r = requests.get(url, params={"iso3": "ETH", "year": 2020, "lat": 9.03, "lon": 38.74})
  ```
- **GPW (Gridded Population of the World)**: NASA/CIESIN, 1 km, 2000–2020.
- **Facebook High Resolution Settlement Layer (HRSL)**: Resolución de ~30 m; libre; detecta zonas habitadas con IA.
### 2.6 Capa de Luz Nocturna (Night Lights) — Proxy de Urbanización
La intensidad de luz nocturna es un predictor de urbanización y presencia de infraestructura con depósitos de agua:[^37]
- **VIIRS/DNB (Suomi NPP)**: Resolución 500 m, mensual; disponible en GEE como `NOAA/VIIRS/DNB/MONTHLY_V1/VCMSLCFG`.
- **DMSP-OLS Night Lights**: Histórico 1992–2013; útil para series temporales largas.

***
## 3. Tabla Maestra de Datasets y APIs
| Capa | Dataset | Resolución | Temporal | Acceso Python | Gratuito |
|---|---|---|---|---|---|
| Agua superficial histórica | JRC Global Surface Water v1.4 | 30 m | 1984–2021 mensual | `ee.Image('JRC/GSW1_4/GlobalSurfaceWater')` GEE [^8] | ✅ |
| Agua superficial actual | Copernicus Water Bodies v2 | 300 m | 2020–hoy mensual | Sentinel Hub API, CDS API [^11][^12] | ✅ |
| Agua fina (urbana) | Sentinel-2 NDWI | 10 m | ~5 días | GEE Python API, sentinelhub-py [^15][^16] | ✅ |
| DEM hidrológico global | MERIT DEM | 90 m | 2000 | Descarga directa tiles [^21] | ✅ |
| DEM condicionado + Flujo | HydroSHEDS v1 | 3–30 arc-sec | 2000 | hydrosheds.org download [^22][^23] | ✅ |
| Micro-depresiones | pysheds (cálculo sobre DEM) | == DEM input | estático | `pip install pysheds` [^26][^20] | ✅ |
| TWI | pysheds + DEM | == DEM input | estático | ídem | ✅ |
| Temperatura + Precipitación | ERA5-Land | ~9 km, horario | 1950–hoy | `pip install cdsapi` [^34][^32] | ✅ |
| Precipitación diaria fina | CHIRPS v2.0 | ~5 km, diaria | 1981–hoy | Descarga NetCDF + xarray [^35][^36] | ✅ |
| Variables bioclimáticas | WorldClim v2 | ~1 km | 1970–2000 | `rasterio` sobre archivos descargados [^37] | ✅ |
| Vegetación (NDVI/EVI) | MODIS MOD13 / Sentinel-2 | 250 m–10 m | 2000–hoy (MODIS); 5 días (S2) | GEE [^28][^38] | ✅ |
| Cobertura terrestre | ESA WorldCover 2021 | 10 m | 2020–2021 | GEE: `ESA/WorldCover/v200` [^37] | ✅ |
| Agua artificial + ríos | OpenStreetMap | Vector | Continuo | osmnx [^45] | ✅ |
| Densidad de población | WorldPop | 100 m–1 km | 2000–2020 anual | REST API, STAC API [^43][^44] | ✅ |
| Urbanización | VIIRS Night Lights | 500 m | 2012–hoy mensual | GEE [^37] | ✅ |
| Toolkit completo MAP | Malaria Atlas Project (MAP) | Varía | Varía | GEE publisher collection [^39] | ✅ |

***
## 4. Pipeline para Construir la Capa de Hábitat Larvario Potencial
La fusión de todas estas fuentes produce un **raster de probabilidad de hábitat larvario** (valor 0–1 por pixel). Este es el corazón del módulo de hábitat del ABM.
### 4.1 Arquitectura del Pipeline
```
INPUT LAYERS
    ├── JRC GSW occurrence raster (30m)
    ├── NDWI Sentinel-2 raster (10m)
    ├── DEM → pysheds → TWI raster (90m)
    ├── DEM → pysheds → Flow Accumulation raster (90m)
    ├── DEM → pysheds → Depression mask raster (90m)
    ├── ERA5-Land / CHIRPS precipitation (mensual/diario)
    ├── ERA5-Land temperature 2m (diario)
    ├── NDVI MODIS / Sentinel-2 (mensual)
    ├── ESA WorldCover LULC (10m)
    ├── WorldPop population density (100m)
    └── OSM water features (vector → rasterize)

PROCESSING
    ├── Reproyección y remuestreo a resolución común (ej. 100m, EPSG:4326)
    ├── Normalización 0-1 de cada capa
    ├── Aplicación de reglas biológicas de An. stephensi:
    │       - Temperatura óptima: 20–32°C → multiplicador continuo
    │       - Precipitación: umbral mínimo > 30 mm/mes
    │       - TWI > umbral → alta humedad topográfica
    │       - LULC: urbano/peri-urbano → presencia de contenedores artificiales
    │       - Population density: correlación positiva con contenedores artificiales
    ├── Combinación por weighted sum o Random Forest / MaxEnt
    └── Segmentación de hábitats discretos (clumping de pixeles contiguos)

OUTPUT
    └── habitat_probability_YYYYMM.tif  ← raster mensual actualizable
    └── habitat_patches_YYYYMM.gpkg    ← vector de parches individuales
```
### 4.2 Toolkit Existente: Earth Observation para Malaria
El **Zenodo Toolkit** de 2023 proporciona scripts completos en GEE + R para exactamente este flujo:[^46]
- Extrae variables ambientales de Landsat/Sentinel-2 y datos climáticos para cualquier zona de estudio.
- Implementa Random Forest para predecir distribuciones de mosquito.
- Incluye datos de campo de ejemplo y scripts GEE listos para usar.

El artículo de referencia sobre GEE para malaria en Malawi (2020) demuestra la viabilidad de construir modelos de idoneidad vectorial a **resolución de 30 m** usando solo datos abiertos de GEE.[^27][^28]

***
## 5. Variables Específicas para *An. stephensi* en el Modelo de Hábitat
Los estudios de MaxEnt y ensemble modeling para *An. stephensi* han identificado las variables más importantes:[^4][^47][^5][^6]
### Variables de Mayor Importancia (por estudios de suitability)
| Variable | Dataset Fuente | Importancia | Efecto |
|---|---|---|---|
| Altitud | HydroSHEDS / SRTM | ★★★★★ | Rango 0–2000 m optimal; disminuye en altitudes muy altas[^48] |
| Temperatura media trimestre más húmedo (BIO8) | WorldClim | ★★★★★ | Óptimo 20–30°C |
| Precipitación del mes más seco (BIO14) | WorldClim | ★★★★ | Humedad mínima necesaria |
| Estacionalidad de precipitación (BIO15) | WorldClim | ★★★★ | Predictor de presencia de agua temporal |
| Isothermality (BIO3) | WorldClim | ★★★ | Relacionado con estabilidad de temperatura |
| Densidad de población | WorldPop | ★★★★ | Proxy de contenedores artificiales + hospedadores[^37] |
| Uso del suelo (urbano/peri-urbano) | ESA CCI LULC | ★★★★ | Correlación directa con hábitats artificiales[^40] |
| Índice de vegetación (NDVI/EVI) | MODIS | ★★★ | Indicador de micro-clima y fuentes de azúcar |
| Luz nocturna | VIIRS | ★★★ | Proxy de infraestructura urbana[^37] |
| Red de carreteras | OpenStreetMap | ★★ | Proxy de urbanización |
| Distancia a ríos / agua | HydroRIVERS + JRC | ★★★ | Buffer de dispersión adulta |

El modelo ensemble más reciente (2025) para la Gran Región del Cuerno de África integra exactamente estas variables y obtiene AUC > 0.94.[^4][^49]

***
## 6. Arquitectura del ABM Espacio-Temporal Completo
### 6.1 Framework: Mesa-Geo (Python)
**Mesa-Geo** es la extensión GIS para **Mesa** (el framework ABM más popular en Python). Permite:[^50][^51]
- Importar capas raster y vectoriales directamente como el espacio del modelo.
- Agentes con posición geográfica real (coordenadas GPS).
- Vecindades basadas en distancia real (metros) o en grafo de adyacencia.
- Exportar resultados como GeoJSON/GeoTIFF en cada tick de simulación.
### 6.2 Estructura de Agentes
```python
# Esquema conceptual Mesa-Geo

class MosquitoAgent(mesa_geo.GeoAgent):
    """Agente mosquito individual"""
    def __init__(self, unique_id, model, geometry, crs):
        super().__init__(unique_id, model, geometry, crs)
        # Estado biológico
        self.stage = "adult"  # egg | larva1 | larva2 | larva3 | larva4 | pupa | adult
        self.age_days = 0
        self.sex = random.choice(["male", "female"])
        self.status = "susceptible"  # susceptible | exposed | infectious
        self.eip_progress = 0.0  # 0.0 → 1.0 (progreso del EIP)
        self.gonotrophic_cycle = 0
        self.blood_fed = False
        self.sugar_energy = 1.0  # nivel de energía (0–1)
        self.gravid = False  # lista para poner huevos
        # Genética
        self.insecticide_resistance = np.random.beta(...)  # frecuencia alélica kdr
        # Localización
        self.habitat_patch_id = None  # ID del parche de cría de origen
        self.flight_range_km = 1.5    # dispersión normal

    def step(self):
        env = self.model.get_environment(self.pos)  # T, HR, lluvia
        self._age(env['temperature'])
        if self.sex == "female" and self.stage == "adult":
            self._host_seeking(env)
            self._update_eip(env['temperature'])
            if self.gravid:
                self._oviposit()
        self._dispersal(env)
        self._mortality(env)

class HabitatPatch(mesa_geo.GeoAgent):
    """Hábitat larvario — puede ser charca, río, contenedor artificial"""
    def __init__(self, unique_id, model, geometry, crs, hab_type):
        super().__init__(unique_id, model, geometry, crs)
        self.hab_type = hab_type  # "temporary_pool" | "river_edge" | "container" | "depression"
        self.water_volume_m3 = 0.0
        self.water_temp_c = 20.0
        self.larval_density = 0.0  # larvae/m²
        self.carrying_capacity = self._calc_K()
        self.active = False  # ¿tiene agua ahora mismo?

    def step(self):
        # Actualizar volumen de agua según precipitación y evapotranspiración
        rain = self.model.climate_engine.get_rain(self.pos, self.model.current_date)
        evapo = self.model.climate_engine.get_evaporation(self.pos, self.model.current_date)
        self.water_volume_m3 += (rain - evapo) * self.geometry.area
        self.active = self.water_volume_m3 > 0
        self.water_temp_c = self.model.climate_engine.get_water_temp(self.pos)
        # Dinámica larval simplificada (si se opta por ABM puro)
        self._larval_development()
```
### 6.3 Módulos del Modelo
```
AnophelesABM
    ├── GeoSpace (Mesa-Geo)
    │       ├── habitat_layer: raster de probabilidad de hábitat (actualizado mensualmente)
    │       ├── population_layer: raster WorldPop
    │       └── patches: lista de HabitatPatch activos
    │
    ├── ClimateEngine
    │       ├── load_era5(date_range, bbox)  → T2m, precipitation, humidity
    │       ├── load_chirps(date_range, bbox) → precipitation alta resolución
    │       ├── interpolate_to_grid(resolution=0.001°) → xarray.Dataset
    │       └── get_EIP(temperature) → días (modelo lineal de grado-día)
    │
    ├── HabitatEngine
    │       ├── load_jrc_gsw(bbox)            → agua permanente/estacional
    │       ├── load_ndwi(date, bbox)          → agua actual Sentinel-2
    │       ├── load_twi(bbox)                 → topographic wetness index
    │       ├── load_depression_mask(bbox)     → micro-depresiones del DEM
    │       ├── load_osm_water(bbox)           → agua OSM
    │       ├── compute_habitat_probability()  → raster fusionado 0–1
    │       └── activate_patches(rain, temp)  → lista de parches activos en el tick
    │
    ├── MosquitoPopulation
    │       ├── spawn_eggs(patch, n_eggs)
    │       ├── develop_larvae(temperature)    → tasas dependientes de T
    │       ├── adult_dispersal()              → vuelo local + migración eólica
    │       └── swarm_mating()
    │
    ├── EpidemiologyModule (opcional)
    │       ├── human_population(WorldPop)
    │       ├── plasmodium_infection(mosquito, human)
    │       └── eip_tracking(mosquito)
    │
    └── OutputEngine
            ├── mosquito_density_raster(tick) → GeoTIFF
            ├── habitat_status_raster(tick)   → GeoTIFF
            └── time_series_csv(metrics)      → pandas DataFrame
```
### 6.4 Temporalidad del ABM
El ABM opera en **ticks diarios** o sub-diarios (6h para capturar el ciclo circadiano de picadura), con actualizaciones de:

| Módulo | Frecuencia de actualización |
|---|---|
| Temperatura del aire (ERA5) | 6h o diaria |
| Precipitación (CHIRPS/ERA5) | Diaria |
| Estado de los hábitats (agua activa) | Diaria |
| Ciclo gonotrófico de la hembra | 2–4 días |
| Duración larvaria completa | 6–14 días (dependiendo de T) |
| Período de incubación extrínseco (EIP) | 10–14 días a 25°C |
| Actualización de la capa NDWI | Mensual (nueva imagen Sentinel-2) |
| Actualización de la capa de población | Anual |
### 6.5 Dispersión: Modelo de Dos Componentes
La dispersión espacial de los adultos se implementa como suma de dos componentes:[^26][^20]

1. **Dispersión local (Gaussiana truncada)**: 95% de los individuos no se alejan más de 2 km de su hábitat de origen. Se implementa como movimiento aleatorio ponderado por la calidad del hábitat vecino.

2. **Migración eólica de largo alcance**: Con probabilidad baja (1–5% por temporada), un agente puede ser incorporado en un vector de viento a alta altitud. El modelo usa los datos de viento de ERA5 (`u_component_of_wind`, `v_component_of_wind`) a ~850 hPa para calcular dirección y distancia de transporte.[^31][^52]

***
## 7. Hoja de Ruta de Implementación
### Fase 1 — Capa de Hábitats (Semanas 1–4)
1. Definir la región de interés (bounding box).
2. Descargar y procesar DEM MERIT (90 m) con `pysheds` → TWI + máscara de depresiones.
3. Extraer JRC GSW occurrence para el área → cuerpos de agua históricos.
4. Descargar ERA5-Land (temperatura y precipitación) con `cdsapi` para al menos 2 años.
5. Descargar WorldPop para el área.
6. Descargar ESA WorldCover (uso del suelo).
7. Extraer features de agua de OSM con `osmnx`.
8. Fusionar todas las capas en un raster común (GeoTIFF, 100 m, EPSG:4326).
9. Calcular el raster de probabilidad de hábitat.
10. Segmentar en parches discretos (usando `rasterio` + `shapely` + `geopandas`).
### Fase 2 — ABM Base (Semanas 5–10)
11. Implementar `HabitatPatch` y `MosquitoAgent` en Mesa-Geo.
12. Conectar el `ClimateEngine` con ERA5/CHIRPS vía xarray.
13. Implementar ciclo de vida completo con tasas temperatura-dependientes.
14. Validar contra datos entomológicos de campo (densidad de adultos, prevalencia).
### Fase 3 — Integración Temporal y Dispersión (Semanas 11–16)
15. Activar/desactivar hábitats dinámicamente según precipitación diaria.
16. Implementar los dos componentes de dispersión.
17. Añadir el módulo epidemiológico (EIP + transmisión humana).
18. Implementar análisis de sensibilidad de parámetros.
### Fase 4 — Validación y Escenarios (Semanas 17–20)
19. Calibrar contra datos de campo de Addis Abeba / Djibouti para *An. stephensi*.
20. Correr escenarios de cambio climático (ERA5 + SSP2.6, SSP4.5, SSP8.5).
21. Correr escenarios de control (gene drive, ITNs, larvicidas) usando el módulo de control.

***
## 8. Recursos de Código Existentes
| Recurso | URL / Fuente | Contenido |
|---|---|---|
| Zenodo Malaria EO Toolkit | zenodo.org/records/7696722 [^46] | GEE + R scripts para predicción de distribución de mosquito con RF |
| pysheds GitHub | github.com/pysheds/pysheds [^26] | Análisis hidrológico DEM en Python |
| ERA5 Python Tutorial | github.com/joaohenry23/Download_ERA5_with_python [^33] | Scripts CDS API Python |
| CHIRPS xarray | stackoverflow.com (solución con xarray) [^36] | Descarga y clip de CHIRPS en Python |
| Sentinel-2 NDWI Python | github.com/ncortim/s2-ndwi [^15] | Cálculo NDWI desde SAFE directory |
| Mesa-Geo | github.com/projectmesa/mesa-geo [^51] | GIS extension para Mesa ABM |
| EMOD malaria | github.com/EMOD-Hub/EMOD [^53] | ABM completo de malaria (IDM/Gates) |
| JRC GSW GEE | developers.google.com/earth-engine/datasets/catalog/JRC_GSW1_4_GlobalSurfaceWater [^8] | Surface water GEE dataset |
| HydroSHEDS downloads | hydrosheds.org/hydrosheds-core-downloads [^22] | DEM, flow direction, flow accumulation |
| WorldPop API | worldpop.org/sdi/introapi [^44] | REST API población |
| MAP GEE catalog | developers.google.com/earth-engine/datasets/publisher/malariaatlasproject [^39] | Malaria Atlas datasets en GEE |

***
## 9. Consideraciones de Escala y Precisión
Para la detección de **micro-depresiones** (charcos de <1 m de diámetro, cruciales en entornos urbanos con *An. stephensi*), el MERIT DEM a 90 m y el SRTM a 30 m son **insuficientes**. Las opciones son:[^24][^54]

- **LiDAR a 1 m**: Disponible en EE.UU. (USGS 3DEP), algunos países europeos y Escandinavia. Para África tropical, la cobertura es muy limitada.
- **TanDEM-X a 12 m** (DLR): Resolución de 12 m; cubre todo el globo; acceso via solicitud científica gratuita. Es la mejor opción disponible hasta la llegada de HydroSHEDS v2.
- **Drones UAV (DJI/senseFly)**: Para áreas de estudio pequeñas (<10 km²), un vuelo UAV genera un DTM a 5–10 cm de resolución. Es la metodología estándar en estudios de campo de larval source management (LSM).

El trabajo de Campbell (2026) en Florida demuestra que datos LiDAR a 1 m permiten identificar microtopographic depressions que predicen la producción de mosquitos con precisión sin precedentes, y su dashboard open-source puede servir como referencia metodológica.[^24]

---

## References

1. [Future global distribution and climatic suitability of Anopheles ...](https://www.nature.com/articles/s41598-025-07653-8) - The establishment and spread of An. stephensi in Africa are likely influenced by a complex interplay...

2. [The origin, invasion history and resistance architecture of ...](https://pubmed.ncbi.nlm.nih.gov/40196515/) - por TPW Dennis · 2025 · Mencionado por 6 — The invasion of Africa by the Asian urban malaria vector,...

3. [A new malaria mosquito is causing outbreaks in African ...](https://www.gavi.org/vaccineswork/new-malaria-mosquito-causing-outbreaks-african-cites-heres-where-it-came) - Anopheles stephensi is an invasive urban-dwelling species of mosquito capable of transmitting two hi...

4. [Predicting environmental suitability and future spread range of An. stephensi in the Greater Horn of Africa using remote sensing and ensemble modeling](https://pmc.ncbi.nlm.nih.gov/articles/PMC12948167/) - Malaria, a life-threatening disease, remains a major global health challenge, particularly in Africa...

5. [Table 1. List of environmental variables used in Anopheles stephensi distribution modeling, after multicollinearity testing.](https://pmc.ncbi.nlm.nih.gov/articles/PMC12991239/table/pntd.0014054.t001/) - The invasive mosquito species Anopheles stephensi plays a critical role in malaria transmission, par...

6. [Future global distribution and climatic suitability of Anopheles ...](https://pmc.ncbi.nlm.nih.gov/articles/PMC12215484/) - Anopheles stephensi, an urban malaria vector, is expanding into new regions and poses a growing glob...

7. [Global Surface Water Explorer - JRC Data Catalogue](https://data.jrc.ec.europa.eu/collection/id-0084)

8. [JRC Global Surface Water Mapping Layers, v1.4](https://developers.google.com/earth-engine/datasets/catalog/JRC_GSW1_4_GlobalSurfaceWater) - This dataset maps the location and temporal distribution of surface water globally from 1984 to 2021...

9. [Anopheles larval species composition and characterization of breeding habitats in two localities in the Ghibe River Basin, southwestern Ethiopia - PubMed](https://pubmed.ncbi.nlm.nih.gov/32046734/) - Different species of Anopheles larvae were identified including An. gambiae s.l., the main malaria v...

10. [Water quality and immatures of the M and S forms of Anopheles gambiae s.s. and An. arabiensis in a Malian village](https://pmc.ncbi.nlm.nih.gov/articles/PMC1508151/) - The associations between the immatures of Anopheles gambiae s.s. (Diptera: Culicidae), its M and S f...

11. [Water Bodies 2020-present (raster 300 m), global, monthly – version 2](https://land.copernicus.eu/api/en/products/water-bodies/water-bodies-global-v2-0-300m) - Detects the areas covered by inland water providing the maximum and the minimum extent of the water ...

12. [Water Bodies 2020-present (raster 300 m), global, monthly – version 2](https://land.copernicus.eu/en/products/water-bodies/water-bodies-global-v2-0-300m) - Detects the areas covered by inland water providing the maximum and the minimum extent of the water ...

13. [Water Bodies - Documentation](https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/clms/bio-geophysical-parameters/water-bodies/water-bodies.html)

14. [On this page](https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/clms/bio-geophysical-parameters/water-bodies/water-bodies/wb_global_100m_monthly_v1.html)

15. [GitHub - ncortim/s2-ndwi: This repository contains Python code for calculating the Normalized Difference Water Index (NDWI) from Sentinel-2 Level 2A imagery using GDAL. The script reads the Green and Near Infrared (NIR) bands from Sentinel-2 data, computes NDWI, and outputs the result as a Cloud Optimized GeoTIFF (COG).](https://github.com/ncortim/s2-ndwi) - This repository contains Python code for calculating the Normalized Difference Water Index (NDWI) fr...

16. [How to Calculate NDWI in Google Earth Engine | Step-by-Step ...](https://www.youtube.com/watch?v=aIfNeI-LZlk) - ndwi helps us detect water bodies from satellite images and today it'll show you how to calculate it...

17. [NDWI Analysis Using Sentinel-2 in Google Earth Engine](https://medium.com/@defaniarman/ndwi-analysis-using-sentinel-2-in-google-earth-engine-08814c1d0b93) - “Analyzing Water Bodies with Sentinel-2: A Step-by-Step Guide to NDWI in Google Earth Engine”

18. [Identification of Aquatic Habitats of Anopheles Mosquito Using Time-series Analysis of Sentinel-1 data through Google Earth Engine](https://isprs-archives.copernicus.org/articles/XLVIII-3-W3-2024/63/2024/)

19. [Application of accuracy improvement algorithms for ...](https://pdfs.semanticscholar.org/3ac5/0c6a50f9513a57fa603662ebc7388ebaa0ca.pdf) - by S Nagabathula · 2024 · Cited by 2 — The Fill-DEM algorithm is proposed by Jenson and Domingue (19...

20. [Using PySheds Python Library for Advanced GIS Watershed Modeling](https://www.youtube.com/watch?v=Q7qLS8MpevM) - Watershed modeling is critical for hydrologists, environmental managers, flood risk assessors, and w...

21. [MERIT DEM Download Guide & Data Notes | DEM & Elevation Data | GeoDataViewer](https://www.geodataviewer.com/datasets/dem/merit-dem/) - MERIT DEM is a 90-meter global DEM that removes major error components from SRTM3 v2.1 including str...

22. [Download HydroSHEDS Core Products](https://www.hydrosheds.org/hydrosheds-core-downloads) - This page provides data downloads for HydroSHEDS core raster data products.

23. [HydroSHEDS Core layers (version 1)](https://www.hydrosheds.org/products/hydrosheds) - Gridded hydrography from elevation data

24. [A Remote Sensing Technology Tool for Precision Mosquito Control](https://southernipm.org/2026/05/18/a-remote-sensing-technology-tool-for-precision-mosquito-control/) - Dr. Lindsay Campbell from the University of Florida received the Bright Idea award for her project "...

25. [Watershed analysis with pysheds](https://pythongis.org/part3/chapter-12/nb/00-watershed-analysis-with-pysheds.html) - In this case study we will cover how to extract watersheds and perform some example analyses using t...

26. [pysheds/pysheds: Simple and fast watershed delineation in python](https://github.com/pysheds/pysheds) - Features · flowdir : Generate a flow direction grid from a given digital elevation dataset. · catchm...

27. [Mapping malaria vector suitability in Malawi with Google Earth ...](https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0235697) - by AN Frake · 2020 · Cited by 34 — Leveraging Google Earth Engine, a raster-based mosquito suitabili...

28. [Leveraging big data for public health: Mapping malaria vector suitability in Malawi with Google Earth Engine](https://pmc.ncbi.nlm.nih.gov/articles/PMC7402481/) - In an era of big data, the availability of satellite-derived global climate, terrain, and land cover...

29. [WWF HydroSHEDS Hydrologically Conditioned DEM, 15 Arc-Seconds](https://developers.google.com/earth-engine/datasets/catalog/WWF_HydroSHEDS_15CONDEM?hl=hi) - HydroSHEDS is a mapping product that provides hydrographic information for regional and global-scale...

30. [WWF HydroSHEDS Hydrologically Conditioned DEM, 15 ...](https://developers.google.com/earth-engine/datasets/catalog/WWF_HydroSHEDS_15CONDEM) - HydroSHEDS is a mapping product that provides hydrographic information for regional and global-scale...

31. [Dataset: era5 — Mosquito Alert Data Portal](https://labs.mosquitoalert.com/metadata_public_portal/notebooks/era5h.html) - Here we provide an example for how to download a time-chunked dataset for a given set of era5-variab...

32. [Complete ERA5 global atmospheric reanalysis - Climate Data Store](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-complete?tab=d_download) - ERA5 is the fifth generation ECMWF atmospheric reanalysis of the global climate covering the period ...

33. [Tutorial for download ERA5 data using python.](https://github.com/joaohenry23/Download_ERA5_with_python) - Tutorial for download ERA5 data using python. Contribute to joaohenry23/Download_ERA5_with_python de...

34. [cdsapi](https://pypi.org/project/cdsapi/) - Climate Data Store API

35. [GitHub - ankwasa/extract-CHIRPS-rainfall-: these scripts download and extract rainfall data in a timeseries format from CHIRPS raster data for any catchment in Africa](https://github.com/ankwasa/extract-CHIRPS-rainfall-) - these scripts download and extract rainfall data in a timeseries format from CHIRPS raster data for ...

36. [Downloading Gridded CHIRPS data sets using python](https://stackoverflow.com/questions/67163212/downloading-gridded-chirps-data-sets-using-python) - I am working with Satellite Gridded dataset from CHIRPS, Here is the link to the dataset: https://da...

37. [Table 1.](https://pmc.ncbi.nlm.nih.gov/articles/PMC12948167/table/T1/) - Malaria, a life-threatening disease, remains a major global health challenge, particularly in Africa...

38. [The Malaria Atlas Project | Earth Engine Data Catalog](https://developers.google.com/earth-engine/datasets/publisher/malariaatlasproject?hl=id) - The Malaria Atlas Project (MAP) aims to disseminate free, accurate and up-to-date geographical infor...

39. [The Malaria Atlas Project | Earth Engine Data Catalog](https://developers.google.com/earth-engine/datasets/publisher/malariaatlasproject) - The Malaria Atlas Project (MAP) aims to disseminate free, accurate and up-to-date geographical infor...

40. [Mapping Potential <i>Anopheles stephensi</i> Habitats for Implementing “Seek and Destroy” Malaria Larval Source Management in Kwale County, Kenya](https://www.sciencepublishinggroup.com/article/10.11648/j.aje.20230704.11) - We will reveal specific locations of potential habitats of <i>Anopheles stephensi</i>, a new and inv...

41. [Overhead tank is the potential breeding habitat of Anopheles stephensi in an urban transmission setting of Chennai, India](https://eprints.whiterose.ac.uk/id/eprint/169170/1/s12936_016_1321_7.pdf)

42. [Open access to global development data - WorldPop](https://www.worldpop.org/datacatalog/) - WorldPop develops peer-reviewed research and methods for the construction of open and high-resolutio...

43. [Population Density](https://hub.worldpop.org/project/categories?id=18) - Worldpop. Population Density

44. [introapi - WorldPop](https://www.worldpop.org/sdi/introapi/) - WorldPop API Basics Advanced Data API Queries REST API rate-limits The WorldPop Program Application ...

45. [Fetching OSM Data via Overpass API — Geospatial ETL](https://www.geospatial-etl.com/mastering-geospatial-data-ingestion-in-python/fetching-osm-data-via-overpass-api/) - Query OpenStreetMap via Overpass API in Python — Overpass QL syntax, bounding box scoping, retry log...

46. [Earth observation for malaria modelling: a practical toolkit for satellite-based prediction of mosquito distributions using Google Earth Engine and R](https://zenodo.org/records/7696722) - This toolkit user-guide provides a user-friendly introduction to implementing the satellite-based an...

47. [Predicting the environmental suitability for Anopheles stephensi ...](https://pure.ug.edu.gh/en/publications/predicting-the-environmental-suitability-for-anopheles-stephensi-/) - We explored the MaxEnt ecological modelling method to forecast An. stephensi's potential hotspots an...

48. [Suitable ecological niches of invasive malaria vector under present ...](https://pubmed.ncbi.nlm.nih.gov/41838734/) - Despite advancements in malaria control, An. stephensi remains a significant threat in Iran, particu...

49. [Predicting environmental suitability and future spread range of An ...](https://www.sciencedirect.com/science/article/pii/S1569843225006739) - The model integrates meteorological, environmental, geophysical, and socioeconomic variables, as wel...

50. [Mesa is an open-source Python library for agent-based ...](https://github.com/mesa/mesa) - Mesa is an open-source Python library for agent-based modeling, ideal for simulating complex systems...

51. [Mesa-Geo: A GIS Extension for the Mesa Agent-Based Modeling Framework in Python](https://dl.acm.org/doi/10.1145/3557989.3566157) - Mesa is an open-source agent-based modeling (ABM) framework implemented in the Python programming la...

52. [Wind-assisted high-altitude dispersal of mosquitoes and other ...](https://pmc.ncbi.nlm.nih.gov/articles/PMC10337859/) - por HE Atieli · 2023 · Mencionado por 46 — These data suggest that windborne dispersal activity of m...

53. [emodpy-malaria - EMOD-Hub](https://emod.idmod.org/emodpy-malaria/) - emodpy-malaria is the primary interface for working with EMOD. It provides the tools to configure th...

54. [Exploring LiDAR data for mapping the micro-topography and tidal ...](https://www.academia.edu/13570883/Exploring_LiDAR_data_for_mapping_the_micro_topography_and_tidal_hydro_dynamics_of_mangrove_systems_An_example_from_southeast_Queensland_Australia) - The aim was to explore the use of Light Detection and Ranging (LiDAR) data to map the micro-topograp...

