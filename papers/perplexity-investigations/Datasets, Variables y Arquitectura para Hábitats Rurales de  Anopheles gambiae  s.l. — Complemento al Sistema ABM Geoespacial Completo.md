# Datasets, Variables y Arquitectura para Hábitats Rurales de *Anopheles gambiae* s.l. — Complemento al Sistema ABM Geoespacial Completo
**Source:** Perplexity Investigation (2026-07-04)
**Language:** Spanish
**File:** papers/perplexity-investigations/Datasets, Variables y Arquitectura para Hábitats Rurales de Anopheles gambiae s.l. — Complemento al Sistema ABM Geoespacial Completo.md

---

## Resumen Ejecutivo

Este documento complementa el reporte sobre *An. stephensi* (vector urbano) y cubre la ecología de cría de los vectores **rurales** del complejo *Anopheles gambiae* s.l., con énfasis en *An. arabiensis*, *An. gambiae* s.s., *An. coluzzii*, *An. funestus* y los vectores forestales asiáticos (*An. dirus*, *An. minimus*). El vector rural opera en un paradigma radicalmente diferente al urbano: sus hábitats son dinámicos, efímeros, dependientes de procesos hidrológicos naturales (ríos, llanuras de inundación, paleocauces, convergencia topográfica, arrozales) y no de infraestructura artificial. La consecuencia directa para el ABM es que la **capa de hábitat rural debe actualizarse diariamente** en función de lluvia acumulada, caudal fluvial, nivel freático y evapotranspiración — no mensualmente como en el escenario urbano.

El estudio seminal de Hardy et al. (2013) establece una clasificación geomorfológica de 10 tipos de hábitats rurales (convergencia topográfica, cuenca de inundación, paleocauce, canal efímero, charca pluvial, pantano, arrozal, canal de irrigación, remanso forestal, salobre costero), cada uno con su propia especie dominante, lag respecto a lluvia y detectabilidad remota. Se catalogan 20+ datasets adicionales específicos para el módulo rural (HydroRIVERS, HydroLAKES, GloFAS, GFSAD, FAO GMIA, SoilGrids, MODIS LST, Hansen GFW, GLW4, GRACE, Sentinel-1 SAR). La arquitectura integrada propone un ABM unificado urbano-rural con un `HabitatType` enum de 14 tipos, un `RuralHabitatEngine` de activación diaria y una tabla maestra de 26 datasets. La Sección 9 compila la tabla final de todas las variables del sistema ABM completo (~40 variables biológicas, de hábitat, ambientales y geoespaciales).

## Contenido Principal

## 1. Ecología de Cría por Especie Rural: Variables Diferenciadoras

### 1.1 *Anopheles gambiae* s.s.
**Hábitat**: Charcos temporales pequeños y soleados formados por lluvia directa; piscinas en lechos de ríos efímeros (estación seca); zonas de convergencia topográfica (nivel freático). Características: exposición solar directa, agua limpia/clara, sin vegetación emergente, sin corriente, perímetro <20 m². Patrón estacional: picos durante el declive de la estación húmeda (junio-julio África Oriental), cuando el agua superficial se fragmenta en charcas aisladas más cálidas. Sensibilidad: lluvia >40 mm/día correlaciona negativamente con densidad larvaria (barre las larvas).

### 1.2 *Anopheles arabiensis*
**Hábitat**: Cuatro tipos geomorfológicos principales (Hardy et al. 2013, Tanzania):
1. **Convergencia topográfica** (cuencas de orden cero): nivel freático sube e intersecta la superficie. Más productivos avanzada la estación seca.
2. **Cuencas de llanura de inundación**: depresiones someras próximas a canales fluviales. Productivas con **lag de 1 mes** del pico de caudal.
3. **Paleocauces**: canales fluviales abandonados (depresiones lineales sinuosas en Landsat). Productivos con **lag de 3 meses**, refugios de estación seca.
4. **Canales fluviales efímeros**: pozas formadas cuando el río deja de fluir. Densidades larvarias más altas del período seco.
**Zoofilia parcial**: más zoofílico y exofágico que *An. gambiae* s.s. → modelar distribución de ganado como capa de hospedadores alternativa.

