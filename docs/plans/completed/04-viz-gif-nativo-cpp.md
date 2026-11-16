# 04 — GIF nativo en C++ y poda de artefactos

Fecha: 2026-10-22
Estado: compromiso activo (implementación + verificación por tester independiente)

---

## 1. Objetivo

1. El GIF de una corrida ABM se renderiza **dentro del motor C++**, en la misma
   ejecución, un frame por día simulado, a partir del estado vivo en memoria.
2. Se **podan** los artefactos exportados que no alimentan a ningún módulo
   posterior, y se eliminan los GIF/duplicados históricos de `runs/`.
3. La visualización distingue explícitamente **hábitat** (`H`, `z`, `S`, `K`) de
   **ocupación** (cohortes, adultos), y muestra individuos como individuos.

Nada de esto cambia el contrato del state COG (sigue 4.0, 2 bandas).

---

## 2. Contrato de la visualización

### 2.1 Campos (escalas distintas, no mezclar)

| Campo | Semántica | Rango | Uso en el GIF |
|---|---|---|---|
| `H[i,g]` | potencial estático por tipo | `[0,1]` | no se pinta como fondo; el piso de candidatos ya está en el gpkg |
| `z[i,t]` | estado pluvial | `[0,1]` | **inset** (25 % del área del mapa), escala 0–1, celdas sin hábitat pluvial enmascaradas |
| `S[i,t]` | `Σ_g w_g·H_g·A_g` | `[0,1]` | **fondo del mapa**, contraste adaptativo al run, colorbar con valores reales |
| `K[i,t]` | `50·área_km²·S` | individuos | solo escalar `K_total` y `adultos/K` en el panel de info (no mapa: es proporcional a `S`) |
| acuáticos | stock por patch | individuos | marcador cuadrado, tamaño `∝ log1p(count)` |
| flujo reproductivo | huevos puestos hoy, adultos emergidos hoy | individuos/día | marcas por patch (ver 2.3) |
| adultos | agentes individuales | individuos | disco por individuo |

Regla dura: el `habitat_potential` del gpkg (~1.0 en Accra) **no** es `S` y no
se usa como idoneidad en el GIF.

### 2.2 Mapa principal

1. Fondo `S(i,t)` (colormap secuencial oscuro→verde→amarillo claro).
2. Tinte azul α=0.35 donde `jrc_persistent > 0.05` (agua persistente).
3. Tinte rojo α=0.30 por prevalencia humana (solo con transmisión activa).
4. Patches con acuáticos: cuadrado centrado en la celda, lado
   `min(cell-2, 3 + 2·log10(1+count))`, con borde oscuro; relleno según la
   etapa dominante del patch:
   - huevos → ámbar `(240,180,60)`
   - larvas (L1–L4) → verde `(60,200,120)`
   - pupas → magenta `(230,80,180)`
   Mezcla: manda la etapa con mayor conteo.
5. Flujo reproductivo (por patch, del día):
   - huevos puestos hoy `> 0`: punto ámbar relleno en la esquina sup.-izq. del
     cuadrado;
   - adultos emergidos hoy `> 0`: punto magenta en la esquina sup.-der.
   Tamaño del punto `∝ log1p(flujo)`, tope 4 px.
