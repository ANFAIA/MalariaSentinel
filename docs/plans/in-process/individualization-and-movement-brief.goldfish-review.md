# Revisión Goldfish (EGM, modo BRAINSTORM) — brief de individualización y movimiento

* **Target:** `docs/plans/in-process/individualization-and-movement-brief.md` (rev. 2, 921 líneas, 80 KB)
* **Fecha:** 2026-11 · rama `docs/conceptual-documentation-layer`
* **Método:** 8 Goldfish independientes, contexto fresco, `Mode: BRAINSTORM`, sin historial de conversación; cada revisor leyó el brief completo y verificó contra el repositorio y `papers/anopheles-dynamics/`
* **Estado de revisores:** 8/8 completados (design critic · pedantic codebase details · skeptical architect · naive comprehension · pragmatic tech lead · structural layout validator · TRIZ inventive catalyst · technical copy editor)

---

## 0. Resumen ejecutivo

El brief es un **dossier de investigación sólido** (61 extractos con DOI y licencia, decisiones trazadas a sección) y **no es todavía un plan implementable**. Tres bloqueos duros:

1. **El motor no tiene reloj de fase ni sub-pasos.** La ley de movimiento que el brief propone (velocidad medida × tiempo de fase) no tiene dónde aterrizar: el día es un único paso y no existe duración de fase en el YAML. La cascada sensorial (100 m → 30–70 m → 0,25–0,72 m → 0,10–0,20 m) abarca cuatro décadas de escala; un solo integrador no puede representarla. **Es la decisión de diseño central que falta.**
2. **El YAML es un contrato congelado y triamente validado**, no un fichero de configuración. Varias filas de §9.7 no son válidas: `egg_batch_max: 112` **rompe la invariante `0 < min <= mean <= max <= n`** (`config_validation.py:582`) con `egg_batch_mean: 120` ⇒ el CLI aborta con `SystemExit` en todos los comandos.
3. **No existe el arnés de escenarios sintéticos.** §10 (E1–E14) no es ejecutable: no hay forma de fijar poblaciones a mano, ni semilla por escenario, ni ruta de ejecución que no sea el modo manifiesto, ni forma de Goodbye al binario (`runs/_check_current` sí contiene los artefactos de §2 — eso se verificó).

Además, **dos lecturas de fuente están mal en el brief** (§2 abajo): la ventana postprandial de Takken 2001 está escrita con el signo invertido, y el rango de disociación gonotrófica de Mamai 2026 está atribuido a *coluzzii* cuando es un agregado de tres especies (para *coluzzii* el rango real es 19,23–34,85 %).

---

## 1. Correcciones de lectura de fuente (prioridad máxima)

### F-1 — Takken 2001: la ventana 40–72 h es donde la respuesta *vuelve*, no donde se suprime

El brief (§6.4 bis, §10 E11) afirma: *"tras la comida, la hembra **no** vuelve a buscar en 40–72 h (Takken 2001)"* y *"la supresión es **olfactiva**"*. El extracto (`papers/anopheles-dynamics/takken-2001-inhibition-host-seeking-blood-feeding-gambiae.md`, líneas 23–27) dice:

> "There was **no host-seeking response at 3 and 24 h pbm**. **Seven percent** of the mosquitoes responded to human emanations **40-h pbm, 27% at 48 h and 68% at 72 h** following a blood meal."

Es decir: la puerta está **cerrada por completo hasta 24 h** y se reabre progresivamente entre 40 h (7 %) y 72 h (68 %); la conclusión del artículo es *"inhibition … for a period of at least 40 h"*. Además, la atenuación olfativa (EAG) es **específica del estadio IV de Christophers** (líneas 33–37): en los estadios I–III no hay diferencia respecto al control. El brief generaliza "olfactiva" a toda la ventana.

**Efecto:** `blood_meal_refractory_days` no puede ser "la ventana 40–72 h". Como mucho, `refractory_days = 2.0` (48 h) describe una puerta reabierta al ~27 %; el valor correcto es **supresión completa = 1–1,5 días** y recuperación progresiva después.

