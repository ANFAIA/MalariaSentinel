# Datasets, Variables y Arquitectura para Hábitats Rurales de *Anopheles gambiae* s.l. — Complemento al Sistema ABM Geoespacial Completo
## Resumen
Este documento complementa el reporte anterior sobre *Anopheles stephensi* (vector urbano) y cubre la ecología de cría de los vectores **rurales** del complejo *Anopheles gambiae* s.l., con énfasis especial en *An. arabiensis*, *An. gambiae* s.s., *An. coluzzii*, *An. funestus* y los vectores forestales asiáticos (*An. dirus*, *An. minimus*). El vector rural opera en un paradigma radicalmente diferente al urbano: sus hábitats son dinámicos, efímeros, dependientes de procesos hidrológicos naturales (ríos, llanuras de inundación, canales de paleocauces, zonas de convergencia topográfica, arrozales) y no de infraestructura artificial. La consecuencia directa para la simulación ABM es que la **capa de hábitat rural debe actualizarse diariamente** en función de la lluvia acumulada, el caudal del río, el nivel freático y la evapotranspiración — no mensualmente como en el escenario urbano.

***
## 1. Ecología de Cría por Especie Rural: Variables Diferenciadoras
Cada especie del complejo tiene requerimientos de hábitat distintos que deben modelarse por separado en el ABM mediante clases de agente `HabitatPatch` con distintos subtipos.
### 1.1 *Anopheles gambiae* s.s.
- **Hábitat preferido**: Charcos temporales pequeños y soleados formados por lluvia directa; piscinas en lechos de ríos efímeros durante la estación seca; zonas de convergencia topográfica donde sube el nivel freático[^1][^2].
- **Características diagnósticas**: Exposición a la luz solar directa (ausencia de sombra); agua limpia y clara; ausencia de plantas emergentes; sin corriente; pequeño perímetro (<20 m²)[^2][^3].
- **Patrón estacional**: Picos de densidad larvaria durante el declive de la estación húmeda (junio-julio en África Oriental), cuando el agua superficial se fragmenta en charcas aisladas más cálidas y someras[^1].
- **Sensibilidad al flujo**: Muy sensible. La lluvia intensa barre las larvas de los hábitats más pequeños. La lluvia de más de 40 mm/día se correlaciona negativamente con densidades larvarias[^1].
### 1.2 *Anopheles arabiensis*
- **Hábitat preferido**: Cuatro tipos geomorfológicos principales identificados en campo en Tanzania[^1]:
  1. **Convergencia topográfica** (cuencas de orden cero sin red de drenaje desarrollada): El nivel freático sube tras las lluvias e intersecta la superficie, formando charcas. Son los hábitats más productivos a medida que avanza la estación seca.
  2. **Cuencas de llanura de inundación** (*floodplain basins*): Depresiones someras próximas a canales fluviales, inundadas cuando el río desborda. Productivas con un **lag de 1 mes** respecto al pico del caudal.
  3. **Paleocauces** (*palaeochannels*): Canales fluviales abandonados visibles en imágenes Landsat como depresiones lineales sinuosas. Productivos con un **lag de 3 meses** respecto al nivel del río, siendo refugios de la estación seca.
  4. **Canales fluviales efímeros**: Pozas formadas cuando el río deja de fluir en la estación seca. Estas charcas tienen las densidades larvarias más altas del período seco[^1].
- **Zoofilia parcial**: Más zoofílico y exofágico que *An. gambiae* s.s. → modela la distribución de ganado como una capa de hospedadores alternativa[^1].
### 1.3 *Anopheles funestus*
- **Hábitat preferido**: Cuerpos de agua **grandes, semipermanentes o permanentes** con **vegetación emergente densa** (carrizos, totoras, juncos, algas); orillas de lagos; arrozales maduros; pantanos; márgenes fluviales sombreados por árboles[^4][^5].
- **Características diagnósticas**:
  - Vegetación emergente presente → **predictor positivo más fuerte**[^4]
  - Hábitats sombreados (dosel arbóreo denso) → significativamente más probables[^4]
  - Profundidad > 50 cm[^4]
  - Agua estancada o de movimiento muy lento[^4]
  - Hábitats permanentes o semipermanentes[^5]
- **Diferencia crítica con *An. gambiae***: *An. funestus* evita los charcos temporales pequeños y soleados que son los preferidos de *An. gambiae* s.s. Esto permite discriminar qué especie coloniza cada parche de hábitat en el ABM.
- **Importancia epidemiológica**: En África Oriental y Meridional, *An. funestus* es responsable de hasta el 90% de las picadas infectivas en entornos rurales[^4][^6].
### 1.4 *Anopheles coluzzii*
- **Hábitat**: Más tolerante a agua con mayor salinidad y contaminación orgánica que *An. gambiae* s.s. — coloniza zonas costeras, estuarios, manglares y hábitats peri-urbanos con agua degradada[^7][^8].
- **Agua salobre**: *An. coluzzii* puede desarrollar sus larvas en agua con hasta ~30‰ de salinidad en zonas costeras de Ghana y Senegal[^8].
### 1.5 *An. dirus*, *An. minimus* (Vectores forestales de Asia)
- **Hábitat**: Remansos de ríos sombreados bajo dosel forestal; piscinas formadas por huellas de animales en suelo forestal; arroyos de bajo orden con flujo lento bajo bosque[^9].
- **Efecto de la deforestación**: *An. minimus* muestra tasas de pupación de 3.8% bajo bosque cerrado vs. 52.5% en zonas deforestadas, con un acortamiento del tiempo de desarrollo larvario de 1.9–3.3 días[^9]. La deforestación **favorece** su proliferación al aumentar la temperatura del agua y reducir la competencia biótica.
- **Implicación para el ABM**: La capa de **pérdida de cobertura forestal** (Hansen/GFW) es una variable dinámica clave para estos vectores.

