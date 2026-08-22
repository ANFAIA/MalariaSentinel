# M7.4 — Ciclo SEIR-SEI de transmisión de malaria

> **Estado**: Plan revisado (2026-08-21).
>
> **Objetivo de dependencia**: M7.4 no queda bloqueado por M7.3. Usa el esqueleto de especies ya presente como proveedor opcional de parámetros, pero funciona con una sola especie activa (`An. coluzzii`) y un registro de especies preparado para expansión posterior.
>
> **Predecesor funcional**: M7.2 — ciclo gonotrófico. M7.3 puede enriquecer parámetros y activar coexistencia, pero no es requisito de compilación ni de ejecución.

## 1. Objetivo y límite

Implementar transmisión estocástica espacial completa entre mosquitos y humanos:

- Vector: `S_V → E_V → I_V`.
- Humano: `S_H → E_H → I_H → R_H → S_H`.
- Fuerza de infección bidireccional Ross-Macdonald, agregada por celda y por especie.
- EIP vectorial dependiente de temperatura, reutilizando el acumulador GDD actual.
- Incubación intrínseca humana, recuperación e inmunidad temporal configurables.
- Salidas diarias espaciales para prevalencia humana, incidencia y expansión del foco.

No incluye todavía inmunidad por edad, embarazo, superinfección, genotipos de parásito, resistencia a insecticida ni calibración epidemiológica Ghana. M7.7 y M7.5 pueden consumir los contratos definidos aquí después.

## 2. Decisión sobre M7.3

### 2.1 Esqueleto encontrado

El código ya contiene una base reutilizable:

| Componente | Ubicación | Estado actual | Uso en M7.4 |
|---|---|---|---|
| Identidad estable | `include/mal_abm_fast/species.hpp` | `MosquitoSpeciesId`, 6 IDs, `species_name()` | Clave de agregación y configuración |
| Parámetros | `include/mal_abm_fast/species_params.hpp` | `SpeciesParams`, actividad, preferencias, salinidad, ciclo gonotrófico | Añadir parámetros de transmisión sin cambiar identidad |
| Registro | `src/species_params.cpp` | Registro total; solo `An. coluzzii` es población activa por defecto | Resolver parámetros vectoriales por especie |
| Estado vectorial | `include/mal_abm_fast/mosquito_state.hpp` | `species_id` en SoA; `parasite_eip_progress` | Añadir estado infeccioso y carga/fecha de infección |
| Submodelo | `include/.../mosquito_submodel.hpp` | Un `species_params_` activo global | Exponer conteos/bites por especie; no exigir multi-especie todavía |
| Pruebas | `tests/test_species.cpp` | Registro, nombres, salinidad y defaults | Extender con parámetros epidemiológicos |

### 2.2 Qué sirve y qué no

**Sirve**: `MosquitoSpeciesId` como enum estable, `species_id` por mosquito, `SpeciesParams` como punto único de configuración, y `accumulate_eip()`/`is_infective()` como base del estado `E_V → I_V`.

**No sirve aún como M7.3 completo**: no hay mezcla de poblaciones con parámetros distintos dentro de un mismo `MosquitoSubmodel`; `Engine` asigna una sola especie/configuración; no existe HBI observado ni curva térmica por especie; `parasite_eip_progress` no representa todavía `S_V/E_V/I_V` de transmisión.

### 2.3 Estrategia de desacoplamiento

1. Crear `TransmissionParams` independiente de `SpeciesParams`.
2. Resolver `TransmissionParams` mediante `species_id`; fallback explícito al perfil default de `An. coluzzii`.
3. En primera entrega, activar una sola especie y conservar comportamiento actual si no se pasan hosts.
4. Permitir varias especies en las estructuras y funciones, sin requerir que M7.3 active sus semillas.
5. No mover ni duplicar el registro de especies. M7.3 solo añadirá perfiles, semillas y comportamiento cuando esté listo.

## 3. Evidencia científica y decisiones de modelado

### Gatore Sinigirira, Ogana y Chirove 2025

