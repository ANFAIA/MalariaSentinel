# Datasets, APIs y Arquitectura para Simulación Geoespacial de Hábitats de *Anopheles stephensi* — Capa de Cría y ABM
**Source:** Perplexity Investigation (2026-07-04)
**Language:** Spanish
**File:** papers/perplexity-investigations/Datasets, APIs y Arquitectura para Simulación Geoespacial de Hábitats de Anopheles stephensi — Capa de Cría y ABM.md

---

## Resumen Ejecutivo

Este documento define la estrategia completa de datos geoespaciales, climatológicos y socioeconómicos para construir: (1) una capa de probabilidad de hábitat larvario de *Anopheles stephensi* (el vector invasivo urbano más prioritario), y (2) un Modelo Basado en Agentes (ABM) espacio-temporal que integre dicha capa como input dinámico. La arquitectura propuesta es completamente open-source, ejecutable en Python, e integra datos satelitales, hidrológicos, climáticos y de población humana.

*An. stephensi* es la prioridad número uno por su carácter urbano (reproducción en depósitos artificiales), expansión activa desde 2012 (Djibouti → Etiopía, Sudán, Kenia, Nigeria, Ghana), y variables de hábitat bien caracterizadas en estudios de idoneidad con AUC >0.94. El pipeline fusiona 10+ capas de datos (JRC GSW, Copernicus Water Bodies, Sentinel-2 NDWI, MERIT DEM + pysheds → TWI/depresiones, ERA5-Land, CHIRPS, WorldPop, ESA WorldCover, OSM, VIIRS) en un raster de probabilidad de hábitat 0–1 actualizable mensualmente. El ABM se implementa en **Mesa-Geo** (Python) con agentes `MosquitoAgent` y `HabitatPatch`, motores separados de clima, hábitat y dispersión (componente local Gaussiano + migración eólica con ERA5), y una hoja de ruta de implementación de 20 semanas en 4 fases. La tabla maestra de datasets (Sección 3) cataloga 14 fuentes con resolución, temporalidad y método de acceso Python.

## Contenido Principal

## 1. Justificación de la Especie: ¿Por qué *Anopheles stephensi*?

*An. stephensi* es la prioridad número uno para modelado prospectivo porque:
- **Vector urbano**: se reproduce en depósitos artificiales de agua (cisternas, barriles, contenedores, tanques de azotea, bebederos) → detectable con datos de urbanización granulares
- **Expansión activa**: detectado en Djibouti en 2012, presente en Etiopía, Sudán, Somalia, Kenia, Nigeria, Ghana (2025)
- **Variables de hábitat bien caracterizadas**: estudios MaxEnt, BRT y ensemble models
- **Proyección de expansión**: modelos globales proyectan hacia Europa meridional, Medio Oriente y Sudamérica

La misma arquitectura es válida para *An. gambiae s.l.* ajustando umbrales.

---

## 2. Capas de Datos Geoespaciales para Detectar Zonas de Cría Potencial

### 2.1 Capa Hidrológica: Cuerpos de Agua, Ríos y Depresiones Topográficas

#### A. JRC Global Surface Water (GSW) — Landsat 1984–2021
Dataset de referencia global (Comisión Europea, 4.7 millones de escenas Landsat). Resolución 30 m. Capas clave: `occurrence` (% tiempo como agua), `seasonality` (meses/año), `change` (expansión/contracción), `YearlyHistory`. Acceso Python via Google Earth Engine:
```python
gsw = ee.Image('JRC/GSW1_4/GlobalSurfaceWater')
seasonal_water = gsw.select('occurrence').gt(10).And(gsw.select('occurrence').lt(100))
```
Los hábitats estacionales (30–80% ocurrencia) son los más productivos (menos depredadores, temperaturas más cálidas).

#### B. Copernicus Water Bodies — Sentinel-2, mensual global 300 m
Producto mensual derivado de Sentinel-2 (índice MNDWI). Resolución 300 m (100 m en versión reciente). Ventaja: dinámico en tiempo real → actualización mensual de hábitats, fundamental para ABM. Acceso via Sentinel Hub API (OData).