### F-2 — Mamai 2026: el rango 19,23–68,64 % no es de *coluzzii*

El brief (§8.1, §9.5) atribuye a *coluzzii* el rango "19,23–68,64 % de las hembras alimentadas que no superan la etapa 2 de Christophers". El extracto (`mamai-2026-coluzzii-dry-season-gonotrophic-dissociation.md`, líneas 46–60) desglosa:

| Especie | % que **sí** desarrolla más allá del estadio 2 | % que **no** lo supera (disociación) |
|---|---|---|
| *A. coluzzii* | 65,15–80,77 % | **19,23–34,85 %** |
| *A. arabiensis* | 51,02–59,91 % | 40,09–48,98 % |
| *A. gambiae* s.s. | 31,36–31,88 % | 68,12–68,64 % |

El "19,23–68,64 %" es el **rango agregado de las tres especies en los dos sitios** (Bama y Soumousso). Y el detachment es **estacional en *coluzzii*** (χ² = 3,953, p = 0,004 en Soumousso; χ² = 5,584, p = 0,018 en Bama), mientras que en *gambiae* y *arabiensis* **no hay variación estacional significativa** (p = 0,979 y p = 0,17). La tasa de inseminación fue del 98 % (n = 300), así que el arresto no se explica por fallo de apareamiento.

**Efecto:** `gonotrophic_arrest_prob_dry = 0,40 ("coluzzii medido")` no existe como medición. El valor de *coluzzii* está en 19,23–34,85 % y **depende de la estación** (el modelo debe aplicar el valor deensky sólo en el inicio de la estación seca); el 0,45 del brief coincide con el rango de *arabiensis*, no con *coluzzii*.

### F-3 — Choumet 2012: los 38,94 µm³ son volumen de bomba, no de sangre

El brief (§6.1) deriva de ahí *"comida mayor por sorbo"* y lo etiqueta **[M]**. El artículo reporta volúmenes de **bomba** (*A. sinensis* 38,94 ± 9,45 µm³ vs *A. togoi* 4,77 ± 1,29), tres órdenes de magnitud por debajo de una comida de 3 µL (3 000 000 µm³), y dice explícitamente que no son volúmenes de sangre ingerida. **La inferencia anatómica es [EP], no [M].**

---

## 2. Bloqueadores