`papers/abm-intervention/GatoreSinigirira-2025-SEIR-SEIMalariaBurundi.md` define la estructura SEIR-SEI, acopla temperatura, lluvia y NDVI a nacimiento/supervivencia vectorial, y destaca sensibilidad de `β`, recuperación humana, mordedura y mortalidad adulta. También documenta bifurcación hacia atrás: `R₀ < 1` no garantiza eliminación bajo alta infección inicial.

**Aplicación**: implementar primero dinámica estocástica local; calcular `R₀` diagnóstico, no usarlo como única regla de eliminación; conservar inicialización alta para pruebas de bistabilidad futura. Lluvia/NDVI entran por `PatchState`/`AquaticCohortBank` existentes, no se duplican dentro de transmisión.

### Mordecai et al. 2013

`papers/anopheles-dynamics/Mordecai-2013-OptimalTemperatureMalariaTransmission.md` fija curvas unimodales de mordedura, mortalidad, PDR y desarrollo vectorial: óptimo cercano a 25 °C, rango aproximado 16–34 °C y caída fuerte sobre 28 °C.

**Aplicación**: `a(T)`, `pdr(T)` y mortalidad deben venir de funciones térmicas existentes o nuevas, con pruebas de límites y monotonicidad fuera del óptimo. No sustituir curvas por interpolación lineal global.

### Evidencia ABM espacial

- Walker et al. 2026, resumido en `papers/research-harness/2026-07-17_ABM-Geospatial-SDSS-Malaria-Transmission-Risk.md`, respalda combinar mapas de idoneidad con exposición por hogar.
- Angelakis et al. 2026 respalda movilidad, inmunidad y clima como procesos acoplados.
- Khelifa y El Saadi 2024 respalda que distribución de hábitats y proximidad a humanos determinan intensidad local.
- Fernandez Montoya et al. 2021 respalda separar exposición residual por comportamiento vectorial, especialmente para especies exofílicas.

**Aplicación**: transmisión se calcula por celda, usa `HostLandscape`/`EffectiveHostLandscape`, y conserva `species_id` en métricas aunque solo una especie esté activa inicialmente.

## 4. Contratos epidemiológicos

### 4.1 Estado humano espacial

Crear `HumanSoA` o `HumanCompartmentGrid` en `include/mal_abm_fast/human_state.hpp`.

MVP recomendado: cohortes contables por celda, no un agente humano por persona. Cada celda mantiene `S`, `E`, `I`, `R` como conteos o dobles no negativos. Esto permite operar con los raster de `HostLandscape`, evita bloquear M7.5 y conserva escala regional.

Campos mínimos:

```text
susceptible[h*w], exposed[h*w], infectious[h*w], recovered[h*w]
days_in_exposed[h*w]       # cola/cohortes discretas o edad media
days_in_infectious[h*w]
incidence[h*w]
prevalence[h*w]
```

Preferir colas de cohortes por edad de estado (`vector<array<int64_t>>`) si se necesita distribución realista de incubación y recuperación; evitar un único `days_in_exposed` que distorsiona ondas epidémicas.

Invariantes por celda: todos los compartimentos `>= 0`, suma igual a población residente/móvil salvo entradas/salidas explícitas, y transiciones calculadas desde el estado al inicio del día.

### 4.2 Estado vectorial

Extender `MosquitoSoA` con:

- `vector_state`: `S_V=0`, `E_V=1`, `I_V=2` para hembras adultas.
- `infection_age_days` o `parasite_eip_progress` como fuente canónica de latencia.
- `infectiousness` opcional, calculada desde estado y especie.
- `last_host_id/cell` solo si futura trazabilidad de bites lo requiere; no incluir en MVP.

Males permanecen fuera del ciclo infeccioso. Mosquitos infectados conservan ciclo gonotrófico, dispersión y mortalidad normales; intervención futura puede modificar esos procesos.

### 4.3 Parámetros

Crear `include/mal_abm_fast/transmission.hpp` con:

- `beta_human_to_vector`: probabilidad de infección por bite sobre humano infeccioso.
- `beta_vector_to_human`: probabilidad de infección por bite de vector infectivo.
- `human_incubation_days` o distribución discreta.
- `human_infectious_days`.
- `immunity_duration_days` y `immunity_enabled`.
- `initial_infected_humans` por celda o semilla reproducible.
- `bite_rate` y multiplicadores por especie/fase/host.
- `temperature_response` para mordedura, PDR y mortalidad.