#### C. NDWI Calculado de Sentinel-2 (10 m) — Detección de Agua Fina
\[ NDWI = \frac{B3_{Green} - B8_{NIR}}{B3_{Green} + B8_{NIR}} \]
Valores >0 indican agua. Para zonas urbanas con charcas pequeñas no detectables a 30–300 m. Estudios 2024 con Sentinel-1 SAR obtuvieron 96.1% de precisión con Sentinel-1 Water Index (SWI).

#### D. DEM Hidrológico + Acumulación de Flujo — Micro-Depresiones
Capa más innovadora: micro-depresiones del terreno que acumulan agua de lluvia no aparecen en datasets ópticos; solo se modelan hidrológicamente del DEM.

| Dataset | Resolución | Características |
|---|---|---|
| **MERIT DEM** | 90 m global | Elimina errores SRTM; mejor para hidrología plana |
| **HydroSHEDS DEM (v1)** | 3–30 arc-seg | Hidrológicamente condicionado; flujo pre-calculado |
| **SRTM 30 m** | 30 m | Base NASA; funciona en relieve |
| **CopDEM / TanDEM-X** | 30 m global | Mayor precisión en terreno plano |
| **LiDAR local** | 1 m (cobertura limitada) | Mejor para microtopografía urbana |

Pipeline `pysheds` en Python:
```python
from pysheds.grid import Grid
grid = Grid.from_raster('merit_dem.tif')
dem = grid.read_raster('merit_dem.tif')
pit_filled = grid.fill_pits(dem)
depressions = grid.detect_depressions(pit_filled)  # hábitats potenciales
flooded_dem = grid.fill_depressions(pit_filled)
fdir = grid.flowdir(inflated_dem, dirmap=dirmap)
acc = grid.accumulation(fdir, dirmap=dirmap)
twi = np.log(acc / (np.tan(slope) + 1e-10))  # Topographic Wetness Index
```

El **TWI** es uno de los predictores más robustos de hábitats larvarios. HydroSHEDS ofrece capas pre-computadas globales en GEE.

### 2.2 Capa Climática y Temporal

**ERA5-Land** (ECMWF/Copernicus): 0.1° (~9 km), horaria, 1950–presente. Variables clave: `2m_temperature`, `total_precipitation`, `2m_dewpoint_temperature` (→ HR), `evaporation` (→ secado de hábitats). Acceso via `cdsapi` (CDS API key).

**CHIRPS**: precipitación diaria 0.05° (~5 km), 1981–presente. Mayor resolución que ERA5, mejor captura de lluvia convectiva local. Acceso via xarray.

**WorldClim v2**: variables bioclimáticas (BIO1–BIO19) a ~1 km para modelado estático de idoneidad (MaxEnt). Variables más importantes: BIO8 (temperatura trimestre más húmedo), BIO14 (precipitación mes más seco), BIO3 (isothermality), BIO15 (estacionalidad).

### 2.3 Capa de Vegetación (NDVI/EVI)
Predictor por dos razones: fuente de néctar (azúcar) para adultos y mantenimiento de humedad/micro-hábitats sombreados.

- MODIS NDVI (MOD13A3): 1 km, mensual, GEE
- Sentinel-2 NDVI: 10 m, cada 5 días
- MAP EVI (Malaria Atlas Project): MODIS EVI gap-filled, GEE

### 2.4 Capa de Uso del Suelo / Cobertura Terrestre (LULC)

| Dataset | Resolución | Período | Acceso |
|---|---|---|---|
| **ESA WorldCover** | 10 m | 2020–2021 | GEE: `ESA/WorldCover/v200` |
| **Copernicus LULC Global** | 100 m | 2015–2019 | GEE |
| **ESA CCI Land Cover** | 300 m | 1992–2020 anual | CDS API |
| **OpenStreetMap (OSM)** | Vector | Continuo | overpass-api + osmnx |

