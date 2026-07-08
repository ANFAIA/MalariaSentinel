# Adaptación Mesa-Geo para ABM MalariaSentinel — Nota M1

**Fecha**: 2026-07-08 · **Autor**: abm-doc-writer (s_956c0459) · **Mesa-Geo verificado**: v0.9.3 (Feb 17 2026)

**Alcance**: pre-trabajo M1 (thin slice Mesa-Geo) para MalariaSentinel Centinela, primer caso Ghana. Restricciones M1:
- 1 especie: *Anopheles gambiae* s.s. rural (*An. stephensi* urbano = M2+).
- 1 tipo de hábitat: charca pluvial (`PLUVIAL_POOL`); clasificación Hardy 2013 (7+ subtipos) = M7+.
- 2 etapas de vida: larva + adulto (huevo + pupa colapsados); 4 etapas = M7+.
- GeoSpace estocástico (vector+raster); ≤30 min/rollout, 100 rollouts ≤50 h. Salida: state `(C=2,T,H,W)` y env `(C_env=4,H,W)`; COG `{aoi}_{scale}_{YYYY}_{MM}_seed{####}.tif` EPSG:4326/UTM; K_max=1000; horizonte mensual.

Convención de flags (grep-friendly): `[M1]` implementa en thin slice · `[custom]` código propio sobre Mesa-Geo · `[M7+]` aplazar al ABM completo (mapeo igual registrado).

---

## §1 — Mosquitos de la malaria (biología → constructos Mesa-Geo)

Mapeo concepto → clase/método, sobre `mesa-geo` v0.9.3 (GitHub `mesa/mesa-geo`).

| Concepto biológico (Perplexity) | Constructo Mesa-Geo | Flag |
|---|---|---|
| Ciclo 4-etapas (huevo→larva→pupa→adulto) colapsado a 2 | `MosquitoAgent.stage ∈ {"larva","adult"}` + `stage_age_days` | `[M1]` colapsado; `[M7+]` huevo/pupa explícitos |
| Ciclo gonotrófico (2–4 d @ 28°C) | `MosquitoAgent.gonotrophic_day: int` + `AnophelesABM._gonotrophic_step()` | `[custom]` |
| EIP *P. falciparum* (~11 d @ 25°C) | `MosquitoAgent.eip_progress: float` + `AnophelesABM._eip_step(temp)` (acumula grado-día sobre 16°C; umbral 110 GD) | `[custom]` |
| Búsqueda hospedador (CO₂, olor, calor) | `MosquitoAgent.host_seeking_state` + `ClimateEngine.host_density_raster` | `[M1]` lookup espacial; `[M7+]` CO₂/olor/señales |
| Enjambre "boids" (apareamiento) | `MosquitoAgent.swarm_id` + `AnophelesABM._boids()` | `[M7+]` |
| Dispersión local (Gaussiana truncada ≤2 km) | `MosquitoAgent._local_disperse(rng, sigma=1000m)` | `[M1]` (simplificado) |
| Migración eólica 120–290 m alt. | `ClimateEngine.get_wind_field(plevel=850)` + `AnophelesABM._long_range_disperse()` | `[M7+]` |
| Antropofilia / HBI (0.04–0.95) | `MosquitoAgent.hbi: float` (0.95 por defecto *gambiae* s.s.) | `[M1]` constante; `[M7+]` evolutivo |
| Endofilia / exofilia | `MosquitoAgent.resting_inside: bool` + `AnophelesABM._resting_step()` | `[M7+]` |
| Alimentación de azúcar (néctar) | `MosquitoAgent.sugar_energy: float` (0..1) | `[M1]` simple |
| Aestivación (RH < 40%, estación seca Sahel) | `MosquitoAgent.aestivating: bool` + `AnophelesABM._aestivation_check(rh)` | `[M7+]` |
| Resistencia kdr (`Vgsc` L995F/S, N1570Y) | `MosquitoAgent.kdr_allele_freq` | `[M7+]` |
| Resistencia metabólica (`CYP6P3` E205D) | `MosquitoAgent.cyp6p3_E205D: bool` | `[M7+]` |
| Resistencia conductual (horario picadura) | `AnophelesABM._activity_mask(hour)` | `[M7+]` |
| Inversión cromosómica 2La/2Rb | `MosquitoAgent.inversion_karyotype` | `[M7+]` |
| Capacidad vectorial Ross-Macdonald | `AnophelesABM.compute_VC()` (post-proceso, validación) | `[M7+]` |
| Capacidad de carga del hábitat (K) | `HabitatPatch.K: int` (≤ `K_max=1000`) | `[M1]` |
| Mortalidad larvaria denso-dependiente | `HabitatPatch.mortality(K, N, density_dep=True)` | `[M1]` |
| Densidad de depredadores acuáticos | `HabitatPatch.predator_pressure` (opcional) | `[M7+]` |
| Preferencias puesta (sustrato, sombra) | `HabitatPatch.prefers_sun: bool` (True para *gambiae* s.s.) | `[M1]` constante; `[M7+]` evolutivo |
| Tasas de desarrollo dependientes de T (Sharpe-DeMichele) | `AnophelesABM._sharpe_demichele(T)` | `[custom]` (helper) |