***
## 2. Clasificación Geomorfológica de los Hábitats Rurales (Tipología ABM)
El estudio seminal de Hardy et al. (2013)[^1] — el primero en clasificar hábitats larvarios por su proceso hidrológico a escala de cuenca (200 km²) — establece la taxonomía que debe implementarse en el ABM rural. Esta clasificación es la base de la clase `HabitatPatch` para el módulo rural:

| Tipo de Hábitat | Proceso Hidrológico | Especie Dominante | Lag Respecto a Lluvia | Detectabilidad Remota |
|---|---|---|---|---|
| **Convergencia topográfica** | Nivel freático sube e intersecta superficie | *An. arabiensis* | 0 meses (estación húmeda avanzada) | TWI alto en DEM[^1] |
| **Cuenca de llanura de inundación** | Desbordamiento del río → depresiones someras | *An. arabiensis* | 1 mes | JRC GSW change + HydroRIVERS buffer[^1] |
| **Paleocauce** | Saturación de sedimentos en depresión lineal | *An. arabiensis* | 3 meses | Landsat (textura sinuosa oscura)[^1] |
| **Canal fluvial efímero (pozas)** | Río deja de fluir → charcas en lecho | *An. arabiensis* / *An. funestus* | Estación seca | HydroRIVERS stream order 1–2[^1] |
| **Charca pluvial directa** | Escorrentía superficial + lluvia directa | *An. gambiae* s.s. | 0 días | pysheds depressions + CHIRPS[^2] |
| **Pantano / margen lacustre** | Nivel alto permanente; vegetación emergente | *An. funestus* | Permanente | JRC GSW occurrence >80%[^4] |
| **Arrozal** | Irrigación + lluvia; agua laminar somera | *An. arabiensis* + *An. gambiae* s.s. | Calendario de cultivo | GFSAD + FAO GMIA[^10] |
| **Canal de irrigación** | Flujo controlado; margenes sombreados | *An. arabiensis* | Continuo (irrigación) | FAO AQUAMAPS[^11] |
| **Remanso forestal** | Suelo forestal + sombra de dosel | *An. dirus* / *An. minimus* | Estación húmeda | EVI Sentinel-2 + Hansen GFW[^9] |
| **Hábitat salobre costero** | Agua mixta o salobre | *An. coluzzii* / *An. melas* | Mareas + lluvia | Sentinel-2 NDWI + salinidad ESA[^8] |

***
## 3. Datasets Específicos para el Módulo Rural
### 3.1 Red Hidrológica con Caudal: HydroRIVERS
- **Qué es**: Red vectorial de **todos los ríos globales** con cuenca de captación ≥10 km² o caudal promedio ≥0.1 m³/s[^12][^13].
- **Información disponible por tramo fluvial**: orden de Strahler, longitud del segmento, caudal promedio anual, país.
- **Por qué es crítico para el ABM rural**: Define los buffer zones de hábitats larvarios perifluviales. Los estudios muestran que >80% de los hábitats larvarios se encuentran dentro de 400 m de cursos de agua[^14] y que el 95% de los hábitats de *An. arabiensis* productivos están dentro de 2 km del río[^1].
- **Acceso Python**:
  ```python
  import geopandas as gpd
  # Descargar shapefile de hydrosheds.org para la región de interés
  rivers = gpd.read_file('HydroRIVERS_v10_af.shp')  # África
  # Seleccionar ríos por orden de Strahler (1-3 = más relevantes para hábitats larvarios)
  rivers_small = rivers[rivers['ORD_STRA'] <= 3]
  # Buffer de 400m para identificar zona perifluvial de cría
  rivers_buffer = rivers_small.to_crs('EPSG:3857').buffer(400).to_crs('EPSG:4326')
  ```
- **Complemento clave**: **HydroLAKES** (polígonos de todos los lagos globales con superficie >0.1 km²) y **HydroBASINS** (cuencas hidrográficas a 12 escalas de resolución), ambos de la misma familia[^15][^16].
### 3.2 Modelo de Flujo Superficial Dinámico: GloFAS / ERA5-Land Runoff
Para simular cuándo y cómo cambian los caudales fluviales (que determinan cuándo se inundan las llanuras y cuándo quedan las pozas en el lecho), se necesita más que el mapa estático de HydroRIVERS:

- **GloFAS (Global Flood Awareness System)** — ECMWF/Copernicus: Predicciones de descarga fluvial en ≥40,000 estaciones virtuales globales, resolución de 0.1°, horizonte de hasta 30 días. Datos históricos retroalimentados desde 1979[^17][^18].
- **ERA5-Land `runoff`**: El total de escorrentía superficial de ERA5-Land (variable `runoff`) permite calcular cuánta agua llega a cada cuenca en cada día.
  ```python
  import cdsapi
  c = cdsapi.Client()
  c.retrieve('reanalysis-era5-land', {
      'variable': ['runoff', 'sub_surface_runoff', 'surface_runoff',
                   'total_precipitation', '2m_temperature',
                   'potential_evaporation'],
      'year': '2024', 'month': '06',
      'day': [str(d).zfill(2) for d in range(1, 31)],
      'time': '00:00', 'format': 'netcdf',
      'area': [15, 28, -5, 48],   # AOI África Oriental
  }, 'era5_runoff_jun2024.nc')
  ```
### 3.3 Arrozales e Infraestructura de Irrigación
Los arrozales son los hábitats más productivos para *An. arabiensis* y *An. gambiae* en África Occidental[^19][^10]. Tres datasets cubren esta capa:

#### A. GFSAD (Global Food Security-support Analysis Data) — NASA/USGS
- **Crop Mask global a 1 km**: distingue cultivos irrigados y de secano[^20][^21].
- Acceso en GEE: `ee.Image('USGS/GFSAD1000_V1')`, banda `landcover`.
- **GFSAD30** (30 m, en desarrollo 2025): mayor resolución, útil para mapear arrozales individuales.