Para *An. stephensi*, OSM es fundamental: contenedores artificiales (depósitos en azoteas, tanques, fuentes, albercas) no aparecen en satélites pero sí en OSM:
```python
tags = {"natural": ["water", "wetland"], "water": True,
        "man_made": ["reservoir", "water_tower"], "leisure": "swimming_pool"}
water_features = ox.features_from_place("Addis Ababa, Ethiopia", tags=tags)
```

### 2.5 Capa de Población Humana
Determina disponibilidad de hospedadores, escala de riesgo y distribución de agua artificial (correlación con urbanización).
- **WorldPop**: densidad 100 m y 1 km, anual 2000–2020, API REST y STAC
- **GPW** (NASA/CIESIN): 1 km, 2000–2020
- **Facebook HRSL**: ~30 m, detecta zonas habitadas con IA

### 2.6 Capa de Luz Nocturna (Night Lights) — Proxy de Urbanización
Predictor de urbanización y presencia de infraestructura con depósitos de agua.
- **VIIRS/DNB** (Suomi NPP): 500 m, mensual, GEE `NOAA/VIIRS/DNB/MONTHLY_V1/VCMSLCFG`
- **DMSP-OLS**: histórico 1992–2013

---

## 3. Tabla Maestra de Datasets y APIs

| Capa | Dataset | Resolución | Temporal | Acceso Python | Gratuito |
|---|---|---|---|---|---|
| Agua superficial histórica | JRC GSW v1.4 | 30 m | 1984–2021 mensual | GEE `JRC/GSW1_4/GlobalSurfaceWater` | ✅ |
| Agua superficial actual | Copernicus WB v2 | 300 m | 2020–hoy mensual | Sentinel Hub API, CDS API | ✅ |
| Agua fina (urbana) | Sentinel-2 NDWI | 10 m | ~5 días | GEE, sentinelhub-py | ✅ |
| DEM hidrológico global | MERIT DEM | 90 m | 2000 | Descarga directa tiles | ✅ |
| DEM condicionado + Flujo | HydroSHEDS v1 | 3–30 arc-sec | 2000 | hydrosheds.org download | ✅ |
| Micro-depresiones | pysheds | == DEM | estático | `pip install pysheds` | ✅ |
| TWI | pysheds + DEM | == DEM | estático | ídem | ✅ |
| Temperatura + Precipitación | ERA5-Land | ~9 km, horario | 1950–hoy | `pip install cdsapi` | ✅ |
| Precipitación diaria fina | CHIRPS v2.0 | ~5 km, diaria | 1981–hoy | NetCDF + xarray | ✅ |
| Variables bioclimáticas | WorldClim v2 | ~1 km | 1970–2000 | rasterio | ✅ |
| Vegetación (NDVI/EVI) | MODIS/Sentinel-2 | 250 m–10 m | 2000–hoy | GEE | ✅ |
| Cobertura terrestre | ESA WorldCover | 10 m | 2020–2021 | GEE `ESA/WorldCover/v200` | ✅ |
| Agua artificial + ríos | OSM | Vector | Continuo | osmnx | ✅ |
| Densidad de población | WorldPop | 100 m–1 km | 2000–2020 | REST API, STAC | ✅ |
| Urbanización | VIIRS Night Lights | 500 m | 2012–hoy mensual | GEE | ✅ |
| MAP completo | Malaria Atlas Project | Varía | Varía | GEE publisher collection | ✅ |

---

## 4. Pipeline para Construir la Capa de Hábitat Larvario Potencial

### 4.1 Arquitectura del Pipeline