**Notas M1**: la transición larva→adulto se modela como evento instantáneo cuando `stage_age_days ≥ pupation_threshold(T)`; la mortalidad pupal se suma a la mortalidad larvaria tardía. El scheduler separa tipos `larva` y `adult` para que el EIP se aplique solo al adulto hembra infectado. Estado normalizado `density / K_max` para el canal 0 del state tensor.

---

## §2 — *An. stephensi* (urbano) — alcance M2+, mapeo registrado

No se implementa en M1. Todos los flags son `[M7+]`. El mapeo queda en este doc para el ingeniero M2+.

| Constructo Perplexity (doc 2) | Constructo Mesa-Geo | Flag |
|---|---|---|
| `HabitatPatch` urbano `CONTAINER_ROOFTOP/ORNAMENTAL/INDUSTRIAL` | `HabitatPatch` con `hab_type=HabitatType.CONTAINER_*` | `[M7+]` |
| OSM water containers (`osmnx`) | `HabitatEngine.load_osm_water(bbox)` → `GeoDataFrame` en `GeoSpace` | `[M7+]` |
| Copernicus Water Bodies 300 m (mensual) | `mesa_geo.raster_layers.ImageLayer` en `GeoSpace` | `[M7+]` |
| Sentinel-2 NDWI 10 m (charcas urbanas finas) | `HabitatEngine.load_s2_ndwi(date, bbox)` → `ImageLayer` | `[M7+]` |
| Sentinel-1 SAR (96.1% precisión) | `HabitatEngine.load_s1_sar(date, bbox)` | `[M7+]` |
| WorldPop / HRSL (densidad humana) | `HabitatEngine.load_worldpop()` | `[M7+]` |
| VIIRS Night Lights (proxy urbanización) | `HabitatEngine.load_viirs()` | `[M7+]` |
| `ClimateEngine` (rain/temp/ET/wind) | ya en M1 con CHIRPS+ERA5; M2+ añade viento 850 hPa | `[M7+]` |
| `AnophelesABM.develop_larvae(T)` | `AnophelesABM._develop_larvae()` (curva Sharpe-DeMichele) | `[M7+]` |
| `AnophelesABM.adult_dispersal()` (local+eólica) | ver §1; M2+ activa ambos componentes | `[M7+]` |
| `AnophelesABM.plasmodium_infection()` | `AnophelesABM._infection_step(host)` | `[M7+]` |
| `AnophelesABM.eip_tracking()` | ver §1 (`_eip_step`) | `[M7+]` |
| `EpidemiologyModule` (humanos, biting rate) | `AnophelesABM.human_layer` + `biting_rate(a, hbi)` | `[M7+]` |
| MaxEnt suitability (BIO8/BIO14/BIO3/BIO15) | `HabitatEngine.compute_suitability()` (static layer) | `[M7+]` |
| OSM buildings (densidad intramunicipal) | `HabitatEngine.load_osm_buildings()` | `[M7+]` |

---

## §3 — *An. gambiae* s.l. (rural) — fuente principal M1

M1 implementa **un único** subtipo de `HabitatPatch`: `PLUVIAL_POOL` (TWI-driven). El resto de los 12 subtipos del `HabitatType` enum de Perplexity son `[M7+]`.

