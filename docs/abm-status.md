# MalariaSentinel — Estado del Proyecto y Arquitectura

> Actualizado: 2026-07-20 · ABM Python: **v0.5.0** · ABM C++ (mal-abm-fast): **F1 complete** · Tests: **71/71 Python + 60/60 C++ + 5/5 parity**

---

## 1. Big Picture — El pipeline SDSS

MalariaSentinel es un **Sistema de Soporte de Decisiones Espacial (SDSS)** para la eliminacion de malaria. El pipeline tiene 6 etapas:

```
INGESTA → SUITABILIDAD → ABM → DATASET → U-Net → PREDICCION
```

**Flujo de datos**: El ABM (etapa 3) genera state COGs mensuales → el dataset builder (etapa 4) los convierte en pares de entrenamiento → la U-Net (etapa 5) aprende a predecir el siguiente paso → la prediccion (etapa 6) produce risk maps para el programa de eliminacion.

**Relacion ABM ↔ U-Net**: El ABM es el "profesor" (lento, preciso, agente-por-agente). La U-Net es el "estudiante" (rapido, aproximado, prediccion 100x mas veloz). La U-Net entrena con datos del ABM y luego reemplaza al ABM en produccion.

```
ABM (lento, preciso)  →  genera datos  →  U-Net entrena
                                                  │
U-Net (rapido, aproximado)  →  predice riesgo mensual  →  decisiones de intervencion
```

---

## 2. Monorepo — Paquetes activos

```
MalariaSentinel/
  mal-commonlib/          # Base compartida: config, paths, loaders de datos
  mal-core/               # Logica estable del pipeline (U-Net, SDSS, API)
  mal-execution/          # CLI batch, scripts CESGA/Hetzner
  mal-abm-fast/           # ABM en C++20 (motor de alto rendimiento)
  mal-data-explorer/      # Visualizacion de datasets, analisis de sesgo
  agents/                 # Infraestructura de agentes, memoria, loops
  mal-ghana-sim/          # [DEPRECATED] Experimento original
  data/                   # Datasets (gitignored raw data)
  papers/                 # Papers de investigacion
  terrain/                # DEM SRTM tiles
  runs/                   # Salidas de experimentos (gitignored)
```

**Regla de dependencias**: Nada depende de los paquetes de experimentos. Cuando un experimento se estabiliza, se promueve a `mal-core` o `mal-commonlib`.

### Diagrama de dependencias

```
mal-commonlib  (sin dependencias — la base)
    │
    ├── mal-core  (depende de mal-commonlib)
    │       │
    │       └── mal-execution  (depende de mal-core + mal-commonlib)
    │
    └── mal-ghana-sim  [DEPRECATED] (dependia de mal-commonlib)

mal-data-explorer  (sin dependencias — scripts sueltos)
mal-abm-fast       (sin dependencias Python — C++20 puro + CMake)
```

---

## 3. mal-commonlib — Base compartida

**Ubicacion**: `mal-commonlib/src/mal_commonlib/`
**Dependencias**: Ninguna (es la fundacion)

### Modulos

| Modulo | Funcion |
|---|---|
| `aoi.py` | Definiciones de Area of Interest (bbox, CRS, escala) |
| `config.py` | Configuracion compartida (paths, RUNS_DIR) |
| `data/loaders/chirps.py` | Cargador CHIRPS (precipitacion) |
| `data/loaders/dem.py` | Cargador MERIT DEM (elevacion) |
| `data/loaders/era5.py` | Cargador ERA5-Land (reanalisis) |
| `data/loaders/jrc_gsw.py` | Cargador JRC Global Surface Water |
| `data/loaders/modis.py` | Cargador MODIS NDVI (MOD13A3) |
| `data/loaders/worldcover.py` | Cargador ESA WorldCover (uso de suelo) |
| `data/utils.py` | Utilidades de procesamiento de datos |
| `terrain/twi.py` | Topographic Wetness Index |

### Tests

8 test files: `test_aoi.py`, `test_chirps.py`, `test_dem.py`, `test_era5.py`, `test_jrc_gsw.py`, `test_modis.py`, `test_twi.py`, `test_worldcover.py`

---

## 4. mal-core — Logica estable del pipeline

**Ubicacion**: `mal-core/src/mal_core/`
**Dependencias**: mal-commonlib, torch, fastapi, typer, pydantic, pyyaml
**CLI**: `malariasim` (entry point)