#### B. FAO AQUASTAT / AQUAMAPS — Áreas de Irrigación
- **Global Map of Irrigation Areas (GMIA) v5.0**: porcentaje de área equipada para irrigación por celda de 5 arc-min (~9 km)[^22][^23].
- **AQUAMAPS**: plataforma GIS interactiva con redes hídricas, infraestructura de irrigación y canales derivados de HydroSHEDS[^24].
- Formato: ASCII-grid + shapefile ESRI, descarga gratuita directa[^22].

#### C. Calendarios de Cultivo por País — FAO/ORYZA
- El **calendario de inundación del arrozal** determina cuándo está activo el hábitat. La FAO/AQUASTAT publica calendarios de riego por cultivo y país[^25].
- En el ABM, este calendario se usa para activar/desactivar los parches de hábitat `RiceField` mensualmente.
### 3.4 Suelo: ISRIC SoilGrids 250 m
La textura y humedad del suelo son críticas porque determinan:
1. La infiltración vs. retención superficial de agua de lluvia → formación de charcas.
2. El tipo de sustrato preferido por *An. gambiae* para ovipositar (sustratos húmedos de grano fino)[^26].

- **SoilGrids** (ISRIC): mapas globales a 250 m de pH, arcilla, limo, arena, densidad aparente, carbono orgánico, CEC, para 6 profundidades[^27].
- Propiedades más relevantes para mosquitos:
  - `clay` (% arcilla): suelos arcillosos retienen más agua → más charcas.
  - `silt` (% limo): preferencia de oviposición[^26].
  - `bdod` (densidad aparente): proxy de compactación y escorrentía.
- **Acceso Python** (REST API en restauración parcial en 2026; alternativa: descarga de tiles GeoTIFF):
  ```python
  import requests
  # Solicitar valor puntual de contenido de arcilla a 5 cm de profundidad
  url = "https://rest.isric.org/soilgrids/v2.0/properties/query"
  params = {"lon": 34.5, "lat": -4.5, "property": "clay",
            "depth": "0-5cm", "value": "mean"}
  r = requests.get(url, params=params)
  ```
### 3.5 Temperatura de la Superficie del Agua: MODIS LST (MOD11)
La temperatura del agua del hábitat larvario no es igual a la temperatura del aire. Para hábitats someros expuestos al sol, la temperatura del agua puede ser 5–10°C más alta que el aire[^2]. El **MODIS Land Surface Temperature (LST)** a 1 km permite estimar la temperatura de agua superficial de hábitats rurales[^28][^29]:

- `MOD11A1` (Terra): LST diurna y nocturna a 1 km.
- `MOD11A2`: promedio de 8 días (menos ruido).
- En GEE: `ee.ImageCollection('MODIS/061/MOD11A1')`.
- La correlación entre LST diurna y temperatura de agua de charcos (<50 cm) es alta (r² > 0.85) en estudios de campo[^28].
### 3.6 Cobertura Forestal y Deforestación: Hansen GFW (Global Forest Watch)
Para los vectores forestales asiáticos (*An. dirus*, *An. minimus*) y para modelar el efecto de la deforestación sobre los vectores africanos (que altera la temperatura del hábitat y la producción larvaria):

- **Hansen Global Forest Change**: Landsat, 30 m, 2000–2023. Pérdida anual de cobertura forestal[^9].
- GEE: `ee.Image('UMD/hansen/global_forest_change_2023_v1_11')`.
- Bandas clave: `treecover2000` (% cobertura inicial), `lossyear` (año de pérdida).
- **EVI (Enhanced Vegetation Index)**: Más sensible que NDVI en zonas de alta biomasa forestal; mejor proxy del dosel de sombra sobre hábitats larvarios.
### 3.7 Análisis de Flujo Avanzado: TauDEM / pysheds para Paleocauces y Cuencas
Para detectar **paleocauces** (canales fluviales abandonados que son hábitats de la estación seca de *An. arabiensis*[^1]) se necesita un análisis DEM especializado más allá del TWI básico:

```python
from pysheds.grid import Grid
import numpy as np

grid = Grid.from_raster('merit_dem.tif')
dem = grid.read_raster('merit_dem.tif')

# 1. ANTES de rellenar depresiones: guardar máscara de depresiones (posibles hábitats)
depressions = grid.detect_depressions(grid.fill_pits(dem))

# 2. Calcular dirección y acumulación de flujo
pit_filled = grid.fill_pits(dem)
flooded = grid.fill_depressions(pit_filled)
inflated = grid.resolve_flats(flooded)
dirmap = (64, 128, 1, 2, 4, 8, 16, 32)
fdir = grid.flowdir(inflated, dirmap=dirmap)
acc = grid.accumulation(fdir, dirmap=dirmap)

# 3. Extraer red de drenaje (ríos y canales actuales)
threshold_km2 = 10   # área mínima de captación para definir un "río"
threshold_cells = threshold_km2 * 1e6 / (90**2)  # para MERIT DEM 90m
branches = grid.extract_river_network(fdir, acc > threshold_cells, dirmap=dirmap)

# 4. Calcular pendiente local → detectar tramos de baja pendiente (pozas potenciales)
slope = grid.cell_slopes(inflated, fdir)
low_slope_mask = slope < np.percentile(slope, 10)   # décimo percentil = fondos de valle

# 5. Detectar depresiones lineales (paleocauces candidatos)
# Paleocauces = áreas de baja pendiente + baja elevación relativa + alto TWI
twi = np.log((acc + 1) / (np.tan(slope) + 1e-5))
paleochannel_candidates = (twi > np.percentile(twi, 80)) & low_slope_mask & ~depressions
```
### 3.8 Nivel Freático: GRACE/GRACE-FO (Anomalías de Agua Total)
El nivel freático es un predictor clave para los hábitats de convergencia topográfica de *An. arabiensis*, que se forman cuando la tabla de agua sube hasta intersectar la superficie[^1]. El sistema GRACE/GRACE-FO de NASA mide anomalías de almacenamiento de agua terrestre (incluye agua subterránea) a escala de cuenca:

