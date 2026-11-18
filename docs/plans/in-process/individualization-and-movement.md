# Individualización de personas y rediseño del movimiento de mosquitos

*   **Author:** david-fm
*   **Status:** Plan — pendiente de la revisión final del autor
*   **Date:** 2026-11
*   **Origen:** brainstorm de individualización y movimiento de vectores, con una revisión
    Goldfish de 8 revisores y una revisión 2 de esa revisión. El documento de diseño
    intermedio y su informe de revisión son artefactos temporales: este plan es
    autocontenido y no depende de ellos.
*   **Decisión del autor sobre la capa macho (2026-11):** **opción 2** — el macho es un
    individuo con un **sitio de enjambre asignado al nacer**, y el enjambre es el
    agregado por sitio. La opción descartada (vuelo simulado del macho al enjambre) y
    su comparación están en **§8.3** y **A18**.

## Decisiones

Los identificadores de decisión que se citan a lo largo del plan se recogen aquí, con
la pregunta que el documento les atribuye. **Todas las preguntas están reconstruidas**
a partir del uso que hace el plan de cada identificador; donde el texto no nombra las
alternativas, se dice.

| ID | Pregunta | Opciones | Elegida | Dónde aterriza |
|---|---|---|---|---|
| D1 | ¿Qué base temporal usa el movimiento? | (a) macro-paso acotado + micro-integrador de dos bandas; (b) integrador continuo por eventos; (c) paso diario + kernel de encuentro | **(a)** | §5; A1, A2 |
| D2 | ¿Qué representa la capa humana? | (a) población individual en SoA; (b) compartimentos agregados por celda; (c) agentes representativos con pesos | **(a)** | §2; N3; A5, A6 |
| D3 | ¿Qué publica el COG de estado? | (a) dos bandas con semántica distinta (afiliación reproductiva / presión de búsqueda de hospedero); (b) una banda con semántica única; (c) "colapso honesto": una banda con su nombre correcto | **(c)** | §10; A8, A9 |
| D4 | ¿Cómo se representa el estado acuático? | (a) la celda como clave y la posición de la madre como payload; (b) registro por celda, materializado para todas las celdas | **(b)** | §9; A10, A11 |
| D5 | ¿Cómo se asigna la capacidad de apareamiento (los cupos) en un sitio de enjambre? | (a) "cupos + carrera" exponencial; (b) saturación por disponibilidad de machos; (c) reparto determinista | **(a)** | §8; A12, A13 |
| W | ¿Qué papel tiene el viento en el movimiento? | (a) evento aparte, a escala de 100 km; (b) término del vector diario | **(a)** | N6; A4, A17 |
| M | ¿Cómo se modela la capa macho? | (A) machos agregados (el enjambre como colectivo); (B) machos como individuos | **(A)** en el sentido de §8: el macho **es** un individuo con sitio de enjambre asignado al nacer, y el enjambre es el **agregado por sitio** | §8; N1; A14, A18 |
| F | ¿La hembra asiste al enjambre con un sitio propio? | (a) la hembra **recibe sitio de enjambre al nacer**, igual que el macho, y asiste al sitio con probabilidad `female_attendance_rate`; (b) la hembra busca cada noche el sitio más próximo; (c) la hembra no tiene sitio y asiste por proximidad | **(a)** | §3; §8.1; E13 |
| C | ¿Con qué base entran las cifras nuevas de configuración? | (a) sólo cifras medidas o publicadas; (b) engineering prior declarado | **(a)** | §0 (regla 2); A15, A16 |
| E | ¿Cuál es el reloj maestro del estado fisiológico de la hembra? | (d) híbrido: el ciclo gonotrófico es el reloj maestro y `age_days` queda como campo de diagnóstico; las opciones (a)–(c) no se nombran en el documento | **(d)** | §3, §7; A15 |
| P | ¿Cómo se organizan las claves de configuración nuevas? | por especie (`species.<fila>`) o por bloque global | **por especie** (`species.<fila>`) | §12 |
| "opción d de la revisión 2" | ¿Cómo se derivan la edad y la etapa ovárica de la hembra? | (d) híbrida: el ciclo gonotrófico es el reloj maestro y `age_days` queda como diagnóstico; las opciones (a)–(c) no se nombran en el documento | **(d)** — mismo contenido que E = (d) | §3 (`age_days`), §7 (`ovarian_stage`) |

## Decisiones cerradas por el autor (ronda final)

Estas decisiones son vinculantes y sustituyen a cualquier formulación anterior. Las secciones citadas ya están corregidas.

| # | Tema | Decisión | Dónde se aplica |
|---|---|---|---|
| K-1 | Criterio G1 | G1 = la cadena de transmisión funciona de extremo a extremo en escenarios sintéticos: hay picaduras, hay transmisión y es efectiva en la persona picada. No hay densidad mínima de picaduras por mosquito ni se exige la cadena completa. Se verifica con los escenarios E00–E18, construidos a mano e incrementales. | Goals; §5.1; Nivel 6 |
| K-2 | Personas por celda | `SLOTS_PER_CELL` es **dinámico**: máximo de `human_total` en la primera extracción de datos, más un 10 %. Se guarda en el manifiesto (`slots_per_cell`) y se reutiliza. No hay valor fijo. | §2; Paso 2; Paso 4; §12 |
| K-3 | Duraciones de fase | DAY 12 / EVENING 4 / NIGHT 6 / DAWN 2 h, en `model_constants.yaml`, con el día empezando a las 06:00. Correspondencia uno a uno con los bins de recolección medidos (EE → EVENING, LE → NIGHT, EM → DAWN) y con la ventana DAY 06–18 del motor. Sustituyen a la tabla compilada. Las duraciones 8/4/10/2 se descartan: ninguna hora de inicio alinea sus fases con los bins. | §12.1–12.2 |
| K-4 | Asignación de sitio de enjambre | No se eligen puntos a mano. El campo se genera con `swarm_markers_per_km2`. Regla **estocástica con acumulación**: cada macho elige entre los sitios alcanzables con peso ∝ hembras alcanzables × (1 + machos ya asignados al sitio); una opción de peso `w_suelto` = 1 [EP] lo deja **suelto** (sin sitio). Asignación en orden de `id`. Se retira `male_swarm_site_range_m`. | §8.1, §8.2, §8.5, §8.6, Paso 8, §12, E13 |
| K-5 | Artefacto `swarm_sites.json` | Artefacto nuevo generado por el Paso 8 (recomendación aceptada). | Paso 8; Apéndice A |
| K-6 | **Pendiente de revisión** | (a) Ausencia de separación mínima entre marcadores: se deja así y **se revisará** si E13/E15 lo muestran. (b) Simetría de la regla de la hembra: se revisará. | §8.2; §8.6 |

## Tiers de las magnitudes

Cada magnitud del plan lleva su tier. Un número sin tier no entra.

| Tier | Significado |
|---|---|
| `[M]` | medido en esta plataforma (datos propios del proyecto) |
| `[P]` | publicado en la literatura, con referencia en `papers/REFERENCES.md` |
| `[EP]` | estimación propia del plan, sin respaldo directo |
| `[NR]` | no revisable / no aplica en esta versión |

--------------------------------------------------------------------------------

## Overview

Este documento describe un **cambio de modelo**, no un ajuste de parámetros. La
unidad de razonamiento del simulador pasa de "celda de 1 km" a "individuo en posición
continua":

*   Las **personas** dejan de ser una densidad agregada por celda y pasan a ser
    individuos con posición, estado de infección y susceptibilidad propios. La
    decisión de a quién pica un mosquito se toma sobre personas concretas.
*   El **movimiento de los mosquitos** deja de ser un salto entre celdas gobernado por
    un campo de atracción continuo y pasa a ser una ley por tramos de distancia
    —activación por CO₂, orientación olfativa, aproximación visual, aterrizaje—
    construida sobre radios y velocidades medidos por especie.

El objetivo de fondo es que en el modelo se pueda **observar la malaria emergiendo a
nivel individual**: quién fue picado, por qué mosquito, cuándo, con qué resultado, y
cómo la supervivencia de cada mosquito determina la persistencia de la cadena.

Hoy eso es imposible por construcción (todo el razonamiento es a nivel de celda) y,
además, **no hay nada que observar** porque la cadena no cierra: en una corrida de 30
días en Accra se registran cero picaduras humanas y la población de vectores pasa de
122 a 2 adultos.

El paquete de escenarios sintéticos que acompaña al plan **ejercita la cadena real**
(alimentar → ovipositar → eclosionar → alimentar). Por eso el arreglo del pipeline es
parte del cambio y no un prerrequisito aparte.

### Acrónimos

Se expanden aquí, antes de su primera aparición en el cuerpo del plan.

| Acrónimo | Significado |
|---|---|
| AOI | *area of interest*: la ventana geográfica del estudio, teselada en celdas de 1 km² |
| COG | *Cloud Optimized GeoTIFF*: el GeoTIFF teselado (bandas + sidecar) que publica el estado diario y la transmisión |
| ODD | *Open Dynamics Description*: la ficha de protocolo del modelo (parámetros, entradas y salidas) |
| NC | *NetCDF*: el formato de los artefactos de entrada (`host_static.nc`, `env.nc`) |
| MRR | *mark-release-recapture* (recaptura tras marcado y liberación): el diseño experimental que mide dispersión y supervivencia |
| MBITES | *Mosquito Bout-based and Individual-based Transmission Ecology Simulator* (Wu et al. 2020): el marco del que el plan toma la proporcionalidad del lote de huevos al volumen de sangre |
| ORN | *olfactory receptor neuron* (neurona receptora olfativa): la neurona que rastrea los pulsos de CO₂ |
| EE / LE / EM | los tres bins horarios de la actividad de picadura de Akuoko et al. 2024 (captura humana 18:00–06:00): **EE** *early evening* 18:00–22:00, **LE** *late evening* 22:00–04:00, **EM** *early morning* 04:00–06:00 [P] |
| SIT / IIT | *sterile insect technique* / *incompatible insect technique*: liberación de machos estériles o con incompatibilidad |
| ITN / IRS | *insecticide-treated net* / *indoor residual spraying*: mosquiteros tratados con insecticida y pulverización residual interior |
| CSR | *compressed sparse row*: formato de las matrices de movilidad (quedan como código muerto, N2) |
| WGS | *whole-genome sequencing* (secuenciación del genoma completo): el tipo de dato del estudio de parentesco de Q-F |
| FR50 / FR90 | *flight range* 50 / 90: el radio de vuelo que contiene el 50 % / 90 % de los individuos desplazados (Wickramasooriya et al. 2026) [P] |
| s.s. | *sensu stricto* (subespecie) |
| s.l. | *sensu lato* (complejo de especies) |
| **sidecar** | JSON que acompaña al raster y declara sus metadatos (bandas, `contract_version`, claves) |
| **GeoPackage / gpkg** | formato geoespacial de fichero único (SQLite con capas vectoriales) que el modelo usa para el hábitat por celda (`habitat_patches.gpkg`) |
| MRB | no aparece en este documento: no hay nada que definir |

## The Problem

### P1 — La cadena de transmisión no cierra

Medido sobre el binario vigente (commit `8d32a05`, reconstruido), corrida de 30 días en
Accra con `MAL_ABM_TRANSMISSION_DEBUG=1`:

| día | adultos | huevos | larvas | pupas | `feeds` | `human_feeds` |
|---|---|---|---|---|---|---|
| 1 | 101 | — | — | — | 62 | **0** |
| 10 | 24 | 0 | 859 | 0 | 10 | **0** |
| 20 | 6 | 0 | 231 | 0 | 2 | **0** |
| 30 | 2 | 0 | 144 | 12 | 1 | **0** |

Tres fallos con **causa raíz compartida**: el modelo razona en celdas de 1 km.

1.   **La población de vectores no se renueva.** Los huevos se depositan en el
    `patch_id` *snap-eado* a ≤500 m (`snap_radius_m`), que puede no estar activado ese
    día; en `promote_stages` un cohorte cuyo parche no aparece en `patch_states` hace
    `continue` (`src/aquatic_cohort_bank.cpp:365`): no envejece ni se desarrolla. De ahí
    859 larvas y sólo 12 pupas en todo el AOI el día 30, y 122 → 2 adultos en 30 días.
2.   **Cero picaduras humanas en 30 días.** El mosquito busca *celdas*, no personas:
    `detect_host_cell` elige la celda con más atracción y `step_toward_host` da **un paso
    de 500 m** (`host_flight_step_m`), redondeado al entero (`src/host_seeking.cpp:308`
    y `:311`, las dos llamadas a `lround`):
    con objetivo diagonal el desplazamiento es 0,354 celdas y **se pierde**. La
    atracción decae con `exp(-d/300)`, de modo que la propia celda siempre gana si tiene
    ganado: el mosquito come pollos (1 117 por celda de 1 km en la franja costera —
    cifra sin fuente ni fecha en el repositorio, pendiente de verificar) y nunca llega
    a la gente (a 1,0–2,8 km). Consecuencia: `pref.human = 0.99` nunca llega a
    aplicarse.
3.   **No hay malaria.** Sin picaduras no hay `infectious_meals`; `S_H` = 40 255
    susceptibles no se mueve.

**Matiz: la agregación no es la única condición que impide el cierre.** Reparar la
agregación por celda no basta por sí solo. Aun con la agregación rota, la cadena
vector→humano requiere una **densidad mínima de adultos por km²** para cerrarse: el
mosquito tiene que encontrar a una persona dentro de su disco de CO₂ con frecuencia
suficiente. Ese presupuesto de encuentro se calcula en **§5**; aquí no se adelanta
ninguna cifra, y su consecuencia sobre G1 (el movimiento no basta por sí solo) se
enuncia en §5.

Además: `feeding_success[si] = 1.0f` se fija siempre (`src/mosquito_submodel.cpp:829`),
`feeding_success_rate` (0,825) **se carga pero el motor no lo consulta** (la transición a
`BLOOD_FED` es determinista) y el `max_delta` de la configuración de picadura tampoco.

### P2 — El modelo no puede representar la biología que la literatura sí mide

La configuración actual y la máquina de estados contradicen o no pueden expresar
mediciones publicadas:

| Lo que el modelo hace hoy | Lo que la evidencia mide | Consecuencia |
|---|---|---|
| Atracción por celda con decaimiento exponencial (`host_seeking_scale_m` = 300 m) | La pluma de olor es intermitente y filamentosa: incluso las hembras que aterrizan pasan el 61,4 % ± 3,9 % del tiempo de vuelo fuera de sus límites teóricos | Trayectorias artificialmente directas; el gradiente continuo no representa el mecanismo real |
| Radio de atracción de 1 500 m por celda, y radio **global** de 2 000 m que lo sobrescribe (`host_seeking.detect_range_m`, `host_seeking.cpp:104-114`) | Ningún paper mide 1,5 km ni 2 km de atracción; los radios documentados son 100 m (activación CO₂), 30–70 m (olfativa), 25–72 cm (visual), 10–20 cm (aterrizaje) | el radio efectivo hoy es el **global de 2 000 m**, muy por encima de los radios documentados: el mosquito "siente" a un humano a kilómetros, no a decenas de metros |
| Paso de vuelo de 500 m por fase | Velocidad de vuelo medida en *coluzzii*: 0,225–0,45 m/s en busca; 45,1 ± 1,63 cm/s (suave), 29,0 ± 2,57 cm/s (tortuoso), 22,5 ± 1,14 cm/s (rasante) | El desplazamiento no puede derivarse de la velocidad × tiempo de fase |
| Una comida = un estado (`BLOOD_FED`) | 11–26 % de las hembras con multicomida por ciclo; una comida no completa la sangre necesaria; el tamaño de comida es variable | El modelo no puede representar ni la multipicadura ni la pre-gravidez |
| Sin estado de régimen seco para el adulto | *coluzzii* 19,23–34,85 % de las hembras alimentadas no superan la etapa 2 de Christophers en época seca | La "seca mata" no es la respuesta real: la respuesta es **aplazar** |
| Machos con la misma supervivencia que las hembras (0,87/día) | Machos *coluzzii*: 0,773 ± 0,094/día | Sobrestimación de machos en ~12 % |
| `egg_batch_n` = 240 con recorte [30, 170] | *coluzzii*: 111,67 ± 5,36 huevos por puesta (susceptible), 93,33 ± 10,36 (resistente) | El lote no tiene respaldo |
| `activity_weights` [0.02, 0.10, 0.80, 0.08] | Perfil horario propio de *coluzzii* en Ghana: EE 25,5 % · LE 48,0 % · EM 26,5 % | [EP] probablemente equivocado |

### P3 — El contrato de observación no puede sostener la individualización

*   Los compartimentos humanos agregados (`S_H`, `I_H`, …) están modelados como estado
    de simulación; para individualizarlos deben pasar a **estadísticas derivadas**.
*   El COG de estado (contrato 4.0) publica dos bandas que hoy difieren sólo porque el
    adulto se "snapea" a un parche; con la semántica nueva pasarían a ser idénticas, y
    publicar dos nombres para un mismo número es peor que publicar un nombre correcto.
*   El ledger de picaduras es agregado por celda/día; sin eventos individuales no se
    pueden reconstruir las cadenas mosquito → persona → mosquito → persona.
*   El tamaño de la población humana debe derivarse del manifiesto, y el `human_id` debe
    ser **determinista y estable** (`human_id = cell_id * SLOTS_PER_CELL + slot`, §2)
    desde el primer día, o cualquier
    optimización posterior (materializar sólo a los humanos picados, o muestreo
    estratificado con pesos) rompe el contrato de observación.

### P4 — El pipeline de verificación no existe

No hay arnés de escenarios sintéticos. Sin él, cualquier cambio de la ley de movimiento
es indistinguible de una regresión: los comparadores actuales (scorecard por corrida) no
guardan historial ni `max_delta`, y la línea base de calibración se desplazará en cada
paso.

## Goals

*   **G1 — La cadena de transmisión funciona de extremo a extremo y es observable a nivel individual.** En un escenario sintético debe haber picaduras de mosquitos a personas, cada picadura registrada con mosquito, persona, fase, volumen, resultado del sondeo y transmisión aplicada; debe haber transmisión, y ésta debe ser **efectiva** en la persona picada (la infección queda establecida en su estado). G1 **no** fija una densidad mínima de picaduras por mosquito ni exige la cadena completa de una población real. Se comprueba con los escenarios E00–E18 del Apéndice A, construidos a mano e incrementales.
*   **G2 — La decisión de picar se toma sobre individuos.** El mosquito elige una
    persona concreta por distancia y preferencia de tipo de presa; no existe "celda
    ganadora". La agregación a celda queda como **salida**, nunca como unidad de
    decisión.
*   **G3 — La ley de movimiento es emergente y está anclada en mediciones.** Los cuatro
    tramos de la cascada sensorial (activación, orientación olfativa, aproximación
    visual, aterrizaje) están presentes, con radios y velocidad por especie; los radios
    sin respaldo y los mecanismos incompatibles con la evidencia se retiran. El paso
    temporal del micro-integrador se deriva de las frecuencias de muestreo de los
    experimentos (25–90 fps) y de la duración medida de las maniobras (0,08–1,6 s), no
    de un valor elegido.
*   **G4 — La fisiología de la sangre es representable.** Acumulación de volumen,
    multipicadura dentro de la misma noche, umbral gonotrófico por primera comida
    (pre-gravídica) y por ciclo, y ventana postprandial explícita.
*   **G5 — La estación seca aplaza, no mata.** La hembra gravídica sin criadero entra en
    `ARRESTED` con supervivencia propia, y la parada ovárica es **por especie**.
*   **G6 — El apareamiento tiene oferta, demanda y alarma.** Capacidad de enjambre
    espacial con cupos, la hembra asiste al enjambre, respaldo local, reintento sin
    caducidad, y un diagnóstico que emite **hembras adultas sin inseminar** cuando el
    campo de enjambres no da abasto. El campo de marcadores es **estático y
    persistente**, calibrado a valores publicados, y no un número libre por corrida.
*   **G7 — La fase acuática tiene contexto siempre.** Toda celda del AOI tiene estado
    acuático; "parche" es un filtro de elegibilidad, no un contenedor de información.
    Los adultos emergen donde la madre puso los huevos.
*   **G8 — Cada paso del plan se mide contra un termómetro reproducible.** Un arnés de
    escenarios sintéticos **construido sobre el manifiesto** (manifiesto sintético sobre
    un AOI recortado de Accra), con maestro de semillas, expectativas calculadas a mano
    para lo que tiene forma cerrada e invariantes con bandas de tolerancia
    pre-registradas para lo que depende de la ley de movimiento.
*   **G9 — Los parámetros que cambian llevan su cifra medida y su referencia.** Ninguna
    clave se "mejora" con un número inventado; las que no tienen respaldo se marcan
    como tales y no se tocan. Cuando dos fuentes publicadas **se contradicen** (la
    fracción de machos del enjambre que se aparea por noche: **0,072 ± 0,0095** en
    *gambiae* s.s. frente a **0,084–0,25 pares por individuo de ambos sexos por
    enjambre** en *coluzzii*, magnitudes **no comparables directamente**), el conflicto
    se declara y ambas cotas entran en la sensibilidad.
*   **G10 — La elección del sitio de oviposición es un mecanismo, no una distancia.** El
    modelo implementa el skip oviposition (49,2 % de las hembras usan 2–4 criaderos) y
    la respuesta a la cohorte de larvas conspecíficas —positiva para larvas tempranas,
    negativa para tardías, medida en *coluzzii*—, más el sesgo por tipo de habitat.

## Non-Goals

*   **N1 — No se modelan los enjambres como agentes colectivos.** El **macho sí es un
    agente individual** (con un sitio de enjambre asignado al nacer: §8.1), pero el
    **enjambre es un agregado**: un recuento por sitio y noche, con una ley de cupos.
    No se simula la dinámica interna del enjambre (atracción al marcador, alineación
    al atardecer, evitación de colisión) ni la geometría subcelular. La revisión de
    §16 justifica esa exclusión **por construcción** (el enjambre no es un colectivo
    emergente y su geometría es subcelular), no por conveniencia; y el motivo
    concreto —la hembra responde al sitio, no a la estructura interna— junto con la
    comparación completa contra la alternativa de vuelo simulado, están en **§8.3** y
    en **A18**. El enjambre **sí** conserva su estructura espacial: los sitios son
    puntos persistentes, con la separación, la altura y la ventana temporal publicadas.
*   **N2 — No se modela la movilidad humana por fases.** Las personas se quedan en casa
    (posición fija dentro de la celda, uniforme). El modelo de datos tiene `home` y
    `current` —iguales ahora— para que la movilidad individual se pueda activar más
    adelante sin romper el contrato. Las matrices OD de gravedad (`beta_day` 0,05 /
    `beta_night` 0,5 / `max_distance_km` 50) salen del camino crítico; los CSR y
    `MobilitySchedule` quedan como código muerto a eliminar en una fase posterior, no
    bloqueante.
*   **N3 — No se optimiza todavía el coste del estado humano individual.** Con D2 = (a)
    el estado individual cuesta **40 B por persona** (suma de los campos del SoA de §2,
    redondeada al múltiplo de 8 B por alineación) ⇒ 2–4 GB por corrida con 50–100 M de
    personas [EP]; con el `human_total` que se derivará del manifiesto (Q-E) la cifra real
    depende de esa densidad. Se optimiza después; los escenarios sintéticos empiezan con
    poblaciones pequeñas (10×10 / 100×100 celdas).
*   **N4 — No se reentrena el surrogate ni se reutilizan checkpoints.** Los checkpoints
    entrenados con bandas normalizadas ≤3.0 no son reutilizables: el contrato vigente
    es la v4.0 (`CONTRACT_VERSION` en `wire.hpp`), que retiró la normalización; el
    golden byte-idéntico hay que regenerarlo.
*   **N5 — No se cambia la semántica de la agregación acuática dentro de la celda.** La
    competencia de la Beverton-Holt sigue siendo por celda (1 km²): la heterogeneidad
    intra-celda no se ve en la fase acuática. Queda declarado como hipótesis explícita.
*   **N6 — No se implementa el viento como término del vector diario.** El viento es un
    **evento aparte** a escala de 100 km; el canal `dispersal.wind_flight_hours` /
    `wind_survival` se conserva y se aísla del radio de atracción.
*   **N7 — No se cambia la velocidad de dispersión por viento con la cifra de enjambre.**
    `vielma-2026` mide la velocidad del **macho en enjambre** (0,66–0,87 m/s), que no es
    velocidad de dispersión; `dispersal.wind_self_speed_ms` (1,0) se mantiene marcado
    como prior.
*   **N8 — No se modela la reacción de las opsinas visuales a la sangre**, ni la
    reactivación por período seco: no hay fuente que lo documente.
*   **N9 — No se abre un PR desde la sesión de agente.** El trabajo se hace en rama de
    trabajo con commits por paso; la apertura del pull request es del usuario.
*   **N10 — No se modela la filopatria natal.** No existe ninguna medición publicada de
    retorno al sitio natal en *Anopheles*; la única mención en la literatura de vectores
    es negativa (Thomas et al. 2013: *"assuming no philopatry"*). Lo que sí está medido
    es la preferencia olfativa por el habitat natal (31,6–37,5 %), que es un sesgo por
    tipo de habitat y se implementa como tal.
*   **N11 — No se simula la competencia intra-enjambre entre machos estériles
    individuales.** **Sí se puede representar** el efecto de SIT/IIT sobre los cupos por
    sitio (machos estériles asignados a los mismos sitios, compitiendo por los mismos
    cupos). **E17** cuantifica ese efecto. El *swarm killing* **sí** se puede representar,
    porque el campo de marcadores es discreto. La formulación canónica larga está en
    **§11**; §8.6 y §16.2 usan la misma.
*   **N12 — El micro-integrador no corre fuera de la banda de percepción.** El campo
    lejano va por macro-paso: a 0,45 m/s el mosquito cruza 70 m en 155 s sin maniobra
    rápida, y un micro-integrador global costaría 7–72 s/día simulado.

## Open Questions

Estas preguntas **no bloquean** la redacción del plan; se resuelven durante la
implementación o se declaran como tales en el documento final.

*   **Q-A — Cohorte con *coluzzii* y *gambiae* s.s. en el mismo AOI**: la decisión de
    estivar es por especie (*coluzzii* sí estiva, *gambiae* s.s. no), de modo que el
    motor tendrá que mezclar reglas si el AOI tiene ambas. Falta decidir el orden de
    precedencia cuando una hembra puede estivar y la otra no.
*   **Q-B — Forma del kernel de dispersión local**: ninguna fuente de *coluzzii*
    distingue exponencial (mediana 386 m, p90 1,28 km) de half-Cauchy (mediana 295 m,
    p90 1,64 km, p95 2,83 km); sólo hay cuantiles FR50/FR90. Es una decisión de diseño,
    no un dato, y la cola pesada infla la colonización a >2 km.
*   **Q-C — ~~"Percepción" como radio o como sensibilidad~~ — RESUELTA (§4, E10)**: los
    radios por tramo son **el mecanismo** de la cascada (§4) y la sensibilidad de sus
    valores es el escenario **E10** (tres variantes dentro del mismo JSON). No queda
    pregunta abierta.
*   **Q-D — Cifra de pollos por celda — cerrada: la cifra no se usa.** Los 1 117 pollos
    por celda de 1 km en la franja costera son una cifra **no verificada** (sin fuente
    ni fecha) y quedan **declarados fuera del modelo**: **no entran en ningún
    cálculo** (§2). La mezcla presa/fauna no se fija con ellos; si en el futuro hace
    falta un valor de fauna, habrá que derivarlo de una fuente con fecha.
*   **Q-E — Cifra de "human_total" — nombre y unidad fijados; queda el valor por AOI.**
    El campo es `human_total` (`results["human_total"]`,
    `mal-core/src/mal_core/ingest/hosts.py:87`) y la **unidad que entra en el modelo es
    personas por celda**, con el reparto en identificadores consecutivos
    `human_id = cell_id * SLOTS_PER_CELL + slot` y **semilla derivada de `cell_id`**
    (§2). La referencia del ODD a ~32 M no es utilizable: el valor por AOI sigue
    teniendo que derivarse del manifiesto.*   **Q-F — Filopatria natal: hueco no cerrable con la literatura actual.** No existe
    ninguna medición de retorno al sitio natal en *Anopheles*. La decisión de diseño
    (no implementarla) está tomada, pero queda un **hueco científico**: la primera
    estimación de filopatria natal en *A. coluzzii* sería aplicando el método de
    parentesco por genoma completo (Jasper et al. 2019) a los WGS de *A. coluzzii* de
    Obuasi (Nagi et al. 2025), **con control de las inversiones cromosómicas** (que ese
    mismo trabajo demuestra que confunden la estimación de parentesco). Es trabajo de
    investigación, no de modelado.
*   **Q-G — Tasa de apareamiento de los machos: dos fuentes que no se reconcilian.**
    **0,072 ± 0,0095** (*gambiae* s.s., Malí) — fracción de machos del enjambre que se
    aparea por noche — frente a **0,084–0,25** (*coluzzii*, Burkina Faso) — **pares por
    individuo de ambos sexos por enjambre**, una observación por enjambre, **no
    comparable** directamente con la anterior (conversión a fracción de machos:
    `p_mate_pairs_per_individual / ρ_macho`, sólo como cota superior). **RESUELTO
    (§8.5)**: el valor por defecto es `p_mate_male_fraction` = **0,072 ± 0,0095** [P]
    (*gambiae* s.s.) — la única de las dos cifras en la unidad que la fórmula necesita;
    la banda de *coluzzii* queda como **cota de sensibilidad**, no como valor por
    defecto.
*   **Q-H — Campo de marcadores de enjambre: ¿de dónde sale?** La literatura da la
    estructura (3–12 enjambres por compuesto, 11–19 m de separación, 2,87 m de altura,
    ≈27 min, Moran's I = 0,2) pero no un mapa para Ghana. Las opciones son derivarlo
    del patrón de asentamiento (decisión heredada de la versión anterior del documento) o medirlo; la primera es un [EP]
    con estructura publicada. **RESUELTO (§8, §15 Paso 8)**: el campo de marcadores lo
    **genera el Paso 8** de forma **determinista** a partir de `swarm_markers_per_km2`
    con **semilla explícita**, y lo publica en el catálogo con la clave de manifiesto
    `swarm_sites` (§13.2). **No hay datos de Ghana**: eso queda como **riesgo
    abierto**, con su mitigación en «Riesgos y mitigaciones».

## Riesgos y mitigaciones

| Riesgo | Mitigación | Dónde se resuelve |
|---|---|---|
| **Corrupción silenciosa del SoA del mosquito** al compactar: cada campo nuevo del SoA exige las tres operaciones (`push_back` en la siembra, `std::swap` en la compactación, `resize`), y el olvido de una corrompe el estado sin error | Las tres operaciones se exigen campo por campo (§3) y hay un **test explícito de round-trip de compactación**; el olvido se considera el riesgo mecánico más probable de la fase | Paso 3 (mosquito) y Paso 8 (campos del macho) |
| **Corrupción silenciosa del SoA humano** al compactar: el estado humano individual es un segundo SoA con el mismo patrón de compactación | El mismo test de round-trip, aplicado al SoA humano; el módulo es el existente (`human_state.*`), sin un SoA nuevo que mantener aparte | Paso 2 |
| **Coste de memoria del estado humano individual**: 40 B por persona ⇒ **2–4 GB por corrida** a escala de país (50–100 M de personas) | **Aceptado en esta iteración** (Non-Goal N3) y documentado en el sidecar; la optimización (materializar sólo a los humanos picados, o muestreo estratificado con pesos) queda como mejora futura, sin romper el `human_id` determinista | Paso 2 (N3) y "Future Improvements" |
| **Coste del micro-integrador**: el motor no tiene tick sub-segundo y el integrador fino no puede correr en todo el AOI | El micro-integrador corre **sólo dentro de la banda de percepción** (NFR-3, N12); el presupuesto declarado es de **0,16–16 s por mosquito-día** [EP] y el objetivo es **< 10 s** en el AOI sintético 10×10 y **≤ 10 min** para 30 días en Accra. **Criterio de abandono**: si un día supera **60 s**, se acorta la corrida o se reduce `N_dentro` | Paso 5 (NFR-3) |
| **Coste de la búsqueda nearest-person**: el repo **no tiene** índice espacial (ni KD-tree ni quadtree), y `host_seeking.cpp` recorre una ventana de celdas | La capa humana indexa a las personas **por celda** (misma rejilla de 1 km) y expone `for_each_person_in_radius`; con radio de 100 m < 1 km la consulta toca **como mucho dos celdas** y se acota por distancia en metros. El plan **no** introduce un índice espacial | Paso 5 (estructura en `human_state.hpp`) |
| **Acoplamiento del arnés al comportamiento del manifiesto de producción**: el arnés depende de rutas de carga que hoy sólo existen para los datos reales | El arnés **pasa siempre por el manifiesto** (restricción del autor, §13): el manifiesto sintético se construye igual que uno real y las trampas del catálogo están enumeradas en el Apéndice B; no hay ruta alternativa de ejecución que mantener en paralelo | Paso 0 (Apéndice B) |
| **Filas por persona re-identificables** en los artefactos nuevos (ledger JSONL y parquet individual llevan una fila por persona) | El modelo no contiene datos de personas reales: las personas son sintéticas y su `human_id` es un índice determinista, no un identificador de persona. Los artefactos quedan **en el directorio de corrida** y el prune los declara "conservar" (NFR-7), no "publicar" | Paso 2 (NFR-7) |
| **Regeneración de goldens**: el cambio de contrato (estado 5.0, hábitat 4.0) invalida los goldens byte a byte y los checkpoints del surrogate | La regeneración va **en el Paso 11**, no como efecto colateral; el Nivel 5 excluye los GeoPackages de la comparación byte a byte (el gpkg sella `last_change`) y el surrogate se reentrena (N4) | Paso 11, Nivel 5 |
| **Bloqueo nocturno permanente por el viento**: con el único nivel disponible (ERA5 `u100`/`v100`, 100 m) el caso nocturno de 5,1 m/s bloquearía el avance toda la noche | Se **acepta como resultado documentado** (no como error) y se declara la limitación del nivel de referencia; los escenarios sintéticos **no** cargan campo de viento —salvo **E18**, que sí lo carga y ejercita el desvío y el bloqueo (§13.6)— ⇒ en el resto la regla queda inactiva y el comportamiento queda documentado | Paso 5 (§4) |
| **Artefactos por persona sin cota de tamaño**: `_humans.parquet` (una fila por persona y por día) puede alcanzar **decenas de GB** a escala de país (50–100 M de personas, §2) | `_humans.parquet` va **muestreado al 1 % con pesos** (§11) y el Nivel 5 lo compara **por contenido**, no byte a byte; la cota de tamaño del conjunto de artefactos nuevos (**decenas de GB** [EP]) queda declarada en §11 | Paso 2 (NFR-7), Nivel 5 |
| **Rama de viento validada sólo contra el AOI sintético**: el único nivel de viento disponible (ERA5 `u100`/`v100`, a 100 m) no es la altura de vuelo, así que la rama no puede validarse contra Ghana | La rama queda cerrada por el escenario **E18** (`gate`), que ejercita el desvío *upwind* y el bloqueo nocturno con campo de viento; la limitación del nivel de referencia queda **declarada** como **[NR]** (§4) | Paso 5 (E18) |
| **Radio de exploración menor que el radio de activación CO₂**: con `exploration_range_m` < `co2_activation_radius_m` la activación por CO₂ sería inalcanzable | **Riesgo cerrado**: el valor por defecto de `exploration_range_m` es **100 m**, igual que `co2_activation_radius_m` (100 m), y la banda 100–200 m [EP] mantiene la condición (§4, §5.2) | §4 |
| **Un lector antiguo acepta el contrato nuevo**: al pasar el COG de estado a una banda, un lector que espere dos bandas leería la segunda como otra cosa | Todo cambio de forma de salida lleva bump de versión **y** regla de rechazo explícita en los lectores (NFR-6); no hay migraciones silenciosas | Paso 11 (NFR-6) |

## Critical User Journeys (CUJs)

### CUJ 1 — Un mosquito encuentra y pica a una persona concreta

*   **Given**: AOI sintético 10×10 con una **hembra a 0,72 m** de una persona (dentro de
    la banda de aproximación visual); `pref.human` alto; sin crías.
*   **When**: la noche avanza por las fases activas del mosquito.
*   **Then**: la hembra entra directamente en la **banda de aproximación visual**
    (0,72 m), donde corre el micro-integrador de dos bandas con `dt = 0,04 s`; el
    **gate de aterrizaje** (`v < 50 mm/s` sostenido 3 s) decide el contacto; la hembra
    sortea `probing_success_rate`, y el ledger registra un evento con id de mosquito, id
    de persona, fase, volumen tomado y resultado del sondeo. Si el volumen acumulado no
    alcanza el umbral, **vuelve a `HOST_SEEKING` la misma noche** y el ciclo gonotrófico
    no arranca.
    *   **Por qué 0,72 m y no 200 m**: el contacto es **geométricamente posible** a
        0,72 m (banda de aproximación visual) y **no** a 200 m. El escenario con la
        persona a 200 m es **E01** (`gate`), cuya expectativa es **0 comidas**; este CUJ
        describe el escenario en el que el contacto sí es posible.

### CUJ 2 — Una comida completa cierra el ciclo y produce una puesta

*   **Given**: hembra con volumen acumulado igual al objetivo (`blood_meal_target_ul`).
*   **When**: la hembra entra en la ruta gonotrófica.
*   **Then**: el ciclo arranca, se abre la ventana postprandial (completa hasta 24 h) y,
    tras la maduración ovárica, la puesta tiene un lote **proporcional al volumen
    acumulado**, no un `binomial(240, 0,5)` fijo.

### CUJ 3 — La época seca aplaza la reproducción en vez de matar a la hembra

*   **Given**: racha de días secos en la celda de la hembra; la hembra está alimentada
    pero no encuentra criadero elegible.
*   **When**: se evalúa la transición de estado.
*   **Then**: la hembra entra en `ARRESTED` con supervivencia propia (no la mortalidad
    basal de 0,87/día), y el diagnóstico reporta la fracción de hembras alimentadas que
    no supera la etapa 2 de Christophers (rango medido en *coluzzii*: 19,23–34,85 %).

### CUJ 4 — El apareamiento está limitado por la literatura, no por la demanda

*   **Given**: aldea de 1 km² con 100 hembras y 100 machos recién-emergidos;
    campo de marcadores de enjambre explícito en el escenario (marcadores estáticos y
    persistentes, con la separación y el número de enjambres por compuesto publicados).
*   **When**: pasan tres noches con ventana de enjambre.
*   **Then**: la aserción **no** es "0 hembras sin inseminar" —con 100 machos y las
    tasas medidas eso es falso— sino la **tasa de inseminación que produce la fórmula
    de §8.1**, con su banda **derivada** de los valores por defecto. Con
    `p_mate_male_fraction` = 0,072 [P] (Diabaté, *gambiae* s.s.; fracción de machos del
    enjambre que se aparea por noche), `female_attendance_rate` = 0,1033 [P]
    (Diabaté 2009), 100 hembras y 100 machos en la aldea de 1 km² y un único sitio de
    enjambre alcanzable: `cupos(s)` = 100 × 0,072 = **7,2 cupos por noche**;
    `hembras_presentes(s)` = 100 × 0,1033 = **10,33 hembras presentes**; la
    probabilidad por noche de una hembra presente es `1 − exp(−7,2/10,33)` = **0,502**,
    y la probabilidad **incondicional** por hembra del alcance (asistencia aplicada
    **una sola vez**, en el término de presencia, §8.1) es 0,1033 × 0,502 =
    **0,0519** ⇒ a las tres noches `1 − (1 − 0,0519)^3` = **0,852**, es decir
    **≈85 % de hembras siguen sin inseminar** [EP; banda derivada de los valores por
    defecto, con el desarrollo aritmético en §8.1]. La oferta (7,2 cupos) **no cubre**
    la demanda (10,33 hembras presentes): el modelo queda limitado por la oferta, y
    ese es el resultado correcto de la fórmula, no un fallo. El diagnóstico de alarma
    compara el valor simulado contra esta banda derivada y **emite** cuando lo supera,
    no cuando llega a cero.
*   **Por qué esto importa**: el enunciado original de este CUJ ("la oferta cubre la
    demanda, 0 sin inseminar") era una expectativa sin base publicada, y la banda
    22,3–52,8 % que se citaba antes viene de otra unidad (pares por individuo de
    **ambos sexos** por enjambre, *coluzzii*) que la fórmula de §8.1 no consume. La
    forma correcta de expresarlo es contra la banda que deriva de la fórmula y de los
    valores por defecto (§8.1), con la cifra publicada como cota de sensibilidad
    (`p_mate_pairs_per_individual`).

### CUJ 5 — La cadena de transmisión individual se puede reconstruir

*   **Given**: una corrida completa con los parámetros del piloto *coluzzii*.
*   **When**: se consulta el artefacto individual y el ledger de picaduras.
*   **Then**: se puede reconstruir la cadena mosquito → persona → mosquito → persona
    con identificadores estables, y los agregados por celda y día del COG de estado se
    derivan de los individuos sin volver a ser la unidad de decisión.

### CUJ 6 — La zona costera emerge donde la madre puso los huevos

*   **Given**: una hembra oviposita en una celda elegible, en un punto que no es el centro
    de la celda.
*   **When**: la cohorte se desarrolla y los adultos emergen.
*   **Then**: el adulto emerge en la posición de la madre (campo `mother_x`/`mother_y`
    **añadido** a la cohorte de huevos: hoy no existe y el adulto emerge snapado al
    centro de la celda, `mosquito_submodel.cpp:530-535`), y la cohorte se indexa por
    celda para la competencia acuática, sin ruta de error por celda sin estado.
*   **Y la clave de la cohorte es `(cell_id, mother_id)`** (§9): la posición de la
    madre es la de **su** cohorte, no una coordenada única por celda — dos hembras que
    ovipositan en la misma celda, o una hembra que usa 2–4 criaderos, dan cohortes con
    coordenadas distintas. La competencia de Beverton-Holt se sigue agregando **por
    celda**, de modo que N5 (los agregados por celda sobreviven) no se rompe.

--------------------------------------------------------------------------------

## Technical Plan (Architecture)

### 0. Principios e invariantes

Cuatro reglas gobiernan todo el diseño:

1.  **La unidad de decisión es el individuo; la celda es un output.** Hay **cuatro**
    puntos de decisión, y sólo uno de ellos es por celda:
    (i) **a quién pica** → por **persona** (identificador individual);
    (ii) **dónde pone** → por **sitio de oviposición**, que es un objeto por celda: la
    elección del sitio es celular, pero la hembra, su estado y su conteo son
    individuales;
    (iii) **dónde emerge** → por **cohorte**, con la posición de la madre dentro de la
    celda;
    (iv) **cuánto se multiplica** → por **celda** (mortalidad acuática y competencia de
    la Beverton-Holt).
    Lo que **sobrevive** a 1 km² es el agregado como *salida* (COG de estado, series de
    salida) y como *límite de capacidad* (la competencia acuática, N5); lo que **no**
    sobrevive es la celda como unidad de decisión de *a quién* se pica y de *cuál* es el
    estado de esa persona. N5 fija esta misma frontera para la fase acuática.
2.  **Ninguna magnitud se introduce sin respaldo.** Cada parámetro nuevo lleva su
    cifra medida y su referencia; los que no la tienen se declaran `[EP]` y no se
    "mejoran". La lista completa se aplica sin cambios (estaba en el apartado 9.7 del
    borrador previo, cuyo contenido se conserva aquí sin cambios).
3.  **La posición es continua; la celda es un índice de salida.** El mosquito y la
    persona tienen posición métrica; la celda se deriva por proyección.
4.  **La migración del vocabulario es parte del cambio, no un efecto secundario.**
    "Patch" → "celda" en la cadena completa, porque dejar dos vocabularios conviviendo
    es lo que hizo ambigua la banda 1 del COG.

Invariantes que **no** cambian: la agregación de la Beverton-Holt por celda; el
contrato v4.0 de la capacidad (`p = s0·K/(K + α·N)`, `k_habitat == 0` ⇒ `p = 0`);
la semántica de desiccate por racha de secas; la fase acuática como cohorte agregada
(los inmaduros **no** pasan a ser individuos); el canal de viento tal como está; y el
formato de salida del COG de transmisión (4 bandas).

### 1. Sistema de coordenadas: metros locales del AOI

Hoy el mosquito guarda `row`, `col` y `lon`, `lat`, y el desplazamiento se cuantiza en
celdas (`host_flight_step_m` = 500 m redondeados con `lround`, que es exactamente el
fallo que hace que un objetivo diagonal se pierda). La posición pasa a **metros locales
respecto al origen del AOI**, con `lon`/`lat` derivados:

```
pos_x[m], pos_y[m]  ──(proyección)──▶  lon, lat        (salida, snapshots)
        │
        └──(celda)──▶  cell_id = row*W + col           (índice, agregación)
```

El `struct` `AOI` está declarado en `wire.hpp:249-276`: sus **miembros** (`west`,
`south`, `east`, `north`, `crs`, `slug`, `resolution_m`, `scale`) viven ahí. El
header `aoi.hpp:3-6` dice literalmente que el struct se declara en `wire.hpp` y que
ese header es para **helpers** adicionales. Por eso la transformación inversa
`xy_to_lonlat(x, y)` y `lonlat_to_xy(lon, lat)` se **añade en `aoi.hpp`** (no en
`wire.hpp`), de modo que la conversión a grados usa la misma ruta que la lectura del
`host_static.nc` y no una segunda convención.

El `lon`/`lat` actual del SoA pasa a ser un valor **derivado** que se recalcula al
escribir salidas, no un estado de la simulación.

### 2. Capa humana: de rejilla SEIR a población individual

`HumanCompartmentGrid` (per-cell `S_H/E_H/I_H/R_H` + colas de cohorte, hoy en
`include/mal_abm_fast/human_state.hpp` y `src/human_state.cpp`) se sustituye por una
población individual en Structure-of-Arrays, **en ese mismo módulo**: `human_state.hpp`
/ `human_state.cpp`. La variante de módulo nuevo (`human_population.hpp` /
`human_population.cpp`) queda **descartada**: `human_state` ya es el dueño de la API
pública de la capa humana que consumen `transmission.cpp` y el CLI (`init`,
`seed_infections`, `seed_random_viable_foci`, `seed_explicit_foci`,
`seed_outbreak_cluster`, `advance_day`, `compute_stats`, `validate_invariants`), y el
SoA sustituye a la rejilla **en el mismo objeto y con la misma frontera de API**: un
tipo (`HumanSoA`) en lugar de otro, en el mismo fichero. Un módulo nuevo obligaría a
duplicar esa frontera en dos unidades de traducción y a decidir cuál de las dos es la
que se enlaza. El SoA cabe porque la rejilla y la población individual exponen las
mismas operaciones (inicializar, sembrar casos, avanzar un día, agregar estadísticas) y
sólo cambia la granularidad del estado que las soporta.

```
HumanSoA
  human_id      int64   // determinista y estable: cell_id * SLOTS_PER_CELL + slot
  cell_id       int32   // celda de origen (home)
  home_x, home_y float  // m, uniforme dentro de la celda, asignación por seed
  cur_x,  cur_y  float  // m, = home en esta versión (movilidad pospuesta)
  state         uint8   // SUSCEPTIBLE | EXPOSED | INFECTIOUS | RECOVERED
  timer         int32   // días restantes en el estado (cohorte discreta)
  susceptible   uint8   // bandera de susceptibilidad individual
```

Decisiones de diseño:

*   **`human_id` determinista y estable**: la fórmula canónica es

    ```
    human_id = cell_id * SLOTS_PER_CELL + slot
    ```

    con `SLOTS_PER_CELL` **dinámico**: se fija **una vez, en la primera extracción de datos del AOI**, como el máximo de `human_total` entre las celdas de esa extracción **más un 10 % de margen** (redondeado hacia arriba). Se guarda en el manifiesto como `slots_per_cell` y las extracciones posteriores lo **reutilizan**: no se recalcula, porque cambiarlo cambiaría todos los `human_id`. Si una celda supera el valor fijado, el AOI se rechaza como error de manifiesto; no se amplía en silencio. La clave se declara en §12.
    * **Unicidad**: `cell_id` ∈ [0, `n_cells`) y `slot` ∈ [0, `SLOTS_PER_CELL`) son
      rangos disjuntos, luego el par (`cell_id`, `slot`) → `human_id` es una biyección
      sobre un rango contiguo y dos personas distintas no pueden compartir identificador.
    * **Estabilidad**: `cell_id` deriva de la rejilla del AOI (`row*W + col`), que no
      depende de la población, y `slot` se asigna por celda con un orden determinista
      (orden por semilla). El identificador no depende del orden de inserción en el
      SoA, así que materializar sólo a los humanos picados o muestrear de forma
      estratificada con pesos no altera el identificador de los que sobreviven.
    * **Rango**: el identificador máximo es `n_cells * SLOTS_PER_CELL − 1`; para el
      AOI de Accra (3 416 celdas) son 2,24·10⁸, dentro de `int32`.
    Es la condición para que más adelante se pueda materializar sólo a los humanos
    picados, o hacer un muestreo estratificado con pesos, sin romper el contrato de
    observación.
*   **Número de personas por celda**: el campo de origen es `human_total`
    (`results["human_total"]`, `mal-core/src/mal_core/ingest/hosts.py:87`), y la
    **unidad que entra en el modelo es personas por celda**: cada celda reparte su
    total en personas concretas con identificadores **consecutivos**
    `human_id = cell_id * SLOTS_PER_CELL + slot`, con `slot` ∈ [0, `SLOTS_PER_CELL`),
    **sembradas con semilla derivada de `cell_id`** (así el reparto es reproducible y
    no depende del orden de inserción). En los escenarios sintéticos, un override
    explícito por celda. El reparto **no puede superar `SLOTS_PER_CELL` personas por
    celda**: si lo superase, es un error de manifiesto y se rechaza el AOI, no se
    recorta en silencio.
    *   **La cifra de pollos por celda queda fuera del modelo**: los 1 117 pollos por
        celda de 1 km en la franja costera son una cifra **no verificada** (sin fuente
        ni fecha) y **no entra en ningún cálculo**; la mezcla presa/fauna no se fija con
        ella (Q-D).
*   **Temporizadores discretos**: la cola de cohorte por edad se conserva (el modelo ya
    la usa para evitar la distorsión de duración exponencial) pero **por individuo**:
    `timer` cuenta los días restantes y se decrementa cada día. Su coste (4 B) entra
    en el desglose de coste por persona de abajo.
*   **Los compartimentos agregados pasan a estadísticas derivadas**: `compute_stats()`
    agrega sobre la población en el momento de escribir salidas. La API pública que
    usan `transmission.cpp` y el CLI (`seed_infections`, `seed_random_viable_foci`,
    `seed_outbreak_cluster`, `advance_day`) conserva sus nombres y su firma, pero
    **cambia la semántica de `advance_day`** (§"Vía de infección", abajo): sembrar
    "5 infecciosos en la celda (r,c)" siembra 5 individuos concretos con
    `state = INFECTIOUS`.
*   **Vía de infección vector→humano** (formulación canónica; la versión larga está en
    **§11**): la infección vector→humano ocurre **únicamente en el evento de picadura**,
    sobre la persona identificada: una picadura infecciosa infecta, como máximo, a esa
    persona. La presión de infección por celda (`λ_H`) queda **retirada** como
    autoridad; `advance_day` deja de aplicar probabilidades por celda y pasa a
    **avanzar sólo temporizadores** (edad, estado gonotrófico, timers de oviposición).
    La aserción que la acompaña —"una picadura infecciosa infecta, como máximo, a la
    persona picada, y a ninguna otra"— se escribe en §11.

**Coste por persona**: **40 B** [EP] — desglose de los campos del SoA de arriba
(`human_id` 8 + `cell_id` 4 + `home_x/home_y` 8 + `cur_x/cur_y` 8 + `state` 1 +
`timer` 4 + `susceptible` 1 = 34 B), redondeada al múltiplo de 8 B por alineación
(34 → 40 B). **La regla de relleno (padding) es una convención del plan**, no una medición
de plataforma: el desglose suma 34 B y se redondea al múltiplo de 8 B por alineación.
Coherencia con la afirmación de escala: 40 B por persona ⇒ **2–4 GB**
por corrida con **50–100 M de personas** [EP]; la cifra real depende del `human_total`
que se derivará del manifiesto (Q-E). Se acepta en esta iteración (Non-Goal N3); los
escenarios sintéticos usan poblaciones de 10×10 a 100×100 celdas.

### 3. Capa vectorial: campos nuevos en `MosquitoSoA`

`mosquito_state.hpp` gana:

| Campo | Tipo | Papel |
|---|---|---|
| `pos_x`, `pos_y` | float | posición métrica continua (§1) |
| `blood_volume_ul` | float | volumen de sangre acumulado (µL) |
| `ovarian_stage` | uint8 | pre-gravídica / alimentada / semi-grávida / gravídica |
| `gonotrophic_arrest` | uint8 | 1 = en `ARRESTED` (época seca) |
| `days_since_target_reached` | int32 | reloj de inanición propio (no se reinicia con comidas parciales) |
| `inseminated` | uint8 | 1 = inseminada (monandría); en el macho, marca el cupo consumido (§8) |
| `nights_uninseminated` | int32 | diagnóstico de la alarma de enjambre |
| `age_days` | int32 | **sólo diagnóstico** (opción d de la revisión 2 = decisión E = (d), tabla de decisiones) |
| `swarm_site_id` | int32 | **sitio de enjambre asignado al nacer, en ambos sexos** (decisión F, §8.1): el macho es el que ocupa el sitio y ofrece cupos; la hembra es la que asiste a él. −1 = **sin sitio alcanzable**: el macho **no se reproduce** y no ofrece cupos; la hembra no asiste a ningún enjambre. **No hay enjambre local de respaldo** (§8.2) |

*   **Estados del ciclo gonotrófico**: `gonotrophic_cycle.hpp:28-40` define el enum
    `GonotrophicState` con la cadena `TENERAL → MATE_SEEKING → HOST_SEEKING → …`, y
    `:97`/`:110` documentan *"Mating is assumed instantaneous for An. gambiae (swarm
    mating)"*. El plan **retira** el valor `MATE_SEEKING` (el apareamiento pasa a ser
    "por sitio y por noche", §8, y deja de ser una transición de estado) y **añade**
    `ARRESTED` (época seca, §7); el resto de los valores del enum se conservan.
    `gonotrophic_cycle.hpp` se toca en el **Paso 3** (retirar `MATE_SEEKING`, añadir
    `ARRESTED`) y **también en el Paso 8** (asignación de sitio al nacer y contabilidad
    de la inseminación), no sólo en el Paso 3.
*   **La hembra recibe sitio de enjambre al nacer**, igual que el macho (decisión F,
    §8.1): el sitio se le asigna con la misma regla de asignación que el macho (§8.2)
    y queda registrado en `swarm_site_id`.
    `female_attendance_rate` = **probabilidad de que una hembra presente en el sitio
    esté en posición de cópula**; se aplica **una sola vez**, en el término de
    presencia (`hembras_presentes(s)` de §8.1), y en ningún otro punto de la fórmula.

**No hay campo `home_x`/`home_y` en el SoA del mosquito.** La revisión de filopatria
natal (ver §16) **no encontró ninguna medición publicada** de retorno al sitio natal
en *Anopheles*, y el mecanismo que la literatura sí documenta (preferencia olfativa
por el habitat natal, 31,6–37,5 % de los huevos en agua natal, Kemibala 2026) es un
**sesgo por tipo de habitat**, no una distancia a una coordenada. La información "dónde se cría" no se pierde: la lleva la cohorte
acuática (§9), que es donde se origina.

Cada campo exige las tres operaciones que ya exige el SoA actual: `push_back` en el
constructor (`mosquito_submodel.cpp:236-260`, `:353-377`, `:522-553`), `std::swap` en la
compactación (`mosquito_submodel.cpp:135-158`) y `resize`
(`mosquito_submodel.cpp:163-180`). El olvido de uno de los tres corrupte el
SoA en silencio: es el riesgo mecánico más probable de la fase 3, y por eso el
plan exige un test explícito de round-trip de compactación.

`feeding_success` (float, 1.0/0.0) **deja de ser el portador del resultado del
sondeo**: pasa a ser un contador de comidas de la noche, y el resultado del sondeo
viaja en el ledger de eventos.

### 4. Ley de movimiento en cascada

Sustituye **el campo de búsqueda de hospedero** por celda (`host_seeking.hpp`:
`compute_attraction`, `cell_attraction`, `detect_host_cell`, `step_toward_host`) y el
paso de aproximación por celda. El **núcleo de oviposición**
(`oviposition_seeking.cpp`: `compute_attraction` con `potential × exp(-d/scale)`) **no**
lo reescribe la cascada: lo que la cascada cambia en oviposición es (a) el **campo de
búsqueda** —la hembra deja de elegir "celda ganadora" y elige **sitio** por la ley de
viaje a la oviposición (final de esta sección)— y (b) la entrada `oviposition.scale_m`
(la única ligazón entre la hembra gravídica y un criadero), que **se retira** en el
paso que reescribe ese núcleo (§15, Paso 9).

El módulo se reescribe como una máquina de estados por tramo de distancia, con
radios **por especie** tomados de `species.<fila>`:

```
                    ┌──────────────────────────────────────────┐
   fase NIGHT ────▶ │ EXPLORACIÓN (sin estímulo)               │
                    │  paseo aleatorio correlacionado           │
                    │  + casting transversal al viento         │
                    │  alcance: exploration_range_m (100 m)    │
                    └───────────────┬──────────────────────────┘
                                    │ d_min ≤ co2_activation_radius_m (100 m)
                                    ▼
                    ┌──────────────────────────────────────────┐
                    │ ACTIVACIÓN (CO₂ pulsado, sin dirección)  │
                    │  → orientarse al viento                  │
                    └───────────────┬──────────────────────────┘
                                    │ d_min ≤ olfactory_radius_m (30–70 m)
                                    ▼
                    ┌──────────────────────────────────────────┐
                    │ RASTREO DE PLUMA                         │
                    │  anemotaxis optomotora contra el viento  │
                    │  temporizador de memoria olfativa →      │
                    │  casting si se pierde la pluma           │
                    └───────────────┬──────────────────────────┘
                                    │ d_min ≤ visual_radius_m (0,25–0,72 m)
                                    ▼
                    ┌──────────────────────────────────────────┐
                    │ APROXIMACIÓN VISUAL (sólo si hay olor)   │
                    │  banda de aproximación visual (0,72 m)  │
                    │  vector hacia la silueta                 │
                    └───────────────┬──────────────────────────┘
                                    │ d ≤ terminal_radius_m (0,10–0,20 m)
                                    ▼
                    ┌──────────────────────────────────────────┐
                    │ CONTACTO (hay presa) → ATERRIZAJE        │
                    │  contacto:   d ≤ radio terminal         │
                    │  aterrizaje: + v < 50 mm/s durante 3 s   │
                    │  (calor + humedad + olor) → COMIDA        │
                    └──────────────────────────────────────────┘
```

`d_min` = **distancia mínima del segmento recorrido al hospedero**, no la distancia
del extremo del paso (regla de barrido, más abajo). Nomenclatura: la banda de
**radio 0,72 m** es la *banda de aproximación visual* (ahí corre el integrador fino);
el *radio terminal* es la distancia de contacto, 0,10–0,20 m. No se confunden.

Reglas de la ley:

*   **Precedencia de las leyes de desplazamiento (una sola cadena).**
    1.  **Cascada sensorial**: decide el tramo en función de la distancia al hospedero
        más cercano, con radios **relativos a la posición actual** (CO₂ 100 m →
        olfativa 30–70 m → visual 0,25–0,72 m → radio terminal 0,10–0,20 m).
    2.  **Exploración**: en el tramo sin estímulo, el siguiente punto del paseo se
        sortea **dentro del disco de `exploration_range_m`** centrado en la posición
        actual.
    3.  **Macro-paso**: el desplazamiento es **velocidad × presupuesto de tiempo de
        vuelo**, con tope de **longitud de trayectoria** `daily_move_capacity_m`
        (590 m/día).
    4.  **Viento**: desvía el vuelo **upwind** (±30°) y puede **bloquearlo** —si la
        velocidad propia no supera el umbral (`wind_block_threshold_ms` =
        `flight_speed_ms`), el avance contra el viento queda bloqueado.
*   **El "sentido" es la distancia al hospedero más cercano dentro del radio de
    percepción**, no una puntuación de atracción. La preferencia por tipo de presa
    (`pref`) entra en el sorteo, no en el gradiente.
*   **Geometría del macro-paso: barrido acotado con detección de cruce.** El
    desplazamiento de un paso **no puede exceder el radio de la banda siguiente**
    (CO₂ 100 m → olfativa 70 m → visual 0,72 m → radio terminal 0,10–0,20 m): si el
    tramo completo excede ese radio, se recorre en sub-pasos de longitud ≤ radio de
    la banda siguiente. La entrada en banda se evalúa por la **distancia mínima del
    segmento recorrido al objetivo** (`d_min`), **no** por la distancia del extremo
    del paso: un mosquito que pasa a 40 m de la persona la ha detectado aunque el
    extremo del paso quede a 300 m.
    **Por qué esto no reproduce el fallo de `host_seeking.cpp`**: allí el paso se
    cuantiza con `lround` sobre celdas enteras de 1 km (`host_seeking.cpp:308` y `:311`,
    las dos llamadas a `lround`), de
    modo que un objetivo diagonal produce un desplazamiento de 0,354 celdas que se
    redondea a 0 y el objetivo se pierde; aquí la posición es **continua** (metros
    locales del AOI, §1) y el cruce se evalúa **sobre el segmento recorrido**, sin
    cuantización a celdas.
*   **Presupuesto de vuelo dirigido: derivado y consumible por día** (desarrollo en
    §5). El número rector es `daily_move_capacity_m = 590 m` **[P]**, y su semántica es
    **longitud máxima de trayectoria diaria (MDTpD, *mean distance travelled per
    day*)**, **no desplazamiento neto**: es la media de los cuatro valores medidos de
    MDTpD (486–695 m/día;
    `papers/anopheles-dynamics/wickramasooriya-2026-coluzzii-mrr-saotome-principe.md:23`).
    El presupuesto de vuelo dirigido es el
    **tiempo que la recorre**: `directed_flight_budget_h = 590 m ÷ flight_speed_ms`
    ⇒ **0,36–0,73 h** (590/0,45 = 1 311 s = 21,9 min; 590/0,225 = 2 622 s = 43,7 min).
    **El presupuesto es consumible por día, no por fase**: un tope por fase
    multiplicaría el desplazamiento diario por cuatro. La longitud de trayectoria del
    día queda acotada por `daily_move_capacity_m` = 590 m.
    **El desplazamiento neto es una salida, no un tope.** La misma fuente da una
    dispersión neta compuesta de **618–1 460 m en 11–15 días** (≈ **50–130 m/día**) y
    **FR50 = 399–1 128 m**; usar 590 m como **desplazamiento** sobrestimaría la
    dispersión neta entre **5 y 10×** ⇒ la magnitud que acota el motor es la
    **longitud de trayectoria**, y el desplazamiento neto se **deriva** de ella.
*   **La routine `adult_dispersal` se retira para ambos sexos.** El motor tiene hoy
    `MosquitoSubmodel::adult_dispersal` (`mosquito_submodel.cpp:1010`): gaussiana
    diaria, probabilidad 0,05/día (`dispersal.adult_prob_day`), σ = 450 m
    (`dispersal.adult_sigma_m`), **sin filtro de sexo**, con tope duro
    `dispersal.adult_max_m` = 2 000 m (clip dentro de la función `offset_m`,
    `dispersal.cpp:34-56`;
    `model_constants.yaml:231-233`). **Decisión: se retira para ambos sexos**; el único
    desplazamiento estocástico es el paseo de exploración de la cascada, acotado por
    `daily_move_capacity_m`. Con ello **desaparecen** la varianza de la gaussiana
    (σ = 450 m) y el tope de 2 000 m, y **dejan de existir** las tres claves
    (`dispersal.adult_prob_day`, `dispersal.adult_sigma_m`,
    `dispersal.adult_max_m`), el CLI (`--disperse-prob`, `--disperse-sigma-m`,
    `--disperse-max-m`) y sus campos `RuntimeOverrides`.
*   **`update_patch_id` y sus tres llamadas.** La routine
    (`mosquito_submodel.cpp:965-1004`) se retira en el paso 7, y para que la retirada
    sea completa se enumeran sus **tres** call sites: `mosquito_submodel.cpp:704`,
    `mosquito_submodel.cpp:844` y `mosquito_submodel.cpp:882` —las dos últimas dentro
    del bloque que reescribe el paso 5 (movimiento por fases)—. Ninguna sobrevive a la
    posición continua.
*   **El viento: nivel de referencia y regla exacta.** El motor sólo carga viento
    **ERA5 6-horario `u100`/`v100`** (`wind_field.cpp:47-56`, `wind_field.hpp:22-26`):
    es el viento a **100 m sobre el suelo**, sin nivel de superficie ni perfil
    vertical, y es **opcional** (`--wind-field`). La regla del plan se define sobre ese
    único nivel:
    *   **Referencia**: `u100`/`v100` (100 m AGL) **[M]**.
    *   **Regla**: el progreso **contra** el viento se bloquea cuando el componente de
        cola del viento, proyectado sobre la dirección de avance, es **≥ la velocidad
        propia de vuelo** (`flight_speed_ms`, 0,225–0,45 m/s): el mosquito no avanza
        más rápido de lo que el viento lo empuja. Umbral **[EP]** —"estimación propia,
        sin respaldo directo"—: la literatura mide velocidades de vuelo y de viento, no
        un umbral de bloqueo. **Nunca hardcodeado**: se calcula en tiempo de
        ejecución con la velocidad configurada.
    *   **Caso nocturno**: el plan cita un viento nocturno de **5,1 m/s a 40–290 m**,
        ~11× la velocidad máxima de vuelo. Con el único nivel disponible ese caso
        **bloquea el avance de forma permanente durante la noche**, y eso se **acepta
        como resultado documentado** del modelo con campo de viento cargado (no como
        error): es coherente con la estadística de permanencia medida (< 60 % de los
        adultos de *arabiensis* se movieron más de 50 m del sitio larvario, Tioyé 2026
        **[P]**). La limitación —el nivel de referencia (100 m) no es el nivel real de
        vuelo— queda declarada: no hay medición publicada del viento a la altura de
        vuelo en *Anopheles* **[NR]**.
    *   **Evaluación**: `WindField::wind_at(lon, lat, día, hora)` devuelve `u, v`
        (`wind_field.hpp:44`); la regla se evalúa con el viento de la **hora de la
        fase** en curso, no con un promedio diario.
    *   **Sin `--wind-field`**: el viento ambiente es 0 ⇒ la regla queda **inactiva**,
        con el comportamiento documentado en la salida (campo de viento ausente).
*   **La pluma es intermitente**: el estado de "rastreo" se pierde con probabilidad al
    salir de un filamento, y dispara el *casting*. No hay decaimiento exponencial
    continuo.
*   **Velocidad**: `flight_speed_ms` por especie (0,225–0,45 m/s en *coluzzii* **[P]**).
    El desplazamiento **no** es velocidad × duración completa de la fase: con la fase
    más larga por defecto (12 h) daría 9,7–19,4 km, frente a una longitud de
    trayectoria medida de 486–695 m/día **[P]**. El
    macro-paso se acota por el presupuesto de vuelo dirigido (§5), que es lo que hace
    que la velocidad medida y el MRR medido dejen de contradecirse.
*   **Radio de exploración: un disco alrededor de la posición actual.** El radio de
    exploración es el **radio del disco de exploración centrado en la posición actual**
    del mosquito, dentro del cual se sortea el **siguiente punto** del paseo; **no es
    una cota de desplazamiento** (eso es `daily_move_capacity_m`, que acota la
    **longitud de trayectoria** del día). Se fija en `exploration_range_m = 100 m`
    **[EP]**, con banda **100–200 m** **[EP]** para la sensibilidad.
    *   **Por qué 100 m y no 50 m**: el disco de exploración debe **contener** al disco
        de activación por CO₂ (`co2_activation_radius_m` = 100 m). Con un radio
        menor, la hembra **sólo activaría CO₂ si hay una persona dentro de su disco de
        exploración**, y el tramo ACTIVACIÓN sería **inalcanzable** salvo por
        movimiento fortuito: el estado de activación dejaría de ser una función del
        estímulo. La banda 50–100 m anterior se **retira** por esa razón.
    *   **Tensión declarada**: el dato de permanencia post-emergencia (Tioyé 2026:
        < 60 % de los adultos de *arabiensis* se movieron más de 50 m del sitio
        larvario) apunta a un radio menor; el valor por defecto prioriza la
        **alcanzabilidad de la cascada**, y la discrepancia queda registrada como banda
        de sensibilidad (100–200 m). En *A. gambiae* s.l. el 70 % de los recapturados
        apareció en otra zona (Diallo 2026), lo que acota la dispersión lejana.
*   **No hay filopatria natal que modelar**: Thomas et al. 2013 derivan sus curvas de
    dispersión *"assuming no philopatry"*. La ausencia de un comportamiento medido es
    un motivo para **no** implementarlo, no para implementarlo con un prior.
*   **El macro-paso no puede resolver la maniobra terminal** y no debe intentarlo: a
    1 s de paso, el mosquito avanza 22–45 cm, más que el radio terminal entero
    (10–20 cm). El micro-integrador cubre sólo la banda fina (§5).
*   **Un solo criterio de contacto, con precedencia.** Hay dos criterios candidatos
    y el plan fija cuál manda:
    *   **Contacto** (existe una presa): se decide **por distancia**,
        `d ≤ terminal_radius_m`, con `terminal_radius_m = 0,10–0,20 m` **[P]**
        (aterrizaje: 10–20 cm). El valor 0,10–0,15 m que aparecía en otro punto del
        documento se retira: la banda es **una sola**.
    *   **Aterrizaje**: exige **además** el **gate de velocidad**, `v < 50 mm/s`
        sostenida **3 s** (Hinze 2021 **[P]**), evaluable **sólo dentro de la banda de
        aproximación visual** (≤ 0,72 m), donde el integrador corre a 25 Hz
        (`dt = 0,04 s`) ⇒ **75 muestras en 3 s** (60 muestras a 20 Hz). Fuera de esa
        banda el macro-paso no produce ticks: **no hay criterio temporal evaluable**, y
        por eso el gate no puede ser el criterio primario.
    *   **Precedencia**: primero el **contacto** (distancia), después el **aterrizaje**
        (velocidad). La distancia sola decide que hay presa; la velocidad decide si la
        hembra se posa.

**Ley de viaje de la fase de oviposición.** La hembra gravídica no "elige celda por
atracción": hace un **paso dirigido al sitio de oviposición elegido**, con distancia
máxima de aproximación **acotada por el presupuesto de movimiento del día**
(`daily_move_capacity_m` = 590 m **[P]** —longitud de trayectoria, no desplazamiento
neto—, y por el remanente
`directed_flight_budget_h_restante`), y elige **entre los sitios alcanzables** por
señal (potencial de hábitat × respuesta temporal, §9), no por distancia mínima. La
elección del sitio es, por tanto, **una elección entre alcanzables**: los sitios fuera
del alcance diario no son candidatos en esa noche. Al llegar, se aplica la
**regla de salida del sitio** ya existente (`oviposition.min_attraction` = 0,3
`model_constants.yaml:265`), que decide si la hembra pone o pasa a la búsqueda de otro
sitio (hasta `oviposition.timeout_days` = 7 días). Con la retirada de
`oviposition.scale_m`, **la hembra gravídica conserva una ligazón con el criadero**:
la ley de viaje y la regla de señal la sustituyen.

### 5. Base temporal: macro-paso acotado + micro-integrador adaptativo de dos bandas

El motor no tiene hoy reloj de fase ni sub-pasos: el día es un
`for p < PHASE_WEIGHT_COUNT` (`mosquito_submodel.cpp:803-805`) con **cuatro pasadas de
fase de igual peso** —la duración de cada fase no existe todavía como dato del motor
(§12.2)—. La cascada sensorial abarca cuatro décadas de escala
(100 m → 10 cm) y no puede representarse con un único integrador.

**Restricción geométrica.** El paso del integrador no puede superar el radio que
intenta resolver. Con la velocidad propia medida (0,225–0,45 m/s) y el radio terminal
medido (0,10–0,20 m), un paso de 1 s avanza 22–45 cm: **mayor que todo el radio
terminal**, luego con 1 s la aproximación terminal es literalmente irresoluble.

**Restricción temporal.** El evento más rápido medido en la literatura es el giro en
el punto más cercano (desaceleración de 40 a 30 cm/s en los 0,08 s previos, aceleración
angular de 12 500 °/s² medida entre 0,04 s antes y 0,04 s después; Hawkes & Gibson
2016). Nyquist ⇒ `dt ≤ 0,08 s`; para tener varias muestras sobre el evento, `dt`
debe quedar por debajo de 0,1 s. **Aritmética**: `f = 1/dt`; muestras por evento de
0,08 s = `0,08/dt`. Con `dt = 0,05 s` (20 Hz) el evento de giro recibe
`0,08/0,05` = **1,6 muestras**, que **no** satisface el criterio que el propio plan
enuncia ("varias muestras"): 1,6 muestras no son varias. **Decisión: `dt = 0,04 s`
(25 Hz ⇒ 0,08/0,04 = 2 muestras sobre el evento)**, que además coincide con la
frecuencia empírica de 25 fps / 0,04 s (Spitzen 2013). El coste del integrador sube
un 25 % respecto de `dt = 0,05 s` (360 000 ticks/mosquito-fase frente a 288 000; de
0,13–13 s/día a **0,16–16 s/día** en el escenario realista de la tabla de coste):
aceptable, y preferible a una afirmación de cobertura que el paso temporal no
sostiene.

**Frecuencias empíricas.** 50 Hz (Hawkes & Gibson 2016, 20 ms por desplazamiento;
Carnaghi 2023), 25 fps / 0,04 s (Spitzen 2013), 90 fps (Cribellier 2018), 60 fps (Hinze
2021), 68 fps (Batista 2019), 0,01 s (Zuo 2026 en *Aedes*). Precedente de modelo:
Cribellier et al. 2026 simula el enjambre con `Δt = 0,02 s`, *"the same as the empirical
video frame rate"*.

Diseño (decisión D1 = a, con el paso temporal corregido por la evidencia):

```
por día
  por fase p (DAY, EVENING, NIGHT, DAWN) con duración phase_duration_hours[p]
                                    y peso activity_weights[p] > 0
    ── macro-paso ─────────────────────────────────────────────
    para cada mosquito activo en fase p:
      0. presupuesto_diario_restante = directed_flight_budget_h   # 0,36–0,73 h (derivado)
         # presupuesto POR MOSQUITO Y POR DÍA: se inicializa DENTRO del bucle
      1. elegir régimen de movimiento (cascada, §4)
      2. t_vuelo = min(t_fase, presupuesto_diario_restante)
         desplazamiento = velocidad × t_vuelo
         presupuesto_diario_restante -= t_vuelo              # consumible POR MOSQUITO Y POR DÍA
      3. **barrido acotado**: el desplazamiento NO puede exceder el radio de la
         banda siguiente (CO₂ 100 m → olfativa 70 m → visual 0,72 m → radio
         terminal 0,10–0,20 m); si el tramo completo excede ese radio, se
         recorre en sub-pasos de longitud ≤ radio de la banda siguiente
      4. **detección de cruce**: d_min = distancia mínima del segmento recorrido
         al hospedero; si d_min ≤ radio de la banda siguiente, el mosquito ENTRA
         en esa banda, aunque el extremo del paso quede lejos
      5. si NO está en el micro-integrador:
           aplicar el macro-paso; la entrada en banda se evalúa por d_min
      6. si está en la banda olfativa (0,72–70 m):
           integrar con dt = 0,25 s hasta agotar la fase o el tiempo de vuelo
      7. si ha entrado en la banda de aproximación visual (≤ 0,72 m):
           integrar con dt = 0,04 s (o el resto de la fase)
    ── fin macro-paso
```

*   **Macro-paso**: un paso por fase, con la **duración** de fase en la configuración
    (`phase_duration_hours`, §12.2) y el **peso** de la fase (`activity_weights`, §12.2),
    y **acotado por un presupuesto de tiempo de vuelo
    dirigido** (`directed_flight_budget_h`) que es **consumible por día**, no por
    fase. El número no es una constante libre de "~1 h": es
    `daily_move_capacity_m / flight_speed_ms` = 590 m ÷ (0,225–0,45 m/s) =
    **0,36–0,73 h** (21,9–43,7 min), con `daily_move_capacity_m = 590 m` **[P]** =
    **longitud máxima de trayectoria diaria (MDTpD)**, media de los valores medidos
    486–695 m/día
    (`papers/anopheles-dynamics/wickramasooriya-2026-coluzzii-mrr-saotome-principe.md:23`);
    el desplazamiento neto es **salida** (§5.1).
    Sin ese
    tope, velocidad × fase = 9,7–19,4 km/día (con la fase más larga por defecto,
    12 h), que contradice el MRR medido por un orden de
    magnitud. El acumulador `presupuesto_diario_restante` se reinicia **por mosquito y
    por día** (se inicializa dentro del bucle de mosquitos): un tope por fase
    multiplicaría el desplazamiento diario por cuatro, y un acumulador compartido por
    todos los mosquitos del día haría que el primero consumiera el presupuesto
    entero.
*   **Micro-integrador de dos bandas** (reemplaza a los "ticks de 1 s" de la primera
    redacción):
    *   **Banda de aproximación visual** (≤ radio visual 0,72 m): `dt = 0,04 s`
        (25 Hz). El paso resultante (0,9–1,8 cm) queda por debajo de la distancia
        media de cierre al blanco (5,4 ± 0,85 cm) y del radio terminal (10–20 cm).
        Cubre el ciclo de dipping (0,43–0,51 s ⇒ 10,8–12,8 muestras) y el evento de
        giro (0,08 s ⇒ 2 muestras). El evento de giro queda como **cota de
        detección** (se ve que ocurre), no como maniobra resuelta.
    *   **Banda olfativa** (0,72–70 m): `dt = 0,25 s`. A 0,45 m/s el mosquito cruza
        70 m en 155 s sin maniobra rápida; la única razón de micro-integrar aquí es
        la máquina de estados de la pluma (*surge*/*cast*, con segmentos crosswind de
        0,5–0,9 s, Cummins 2012).
    *   **Fuera del radio olfativo**: paso macro por fase. El micro-integrador **no
        aporta nada** en campo lejano.
*   **Coste** (con `c ≈ 0,1 µs` por tick y 4 h de fase):

    | `dt` (s) | ticks/mosq-fase | N=10 | N=100 | N=1000 |
    |---|---|---|---|---|
    | 1 | 14 400 | 14 ms | 0,14 s | 1,44 s |
    | 0,25 | 57 600 | 58 ms | 0,58 s | 5,76 s |
    | 0,05 | 288 000 | 0,29 s | 2,88 s | 28,8 s |
    | **0,04 (elegido)** | **360 000** | **0,36 s** | **3,6 s** | **36 s** |
    | 0,02 (precedente) | 720 000 | 0,72 s | 7,2 s | 72 s |

    Con `N_dentro` realista en la banda olfativa (≈ 4,5–45 con 10²–10³ adultos y 10⁴
    personas; 45–450 con 10⁵ personas, sobre un AOI de 3 416 km² y R = 70 m), el
    coste a **0,04 s es 0,16–16 s/día** (tolerable) y a 0,02 s **0,3–32 s/día**. Si el
    micro-integrador corriera **globalmente**, 0,02 s daría 7–72 s/día: inaceptable.
    **El coste no es lo que mata los ticks de 1 s — la resolución es lo que los mata.**
    La condición de funcionamiento es que el micro-integrador sólo corra dentro de la
    banda de percepción.
*   **Criterio de abandono**: el presupuesto por mosquito-día es **0,16–16 s/día**
    (NFR-3). Si **un día** de la corrida supera **60 s**, se **acorta la corrida** o se
    **reduce `N_dentro`** (el número de mosquitos dentro de la banda de percepción):
    un escenario no se puede validar con un día cuyo coste se ha salido del
    presupuesto.
*   **Memoria olfativa**: no hay valor primario en *Anopheles*. Lo único medido es que
    el ORN de CO₂ de *coluzzii* rastrea **pulsos de 1 s separados por 1 s** (Majeed
    2017), con la latencia de activación sólo en figuras ⇒ **[NR]** en segundos. Los
    300 ms (Dekker 2005) y 0,03 s (Dekker & Cardé 2011) son de *Aedes* ⇒ **[P]**. El
    "≈2 s" que circulaba en la síntesis secundaria **se elimina**: no tiene fuente.
    El valor de diseño es **0,5–0,9 s** (segmentos de *cast*, Cummins 2012).
*   **Latencia de respuesta a ráfaga de viento**: no hay medición publicada (la
    literatura del viento trata tasas, no latencias) ⇒ el integrador no necesita
    resolución sub-segundo para capturar el viento.
*   **Un solo criterio de contacto, con precedencia** (regla completa en §4):
    **contacto** por distancia (`d ≤ terminal_radius_m`, 0,10–0,20 m) y **aterrizaje**
    por el gate de velocidad (`v < 50 mm/s` sostenida 3 s, Hinze 2021 **[P]**),
    evaluable **sólo dentro de la banda de aproximación visual** (≤ 0,72 m), donde
    `dt = 0,04 s` ⇒ 25 Hz ⇒ **75 muestras en 3 s**. El gate de velocidad **no**
    sustituye a la distancia: es el segundo criterio, no el único.
*   **Determinismo**: el consumo de RNG del micro-integrador debe ser determinista y
    reproducible; los draws usan un stream derivado del `uid` del mosquito, para que el
    orden de recorrido no altere el resultado.
*   **Deuda de implementación**: el estado del motor está en celdas de 1 km; la banda
    fina exige coordenadas continuas **a escala métrica** en el SoA (§1).

#### 5.1 — Presupuesto de encuentro: por qué G1 no se cierra sólo con el movimiento

Cascada de densidad a picaduras, con los datos de entrada de P1 (**[M]**) y la
aritmética ** [EP]** ("estimación propia, sin respaldo directo"):

| Magnitud | Cálculo | Valor |
|---|---|---|
| Densidad de adultos | 122 adultos / 3 416 km² | **0,036 adultos/km²** |
| Densidad de personas | 40 255 susceptibles / 3 416 km² | **11,8 personas/km²** |
| Área del disco CO₂ (R = 100 m) | π·(0,1 km)² | **0,0314 km²** |
| Área del disco de exploración (R = 100 m) | π·(0,1 km)² | **0,0314 km²** |
| Personas esperadas en el disco CO₂ | 11,8 × 0,0314 | **0,370** |
| Personas esperadas en el disco de exploración | 11,8 × 0,0314 | **0,370** |
| Prob. de que el disco de exploración contenga ≥1 persona | 1 − exp(−0,370) | **31 %** |
| Picaduras por mosquito-noche (antes de `probing_success_rate`) | 0,370 | **0,370** |
| Picaduras por mosquito-noche (con `probing_success_rate` 0,465–0,99) | 0,370 × p | **0,172–0,366** |
| Picaduras por noche en todo el AOI | 122 × (0,172–0,366) | **21–45** |
| Ciclos gonotróficos iniciados por noche (dos comidas por ciclo) | (21–45) / 2 | **10,5–22,3** |

> **El 0,825 no es el valor de `probing_success_rate`.** El 0,825 es el valor de la clave
> **retirada** `gonotrophic.feeding_success_rate`, que el motor cargaba sin consultar
> (§12). La clave nueva `probing_success_rate` tiene rango **0,465–0,99** [EP] (§5.2);
> el 0,825 se conserva sólo como punto de referencia histórico dentro de ese rango.
> **G1 no tiene suelo de densidad.** El valor 0,036 adultos/km² es el dato medido del AOI (122 adultos / 3 416 km²), no un criterio: G1 se comprueba en escenarios sintéticos cuya densidad fija el propio escenario (Nivel 6).

> **Nota (radio de exploración).** Esta tabla usa el disco de exploración del valor por
> defecto **100 m** (§4, `exploration_range_m`): π·(0,1 km)² = 0,0314 km². Con la banda
> 100–200 m el rango se multiplica por 1 a 4; la fórmula (personas en el disco ×
> `probing_success_rate`) no cambia.

Consecuencia: con la densidad de adultos medida, el AOI produce del orden de **21–45 picaduras por noche en total** (**0,172–0,366 picaduras por mosquito-noche**), frente a las **0** actuales. Esa cifra describe el AOI real; **no es criterio de G1** y no se fija ninguna densidad de picaduras por mosquito. G1 se comprueba en escenarios sintéticos donde deben darse picaduras, transmisión y transmisión efectiva en la persona picada (Nivel 6).

**Las dos magnitudes que acotan el desplazamiento (base de la banda de E02).** La
**longitud de trayectoria** del día está acotada por `daily_move_capacity_m` = 590 m
(MDTpD medido, §4), y el **desplazamiento neto por noche** está acotado por el
diámetro del disco de exploración, `2 × exploration_range_m` = **200 m**. La banda de
E02 (Apéndice A) se deriva de estas dos cifras: **no** es una banda empírica
independiente.

#### 5.2 — Inventario de claves del movimiento

Toda mecánica nombrada en §4, §6 y §7 necesita su clave. **Ninguna de las claves de
esta tabla existe hoy** en `mal-core/config/model_constants.yaml` (comprobado: no hay
`blood_meal_*`, `phase_duration_hours`, `probing_success_rate`, `exploration_range_m`
ni `directed_flight_budget_h`): todas son **nuevas** y entran por el esquema de
configuración (§12).

| Clave | Valor | Unidad | Tier | Referencia / nota |
|---|---|---|---|---|
| `exploration_range_m` | 100 (banda 100–200) | m | [EP] | radio del **disco de exploración** centrado en la posición actual (no es cota de desplazamiento); ≥ `co2_activation_radius_m` (100 m) para que el tramo ACTIVACIÓN sea alcanzable; banda de sensibilidad [EP] |
| `exploration_step_m` | 50 | m | [EP] | longitud nominal del paso del paseo de exploración |
| `exploration_step_correlation` | 0,5 | [adimensional] | [EP] | correlación paso–paso (paseo correlacionado, no paseo libre) |
| `casting_probability` | 0,10 | [1/paso de rastreo] | [EP] | probabilidad de perder la pluma y pasar a *casting*; la intermitencia está medida (61,4 ± 3,9 % del tiempo de vuelo fuera de los límites teóricos, P2) pero la probabilidad por paso no |
| `casting_angle_deg` | 90 ± 30 | ° | [EP] | transversalidad del *casting* respecto al viento |
| `plume_memory_s` | 0,5–0,9 | s | [P] | segmentos de *cast* (Cummins 2012) |
| `anemotaxis_rule` | contra el viento (*upwind*), desviación ± 30° | — | [EP] | sin medición publicada del ángulo de orientación |
| `wind_reference` | `u100`/`v100` (100 m AGL, ERA5 6-horario) | — | [M] | `wind_field.cpp:47-56`, `wind_field.hpp:22-26`; único nivel disponible |
| `wind_block_threshold_ms` | = `flight_speed_ms` | m/s | [EP] | umbral de bloqueo del avance contra el viento; sin respaldo directo |
| `flight_speed_ms` | 0,225–0,45 | m/s | [P] | *coluzzii* en busca |
| `daily_move_capacity_m` | 590 | m | [P] | **longitud máxima de trayectoria diaria (MDTpD)**, no desplazamiento neto; media de los MDTpD medidos 486–695 m/día (`papers/anopheles-dynamics/wickramasooriya-2026-coluzzii-mrr-saotome-principe.md:23`) |
| `directed_flight_budget_h` | 0,36–0,73 | h | [EP] | **derivado**: 590 m ÷ `flight_speed_ms`; consumible **por día** |
| `co2_activation_radius_m` | 100 | m | [P] | activación por CO₂ |
| `olfactory_radius_m` | 30–70 | m | [P] | rastreo de pluma |
| `visual_radius_m` | 0,25–0,72 | m | [P] | banda de aproximación visual (integrador fino) |
| `terminal_radius_m` | 0,10–0,20 | m | [P] | radio terminal (contacto); banda única |
| `phase_duration_hours` | DAY 12 / EVENING 4 / NIGHT 6 / DAWN 2 | h | [EP] | **decisión del autor** (K-3): valores del plan, en el YAML (`integration.phase_duration_hours`), que **sustituyen** a la tabla compilada (`mobility_schedule.hpp:41-46` sólo tiene el enum y sus ventanas en comentarios); **suman 24 h**; el reparto de los bins EE/LE/EM sobre las cuatro fases lo fija §12.2 |
| `probing_success_rate` | 0,465–0,99 | [fracción] | [EP] | por especie; sustituye a `feeding_success_rate` (0,825), que el motor cargaba sin consultar |
| `blood_meal_target_ul` | 0,5 | µL | [EP] | objetivo de una comida completa |
| `first_cycle_target_ul` | 0,8 | µL | [EP] | > `blood_meal_target_ul`: hacen falta dos comidas |
| `blood_meal_size_ul` | 0,3 | µL | [EP] | media del volumen tomado por comida |
| `meal_size_min_ul` | 0,1 | µL | [EP] | volumen mínimo de una comida válida |
| `blood_meal_refractory_days` | 0,5 | días | [EP] | ventana postprandial tras alcanzar el objetivo |
| `eggs_per_ul` | 223 | [huevos/µL] | [EP] | calibrado para que 0,5 µL dé ≈112 huevos, la puesta medida en *coluzzii* (111,67 ± 5,36) **[P]** |
| `gonotrophic_arrest_prob_dry` | 19,23–34,85 / 40,09–48,98 / 68,12–68,64 % | [fracción] | [P] | *coluzzii* / *arabiensis* / *gambiae* s.s. |
| `arrested_daily_survival` | 0,986 | [1/día] | [EP] | derivado de los hasta 212 días de estivación **[P]**: 212·ln(0,986) ⇒ sⁿ = 0,05 |

**Longitud de trayectoria frente a desplazamiento neto.** `daily_move_capacity_m`
acota la **longitud de trayectoria** diaria (590 m, MDTpD medido); el
**desplazamiento neto** es una **salida** del modelo: la misma fuente da 618–1 460 m de
dispersión neta compuesta en 11–15 días (≈50–130 m/día) y FR50 = 399–1 128 m. Usar
590 m como desplazamiento sobrestimaría la dispersión neta entre 5 y 10×.

### 6. Pickup de presa, multipicadura y fisiología de la sangre

La transición actual (`mosquito_submodel.cpp:757-779` y `:855-862`) es
determinista: `if (picked != nullptr) → BLOOD_FED`. Se sustituye por:

```
PROBING
  ├─ sortea probing_success_rate (por especie, 0,465–0,99) [EP]
  │    ├─ fallo ─▶ vuelve a HOST_SEEKING (misma noche, mismo fase)
  │    └─ acierto
  │         ├─ sortea volumen v ~ lognormal(blood_meal_size_ul, σ)
  │         ├─ blood_volume_ul += v
  │         ├─ registra evento en el ledger (mosquito, presa, fase, v, resultado)
  │         ├─ si blood_volume_ul < blood_meal_target_ul
  │         │    └─ vuelve a HOST_SEEKING (misma noche)   ◀── NUEVO
  │         └─ si blood_volume_ul ≥ blood_meal_target_ul
  │              ├─ arranca el reloj gonotrófico
  │              ├─ abre la ventana postprandial
  │              └─ BLOOD_FED
```

Detalles:

*   **El flag "alimentada hoy" no significa "sangre completa"**: `feeding_success` pasa
    a ser un contador de comidas de la noche; el estado physiological lo decide
    `blood_volume_ul` frente al objetivo.
*   **La salida del bucle de búsqueda dentro de la misma fase**: hoy el flujo por fases
    tiene un `break` implícito cuando una hembra entra en `BLOOD_FED`. Con la
    multipicadura, la iteración por fases debe continuar con un flag "todavía hambrienta"
    por hembra.
*   **Primer ciclo (pre-gravídica)**: `first_cycle_target_ul` = 0,8 µL **[EP]** >
    `blood_meal_target_ul` = 0,5 µL **[EP]**; hacen falta dos comidas (una comida no
    completa la sangre necesaria). El motor ya distingue `first_cycle_days` (4,0) de
    `cycle_duration_days` (2,0).
*   **Reloj de inanición propio**: `days_since_target_reached` no se reinicia con las
    comidas parciales; el `gonotrophic_timer` actual no sirve (se pone a 0 en cada
    transición).
*   **El descanso post-prandial** (`resting_duration_days` = 0,5 día) sólo se dispara al
    alcanzar el objetivo; una comida parcial no oviposita. La ventana postprandial se
    expresa con `blood_meal_refractory_days` = 0,5 día **[EP]**.
*   **Lote de huevos ∝ volumen acumulado** (MBITES), no `binomial(egg_batch_n, p)`:
    `huevos = round(blood_volume_ul × eggs_per_ul)` con `eggs_per_ul` = 223
    [huevos/µL] **[EP]**, calibrado para que un objetivo de 0,5 µL dé ≈112 huevos,
    la puesta medida en *coluzzii* (111,67 ± 5,36) **[P]**. Esto **rompe la invariante
    de validación** `0 < min <= mean <= max <= n` de
    `config_validation.py`; el bloque `gonotrophic` se **redefine** (no se "corrige con
    un valor"), y el test `test_config_validation.py` que la fija se reescribe.
*   **El `feeding_success_rate` (0,825) se retira** del esquema de configuración: se
    carga en `GonotrophicParams` (`gonotrophic_cycle.hpp:71`) pero el motor no lo
    consulta. Se sustituye por `probing_success_rate`, por especie.

### 7. Estado fisiológico y época seca

*   `ovarian_stage` se deriva del reloj gonotrófico (opción d de la revisión 2 del diseño
    previo): ciclo 0 ⇒
    pre-gravídica; ciclo cerrado ⇒ gravídica. `gonotrophic_cycles` es el reloj maestro.
*   `ARRESTED` es un estado nuevo de la máquina gonotrófica: hembra alimentada y
    gravídica en celda **sin criadero elegible** durante una racha de días secos.
    No muere, no pone; espera.
*   La **parada ovárica** es por especie: `gonotrophic_arrest_prob_dry` con
    19,23–34,85 % para *coluzzii*, 40,09–48,98 % para *arabiensis*, 68,12–68,64 % para
    *gambiae* s.s. **[P]**; y `aestivation_supported` por especie (`true` para
    *coluzzii*, `false` para *gambiae* s.s., que no estiva).
*   La **supervivencia en arresto** es propia (`arrested_daily_survival` = **0,986
    por día** **[EP]**, muy superior a la basal de 0,87/día): la literatura da hasta 212
    días de estivación **[P]**, y el valor propio se deriva de ahí (sⁿ = 0,05 con
    n = 212 ⇒ s = 0,986). Una hembra en `ARRESTED` no muere a los 7 días.
*   El **disparador es la racha de días secos de la celda**, no el calendario: es el
    mismo disparador que activa el estrés acuático.

### 8. Apareamiento y enjambres (macho-individual con sitio asignado; enjambre, agregado por sitio)

Los machos son **individuos en el SoA** — el SoA ya los guarda (`mosquito_state.hpp:37`,
`sex` = 0 MALE / 1 FEMALE) y el ciclo gonotrófico los excluye
(`mosquito_submodel.cpp:569`), de modo que no comen sangre ni ponen huevos. Lo que hoy
**no** existe es su conducta: se mueven con el kernel de dispersión de la hembra
(`adult_dispersal`, `mosquito_submodel.cpp:1010`, sin filtro de sexo) y mueren con su
tasa (0,87, hoy compartida).

Esta sección define esa conducta: **cada macho y cada hembra llevan un sitio de
enjambre asignado al nacer** (decisión F: la hembra recibe sitio igual que el macho), y
el enjambre es el agregado de los machos asignados a ese sitio durante la ventana
nocturna**. La granularidad individual está justificada por la literatura; la
granularidad *subcelular* del enjambre no (ver §8.3).

#### 8.1 — El ciclo del macho, de la eclosión al apareamiento

| Tramo | Mecanismo | Valor | Fuente / tier |
|---|---|---|---|
| Eclosión | el adulto emerge en la **posición exacta de la madre** (campo nuevo `mother_x`/`mother_y` en la cohorte acuática) | — | §9 |
| Dieta | el macho **no** se alimenta de sangre; sólo sugar | — | — |
| Supervivencia | tasa **propia**, separada de la hembra | **0,773 ± 0,094**/día | Epopa et al. 2017 **[M]** |
| Sugar | dependencia de sugar como mecanismo de supervivencia | con sugar **3,84–4,94 días** de vida; sin sugar **1,94–2,99** | Gary et al. 2009 **[P]** |
| Presupuesto de movimiento | dispersión neta **medida por experimento** (es un **rango**, no una media), no tasa diaria | **rango de 40 a 549 m** en ventana de recaptura ≤ 7 días (*coluzzii*); media **85,7 m** y **ninguno más allá de 100 m** (*arabiensis*) | Epopa 2017; Kaiser 2021 **[P]** |
| Asignación de sitio | en la eclosión, el macho elige entre los **alcanzables** (distancia ≤ `male_move_capacity_m`) con peso ∝ hembras alcanzables × (1 + machos ya asignados), o queda **suelto** (peso `w_suelto` = 1 [EP]); sin sitio (ninguno alcanzable o suelto), **no se reproduce** (`swarm_site_id = -1`) | `male_move_capacity_m` = 50 m/día | §8.6 **[EP]** |
| Ventana de enjambre | cada noche, en la ventana posterior a la puesta de sol | inicio **18:05–18:45**; duración **28,3 min** (media del rango mensual **19–39 min**; Ouédraogo 2025 mide ≈**27 min**, compatible con esa banda); **5–33 min** tras la puesta de sol | Bimbilé Somda 2018 **[P]**; Ouédraogo 2025 **[M]** |
| Entrada en el enjambre | un macho empieza a volar sobre el marcador 2–3 min tras la puesta de sol; otros se unen en 7–90 s | t = **46 ± 8 s** | Poda et al. 2024 **[M]** |
| Fidelidad | el macho **conserva su sitio** durante su vida; el campo de sitios es estático, luego la permanencia es automática | un macho liberado seguía en un sitio de enjambre **8 días** después | Kaiser et al. 2021 **[P]** |
| Apareamiento | **azar**, no selección sexual; cupos por sitio y noche | **0,072 ± 0,0095** = fracción de machos del enjambre que se aparea por noche (*gambiae* s.s.) **[P]**; **0,084–0,25** = pares por individuo de **ambos sexos** por enjambre (*coluzzii*) **[M]**, magnitud **no comparable** con la anterior | Diabaté 2011; Ouédraogo 2025 |
| Reintento | si no se insemina, reintenta cada noche; el esperma dura de por vida | — | — |
| La hembra asiste | la hembra va al **sitio** (asignado al nacer, igual que el macho), con tasa baja | **10,33 %** (47/455 hembras *tethered* inseminadas en enjambres M-form) = probabilidad de que una hembra **presente en el sitio** esté en posición de cópula; se aplica **una sola vez**, en el término de presencia (§8.1) | Diabaté 2009 **[P]** |
**El pseudo-algoritmo** tiene dos piezas: una asignación **al nacer** (discreta, sin
vuelo simulado) y una asistencia **por noche** (agregada por sitio).

```
# elegir(C, H, n): s ∈ C con peso ∝ H[s] × (1 + n[s]); peso w_suelto = 1 para «suelto» (-1).
#   H[s] = hembras alcanzables de s (para el macho); n[s] = machos ya asignados a s (acumulación).
#   Para la hembra: M[s] = machos alcanzables de s; n_f[s] = hembras ya asignadas a s.
# Los sitios no se eligen a mano: son el campo generado (Paso 8). Asignación en orden de id.
al emerger el macho m (posición de la madre, x_m, y_m):
    candidatos = { s ∈ sitios : dist((x_m,y_m), s) ≤ male_move_capacity_m }   # 50 m/día
    if candidatos ≠ ∅:
        m.swarm_site_id  = elegir(candidatos, H, n)       # estocástico, con acumulación; puede quedar suelto (§8.6)
        m.inseminated    = 0 ; m.nights_uninseminated = 0
    else:
        m.swarm_site_id  = -1     # estado de primera clase: SIN SITIO (§8.2);
                                 # el macho no se reproduce: no ofrece cupos (§8.6)

al emerger la hembra f (posición de la madre, x_f, y_f):
    # la hembra RECIBE SITIO AL NACER, igual que el macho (decisión F, §3)
    # mismo criterio de alcance que el macho: `male_move_capacity_m` (50 m/día)
    candidatos_f = { s ∈ sitios : dist((x_f,y_f), s) ≤ male_move_capacity_m }
    if candidatos_f ≠ ∅:
        f.swarm_site_id  = elegir(candidatos_f, M, n_f)    # simétrica: pesa por machos alcanzables (§8.6)
    else:
        f.swarm_site_id  = -1     # SIN SITIO: no asiste a ningún enjambre

cada noche, dentro de la ventana de enjambre:
    for cada macho adulto m con swarm_site_id ≥ 0:   # los machos SIN SITIO no se reproducen
        destino = m.swarm_site_id
    for cada sitio s del campo:
        M(s)          = Σ { m : destino(m) = s y m está vivo }        # tamaño del enjambre
        M_disp(s)     = Σ { m : destino(m) = s y m está vivo y NO está inseminado }
                       # los machos ya inseminados siguen en el enjambre (forman parte
                       # de M(s)) pero no vuelven a aparearse: el esperma dura de por vida
        male_offer_factor(s) = (s es un sitio del campo) ? 1 : local_swarm_male_offer_factor
                       # valor por defecto 0: no hay medición de asistencia de hembras
                       # a enjambres sin marcador (Kaiser et al. 2021) ⇒ [EP]
                       # actúa sobre el lado MASCULINO: reduce la oferta de cupos.
                       # En el diseño vigente todo s es un sitio del campo: el enjambre
                       # local no se crea (no hay machos sin sitio asignables, §8.6), de
                       # modo que el factor no llega a cambiar la oferta.
        cupos(s)      = M_disp(s) × p_mate_male_fraction
                       × (M(s) / male_swarm_reference_size)^(−p_mate_size_exponent)
                       # p_mate_male_fraction = 0,072 ± 0,0095 (fracción de machos del
                       # enjambre que se aparea por noche) [P]
                       # p_mate_size_exponent = 0 ⇒ eficiencia por macho constante
                       # (Diabaté 2011); > 0 ⇒ eficiencia decreciente con el tamaño
        hembras_alcance(s)   = hembras no inseminadas con swarm_site_id = s
        hembras_presentes(s) = hembras_alcance(s) × female_attendance_rate
                       # female_attendance_rate = 0,1033 [P] (Diabaté 2009): probabilidad de
                       # que una hembra presente en el sitio esté en posición de cópula.
                       # LA ASISTENCIA SE APLICA UNA SOLA VEZ, AQUÍ (término de presencia).
        p(inseminada | hembra presente) = 1 − exp( − cupos(s) / max(1, hembras_presentes(s)) )
        p(inseminada | hembra del alcance) = (hembras_presentes(s) / hembras_alcance(s))
                                              × p(inseminada | hembra presente)
                       # el cociente es la asistencia (0,1033), NO una segunda aplicación
                       # de ella; esta es la probabilidad incondicional por hembra del
                       # alcance, la que consume el diagnóstico de alarma (§8.6)
        sortear las parejas; los machos emparejados quedan inseminados;
        los que no, incrementan nights_uninseminated
```

**El apareamiento ya no es un estado.** El valor `MATE_SEEKING` del enum
`GonotrophicState` (`gonotrophic_cycle.hpp:28-40`) **se retira** (§3, §15, Paso 3): el
apareamiento se resuelve **por sitio y por noche**, con la hembra asistiendo al sitio
que se le asignó al nacer (decisión F) y `female_attendance_rate` aplicada **una sola
vez**, en el término de presencia. La máquina de estados se toca **también en el
Paso 8** (§15).

**Banda derivada de la fórmula de arriba (valores por defecto).** La aritmética que
sigue es la que produce el modelo con `p_mate_male_fraction` = 0,072 [P]
(`model_constants.yaml`, bloque `mating:`) y `female_attendance_rate` = 0,1033 [P],
con **100 hembras y 100 machos** recién-emergidos en una aldea de 1 km² y **un único
sitio de enjambre** alcanzable; la banda resultante es [EP], derivada de la fórmula y
de esos valores por defecto:

| Magnitud | Cálculo | Valor |
|---|---|---|
| `M(s)` / `M_disp(s)` (machos con sitio, sin inseminar) | 100 machos recién-emergidos, todos con sitio asignado | 100 / 100 |
| `cupos(s)` | `M_disp(s) × p_mate_male_fraction × (M(s)/100)^0` = 100 × 0,072 × 1 | **7,2 cupos/noche** |
| `hembras_presentes(s)` | 100 hembras × `female_attendance_rate` = 100 × 0,1033 | **10,33 hembras presentes** |
| `p(inseminada \| hembra presente)` | `1 − exp(−7,2/10,33)` = 1 − exp(−0,6970) = 1 − 0,4981 | **0,5019** |
| `p(inseminada \| hembra del alcance)` | asistencia (0,1033, aplicada **una sola vez**) × 0,5019 | **0,05185** (5,19 %/noche) |
| sin inseminar tras **1 noche** | 1 − 0,05185 | **94,81 %** |
| sin inseminar tras **3 noches** | (1 − 0,05185)^3 = 0,94815^3 | **85,24 %** (14,76 % inseminadas) |

Dos consecuencias que el implementer no debe reinterpretar: (a) la **oferta no cubre la
demanda** (7,2 cupos frente a 10,33 hembras presentes ⇒ razón 0,697 < 1), de modo que
el modelo queda limitado por la oferta masculina; (b) la banda publicada de *coluzzii*
(22,3–52,8 % a tres noches) viene de **otra unidad** (pares por individuo de ambos sexos
por enjambre) y **no** es la salida de esta fórmula: queda como cota de sensibilidad
de `p_mate_pairs_per_individual` (§8.5), no como criterio. Por eso **E13 pasa a
`report`** (Apéndice A): la banda que el modelo puede sostener con estos valores por
defecto es la derivada arriba.

#### 8.2 — La geometría espacial: el sitio, no la celda

La unidad de la capa macho **no es la celda de 1 km**, sino el **sitio de enjambre**:

*   **La hembra también recibe sitio, al nacer** (decisión F): el sitio se le asigna con
    la misma regla que al macho (§8.6) —un sitio **alcanzable**
    (`dist ≤ male_move_capacity_m`), con peso de acumulación o suelto (§8.6)—;
    si no hay ninguno alcanzable, `swarm_site_id = -1` y la hembra **no asiste a
    ningún enjambre**. El sitio de la hembra **no genera cupos**: la
    `female_attendance_rate` es la probabilidad de que una hembra **presente** en el
    sitio esté en posición de cópula (§8.1), y se aplica **una sola vez**.

*   El sitio explica el **47,6 %** de la varianza del tamaño del enjambre; el *tipo*
    de marcador no explica nada (F = 0,40, P = 0,26) ⇒ lo que importa es **dónde**,
    no **qué** hay (Diabaté et al. 2011) **[P]**.
*   El reparto de sitios **no es aleatorio**: Moran's I = **0,2** (P < 0,001) y
    Getis-Ord G observado **0,00876** vs **0,00392** esperado (P < 0,000014) ⇒
    "hot spots" (Ouédraogo et al. 2025) **[M]**.
*   Separación entre enjambres del mismo compuesto: **11,32 / 18,14 / 18,88 m**
    (Ouédraogo et al. 2025) **[M]**; los marcadores reportados son montones de leña, montones de basura
   y pozos (Diabaté et al. 2011; Niang et al. 2021).
*   Altura **2,87 ± 0,20 m**; duración ≈ **27 min** (18:05–18:45) (Ouédraogo et al.
    2025) **[M]**, dentro de la banda **19–39 min** que fija `swarm_duration_min`
    (§8.6); modo de tamaño ~100 y ~180 machos, rango real 4–700 (Diabaté et
    al. 2011) **[P]**; 35 enjambres por aldea, media de 50 mosquitos por enjambre
    (Niang et al. 2021) **[P]**.
*   **El radio de vida del macho es menor que una celda**: dispersión media 85,7 m
    (Kaiser et al. 2021) y **rango de dispersión neta de 40 a 549 m** (Epopa et al.
    2017), frente a celdas
    de 1 km ⇒ un agregado anclado a la celda mezclaría machos que no pueden estar en el
    mismo sitio.

**Regla de asignación (estocástica con acumulación).** Los sitios son el campo generado en el Paso 8 (densidad `swarm_markers_per_km2`, semilla explícita). **No se eligen a mano** y no hay separación mínima entre ellos. Al nacer, el macho considera los sitios **alcanzables** (distancia ≤ `male_move_capacity_m` = 50 m/día) y sortea uno con peso **∝ hembras alcanzables × (1 + machos ya asignados)**: se orienta hacia donde hay hembras, y el término `(1 + n)` hace que un sitio con machos atraiga más machos (acumulación). Una opción de peso `w_suelto` = 1 [EP] deja al macho **suelto**, sin sitio; así no todos los machos se asignan. Las asignaciones se hacen en orden de `id` y con RNG sembrado, para que el resultado sea reproducible. La hembra usa la misma forma con el papel invertido (peso ∝ machos alcanzables × (1 + hembras asignadas)); **esta simetría es una simplificación pendiente de revisión** (K-6). Un macho que emerge a más de 50 m de cualquier marcador queda **sin sitio** (`swarm_site_id = -1`) y **no se reproduce** (§8.6).

**Campo de marcadores: estático y persistente, no un número libre por corrida.** Los
enjambres se forman en **los mismos sitios, a las mismas horas, durante años**
(Somers et al. 2022; Diabaté et al. 2009/2011). El campo se calibra contra los valores
publicados; lo que queda libre es su **densidad** (`swarm_markers_per_km2`), con banda
y fuente declaradas.

**No hay enjambre local de respaldo.** Un macho que emerge sin ningún sitio alcanzable
dentro de `male_move_capacity_m` conserva `swarm_site_id = -1` y **no se reproduce**
(§8.6): no entra en ningún `M(s)`, no aporta a `M_disp(s)` y, por tanto, no genera
cupos. La clave `local_swarm_male_offer_factor` = 0 **[EP]** se conserva con ese
valor por defecto, coherente con que no hay medición de asistencia de hembras a
enjambres sin marcador (Kaiser et al. 2021 **[P]**): con la asignación vigente, ningún
macho pertenece a un enjambre local, de modo que el factor no llega a cambiar la
oferta; queda declarado para que el implementer no lo lea como una asistencia positiva.

**Decisión: `swarm_site_id = -1` es un estado de primera clase ("sin sitio").** Se
conserva el valor 0 para `local_swarm_male_offer_factor` en lugar de inventar una
asistencia positiva sin fuente, y la consecuencia se escribe explícita: un macho en
estado "sin sitio" **no se reproduce** (su `male_offer_factor` es 0: no ofrece cupos
y no puede ser emparejado) y **no muere por ello** (la supervivencia del macho no
depende del sitio). El estado es observable en el diagnóstico: el recuento de machos
sin sitio por noche es una de las salidas del paso 8, y su crecimiento indica que
`male_move_capacity_m` o la densidad de marcadores están mal calibrados. La
diferencia entre "sin sitio" y "con sitio sin oferta" es explícita en el modelo: el
primero es un estado del macho, el segundo es un factor del sitio.

#### 8.3 — Por qué no la opción 3 (machos con vuelo simulado al enjambre)

La alternativa descartada se documenta aquí porque **es la obvia** y porque un revisor
la va a proponer.

**Etiqueta canónica.** Este documento usa **una sola** etiqueta para el diseño
adoptado: **«opción 2 — machos individuales con sitio de enjambre asignado al nacer;
el enjambre es el agregado por sitio»**, y **«opción 3 — machos con vuelo simulado al
enjambre»** para la descartada. La etiqueta «opción 1» **no nombra nada** en esta
versión: era la numeración de un borrador previo y se elimina; si un revisor la
encuentra en un texto antiguo, corresponde a la opción 2 (la agregación simulada en el
marcador es el mecanismo de la opción 3, documentada en A18).

**Opción 3**: cada macho es un agente con vuelo **simulado** hasta el sitio de
enjambre, sobre una rejilla subcelular (≈10 m), con las reglas mínimas que reproducen
el enjambre en un ABM validado con datos de *coluzzii*: **atracción al marcador
visual + alineación al eje del atardecer + evitación de colisión por debajo de 2,5
longitudes corporales** (Cribellier et al. 2026), a velocidad **0,50 ± 0,00 m/s**
(rango 0,24–1,28) y con los macho-flight de Poda et al. 2024 **[M]**.

| Criterio | **Opción 2 — machos individuales con sitio de enjambre asignado al nacer; el enjambre es el agregado por sitio** (elegida) | **Opción 3 — machos con vuelo simulado al enjambre** (descartada) |
|---|---|---|
| Lo que la literatura mide | sitio como determinante (47,6 % de varianza), persistencia de 8 días, entrada en 46 ± 8 s, geometría del enjambre, velocidad de vuelo | las **reglas internas** del enjambre (marcador + atardecer + colisión) |
| Lo que el modelo necesita | el **recuento de machos disponibles por sitio y noche** | lo mismo |
| Granularidad de la posición | sitio (11–19 m de separación) | subcelular (σ 4–10 cm, centro a 0,67 m) |
| Coste | recuento por sitio y noche: una pasada sobre los machos | además de la pasada nocturna, una **simulación de vuelo por macho y por noche** sobre rejilla subcelular |
| Coste a escala de AOI | — | el mismo orden de población (10⁵–10⁶ machos/noche) con un coste por macho muy superior ⇒ rompe NFR-3 (≈2 min en Accra) |
| Refactor | ninguno | ninguno adicional: **la ventana nocturna es una fase del día en ambas opciones**, así que el argumento del "reloj diel" no discrimina entre ellas |
| Lo que aporta a la transmisión | la disponibilidad de cupos por sitio | **nada adicional**: la salida que el modelo necesita —la oferta de cupos por sitio y noche— es **idéntica**; la hembra responde al **sitio**, no a la estructura interna del enjambre (Charlwood 2023, sólo abstract), y asiste con tasa baja (10,33 %, cota inferior) |
| Riesgo de resultado | bajo: los parámetros proceden de medidas | alto: **no hay dato publicado** que parametrice la atracción ni la fidelidad ⇒ el resultado dependería de parámetros inventados |
| Intervenciones | *swarm killing* (matar los machos asignados a un marcador) y **efecto de SIT/IIT sobre los cupos por sitio** (machos estériles asignados a los mismos sitios, compitiendo por los mismos cupos; **no** se simula la competencia intra-enjambre entre machos estériles individuales) | ninguna: sin marcadores discretos que eliminar y **sin sitio al que asignar** los machos estériles ⇒ ni *swarm killing* ni el efecto de SIT/IIT sobre los cupos |

**Por qué la diferencia importa.** La granularidad del enjambre **no** es el mecanismo
que limita la transmisión: el mecanismo es la **oferta de cupos por sitio y noche**
(publicado: 7,2 % de los machos del enjambre) y la asistencia de las hembras (10,33 %,
cota inferior). Simular la dinámica interna del enjambre para obtener esa misma oferta
es pagar precisión geométrica donde la biología no discrimina. *Si* el modelo llegara a
necesitar el comportamiento intra-enjambre (por ejemplo, para cuantificar la
**segregación de enjambres entre especies**, χ² = 56,92 — Diabaté et al. 2009, hoy
documentado como mecanismo ausente), la opción 3 es el camino, y el diseño de la
opción 2 lo deja abierto: los machos ya son individuos con un sitio, y una capa de
vuelo se puede añadir **encima** sin tocar el resto.

#### 8.4 — Lo que el agregado por sitio conserva y lo que pierde

**Conserva**: la estructura espacial (dónde hay enjambre y cuánta oferta hay), la
dinámica temporal (los enjambres duran 19–39 min —media 28,3 min— al atardecer y se
dispersan a las
19:15), la fenología (lluvia = 0 parejas en el enjambre), la eficiencia por macho
parametrizable con el tamaño del enjambre (`p_mate_size_exponent`; constante por
defecto, §8.5), y la capacidad de representar *swarm killing* y el **efecto
de SIT/IIT sobre los cupos por sitio** (machos estériles asignados a los mismos
sitios, compitiendo por los mismos cupos; **no** se simula la competencia
intra-enjambre entre machos estériles individuales).

**Pierde**: (a) la estructura interna del enjambre, que no discrimina la transmisión;
(b) la heterogeneidad individual de la fidelidad al sitio (todos los machos de un
sitio: la asignación es estocástica con acumulación, §8.6); (c) el movimiento
*macho → sitio* como trayectoria, modelado como un cuanto discreto: el sitio se sortea entre los **alcanzables** con `male_move_capacity_m` (50 m/día), con peso de acumulación, o el macho queda suelto (§8.6).

#### 8.5 — Sobre la tasa de apareamiento (dos unidades distintas, `p_mate` las confundía)

Hasta ahora, `p_mate` era **una sola clave** para **dos cantidades que no son la misma**:

| Magnitud | Clave | Valor | Especie / lugar | Tier |
|---|---|---|---|---|
| Fracción de machos del enjambre que se aparea por noche | `p_mate_male_fraction` | **0,072 ± 0,0095** (7,2 %); "una pareja más por cada 14 machos extra" | *A. gambiae* s.s., Malí (Diabaté et al. 2011) | **[P]** |
| Pares por individuo de **ambos sexos** por enjambre | `p_mate_pairs_per_individual` | **0,084–0,25** (7/83 en el menor, 693/2 783 en el mayor) | *A. coluzzii*, Burkina Faso (Ouédraogo et al. 2025) | **[M]** |

La segunda cifra **cuenta ambos sexos** y es **una observación por enjambre**, no una
tasa por macho y noche: **no es directamente comparable** con la primera, y no puede
compararse "de un factor 4" entre las dos magnitudes. **Regla de conversión**,
si se usa como cota: la fracción de machos del enjambre que se aparea por noche es
`p_mate_pairs_per_individual / ρ_macho`, con `ρ_macho` la fracción de machos del
enjambre (con `ρ_macho` = 0,5 da **0,168–0,50**), y sólo como **cota superior**,
porque la fuente cuenta los pares del enjambre completo, no de una noche.

La decisión: el modelo usa `p_mate_male_fraction` = **0,072 ± 0,0095** como valor por
defecto —es la única de las dos cifras que está en la unidad que la fórmula necesita—
y `p_mate_pairs_per_individual` = **0,084–0,25** como cota de sensibilidad, con el
conflicto declarado en la configuración. El tope de **≤ 3 hembras por macho por noche** (Ekechukwu & Tripet
2019) es un límite de capacidad **citado, no medido en ese artículo** ⇒ **[M]/[NR]**;
y no llega a biting en la práctica, porque la eficiencia observada (0,08–0,25) está
muy por debajo de 3.

La forma de la curva tiene una discrepancia adicional: Diabaté encuentra eficiencia
por macho aproximadamente **constante**, Ouédraogo encuentra eficiencia **decreciente**
con el tamaño del enjambre (parejas ∝ tamaño, t = 9,16, p < 0,001, pero la pendiente
por macho cae). El modelo por defecto usa eficiencia constante y expone un exponente
`p_mate_size_exponent` para el caso decreciente; el valor por defecto (**0**) es el
más simple y el único que reproduce la afirmación de Diabaté de que "el éxito del macho
individual es similar se una a un enjambre grande o pequeño".

**Ley de `p_mate_size_exponent`.** El exponente **entra en la fórmula de cupos**
(§8.1) y no es una constante declarada y no usada:

```
cupos(s) = M_disp(s) × p_mate_male_fraction × (M(s) / male_swarm_reference_size)^(−p_mate_size_exponent)
```

con `male_swarm_reference_size` = **100 machos** (tamaño de enjambre de referencia)
**[EP]** y `p_mate_size_exponent` = **0** por defecto, banda **0–1** **[EP]**
(estimación propia, sin respaldo directo: Ouédraogo et al. 2025 reportan la tendencia
—eficiencia decreciente con el tamaño— pero no un exponente). Con
`p_mate_size_exponent` = 0 la eficiencia por macho es constante (Diabaté 2011); con 1
el número de pares deja de crecer con el tamaño del enjambre.

**Contraargumento registrado, no descartado.** Iacomelli et al. 2026 demuestra
interacción macho-macho experimental (sincronización de **velocidad**, no de
dirección) y afirma que "los modelos estándar requieren nuevas clases de modelo";
Shishika et al. 2014 reporta correlación direccional elevada en campo. Ningún
resultado publicado exige esa granularidad para el objetivo actual (transmisión
espacial), y la generalización laboratorio→campo sigue abierta. La razón para
descartar la opción 3 **no** es que estos resultados sean erróneos, sino que el
objetivo del plan no los necesita: §8.3.

**La banda que el modelo puede sostener.** Con la fórmula de §8.1 y los valores por
defecto (`p_mate_male_fraction` = 0,072 [P], `female_attendance_rate` = 0,1033 [P], 100
hembras y 100 machos), la fracción de hembras sin inseminar a las tres noches es
**85,24 %** [EP; banda derivada de la fórmula, con el desarrollo aritmético en §8.1].
La banda publicada de *coluzzii* (**22,3–52,8 %**) sale de otra unidad (pares por
individuo de ambos sexos por enjambre) y **no** es un criterio del modelo: queda como
cota de sensibilidad de `p_mate_pairs_per_individual`, nunca como banda de aceptación.

#### 8.6 — El resto de las decisiones de la capa macho

*   **Reintento sin caducidad**: si no se insemina, se reintenta cada noche; el esperma
    ya adquirido dura de por vida (monandría + tapón espermático).
*   **Alarma**: el motor emite, por celda y noche, el número de **hembras adultas sin
    inseminar por más de N noches**. Si crece, el campo de enjambres está roto.
*   **Asignación de sitio al nacer, y su consecuencia sobre `M(s)` y los cupos**:
    el sitio se **asigna al nacer** entre los **alcanzables** con `male_move_capacity_m` = 50 m/día, sorteado con peso de acumulación, o el macho queda suelto (§8.6). Un macho sin sitio
    alcanzable conserva `swarm_site_id = -1` y **no se reproduce**: no entra en
    `M(s)` de ningún sitio, no suma en `M_disp(s)` y, por tanto, **no genera cupos**.
    Consecuencia sobre los cupos: `cupos(s) = M_disp(s) × p_mate_male_fraction`
    refleja la oferta real de los machos **con sitio asignado**; si la densidad de
    marcadores es baja, aparecen machos sin sitio y el recuento de la alarma los hace
    visibles.
*   **Supervivencia de los machos, separada de la hembra**: `male_daily_survival` =
    **0,773 ± 0,094** (Epopa et al. 2017) **[M]** — hoy el YAML aplica 0,87 a ambos sexos
    y sobrestima los machos en ~12 %. Se añade la dependencia de azúcar como mecanismo
    [EP]: sin azúcar 1,94–2,99 días de vida, con azúcar 3,84–4,94 días (Gary et al.
    2009) **[P]**.
*   **Movimiento de los machos, con su propio presupuesto**: la dispersión macho medida
    es un **rango de 40 a 549 m** por experimento, en línea recta, con ventana de
    recaptura ≤ 7 días (Epopa et al. 2017) — **no es una tasa diaria** — y en
    *arabiensis* ningún macho superó los 100 m (Kaiser et al. 2021) **[P]**. El
    desplazamiento diario masculino es
    **muy inferior** a los 486–695 m/día de la hembra ⇒ el macho necesita su propio
    `male_move_capacity_m`, no el de la hembra. **Valor**: `male_move_capacity_m` =
    **50 m/día** por defecto, banda **40–100 m/día** **[EP]** (estimación propia, sin
    respaldo directo: se toma el orden de magnitud de la permanencia post-emergencia —
    < 60 % de los adultos se mueven > 50 m del sitio larvario, *arabiensis* [P]— y de
    la dispersión media de 85,7 m (Kaiser et al. 2021) [P]); el escenario puede
    sobrescribirlo.
*   **Velocidad de vuelo del macho**: 0,50 ± 0,00 m/s en enjambre (rango 0,24–1,28)
    (Poda et al. 2024) **[M]**; fuera del enjambre sólo hay un dato de arena,
    **0,20 ± 0,00 m/s** (vuelo de escape) (Poda et al. 2024), que **no** es velocidad de
    dispersión en campo ⇒ se declara **[EP] con banda**, no dato.
*   **Razón de sexes**: `male_ratio` por especie (0,5 por defecto, [EP]) — hoy el ODD la
    declara "neutral default"; la evidencia disponible apunta a sesgo **macho** en campo
    (Vielma et al. 2026).
*   **Ventana de apareamiento**: `swarm_start_min_after_sunset` = 5, `swarm_duration_min`
    = **28,3 min** (media del rango mensual 19–39 min; Bimbilé Somda et al. 2018
    **[P]**), compatible con los ≈**27 min** (18:05–18:45) de Ouédraogo et al. 2025
    **[M]**, y
    `rain_suppresses_swarming` (0 parejas por enjambre en el pico de lluvias).
*   **Preferencia de apareamiento antes/después de la primera comida**: el motor
    permite ambas ventanas (noches 2 y 3), porque *arabiensis* aparea antes (98,47 % de
    las hembras que copulan aún no habían comido) y *gambiae* s.s. se reparte 49/51.
*   **Aislamiento de enjambres entre especies**: publicado (χ² = 56,92, segregación por
    marcador; Diabaté et al. 2009) pero medido en Malí entre formas M y S ⇒ el modelo
    actual no lo captura y se documenta como mecanismo ausente.
*   **Intervenciones**: con la opción 2 (machos individuales con sitio de enjambre asignado
    al nacer; el enjambre es el agregado por sitio) el modelo **sí** puede representar el *swarm
    killing* (que requiere marcadores discretos que se pueden eliminar: ↓insemination y
    ↓densidad de hembras, p < 0,001; Sawadogo et al. 2022) y el **efecto de SIT/IIT
    sobre los cupos por sitio** (machos estériles asignados a los mismos sitios,
    compitiendo por los mismos cupos; el lado femenino requiere la capa de individuos
    humanos del paso 2). **No** se simula la competencia *intra-enjambre* entre machos
    estériles individuales: la granularidad del enjambre queda excluida (§8.3, A18).

### 9. Capa acuática: `PatchState` → registro por celda (decisión D4 = b)

`PatchState` (en `wire.hpp`) pasa a ser un registro **por celda para todas las células**
del AOI, y "patch" deja de ser un contenedor de información para ser un **filtro de
elegibilidad**:

```
CellState (antes PatchState)
  cell_id        int32    // antes patch_id (sintético, asignaba el coordinador)
  row, col       int32
  eligible       bool     // antes "activated": gpkg ∪ potencial ≥ umbral, ∧ salinidad
  rain_d         float
  temp_d         float
  salinity_ppt   float
  habitat_avail  float    // S(i,t)
  habitat_dry_days int
  k_habitat      float
```

**Fuente del potencial y de la salinidad por celda** (decisión):

*   El **potencial** por celda **no** viene del gpkg. El gpkg de *features* sólo cubre
    las celdas candidatas (99 con datos sobre 3.416 en el AOI de Accra) y su
    `habitat_potential` es un atributo de punto. La fuente autoritativa es el
    **recálculo por celda** a partir de los planos estáticos del contrato v3.0
    (`jrc_persistent`, `lc_built`, `lc_wetland`, `lc_open_plus_water`, `lc_crop`) con la
    regla del motor `habitat_potential()`
    (`mal-core/src/mal_core/abm/include/mal_abm_fast/habitat_availability.hpp:76`), que
    es el espejo C++ de `mal_core.habitat.potential.static_potential`
    (`mal-core/src/mal_core/habitat/potential.py:50`); el potencial total es la suma de
    los seis tipos de hábitat recortada a [0, 1]
    (`mal_core.habitat.potential.total_potential`, mismo fichero, `:82`). El valor es un
    **índice**, no un conteo de charcas medido: `[EP]` — "estimación propia, sin
    respaldo directo" (es una recripción de los planos del contrato v3.0, no una
    medición). `CellState` incorpora por tanto un campo `potential` (índice estático
    por celda, adimensional, [0, 1]).
*   La **salinidad** sí es un campo por celda y por día: la banda `salinity_ppt` del NC
    de entorno, que difunde el NC mensual de SMAP a cada día
    (`mal-core/src/mal_core/ingest/daily_nc.py:399`, escritura en `:462`), leída por
    celda con `ClimateEngine::salinity_at(row, col)`
    (`mal-core/src/mal_core/abm/src/climate.cpp:149`). Sin datos, el valor es
    `aquatic_stages.salinity_missing_psu = 0,0 psu` (agua dulce)
    (`mal-core/config/model_constants.yaml:274`) `[M]`.
*   **Efecto sobre la regla `k_habitat == 0 ⇒ p = 0`**: al materializarse el registro
    para *todas* las celdas, la regla deja de ser el caso raro (celda sin parche) y
    pasa a ser la respuesta mayoritaria: toda celda con potencial total 0, o sin
    disponibilidad, tiene `k_habitat == 0` y por tanto **todas sus L1–L4 mueren ese
    día** (contrato de estado 4.0, sin excepción ni valor por defecto). Es coherente
    con que el potencial sea estático (no cae a 0 dentro de una corrida) y con la
    semántica de `habitat_availability.hpp`; pero exige que los planos estáticos y la
    banda `salinity_ppt` cubran la **rejilla completa** del AOI, no sólo las celdas
    candidatas del gpkg.
*   **Trabajo de producción que falta** (anotado para el §15): (a) publicar/verificar
    los planos estáticos y la banda `salinity_ppt` para la rejilla completa del AOI
    (hoy la oferta de hábitat se produce por *features* del gpkg); (b) un punto de
    entrada Python de potencial a nivel de rejilla —`static_potential` es hoy una
    función por columna de features y `total_potential` no tiene consumidor de
    rejilla—; (c) el mismo plano por celda es el que necesitan los scorers del §10.

*   **Artefacto del plano de hábitat por celda — `habitat_cell_planes.json`.** El plano
    que necesitan los scorers **no existe hoy** (hoy sólo se publica el sidecar). Queda
    fijado así:
    *   **Productor**: el **Paso 7**, que es el paso que materializa el registro por
        celda (`CellState` para todas las celdas).
    *   **Esquema**: JSON con una entrada por `cell_id`; cada entrada declara el
        **potencial total** (índice adimensional en [0, 1], §9) y la **elegibilidad**
        (booleano; el filtro que antes era `activated`).
    *   **Dónde se escribe**: en el **directorio de la corrida**, junto a los demás
        artefactos de salida (`<run>/habitat_cell_planes.json`).
    *   **Cómo lo localizan los scorers**: por **ruta relativa al directorio de la
        corrida** (`<run>/habitat_cell_planes.json`), que es donde `D1_habitat_occupancy`
        y `D8_coupling` resuelven el denominador y la correlación (§10).

Consecuencias:

*   El cálculo diario **ya es por celda** (`coordinator.cpp`: `z_`, `feats_`,
    `dry_days_`, `K_cell_` son arrays de H×W). Lo que cambia es que se **materializa**
    para toda la rejilla, no sólo para las celdas candidatas. Coste: 3 416 celdas ×
    ~40 B ≈ 140 kB por día en el AOI de Accra (61×56).
*   **La doble fuente de potencial desaparece**: `oviposition_seeking.cpp:49-54` usa
    el potencial del gpkg y hace *fallback* a `ps.habitat_avail`. Con el registro por
    celda hay **una sola fuente**: el potencial estático per-cell.
*   **La ruta de error `aquatic_cohort_bank.cpp:308` ("no PatchState for today")
    desaparece por construcción**: toda celda tiene registro ⇒ `k_habitat == 0` pasa a
    ser la respuesta definida (muerte de L1–L4 ese día, contrato v4.0).
*   **La clave de la cohorte pasa a `(cell_id, mother_id)`** (`CohortKey` en
    `aquatic_cohort_bank.hpp`): se elige la **alternativa (a)** del par
    madre-por-celda / madre-por-cohorte. `mother_id` identifica a la hembra que
    oviposita (individuo, no celda), de modo que dos hembras distintas que ovipositan
    en la misma celda dan **cohortes distintas**, cada una con sus propias coordenadas
    de madre; y una hembra que usa 2–4 criaderos produce hasta cuatro cohortes con
    coordenadas distintas. La agregación de la Beverton-Holt sigue siendo **por celda**
    (antes de aplicar `p = S0·K/(K+α·N)` se suman los recuentos de todas las cohortes
    de la celda): la competencia no se desagrega y N5 sobrevive (los agregados por celda
    no se disuelven; lo que se individúa es el origen de los huevos). La alternativa
    (b) —bajar G7/CUJ 6 a "el adulto emerge en la celda" y llevar la posición de la
    madre como distribución en el artefacto individual— **se rechaza**: perdería la
    individualización del adulto justo en el punto en que nace. Coste: el número de
    cohortes por celda pasa a ser mayor que 1 (hasta una cohorte por hembra y por
    noche), lo que
    multiplica la memoria del banco acuático; el paso 7 debe medir ese coste en el
    AOI de Accra.
*   **La posición de la madre se AÑADE al cohorte de huevos** (`mother_x`, `mother_y`),
    **por cohorte `(celda, madre)`, no por celda**: es lo que evita que las oviposiciones
    colapsen en una única coordenada por celda.
    Esto **no existe hoy**: `AquaticCohort` es
    `{patch_id, stage, instar, development, count, mean_age_days}` y el adulto emerge
    **snapado al centro de la celda** (`mosquito_submodel.cpp:530-535`). Con el campo
    añadido, el adulto emerge **donde puso los huevos la madre** — que es el
    el comportamiento correcto y lo que hace que la composición por celda de los adultos
    emergentes signifique algo. La posición de la madre es la de **su** cohorte: con la
    clave `(celda, madre)` cada oviposición conserva su coordenada.
*   **La oviposición pasa a ser multi-sitio y con elección por estado del criadero**:
    *   **49,2 %** de las hembras usan **2–4 criaderos** (Onen et al. 2026) **[P]** ⇒ la
        hembra no es "monócrica de sitio"; el modelo debe permitir ovipositar en más
        de un sitio dentro de la misma noche y en noches distintas.
    *   La elección depende del **estado y la densidad de la cohorte de larvas
        conspecíficas en la celda destino**, con signo **positivo para larvas
        tempranas y negativo para larvas tardías**, por vía olfativa (Mwingira et al.
        2020, ***A. coluzzii***) **[M]**. Es el único mecanismo ovipositorio medido en
        *coluzzii*, y es un mecanismo de **señal en el sitio**, no de distancia.
    *   La jerarquía de volátiles de pasto (Poaceae > *Typha* > *Cyperus*) modula la
        elección (Asmare et al. 2017, *coluzzii* y *arabiensis*) **[M]** ⇒ sesgo por
        **tipo de habitat**, que es como se implementa.
    *   La **preferencia olfativa por el habitat natal** (31,6–37,5 % de los huevos en
        agua natal; nula en agua de laboratorio, atenuada en semi-campo) (Kemibala et
        al. 2026, *A. gambiae* s.l.) **[P]** es el único resquicio de "filopatria" y se
        implementa como sesgo del kernel por tipo de habitat, **nunca** como distancia
        a una coordenada.
    *   La **persistencia del criadero** importa: un estanque fresco sostiene ~2× las
        larvas (50 vs 24 vs 20) (Eneh et al. 2019) **[P]**.
*   **`update_patch_id` se retira** (`mosquito_submodel.cpp:965-1004`) y con él
    `dispersal.snap_radius_m` (500 m): sin afiliación de parche en el lado de adultos no
    hay nada que "snap-ear".
*   El sidecar acuático (`write_diagnostics`) escribe `cell_id` en lugar de `patch_id`.

### 10. Contratos y versionado

**Un solo bump.** El estado y el entorno se versionan por separado: en C++,
`CONTRACT_VERSION()` lee `contracts.cogs_state`
(`mal-core/src/mal_core/abm/include/mal_abm_fast/wire.hpp:107`) y el NC de entorno lleva
su propia clave `contracts.env_nc` (`mal-core/config/model_constants.yaml:9`). El plan
publica **dos** versiones de estado (4.1 y 5.0): eso no se publica. Hay **un** número
nuevo de contrato de estado, y **4.1 no existe**.

| Contrato | Hoy | Plan | Motivo |
|---|---|---|---|
| `contracts.cogs_state` | 4.0 | **5.0** (MAJOR) | una sola banda: se retira `adult_patch_count` |
| `contracts.env_nc` (NC de entorno) | 3.0 | **3.0** (sin cambio) | mismas bandas, mismos planos: el fichero NC no cambia |
| Contrato de hábitat (registro por celda) | 3.0 | **4.0** | el registro por celda pasa a ser parte del contrato (clave nueva `contracts.habitat`) |
| Sidecar JSON acuático | `patch_id` | `cell_id` | renombrado de vocabulario |

*   **5.0 (MAJOR), contrato de estado**: se publica **una sola banda**,
    `adult_cell_count` (recuento bruto de adultos por celda, en su posición actual, sin
    normalizar por capacidad y sin recortar a [0, 1]); el sidecar lo declara
    (`band_names: ["adult_cell_count"]`) y `adult_patch_count` se retira.
*   **4.0, contrato de hábitat**: el paso de "conjunto de parches candidatos" a
    "registro por celda para todas las celdas" es un cambio de **semántica**, no de
    formato, y por eso es un bump mayor de ese contrato. Se propone la clave nueva
    `contracts.habitat: "4.0"` en `model_constants.yaml` (el §12 la declara). El **NC de
    entorno no cambia de versión** porque su formato —bandas y
    planos— es idéntico: lo que cambia es la lectura que hace el motor de esas bandas,
    y esa lectura se versiona con el contrato de hábitat.
*   **Los lectores deben rechazar una versión desconocida**: un consumidor que ve `5.0`
    con dos bandas, o un sidecar cuyo `band_names` no coincida con `STATE_BAND_NAMES`,
    debe fallar en vez de leer mal. No se publica un 4.1: no hay estado intermedio que
    leer.

**La superficie real del cambio de bandas** (qué hay que tocar, con ruta):

*   `mal-core/src/mal_core/abm/include/mal_abm_fast/wire.hpp:217` —
    `STATE_BAND_NAMES[2] = {"adult_patch_count", "adult_cell_count"}`: pasa a un solo
    nombre.
*   `mal-core/src/mal_core/abm/include/mal_abm_fast/output_contract.hpp:42-77` —
    `StateCogMetadata::band_names` (`std::array<std::string, 2>`) y `nodata`: pasan a
    una sola banda.
*   `docs/concepts/contracts.yaml` — claves `cogs_state` (lista `bands`) y
    `state_sidecar` (clave `band_names` y lista de claves del sidecar).
*   `mal-core/src/mal_core/training/dataset.py:20` — `VECTOR_CHANNELS = 2`.
*   `mal-core/src/mal_core/prediction/state_loader.py:83` — `src.read()` lee todas las
    bandas: pasa a leer una.
*   `mal-core/src/mal_core/training/trainer.py:63-64` — **sin cambio**: los canales los
    fija el dato (`in_channels = sample_x.shape[0]`, `out_channels = sample_y.shape[0]`),
    no la firma del modelo.
*   `mal-core/src/mal_core/training/wrapper.py:52-66` — al cargar un checkpoint, los
    canales salen de los metadatos o de los pesos; sus *fallbacks* (`:62` y `:66`, 6 y 2)
    dejan de ser ciertos y se sustituyen por los valores reales.
*   `mal-core/src/mal_core/training/model.py:45` — `in_channels=6, out_channels=2`: son
    **valores por defecto que el entrenamiento nunca usa** (el trainer los sobreescribe
    siempre); sólo hay que ajustarlos para que no mientan.
*   el manifiesto del modelo entrenado y los goldens del COG de estado: se regeneran.

**`VECTOR_CHANNELS`**: la constante vale 2 (`training/dataset.py:20`) pero **el paquete
no la consume** — los canales se leen del raster (`dataset.py:115` y `:227` leen
`src.read()` y apilan lo que haya). Lo que sí la consume es
`tools/gen_concepts_values.py:1075`, que la emite como macro `training.vector_channels`
en `docs/concepts/generated/macros.tex`: pasarla a 1 cambia un artefacto generado con
`--check` en el build, y hay que regenerarlo (`uv run python tools/gen_concepts_values.py`),
nunca editarlo a mano.

**Modelo**: los canales **no los fija la firma de `UNet`**, los fija el dato.
`dataset.py` apila, para la entrada, las bandas de estado + las de transmisión
(`TRANSMISSION_CHANNELS = 4`, `dataset.py:21`) + las de entorno (`ENV_CHANNELS = 4`,
`dataset.py:22`) — `dataset.py:299-300` y `:308` —, y para el objetivo, las de
estado + las de transmisión del día siguiente. De ahí que **con dos bandas de estado
la entrada tenga 10 canales y la salida 6**, y no 6 y 2: `trainer.py:63-64` los toma
de las formas del dato (`sample_x.shape[0]`, `sample_y.shape[0]`) y construye el
`UNet` con ellos, de modo que los valores por defecto de `model.py:45` (6 y 2) nunca
se usan al entrenar. **Con una sola banda de estado la entrada pasa a 9 y la salida a
5.** Al cargar un checkpoint, `wrapper.py:52-66` deduce los canales de los metadatos o
de los pesos, con *fallbacks* 6 y 2 (`wrapper.py:62` y `:66`) que hay que corregir.
El modelo se reentrena desde cero: los checkpoints entrenados con las bandas normalizadas de
≤ 3.0 **no se reutilizan** sin reentrenar.

**Los dos scorers que leen la banda 2 — decisión: se adaptan, no se retiran.**
`D1_habitat_occupancy` (`mal-core/src/mal_core/scoring/scorers/d1_habitat_occupancy.py:68-69`)
lee `ds.read(2)` como **máscara de hábitat** (peso 1,0 en `COMPOSITE_WEIGHTS`,
`mal-core/src/mal_core/scoring/registry.py:69`) y `D8_coupling`
(`mal-core/src/mal_core/scoring/scorers/d8_coupling.py:49-50`) lee `ds.read(2)` para
correlacionar (peso 2,0). Con una sola banda, la banda 2 no existe:

*   **D1 se adapta**: el numerador —celdas con adultos— sale de la banda única
    (`adult_cell_count > 0`); el **denominador** —las celdas de hábitat— deja de salir
    del COG de estado y sale del **plano de hábitat por celda** que el §9 garantiza para
    todas las celdas (potencial total y elegibilidad). Se conservan el objetivo
    "0,20–0,70 de celdas de hábitat ocupadas" y el peso 1,0; la etiqueta del scorer pasa
    a "celdas de hábitat ocupadas por adultos".
*   **D8 se adapta**: correlaciona `adult_cell_count` con ese mismo plano de hábitat por
    celda; conserva su peso 2,0 y su sentido (acoplamiento entre adultos y hábitat).
*   `COMPOSITE_WEIGHTS` **no se reescribe**: los pesos 1,0 (D1) y 2,0 (D8) siguen
    siendo los de esos scorers (el compuesto es una media geométrica y ya resuelve por
    sí mismo el número variable de dimensiones). `GATES` **no cambia**: D1 y D8 no son
    gates (`registry.py:75`).
*   **Requisito de producción**: los dos scorers necesitan el plano de hábitat por celda
    en el directorio de corrida (o su ruta vía manifiesto). Lo publica el mismo paso que
    materializa el registro por celda (§9): lo publica el **Paso 7** (§15).

**Conflicto de semántica: manda el contrato.** Los dos scorers documentan la banda 2
como "hábitat" / "presión de búsqueda de hospedero", mientras que el contrato la declara
`adult_cell_count` (recuento bruto de adultos por celda; `docs/concepts/contracts.yaml:77-78`).
La autoridad es el contrato (`STATE_BAND_NAMES`, `StateCogMetadata::band_names`); lo que
se corrige es la documentación de los scorers. En consecuencia, las alternativas A8
("banda 1 = afiliación reproductiva") y A9 ("banda 1 = presión de búsqueda de
hospedero") quedan **rechazadas**: describen una semántica de banda que el contrato
publicado no tiene.

**Ficheros de consumo que hay que tocar** (contrato de estado 5.0):

*   `mal-core/src/mal_core/scoring/scorers/d1_habitat_occupancy.py`
*   `mal-core/src/mal_core/scoring/scorers/d8_coupling.py`
*   `mal-core/src/mal_core/scoring/registry.py`
*   `mal-core/src/mal_core/training/dataset.py`
*   `mal-core/src/mal_core/training/model.py`
*   `mal-core/src/mal_core/prediction/state_loader.py`
*   `docs/concepts/contracts.yaml`

### 11. Observabilidad: eventos e individuos

**Vía de infección vector→humano — una sola** (texto canónico; el §2 y N11 lo citan y
lo copian tal cual):

> La infección vector→humano ocurre **únicamente en el evento de picadura**, sobre la
> persona identificada: una picadura infecciosa infecta, **como máximo, a esa persona, y
> a ninguna otra**. La presión de infección por celda (`λ_H`) queda **retirada** como
> autoridad; `advance_day` deja de aplicar probabilidades por celda y pasa a **avanzar
> sólo temporizadores** (edad, estado gonotrófico, timers de oviposición).

*   **Lo que se retira.** `TransmissionModel::advance_human_transmission`
    (`mal-core/src/mal_core/abm/src/transmission.cpp:446`) calcula hoy
    `infectious_pressure_[celda]` a partir del ledger y luego
    `λ_H[celda] = 1 − exp(−β_vh · I_bites/pop)`; ese `λ_H` lo aplica
    `HumanCompartmentGrid::advance_day`
    (`mal-core/src/mal_core/abm/src/human_state.cpp:232`, aplicación en `:241-266`) a
    **toda** la población susceptible de la celda (`binomial(s_int, λ)`). Ese par
    —agregado por celda— se elimina: mantenerlo junto a la vía por picadura contaría
    dos veces. Nota de cita: el FOI **no** está en `transmission.cpp:65-66` — esas
    líneas son la inicialización de `lambda_h_` e `infectious_pressure_` (`init`), no
    el cálculo del FOI.
*   **Lo que lo sustituye.** En el evento de picadura, sobre la persona identificada
    `h`: `p_infect(h) = β_vh × su_h` (`su_h` = susceptibilidad de esa persona); la
    infección se aplica a `h` y a nadie más. `λ_H` e `infectious_pressure_` dejan de
    ser entradas del lado humano; quedan, si acaso, como **estadística de readout**
    (cuántas comidas infecciosas hubo por celda), nunca como mecanismo.
*   **El lado humano→vector.** La exposición del vector ya es por evento de picadura
    (`mal-core/src/mal_core/abm/src/mosquito_submodel.cpp`, función
    `record_female_feed`, líneas 75-125): `p_expose = β_hv × prev`,
    donde `prev` es hoy la prevalencia de la **celda**
    (`human_grid->prev_at(host_row, host_col)`). Con la individualización, `prev` pasa
    a ser el estado de la **persona picada** (`prev_h`): no queda ninguna magnitud de
    celda actuando como autoridad en ninguna de las dos direcciones.
*   **`advance_day` (lado humano)** deja de aplicar probabilidades y pasa a **avanzar
    sólo temporizadores**: los de la persona —edad, estado individual, temporizadores
    de inmunidad y calendario de movimiento—; el bloque canónico de arriba da la
    enumeración abreviada. La transición `I → R` la fija el temporizador
    de duración de la infección, no una bernoulli por celda.
*   **El agregado por celda sobrevive** como *contador*, no como autoridad. Las
    estructuras del ledger están en
    `mal-core/src/mal_core/abm/include/mal_abm_fast/bite_ledger.hpp` —**no** en
    `wire.hpp`—: `BiteEventAggregate` con clave `row`/`col`/`HostType` y contadores, y
    `BiteLedger` con `today()`. El ledger sigue contando comidas infecciosas por celda
    y por tipo de hospedero, y todos sus consumidores leen `today()`: los eventos
    individuales se apilan encima sin romper el contrato del ledger. Individualizar los
    eventos **no** individualiza el contador.

Tres artefactos nuevos, más la evolución de los existentes:

```
runs/<run>/
  <run>_dayNNN.tif          COG de estado (1 banda en 5.0)
  <run>_dayNNN.json         sidecar (deprecated_bands, stats por individuo)
  <run>_aquatic.json        sidecar acuático (cell_id, cohortes, madre)
  <run>_bites.jsonl         ◀ NUEVO: ledger de eventos de picadura
  <run>_mating.jsonl       ◀ NUEVO: ledger de apareamiento (sitio, cupos, parejas)
  <run>_agents.parquet      ◀ NUEVO: estado por mosquito y por día
  <run>_humans.parquet      ◀ NUEVO: estado por persona (muestreado al 1 % con pesos)
```

**Ledger de picaduras** — de agregado a eventos:

```
BiteEvent
  day, phase, tick
  mosquito_uid, species
  host_id            (persona o presa; null para fauna)
  host_type
  volume_ul
  probing_ok
  transmission_applied   (β_vh × su_h en el evento; β_hv × prev_h al vector)
  cell_id              (derivado, para agregados)
```

**Granularidad, consumidores y cota** del ledger de picaduras: una línea JSONL por
evento de picadura; **consumidores**: el diagnóstico de picaduras (CUJ 1, CUJ 5) y el
COG de transmisión, que sigue leyendo los agregados de `today()`; **cota de tamaño**:
escala con el número de picaduras, no con el número de personas.

`BiteLedger` **se conserva** como capa de agregados (el COG de transmisión y la lógica de
ITN/IRS lo consumen, leyendo `today()`) y **se añade** encima la capa de eventos. Las
estructuras viven en `mal-core/src/mal_core/abm/include/mal_abm_fast/bite_ledger.hpp`
(`BiteEventAggregate`, con clave `row`/`col`/`HostType`; `BiteLedger`, con `today()`),
**no** en `wire.hpp`. Así el contrato de transmisión 4.0 no se rompe: el agregado por
celda sobrevive como contador de lectura, y la autoridad de la infección es el evento
individual (§11).

**Artefacto individual por mosquito — `_agents.parquet`**: una fila **por mosquito y por
día** (no por tick: el tick no es una unidad de publicación reproducible y multiplicaría
el tamaño por el número de sub-pasos). Columnas: `uid`, especie, `sex`, `pos_x`,
`pos_y`, `cell_id`, estado gonotrófico, `blood_volume_ul`, `ovarian_stage`,
`gonotrophic_cycles`, `inseminated`, `vector_state`, `age_days` y —**para los machos**—
`swarm_site_id` y `nights_uninseminated`. **Consumidores**: el diagnóstico de la alarma
de enjambre (§8.6) y la reconstrucción de cadenas (§11, CUJ 5). **Cota de tamaño**: el
fichero escala con el número de mosquitos × días; a escala de país forma parte de la
cota de **decenas de GB** del conjunto de artefactos nuevos (§11, «Riesgos»).

**Artefacto individual por persona — `_humans.parquet`**: una fila **por persona y por
día**, **muestreada al 1 % con pesos** (`weight` = 1 / probabilidad de inclusión): la
población humana es la que domina el tamaño (40 B por persona en memoria, §2).
Columnas: `human_id`, `cell_id`, `x`, `y`, `state`, `timer`, `susceptible`.
**Consumidores**: las estadísticas derivadas (`compute_stats()`) y el control de la
exposición individual. El `human_id` sigue siendo el identificador determinista y
estable, de modo que el muestreo **no** rompe el contrato de observación (§2).

**Ledger de apareamiento** — eventos de la capa macho, en su **propio** fichero
(`<run>_mating.jsonl`):

```
MatingEvent
  day, swarm_site_id
  males_present            (M(s) esa noche)
  pairs                    (parejas sorteadas)
  males_inseminated
  females_uninseminated    (y su nº de noches sin inseminar)
  cap_source               (sitio del campo | enjambre local)
```

Es el instrumento con el que se lee la **alarma** de §8.6 (hembras adultas sin
inseminar por más de N noches) y con el que se evalúa una intervención de *swarm
killing*. **Granularidad**: una línea JSONL por **sitio y noche**. **Consumidores**: la
alarma de enjambre (§8.6) y los escenarios E13–E15 y E17. **Cota de tamaño**: escala
con el número de sitios × noches, no con el número de personas.

**Cota de tamaño del conjunto de artefactos nuevos.** A escala de país
(50–100 M de personas, §2) el conjunto `_humans.parquet` + `_agents.parquet` +
`_mating.jsonl` es del orden de **decenas de GB** [EP] (cota declarada, no medición).
Por eso `_humans.parquet` va **muestreado al 1 % con pesos** y por eso el Nivel 5
compara ese artefacto **por contenido**, no byte a byte.

### 12. Configuración: qué cambia en `model_constants.yaml`

El esquema (`version: 2`) sube a `version: 3` porque cambian claves congeladas. Las
claves se organizan **por especie** (`species.<fila>`), según la decisión P, y se
retiran las que la evidencia no sostiene.

**Se retiran (existen hoy, en todas las filas de especie y en los bloques globales):**

| Clave | Motivo |
|---|---|
| `species.<fila>.host_seeking_radius_m` (1500) | "olor de asentamiento" sin respaldo |
| `species.<fila>.host_seeking_scale_m` (300 / 120) | decaimiento exponencial incompatible con la pluma intermitente |
| `host_seeking.detect_range_m` (2000) | radio **global** por celda: **sobrescribe** el radio por especie (`host_seeking.cpp:104-114`, `model_constants.yaml:253-258`); lo sustituye `species.<fila>.co2_activation_radius_m` = 100 m (§4) |
| `host_seeking.approach_step_m` (50) | paso de aproximación **por celda**: lo sustituye la cascada por persona (§4) |
| `oviposition.detect_range_m` (2000) | detección de criadero **por celda**: lo sustituye la elección de sitio de oviposición (§9) |
| `oviposition.step_m` (50) | paso de aproximación **por celda** hacia el criadero: mismo mecanismo por celda que la cascada sustituye |
| `dispersal.host_flight_step_m` (500) | contradice la capacidad medida; lo sustituye velocidad × tiempo |
| `dispersal.snap_radius_m` (500) | sin afiliación de parche en el lado de adultos |
| `oviposition.scale_m` (50) | mismo problema de campo continuo — **se retira en el Paso 9**, que es el paso que reescribe el núcleo de oviposición (el Paso 7 sólo retira `dispersal.snap_radius_m`) |
| `gonotrophic.feeding_success_rate` (0,825) | cargado pero nunca consultado |
| `dispersal.adult_prob_day` (0,05) | la routine `MosquitoSubmodel::adult_dispersal` (`mosquito_submodel.cpp:1010`, gaussiana diaria **sin filtro de sexo**) se **retira para ambos sexos**: el único desplazamiento estocástico pasa a ser el paseo de exploración de la cascada, acotado por `daily_move_capacity_m` (§4) |
| `dispersal.adult_sigma_m` (450) | ídem: con la routine fuera desaparecen la varianza gaussiana (σ = 450 m) y su tope duro; la banda medida 486–695 m/día pasa a ser `daily_move_capacity_m` (590 m) |
| `dispersal.adult_max_m` (2000) | ídem: desaparece el tope duro de 2 000 m |

**Los cuatro radios y pasos por celda: cuál manda.** Además del radio por especie
`species.<fila>.host_seeking_radius_m` (1500 m, ya listado arriba), el plan retira
**cuatro** claves que codifican el mismo mecanismo por celda: los dos radios
(`host_seeking.detect_range_m` = 2 000 m y `oviposition.detect_range_m` = 2 000 m) y los
dos pasos (`host_seeking.approach_step_m` = 50 m y `oviposition.step_m` = 50 m). Con ellas
retiradas, el radio que manda en el plan es
**`species.<fila>.co2_activation_radius_m` = 100 m** [P]
(§4), y los tramos siguientes son los de la cascada: olfativa 30–70 m, visual
0,25–0,72 m, terminal 0,10–0,20 m. No queda ningún radio global por celda: el
`detect_range_m` global de 2 000 m era el que hoy sobrescribía el radio por especie.

**El CLI acompañante desaparece**: `--disperse-prob`, `--disperse-sigma-m` y
`--disperse-max-m` (`main.cpp`) se retiran con las tres claves de `dispersal.*`; ningún
escenario puede volver a activarlas.

**Cambian:** `species.coluzzii.activity_weights` → `[0.00, 0.255, 0.480, 0.265]`
(re-derivada con las duraciones por defecto 12/4/6/2, mapeo explícito más abajo); `species.coluzzii.salinity_hi_tol_ppt` → 10,5 (con la clave renombrada a la unidad real). `host_seeking.detect_range_m` (2000) **se retira**, no se renombra: el radio que lo sustituye es `species.<fila>.co2_activation_radius_m` = 100 m [P] (§4), y el resto de las claves de radio y de paso por celda se retiran con él (ver la tabla de retiradas).

**Se crean, por especie** (`species.<fila>`; cada clave vive en las **cinco**
superficies descritas más abajo). Inventario completo: valor, unidad, tier y
referencia.

| Clave | Valor | Unidad | Tier | Referencia / nota |
|---|---|---|---|---|
| `co2_activation_radius_m` | 100 | m | [P] | activación por CO₂ |
| `olfactory_radius_m` | 30–70 | m | [P] | rastreo de pluma |
| `visual_radius_m` | 0,25–0,72 | m | [P] | banda de aproximación visual (integrador fino) |
| `terminal_radius_m` | 0,10–0,20 | m | [P] | **radio terminal** (contacto); banda única, no 0,10–0,15 |
| `flight_speed_ms` | 0,225–0,45 | m/s | [P] | *coluzzii* en busca |
| `exploration_range_m` | 100 (banda 100–200) | m | [EP] | radio del **disco de exploración** centrado en la posición actual (no es cota de desplazamiento); ≥ `co2_activation_radius_m` (100 m) para que el tramo ACTIVACIÓN sea alcanzable; banda de sensibilidad [EP] |
| `exploration_step_m` | 50 | m | [EP] | longitud nominal del paso del paseo de exploración |
| `exploration_step_correlation` | 0,5 | [adimensional] | [EP] | correlación paso–paso (paseo correlacionado) |
| `casting_probability` | 0,10 | [1/paso de rastreo] | [EP] | probabilidad de perder la pluma y pasar a *casting* |
| `casting_angle_deg` | 90 ± 30 | ° | [EP] | transversalidad del *casting* respecto al viento |
| `plume_memory_s` | 0,5–0,9 | s | [P] | segmentos de *cast* (Cummins 2012); 0,3 s es *Aedes* |
| `anemotaxis_rule` | contra el viento (*upwind*), desviación ± 30° | — | [EP] | sin medición publicada del ángulo de orientación |
| `wind_reference` | `u100`/`v100` (100 m AGL, ERA5 6-horario) | — | [M] | `wind_field.cpp:47-56`, `wind_field.hpp:22-26`; único nivel disponible |
| `wind_block_threshold_ms` | = `flight_speed_ms` | m/s | [EP] | umbral de bloqueo del avance contra el viento |
| `daily_move_capacity_m` | 590 | m | [P] | **longitud máxima de trayectoria diaria (MDTpD)**, no desplazamiento neto; media de los MDTpD medidos 486–695 m/día (`papers/anopheles-dynamics/wickramasooriya-2026-coluzzii-mrr-saotome-principe.md:23`) |
| `directed_flight_budget_h` | 0,36–0,73 | h | [EP] | **derivado**: 590 m ÷ `flight_speed_ms` (21,9–43,7 min); **consumible por día**, no por fase; no es "~1 h/día" |
| `blood_meal_target_ul` | 0,5 | µL | [EP] | objetivo de una comida completa |
| `first_cycle_target_ul` | 0,8 | µL | [EP] | > `blood_meal_target_ul`: hacen falta dos comidas |
| `blood_meal_size_ul` | 0,3 | µL | [EP] | media del volumen tomado por comida |
| `meal_size_min_ul` | 0,1 | µL | [EP] | volumen mínimo de una comida válida |
| `blood_meal_refractory_days` | 0,5 | días | [EP] | ventana postprandial tras alcanzar el objetivo |
| `probing_success_rate` | 0,465–0,99 | [fracción] | [EP] | por especie; sustituye a `feeding_success_rate` (0,825), que el motor cargaba sin consultar |
| `eggs_per_ul` | 223 | [huevos/µL] | [EP] | calibrado para que 0,5 µL dé ≈112 huevos (puesta medida 111,67 ± 5,36) **[P]** |
| `arrested_daily_survival` | 0,986 | [1/día] | [EP] | derivado de los hasta 212 días de estivación **[P]**: 212·ln(0,986) ⇒ sⁿ = 0,05 |
| `gonotrophic_arrest_prob_dry` | 19,23–34,85 / 40,09–48,98 / 68,12–68,64 % | [fracción] | [P] | *coluzzii* / *arabiensis* / *gambiae* s.s. |
| `male_ratio` | 0,5 | [fracción] | [EP] | hoy el ODD declara "neutral default"; la evidencia apunta a sesgo macho (Vielma et al. 2026) |
| `male_daily_survival` | 0,773 ± 0,094 | [1/día] | [M] | Epopa et al. 2017; separado de la hembra (0,87) |
| `meals_per_cycle_mean` | — | [comidas/ciclo] | [EP] | se mantiene con el valor que el YAML declare; el umbral real es `first_cycle_target_ul` |
| `aestivation_supported` | por especie | [booleano] | [EP] | bandera de especie; la supervivencia en arresto la fija `arrested_daily_survival` |

**Se crea el bloque `mating:`** (capa macho, §8). El bloque **no existe hoy**: no hay
ninguna clave `p_mate`, `local_swarm` ni `mating` en `model_constants.yaml`,
`config_validation.py`, `config.hpp` ni `config.cc`. Por eso `mating.p_mate`,
`mating.local_swarm_attendance_factor` e `insemination_prob` **no se retiran: se
crean**, con nombres nuevos y con el mismo tratamiento que `sperm_store_days` (que
tampoco existe como clave configurable: su semántica es fija, §12.3).

| Clave | Valor | Unidad | Tier | Referencia / nota |
|---|---|---|---|---|
| `p_mate_male_fraction` | 0,072 ± 0,0095 | [fracción de machos del enjambre por noche] | [P] | Diabaté et al. 2011 (*gambiae* s.s.); **única** de las dos cifras en la unidad que la fórmula necesita |
| `p_mate_pairs_per_individual` | 0,084–0,25 | [pares por individuo de ambos sexos, por enjambre] | [M] / [NR] | Ouédraogo et al. 2025 (*coluzzii*): **cota de sensibilidad, no comparable** con la anterior; con `ρ_macho` = 0,5 equivale a 0,168–0,50 como cota superior |
| `p_mate_size_exponent` | 0 (banda 0–1) | [adimensional] | [EP] | **entra en la ecuación**: `cupos(s) = M_disp(s) × p_mate_male_fraction × (M(s)/male_swarm_reference_size)^(−p_mate_size_exponent)` (§8.5) |
| `male_swarm_reference_size` | 100 | [machos por enjambre] | [EP] | tamaño de referencia de la ley de eficiencia; escala del exponente anterior |
| `female_attendance_rate` | 0,1033 | [fracción] | [P] | Diabaté 2009 (47/455 hembras *tethered* inseminadas): probabilidad de que una hembra presente en el sitio esté en posición de cópula; **se aplica una sola vez**, en el término de presencia (`hembras_presentes(s)`, §8.1) |
| `local_swarm_male_offer_factor` | 0 | [fracción] | [EP] | enjambre local sin marcador: no hay medición de asistencia de hembras (Kaiser et al. 2021); actúa sobre la **oferta masculina** (`male_offer_factor`), no sobre la demanda |
| `male_move_capacity_m` | 50 (banda 40–100) | m/día | [EP] | estimación propia; orden de magnitud de la permanencia post-emergencia (< 60 % de los adultos a más de 50 m del sitio larvario) [P] y de la dispersión media 85,7 m (Kaiser et al. 2021) [P]; el escenario puede sobrescribirlo |
| `male_females_per_night_max` | 3 | [hembras por macho por noche] | [M]/[NR] | Ekechukwu & Tripet 2019: límite **citado, no medido** en ese artículo |
| `swarm_duration_min` | 28,3 (banda 19–39) | min | [P]/[M] | media del rango mensual (Bimbilé Somda et al. 2018 [P]); ≈27 min (18:05–18:45) en Ouédraogo et al. 2025 [M] |
| `swarm_start_min_after_sunset` | 5 | min | [P] | Bimbilé Somda et al. 2018 |
| `swarm_height_m` | 2,87 ± 0,20 | m | [M] | Ouédraogo et al. 2025 |
| `swarm_markers_per_km2` | banda declarada | [marcadores/km²] | [EP] | densidad del campo de sitios; la fija el escenario |
| `swarm_markers_source` | — | [cadena] | [EP] | procedencia del campo de sitios del escenario |
| `rain_suppresses_swarming` | sí | [booleano] | [P] | 0 parejas por enjambre en el pico de lluvias |

**No son claves configurables**: `male_offer_factor` (antes `cap(s)`) es **derivado**
—1 para un sitio del campo, `local_swarm_male_offer_factor` para un enjambre local— y
actúa sobre el lado **masculino** de la oferta (§8.1). `p_mate_pairs_per_individual` no
entra en la ecuación por defecto: es cota de sensibilidad. Con la asignación de §8.6 no
se crea ningún enjambre local (los machos sin sitio no se reproducen), de modo que el
valor 0 de `local_swarm_male_offer_factor` no llega a cambiar la oferta.

**Se crean (integración temporal, bloque `integration:`)**:

| Clave | Valor | Unidad | Tier | Referencia / nota |
|---|---|---|---|---|
| `directed_flight_budget_h` | 0,36–0,73 | h | **derivado** | 590 m ÷ `flight_speed_ms` (§5); consumible **por día**; no es "~1 h/día" |
| `dt_terminal_s` | 0,04 | s | [EP] | 25 Hz: Nyquist estricto sobre el evento de giro de 0,08 s ⇒ 2 muestras (§5) |
| `dt_olfactory_s` | 0,25 | s | [EP] | banda olfactiva (0,72–70 m) |
| `plume_memory_s` | 0,5–0,9 | s | [P] | segmentos de *cast* (Cummins 2012); la cota de 300 ms es *Aedes* [P] |
| `landing_speed_mm_s` | 50 | mm/s | [P] | gate de aterrizaje (Hinze 2021) |
| `landing_speed_hold_s` | 3 | s | [P] | mantenimiento del gate; evaluable sólo dentro de la banda visual (25 Hz ⇒ 75 muestras) |

**Regla de duplicación (claves que aparecen en dos superficies).** `directed_flight_budget_h`
y `plume_memory_s` están declaradas en las dos superficies: la fila por especie
(`species.<fila>.<clave>`) y el bloque `integration:`. Regla: **la tabla por especie
sobreescribe; `integration:` es el valor por defecto**. El valor que consume el motor es
el de `species.<fila>.<clave>` cuando la fila lo declara, y el de `integration:` cuando
no; no hay una tercera fuente. Con los valores por defecto del plan los dos coinciden
(`plume_memory_s` = 0,5–0,9 s [P]; `directed_flight_budget_h` = 0,36–0,73 h,
**derivado**: 590 m ÷ `flight_speed_ms`), de modo que la duplicación no altera ningún
valor por defecto: sólo fija qué superficie manda cuando una fila difiere.

**Se crea (capa macho, bloque `mating:`)**: `male_move_capacity_m` — ya declarado
en la tabla del bloque `mating:` (50 m/día, banda 40–100, [EP]), con la advertencia de
que la cifra publicada (rango de **40 a 549 m**) es una dispersión neta **por
experimento** con ventana ≤ 7 días, **no** una tasa diaria: la clave documenta la
ambigüedad en vez de ocultarla.

**No se crea (capa macho)**: `male_swarm_site_range_m` se **retira**. Su única función era fijar una separación mínima entre marcadores; la asignación ya no la usa: el campo se genera con `swarm_markers_per_km2` y el macho sortea entre los sitios alcanzables con peso de acumulación, o queda suelto (§8.6). **[EP]**

**Se crea (clave de manifiesto)**: `slots_per_cell`, fijada en la primera extracción como máximo de `human_total` más 10 %; con él, `human_id = cell_id * SLOTS_PER_CELL + slot` es una biyección
estable (§2).

**Se crean (contratos, bloque `contracts:`)**: `contracts.habitat` = **"4.0"** (el
registro por celda pasa a ser parte del contrato) y `contracts.cogs_state` = **"5.0"**
(una sola banda; §10). El contrato del NC de entorno (`contracts.env_nc`) **no
cambia**: sigue en "3.0".

**El bloque `gonotrophic` se redefine**: `egg_batch_n/mean/min/max` (invariante
`min <= mean <= max <= n`) se sustituyen por un lote **proporcional al volumen
acumulado** con tope `egg_batch_max`; la validación de `config_validation.py` cambia
en consecuencia, y `test_config_validation.py` se reescribe.

**Nota sobre `host_seeking_scale_m`**: además de retirarse como radio de atracción,
esta clave **pondera el kernel de siembra** (`seeding.hpp`). Retirarla cambia la
distribución inicial de la población ⇒ hay que decidir explícitamente si la siembra
pasa a usar `exploration_range_m` o si su propio kernel se mantiene con otra clave.
Es un efecto secundario que la versión anterior del documento señalaba y que el plan debe resolver de
forma explícita (se resuelve en el plan de implementación: la siembra pasa a usar
`daily_move_capacity_m`).

#### 12.1 — Superficies de configuración: **cinco**, no tres

Cada clave de especie (y cada clave global) vive en **cinco** superficies mantenidas
que deben cambiar a la vez. Un cambio de esquema que toque sólo el YAML rompe algo, y
cada superficie rompe de una manera distinta:

| # | Superficie | Ruta | Qué rompe si la clave no está o no coincide |
|---|---|---|---|
| 1 | YAML | `mal-core/config/model_constants.yaml` | el propio motor no arranca: el cargador de Python valida antes |
| 2 | Modelo pydantic | `mal-core/src/mal_core/config_validation.py` (`SpeciesRow:159`, `Gonotrophic:284`, `Dispersal:296`, `HostSeeking:312`; `_StrictModel` con `extra="forbid"` en todos los niveles, `config_validation.py:110`) | una clave **nueva no declarada** rompe el validador (`extra="forbid"`); una clave **retirada** sin quitar del modelo rompe igual |
| 3 | `struct` C++ | `mal-core/src/mal_core/abm/include/mal_abm_fast/config.hpp` (`SpeciesRow:139`, `GonotrophicCfg:376`, `DispersalCfg:408`, `HostSeekingCfg:450`) | el motor no enlaza o lee un valor por defecto silencioso |
| 4 | Enlaces por nombre | `mal-core/src/mal_core/abm/src/config.cc` (`Loader::key()` busca la clave **por nombre**; si falta, la carga en `missing` y `ConfigError` al final; una clave **desconocida se ignora en silencio**) | falla **sólo** si falta una clave que él exige: una clave nueva olvidada aquí **no** falla — el motor usa el valor por defecto de C++ |
| 5 | Volcado | `mal-core/src/mal_core/abm/src/config_dump.cpp:103-106` | el volcado **omite la clave en silencio** y rompe **sólo** el golden del dump (`tests/test_config_engine_golden.cpp`) |

**Regla**: una clave no está en el modelo hasta que está en las cinco. La paridad
Python↔C++ la verifica `mal-core/tests/test_config_validation.py` y el golden del
volcado, `mal-core/src/mal_core/abm/tests/test_config_engine_golden.cpp`.

**Una sola rebanada.** Las cinco superficies se resuelven **una vez**, en el **Paso 4**,
con **todas** las claves nuevas del plan; a partir de ahí **ninguna clave se añade**
(§12.4). Eso incluye las claves de los pasos que antes se creaban más tarde: Paso 2
(`SLOTS_PER_CELL`), Paso 3 (fisiología de la sangre), Paso 6 (`arrested_daily_survival`,
`gonotrophic_arrest_prob_dry`), Paso 7 (`contracts.habitat`) y Paso 8 (bloque
`mating:`) — todas nacen en el Paso 4 y los pasos posteriores sólo las **consumen**.

#### 12.2 — `activity_weights`: el mapeo explícito

El YAML declara hoy `activity_weights: [0.02, 0.10, 0.80, 0.08]`
(`model_constants.yaml:66`) en el orden **[DAY, EVENING, NIGHT, DAWN]** (orden fijado
en `species_params.hpp:30-33` y validado en `config.cc:598-610`, que exige **cuatro**
elementos). El plan propone la fila derivada con las duraciones de K-3: `[0.00, 0.255, 0.480, 0.265]` (sección 12.2).

**Mapeo de los tres bins medidos a las cuatro fases del motor** (fuente:
`papers/anopheles-dynamics/akuoko-2024-biting-behaviour-ghana.md:25-26` y la
derivación del propio estudio):

*   Bins de la fuente: **EE** = 18:00–22:00, **LE** = 22:00–04:00, **EM** = 04:00–06:00.
*   Fases del motor (`mobility_schedule.hpp:41-46`): **DAY** = 06:00–18:00,
    **EVENING** = 18:00–21:00, **NIGHT** = 21:00–05:00, **DAWN** = 05:00–06:00.
*   Tasas horarias de *coluzzii* (n = 935): EE = 25,5 %/4 h = 6,375 %/h;
    LE = 48,0 %/6 h = 8,0 %/h; EM = 26,5 %/2 h = 13,25 %/h.

| Fase | Horas del motor | Fracción de las horas del bin | Cálculo | Valor |
|---|---|---|---|---|
| DAY | 12 (06:00–18:00) | ninguna | las colecciones empiezan a las 18:00 ⇒ no medido | **0,000** |
| EVENING | 4 (18:00–22:00) | EE completa | 4 × 6,375 % | **0,255** |
| NIGHT | 6 (22:00–04:00) | LE completa | 48,0 % (tasa de 8,0 %/h × 6 h) | **0,480** |
| DAWN | 2 (04:00–06:00) | EM completa | 2 × 13,25 % | **0,265** |

Suma = 1,000. La fila es `[DAY, EVENING, NIGHT, DAWN] = [0.00, 0.255, 0.480, 0.265]`, con
`w_DAY = 0` como **consecuencia de la falta de dato**, no como afirmación (perfil
medido, no supuesto).

**Duración de las fases — cerrada (decisión del autor).** `phase_duration_hours` es
**lógica nueva**: el motor no tiene hoy ninguna tabla de duraciones
(`mobility_schedule.hpp:41-46` es el enum `TimePhase` con las ventanas **anotadas en
comentarios**: 06:00–18:00 / 18:00–21:00 / 21:00–05:00 / 05:00–06:00). El día corre
**cuatro pasadas de fase** (`mosquito_submodel.cpp:803-805`, comentario "one realization
per day+phase"), **cada una de igual peso**; el único reloj es `dispersal.flight_hour`
= 20 (`model_constants.yaml:238` → `engine.cpp:577` `set_current_hour`), usado sólo por
`is_nighttime_hour` (`mosquito_submodel.cpp:1013`).
El **valor por defecto** son **DAY 12 h / EVENING 4 h / NIGHT 6 h / DAWN 2 h** (Σ = 24 h), en el YAML, con el día empezando a las **06:00** (el mismo inicio que la ventana DAY 06–18 del motor). Sustituyen a las ventanas de los comentarios de `mobility_schedule.hpp`. Cada fase corresponde a un bin medido: EVENING 18–22 = EE, NIGHT 22–04 = LE, DAWN 04–06 = EM. Con ese reloj el reparto EE/LE/EM → fases es `[0.000, 0.255, 0.480, 0.265]`. **Este reparto cambia respecto a la versión anterior del plan.** Si se fija otra hora de inicio, las fases dejan de corresponder a los bins y el reparto debe recalcularse y justificarse de nuevo.
La tabla de duraciones vive en la configuración (`integration.phase_duration_hours`);
`mobility_schedule.hpp` **no** contiene cálculo de duración que tocar (sólo el enum y
sus ventanas en comentario → tabla), y el **reloj de fase se añade en el motor**
(§15, Paso 5): la hora de la fase se fija en
`mal-core/src/mal_core/abm/src/engine.cpp` (hoy un único `set_current_hour` por día,
`engine.cpp:577`) y la duración de cada fase la consume
`mal-core/src/mal_core/abm/src/mosquito_submodel.cpp` al abrir cada pasada
(`mosquito_submodel.cpp:803-805`). La fila `activity_weights` se re-deriva en el
**mismo paso** con el procedimiento de esta tabla.

**Validación de `activity_weights`.** La fila debe (i) sumar **1** (Σ = 1,000) y (ii)
ser coherente con las duraciones vigentes: el valor de cada fase es la **fracción de
horas** que esa fase ocupa en el perfil medido (la tabla de arriba). `activity_weights`
deja de ser sólo "¿está activa la fase?" (`host_seeking.hpp:43`) y pasa a ser el
**perfil horario por fase**; el motor pasa de cuatro pasadas de igual peso a pasadas
**con duración y peso** (§15, Paso 5).

#### 12.3 — Umbral de *override*: una clave, un nombre

Ninguna de las tres claves que aparecen en esta sección **existe hoy** en el
repositorio: `p_mate`, `insemination_prob` y `local_swarm_attendance_factor` no están
en `model_constants.yaml`, `config_validation.py`, `config.hpp` ni `config.cc` (la
única aparición de `p_mate` en el repo es este mismo plan). Por eso **no se retiran:
se crean**, con nombres nuevos y sin alias.

*   **El nombre vivo de la tasa es `p_mate_male_fraction`** (0,072 ± 0,0095, [P]),
    dentro del bloque `mating:` que se crea en el Paso 4; el override por escenario se
    hace sobre `p_mate_male_fraction` (o sobre `p_mate_pairs_per_individual`, que es
    cota, no valor por defecto). Los nombres `p_mate` e `insemination_prob` **no** se
    crean: no hay dos nombres para lo mismo.
*   **La asistencia de hembras al enjambre tiene un solo nombre**:
    `female_attendance_rate` (0,1033, [P]), aplicada **una sola vez**, en el término de
    presencia (§8.1). `local_swarm_attendance_factor` no se crea; el factor que sí
    existe es `local_swarm_male_offer_factor` = 0 [EP], que actúa sobre la **oferta
    masculina** (§8.1).
*   **`sperm_store_days` recibe el mismo tratamiento**: **no existe como clave
    configurable** (tampoco hoy) y su semántica es fija —monandría con tapón
    espermático, el esperma no caduca (§8.6)—, sin ninguna magnitud que el
    implementer pueda elegir. Las cuatro son, en el mismo sentido, **creaciones
    pendientes o semánticas fijas**, no retiradas. Si en el futuro se modela el
    desgaste, se añade la clave en ese momento, con su rebanada (§12.4).

#### 12.4 — Orden: **una sola rebanada**, en el Paso 4

El esquema de configuración (las cinco superficies) se resuelve **una sola vez**, en el
**Paso 4**, con **todas** las claves nuevas del plan. **Ninguna clave se añade después
del Paso 4**: los pasos siguientes sólo **consumen** lo que el Paso 4 ya creó. Así
ninguna etapa del motor usa constantes compiladas (lo prohíbe
`mal-core/tests/test_no_constants_guard.py`) y no hay ramas en paralelo para el esquema
(dejarían a los pasos intermedios sin configuración).

**Consecuencia de orden.** Los pasos que consumen claves nuevas son el Paso 2
(`SLOTS_PER_CELL`), el Paso 3 (fisiología de la sangre), el Paso 5 (cascada y
movimiento), el Paso 6 (estado fisiológico y seca), el Paso 7 (acuático y
`contracts.habitat`) y el Paso 8 (bloque `mating:`). Como sus claves nacen en el Paso 4,
**el número de paso es una etiqueta, no el orden de ejecución**: el orden efectivo de
implementación es **0 (arnés) → 1 (línea base) → 4 (esquema) → 2, 3, 5, 6, 7, 8, 9, 10,
11**.

**Qué claves consume cada paso** (todas ya declaradas en el Paso 4):

| Paso | Claves que consume |
|---|---|
| Paso 0 — arnés de escenarios | el manifiesto sintético y el bloque `rng:` (semilla maestra, §13.4); ninguna clave nueva de modelo |
| Paso 1 — línea base | ninguna clave nueva |
| Paso 2 — individuos humanos | `SLOTS_PER_CELL` (global) y el campo de manifiesto `human_total` (personas por celda, §2) |
| Paso 3 — fisiología de la sangre | `blood_meal_target_ul`, `first_cycle_target_ul`, `blood_meal_size_ul`, `meal_size_min_ul`, `blood_meal_refractory_days`, `probing_success_rate`, `eggs_per_ul`, `species.<fila>.meals_per_cycle_mean`, bloque `gonotrophic` redefinido (`egg_batch_max`) |
| Paso 4 — esquema | **crea** todas las claves nuevas (las cinco superficies) |
| Paso 5 — cascada y movimiento | `species.<fila>.co2_activation_radius_m`, `olfactory_radius_m`, `visual_radius_m`, `terminal_radius_m`, `flight_speed_ms`, `exploration_range_m`, `exploration_step_m`, `exploration_step_correlation`, `casting_probability`, `casting_angle_deg`, `plume_memory_s`, `anemotaxis_rule`, `wind_reference`, `wind_block_threshold_ms`, `daily_move_capacity_m`, `directed_flight_budget_h`; `integration.phase_duration_hours`, `integration.dt_terminal_s`, `integration.dt_olfactory_s`, `integration.landing_speed_mm_s`, `integration.landing_speed_hold_s` |
| Paso 6 — estado fisiológico y seca | `arrested_daily_survival`, `gonotrophic_arrest_prob_dry`, `species.<fila>.aestivation_supported` |
| Paso 7 — acuático por celda | `contracts.habitat` ("4.0") |
| Paso 8 — machos y cupos | bloque `mating:` completo (`p_mate_male_fraction`, `p_mate_pairs_per_individual`, `p_mate_size_exponent`, `male_swarm_reference_size`, `female_attendance_rate`, `local_swarm_male_offer_factor`, `male_move_capacity_m`, `male_females_per_night_max`, `swarm_duration_min`, `swarm_start_min_after_sunset`, `swarm_height_m`, `swarm_markers_per_km2`, `swarm_markers_source`, `rain_suppresses_swarming`) y `species.<fila>.male_ratio`, `male_daily_survival` |
| Paso 9 — sitio de oviposición | ninguna clave nueva; retira `oviposition.scale_m` |
| Paso 10 — escenarios | sólo overrides de escenario de las claves anteriores |
| Paso 11 — contratos y consumidores | `contracts.cogs_state` ("5.0") |

**Retiradas y forma intermedia del YAML.** El cargador es estricto en los dos sentidos:
el modelo pydantic rechaza claves desconocidas (`extra="forbid"`) y `config.cc` falla
si falta una clave que él exige. Como la rebanada es única, **las claves nuevas existen
todas desde el Paso 4** y **las claves retiradas se eliminan del YAML en el mismo
commit que las retira el código**. Excepción declarada: dos claves cuyo código se
reescribe más tarde —`dispersal.snap_radius_m` (Paso 7) y `oviposition.scale_m`
(Paso 9)— **permanecen declaradas** en el YAML hasta que su paso las retire, porque el
motor las leería si desapareciesen antes; su eliminación posterior es una
**eliminación**, no una creación, y por tanto no contradice la regla de la rebanada
única. Ninguna rebanada intermedia puede tener una clave presente en el YAML y ausente
en una de las otras cuatro superficies.

**El bloque `rng:`**: las tres semillas fijas actuales (`aquatic_seed_washout`,
`aquatic_seed_stage_mortality`, `aquatic_seed_larva_mortality`,
`model_constants.yaml:277-279`) se **retiran**: el stream acuático se deriva de la
semilla maestra (§13.4). Sin ese cambio, "una semilla maestra" es falso.

### 13. Arnés de escenarios sintéticos

Pre-requisito de todo lo demás: sin él no hay termómetro.

**Restricción de diseño (impuesta por el autor).** La versión anterior del documento pedía explícitamente
"una ruta de ejecución que **no** pase por el modo manifiesto" (su apartado 13, paso 0).
El autor lo rechaza: **el arnés debe pasar siempre por el manifiesto**. La solución no es una ruta alternativa, sino **un manifiesto sintético**
construido igual que uno real, sobre un AOI pequeño, donde lo único "a mano" son las
personas, los animales y los mosquitos.

#### 13.1 — El AOI sintético

*   **Slug**: `accra-synth-10x10`. **Bounding box** recortado de la ventana de Accra:
    `[-0.2, 5.7, -0.10971147034573944, 5.789842104336081]` ⇒ `cells_per_side() = (10, 10)`
    con celdas de exactamente 1 km.
*   **La geometría llega al binario por el `--bbox` que ya existe**:
    `mal-core/src/mal_core/abm/wrapper.py:166-172`
    sólo consulta `aois.yaml` cuando no se da bbox, y `--resolution-m` / `--scale` toman
    después los valores por defecto del binario (1 000 m / regional). **No hay que tocar
    ningún fichero de producción para esto.**
*   **Raíz de datos**: `runs/synthetic/accra-synth-10x10/` (fuera de `data/`, que está
    protegida y git-ignored; `runs/` sí es el sitio natural de las corridas).
*   **Tres artefactos, todos remuestreados de `data/accra-coastal-test/`**:
    *   `env.nc` — 10×10, las **9 variables** del contrato `env_nc = "3.0"`, con
        `contract_version = "3.0"` **sin cambios**: el viento **no** entra como banda
        nueva del NC de entorno (eso obligaría a bumpear `contracts.env_nc`, fuera del
        alcance de este plan); el motor lo carga como **dataset aparte** (§15, Paso 5).
    *   `habitat_patches.gpkg` — Point por celda con `hab_type`, `dynamics` (int 0/1),
        `habitat_potential`, `row`, `col`; el potencial **recalculado** con
        `mal_core.habitat.potential`.
    *   `host_static.nc` — 9 variables sobre (y, x).
*   **Dos generadores de AOI, y sólo uno para el arnés**:
    `mal-execution/scripts/make_synthetic_aoi.py` genera el AOI **10×10** del arnés
    (este apartado); `mal-core/src/mal_core/abm/tests/fixtures/make_golden_fixtures.py`
    genera el AOI **8×8** de los goldens de `ctest`. El arnés usa el **10×10**,
    porque los escenarios necesitan una rejilla de **1 km exacta** (100 celdas) y
    personas, animales y cohortes **en metros**; los fixtures 8×8 no se tocan en este
    plan.
*   **Campo de viento del AOI sintético (para E18)**: además de los tres artefactos
    anteriores, el generador escribe el **campo de viento** (`u100`/`v100`, ERA5
    6-horario) que el motor carga por `--wind-field` (`wind_field.cpp:47-56`,
    `wind_field.hpp:22-26`). Es el único nivel de viento disponible (§4); sin él, la
    rama de viento queda inactiva y la anemotaxis y el bloqueo no se ejercitan.
*   **Lo "a mano"**: el plano `human` de `host_static.nc` es la población del escenario
    (recuentos por celda) y `cattle`/`goats`/`sheep` son los animales del escenario.

#### 13.2 — Los parámetros del escenario viajan en el manifiesto

Un conjunto nuevo de ficheros de escenario: **19** ficheros, `E00.json … E18.json` (uno
por escenario; E10 lleva sus tres variantes **dentro** del mismo JSON, en `variants`),
referenciado por el manifiesto. El manifiesto sigue siendo la **única fuente de
verdad**: el escenario es un dataset más, con su validación de completitud como todos
los demás.

**Una clave de dataset por escenario**, no una clave con diecinueve ficheros:

*   La clave es `scenario:E01`, `scenario:E02`, … (`:` como separador del dataset y
    del id), y su `files` indexa **un** fichero: `files: {"E01": "scenarios/E01.json"}`.
*   **Resolución de la ruta en runtime**: `validate_completeness()`
    (`manifest.py:193`) resuelve cada fichero declarado contra `root/aoi`
    (`manifest.py:203-243`): con `files["E01"] = "scenarios/E01.json"` el fichero
    tiene que existir en `<data-root>/<aoi>/scenarios/E01.json`.
*   **Quién lo pone ahí**: el **generador** (`make_synthetic_aoi.py`, Paso 0) **copia**
    los JSON versionados desde `mal-core/src/mal_core/abm/tests/scenarios/` al
    directorio del AOI. La **copia canónica** es la del repo; en runtime el arnés
    **no** lee del repo.
*   `validate_completeness()` comprueba **todos** los ficheros declarados e **ignora**
    `required_for_abm`: la opcionalidad real es la **ausencia de la clave**. Por eso
    el manifiesto sintético declara **una sola** clave de escenario —la del escenario
    que se ejecuta— y el generador escribe los 19 ficheros, pero sólo el declarado
    cuelga del manifiesto.
*   El arnés resuelve `files[str(id)]` de la clave `scenario:<id>`; **nunca** «el
    primero». Un escenario sin clave declarada es un error de manifiesto explícito.

Ejecución:

```
malariasim abm --aoi accra-synth-10x10 --bbox <…> --data-root runs/synthetic \
                --scenario E01 --seed 20261117
```

La ruta es exactamente la de producción: `validate_completeness()` → `resolve()` →
binario.

#### 13.3 — Siembra por individuo (lo que hay que añadir)

Hoy `SeedInstruction` (`seeding.hpp:119`) transporta **recuentos**, no individuos; el
sexo es una moneda (`mosquito_submodel.cpp:358`) y la posición es el centro del parche.
Sin siembra individual, **E01, E02, E07, E08, E09, E13 y E14 son inejpresables**. Se añade:

*   `AgentSpec` (mosquito): (x, y), sexo, estado, edad, estado vectorial.
*   `AquaticSpec` (cohorte): (x, y), celda, estadio, instar, desarrollo, recuento.
*   `ScenarioSpec`: lista de `AgentSpec`, lista de `AquaticSpec`, lista de personas con
    (x, y) y estado, semilla maestra, días, **modo**, expectativas.
*   `SeedingMode::SCENARIO` y su rama en `CoordinatorModel`
    (`build_scenario_seed_instructions`).

**Convención de coordenadas: una sola.** Todos los agentes, las personas y las cohortes
del escenario usan **coordenadas proyectadas en metros del AOI** (origen local del
AOI, §1). `lon`/`lat` sólo aparecen en los artefactos geográficos de entrada
(`env.nc`, `host_static.nc`, `habitat_patches.gpkg`), nunca en un `ScenarioSpec` ni en
un `AgentSpec`: la especificación del Apéndice A que hoy dice «1 hembra en (lon,lat)»
queda corregida a metros.

Los humanos pasan de "recuento por celda" a **individuos con posición**, que es el
requisito de E01 (una persona a 200 m del mosquito: 200 m está por debajo de la
resolución de 1 km, así que la granularidad sub-celda es obligatoria).

#### 13.3.1 — Especificación normativa del escenario

**Dónde vive el arnés.** El componente tiene nombre y ubicación fija:
`mal-core/src/mal_core/abm/tests/scenarios/harness.py` (biblioteca: carga el
`ScenarioSpec`, resuelve la clave de manifiesto `scenario:<id>`, lanza el binario,
compara y escribe el observado-vs-esperado) y
`mal-core/src/mal_core/abm/tests/test_scenarios.py` (punto de entrada **pytest**: un
test por escenario). El arnés entra en el CI por `pytest` —el `pyproject.toml` raíz
configura `testpaths = ["mal-core/tests", "mal-commonlib/tests",
"mal-core/src/mal_core/abm/tests"]`—, **no** por `ctest` (que es C++). El directorio
`mal-core/src/mal_core/abm/tests/scenarios/` **lo crea el Paso 0**, junto con los JSON
versionados: hoy **no existe**.

**Claves del `ScenarioSpec`** (JSON, un fichero por escenario):

| Clave | Tipo | Unidad | Obligatoria | Significado |
|---|---|---|---|---|
| `id` | string | — | sí | `E00`…`E18`; coincide con el nombre del fichero y con el id de la clave de manifiesto |
| `mode` | enum `gate` \| `report` | — | sí | `gate`: compara y **sale con código distinto de 0** si no cumple (lo recolecta el CI); `report`: escribe observado-vs-esperado y **sale siempre con 0** |
| `seed` | int | — | sí | semilla maestra; de ella derivan todos los sub-streams (§13.4) |
| `days` | int | días | sí | días simulados |
| `agents` | list[`AgentSpec`] | — | sí (puede estar vacía) | mosquitos a sembrar |
| `aquatic` | list[`AquaticSpec`] | — | no (por defecto `[]`) | cohortas acuáticas a sembrar |
| `humans` | list[`HumanSpec`] | — | no (por defecto `[]`) | personas con posición y estado |
| `livestock` | list[`LivestockSpec`] | — | no (por defecto `[]`) | animales (bovino/caprino/ovino) |
| `overrides` | map[string → number] | según la clave | no | claves de `model_constants.yaml` que el escenario sobreescribe (bandas de sensibilidad) |
| `variants` | list[map] | — | no (por defecto `[]`) | **variantes de un mismo escenario** (sólo E10): cada elemento declara los mismos campos del `ScenarioSpec` raíz más sus `overrides` y sus `expectations` propios; el arnés ejecuta **una variante por elemento**, con la misma semilla, y compara cada una con su propia banda |
| `expectations` | list[`Expectation`] | — | **obligatoria si `mode` = `gate`** | resultado esperado y tolerancia pre-registrada |

**`AgentSpec`**: `x` (m, req), `y` (m, req), `sex` (`MALE` \| `FEMALE`, req),
`state` (enum del SoA, opt), `age_days` (días, opt), `infective` (bool, opt),
`swarm_site_id` (int, opt; −1 = sin sitio).

**`AquaticSpec`**: `x` (m, req), `y` (m, req), `cell_id` (int, req), `stage`
(`EGG`\|`L1`\|`L2`\|`L3`\|`L4`\|`PUPA`, req), `instar` (int, opt), `development`
(fracción 0–1, opt), `count` (int, req).

**`HumanSpec`**: `x` (m, req), `y` (m, req), `state`
(`SUSCEPTIBLE`\|`EXPOSED`\|`INFECTIOUS`\|`RECOVERED`, opt), `timer` (días, opt).

**`Expectation`**: `kind` (`band` \| `value` \| `report`), `value` (número),
`tol` (número; para `band`, semi-amplitud o par de extremos), `unit`, y `expression`
(cadena que dice **cómo** se calcula el valor esperado, con su referencia). `kind` =
`report` significa «este número se escribe, pero no falla el CI».

**Quién escribe cada expectativa.** La expectativa se escribe **una sola vez**, en el
paso que implementa el comportamiento que comprueba: el Paso 2 escribe la de `human_id`
(E08, E09), el Paso 3 las de la sangre (E03–E06, E11), el Paso 5 las de la cascada
(E01, E02, E10) y del viento (E18), el Paso 6 la de la seca (E12), el Paso 7 la de la
emergencia (**aserción A** de E07), el Paso 9 la de elección del sitio de oviposición
(**aserción B** de E07), el Paso 8 las de los machos (E14, E15) y el Paso 10 la de SIT/IIT
(E17). El **Paso 1 no escribe expectativas**: escribe el **baseline** —lo que hace hoy
la cadena actual— en un artefacto aparte (`runs/_check_current/E01.baseline.json`), y
ese baseline es lo que se compara para detectar regresiones.

**El criterio de cierre de un paso no es «el escenario pasa» antes del Paso 10.** El
arnés existe desde el Paso 0, de modo que un paso **puede** ejecutar su escenario desde
el momento en que escribe su expectativa. Lo que el plan exige de cada paso es que su
expectativa esté **pre-registrada y sea satisfacible** por el comportamiento que ese
paso implementa (§15, columna «Cálculo a mano pre-registrado»): si al terminar el paso
el escenario todavía no se puede ejecutar —porque depende de un paso posterior— su
expectativa queda escrita y **marcada como pendiente** (`mode: report` con la banda
derivada), y el paso **no** se da por cerrado hasta que el escenario que lo cierra pase
en modo `gate`. El Paso 10 cierra el conjunto: fija los modos definitivos
(`gate`/`report`) y verifica que **cada** escenario de la tabla de §15 tiene su
expectativa y su modo.

**Quién escribe cada fichero JSON.** El **Paso 0** crea los 19 ficheros
`scenarios/E00.json … E18.json` **vacíos de expectativas**, con su modo provisional y
sus overrides. Cada paso **edita** su propio fichero y le añade sus expectativas. El
**Paso 10** hace la pasada final: fija los modos y comprueba la cobertura completa.
El arnés, por tanto, **no** crea el conjunto de escenarios tres veces.

**Modos y CI.** Los escenarios `gate` **fallan el CI**; los `report` no. Esto resuelve
la contradicción anterior entre «el arnés termina con código 0» (§13.6) y «los
escenarios con forma cerrada fallan el CI» (Nivel 4): depende del modo declarado.

#### 13.4 — Maestros de semillas: hay que arreglar un hueco real

Un único `--seed` debe derivar los sub-streams de **todos** los subsistemas
(coordinador, submodel, banco acuático, micro-integrador). El motor deriva hoy los
streams de coord/sub/transmisión del `Prng` maestro (`engine.cpp:103-105, 303-305`),
pero **el banco acuático se auto-siembra con constantes fijas**
(`aquatic_cohort_bank.cpp:204/227/298`, leídas de `model_constants.yaml:277-279`).
Consecuencia: **"una semilla maestra" hoy sólo es cierto para tres de los cinco
streams**. El paso 0 del plan debe **derivar también el stream acuático** de la semilla
maestra (y añadir el cuarto `peek_state()` para el micro-integrador), o la
reproducibilidad bit a bit del escenario no está garantizada.

#### 13.5 — Tres trampas del catálogo que el escenario debe esquivar

1.  **`required_for_abm` es decorativo.** `validate_completeness()`
    (`manifest.py:193`) **comprueba todos los ficheros declarados** e ignora la marca de
    obligatoriedad; la opcionalidad real viene de que la clave **no exista**. Por tanto
    los datasets opcionales **no deben declararse** — y como cada escenario es **una
    clave propia** (`scenario:<id>`, §13.2), el manifiesto declara **una sola**: E01 no
    depende de que exista E16. El generador escribe los 19 ficheros, pero sólo el
    declarado cuelga del manifiesto.
2.  **Discrepancia de tipo en `dynamics`.** Python escribe `persistent|pluvial`
    (`ingest/env.py:88`) y C++ lee un int (`habitat_engine.cpp:220`) ⇒ siempre 0.
    Inofensivo hoy (la separación se recalcula por nombre desde los planos H), pero el
    gpkg sintético debe escribir el **int** y no heredar el error.
3.  **El motor descarta en silencio los parches con `habitat_potential < 0,01`**
    (`habitat_engine.cpp:216`). Una de las 99 features de la ventana de Accra
    (0,00978) queda por debajo del suelo ⇒ la ruta de recorte **debe aplicar el umbral
    explícitamente**, o el escenario tendrá menos parches de los que cree.

#### 13.6 — Comportamiento de cada escenario

Cada escenario declara su **modo** (§13.3.1): `gate` compara y sale con código
distinto de 0 si no cumple (lo recolecta el CI); `report` escribe
observado-vs-esperado en `runs/_check_current/` y **termina siempre con código 0**.
El detalle por escenario —mapa **E00–E18**, definiciones y expectativas— está en el
**Apéndice A** de este documento; la cadena de semillas y las trampas del catálogo, en
el **Apéndice B**.

**Escenarios que la evidencia de §16 añade al conjunto:**

*   **E15 — Intervención dirigida al enjambre (*swarm killing*)**: mata los machos de los
    marcadores; la aserción es la caída de la tasa de inseminación y de la densidad de
    hembras. Es el escenario que **obliga** a que el campo de marcadores sea discreto y
    eliminable, no un campo uniforme.
*   **E16 — Contrescenario ITN al 60 %**: el mismo campo de sitios con ITN al 60 %;
    comprueba que la protección individual **no** compensa la pérdida de cupos del
    enjambre. Es un contrascenario de **ITN**, no de SIT/IIT: lo que el escenario
    llevaba bajo el título «Contrescenario SIT/IIT» era en realidad ITN al 60 %, y el
    título se corrige para que el escenario y su nombre digan lo mismo.
*   **E17 — SIT/IIT sobre los cupos por sitio**: machos estériles asignados a los
    mismos sitios, compitiendo por los mismos cupos. El modelo **sí** representa este
    efecto y **no** simula la competencia *intra-enjambre* entre machos estériles
    individuales (N11, §8.6). La aserción es la caída de `cupos(s)` y el aumento de la
    fracción de hembras sin inseminar. **E17 se crea** para que N11 y §8.6 remitan a
    un escenario que existe.
*   **E18 — Rama de viento**: el AOI sintético **incluye campo de viento**
    (`u100`/`v100`) entre sus entradas de entorno, que el motor carga por
    `--wind-field` (ERA5 6-horario; `wind_field.cpp:47-56`). El escenario ejercita la
    rama de viento de §4: desvío *upwind* del vuelo y **bloqueo** del avance cuando la
    componente de cola del viento alcanza la velocidad propia de vuelo. Es el `gate`
    que cierra la rama de viento (Paso 5).

### 14. Flujo de datos


**Un día de simulación (motor C++)**

```
                    ┌───────────────────────────────────────────────┐
  env NC ──────────▶│ ClimateEngine  (lluvia, T, planos estáticos)     │
                    └───────────────┬───────────────────────────────┘
                                    ▼
                    ┌───────────────────────────────────────────────┐
  habitat gpkg ───▶│ HabitatEngine ──▶ CoordinatorModel              │
                    │                   update_habitat_day()          │
                    │                   → z[], S[], K_cell[], dry[]   │
                    │                   to_dataframe() → CellState[] │
                    │                   (TODAS las celdas + eligible)│
                    └───────────────┬───────────────────────────────┘
                                    ▼
                    ┌───────────────────────────────────────────────┐
                    │ MosquitoSubmodel::advance_day                 │
                    │  1. banco acuático: desarrollo, mortalidad,    │
                    │     BH por celda, emergencia en la posición    │
                    │     de la madre                              │
                    │  2. fases: macro-paso + micro-integrador     │
                    │     · cascada sensorial (§4)                   │
                    │     · pick de presa individual + multipicadura │
                    │     · oviposición multi-sitio elegible       │
                    │     · enjambre: oferta/competencia            │
                    │  3. mortalidad, dispersión                    │
                    └───────────────┬───────────────────────────────┘
                                    ▼
        ┌───────────────────────────┼───────────────────────────┐
        ▼                           ▼                           ▼
  CellState[] → COG estado    HumanSoA → stats        BiteEvent → JSONL
  (bandas)      + sidecar      (agregados derivados)   (eventos)
```

**La decisión de picar (detalle)**

```
mosquito (pos_x, pos_y)
      │
      ▼
  ¿hay persona dentro de co2_activation_radius_m (100 m)?
      │ no ─▶ EXPLORACIÓN: paseo correlacionado (+ casting)
      │ sí
      ▼
  ¿hay persona dentro de olfactory_radius_m (30–70 m)?
      │ no ─▶ ACTIVACIÓN: orientarse al viento
      │ sí
      ▼
  ¿hay persona dentro de visual_radius_m (0,25–0,72 m)?
      │ no ─▶ RASTREO: anemotaxis optomotora (bloqueada si el viento > velocidad propia)
      │ sí
      ▼
  ¿la distancia ≤ terminal_radius_m (0,10–0,20 m)?
      │ no ─▶ APROXIMACIÓN VISUAL (sólo con el estado olfativo encendido)
      │ sí
      ▼
  ¿ATERRIZAJE? velocidad v < landing_speed_mm_s (50 mm/s) sostenida
     landing_speed_hold_s (3 s)?  ─ evaluable SÓLO dentro de la banda visual
     (≤ 0,72 m), donde dt = 0,04 s (25 Hz) ⇒ 75 muestras en 3 s
      │ no ─▶ sigue en APROXIMACIÓN (fuera de la banda visual el gate
      │        de velocidad NO es evaluable: no hay ticks)
      │ sí
      ▼
  CONTACTO: sortea probing_success_rate → sortea volumen → acumula
      │
      ├─ blood_volume_ul < objetivo ─▶ vuelve a HOST_SEEKING (misma noche)
      └─ blood_volume_ul ≥ objetivo ─▶ BLOOD_FED: arranca ciclo, ventana postprandial
```

### 15. Orden de integración

El orden de ejecución se revisa para priorizar **hembras y movimiento** junto con el
arnés de comprobación y la **visualización** de corridas, e introducir **humanos y
animales individuales** a lo largo del camino. Los identificadores de paso (0–11) se
**mantienen**: cambia el orden, no el contenido ni las referencias a E00–E18.
La fecundación sigue siendo automática hasta el Paso 8 (machos).

#### 15.0 — Decisiones cerradas por el autor (2a, 2b, 2c)

Prioridad declarada: **consistencia con la realidad sobre estabilidad de identificadores.**

| Paso | Decisión | Consecuencia en el plan |
|---|---|---|
| 2a | Personas en **`HumanSoA`** dentro de `human_state.hpp` (opción A). | Sin módulo nuevo. |
| 2a | **Posición:** uniforme dentro de la celda, asignada por semilla. | Sin edificios; `home_x/home_y` se sortean. |
| 2a | **Número de personas:** el de la rejilla real (i), repartido por celda. | **Se descarta** `SLOTS_PER_CELL` con slots vacíos. La fórmula `human_id = cell_id * SLOTS_PER_CELL + slot` (Paso 2, E08 y §15 de la tabla) queda **sin efecto** y se reemplaza por `human_id` único y determinista por semilla. |
| 2b | Ledger de eventos (`BiteEvent`) **sólo en modo escenario** (`--scenario`). | Las corridas de producción no cambian de tamaño. |
| 2c | Individuos de ganado **sin infección** (solo dilución), opción A. | No hay estado de infección en animales. |
| 2c | **Fuente:** ganado GLW por especie (`ingest/hosts.py:93`, `load_glw_livestock`), agregado sin distinguir especie en el ABM. | Especies: secundario; se trata como «animal» genérico. |
| 2c | **Wildlife no entra como individuos.** Es un índice de idoneidad en [0, 1] (`mal_commonlib` `wildlife.py`), no un recuento. | Convertirlo en individuos exige un factor de densidad sin dato; queda **fuera de 2c** hasta que haya uno. |
| Vis. | Visualización **dentro del motor C++**, un fotograma **por día** (sin fases), trazo = polilínea de las posiciones diarias, mosquito como círculo (§15.1). | §15.1 y §15.1.2 reescritos; V1 y el `xfail` por fase se sustituyen. |

| Orden | Paso | Entrega | Precondición |
|---|---|---|---|
| 1 | 0 | Arnés de escenarios (§13) **y** visualización de corridas (§15.1) | — |
| 2 | 1 | Línea base E01/E02 con la cadena actual | 1 |
| 3 | 2a *(nuevo)* | Humanos individuales con posición uniforme por semilla en la celda, número real por celda (§15.0) | 2 |
| 4 | 4 | Esquema de configuración completo en las cinco superficies (§12.1) | 3 |
| 5 | 5 | Cascada de percepción y movimiento de la hembra, micro-integrador de dos bandas | 4 |
| 6 | 2b *(nuevo)* | Ledger de eventos individual, solo en modo escenario (§15.0) | 5 |
| 7 | 3 | Sangre: multipicadura, umbral gonotrófico, pre-gravídica, ventana postprandial | 6 |
| 8 | 6 | Estado fisiológico y estación seca (`ovarian_stage`, `ARRESTED`) | 7 |
| 9 | 7 | Estado acuático por celda; emergencia en la posición de la madre | 8 |
| 10 | 9 | Elección del sitio de oviposición por el hábitat | 9 |
| 11 | 2c *(nuevo)* | Ganado individual sin infección, fuente GLW (§15.2) | 10 |
| 12 | 8 | Machos, sitios de enjambre, cupos y alarma | 11 |
| 13 | 10 | Modos definitivos y cobertura de los escenarios E00–E18 | 12 |
| 14 | 11 | Contratos 5.0 y consumidores (versionado, scorers, dataset) | 13 |

**Por qué este orden y no el del borrador anterior** (cada cambio tiene su causa):

*   **El Paso 4 sube antes del 3.** §12.4 exige que una clave esté en las cinco
    superficies antes de que el paso que la consume escriba código. El borrador
    anterior ponía el Paso 3 (que consume `blood_meal_target_ul` y
    `probing_success_rate`) **antes** del Paso 4: era una inconsistencia del propio
    plan, corregida aquí.
*   **El Paso 2 se parte en 2a y 2b.** E01 y E02 necesitan a la persona a 200 m y a
    2 000 m en metros: la parte posicional (2a) va antes de la cascada (5). El ledger
    de eventos (2b) lo necesitan E03, E08, E09 y el criterio de picaduras humanas del
    Nivel 6; va después de 5 y antes de 3, porque E03 cuenta eventos en el ledger.
*   **Los machos (Paso 8) se retrasan al final del bloque de hembras.** Mientras la
    fecundación sea automática, la cadena hembra → huevos → emergencia se puede medir
    sin machos. El retiro de `MATE_SEEKING` en el Paso 3 no depende del orden.
*   **El Paso 9 (sitio de oviposición) va después del 7** porque depende del registro
    por celda; sigue siendo parte del movimiento de la hembra.
*   **Los animales (2c) van tras el bloque de hembras**: sin la cascada y el ledger no
    hay forma de medir si la presencia de hospederos animales desplaza picaduras
    humanas. Ver §15.2.

#### 15.1 — Visualización de corridas (decidida)

**Decisión:** visualización en C++, dentro del motor. Python no entra en el camino de la
corrida.

*   **GIF:** se mantiene el GIF nativo (`viz.cpp`, `viz_tx.cpp`, `gif.h` ya vendorizado)
    y se le añade la vista de trayectorias y picaduras de la corrida de escenario.
*   **PNG estáticos** (mapa de un día, serie de 30 días): `stb_image_write.h` (un fichero,
    dominio público) en `include/mal_abm_fast/third_party/`, junto a `gif.h`. Si no se
    necesitan PNG, la serie sale en CSV.
*   **Trayectorias por hembra:** las dibuja el propio motor con las posiciones que ya
    tiene en memoria; el visualizador es el mismo C++ y lee las mismas variables. **No
    lee `_agents.parquet`**, de modo que la visualización **no añade** la dependencia de
    Apache Arrow (el Parquet sigue siendo un artefacto de análisis, §11).
*   **Granularidad:** **un fotograma por día simulado**, sin fases. El **trazo** de cada
    mosquito es la polilínea de sus posiciones diarias acumuladas; el mosquito se dibuja
    como círculo (hembra relleno, macho hueco). Las posiciones **por fase** del día no se
    visualizan.
*   **Consecuencia aceptada:** un escenario de 1 día (E00, E01) da un GIF de **1 fotograma**
    con la siembra y el resultado en la misma imagen. Lo que lo hace legible es V2/V3
    (marcadores en metros, anillos de la cascada y regla), no el número de fotogramas.

#### 15.1.1 — Qué cambia en el visualizador, paso a paso

Regla: cada paso del plan que cambia el comportamiento simulado añade su cambio de
visualización **en el mismo commit**. Lo que no está aquí no se redibuja.

| Paso | Cambio del modelo | Cambio del visualizador |
|---|---|---|
| 2a | Personas individuales | Pintar personas como puntos (no como densidad por celda). |
| 2b | Ledger de eventos | Picaduras como eventos puntuales (`BiteEvent`), no como cuadrado por celda. |
| 3 | Multipicadura y ciclo | Mostrar en la hembra el número de picaduras de la noche. |
| 5 | Cascada de movimiento | Trazo = polilínea de las posiciones diarias (fuente: el estado del motor en memoria, no `_agents.parquet`). |
| 6 | Arresto ovárico en seca | Estado `ARRESTED` con un tercer tratamiento visual (no un color nuevo de la paleta). |
| 7 | Emergencia en la posición de la madre | Las hembras nacen en el punto de la madre, no en el centro de la celda. |
| **Puesta de huevos** (cambio pedido) | Lote de huevos ∝ volumen de sangre (`eggs_per_ul`, Paso 3) y oviposición en el sitio del hábitat (Paso 9) | Marcar en el mapa el **punto de oviposición**, no la celda; la serie de huevos pasa a usar el lote real, no el de la celda. |
| 8 | Machos con sitio y enjambre | Enjambres como marcadores puntuales (`swarm_sites`). |

**Cambios de estilo pedidos por el autor** (aplicar en el primer commit de visualización):

*   **Transmisión (`viz_tx.cpp`):** las celdas **dejan de llevar color verde/rojo** (rampas
    `kHumanCellLow/High`, `kAnimalCellLow/High`, líneas 52–55). Sólo se dibujan: los
    **agentes**, las **picaduras** y los **agentes infectados**. Las celdas quedan en un
    gris neutro de fondo.
*   **Sexo:** las hembras son **disco relleno** y los machos **disco hueco**. Esto ya
    existe en `viz.cpp:1017-1045`; se mantiene y se verifica en el GIF de transmisión
    (`viz_tx.cpp` aún no lo distingue, línea 697-701: un solo símbolo para todos los
    agentes).
*   **Infectados:** anillo rojo sobre el agente (`kInfectious`), igual que en `viz.cpp:1050`.

**Decidido:** el punto de oviposición se dibuja como **cruz** (símbolo propio, distinto de
el disco de hembra y de macho).

#### 15.1.2 — Estado del visualizador y trabajo pendiente (medido el 2026-11-18)

**Estado hoy (medido, no supuesto).** Una corrida de escenario con `--enable-transmission`
escribe `<stem>_transmission.gif` (`viz_tx.cpp`) con **un fotograma por día simulado**:
E00 (1 día) produce un GIF de **1 diapositiva**, E01/E02 (3 días) uno de **3**. No hay
ninguna vista de escenario: las celdas siguen coloreadas por densidad (rampas
`kHumanCellLow/High`, `kAnimalCellLow/High`), todos los agentes llevan el mismo símbolo y
las picaduras salen como cuadrado por celda. Por eso un GIF de escenario **no sirve hoy
para confirmar ni refutar** ninguna expectativa: no se ve a la persona sembrada, ni la
distancia, ni la trayectoria. El test `test_baseline_gif_has_one_frame_per_day` fija este
estado, y **sigue siendo correcto**: la unidad del GIF es el día (decisión del autor,
§15.1). `test_target_gif_has_one_frame_per_phase` (`xfail` estricto, objetivo
≥ `days × 4`) **queda sin objeto** y se **elimina** en el commit de V5/V6; el objetivo
que lo sustituye es V1 (trazo) y V6 (humo).

**Cambios pendientes del visualizador** (además de la tabla de §15.1.1, que sigue
vigente; cada uno va en el commit del paso que lo hace posible, no antes):

| Id | Cambio | Paso que lo habilita | Fichero |
|---|---|---|---|
| V0 | El arnés pide el GIF de forma explícita (`--gif`) sólo en modo escenario y lo archiva junto a `<id>.observed.json`; hoy sale como efecto lateral de `enable_transmission`. | 0 (hecho en el arnés; falta el flag explícito) | `harness.py` |
| V1 | **Trazo del mosquito**: polilínea de sus posiciones diarias acumuladas, dibujada por el motor desde su estado en memoria; el mosquito sigue siendo un círculo (hembra relleno, macho hueco). **Sin fotogramas por fase**: un fotograma por día. Mínimo comprobable: `n_frames == days` y la polilínea del fotograma `d` tiene `d+1` vértices. | 5 (antes la hembra no sale de su celda y el trazo sería un punto) | `viz_tx.cpp`, `engine.cpp` |
| V2 | **Marcadores de escenario**: persona como punto en su posición en metros; ganado; cohortes acuáticas / criaderos; sitios de enjambre. Hoy el visualizador sólo conoce celdas. | 2a (personas), 2c (ganado), 7 (criaderos), 8 (enjambres) | `viz_tx.cpp` |
| V3 | **Anillos de la cascada** alrededor de la hembra (activación, olfativa, visual: radios de §4) y regla de escala en metros: es lo que permite ver *a ojo* que a 200 m no hay contacto (E01) y a 2 000 m tampoco (E02). | 5 | `viz_tx.cpp` |
| V4 | **Rótulo de escenario**: id, día, modo (`gate`/`report`) y el valor observado frente al esperado en el pie del fotograma (la banda del `catalog.yaml`). | 5 (primera expectativa en forma cerrada) | `viz_tx.cpp`, `harness.py` |
| V5 | Quitar las rampas verde/rojo de celdas (decisión del autor, §15.1) y distinguir sexo (disco relleno/hueco) también en `viz_tx.cpp:697-701`. | 0/2a, primer commit de visualización | `viz_tx.cpp` |
| V6 | Prueba de humo del GIF en CI: abrirlo y comprobar `n_frames == days` y que no es uniforme (no todo gris). Sustituye al `xfail` eliminado. | con V1 | `test_scenarios.py` |

**Qué NO está hecho y no debe darse por hecho.** Ninguna de V0–V6 está implementada. Los
GIF de los 19 escenarios existen (los escribe el arnés en `runs/_check_current/<id>/`)
pero son los del visualizador actual; documentarlos como evidencia de comportamiento
sería un error.

#### 15.2 — Ganado individual sin infección (Paso 2c)

*   **Alcance:** animales como hospederos individuales con posición en metros, sin
    estado de infección y sin especie (decisión §15.0).
*   **Fuente:** los recuentos de ganado que ya produce `ingest/hosts.py` desde GLW
    (`livestock_total` y la agregación por especie, que se suma). El escenario
    `LivestockSpec` (§13.2) sólo sirve para pruebas sintéticas.
*   **Fuera de alcance:** *wildlife* (`mal_commonlib` `wildlife.py`), porque es un índice
    de idoneidad y no un recuento.

**Escenario que cierra cada paso.** Cada paso tiene **su** escenario, y el criterio de
aceptación del paso es: **su escenario pasa**. El cálculo a mano va pre-registrado
antes de escribir el código. Esta tabla es la **referencia autoritativa** paso ↔
escenario ↔ modo ↔ criterio: el **Nivel 4** del plan de verificación la cita, y el
Apéndice A define cada escenario. Un escenario `report` **no cierra** ningún paso: su
criterio es una banda que se revisa, no un fallo de CI.

| Paso | Escenario | Modo | Cálculo a mano pre-registrado (criterio del paso) |
|---|---|---|---|
| 0 | E00 | `gate` | 1 mosquito sembrado, 1 día: posición, sexo y estado; y el manifiesto declara **una sola** clave `scenario:E00` |
| 1 | E01 + E02 | `gate` + `report` | E01: 1 hembra, 1 persona a 200 m, 0 criaderos ⇒ **0 comidas** (la distancia no permite el contacto) y entrada en inanición el día 3 — es el **baseline** de la cadena actual, no una expectativa; E02: banda de distancia **derivada del modelo** (`report`) |
| 2 | E08 + E09 | `gate` | E08: `human_id = cell_id * SLOTS_PER_CELL + slot` y nº de personas por celda, verificables **por construcción** (unicidad y estabilidad), sin "celda ganadora"; E09: una picadura infecciosa infecta **como máximo** a la persona picada |
| 3 | E03, E04, E05, E06, E11 | `gate` | E03: nº de eventos por noche en el ledger (multipicadura) = N·p·P(contacto); E04: comida parcial ⇒ el ciclo **no** arranca; E05: umbral alcanzado ⇒ lote de huevos ∝ volumen acumulado (`eggs_per_ul` = 223); E06: `first_cycle_target_ul` (0,8 µL) exige dos comidas; E11: la ventana postprandial no se reabre antes de 12 h |
| 4 | **paridad de configuración** (E01 se cierra en el Paso 5) | `gate` | cada clave nueva devuelve el valor del YAML en las **cinco** superficies (pydantic, `struct` C++, enlace por nombre, volcado, golden). El Paso 4 no escribe expectativas: su criterio es la **paridad de las cinco superficies**, que es un test, no un escenario |
| 5 | E01 + E02 + E10 + **E18** | `gate` + `report` | E01 (`gate`): a 200 m la hembra **no** contacta —la cascada respeta su banda de activación (100 m)—; E18 (`gate`): con campo de viento cargado, el vuelo se desvía *upwind* y el vuelo nocturno se bloquea; E02 (`report`): banda de distancia **derivada del modelo** (≤ `daily_move_capacity_m` de longitud de trayectoria; desplazamiento neto por noche ≤ 2 × `exploration_range_m`); E10 (`report`): sensibilidad de los tres radios de la cascada |
| 6 | E12 | `gate` | fracción de hembras alimentadas sin pasar de estadio 2 = 19,23–34,85 % (*coluzzii*) |
| 7 | E07 (aserción A) | `gate` | la emergencia ocurre **en la posición de la madre**, no en el centro de la celda |
| 8 | E14 + E15 | `gate` | E14: los machos asignados no entran al enjambre antes de su ventana y se emite la alarma `hembras_sin_inseminar`; E15: el *swarm killing* deja el sitio sin oferta. **E13** (`report`) y **E16** (`report`) se revisan como bandas, no cierran el paso |
| 9 | E07 (aserción B) | `gate` | el sitio de oviposición es el del **hábitat**, no el del hospedero (multi-sitio, señal por tipo de hábitat). E07 lleva **dos** aserciones: la de emergencia (Paso 7) y la de elección de sitio (Paso 9) |
| 10 | E17 | `gate` | `cupos(s)` baja de forma proporcional a los machos estériles asignados y sube la fracción de hembras sin inseminar. El **versionado** (una sola banda, contrato 5.0) es del **Paso 11**; aquí sólo el **determinismo**: dos corridas idénticas byte a byte (Nivel 5) |
| 11 | **Niveles 5/6** (sin escenario propio: es un contrato y una regresión de la cadena) | `gate` | el COG de estado publica **una sola** banda con `contract_version` = "5.0" y **no** se publica 4.1; D1 y D8 se adaptan al plano de hábitat por celda; la corrida de Accra registra **picaduras humanas > 0** y la población de vectores no colapsa (§10, Nivel 6) |

## Revisión de la evidencia (§16 — investigación de apoyo)

Esta sección sale de "Technical Plan" y sube a primer nivel: es **evidencia de
apoyo**, no arquitectura, y así lo declara su propio contenido. Conserva su número
(§16) para que las remisiones del documento sigan siendo válidas.

Tres revisiones en paralelo se hicieron sobre la evidencia, con subagentes independientes, antes
de cerrar el Technical Plan. Sus resultados cambian tres cosas del diseño.

### 16.1 — Filopatria natal: el campo `home_x/home_y` no tiene base

Búsqueda en el índice de texto completo de Europe PMC con `"philopatry" AND (Anopheles
OR "malaria vector")`: 30 resultados, **ninguno** sobre *Anopheles*. La única mención de
la palabra en la literatura de vectores de malaria es **negativa**: Thomas et al. 2013
derivan sus curvas de dispersión *"assuming no philopatry"*.

Lo que la literatura sí documenta, y que **no** es filopatria:

| Mecanismo | Valor | Especie | Tier |
|---|---|---|---|
| Preferencia olfativa por el habitat natal | 31,6–37,5 % de los huevos en agua natal (p = 0,001–0,032); **nula** en agua de laboratorio | *A. gambiae* s.s., *A. arabiensis* | [P] |
| Permanencia post-emergencia | **< 60 %** de los adultos se mueven > 50 m del sitio larvario | *A. arabiensis* | [P] |
| Skip oviposition | **49,2 %** de hembras usan **2–4** criaderos | *A. arabiensis* | [P] |
| Respuesta a larvas conspecíficas | larvas **tempranas +**, tardías **−**, por vía olfativa | ***A. coluzzii*** | **[M]** |
| Fidelidad a la zona de liberación | 70 % de recapturados en otra zona | *A. gambiae* s.l. (89,7 % *coluzzii*) | [M] |
| Estructura genética por distancia (IBD) | detectada; la **distancia**, no el habitat, estructura | ***A. coluzzii***, Ghana | [M] |

**Consecuencias en el plan**: (i) el campo `home_x/home_y` **se elimina** (§3); (ii) la
permanencia a < 50 m es la **tensión declarada** del radio de exploración, que el
plan resuelve priorizando la **alcanzabilidad de la cascada**
(`exploration_range_m` = 100 m, banda 100–200 m, §4);
(iii) la preferencia natal entra como **sesgo por tipo de habitat**, no como distancia
(§9); (iv) el skip oviposition obliga a que la oviposición sea **multi-sitio** (§9).

### 16.2 — Capa macho: el enjambre no es un colectivo emergente

El ABM validado con datos de *coluzzii* (Cribellier et al. 2026) reproduce el enjambre
con tres reglas mínimas —atracción al marcador visual, alineación al eje del atardecer,
evitación de colisión por debajo de 2,5 longitudes corporales— **ninguna de las cuales
es una regla de boids hacia los conspecificos**. La geometría (cono de 0,67 m, σ de
4–10 cm, separación al vecino de 0,11 m) es tres órdenes de magnitud por debajo de la
celda de 1 km.

**Consecuencias en el plan**: (i) la justificación de la decisión sobre la capa macho
(la **opción 2 — machos individuales con sitio de enjambre asignado al nacer; el enjambre
es el agregado por sitio**) cambia de
"conveniencia" a **suficiencia por construcción** (§8); (ii) el "número libre" de
marcadores se sustituye por un **campo de marcadores estático y persistente** calibrado
a valores publicados (§8); (iii) la supervivencia del macho se separa (0,773 ± 0,094);
(iv) el macho recibe su **propio presupuesto de movimiento**; (v) el modelo **sí**
puede simular *swarm killing* (matar los machos asignados a un marcador) y **sí**
representa el **efecto de SIT/IIT sobre los cupos por sitio** (machos estériles
asignados a los mismos sitios, compitiendo por los mismos cupos; el lado femenino
requiere la capa de individuos humanos del paso 2), pero **no simula** la competencia
*intra-enjambre* entre machos estériles individuales; (vi) la granularidad individual
del macho se
justifica por la **fidelidad al sitio** (un macho liberado seguía en un sitio de
enjambre 8 días después: Kaiser et al. 2021) y no por la dinámica del enjambre, que
queda excluida (§8.3, A18).

### 16.3 — Resolución temporal: los ticks de 1 s eran irresolubles

Con la velocidad medida (0,225–0,45 m/s) y el radio terminal medido (0,10–0,20 m, §4), un
paso de 1 s avanza 22–45 cm: **mayor que el radio terminal entero**. El evento más
rápido medido (giro en el punto más cercano) dura 0,08 s. Las frecuencias de muestreo
de los experimentos van de 25 a 90 fps y el precedente de modelo usa Δt = 0,02 s.

**Consecuencias en el plan**: el micro-integrador pasa de "1 s" a **dos bandas
adaptativas** (0,04 s terminal —25 Hz, Nyquist estricto sobre el evento de giro de
0,08 s— y 0,25 s olfativa), el macro-paso se acota por un
**presupuesto de tiempo de vuelo dirigido**, derivado de la capacidad de movimiento
diaria `daily_move_capacity_m` (§5), en vez de por la duración de la
fase, y el "[EP] ≈2 s" de memoria olfativa **se elimina** por no tener fuente (§5).

**New papers**: 25 extractos nuevos en `papers/anopheles-dynamics/` (filopatria y
oviposición: 9; capa macho y enjambre: 14; escala temporal: 2), con las filas 89–113
de `papers/REFERENCES.md` añadidas.

## Alternatives Considered

Las opciones siguientes son las que la versión anterior del documento ya evaluó (con su aritmética), más las que
surgen de las decisiones de arquitectura del Technical Plan. Cada una se documenta con
el motivo del rechazo, para que el implementador no las reabra sin evidencia nueva.

### A1 — Base temporal del movimiento: integrador continuo por eventos

*   **Mecanismo**: cada mosquito se mueve en tiempo continuo; el motor calcula el
    siguiente evento (contacto con un filamento de olor, cambio de régimen, viento)
    y salta directamente a él.
*   **Ventajas**: fidelidad máxima; representa la estructura filamentosa de la pluma sin
    aproximarla.
*   **Inconvenientes**: es el cambio más invasivo; el motor no tiene hoy reloj de fase
    ni sub-pasos (el día es un único `for p < PHASE_WEIGHT_COUNT`), y un planificador de
    eventos por mosquito rompe el determinismo del consumo de RNG (el orden de
    resolución depende de prioridades).
*   **Motivo del rechazo**: coste de implementación y riesgo de determinismo frente a
    un beneficio que sólo se materializa en la pluma, que la propia literatura describe
    como intermitente y que el macro-paso ya aproxima con el estado "rastreo perdido".

### A2 — Base temporal del movimiento: integrador grueso + kernel de encuentro

*   **Mecanismo**: se conserva un paso diario y la probabilidad de encontrar un
    hospedero se modela como un kernel de encuentro (función de la distancia y de la
    densidad).
*   **Ventajas**: el más barato; no requiere posiciones continuas ni sub-pasos.
*   **Inconvenientes**: **anula el objetivo del apartado 1 de la versión anterior del documento** (que la
    unidad de razonamiento pase del mosquito individual a la trayectoria individual): sin trayectoria
    individual no hay quién-picó-a-quién, ni cadena mosquito → persona → mosquito.
*   **Motivo del rechazo**: contradice el objetivo declarado del cambio. Es la opción
    que el modelo actual ya implementa de facto (el campo de atracción por celda es un
    kernel de encuentro), y su debilidad es precisamente lo que motivó el rediseño.

### A3 — Movimiento: mantener el campo de atracción por celda con decaimiento exponencial

*   **Mecanismo**: se conserva `A_jk = host_count_jk × exp(-dist_j / scale)` por celda,
    ajustando `scale` y `radius`.
*   **Ventajas**: el cambio más pequeño; toca una constante.
*   **Inconvenientes**: incompatible con la estructura medida de la pluma (intermitente
    y filamentosa: el 61,4 % ± 3,9 % del tiempo de vuelo de las hembras que aterrizan
    queda fuera de los límites teóricos de la pluma) y con los radios reales
    (100 m / 30–70 m / 0,25–0,72 m / 0,10–0,20 m, frente a 1 500 m y 300 m).
*   **Motivo del rechazo**: el propio modelo espacial de referencia (Cummins 2012)
    advierte contra trayectorias "artificialmente directas". Un ajuste de constante no
    corrige un mecanismo equivocado.

### A4 — Movimiento: el viento como término del vector diario

*   **Mecanismo**: el viento de cada día se suma al desplazamiento del mosquito.
*   **Ventajas**: sin proceso ni estado extra.
*   **Inconvenientes**: mezcla dos escalas: el viento de la noche es 5,1 m/s (p10–p90
    2,4–8,0) a 40–290 m de altura, con desplazamientos de 30–120 km en 2–9 h de vuelo
    pasivo; el movimiento local es de cientos de metros por día.
*   **Motivo del rechazo**: decisión W = (a), el viento es un **evento aparte** a escala
    de 100 km con sus propias condiciones de altitud, duración y supervivencia. El
    canal `dispersal.wind_flight_hours` / `wind_survival` se conserva y se aísla del
    radio de percepción.

### A5 — Capa humana: mantener los compartimentos agregados por celda

*   **Mecanismo**: `S_H`/`I_H`/… siguen siendo el estado; el mosquito "pica" a una
    celda y el resultado se reparte por celda.
*   **Ventajas**: coste trivial; toda la capa de transmisión y el COG siguen funcionando.
*   **Inconvenientes**: es exactamente el motivo por el que no hay malaria observable:
    el ledger no puede reconstruir quién fue picado ni por quién, y la transmisión
    vector→humano se aplica a una densidad, no a una persona.
*   **Motivo del rechazo**: decisión D2 = (a). Los compartimentos pasan a **estadísticas
    derivadas**; se conservan como salida, no como estado.

### A6 — Capa humana: agentes representativos con pesos

*   **Mecanismo**: un subconjunto de la población representa a un grupo, con un peso
    por agente para las estadísticas.
*   **Ventajas**: coste acotado a escala de país sin cambiar el motor.
*   **Inconvenientes**: el `human_id` deja de corresponder a una persona; el contrato de
    observación (el ledger de picaduras con identificadores) miente sobre su unidad.
*   **Motivo del rechazo**: se aplaza, no se evita: es exactamente la optimización que
    el plan deja para después (Non-Goal N3) **precisamente porque** el `human_id`
    determinista (`cell_id * SLOTS_PER_CELL + slot`) la hace posible más adelante sin romper el
    contrato.

### A7 — Movimiento humano por fases (matrices OD de gravedad)

*   **Mecanismo**: `beta_day` 0,05 / `beta_night` 0,5 / `max_distance_km` 50, con
    matrices de origen-destino.
*   **Ventajas**: reproduce el contraste día/noche en la disponibilidad de hospederos.
*   **Inconvenientes**: es una consecuecia de la individualización, no un requisito de
    ella; los CSR y `MobilitySchedule` quedan como código muerto a eliminar; y la
    literatura de la movida humana en el contexto de la malaria es más pobre que la de
    la respuesta del vector.
*   **Motivo del rechazo**: Non-Goal N2. El modelo de datos conserva `home` y `current`
    (iguales ahora) para que la movilidad individual sea activable más adelante sin
    romper el contrato.

### A8 — Banda 1 del COG de estado: afiliación reproductiva

*   **Mecanismo**: el adulto se cuenta en la celda de su cohorte de origen; las dos
    bandas responden a preguntas distintas ("¿dónde se cría?" frente a "¿dónde está?").
*   **Ventajas**: dos canales distintos y ambos útiles; conserva un canal que hoy
    alimenta el surrogate.
*   **Inconvenientes**: reintroduce la afiliación de parche en el lado de adultos, que
    es justo lo que la decisión D4 (b) elimina; y obliga a un bump de contrato mayor.
*   **Motivo del rechazo**: decisión D3 = (c) ("colapso honesto"): con la semántica de
    posición, las dos bandas serían idénticas y publicar una banda con dos nombres
    distintos es peor que publicar una banda con su nombre correcto. La información
    "dónde se cría" no se pierde: queda en el sidecar acuático y en el artefacto
    individual.

### A9 — Banda 1 del COG de estado: presión de búsqueda de hospedero

*   **Mecanismo**: la banda 1 cuenta hembras en `TENERAL`/`HOST_SEEKING` por celda.
*   **Ventajas**: es el canal que más predice el paso siguiente.
*   **Inconvenientes**: el nombre actual (`adult_patch_count`) describiría otra cosa, y
    reintroduce la semántica que el contrato v4.0 retiró a propósito.
*   **Motivo del rechazo**: contradice el propósito declarado de v4.0; y el surrogate
    tendrá que reentrenarse de todos modos (el surrogate se entrena con bandas
    normalizadas ≤ 3.0 y el contrato vigente es la v4.0, que retiró la normalización:
    §10, N4), de modo que no hay ventaja
    de compatibilidad que defender.

### A10 — Estado acuático: la celda como clave y la posición de la madre como payload

*   **Mecanismo**: la cohorte conserva `cell_id` como clave de agregación y guarda el
    `(x, y)` de la madre; el resto del comportamiento acuático no cambia.
*   **Ventajas**: coste cero; la dependencia de densidad sigue funcionando sin tocar
    nada.
*   **Inconvenientes**: la ruta de error "no PatchState for today"
    (`aquatic_cohort_bank.cpp:308`) sigue viva; "patch" sigue significando "celda
    candidata" mientras el lado de adultos ya no tiene parche (dos vocabularios
    conviviendo); y el gpkg conserva un papel que el registro por celda vuelve
    redundante.
*   **Motivo del rechazo**: decisión D4 = (b). Con (b) desaparece la ruta de error por
    construcción, la doble fuente de potencial se unifica, y el registro por celda es
    la precondición de la competencia sub-celda. El coste —bump del contrato de hábitat
    3.0 → 4.0 y renombrado en toda la cadena— se paga en el mismo PR donde ya se
    mueven el COG de estado, la capa humana y el ledger.

### A11 — Estado acuático: servicio de consulta posición → celda

*   **Mecanismo**: arrays de S/K/temperatura/salinidad/`dry_days` para todas las
    celdas, precomputados por día y expuestos como una función.
*   **Ventajas**: barato; un único contrato de hábitat; "patch" puede quedar como vista
    derivada.
*   **Inconvenientes**: si se escriben las dos vistas pueden divergir: hay que elegir
    una como derivada y generarla.
*   **Motivo del rechazo**: no es incompatible con D4 = (b) —es su implementación
    interna—, pero por sí solo no resuelve el problema de vocabulario ni el de la doble
    fuente de potencial. Se adopta como **parte** de (b): el registro por celda es la
    vista Canónica y "patch" es el filtro booleano.

### A12 — Capacidad de enjambre: saturación por disponibilidad de machos (R1)

*   **Mecanismo**: `p = min(1, p_mate_male_fraction × machos_alcance)`, con el tope de 3
    hembras por
    macho aplicado después como restricción.
*   **Ventajas**: la más simple; con 100 machos y 100 hembras da `p = 1`.
*   **Inconvenientes**: **contradice** el tope de 3 hembras por macho y noche
    (Ekechukwu & Tripet 2019): con 100 hembras inseminadas harían falta 14 hembras por
    macho. Y las hembras sin inseminar sólo aparecerían por ausencia de machos, no por
    densidad ⇒ la alarma de enjambre no discrimina nada.
*   **Motivo del rechazo**: decisión D5 = (a) ("cupos + carrera"): es la única lectura
    coherente con **las dos** mediciones, y hace que la fracción de hembras sin
    inseminar sea una salida del modelo en vez de un número fijado a mano.

### A13 — Capacidad de enjambre: reparto determinista de cupos

*   **Mecanismo**: los cupos se asignan por orden (por celda, por distancia) en vez de
    por carrera exponencial.
*   **Ventajas**: sin aleatoriedad extra; tests más fáciles.
*   **Inconvenientes**: introduce un orden artificial —"quién llega primero"— que hay
    que fijar en la especificación para que sea reproducible, y que no corresponde a
    ningún proceso biológico.
*   **Motivo del rechazo**: la expresión exponencial es la forma canónica de un
    proceso de cupos con competencia y no requiere un orden externo. La versión
    determinista se acepta sólo si el test necesita reproducibilidad bit a bit de un
    resultado que ya es reproducible por semilla.

### A14 — Capa macho: el enjambre como agregado por celda, sin machos individuales

*   **Mecanismo**: el enjambre se mantiene como un **contador agregado por celda**
    (nº de machos presentes en la ventana nocturna); no hay sitios de enjambre, ni
    marcadores, ni cupos por sitio: el apareamiento se decide por celda.
*   **Ventajas**: no exige estado nuevo y el coste es el de la cadena actual.
*   **Inconvenientes**: (i) **tira información que ya existe**: el SoA **ya** guarda
    los machos individualmente (`mosquito_state.hpp:37`) y el agregado por celda de 1 km
    mezcla machos que no pueden estar en el mismo sitio (§8.2); (ii) **no puede
    representar *swarm killing*** (no hay marcadores discretos que eliminar) ni el
    **efecto de SIT/IIT sobre los cupos por sitio** (no hay sitio al que asignar los
    machos estériles); (iii) la alarma de "hembras sin inseminar" se vuelve un
    agregado por celda y deja de discriminar el campo de enjambres.
*   **Motivo del rechazo**: la granularidad individual del macho ya está disponible en
    el motor y la fidelidad al sitio está medida (un macho liberado seguía en un sitio
    de enjambre 8 días después: Kaiser et al. 2021) **[P]**; el agregado por celda no
    compra nada a cambio y bloquea las dos intervenciones que sí se pueden representar.
    (Esta alternativa es **distinta** de A18: allí el enjambre se simula con vuelo por
    macho; aquí no hay ni sitio ni vuelo.)

### A15 — Edad de la hembra: `age_days` como variable de estado

*   **Mecanismo**: la edad cronológica en días pasa a ser estado primario, con
    mortalidad, fecundidad y respuesta al hospedero dependientes de ella.
*   **Ventajas**: permite expresar la pre-gravidez, la oviposición retrasada y la
    composición de estados abdominales que miden las capturas aéreas.
*   **Inconvenientes**: **no hay ninguna medición publicada** del efecto del número de
    ciclos gonotróficos sobre supervivencia, fecundidad, antropofilia o duración del
    ciclo ⇒ sería un engineering prior, justo lo que la decisión C = (a) prohíbe.
*   **Motivo del rechazo**: decisión E = (d) (híbrido): el ciclo gonotrófico es el reloj
    maestro y de él se derivan `ovarian_stage` y `gonotrophic_arrest`; `age_days` queda
    como campo de diagnóstico.

### A16 — Lote de huevos: `binomial(240, p)` con recorte

*   **Mecanismo**: el lote se sortea de una binomial con la temperatura como
    modificador y se recorta a [30, 170].
*   **Ventajas**: encaja en la invariante de configuración existente
    (`0 < min <= mean <= max <= n`).
*   **Inconvenientes**: la medida de *coluzzii* es 111,67 ± 5,36 huevos por puesta
    (susceptible) y 93,33 ± 10,77 (resistente); el `binomial(240, …)` no tiene
    respaldo, y la invariante impide representar un lote **proporcional al volumen de
    sangre** (MBITES).
*   **Motivo del rechazo**: la decisión C = (a) exige la cifra medida, y la
    proporcionalidad al volumen es el mecanismo documentado (Wu et al. 2020). El bloque
    de configuración se **redefine** en vez de ajustarse.

### A17 — Movimiento: mantener el calor como término diario del vector

*   **Mecanismo**: el calor modula la velocidad de vuelo y la supervivencia con la
    temperatura del día.
*   **Ventajas**: es lo que el modelo ya hace.
*   **Inconvenientes**: no es lo que la evidencia documenta. Lo que la literatura
    documenta es (i) la restricción del avance contra el viento cuando la velocidad
    del viento ambiente supera la velocidad propia, y (ii) la búsqueda de presa en
    función de la pluma y de la distancia.
*   **Motivo del rechazo**: la temperatura se conserva como determinante del
    desarrollo acuático y de la supervivencia (medido), pero **no** como determinante de
    la ley de movimiento (no medido). La velocidad de vuelo por especie es un valor
    medido, no una curva térmica.

### A18 — Capa macho: machos como individuos con vuelo simulado al enjambre (opción 3, descartada)

*   **Mecanismo**: cada macho es un agente que, en la ventana de enjambre, vuela hacia
    su sitio de enjambre sobre una rejilla subcelular (≈10 m) aplicando las reglas
    mínimas del ABM validado con *coluzzii*: atracción al marcador visual, alineación
    al eje del atardecer y evitación de colisión por debajo de 2,5 longitudes
    corporales (Cribellier et al. 2026), a 0,50 ± 0,00 m/s (Poda et al. 2024).
*   **Ventajas**: es la única alternativa que reproduce el enjambre como **objeto
    espacial** — cono elíptico, centro a 0,67 m sobre el marcador, σ 4–10 cm, distancia
    al vecino 0,11 m (Poda et al. 2024) — y reproduce el tiempo de entrada
    (46 ± 8 s). Deja además abierta la segregación de enjambres entre especies
    (χ² = 56,92; Diabaté et al. 2009), hoy ausente del modelo.
*   **Inconvenientes**: (i) el enjambre **no discrimina la transmisión**: la hembra
    responde al **sitio**, no a la estructura interna (Charlwood 2023, sólo abstract), y
    asiste con tasa baja (10,33 %, cota inferior de la probabilidad de inseminación por
    hembra); la oferta de cupos por sitio es lo que limita la
    reproducción, y se obtiene sin simular la dinámica interna. (ii) **No hay dato
    publicado** que parametrice la atracción ni la fidelidad al sitio ⇒ el resultado
    dependería de parámetros inventados, contra la regla del proyecto (todo número con
    fila en `papers/REFERENCES.md`). (iii) La simulación de vuelo por macho y por noche
    multiplica el coste de la fase nocturna; **el argumento del coste y el del "reloj
    diel" no discriminan por sí solos** (la opción elegida recorre la misma población y
    usa la misma ventana nocturna): lo que discrimina son (i) y (ii).
*   **Motivo del rechazo**: el objetivo del plan es la transmisión espacial y la
    trazabilidad individual, no la mecánica intra-enjambre; **la salida que el modelo
    necesita —la oferta de cupos por sitio y noche— es idéntica en las dos opciones**,
    y el precio es inventar la parametrización de la atracción y la fidelidad (regla 4
    del proyecto: todo número con fila en `papers/REFERENCES.md`). La comparación
    completa, con la tabla de criterios, está en §8.3. La alternativa **queda abierta**:
    la opción elegida (§8) deja los machos como individuos con un sitio asignado, de
    modo que una capa de vuelo se puede añadir encima sin tocar el resto del diseño.

## Non-Functional Requirements

*   **NFR-1 — Determinismo bit a bit.** Una corrida con la misma semilla maestra y el
    mismo manifiesto produce el mismo resultado, byte a byte, en todas las salidas
    (COG, sidecars, JSONL, parquet). Los sub-streams de todos los subsistemas —incluidos
    el banco acuático y el micro-integrador, que hoy no derivan de la semilla maestra—
    se derivan de ella.
*   **NFR-2 — El motor sigue siendo C++ de un solo hilo por rollout.** La lógica
    vectorial (SoA) se conserva; la individualización humana añade un segundo SoA, no
    un motor de agentes genéricos.
*   **NFR-3 — Coste de una corrida a escala de AOI real.** El micro-integrador sólo
    corre dentro de la banda de percepción. Objetivo: **≤ 10 min para 30 días en
    Accra** (AOI de 61×56; la referencia actual es la corrida de 30 días que hoy tarda
    ~2 min); el escenario sintético 10×10 debe tardar **< 10 s**.
    *   **Presupuesto por mosquito-día**: **0,16–16 s/día** (§5, tabla de coste), para
        `N_dentro` ≈ 4,5–45 sobre un AOI de 3 416 km².
    *   **Criterio de abandono**: si **un día** de la corrida supera **60 s**, se
        **acorta la corrida** o se **reduce `N_dentro`** (§5). El presupuesto por
        mosquito-día es el tope de diseño; los 60 s por día son el tope de operación.
*   **NFR-4 — Coste del estado humano individual.** **40 B por persona** [EP]
    (desglose en §2; el **relleno (padding) al múltiplo de 8 B es una convención del
    plan**, no una medición de plataforma) ⇒ **2–4 GB por corrida** a escala de país,
    es decir con **50–100 M de personas** [EP]. El valor por celda del campo
    `human_total` (`mal-core/src/mal_core/ingest/hosts.py:87`) está en **personas por
    celda** (§2). Aceptado en esta iteración (N3); documentado en el    sidecar.
*   **NFR-5 — Trazabilidad de cada número.** Ningún parámetro del motor existe sin una
    entrada en `model_constants.yaml` con su valor, su unidad, su tier de evidencia
    ([M]/[P]/[EP]/[NR]) y su referencia. El volcado de configuración (`config_dump.cpp`)
    incluye la clave nueva.
*   **NFR-6 — Nada se "limpia" sin contrato.** Todo cambio de forma de salida va
    acompañado de bump de versión de contrato y de una regla de rechazo explícita en
    los lectores: un lector que ve una versión o un nombre de banda desconocidos
    **falla** (§10). No hay migraciones silenciosas.
*   **NFR-7 — Los artefactos no se acumulan.** El prune por **clase de fichero**
    (nunca por directorio) se mantiene: el ledger de picaduras y los parquet
    individuales son **la** información que no se puede regenerar, y por eso se
    declaran como "conservar" en el prune.
*   **NFR-8 — Compatibilidad Python/C++.** Toda constante nueva existe en las
    **cinco** superficies (YAML, modelo pydantic, `struct` C++, enlace por nombre en
    `config.cc` y volcado en `config_dump.cpp`; §12.1) y hay un test de paridad de
    configuración. Un cambio de esquema que toque sólo una copia falla el CI.
*   **NFR-9 — Los escenarios son parte del CI.** El arnés se ejecuta en cada commit
    con paso 0; los escenarios con forma cerrada fallan el CI, los demás escriben su
    banda de tolerancia para revisión.

--------------------------------------------------------------------------------

## Additional Resources

*   *(el documento de diseño intermedio y su informe de revisión Goldfish son
    artefactos temporales del flujo de diseño: este plan es autocontenido y no depende
    de ellos).*
*   `papers/anopheles-dynamics/` — 84 extractos de la literatura citada.
*   `papers/REFERENCES.md` — filas 32–88 (rondas de fisiología de la sangre, cascada
    sensorial, machos y estado fisiológico).
*   `docs/plans/in-process/odd-fixes/` — el trabajo **pendiente** que este cambio no
    cierra, reagrupado por tema en nueve documentos (2026-11-17): 01 habitat y
    entorno, 02 fase acuática, 03 comportamiento del vector, 04 semántica de
    transmisión, 05 parámetros y calibración, 06 observación y salida, 07 higiene del
    motor, 08 preguntas estacionadas, 09 documentación y `papers/`. Cada documento
    contiene sólo lo **no realizado**; lo cubierto por este plan (los antiguos packs
    02 individualización y 09 semilla maestra, y parte de 03, 04, 05, 08, 10 y 13)
    no se repite allí.
*   `mal-core/src/mal_core/abm/include/mal_abm_fast/wire.hpp` — invariantes del contrato
    de estado (nombres de banda, `CONTRACT_VERSION`, `STATE_BAND_NAMES`).
*   `mal-core/src/mal_core/download/manifest.py` — contrato de datos y manifiesto.

## Future Improvements

*   **Movilidad humana por fases**: activar `current` distinto de `home` con matrices OD
    de gravedad, una vez que el contrato de observación soporte `human_id` estable.
*   **Optimización del estado humano individual**: materializar sólo a los humanos que un
    mosquito pica, o muestreo estratificado con pesos, sin romper el `human_id`
    determinista.
*   **Competencia acuática sub-celda**: el registro por celda (D4 = b) es la precondición
    para, si algún día se quiere, que dos hembras a 50 m dentro de la misma celda no
    compitan como un único pool.
*   **Estructura fina del enjambre**: modelar machos como individuos sólo se justifica si
    aparece una intervención que dependa de ella (rooteo de enjambres, SIT/GM).
*   **Perfil numérico de picadura con opción día**: el perfil medido de *coluzzii* no
    cubre el día; `w_DAY = 0` es una consecuencia de la falta de dato, no una afirmación.

--------------------------------------------------------------------------------

## Detailed Implementation Plan

Una lista única, ordenada por identificador de paso; el **orden de ejecución** es el de §15. Cada entrada indica qué
cambia y por qué. Los ficheros se agrupan por el paso en que se tocan; un paso no
empieza hasta que el anterior pasa su verificación.

**Dos reglas de ubicación, válidas en todos los pasos**:

*   **Todos los headers del repo viven en
    `mal-core/src/mal_core/abm/include/mal_abm_fast/`** (41 ficheros), **no** en
    `src/`: el header nuevo `swarm_site_field.hpp` va ahí, y `src/` sólo lleva
    implementadores (`.cpp`).
*   **`mal-core/src/mal_core/abm/src/CMakeLists.txt`** (biblioteca
    `mal_abm_fast_core`) y **`mal-core/src/mal_core/abm/tests/CMakeLists.txt`**
    (`add_executable` + `gtest_discover_tests` por test) se tocan **en el mismo commit
    que el fichero nuevo**: sin ellos el módulo y los tests nuevos **no se compilan ni
    aparecen en `ctest`**, y el paso se vería verde sin haber probado nada.

### Estado de ejecución (actualizado 2026-11-18, rama `sim/individualization-movement`)

**Pasos 0 y 1: hechos y verificados; sin commit todavía** (el árbol de trabajo lleva los
cambios). **Siguiente paso a ejecutar: 2a** (humanos individuales, §15.0), luego 4, 5, 2b…
en el orden de §15. Quien arranque en una sesión nueva debe leer esta sección y §15.1.2.

*Qué existe y dónde:*

| Pieza | Fichero |
|---|---|
| Siembra por escenario (`ScenarioSpec`, `load_scenario_spec`, `SeedingMode::SCENARIO`, `seed_scenario`, `register_scenario_cell`, `derive_substream_seed`, streams acuáticos derivados del maestro, `micro_rng_`) | `abm/include/mal_abm_fast/{seeding,prng,mosquito_submodel,coordinator,engine,aquatic_cohort_bank}.hpp` y sus `.cpp`, `main.cpp` (`--scenario`) |
| Plomería Python (`SCENARIO_ARTIFACT`, `scenario_key`, `resolve_scenario`, `--scenario`, `--data-root`, `dynamics` entero) | `download/catalog.py`, `abm/wrapper.py`, `cli.py`, `ingest/env.py` |
| AOI sintético 10×10 + manifiesto con **una** clave `scenario:<id>` | `mal-execution/scripts/make_synthetic_aoi.py` → `runs/synthetic/accra-synth-10x10/` |
| 19 escenarios `E00…E18.json` (sin expectativas) y su documentación | `abm/tests/scenarios/E*.json`, `catalog.yaml` |
| Arnés y punto de entrada pytest | `abm/tests/scenarios/harness.py`, `abm/tests/test_scenarios.py` |
| Tests | C++: `test_scenario_seeding.cpp` (35); Python: `mal-core/tests/test_scenario_manifest.py` (14), `test_scenarios.py` |

*Cómo se verifica (todo medido al cerrar el paso):* `ctest` 313/313; `uv run pytest` desde
la raíz en verde (el arnés incluido); tras cualquier `cmake --build`, copiar
`build/src/mal_abm_fast` a `abm/bin/mal_abm_fast_darwin`. Ejecutar un escenario a mano:
`uv run malariasim abm --aoi accra-synth-10x10 --bbox=-0.2,5.7,-0.10971147034573944,5.789842104336081 --data-root runs/synthetic --scenario E01 --seed 20261117 --days 3 --month 6 --enable-transmission`.

*Qué comprueba hoy el arnés y qué no* (la documentación por escenario, con el propósito, lo
que implica, lo esperado y lo comprobado hoy, está en `abm/tests/scenarios/catalog.yaml` y
se publica en el documento ABM, apéndice «Scenario harness», generada por
`tools/gen_concepts_values.py`):

*   **Fidelidad de siembra, los 19 escenarios (real):** identidad de conservación
    `adultos(d) = adultos(d−1) − muertes(d) + emergidos(d)` desde lo sembrado; el COG y el
    registro de cohortes coinciden; las pupas sembradas de E07 emergen; la mortalidad
    cambia con la semilla (E13/E15); determinismo byte a byte (E01/E02/E13).
*   **Baseline de la cadena actual (E00/E01/E02):** la hembra no sale de su celda; la
    picadura sale del agregado de celda (ver arriba).
*   **Objetivos del plan como `xfail` estricto:** E01 sin picadura a 200 m, E02 sin
    picadura a 2 000 m, y el trazo del GIF (V1). Fallan hoy por la razón
    correcta; al pasar, el test se pone rojo y obliga a promoverlos.
*   **Lo que NO comprueban:** ningún comportamiento biológico de E03–E18 (sangre, seca,
    machos, viento…): dependen de pasos posteriores y su expectativa la escribe cada
    paso. Un escenario que sólo «corre» no cuenta como cerrado.

*Desviaciones y deudas conocidas (no ocultas):*

*   Celdas de ≈ 998,9 × 999,0 m (el bbox da 9 989 × 9 990 m), no 1 000 m exactos; el motor
    usa `resolution_m` = 1 000 para metros → celda.
*   `host_static.nc` sale del remuestreo de Accra, no de recuentos puestos a mano; el
    suelo de potencial 0,01 no descarta ninguna celda de esta ventana.
*   Los `overrides` no vacíos los **rechaza** el motor hasta el Paso 5: el arnés los quita
    del JSON ejecutado y los anota (`overrides_not_applied_until_paso_5`). E10 declara
    claves (`co2_activation_radius_m`, `olfactory_radius_m`, `visual_radius_m`) que aún
    **no existen** en `model_constants.yaml` (Paso 4).
*   El parser aún no admite `PRE_GRAVID` (E06 usa `TENERAL`), `blood_volume_ul` (E04/E05),
    sitios de enjambre y `swarm_site_id` (E13–E17), ITN (E16) ni machos estériles (E17):
    cada paso amplía el esquema que necesita.
*   `cell_id` de las cohortes acuáticas se valida en el motor (`engine.cpp`), sin test
    unitario. `mode`, `humans[].state` y `livestock[].species` no validan el tipo antes de
    leer (lanzan `type_error` en vez del error con ruta).
*   Los GIF de escenario son los del visualizador actual (1 fotograma por día) y no
    prueban nada: ver §15.1.2 (V0–V6).

### Paso 0 — Arnés de escenarios sobre manifiesto sintético

*   **`mal-execution/scripts/make_synthetic_aoi.py`** (nuevo) — construye el AOI
    sintético: recorta `data/accra-coastal-test/` a la ventana 10×10 y escribe
    `env.nc`, `habitat_patches.gpkg` y `host_static.nc` bajo
    `runs/synthetic/accra-synth-10x10/`. Recalcula el potencial con
    `mal_core.habitat.potential` y aplica el umbral de 0,01 de forma explícita
    (`habitat_engine.cpp:216` descarta por debajo). Es el generador de "los datos" del
    escenario. Además **copia** los JSON de escenario desde
    `mal-core/src/mal_core/abm/tests/scenarios/` a
    `runs/synthetic/accra-synth-10x10/scenarios/` (§13.2) y escribe el **campo de
    viento** `u100`/`v100` que carga `--wind-field` (para E18, §13.6).
*   **`mal-core/src/mal_core/ingest/env.py`** (modifica) — el productor de `dynamics`
    escribe hoy la **cadena** `persistent|pluvial` (`ingest/env.py:88`) mientras el
    motor lee un **int** (`habitat_engine.cpp:220`) ⇒ siempre 0. El productor pasa a
    escribir el int; el gpkg sintético también.
*   **`mal-core/src/mal_core/ingest/daily_nc.py`** y
    **`mal-core/src/mal_core/habitat/potential.py`** (modifican) — producción del
    **potencial y la salinidad por celda** para la rejilla completa (§9): el motor
    necesita el potencial de todas las celdas, no sólo de las candidatas, porque
    `k_habitat == 0 ⇒ p = 0` y el potencial entra en el registro por celda.
*   **`mal-core/src/mal_core/download/catalog.py`** (modifica) — añade el artefacto
    `SCENARIO_ARTIFACT` junto a `INGEST_ARTIFACTS:56`, para que un dataset `scenario`
    sea validable por `validate_completeness()`. Sin él, el manifiesto sintético no
    tiene dónde colgar los ficheros de escenario.
*   **`mal-core/src/mal_core/abm/wrapper.py`** (modifica) — resuelve el dataset
    `scenario` por id y lo pasa al binario como `--scenario`. `required_for_abm` se
    ignora en la validación (`manifest.py:193`), así que **los datasets opcionales no
    se declaran**: la opcionalidad se implementa con la ausencia de la clave.
*   **`mal-core/src/mal_core/cli.py`** (modifica) — añade `--scenario <id>` y
    `--data-root`, de modo que `malariasim abm --aoi accra-synth-10x10 --bbox …` llegue
    al wrapper con la raíz de datos alternativa.
*   **`mal-core/src/mal_core/abm/src/main.cpp`** (modifica) — añade la opción
    `--scenario` y el modo `SeedingMode::SCENARIO`.
*   **`mal-core/src/mal_core/abm/include/mal_abm_fast/seeding.hpp`** (modifica) —
    define `AgentSpec`, `AquaticSpec` y `ScenarioSpec`; extiende `SeedingConfig` con
    `SeedingMode::SCENARIO`. Hoy `SeedInstruction` transporta recuentos, no individuos
    (`seeding.hpp:119`), y el sexo se sortea como una moneda
    (`mosquito_submodel.cpp:358`): sin este cambio los escenarios E01/E02/E07/E08/E09/E13/E14
    son inejpresables.
*   **`mal-core/src/mal_core/abm/src/coordinator.cpp`** y
    **`include/mal_abm_fast/coordinator.hpp`** (modifican) —
    `build_scenario_seed_instructions()`: traduce el `ScenarioSpec` a instrucciones
    por individuo, **sin** el snap al parche más cercano que hace hoy
    `--seeding-mode explicit` (imprescindible para E07: un mosquito en una celda no
    candidata).
*   **`mal-core/src/mal_core/abm/src/seeding.cpp`** (modifica) — los **tres** modos de
    siembra (`random-viable`, `explicit` y el nuevo `SCENARIO`): el plan nombra sólo
    `seeding.hpp`, pero la lógica de siembra por modo vive en el `.cpp`.
*   **`mal-core/src/mal_core/abm/src/mosquito_submodel.cpp`** y
    **`include/mal_abm_fast/mosquito_submodel.hpp`** (modifican) — constructor de
    siembra por individuo: posición métrica, sexo y estado desde el spec. El **stream
    RNG del banco acuático** deja de auto-sembrarse con constantes fijas
    (`aquatic_cohort_bank.cpp:204/227/298`) y se deriva del `Prng` maestro; se añade el
    cuarto `peek_state()` para el micro-integrador (`engine.cpp:103-105, 303-305`).
*   **`mal-core/src/mal_core/abm/include/mal_abm_fast/prng.hpp`** y
    **`src/prng.cpp`** (modifican) — helper para derivar un sub-stream por etiqueta
    (coordinator/submodel/aquatic/micro), de forma que la derivación sea explícita y
    no dependa del orden de las llamadas.
*   **`mal-core/src/mal_core/abm/src/engine.cpp`** (modifica) — rama de escenario:
    carga el `ScenarioSpec`, pasa los streams derivados y abre el stream del
    micro-integrador.
*   **`mal-core/src/mal_core/abm/tests/scenarios/E00.json … E18.json`** (nuevos; **los
    crea este paso**, junto con el directorio) — 19 ficheros, uno por escenario (E10 con
    sus tres variantes dentro del mismo JSON), con la semilla, el modo y el esqueleto
    de la siembra (agentes, personas, cohortas). **Las expectativas las añade cada paso
    que implementa el comportamiento que comprueba** (§13.3.1); E01/E02 reciben su
    **baseline** en el Paso 1. Este paso **no escribe expectativas**: deja cada JSON con
    su modo provisional y sus overrides.
*   **`mal-core/src/mal_core/abm/tests/fixtures/make_golden_fixtures.py`** (no se
    modifica) — **los dos generadores de AOI son distintos y no se mezclan**: el arnés
    de escenarios usa **`make_synthetic_aoi.py` (AOI 10×10)**, porque los escenarios
    necesitan una rejilla de 1 km exacta (100 celdas) y personas, animales y cohortes
    **en metros**; `make_golden_fixtures.py` (AOI **8×8**) existe para los **goldens de
    `ctest`** y se queda como está (§13.1).
*   **`mal-core/tests/test_scenario_manifest.py`** (nuevo) — verifica que el manifiesto
    sintético valida, que el escenario se resuelve y que dos corridas con la misma
    semilla producen artefactos idénticos byte a byte.

### Paso 1 — Línea base

*   **`mal-core/src/mal_core/abm/tests/scenarios/`** (modifica) — E00, E01 y E02
    **completados** con el **baseline de la cadena actual**. **Medido el 2026-11-18**
    (corrige la suposición anterior de «0 picaduras»): la hembra sembrada **no sale de
    su celda en 3 días** y la cadena registra **1 picadura humana el día 1** y ninguna
    después, **también en E02 (persona a 2 000 m)**: la picadura se sortea contra el
    agregado de la celda (≈127 000 personas), no contra la persona sembrada. Ese hecho
    es el fallo que cierran el Paso 2a y el Paso 5; está fijado por
    `test_baseline_bite_is_drawn_from_cell_aggregate` y los objetivos `xfail` estrictos
    `test_target_e01_no_bite_at_200_m` / `test_target_e02_no_bite_at_2000_m`. El Paso 1 **no escribe expectativas**: escribe el
    baseline en `runs/_check_current/E0x.baseline.json`, y ese baseline es lo que se
    compara para detectar regresiones. Los pasos 2+ sustituyen el baseline por
    expectativas en forma cerrada.
*   **`runs/_check_current/`** (generado) — salida de comparación observado-vs-esperado
    de cada escenario. Se regenera en cada corrida; no se versiona.

### Paso 2 — Individuos humanos, ledger de eventos

*   **`mal-core/src/mal_core/abm/include/mal_abm_fast/human_state.hpp`** (modifica) —
    `HumanCompartmentGrid` pasa a un `HumanSoA` de individuos: `human_id` (determinista
    y estable: `human_id = cell_id * SLOTS_PER_CELL + slot`, con `SLOTS_PER_CELL` fijado en la primera extracción (manifiesto, §2), `cell_id`, `home_x/home_y` (posición fija
    uniforme dentro de la celda, asignada por semilla), `cur_x/cur_y` (iguales a `home`
    en esta versión), `state` y `timer`. Los compartimentos agregados pasan a
    **estadísticas derivadas** (`compute_stats()`); la API pública (`seed_infections`,
    `seed_random_viable_foci`, `seed_explicit_foci`, `seed_outbreak_cluster`,
    `advance_day`) mantiene su semántica, pero respaldado por individuos. **No se crea
    `human_population.hpp/.cpp`**: el módulo es el existente (§2).
*   **`mal-core/src/mal_core/abm/src/human_state.cpp`** (modifica) — implementación de
    las colas de cohorte por individuo (temporizador discreto en vez de cola por celda),
    del sorteo binomial de exposiciones y de la derivación de estadísticas. Consume el
    `Prng` que hoy usa la rejilla. **`advance_day` avanza sólo temporizadores**
    (edad, estado gonotrófico, timers de oviposición): deja de aplicar `λ_H` por celda
    (`human_state.cpp:241-266`).
*   **`mal-core/src/mal_core/abm/include/mal_abm_fast/bite_ledger.hpp`** (modifica) —
    `BiteLedger` conserva la capa de agregados (`BiteEventAggregate`, que consumen el
    COG de transmisión y la lógica de ITN/IRS) y **añade** la capa de eventos
    (`BiteEvent`: mosquito, persona, fase, volumen, resultado del sondeo, transmisión
    aplicada). El contrato de transmisión 4.0 no se rompe.
*   **`mal-core/src/mal_core/abm/src/transmission.cpp`** (modifica) — la exposición deja
    de aplicarse a una densidad de celda y se aplica a un individuo: la picadura
    identifica a la persona y la transmisión se propaga a esa persona. **Se retiran**
    `advance_human_transmission` (`transmission.cpp:446-479`), `lambda_h_`
    (`transmission.hpp:280`) e `infectious_pressure_` (`transmission.hpp:281`); el
    agregado por celda **sobrevive** como contador de `(row, col, tipo de hospedero)`
    en el ledger, que es lo que leen el COG de transmisión y la lógica de ITN/IRS.
*   **`mal-core/src/mal_core/abm/src/mosquito_submodel.cpp`** (modifica) — el término
    por celda `prev` (`mosquito_submodel.cpp:105-113`, `prev_at(host_row, host_col)`)
    pasa a **`prev_h`**: el estado individual de la persona picada.
*   **`mal-core/src/mal_core/abm/src/transmission_debug_log.cpp`** y
    **`include/mal_abm_fast/transmission_debug_log.hpp`** (modifican) — el log de
    depuración pasa a registrar eventos con identificadores (es el instrumento con el
    que se detectó el "cero picaduras humanas" del §P1).
*   **`mal-core/src/mal_core/abm/src/main.cpp`** (modifica) — flags de siembra humana
    por celda → por posición, para que el escenario pueda fijar la posición de una
    persona a 200 m (por debajo de la resolución de 1 km).

### Paso 3 — Fisiología de la sangre

*   **`mal-core/src/mal_core/abm/include/mal_abm_fast/gonotrophic_cycle.hpp`** (modifica)
    — **retira** el valor `MATE_SEEKING` del enum `GonotrophicState`
    (`gonotrophic_cycle.hpp:28-40`; el apareamiento deja de ser la transición *"Mating
    is assumed instantaneous for An. gambiae (swarm mating)"*, `:97`/`:110`) y **añade**
    `ARRESTED`; `GonotrophicParams` gana
    `blood_meal_target_ul`, `first_cycle_target_ul`, `probing_success_rate` y retira
    `feeding_success_rate` (que se carga en `gonotrophic_cycle.hpp:71` y el motor nunca
    consulta).
*   **`mal-core/src/mal_core/abm/include/mal_abm_fast/mosquito_state.hpp`** (modifica) —
    campos nuevos del SoA: `pos_x`, `pos_y`, `blood_volume_ul`, `ovarian_stage`,
    `gonotrophic_arrest`, `days_since_target_reached`, `inseminated`,
    `nights_uninseminated`, `age_days`, `swarm_site_id`. **No hay campo
    `home_x/home_y` para el adulto**: la filopatria natal no tiene base publicada
    (§16.1).
*   **`mal-core/src/mal_core/abm/src/mosquito_submodel.cpp`** (modifica) — la
    transición determinista `if (picked != nullptr) → BLOOD_FED`
    (`mosquito_submodel.cpp:757-779` y `:855-862`) se sustituye por la máquina
    `PROBING` con multipicadura; el reloj de inanición deja de reiniciarse con las
    comidas parciales; el lote de huevos pasa a ser **proporcional al volumen
    acumulado**; la oviposición se vuelve **multi-sitio** con el sesgo por estado de
    la cohorte de larvas conspecíficas (§9). Cada campo nuevo del SoA exige las tres
    operaciones: `push_back` (los tres bloques de siembra de adultos:
    `mosquito_submodel.cpp:236-260`, `:353-377`, `:522-553`; y el `reserve` de
    capacidad en `:323-344`), `std::swap` en la compactación
    (`mosquito_submodel.cpp:135-158`) y `resize` (`mosquito_submodel.cpp:163-180`).
*   **`mal-core/src/mal_core/abm/tests/test_mosquito_submodel.cpp`** (modifica) —
    casos de multipicadura, de umbral gonotrófico y de reloj de inanición.
*   **`mal-core/src/mal_core/abm/tests/test_gonotrophic.cpp`** (modifica) — el umbral
    por primera comida (pre-gravídica) y la ventana postprandial.

### Paso 4 — Esquema de configuración: **todas** las claves nuevas del plan

*   **La rebanada de esquema precede a su consumidor.** Ningún paso del motor puede
    usar constantes compiladas (`mal-core/tests/test_no_constants_guard.py` lo
    prohíbe): las claves que consume un paso están en el YAML, en el modelo pydantic,
    en el `struct` C++, en el enlace por nombre de `config.cc` y en el volcado de
    `config_dump.cpp` **antes** de que ese paso escriba código (§12.1, §12.4).

*   **`mal-core/config/model_constants.yaml`** (modifica) — **todas** las claves nuevas
    del plan, en las cinco superficies (§12.4):
    *   bloque `integration:` (`phase_duration_hours`, `directed_flight_budget_h`
        derivado, `dt_terminal_s` = 0,04, `dt_olfactory_s` = 0,25, `plume_memory_s`,
        `landing_speed_mm_s`, `landing_speed_hold_s`);
    *   bloque `mating:` completo (tabla de §12: `p_mate_male_fraction`,
        `p_mate_pairs_per_individual`, `p_mate_size_exponent`,
        `male_swarm_reference_size`, `female_attendance_rate`,
        `local_swarm_male_offer_factor`, `male_move_capacity_m`,
        `male_females_per_night_max`, `swarm_duration_min`,
        `swarm_start_min_after_sunset`, `swarm_height_m`, `swarm_markers_per_km2`,
        `swarm_markers_source`, `rain_suppresses_swarming`);
    *   clave de manifiesto `slots_per_cell` (fijada en la primera extracción, §2);
    *   **todas** las claves por especie de la tabla de §12 — movimiento y sensorial
        (`co2_activation_radius_m`, `olfactory_radius_m`, `visual_radius_m`,
        `terminal_radius_m`, `flight_speed_ms`, `exploration_range_m`,
        `exploration_step_m`, `exploration_step_correlation`, `casting_probability`,
        `casting_angle_deg`, `plume_memory_s`, `anemotaxis_rule`, `wind_reference`,
        `wind_block_threshold_ms`, `daily_move_capacity_m`,
        `directed_flight_budget_h`), **macho** (`male_ratio`, `male_daily_survival`) y
        **estivación** (`aestivation_supported`);
    *   las de la sangre (`blood_meal_target_ul`, `first_cycle_target_ul`,
        `blood_meal_size_ul`, `meal_size_min_ul`, `blood_meal_refractory_days`,
        `probing_success_rate`, `eggs_per_ul`), las de la seca
        (`arrested_daily_survival`, `gonotrophic_arrest_prob_dry`) y el bloque
        `gonotrophic` redefinido;
    *   `contracts.habitat` = "4.0" y `contracts.cogs_state` = "5.0" (los **dos**
        contratos que este plan publica; §10).
*   **`mal-core/src/mal_core/config_validation.py`** (modifica) — los modelos
    pydantic (`SpeciesRow:159`, `HostSeeking:312`, `Dispersal:296`) admiten las
    claves nuevas; `extra="forbid"` obliga a declarar cada una.
*   **`mal-core/src/mal_core/abm/include/mal_abm_fast/config.hpp`** (modifica) — los
    `struct` C++ (`SpeciesRow:139`, `DispersalCfg:408`, `HostSeekingCfg:450`) siguen
    al YAML.
*   **`mal-core/src/mal_core/abm/src/config.cc`** (modifica) — enlaces por nombre de
    las claves nuevas; **una clave nueva que aquí falte no falla el motor**, luego
    esta rebanada y la del volcado van en el mismo commit.
*   **`mal-core/src/mal_core/abm/src/config_dump.cpp`** (modifica) — el volcado
    incluye las claves nuevas (`config_dump.cpp:103-106`); el golden del dump se
    regenera.
*   **`mal-core/src/mal_core/abm/tests/test_config_engine_golden.cpp`** (modifica) —
    golden del volcado con la configuración nueva (el golden vive en C++; **no** hay
    `tests/test_config_engine_golden.py`).
*   **`mal-core/src/mal_core/abm/tests/test_config.cpp`** (modifica) — paridad de
    configuración Python/C++.
*   **`mal-core/tests/test_config_validation.py`** (modifica) — validación del
    esquema nuevo; `mal-core/tests/test_yaml_comments.py` comprueba que cada clave
    lleva su comentario con unidad y referencia.

### Paso 5 — Cascada de percepción y movimiento emergente

*   **`mal-core/src/mal_core/abm/src/engine.cpp`** (modifica) — el **reloj de fase**:
    `set_current_hour` pasa a fijarse **por fase** (hoy una sola vez por día,
    `engine.cpp:577`, con `dispersal.flight_hour` = 20), y la duración de cada fase se
    lee de `integration.phase_duration_hours`. El motor pasa de cuatro pasadas de
    **igual peso** a **pasadas con duración y peso** (§12.2).
*   **`mal-core/src/mal_core/abm/src/mosquito_submodel.cpp`** (modifica) — el bucle de
    fases (`mosquito_submodel.cpp:803-805`) consume la duración y el peso de cada fase:
    el tiempo de vuelo disponible en la fase es `min(t_fase, presupuesto restante)`, y
    el **presupuesto de vuelo se inicializa por mosquito y por día** (§5).

*   **`mal-core/src/mal_core/abm/include/mal_abm_fast/host_seeking.hpp`** (modifica) —
    se elimina el campo de atracción por celda (`compute_attraction`, `cell_attraction`,
    `detect_host_cell`, `step_toward_host`) y se sustituye por la máquina de estados
    de la cascada (§4) y por el **micro-integrador de dos bandas** (§5), con
    `dt_terminal_s`, `dt_olfactory_s` y `directed_flight_budget_h`.
*   **`mal-core/src/mal_core/abm/src/host_seeking.cpp`** (reescribe) — los cinco
    estados de la cascada, la integración adaptativa, el gate de aterrizaje por
    velocidad (`v < 50 mm/s` durante 3 s) y el consumo de RNG por `uid` (para que el
    orden de recorrido no altere el resultado).
*   **`mal-core/src/mal_core/abm/include/mal_abm_fast/aoi.hpp`** (modifica) — la
    transformación `xy_to_lonlat` / `lonlat_to_xy`, de modo que la conversión a grados
    use la misma ruta que la lectura de `host_static.nc`. **Geometría**: `AOI`
    (`wire.hpp:249-276`) tiene `west`/`south`/`east`/`north`, `crs = "EPSG:4326"`,
    `slug`, `resolution_m` (por defecto `ingest.cell_size_hint_m` = 1 000 m,
    `model_constants.yaml:150`) y `scale`; **no** tiene `origin` ni `transform` —la
    afín GDAL vive en `StateCogMetadata::transform`
    (`include/mal_abm_fast/output_contract.hpp:42-77`)—, así que el origen local de
    metros es la **esquina suroeste** del bbox. El radio terrestre es
    `geodesy.earth_radius_m` = **6 371 008,8 m** (`model_constants.yaml:132`) y el
    factor de latitud `geodesy.metres_per_deg_lat` = 111 195,080 233 532 92 m/°
    (`model_constants.yaml:133`): **no** se usa 6 371 000 ni un redondeo de docstring.
    La conversión metros→celda usa `resolution_m`; el motor ya tiene
    `cells_per_side_h(aoi)` (`aoi.hpp:37`) para la altura.
*   **`mal-core/src/mal_core/abm/include/mal_abm_fast/human_state.hpp`** y
    **`src/human_state.cpp`** (modifican) — **búsqueda de personas por rejilla de
    celdas**: en el repo **no existe** ninguna estructura de nearest-person (ni KD-tree
    ni quadtree; `host_seeking.cpp` recorre una ventana de celdas), y el plan **no**
    introduce un índice espacial. La capa humana indexa a las personas **por celda**
    (misma rejilla de 1 km) y expone `for_each_person_in_radius(pos, radius, fn)`:
    con `co2_activation_radius_m` = 100 m < 1 km, la consulta toca la celda propia y,
    si el mosquito está a menos de 100 m del borde, la celda vecina; el radio se
    acota por distancia en metros. Propietario de la estructura: `human_state.hpp`.
*   **`mal-core/src/mal_core/abm/src/wind_field.cpp`** y
    **`include/mal_abm_fast/wind_field.hpp`** (modifican) — el motor hoy carga viento
    **ERA5 6-horario u100/v100** (`wind_field.cpp:47-56`, `wind_field.hpp:22-26`): 100 m
    sobre el suelo, sin nivel de superficie ni perfil vertical, y **opcional**
    (`--wind-field`). El AOI sintético **no** declara el dataset de viento en los
    escenarios, **salvo E18**, que lo carga para ejercitar la rama ⇒ viento 0 en el
    resto, con la regla de bloqueo y la anemotaxis **inactivas**: eso es una salida
    documentada, no un fallo.*   **`mal-core/src/mal_core/abm/src/oviposition_seeking.cpp`** (reescribe en el
    **Paso 9**) — el núcleo de oviposición (búsqueda de criadero) se reescribe en el
    Paso 9, no aquí: la cascada sólo sustituye el **campo de búsqueda de hospedero**.
*   **`mal-core/src/mal_core/abm/tests/test_host_seeking.cpp`** (reescribe) — casos
    por tramo, con distancias medidas.
*   **`mal-core/src/mal_core/abm/tests/test_mobility.cpp`** (modifica) — el módulo de
    movilidad humana (`MobilitySchedule`) queda **sin consumidor** al aplicarse N2; el
    test se marca como *skip* con la nota de eliminación pendiente, no se borra.

### Paso 6 — Estado fisiológico y estación seca

*   **`mal-core/src/mal_core/abm/src/mosquito_submodel.cpp`** (modifica) — la
    transición a `ARRESTED` (hembra alimentada y gravídica en celda sin criadero
    elegible durante racha de secas), con supervivencia propia y parada ovárica por
    especie; `ovarian_stage` derivado de `gonotrophic_cycles`.
*   **`mal-core/src/mal_core/abm/include/mal_abm_fast/thermal_responses.hpp`**
    (modifica) — si la supervivencia en arresto se modela como una curva, se añade
    aquí y no en el submodelo, para no duplicar la lógica térmica.
*   **`mal-core/src/mal_core/abm/tests/test_lifecycle.cpp`** (modifica) — casos de
    época seca: la hembra no muere, se aplaza, y el diagnóstico emite la fracción
    medida (19,23–34,85 % en *coluzzii*).

### Paso 7 — Estado acuático por celda

*   **`mal-core/src/mal_core/abm/include/mal_abm_fast/wire.hpp`** (modifica) —
    `PatchState` → `CellState`: `patch_id` → `cell_id`, `activated` → `eligible`; se
    documenta que "patch" es un filtro de elegibilidad y no un contenedor de
    información. Se añade `mother_x`/`mother_y` al payload de la cohorte (§9).
*   **`mal-core/src/mal_core/abm/include/mal_abm_fast/aquatic_cohort_bank.hpp`**
    (modifica) — `CohortKey` pasa a ser `(cell_id, mother_id)` (§9): `mother_id`
    identifica a la hembra que oviposita (individuo), de modo que dos hembras que
    ovipositan en la misma celda dan cohortes distintas; la Beverton-Holt sigue
    aplicándose **por celda** (suma de recuentos de las cohortes de la celda), luego
    N5 sobrevive. `AquaticCohort` gana la posición de la madre (`mother_x`,
    `mother_y`); `EmergenceEvent` lleva la posición de emergencia (no el centro de la
    celda).
*   **`mal-core/src/mal_core/abm/src/aquatic_cohort_bank.cpp`** (modifica) — la ruta
    de error "no PatchState for today" (`aquatic_cohort_bank.cpp:304-306`) desaparece
    por construcción: toda celda tiene registro. La Beverton-Holt sigue siendo por
    celda (1 km²).
*   **`mal-core/src/mal_core/abm/src/coordinator.cpp`** (modifica) — `to_dataframe()`
    materializa `CellState` para **todas** las celdas del AOI, no sólo las candidatas;
    `patch_registry_` se sustituye por `cell_id` directo.
*   **`mal-core/src/mal_core/abm/src/mosquito_submodel.cpp`** (modifica) — se retira
    `update_patch_id` (`mosquito_submodel.cpp:965-1004`) y con él
    `dispersal.snap_radius_m`; la emergencia coloca al adulto en la posición de la
    madre en lugar del centro de la celda (`mosquito_submodel.cpp:530-535`).
*   **`mal-core/src/mal_core/abm/src/output_contract.cpp`** y
    **`include/mal_abm_fast/output_contract.hpp`** (modifican) — el sidecar escribe
    `cell_id` y las estadísticas por individuo; `StateCogMetadata::band_names`
    (`output_contract.hpp:42-77`) pasa a **una sola** banda. **No se publica 4.1**:
    el contrato de estado va de 4.0 a **5.0** en un solo bump (§10).
*   **`mal-core/src/mal_core/abm/tests/test_state_cog.cpp`** (modifica) — golden del
    COG de estado: **5.0** (una sola banda, `adult_cell_count`). **No se publica
    4.1**: no hay estado intermedio que leer, y los checkpoints del surrogate entrenados
    con las bandas normalizadas de ≤ 3.0 no se reutilizan sin reentrenar. El golden se
    regenera.
*   **`habitat_cell_planes.json`** (nuevo; se escribe en el **directorio de la
    corrida**) — el **plano de hábitat por celda** que necesitan los scorers (§9, §10):
    JSON con una entrada por `cell_id` y, en cada una, el **potencial total** (índice
    adimensional en [0, 1]) y la **elegibilidad** (booleano). **Lo produce este Paso 7**
    (es el paso que materializa el registro por celda) y los scorers lo localizan por
    **ruta relativa al directorio de la corrida** (`<run>/habitat_cell_planes.json`).
*   **`mal-core/src/mal_core/abm/tests/test_pool_water.cpp`** y
    **`test_habitat_engine.cpp`** (modifican) — las fábricas de `PatchState` pasan a
    `CellState` y deben fijar `k_habitat` explícitamente (1000,0) o las larvas mueren
    el día 1 (contrato de estado 4.0, §9).

### Paso 8 — Machos: sitio asignado, enjambre por sitio, cupos

*   **`mal-core/src/mal_core/abm/include/mal_abm_fast/gonotrophic_cycle.hpp`** (modifica)
    — **también en este paso**: la asignación de sitio al nacer (macho **y** hembra,
    decisión F) y la contabilidad de la inseminación tocan la misma máquina de estados;
    el valor `MATE_SEEKING`, **retirado en el Paso 3**, no se reintroduce.

*   **`mal-core/src/mal_core/abm/include/mal_abm_fast/mosquito_state.hpp`** (modifica) —
    `swarm_site_id` (int32, −1 = **sin sitio alcanzable**; no hay enjambre local de
    respaldo, §8.2), `inseminated` y
    `nights_uninseminated` pasan a aplicar **también a los machos** (el SoA ya los
    guarda; no hay coste de memoria añadido). Las tres operaciones del SoA
    (`push_back`, `std::swap` en la compactación, `resize`) se aplican a los campos
    nuevos.
*   **`mal-core/src/mal_core/abm/src/mosquito_submodel.cpp`** (modifica) —
    (a) **asignación de sitio al emerger**: el macho nace en la posición de la madre
    (`mother_x`/`mother_y` de la cohorte acuática, §9) y sortea uno de los sitios **alcanzables** con peso de acumulación, o queda **suelto** (distancia ≤ `male_move_capacity_m`
    = 50 m/día). Si no hay ningún sitio
    alcanzable, `swarm_site_id = -1` ⇒ **sin sitio: no se reproduce** y no genera
    cupos (§8.6). La hembra recibe sitio al nacer con el **mismo** criterio
    (decisión F).
    (b) **asistencia nocturna**: en la ventana de enjambre, cada macho asiste a su
    sitio; el recuento por sitio se reconstruye sumando los machos asignados.
    (c) **cupos**: `cupos(s) = M_disp(s) × p_mate_male_fraction ×
    (M(s) / male_swarm_reference_size)^(−p_mate_size_exponent)`, con
    `p_mate_male_fraction` = 0,072 ± 0,0095 [P], `p_mate_size_exponent` = 0 (banda 0–1)
    [EP] y `male_swarm_reference_size` = 100 [EP] (§8.5); el sorteo empareja machos y
    hembras no inseminadas dentro del alcance de vuelo;
    los machos emparejados quedan `inseminated`, los demás incrementan
    `nights_uninseminated`.
    (d) **reintento sin caducidad** y **supervivencia del macho separada de la
    hembra** (`male_daily_survival` = 0,773 ± 0,094).
    (e) Se retira el movimiento de los machos por el kernel de la hembra: el macho
    tiene su propio presupuesto (`male_move_capacity_m`).
*   **`mal-core/src/mal_core/abm/include/mal_abm_fast/swarm_site_field.hpp`** (nuevo) y
    **`src/swarm_site_field.cpp`** (nuevo) — la capa
    estática y persistente de sitios de enjambre: id, posición métrica, y la
    estructura publicada (separación 11–19 m, altura 2,87 m, duración ≈27 min,
    ventana 5–33 min tras la puesta de sol, densidad `swarm_markers_per_km2`); el
    campo se **resuelve una vez** por corrida y se cachea, no se recalcula por noche.
    **El header va en `include/mal_abm_fast/`**, no en `src/`, y el `.cpp` se declara
    en `src/CMakeLists.txt`.
*   **Artefacto del campo de sitios** (no existe hoy: no hay `swarm_sites.gpkg` ni una
    variable `swarm_field` en el repo). Definición: fichero **`swarm_sites.json`**,
    formato JSON con una lista de `{"id": int, "x_m": float, "y_m": float,
    "marker_type": string}` en **metros proyectados del AOI**; **productor: este Paso
    8**, que lo **genera de forma determinista** a partir de `swarm_markers_per_km2`
    con una **semilla explícita** (derivada de la semilla maestra del escenario) y lo
    escribe en el **directorio de la corrida**; **clave de manifiesto**: `swarm_sites`
    (una clave por AOI, con su fichero); **catálogo**: `swarm_sites` se declara en
    `mal-core/src/mal_core/download/catalog.py`, junto a `SCENARIO_ARTIFACT`; por eso
    la clave es validable por `validate_completeness()`; **consumidor**:
    `coordinator.cpp`, que lo carga y lo cachea. El campo **no** se deriva del gpkg de
    hábitat (los marcadores —montones de leña, basura, pozos— no son hábitat), y por
    eso es un artefacto propio. **No hay datos de Ghana**: el campo es una generación
    sintética calibrada por densidad; es un **riesgo abierto**, con su mitigación en
    «Riesgos y mitigaciones».
*   **`mal-core/src/mal_core/download/catalog.py`** (modifica) — publica el artefacto
    `swarm_sites` en el catálogo (junto a `SCENARIO_ARTIFACT`, que el Paso 0 añade),
    de modo que la clave de manifiesto `swarm_sites` sea validable por
    `validate_completeness()` y resoluble como las demás.
*   **`mal-core/src/mal_core/abm/wrapper.py`** (modifica) — resuelve el dataset
    `swarm_sites` desde la clave de manifiesto y pasa el fichero al binario como
    `--swarm-sites` (igual que resuelve el dataset `scenario` en el Paso 0).
*   **`mal-core/src/mal_core/abm/src/coordinator.cpp`** (modifica) — carga el campo de
    sitios desde el artefacto del manifiesto y lo pone a disposición del submodelo.
*   **`mal-core/src/mal_core/abm/src/main.cpp`** (modifica) — flag `--swarm-sites
    <fichero>` para pasar el campo (resuelto por el wrapper desde la clave de
    manifiesto `swarm_sites`); y el flag de *swarm killing* que E15 necesita (matar los
    machos asignados a un marcador).
*   **`mal-core/src/mal_core/abm/tests/test_mating.cpp`** (nuevo) — casos de
    asignación de sitio (con y sin sitio a alcance), de enjambre local, de cupos y
    del reintento; y un caso que verifique que el **resultado no depende** de la
    granularidad del enjambre (opción 2 vs opción 3 dan la misma oferta).
*   **`mal-core/src/mal_core/abm/tests/test_dispersal.cpp`** (modifica) — casos de
    movimiento de macho con presupuesto propio.

*   **Lo que NO se hace** (y por qué): no se simula el vuelo del macho al enjambre
    (opción 3, §8.3 y A18). La diferencia queda documentada en §8.3 y en A18 del
    documento de plan; si en el futuro se requiere el comportamiento intra-enjambre
    (p. ej. segregación de enjambres entre especies), la capa se añade encima de esta
    sin tocar el resto del diseño.

### Paso 9 — Elección del sitio de oviposición

*   **`mal-core/src/mal_core/abm/src/oviposition_seeking.cpp`** (reescribe) — el
    kernel pasa de `potential × exp(-d/scale)` a un criterio de **elegibilidad +
    señal en el sitio** (cohorte de larvas conspecíficas, sesgo por tipo de habitat,
    multi-sitio). Se corrige también la cabecera de `oviposition_seeking.hpp`, que
    documenta un `twi × water_frac` retirado en el contrato v3.0.
*   **`mal-core/src/mal_core/abm/include/mal_abm_fast/oviposition_seeking.hpp`**
    (reescribe) — idem cabecera, y se retira la noción de `scale_m` (radio de
    atracción con decaimiento continuo). **Aquí se retira `oviposition.scale_m`**
    (50 m), no en el paso de movimiento: es este paso el que reescribe el núcleo de
    oviposición. La ligazón entre la hembra gravídica y el criadero la sustituyen la
    **ley de viaje** y la **regla de señal sobre los sitios alcanzables** (§4, §9).
*   **`mal-core/src/mal_core/abm/include/mal_abm_fast/wire.hpp`** (modifica) — se
    retira `OVIPOSITION_SCALE_M()` (`wire.hpp:68`), que es el único consumidor de la
    clave; `wire.hpp` declara también `AOI` (`wire.hpp:249-276`) y
    `STATE_BAND_NAMES` (`wire.hpp:217`), que se tocan en los pasos 7 y 11.
*   **`mal-core/src/mal_core/abm/src/oviposition_seeking.cpp`** (completa el Paso 9) —
    el sesgo por estado/densidad de la cohorte de larvas conspecíficas y la
    persistencia del criadero, con los valores publicados de *coluzzii*.
*   **`mal-core/src/mal_core/abm/tests/test_oviposition.cpp`** (nuevo) — casos de
    elección de sitio y de skip oviposition.

### Paso 10 — Modos definitivos y verificación de cobertura de los escenarios

*   **`mal-core/src/mal_core/abm/tests/scenarios/E00.json … E18.json`** (modifican —
    fijan los modos definitivos; el Paso 0 los creó) — este paso escribe **sólo la
    expectativa de E17**
    (SIT/IIT sobre los cupos por sitio) y **fija los modos definitivos** de los 19
    escenarios (`gate`/`report`), comprobando que **cada** escenario de la tabla de §15
    tiene su expectativa y su modo (§13.3.1). Las expectativas de E03–E06 y E11 las
    escribió el Paso 3; las de E01, E02, E10 y E18, el Paso 5; la de E12, el Paso 6; las
    de E07, los Pasos 7 y 9 (una aserción cada uno); las de E14 y E15, el Paso 8; las
    de E08 y E09, el Paso 2. E16 (contrascenario ITN al 60 %) queda en `report`. Los JSON
    **no** cambian de sitio: la copia canónica es la del repo (§13.2) y el generador la
    copia al directorio del AOI.
*   **`mal-core/src/mal_core/abm/tests/scenarios/harness.py`** (nuevo) — el arnés:
    carga el `ScenarioSpec`, resuelve la clave de manifiesto `scenario:<id>`, lanza el
    binario, compara y escribe el observado-vs-esperado en `runs/_check_current/`.
*   **`mal-core/src/mal_core/abm/tests/test_scenarios.py`** (nuevo) — punto de entrada
    **pytest** (un test por escenario); el arnés entra en el CI por `pytest` desde la
    raíz del repositorio, no por `ctest`.

### Paso 11 — Contratos, consumidores y recalibración de los scorers

*   **Las claves ya nacieron en el Paso 4.** Este paso **no crea ninguna clave**: aplica
    los valores de contrato, retira las claves que el código deja de leer y adapta los
    consumidores (§12.4).

*   **`mal-core/config/model_constants.yaml`** (modifica) — `version: 3`; se retiran
    `host_seeking_scale_m`/`host_seeking_radius_m` (por especie),
    `dispersal.host_flight_step_m`, `dispersal.snap_radius_m`, `oviposition.scale_m`,
    `dispersal.adult_prob_day`, `dispersal.adult_sigma_m`, `dispersal.adult_max_m`,
    `gonotrophic.feeding_success_rate` y las tres semillas fijas del bloque `rng:`.
    **Ninguna clave se crea aquí**: las bloques `integration:` y `mating:`, las claves
    por especie, `SLOTS_PER_CELL`, `contracts.habitat` y `contracts.cogs_state` ya
    nacieron en el **Paso 4** (§12.4); este paso sólo **retira** las que el código
    deja de leer y fija los **valores** de contrato que este plan publica. Cada clave
    lleva su unidad y su tier de evidencia.
*   **`mal-core/src/mal_core/config_validation.py`** (modifica) — los modelos
    pydantic (`SpeciesRow:159`, `HostSeeking:312`, `Dispersal:296`, `Gonotrophic:284`)
    siguen al YAML; el bloque `gonotrophic` se **redefine** (lote proporcional al
    volumen) y su validación `0 < min <= mean <= max <= n`
    (`config_validation.py:603-608`, y declarada en el docstring del módulo,
    `config_validation.py:34-35`) cambia en consecuencia.
*   **`mal-core/src/mal_core/abm/include/mal_abm_fast/config.hpp`** (modifica) — los
    `struct` C++ (`SpeciesRow:139`, `DispersalCfg:408`, `HostSeekingCfg:450`,
    `GonotrophicCfg:376`) siguen al YAML.
*   **`mal-core/src/mal_core/abm/src/config_dump.cpp`** (modifica) — el volcado
    incluye las claves nuevas y **retira** las antiguas
    (`config_dump.cpp:103-106`); es la superficie que la calibración consume.
*   **`mal-core/src/mal_core/abm/tests/test_config.cpp`** (modifica) — paridad de
    configuración Python/C++ (el golden del volcado vive en
    `mal-core/src/mal_core/abm/tests/test_config_engine_golden.cpp`; **no** existe un
    `tests/test_config_engine_golden.py`).
*   **`mal-core/src/mal_core/abm/include/mal_abm_fast/wire.hpp`** (modifica) —
    `STATE_BAND_NAMES` (`wire.hpp:217`) pasa a un solo nombre (`adult_cell_count`);
    `CONTRACT_VERSION()` (`wire.hpp:107`) lee `contracts.cogs_state` = "5.0".
*   **`mal-core/src/mal_core/training/dataset.py`** (modifica) — `VECTOR_CHANNELS` pasa
    de 2 a 1 con el contrato 5.0; el loader lee el nombre de banda del sidecar en vez
    de asumir posiciones.
*   **`mal-core/src/mal_core/prediction/state_loader.py`** (modifica) — lee el COG de
    estado con una banda y **rechaza** versiones de contrato desconocidas.
*   **`mal-core/src/mal_core/scoring/scorers/d1_habitat_occupancy.py`** (modifica) —
    deja de leer `ds.read(2)`: el numerador sale de `adult_cell_count > 0` y el
    **denominador** del **plano de hábitat por celda** que publica el Paso 7 (§9,
    §10). Conserva el objetivo 0,20–0,70 y el peso 1,0.
*   **`mal-core/src/mal_core/scoring/scorers/d8_coupling.py`** (modifica) — correlaciona
    `adult_cell_count` con ese mismo plano de hábitat por celda; conserva el peso 2,0.
*   **`mal-core/src/mal_core/scoring/registry.py`** (modifica) — recalibración de los
    scorers que leen bandas del COG (los que dependan de la banda desaparecida se
    **adaptan**, no se retiran: `COMPOSITE_WEIGHTS` no cambia y `GATES` tampoco);
    el registro de scorers es `mal-core/src/mal_core/scoring/registry.py::build_registry`.
*   **`mal-core/src/mal_core/training/model.py`** (modifica) — **no cambia los canales**:
    sus valores por defecto (`model.py:45`, 6 y 2) no los usa el entrenamiento
    (`trainer.py:63-64` los sobreescribe con los del dato); lo que sí hay que tocar es
    `mal-core/src/mal_core/training/wrapper.py:62,66` (los *fallbacks* de canales, que
    pasan a 9 de entrada y 5 de salida con una sola banda de estado). El modelo se
    **reentrena desde cero** (los checkpoints con
    bandas normalizadas de ≤ 3.0 no se reutilizan).
*   **`docs/concepts/contracts.yaml`** (modifica) — clave `cogs_state` (lista `bands`)
    y clave `state_sidecar` (`band_names` y lista de claves del sidecar).
*   **`docs/concepts/generated/*.tex`** (regenera) — artefactos **generados**
    (`macros.tex` y derivados): **no se editan a mano**; se regeneran con
    `uv run python tools/gen_concepts_values.py` (editarlos a mano rompe
    `gen_concepts_values.py --check`).
*   **`tools/gen_concepts_values.py`** (modifica) — la macro
    `training.vector_channels` (`gen_concepts_values.py:1075`) refleja el cambio de
    bandas; **el fichero nunca se edita a mano**, se regenera.
*   **`tools/coherence_signals.py`** (modifica) — señales de coherencia que dependen de
    las bandas o de las claves del contrato.
*   **`mal-core/src/mal_core/abm/tests/test_config_engine_golden.cpp`** (modifica) —
    golden del motor con la configuración nueva.

### Ficheros de documentación

*   **Documentación viva** — los specs de `docs/specs/` se retiraron: el fichero
    `docs/specs/abm/spec.md` **no existe**. Los ficheros vivos son
    **`docs/concepts/abm/odd-2010-malariasentinel.tex`** (el ODD conceptual) y
    **`docs/concepts/contracts.yaml`** (los contratos). En ambos se actualizan las
    invariantes afectadas por la banda única, por el registro por celda y por los
    identificadores de evento. El detalle de los pasajes del ODD va en la entrada
    siguiente.
*   **`docs/concepts/abm/odd-2010-malariasentinel.tex`** — este plan sustituye a los
    antiguos packs ODD 02 (individualización) y 09 (semilla maestra), borrados, y a la
    parte cubierta de los packs 03, 04, 05, 08, 10 y 13, cuyo pendiente vive ahora
    en los documentos reagrupados de `docs/plans/in-process/odd-fixes/`. Los
    **pasajes concretos a enmendar** en el commit que aplica este plan son:

    | Pasaje del ODD | Por qué lo invalida este plan |
    |---|---|
    | §2.1 "Entities" | las personas pasan a ser individuos (§2) |
    | §2.2 "State variables" | campos nuevos del SoA, estado humano individual, estado acuático por celda (§3, §9) |
    | §4.10 "Collectives" | la fase acuática sigue siendo cohorte; el enjambre es un agregado por sitio (§8, N1) |
    | §5.4 "Randomness and reproducibility" | un solo maestro de semilla, con el stream acuático derivado (§13.4, NFR-1) |
    | §7.2 "Advance aquatic stages" | registro por celda y emergencia en la posición de la madre (§9) |
    | §7.6 "Seek hosts and feed" | cascada sensorial, multipicadura y sondeo por individuo (§4, §6) |
    | Appendix A.5 | semillas y sub-streams (§13.4, Apéndice B) |

    Los pasajes de los documentos **pendientes** del directorio
    `docs/plans/in-process/odd-fixes/` siguen listados en cada uno de ellos, que es
    donde queda lo que este plan no decide.
*   **`papers/REFERENCES.md`** — ya actualizado con las filas 89–113 (§16).
*   **Artefactos temporales que se borran al cerrar este plan**: este plan es el único
    artefacto durable. El borrado es **por fichero**, nunca por directorio, conforme a
    la regla de limpieza del proyecto. Las rutas exactas:

    | Artefacto | Ruta exacta | Estado |
    |---|---|---|
    | Documento de diseño intermedio (brief del RFC) | `docs/designs/individualization-and-movement-brief.md` | ya borrado (`c235a33`) |
    | Informe de revisión Goldfish del brief | `docs/designs/individualization-and-movement-brief.goldfish-review.md` | ya borrado (`c235a33`) |
    | Informes de la revisión 2 | `runs/_reviews/individualization-and-movement/consolidated_review_report.md`, `runs/_reviews/individualization-and-movement/comprehension_report.md`, `runs/_reviews/individualization-and-movement/critic_report.md`, `runs/_reviews/individualization-and-movement/implementation_readiness_report.md`, `runs/_reviews/individualization-and-movement/intermediate_zoom_out_report.md`, `runs/_reviews/individualization-and-movement/zoom_out_report.md` | pendientes de borrar |
    | Nota de decisiones de la corrección del plan | `runs/_reviews/individualization-and-movement/work/cambios-y-decisiones.md` | pendiente de borrar |
    | Copias de trabajo del parcheado por regiones | `runs/_reviews/individualization-and-movement/work/plan.base.md`, `runs/_reviews/individualization-and-movement/work/plan.diff`, `runs/_reviews/individualization-and-movement/work/region1.md` … `region5.md`, `runs/_reviews/individualization-and-movement/work/region1.patch` … `region5.patch`, `runs/_reviews/individualization-and-movement/work/prompt-*.md` | pendientes de borrar |

    El arnés de escenarios está especificado dentro de este plan (§13) y no tiene nota
    aparte.

### Plan de verificación

**Criterio de aceptación de cada paso**: el arnés de escenarios pasa, `ctest` no
empeora, y la suite Python de `mal-core` está verde.

*   **Nivel 1 — unidad (C++)**: el comando canónico de reconstrucción es

    ```bash
    cmake -S mal-core/src/mal_core/abm -B mal-core/src/mal_core/abm/build
    cmake --build mal-core/src/mal_core/abm/build -j
    ctest --test-dir mal-core/src/mal_core/abm/build
    ```

    y **después de cualquier `cmake --build`** hay que copiar el binario a la ruta que
    el wrapper resuelve primero:
    `cp mal-core/src/mal_core/abm/build/src/mal_abm_fast mal-core/src/mal_core/abm/bin/mal_abm_fast_darwin`
    (si no, la corrida usa el binario viejo en silencio). Es el **mismo comando** que
    usa el Nivel 6.

    **Lista blanca de fallos preexistentes**, con dueño y fichero:

    | Fichero | Aserción | Dueño |
    |---|---|---|
    | `mal-core/src/mal_core/abm/tests/test_config.cpp:193` | `resting_duration_days` 1,0 frente a 0,5 | el **Paso 3** (reescritura del bloque gonotrófico) actualiza la aserción |
    | `mal-core/src/mal_core/abm/tests/test_gonotrophic.cpp:127` | `resting_duration_days` 1,0 frente a 0,5 | el **Paso 3** |
    | `mal-core/src/mal_core/abm/tests/test_species.cpp` | defaults de *coluzzii* | el **Paso 4** (rebanada de esquema) |

    Ningún otro fallo preexistente está en la lista blanca: un fallo nuevo es una
    regresión y bloquea el paso.
*   **Nivel 2 — contrato (Python)**: el comando canónico es **`uv run pytest`** **desde
    la raíz del repositorio**: el `pyproject.toml` raíz configura
    `testpaths = ["mal-core/tests", "mal-commonlib/tests",
    "mal-core/src/mal_core/abm/tests"]`, de modo que `cd mal-core && uv run pytest tests`
    **no** recolecta `mal-core/src/mal_core/abm/tests/` y deja fuera el arnés. Incluye
    `test_config_validation.py` (reescrito), `test_no_constants_guard.py` (ninguna
    constante compilada fuera del YAML) y `test_yaml_comments.py` (cada clave nueva
    lleva su comentario con unidad y referencia).
*   **Nivel 3 — paridad Python/C++**: `test_habitat_python_contract.py` (β urban
    unificado 0,75) y el test de paridad de configuración, porque las claves nuevas
    viven en **cinco** superficies (§12.1): YAML, modelo pydantic, `struct` C++,
    enlace por nombre en `config.cc` y volcado en `config_dump.cpp`.
*   **Nivel 4 — escenarios**: el arnés (`mal-core/src/mal_core/abm/tests/scenarios/`
    con `harness.py`, y el punto de entrada `mal-core/src/mal_core/abm/tests/test_scenarios.py`)
    se ejecuta con la semilla maestra; cada escenario escribe observado-vs-esperado
    en `runs/_check_current/`. La **tabla de pasos de §15** («Escenario que cierra
    cada paso») es la referencia autoritativa: cada paso tiene su escenario, su modo y
    su criterio, y el criterio de aceptación del paso es que su escenario pase. **E07
    tiene dos aserciones** y cierra dos pasos (el 7 y el 9); el **Paso 4** y el **Paso
    11 no tienen escenario propio**: su criterio es, respectivamente, la paridad de las
    cinco superficies y el contrato 5.0 más los Niveles 5/6. Los
    escenarios en **modo `gate`** **fallan el CI**; los de **modo `report`** llevan
    banda de tolerancia pre-registrada y se revisan, y **no cierran** ningún paso. En
    particular: **E01** (`gate`) = 0 comidas, la distancia no permite el contacto;
    **E02** (`report`) = banda de distancia derivada del modelo; **E13** (`report`) =
    banda de hembras sin inseminar derivada de la fórmula de §8.1; **E18** (`gate`) =
    desvío *upwind* y bloqueo nocturno con campo de viento.
*   **Nivel 5 — determinismo**: dos corridas con la misma semilla producen artefactos
    **idénticos byte a byte**; dos semillas distintas producen artefactos distintos.
    El alcance byte-a-byte **excluye los GeoPackages**: el gpkg sella
    `gpkg_contents.last_change` y **no** es reproducible byte a byte
    (`mal-core/src/mal_core/abm/tests/golden/README.md:15-17`,
    `fixtures/make_golden_fixtures.py:17-19`). Se comparan byte a byte el **COG de
    estado**, los **sidecars JSON**, los **JSONL** (`_bites.jsonl` y `_mating.jsonl`) y
    `_agents.parquet`; los **gpkg** se comparan **por contenido** (tabla de atributos
    ordenada, con `row`/`col`/`potential` recalculados). **`_humans.parquet` queda
    excluido** de la comparación byte a byte porque va **muestreado al 1 % con pesos**
    (§11): se compara **por contenido** (conjunto de `human_id` muestreados y sus
    pesos, con la misma semilla). El **input sintético**
    (`runs/synthetic/accra-synth-10x10/`) queda **exento** de la comparación byte a
    byte: es la entrada, no la salida. Este test es el que detecta que un sub-stream
    se ha auto-sembrado (el hueco de `aquatic_cohort_bank.cpp:204/227/298`).
*   **Nivel 6 — regresión de la cadena (P1)**: se comprueba sobre el **binario
    reconstruido** con el comando del Nivel 1 (incluida la copia a
    `bin/mal_abm_fast_darwin`), no sobre el golden (el golden hay que regenerarlo con
    el cambio de contrato). Se separan **dos** criterios, con valor objetivo:

    *   **(a) Picaduras humanas > 0**: una corrida de 30 días del AOI de Accra registra
        **al menos una** picadura humana. Es el criterio de éxito del §P1 y el
        indicador que se compara con el estado actual (0 picaduras en 30 días).
    *   **(b) La población de vectores no colapsa**: al final de los 30 días, la densidad de adultos es **≥ el 50 %** de la densidad inicial de la misma corrida. El baseline es el que se captura tras el Paso 7, no el 122 → 2 actual.
    *   **(c) La cadena funciona en los escenarios sintéticos** (Apéndice A): hay picaduras, transmisión y la transmisión es efectiva en la persona picada. Éste es el criterio de G1; no fija ninguna densidad mínima. El 0,036 adultos/km² se conserva sólo como dato del AOI (§5.1).
*   **Nivel 7 — revisión de la base teórica**: cada número nuevo que entra en
    `model_constants.yaml` tiene una entrada en `papers/REFERENCES.md` con su fila y
    su tier. Un número sin fila no entra.

### Dependencias y orden

El orden de ejecución es el de §15 (revisado: hembras y movimiento primero).
Cada paso necesita el anterior como termómetro. Los pasos 2–9 tocan el mismo núcleo (`mosquito_submodel.cpp` +
`mosquito_state.hpp`) y **no se paralelizan entre sí**. **El esquema de configuración
no se paraleliza en una rama separada**: el **Paso 4** (todas las claves nuevas) precede al Paso 3 (sangre), al Paso 5
(cascada), al Paso 7 (acuático) y al Paso 8 (machos), y dejar el esquema en otra rama
dejaría a esos pasos sin configuración y con constantes compiladas, que
`test_no_constants_guard.py` prohíbe. Lo único que puede desarrollarse en paralelo es
el **arnés de escenarios (Paso 0)**, que no toca el núcleo del motor.

--------------------------------------------------------------------------------

<!-- Provenance: Indicates initial structural drafting via EGM. -->

*Drafted with EGM*

## Apéndice A — Mapa de escenarios E00–E18

Cada escenario es un fichero `scenarios/E00.json … E18.json` (**19** ficheros; E10 lleva
sus tres variantes **dentro** del mismo JSON, en `variants`), referenciado por la clave
de dataset `scenario:<id>` del manifiesto (§13.2): el manifiesto declara **una sola**
clave, la del escenario que se ejecuta, y el generador copia el JSON del repo al
directorio del AOI (`<data-root>/<aoi>/scenarios/`). La columna **expectación** es la
que el test compara; cuando lleva banda de tolerancia, la banda se declara en el
propio JSON, con su unidad y su tier. Las coordenadas son **metros proyectados del
AOI** (§13.3).
| ID | Modo | Qué ejercita | Escenario | Expectación |
|---|---|---|---|---|
| E00 | `gate` | Mínimo del arnés | 1 mosquito sembrado, 1 día | posición, sexo y estado tras 1 día, verificables por construcción; el manifiesto declara **una sola** clave `scenario:E00` |
| E01 | `gate` | Cadena mínima: una hembra, una persona a 200 m, sin criadero | 1 hembra en (x, y) en metros; `humans` con 1 persona a 200 m; `aquatic = []`; 3 días | 0 comidas (la distancia no permite el contacto); **ninguna** oviposición; la hembra entra en inanición al día 3 |
| E02 | `report` | El mosquito **no** está donde el humano | 1 hembra, persona a 2 000 m | **banda derivada del modelo**: la longitud de trayectoria por noche no puede superar `daily_move_capacity_m` = 590 m, y el desplazamiento neto por noche no puede superar 2 × `exploration_range_m` (= 200 m con el valor por defecto de 100 m, §4). Se publica (`report`), **no** es criterio de fallo: la llegada depende de la dirección del paseo. La banda anterior **[1 410, 2 000] m se retira**: es inalcanzable |
| E03 | `gate` | Multipicadura y Contacto | N hembras con `probing_success_rate` congelado, personas en contacto | comidas = N·p·P(contacto); el ledger muestra **varios** eventos por noche (nº de eventos = nº de picaduras, no el agregado por celda) |
| E04 | `gate` | Comida parcial | 1 hembra, 1 persona, `blood_volume_ul` sembrado por debajo del umbral | sigue en `HOST_SEEKING` esa noche; el ciclo gonotrófico **no** arranca |
| E05 | `gate` | Umbral alcanzado | 2 hembras: una parcial + una completa | el ciclo arranca; el lote de huevos ∝ volumen acumulado (`eggs_per_ul` = 223) |
| E06 | `gate` | Primer ciclo (`PRE_GRAVID`) | 1 hembra que necesita 2 comidas | hacen falta 2 comidas; se respeta `first_cycle_target_ul` (0,8 µL) |
| E07 | `gate` | El criadero gana al hospedero | 1 hembra, 1 criadero a 300 m, 1 persona a 2 000 m | **dos aserciones**: **(A)** la emergencia ocurre en la **posición de la madre**, no en el centro de la celda (cierra el **Paso 7**); **(B)** la hembra va al **hábitat**, no al hospedero (cierra el **Paso 9**; la oviposición natal no está modelada: §16.1) |
| E08 | `gate` | Dos hembras, dos personas | 2 hembras en celdas distintas, 2 personas | cada una pica a la persona que le corresponde por **ruleta ponderada por `pref`** entre las que hay dentro de su radio de percepción, con la **distancia como criterio de tramo** (no de puntuación de atracción); **no** hay "celda ganadora"; `human_id` distintos y estables |
| E09 | `gate` | Vector infeccioso | 1 hembra `infective=true`, ≥3 personas | varias picaduras infecciosas; P(>1 persona infectada) > 0; una picadura infecciosa infecta **como máximo** a la persona picada |
| E10 | `report` | Sensibilidad a los radios | tres variantes en el mismo JSON (`variants`) | activación 50/100/200 m; olfativa 10/30/70 m; visual 0,25/0,72 m — cuantifica el peso de cada tramo de la cascada; los valores por defecto son los **verificados** |
| E11 | `gate` | Ventana postprandial | 1 hembra alimentada el día 0 | **primer** intento de comida tras alcanzar el objetivo **no antes de 12 h** (`blood_meal_refractory_days` = 0,5 d), banda [12 h, 12 h + 1 fase]; la **reapertura progresiva** (7 % @40 h, 27 % @48 h, 68 % @72 h) se publica con banda declarada y tier **[EP]** —"estimación propia, sin respaldo directo"— y **no** es criterio de fallo |
| E12 | `gate` | Arresto ovárico en seca | ráfaga de lluvia y después seca (`env.nc`) | fracción de hembras alimentadas sin pasar de estadio 2 ∈ **19,23–34,85 %** (*coluzzii*) **[P]**: la banda es el **dato publicado**, no un parámetro del escenario; el escenario congela la racha de secas y **mide** la fracción, que se compara contra la banda |
| E13 | `report` | Machos y oferta de apareamiento | 100 hembras + 100 machos recién emergidos en **una celda de 1 km²** y **un único sitio de enjambre alcanzable por todos ellos** (con `w_suelto` = 1, una fracción de machos puede quedar suelta: el escenario lo mide) (`dist ≤ male_move_capacity_m` = 50 m para los 200 agentes, de modo que todos comparten `swarm_site_id`); `swarm_markers_per_km2` **fijado en el escenario** | los machos se **asignan** a los sitios dentro de su alcance; la oferta se calcula con la fórmula de §8.1 y los valores por defecto (`p_mate_male_fraction` = 0,072 [P]; `female_attendance_rate` = 0,1033 [P]): con 100 hembras y 100 machos, `cupos(s)` = 100 × 0,072 = **7,2 parejas/noche** frente a 100 × 0,1033 = **10,33 hembras presentes** ⇒ `p(inseminada \| hembra)` = 0,1033 × (1 − exp(−7,2/10,33)) = **0,0518** ⇒ **≈ 85,2 % de hembras sin inseminar tras 3 noches** [EP] (derivado de la aritmética de §8.1; la banda de tolerancia la calcula y escribe el implementer a partir de esta aritmética). El 85,2 % es una **cota inferior** de la fracción sin inseminar: `M_disp` decrece con los machos ya inseminados. La banda publicada 22,3–52,8 % **se retira**: no es derivable de la fórmula |
| E14 | `gate` | Machos presentes, enjambre todavía no | 1 hembra en celda con machos recién emergidos (antes de su primera ventana de enjambre) | **no** queda inseminada (los machos asignados a un sitio no entran al enjambre antes de la ventana); se emite la alarma `hembras_sin_inseminar`; la hembra asiste al sitio si está dentro de su alcance |
| E15 | `gate` | *Swarm killing* | campo de marcadores + 1 enjambre en la aldea | matar los machos **asignados** al marcador deja el sitio sin oferta ⇒ la fracción de hembras sin inseminar sube; **es la prueba de que el campo de sitios es una capa estática y no un número por corrida** |
| E16 | `report` | Contrascenario **ITN al 60 %** | el mismo campo, con ITN al 60 % | el ITN **no** compensa la pérdida de cupos del enjambre; deja por escrito un límite del modelo, no un resultado del modelo |
| E17 | `gate` | **SIT/IIT sobre los cupos por sitio** | machos estériles asignados a los mismos sitios, compitiendo por los mismos cupos | `cupos(s)` baja de forma proporcional al número de machos estériles asignados; la fracción de hembras sin inseminar sube. El modelo **sí** representa este efecto y **no** simula la competencia *intra-enjambre* entre machos estériles individuales (N11, §8.6) |
| E18 | `gate` | Rama de viento: desvío *upwind* y bloqueo nocturno | AOI sintético **con campo de viento** (`u100`/`v100`, cargado por `--wind-field`; §13.1) | el vuelo se **desvía contra el viento** (desvío ±30°, `anemotaxis_rule`, [EP]) y el avance queda **bloqueado** cuando la componente de cola del viento, proyectada sobre la dirección de avance, alcanza la velocidad propia de vuelo (`flight_speed_ms` = 0,225–0,45 m/s, §4) |

## Apéndice B — Cadena de semillas y trampas del catálogo

```
--seed S  (maestro)
   └─ main.cpp:1020   Prng rng(seed_rollout = S + rollout_index)      ← nuevo por rollout
        ├─ engine.cpp:103-105  coord_seed = rng.peek_state()[0]; rng.uniform_double();
        │                      sub_seed   = rng.peek_state()[0]
        │        ├─ CoordinatorModel(coord_seed32)   (ruleta de siembra, foci)
        │        └─ MosquitoSubmodel(sub_seed)       (dispersión, binomial gonotrófico, elección de presa)
        ├─ engine.cpp:303-305  trans_seed = rng.peek_state()[0]; rng.uniform_double()
        │        └─ TransmissionModel::init(trans_seed)  (exposiciones humanas, foci)
        └─ (nuevo) micro_seed = rng.peek_state()[0]; rng.uniform_double()
                 └─ micro-integrador de dos bandas (N4)
```

*   El motor **no conserva** el `Prng` maestro: consume dos dibujos para derivar los
    streams de coordinador y submodelo, y un tercero para el de transmisión. El orden
    importa: la derivación es posicional, no idempotente.
*   El banco acuático **no** usa el stream maestro: usa semillas de producción fijas
    (`model_constants.yaml:276-279`: `aquatic_seed_washout=789`,
    `aquatic_seed_stage_mortality=42`, `aquatic_seed_larva_mortality=123`),
    re-siembraadas por llamada (`aquatic_cohort_bank.cpp:204, 227, 298`).
    Consecuencia (estado actual): los streams acuáticos son **idénticos entre
    escenarios**; un escenario no puede variar la mortalidad acuática por semilla.
    **Resuelto en el Paso 0**: el stream acuático se deriva del `Prng` maestro (igual
    que el micro-integrador, `engine.cpp:103-105, 303-305`), y el cuarto `peek_state()`
    se añade para el micro-integrador. Con ese cambio, "una semilla maestra" es cierto
    para los cuatro streams.
*   Cada rollout usa un `Prng` nuevo; reutilizar uno cambia los sub-streams derivados.
*   Los rollouts multihilo son reproducibles bit a bit **con el mismo binario**, no
    entre binarios: los golden hay que regenerarlos en el mismo PR que el cambio de
    API.

**Trampas del catálogo que el arnés debe esquivar**:

| Trampa | Detalle | Contención |
|---|---|---|
| Validación de catálogo | `validate_completeness()` comprueba **todos** los ficheros declarados: el manifiesto declara **una sola** clave de escenario (`scenario:<id>`) con **un** fichero; el generador escribe los 19 JSON, pero el manifiesto cuelga **sólo** el que se ejecuta | el arnés resuelve `files[str(id)]` de la clave `scenario:<id>`, nunca "el primero"; un escenario sin clave declarada es un error explícito |
| Deriva de identidad | `"scenario"` no es una salida de un loader: `downloadable_datasets()` / `catalog_status()` la ignoran | añadir `SCENARIO_ARTIFACT` a `catalog.py`, junto a `INGEST_ARTIFACTS` |
| Clave del campo de sitios | `swarm_sites` tampoco es una salida de un loader: es un artefacto propio (JSON con `{id, x_m, y_m, marker_type}`), **generado por el Paso 8** de forma determinista a partir de `swarm_markers_per_km2` con semilla explícita | mismo camino que `scenario`: artefacto en el catálogo (`catalog.py`) y clave de manifiesto, resuelto por `wrapper.py`; si la clave **no** está, el campo de sitios es vacío y los machos nacen "sin sitio" (§8.2) |
| `dynamics` con tipos distintos | Python escribe una cadena, C++ lee un int ⇒ siempre 0 | el productor (`mal-core/src/mal_core/ingest/env.py:88`) escribe el **int**; el gpkg sintético escribe int `0/1` |
| Suelo de potencial | el motor descarta parches con `potential` < 0,01; la ventana de Accra contiene uno en 0,00978 | el generador aplica el mismo suelo e informa del número de descartes |
| Geometría de celda | las celdas de Accra son 992,8 m × 997,5 m; la rejilla sintética es 1000 m | remuestrear, nunca copiar una feature sin recalcular `row`/`col`/`potential`; la conversión metros→celda usa `resolution_m` y `geodesy.earth_radius_m` = 6 371 008,8 m |
| gpkg no reproducible byte a byte | GeoPackage sella `gpkg_contents.last_change` | comparar **contenido** (tabla de atributos ordenada), no bytes; la comparación byte a byte del Nivel 5 excluye los gpkg |
| Golden fixtures | cualquier cambio de la API de siembra o del SoA cambia los bytes dorados | regenerar con `make_golden_fixtures.py` en el mismo PR; el golden sigue siendo 8×8 y el arnés sintético es aparte: **los dos generadores de AOI no se mezclan** — el arnés usa el AOI 10×10 de `make_synthetic_aoi.py` (§13.1) |
| Ruta protegida | `data/` es protegida y `data/**/*.json` está en `.gitignore` | generar bajo `runs/synthetic/` + `--data-root`; los JSON de escenario viven en `mal-core/src/mal_core/abm/tests/scenarios/`, donde se revisan en un PR, y el generador los **copia** a `<data-root>/<aoi>/scenarios/`: el arnés **no** lee del repo en runtime (§13.2) |
| Defaults que estorban | `--seeding-mode random-viable`, `--human-seeding-mode random-viable`, `initial_human_prevalence` | el fichero de escenario sobrescribe los tres explícitamente (`SCENARIO`; `none`; prevalencia 0) |
| Viento ausente | el campo de viento es opcional (`--wind-field`): sin él, viento 0 | el AOI sintético **no** declara el dataset de viento en los escenarios salvo **E18**, que lo carga para ejercitar la rama (desvío *upwind* y bloqueo nocturno, §4, §13.6); en el resto, anemotaxis y bloqueo inactivos: salida documentada, no un fallo |
| No-determinismo de OpenMP | los rollouts paralelos no comparten más que el sistema de ficheros; cada uno tiene su `Prng` | una aserción por rollout; multi-rollout sólo para estadística de ensembles |