| Constructo Perplexity (doc 3) | Constructo Mesa-Geo | Flag |
|---|---|---|
| `HabitatType` enum (12 subtipos rurales) | M1 usa `PLUVIAL_POOL`; resto enums definidos pero inertes | `[M1]` PLUVIAL_POOL; `[M7+]` resto |
| `RuralHabitatEngine.get_active_habitats(date)` | `AnophelesABM._activate_habitats(date)` (solo `PLUVIAL_POOL`) | `[M1]` |
| Activación charca pluvial (umbral `rain_24h > 15 mm`) | `HabitatPatch.activate(rain_24h, T)` en `step()` | `[M1]` |
| pysheds — TWI (pre-proceso) | `HabitatEngine.compute_twi(dem_path)` (helper en `mal-commonlib`) | `[M1]` |
| pysheds — `detect_depressions` (máscara de charca) | `HabitatEngine.detect_pluvial_pools(dem_path)` → `GeoDataFrame` | `[M1]` |
| MERIT DEM 90 m / SRTM 30 m | `DataLayer("dem", path, crs)` en `GeoSpace` (raster) | `[M1]` |
| ERA5-Land (T2m, precipitación, evaporación) | `ClimateEngine.load_era5_land(date_range, bbox)` (vía `cdsapi`) | `[M1]` |
| CHIRPS v2.0 (lluvia diaria 5 km) | `ClimateEngine.load_chirps(date_range, bbox)` (vía xarray) | `[M1]` |
| MODIS NDVI (MOD13A3 mensual 1 km) | `ClimateEngine.get_ndvi(date)` (canal 3 del env tensor) | `[M1]` |
| HydroRIVERS (buffer 400 m hábitats perifluviales) | `HabitatEngine.load_hydrorivers(bbox)` (GeoDataFrame en `GeoSpace`) | `[M7+]` |
| HydroLAKES / HydroBASINS | `HabitatEngine.load_hydrolakes/basins()` | `[M7+]` |
| GloFAS (caudal forecast 0.1°) | `ClimateEngine.get_glofas_discharge(date)` | `[M7+]` |
| SoilGrids 250 m (`clay`, `silt`, `bdod`) | `HabitatEngine.load_soilgrids()` | `[M7+]` |
| MODIS LST (MOD11A1) → T agua somera | `ClimateEngine.get_lst(date)` | `[M7+]` (M1 usa T2m como proxy) |
| Hansen GFW (deforestación 30 m) | `HabitatEngine.load_gfw()` | `[M7+]` |
| GRACE/GRACE-FO TWS | `ClimateEngine.get_grace_tws()` | `[M7+]` |
| GLW4 ganado (zoofilia *arabiensis*) | `HabitatEngine.load_glw4()` | `[M7+]` (M1 fija `hbi=0.95`) |
| Sentinel-1 SAR (penetra nubes) | `HabitatEngine.load_s1_sar()` | `[M7+]` |
| GFSAD arrozales / FAO GMIA irrigación | `HabitatEngine.load_gfsad()/load_gmia()` | `[M7+]` |
| WorldClim BIO1–BIO19 (static) | `HabitatEngine.load_worldclim()` | `[M7+]` |
| EVI Hansen (forestal *minimus/dirus*) | `HabitatEngine.load_hansen_evi()` | `[M7+]` |
| MODFLOW (nivel freático) | `ClimateEngine.get_water_table()` | `[M7+]` |
| WorldPop (densidad humana rural) | `HabitatEngine.load_worldpop()` | `[M7+]` (M1 ignora) |
| ESA WorldCover 10 m (filtro charca natural) | `HabitatEngine.load_worldcover()` | `[M1]` (filtro landcover=wetland/water) |

**Notas M1**: la capa de entrada es `habitat_patches_YYYYMM.gpkg` segmentado de depresiones TWI (pysheds) filtrado por ESA WorldCover. La activación se evalúa **mensualmente** (contrato de salida); internamente el motor agrega CHIRPS diario y ERA5-Land 6-horario para acumular lluvia de 7 d previas. El M1 **no simula huevo ni pupa**: el `HabitatPatch` produce adultos que se depositan directamente en `GeoSpace` como `MosquitoAgent(stage="adult")`.