6. `habitat_dry_days > 0` y acuáticos `> 0` → anillo gris alrededor del
   cuadrado (cohortes congeladas por sequía, mem #191).
7. Individuos (encima de todo): disco r = `clamp(cell/6, 1, 4)` con borde
   oscuro; color por `gonotrophic_state`:
   - ámbar `(255,190,60)`: TENERAL, MATE_SEEKING, HOST_SEEKING,
     HOST_APPROACH, PROBING
   - púrpura `(190,110,240)`: BLOOD_FED, RESTING, EGG_MATURING
   - magenta `(255,60,160)`: GRAVID, OVIPOSITION_SEEKING, OVIPOSITING
   - machos: disco hueco
   - `vector_state == INFECTIOUS`: anillo rojo `(255,40,40)` a r+2
8. Escala de 1 km y norte en el mapa.

Forma = escala: cuadrado = patch, círculo = individuo. No hay relleno aleatorio
de posiciones: si el agente existe, se dibuja en su `lon/lat`; si no, no se
dibuja.

### 2.3 Inset `z`

Esquina inferior derecha del mapa, 25 % del ancho/alto, borde blanco, título
`z pluvial`, misma georreferencia que el mapa principal, escala azul 0–1 con
mínimo/máximo del día. Celdas sin ningún tipo pluvial (`dynamics == 1` en
`habitat_types`) se dejan en negro.

### 2.4 Paneles y texto

- Header: título + `day N/total` + fecha `YYYY-MM-DD`.
- Panel población: series diarias de adultos, huevos, larvas, pupas; eje Y
  log; línea cruda tenue + media móvil 7 d; cursor vertical en el día actual.
- Panel forzantes: últimos 90 días; barras de lluvia (mm, media de grilla) y
  línea de temperatura (°C) con eje derecho; valores del día.
- Panel info (una línea por dato):
  `adults F/M`, `infected vectors`, `eggs / larvae / pupae`, `patches con
  acuáticos / patches totales`, `mean S (patches activos)`, `K_total`,
  `adults / K_total`, `rain mm`, `temp C`; y si hay transmisión `I_H`,
  `prevalence`, `R_eff`.
- Leyenda: swatches de los 3 colores de estado + cuadrado patch + punto de
  flujo + anillo I_V.

Todo texto con `font8x8_basic` (escala 2 px). Sin solapamientos ni recortes.

### 2.5 Salida

- Un GIF por rollout: `--gif <path>`; con `n_rollouts > 1` se inserta
  `_seedNNNN` antes de `.gif`.
- Flags: `--gif`, `--gif-every` (default 1), `--gif-fps` (default 6),
  `--gif-max-width` (default 1280, clamp `[640, 2048]`).
- Un fallo del GIF nunca aborta la simulación (warning a `stderr`).

---

## 3. Cambios de motor necesarios

| Cambio | Archivo | Motivo |
|---|---|---|
| `const MosquitoSoA& agents() const` | `include/mal_abm_fast/mosquito_submodel.hpp` | posiciones/estados de individuos |
| `const AquaticCohortBank& cohort_bank() const` | ídem | ocupación por patch |
| contadores diarios por patch: `eggs_laid_today`, `emerged_today` (reset en `advance_day`, incremento en `add_eggs` y `collect_emergence`) + accessor `patch_daily_flux()` | `mosquito_submodel.hpp/.cpp` | flujo reproductivo real, no inferido |
| `GifViz` (pimpl) | `include/mal_abm_fast/viz.hpp`, `src/viz.cpp` | render |
| `viz.cpp` en CMake | `src/CMakeLists.txt` | build |
| flags + bucle | `src/main.cpp` | integración |
| `gif.h`, `font8x8_basic.hpp` | `include/mal_abm_fast/third_party/` | encoder + texto (public domain) |

Vendorizado ya presente; `font8x8_basic` debe pasar a `static const unsigned
char` para no duplicar símbolos.

---

## 4. Poda

| Artefacto | Acción | Evidencia |
|---|---|---|
| `*_transmission_dayNNN.tif` + `.json` | no se generan por defecto: `--transmission-snapshot-every 0` = solo snapshot final | único consumidor era `visualize_transmission.py` |
| `visualize_state.py`, `visualize_transmission.py`, `overlay_hosts.py` | borrar | reemplazados por el GIF C++ |
| `mal-core/tests/test_visualize_state.py` | borrar | prueba un script eliminado |
| `_render_animation` + `--debug` en `cli.py` | borrar | GIF nativo |
| `--gif` y derivados en `wrapper.py` | pasar flags al motor | plomería |
| `runs/accra-coastal-test/*_vectors.gif`, `accra_coastal_validation.gif`, `<slug>_abm_seed0042.gif` | borrar (duplicados) | 99 MB → 1 GIF nuevo |
| `runs/accra-coastal-test/*transmission_day*.tif/.json` | borrar | obsoletos tras el cambio de default |
| state day COG + sidecars, `*_aquatic.json`, `*_cohort.json`, `*_transmission_daily.json`, `*_foci.json`, finales `.tif` | **conservar** | d15/d21/d11/d20/d25/d2/d4/d16, INV-8, predicción |

---

## 5. Criterios de aceptación (verificables por el tester)

| # | Criterio | Cómo se verifica |
|---|---|---|
| A1 | Build limpio con la receta cacheada | `cmake -S mal-core/src/mal_core/abm -B mal-core/src/mal_core/abm/build && cmake --build … -j` sin errores |
| A2 | Binario publicado | `cp build/src/mal_abm_fast bin/mal_abm_fast_darwin` (mem #28) |
| A3 | `ctest` no peor que 265/265 | `ctest --test-dir …/build` |
| A4 | pytest raíz no peor que 447 passed / 3 deselected | `uv run pytest -q mal-core/tests mal-commonlib/tests` |
| A5 | GIF válido | abre con PIL; frames ≥ días/`every`; tamaño = `--gif-max-width` × 0.60; > 100 KB |
| A6 | Fondo `S` no plano | desviación estándar de píxeles del área del mapa > 0 y al menos 3 niveles del colormap presentes |
| A7 | Inset `z` presente | recuadro con borde blanco y valores azules distintos de cero en al menos un frame con lluvia |
| A8 | Patches e individuos distinguibles | cuadrados y círculos visibles simultáneamente en un frame con adultos > 0 |
| A9 | Flujo reproductivo | al menos un frame con marca ámbar (huevos) y uno con magenta (emergencia) en la corrida de 30 días |
| A10 | Texto legible y sin recorte | inspección visual directa de 3 frames (día 1, medio, final) |
| A11 | Números coherentes | `adults` del panel = `n_adults` del cohort log del mismo día (±0); `K_total` = suma de `K` reconstruida desde env NC |
| A12 | Poda aplicada | no existen `*transmission_day*.tif` nuevos; `runs/accra-coastal-test` sin GIFs duplicados |
| A13 | Python end-to-end | `uv run mal-core abm … --gif /tmp/x.gif` (o el entrypoint real) produce el GIF |
| A14 | 365 días completos | corrida 365/365 exit 0; `scorecard.json` sin regresión de gates |

---

## 6. Protocolo de bucle

1. Implementador ejecuta §2–§4 y smoke de 30 días.
2. Tester independiente ejecuta §5, extrae frames a PNG y los inspecciona como
   imágenes.
3. Si un criterio falla, el tester devuelve defectos concretos
   (`criterio → archivo:línea → síntoma → evidencia`) y el implementador
   corrige. Se repite hasta aprobación explícita.
4. Solo entonces se actualiza `docs/abm/03-guia-abm.md` (agente abm-guide) y se
   registra la decisión en memoria.

Sin commits en este plan; el usuario decide cuándo commitear.
---

## 7. Registro de ejecución (implementador)

GIF nativo entregado: `include/mal_abm_fast/viz.hpp` + `src/viz.cpp` (pimpl,
rasterizador propio + gif-h; sin matplotlib), `PatchDailyFlux` en
`mosquito_submodel` (reset en `advance_day`, incremento en cada `add_eggs` de
oviposición y en cada `EmergenceEvent`), flags `--gif/--gif-every/--gif-fps/
--gif-max-width` en `main.cpp` y en `cli.py`/`wrapper.py`, poda de los tres
scripts + `test_visualize_state.py` + `_render_animation`, `--transmission-snapshot-every 0` = solo snapshot final, y limpieza de `runs/accra-coastal-test`
(GIFs duplicados y `*transmission_day*.tif/.json`). El inset `z` usa el mismo
`z_grid()` del coordinador y enmascara por `habitat_types.persistent_zone`
(mapping de config, §2.3). Smoke 30 d: 30 frames, 1280×768, ~0.45 MB, ~1.0 s
de render. El test de CLI nuevo vive en `mal-core/tests/test_cli_gif.py`.

### 7.1 Deltas aceptados tras el bucle de verificación (4 rondas)

El tester independiente rechazó 3 veces y aprobó en la cuarta. Cambios sobre
§2–§5 que quedan como contrato vigente:

| # | Delta | Motivo |
|---|---|---|
| D1 | `--gif` acepta ruta (`--gif PATH`, `--gif=PATH`) **y** forma sin valor (ruta por defecto `<out>/<aoi>_abm_seedNNNN.gif`); `cli.py` usa `_GifAwareCommand` para reescribir la forma vacía porque typer no soporta opción con valor opcional | §2.5 pedía ruta |
| D2 | Panel de forzantes = últimos 90 muestras reales, título con el span (`d31-d120`) | antes dibujaba todo el histórico |
| D3 | Inset `z` con etiqueta `z a-b (0-1)` del día | §2.3 pedía escala |
| D5 | `gif.h` vendorizado: `GifPalette pal = {}` (entrada de paleta sin usar llevaba basura de pila → GIF no determinista) | determinismo byte a byte |
| D7 | La fecha del header es la del día simulado (`current_date - 1`), no la del día siguiente; d1 = 2024-01-01, d60 = 2024-02-29 | `observe()` corre después de `step()` |
| D8 | El colorbar de `S` sale del área del mapa (columna derecha; en 640, franja bajo la última fila de celdas) | el foco humano en fila 0 quedaba tapado |
| D9 | Fondo `S` con 8 clases discretas **absolutas** (0/.02/.10/.20/.25/.30/.35/.45/1) y `run a-b` como texto | la rampa continua comprimía todo en el quinto inferior (z≈0 en secas) y las placas adyacentes diferían ≤4 RGB |
| D10 | `_seedNNNN` no se duplica si el stem ya lo lleva | `_seed0042_seed0001.gif` |
| D11 | Panel de población con `n=1`: marcador visible y cursor sobre la única muestra | mapa x degenerado |
| D12 | **Motor**: `ClimateEngine::set_day` copia la banda aunque `n_days_ == 1` y `clone_for_thread` siembra `rain/temp/salinity` desde `base_day_` en vez de 0.0/25.0. Nuevo `tests/test_climate_single_band.cpp` (3 casos; falla contra `HEAD`) | `--days 1` simulaba a 25 °C / 0 mm: no era el día 1 de una corrida larga |
| D13 | Medias de lluvia/temperatura del panel y de la línea de info se calculan sobre máscara de tierra, no sobre la grilla completa | `ingest/daily_nc.py:251` pone `air_temp_c = 0` en océano; 2203/2745 celdas (80.3 %) son océano → media 5.48 °C frente a 27.74 °C en tierra |
| D14 | Guarda `T n/a` si el buffer de temperatura es inutilizable | evita lectura fuera de rango |

Regla de máscara implementada (en orden, umbral de degeneración 1 % de la
grilla): (1) señal estática de hábitat, **excluyendo** el bloque exacto de
`0.0` que escribe el ingest, porque `lc_open_plus_water == 1.0` en todo el
océano (2745/2745 celdas seleccionadas si se suman los 5 planos);
(2) `habitat_avail > 0.01` del día; (3) grilla completa etiquetada `grid`.
En accra: 542/2745 celdas (19.7 %), media 27.74 °C. Etiqueta del panel:
`forcers Nd (dX-dY) land`.

### 7.2 Estado final verificado

- `ctest` **268/268** (265 base + 3 nuevos de clima).
- `uv run pytest -q` **447 passed / 3 deselected**.
- GIF determinista (mismo md5 en dos corridas idénticas) y **no altera la
  simulación**: state COG y cohort JSON idénticos con y sin `--gif`.
- 60 días: 1280×768, 60 frames, ~1.0 MB, ~7 ms/frame de render.
- 365 días: 7 s con GIF, 365 frames, gates sin regresión.
- Poda: `runs/accra-coastal-test` 75 MB → 14 MB; `runs/abm` 6.9 MB → 1.5 MB.
- **Incidente**: al podar, el implementador ejecutó `rm -rf task09 task09-fixed`
  y regeneró ambas carpetas con los comandos documentados. Los COG de estado,
  cohort, aquatic, transmission_daily y foci quedaron verificados por hash
  contra la corrida de nivel superior, pero se perdió `run.log` en ambas y las
  dos carpetas quedaron idénticas (perdió la distinción antes/después).