- **GRACE Terrestrial Water Storage (TWS)**: Resolución ~300–500 km (demasiado gruesa para modelar a nivel local, pero útil como variable de tendencia estacional).
- En GEE: `ee.ImageCollection('NASA/GRACE/MASS_GRIDS/LAND')`.
- **Para nivel freático local**: combinar con ERA5-Land `depth_to_water_table` (disponible en ERA5-Land Extended) o modelos de flujo subterráneo (MODFLOW).

***
## 4. Variables Físico-Químicas del Hábitat (In-situ → Modelables)
Además de las variables geoespaciales satelitales, los estudios de campo documentan las siguientes propiedades **in-situ** de los hábitats positivos para larvas. Estas deben modelarse en el `HabitatPatch` como variables de estado:

| Variable | Efecto sobre *An. gambiae* | Fuente de Datos en Simulación |
|---|---|---|
| **Turbidez del agua** | Agua turbia correlaciona positivamente con densidad larvaria (protección ante depredadores)[^3] | Proxy: NDWI + sedimento en suspensión MODIS (MOD09) |
| **Corriente de agua** | Agua estancada o lento → positivo; flujo rápido → letal para larvas[^3][^1] | HydroRIVERS velocity + ERA5 runoff |
| **pH** | 7.0–8.5 óptimo; no significativo en análisis multivariante[^2] | SoilGrids pH (proxy) |
| **Temperatura del agua** | 25–30°C óptimo; deriva MODIS LST[^2][^28] | MODIS MOD11A1 + ERA5 T2m |
| **Presencia de vegetación emergente** | Predictor positivo más fuerte para *An. funestus*; negativo para *An. gambiae* s.s.[^4][^2] | NDVI Sentinel-2 en zona de hábitat |
| **Sombra del dosel** | Positivo para *An. funestus*; negativo para *An. gambiae* s.s.[^3][^4] | Clasificación EVI + árbol dosel Hansen |
| **Superficie del hábitat (m²)** | Pequeños (<20 m²) → *An. gambiae*; grandes → *An. funestus*[^2][^1] | Segmentación de parches: JRC GSW + NDWI |
| **Exposición solar** | Soleado → *An. gambiae*; sombreado → *An. funestus*[^3][^2] | Aspect + hillshade del DEM |
| **Distancia a la casa habitada** | 80–400 m radio de vuelo; <300 m en zonas de alta transmisión[^30][^14] | WorldPop + OSM buildings |
| **Presencia de ganado** | *An. arabiensis* zoofílico → productividad aumenta con proximitad bovina[^1] | FAO Livestock density raster (GLW4) |

***
## 5. Datasets Adicionales para el Módulo Rural
### 5.1 Global Livestock Density (GLW4) — FAO/ILRI
*An. arabiensis* alimenta preferentemente de ganado bovino y equino cuando está disponible[^1]. El mapa de densidad de ganado GLW4 (Global Livestock of the World, versión 4) a 1 km proporciona densidades de bovinos, ovinos, caprinos, porcinos y aves por pixel:
- **Acceso**: descarga directa desde dataverse.harvard.edu o via worldpop.org.
- Integración en ABM: ajusta la probabilidad de que una hembra adulta tenga éxito en una comida de sangre de animal vs. humano.
### 5.2 MODIS LST Nocturna — Temperatura de Suelo Nocturna
La temperatura mínima nocturna del suelo determina la supervivencia del adulto y la tasa de desarrollo del parásito *Plasmodium* en el mosquito (EIP). La LST nocturna de MODIS a 1 km (MOD11A2, banda `LST_Night_1km`) es el mejor proxy disponible para temperatura ambiental nocturna en zonas sin estaciones meteorológicas[^28].
### 5.3 Remote Sensing + ML (framework existente de 2025)
Un artículo de 2025 propone un framework en **dos pasos** para detección de hábitats larvarios rurales con Sentinel-2 + Random Forest[^31]:
1. **Paso 1**: Clasificación de superficie de agua de la zona de estudio (NDWI + MNDWI + SAR Sentinel-1).
2. **Paso 2**: Predicción de presencia de larvas a partir de características del parche de agua (tamaño, forma, índices espectrales, contexto de uso del suelo).

El resultado supera a los modelos clásicos de MaxEnt en precisión de predicción a escala de campo (resolución 10 m)[^31].
### 5.4 Sentinel-1 SAR — Detección de Agua Bajo Nubes
En zonas tropicales con alta nubosidad estacional (inicio de estación húmeda), los índices ópticos (NDWI) fallan. Sentinel-1 C-band SAR penetra las nubes y permite detectar agua superficial incluyendo arrozales inundados y llanuras de inundación:
- **Sentinel-1 Water Index (SWI)**: Combinación de backscatter VV y VH a 10 m. En estudios recientes sobre hábitats de *Anopheles*, alcanzó 96.1% de precisión[^32].
- GEE: `ee.ImageCollection('COPERNICUS/S1_GRD')`.

***
## 6. Arquitectura Integrada: ABM Mosquito Completo (Urbano + Rural)
### 6.1 Unificación de los Dos Módulos de Hábitat
El ABM completo fusiona el módulo urbano (*An. stephensi*, contenedores artificiales) con el módulo rural (*An. gambiae* s.l., hábitats naturales) en un único framework Mesa-Geo, discriminando la especie por el tipo de parche de hábitat:

```python
# Enum de tipos de hábitat para el ABM unificado
from enum import Enum

class HabitatType(Enum):
    # --- URBANO (An. stephensi) ---
    CONTAINER_ROOFTOP   = "container_rooftop"    # cisterna/barril en azotea
    CONTAINER_ORNAMENTAL = "container_ornamental" # fuentes, jardineras
    CONTAINER_INDUSTRIAL = "container_industrial" # industria/obras

    # --- RURAL NATURAL (An. gambiae / An. arabiensis / An. funestus) ---
    TOPOGRAPHIC_CONV    = "topographic_convergence"  # nivel freático emergente
    FLOODPLAIN_BASIN    = "floodplain_basin"          # cuenca de llanura inundación
    PALEOCHANNEL        = "paleochannel"              # cauce abandonado
    RIVER_CHANNEL       = "river_channel"             # pozo en lecho efímero
    PLUVIAL_POOL        = "pluvial_pool"              # charca de lluvia directa
    SPRING_FED          = "spring_fed"                # manantial / agua subterránea
    SWAMP_MARSH         = "swamp_marsh"               # pantano / margen lacustre

    # --- AGRÍCOLA (An. arabiensis / An. gambiae s.s.) ---
    RICE_PADDY          = "rice_paddy"               # arrozal inundado
    IRRIGATION_CANAL    = "irrigation_canal"         # canal de riego

    # --- FORESTAL (An. dirus / An. minimus, Asia) ---
    FOREST_POOL         = "forest_pool"              # poza bajo dosel forestal

    # --- COSTERO (An. coluzzii / An. melas) ---
    BRACKISH_WETLAND    = "brackish_wetland"         # manglar / estuario
```
### 6.2 Motor de Hábitat Rural: Activación Dinámica Diaria
El motor rural actualiza diariamente qué parches están activos, basándose en:

```python
class RuralHabitatEngine:
    """
    Gestiona la activación de hábitats naturales rurales.
    Requiere ERA5-Land (runoff, T2m, evaporation) y
    CHIRPS (precipitación diaria alta resolución).
    """
    def __init__(self, era5_dataset, chirps_dataset, hydrorivers_gdf, dem_grid):
        self.era5 = era5_dataset         # xarray.Dataset ERA5-Land diario
        self.chirps = chirps_dataset     # xarray.Dataset CHIRPS diario
        self.rivers = hydrorivers_gdf    # GeoDataFrame HydroRIVERS
        self.grid = dem_grid             # pysheds Grid con TWI, acc, depressions

    def get_active_habitats(self, date, species="an_arabiensis"):
        """
        Retorna GeoDataFrame de hábitats activos para la fecha y especie dadas.
        """
        rain_24h = self._get_rainfall(date)            # mm/día CHIRPS
        runoff = self._get_runoff(date)                # m³/s ERA5-Land
        river_stage = self._estimate_river_stage(date) # nivel relativo (0-1)
        evaporation = self._get_evaporation(date)      # mm/día ERA5-Land
        water_table = self._estimate_water_table(date) # profundidad (m)

        # Reglas de activación por tipo geomorfológico
        active = []

        # Charcas pluviales directas (An. gambiae s.s.)
        if rain_24h > 15:   # umbral de lluvia formadora de charca
            active += self._activate_pluvial_pools(rain_24h)

        # Convergencia topográfica (An. arabiensis, final estación húmeda)
        if water_table < 0.3:   # tabla de agua a <30cm → afloramiento
            active += self._activate_topographic_convergence()

        # Cuencas de llanura (lag 1 mes)
        if river_stage[1_month_lag] > 0.8:  # desbordamiento hace 1 mes
            active += self._activate_floodplain_basins()

        # Pozas en cauce efímero (estación seca)
        if river_stage < 0.1 and evaporation < rain_24h + 2:  # río parado
            active += self._activate_river_channel_pools()

        # Arrozales (según calendario de cultivo FAO)
        if self._is_rice_season(date):
            active += self._activate_rice_paddies()

        return active
```
### 6.3 Tabla Maestra: Todos los Datasets del ABM Completo
La siguiente tabla integra los datasets del módulo urbano (*An. stephensi*, reportado anteriormente) y el rural (*An. gambiae* s.l., este documento):

| Módulo | Capa | Dataset | Resolución | Acceso Python |
|---|---|---|---|---|
| **Ambos** | Temperatura y precipitación | ERA5-Land (ECMWF) | 9 km, diario | `cdsapi`[^18] |
| **Ambos** | Precipitación fina | CHIRPS v2.0 | 5 km, diario | xarray directo[^33] |
| **Ambos** | Agua superficial histórica | JRC GSW v1.4 | 30 m | GEE[^34] |
| **Ambos** | DEM hidrológico | MERIT DEM | 90 m | tile download[^35] |
| **Ambos** | TWI + depresiones | pysheds | == DEM | `pip install pysheds`[^36] |
| **Ambos** | Densidad población | WorldPop | 100 m | REST API[^37] |
| **Ambos** | Cobertura terrestre | ESA WorldCover | 10 m | GEE[^38] |
| **Urbano** | Agua superficial actual | Copernicus WB | 300 m, mensual | Sentinel Hub API[^39] |
| **Urbano** | Agua fina | Sentinel-2 NDWI | 10 m | GEE / sentinelhub-py[^40] |
| **Urbano** | Infraestructura agua | OpenStreetMap | vector | osmnx[^41] |
| **Urbano** | Urbanización | VIIRS Night Lights | 500 m | GEE[^38] |
| **Rural** | Red fluvial con caudal | HydroRIVERS v1 | vector | geopandas[^12][^13] |
| **Rural** | Lagos | HydroLAKES | vector | geopandas[^15] |
| **Rural** | Cuencas hidrográficas | HydroBASINS | vector | geopandas[^16] |
| **Rural** | Runoff/escorrentía | ERA5-Land runoff | 9 km, diario | `cdsapi`[^18] |
| **Rural** | Caudales forecast | GloFAS | 0.1°, diario | GloFAS API (ECMWF)[^17] |
| **Rural** | Arrozales | GFSAD 1 km | 1 km | GEE `USGS/GFSAD1000_V1`[^20] |
| **Rural** | Irrigación | FAO GMIA v5 | 9 km | descarga ASCII-grid[^22] |
| **Rural** | Texturas de suelo | SoilGrids (ISRIC) | 250 m | REST API + GeoTIFF[^27] |
| **Rural** | LST diurna/nocturna | MODIS MOD11A1 | 1 km | GEE[^28][^29] |
| **Rural** | Deforestación | Hansen GFW | 30 m | GEE `UMD/hansen/...`[^9] |
| **Rural** | Agua bajo nubes (SAR) | Sentinel-1 SAR | 10 m | GEE `COPERNICUS/S1_GRD`[^32] |
| **Rural** | Densidad de ganado | GLW4 (FAO/ILRI) | 1 km | Harvard Dataverse[^1] |
| **Rural** | Anomalías agua terrestre | GRACE-FO | ~500 km | GEE `NASA/GRACE/...`[^42] |
| **Rural** | Variables bioclimáticas | WorldClim v2 / CHELSA | 1 km | descarga raster[^38] |