---

## §4 — Tabla resumen de constructos

| Constructo Mesa-Geo | Impl M1 | M7+ | Sección Perplexity |
|---|---|---|---|
| `mesa_geo.GeoAgent` (base) | sí | sí | biología §6.3; stephensi §6.2 |
| `MosquitoAgent(GeoAgent)` | sí (2 etapas) | 4 etapas | biología §2; stephensi §6.2 |
| `HabitatPatch(GeoAgent)` | sí (`PLUVIAL_POOL`) | 12 subtipos enum | gambiae §2, §6.1 |
| `AnophelesABM(mesa.Model)` | sí | sí | stephensi §6.3; gambiae §6 |
| `mesa_geo.GeoSpace` (raster+vector) | sí (raster + 1 vector) | multi-capa | stephensi §6.2 |
| `mesa.time.BaseScheduler` / `RandomActivationByType` | sí (types: `patch`,`larva`,`adult`) | sí | mesa core |
| `ClimateEngine` (rain/temp/ET/wind) | parcial (CHIRPS+ERA5-Land) | full (GloFAS, LST, GRACE, viento) | stephensi §6.3; gambiae §3 |
| `HabitatEngine` (rural daily activation) | parcial (TWI + pluvial) | full (12 subtipos) | gambiae §6.2 |
| `DataLayers` (DEM, ERA5, CHIRPS, MODIS NDVI) | parcial | full (Sentinel-1, SoilGrids, etc.) | stephensi §3; gambiae §3 |
| `EIP tracker` (grado-día) | `[custom]` en M1 | sí | biología §7 |

---

## §5 — API drift (mesa-geo v0.9.3, Feb 17 2026)

- **Repo URL**: Perplexity cita `https://github.com/projectmesa/mesa-geo`; el repo activo es `https://github.com/mesa/mesa-geo` (organización `mesa`). README verificado en `https://github.com/mesa/mesa-geo` y docs en `https://mesa-geo.readthedocs.io/en/stable/`.
- **Scheduler**: Mesa-Geo **no provee** schedulers propios. Usar `mesa.time.{BaseScheduler, RandomActivation, RandomActivationByType, StagedActivation}`. Recomendado M1: `RandomActivationByType` con `["patch","larva","adult"]` y `model.agents_by_type[T].do("step")`.
- **`GeoAgent.__init__`**: la firma actual es `GeoAgent(model, geometry, crs)` — **sin** `unique_id` como primer argumento. La firma `(self, unique_id, model, geometry, crs)` que muestran los docs de Perplexity es de una versión anterior (Mesa 0.9 / mesa-geo pre-v0.6). Mesa asigna `unique_id` automáticamente al añadir el agente al scheduler. Los M1 engineers deben eliminar `unique_id` de los `__init__` propuestos por Perplexity.
- **`GeoSpace.__init__`**: `GeoSpace(crs="epsg:3857", warn_crs_conversion=True)`. El default es Web Mercator, no EPSG:4326. Para el contrato M1 instanciar explícitamente `GeoSpace(crs="EPSG:4326")` (o UTM del AOI).
- **Capas raster**: `mesa_geo.raster_layers.{ImageLayer, RasterLayer}` (≥ v0.6). `GeoSpace.add_layer()` acepta vector (`GeoDataFrame`) o raster; el CRS del layer se convierte al del `GeoSpace` con `warn_crs_conversion=True` por defecto.
- **Version check**: `pip show mesa-geo` → v0.9.3 (Feb 17, 2026). Instalación: `pip install -U mesa-geo` o `pip install -U -e git+https://github.com/mesa/mesa-geo.git#egg=mesa-geo`.

---

**Referencias Perplexity** (líneas, worktree):  
`papers/perplexity-investigations/Mosquitos de la Malaria...md:1-641` · `...An. stephensi...md:1-591` · `...An. gambiae s.l...md:1-512`.  
Mesa-Geo: `https://github.com/mesa/mesa-geo` v0.9.3, fuente `mesa_geo/geospace.py` y `mesa_geo/geoagent.py` consultadas vía `webfetch`.