| # | Hallazgo | Revisor | Verificación propia | Triaje |
|---|---|---|---|---|
| **B1** | Los casos `HOST_SEEKING`, `HOST_APPROACH` y `PROBING` de `gonotrophic_cycle.hpp` **sólo contienen comentarios**: no asignan estado. La transición real (`picked != nullptr` ⇒ `BLOOD_FED`) la hace el llamador, de forma determinista. El estado `PROBING` **nunca se alcanza**; `feeding_success_rate` se carga y no se consulta. | codebase details | **Confirmado**: `gonotrophic_cycle.hpp:115–132` | **Aceptado.** §6.3 debe reescribirse contra la ruta viva (bucle de fases), no contra la máquina de estados |
| **B2** | La ruta "phase-aware" (host landscape efectivo por fase) **exige `MobilitySchedule` con datos** (`engine.cpp:264`). Si se retira la movilidad, el motor cae en la ruta "celda ganadora" que el brief existe para eliminar. | design critic | **Confirmado**: `engine.cpp:264` (`mobility_schedule_ && has_data()`) | **Aceptado.** §4 debe decir que la movilidad se conserva como *muestreador de fases* (H_residencial), no como movimiento individual |
| **B3** | El motor no tiene reloj de fase ni sub-pasos: la ley "velocidad medida × tiempo de fase" no es representable. A 0,3 m/s, una fase de 2 h son ~2 km, y el ascenso terminal de 10–20 cm son 0,3–0,7 s. | inventive catalyst | **Confirmado**: `model_constants.yaml` no tiene duración de fase; el bucle de día es `for (p = 0; p < PHASE_WEIGHT_COUNT; ++p)` | **Aceptado → decisión D1** |
| **B4** | Velocidad de vuelo (0,225–0,45 m/s) × fases ⇒ **13–20 km por noche**, contra un alcance diario medido de **486–695 m/día** (MRR, *coluzzii*). El motor actual avanza 500 m por fase y por día (4 × 500 m), no 500 m/día. | design critic, comprehension | **Confirmado** el desajuste; `host_flight_step_m: 500` (YAML:240) | **Aceptado → decisión D1** |
| **B5** | `egg_batch_max: 170 → 112` **rompe la invariante pydantic** `0 < min <= mean <= max <= n` con `egg_batch_mean: 120`: el CLI aborta en todos los comandos. | tech lead | **Confirmado**: `config_validation.py:582` + `test_config_validation.py:553`; YAML `mean=120, max=170` | **Aceptado y corregido** en el brief |
| **B6** | El YAML exige cambio **en cuatro sitios por clave**: `model_constants.yaml`, `config.cc` (parser), `config.hpp` (structs), `config_validation.py` (pydantic `extra="forbid"`, sin defaults), más `species_params.hpp`, `config_dump.cpp` y un **comentario de unidad por hoja** (`test_yaml_comments.py`). §9.7 nombra un solo fichero. | tech lead | **Confirmado** (3 capas + test de unidades) | **Aceptado.** §9.7 se reconstruye como inventario con columna "ficheros a tocar" |
| **B7** | Retirar `host_seeking_radius_m` / `host_seeking_scale_m` **no es borrar dos líneas**: `compute_attraction` usa el radio de la fila de especie vía centinela `-1`, `detect_host_cell`/`approach_vector`/`step_toward_host` dependen de la estructura `HostAttraction` (que ancla fila/columna), y `SeedingConfig::host_seeking_scale_m` **también** pondera dónde se siembra la población inicial. | tech lead | Coherente con `host_seeking.hpp:103–110` y `seeding.hpp` | **Aceptado.** §9.7 + §13 deben nombrar las 4 funciones y el reemplazo del kernel de siembra |
| **B8** | No existe el arnés de escenarios: sin hook de siembra por individuo, sin override de población humana, sin ruta de ejecución para escenarios sintéticos (el modo manifiesto valida completitud contra el catálogo). | tech lead, codebase details, skeptical architect | Coherente con `wrapper.py::run_abm_from_manifest` | **Aceptado → paso 0 nuevo** |
| **B9** | El estado humano vive en `HumanCompartmentGrid` (SEIR por celda) y la **transmisión** deriva de él: `λ_H(x) = 1 − exp(−β_vh·I_bites(x)/H(x))` y `p_inf = β_hv × prev_at(row, col)`. Retirar la rejilla deja sin fuente a la capa de transmisión **y al COG de transmisión de 4 bandas** (`TRANSMISSION_BAND_NAMES[4]`). | codebase details, design critic | **Confirmado**: `transmission_output.hpp:21` (4 bandas), `human_state.hpp:32` | **Aceptado.** §13 gana un bloque "capa humana" y §11 un contrato de estadísticas derivadas |
| **B10** | Individualizar 64 M humanos sin política de muestreo no es un plan: el coste por persona es ≈ 58 B ⇒ 3,7 GB por run, y la epidemicidad por celda es un modelo *bien mezclado* que no puede representar agrupamiento doméstico (el dato de convivientes 3/8 y 6/9 del propio brief). | tech lead, design critic, skeptical architect | — | **Aceptado → decisión D2** |
| **B11** | La clave de cohorte acuática es `(patch_id, stage, instar)` y la dependencia de densidad de Beverton–Holt (`p = s0·K/(K+α·N)`) agrega **por parche/celda** con `K` de área de celda. Si la cohorte se re-indexa por posición exacta, la densidad dependence se desarma (cada sub-cohorte ve `N` minúsculo) y la supervivencia larvaria se infla en silencio. Además `PatchState` **sólo existe para células candidatas**, mientras que `S`/`K` existen para todas. | inventive catalyst | Coherente con `aquatic_cohort_bank.cpp` (`larva_per_patch`) | **Aceptado con resolución**: la cohorte **mantiene la celda como clave** y guarda la posición de la madre como *payload*. La alternativa (estado acuático por celda) queda como trabajo futuro |
| **B12** | Bajo la regla "el parche se resuelve por posición", la banda 1 (`adult_patch_count`) y la banda 2 (`adult_cell_count`) **se vuelven idénticas**, contra un contrato congelado (4.0) del que el surrogate toma dos canales. | inventive catalyst | **Confirmado**: `wire.hpp:120–125` define las dos bandas por patch vs posición | **Aceptado → decisión D3** |
| **B13** | La fórmula de apareamiento es inconsistente: `p(inseminada) = 1 − exp(−oferta)` usa como **tasa el número de apareos ya realizados** para una hembra; y `0,072·N ≤ 3·N` hace que el tope nunca limite. Con 100 machos al alcance la fórmula da ≈ 0,999 de probabilidad de inseminación. | naive comprehension, copy editor | — | **Aceptado y corregido** en el brief |
| **B14** | E13 es circular: la expectativa ("oferta ≥ demanda") depende de `swarm_markers_per_km2`, que es [EP] sin valor y se calibra *en* E13. | copy editor, comprehension | — | **Aceptado**: E13 debe **fijar** el parámetro y reportarlo, no afirmarlo |
| **B15** | §5.2 da un radio visual de "≤1 m" mientras §9.5 da 0,25–0,72 m para el mismo mecanismo; el modelo ocular da 25–72 cm, no 1 m. | naive comprehension, copy editor | — | **Aceptado y corregido** |