```
INPUT LAYERS
    ├── JRC GSW occurrence (30m)
    ├── NDWI Sentinel-2 (10m)
    ├── DEM → pysheds → TWI (90m)
    ├── DEM → pysheds → Flow Accumulation (90m)
    ├── DEM → pysheds → Depression mask (90m)
    ├── ERA5-Land / CHIRPS precipitation
    ├── ERA5-Land temperature 2m
    ├── NDVI MODIS / Sentinel-2
    ├── ESA WorldCover LULC (10m)
    ├── WorldPop population density (100m)
    └── OSM water features (vector → rasterize)

PROCESSING
    ├── Reprojection + resampling to common resolution (ej. 100m, EPSG:4326)
    ├── 0–1 normalization per layer
    ├── Biological rules for An. stephensi:
    │       - T optimal: 20–32°C → continuous multiplier
    │       - Precipitation: threshold > 30 mm/month
    │       - TWI > threshold → high topographic humidity
    │       - LULC: urban/peri-urban → artificial containers
    │       - Population density: positive correlation with containers
    ├── Weighted sum or Random Forest / MaxEnt combination
    └── Discrete habitat segmentation (contiguous pixel clumping)

OUTPUT
    └── habitat_probability_YYYYMM.tif   ← monthly-updatable raster
    └── habitat_patches_YYYYMM.gpkg      ← individual patch vector
```

### 4.2 Toolkit Existente
El **Zenodo Toolkit** (2023) proporciona scripts GEE + R para extracción de variables ambientales y Random Forest. El artículo de referencia Malawi (2020) demuestra viabilidad de modelos de idoneidad vectorial a **30 m** con solo datos abiertos de GEE.

---

## 5. Variables Específicas para *An. stephensi*

| Variable | Dataset Fuente | Importancia | Efecto |
|---|---|---|---|
| Altitud | HydroSHEDS / SRTM | ★★★★★ | Rango 0–2000 m óptimo |
| Temperatura trimestre más húmedo (BIO8) | WorldClim | ★★★★★ | Óptimo 20–30°C |
| Precipitación mes más seco (BIO14) | WorldClim | ★★★★ | Humedad mínima necesaria |
| Estacionalidad precipitación (BIO15) | WorldClim | ★★★★ | Agua temporal |
| Isothermality (BIO3) | WorldClim | ★★★ | Estabilidad térmica |
| Densidad de población | WorldPop | ★★★★ | Proxy contenedores + hospedadores |
| Uso del suelo (urbano) | ESA CCI LULC | ★★★★ | Correlación hábitats artificiales |
| NDVI/EVI | MODIS | ★★★ | Micro-clima + azúcar |
| Luz nocturna | VIIRS | ★★★ | Proxy infraestructura urbana |
| Red de carreteras | OSM | ★★ | Proxy urbanización |
| Distancia a ríos/agua | HydroRIVERS + JRC | ★★★ | Buffer dispersión |

El modelo ensemble más reciente (2025, Cuerno de África) integra estas variables con AUC > 0.94.

---

## 6. Arquitectura del ABM Espacio-Temporal Completo

### 6.1 Framework: Mesa-Geo (Python)
Extensión GIS para Mesa (ABM Python más popular). Permite importar raster/vectorial como espacio del modelo, agentes con coordenadas GPS, vecindades basadas en distancia real (metros), y exportación GeoJSON/GeoTIFF por tick.

### 6.2 Estructura de Agentes

```python
class MosquitoAgent(mesa_geo.GeoAgent):
    def __init__(self, unique_id, model, geometry, crs):
        super().__init__(unique_id, model, geometry, crs)
        self.stage = "adult"  # egg|larva1-4|pupa|adult
        self.age_days = 0
        self.sex = random.choice(["male", "female"])
        self.status = "susceptible"  # susceptible|exposed|infectious
        self.eip_progress = 0.0
        self.gonotrophic_cycle = 0
        self.blood_fed = False
        self.sugar_energy = 1.0
        self.gravid = False
        self.insecticide_resistance = np.random.beta(...)
        self.habitat_patch_id = None
        self.flight_range_km = 1.5

    def step(self):
        env = self.model.get_environment(self.pos)
        self._age(env['temperature'])
        if self.sex == "female" and self.stage == "adult":
            self._host_seeking(env)
            self._update_eip(env['temperature'])
            if self.gravid: self._oviposit()
        self._dispersal(env)
        self._mortality(env)

class HabitatPatch(mesa_geo.GeoAgent):
    def __init__(self, unique_id, model, geometry, crs, hab_type):
        super().__init__(unique_id, model, geometry, crs)
        self.hab_type = hab_type
        self.water_volume_m3 = 0.0
        self.water_temp_c = 20.0
        self.larval_density = 0.0
        self.carrying_capacity = self._calc_K()
        self.active = False

    def step(self):
        rain = self.model.climate_engine.get_rain(self.pos, self.model.current_date)
        evapo = self.model.climate_engine.get_evaporation(self.pos, self.model.current_date)
        self.water_volume_m3 += (rain - evapo) * self.geometry.area
        self.active = self.water_volume_m3 > 0
        self.water_temp_c = self.model.climate_engine.get_water_temp(self.pos)
        self._larval_development()
```