### 1.3 *Anopheles funestus*
**Hábitat**: Cuerpos de agua **grandes, semipermanentes o permanentes** con **vegetación emergente densa** (carrizos, totoras, juncos); orillas de lagos; arrozales maduros; pantanos. Características diagnósticas: vegetación emergente (predictor positivo más fuerte), sombra de dosel arbóreo, profundidad >50 cm, agua estancada o lenta. Diferencia crítica: evita charcos temporales pequeños y soleados (preferidos de *An. gambiae* s.s.). Importancia epidemiológica: hasta el **90% de las picadas infectivas** en entornos rurales de África Oriental y Meridional.

### 1.4 *Anopheles coluzzii*
**Hábitat**: Tolerante a mayor salinidad y contaminación orgánica que *An. gambiae* s.s. Coloniza zonas costeras, estuarios, manglares y hábitats peri-urbanos con agua degradada. Puede desarrollar larvas en agua con hasta ~30‰ de salinidad (Ghana, Senegal).

### 1.5 *An. dirus*, *An. minimus* (Vectores forestales de Asia)
**Hábitat**: Remansos de ríos sombreados bajo dosel forestal; piscinas de huellas de animales; arroyos de bajo orden con flujo lento. Efecto de deforestación: *An. minimus* muestra 3.8% de pupación bajo bosque cerrado vs. 52.5% en zonas deforestadas, con acortamiento del desarrollo larvario en 1.9–3.3 días. La capa de **pérdida de cobertura forestal** (Hansen/GFW) es una variable dinámica clave.

---

## 2. Clasificación Geomorfológica de los Hábitats Rurales (Tipología ABM)

| Tipo de Hábitat | Proceso Hidrológico | Especie Dominante | Lag Lluvia | Detectabilidad |
|---|---|---|---|---|
| Convergencia topográfica | Nivel freático emerge | *An. arabiensis* | 0 meses (húmeda) | TWI alto |
| Cuenca llanura inundación | Desbordamiento río | *An. arabiensis* | 1 mes | JRC GSW change + buffer |
| Paleocauce | Saturación sedimento | *An. arabiensis* | 3 meses | Landsat textura sinuosa |
| Canal efímero (pozas) | Río deja de fluir | *An. arabiensis/funestus* | Seca | HydroRIVERS order 1–2 |
| Charca pluvial directa | Escorrentía + lluvia | *An. gambiae* s.s. | 0 días | pysheds depressions + CHIRPS |
| Pantano / margen lacustre | Nivel alto permanente | *An. funestus* | Permanente | JRC GSW occurrence >80% |
| Arrozal | Irrigación + lluvia | *An. arabiensis/gambiae* | Calendario | GFSAD + FAO GMIA |
| Canal de irrigación | Flujo controlado | *An. arabiensis* | Continuo | FAO AQUAMAPS |
| Remanso forestal | Suelo + dosel | *An. dirus/minimus* | Húmeda | EVI + Hansen GFW |
| Salobre costero | Agua mixta/mareas | *An. coluzzii/melas* | Mareas+lluvia | NDWI + salinidad ESA |

---

## 3. Datasets Específicos para el Módulo Rural

### 3.1 Red Hidrológica con Caudal: HydroRIVERS
Red vectorial de todos los ríos globales (cuenca ≥10 km² o caudal ≥0.1 m³/s). Información: orden Strahler, longitud, caudal promedio anual. Crítico: >80% de hábitats larvarios están dentro de 400 m de cursos de agua; 95% de hábitats de *An. arabiensis* productivos dentro de 2 km del río.
```python
rivers = gpd.read_file('HydroRIVERS_v10_af.shp')
rivers_small = rivers[rivers['ORD_STRA'] <= 3]
rivers_buffer = rivers_small.to_crs('EPSG:3857').buffer(400).to_crs('EPSG:4326')
```
Complementos: **HydroLAKES** (lagos >0.1 km²) y **HydroBASINS** (cuencas a 12 escalas).

### 3.2 Modelo de Flujo Superficial Dinámico: GloFAS / ERA5-Land Runoff
**GloFAS** (ECMWF/Copernicus): predicciones de descarga fluvial en ≥40,000 estaciones virtuales, 0.1°, hasta 30 días de horizonte. Datos históricos desde 1979.
**ERA5-Land `runoff`**: escorrentía superficial diaria para calcular aporte hídrico a cada cuenca.