---

## 3. Majors (los que más condicionan el draft)

| # | Hallazgo | Revisor | Triaje |
|---|---|---|---|
| M1 | La ruta de fase hace **4 pasos de 500 m al día**, no 500 m/día; y `detect_host_cell` tiene un **suelo de atracción de 0,5** (`host_seeking.cpp:262`) que el brief no menciona. | codebase details | Aceptado → §5.4 |
| M2 | `resting_duration_days = 0.5` se trunca a 0 en `static_cast<int32_t>` (`gonotrophic_cycle.hpp:76,136`) ⇒ el descanso real es **1 día**, no 0,5. | codebase details | Aceptado → §6 |
| M3 | `activity_weights` no es reproducible con la normalización que el brief insinúa; y `w_DAY = 0` **elimina la actividad diurna** (la mosquito vuela de día). El peso derivado es [EP] sobre un perfil [M]. | copy editor | Aceptado → §9.7 |
| M4 | `blood_meal_target_ul ≈ 3,0 µL` = media de una comida ⇒ la multipicadura es un caso de cola, contrario a la premisa (Q13b). La literatura cited por el propio brief exige **dos comidas** en pre-gravíd. | copy editor | Aceptado → §6.2 (objetivo 6 µL en el primer ciclo) |
| M5 | `meals_per_cycle_mean = 0,15` es ambiguo (nº de comidas adicionales vs probabilidad de multicomida); el 11–26 % medido es **fracción de hembras con multicomida**, no un recuento. | copy editor | Aceptado → §6.2 |
| M6 | La inferencia "volumen ingerido ⇒ ¶" usa volumen de bomba (µm³) como volumen de sangre (µL). | copy editor | Aceptado → §6.1 (F-3) |
| M7 | El **COG de transmisión de 4 bandas** depende de la rejilla humana que se propone retirar: hay que definir el contrato de estadísticas derivadas. | codebase details | Aceptado → §11 |
| M8 | El `BiteLedger` es un agregado por celda: un ledger por individuo necesita **esquema de evento + mapa hash** y cambia el contrato del sidecar. | codebase details | Aceptado → §11 |
| M9 | `update_patch_id` es O(parches) por adulto por paso: con 6 000 parches y ~200 000 adultos son 1,2 000 000 000 comparaciones por paso. | codebase details | Aceptado → §5.4 (hash espacial) |
| M10 | `adult_mortality` toma la temperatura **de la celda del parche**: con posición continua se pierde la curva térmica (fuera de la celda vacía, 20 °C). | codebase details | Aceptado → §5.4 |
| M11 | El **catálogo de ingesta** declara `host_static` como artefacto; retirar la movilidad toca `validate_completeness` (que valida *todas* las entradas). | design critic | Aceptado → §13 |
| M12 | Los checkpoints del surrogate (`torch.save(state_dict)`) **no llevan versión de contrato ni hash de constantes**: uno de la era 3.0 carga sin error en un modelo 4.0 con las mismas formas. | tech lead | Aceptado → §14 |
| M13 | Los *goldens* son **byte-idénticos** (`test_config_engine_golden.cpp:115`): todo PR de comportamiento debe regenerarlos. | tech lead | **Confirmado** → checklist de PR |
| M14 | La ruta Python usa `bin/mal_abm_fast_darwin` y el test C++ usa otro binario: un PR puede pasar el golden y no verse en el CLI. | tech lead | Aceptado (memoria #28 ya lo recoge) |
| M15 | El marco de calibración **no está donde dice §13 paso 9**: en este checkout no existe `mal-core/src/mal_core/abm/tests/calibration/`; los scorers están en `mal-core/src/mal_core/scoring/scorers/` (d1…d25 + `gates.py`). La variante con `thresholds.yaml`, `scorers/base.py` y `experiments/` vive en `.gitagent/worktree/` (otro agente). No hay `max_delta` en ninguna de las dos variantes: **la "comparación con el run anterior" no existe**. | tech lead | Aceptado → §13 paso 9 reescrito |
| M16 | `species.neutral` sólo tiene `weights`: el validador exige filas completas por especie ⇒ las 25+ claves nuevas de §9.5 obligan a un concepto de fila parcial o a 6 filas × 25 claves. | tech lead | Aceptado → §9.7 |
| M17 | `arabiensis.host_seeking_scale_m` es **120.0**, no 300 (YAML:101). | tech lead | Aceptado y corregido |
| M18 | `oviposition.scale_m` / `oviposition.detect_range_m` / `oviposition.step_m` y `dispersal.snap_radius_m` están **omitidos de §9.7** pese a que §5.4 y §8 los dependen; y §5.4 cita una ruta inexistente (`host_seeking.oviposition.*` → son `oviposition.*` de primer nivel). | structural, tech lead | Aceptado y corregido |
| M19 | §9.5 coloca las claves de enjambre en `species.<fila>` y §9.7 las coloca en un bloque `mating.*`: dos hogares para las mismas claves. | structural | Aceptado → §9.5 reescrito con columna "namespace" |
| M20 | §9.4 dice que `host_seeking_scale_m` tiene "mecanismo respaldado (Giraldo 2023)" y §5.4 dice que se retira: tres veredictos para la misma clave (§9.4, §5.4, §9.7). | structural, copy editor | Aceptado → un veredicto, una sección canónica |
| M21 | `dispersal.adult_max_m` (2 000) y `wind_migration_prob` quedan huérfanos si `adult_sigma_m` se renombra; `egg_batch_mean`/`egg_batch_min` quedan sin destino si el lote pasa a ser proporcional al volumen. | tech lead | Aceptado → §9.7 |
| M22 | El modelo de動力 del viento se contradice: §5.5 dice que el viento es un evento de 100 km, y §5.1 lo usa como restricción diaria "con el viento del día" — y no hay viento near-surface en el ABM. | inventive catalyst | Aceptado → §5.5 con dos regímenes declarados |
| M23 | El **oráculo de §10** no puede ser "trayectoria esperada calculada a mano" para un modelo estocástico, y E1 (1 comida/noche) contradice el propio E11 (refractario). | inventive catalyst | Aceptado → invariantes + bandas de tolerancia pre-registradas |
| M24 | El número de humanos del brief (64 M) no coincide con el del ODD (~32 M) y debe derivarse del manifiesto (`human_total`), no de una constante escrita a mano. | design critic, codebase details | Aceptado → corregir a "derivado del manifiesto" |
| M25 | 12 bloques duplicados en el brief (tablas de machos ×2, radios ×6, velocidad ×4, supervivencia del macho ×6, sangre ×5, seco ×5, viento ×6, claves ×2, decisiones ×3), tres de ellos **contradictorios**. | structural | Aceptado → tabla canónica por Magnitud |
| M26 | El documento no cumple el estándar de especificación: faltan §Objetivos/No-objetivos, §Alternativas evaluadas, y §Riesgos **con mitigación** (§14 es una lista de nueve viñetas sin columna de mitigación). | structural | Aceptado → §2 bis, §3 bis, §14 reescrito |
| M27 | Falta trazabilidad pack → sección: el preámbulo afirma sustituir los packs 02/03/04/05/08/10/11 sin mapear sus "Initial steps" y "Dependencies". | structural | Aceptado → tabla de trazabilidad |
| M28 | Numeración rota: `§6.4 bis` entre §6.4 y §6.5; §12.3 con subtítulos en negrita (no son títulos); encabezado §9 pegado ("DossierInvestigado el 2026-11"). | structural | Aceptado → renumerar, promover, separar |
| M29 | §12 "Puntos aún abiertos" contiene casi nada abierto: §12.1 y §12.2 son un registro de decisiones duplicado de §3. | structural | Aceptado → §12 = sólo lo abierto |
| M30 | 8 nombres distintos para la columna de nivel de evidencia (`Estado`, `estado`, `tier`, `evidencia`, `Verdicto`) y 6 tablas sin nivel; `[NO-VERIFICADO]` está definido pero **aparece 0 veces**. | structural, copy editor | Aceptado → leyenda izada al preámbulo + 5 tags definidos |
| M31 | Rutas de código citadas sin el prefijo real (`src/…` en vez de `mal-core/src/mal_core/abm/src/…`), ruta de config inexistente, nombre de fichero de extract desalineado con el año de la referencia. | structural | Aceptado y corregido |
| M32 | §2 cita "1 117 pollos/celda" sin fuente, sin unidad explícita ni fecha, siendo el núcleo empírico de la afirmación central. | copy editor | Aceptado → marcar como pendiente de fuente o retirar |
| M33 | `record_female_feed` sorteando `β_hv × prev` en **cada** comida: la probabilidad de infección por ciclo es `1 − (1 − p)^N`, no `N·p`; y las comidas del mismo mosquito no son independientes. | copy editor | Aceptado → §6.4 |
| M34 | "De por vida" (esperma) y "monandria" se apoyan en una cita marcada **[NO-VERIFICADO]** en la fuente (Tripet et al. 2003, no OA), pero el brief los etiqueta [M]/[P]. | copy editor | Aceptado → degradar a hipótesis de diseño |
| M35 | El cero de)-DAY: `w_DAY = 0` + `adult_prob_day = 0.05` ⇒ la dispersión efectiva cae de 5 %/día a 2,5 %/día. | design critic | Aceptado → nota en §9.7 |