Separar `TransmissionParams` de `SpeciesParams` evita que M7.3 tenga que definir toda epidemiología. `SpeciesParams` puede obtener después un `transmission_profile_id` o parámetros vectoriales propios.

## 5. Ecuaciones y algoritmo diario

### 5.1 Fuerzas de infección

Para celda `x`, especie `s`:

```text
lambda_H(x) = 1 - exp(- sum_s [ a_s(x) * b_vh_s * I_V_s(x) / H(x) ])
lambda_V_s(x) = 1 - exp(- a_s(x) * b_hv_s * I_H(x) / H(x))
```

Donde `H(x)=S_H+E_H+I_H+R_H`, `a_s` integra densidad de hembras, actividad de fase, HBI/preferencia y exposición espacial. Para `H=0`, ambas fuerzas son cero. Usar hazard exponencial evita probabilidades mayores que 1 y funciona mejor con múltiples especies que sumar probabilidades lineales.

### 5.2 Orden de `Engine::step()`

Extender el orden actual sin romper ciclo acuático:

1. `CoordinatorModel::activate_patches()` y lectura de clima.
2. Aplicar movilidad humana/fase al `HumanCompartmentGrid` si hay `MobilitySchedule`; si no, identidad.
3. Calcular exposición/bites desde estado vectorial previo y humanos previos.
4. Muestrear `S_H→E_H` y `S_V→E_V` con substream PRNG de transmisión.
5. Avanzar colas humanas `E_H→I_H`, `I_H→R_H`, `R_H→S_H`.
6. Avanzar EIP vectorial `E_V→I_V` usando temperatura diaria y perfil de especie.
7. Ejecutar ciclo gonotrófico, oviposición, dispersión, mortalidad y emergencia existentes.
8. Aplicar nacimientos/emergencias como `S_V` y registrar estadísticas.
9. Validar invariantes y guardar `TransmissionDailyStats`.
10. Avanzar fecha.

El orden exacto debe fijarse en tests; no permitir que una infección adquirida ese día transmita en el mismo día.

### 5.3 Bites y gonotrofismo

Reusar `BiteLedger`, `HostSeekingModel`, `EffectiveHostLandscape` y `feeding_success`. Cada bite exitoso debe registrar al menos celda, especie, host class, intentos, éxitos y bites infecciosos. No inferir transmisión desde `n_host_seeking` porque buscar huésped no equivale a alimentación exitosa.

## 6. Cambios requeridos en `mal-core/src/mal_core/abm/`

### C++ headers

- `include/mal_abm_fast/human_state.hpp`: grid/cohortes humanas, transiciones e invariantes.
- `include/mal_abm_fast/transmission.hpp`: parámetros, `TransmissionModel`, fuerzas de infección y muestreo.
- `include/mal_abm_fast/transmission_output.hpp`: grids y estadísticas de transmisión.
- `include/mal_abm_fast/mosquito_state.hpp`: estado vectorial y helpers de compactación.
- `include/mal_abm_fast/mosquito_submodel.hpp`: conteos por especie/estado, bites efectivos y mutadores controlados.
- `include/mal_abm_fast/engine.hpp`: ownership de humanos/transmisión, configuración y snapshot de transmisión.
- `include/mal_abm_fast/wire.hpp`: contrato de grids de transmisión, sin cambiar significado de bandas estatales existentes.

### C++ sources

- `src/human_state.cpp`: inicialización desde `HostLandscape`, movilidad, colas y transición humana.
- `src/transmission.cpp`: fuerzas, muestreo binomial/Poisson, EIP y estadísticas.
- `src/transmission_output.cpp`: raster/JSON de incidencia, prevalencia y foco.
- `src/mosquito_state.cpp`: resize/compactación de nuevos arrays y defaults `S_V`.
- `src/mosquito_submodel.cpp`: infección por bite, estado `E_V/I_V`, conteos por especie y exposición.
- `src/engine.cpp`: integrar modelo en `step()`, configurar semillas, validar invariantes y escribir salidas.
- `src/main.cpp`: flags de transmisión, semilla humana, log y snapshots diarios.
- `src/CMakeLists.txt`: registrar fuentes nuevas.