### 3.3 Arrozales e Infraestructura de Irrigación
**GFSAD** (NASA/USGS): crop mask global a 1 km (GEE `USGS/GFSAD1000_V1`). GFSAD30 (30 m, 2025) para arrozales individuales.
**FAO AQUASTAT / GMIA v5.0**: % de área equipada para irrigación por celda de 5 arc-min (~9 km).
**Calendarios de cultivo FAO/ORYZA**: determinan cuándo está activo el hábitat `RiceField` en el ABM.

### 3.4 Suelo: ISRIC SoilGrids 250 m
Propiedades relevantes: `clay` (% arcilla, retención de agua), `silt` (% limo, preferencia oviposición), `bdod` (densidad aparente, proxy de compactación). Acceso via REST API o tiles GeoTIFF.

### 3.5 Temperatura de la Superficie del Agua: MODIS LST
Para hábitats someros expuestos, la temperatura del agua puede ser 5–10°C más alta que el aire. `MOD11A1` (Terra, LST diurna/nocturna, 1 km). Correlación con temperatura de charcos (<50 cm): r² > 0.85.

### 3.6 Cobertura Forestal y Deforestación: Hansen GFW
Landsat 30 m, 2000–2023. Bandas: `treecover2000` (% cobertura inicial), `lossyear` (año de pérdida). Crítico para vectores forestales asiáticos y para modelar efecto de deforestación en vectores africanos.

### 3.7 Análisis de Flujo Avanzado: TauDEM / pysheds para Paleocauces
```python
depressions = grid.detect_depressions(grid.fill_pits(dem))
fdir = grid.flowdir(inflated, dirmap=dirmap)
acc = grid.accumulation(fdir, dirmap=dirmap)
branches = grid.extract_river_network(fdir, acc > threshold, dirmap=dirmap)
slope = grid.cell_slopes(inflated, fdir)
low_slope_mask = slope < np.percentile(slope, 10)
twi = np.log((acc + 1) / (np.tan(slope) + 1e-5))
paleochannel_candidates = (twi > np.percentile(twi, 80)) & low_slope_mask & ~depressions
```

### 3.8 Nivel Freático: GRACE/GRACE-FO
Mide anomalías de almacenamiento de agua terrestre (incluye agua subterránea). Resolución ~300–500 km (útil como tendencia estacional). Combinar con ERA5-Land Extended `depth_to_water_table` para nivel freático local.

---

## 4. Variables Físico-Químicas del Hábitat (In-situ → Modelables)

| Variable | Efecto en *An. gambiae* | Fuente en Simulación |
|---|---|---|
| **Turbidez** | Correlación positiva (protección depredadores) | Proxy: NDWI + MODIS sedimento |
| **Corriente** | Estancada/lento → positivo; rápido → letal | HydroRIVERS velocity + ERA5 runoff |
| **pH** | 7.0–8.5 óptimo | SoilGrids pH (proxy) |
| **Temperatura agua** | 25–30°C óptimo | MODIS MOD11A1 + ERA5 T2m |
| **Vegetación emergente** | Predictor + para *An. funestus*; – para *An. gambiae* | NDVI Sentinel-2 |
| **Sombra dosel** | + *An. funestus*; – *An. gambiae* | EVI + Hansen treecover |
| **Superficie hábitat** | <20 m² → *An. gambiae*; grandes → *An. funestus* | JRC GSW + NDWI segmentation |
| **Exposición solar** | Soleado → *An. gambiae*; sombreado → *An. funestus* | Aspect + hillshade DEM |
| **Distancia a casa** | 80–400 m radio vuelo; <300 m alta transmisión | WorldPop + OSM buildings |
| **Presencia ganado** | *An. arabiensis* zoofílico | FAO GLW4 |

---

## 5. Datasets Adicionales para el Módulo Rural

### 5.1 Global Livestock Density (GLW4) — FAO/ILRI
Mapa de densidad de ganado a 1 km (bovinos, ovinos, caprinos, porcinos, aves). Para *An. arabiensis* ajusta probabilidad de comida de sangre animal vs. humano.