---

## 4. Nits (agrupados)

* **Artefactos de edición introducidos al redactar** (míos): §9.7 contiene la concatenación de cadenas `` `diabate-2011-` + '…' + `md` `` en tres filas; §13 paso 7 repite una frase truncada (*"apareamiento al atardecer + diagnóstico de enjambre (machos por celda y noche)."*); §13 paso 9 deja un fragmento colgante (*"Crash en la producción larvaria)."*); §12.4 usa "ó" por "o"; el preámbulo cuenta los extractos de dos formas incompatibles (84/61/filas 32–88 vs 30/filas 32–61).
* **Citas**: "Carnaghi 2024" en el cuerpo vs `carnaghi-2023-coluzzii-visual-thermal-landing-targets.md`; el extracto de Takken se cita como si fuera de *coluzzii* (es *gambiae*).
* **Registro**: "ruleta", "maestro de semillas", "ledger", "snap-eado", "arreglo" → "selección ponderada", "generador de semillas maestro", "registro de picaduras", "ajustado por proximidad", "configuración".
* **Sobrecarga de términos**: "celda" designa ≥3 objetos (malla de 1 km, malla de escenario, celda de reporte del COG) + "parche"; "cohorte" designa la cohorte acuática y también un grupo de especies; "marcador" = sitio de enjambre y señal de contraste; "fase" = fase de vuelo / fase del día / fase gonotrófica / iteración del bucle; "pluma" y "penacho" son lo mismo.
* **Encuadre**: "de forma permanente", "la buena noticia", "tu preocupación", "exactamente", "el mayor hueco de la fila" — promoción y segunda persona en un documento de diseño.
* **Tipografía**: negrita inconsistente para valores; backticks sólo en algunos sitios; sangrado de línea distinto entre §6.4 bis y el resto.

