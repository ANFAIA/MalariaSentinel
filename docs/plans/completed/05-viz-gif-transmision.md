# Plan 05 — GIF de transmisión (mapa 2)

Estado: implementado y validado (ctest 279/279, pytest 454/3 deselected;
determinismo md5 verificado end-to-end en accra-coastal-test). Pendiente:
aprobación del tester visual (§9) y commit/rama/PR (§11 — sin commit sin
permiso del usuario).
Fecha: 2026-10-30.
Base: `main` (post merge de PR #53, máscara tierra/mar veraz).

## 0. Objetivo

Generar un segundo GIF nativo en C++, complementario al de hábitat/expansión
(`04-viz-gif-nativo-cpp.md`), centrado en la **transmisión de la malaria**:

- Ver claro, además de los mosquitos, las **celdas picables**, diferenciando
  con nitidez dónde hay humanos y dónde no.
- Visualizar el **movimiento diario humano y animal**.
- Visualizar las **feromonas / penachos de atracción** (aquello que atrae a los
  mosquitos), diferenciados entre sí.
- **Sin información de habitabilidad del terreno**: nada de `S(i,t)`, clases de
  hábitat, `K`, cohortes acuáticas, `z` pluvial ni marcadores de parches. Eso
  pertenece al mapa 1. Mapa 1 = "dónde cría y cómo se expande el vector";
  mapa 2 = "dónde pica, a quién y cómo viaja la infección".

## 1. Decisiones del usuario (2026-10-30)

1. **Escala real de los penachos**: renderizar los kernels del modelo tal cual
   (host 300 m, oviposición 50 m). La leyenda cita las escalas. Sin exageración
   del radio (prohibido multiplicar por N para que "se vea más").
2. **Movimiento**: flechas de los flujos del día + inset día/noche (`H_eff`).
3. **Salida**: GIF aparte, **sin flag nueva**. Se activa automáticamente cuando
   la corrida lleva `--transmission`. Ruta default
   `<out>/<aoi>_abm_seedNNNN_transmission.gif` (misma convención de rollout
   que el mapa 1). Comparte `--gif-every`, `--gif-fps`, `--gif-max-width`.

## 2. Fuentes de datos (verificadas en el motor, sin inventar nada)

| Necesidad | Fuente real | Ancla |
|---|---|---|
| Celdas picables | `HostCell`: `humans_present`, `cattle/goats/sheep/pigs/chickens`, `wildlife_proxy`, `building_fraction`, `indoor_fraction`, `urbanicity` | `include/mal_abm_fast/host_landscape.hpp:22-34` |
| Hospedadores efectivos por fase | `EffectiveHostLandscape::expected_effective_hosts(phase, is_livestock)` (determinista, sin RNG); `sample_effective_hosts(...)` (multinomial, consume `rng_`) | `effective_host_landscape.hpp:45` y métodos del .cpp |
| Movimiento humano/animal | `MobilitySchedule` CSR OD día/noche humano + ganado. En `accra-coastal-test`: día 2 022 773 nnz, noche 547 959, ganado 2 240 878 (`mobility_manifest.json`; `beta_day=0.05`, `beta_night=0.5`, `beta_livestock=0.1`) | `mobility_schedule.hpp` |
| Picaduras reales | `BiteLedger::today()`: por celda y tipo de host, `attempts`, `successful_meals`, `infectious_meals`, `mosquito_deaths` | `bite_ledger.hpp:64-75`; público vía `submodel().bite_ledger()` |
| Infección humana | `HumanCompartmentGrid::susceptible/exposed/infectious/recovered`, `prev_at(r,c)`; `infectious_pressure_grid()`; `last_force_of_infection()` | `human_state.hpp:92-106`; `transmission.hpp:205-213` |
| Mosquitos individuales | `submodel().agents()` SoA: lon/lat, gonotrophic, vector_state | `mosquito_state.hpp` |
| Estadísticas diarias | `TransmissionDailyStats`: S/E/I/R humanos, incidencia, prevalencia, S_V/E_V/I_V, bites humanos, bites infecciosas, `r_eff_approx` | `transmission.hpp:104-126` |
| Actividad por fase (coluzzii) | pesos `DAY 0.02, EVENING 0.10, NIGHT 0.80, DAWN 0.08` | `activity_weights` |
| Penachos | kernel host `A = hosts × pref × indoor_mod × urban_mod × exp(-d/300 m)` (coluzzii `host_seeking_scale_m=300`, radius 1500); kernel oviposición `A = potential × exp(-d/50 m)` sobre parches activados (`scale_m=50`, detect 2000) | `host_seeking.cpp:32-62`; `oviposition_seeking.cpp:36-77` |

Datos existentes; lo único que falta es **acceso** (accessors) y **captura
diagnóstica** del movimiento realizado del día. No se modifica ninguna
ecuación de dinámica.

## 3. Feromonas (penachos) — tres familias, escalas reales

| Feromona | Kernel real | Escala | Color |
|---|---|---|---|
| Penacho host humano | `Σ humans × pref_human × indoor_mod × urban_mod × exp(-d/300 m)` | 300 m | ámbar cálido |
| Penacho host animal | mismo kernel con `cattle+goats+sheep+pigs+chickens+wildlife × pref_*` | 300 m | verde oliva |
| Penacho oviposición (agua + VOC) | `Σ potential × exp(-d/50 m)` sobre células de hábitat activadas | 50 m | cian |

Notas de implementación:

- A 1 km/celda la escala de 300 m es **sub-celda** (`exp(-1000/300) = 3.6 %`):
  los halos serán pequeños (≈3–4 px a 12 px/celda). Es correcto y esperado.
- Dato a documentar en la leyenda del GIF y en este plan: el penacho de
  oviposición usa las **celdas con hábitat activado** como fuente (dato del
  motor), pero **no se pinta la habitabilidad** del terreno (ni `S`, ni `K`,
  ni clases): solo el campo de atracción difuso. La fuente es un dato del
  motor, no una capa de habitabilidad.
- Render por fuente con radio acotado (`3 × scale` de detención) y blending
  aditivo; el campo se evalúa a nivel de celda con el kernel del modelo.

## 4. Capas del mapa (orden de pintado, de fondo a frente)

1. **Base — celdas picables**, tres clases inequívocas:
   - con humanos: tono arena→rojo ∝ `log1p(humans)` + **contorno claro**;
   - solo animales: verde oliva ∝ `log1p(livestock_units)`;
   - sin hosts: gris oscuro.
2. **Feromonas**: halos aditivos translúcidos, una familia por color (§3).
3. **Movimiento diario**: flechas top-N (~120) de los flujos realizados del
   día — humano cian, ganado marrón, grosor ∝ individuos movidos; + inset
   "día vs noche" (`H_eff` DAY vs NIGHT).
4. **Mosquitos**: misma simbología que el mapa 1 (discos por estado
   gonotrófico: host-seeking ámbar, blood/resting púrpura, gravid magenta;
   anillo rojo si `I_V`) — coherencia cruzada entre mapas.
5. **Picaduras de hoy** (`bite_ledger.today()`): cuadrados en la celda del
   host, color por tipo de host (humano / animal), **anillo rojo si
   `infectious_meals`**.
6. **Infección humana** (solo con `--transmission`): contorno rojo ∝ `I_H`
   por celda + puntos de incidencia (`E_H` nuevos hoy).

## 5. Paneles derechos (espejo del layout del mapa 1)

- Cabecera: `MalariaSentinel ABM · transmisión` + día/fecha (fecha simulada,
  igual criterio que mapa 1).
- Mapa ≈58 % del ancho con las 6 capas.
- Panel 1: **SEIR humanos** (log) S/E/I/R + barras de incidencia.
- Panel 2: **Picaduras/día**: humanos vs animales + línea de bites
  infecciosas.
- Panel 3: **Movimiento**: personas/ganado movidos por día + referencia al
  inset día/noche.
- Panel 4: **Info**: fecha, humanos totales, I_H, prevalencia %, incidencia,
  R_eff, bites humanos/animales, bites infecciosas, adultos, I_V.
- Leyenda completa de las 6 capas + escalas de los penachos (300 m / 50 m).

## 6. Exclusión deliberada

No se pinta: `S(i,t)`, clases de hábitat, `K`/`K_total`, cohortes acuáticas
(tamaño/etapa/puntos de flujo), `z` pluvial, marcadores de parches activos,
colorbar de hábitat, capa JRC. Complementariedad estricta con el mapa 1.

## 7. Cambios de código

| Archivo | Cambio |
|---|---|
| `engine.hpp` | Accessors const: `host_landscape()`, `mobility_schedule()` (~6 líneas; los miembros ya existen, son privados) |
| `mosquito_submodel.{hpp,cpp}` | Captura diagnóstica tipo `PatchDailyFlux`: grids efectivos realizados por fase (copia de lo ya calculado en la llamada multinomial) + top flujos del día. **Cero impacto en RNG**: se copia el resultado ya muestreado, no se vuelve a muestrear |
| `viz_common.{hpp,cpp}` (nuevo) | Refactor mínimo: extraer de `viz.cpp` el `Canvas`, primitivas de dibujo (rect/disc/ring/line/text), uso de `gif.h` y `font8x8`. `viz.cpp` (mapa 1) pasa a usarlos sin cambio de comportamiento |
| `viz_tx.hpp` / `viz_tx.cpp` (nuevo) | Clase `GifVizTx`: `observe(engine, history, day)`, `finish()`; las 6 capas + 4 paneles |
| `main.cpp` | Wiring: si la corrida lleva `--transmission`, instanciar `GifVizTx` con ruta default `<out>/<aoi>_abm_seedNNNN_transmission.gif`; cadencia/size compartidos con `--gif-every/--gif-fps/--gif-max-width`. Sin flag nueva |
| `wrapper.py` | Sin kwarg nueva. Documenta el artefacto `_transmission.gif` |
| `CMakeLists.txt` | `viz_common.cpp`, `viz_tx.cpp`; tests nuevos |

Degradación elegante (obligatoria):

- sin `--hosts`: usa el default (humanos en todas partes) y el mapa sale;
- sin CSR de movilidad: no hay flechas ni inset de fases, el mapa sale;
- fallo de render del GIF: **warning, la simulación continúa** (criterio ya
  establecido en el mapa 1).

## 8. Tests

- `test_viz_tx.cpp`: kernel de penachos verificado contra valores calculados a
  mano en una malla mínima (decaimiento e⁻¹ a 300 m y 50 m medido en la celda
  vecina); extracción de top-flujos; clasificación de celdas picables
  (humano / solo-animal / vacía).
- **No-afectación**: con y sin `--gif-trans`-interno, el COG de estado y los
  JSON de cohortes son **byte-idénticos** (mismo test que existe para el
  mapa 1). Además: misma semilla, con/sin GIF de transmisión, mismas
  estadísticas finales (RNG intacto).
- **Determinismo**: dos corridas idénticas → md5 del GIF idéntico.
- `test_cli_gif.py`: +casos para el artefacto `_transmission.gif`
  (presencia/ausencia según `--transmission`).
- `ctest` completo verde (baseline 268) y `uv run pytest -q` verde
  (baseline 452 passed / 3 deselected).

## 9. Validación visual (bucle implementador → tester)

Como en el mapa 1: implementador produce; tester independiente extrae frames
y verifica; si no aprueba, vuelve al implementador hasta aprobación.

Criterios del tester:

1. Celdas de humanos contrastadas contra `population.tif` del AOI (referencia
   real): mismas celdas marcadas como "con humanos".
2. Toda picadura del día cae en una celda con hosts (humano o animal);
   `infectious_meals` solo donde hay presión/infección.
3. Decaimiento del halo medido en píxeles: e⁻¹ a ~300 m (host) y ~50 m
   (oviposición).
4. Flechas: al menos un flujo humano real del OD aparece; grosor proporcional
   al volumen; inset día/noche coherente con `beta_day=0.05` vs
   `beta_night=0.5`.
5. Cero contenido de habitabilidad (`S`/`K`/parches/acuáticos).
6. Determinismo (md5) y no-afectación (COG/JSON byte-idénticos).
7. Coherencia de simbología con el mapa 1 (mosquitos, cabecera, fecha).

## 10. Coste

- +~10 ms/frame por el segundo GIF; 365 días ≈ +6 s de render.
- GIF 2 ≈ 6 MB en `accra-coastal-test` (365 frames, 1280 px).
- Disco despreciable frente al criterio de poda ya aplicado.

## 11. Restricciones operativas

- **Sin commit y sin push sin permiso explícito del usuario** (regla vigente
  de la iteración del mapa; reiterada por el usuario).
- Trabajo sobre rama nueva cuando toque commitear (hablarlo con el usuario
  antes).
- Cambios estrictamente de visualización/diagnóstico: ninguna ecuación de
  dinámica, ninguna constante de modelo, ningún umbral de transmisión se
  toca.
- El render no consume RNG (ni muestrea `sample_effective_hosts` con el RNG
  del motor).

## 12. Próximos pasos (fuera de este plan, en el momento oportuno)

- Lanzar subagente implementador con este documento como brief.
- Tras aprobación del tester, proponer commit/rama/PR al usuario.
- Pendiente relacionado (no bloqueante, ya anotado): el penacho de
  oviposición depende de `activated`; si en el futuro se reintroduce
  salinidad real (hoy placeholder de ceros), el penacho se restringirá solo.

## 13. Revisión de legibilidad y diagnóstico aprobada (2026-10-30)

Esta revisión supersede, para el GIF de transmisión, las capas de halos y el
panel lateral de movimiento descritos en §§3–5:

- Se eliminan del mapa los tres halos de atracción (humanos, animales y
  oviposición). Se mantienen las flechas de movimiento en el mapa y los insets
  DAY/NIGHT. Se elimina el panel lateral `moved/day human + livestock`.
- La columna lateral muestra SEIR/incidencia humanos, comidas por hospedador,
  comidas infecciosas de cualquier hospedador (`inf meals/day`) e `I_V` total.
  El panel `I_V` incluye un punto real de inicio previo al primer paso,
  obtenido de las hembras adultas infecciosas tras la siembra inicial; luego
  continúa con el `I_V` diario. No se altera la dinámica ni se consumen RNG.
- La fuente bitmap no soporta UTF-8 (reemplaza cada byte no ASCII con `?`). Los
  rótulos del GIF usan ASCII y títulos/leyendas compactos para evitar texto
  corrupto o superpuesto.
- Se escribe `<transmission-GIF-stem>_debug.jsonl`, con metadata versionada,
  parámetros, estados/compartimentos por día, eventos vectoriales (siembra
  inicial, nuevas exposiciones, finalizaciones EIP) y bites agregados por
  humano/animal/tipo de hospedador y por celda.
- Verificación de esta revisión: `ctest` de los targets de visualización,
  transmisión y logging; `uv run pytest -q` (454 passed, 3 deselected); y una
  smoke run de 6 días con GIF 1280×768 y JSONL de 7 registros (metadata + 6
  diarios). Sin commit ni push en esta iteración.