### 5.2 MODIS LST Nocturna
Temperatura mínima nocturna del suelo determina supervivencia adulta y tasa de desarrollo de *Plasmodium* (EIP). `MOD11A2`, banda `LST_Night_1km`.

### 5.3 Remote Sensing + ML (2025)
Framework en dos pasos: (1) clasificación de superficie de agua (NDWI + MNDWI + SAR Sentinel-1), (2) predicción de presencia de larvas por características del parche (tamaño, forma, índices espectrales, contexto LULC). Supera a MaxEnt a resolución 10 m.

### 5.4 Sentinel-1 SAR — Agua Bajo Nubes
En zonas tropicales con alta nubosidad, los índices ópticos fallan. Sentinel-1 C-band SAR penetra nubes. **Sentinel-1 Water Index (SWI)**: combinación VV+VH a 10 m, 96.1% precisión en hábitats de *Anopheles*.

---

## 6. Arquitectura Integrada: ABM Mosquito Completo (Urbano + Rural)

### 6.1 Unificación de los Dos Módulos de Hábitat

```python
class HabitatType(Enum):
    # URBANO (An. stephensi)
    CONTAINER_ROOFTOP = "container_rooftop"
    CONTAINER_ORNAMENTAL = "container_ornamental"
    CONTAINER_INDUSTRIAL = "container_industrial"
    # RURAL NATURAL (An. gambiae / An. arabiensis / An. funestus)
    TOPOGRAPHIC_CONV = "topographic_convergence"
    FLOODPLAIN_BASIN = "floodplain_basin"
    PALEOCHANNEL = "paleochannel"
    RIVER_CHANNEL = "river_channel"
    PLUVIAL_POOL = "pluvial_pool"
    SPRING_FED = "spring_fed"
    SWAMP_MARSH = "swamp_marsh"
    # AGRÍCOLA
    RICE_PADDY = "rice_paddy"
    IRRIGATION_CANAL = "irrigation_canal"
    # FORESTAL (Asia)
    FOREST_POOL = "forest_pool"
    # COSTERO
    BRACKISH_WETLAND = "brackish_wetland"
```

### 6.2 Motor de Hábitat Rural: Activación Dinámica Diaria

```python
class RuralHabitatEngine:
    def __init__(self, era5_dataset, chirps_dataset, hydrorivers_gdf, dem_grid):
        self.era5 = era5_dataset
        self.chirps = chirps_dataset
        self.rivers = hydrorivers_gdf
        self.grid = dem_grid

    def get_active_habitats(self, date, species="an_arabiensis"):
        rain_24h = self._get_rainfall(date)
        runoff = self._get_runoff(date)
        river_stage = self._estimate_river_stage(date)
        evaporation = self._get_evaporation(date)
        water_table = self._estimate_water_table(date)

        active = []
        # Charcas pluviales (An. gambiae s.s.)
        if rain_24h > 15:
            active += self._activate_pluvial_pools(rain_24h)
        # Convergencia topográfica (An. arabiensis)
        if water_table < 0.3:
            active += self._activate_topographic_convergence()
        # Cuencas de llanura (lag 1 mes)
        if river_stage[1_month_lag] > 0.8:
            active += self._activate_floodplain_basins()
        # Pozas en cauce efímero (estación seca)
        if river_stage < 0.1 and evaporation < rain_24h + 2:
            active += self._activate_river_channel_pools()
        # Arrozales (calendario FAO)
        if self._is_rice_season(date):
            active += self._activate_rice_paddies()
        return active
```

### 6.3 Tabla Maestra: Todos los Datasets del ABM Completo