---

## 5. Hallazgos rechazados (con verificación propia)

| # | Hallazgo del revisor | Veredicto |
|---|---|---|
| R1 | *"Los artefactos de §2 no existen"* (`runs/_check_current/`, `bin/`) | **Rechazado.** Ambos existen: `runs/_check_current/` contiene `accra-coastal-test_abm_seed0042_day010/day020.tif/.json` y `_aquatic.json`; `mal-core/src/mal_core/abm/bin/mal_abm_fast_darwin` existe. **Lo que sí es cierto**: la tabla de §2 debe llevar su procedencia (commit `8d32a05`, ruta del binario, directorio del run) porque el binario se sobrescribirá en el primer PR de comportamiento |
| R2 | *"El marco de calibración no existe en el repositorio"* | **Rechazado en substance.** Existe en este checkout como `mal-core/src/mal_core/scoring/` (scorers d1…d25 + `gates.py`) y en el worktree de otro agente como `mal-core/src/mal_core/abm/tests/calibration/` (con `thresholds.yaml`, `scorers/base.py`, `experiments/`, `run_calibration.sh`). Lo que **sí** es cierto: `AGENTS.md` describe la ruta del worktree, y **ninguna de las dos variantes implementa `max_delta` ni un registro histórico de runs** ⇒ "el run anterior" no tiene referente |
| R3 | *"El estado `PROBING` no se usa"* | **Aceptado** (era B1) — confirmado en `gonotrophic_cycle.hpp:127–132` |

