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
2.   **Cero picaduras humanas en 30 días.** La mosquito busca *celdas*, no personas:
    `detect_host_cell` elige la celda con más atracción y `step_toward_host` da **un paso
    de 500 m** (`host_flight_step_m`), redondeado al entero (`src/host_seeking.cpp:307`):
    con objetivo diagonal el desplazamiento es 0,354 celdas y **se pierde**. La
    atracción decae con `exp(-d/300)`, de modo que la propia celda siempre gana si tiene
    ganado: la mosquito come pollos (1 117 por celda de 1 km en la franja costera —
    cifra sin fuente ni fecha en el repositorio, pendiente de verificar) y nunca llega
    a la gente (a 1,0–2,8 km). Consecuencia: `pref.human = 0.99` nunca llega a
    aplicarse.
3.   **No hay malaria.** Sin picaduras no hay `infectious_meals`; `S_H` = 40 255
    susceptibles no se mueve.

Además: `feeding_success[si] = 1.0f` se fija siempre (`src/mosquito_submodel.cpp:829`),
`feeding_success_rate` (0,825) **se carga pero el motor no lo consulta** (la transición a
`BLOOD_FED` es determinista) y el `max_delta` de la configuración de picadura tampoco.

### P2 — El modelo no puede representar la biología que la literatura sí mide

La configuración actual y la máquina de estados contradicen o no pueden expresar
mediciones publicadas:

| Lo que el modelo hace hoy | Lo que la evidencia mide | Consecuencia |
|---|---|---|
| Atracción por celda con decaimiento exponencial (`host_seeking_scale_m` = 300 m) | La pluma de olor es intermitente y filamentosa: incluso las hembras que aterrizan pasan el 61,4 % ± 3,9 % del tiempo de vuelo fuera de sus límites teóricos | Trayectorias artificialmente directas; el gradiente continuo no representa el mecanismo real |
| Radio de atracción de 1 500 m por celda | Ningún paper mide 1,5 km de atracción; los radios documentados son 100 m (activación CO₂), 30–70 m (olfativa), 25–72 cm (visual), 10–20 cm (aterrizaje) | La mosquito nunca "siente" a un humano hasta muy cerca |
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
*   El tamaño de la población humana debe derivarse del manifiesto, y el `human_id` debe ser
    **determinista y estable** (`celda × slot + slot`) desde el primer día, o cualquier
    optimización posterior (materializar sólo a los humanos picados, o muestreo
    estratificado con pesos) rompe el contrato de observación.

### P4 — El pipeline de verificación no existe

No hay arnés de escenarios sintéticos. Sin él, cualquier cambio de la ley de movimiento
es indistinguible de una regresión: los comparadores actuales (scorecard por corrida) no
guardan historial ni `max_delta`, y la línea base de calibración se desplazará en cada
paso.

## Goals

*   **G1 — La cadena cierra y es observable a nivel individual.** En una corrida el
    motor debe registrar picaduras humanas, con mosquito identificable, persona
    identificable, fase, volumen tomado, resultado del sondeo y transmisión aplicada.
*   **G2 — La decisión de picar se toma sobre individuos.** La mosquito elige una
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
    como tales y no se tocan. Cuando dos fuentes publicadas **se contradicen** (el
    porcentaje de machos de un enjambre que se aparea por noche: 0,072 en *gambiae* s.s.
    frente a 0,084–0,25 en *coluzzii*), el conflicto se declara y ambas cotas entran en
    la sensibilidad.
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
    el estado individual cuesta ~58 B por persona ⇒ 2–4 GB por corrida a escala de
    país. Se optimiza después; los escenarios sintéticos empiezan con poblaciones
    pequeñas (10×10 / 100×100 celdas).