### 6.3 Módulos del Modelo

```
AnophelesABM
    ├── GeoSpace (Mesa-Geo)
    │       ├── habitat_layer: probability raster (monthly)
    │       ├── population_layer: WorldPop
    │       └── patches: HabitatPatch list
    ├── ClimateEngine
    │       ├── load_era5(date_range, bbox) → T2m, precipitation, humidity
    │       ├── load_chirps(date_range, bbox) → precipitation
    │       ├── interpolate_to_grid() → xarray.Dataset
    │       └── get_EIP(temperature) → days
    ├── HabitatEngine
    │       ├── load_jrc_gsw(bbox) → permanent/seasonal water
    │       ├── load_ndwi(date, bbox) → current water
    │       ├── load_twi(bbox) → topographic wetness index
    │       ├── load_depression_mask(bbox)
    │       ├── load_osm_water(bbox)
    │       ├── compute_habitat_probability() → 0-1 raster
    │       └── activate_patches(rain, temp) → active patch list
    ├── MosquitoPopulation
    │       ├── spawn_eggs(patch, n_eggs)
    │       ├── develop_larvae(temperature)
    │       ├── adult_dispersal() → local + windborne
    │       └── swarm_mating()
    ├── EpidemiologyModule (optional)
    │       ├── human_population(WorldPop)
    │       ├── plasmodium_infection(mosquito, human)
    │       └── eip_tracking(mosquito)
    └── OutputEngine
            ├── mosquito_density_raster(tick) → GeoTIFF
            ├── habitat_status_raster(tick) → GeoTIFF
            └── time_series_csv(metrics) → pandas DataFrame
```

### 6.4 Temporalidad del ABM
Ticks **diarios** o sub-diarios (6h para ciclo circadiano de picadura):

| Módulo | Frecuencia |
|---|---|
| Temperatura (ERA5) | 6h o diaria |
| Precipitación | Diaria |
| Estado hábitats | Diaria |
| Ciclo gonotrófico | 2–4 días |
| Desarrollo larval completo | 6–14 días |
| EIP | 10–14 días a 25°C |
| Capa NDWI | Mensual (nueva Sentinel-2) |
| Capa población | Anual |

### 6.5 Dispersión: Modelo de Dos Componentes
1. **Dispersión local (Gaussiana truncada)**: 95% individuos ≤ 2 km del hábitat de origen
2. **Migración eólica**: probabilidad baja (1–5% por temporada) usando viento ERA5 a ~850 hPa

---

## 7. Hoja de Ruta de Implementación

**Fase 1 — Capa de Hábitats (Semanas 1–4)**: Definir ROI, procesar DEM MERIT con pysheds (TWI + depresiones), extraer JRC GSW, descargar ERA5-Land + WorldPop + ESA WorldCover, extraer OSM water, fusionar capas en raster común (100m GeoTIFF), segmentar parches discretos.

**Fase 2 — ABM Base (Semanas 5–10)**: Implementar HabitatPatch y MosquitoAgent en Mesa-Geo, conectar ClimateEngine con ERA5/CHIRPS, implementar ciclo de vida completo, validar contra datos entomológicos.

**Fase 3 — Integración Temporal y Dispersión (Semanas 11–16)**: Activar/desactivar hábitats dinámicamente, implementar dos componentes de dispersión, añadir módulo epidemiológico, análisis de sensibilidad.