---

## 6. Decisiones que corresponden al usuario (bloquean el draft)

| # | Decisión | Opciones | Por qué bloquea |
|---|---|---|---|
| **D1** | **Base temporal del movimiento** | (a) paso macro por fase + micro-simulador local (1 s) dentro del radio olfativo; (b) tiempo continuo por eventos (cola de prioridad); (c) integrador grueso + kernel analítico de encuentro (publica el error) | (a) es la única que honra la evidencia en cm **y** mantiene el desplazamiento diario compatible con el MRR medido; (c) es la más barata pero **anula el objetivo del §1** (trayectorias individuales) |
| **D2** | **Alcance de la individualización humana** | (a) 64 M agentes completos (~3,7 GB/run); (b) muestreo estratificado con pesos; (c) materialización perezosa (el humano se individualiza **cuando es mordido**) + reservorio por celda | (c) entrega el mismo resultado observable ("quién fue mordido, quién se infectó, cadenas de transmisión") con coste ∝ tasa de eventos; es la que yo recomendaría, pero cambia la meaning de "cada persona es un individuo" |
| **D3** | **Significado de la banda 1 del COG de estado** | (a) afiliación funcional a la celda acuática de origen; (b) presión de búsqueda de hospedero (reintroduce la semántica ≤3.0); (c) deprecar banda 1 y colapsar a una | con "parche por posición", (a)/(b)/(c) son la única forma de que las dos bandas no sean idénticas |
| **D4** | **Clave de la cohorte acuática** | (a) celda como clave + posición de la madre como payload (mi recomendación,采纳 del catálogo del catalyst); (b) estado acuático por celda como contrato de primera clase (limpio pero rompe el vocabulario "patch" en ingest, gpkg y diagnósticos) | determina si la dependencia de densidad sigue funcionando |
| **D5** | **Semántica de la capacidad de enjambre** | `p(hembra inseminada)` debe expresarse sobre **machos disponibles** y **hembras que compiten**, no sobre apareos realizados | el 0,072 y el ≤3 por macho no acotan lo mismo |
| **D6** | **Alcance del primer PR** | (a) sólo arnés de escenarios + §10 ejecutable (sin tocar biología); (b) además, capa de movimiento con posiciones continuas | (a) es verificable en 2–4 días y no invalida los goldens |