***
## 7. Variables Prioritarias por Tipo de Hábitat Rural (Tabla de Decisión ABM)
Esta tabla guía la lógica de activación de hábitats en el motor rural del ABM:

| Tipo Hábitat | Variable Primaria | Umbral de Activación | Lag | Dataset Fuente |
|---|---|---|---|---|
| Charca pluvial | Precipitación 24h | > 15 mm/día | 0 días | CHIRPS[^2] |
| Convergencia topográfica | Nivel freático | < 0.3 m profundidad | 0–7 días | ERA5-Land water table[^1] |
| Cuenca llanura inundación | Caudal del río | > Q75 → desbordamiento | 1 mes | HydroRIVERS + ERA5 runoff[^1] |
| Paleocauce | Caudal + saturación | Post-inundación + sequía | 3 meses | Correlación retardada TWI + runoff[^1] |
| Poza en lecho efímero | Caudal del río | < Q10 (río parado) | 0 días | GloFAS + HydroRIVERS[^1] |
| Pantano / margen lacustre | JRC GSW occurrence | > 50% de tiempo | Permanente | JRC GSW[^34] |
| Arrozal inundado | Calendario cultivo | Meses de inundación | Calendario | GFSAD + FAO[^22][^20] |
| Canal de irrigación | Período de riego | Según zona de riego | Calendario | FAO GMIA[^22] |
| Poza forestal | Lluvia + EVI bosque | > 10 mm/día + EVI > 0.4 | 0–3 días | CHIRPS + Sentinel-2 EVI[^9] |

***
## 8. Diferencias Clave entre el ABM Urbano y el Rural
| Dimensión | *An. stephensi* (Urbano) | *An. gambiae* s.l. (Rural) |
|---|---|---|
| **Hábitat dominante** | Contenedores artificiales | Cuerpos de agua naturales transitorios |
| **Detectabilidad satelital** | Baja (sub-pixel, requiere proxy) | Media-alta (Sentinel-2 10 m, SAR) |
| **Permanencia del hábitat** | Semi-permanente (cisterna) | Muy variable (días a meses) |
| **Actualización de la capa** | Mensual | **Diaria** (crítico) |
| **Variable climática clave** | Temperatura (cría artificial) | Precipitación + caudal fluvial |
| **Dispersión adulto** | Restringida (<2 km urbana) | Mayor (hasta 5+ km; migración eólica) |
| **Densidad de hospedadores** | Alta (ciudad densa) | Baja-media (rural disperso) |
| **Competencia biótica** | Baja (agua limpia sin depredadores) | Alta (depredadores acuáticos en agua natural) |
| **Principal driver de expansión** | Urbanización + comercio | Cambio climático + deforestación |

***
## 9. Tabla Final: Variables del ABM Completo (Urbano + Rural Integrado)
Esta tabla maestra reúne **todas las variables** del sistema ABM integrado *An. stephensi* + *An. gambiae* s.l.:
### Variables Biológicas del Agente Mosquito (compartidas)
- Etapa de vida (huevo, larva I–IV, pupa, adulto)
- Sexo y estado reproductivo
- Estado epidemiológico (susceptible / expuesto / infectivo)
- Progreso del EIP (Período de Incubación Extrínseco)
- Ciclo gonotrófico (días desde última comida de sangre)
- Reserva de energía (azúcar)
- ID del parche de hábitat de origen
- Resistencia a insecticidas (frecuencia alélica kdr)
### Variables del Parche de Hábitat
- Tipo geomorfológico / origen (ver tabla sección 2)
- Especie preferida (parametrizado por tipo de parche)
- Volumen de agua activo (m³)
- Temperatura del agua (°C) ← MODIS LST + ERA5
- Turbidez (proxy) ← NDWI valor
- Cobertura de vegetación emergente ← NDVI / EVI
- Sombra del dosel ← aspect + Hansen EVI
- Densidad larvaria actual (larvas/m²)
- Capacidad de carga (K) ← función del tipo y tamaño
- Estado activo/inactivo ← función de lluvia + caudal + evaporación
### Variables Ambientales Espacializadas (rasters de entrada al ABM)
- Temperatura del aire 2m (ERA5-Land, diaria)
- Precipitación total diaria (CHIRPS, diaria)
- Velocidad y dirección del viento a 850 hPa (ERA5, 6-horario → dispersión eólica)
- Humedad relativa (ERA5-Land T2m + dewpoint)
- Evapotranspiración potencial (ERA5-Land)
- Escorrentía superficial (ERA5-Land)
- Nivel freático estimado (ERA5-Land extended)
- Caudal fluvial (GloFAS / ERA5 runoff)
- LST diurna / nocturna (MODIS MOD11A1)
### Variables Geoespaciales Estáticas (actualizables anualmente)
- Probabilidad de hábitat larvario (raster fusionado, actualización mensual)
- Cobertura terrestre (ESA WorldCover)
- Densidad de población humana (WorldPop)
- Densidad de ganado (GLW4)
- Distancia a ríos (buffer HydroRIVERS)
- Zonas de arrozal / irrigación (GFSAD + FAO GMIA)
- Cobertura forestal y pérdida anual (Hansen GFW)
- Textura del suelo (SoilGrids)
- Elevación y TWI (MERIT DEM + pysheds)
- Índice NDVI / EVI (MODIS / Sentinel-2, mensual)
- Urbanización (VIIRS Night Lights, anual)