| Módulo | Capa | Dataset | Resolución | Acceso Python |
|---|---|---|---|---|
| **Ambos** | Temperatura y precipitación | ERA5-Land | 9 km, diario | `cdsapi` |
| **Ambos** | Precipitación fina | CHIRPS v2.0 | 5 km, diario | xarray |
| **Ambos** | Agua superficial histórica | JRC GSW v1.4 | 30 m | GEE |
| **Ambos** | DEM hidrológico | MERIT DEM | 90 m | tile download |
| **Ambos** | TWI + depresiones | pysheds | == DEM | `pip install pysheds` |
| **Ambos** | Densidad población | WorldPop | 100 m | REST API |
| **Ambos** | Cobertura terrestre | ESA WorldCover | 10 m | GEE |
| **Urbano** | Agua superficial actual | Copernicus WB | 300 m, mensual | Sentinel Hub API |
| **Urbano** | Agua fina | Sentinel-2 NDWI | 10 m | GEE |
| **Urbano** | Infraestructura agua | OSM | vector | osmnx |
| **Urbano** | Urbanización | VIIRS Night Lights | 500 m | GEE |
| **Rural** | Red fluvial | HydroRIVERS v1 | vector | geopandas |
| **Rural** | Lagos | HydroLAKES | vector | geopandas |
| **Rural** | Cuencas | HydroBASINS | vector | geopandas |
| **Rural** | Escorrentía | ERA5-Land runoff | 9 km, diario | `cdsapi` |
| **Rural** | Caudales forecast | GloFAS | 0.1°, diario | GloFAS API |
| **Rural** | Arrozales | GFSAD 1 km | 1 km | GEE `USGS/GFSAD1000_V1` |
| **Rural** | Irrigación | FAO GMIA v5 | 9 km | ASCII-grid download |
| **Rural** | Suelo | SoilGrids | 250 m | REST API + GeoTIFF |
| **Rural** | LST | MODIS MOD11A1 | 1 km | GEE |
| **Rural** | Deforestación | Hansen GFW | 30 m | GEE |
| **Rural** | Agua bajo nubes | Sentinel-1 SAR | 10 m | GEE |
| **Rural** | Densidad ganado | GLW4 (FAO/ILRI) | 1 km | Harvard Dataverse |
| **Rural** | Agua terrestre | GRACE-FO | ~500 km | GEE |
| **Rural** | Bioclimáticas | WorldClim v2 / CHELSA | 1 km | raster download |

---

## 7. Variables Prioritarias por Tipo de Hábitat Rural

| Tipo Hábitat | Variable Primaria | Umbral Activación | Lag | Dataset |
|---|---|---|---|---|
| Charca pluvial | Precipitación 24h | >15 mm/día | 0 días | CHIRPS |
| Convergencia topográfica | Nivel freático | <0.3 m profundidad | 0–7 días | ERA5-Land water table |
| Cuenca llanura | Caudal río | >Q75 (desbordamiento) | 1 mes | HydroRIVERS + runoff |
| Paleocauce | Caudal + saturación | Post-inundación + sequía | 3 meses | TWI + runoff |
| Poza lecho efímero | Caudal río | <Q10 (río parado) | 0 días | GloFAS + HydroRIVERS |
| Pantano / lago | JRC GSW occurrence | >50% tiempo | Permanente | JRC GSW |
| Arrozal | Calendario cultivo | Meses de inundación | Calendario | GFSAD + FAO |
| Canal irrigación | Período riego | Según zona | Calendario | FAO GMIA |
| Poza forestal | Lluvia + EVI bosque | >10 mm/día + EVI >0.4 | 0–3 días | CHIRPS + Sentinel-2 EVI |

---

## 8. Diferencias Clave entre el ABM Urbano y el Rural

| Dimensión | *An. stephensi* (Urbano) | *An. gambiae* s.l. (Rural) |
|---|---|---|
| **Hábitat** | Contenedores artificiales | Cuerpos de agua naturales |
| **Detectabilidad** | Baja (sub-pixel, proxy) | Media-alta (Sentinel-2, SAR) |
| **Permanencia** | Semi-permanente | Muy variable (días a meses) |
| **Actualización capa** | Mensual | **Diaria** |
| **Variable clave** | Temperatura | Precipitación + caudal |
| **Dispersión** | <2 km urbana | Hasta 5+ km + eólica |
| **Densidad hospedadores** | Alta (ciudad) | Baja-media (rural disperso) |
| **Competencia biótica** | Baja | Alta |
| **Driver expansión** | Urbanización + comercio | Cambio climático + deforestación |

---

## 9. Tabla Final: Variables del ABM Completo (Urbano + Rural Integrado)