---

## 7. Estado de la corrección en el brief

**Corregido en este ciclo** (hechos verificables, sin decisiones de diseño): F-1 (Takken), F-2 (Mamai, por especie), F-3 (Choumet), B5 (`egg_batch_max`), B13 (fórmula de enjambre), B14 (E13 circular), B15 (radio visual), M4 (`blood_meal_target_ul`), M5 (`meals_per_cycle_mean`), M17 (`arabiensis` 120), M18 (rutas `oviposition.*`, `snap_radius_m`), M19/M20 (namespace y veredicto de `host_seeking_scale_m`), M22 (dos regímenes de viento), M3 (`activity_weights` [EP]), M32 (pollos), M34 (monandria), nits de citación y de artefactos de edición, numeración de §6.4 bis, encabezado §9, preámbulo.

**Diferido a la sesión del draft** (requiere D1–D6 o reescritura grande): §9.7 como inventario completo con "ficheros a tocar"; §13 con paso 0 + criterios mecánicos por paso; §11 (contratos de salida); §14 como tabla con mitigación; §2 bis objetivos/no-objetivos; §3 bis alternativas; tabla de trazabilidad pack → sección; consolidación de las 12 duplicaciones; §5.4 (hash espacial, suelo 0,5, 4 pasos/día, temperatura continua); §6.3 reescrito contra la ruta viva (no contra la máquina de estados); §4 (papel de la movilidad como muestreador de fases); la política de comparación del calibrador (registro de runs + clave de comparabilidad `constants_sha256` + baseline fijado).

---

## Anexo — mapa hallazgo → revisor

| Revisor | Foco | Aportación distinctive |
|---|---|---|
| design critic | arquitectura, coste, riesgos | lista de corrección de 29 puntos de YAML; **contrato YAML triamente validado**; el COG de estado ya está en 4.0 (no es un riesgo nuevo); el artefacto nuevo (ledger) sin esquema; checkpoints sin versionar |
| pedantic codebase details | fidelity documento ↔ código | **código real vs brief** (PROBING muerto, `resize` inexistente, 4 pasos/día, truncamiento de `resting_duration_days`, O(N) en `update_patch_id`, temperatura por celda, ledger agregado) |
| skeptical architect | YAGNI, minimalismo | **D2**: ¿individualizar humanos es necesario para el objetivo?; qué pasos del §13 se pueden aplazar; **el mecanismo espacial de apareamiento no cambia ninguna salida epidemiológica** |
| naive comprehension |术语, glosario, coherencia interna | **B4** (velocidad × fase vs alcance medido), **B13** (semántica de la fórmula de enjambre), "percepción" vs "radio" vs "sensibilidad", "celda" ×3, "cohorte" ×2 |
| pragmatic tech lead | ejecutabilidad | **B8** (arnés inexistente), **B5** (invariante egg batch), checklist de PR, primer PR concreto con su gtest y sus 10 aserciones, 13 decisiones abiertas ordenadas por daño |
| structural layout validator | estructura, jerarquía, tablas | 12 duplicaciones, 3 contradictorias; §12 no contiene nada abierto; 6 tablas sin nivel de evidencia; 5 nombres para la columna de evidencia; compliance con el estándar de feature-spec |
| TRIZ inventive catalyst | contradicciones de sistema | **B1/B3** (base temporal), **B11** (clave de cohorte vs Beverton–Holt), **B12** (las dos bandas se vuelven iguales), **B10** (64 M), **D5**, patrón de oráculo de dos niveles |
| technical copy editor | precisión del lenguaje | **F-1/F-2/F-3** (lectura de fuentes), errores de tier ([M] donde es [EP]), *key* duplicada, artefactos de concatenación de cadenas,ENA |