### Modulos

| Modulo | Funcion | Estado |
|---|---|---|
| `cli.py` | CLI Typer: `predict`, `status`, `serve` | Implementado |
| `unet.py` | U-Net 4 bloques down/up, 32-64-128-256, MSE + soft-Dice | Implementado |
| `unet_wrapper.py` | Wrapper de inferencia U-Net | Implementado |
| `train.py` | Loop de entrenamiento U-Net (Adam, val Dice) | Implementado |
| `dataset.py` | Dataset builder: pares (state_t + env) → state_{t+1} | Implementado |
| `predict.py` | Pipeline de prediccion: load model → inference → GeoTIFF | Implementado |
| `env.py` | Carga de env stack (4 canales: water_frac, rain, temp, ndvi) | Implementado |
| `state.py` | Carga de estado ABM desde COGs | Implementado |
| `registry.py` | Registro de modelos (model.yaml manifests) | Implementado |
| `scenario.py` | Schema YAML de escenarios (intervenciones + clima) | Implementado |
| `server.py` | FastAPI: `/predict`, `/aoi/{name}/risk`, `/aoi/{name}/status` | Implementado |
| `aoi.py` | AOI + aggregators (promoted desde commonlib) | Implementado |

### U-Net Arquitectura

```
Input: (state_t + env) = (6, 128, 128)  →  Target: state_{t+1} = (2, 128, 128)
4 bloques down/up: 32 → 64 → 128 → 256 → bottleneck(512)
BatchNorm + ReLU, skip connections (concat)
Loss: MSE + 0.5 × soft-Dice
```

### CLI

```bash
# Prediccion
malariasim predict --aoi ghana --scale regional --year 2026 --month 6 --model best_model

# Estado
malariasim status --aoi ghana

# Servidor
malariasim serve --host 127.0.0.1 --port 8000
```

### Como mal-core se conecta con el ABM

mal-core consume la salida del ABM (state COGs) para entrenar la U-Net y generar predicciones:

1. **ABM** (C++ o Python) produce state COGs mensuales en `runs/`
2. **mal-core/dataset.py** lee los COGs y construye pares de entrenamiento (state_t → state_{t+1})
3. **mal-core/train.py** entrena la U-Net con esos pares
4. **mal-core/predict.py** carga la U-Net entrenada y genera risk maps
5. **mal-core/server.py** expone la prediccion via REST API

---

## 5. mal-execution — CLI batch y scripts

**Ubicacion**: `mal-execution/scripts/`
**Dependencias**: mal-core, mal-commonlib
**Estado**: Scripts operacionales, no es un paquete Python empaquetado

### Scripts CESGA (HPC)

| Script | Funcion |
|---|---|
| `cesga-run/cesga_config.sh` | Configuracion del cluster CESGA FT3 |
| `cesga-run/manage_jobs.sh` | Gestion de jobs SLURM |
| `cesga-run/prepare_data.sh` | Preparacion de datos en el cluster |
| `cesga-run/run_abm.sh` | Ejecucion del ABM en el cluster |
| `cesga-run/setup_env.sh` | Setup del entorno en el cluster |

### Scripts Hetzner (Cloud)

| Script | Funcion |
|---|---|
| `hetzner-run/cloud-init.yaml` | Cloud-init para VMs Hetzner |
| `hetzner-run/hetzner-run` | Script de ejecucion en cloud |
| `hetzner-run/lib/common.sh` | Utilidades compartidas |
| `hetzner-run/lib/jobs.sh` | Gestion de jobs |
| `hetzner-run/lib/sync.sh` | Sincronizacion de datos |
| `hetzner-run/lib/vm.sh` | Gestion de VMs |

### Scripts de entrenamiento

| Script | Funcion |
|---|---|
| `train_unet.py` | Entrenamiento U-Net (batch) |
| `train_unet_subsample.py` | Entrenamiento con subsampling |
| `validate_unet.py` | Validacion U-Net |

### Como mal-execution orquesta el ABM

mal-execution es la capa de orquestacion para ejecutar el ABM en escenarios reales (HPC o cloud):

1. `cesga-run/run_abm.sh` invoca `mal_abm_fast run` (C++) o el Python ABM
2. `prepare_data.sh` descarga y prepara los env COGs y habitat gpkg
3. `manage_jobs.sh` gestiona multiples jobs SLURM para rollouts paralelos
4. Los resultados se sincronizan de vuelta con `sync.sh`