### Variables Biológicas del Agente Mosquito
Etapa de vida, sexo, estado reproductivo, estado epidemiológico (susceptible/expuesto/infectivo), progreso EIP, ciclo gonotrófico, reserva de energía (azúcar), ID parche origen, resistencia a insecticidas (frecuencia alélica kdr).

### Variables del Parche de Hábitat
Tipo geomorfológico, especie preferida, volumen de agua activo (m³), temperatura del agua (°C), turbidez (proxy NDWI), cobertura vegetación emergente (NDVI/EVI), sombra dosel (aspect + Hansen EVI), densidad larvaria (larvas/m²), carrying capacity K, estado activo/inactivo.

### Variables Ambientales Espacializadas (rasters de entrada)
Temperatura aire 2m (ERA5-Land, diaria), precipitación diaria (CHIRPS), viento 850 hPa (ERA5, 6h → dispersión eólica), humedad relativa (ERA5 T2m + dewpoint), evapotranspiración potencial (ERA5-Land), escorrentía superficial (ERA5-Land), nivel freático estimado (ERA5-Land extended), caudal fluvial (GloFAS/ERA5 runoff), LST diurna/nocturna (MODIS MOD11A1).

### Variables Geoespaciales Estáticas
Probabilidad de hábitat larvario (raster fusionado), cobertura terrestre (ESA WorldCover), densidad población (WorldPop), densidad ganado (GLW4), distancia a ríos (buffer HydroRIVERS), arrozales/irrigación (GFSAD + FAO GMIA), cobertura forestal (Hansen GFW), textura suelo (SoilGrids), elevación y TWI (MERIT DEM + pysheds), NDVI/EVI (MODIS/Sentinel-2), urbanización (VIIRS Night Lights).

---

## 10. Recursos Clave Adicionales

| Recurso | URL / Fuente | Utilidad |
|---|---|---|
| HydroRIVERS | hydrosheds.org/products/hydrorivers | Red fluvial global |
| HydroLAKES | hydrosheds.org/products/hydrolakes | Lagos globales |
| HydroBASINS | hydrosheds.org/products/hydrobasins | Cuencas hidrográficas |
| FAO GMIA v5 | fao.org/aquastat | Irrigación global |
| GFSAD1000 GEE | `USGS/GFSAD1000_V1` | Arrozales/croplands |
| SoilGrids 250m | isric.org/explore/soilgrids | Texturas de suelo |
| GLW4 Ganado | Harvard Dataverse | Densidad ganado |
| Hansen GFW | `UMD/hansen/global_forest_change_2023_v1_11` | Deforestación |
| Hardy et al. (2013) | PMC3849348 | Clasificación geomorfológica |
| *An. funestus* ecología | PMC7310514 | Variables hábitat funestus |
| Framework ML 2 pasos | Springer 2025 | RF para hábitat rural |

---

## References