*   **N4 — No se reentrena el surrogate ni se reutilizan checkpoints.** Los checkpoints
    entrenados con bandas normalizadas ≤3.0 no son reutilizables (memoria #195); el
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
*   **N11 — No se simulan SIT/IIT.** El modelo no puede representar la competencia entre
    machos estériles individuales dentro de un enjambre. Se documenta como límite, con
    un escenario de contrascenario (E16). El *swarm killing* **sí** se puede
    representar, porque el campo de marcadores es discreto.
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
*   **Q-C — "Percepción" como radio o como sensibilidad**: la evidencia da radios por
    tramo; cuánto pesa cada tramo en la decisión de picar queda como sensibilidad del
    paquete sintético (escenario E10).
*   **Q-D — Cifra de pollos por celda**: el diseño previo fijaba 1 117 pollos por celda de 1 km
    en la franja costera como "cifra sin fuente ni fecha en el repositorio, pendiente".
    Hay que localizarla o retirarla antes de fijar la mezcla presa/fauna.
*   **Q-E — Cifra de "human_total"**: la referencia del ODD a ~32 M no es utilizable; el
    valor por AOI debe derivarse del manifiesto. Falta el nombre del campo y su
    unidades.
*   **Q-F — Filopatria natal: hueco no cerrable con la literatura actual.** No existe
    ninguna medición de retorno al sitio natal en *Anopheles*. La decisión de diseño
    (no implementarla) está tomada, pero queda un **hueco científico**: la primera
    estimación de filopatria natal en *A. coluzzii* sería aplicando el método de
    parentesco por genoma completo (Jasper et al. 2019) a los WGS de *A. coluzzii* de
    Obuasi (Nagi et al. 2025), **con control de las inversiones cromosómicas** (que ese
    mismo trabajo demuestra que confunden la estimación de parentesco). Es trabajo de
    investigación, no de modelado.
*   **Q-G — Tasa de apareamiento de los machos: dos fuentes que no se reconcilian.**
    0,072 ± 0,0095 (*gambiae* s.s., Malí) frente a 0,084–0,25 parejas por macho
    (*coluzzii*, Burkina Faso). La diferencia es de un factor 4 y no hay publicación que
    la resuelva. Mientras tanto, la configuración lleva las dos cotas y la
    sensibilidad recorre el intervalo. Falta decidir si el valor por defecto es el
    *coluzzii* (más alto, menos evidencia) o el de *gambiae* s.s. (más bajo, más
    replicable).
*   **Q-H — Campo de marcadores de enjambre: ¿de dónde sale?** La literatura da la
    estructura (3–12 enjambres por compuesto, 11–19 m de separación, 2,87 m de altura,
    ≈27 min, Moran's I = 0,2) pero no un mapa para Ghana. Las opciones son derivarlo
    del patrón de asentamiento (decisión heredada del diseño previo) o medirlo; la primera es un [EP]
    con estructura publicada.

## Critical User Journeys (CUJs)

### CUJ 1 — Un mosquito encuentra y pica a una persona concreta

*   **Given**: AOI sintético 10×10 con una persona a 200 m de la posición inicial del
    mosquito; `pref.human` alto; sin crías.
*   **When**: la noche avanza por las fases activas del mosquito.
*   **Then**: la hembra se aproxima por tramos (exploración → activación a 100 m →
    orientación olfativa → aproximación visual), recibe el micro-integrador de dos
    bandas al cruzar los 70 m y el 0,72 m, alcanza la persona, sortea
    `probing_success_rate`, y el ledger registra un evento con id de mosquito, id de
    persona, fase, volumen tomado y resultado del sondeo. Si el volumen acumulado no
    alcanza el umbral, **vuelve a `HOST_SEEKING` la misma noche** y el ciclo gonotrófico
    no arranca.

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
    tasas medidas eso es falso— sino la **tasa de inseminación medida**: con
    `p_mate = 0,072` (Diabaté, *gambiae* s.s.) la probabilidad por noche de una hembra
    sin inseminar es `1 − exp(−0,072)` = 6,9 % ⇒ **≈19 %** de hembras siguen sin
    inseminar a las tres noches; con `p_mate = 0,084–0,25` (*coluzzii*) el rango es
    **≈8–21 %**. El diagnóstico de alarma compara el valor simulado contra este
    intervalo publicado, y **emite** cuando lo supera, no cuando llega a cero.
*   **Por qué esto importa**: el enunciado original de este CUJ ("la oferta cubre la
    demanda, 0 sin inseminar") era una expectativa sin base publicada. La forma
    correcta de expresarlo es contra el rango medido.

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

--------------------------------------------------------------------------------

## Technical Plan (Architecture)

### 0. Principios e invariantes

Cuatro reglas gobiernan todo el diseño:

1.  **La unidad de decisión es el individuo; la celda es un outputs.** Ninguna decisión
    (a quién pica, dónde pone, dónde emerge) se toma sobre un agregado de celda. La
    agregación a 1 km² sobrevive sólo en tres sitios: la competencia acuática
    (Beverton-Holt), el COG de estado y las series de salida.
2.  **Ninguna magnitud se introduce sin respaldo.** Cada parámetro nuevo lleva su
    cifra medida y su referencia; los que no la tienen se declaran `[EP]` y no se
    "mejoran". La lista completa se aplica sin cambios (estaba en el apartado 9.7 del
    diseño previo, cuyo contenido se conserva aquí sin cambios).
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

Se añade a la clase `AOI` (en `aoi.hpp`) la transformación inversa
`xy_to_lonlat(x, y)` y `lonlat_to_xy(lon, lat)`, de modo que la conversión a grados
usa la misma ruta que la lectura del `host_static.nc` y no una segunda convención.

El `lon`/`lat` actual del SoA pasa a ser un valor **derivado** que se recalcula al
escribir salidas, no un estado de la simulación.

### 2. Capa humana: de rejilla SEIR a población individual

`HumanCompartmentGrid` (per-cell `S_H/E_H/I_H/R_H` + colas de cohorte) se sustituye
por una población individual en Structure-of-Arrays, en un módulo nuevo
`human_population.hpp` / `human_population.cpp`:

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

*   **`human_id` determinista y estable**: `cell_id × SLOTS_PER_CELL + slot`. Es la
    condición para que más adelante se pueda materializar sólo a los humanos picados, o
    hacer un muestreo estratificado con pesos, sin romper el contrato de observación.
*   **Número de personas por celda**: derivado del `human_total` que ya calcula
    `mal-core/src/mal_core/ingest/hosts.py` (`results["human_total"]`) y del raster de
    `host_static.nc`, repartido por celda con la densidad residencial. En los escenarios
    sintéticos, un override explícito por celda.
*   **Temporizadores discretos**: la cola de cohorte por edad se conserva (el modelo ya
    la usa para evitar la distorsión de duración exponencial) pero **por individuo**:
    `timer` cuenta los días restantes y se decrementa cada día. Coste: 4 B por humano
    más el estado.
*   **Los compartimentos agregados pasan a estadísticas derivadas**: `compute_stats()`
    agrega sobre la población en el momento de escribir salidas. La API pública que
    usan `transmission.cpp` y el CLI (`seed_infections`, `seed_random_viable_foci`,
    `seed_outbreak_cluster`, `advance_day`) se mantiene con la misma semántica, pero
    backed por individuos: sembrar "5 infecciosos en la celda (r,c)" siembra 5
    individuos concretos con `state = INFECTIOUS`.

**Coste**: ~58 B por persona ⇒ 2–4 GB por corrida a escala de país. Se acepta en esta
iteración (Non-Goal N3); los escenarios sintéticos usan poblaciones de 10×10 a 100×100
celdas.

### 3. Capa vectorial: campos nuevos en `MosquitoSoA`

`mosquito_state.hpp` gana:

| Campo | Tipo | Papel |
|---|---|---|
| `pos_x`, `pos_y` | float | posición métrica continua (§1) |
| `blood_volume_ul` | float | volumen de sangre acumulado (µL) |
| `ovarian_stage` | uint8 | pre-gravídica / alimentada / semi-grávida / gravídica |
| `gonotrophic_arrest` | uint8 | 1 = en `ARRESTED` (época seca) |
| `days_since_target_reached` | int32 | reloj de inanición propio (no se reinicia con comidas parciales) |
| `inseminated` | uint8 | 1 = inseminada (monandria); en el macho, marca el cupo consumido (§8) |
| `nights_uninseminated` | int32 | diagnóstico de la alarma de enjambre |
| `age_days` | int32 | **sólo diagnóstico** (opción d de la revisión 2 del diseño previo) |
| `swarm_site_id` | int32 | **sitio de enjambre asignado al macho** (−1 = enjambre local efímero en su posición de eclosión); en la hembra, el sitio que percibe (§8) |

**El campo `home_x`/`home_y` que esta tabla contenía en la primera redacción **se
elimina**. La revisión de filopatria natal (ver §16) **no encontró ninguna medición
publicada** de retorno al sitio natal en *Anopheles*, y el mecanismo que la literatura
sí documenta (preferencia olfativa por el habitat natal, 31,6–37,5 % de los huevos en
agua natal, Kemibala 2026) es un **sesgo por tipo de habitat**, no una distancia a una
coordenada. La información "dónde se cría" no se pierde: la lleva la cohorte
acuática (§9), que es donde se origina.

Cada campo exige las tres operaciones que ya exige el SoA actual: `push_back` en el
constructor, `std::swap` en la compactación (`mosquito_submodel.cpp:152` y alrededores)
y `resize` (`mosquito_submodel.cpp:180`). El olvido de uno de los tres corrupte el
SoA en silencio: es el riesgo mechanically más probable de la fase 3, y por eso el
plan exige un test explícito de round-trip de compactación.

`feeding_success` (float, 1.0/0.0) **deja de ser el portador del resultado del
sondeo**: pasa a ser un contador de comidas de la noche, y el resultado del sondeo
viaja en el ledger de eventos.

### 4. Ley de movimiento en cascada

Sustituye al campo de atracción por celda (`host_seeking.hpp`: `compute_attraction`,
`cell_attraction`, `detect_host_cell`, `step_toward_host`) y al kernel de oviposición
(`oviposition_seeking.cpp`: `compute_attraction` con `potential × exp(-d/scale)`).

El módulo se reescribe como una máquina de estados por tramo de distancia, con
radios **por especie** tomados de `species.<fila>`:

```
                    ┌──────────────────────────────────────────┐
   fase NIGHT ────▶ │ EXPLORACIÓN (sin estímulo)               │
                    │  paseo aleatorio correlacionado           │
                    │  + casting transversal al viento         │
                    └───────────────┬──────────────────────────┘
                                    │ d ≤ co2_activation_radius_m (100 m)
                                    ▼
                    ┌──────────────────────────────────────────┐
                    │ ACTIVACIÓN (CO₂ pulsado, sin dirección)  │
                    │  → orientarse al viento                  │
                    └───────────────┬──────────────────────────┘
                                    │ d ≤ olfactory_radius_m (30–70 m)
                                    ▼
                    ┌──────────────────────────────────────────┐
                    │ RASTREO DE PLUMA                         │
                    │  anemotaxis optomotora contra el viento  │
                    │  temporizador de memoria olfativa →      │
                    │  casting si se pierde la pluma           │
                    └───────────────┬──────────────────────────┘
                                    │ d ≤ visual_radius_m (0,25–0,72 m)
                                    ▼
                    ┌──────────────────────────────────────────┐
                    │ APROXIMACIÓN VISUAL (sólo si hay olor)   │
                    │  vector hacia la silueta                 │
                    └───────────────┬──────────────────────────┘
                                    │ d ≤ terminal_radius_m (0,10–0,20 m)
                                    ▼
                    ┌──────────────────────────────────────────┐
                    │ CONTACTO → aterrizaje                     │
                    │  (calor + humedad + olor) → COMIDA        │
                    └──────────────────────────────────────────┘
```

Reglas de la ley:

*   **El "sentido" es la distancia al hospedero más cercano dentro del radio de
    percepción**, no una puntuación de atracción. La preferencia por tipo de presa
    (`pref`) entra en el sorteo, no en el gradiente.
*   **Progreso neto contra el viento bloqueado**: si la velocidad del viento ambiente
    supera la velocidad propia de vuelo, el mosquito no avanza contra el viento. El
    umbral se calcula en tiempo de ejecución con la velocidad configurada y el viento
    del día; **nunca hardcodeado**, porque la velocidad propia de la hembra en busca no
    está medida.
*   **La pluma es intermitente**: el estado de "rastreo" se pierde con probabilidad al
    salir de un filamento, y dispara el *casting*. No hay decaimiento exponencial
    continuo.
*   **Velocidad**: `flight_speed_ms` por especie (0,225–0,45 m/s en *coluzzii*). El
    desplazamiento **no** es velocidad × duración completa de la fase: con fases de
    4 h daría 6,5 km, frente a una dispersión medida de 486–695 m/día. El macro-paso
    se acota por un **presupuesto de tiempo de vuelo dirigido** (~1 h/día; ver §5), que
    es lo que hace que la velocidad medida y el MRR medido dejen de contradecirse.
*   **Restricción de cercanía al sitio de cría**: en *arabiensis*, **< 60 %** de los adultos
    se movieron más de 50 m del sitio larvario (Tioyé 2026) ⇒ más del 40 % permanece
    a menos de 50 m. El radio de exploración por defecto debe ser de ese orden, no de
    kilómetros. En *A. gambiae* s.l. el 70 % de los recapturados apareció en otra zona
    (Diallo 2026), lo que acota la dispersión lejana.
*   **No hay filopatria natal que modelar**: Thomas et al. 2013 derivan sus curvas de
    dispersión *"assuming no philopatry"*. La ausencia de un comportamiento medido es
    un motivo para **no** implementarlo, no para implementarlo con un prior.
*   **El macro-paso no puede resolver la maniobra terminal** y no debe intentarlo: a
    1 s de paso, el mosquito avanza 22–45 cm, más que el radio terminal entero
    (10–15 cm). El micro-integrador cubre sólo la banda fina (§5).

La condición de parada contra el viento usa el **campo de viento del día**
(`wind_field.cpp`, ya cargado con `--wind-field`); si no hay campo de viento cargado, el
viento ambiente es 0 y la restricción no aplica — con el comportamiento documentado en
la salida.

### 5. Base temporal: macro-paso acotado + micro-integrador adaptativo de dos bandas

El motor no tiene hoy reloj de fase ni sub-pasos: el día es un único
`for p < PHASE_WEIGHT_COUNT`. La cascada sensorial abarca cuatro décadas de escala
(100 m → 10 cm) y no puede representarse con un único integrador.

**Restricción geométrica.** El paso del integrador no puede superar el radio que
intenta resolver. Con la velocidad propia medida (0,225–0,45 m/s) y el radio terminal
medido (0,10–0,15 m), un paso de 1 s avanza 22–45 cm: **mayor que todo el radio
terminal**, luego con 1 s la aproximación terminal es literalmente irresoluble.

**Restricción temporal.** El evento más rápido medido en la literatura es el giro en
el punto más cercano (desaceleración de 40 a 30 cm/s en los 0,08 s previos, aceleración
angular de 12 500 °/s² medida entre 0,04 s antes y 0,04 s después; Hawkes & Gibson
2016). Nyquist ⇒ `dt ≤ 0,08 s`; para tener varias muestras sobre el evento, `dt`
debe quedar por debajo de 0,1 s.

**Frecuencias empíricas.** 50 Hz (Hawkes & Gibson 2016, 20 ms por desplazamiento;
Carnaghi 2023), 25 fps / 0,04 s (Spitzen 2013), 90 fps (Cribellier 2018), 60 fps (Hinze
2021), 68 fps (Batista 2019), 0,01 s (Zuo 2026 en *Aedes*). Precedente de modelo:
Cribellier et al. 2026 simula el enjambre con `Δt = 0,02 s`, *"the same as the empirical
video frame rate"*.

Diseño (decisión D1 = a, con el paso temporal corregido por la evidencia):

```
por día
  por fase p (DAY, EVENING, NIGHT, DAWN) con actividad > 0
    ── macro-paso ─────────────────────────────────────────────
    para cada mosquito activo en fase p:
      1. elegir régimen de movimiento (cascada, §4)
      2. t_vuelo = min(t_fase, presupuesto_de_vuelo_dirigido)
         desplazamiento = velocidad × t_vuelo
      3. si NO está en el micro-integrador:
           aplicar desplazamiento macro; comprobar si ha entrado
           en la banda olfativa (≤ 70 m)
      4. si está en la banda olfativa:
           integrar con dt = 0,25 s hasta agotar la fase o el tiempo de vuelo
      5. si ha entrado en la banda terminal (≤ 0,72 m):
           integrar con dt = 0,05 s (o el resto de la fase)
    ── fin macro-paso
```

*   **Macro-paso**: un paso por fase, con la duración de fase en la configuración
    (`phase_duration_hours`, hoy implícita) y **acotado por un presupuesto de tiempo de
    vuelo dirigido** (`directed_flight_budget_h`, ~1 h/día). Sin ese tope,
    velocidad × fase = 6,5 km/día, que contradice el MRR medido por un orden de
    magnitud. El presupuesto es el número que reconcilia velocidad y distancia.
*   **Micro-integrador de dos bandas** (reemplaza a los "ticks de 1 s" de la primera
    redacción):
    *   **Banda terminal** (≤ radio visual 0,72 m): `dt = 0,05 s`. El paso resultante
        (1,1–2,3 cm) queda por debajo de la distancia media de cierre al blanco
        (5,4 ± 0,85 cm) y del radio terminal (10 cm). Cubre el ciclo de dipping
        (0,43–0,51 s) y el evento de giro (0,08 s).
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
    | 0,02 (precedente) | 720 000 | 0,72 s | 7,2 s | 72 s |

    Con `N_dentro` realista en la banda olfativa (≈ 4,5–45 con 10²–10³ adultos y 10⁴
    personas; 45–450 con 10⁵ personas, sobre un AOI de 3 416 km² y R = 70 m), el
    coste a 0,05 s es **0,13–13 s/día** (tolerable) y a 0,02 s **0,3–32 s/día**. Si el
    micro-integrador corriera **globalmente**, 0,02 s daría 7–72 s/día: inaceptable.
    **El coste no es lo que mata los ticks de 1 s — la resolución es lo que los mata.**
    La condición de funcionamiento es que el micro-integrador sólo corra dentro de la
    banda de percepción.
*   **Memoria olfativa**: no hay valor primario en *Anopheles*. Lo único medido es que
    el ORN de CO₂ de *coluzzii* rastrea **pulsos de 1 s separados por 1 s** (Majeed
    2017), con la latencia de activación sólo en figuras ⇒ **[NR]** en segundos. Los
    300 ms (Dekker 2005) y 0,03 s (Dekker & Cardé 2011) son de *Aedes* ⇒ **[P]**. El
    "≈2 s" que circulaba en la síntesis secundaria **se elimina**: no tiene fuente.
    El valor de diseño es **0,5–0,9 s** (segmentos de *cast*, Cummins 2012).
*   **Latencia de respuesta a ráfaga de viento**: no hay medición publicada (la
    literatura del viento trata tasas, no latencias) ⇒ el integrador no necesita
    resolución sub-segundo para capturar el viento.
*   **Gate de aterrizaje por velocidad, no por radio**: `v < 50 mm/s` sostenida 3 s
    (Hinze 2021) en lugar de una distancia fija.
*   **Determinismo**: el consumo de RNG del micro-integrador debe ser determinista y
    reproducible; los draws usan un stream derivado del `uid` del mosquito, para que el
    orden de recorrido no altere el resultado.
*   **Deuda de implementación**: el estado del motor está en celdas de 1 km; la banda
    fina exige coordenadas continuas **a escala métrica** en el SoA (§1).

### 6. Pickup de presa, multipicadura y fisiología de la sangre

La transición actual (`mosquito_submodel.cpp:757-779` y `:855-862`) es
determinista: `if (picked != nullptr) → BLOOD_FED`. Se sustituye por:

```
PROBING
  ├─ sortea probing_success_rate (por especie, 0,465–0,99)
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
*   **Primer ciclo (pre-gravídica)**: `first_cycle_target_ul` > `blood_meal_target_ul`;
    hacen falta dos comidas. El motor ya distingue `first_cycle_days` (4,0) de
    `cycle_duration_days` (2,0).
*   **Reloj de inanición propio**: `days_since_target_reached` no se reinicia con las
    comidas parciales; el `gonotrophic_timer` actual no sirve (se pone a 0 en cada
    transición).
*   **El descanso post-prandial** (`resting_duration_days` = 0,5) sólo se dispara al
    alcanzar el objetivo; una comida parcial no oviposita.
*   **Lote de huevos ∝ volumen acumulado** (MBITES), no `binomial(egg_batch_n, p)`.
    Esto **rompe la invariante de validación** `0 < min <= mean <= max <= n` de
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
    *gambiae* s.s.; y `aestivation_supported` por especie (`true` para *coluzzii*,
    `false` para *gambiae* s.s., que no estiva).
*   La **supervivencia en arresto** es propia (`arrested_daily_survival`), muy superior
    a la basal de 0,87/día: la literatura da hasta 212 días de estivación. Una hembra
    en `ARRESTED` no muere a los 7 días.
*   El **disparador es la racha de días secos de la celda**, no el calendario: es el
    mismo disparador que activa el estrés acuático.

### 8. Apareamiento y enjambres (macho-individual con sitio asignado; enjambre, agregado por sitio)

Los machos son **individuos en el SoA** — el SoA ya los guarda (`mosquito_state.hpp:37`,
`sex` = 0 MALE / 1 FEMALE) y el ciclo gonotrófico los excluye
(`mosquito_submodel.cpp:569`), de modo que no comen sangre ni ponen huevos. Lo que hoy
**no** existe es su conducta: se mueven con el kernel de dispersión de la hembra
(`adult_dispersal`, `mosquito_submodel.cpp:1010`, sin filtro de sexo) y mueren con su
tasa (0,87, hoy compartida).

Esta sección define esa conducta: **cada macho lleva un sitio de enjambre asignado, y
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
| Presupuesto de movimiento | dispersión neta **medida por experimento**, no tasa diaria | **40–549 m** en 7 días (*coluzzii*); media **85,7 m** y **ninguno más allá de 100 m** (*arabiensis*) | Epopa 2017; Kaiser 2021 **[P]** |
| Asignación de sitio | en la eclosión, el macho adopta el **sitio persistente más cercano** dentro de su alcance de vuelo; si no hay ninguno, **enjambre local** en su posición de eclosión | `male_swarm_site_range_m` | §8.2 **[EP]** (bandas 100 m / 550 m) |
| Ventana de enjambre | cada noche, en la ventana posterior a la puesta de sol | inicio **18:05–18:45**, duración media **27 min**; **5–33 min** tras la puesta de sol | Ouédraogo 2025; Bimbilé Somda 2018 **[M]/[P]** |
| Entrada en el enjambre | un macho empieza a volar sobre el marcador 2–3 min tras la puesta de sol; otros se unen en 7–90 s | t = **46 ± 8 s** | Poda et al. 2024 **[M]** |
| Fidelidad | el macho **conserva su sitio** durante su vida; el campo de sitios es estático, luego la permanencia es automática | un macho liberado seguía en un sitio de enjambre **8 días** después | Kaiser et al. 2021 **[P]** |
| Apareamiento | **azar**, no selección sexual; cupos por sitio y noche | 7,2 % de los machos del enjambre por noche (*gambiae* s.s.) / **0,084–0,25 parejas por macho** (*coluzzii*) | Diabaté 2011; Ouédraogo 2025 **[P]/[M]** |
| Reintento | si no se insemina, reintenta cada noche; el esperma dura de por vida | — | — |
| La hembra asiste | la hembra va al **sitio**, con tasa baja | **10,33 %** (47/455) de hembras *tethered* | Diabaté 2009 **[P]** |

**El pseudo-algoritmo** tiene dos piezas: una asignación **al nacer** (discreta, sin
vuelo simulado) y una asistencia **por noche** (agregada por sitio).

```
al emerger el macho m (posición de la madre, x_m, y_m):
    candidatos = { s ∈ sitios : dist((x_m,y_m), s) ≤ male_swarm_site_range_m }
    if candidatos ≠ ∅:
        m.swarm_site_id  = argmin_s dist((x_m,y_m), s)      # desempate por RNG sembrado
        m.inseminated    = 0 ; m.nights_uninseminated = 0
    else:
        m.swarm_site_id  = -1     # enjambre local efímero, en su posición de eclosión

cada noche, dentro de la ventana de enjambre:
    for cada macho adulto m:
        destino = (m.swarm_site_id ≥ 0) ? m.swarm_site_id : enjambre_local(m.pos)
    for cada sitio s (y cada enjambre local e):
        M(s)          = Σ { m : destino(m) = s y m está vivo }
        cap(s)        = (s es un sitio del campo) ? 1 : local_swarm_attendance_factor
                       # valor por defecto 0: no hay medición de asistencia de hembras
                       # a enjambles sin marcador (Kaiser et al. 2021) ⇒ [EP]
        cupos(s)      = M(s) × p_mate × cap(s)              # fracción de machos que
                                                          # se aparea esa noche
        competidoras(s) = hembras no inseminadas dentro del alcance de vuelo de s
        p(inseminada) = 1 − exp( − cupos(s) / max(1, competidoras(s)) )
        sortear las parejas; los machos emparejados quedan inseminados;
        los que no, incrementan nights_uninseminated
```

#### 8.2 — La geometría espacial: el sitio, no la celda

La unidad de la capa macho **no es la celda de 1 km**, sino el **sitio de enjambre**:

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
    2025) **[M]**; modo de tamaño ~100 y ~180 machos, rango real 4–700 (Diabaté et
    al. 2011) **[P]**; 35 enjambres por aldea, media de 50 mosquitos por enjambre
    (Niang et al. 2021) **[P]**.
*   **El radio de vida del macho es menor que una celda**: dispersión media 85,7 m
    (Kaiser et al. 2021) y máximo observado 549 m (Epopa et al. 2017), frente a celdas
    de 1 km ⇒ un agregado anclado a la celda mezclaría machos que no pueden estar en el
    mismo sitio.

**Campo de marcadores: estático y persistente, no un número libre por corrida.** Los
enjambres se forman en **los mismos sitios, a las mismas horas, durante años**
(Somers et al. 2022; Diabaté et al. 2009/2011). El campo se calibra contra los valores
publicados; lo que queda libre es su **densidad** (`swarm_markers_per_km2`), con banda
y fuente declaradas.

**El enjambre local (respaldo).** Cuando un macho emerge a más de
`male_swarm_site_range_m` de cualquier sitio, forma un enjambre **en su propia
posición de eclosión**: es un comportamiento observado ("los machos liberados formaron
sus propios enjambres el día de la liberación, cerca del lugar de liberación"; Kaiser
et al. 2021) **[P]**, pero **no** hay dato sobre si las hembras asisten a esos
enjambres sin marcador ⇒ su capacidad de apareamiento se modela como **cero por
defecto** (`local_swarm_attendance_factor` = 0, **[EP]**), con banda de sensibilidad, y
la hembra que asiste a un enjambre **con** marcador como caso medido (10,33 %) y no
como caso modelado. Consecuencia explícita: un macho que emerge lejos de todo sitio
**no** muere por ello, pero tampoco se reproduce — y esa asymetría es visible en el
diagnóstico.

#### 8.3 — Por qué no la opción 3 (machos con vuelo simulado al enjambre)

La alternativa descartada se documenta aquí porque **es la obvia** y porque un revisor
la va a proponer.

**Opción 3**: cada macho es un agente con vuelo **simulado** hasta el sitio de
enjambre, sobre una rejilla subcelular (≈10 m), con las reglas mínimas que reproducen
el enjambre en un ABM validado con datos de *coluzzii*: **atracción al marcador
visual + alineación al eje del atardecer + evitación de colisión por debajo de 2,5
longitudes corporales** (Cribellier et al. 2026), a velocidad **0,50 ± 0,00 m/s**
(rango 0,24–1,28) y con los macho-flight de Poda et al. 2024 **[M]**.

| Criterio | Opción 2 (elegida) | Opción 3 (descartada) |
|---|---|---|
| Lo que la literatura mide | sitio como determinante (47,6 % de varianza), persistencia de 8 días, entrada en 46 ± 8 s, geometría del enjambre, velocidad de vuelo | las **reglas internas** del enjambre (marcador + atardecer + colisión) |
| Lo que el modelo necesita | el **recuento de machos disponibles por sitio y noche** | lo mismo |
| Granularidad de la posición | sitio (11–19 m de separación) | subcelular (σ 4–10 cm, centro a 0,67 m) |
| Coste | nulo: el SoA **ya** guarda machos individuales | una rejilla y una simulación de vuelo por macho y por noche |
| Coste a escala de AOI | — | con 10⁵–10⁶ machos/noche en un AOI de país es el coste dominante ⇒ rompe NFR-3 (≈2 min en Accra) |
| Refactor | ninguno | exige un **reloj diel dentro del paso diario**: el motor tiene un día, no una ventana de 27 min |
| Lo que aporta a la transmisión | la disponibilidad de cupos por sitio | **nada**: la hembra responde al **sitio**, no a la estructura interna del enjambre (Charlwood 2023, sólo abstract), y la hembra asiste con tasa baja (10,33 %) |
| Riesgo de resultado | bajo: los parámetros proceden de medidas | alto: **no hay dato publicado** que parametrice la attraction ni la fidelidad ⇒ el resultado dependería de parámetros inventados |
| Interventions | *swarm killing* (matar los machos asignados a un marcador) y **SIT/IIT** (machos estériles compitiendo por el mismo cupo) | las mismas |

**Por qué la diferencia importa.** La granularidad del enjambre **no** es el mecanismo
que limita la transmisión: el mecanismo es la **oferta de cupos por sitio y noche**
(published: 7,2 % de los machos del enjambre) y la asistencia de las hembras (10,33 %).
Simular la dynamics interna del enjambre para obtener esa misma oferta es pagar
precisión geométrica donde la biología no discrimina. *Si* el modelo llegara a
necesitar el comportamiento intra-enjambre (por ejemplo, para cuantificar la
**segregación de enjambres entre especies**, χ² = 56,92 — Diabaté et al. 2009, hoy
documentado como mecanismo ausente), la opción 3 es el camino, y el diseño de la
opción 2 lo deja abierto: los machos ya son individuos con un sitio, y una capa de
vuelo se puede añadir **encima** sin tocar el resto.

#### 8.4 — Lo que el agregado por sitio conserva y lo que pierde

**Conserva**: la estructura espacial (dónde hay enjambre y cuánta oferta hay), la
dinámica temporal (los enjambres son de ≈27 min al atardecer y se dispersan a las
19:15), la fenología (lluvia = 0 parejas en el enjambre), la eficiencia por macho
decreciente con el tamaño, y la capacidad de representar *swarm killing* y SIT/IIT.

**Pierde**: (a) la estructura interna del enjambre, que no discrimina la transmisión;
(b) la heterogeneidad individual de la fidelidad al sitio (todos los machos de un
sitio son equiprobables en la asignación, con desempate aleatorio); (c) el movimiento
*macho → sitio* como trayectoria, modelado como un cuanto discreto con
`male_swarm_site_range_m` como único parámetro de alcance.

#### 8.5 — Sobre `p_mate` (el número que la literatura NO fija de forma única)

Hay dos estimaciones publicadas del porcentaje de machos de un enjambre que se aparea
por noche, y **no coinciden**:

| Estimación | Valor | Especie / lugar | Tier |
|---|---|---|---|
| Diabaté et al. 2011 | **0,072 ± 0,0095** (7,2 %); "una pareja más por cada 14 machos extra" | *A. gambiae* s.s., Malí | **[P]** |
| Ouédraogo et al. 2025 | **0,084–0,25** parejas por macho (7/83 en el menor, 693/2 783 en el mayor) | *A. coluzzii*, Burkina Faso | **[M]** |

La diferencia es de un factor 4 y **no se puede resolver con la literatura disponible**.
La decisión: usar el valor de *coluzzii* (0,084–0,25) como ancla por defecto y el de
Diabaté como cota inferior en la sensibilidad, con el conflicto documentado en la
configuración. El tope de **≤ 3 hembras por macho por noche** (Ekechukwu & Tripet
2019) es un límite de capacidad **citado, no medido en ese artículo** ⇒ **[M]/[NR]**;
y no llega a biting en la práctica, porque la eficiencia observada (0,08–0,25) está
muy por debajo de 3.

La forma de la curva tiene una discrepancia adicional: Diabaté encuentra eficiencia
por macho aproximadamente **constante**, Ouédraogo encuentra eficiencia **decreciente**
con el tamaño del enjambre (parejas ∝ tamaño, t = 9,16, p < 0,001, pero la pendiente
por macho cae). El modelo por defecto usa eficiencia constante y expone un exponente
`p_mate_size_exponent` [EP] para el caso decreciente; el valor por defecto (0) es el
más simple y el único que reproduce la afirmación de Diabaté de que "el éxito del macho
individual es similar se una a un enjambre grande o pequeño".

**Contraargumento registrado, no descartado.** Iacomelli et al. 2026 demuestra
interacción macho-macho experimental (sincronización de **velocidad**, no de
dirección) y afirma que "los modelos estándar requieren nuevas clases de modelo";
Shishika et al. 2014 reporta correlación direccional elevada en campo. Ningún
resultado publicado exige esa granularidad para el objetivo actual (transmisión
espacial), y la generalización laboratorio→campo sigue abierta. La razón para
descartar la opción 3 **no** es que estos resultados sean erróneos, sino que el
objetivo del plan no los necesita: §8.3.

#### 8.6 — El resto de las decisiones de la capa macho

*   **Reintento sin caducidad**: si no se insemina, se reintenta cada noche; el esperma
    ya adquirido dura de por vida (monandria + tapón espermático).
*   **Alarma**: el motor emite, por celda y noche, el número de **hembras adultas sin
    inseminar por más de N noches**. Si crece, el campo de enjambres está roto.
*   **Supervivencia de los machos, separada de la hembra**: `male_daily_survival` =
    **0,773 ± 0,094** (Epopa et al. 2017) **[M]** — hoy el YAML aplica 0,87 a ambos sexos
    y sobrestima los machos en ~12 %. Se añade la dependencia de azúcar como mecanismo
    [EP]: sin azúcar 1,94–2,99 días de vida, con azúcar 3,84–4,94 días (Gary et al.
    2009) **[P]**.
*   **Movimiento de los machos, con su propio presupuesto**: la dispersión macho medida
    es una **media de 40–549 m por experimento** con ventana de recaptura ≤ 7 días
    (Epopa et al. 2017) — **no es una tasa diaria** — y en *arabiensis* ningún macho
    superó los 100 m (Kaiser et al. 2021) **[P]**. El desplazamiento diario masculino es
    **muy inferior** a los 486–695 m/día de la hembra ⇒ el macho necesita su propio
    `male_move_capacity_m`, no el de la hembra.
*   **Velocidad de vuelo del macho**: 0,50 ± 0,00 m/s en enjambre (rango 0,24–1,28)
    (Poda et al. 2024) **[M]**; fuera del enjambre sólo hay un dato de arena,
    **0,20 ± 0,00 m/s** (vuelo de escape) (Poda et al. 2024), que **no** es velocidad de
    dispersión en campo ⇒ se declara **[EP] con banda**, no dato.
*   **Razón de sexes**: `male_ratio` por especie (0,5 por defecto, [EP]) — hoy el ODD la
    declara "neutral default"; la evidencia disponible apunta a sesgo **macho** en campo
    (Vielma et al. 2026).
*   **Ventana de apareamiento**: `swarm_start_min_after_sunset` = 5, `swarm_duration_min`
    = 28,3 (19–39 por mes) (Bimbilé Somda et al. 2018) **[P]**, y
    `rain_suppresses_swarming` (0 parejas por enjambre en el pico de lluvias).
*   **Preferencia de apareamiento antes/después de la primera comida**: el motor
    permite ambas ventanas (noches 2 y 3), porque *arabiensis* aparea antes (98,47 % de
    las hembras que copulan aún no habían comido) y *gambiae* s.s. se reparte 49/51.
*   **Aislamiento de enjambres entre especies**: publicado (χ² = 56,92, segregación por
    marcador; Diabaté et al. 2009) pero medido en Malí entre formas M y S ⇒ el modelo
    actual no lo captura y se documenta como mecanismo ausente.
*   **Intervenciones**: con la opción 2 el modelo **sí** puede representar el *swarm
    killing* (que requiere marcadores discretos que se pueden eliminar: ↓insemination y
    ↓densidad de hembras, p < 0,001; Sawadogo et al. 2022) y **SIT/IIT** (machos
    estériles asignados a los mismos sitios, compitiendo por los mismos cupos; el
    lado femenino requiere la capa de individuos humanos del paso 2).

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

Consecuencias:

*   El cálculo diario **ya es por celda** (`coordinator.cpp`: `z_`, `feats_`,
    `dry_days_`, `K_cell_` son arrays de H×W). Lo que cambia es que se **materializa**
    para toda la rejilla, no sólo para las celdas candidatas. Coste: 3 416 celdas ×
    ~40 B ≈ 140 kB por día en el AOI de Accra (61×56).
*   **La doble fuente de potencial desaparece**: `oviposition_seeking.cpp:49-54` usa
    el potencial del gpkg y hace *fallback* a `ps.habitat_avail`. Con el registro por
    celda hay **una sola fuente**: el potencial estático per-cell.
*   **La ruta de error `aquatic_cohort_bank.cpp:304-306` ("no PatchState for today")
    desaparece por construcción**: toda celda tiene registro ⇒ `k_habitat == 0` pasa a
    ser la respuesta definida (muerte de L1–L4 ese día, contrato v4.0).
*   **La clave de la cohorte pasa a `cell_id`** (`CohortKey` en
    `aquatic_cohort_bank.hpp`): la agregación de la Beverton-Holt sigue siendo por
    celda (1 km², hipótesis explícita).
*   **La posición de la madre se AÑADE al cohorte de huevos** (`mother_x`, `mother_y`).
    Esto **no existe hoy**: `AquaticCohort` es
    `{patch_id, stage, instar, development, count, mean_age_days}` y el adulto emerge
    **snapado al centro de la celda** (`mosquito_submodel.cpp:530-535`). Con el campo
    añadido, el adulto emerge **donde puso los huevos la madre** — que es el
    el comportamiento correcto y lo que hace que la composición por celda de los adultos
    emergentes signifique algo.
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

| Contrato | Hoy | Plan | Motivo |
|---|---|---|---|
| `contracts.cogs_state` | 4.0 | **4.1** (MINOR) → **5.0** (MAJOR) | banda 1 deprecada (4.1), banda única (5.0) |
| `contracts.env_nc` | 3.0 | **sin cambio** | el NC de entorno no cambia: mismas bandas, mismos planos |
| Contrato de hábitat (registro por celda) | 3.0 (implícito) | **5.0** | el registro por celda pasa a ser parte del contrato |
| Sidecar JSON acuático | `patch_id` | `cell_id` | renombrado de vocabulario |

*   **4.1 (MINOR)**: la banda 1 `adult_patch_count` **se mantiene** en el shape (los
    lectores por nombre siguen funcionando y el surrogate conserva sus 2 canales), pero
    sus valores pasan a ser la **copia** de la banda 2, y el sidecar lo declara:
    `"deprecated_bands": ["adult_patch_count"]`.
*   **5.0 (MAJOR)**: se publica **una sola banda** (`adult_count`, la de posición) más el
    sidecar nuevo con las estadísticas por individuo. `VECTOR_CHANNELS` pasa de 2 a 1
    en `mal-core/src/mal_core/training/dataset.py`; `prediction/state_loader.py` se
    actualiza; el golden del COG de estado se regenera.
*   **Los lectores deben rechazar una versión desconocida** (INV-16): un consumidor que
    ve `5.0` con dos bandas, o `4.1` sin la declaración de deprecación, debe fallar
    en vez de leer mal.

### 11. Observabilidad: eventos e individuos

Tres artefactos nuevos, más la evolución de los existentes:

```
runs/<run>/
  <run>_dayNNN.tif          COG de estado (2 bandas en 4.1, 1 en 5.0)
  <run>_dayNNN.json         sidecar (deprecated_bands, stats por individuo)
  <run>_aquatic.json        sidecar acuático (cell_id, cohortes, madre)
  <run>_bites.jsonl         ◀ NUEVO: ledger de eventos de picadura
  <run>_mating.jsonl       ◀ NUEVO: ledger de apareamiento (sitio, cupos, parejas)
  <run>_agents.parquet      ◀ NUEVO: estado por mosquito por tick/día
  <run>_humans.parquet      ◀ NUEVO: estado por persona (muestreado o completo)
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
  transmission_applied   (β_hv × prev, o β_vh × su)
  cell_id              (derivado, para agregados)
```

`BiteLedger` (hoy `BiteEventAggregate` por celda/tipo/día) **se conserva** como capa
de agregados (el COG de transmisión y la lógica de ITN/IRS lo consumen) y **se añade**
encima la capa de eventos. Así el contrato de transmisión 4.0 no se rompe.

**Artefacto individual** — una fila por mosquito y por tick (o por día, según el
volumen): `uid`, especie, `sex`, `pos_x`, `pos_y`, `cell_id`, estado gonotrófico,
`blood_volume_ul`, `ovarian_stage`, `gonotrophic_cycles`, `inseminated`, `vector_state`,
`age_days`, y —**para los machos**— `swarm_site_id` y `nights_uninseminated`.

**Ledger de apareamiento** — eventos de la capa macho, en el mismo JSONL o en uno
propio (`<run>_mating.jsonl`):

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
killing*.

### 12. Configuración: qué cambia en `model_constants.yaml`

El esquema (`version: 2`) sube a `version: 3` porque cambian claves congeladas. Las
claves se organizan **por especie** (`species.<fila>`), según la decisión P, y se
retiran las que la evidencia no sostiene.

**Se retiran (en todas las filas de especie y en los bloques globales):**

| Clave | Motivo |
|---|---|
| `species.<fila>.host_seeking_radius_m` (1500) | "olor de asentamiento" sin respaldo |
| `species.<fila>.host_seeking_scale_m` (300 / 120) | decaimiento exponencial incompatible con la pluma intermitente |
| `dispersal.host_flight_step_m` (500) | contradice la capacidad medida; lo sustituye velocidad × tiempo |
| `dispersal.snap_radius_m` (500) | sin afiliación de parche en el lado de adultos |
| `oviposition.scale_m` (50) | mismo problema de campo continuo |
| `gonotrophic.feeding_success_rate` (0,825) | cargado pero nunca consultado |

**Cambian:** `species.coluzzii.activity_weights` → `[0.00, 0.191, 0.676, 0.133]`;
`species.coluzzii.salinity_hi_tol_ppt` → 10,5 (con la clave renombrada a la unidad real);
`dispersal.adult_sigma_m` → `daily_move_capacity_m` = 590; `host_seeking.detect_range_m`
→ `species.<fila>.co2_activation_radius_m` = 100.

**Se crean** (por especie salvo indicación): `co2_activation_radius_m`,
`olfactory_radius_m`, `visual_radius_m`, `terminal_radius_m`, `flight_speed_ms`,
`exploration_range_m`, `male_ratio`, `male_daily_survival`, `insemination_prob`,
`sperm_store_days`, `blood_meal_refractory_days`, `blood_meal_size_ul`,
`blood_meal_target_ul`, `meal_size_min_ul`, `probing_success_rate`,
`meals_per_cycle_mean`, `gonotrophic_arrest_prob_dry`, `aestivation_supported`;
y el bloque `mating:` (`p_mate` con las dos cotas publicadas, `p_mate_size_exponent`
[EP], `male_females_per_night_max` 3, `swarm_duration_min` 28,3,
`swarm_start_min_after_sunset` 5, `swarm_height_m` 2,87, `swarm_markers_per_km2` [EP],
`swarm_markers_source`, `rain_suppresses_swarming`, `local_swarm_attendance_factor` 0
[EP] — ver §8.2).

**Se crean (integración temporal, bloque `integration:`)**: `phase_duration_hours`,
`directed_flight_budget_h` (~1 h/día, §5), `dt_terminal_s` (0,05),
`dt_olfactory_s` (0,25), `plume_memory_s` (0,5–0,9, con la cota de 300 ms marcada [P]
como *Aedes*), `landing_speed_mm_s` (50) y `landing_speed_hold_s` (3).

**Se crea (capa macho, bloque `mating:`)**: `male_move_capacity_m`, con la
advertencia de que la cifra publicada (40–549 m) es una **media por experimento** con
ventana ≤ 7 días, **no** una tasa diaria: la clave documenta la ambigüedad en vez de
ocultarla.

**Se crea (capa macho, bloque `mating:`)**: `male_swarm_site_range_m` — el **radio de
alcance para asignar sitio de enjambre** al macho que emerge (§8.1). Es un parámetro
distinto de `male_move_capacity_m`: el primero decide *a qué sitio se asigna* el macho
(una vez, al nacer); el segundo, cuánto se desplaza al día. Bandas: **100 m**
(ningún macho de *arabiensis* superó los 100 m; media 85,7 m; Kaiser et al. 2021)
como valor por defecto, y **550 m** como cota superior (máximo observado en *coluzzii*,
Epopa et al. 2017). **[EP]** — no hay una medición directa del radio de asignación de
sitio: se infiere del rango de dispersión; por eso el valor por defecto es el
**conservador** (el sitio más próximo dentro del alcance más corto).

**El bloque `gonotrophic` se redefine**: `egg_batch_n/mean/min/max` (invariante
`min <= mean <= max <= n`) se sustituyen por un lote **proporcional al volumen
acumulado** con tope `egg_batch_max`; la validación de `config_validation.py` cambia
en consecuencia, y `test_config_validation.py` se reescribe.

**Nota sobre `host_seeking_scale_m`**: además de retirarse como radio de atracción,
esta clave **pondera el kernel de siembra** (`seeding.hpp`). Retirarla cambia la
distribución inicial de la población ⇒ hay que decidir explícitamente si la siembra
pasa a usar `exploration_range_m` o si su propio kernel se mantiene con otra clave.
Es un efecto secundario que el diseño previo señalaba y que el plan debe resolver de
forma explícita (se resuelve en el plan de implementación: la siembra pasa a usar
`daily_move_capacity_m`).

**Tres sitios, no uno.** Cada clave de especie vive en **tres** lugares que deben
cambiar a la vez: el modelo pydantic `SpeciesRow` de
`mal-core/src/mal_core/config_validation.py:153`, el `struct SpeciesRow` de
`mal-core/src/mal_core/abm/include/mal_abm_fast/config.hpp:73` y el volcado de
`mal-core/src/mal_core/abm/src/config_dump.cpp:103-106`. Un cambio de esquema que
toque sólo el YAML rompe la validación o el volcado de configuración.

**El bloque `rng:`**: las tres semillas fijas actuales (`aquatic_seed_washout`,
`aquatic_seed_stage_mortality`, `aquatic_seed_larva_mortality`,
`model_constants.yaml:277-279`) se **retiran**: el stream acuático se deriva de la
semilla maestra (§13.4). Sin ese cambio, "una semilla maestra" es falso.

### 13. Arnés de escenarios sintéticos

Pre-requisito de todo lo demás: sin él no hay termómetro.

**Restricción de diseño (impuesta por el autor).** El diseño previo pedía explícitamente
"una ruta de ejecución que **no** pase por el modo manifiesto" (su apartado 13, paso 0).
El autor lo rechaza: **el arnés debe pasar siempre por el manifiesto**. La solución no es una ruta alternativa, sino **un manifiesto sintético**
construido igual que uno real, sobre un AOI pequeño, donde lo único "a mano" son las
personas, los animales y los mosquitos.

#### 13.1 — El AOI sintético

*   **Slug**: `accra-synth-10x10`. **Bounding box** recortado de la ventana de Accra:
    `[-0.2, 5.7, -0.10971147034573944, 5.789842104336081]` ⇒ `cells_per_side() = (10, 10)`
    con celdas de exactamente 1 km.
*   **La geometría llega al binario por el `--bbox` que ya existe**: `wrapper.py:130-134`
    sólo consulta `aois.yaml` cuando no se da bbox, y `--resolution-m` / `--scale` toman
    después los valores por defecto del binario (1 000 m / regional). **No hay que tocar
    ningún fichero de producción para esto.**
*   **Raíz de datos**: `runs/synthetic/accra-synth-10x10/` (fuera de `data/`, que está
    protegida y git-ignored; `runs/` sí es el sitio natural de las corridas).
*   **Tres artefactos, todos remuestreados de `data/accra-coastal-test/`**:
    *   `env.nc` — 10×10, las 9 variables del contrato `env_nc = "3.0"`, con
        `contract_version = "3.0"`.
    *   `habitat_patches.gpkg` — Point por celda con `hab_type`, `dynamics` (int 0/1),
        `habitat_potential`, `row`, `col`; el potencial **recalculado** con
        `mal_core.habitat.potential`.
    *   `host_static.nc` — 9 variables sobre (y, x).
*   **Lo "a mano"**: el plano `human` de `host_static.nc` es la población del escenario
    (recuentos por celda) y `cattle`/`goats`/`sheep` son los animales del escenario.

#### 13.2 — Los parámetros del escenario viajan en el manifiesto

Un conjunto nuevo de ficheros `scenarios/E01.json … E16.json` (uno por escenario),
referenciado por una **clave de dataset nueva** en el manifiesto (`scenario`, con su
`files` indexado por id). El manifiesto sigue siendo la **única fuente de verdad**: el
escenario es un dataset más, con su validación de completitud como todos los demás.

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
Sin siembra individual, **E1, E2, E7, E8, E9, E13 y E14 son inejpresables**. Se añade:

*   `AgentSpec` (mosquito): (x, y), sexo, estado, edad, estado vectorial.
*   `AquaticSpec` (cohorte): (x, y), celda, estadio, instar, desarrollo, recuento.
*   `ScenarioSpec`: lista de `AgentSpec`, lista de `AquaticSpec`, lista de personas con
    (x, y) y estado, semilla maestra, días, expectativas.
*   `SeedingMode::SCENARIO` y su rama en `CoordinatorModel`
    (`build_scenario_seed_instructions`).

Los humanos pasan de "recuento por celda" a **individuos con posición**, que es el
requisito de E1 (una persona a 200 m del mosquito: 200 m está por debajo de la
resolución de 1 km, así que la granularidad sub-celda es obligatoria).

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
    los datasets opcionales **no deben declararse** — y si los 16 ficheros de escenario
    se declaran como un único dataset, E1 dependería de que exista E16.
2.  **Discrepancia de tipo en `dynamics`.** Python escribe `persistent|pluvial`
    (`ingest/env.py:88`) y C++ lee un int (`habitat_engine.cpp:220`) ⇒ siempre 0.
    Inofensivo hoy (la separación se recalcula por nombre desde los planos H), pero el
    gpkg sintético debe escribir el **int** y no heredar el error.
3.  **El motor descarta en silencio los parches con `habitat_potential < 0,01`**
    (`habitat_engine.cpp:216`). Una de las 99 features de la ventana de Accra
    (0,00978) queda por debajo del suelo ⇒ la ruta de recorte **debe aplicar el umbral
    explícitamente**, o el escenario tendrá menos parches de los que cree.

#### 13.6 — Comportamiento de cada escenario

Cada escenario es un **script** que escribe observado-vs-esperado en
`runs/_check_current/` y **termina con código 0** (no es un test con aserciones que
fallan): el paso 1 del plan marca los fallos esperados de la cadena actual y sirve de
línea base. El detalle por escenario —mapa E1–E16, definiciones y expectativas— está
en el **Apéndice A** de este documento; la cadena de semillas y las trampas del
catálogo, en el **Apéndice B**.

**Escenarios que la evidencia de §16 añade al conjunto:**

*   **E15 — Intervención dirigida al enjambre (*swarm killing*)**: mata los machos de los
    marcadores; la aserción es la caída de la tasa de inseminación y de la densidad de
    hembras. Es el escenario que **obliga** a que el campo de marcadores sea discreto y
    eliminable, no un campo uniforme.
*   **E16 — Contrescenario SIT/IIT**: el modelo **no puede** simularlo (exige machos
    estériles individuales compitiendo por enjambre). El escenario existe para
    **documentar el límite** del modelo, no para validar un número.

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
  CONTACTO: sortea probing_success_rate → sortea volumen → acumula
      │
      ├─ blood_volume_ul < objetivo ─▶ vuelve a HOST_SEEKING (misma noche)
      └─ blood_volume_ul ≥ objetivo ─▶ BLOOD_FED: arranca ciclo, ventana postprandial
```

### 15. Orden de integración

El orden no es negociable: cada paso necesita el anterior como termómetro.

| # | Paso | Precondición |
|---|---|---|
| 0 | Arnés de escenarios sobre manifiesto sintético (§13) | — |
| 1 | Línea base: E1–E2 con la cadena actual, marcando los fallos esperados | 0 |
| 2 | Individuos humanos + ledger de eventos + `probing_success_rate` | 1 |
| 3 | Volumen de sangre, multipicadura, umbral gonotrófico, pre-gravídica, ventana postprandial, reloj de inanición | 2 |
| 4 | Cascada de percepción y movimiento emergente por especie, con micro-integrador de dos bandas | 3 |
| 5 | Estado fisiológico: `ovarian_stage`, `ARRESTED`, estación seca | 4 |
| 6 | Estado acuático por celda (hábitat 5.0), `cell_id`, posición de la madre en la cohorte | 5 |
| 7 | Machos, campo de marcadores de enjambre, cupos, alarma | 6 |
| 8 | Elección del sitio de oviposición por estado de la cohorte de larvas y multi-sitio | 7 |
| 9 | Escenarios E3–E16 completos con expectativas calculadas a mano | 8 |
| 10 | Recalibración de los scorers + política de comparación | 9 |

Los pasos 2–8 tocan el mismo núcleo (`mosquito_submodel.cpp` +
`mosquito_state.hpp`), de modo que **no se paralelizan entre sí**; sí pueden paralelizarse
las piezas aisladas (arnés de escenarios, esquema de configuración en Python, contrato de
salida) con los pasos del motor, en ramas separadas.

### 16. Revisión de la base teórica (investigación de apoyo)

Tres revisiones en paralelo se hicieron sobre la evidencia, con subagentes independientes, antes
de cerrar el Technical Plan. Sus resultados cambian tres cosas del diseño.

#### 16.1 — Filopatria natal: el campo `home_x/home_y` no tiene base

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
permanencia a < 50 m se convierte en **restricción del radio de exploración** (§4);
(iii) la preferencia natal entra como **sesgo por tipo de habitat**, no como distancia
(§9); (iv) el skip oviposition obliga a que la oviposición sea **multi-sitio** (§9).

#### 16.2 — Capa macho: el enjambre no es un colectivo emergente

El ABM validado con datos de *coluzzii* (Cribellier et al. 2026) reproduce el enjambre
con tres reglas mínimas —atracción al marcador visual, alineación al eje del atardecer,
evitación de colisión por debajo de 2,5 longitudes corporales— **ninguna de las cuales
es una regla de boids hacia los conspecificos**. La geometría (cono de 0,67 m, σ de
4–10 cm, separación al vecino de 0,11 m) es tres órdenes de magnitud por debajo de la
celda de 1 km.

**Consecuencias en el plan**: (i) la justificación de la decisión M cambia de
"conveniencia" a **suficiencia por construcción** (§8); (ii) el "número libre" de
marcadores se sustituye por un **campo de marcadores estático y persistente** calibrado
a valores publicados (§8); (iii) la supervivencia del macho se separa (0,773 ± 0,094);
(iv) el macho recibe su **propio presupuesto de movimiento**; (v) el modelo **sí**
puede simular *swarm killing* (matar los machos asignados a un marcador) y **SIT/IIT**
(machos estériles compitiendo por los mismos cupos; el lado femenino requiere la capa
de individuos humanos del paso 2); (vi) la granularidad individual del macho se
justifica por la **fidelidad al sitio** (un macho liberado seguía en un sitio de
enjambre 8 días después: Kaiser et al. 2021) y no por la dinámica del enjambre, que
queda excluida (§8.3, A18).

#### 16.3 — Resolución temporal: los ticks de 1 s eran irresolubles

Con la velocidad medida (0,225–0,45 m/s) y el radio terminal medido (0,10–0,15 m), un
paso de 1 s avanza 22–45 cm: **mayor que el radio terminal entero**. El evento más
rápido medido (giro en el punto más cercano) dura 0,08 s. Las frecuencias de muestreo
de los experimentos van de 25 a 90 fps y el precedente de modelo usa Δt = 0,02 s.

**Consecuencias en el plan**: el micro-integrador pasa de "1 s" a **dos bandas
adaptativas** (0,05 s terminal, 0,25 s olfativa), el macro-paso se acota por un
**presupuesto de tiempo de vuelo dirigido** (~1 h/día) en vez de por la duración de la
fase, y el "[EP] ≈2 s" de memoria olfativa **se elimina** por no tener fuente (§5).

**New papers**: 25 extractos nuevos en `papers/anopheles-dynamics/` (filopatria y
oviposición: 9; capa macho y enjambre: 14; escala temporal: 2), con las filas 89–113
de `papers/REFERENCES.md` añadidas.

## Alternatives Considered

Las opciones siguientes son las que el diseño previo ya evaluó (con su aritmética), más las que
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
*   **Inconvenientes**: **anula el objetivo del apartado 1 del diseño previo** (que la
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

*   **Mecanismo**: `S_H`/`I_H`/… siguen siendo el estado; la mosquito "pica" a una
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
    determinista (`celda × slot + slot`) la hace posible más adelante sin romper el
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
    tendrá que reentrenarse de todos modos (memoria #195), de modo que no hay ventaja
    de compatibilidad que defender.

### A10 — Estado acuático: la celda como clave y la posición de la madre como payload

*   **Mecanismo**: la cohorte conserva `cell_id` como clave de agregación y guarda el
    `(x, y)` de la madre; el resto del comportamiento acuático no cambia.
*   **Ventajas**: coste cero; la dependencia de densidad sigue funcionando sin tocar
    nada.
*   **Inconvenientes**: la ruta de error "no PatchState for today"
    (`aquatic_cohort_bank.cpp:304-306`) sigue viva; "patch" sigue significando "celda
    candidata" mientras el lado de adultos ya no tiene parche (dos vocabularios
    conviviendo); y el gpkg conserva un papel que el registro por celda vuelve
    redundante.
*   **Motivo del rechazo**: decisión D4 = (b). Con (b) desaparece la ruta de error por
    construcción, la doble fuente de potencial se unifica, y el registro por celda es
    la precondición de la competencia sub-celda. El coste —bump del contrato de hábitat
    3.0 → 5.0 y renombrado en toda la cadena— se paga en el mismo PR donde ya se
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

*   **Mecanismo**: `p = min(1, 0,072 × machos_alcance)`, con el tope de 3 hembras por
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

### A14 — Capa macho: machos como individuos con enjambre

*   **Mecanismo**: cada macho es un agente con posición, comportamiento de agregación
    en el marcador y un apareamiento explícito.
*   **Ventajas**: permite intervenciones dirigidas al enjambre (roteo de enjambres,
    SIT/GM) y representa la estructura fina de la observación.
*   **Inconvenientes**: **hace el modo de fallo más difícil**, no más improbable: el
    resultado dependería del estado de cada macho, y los datos de enjambre disponibles
    son de *gambiae* y *arabiensis*, no de *coluzzii*. El único número libre (densidad
    de marcadores) seguiría siendo el mismo, pero ahora habría que calibrar además la
    regla de formación del enjambre.
*   **Motivo del rechazo**: decisión M = (A) agregados. La opción B sólo se justifica si
    aparece una intervención que dependa de la estructura fina del enjambre.

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

### A18 — Capa macho: machos como individuos con vuelo simulado al enjambre

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
    asiste con tasa baja (10,33 %); la oferta de cupos por sitio es lo que limita la
    reproducción, y se obtiene sin simular la dinámica interna. (ii) Exige un **reloj
    diel dentro del paso diario**: el motor tiene un día, no una ventana de 27 min
    ⇒ refactor del bucle temporal. (iii) El coste: con 10⁵–10⁶ machos por noche en un
    AOI de país es el coste dominante ⇒ rompe NFR-3. (iv) **No hay dato publicado** que
    parametrice la atracción ni la fidelidad al sitio ⇒ el resultado dependería de
    parámetros inventados, contra la regla del proyecto (todo número con fila en
    `papers/REFERENCES.md`).
*   **Motivo del rechazo**: el objetivo del plan es la transmisión espacial y la
    trazabilidad individual, no la mecánica intra-enjambre; el mecanismo que limita la
    reproducción está medido y es el agregado por sitio. La comparación completa, con
    la tabla de criterios, está en §8.3. La alternativa **queda abierta**: la opción
    elegida (§8) deja los machos como individuos con un sitio asignado, de modo que una
    capa de vuelo se puede añadir encima sin tocar el resto del diseño.

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
    corre dentro de la banda de percepción. Objetivo: una corrida de 30 días del AOI de
    Accra (61×56) con la población actual debe completarse en un tiempo comparable al
    actual (la referencia es la corrida de 30 días que hoy tarda ~2 min); el escenario
    sintético 10×10 debe tardar **< 10 s**.
*   **NFR-4 — Coste del estado humano individual.** ~58 B por persona ⇒ 2–4 GB por
    corrida a escala de país. Aceptado en esta iteración (N3); documentado en el
    sidecar.
*   **NFR-5 — Trazabilidad de cada número.** Ningún parámetro del motor existe sin una
    entrada en `model_constants.yaml` con su valor, su unidad, su tier de evidencia
    ([M]/[P]/[EP]/[NR]) y su referencia. El volcado de configuración (`config_dump.cpp`)
    incluye la clave nueva.
*   **NFR-6 — Nada se "limpia" sin contrato.** Todo cambio de forma de salida va
    acompañado de bump de versión de contrato y de una regla de rechazo explícita en
    los lectores (INV-16). No hay migraciones silenciosas.
*   **NFR-7 — Los artefactos no se acumulan.** El prune por clase de fichero (§207 de
    las memorias del proyecto) se mantiene: el ledger de picaduras y los parquet
    individuales son **la** información que no se puede regenerar, y por eso se
    declaran como "conservar" en el prune.
*   **NFR-8 — Compatibilidad Python/C++.** Toda constante nueva existe en las tres
    copias (YAML, modelo pydantic, `struct` C++) y hay un test de paridad de
    configuración. Un cambio de esquema que toque sólo una copia falla el CI.
*   **NFR-9 — Los escenarios son parte del CI.** El arnés se ejecuta en cada commit
    con paso 0; los escenarios con forma cerrada fallan el CI, los demás escriben su
    banda de tolerancia para revisión.

--------------------------------------------------------------------------------

### Additional Resources

*   *(el documento de diseño intermedio y su informe de revisión Goldfish son
    artefactos temporales del flujo de diseño: este plan es autocontenido y no depende
    de ellos).*
*   `papers/anopheles-dynamics/` — 84 extractos de la literatura citada.
*   `papers/REFERENCES.md` — filas 32–88 (rondas de fisiología de la sangre, cascada
    sensorial, machos y estado fisiológico).
*   `docs/plans/in-process/odd-fixes/` — packs ODD 02, 03, 04 y partes de 05/08/10/11,
    que este cambio sustituye.
*   `mal-core/src/mal_core/abm/include/mal_abm_fast/wire.hpp` — invariantes del contrato
    de estado (nombres de banda, `CONTRACT_VERSION`, `STATE_BAND_NAMES`).
*   `mal-core/src/mal_core/download/manifest.py` — contrato de datos y manifiesto.

### Future Improvements

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

Una lista única, ordenada por el orden de integración de §15. Cada entrada indica qué
cambia y por qué. Los ficheros se agrupan por el paso en que se tocan; un paso no
empieza hasta que el anterior pasa su verificación.

### Paso 0 — Arnés de escenarios sobre manifiesto sintético

*   **`mal-execution/scripts/make_synthetic_aoi.py`** (nuevo) — construye el AOI
    sintético: recorta `data/accra-coastal-test/` a la ventana 10×10 y escribe
    `env.nc`, `habitat_patches.gpkg` y `host_static.nc` bajo
    `runs/synthetic/accra-synth-10x10/`. Recalcula el potencial con
    `mal_core.habitat.potential` y aplica el umbral de 0,01 de forma explícita
    (`habitat_engine.cpp:216` descarta por debajo). Es el generador de "los datos" del
    escenario.
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
    (`mosquito_submodel.cpp:358`): sin este cambio los escenarios E1/E2/E7/E8/E9/E13/E14
    son inejpresables.
*   **`mal-core/src/mal_core/abm/src/coordinator.cpp`** y
    **`include/mal_abm_fast/coordinator.hpp`** (modifican) —
    `build_scenario_seed_instructions()`: traduce el `ScenarioSpec` a instrucciones
    por individuo, **sin** el snap al parche más cercano que hace hoy
    `--seeding-mode explicit` (imprescindible para E7: un mosquito en una celda no
    candidata).
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
*   **`mal-core/src/mal_core/abm/tests/scenarios/E01.json … E16.json`** (nuevos) — un
    fichero por escenario, con la lista de agentes, la lista de personas, la semilla y
    las expectativas.
*   **`mal-core/src/mal_core/abm/tests/fixtures/make_golden_fixtures.py`** (modifica) —
    el generador de fixtures existente (AOI 8×8) se reutiliza para el AOI sintético
    10×10, de modo que los escenarios no dependan del script de producción.
*   **`mal-core/tests/test_scenario_manifest.py`** (nuevo) — verifica que el manifiesto
    sintético valida, que el escenario se resuelve y que dos corridas con la misma
    semilla producen artefactos idénticos byte a byte.

### Paso 1 — Línea base

*   **`mal-core/src/mal_core/abm/tests/scenarios/`** (nuevos) — E1 y E2 escritos con
    las **expectaciones de la cadena actual** (fallos conocidos: 0 picaduras humanas,
    población de vectores colapsada). Los pasos 2+ los sustituyen por las
    expectativas correctas.
*   **`runs/_check_current/`** (generado) — salida de comparación observado-vs-esperado
    de cada escenario. Se regenera en cada corrida; no se versiona.

### Paso 2 — Individuos humanos, ledger de eventos

*   **`mal-core/src/mal_core/abm/include/mal_abm_fast/human_state.hpp`** (modifica) —
    `HumanCompartmentGrid` pasa a un `HumanSoA` de individuos: `human_id` (determinista:
    `cell_id × SLOTS_PER_CELL + slot`), `cell_id`, `home_x/home_y` (posición fija
    uniforme dentro de la celda, asignada por semilla), `cur_x/cur_y` (iguales a `home`
    en esta versión), `state` y `timer`. Los compartimentos agregados pasan a
    **estadísticas derivadas** (`compute_stats()`); la API pública (`seed_infections`,
    `seed_random_viable_foci`, `seed_explicit_foci`, `seed_outbreak_cluster`,
    `advance_day`) mantiene su semántica, pero backed por individuos.
*   **`mal-core/src/mal_core/abm/src/human_state.cpp`** (modifica) — implementación de
    las colas de cohorte por individuo (temporizador discreto en vez de cola por celda),
    del sorteo binomial de exposiciones y de la derivación de estadísticas. Consume el
    `Prng` que hoy usa la rejilla.
*   **`mal-core/src/mal_core/abm/include/mal_abm_fast/bite_ledger.hpp`** (modifica) —
    `BiteLedger` conserva la capa de agregados (`BiteEventAggregate`, que consumen el
    COG de transmisión y la lógica de ITN/IRS) y **añade** la capa de eventos
    (`BiteEvent`: mosquito, persona, fase, volumen, resultado del sondeo, transmisión
    aplicada). El contrato de transmisión 4.0 no se rompe.
*   **`mal-core/src/mal_core/abm/src/transmission.cpp`** (modifica) — la exposición deja
    de aplicarse a una densidad de celda y se aplica a un individuo: la picadura
    identifica a la persona y la transmisión se propaga a esa persona.
*   **`mal-core/src/mal_core/abm/src/transmission_debug_log.cpp`** y
    **`include/mal_abm_fast/transmission_debug_log.hpp`** (modifican) — el log de
    depuración pasa a registrar eventos con identificadores (es el instrumento con el
    que se detectó el "cero picaduras humanas" del §P1).
*   **`mal-core/src/mal_core/abm/src/main.cpp`** (modifica) — flags de siembra humana
    por celda → por posición, para que el escenario pueda fijar la posición de una
    persona a 200 m (por debajo de la resolución de 1 km).

### Paso 3 — Fisiología de la sangre

*   **`mal-core/src/mal_core/abm/include/mal_abm_fast/gonotrophic_cycle.hpp`** (modifica)
    — añade `ARRESTED` al enum `GonotrophicState`; `GonotrophicParams` gana
    `blood_meal_target_ul`, `first_cycle_target_ul`, `probing_success_rate` y retira
    `feeding_success_rate` (que se carga en `gonotrophic_cycle.hpp:71` y el motor nunca
    consulta).
*   **`mal-core/src/mal_core/abm/include/mal_abm_fast/mosquito_state.hpp`** (modifica) —
    campos nuevos del SoA: `pos_x`, `pos_y`, `blood_volume_ul`, `ovarian_stage`,
    `gonotrophic_arrest`, `days_since_target_reached`, `inseminated`,
    `nights_uninseminated`, `age_days`, `swarm_marker_id`. **El campo `home_x/home_y`
    que la primera redacción preveía para el adulto queda fuera**: la filopatria natal
    no tiene base publicada (§16.1).
*   **`mal-core/src/mal_core/abm/src/mosquito_submodel.cpp`** (modifica) — la
    transición determinista `if (picked != nullptr) → BLOOD_FED`
    (`mosquito_submodel.cpp:757-779` y `:855-862`) se sustituye por la máquina
    `PROBING` con multipicadura; el reloj de inanición deja de reiniciarse con las
    comidas parciales; el lote de huevos pasa a ser **proporcional al volumen
    acumulado**; la oviposición se vuelve **multi-sitio** con el sesgo por estado de
    la cohorte de larvas conspecíficas (§9). Cada campo nuevo del SoA exige las tres
    operaciones (`push_back`, `std::swap` en la compactación
    `mosquito_submodel.cpp:152`, `resize` `mosquito_submodel.cpp:180`).
*   **`mal-core/src/mal_core/abm/tests/test_mosquito_submodel.cpp`** (modifica) —
    casos de multipicadura, de umbral gonotrófico y de reloj de inanición.
*   **`mal-core/src/mal_core/abm/tests/test_gonotrophic.cpp`** (modifica) — el umbral
    por primera comida (pre-gravídica) y la ventana postprandial.

### Paso 4 — Cascada de percepción y movimiento emergente

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
    use la misma ruta que la lectura de `host_static.nc`.
*   **`mal-core/src/mal_core/abm/src/oviposition_seeking.cpp`** (reescribe) — el
    kernel pasa de `potential × exp(-d/scale)` a un criterio de **elegibilidad +
    señal en el sitio** (cohorte de larvas conspecíficas, sesgo por tipo de habitat,
    multi-sitio). Se corrige también la cabecera de `oviposition_seeking.hpp`, que
    documenta un `twi × water_frac` retirado en el contrato v3.0.
*   **`mal-core/src/mal_core/abm/include/mal_abm_fast/oviposition_seeking.hpp`**
    (reescribe) — idem cabecera, y se retira la noción de `scale_m` (radio de
   atracción con decaimiento continuo).
*   **`mal-core/src/mal_core/abm/tests/test_host_seeking.cpp`** (reescribe) — casos
    por tramo, con distancias medidas.
*   **`mal-core/src/mal_core/abm/tests/test_mobility.cpp`** (modifica) — el módulo de
    movilidad humana (`MobilitySchedule`) queda **sin consumidor** al aplicarse N2; el
    test se marca como *skip* con la nota de eliminación pendiente, no se borra.

### Paso 5 — Estado fisiológico y estación seca

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

### Paso 6 — Estado acuático por celda

*   **`mal-core/src/mal_core/abm/include/mal_abm_fast/wire.hpp`** (modifica) —
    `PatchState` → `CellState`: `patch_id` → `cell_id`, `activated` → `eligible`; se
    documenta que "patch" es un filtro de elegibilidad y no un contenedor de
    información. Se añade `mother_x`/`mother_y` al payload de la cohorte (§9).
*   **`mal-core/src/mal_core/abm/include/mal_abm_fast/aquatic_cohort_bank.hpp`**
    (modifica) — `CohortKey` pasa a `cell_id`; `AquaticCohort` gana la posición de la
    madre; `EmergenceEvent` lleva la posición de emergencia (no el centro de la celda).
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
    `cell_id` y las estadísticas por individuo; se declara `deprecated_bands` en 4.1.
*   **`mal-core/src/mal_core/abm/tests/test_state_cog.cpp`** (modifica) — golden del
    COG de estado: 4.1 (dos bandas, la primera copia de la segunda, con
    `deprecated_bands`) y 5.0 (una sola banda). El golden se regenera.
*   **`mal-core/src/mal_core/abm/tests/test_pool_water.cpp`** y
    **`test_habitat_engine.cpp`** (modifican) — las fábricas de `PatchState` pasan a
    `CellState` y deben fijar `k_habitat` explícitamente (1000,0) o las larvas mueren
    el día 1 (memoria #195).

### Paso 7 — Machos: sitio asignado, enjambre por sitio, cupos

*   **`mal-core/src/mal_core/abm/include/mal_abm_fast/mosquito_state.hpp`** (modifica) —
    `swarm_site_id` (int32, −1 = enjambre local efímero), `inseminated` y
    `nights_uninseminated` pasan a aplicar **también a los machos** (el SoA ya los
    guarda; no hay coste de memoria añadido). Las tres operaciones del SoA
    (`push_back`, `std::swap` en la compactación, `resize`) se aplican a los campos
    nuevos.
*   **`mal-core/src/mal_core/abm/src/mosquito_submodel.cpp`** (modifica) —
    (a) **asignación de sitio al emerger**: el macho nace en la posición de la madre
    (`mother_x`/`mother_y` de la cohorte acuática, §9) y adopta el sitio persistente
    más cercano dentro de `male_swarm_site_range_m` (desempate por RNG sembrado); si no
    hay ninguno, `swarm_site_id = -1` ⇒ enjambre local en su posición de eclosión.
    (b) **asistencia nocturna**: en la ventana de enjambre, cada macho asiste a su
    sitio; el recuento por sitio se reconstruye sumando los machos asignados.
    (c) **cupos**: `cupos(s) = M(s) × p_mate`, con el exponente `p_mate_size_exponent`;
    el sorteo empareja machos y hembras no inseminadas dentro del alcance de vuelo;
    los machos emparejados quedan `inseminated`, los demás incrementan
    `nights_uninseminated`.
    (d) **reintento sin caducidad** y **supervivencia del macho separada de la
    hembra** (`male_daily_survival` = 0,773 ± 0,094).
    (e) Se retira el movimiento de los machos por el kernel de la hembra: el macho
    tiene su propio presupuesto (`male_move_capacity_m`).
*   **`mal-core/src/mal_core/abm/src/swarm_site_field.{hpp,cpp}`** (nuevo) — la capa
    estática y persistente de sitios de enjambre: id, posición métrica, y la
    estructura publicada (separación 11–19 m, altura 2,87 m, duración ≈27 min,
    ventana 5–33 min tras la puesta de sol, densidad `swarm_markers_per_km2`); el
    campo se **resuelve una vez** por corrida y se cachea, no se recalcula por noche.
*   **`mal-core/src/mal_core/abm/src/coordinator.cpp`** (modifica) — carga el campo de
    sitios desde el artefacto del manifiesto y lo pone a disposición del submodelo.
*   **`mal-core/src/mal_core/abm/src/main.cpp`** (modifica) — flag `--swarm-markers`
    para pasar el campo; y el flag de *swarm killing* que E15 necesita (matar los
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

### Paso 8 — Elección del sitio de oviposición

*   **`mal-core/src/mal_core/abm/src/oviposition_seeking.cpp`** (completa el paso 4) —
    el sesgo por estado/densidad de la cohorte de larvas conspecíficas y la
    persistencia del criadero, con los valores publicados de *coluzzii*.
*   **`mal-core/src/mal_core/abm/tests/test_oviposition.cpp`** (nuevo) — casos de
    elección de sitio y de skip oviposition.

### Paso 9 — Escenarios completos

*   **`mal-core/src/mal_core/abm/tests/scenarios/E03.json … E16.json`** (nuevos) — los
    escenarios con expectativas calculadas a mano; E15 (*swarm killing*) y E16
    (contrescenario SIT/IIT, que documenta un límite del modelo) incluidos.
*   **`mal-core/src/mal_core/abm/tests/test_scenarios.py`** (nuevo) — ejecuta el arnés
    completo y compara con las bandas de tolerancia.

### Paso 10 — Configuración, contratos y consumidores

*   **`mal-core/config/model_constants.yaml`** (modifica) — `version: 3`; se retiran
    `host_seeking_scale_m`/`host_seeking_radius_m` (por especie),
    `dispersal.host_flight_step_m`, `dispersal.snap_radius_m`, `oviposition.scale_m`,
    `gonotrophic.feeding_success_rate` y las tres semillas fijas del bloque `rng:`; se
    crean los bloques `integration:` y `mating:` y las claves por especie de §12.
    Cada clave lleva su unidad y su tier de evidencia.
*   **`mal-core/src/mal_core/config_validation.py`** (modifica) — los modelos
    pydantic (`SpeciesRow:153`, `HostSeeking:293`, `Dispersal:278`, `Gonotrophic:267`)
    siguen al YAML; el bloque `gonotrophic` se **redefine** (lote proporcional al
    volumen) y su validación `min <= mean <= max <= n`
    (`config_validation.py:579-584`) cambia en consecuencia.
*   **`mal-core/src/mal_core/abm/include/mal_abm_fast/config.hpp`** (modifica) — los
    `struct` C++ (`SpeciesRow:73`, `DispersalCfg:175`, `HostSeekingCfg:190`,
    `GonotrophicCfg:164`) siguen al YAML.
*   **`mal-core/src/mal_core/abm/src/config_dump.cpp`** (modifica) — el volcado
    incluye las claves nuevas y **retira** las antiguas
    (`config_dump.cpp:103-106`); es la superficie que la calibración consume.
*   **`mal-core/src/mal_core/abm/tests/test_config.cpp`** y
    **`tests/test_config_engine_golden.py`** (modifican) — paridad de configuración
    Python/C++ y golden del volcado.
*   **`mal-core/src/mal_core/training/dataset.py`** (modifica) — `VECTOR_CHANNELS` pasa
    de 2 a 1 con el contrato 5.0; el loader lee el nombre de banda del sidecar en vez
    de asumir posiciones.
*   **`mal-core/src/mal_core/prediction/state_loader.py`** (modifica) — lee el COG de
    estado con una banda y **rechaza** versiones de contrato desconocidas.
*   **`mal-core/src/mal_core/scoring/registry.py`** y
    **`mal-core/src/mal_core/scoring/scorers/*.py`** (modifican) — recalibración de
    los scorers que leen bandas del COG; los scorers que dependan de la banda
    desaparecida se adaptan o se retiran (el registro de scorers es
    `mal-core/src/mal_core/scoring/registry.py::build_registry`, con pesos en
    `COMPOSITE_WEIGHTS` y gates en `GATES`).
*   **`mal-core/src/mal_core/abm/tests/test_config_engine_golden.cpp`** (modifica) —
    golden del motor con la configuración nueva.

### Ficheros de documentación

*   **`docs/specs/abm/spec.md`** (o el documento de contrato vigente que lo
    substituya) — se actualizan las invariantes afectadas por la banda única, por el
    registro por celda y por los identificadores de evento.
*   **`docs/concepts/abm/odd-2010-malariasentinel.tex`** — los packs ODD 02, 03, 04
    y las partes de 05/08/10/11 quedan sustituidos por este plan; los pasajes
    concretos a enmendar se listan en `docs/plans/in-process/odd-fixes/`.
*   **`papers/REFERENCES.md`** — ya actualizado con las filas 89–113 (§16).
*   **Artefactos temporales que se borran al cerrar este plan**: el documento de diseño
    intermedio (y su informe de revisión Goldfish) y la nota de trabajo del arnés de
    escenarios. Este plan es el único artefacto durable; los borrados van **por
    fichero**, nunca por directorio, conforme a la regla de limpieza del proyecto.

### Verificación Plan

**Criterio de aceptación de cada paso**: el arnés de escenarios pasa, `ctest` no
empeora, y la suite Python de `mal-core` está verde.

*   **Nivel 1 — unidad (C++)**: `cmake --build … -j && ctest --test-dir …`. Los
    fallos preexistentes conocidos (la familia de `gonotrophic resting_duration_days`
    1.0 vs 0.5, y los defaults de *coluzzii*) no son regresiones y se anotan como tales.
*   **Nivel 2 — contrato (Python)**: `cd mal-core && uv run pytest tests -v`. Incluye
    `test_config_validation.py` (reescrito), `test_no_constants_guard.py` (ninguna
    constante compilada fuera del YAML) y `test_yaml_comments.py` (cada clave nueva
    lleva su comentario con unidad y referencia).
*   **Nivel 3 — paridad Python/C++**: `test_habitat_python_contract.py` (β urban
    unificado 0,75) y el nuevo test de paridad de configuración, porque las claves
    nuevas viven en tres copias.
*   **Nivel 4 — escenarios**: el arnés (`mal-core/src/mal_core/abm/tests/scenarios/`)
    se ejecuta con la semilla maestra; cada escenario escribe observado-vs-esperado
    en `runs/_check_current/`. Los escenarios con forma cerrada (E1: la mosquito
    encuentra y pica a una persona concreta; E2: la comida cierra el ciclo; E6: la
    emergencia ocurre en la posición de la madre; E7: el adulto emerge con la
    filopatria **no** modelada) fallan el CI; los que dependen de la ley de movimiento
    (E4, E5, E10, E13) llevan banda de tolerancia pre-registrada y se revisan.
*   **Nivel 5 — determinismo**: dos corridas con la misma semilla producen artefactos
    idénticos byte a byte; dos semillas distintas producen artefactos distintos. Este
    test es el que detecta que un sub-stream se ha auto-sembrado (el hueco de
    `aquatic_cohort_bank.cpp:204/227/298`).
*   **Nivel 6 — regresión de la cadena (P1)**: una corrida de 30 días del AOI de
    Accra deja de registrar **cero picaduras humanas**, y la población de vectores deja
    de colapsar (122 → 2 adultos). Es el criterio de éxito del §P1, y se comprueba
    sobre el binario reconstruido, no sobre el golden (el golden hay que regenerarlo
    con el cambio de contrato).
*   **Nivel 7 — revisión de la base teórica**: cada número nuevo que entra en
    `model_constants.yaml` tiene una entrada en `papers/REFERENCES.md` con su fila y
    su tier. Un número sin fila no entra.

### Dependencias y orden

El orden de §15 no es negociable porque cada paso necesita el anterior como
termómetro. Los pasos 2–8 tocan el mismo núcleo (`mosquito_submodel.cpp` +
`mosquito_state.hpp`) y **no se paralelizan entre sí**. Sí pueden paralelizarse, en
ramas separadas: el arnés de escenarios (paso 0), el esquema de configuración en Python
y C++ (paso 10), y el contrato de salida (pasos 6 y 10).

--------------------------------------------------------------------------------

<!-- Provenance: Indicates initial structural drafting via EGM. -->

*Drafted with EGM*

## Apéndice A — Mapa de escenarios E1–E16

Cada escenario es un fichero `scenarios/E01.json … E16.json`, referenciado por la clave
de dataset `scenario` del manifiesto. La columna **expectación** es la que el test
compara; cuando lleva banda de tolerancia, la banda se declara en el propio JSON.

| ID | Qué ejercita | Escenario | Expectación |
|---|---|---|---|
| E1 | Cadena mínima: una hembra, una persona a 200 m, sin criadero | 1 hembra en (lon,lat); `human` en una persona a 200 m; `aquatic=[]`; 3 días | 1 comida por noche; **ninguna** oviposición; la hembra entra en inanición al día 3 |
| E2 | La mosquito **no** está donde el humano | 1 hembra, persona a 2 km | 0 comidas hasta que la ley de movimiento la acerque; la probabilidad de llegada **es** el resultado (banda de tolerancia) |
| E3 | Multipicadura y Contacto | N hembras con `probing_success_rate` congelado, personas en contacto | comidas ≈ N·p·P(contacto); el ledger muestra **varios** eventos por noche |
| E4 | Comida parcial | 1 hembra, 1 persona, `blood_volume_ul` sembrado por debajo del umbral | sigue en `HOST_SEEKING` esa noche; el ciclo gonotrófico **no** arranca |
| E5 | Umbral alcanzado | 2 hembras: una parcial + una completa | el ciclo arranca; el lote de huevos ∝ volumen acumulado |
| E6 | Primer ciclo (`PRE_GRAVID`) | 1 hembra que necesita 2 comidas | hacen falta 2 comidas; se respeta `first_cycle_days` |
| E7 | El criadero gana al hospedero | 1 hembra, 1 criadero a 300 m, 1 persona a 2 km | va al **hábitat**, no al hospedero (y la polinización natal no está modelada: §16.1) |
| E8 | Dos hembras, dos personas | 2 hembras en celdas distintas, 2 personas | cada una pica por el Weighted-Roulette de `pref` + distancia; **no** hay "celda ganadora" |
| E9 | Vector infeccioso | 1 hembra `infective=true`, ≥3 personas | varias picaduras infecciosas; P(>1 persona infectada) > 0 |
| E10 | Sensibilidad a los radios | E10 ×3 (una por variante) | activación 50/100/200 m; olfativa 10/30/70 m; visual 0,25/0,72 m — cuantifica el peso de cada tramo de la cascada; los valores por defecto son los **verificados** |
| E11 | Ventana postprandial | 1 hembra alimentada el día 0 | la alimentación se cierra 24 h y se reabre progresivamente (7 % @40 h, 27 % @48 h, 68 % @72 h) |
| E12 | Arresto ovárico en seca | ráfaga de lluvia y después seca (`env.nc`) | fracción de hembras alimentadas sin pasar de estadio 2 = 19,23–34,85 % (*coluzzii*) |
| E13 | Machos y oferta de apareamiento | 100 hembras + 100 machos recién emergidos en una celda de 1 km²; `swarm_markers_per_km2` **fijado en el escenario** y `male_swarm_site_range_m` explícito | los machos se **asignan** a los sitios dentro de su alcance; la oferta (`p_mate` × machos asignados a los sitios alcanzables) ≥ la demanda; **hembras sin inseminar tras 3 noches = 8–21 %** (banda medida), no 0 (§16.3) |
| E14 | Machos presentes, enjambre todavía no | 1 hembra en celda con machos recién emergidos (antes de su primera ventana de enjambre) | **no** queda inseminada (los machos asignados a un sitio no entran al enjambre antes de la ventana); se emite la alarma `hembras_sin_inseminar`; la hembra asiste al sitio si está dentro de su alcance |
| E15 | *Swarm killing* | campo de marcadores + 1 enjambre en la aldea | matar los machos **asignados** al marcador deja el sitio sin oferta ⇒ la fracción de hembras sin inseminar sube; **es la prueba de que el campo de sitios es una capa estática y no un número por corrida** |
| E16 | Contrescenario SIT/IIT | el mismo campo, con ITN al 60 % | el ITN **no** compensa la pérdida de cupos del enjambre (si se modela ITN); deja por escrito un límite del modelo, no un resultado del modelo |

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
    Consecuencia: los streams acuáticos son **idénticos entre escenarios**; un
    escenario no puede variar la mortalidad acuática por semilla. Corregirlo (derivar
    el stream del maestro) es parte del paso 0.
*   Cada rollout usa un `Prng` nuevo; reutilizar uno cambia los sub-streams derivados.
*   Los rollouts multihilo son reproducibles bit a bit **con el mismo binario**, no
    entre binarios: los golden hay que regenerarlos en el mismo PR que el cambio de
    API.

**Trampas del catálogo que el arnés debe esquivar**:

| Trampa | Detalle | Contención |
|---|---|---|
| Validación de catálogo | `validate_completeness()` comprueba **todos** los ficheros declarados: el manifiesto debe listar los 16 JSON aunque sólo se ejecute uno | el generador escribe los 16; el arnés resuelve el id pedido (`files[str(id)]`), nunca "el primero" |
| Deriva de identidad | `"scenario"` no es una salida de un loader: `downloadable_datasets()` / `catalog_status()` la ignoran | añadir `SCENARIO_ARTIFACT` a `catalog.py`, junto a `INGEST_ARTIFACTS` |
| Versionado de contrato | el NC recortado conserva `contract_version="3.0"`; el gpkg conserva las columnas v3.0 | un recorte no bumpea contrato; una columna nueva (p. ej. `dynamics` como int) sí lo es |
| `dynamics` con tipos distintos | Python escribe una cadena, C++ lee un int ⇒ siempre 0 | el gpkg sintético escribe int `0/1`; se abre issue para el par productor/consumidor |
| Suelo de potencial | el motor descarta parches con `potential < 0.01`; la ventana de Accra contiene uno en 0,00978 | el generador aplica el mismo suelo e informa del número de descartes |
| Geometría de celda | las celdas de Accra son 992,8 m × 997,5 m; la rejilla sintética es 1000 m | remuestrear, nunca copiar una feature sin recalcular `row`/`col`/`potential` |
| gpkg no reproducible byte a byte | GeoPackage sella `gpkg_contents.last_change` | comparar **contenido** (tabla de atributos ordenada), no bytes |
| Golden fixtures | cualquier cambio de la API de siembra o del SoA cambia los bytes dorados | regenerar con `make_golden_fixtures.py` en el mismo PR; el golden sigue siendo 8×8 y el arnés sintético es aparte |
| Ruta protegida | `data/` es protegida y `data/**/*.json` está en `.gitignore` | generar bajo `runs/synthetic/` + `--data-root`; los JSON de escenario viven en `mal-core/src/mal_core/abm/tests/scenarios/`, donde se revisan en un PR |
| Defaults que estorban | `--seeding-mode random-viable`, `--human-seeding-mode random-viable`, `initial_human_prevalence` | el fichero de escenario sobrescribe los tres explícitamente (`SCENARIO`; `none`; prevalencia 0) |
| No-determinismo de OpenMP | los rollouts paralelos no comparten más que el sistema de ficheros; cada uno tiene su `Prng` | una aserción por rollout; multi-rollout sólo para estadística de ensembles |