---

## 6. mal-abm-fast — Motor ABM en C++

**Ubicacion**: `mal-abm-fast/`
**Estado**: M-perf F1 **complete** (60/60 ctest + 5/5 parity pytest)
**Objetivo**: 100 rollouts en <5 min wall en un nodo FT3 ilk

### Que es?

Re-implementacion en C++20 del ABM Python reference (`mal-ghana-sim/abm/`). El motor es **black-box equivalente**: dados los mismos inputs (env, habitat, seed, days), produce los mismos state COGs que el Python.

### Arquitectura

```
                          main.cpp (CLI11)
                               │
                               ▼
               ┌───────────────────────────────┐
               │      CoordinatorModel         │
               │   (AOI, current_date,         │
               │    ClimateEngine,             │
               │    HabitatEngine, Prng,       │
               │    dynamic-patch registry)    │
               └───────┬───────┬───────┬───────┘
                       │       │       │
                       ▼       ▼       ▼
               ┌───────┐ ┌───┐───┐ ┌────────────────┐
               │       │ │   │   │ │                │
        ClimateEngine  │ │Habitat│ │ MosquitoSubmodel
        (env reader +  │ │Engine │ │ (SoA, PRNG,
         set_day())    │ │(gpkg  │ │  7 per-day ops)
               │       │ │reader)│ │                │
               ▼       ▼ │   │   ▼ ▼                │
               └───────┴─┴───┴───┴────────────────┘
                               │
                               ▼
               ┌───────────────────────────────┐
               │  output_contract.{hpp,cpp}    │
               │  write_state_cog (GDAL)       │
               │  write_state_sidecar (json)   │
               └───────────────────────────────┘
```

### Componentes C++

| Header | Funcion |
|---|---|
| `wire.hpp` | Tipos de datos compartidos + constantes (K_MAX, EIP, etc.) |
| `aoi.hpp` | Area of Interest (bbox, cells_per_side, transform) |
| `prng.hpp` | PRNG xoshiro256** (determinista, por-rollout aislado) |
| `eip.hpp` | EIP: accumulate_eip (grado-dias, NaN-safe) |
| `dispersal.hpp` | Dispersacion de adultos (kernel Gaussiano, clip) |
| `climate.hpp` | ClimateEngine (lector NetCDF/TIF, lookups por dia) |
| `env_reader.hpp` | Lector de env NetCDF4 (rainfall, temp, water_frac, ndvi) |
| `habitat_engine.hpp` | HabitatEngine (lector gpkg, materialise patches) |
| `coordinator.hpp` | CoordinatorModel (activacion, dynamic patches, densidad) |
| `mosquito_state.hpp` | MosquitoSoA (struct-of-arrays, poblacion) |
| `mosquito_submodel.hpp` | MosquitoSubmodel (7 operaciones diarias) |
| `engine.hpp` | Engine facade (orchestration) |
| `output_contract.hpp` | Escritura COG + sidecar JSON (GDAL) |
| `seeding.hpp` | Seeding modes (UNIFORM, RANDOM_VIABLE, EXPLICIT) |

### Constantes del motor C++ (actualizadas en F1)

| Constante | Valor C++ | Valor Python | Notas |
|---|---|---|---|
| `K_MAX` | 1000 | 1000 | Iguales |
| `INIT_FRAC` | 0.30 | 0.30 | Iguales |
| `EIP_BASE_C` | 16.0 | 16.0 | Iguales |
| `EIP_THRESHOLD_GD` | 110.0 | 110.0 | Iguales |
| `ADULT_DISPERSE_PROB` | **0.10** | 0.20 | C++ usa 10% (Python 20%) |
| `ADULT_DISPERSE_SIGMA_M` | **300.0** | 1000.0 | C++ sigma=300m (Python 1km) |
| `ADULT_DISPERSE_MAX_M` | **800.0** | 2000.0 | C++ cap 800m (Python 2km) |
| `BIRTH_FECUNDITY` | **0.10** | 0.005 (xK) | C++: 10% adultos/2 |
| `PLUVIAL_POOL_RAIN_THRESHOLD_MM` | **50.0** | 15.0 | C++ 50mm (Python 15mm) |
| `LARVA_BH_S0` | 0.95 | — | Mortalidad Beverton-Holt |
| `LARVA_BH_ALPHA` | 0.05 | — | Coeficiente competencia |
| `ADULT_DAILY_MORT_BASE` | 0.90 | — | Mortalidad Lardeux 2009 |
| `ADULT_OPT_C` | 26.0 | — | Temperatura optima |
| `ADULT_SIGMA` | 7.0 | — | Ancho respuesta termica |
| `LARVA_DESICCATION_GRACE_DAYS` | 5 | — | Dias gracia desecacion |
| `LARVA_DESICCATION_DAILY_RATE` | 0.10 | — | Tasa desecacion |