### CLI y configuración

Añadir opciones explícitas, con defaults backward-compatible:

- `--transmission-config PATH`.
- `--enable-transmission` (off si no existe `--hosts`; on explícito para simulación epidemiológica).
- `--initial-infected PATH|JSON`.
- `--human-population PATH` si densidad no viene de hosts.
- `--transmission-snapshot-every N`.
- `--emit-transmission-log PATH`.

No activar transmisión silenciosamente en corridas históricas que solo esperan dinámica vectorial.

### Salida espacial sin romper contrato

Conservar `state_dayNNN.tif` de 2 bandas. Generar archivo separado por día, por ejemplo `transmission_dayNNN.tif`, con bandas:

1. `human_prevalence` = `I_H/H`.
2. `human_incidence` = nuevos `E_H` del día normalizados por `H`.
3. `infectious_vector_pressure` = suma de bites potencialmente infecciosos por celda.
4. `active_focus` = máscara/score de expansión, definido como incidencia o presión sobre umbral configurable.

Emitir sidecar con nombres, CRS, transform, día, seed, parámetros hash, población total y versión de contrato. Evitar meter bandas nuevas en COG estatal: downstream actual espera exactamente 2.

JSON diario/agregado debe incluir `S_H/E_H/I_H/R_H`, incidencia, prevalencia, `R_eff` aproximado, conteos vectoriales por especie/estado y checksum de seed.

## 7. Visualizador y GIF de expansión

Modificar `scripts/visualize_state.py`, que hoy genera tres paneles: densidad adulta, idoneidad y dinámica poblacional.

Nuevo layout de 4 paneles:

- Superior izquierda: densidad adulta existente.
- Superior derecha: idoneidad existente.
- Inferior izquierda: dinámica poblacional existente.
- Inferior derecha: expansión de malaria desde `transmission_dayNNN.tif`.

Panel de expansión debe mostrar `human_prevalence` o `active_focus` como heatmap, mantener escala global entre frames y dibujar contorno/umbral del foco. Añadir leyenda de día y métrica agregada (`prevalence`, `new infections`, área activa). Si no hay raster de transmisión, mostrar aviso visible y no fallar el GIF vectorial.

Cambios concretos:

- `load_transmission_tif(path)` con validación de bandas/sidecar.
- `find_transmission_files(run_dir)` emparejado por `dayNNN` con snapshots estatales.
- `make_frame(..., transmission, ...)` y `GridSpec(2, 2)` sin aplastar el panel temporal; aumentar figsize y ajustar `tight_layout`.
- Normalización configurable (`--transmission-band prevalence|incidence|focus`, `--transmission-cmap`, percentiles propios).
- Fallback si faltan algunos días: usar `None`, interpolación prohibida; conservar correspondencia temporal explícita.
- Tests de CLI con GeoTIFF sintético, ausencia de raster, días desalineados y GIF no vacío.

La gráfica mostrará expansión espacial real, no una inferencia visual desde densidad de mosquitos. El raster debe salir del estado humano/transmisión.

## 8. Pruebas y aceptación

### Unitarias C++

- `tests/test_human_state.cpp`: conservación de población, transiciones, inmunidad y bordes de colas.
- `tests/test_transmission.cpp`: hazard `0`, saturación, denominador humano cero, binomial reproducible y separación de substreams.
- `tests/test_eip.cpp`: regresión del acumulador actual y transición exacta `E_V→I_V`.
- `tests/test_species.cpp`: perfil epidemiológico total para cada ID; fallback y diferencias no activadas.
- `tests/test_transmission_output.cpp`: shapes, nodata, sidecar y bandas.
- `tests/test_engine.cpp`: orden diario y transmisión off/on.

### Escenarios deterministas