**Fase 4 — Validación y Escenarios (Semanas 17–20)**: Calibrar con datos de campo (Addis Abeba / Djibouti), escenarios de cambio climático (SSP2.6, SSP4.5, SSP8.5), escenarios de control.

---

## 8. Recursos de Código Existentes

| Recurso | URL | Contenido |
|---|---|---|
| Zenodo Malaria EO Toolkit | zenodo.org/records/7696722 | GEE + R scripts para RF |
| pysheds GitHub | github.com/pysheds/pysheds | Análisis hidrológico DEM |
| ERA5 Python Tutorial | github.com/joaohenry23/Download_ERA5_with_python | Scripts CDS API |
| CHIRPS xarray | stackoverflow.com (ID 67163212) | Descarga CHIRPS |
| Sentinel-2 NDWI | github.com/ncortim/s2-ndwi | Cálculo NDWI |
| Mesa-Geo | github.com/projectmesa/mesa-geo | GIS extension para ABM |
| EMOD malaria | github.com/EMOD-Hub/EMOD | ABM completo (IDM/Gates) |
| JRC GSW GEE | developers.google.com/earth-engine/datasets/catalog/JRC_GSW1_4_GlobalSurfaceWater | Surface water dataset |
| HydroSHEDS | hydrosheds.org | DEM, flow direction, accumulation |
| WorldPop API | worldpop.org/sdi/introapi | REST API población |
| MAP GEE catalog | developers.google.com/earth-engine/datasets/publisher/malariaatlasproject | Malaria Atlas datasets |

---

## 9. Consideraciones de Escala y Precisión

Para micro-depresiones (<1 m diámetro, cruciales en entornos urbanos con *An. stephensi*), MERIT DEM (90 m) y SRTM (30 m) son **insuficientes**. Opciones:
- **LiDAR a 1 m**: Disponible en EE.UU. (USGS 3DEP), Europa. En África tropical, cobertura limitada.
- **TanDEM-X a 12 m** (DLR): Cobertura global, acceso via solicitud científica gratuita. Mejor opción hasta HydroSHEDS v2.
- **Drones UAV**: Para áreas <10 km², DTM a 5–10 cm. Estándar en estudios de larval source management (LSM).

Campbell (2026) en Florida demuestra que LiDAR a 1 m identifica microtopographic depressions que predicen producción de mosquitos con precisión sin precedentes.

---

## References