**Diferencias clave C++ vs Python**: Parametros calibrados para M-perf budget (30k parches, 30 dias, 60s). Dispersion y nacimiento mas conservadores. Umbral de lluvia subido a 50mm.

### Operaciones diarias del submodel (7 ops, Python tiene 5)

| # | Operacion | Descripcion |
|---|---|---|
| 1 | `larva_mortality_inactive` | Elimina larvas en parches inactivos |
| **2.5** | `larva_mortality_density` | Mortalidad Beverton-Holt density-dependent |
| 2 | `larva_growth` | Crecimiento + acumulacion EIP |
| 3 | `larva_to_adult` | Promocion larva→adulto (eip ≥ 110 GD) |
| 4 | `adult_dispersal` | 10% se mueven (Gaussiana, σ=300m, cap 800m) |
| **6** | `adult_mortality` | Mortalidad Lardeux thermo-dependent |
| 5 | `birth` | binomial(n_adults/2, 0.10) nuevas larvas |

**Nuevas en C++**: `larva_mortality_density` y `adult_mortality`.

### Flujo por dia

```
1. activate_patches(day)
   → Consulta ClimateEngine → activated = (rain > 50mm)
   → Evalua PLUVIAL_POOL: TWI>8 AND water>0 AND rain>50mm

2. to_dataframe()
   → Materializa todos los parches en vector<PatchState>

3. advance_day(aoi, patch_states)
   → larva_mortality_inactive
   → larva_mortality_density (Beverton-Holt)
   → larva_growth (eip += max(0, T - 16°C))
   → larva_to_adult (eip ≥ 110 GD)
   → adult_dispersal (10%, Gaussiana σ=300m, cap 800m)
   → adult_mortality (Lardeux)
   → birth (binomial(n_adults/2, 0.10))

4. snapshot(...) (fin de mes)
   → aggregate_density + suitability_grid
   → write_state_cog (2-band COG + sidecar)
```

### CLI del motor C++

```bash
# Single rollout
./mal_abm_fast run \
    --aoi ghana --year 2024 --month 6 --seed 1 --days 30 \
    --env data/runs/ghana/ghana_regional_2024_06_env.tif \
    --habitat data/runs/ghana/ghana_regional_2024_06_habitat_patches.gpkg \
    --output data/runs/ghana/ghana_regional_2024_06_state.tif

# 100 rollouts (M-perf target)
./mal_abm_fast run --n-rollouts 100 \
    --aoi ghana --year 2024 --month 6 --seed 1 --days 30 \
    --env data/runs/ghana/ghana_regional_2024_06_env.tif \
    --habitat data/runs/ghana/ghana_regional_2024_06_habitat_patches.gpkg \
    --output /tmp/rollout/state.tif

# Daily snapshots (time-series para U-Net)
./mal_abm_fast run --snapshot-every 1 --n-rollouts 10 \
    --aoi ghana --year 2024 --month 6 --seed 1 --days 30 \
    --env data/runs/ghana/ghana_regional_2024_06_env.tif \
    --habitat data/runs/ghana/ghana_regional_2024_06_habitat_patches.gpkg \
    --output /tmp/rollout/state.tif
```

### CLI flags

| Flag | Default | Descripcion |
|---|---|---|
| `--aoi` | — | AOI slug |
| `--bbox` | — | Custom bbox W,S,E,N |
| `--env` | — | Path a env GeoTIFF/NetCDF |
| `--habitat` | — | Path a habitat GeoPackage |
| `--output` | — | Output path para state COG |
| `--year` | 2024 | Ano de inicio |
| `--month` | 6 | Mes de inicio (1-12) |
| `--seed` | 1 | PRNG seed |
| `--days` | 30 | Dias de simulacion |
| `--n-rollouts` | 1 | Numero de rollouts |
| `--snapshot-every` | 0 | Frecuencia snapshots (0=solo final) |
| `--crs` | EPSG:4326 | CRS del output |
| `--resolution-m` | 1000 | Resolucion metros |
| `--scale` | regional | regional/national/continental |