1. [Habitat Hydrology and Geomorphology - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC3849348/)
2. [Anopheles larval species composition - PubMed](https://pubmed.ncbi.nlm.nih.gov/32046734/)
3. [Table 4 - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC3060147/table/T4/)
4. [Aquatic habitats of An. funestus - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC7310514/)
5. [Anopheles funestus - Wikipedia](https://en.wikipedia.org/wiki/Anopheles_funestus)
6. [Ecological observations for An. funestus control - PMC](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9161514/)
7. [Larval ecology of An. coluzzii in Ghana - Malaria Journal](https://malariajournal.biomedcentral.com/articles/10.1186/s12936-015-0989-4)
8. [Oviposition and Development of An. coluzzii - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC6811990/)
9. [Deforestation effects on An. minimus - Parasites & Vectors](https://parasitesandvectors.biomedcentral.com/articles/10.1186/s13071-016-1611-5)
10. [Urban agricultural land use and mosquito larvae - Journal of Vector Ecology](https://bioone.org/journals/journal-of-vector-ecology/volume-31/issue-2)
11. [AQUASTAT - FAO](https://www.fao.org/aquastat/)
12. [HydroRIVERS Africa Knowledge Platform](https://akp-dev.biopama.org/dataset/hydrorivers)
13. [HydroRIVERS - HydroSHEDS](https://www.hydrosheds.org/products/hydrorivers)
14. [Mapping mosquito breeding sites - Malaria Journal](https://malariajournal.biomedcentral.com/articles/10.1186/1475-2875-10-361)
15. [HydroSHEDS Tutorial - YouTube](https://www.youtube.com/watch?v=edU3bdOZKvk)
16. [HydroSHEDS](https://www.hydrosheds.org/)
17. [ERA5 Mosquito Alert Portal](https://labs.mosquitoalert.com/metadata_public_portal/notebooks/era5h.html)
18. [Complete ERA5 - CDS](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-complete)
19. [Utilization of vector bionomics - PubMed](https://pubmed.ncbi.nlm.nih.gov/41184992/)
20. [GFSAD1000 - GEE](https://developers.google.com/earth-engine/datasets/catalog/USGS_GFSAD1000_V1)
21. [GFSAD Earthdata](https://www.earthdata.nasa.gov/data/catalog/lpcloud-gfsad1kcm-001)
22. [FAO GMIA v5](https://www.fao.org/aquastat/en/geospatial-information/global-maps-irrigated-areas/latest-version/)
23. [Irrigation areas v5 - AmeriGEOSS](https://data.amerigeoss.org/dataset/f79213a0-88fd-11da-a88f-000d939bc5d8)
24. [AQUAMAPS - FAO](https://www.fao.org/land-water/databases-and-software/aquamaps/en/)
25. [AQUASTAT Databases - FAO](https://www.fao.org/aquastat/en/databases/)
26. [Ovipositional site selection - Academia](https://www.academia.edu/33493709/Ovipositional_site_selection_by_Anopheles_gambiae)
27. [SoilGrids - ISRIC](https://isric.org/explore/soilgrids/)
28. [MODIS Science Team](https://modis.gsfc.nasa.gov/sci_team/pubs/abstract_new.php?id=10018)
29. [MODIS LST User Guide](https://earthdata.nasa.gov/s3fs-public/2025-04/MOD11_User_Guide_V5.pdf)
30. [Mapping mosquito breeding sites - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC3265567/)
31. [Two-steps RS+ML framework - Springer](https://link.springer.com/article/10.1007/s41748-025-00865-y)
32. [Aquatic Habitats with Sentinel-1 - ISPRS](https://isprs-archives.copernicus.org/articles/XLVIII-3-W3-2024/63/2024/)
33. [Downloading CHIRPS with Python - StackOverflow](https://stackoverflow.com/questions/67163212/downloading-gridded-chirps-data-sets-using-python)
34. [JRC GSW - GEE](https://developers.google.com/earth-engine/datasets/catalog/JRC_GSW1_4_GlobalSurfaceWater)
35. [MERIT DEM Guide](https://www.geodataviewer.com/datasets/dem/merit-dem/)
36. [pysheds GitHub](https://github.com/pysheds/pysheds)
37. [WorldPop API](https://www.worldpop.org/sdi/introapi/)
38. [Predicting suitability of An. stephensi - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC12948167/table/T1/)
39. [Copernicus Water Bodies](https://land.copernicus.eu/api/en/products/water-bodies/water-bodies-global-v2-0-300m)
40. [s2-ndwi GitHub](https://github.com/ncortim/s2-ndwi)
41. [OSM Overpass API - Geospatial ETL](https://www.geospatial-etl.com/mastering-geospatial-data-ingestion-in-python/fetching-osm-data-via-overpass-api/)
42. [Hydrological modeling of disease vectors - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC2275725/)

---

## Relevancia para MalariaSentinel / Centinela

Este documento completa el **módulo rural del Centinela**, complementando el módulo urbano de *An. stephensi*. La clasificación geomorfológica de 10 tipos de hábitats (Sección 2) se traduce directamente en subtipos de `HabitatPatch` en el ABM. El `RuralHabitatEngine` con activación diaria (Sección 6.2) define el requisito de resolución temporal del sistema — más exigente que el urbano mensual. La tabla maestra de 26 datasets (Sección 6.3) es el inventario completo de fuentes de datos del proyecto. Las diferencias urbano-rural (Sección 8) guían la parametrización diferenciada por especie. La tabla final de variables (Sección 9) es el **registro canónico** de todas las variables del ABM integrado (~40 en 4 dominios), que debe mantenerse sincronizado con el esquema de datos del Centinela a medida que el proyecto evoluciona.