1. [Future global distribution of Anopheles stephensi - Nature](https://www.nature.com/articles/s41598-025-07653-8)
2. [The origin, invasion history and resistance architecture - PubMed](https://pubmed.ncbi.nlm.nih.gov/40196515/)
3. [A new malaria mosquito in African cities - GAVI](https://www.gavi.org/vaccineswork/new-malaria-mosquito-causing-outbreaks-african-cites-heres-where-it-came)
4. [Predicting suitability of An. stephensi in Greater Horn of Africa - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC12948167/)
5. [Variables used in An. stephensi distribution modeling - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC12991239/table/pntd.0014054.t001/)
6. [Future global distribution and climatic suitability - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC12215484/)
7. [Global Surface Water Explorer - JRC](https://data.jrc.ec.europa.eu/collection/id-0084)
8. [JRC GSW Mapping Layers v1.4 - GEE](https://developers.google.com/earth-engine/datasets/catalog/JRC_GSW1_4_GlobalSurfaceWater)
9. [Anopheles larval species composition - PubMed](https://pubmed.ncbi.nlm.nih.gov/32046734/)
10. [Water quality and immatures of An. gambiae - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC1508151/)
11. [Copernicus Water Bodies v2](https://land.copernicus.eu/en/products/water-bodies/water-bodies-global-v2-0-300m)
12. [Water Bodies Documentation](https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/clms/bio-geophysical-parameters/water-bodies/water-bodies.html)
13. [s2-ndwi GitHub](https://github.com/ncortim/s2-ndwi)
14. [NDWI Analysis with Sentinel-2 - Medium](https://medium.com/@defaniarman/ndwi-analysis-using-sentinel-2-in-google-earth-engine-08814c1d0b93)
15. [Identification of Aquatic Habitats with Sentinel-1 - ISPRS](https://isprs-archives.copernicus.org/articles/XLVIII-3-W3-2024/63/2024/)
16. [MERIT DEM Guide](https://www.geodataviewer.com/datasets/dem/merit-dem/)
17. [HydroSHEDS Downloads](https://www.hydrosheds.org/hydrosheds-core-downloads)
18. [HydroSHEDS Core layers](https://www.hydrosheds.org/products/hydrosheds)
19. [Remote Sensing Tool for Mosquito Control - Southern IPM](https://southernipm.org/2026/05/18/a-remote-sensing-technology-tool-for-precision-mosquito-control/)
20. [pysheds documentation](https://pythongis.org/part3/chapter-12/nb/00-watershed-analysis-with-pysheds.html)
21. [pysheds GitHub](https://github.com/pysheds/pysheds)
22. [Mapping malaria vector suitability in Malawi - PLOS ONE](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0235697)
23. [Leveraging big data for malaria - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC7402481/)
24. [HydroSHEDS DEM in GEE](https://developers.google.com/earth-engine/datasets/catalog/WWF_HydroSHEDS_15CONDEM)
25. [ERA5 Mosquito Alert Portal](https://labs.mosquitoalert.com/metadata_public_portal/notebooks/era5h.html)
26. [Complete ERA5 - CDS](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-complete)
27. [cdsapi PyPI](https://pypi.org/project/cdsapi/)
28. [CHIRPS extraction GitHub](https://github.com/ankwasa/extract-CHIRPS-rainfall-)
29. [Downloading CHIRPS with Python - StackOverflow](https://stackoverflow.com/questions/67163212/downloading-gridded-chirps-data-sets-using-python)
30. [Mapping An. stephensi habitats in Kwale, Kenya](https://www.sciencepublishinggroup.com/article/10.11648/j.aje.20230704.11)
31. [Overhead tank as An. stephensi habitat - White Rose](https://eprints.whiterose.ac.uk/id/eprint/169170/1/s12936_016_1321_7.pdf)
32. [WorldPop Data Catalog](https://www.worldpop.org/datacatalog/)
33. [WorldPop API](https://www.worldpop.org/sdi/introapi/)
34. [Earth observation for malaria modelling - Zenodo](https://zenodo.org/records/7696722)
35. [Predicting suitability for An. stephensi - UG](https://pure.ug.edu.gh/en/publications/predicting-the-environmental-suitability-for-anopheles-stephensi-)
36. [Suitable ecological niches of An. stephensi - PubMed](https://pubmed.ncbi.nlm.nih.gov/41838734/)
37. [Predicting suitability of An. stephensi - ScienceDirect](https://www.sciencedirect.com/science/article/pii/S1569843225006739)
38. [Mesa ABM GitHub](https://github.com/mesa/mesa)
39. [Mesa-Geo ACM](https://dl.acm.org/doi/10.1145/3557989.3566157)
40. [Wind-assisted high-altitude dispersal - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC10337859/)
41. [emodpy-malaria](https://emod.idmod.org/emodpy-malaria/)

---

## Relevancia para MalariaSentinel / Centinela

Este documento define el **módulo urbano completo** del Centinela. El pipeline de 10+ capas geoespaciales (Sección 2) y su fusión en un raster de probabilidad de hábitat (Sección 4) constituye el `HabitatEngine` del ABM. La tabla maestra de datasets (Sección 3) y la hoja de ruta de 20 semanas (Sección 7) sirven como plan de implementación directo. Las clases `MosquitoAgent` y `HabitatPatch` (Sección 6) con sus atributos biológicos y genéticos son el modelo de agente canónico del proyecto. El framework Mesa-Geo es el backbone ABM recomendado. La arquitectura de dos componentes de dispersión (local Gaussiano + eólico con ERA5) y el módulo epidemiológico opcional (EIP + transmisión humana) completan el diseño del sistema Centinela para entornos urbanos con *An. stephensi*.