### Input: Env NetCDF (v2.0)

| Variable | Dimensiones | dtype | Unidades |
|---|---|---|---|
| `rainfall` | (time,y,x) | float32 | mm/day |
| `water_temp_c` | (time,y,x) | float32 | °C |
| `water_frac` | (time,y,x) | float32 | [0,1] |
| `ndvi` | (time,y,x) | float32 | [0,1] |
| `twi` (optional) | (y,x) | float32 | — |

### Output: State COG (v1.1)

- **Band 1**: density (mosquitos / K_MAX ∈ [0,1])
- **Band 2**: suitability (adult density by cell / K_MAX ∈ [0,1])
- **Sidecar JSON**: crs, transform, seed, n_rollouts, rollout_index, contract_version, band_names, k_max, generator_version

### Determinismo

PRNG xoshiro256** canonico. Dos runs con mismo `(seed, i, days, AOI, env, habitat)` producen bytes identicos del COG.

### Seeding modes

| Modo | Descripcion |
|---|---|
| `UNIFORM` | Legacy: init_frac de K en cada parche |
| `RANDOM_VIABLE` | Solo parches viables (water_frac > 0, TWI > 8) |
| `EXPLICIT` | Seed instructions explicitas |

### Tests

```bash
# C++ unit tests (GoogleTest)
ctest --test-dir mal-abm-fast/build --output-on-failure
# 60 tests

# Python parity test (F1.e)
cd mal-ghana-sim && uv run pytest tests/test_abm_fast_parity.py -v
# 5 tests, tolerance: max(2e-2 abs, 12% rel)
```

### Build (macOS)

```bash
brew install cmake ninja pkg-config gdal eigen cli11 nlohmann-json googletest
cmake -S mal-abm-fast -B mal-abm-fast/build -G Ninja \
      -DCMAKE_BUILD_TYPE=Release
cmake --build mal-abm-fast/build -j
ctest --test-dir mal-abm-fast/build --output-on-failure
```

---

## 7. mal-data-explorer — Visualizacion de datasets

**Ubicacion**: `mal-data-explorer/`
**Dependencias**: pandas, matplotlib, geopandas, shapely, cartopy, contextily, pypdf, scipy

### Scripts

| # | Script | Descripcion |
|---|---|---|
| 01 | `01_dataset_metadata.py` | Auditoria metadata GBIF (GUF) |
| 02 | `02_map_anopheles_guf.py` | Mapa ocurrencias Guayana Francesa |
| 03 | `03_map_ghana.py` | Mapa sitios larvarios IDIT Ghana |
| 04 | `04_map_colombia.py` | Mapa VectorLink Colombia |
| 05 | `05_map_react.py` | Mapa REACT Burkina Faso + Cote d'Ivoire |
| 06 | `06_compare_three_maps.py` | Comparacion 3 datasets |
| 07 | `07_compare_datasets.py` | Comparacion cuantitativa 6 datasets |
| 08 | `08_explore_react.py` | Exploracion dataset REACT |
| 09 | `09_two_focus_analysis.py` | Analisis patron dos focos |
| 10 | `10_two_focus_plot.py` | Visualizacion patron dos focos |
| 11 | `11_bias_analysis.py` | Analisis sesgo dataset GUF |
| 12 | `12_bias_plot.py` | Visualizaciones sesgo |

### Conexion con el ABM

Independiente del ABM. Analiza datasets de ocurrencia de Anopheles para entender distribucion geografica, identificar sesgos, y validar que el ABM genera mosquitos en zonas correctas.

---

## 8. agents/ — Infraestructura de agentes

### Loops

| Agente | Funcion |
|---|---|
| `test-fixer` | Itera verificacion hasta exit 0 |
| `code-reviewer` | Revisa diffs (solo lectura) |
| `doc-researcher` | Busca en KB, luego web |
| `security-auditor` | Auditoria OWASP (solo lectura) |
| `memory-curator` | Unico writer al knowledge graph |
| `improvement-agent` | Revisa + aplica mejoras |

### Memory module

- Neo4j + Graphiti MCP docker stack
- Schema 8 labels: Component, Investigation, Architecture, Pattern, Pitfall, Tool, Operational, Preference
- 8 herramientas custom: memory_audit, memory_init, memory_node, memory_query, memory_recall, memory_rel, memory_seed, memory_status