1. **Sin infección**: `I_H=I_V=0` conserva equilibrio libre de enfermedad.
2. **`R₀ < 1`**: brote estocástico termina en población cerrada en corrida suficientemente larga; reportar distribución, no exigir cada seed.
3. **`R₀ > 1`**: crecimiento inicial y persistencia mediana bajo varias seeds.
4. **EIP**: a 25 °C, transición cercana a parámetros del perfil; a <16 °C no progresa; sobre 28 °C la tasa no crece indefinidamente.
5. **Ciclo completo**: bite infectivo produce `E_H`, luego `I_H`, recuperación y retorno tras waning.
6. **Una especie vs. varias**: ejecución default idéntica al modo single-species; conteos por especie listos aunque solo una tenga masa.
7. **Espacial**: foco se desplaza con dispersión/movilidad; celda sin humanos no recibe infección humana.
8. **Reproducibilidad**: misma seed produce logs y rasters idénticos; seeds distintas no comparten estado.

### Criterios de aceptación

- Build C++ y suite existente pasan sin modificar contrato de estado de 2 bandas.
- M7.4 corre con `An. coluzzii` sin M7.3 completo ni `M7.5`.
- `SEIR-SEI` completo observable en logs y raster.
- Fuerzas de infección respetan bites efectivos, sexo, especie y temperatura.
- Invariantes humanas/vectoriales no fallan durante corrida de 90 días.
- GIF incluye cuarto panel cuando hay salidas de transmisión y fallback documentado cuando no las hay.
- Resultados de sensibilidad identifican `β`, recuperación, mordedura y mortalidad como parámetros prioritarios, alineado con Gatore 2025/Mordecai 2013.

## 9. Orden de implementación

1. Congelar contratos y fixtures sintéticos; no tocar M7.3.
2. Extraer/validar `TransmissionParams` y perfiles default desde `SpeciesParams`.
3. Implementar `HumanCompartmentGrid` y pruebas de transición aisladas.
4. Implementar `TransmissionModel` con fuerzas y estado vectorial, primero sin movilidad.
5. Integrar con `MosquitoSubmodel`, `BiteLedger`, gonotrofismo y EIP.
6. Integrar `Engine::step()` y CLI con transmisión opt-in.
7. Emitir raster/JSON de transmisión y actualizar CMake/wire docs.
8. Actualizar visualizador y pruebas de GIF.
9. Ejecutar smoke, unitarias, calibración fast y escenario 90 días.
10. Solo después conectar perfiles multi-especie completos de M7.3.

## 10. Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| M7.3 cambia enum/registry | Mantener `MosquitoSpeciesId` como única clave; no copiar nombres ni IDs en transmisión |
| Densidad humana ausente | Transmisión requiere `--hosts` o población explícita; fallar con mensaje claro |
| Doble conteo de bites | Usar `feeding_success`/`BiteLedger`; separar intento, alimentación e infección |
| R₀ clásico contradice estocasticidad | Usar `R₀` como diagnóstico; aceptar distribución por seeds y bifurcación futura |
| COG incompatible | Archivo de transmisión separado; estado actual sigue 2 bandas |
| GIF mezcla días | Emparejar por número de día; no ordenar por nombre solamente |
| Una cola humana distorsiona incubación | Cohortes discretas por edad; test de duración y masa conservada |
| Rendimiento regional | Grid/cohortes humanas, agregación por celda, PRNG por módulo y sin agente humano individual |

## Referencias

- Issue: `ANFAIA/MalariaSentinel#18`.
- `papers/abm-intervention/GatoreSinigirira-2025-SEIR-SEIMalariaBurundi.md`.
- `papers/anopheles-dynamics/Mordecai-2013-OptimalTemperatureMalariaTransmission.md`.
- `papers/research-harness/2026-07-17_ABM-Geospatial-SDSS-Malaria-Transmission-Risk.md`.
- `papers/spatial-analysis/MalariaEliminationWithSpatialDecisionSupportSystems.md`.
- Código base: `mal-core/src/mal_core/abm/include/mal_abm_fast/{species.hpp,species_params.hpp,mosquito_state.hpp,mosquito_submodel.hpp,engine.hpp}`.
- Visualizador: `mal-core/src/mal_core/abm/scripts/visualize_state.py`.