***
## 10. Recursos Clave Adicionales
| Recurso | URL / Fuente | Utilidad |
|---|---|---|
| HydroRIVERS shapefile | hydrosheds.org/products/hydrorivers [^13] | Red fluvial global |
| HydroLAKES | hydrosheds.org/products/hydrolakes | Lagos globales |
| HydroBASINS | hydrosheds.org/products/hydrobasins | Cuencas hidrográficas |
| FAO GMIA v5 | fao.org/aquastat/...global-maps-irrigated-areas [^22] | Irrigación global |
| GFSAD1000 GEE | `USGS/GFSAD1000_V1` [^20] | Arrozales / croplands |
| SoilGrids 250m | isric.org/explore/soilgrids [^27] | Texturas de suelo |
| GLW4 Ganado | Harvard Dataverse | Densidad ganado |
| Hansen GFW | `UMD/hansen/global_forest_change_2023_v1_11` [^9] | Deforestación |
| Hardy et al. (2013) | PMC3849348 [^1] | Clasificación geomorfológica hábitats rurales |
| An. funestus ecología | PMC7310514 [^4] | Variables hábitat funestus |
| Framework 2-pasos ML | Springer 2025 [^31] | RF para hábitat larvario rural |

---

## References

1. [Habitat Hydrology and Geomorphology Control the ...](https://pmc.ncbi.nlm.nih.gov/articles/PMC3849348/) - Larval source management is a promising component of integrated malaria control and elimination. Thi...

2. [Anopheles larval species composition and characterization of breeding habitats in two localities in the Ghibe River Basin, southwestern Ethiopia - PubMed](https://pubmed.ncbi.nlm.nih.gov/32046734/) - Different species of Anopheles larvae were identified including An. gambiae s.l., the main malaria v...

3. [Table 4.](https://pmc.ncbi.nlm.nih.gov/articles/PMC3060147/table/T4/) - Pre-adult stages of malaria vectors in semi-arid areas are confronted with highly variable and chall...

4. [Aquatic habitats of the malaria vector Anopheles funestus ...](https://pmc.ncbi.nlm.nih.gov/articles/PMC7310514/) - In rural south-eastern Tanzania, Anopheles funestus is a major malaria vector, and has been implicat...

5. [Anopheles funestus - Wikipedia](https://en.wikipedia.org/wiki/Anopheles_funestus)

6. [Using ecological observations to improve malaria control in areas where Anopheles funestus is the dominant vector](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9161514/) - The most important malaria vectors in sub-Saharan Africa are Anopheles gambiae, Anopheles arabiensis...

7. [Larval ecology of Anopheles coluzzii in Cape Coast, Ghana: water quality, nature of habitat and implication for larval control - Malaria Journal](https://malariajournal.biomedcentral.com/articles/10.1186/s12936-015-0989-4) - Background There is a growing interest in larval control intervention to supplement existing malaria...

8. [Oviposition and Development of Anopheles coluzzii coetzee ... - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC6811990/) - This demonstrated ability to adapt to brackish water for breeding, is indicative of a clear possibil...

9. [Life-table studies revealed significant effects of deforestation on the development and survivorship of Anopheles minimus larvae - Parasites & Vectors](https://parasitesandvectors.biomedcentral.com/articles/10.1186/s13071-016-1611-5) - Background Many developing countries are experiencing rapid ecological changes such as deforestation...

10. [Urban agricultural land use and characterization of mosquito larval habitats in a medium-sized town of Côte d'Ivoire](https://bioone.org/journals/journal-of-vector-ecology/volume-31/issue-2/1081-1710(2006)31%5B319:UALUAC%5D2.0.CO;2/Urban-agricultural-land-use-and-characterization-of-mosquito-larval-habitats/10.3376/1081-1710(2006)31%5B319:UALUAC%5D2.0.CO;2.short) - Urban agriculture is common across Africa and contributes to the livelihoods of urban dwellers. Some...

11. [AQUASTAT - FAO's Global Information System on Water and ...](https://www.fao.org/aquastat/) - AQUASTAT is the FAO global information system on water resources and agricultural water management. ...

12. [HydroRivers | Africa Knowledge Platform](https://akp-dev.biopama.org/dataset/hydrorivers) - HydroRIVERS represents a vectorized line network of all global rivers that have a catchment area of ...

13. [HydroRIVERS - HydroSHEDS](https://www.hydrosheds.org/products/hydrorivers) - HydroRIVERS represents a vectorized line network of all global rivers that have a catchment area of ...

14. [Mapping of mosquito breeding sites in malaria endemic areas in Pos Lenjang, Kuala Lipis, Pahang, Malaysia - Malaria Journal](https://malariajournal.biomedcentral.com/articles/10.1186/1475-2875-10-361) - Background The application of the Geographic Information Systems (GIS) to the study of vector transm...

15. [How to Download Free Global Hydrology Data with HydroSHEDS  Basins, Rivers, Lakes & DEM, Air Temp](https://www.youtube.com/watch?v=edU3bdOZKvk) - In this tutorial, I’ll show you how to access and download all major datasets from HydroSHEDS, inclu...

16. [HydroSHEDS](https://www.hydrosheds.org/) - The HydroSHEDS database provides freely available global digital data layers in support of hydro-eco...

17. [Dataset: era5 — Mosquito Alert Data Portal](https://labs.mosquitoalert.com/metadata_public_portal/notebooks/era5h.html) - Here we provide an example for how to download a time-chunked dataset for a given set of era5-variab...

18. [Complete ERA5 global atmospheric reanalysis - Climate Data Store](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-complete?tab=d_download) - ERA5 is the fifth generation ECMWF atmospheric reanalysis of the global climate covering the period ...

19. [Utilization of vector bionomics, remote sensing and larval habitat characterization data to inform larval source management decision in the high malaria burden state of Kebbi, Nigeria - PubMed](https://pubmed.ncbi.nlm.nih.gov/41184992/) - The consistently high entomology indices, measured protection gaps, productive and abundant larval h...

20. [GFSAD1000: Cropland Extent 1km Multi-Study Crop Mask, Global ...](https://developers.google.com/earth-engine/datasets/catalog/USGS_GFSAD1000_V1) - The GFSAD is a NASA-funded project to provide high-resolution global cropland data and their water u...

21. [Global Food Security Support Analysis Data (GFSAD) Crop ...](https://www.earthdata.nasa.gov/data/catalog/lpcloud-gfsad1kcm-001) - Global Food Security Support Analysis Data (GFSAD) Crop Mask 2010 Global 1 km V001

22. [global-maps-irrigated-areas/latest-version](https://www.fao.org/aquastat/en/geospatial-information/global-maps-irrigated-areas/latest-version/) - Download the Global Map of Irrigation Areas - version 5.0 (0.90 MB - Low resolution PDF-file); Go to...

23. [Irrigation areas v.5 (Global - 5 arc/min) - AmeriGEOSS Community Platform DataHub. (BETA)](https://data.amerigeoss.org/dataset/f79213a0-88fd-11da-a88f-000d939bc5d8) - Global Map of Irrigation Areas - Version 5 Grid with percentage of area equipped for irrigation with...

24. [AQUAMAPS | Land & Water - Food and Agriculture Organization](https://www.fao.org/land-water/databases-and-software/aquamaps/en/)

25. [AQUASTAT - FAO's Global Information System on Water and ...](https://www.fao.org/aquastat/en/databases/) - FAO AQUASTAT

26. [Ovipositional site selection by Anopheles gambiae: influences of substrate moisture and texture](https://www.academia.edu/33493709/Ovipositional_site_selection_by_Anopheles_gambiae_influences_of_substrate_moisture_and_texture) - The influence of substrate moisture (hydration) and grain size (texture) on oviposition was quantifi...

27. [SoilGrids - Global gridded soil information](https://isric.org/explore/soilgrids/) - SoilGrids is one of ISRIC’s flagship products. It is a system for global digital soil mapping that u...

28. [Science Team - MODIS Web - NASA](https://modis.gsfc.nasa.gov/sci_team/pubs/abstract_new.php?id=10018) - The Moderate Resolution Imaging Spectroradiometer website that houses all central information on the...

29. [MODIS Land Surface Temperature Products](https://earthdata.nasa.gov/s3fs-public/2025-04/MOD11_User_Guide_V5.pdf)

30. [Mapping of mosquito breeding sites in malaria endemic areas in ...](https://pmc.ncbi.nlm.nih.gov/articles/PMC3265567/) - Breeding habitats were located at 100-400 m from human settlement. Map of villages with 400 m buffer...

31. [A Two-steps Remote Sensing and Machine Learning Framework for ...](https://link.springer.com/article/10.1007/s41748-025-00865-y) - One crucial aspect of Anopheles mosquito ecology is their dependence on aquatic habitats for breedin...

32. [Identification of Aquatic Habitats of Anopheles Mosquito Using Time-series Analysis of Sentinel-1 data through Google Earth Engine](https://isprs-archives.copernicus.org/articles/XLVIII-3-W3-2024/63/2024/)

33. [Downloading Gridded CHIRPS data sets using python](https://stackoverflow.com/questions/67163212/downloading-gridded-chirps-data-sets-using-python) - I am working with Satellite Gridded dataset from CHIRPS, Here is the link to the dataset: https://da...

34. [JRC Global Surface Water Mapping Layers, v1.4](https://developers.google.com/earth-engine/datasets/catalog/JRC_GSW1_4_GlobalSurfaceWater) - This dataset maps the location and temporal distribution of surface water globally from 1984 to 2021...

35. [MERIT DEM Download Guide & Data Notes | DEM & Elevation Data | GeoDataViewer](https://www.geodataviewer.com/datasets/dem/merit-dem/) - MERIT DEM is a 90-meter global DEM that removes major error components from SRTM3 v2.1 including str...

36. [pysheds/pysheds: Simple and fast watershed delineation in python](https://github.com/pysheds/pysheds) - Features · flowdir : Generate a flow direction grid from a given digital elevation dataset. · catchm...

37. [introapi - WorldPop](https://www.worldpop.org/sdi/introapi/) - WorldPop API Basics Advanced Data API Queries REST API rate-limits The WorldPop Program Application ...

38. [Table 1.](https://pmc.ncbi.nlm.nih.gov/articles/PMC12948167/table/T1/) - Malaria, a life-threatening disease, remains a major global health challenge, particularly in Africa...

39. [Water Bodies 2020-present (raster 300 m), global, monthly – version 2](https://land.copernicus.eu/api/en/products/water-bodies/water-bodies-global-v2-0-300m) - Detects the areas covered by inland water providing the maximum and the minimum extent of the water ...

40. [GitHub - ncortim/s2-ndwi: This repository contains Python code for calculating the Normalized Difference Water Index (NDWI) from Sentinel-2 Level 2A imagery using GDAL. The script reads the Green and Near Infrared (NIR) bands from Sentinel-2 data, computes NDWI, and outputs the result as a Cloud Optimized GeoTIFF (COG).](https://github.com/ncortim/s2-ndwi) - This repository contains Python code for calculating the Normalized Difference Water Index (NDWI) fr...

41. [Fetching OSM Data via Overpass API — Geospatial ETL](https://www.geospatial-etl.com/mastering-geospatial-data-ingestion-in-python/fetching-osm-data-via-overpass-api/) - Query OpenStreetMap via Overpass API in Python — Overpass QL syntax, bounding box scoping, retry log...

42. [Hydrological modeling of geophysical parameters of arboviral and protozoan disease vectors in Internally Displaced People camps in Gulu, Uganda](https://pmc.ncbi.nlm.nih.gov/articles/PMC2275725/) - The aim of this study was to determine if remotely sensed data and Digital Elevation Model (DEM) can...