### Research harness

Pipeline para ciclos de investigacion: search → write → review → hypothesize.

---

## 9. Ciclo de vida del mosquito (ABM)

### Estados y transiciones

```
[*] → Larva: Seeding (n_patches × K × 0.3)

Larva → Larva: Mortalidad inactive patches
Larva → Larva: Mortalidad Beverton-Holt
Larva → Larva: Crecimiento (eip += max(0, T - 16°C))
Larva → Adulto: eip ≥ 110 GD (~11 dias @ 25°C)

Adulto → Adulto: Dispersal (10%/dia, σ=300m, cap 800m)
Adulto → Adulto: Mortalidad Lardeux [C++ only]
Adulto → Adulto: Birth (binomial(n_adults/2, 0.10))
```

### Simplificaciones (M1)

- Etapas colapsadas: huevo + pupa ignorados (M7+)
- Sin ciclo gonotrofico (M7+)
- Sin busqueda de hospedador (M7+)
- Sin infeccion Plasmodium (M7+)
- 1 sola especie: An. gambiae s.s. (M8+)

---

## 10. Contrato de salida

### State COG

- **Band 1**: density (count / K_MAX, [0,1])
- **Band 2**: suitability (n_adults / K_MAX, post-dispersal, [0,1])
- **Sidecar JSON**: crs, transform, seed, contract_version, band_names, k_max

### Env Tensor

- **Band 0**: water_frac [0,1] (JRC GSW 30m)
- **Band 1**: rainfall mm/mes crudos
- **Band 2**: temp_suitability [0,1] (Mordecai)
- **Band 3**: ndvi [0,1]

---

## 11. Milestones

| Milestone | Nombre | Estado |
|---|---|---|
| M0 | Casablanca (reaction-diffusion) | Completado (reemplazado) |
| M1 | ABM Thin Slice | Completado |
| M2 | Validacion datos reales | Completado |
| M-perf F1 | C++ ABM Engine | Completado |
| M3 | U-Net Training | Pendiente |
| M4 | U-Net Inference | Pendiente |
| M5 | SDSS Shell | Pendiente |
| M6 | Operational | Pendiente |
| M7 | Biology v2 | Pendiente |

---

## 12. M2 vs. futuro (M3+)

| Componente | M2 (actual) | M3+ |
|---|---|---|
| Especies | 1: An. gambiae s.s. | + An. stephensi |
| Habitat | PLUVIAL_POOL + dynamic | 12 subtipos Hardy |
| Etapas vida | 2: larva + adulto | 4: huevo→larva→pupa→adulto |
| Ciclo gonotrofico | No | 2-4 dias @ 28°C |
| EIP | grado-dia (16°C, 110 GD) | + Sharpe-DeMichele |
| Dispersion | Gaussiana local | + Eolica 120-290m |
| Busqueda hospedador | No | CO2, olor, calor |
| Resistencia kdr | No | alleles Vgsc |
| Mortalidad adulta | C++: Lardeux; Py: simplificada | Validacion datos |
| Mortalidad larvaria | C++: Beverton-Holt; Py: solo inactive | — |
| Poblacion | Polars/SoA | + mesa-frames |
| Validacion | 20 sitios + parity | 100+ rollouts |

---

## 13. Resumen ejecutivo

### Lo que funciona hoy

**ABM Python (v0.5.0)**: 71/71 tests, ~9M agentes Polars, JRC GSW 30m, dynamic patches, adult density by cell post-dispersal, ciclo biologico completo.

**ABM C++ (mal-abm-fast F1)**: 60/60 ctest + 5/5 parity, C++20 black-box equivalente, Beverton-Holt + Lardeux mortality, PRNG xoshiro256** determinista, seeding modes, --n-rollouts + --snapshot-every.

**Pipeline SDSS (mal-core)**: U-Net 32-64-128-256, CLI `malariasim`, FastAPI REST API, model registry, scenario config.

### Siguientes pasos

1. **M3**: Generar 100+ rollouts con mal-abm-fast → dataset → entrenar surrogate
2. **M4**: Integrar prediccion → risk maps mensuales
3. **M5**: Interfaz SDSS para programas de eliminacion
4. **M6**: Deployment en Ghana con datos en vivo
5. **M7**: 4 etapas vida, ciclo gonotrofico, busqueda hospedador, resistencia kdr
