# Brief — Individualización de personas y rediseño del movimiento de mosquitos

> **Estado**: borrador de diseño (2026-11), **revisión 2**, corregida tras la revisión
> Goldfish de 8 revisores (informe: `individualization-and-movement-brief.goldfish-review.md`).
> Bloques de investigación cerrados: fisiología de la sangre (§6), dossier de *Anopheles
> coluzzii* (§9), **cascada sensorial y navegación** (§5) y **machos + estado fisiológico de
> la hembra** (§5.6, §6.4 bis, §8.1). Toda la evidencia está en `papers/`:
> **84 extractos** en `papers/anopheles-dynamics/` y **filas 32–88** de
> `papers/REFERENCES.md` (30 extractos nuevos en la ronda de fisiología de la sangre, §6;
> 11 en el dossier de la especie, §9; el resto en las rondas de cascada sensorial, machos y
> estado fisiológico, §5 y §8). Las decisiones que aún faltan del usuario están en §12.
>
> **Alcance**: sustituye a los packs ODD 02, 03, 04 y partes de 05/08/10/11
> (`docs/plans/in-process/odd-fixes/`). Es un plan de **cambio de modelo**, no un ajuste:
> cambia la unidad de razonamiento de "celda de 1 km" a "individuo en posición continua".
>
> **Decisión marco**: los escenarios sintéticos del paquete de verificación **ejercitan la
> cadena real** (alimentar → ovipositar → eclosionar → alimentar). Por tanto el arreglo del
> pipeline es parte del cambio, no un prerrequisito aparte.

---

## 1. Qué se quiere conseguir

Que en el modelo se pueda **observar la malaria emergiendo a nivel individual**: quién fue
picado, por quién, cuándo, con qué resultado, y cómo la supervivencia de cada mosquito
determina la persistencia de la cadena. Hoy eso es imposible por construcción (todo el
razonamiento es a nivel de celda) y además **no hay nada que observar** porque la cadena
no cierra (ver §2).

## 2. Estado actual verificado (no inferido)

Medido sobre el binario vigente (commit `8d32a05`, reconstruido y copiado a
`mal-core/src/mal_core/abm/bin/mal_abm_fast_darwin`), corrida de 30 días en Accra
(`runs/_check_current/`, con `MAL_ABM_TRANSMISSION_DEBUG=1`):

| día | adultos | huevos | larvas | pupas | `feeds` | `human_feeds` |
|---|---|---|---|---|---|---|
| 1 | 101 | — | — | — | 62 | **0** |
| 10 | 24 | 0 | 859 | 0 | 10 | **0** |
| 20 | 6 | 0 | 231 | 0 | 2 | **0** |
| 30 | 2 | 0 | 144 | 12 | 1 | **0** |

Tres fallos con **causa raíz compartida** (el modelo razona en celdas de 1 km):

1. **La población de vectores no se renueva.** Los huevos se depositan en el `patch_id`
   *snap-eado* a ≤500 m (`snap_radius_m`), que puede no estar activado ese día; en
   `promote_stages` un cohorte cuyo parche no aparece en `patch_states` hace `continue`
   (`src/aquatic_cohort_bank.cpp:365`): no envejece ni se desarrolla. De ahí 859 larvas y
   sólo 12 pupas en todo el AOI el día 30, y 122 → 2 adultos en 30 días.
2. **Cero picaduras humanas en 30 días.** La mosquito busca *celdas*, no personas:
   `detect_host_cell` elige la celda con más atracción y `step_toward_host` da **un paso de
   500 m** (`host_flight_step_m`) redondeado al entero (`src/host_seeking.cpp:307`, `lround`):
   con objetivo diagonal el desplazamiento es 0,354 celdas y **se pierde**. La atracción
   decae con `exp(-d/300)`, de modo que la propia celda siempre gana si tiene ganado: la
   mosquito come pollos (1 117 por celda de 1 km en la franja costera — **cifra sin fuente ni fecha en el repositorio: pendiente**) y nunca llega a la gente
   (a 1,0–2,8 km). Consecuencia: `pref.human = 0.99` nunca llega a aplicarse.
3. **No hay malaria.** Sin picaduras no hay `infectious_meals`; `S_H` = 40 255 susceptibles
   no se mueve.

Además: `feeding_success[si] = 1.0f` se fija siempre (`src/mosquito_submodel.cpp:829`),
`feeding_success_rate` (0,825) **se carga pero el motor no lo consulta** (la transición a
`BLOOD_FED` es determinista), y el `max_delta` de la configuración de picadura tampoco.

## 3. Decisiones tomadas en esta iteración

| # | Decisión | Consecuencia principal |
|---|---|---|
| Q8 | Los escenarios sintéticos **ejercitan la cadena real** | El pipeline debe funcionar; los escenarios son el instrumento de validación |
| Q8b | Alcance **(b)**: la individualización **sustituye** los mecanismos de comida y oviposición; sólo se reparan los que sobreviven (desarrollo larvaro, máquina gonotrófica, renovación de población) | Un solo modelo; sin trabajo duplicado |
| Q10 | Las personas **se quedan en casa** (posición fija dentro de la celda, uniforme); la movilidad individual se pospone | El modelo de datos debe tener `home` y `current` (iguales ahora) |
| Q11 | Movimiento **emergente y por especie**, con la **cascada sensorial documentada y su alcance por especie** (activación 100 m [P] · orientación olfativa 30–70 m [P] · visual 25–72 cm [M] · terminal 10–20 cm [M]) y velocidad de vuelo medida (0,225–0,45 m/s) | Ni `host_flight_step_m` ni el kernel gaussiano sobreviven; el campo de atracción por celda desaparece |
| Q12 | Especie piloto: ***Anopheles coluzzii*** | Fila ya activa (`species.default_species`); no cambia el calibrador |
| Q13 | **Mezcla de señales dependiente del estado gonotrófico**: hambrienta → hospedero; gravídica → hábitat de cría | El pack 05 pasa a ser requisito, no alternativa |
| Q13b | **Acumulación de volumen sanguíneo**: una picadura no completa la sangre necesaria; la hembra sigue picando hasta un umbral | Nuevo parámetro de especie + cambio de la máquina gonotrófica |
| Q14 (W) | El viento es un **evento aparte** (migración/dispersión a escala de 100 km), no un término del vector diario | Se conserva el canal `dispersal.wind_flight_hours` / `wind_survival`; se aísla del radio de atracción |
| Q14 (S) | **No existe "olor de asentamiento"**: el movimiento es exploración aleatoria correlacionada + guiado de olor cercano | Se retira el campo de atracción de 1500 m; la ley se construye por tramos de distancia |
| Q14 (P) | El radio de percepción **viene de la configuración de la especie** y su valor debe estar verificado en la literatura para la especie elegida | Claves por especie en `species.<fila>`; valores verificados contra la fuente, no priors |
| Q14 (C) | Se **adoptan** las correcciones de parámetro, pero **basadas en papers**, no en engineering priors | Cada corrección entra con su cifra medida y su referencia; sin valor medido ⇒ no se cambia |
| Q15 (M) | **Machos triviales pero configurados por especie**, con `male_ratio`, `insemination_prob` y un **diagnóstico de enjambre**; el apareamiento es un **encuentro espacial con la capacidad de los enjambres** (§5.7), con la hembra volando al enjambre y respaldo local | No se modelan enjambres como agentes; el ODD ya declara "no hay colectivos"; el apareamiento pasa de instantáneo a probabilidad por hembra **y por distancia** |
| Q16 (E) | **Máquina de estados fisiológicos**: `gonotrophic_cycles` (reloj) + `blood_volume_accumulated` + `ovarian_stage` + `gonotrophic_arrest`; `age_days` sólo como diagnóstico | Sin evidencia medida de dependencia de la edad, `age_days` no puede ser variable de estado |
| Q17 | **Época seca = "no hay criadero", no "mueren"**: la hembra gravídica sin criadero entra en `ARRESTED` | Requiere que la parada ovárica sea por especie (`coluzzii` sí estiva; `gambiae` s.s. no) |
| Q18 | **Base temporal del movimiento = opción (a)**: paso macro por fase (el desplazamiento diario sigue anclado al MRR medido) + **micro-simulador local** (ticks de 1 s) cuando el mosquito entra en el radio olfativo | El motor no tiene hoy reloj de fase ni sub-pasos (`model_constants.yaml` no tiene duración de fase; el día es un único `for p < PHASE_WEIGHT_COUNT`), y la cascada abarca 4 décadas de escala (100 m → 10 cm) ⇒ un solo integrador no la representa. Opción (b) (tiempo continuo por eventos) es más fiel pero mucho más invasiva; (c) (integrador grueso + kernel de encuentro) es la más barata pero **anula el objetivo del §1** (trayectorias individuales) |
| Q19 | **Individualización humana = opción (a)**: todas las personas son individuos con posición, estado y timers propios | El coste por persona (~58 B) implica 2–4 GB de estado por corrida a escala de país ⇒ **se optimiza después**, y **los escenarios sintéticos empiezan con poblaciones pequeñas** (10×10 / 100×100 celdas). Para conservar la opción de optimizar sin romper el contrato de observación, el `human_id` debe ser **determinista y estable** (`celda × slot + slot`) desde el primer día |

## 4. Modelo de datos humano

- Cada persona es un **individuo**: posición `home` (uniforme dentro de la celda de 1 km,
  assignment determinista por *seed*), posición `current` (igual a `home` en esta versión),
  estado de infección, y susceptibilidad individual.
- **Estado de infección individual**; los compartimentos agregados (`S_H`, `I_H`, …) se
  **retiran como estado de simulación** y pasan a ser **estadísticas derivadas** para
  salidas y visualización (pack 02, decisión 1).
- La agregación a celda sigue siendo necesaria para: el ledger de picaduras, las salidas
  COG de estado y el cálculo de eficiencia de transmisión; pero **la unidad de decisión
  (a quién pica, con qué resultado) es siempre el individuo**.
- La movilidad por fases (matrices OD de gravedad, `beta_day` 0,05 / `beta_night` 0,5 /
  `max_distance_km` 50) **sale del camino crítico**; los CSR y `MobilitySchedule` quedan
  como código muerto a eliminar en una fase posterior (no bloqueante para este cambio).

## 5. Ley de movimiento

### 5.1 Decisión: **no existe "olor de asentamiento"**

No hay evidencia de una señal de largo alcance que atraiga a los mosquitos hacia un
asentamiento humano. Lo que la literatura documenta es una **cascada sensorial con
alcances decrecientes**, y la parte más larga del proceso es *exploración*, no
*atracción*. Valores **verificados contra el texto original** (verificado en
`papers/anopheles-dynamics/`, con la auditoría completa en
`audit-gemini-synthesis-host-seeking-numeric-claims.md`):

| tramo | escala | señal | comportamiento | evidencia |
|---|---|---|---|---|
| activación | **100 m** | CO₂ (pulsado) | despegue o paso de reposo a búsqueda activa; **sin vector** hacia la fuente (53 % vs 39 % control) | [P] *gambiae* s.s., túnel de semicampo (Lorenz 2013) |
| orientación olfativa | **70 m** (mezcla + CO₂) · **50 m** (sólo CO₂: 65 % vs 36 %) | volátiles cutáneos + CO₂ | anemotaxis optomotora contra el viento; *casting* transversal si se pierde la pluma | [P] *gambiae* s.s., semicampo (Lorenz 2013) |
| orientación olfativa **en campo abierto** | **30 m** (olor humano: 57 % vs 51 %); **el CO₂ solo no da dirección**; nada más allá de 30 m | olor humano | la turbulencia disuelve la pluma antes | [P] *arabiensis* (Lorenz 2013) |
| aproximación visual | **25–72 cm** (radio del modelo ocular: 39 cm para un blanco grande horizontal, 72 cm vertical, 25 cm pequeño horizontal) | contraste de silueta, **habilitado por olor** | vector visual hacia formas grandes/oscuras | [M]-modelo *coluzzii* (Carnaghi 2023/2024; extracto `carnaghi-2023-coluzzii-visual-thermal-landing-targets.md`) |
| respuesta visual medida | **9,8 % → 43,4 %** (baldosa negra) y **6,8 % → 24,1 %** (transparente) al añadir olor; giro a **0–15 cm** de la superficie (giro medio 5,4 ± 0,85 cm) | olor + CO₂ | aproximación final | [M] *coluzzii* (Hawkes & Gibson 2016) |
| aterrizaje | **radio terminal 10–20 cm** (mínimo de velocidad medido) | calor + humedad + olor | aterrizaje ∝ **área** calentada (⅛ y ¼ dan ~2–2,5× menos que ½; **no hay regla dura del 50 %**) | [M] *coluzzii* (Carnaghi 2021/2024); [P] el "15 cm" de *gambiae* s.s. (Spitzen 2013) |
| sensorialidad del CO₂ | umbral del ORN maxilar **≤350–400 ppm**; rastrea pulsos **600→4 800 ppm sin saturar** | CO₂ | detección por incremento, no por nivel | [M] *coluzzii* (Majeed 2017) |

**Restricción física**: el progreso neto contra el viento se bloquea cuando la
velocidad del viento ambiente supera la velocidad propia de vuelo. La velocidad propia
de la hembra en busca **no está medida** ⇒ el umbral se calcula en tiempo de ejecución
con la velocidad configurada y el viento del día, **nunca hardcodeado**.

**Corrección importante sobre la geometría del penacho**: el "campo de atracción
exponencial de 300 m" del YAML (`host_seeking_scale_m`) no tiene base. La pluma es
**intermitente y filamentosa** por encima de ~1 m: incluso las hembras que aterrizan
pasan el **61,4 % ± 3,9 %** del tiempo de vuelo **fuera** de los límites teóricos de la
pluma (88,9 % ± 3,8 % si no aterrizan) [P, *gambiae* s.s., Spitzen 2013]. Un gradiente
continuo produce trayectorias "artificialmente directas" — es lo que advierte el propio
modelo espacial de referencia (Cummins 2012, modelo genérico calibrado para *Culex*).

**Reconciliación de un dato que parecía contradecir la decisión**: el MRR de machos de
*coluzzii* encuentra que las recapturas se concentran en el núcleo habitado del pueblo
(varianza >44 %) y lo lee como "atractivo por población humana" (Epopa 2017). Pero
**los machos no pican**: ese agrupamiento no puede deberse al olor de la presa. La
literatura de enjambres da la explicación alternativa y medida: el **sitio** explica el
**47,6 %** de la varianza del tamaño de enjambre (Diabaté 2011) y los enjambres se
concentran en el área residencial (distancia mediana al enjambre más cercano: 10 m).
Es **fidelidad al sitio de enjambre**, no atracción por personas.

### 5.2 Arquitectura de estados por distancia (propuesta)

| régimen | condición | movimiento | fuente |
|---|---|---|---|
| exploración | sin estímulo | paseo aleatorio correlacionado + *casting* transversal al viento | fuera de la pluma (Cummins 2012; Lorenz 2013) |
| rastreo de pluma | contacto con un filamento de olor | anemotaxis optomotora contra el viento; temporizador de memoria olfativa que dispara *casting* si se pierde | [P] *gambiae* s.s. (Spitzen 2013); el "casting" de 2 s del resumen de Gemini **no se ha podido verificar** ⇒ **[EP]**; el dato accesible más próximo son 300 ms en *Aedes* (Dekker & Cardé 2011, sólo resumen) |
| aproximación | ≤0,72 m (radio del modelo ocular: 0,39 m objetivo grande horizontal, 0,72 m vertical, 0,25 m pequeño horizontal) | vector visual a silueta, **sólo si el estado olfativo está encendido** | [M] *coluzzii* (Hawkes & Gibson 2016; Carnaghi 2023) |
| contacto | 10–20 cm | aterrizaje condicionado a calor + humedad + olor | [M] *coluzzii* (Carnaghi 2023/2024) |

### 5.3 Cinemática de vuelo (medida en *coluzzii*)

| régimen | velocidad sobre el suelo | velocidad angular | altura | fuente |
|---|---|---|---|---|
| suave | **45,1 ± 1,63 cm/s** | 268,5 ± 33,0 °/s | 11,8 → 13,0 cm | [M] *coluzzii* (Hawkes & Gibson 2016) |
| tortuoso | **29,0 ± 2,57 cm/s** | 497,8 ± 52,2 °/s | 7,5 → 13,6 cm | [M] *coluzzii* (íd.) |
| rasante (*dipping*) | **22,5 ± 1,14 cm/s** | 531,9 ± 25,7 °/s | **nunca >3,5 cm** | [M] *coluzzii* (íd.) |
| en el campo de olor | hasta **0,5 m/s** (mínimo de velocidad a 10–20 cm) | — | — | [M] *coluzzii* (Cribellier 2018) |

**No hay contradicción** con los 0,66–0,87 m/s de `vielma-2026`: aquéllos son **machos
en enjambre** (vuelo cerca de la marca, sin carga de viento); estos son **hembras en
busca de hospedero** (0,225–0,45 m/s sobre el suelo en túnel de 0,1 m/s). Se usan para
comportamientos distintos: enjambre vs. búsqueda. **Ninguno de los dos es una
velocidad de dispersión**.

### 5.4 Consecuencias concretas en el motor (verificadas en el código actual)

El kernel actual (`host_seeking.hpp`) es **un campo de atracción por celda de 1 km**
con decaimiento exponencial, y estos son los cambios que la evidencia impone:

| clave actual | valor | por qué se retira / cambia |
|---|---|---|
| `species.<fila>.host_seeking_radius_m` | **1500 m** | es exactamente el "olor de asentamiento" que la evidencia no sostiene ⇒ **se retira** |
| `host_seeking.detect_range_m` | **2000 m** | el mosquito puede "detectar" un hospedero a 2 km ⇒ **se sustituye** por el radio de activación por especie (100 m) y el radio olfativo (30–70 m) |
| `species.<fila>.host_seeking_scale_m` | **300 m** | decaimiento exponencial de un campo continuo: lo que la física de la pluma **no** permite (§5.1) |
| `dispersal.host_flight_step_m` | **500 m** (éste es el paso que usa el motor en la pasada por fases, `mosquito_submodel.cpp:832-836`; `host_seeking.approach_step_m` = 50 m es el otro) | pasa a derivarse de la **velocidad de vuelo medida** (0,225–0,45 m/s) × tiempo de vuelo de la fase ⇒ el desplazamiento deja de ser un múltiplo del tamaño de celda |
| `oviposition.scale_m` / `oviposition.detect_range_m` | 50 m / 2000 m | mismo problema en la búsqueda de criadero: el radio de detección debe salir de la evidencia (movimiento real hacia el agua) |

El `HostAttraction` deja de ser "celda con más gente": pasa a ser **hospederos
individuales** con distancia continua, y la "atracción" se sustituye por un
**sentido de distancia al hospedero más cercano dentro del radio de percepción**,
con la preferencia por tipo de hospedero (`pref`) jugando en el sorteo.

### 5.5 Viento: **evento aparte** (decisión W = a)

El viento no actúa como un término diario de desplazamiento: actúa como un **proceso
de dispersión a escala de 100 km**, con condiciones distintas (altitud, duración,
supervivencia).

| parámetro | valor | fuente |
|---|---|---|
| altitud de vuelo | 40–290 m sobre el suelo | [M] Huestis 2019 |
| viento nocturno a esa altitud | 5,1 m/s (p10–p90 2,4–8,0) | [M] Huestis 2019 |
| desplazamiento 2 h / 9 h de vuelo pasivo | media 30 / 120 km; máximos 70–295 km | [M] Huestis 2019 |
| composición de los que ascienden | >80 % hembras; de las hembras ascendentes: 87,5 % grávidas, 0,7 % semi-grávidas, 2,9 % recién alimentadas | [M] Huestis 2019 |
| estados abdominales de las capturas en altura | Sella 1–2 alimentada, 3–5 semi-grávida, 6–7 gravídica | [P] Bamou 2025 |

Regla de modelado: la migración eólica es un **evento raro y de gran escala** con
probabilidad y destino, **no** una "probabilidad de dispersión por celda" (que sería la
misma ficción de la atracción a escala de paisaje). El motor ya tiene
`dispersal.wind_flight_hours` y `dispersal.wind_survival`; lo que cambia es que **el
radio de atracción de 1500 m no debe contaminar este canal**: son escalas distintas.

Dispersión local (a escala de aldea), por el contrario, **sí** es un kernel por
individuo y ya tiene anclaje empírico: 112 m (hembras) de media y 623 m máximo en
MRR continuo en Mali (89,7 % *coluzzii*), con 70 % de las recapturas en otra zona
(Diallo 2026).

### 5.6 Machos: **agregado por especie**, con diagnóstico de enjambre

Decisión tomada **con base en estudios** (no por gusto):

| hecho | valor | evidencia |
|---|---|---|
| Machos inseminados por noche | **≤3 hembras por macho** | [M] *coluzzii* (Ekechukwu & Tripet 2019) |
| Tasa de inseminación en jaula (1:2) | 52,6 % (estrés hídrico del macho) / 40,8 % (estrés de la hembra) | [M] *coluzzii* (íd.) |
| Esperma transferido | 2 856 células (control); 10 598 bajo estrés (3,7×) | [M] *coluzzii* (íd.) |
| Esperma almacenado | 1 700–7 000 células; ~4× menos a los 7 d; debe sobrevivir **meses** | [M] *coluzzii* (íd.) |
| Machos que se emparejan por noche | **7,2 %** de los machos del enjambre | [P] *gambiae* M-form (Diabaté 2011) |
| Geometría del enjambre | 1–3 m de altura; empieza **+5 min** tras la puesta de sol; pico 9–15 min; vacío a 25–30 min; 28,3 ± 0,35 min de duración | [P] (Diabaté 2011; Bimbilé Somda 2018) |
| Tamaño del enjambre | modos ~100 y 180 machos (rango 4–700); **el sitio explica el 47,6 % de la varianza** | [P] (Diabaté 2011; Bimbilé Somda 2018) |
| Efecto de la lluvia | **0 parejas por enjambre** en el pico de lluvias (ago–sep) | [P] *arabiensis* (Bimbilé Somda 2018) |
| Orden apareamiento/alimentación | **98,47 %** de las hembras que copulan quedan inseminadas; sólo **2,97 %** ya había comido ⇒ **el apareamiento precede a la primera comida** | [P] *arabiensis* (Bimbilé Somda 2018) |
| Diferencia por especie | *funestus* forma enjambre al atardecer y **evita** las marcas de contraste; un macho puede inseminar ≥4 hembras | [P] *funestus* (Charlwood 2003) |

**Por qué los machos pueden seguir siendo triviales**: su único papel demostrado es la
fertilización. Con razón de sexes 1:1, un macho puede atender tres hembras por
noche ⇒ **los machos no son limitantes** a 1:1; la cantidad de esperma no cambia el
resultado binario; y no existe ninguna medida publicada que enlace la abundancia de
machos con la tasa de picadura o la supervivencia de las hembras.

**Lo que se pierde de forma permanente con esa decisión**: (i) la **estructura espacial
de los enjambres**; (ii) la **fenología estacional** del enjambre (colapso en lluvias);
(iii) el **aislamiento de sitio de enjambre entre especies**; (iv) los canales de
fertilidad/mortalidad mediados por machos (Zhu 2017: menos apareamientos → menos
reproducción **o** más vuelos → más mortalidad de hembras); (v) cualquier evaluación de
intervenciones dirigidas a machos (ATSB, rocío sobre enjambres, SIT/GM).

**Camino intermedio**: (A) ahora, con **claves por especie** y la probabilidad de
inseminación evaluada por hembra en `TENERAL`; y el motor emite un **diagnóstico de
enjambre** (machos por celda y por noche) para que (B) se pueda calibrar más adelante
sin reescribir el motor.

**Corrección que se lleva el motor**: la supervivencia diaria de los machos es
**0,773 ± 0,094** (0,700–0,865 por estación) [*coluzzii*, Epopa 2017], mientras que el
YAML aplica `ADULT_DAILY_MORT_BASAL = 0,87` (supervivencia) a **ambos sexos** ⇒ el motor
sobrestima la población de machos en ~12 %. La causa es energética: enjambrar y aparearse
cuesta supervivencia futura (Ekechukwu & Tripet 2019). Consecuencia: el macho necesita su
propia clave de supervivencia, o el `0,87` debe revisarse a la baja para el sexo masculino.

**Matiz sobre el momento del apareamiento**: en *arabiensis* el 98,47 % de las hembras
que copulan quedan inseminadas y sólo el 2,97 % había comido ⇒ apareamiento antes de la
primera comida; pero en *gambiae* s.s. (São Tomé) el reparto es **49 % antes / 51 % después**
de la primera comida ⇒ el motor debe **permitir ambas** ventanas (noches 2 y 3), como
propone §5.7.2.

**Coherencia con el ODD**: el ODD **ya tiene** a los machos como individuos con
atributo `sex` y razón de sexes `Bernoulli(0.5)`, y ya tiene un estado `MATE_SEEKING`
que resuelve en una actualización. Su texto dice literalmente "no hay colectivos
emergentes: no hay rebaños, **enjambres**, households ni grupos sociales" y "el
apareamiento es instantáneo (MATE_SEEKING dura una actualización)"; la nota del
revisor que pide "no debería haber colectivos? → p. ej. los machos de mosquito forman
colectivos en muchas especies para atraer a la hembra" (notas del ODD, **p.3**) es
justo lo que esta decisión responde con evidencia. Lo que **cambia** es que la razón
de sexes deja de ser "un valor neutral por defecto, no ajustado" y pasa a ser **una
clave por especie**, y que el apareamiento instantaneous se sustituye por una
**probabilidad por hembra** con momento explícito (al atardecer, antes de la primera
comida).

### 5.7 Cómo se aparean los machos (mecanismo, y por qué no pueden "quedarse quietos")

Tu preocupación —que machos y hembras se separen al principio y la hembra nunca llegue a
fecundarse, mientras los machos se quedan quietos— es **exactamente el modo de fallo que
introduce un modelo espacial de apareamiento**, y por eso el mecanismo tiene que quedar
escrito antes de tocar el motor. La buena noticia: la biología dice que **la hembra es
quien va a buscar al macho**, no al revés.

#### 5.7.1 Lo que hacen los machos (evidencia)

| comportamiento | valor | evidencia |
|---|---|---|
| **Forman enjambre al anochecer**, en sitios fijos | empiezan **+5 min** tras la puesta de sol; pico **9–15 min**; enjambre casi vacío a los **25–30 min**; 1–3 m sobre el suelo | [P] *gambiae* M-form (Diabaté 2011) |
| El enjambre dura | **28,31 ± 0,35 min** (media mensual 19–39) | [P] *arabiensis* (Bimbilé Somda 2018) |
| Tamaño del enjambre | modos **100** y **180** machos; media 118,55 ± 0,65 (ambos sexos); rango 4–700 | [P] (Diabaté 2011; Bimbilé Somda 2018) |
| **El sitio explica el 47,6 % de la varianza** del tamaño; el tipo de marcador, no | F = 0,40, P = 0,26 | [P] (Diabaté 2011) |
| Densidad del campo de enjambre | 190 sitios de enjambre en una aldea; **distancia mediana al enjambre más próximo: 10 m** (25 % a <6,5 m) | [P] (Diabaté 2011) |
| Dónde están | concentrados **a lo largo del área residencial** (modelo "hotspot" de leks) | [P] (Diabaté 2011) |
| Pareamiento por noche | **7,2 %** de los machos del enjambre (SE 0,0095); "1 apareamiento extra por cada 14 machos extra"; el éxito individual **no depende** del tamaño del enjambre | [P] (Diabaté 2011) |
| Capacidad por macho | **≤3 hembras por macho y noche** (limitados por esperma y por tamaño del tapón) | [M] *coluzzii* (Ekechukwu & Tripet 2019) |
| Coste energético | los machos pueden enjambrar noches seguidas, pero el apareamiento **reduce su supervivencia futura** | [P]/[M] (Ekechukwu & Tripet 2019) |
| Diferencia por especie | *funestus* enjambra al atardecer en zonas abiertas junto a las casas de reposo y **evita** los marcadores de contraste; *arabiensis* enjambra **antes** del atardecer de octubre a julio | [P] (Charlwood 2003; Bimbilé Somda 2018) |
| Efecto de la lluvia | el apareamiento **colapsa** en el pico de lluvias: **0 parejas por enjambre** en agosto–septiembre; en el tamaño y la duración del enjambre también | [P] *arabiensis* (Bimbilé Somda 2018) |
| La hembra va al enjambre | "las hembras son en gran medida monándricas y **visitan los enjambres iniciados por los machos al anochecer una vez en su vida** para copular" | [M]/[P] *coluzzii* (Ekechukwu & Tripet 2019) |
| La hembra acepta a cualquiera | "las hembras parecen aceptar cualquier macho entrante" (elección de pareja débil) | [P] (íd.) |
| Refractariedad post-copulación | el **tapón espermático** hace a la hembra refractaria ⇒ en la práctica, **una sola cópula por vida** | [P] (íd.) |
| Momento respecto a la primera comida | **98,47 %** de las hembras que copulan quedan inseminadas y sólo **2,97 %** ya había comido (*arabiensis*); pero en *gambiae* s.s. el reparto es **49 % antes / 51 % después** de la primera comida (São Tomé) | [P] (Bimbilé Somda 2018; Charlwood 2003) |
| Supervivencia del macho | **0,773 ± 0,094/día** (pooled; 0,700–0,865 por estación) | [M] *coluzzii* (Epopa 2017) |

Dos consecuencias que **corrigen el motor actual**:

1. **Los machos NO se quedan quietos**: enjambran al anochecer en sitios fijos y se
   dispersan el resto del día. Y **la señal que atrae a la hembra es el enjambre**, no
   el macho suelto: por eso el enjambre es la entidad que hay que modelar, no el macho.
2. **La supervivencia de los machos es más baja que la de las hembras** (0,773 vs 0,87
   que el YAML aplica a ambos sexos) ⇒ el motor **sobrestima los machos en ~12 %**. La
   causa es física: enjambrar y aparearse cuesta energía.

#### 5.7.2 El mecanismo (agregado espacial, con garantía de suministro)

Se mantienen los machos como **agregado**, pero el apareamiento se modela como un
**encuentro espacial explícito** entre hembras y la **capacidad de los enjambres**:

```
# por noche, por fase EVENING (dentro de la ventana de enjambre)
capacidad_de_enjambre(m, n) = min(0.072 · N_machos(m, n), 3 · N_machos(m, n))  # Diabaté 2011 / Ekechukwu 2019
machos_disponibles(c, n)   = Σ_{m: |c − m| ≤ alcance} N_machos(m, n)          # machos *presentes* al alcance
hembras_competidoras(c, n) = hembras no inseminadas presentes en el alcance     # las que compiten
p(inseminada | hembra, noche) = 1 − exp(− 0.072 · machos_disponibles(c, n)
                                     / max(1, hembras_competidoras(c, n)))   # limitada a 1
```

**Semántica** (corregida tras la revisión): el 0,072 es la **fracción de machos del enjambre
que se aparea esa noche** (Diabaté 2011), es decir una **capacidad**; el tope de 3 hembras
por macho y noche (Ekechukwu 2019) acota por macho. Ninguno de los dos es una probabilidad
por hembra: la probabilidad de que **una** hembra quede inseminada depende de cuántos machos
hay al alcance y de cuántas hembras compiten por ellos, y por eso la expresión divide por
las competidoras (con el tope `min(1, …)`).

Y el **sistema de seguridad** que evita el modo de fallo (hembras sin inseminar por falta
de enjambre accesible):

- **La hembra vuela al enjambre.** Si una hembra no está inseminada y hay un enjambre
  dentro de su alcance de vuelo, la regla de movimiento de esa noche la lleva hacia él
  (esto es lo que hace la hembra real: visita el enjambre). Con la distancia mediana
  entre enjambres de **10 m** en el área residencial, una hembra que vive donde hay
  gente **siempre** tiene un enjambre al alcance.
- **Respaldo local**: los enjambres los **inician los machos** ("swarms initiated by
  males"), así que cualquier grupo de machos puede formar un enjambre pequeño donde esté
  (tamaño real 4–700). Por tanto, **no hay territorio sin pareja**: si hay machos en la
  celda, hay capacidad de apareamiento.
- **Plazo y reintento**: si aun así no se insemina, la hembra lo reintenta cada noche
  (también en noches posteriores a su primera comida, como en el 51 % de *gambiae* s.s.).
  No hay fecha de caducidad: el esperma que ya tiene le dura **de por vida** (incluso
  meses, para la estivación), y ella no vuelve a aparearse (monandria + tapón).
- **Señal de alarma**: el motor emite el número de **hembras adultas sin inseminar por
  más de N noches**, por celda. Si esa cifra crece, el campo de enjambres está roto (o
  no hay quien los forme) y el test falla.

#### 5.7.3 Lo que queda sin respaldo (y hay que calibrar en los escenarios)

| magnitud | estado | plan |
|---|---|---|
| Densidad de **marcadores de enjambre por km²** | **[EP]** — se sabe que se concentran en el área residencial y que están a ~10 m entre sí, pero no hay cifra por km² | se calibra en el escenario E13 (oferta vs demanda) |
| Cómo se decide dónde hay marcador | **[P] parcial**: el sitio explica el 47,6 % del tamaño y los enjambres se concentran en el área residencial ⇒ los marcadores se **derivan del patrón de asentamiento**, no al azar | clave `swarm_markers_source: settlement` |
| Fracción de la población macho que está en enjambre esa noche | **[EP]** | `swarm_participation_frac` |
| Coste energético del enjambre en supervivencia | **[P]** cualitativo ("decreased future survival") | `male_swarm_survival_penalty` |
| Efecto de la lluvia sobre el enjambre | **[P] medido**: 0 parejas por enjambre en ago–sep | `rain_suppresses_swarming` (temporal) |
| Distancia a la que la hembra detecta el enjambre | **[EP]** | `female_swarm_attraction_m` |

#### 5.7.4 Alternativa descartada (y por qué)

Modelar a los machos como individuos con movimiento, enjambre y apareamiento (opción B)
**no** evita el modo de fallo: lo hace **más difícil**, porque el estado de cada macho
importaría para el resultado, y no hay datos de enjambre de *coluzzii* (los hay de
*gambiae* y *arabiensis*). Con el agregado espacial, el resultado depende de **cantidades
medidas** (7,2 %, ≤3 hembras/macho/noche, 10 m entre enjambres, 28 min de ventana) y el
único número libre es la densidad de marcadores, que se calibra en un escenario
sintético. La opción B sólo se justifica si aparece una intervención que dependa de la
estructura fina del enjambre (rooteo de enjambres, SIT/GM).

## 6. Fisiología de la sangre y multipicadura

Investigado el 2026-11; 19 extractos nuevos en `papers/anopheles-dynamics/` (filas 43–61
de `papers/REFERENCES.md`).

### 6.1 Qué dice la evidencia

| Hallazgo | Valor | Fuente | Estado |
|---|---|---|---|
| Volumen ingerido por comida | **~3 µL** de media; 3–4 µL para *Anopheles*; 2,5 µL para *Aedes* | `takken-2024-adult-anopheles-gambiae-behaviour-review.md`, `konopka-2026-coordinated-mosquito-biting-human-skin.md` | [P] review/*Aedes*; **no hay medición en µL de *coluzzii* ni del complejo en Ghana** |
| Comida por sorbo | **volumen de la bomba**, no de sangre: cibial 38,94 ± 9,45 µm³ en *Anopheles* vs 4,77 ± 1,29 en *Aedes*; caudal 12,7 ± 1,7 nl/s (*An. sinensis*) | `ha-2015-feeding-pump-organs-anopheles-sinensis-aedes-togoi.md`, `lee-2016-liquid-feeding-aedes-togoi-anopheles-sinensis.md` | [M] anatomía ⇒ **inferencia [EP]**: "comida mayor por sorbo" (el artículo no reporta volumen de sangre ingerida) |
| Umbral de fin de búsqueda de hospedero | **2,5 µL** en *Aedes* (con menos, sigue buscando) | `klowden-lea-1978-blood-meal-size-continued-host-seeking-aedes.md`, `johnson-2023-blood-meal-size-feeding-frequency-aedes-midgut.md` | [P] *Aedes*; depende de edad y tamaño (`xue-edman-scott-1995-…md`) |
| Umbral de inicio de oviposición | **no reportado en *Anopheles***; el único umbral publicado (0,25 cal de lípido) es de *A. albimanus* y mide reservas, no volumen | `briegel-horler-1993-multiple-blood-meals-reproductive-strategy-anopheles.md` | [EP] |
| Hembras pre-gravíd | necesitan **dos comidas** para madurar ovarios; la primera comida inicia una vitelogénesis limitada | `charlwood-2003-mate-or-a-meal-pre-gravid-anopheles-gambiae.md`, `briegel-horler-1993-…md`, `takken-2024-…md` | [P] *gambiae* s.l. (São Tomé) |
| Continuar buscando mientras maduran | *Anopheles* **sí**; *Aedes* no | `klowden-briegel-1994-gonotrophic-cycle-multiple-feeding-anopheles-aedes.md` | [M] |
| Comidas múltiples por ciclo | 11 % (*gambiae*, Kenia), 14 % (*funestus*, Kenia), 18,9 % (*arabiensis*, Zambia; +3–5 % de sesgo de método), 23,2–25,7 % (Zambia 2017); laboratorio hasta **5** comidas a 6–24 h | `scott-2006-…md`, `norris-2010-…md`, `das-2017-…md`, `briegel-horler-1993-…md` | [M] en *gambiae* s.l./funestus/arabiensis (proxies) |
| Tasa de alimentarse / llegar a repleción | 46,5 % se alimentan; **10 % de las que se alimentan no llegan a repleción**; *pool feeding* 7,5 % y nunca suficiente | `choumet-2012-visualizing-anopheles-gambiae-blood-feedings-mice.md` | [M] laboratorio |
| Mordida a través de ITN | 71 % alimentan con ITN vs 99 % sin ITN | `hauser-2019-anopheles-gambiae-biting-through-permethrin-net.md` | [M] |
| Consecuencia epidemiológica | **3/8 y 6/9** de los pares de convivientes con el mismo genotipo de *P. falciparum* ⇒ un mosquito infecta a más de una persona | `conway-mcbride-1991-genetic-evidence-interrupted-feeding-malaria.md` | [M] |
| Comidas sucesivas y EIP | la comida adicional **acelera** oocistos/esporogonía y acorta el EIP | `brackney-2021-frequency-matters-successive-feeding-episodes.md` | [M] *P. berghei*/*falciparum* |
| Precedente de modelado | tamaño de comida como variable aleatoria; "la provisión de sangre puede requerir varias comidas"; lote ∝ comida; muerte por sobrealimentación | `wu-2020-mbitses-vector-bionomics-emergent-properties.md` | [M] MBITES |
| Palanca de mayor impacto | "probing e ingesting success" son los parámetros más influyentes; el signo de la relación GCD–*R0* puede cambiar | `dahlin-2025-heterogeneous-mosquito-biting-transmission-framework.md` | [M] |

### 6.2 Parametrización (claves **per-especie**, no en el bloque `gonotrophic` global)

| clave | valor | estado | nota |
|---|---|---|---|
| `blood_meal_size_ul` | **3,0 µL** media; rango 1,5–4,0 µL (lognormal, σ = prior) | [P] | sin distribución reportada en la literatura |
| `blood_meal_target_ul` | **6,0 µL** (dos comidas de 3,0 µL) | **[EP]** | ningún estudio reporta el umbral en *Anopheles*; 6,0 µL es el valor coherente con la necesidad de **dos comidas** en pre-gravíd (*charlwood-2003*); 3,0 µL para los ciclos siguientes |
| `meal_size_min_ul` | **2,5 µL** | [P] *Aedes* | para *Anopheles*, prior |
| `probing_success_rate` | 0,465 (lab) … 0,71–0,99 (campo con/sin ITN) | [M] *gambiae* lab | **sustituye** a `feeding_success_rate` |
| `meals_per_cycle_mean` | **0,15** central = nº medio de **comidas adicionales** por ciclo (la fracción medida 11–26 % es de hembras **con** multicomida, no un recuento de comidas) | [P] | depende del estado de ITN (18,9 % → 9,1 %) |
| `first_cycle_target_ul` | > `blood_meal_target_ul` (estado `PRE_GRAVID` propio) | [P] | el primer ciclo es multi-comida por definición |
| `egg_batch` | **proporcional al volumen acumulado** (MBITES), no `binomial(240, 0,5)` fijo | [M] modelo | con tope `egg_batch_max`. **Ojo**: el bloque actual valida la invariante `0 < min <= mean <= max <= n` (`config_validation.py:582`), que un lote proporcional al volumen no puede cumplir ⇒ hay que **redefinir el bloque**, no cambiar un valor |

### 6.3 Cambios en la máquina de estados

1. **Estado nuevo por hembra**: `blood_meal_ingested_ul` (SoA) — hay que tocar
   `swap_with_last` y `resize` en `mosquito_submodel.cpp`.
2. **`feeding_success` deja de ser booleano**: pasa a volumen acumulado (el flag
   "alimentada hoy" se puede conservar, pero ya no significa lo mismo).
3. **Transición nueva**: `PROBING` → (sorteo de volumen `v`) → si `acumulado ≥ target`
   ⇒ ruta actual `BLOOD_FED`; si no ⇒ **vuelve a `HOST_SEEKING` en la misma noche**
   conservando el volumen. Hoy la única salida de un feed exitoso es `BLOOD_FED`, que
   saca a la hembra del bucle de búsqueda hasta el día siguiente.
4. **El pase por fases está roto para multi-comida**: hoy "una hembra alimenta en la
   primera fase activa donde detecta hospedero" y pasa a `BLOOD_FED`; con la nueva
   fisiología debe poder **re-entrar en el bucle dentro de la misma fase y de la misma
   noche** ⇒ iterar fases con un flag "todavía hambrienta" por hembra, no un `break`
   implícito por fase.
5. **Separar dos probabilidades** (`dahlin-2025` las marca como las de mayor palanca):
   `probing_success_rate` (intento → engorde) y `meal_size` (continuo). El
   `feeding_success_rate` actual (0,825) **se carga en `GonotrophicParams` y se documenta
   como el gate `PROBING→BLOOD_FED`, pero el motor no lo consulta**: la transición es
   determinista (`if (picked != nullptr) → BLOOD_FED`, `mosquito_submodel.cpp:757-779` y
   `:855-862`) ⇒ el 0,825 **no afecta a nada**. Se sustituye por `probing_success_rate`
   (0,465–0,99 según contexto) y se retira la clave (`config_validation.py:527`,
   `config_dump.cpp:224`).
6. **El descanso post-prandial sólo tras comida completa**: `resting_duration_days` (0,5)
   se dispara al alcanzar el target; una comida parcial no debe ovipositar.
7. **Inanición (7 días)**: el temporizador usa `gonotrophic_timer`, que se pone a 0 en
   cada transición ⇒ con re-entradas a `HOST_SEEKING` tras cada comida parcial **el
   reloj se reiniciaría** y ninguna hembra moriría de inanición. Hace falta un contador
   propio (p. ej. `days_since_target_reached`) que no se reinicie con comidas parciales.
8. **Rama pre-gravíd**: primera comida ⇒ vitelogénesis limitada; la actividad
   gonotrófica arranca un día más tarde (`charlwood-2003`). El motor ya distingue
   `first_cycle_days` (4,0) de `cycle_duration_days` (2,0): el primer ciclo no es sólo más
   lento, es **multi-comida**.
9. **El reloj de maduración ovárica arranca al alcanzar el target**, no tras la primera
   comida; y el ciclo gonotrófico **se acorta con comidas completadas** (`briegel-horler-
   1993`: la fecundidad sube con comidas sucesivas) ⇒ `cycle_duration_days` y el número de
   comidas dejan de ser independientes.
10. **Lote de huevos proporcional al volumen acumulado** (MBITES), no un
    `binomial(240, 0,5)` en la oviposición.

### 6.4 Consecuencias para la transmisión

- `record_female_feed` sortea `beta_hv × prev` en **cada** comida ⇒ con N comidas por
  ciclo la probabilidad de infección vector→humano por ciclo pasa de 1 sorteo a N; y las
  hembras infecciosas cuentan **cada** comida como picadura infecciosa.
- Una hembra multi-comida puede infectar a **varios convivientes** (evidencia genética:
  3/8 y 6/9 de pares) ⇒ el ledger debe admitir **varios eventos por hembra y por noche**,
  con identificador de hembra y de comida, y distinguir comidas parciales de completas.
- La comida adicional **acelera el EIP** ⇒ el reloj de EIP puede acelerarse en la segunda
  comida (`brackney-2021`).

### 6.4 bis Ventana postprandial (supresión de la búsqueda)

La hembra alimentada **no vuelve a buscar hospedero inmediatamente**: hay una ventana
refractaria medida.

| tiempo tras la comida | respuesta a CO₂ + olor humano | especie | evidencia |
|---|---|---|---|
| 3 h y 24 h | **sin respuesta** | *A. gambiae* | [P] Takken 2001 |
| 40 h | 7 % | *A. gambiae* | [P] Takken 2001 |
| 48 h | 27 % | *A. gambiae* | [P] Takken 2001 |
| 72 h | 68 % | *A. gambiae* | [P] Takken 2001 |
| 72 h | suprimida | *A. gambiae*; *A. aegypti* máximo a las 24 h; *A. stephensi* recuperada a las 72 h | [P] Uehara 2026 |

Además, la **amplitud EAG olfativa** (respuesta a sudor humano y a indol) es
significativamente **menor** en el grupo alimentado que en el control **en el estadio IV de
Christophers**; en los estadios I–III no hay diferencia respecto al control (Takken 2001) ⇒
la atenuación olfativa es **específica del estadio IV**, no una propiedad de toda la
ventana postprandial.

**Consecuencia para el motor**: la puerta está **cerrada por completo hasta 24 h** y se
reabre progresivamente (7 % a las 40 h, 27 % a las 48 h, 68 % a las 72 h); la conclusión
del artículo es *"inhibition … for a period of at least 40 h"*. Por tanto
`blood_meal_refractory_days` representa la **supresión completa** (1–1,5 d), **no** una
ventana de supresión de 40–72 h: a las 48 h la hembra ya responde al 27 % del nivel
control. El motor actual la deja en búsqueda ~2,5 d tras la comida (0,5 d de descanso + 2 d
de maduración) ⇒ es **más conservador que la medida**, no "coherente" con ella. Lo que hay
que añadir es la ventana **explícitamente** (clave `blood_meal_refractory_days`), para que
la multipicadura dentro de la misma noche y la ventana refractaria no se confundan.

**No verificado** (y no se implementa): la reacción de las opsinas visuales a la sangre, y la reactivación por período seco. No hay ninguna fuente leída que lo
documente; el trabajo de 2026 sobre el cerebro de la hembra (Rossi 2026) describe un
cambio global (1 895 genes diferencialmente expresados, con un giro glial) coherente con
un período refractario, pero **no** identifica opsinas como downregulated.

### 6.5 Huecos

- **No existe ninguna medición publicada de volumen sanguíneo (µL) de *coluzzii* ni del
  complejo *gambiae* s.l. en Ghana**: el 3 µL es cifra de review; la cifra de 3–4 µL
  atribuida a *Anopheles* en `konopka-2026` **no es medición de ese artículo** (remite a
  Choumet 2012, donde no se hallan esas cifras) ⇒ atribución **no verificada**.
- **No hay umbral de volumen publicado para el inicio de la oviposición en *Anopheles***.
- **La tasa de *partial feeding* real en campo está esencialmente sin medir**
  (`johnson-2023` lo dice) ⇒ es la magnitud que este rediseño introduce.
- **Contradicción sin reconciliar**: `lee-2016` mide un caudal de ingestión **mayor en
  *Aedes togoi***, mientras `konopka-2026` atribuye al *Anopheles* la comida mayor por su
  mayor volumen de bomba.

## 7. Individuos, picadura y transmisión

- **Selección de la presa**: ruleta sobre tipos de presa ponderada por `pref` de la
  especie y por la distancia (más cerca → más probable), tal como el ODD p.6 pide
  ("the nearest to the borders the less probable that the mosquito bites that agent").
- **`feeding_success_rate` (0,825) se sustituye** por `probing_success_rate`
  (0,465 en laboratorio, 0,71–0,99 en campo con/sin ITN), cableado por individuo
  (pack 02, punto 3). El 0,825 actual no lo consulta el motor: la transición a
  `BLOOD_FED` es determinista (`picked != nullptr`).
- **El estado infectivo se lee del individuo**, no del grid agregado (`human_grid_`).
- La agregación a celda ocurre sólo al escribir salidas.

## 8. Oviposición y cohortes acuáticas

- Los huevos **heredan la posición exacta de la hembra** (pack 02, punto 2), no la celda
  snap-eada; y el parche se resuelve por *posición*, no por `snap_radius_m`.
- La cohorte conserva la posición de la madre → el desarrollo acuático deja de depender
  de que el parche "esté activado" en el mapa de celdas.
- Semántica de parche seco: la congelación de larvas por desiccate se decide por la
  **posición** de la cohorte (memoria #191), no por el estado del parche abstracto.

### 8.1 Época seca, parada ovárica y estivación (nuevo, con evidencia)

La regla actual de "parche seco" mata lo que hay dentro del parche (EGG + L1–L2 por
desecación; y con `k_habitat == 0` la Beverton-Holt da `p = 0` y mata **todas** las
L1–L4 del parche; huevos y pupas sobreviven). Nada de eso afecta a los adultos — y la
literatura dice que la respuesta de la hembra adulta a un hábitat seco **no es morir,
es aplazar**:

| hecho | valor | especie | evidencia |
|---|---|---|---|
| Parada ovárica al inicio de la estación seca | por especie: *coluzzii* **19,23–34,85 %**, *arabiensis* 40,09–48,98 %, *gambiae* s.s. 68,12–68,64 % de las hembras alimentadas **no superan la etapa 2 de Christophers** (el rango agregado 19,23–68,64 % es de las tres especies en los dos sitios) | *A. coluzzii* (sólo su fila) | **[M]** Mamai 2026; en *coluzzii* el arresto es **estacional** (p = 0,004 / 0,018), en *gambiae*/*arabiensis* no hay variación estacional significativa |
| Ranking de especie | *coluzzii* **65,15–80,77 %** > *arabiensis* 51,02–59,91 % > *gambiae* 31,36–31,88 % | | **[M]** Mamai 2026 |
| La parada no es sólo ovárica | incluye **oviposición suprimida incluso con huevos plenamente formados** | *A. coluzzii* | **[M]** Mamai 2026 (citando Yaro 2012) |
| Respuesta de oviposición (hþmbras que ponen tras 3 d con agua) | **70 % → 20 %** | *gambiae* s.s. M-form | [P] Yaro 2012 |
| Tamaño del lote | **173 → 101 huevos** | *gambiae* s.s. M-form | [P] Yaro 2012 |
| Proporción en parada gonotrófica | **5 % → 45 %** (35–50 % de las que no ponen, con huevos arrestados; el 50–65 % restante Maduró pero no puso) | *gambiae* s.s. M-form | [P] Yaro 2012 |
| Tasa de alimentación | **sin cambio estacional** | *gambiae* s.s. M-form | [P] Yaro 2012 |
| Tasa de inseminación | 65 % todo el año; **82 %** en abr–may (seca) | *gambiae* s.s. M-form | [P] Yaro 2012 |
| Supervivencia máxima en estivación | **212 días (7 meses)**; la supervivencia máxima pasa de 4 semanas a 7 meses | *gambiae* s.s. | [P] Lehmann 2010 |
| Persistencia *in situ* de *coluzzii* | presente todo el año seco (ene–may); densidad **10–90×** en dos picos, con máximos **≥6 semanas antes de la primera lluvia** ⇒ persistencia local, no migración; el crecimiento poblacional arranca en **junio** para *coluzzii* frente a **agosto** para *gambiae*/*arabiensis* | *A. coluzzii* | **[M]** Dao 2014 |
| Coste energético de la transición | *coluzzii* es la única que sube lípidos, azúcares, glucógeno y proteína | *coluzzii* | **[M]** Mamai 2026 |
| *gambiae* s.s. **no** estiva | recoloniza por migración | *A. gambiae* s.s. | **[M]** Dao 2014 |

**Consecuencias para el motor**:
1. Una hembra **gravídica sin criadero aceptable no muere ni pone en el vacío**: entra en
   `ARRESTED` (reproducción aplazada) y espera. La "estivación" es un estado, no una
   muerte.
2. La probabilidad de parada, la respuesta de oviposición y el tamaño del lote tienen que ser
   **estacionales**, y la estacionalidad relevante **no es el calendario**: es la
   **racha de días secos de la celda** (el mismo disparador que activa los parches secos).
3. `*gambiae* s.s.` y `*arabiensis*` **no** estivan (Dao 2014) ⇒ la clave
   `aestivation_supported` es **por especie** y vale `true` para *coluzzii*, `false` para
   *gambiae* s.s.
4. La supervivencia en arresto (hasta 212 d) es **muy superior** a la mortalidad adulta
   basal del motor (0,87/día): una hembra en `ARRESTED` no debe morir a los 7 d.

## 9. Parámetros de la especie piloto (*Anopheles coluzzii*)

Dossier investigado el 2026-11; 11 extractos nuevos creados en
`papers/anopheles-dynamics/`. Estado: **[M]** medido en *coluzzii* · **[P]** proxy de
*gambiae* s.l. o congenere · **[EP]** engineering prior del YAML (sin respaldo) ·
**[NR]** no reportado.

### 9.1 Movimiento

| Parámetro | Valor | Fuente (`papers/`) | Estado |
|---|---|---|---|
| Capacidad de movimiento diaria | MDTpD **486–695 m/día** (hembras, 4 experimentos) | `wickramasooriya-2026-coluzzii-mrr-saotome-principe.md` | [M] islas, forma forest, recaptura <1 % |
| Ídem, límite inferior | 40–549 m en 7 días (machos, Burkina Faso) | `epopa-2017-male-coluzzii-mrr-bana-burkina-faso.md` | [M] machos (no persiguen hospedero) |
| Suelo de exploración | 350 m/día (paseo aleatorio validado contra dos kernels empíricos) | `dispersal-kernel-calibration.md` | [P] *gambiae* s.l. |
| Forma del kernel | exponencial (mediana 386 m, p90 1,28 km) vs half-Cauchy (mediana 295 m, p90 1,64 km, p95 2,83 km) | `dispersal-kernel-calibration.md` | [P] **ninguna fuente de coluzzii distingue la forma**; sólo cuantiles FR50/FR90 |
| Cola (cap) | FR90 **902–2 606 m**; recaptura máxima 3 243 m | `wickramasooriya-2026-…md` | [M] |
| Velocidad de vuelo (hembra en busca) | **0,225–0,45 m/s** sobre el suelo (45,1 cm/s suave, 29,0 tortuoso, 22,5 rasante); hasta **0,5 m/s** en el campo de olor | `hawkes-gibson-2016-coluzzii-visual-host-cues-dipping-flight.md`, `cribellier-2018-coluzzii-flight-around-odour-baited-trap.md` | [M] *coluzzii* |
| Velocidad de vuelo (macho en enjambre) | **0,66–0,87 m/s** | `vielma-2026-coluzzii-swarm-flight-speed-burkina-faso.md` | [M] — **no es velocidad de dispersión** ni de búsqueda |
| Radio de **activación** (CO₂, sin dirección) | **100 m** (53 % vs 39 % control) | `lorenz-2013-taxis-assays-range-attraction-100m.md` | [P] *gambiae* s.s. semicampo |
| Radio de **orientación olfativa** | **70 m** (mezcla + CO₂) · **50 m** (sólo CO₂) · **30 m en campo abierto** (el CO₂ solo no orienta) | `lorenz-2013-taxis-assays-range-attraction-100m.md` | [P] *gambiae* s.s. / *arabiensis* |
| Radio **visual** | **25–72 cm** (modelo ocular); respuesta 9,8 %→43,4 % con olor; giro a 0–15 cm | `carnaghi-2023-coluzzii-visual-thermal-landing-targets.md`, `hawkes-gibson-2016-coluzzii-visual-host-cues-dipping-flight.md` | [M] *coluzzii* |
| Radio **terminal** (aterrizaje) | **10–20 cm** (mínimo de velocidad) | `carnaghi-2021-coluzzii-multimodal-landing-synergy.md` | [M] *coluzzii* |
| Umbral sensorial de CO₂ | ORN maxilar **≤ 350–400 ppm**; rastrea 600→4800 ppm sin saturar | `majeed-2017-coluzzii-co2-maxillary-palp-sensory-range.md` | [M] *coluzzii* |
| Tiempo de *casting* / memoria olfativa | **no verificado** (≈ 2 s del resumen de Gemini); dato accesible más próximo: 300 ms en *Aedes* | `audit-gemini-synthesis-host-seeking-numeric-claims.md`, `dekker-carde-2011-aedes-aegypti-surge-cast.md` | **[EP]** |
| Radio de **exploración** | 0,5–0,7 km/día (es el alcance, no un radio de atracción) | derivado de MDTpD | [M]/[P] |
| `host_seeking_radius_m` = 1500 m (YAML) | — | — | **[EP] sin ningún respaldo**: ningún paper mide 1,5 km de atracción |
| Sesgo dirigido hacia el asentamiento | recapturas concentradas en el núcleo habitado (varianza >44 %) | `epopa-2017-…md` | [M] cualitativo, **sin cuantificar** |
| Atractor del hábitat (dirección definida) | oviposición prefiere agua dulce (r = −0,54, p = 0,001); rechaza charcos salinos y ambientes anóxicos | `nwaefuna-2019-oviposition-development-coluzzii-salt-water.md`, `kudom-2015-…md` | [M] |
| Deriva por viento | movimiento alineado con el viento dominante en São Tomé (Rayleigh P = 0,0005 / <0,0001); nulo en Príncipe (valle) | `wickramasooriya-2026-…md` | [M] dependiente del contexto |
| Migración / estacionalidad | población de hembras ×6,72 entre seco y húmedo; ausente >800–1 000 m de altitud | `wickramasooriya-2026-…md`, `tene-fossog-2015-…md` | [M] (islas) |

### 9.2 Vectorial y picadura

| Parámetro | Valor | Fuente | Estado |
|---|---|---|---|
| Composición del complejo en Ghana | *coluzzii* **55,9 % (935/1670)**, *gambiae* s.s. 39,5 %, *arabiensis* 2,3 %, *melas* 2,2 % | `akuoko-2024-biting-behaviour-ghana.md` | [M] |
| Composición en Accra (criaderos) | *coluzzii* **54,79 % (372/677)**; drenajes = 48,21 % de los hábitats positivos | `sabtiu-2025-larval-habitat-diversity-accra-ghana.md` | [M] AOI-local |
| Zona sur de Ghana | *coluzzii* 41 % / *gambiae* 31 % / *funestus* 28 %; **coluzzii exclusivo en la zona costera** | `osae-2015-diversity-resistance-vector-competence-southern-ghana.md` | [M] |
| Antropofilia | HBI ≈ 1 (*funestus*); coluzzii esencialmente antropofágico | `osae-2015-…md` | [M] indirecto (sin HBI numérico para coluzzii) |
| Perfil horario (coluzzii) | EE 25,5 % · LE 48,0 % · EM 26,5 % (bins 18–22 / 22–04 / 04–06) | `akuoko-2024-…md` | [M] |
| ⇒ `activity_weights` derivada | **[0.00, 0.191, 0.676, 0.133]** (DAY no medido) | derivado | **[EP] (perfil [M] Akuoko 2024)** — la redistribución a las fases del motor es una transformación, no una medición; regla: `w_fase ∝ fracción_de_picaduras_de_la_fase × actividad_de_la_fase`, con `w_DAY = 0` por falta de dato (efecto colateral: la actividad diurna desaparece) |
| Tasa de picaduras por noche | [NR] en coluzzii; a ≈ 1/ciclo gonotrófico ≈ 0,33–0,40/día | `biting-rate-eip-gonotrophic-parameters-reference.md` | [P] |
| Tamaño de puesta | **111,67 ± 5,36** huevos/hembra (susceptible), 93,33 ± 10,77 (resistente) | `nkahe-2020-coluzzii-fitness-cost-life-traits.md` | [M] colonia de Camerún — **contradice `egg_batch_n: 240`** del YAML |
| Ciclo gonotrófico | 2–3 d (campo); 2,65 d por defecto del motor; intervalo de oviposición 3 d | `biting-rate-eip-…md`, `nkahe-2020-…md` | [P] |
| EIP | 111/(T−16) d (Detinova); 10–12 d a 25 °C | `biting-rate-eip-…md` | [P] (es del parasite, no del vector) |
| Competencia vectorial | **CSP 1,1 %** en coluzzii vs 3,8 % *gambiae* s.s. y 4,9 % *funestus* | `osae-2015-…md` | [M] — el piloto es **el menos competente** de los tres |
| Resistencia (kdr L1014F) | 0,75–0,90 en coluzzii; vida adulta hembra **13,9 d** (resistente) vs 21,7 d (susceptible) | `osae-2015-…md`, `nkahe-2020-…md` | [M] — el modelo no tiene kdr; la longevidad resistente sí debe entrar en el rango de mortalidad |

### 9.3 Supervivencia y fase larvaria

| Parámetro | Valor | Fuente | Estado |
|---|---|---|---|
| Supervivencia diaria adulta | machos 0,700–0,865 (pooled 0,773 ± 0,094); hembras: mediana >0,5 hasta día 10–11 (Príncipe) / 7–8 (São Tomé húmedo) | `epopa-2017-…md`, `wickramasooriya-2026-…md` | [M] — el `ADULT_DAILY_MORT_BASAL = 0,87` del YAML está en el **borde alto** |
| Desarrollo larvaro vs T | **[NR] en coluzzii**; proxy: *gambiae* s.s. (Bayoh & Lindsay 2003), *gambiae* s.l. Ghana (Agyekum 2022), coluzzii de Camerún 7,57 d (susceptible) / 10,61 d (resistente) a 27 °C | `bayoh-lindsay-2003-…md`, `agyekum-2022-…md`, `nkahe-2020-…md` | [P] |
| Temperatura de cría en campo | mediana 34,9 °C (rango 33,4–37,1) en criaderos con coluzzii (Cape Coast); 27–32 °C en Accra | `kudom-2015-…md`, `sabtiu-2025-…md` | [M] |
| Tipos de cría | drenajes, zanjas bloqueadas, huellas de neumático, charcos de lluvia, arroz irrigado; tolera fecalización; **ausente en agua anóxica** | `sabtiu-2025-…md`, `kudom-2015-…md`, `osae-2015-…md` | [M] |
| Tolerancia a salinidad | eclosión 73 % (dulce) → **0,4 % a 10,5 ppt** → 0 %; LC50 larvaria L3 ≈ 6,7 ppt, L4 ≈ 8,9 ppt; LC50 agudo 24 h **13,0 ppt** (coluzzii) vs 10,3 ppt (*gambiae*); techo fisiológico ~10,5 ppt (≈30 %SW) | `nwaefuna-2019-…md`, `kengne-2019-brackish-water-osmoregulation-mosquitoes.md`, `tene-fossog-2015-…md` | [M] |
| Densidad larvaria | 0,2–5,02 larvas/dip; 22 919 larvas; 77,01 % en temporada lluviosa | `sabtiu-2025-…md` | [M] por *dip* ⇒ no comparable con `K` (ind·km⁻²) |

### 9.4 Auditoría de la fila `species.coluzzii` del YAML

| Clave | Valor actual | Veredicto |
|---|---|---|
| `activity_weights` | [0.02, 0.10, 0.80, 0.08] | **[EP] y probablemente equivocado**: se parece al agregado *gambiae* s.l. (LE 66,6 %), no al perfil de *coluzzii*. **Sustituir por [0.00, 0.191, 0.676, 0.133]** (derivación en el extracto de Akuoko) |
| `weights` (hábitat) | 0.40 / 0.10 / 0.20 / 0.00 / 0.25 / 0.05 | cualitativamente coherente con la evidencia (criaderos permanentes/irrigados, urbanos, temporales de lluvia), pero **los números son [EP]**: ninguna fuente mide afinidad en la taxonomía del contrato; `wetland_pluvial: 0.00` no tiene base documental |
| `pref.human` | 0.99 | coherente (HBI ≈ 1), pero **el reparto ganado/fauna es [EP]** y la medición es *gambiae* s.l. en Ghana sur, no coluzzii |
| `salinity_opt_ppt` | 0.0 | **respaldado** (preferencia de oviposición por dulce; criaderos con mediana 0,8 ppt) |
| `salinity_hi_tol_ppt` | 30.0 | **ambiguo y mal escalado**: sólo es defendible leído como ~30 %SW (≈10,5 ppt); leído como ppt excede la eclosión (0 % a 10,5 ppt), la LC50 larvaria (6,7–8,9 ppt) y la LC50 aguda (13,0 ppt) ⇒ **renombrar clave/unidad** |
| `salinity_slope` | 0.08 (vs 0,12 de *gambiae*) | dirección correcta (razón medida 1,26×, no 1,5×); **magnitud [EP]** (no hay curva medida) |
| `host_seeking_scale_m` | 300.0 | **mecanismo NO respaldado** (§5.4: el decaimiento exponencial de un campo continuo es incompatible con la estructura intermitente de la pluma; Giraldo 2023 respalda gradiente de olor a corta distancia, no un campo de 300 m) ⇒ **retirar** |
| `host_seeking_radius_m` | 1500.0 | **[EP] sin base alguna** ⇒ el mayor hueco de la fila; se renombra como alcance de exploración |
| `dispersal.adult_sigma_m` / `adult_max_m` | 450 m / 2 000 m | coherentes con la literatura y por debajo del FR90 de *coluzzii* (902–2 606 m): **conservadores pero defendibles** |
| `dispersal.adult_prob_day` | **0,05/día** | ⇒ el **95 %** de los mosquitos no se mueve ningún día (la cifra 0,10 que circulaba en documentos era errónea); **valor [EP]**, sin fuente publicada |
| `dispersal.wind_self_speed_ms` | 1,0 m/s | **15–50 % por encima** de la velocidad medida (0,66–0,87 m/s) |
| `dispersal.host_flight_step_m` | 500 m | contradice la capacidad medida (486–695 m/día) y desaparece con la ley nueva |
| `egg_batch_n` (fuera de la fila) | 240 (rango 30–170) | **sin respaldo**: la medida es 94–112 huevos por puesta |

### 9.5 Claves nuevas propuestas en `species.<fila>`

| clave | unidades | valor *coluzzii* | estado | nota |
|---|---|---|---|---|
| `daily_move_capacity_m` | m | 590 (rango 486–695) | [M] | sustituye `adult_sigma_m`; el kernel (exponencial vs half-Cauchy) queda como decisión de forma, no de valor |
| `exploration_range_m` | m | 500–700 | [M] (rango 486–695, MRR *coluzzii*) | alcance de exploración; **no** un radio de atracción. El 350 m/día de *gambiae* s.l. es [P] y no se mezcla en la misma fila |
| `co2_activation_radius_m` | m | 100 | [P] *gambiae* s.s. | radio de activación (sin dirección) |
| `olfactory_radius_m` | m | 70 (semicampo) / 30 (campo abierto) | [P] | radio de orientación; para un AOI abierto se queda en 30 |
| `visual_radius_m` | m | 0,25–0,72 | [M]-modelo | radio visual *coluzzii* |
| `terminal_radius_m` | m | 0,10–0,20 | [M] | radio de aterrizaje |
| `flight_speed_ms` (hembra) | m/s | 0,225–0,45 | [M] | velocidad en busca; **no** la del enjambre |
| `male_ratio` | fracción | 0,5 | [EP] | razón de sexes al nacer (ODD: "neutral default") |
| `insemination_prob` | fracción | 0,95 | [EP] | **respaldo local** (§5.7.2) cuando la hembra no alcanza ningún enjambre; el mecanismo principal es el espacial, no esta probabilidad por hembra |
| `sperm_store_days` | días | 90 | [EP] | ventana de fertilidad tras la inseminación |
| `blood_meal_refractory_days` | días | 1,0–1,5 (supresión completa; recuperación 7 % a 40 h → 68 % a 72 h) | [P] *gambiae* | ventana **cerrada por completo**; no es una ventana de supresión de 40–72 h (§6.4 bis) |
| `gonotrophic_arrest_prob_dry` | fracción | 0,19–0,35 para *coluzzii* (rango medido); el valor por defecto se elige dentro del rango | [M] (rango) / [EP] (valor por defecto) | parada ovárica en época seca. **Por especie**: *coluzzii* 19,23–34,85 %, *arabiensis* 40,09–48,98 %, *gambiae* s.s. 68,12–68,64 % (Mamai 2026) |
| `swarm_pairing_prob_night` | fracción | 0,072 | [P] | fracción de machos del enjambre que se aparea cada noche |
| `male_females_per_night_max` | hembras/macho/noche | 3 | [M] | capacidad de un macho |
| `swarm_duration_min` | min | 28,3 | [P] | duración media del enjambre |
| `swarm_start_min_after_sunset` | min | 5 | [P] | inicio del enjambre |
| `swarm_size_mode` | machos | 100 / 180 | [P] | modos del tamaño |
| `swarm_nn_median_m` | m | 10 | [P] | distancia mediana entre enjambres (define la densidad del campo) |
| `male_daily_survival` | 1/día | 0,773 | [M] | **el YAML aplica 0,87 a ambos sexos** |
| `swarm_markers_per_km2` | km⁻² | — | **[EP]** | único número libre: se calibra en el escenario E13 |
| `swarm_flight_speed_ms` | m/s | 0,66–0,87 | [M] | velocidad del macho **en enjambre**; no sustituye a `wind_self_speed_ms` (1,0), que es velocidad de vuelo propio en dispersión |
| `blood_meal_size_ul` | µL | 3,0 (rango 1,5–4,0) | [P] | volumen por picadura (review *gambiae*; sin dato en Ghana) |
| `blood_meal_target_ul` | µL | 6,0 (primer ciclo) / 3,0 (siguientes) | **[EP]** | umbral de inicio de oviposición (**sin valor publicado**); 6,0 µL por la necesidad de dos comidas en pre-gravíd |
| `meal_size_min_ul` | µL | 2,5 | [P] *Aedes* | por debajo, la hembra sigue buscando |
| `probing_success_rate` | fracción | 0,465–0,99 | [M] *gambiae* lab | sustituye a `feeding_success_rate` (0,825, sin consumidor) |
| `meals_per_cycle_mean` | comidas/ciclo | 0,15 = nº medio de comidas **adicionales** por ciclo (11–26 % medido = fracción de hembras con multicomida) | [P] | depende del estado de ITN |
| `activity_weights` (corregida) | fracción | [0.00, 0.191, 0.676, 0.133] | **[EP] (perfil [M])** | ver §9.4 |
| `salinity_hi_tol_ppt` (renombrada) | ppt | 10,5 (fisiológico) / 2,3 (campo IQR) | [M] | separar "tope fisiológico" de "rango de campo" |

### 9.6 Huecos (no reemplazables por proxy)

1. **MRR de hembras *coluzzii* en África continental**: no existe (los dos MRR de coluzzii
   son machos en Burkina Faso e hembras en islas del Atlántico) ⇒ la capacidad se ancla
   con un rango, no con un valor único.
2. **Forma del kernel de dispersión** en *coluzzii*: no distinguible con los datos
   disponibles; elegir cola pesada infla la colonización a >2 km.
3. **Alcance de detección de hospedero en *coluzzii***: **no existe ninguna medición
   publicada** ⇒ los radios de activación (100 m) y de orientación olfativa
   (30–70 m) son **proxy de *gambiae* s.s./*arabiensis*** y sólo se pueden declarar como
   tales; los únicos radios de *coluzzii* son los **visuales** (25–72 cm, modelo ocular).
4. **Tasa de picaduras por noche** (HBR) de *coluzzii* en Ghana: sin dato.
5. **Curva de desarrollo larvaro vs T** para *coluzzii*: no existe ⇒ proxy *gambiae* s.s.,
   que sobreestima el desarrollo de *coluzzii* en el rango templado de la costa.
6. **¿Vuelve la hembra al mismo criadero?** (skips ovipositorios): sin dato.
7. **Perfil numérico de picadura**: ya no es hueco — el dato existe (Akuoko 2024) y está
   incorporado al extracto.
8. **Latencia de *casting* / memoria olfática**: no hay fuente primaria (el "≈ 2 s" del
   resumen de Gemini no se ha podido verificar); dato más próximo: 300 ms en *Aedes*
   ⇒ **[EP]**.
9. **Aislamiento del sitio de enjambre en *coluzzii***: los datos de enjambre son de
   *gambiae* (*arabiensis*); no hay marcador de enjambre medido en *coluzzii* ⇒ el
   diagnóstico de enjambre será un proxy.
10. **Efecto del número de ciclos gonotróficos** sobre supervivencia, fecundidad o
   antropofilia: **no se ha encontrado ninguna medición publicada** ⇒ `age_days` no puede
   ser variable de estado (ver §12.3).


### 9.7 Cambios concretos en el YAML (decisión C = a: sólo con respaldo en papers)

Cada fila dice qué clave se toca, con qué valor y de dónde sale. "Retirar" = la clave
desaparece (su supuesto es incompatible con la evidencia, §5.3). "Mantener" = el valor
sigue sin respaldo y se marca como tal; **no se "mejora" con un número inventado**.

| clave | actual | nuevo | fuente (`papers/`) | tier | acción |
|---|---|---|---|---|---|
| `species.coluzzii.activity_weights` | [0.02, 0.10, 0.80, 0.08] | **[0.00, 0.191, 0.676, 0.133]** | `akuoko-2024-biting-behaviour-ghana.md` (perfil horario propio de *coluzzii*, redistribuido a las fases del motor) | **[EP] (perfil [M])** | **cambiar** (DAY = 0, no medido ⇒ la actividad diurna se elimina: con `adult_prob_day` 0,05 la dispersión efectiva baja de 5 %/día a 2,5 %/día) |
| `species.coluzzii.salinity_hi_tol_ppt` | 30.0 | **10,5** (con la clave renombrada a la unidad real: ppt, no %SW) | `nwaefuna-2019-…md` (eclosión 0,4 % a 10,5 ppt; LC50 larvaria 6,7–8,9 ppt; LC50 aguda 13,0 ppt) | [M] | **cambiar + renombrar** |
| `species.coluzzii.salinity_slope` | 0.08 | — | no hay curva medida | [EP] | **mantener** (marcado como prior) |
| `species.coluzzii.salinity_opt_ppt` | 0.0 | — | preferencia por agua dulce | [M] | mantener |
| `species.coluzzii.weights` (hábitat) | 0,40/0,10/0,20/0,00/0,25/0,05 | — | la taxonomía del contrato no está medida | [EP] | **mantener** (marcado) |
| `species.coluzzii.pref.human` | 0.99 | — | HBI ≈ 1 | [M] | mantener; el reparto con fauna sigue [EP] |
| `species.coluzzii.host_seeking_radius_m` | 1500.0 | — | sin base | — | **retirar** (§5.3) |
| `species.coluzzii.host_seeking_scale_m` | 300.0 | — | decaimiento exponencial de un campo continuo | — | **retirar** (§5.3) |
| `species.*.host_seeking_radius_m` / `host_seeking_scale_m` (resto de filas) | 1500 / 300 (`arabiensis`: 1500 / **120**) | — | ídem | — | **retirar en todas las filas**. Ojo: `host_seeking_scale_m` **también** pondera el kernel de siembra (`seeding.hpp`) ⇒ retirarla cambia la distribución inicial de la población |
| `gonotrophic.egg_batch_n` | 240 | — | el draw `binomial(240, p)` + recorte [30,170] es [EP] | [EP] | **sustituir por lote ∝ volumen** (MBITES) |
| `gonotrophic.egg_batch_max` | 170 | **no puede bajar de `egg_batch_mean` (120)**: la invariante `0 < min <= mean <= max <= n` (`config_validation.py:582`, test `test_config_validation.py:553`) hace que `max = 112` **rechace el arranque del CLI** | `nkahe-2020-coluzzii-fitness-cost-life-traits.md` (111,67 ± 5,36 huevos; 93,33 ± 10,77 en resistente) | [M] | **cambiar el bloque**: el lote ∝ volumen invalida la invariante ⇒ hay que redefinir `egg_batch_mean`/`min`/`max`/`n` **y** la validación, no un único valor |
| `dispersal.adult_sigma_m` | 450.0 | → `daily_move_capacity_m` = **590** (rango 486–695) | `wickramasooriya-2026-coluzzii-mrr-saotome-principe.md` | [M] | **renombrar + cambiar** |
| `dispersal.adult_prob_day` | 0.05 | 0.05 | ya corregido (el 0,10 de documentos antiguos era erróneo) | **[EP]** | mantener (sin fuente publicada) |
| `dispersal.wind_self_speed_ms` | 1.0 | — (no importar la cifra del enjambre) | `vielma-2026-…md` mide la velocidad del **macho en enjambre**, que no es velocidad de dispersión | [NR] | **no cambiar con esta cifra**: mantener 1,0 como [EP] hasta tener velocidad de vuelo propio en dispersión |
| `dispersal.wind_flight_hours` | 4.0 | revisar contra el rango medido 2–9 h | `huestis-2019-…md` | [EP] | **revisar** (el 4,0 es prior; el rango medido es 2–9 h) |
| `dispersal.wind_survival` | 0.85 | — | `sanogo-2021-high-altitude-survival.md` no da fracción | [EP] | **mantener** (marcado) |
| `dispersal.host_flight_step_m` | 500.0 | — | contradice la capacidad medida | — | **retirar** (ley nueva) |
| `dispersal.snap_radius_m` | 500.0 | — | el parche se resuelve por **posición**, no por proximidad | — | **retirar** o dejar sin efecto (§8) |
| `oviposition.scale_m` | 50.0 | — | mismo problema que `host_seeking_scale_m`: decaimiento de un campo continuo | — | **retirar** (radio de detección por especie) |
| `oviposition.detect_range_m` | 2000.0 | → radio de oviposición por especie | pendiente | [EP] | **cambiar** (§5.4) |
| `oviposition.step_m` | 50.0 | → velocidad × tiempo de fase | pendiente | [EP] | **cambiar** (depende de D1) |
| `host_seeking.detect_range_m` | 2000.0 | → `species.<fila>.co2_activation_radius_m` (100 m, [P] *gambiae* s.s.) | §9.5 | [P] | **cambiar** |
| `host_seeking.approach_step_m` | 50.0 | — (depende de la base temporal, D1) | pendiente | [EP] | **cambiar** |
| `host_seeking.starvation_days` | 7 | 7 | coherente | [EP] | mantener (pero **exige** el reloj propio, §6.3-7) |
| `host_seeking.indoor_attraction_add` / `urbanicity_add` | 0.72 / 0.2 | — | sin fuente | [EP] | **mantener** (marcado) |
| `gonotrophic.feeding_success_rate` | 0.825 | → `probing_success_rate` (por especie) | `choumet-2012-…md` (0,465 lab), `hauser-2019-…md` (0,71–0,99 campo) | [M]/**[P]** | **sustituir** (§6.3-5) |
| `adults.male_daily_survival` (clave **nueva**) | — | **0,773** | `epopa-2017-male-coluzzii-mrr-bana-burkina-faso.md` | [M] | **crear**: la clave actual `adults.daily_mort_basal` es la supervivencia diaria de **ambos sexos** (0,87), no una rama por sexo |
| `mating.swarm_pairing_prob_night` (nuevo bloque) | — | 0,072 | `diabate-2011-gambiae-swarms-mating-success-mali.md` | [P] | **crear** |
| `mating.male_females_per_night_max` | — | 3 | `ekechukwu-2019-coluzzii-sperm-transfer-monandry.md` | [M] | **crear** |
| `mating.swarm_duration_min` | — | 28,3 | `bimbile-somda-2018-arabiensis-swarming-mating-burkina-faso.md` | [P] | **crear** |
| `mating.swarm_start_min_after_sunset` | — | 5 | `diabate-2011-gambiae-swarms-mating-success-mali.md` | [P] | **crear** |
| `mating.swarm_nn_median_m` | — | 10 | `diabate-2011-gambiae-swarms-mating-success-mali.md` | [P] | **crear** |
| `mating.swarm_markers_per_km2` | — | — (se calibra **fuera** del test; E13 lo fija explícitamente) | sin fuente | **[EP]** | **crear, calibrar en E13** |
| `mating.rain_suppresses_swarming` | — | bool (0 parejas por enjambre en ago–sep) | `bimbile-somda-2018-arabiensis-swarming-mating-burkina-faso.md` | [P] | **crear** |
| `mating.female_swarm_attraction_m` | — | **[EP]** | sin fuente | [EP] | **crear** |

## 10. Escenarios sintéticos (paquete de verificación)

Estructura acordada:
- **Ejercitan la cadena real**: alimentar → ovipositar → eclosionar → alimentar.
- **Expectativas calculadas a mano** (no extraídas del propio modelo) **para lo que tiene
  forma cerrada**, e **invariantes + bandas de tolerancia pre-registradas** para lo que
  depende de la ley de movimiento (que no tiene forma analítica): de modo que
  el test pueda fallar primero. Ejemplo de forma: con 200 personas, 10 hembras, alcance de
  contacto R y `probing_success_rate` p, el número esperado de comidas por noche es
  `10 · p · P(dentro de R)` y la distribución entre personas es binomial con esa media.
- **Un maestro de semillas** (pack 09) para que todo el paquete sea reproducible con un
  único seed.

Catálogo propuesto (con la expectativa teórica que cada uno debe satisfacer):

| # | Escenario | Qué fija la expectativa |
|---|---|---|
| E1 | Una hembra, una persona a 200 m, sin crías | 1 comida por noche; la hembra no oviposita; al 3.er día entra en inanición |
| E2 | Una hembra, una persona a 2 km | 0 comidas hasta que la exploración la acerque; la probabilidad de llegada es la de la ley de movimiento |
| E3 | Hembra con `probing_success_rate` bajo y gente en contacto | nº de comidas ≈ N · p · P(contacto); el ledger registra varios eventos por noche |
| E4 | Comida parcial (volumen < `meal_size_min_ul`) | la hembra **sigue** en `HOST_SEEKING` la misma noche; el ciclo gonotrófico no arranca |
| E5 | Comida acumulada alcanza `blood_meal_target_ul` | el ciclo arranca; el lote de huevos es proporcional al volumen acumulado |
| E6 | Primer ciclo (`PRE_GRAVID`) | hacen falta dos comidas; `first_cycle_days` se respeta |
| E7 | Cría cerca, persona lejos | la hembra va a la cría (señal de hábitat), no a la persona (señal de hospedero) |
| E8 | Dos hembras, dos personas | cada una pica a la que le toca por ruleta de `pref` y distancia; **no** hay "celda ganadora" |
| E9 | Hembra infecciosa con varias comidas | varias picaduras infecciosas; probabilidad de infectar a >1 persona (evidencia genética 3/8, 6/9) |
| E10 | Sensibilidad a los radios de percepción (activación 50/100/200 m · olfativa 10/30/70 m · visual 0,25/0,72 m) | cuantifica el peso de cada tramo de la cascada; los valores por defecto son los **verificados** |
| E11 | Ventana postprandial | la puerta está **cerrada por completo hasta 24 h** y se reabre progresivamente (7 % a las 40 h, 27 % a las 48 h, 68 % a las 72 h) (Takken 2001): el motor no debe permitir una comida antes de `blood_meal_refractory_days` y sí debe permitirla después |
| E12 | Parada ovárica en época seca | con racha de días secos, la fracción de hembras alimentadas que **no** supera la etapa 2 de Christophers debe ser la medida (**19,23–34,85 %** en *coluzzii*; el rango agregado de las tres especies es 19,23–68,64 %) |
| E13 | Machos y oferta de apareamiento | el escenario **fija** `swarm_markers_per_km2` (valor explícito en el test, no una constante libre) y **reporta** el resultado: con 100 hembras y 100 machos recién-emergidos en una aldea de 1 km², la **oferta** (0,072 × machos por enjambre × número de enjambres) debe ser ≥ la **demanda** (hembras nuevas); y el número de hembras adultas sin inseminar tras 3 noches debe ser 0 |
| E14 | Machos presentes pero sin enjambre formado | una hembra en una celda con machos **recién emergidos** (antes de su primera ventana de enjambre) **no** debe inseminarse, y el diagnóstico debe emitir la alarma `hembras_sin_inseminar`; la hembra debe **volar al enjambre más cercano** cuando exista |

**Escenarios adoptados** (adversarios del modelo, deben fallar si el modelo es correcto):
- mosquito con gente en la celda pero a 2 km → **no** debe picar (regresión del "celda
  ganadora");
- gente pero sin crías → **no** debe haber eclosión;
- crías pero con salinidad > 10,5 ppt → eclosión ~0 (tope fisiológico medido);
- hembra que no completa el ciclo gonotrófico por comidas parciales → **no** debe ovipositar.

## 11. Observabilidad (qué emite una corrida)

Propuesta de contrato de observación (pack 10), a nivel individual:

| capa | contenido | granularidad |
|---|---|---|
| **Vector** | estado por mosquito: id, especie, posición (x, y), estado gonotrófico, volumen de sangre acumulado, edad/ciclos, infectivo, destino | por tick |
| **Eventos** | picaduras: id de mosquito, id de persona/presa, fase, volumen tomado, resultado (probing ok/fall), transmisión (β_hv / β_vh aplicada) | por evento |
| **Acuático** | cohortes: id, posición de la madre, fase, edad, k_habitat, supervivencia | por cohorte y por tick |
| **Agregados** | celda × día: adultos, cohortes por fase, densidad de personas, picaduras, infecciones, casos | para el COG de estado y las series |
| **Machos y enjambres** | por celda y noche: machos presentes, machos en enjambre, **oferta de apareamiento** (0,072 × número de machos del enjambre) y número de enjambres; hembras **sin inseminar** por número de noches | agregado por celda; el número de hembras sin inseminar es la **alarma** del mecanismo (§5.7.2) |

Consecuencias:
- El COG de estado (contrato 4.0, memoria #195) pasa a tener **bandas de conteos
  crudos por celda** (ya sin normalizar por `K_MAX`), y el nivel individual se guarda en
  un artefacto aparte (parquet/arrow por tick o por día).
- El "ledger" de picaduras pasa de agregado por celda/día a **eventos**, de modo que se
  pueden reconstruir las trayectorias individuales y las cadenas de transmisión
  (mosquito → persona → mosquito → persona).
- Todo con el maestro de semillas (pack 09) para que un escenario sea reproducible bit a
  bit.

## 12. Puntos aún abiertos

### 12.1 Cerrados en esta iteración

| # | Punto | Decisión |
|---|---|---|
| W | Viento: ¿evento aparte o término del vector diario? | **(a) evento aparte** — ver §5.5 |
| S | ¿Existe "olor de asentamiento"? | **no** — movimiento = exploración correlacionada + guiado de olor cercano (§5.1) |
| P | Radio de percepción | **clave por especie** en `species.<fila>` con la cascada documentada y su alcance por especie: activación 100 m · olfativa 70 m (30 m en campo abierto) · visual 25–72 cm · terminal 10–20 cm (§5.1, §9.1) |
| C | Correcciones de parámetro | **se adoptan** (`activity_weights`, salinidad 10,5 ppt, `egg_batch` ∝ volumen), siempre con la cifra medida y su referencia; sin valor medido, no se cambia (§9.7) |
| D1 | Base temporal del movimiento | **opción (a)**: paso macro por fase + micro-simulador local (§3, Q18) |
| D2 | Alcance de la individualización humana | **opción (a)**: todas las personas son individuos; se optimiza después y los escenarios empiezan con poblaciones pequeñas (§3, Q19) |
| D3 | Significado de la banda 1 del COG de estado | **(c) colapso honesto**: banda 1 deprecada (valores = copia de la banda 2, deprecación declarada en el sidecar) y una versión mayor posterior publica **una sola** banda + el artefacto individual (§12.5, Q20). Con "parche por posición" las dos bandas serían idénticas, y publicar una banda con dos nombres distintos es peor que publicar una banda con su nombre correcto |
| D4 | Clave de la cohorte acuática | **pendiente** — (a) celda-clave + posición de la madre como payload vs (b) estado acuático por celda como contrato de primera clase (§12.5, Q21). (a) no cambia el comportamiento acuático; (b) elimina la ruta de error "no PatchState" y habilita la competencia sub-celda, a cambio de renombrar "patch" en toda la cadena y de un bump de contrato |
| D5 | Semántica de la capacidad de enjambre | **(a) cupos + carrera**: cupos = `3 × 0,072 × M` por enjambre y noche; `p = 1 − exp(−cupos/hembras_competidoras)` (§12.5, Q22). Es la única lectura que respeta **las dos** mediciones (0,072 limita el lado macho; ≤3 hembras/macho limita el lado hembra), y hace que la fracción de hembras sin inseminar dependa de la densidad espacial ⇒ la alarma de §5.7.2 discrimina |

### 12.2 Resueltos por la investigación (machos y edad)

| # | Punto | Resolución con evidencia | Lo que queda |
|---|---|---|---|
| M | ¿Machos triviales o colectivo? | **CERRADO (confirmado por el usuario)**: (A) trivial y espacial (§5.7). Mecanismo: capacidad de enjambre = 0,072 × machos (Diabaté 2011), tope 3 hembras/macho/noche (Ekechukwu 2019), la hembra **vuela al enjambre**, respaldo local si hay machos, reintento sin caducidad, y alarma de "hembras sin inseminar" en el diagnóstico | — |
| E | Edad / estado fisiológico de la hembra | **CERRADO (confirmado por el usuario)**: máquina de estados fisiológicos, `gonotrophic_cycles` como reloj + `blood_volume_accumulated` + `ovarian_stage` + `gonotrophic_arrest`; `age_days` sólo diagnóstico (§12.3) | — |

Por qué la opción (b) ("añadir edad en días como variable primaria") **no** se
adopta: en esta ronda no se encontró **ninguna** medición publicada del efecto del número
de ciclos gonotróficos sobre supervivencia, fecundidad, índice de antropofilia o duración del
ciclo. Sin esa medición, `age_days` sería un engineering prior — justo lo que la decisión
C = a prohibe.

**Estado de §12.2**: M y E quedan **cerrados y confirmados** por el usuario. Q17
(época seca) se adopta por su respaldo en la evidencia (Mamai 2026, Dao 2014, Lehmann
2010, Yaro 2012) y es reversible si aparece nueva evidencia.

### 12.3 Opciones para la edad de la hembra (explicadas y resueltas)

Lo que el motor tiene hoy: la "edad" de una hembra es, en la práctica, **un contador
de ciclos gonotróficos completados** (`gonotrophic_cycles`). Las alternativas, y lo que
dice la evidencia de cada una:

**(a) Mantener el estado actual** — la edad *es* el número de ciclos.
- Ganamos: nada que implementar.
- Perdemos: no hay edad *dentro* del ciclo; no se puede expresar "pre-gravídica" ni
  "oviposición retrasada"; no se puede reproducir la composición de estados que miden
  las capturas aéreas (87,5 % grávidas, 0,7 % semi-grávidas, 2,9 % recién alimentadas).

**(b) Añadir `age_days` por hembra** (edad cronológica en días).
- Ganamos: permite mortalidad, fecundidad y respuesta a hospedero dependientes de la edad,
  y el tope de 30 días observado en MRR (Diallo 2026) se vuelve una restricción explícita.
- Perdemos: un campo SoA más (`swap_with_last`/`resize`) y un paso de incremento; y
  **depende de que exista evidencia medida**: en esta ronda **no se ha encontrado ninguna**
  (ni efecto del número de ciclos sobre supervivencia, fecundidad, antropofilia o duración del
  ciclo) ⇒ sería un prior sin respaldo.

**(c) Estado fisiológico explícito** (nullípara / alimentada-nullípara /
  alimentada-para / semi-grávida / gravídica), con transiciones, como en la
  clasificación abdominal de campo (Sella 1–2 alimentada, 3–5 semi-grávida, 6–7
  gravídica).
- Ganamos: es exactamente lo que mide la literatura de campo; encaja con la multivisita
  (pre-gravídica → alimentada → gravídica), con la ventana postprandial (supresión
  completa hasta 24 h; recuperación progresiva del 7 % al 68 % entre 40 y 72 h) y con la
  parada ovárica de época seca (19,23–34,85 % en *coluzzii*).
- Perdemos: no ordena a los individuos dentro de un estado (dos hembras "gravídicas" no se
  distinguen), y **duplica** parte de la máquina gonotrófica que ya existe.

**(d) Híbrido (decisión)**: el ciclo gonotrófico sigue siendo el reloj maestro; de él se
**derivan** los estados fisiológicos (ciclo 0 ⇒ pre-gravídica; ciclo cerrado ⇒
gravídica), y se añaden tres campos: `blood_volume_accumulated` (ya en §6.3),
`ovarian_stage` y `gonotrophic_arrest` (parada de estación seca, §8.1); `age_days`
queda **como campo de diagnóstico** (el ODD ya lo tiene así para las cohortas
acuáticas: `mean_age_days`).
- Ganamos: cubre la multipicadura, la pre-gravídica, la ventana postprandial y la
  estivación sin duplicar la máquina; la estivación interactúa directamente con
  la semántica de "parche seco" que ya tiene el proyecto.
- Perdemos: si en el futuro aparece evidencia medida de dependencia de la edad, habría que
  añadir `age_days` como campo de estado (no como diagnóstico).

**Estado**: (d) es la recomendación y la propuesta; (b) queda descartada por falta de
respaldo medido, no por preferencia.

### 12.4 Pendientes de reconciliación (no bloquean)

| # | Punto | Nota |
|---|---|---|
| — | Cohorte con hémbras 'coluzzii' y 'gambiae' s.s. en el mismo AOI | La decisión de aestivar es **por especie** (§8.1); el motor tendrá que mezclar reglas si el AOI tiene ambas |
| — | Forma del kernel de dispersión local | Ninguna fuente de *coluzzii* distingue exponencial de half-Cauchy (sólo cuantiles FR50/FR90): la forma es decisión de diseño, no un dato |
| — | 'Percepción' como 'radio' o 'sensibilidad' | La evidencia da **radios por tramo**; el parámetro 'cuánto pesa cada uno' en la decisión de picar queda como sensibilidad en el paquete sintético (E10) |

### 12.5 D3, D4 y D5: opciones, implicaciones y qué se rompe en cada caso

Las tres decisiones se toman juntas en el draft: las tres tocan el mismo insieme de
contratos (estado acuático, COG de estado, aparición) y una de ellas puede determinar la
forma de las otras dos.

#### D3 — Qué significa la banda 1 del COG de estado (`adult_patch_count`)

**Contexto verificado**

- `wire.hpp:120–129`: dos bandas, `STATE_BAND_NAMES[2] = {"adult_patch_count", "adult_cell_count"}`;
  contrato 4.0: conteos **crudos** por celda, sin `/K_MAX` ni recorte [0,1].
- `mosquito_submodel.cpp:965–1004` (`update_patch_id`): el adulto se asigna al **parche
  activado más próximo** dentro de `dispersal.snap_radius_m` (500 m), que **no** es la celda
  en la que está ⇒ hoy las dos bandas difieren.
- Los lectores leen **por nombre de banda** (`docs/specs/abm/spec.md` INV-12, INV-16): el
  surrogate toma las 2 bandas (`training/dataset.py:20`, `VECTOR_CHANNELS = 2`) + 4 de
  transmisión = 6 canales; `prediction/state_loader.py` apila 2 + 4.
- Con la regla del §8 ("el parche se resuelve por posición") la banda 1 **coincide** con la
  banda 2 ⇒ dos canales idénticos y un contrato que miente sobre lo que contiene.

**Opciones**

| | Qué pasa a responder la banda 1 | Implicaciones |
|---|---|---|
| **(a)** | **Afiliación reproductiva**: el adulto se cuenta en la celda de su cohorte de origen (o de su último sitio de oviposición) | Dos canales distintos y ambos útiles: "¿dónde va a criar?" frente a "¿dónde está?". El parche sobrevive con un significado preciso. La banda pasa a ser **derivada y con memoria** (cambia en oviposición/emergencia, no cada día) ⇒ deja de ser una foto diaria de la población. Contrato 5.0 (breaking) |
| **(b)** | **Presión de búsqueda de hospedero**: hembras en `TENERAL`/`HOST_SEEKING` por celda | Es el canal que más predice el paso siguiente. Reintroduce la semántica que v4.0 retiró a propósito (`host_seeking_pressure` era el nombre viejo), pero **sin** la normalización por `K_MAX` que lo motivó ⇒ defendible. Obliga a renombrar la banda (el nombre actual describiría otra cosa) |
| **(c)** | **Colapso honesto**: banda 1 deprecada; durante una versión de contrato se rellena con el valor de la banda 2; la 5.0 publica una sola banda + el artefacto individual | Lo más barato y lo más honesto. Se pierde "dónde se cría", recuperable del sidecar acuático (`*_aquatic.json`, `cohort_bank().write_diagnostics`). Los lectores sobreviven una versión |
| **(d)** | **Añadir una banda** en vez de reutilizar: 5.0 con tres bandas (posición · afiliación reproductiva · hembras buscando) | Cambio **aditivo**, no semántico: menos riesgo de lectura equivocada. El surrogate pasa de 2+4 a 3+4 canales ⇒ `VECTOR_CHANNELS` 2→3 y reentrenamiento (de todos modos forzado) |

**Coste común a las cuatro**: los checkpoints del surrogate no son reutilizables en ningún
caso (memoria #195) y el golden byte-idéntico hay que regenerarlo. La elección debe hacerse
por lo que el consumidor necesita, no por los checkpoints.

#### D4 — Clave de la cohorte acuática

**Contexto verificado**

- `aquatic_cohort_bank.hpp`: `CohortKey` = (`patch_id`, `stage`, `instar`).
- `aquatic_cohort_bank.cpp` (`larva_mortality_density`): agrega `larva_per_patch[patch]` y
  calcula `p = s0·K/(K + α·N)` con **N = larvas de las 4 instars sumadas por parche** y
  **K = `PatchState.k_habitat` = `K_ref × cell_area_km2 × S[i]`** (una cantidad de **área
  de celda**).
- `coordinator.cpp`: `PatchState` se construye **sólo para células candidatas** (parches del
  gpkg ∪ células sobre el umbral de potencial), mientras que `S`/`K` existen para **todas**
  las células.
- §8 dice hoy: "los huevos heredan la posición exacta de la hembra" y "el parche se resuelve
  por posición".

**El problema**: si la clave pasa a ser la posición exacta, la agregación por parche/celda se
desarma (cada sub-posición ve un N minúsculo) ⇒ **la dependencia de densidad se apaga en
silencio**, la supervivencia larvaria se infla y el contrato de capacidad queda vacío; y una
cohorte que cae en una célula no candidata se queda **sin** `PatchState` (ni temperatura, ni
salinidad, ni `k_habitat`, ni racha de secas).

**Opciones**

| | Clave y contexto | Implicaciones |
|---|---|---|
| **(a)** | **Celda como clave, posición de la madre como payload**: la cohorte conserva `cell_id` como clave de agregación y guarda `(x, y)` de la madre como atributo (emergencia, reporte de oviposición, geometría de encuentro) | **Cero cambios de contrato**; la dependencia de densidad sigue funcionando sin tocar nada. La hipótesis queda explícita: dentro de una celda las larvas compiten como un único pool (heterogeneidad intra-celda invisible en la fase acuática: limitación documentada). El "cohorte con posición" del §8 se cumple a medias: posición exacta para la eclosión, ecología de la celda |
| **(b)** | **Estado acuático por celda como contrato de primera clase**: promover el campo de hábitat (S, K, temperatura, salinidad, `dry_days`) a registro propio para **todas** las células; `PatchState` deja de portar el estado acuático y "patch" queda sólo como filtro de candidatas/siembra | La solución limpia: toda cohorte tiene contexto. Pero es el más grande de los tres: hay que renombrar "patch" en la ingesta (gpkg `hab_type`/`habitat_potential`), en el seeding, en el JSON de diagnóstico acuático y en el "activated" que hoy también gatilla la llegada a oviposición (`mosquito_submodel.cpp:690–700`); contrato de hábitat 3.0 → 5.0; trabajo de ingesta y registro |
| **(c)** | **Servicio de consulta posición → celda**: arrays `S`/`K`/temperatura/salinidad/`dry_days` para todas las células, precomputados por día (que ya se calculan en `coordinator.cpp::update_habitat_day`), expuestos como una única función que consume todo proceso | Barato; un solo contrato de hábitat; el "patch" puede quedar como vista **derivada** ⇒ si se escriben las dos vistas pueden divergir: hay que elegir una como derivada y generarla |

(a) y (c) son compatibles: (a) decide la clave, (c) decide cómo se consulta el contexto.

#### D5 — Semántica de la capacidad de enjambre

**Contexto verificado (con la aritmética)**

- Diabaté 2011 (*gambiae* M, Mali, **[P]**): "per-male mating probability per night: 0,072
  (SE 0,0095), i.e. ~7 % de los machos de un enjambre se aparean cada noche" y "una cópula
  adicional por cada 14 machos adicionales"; 1 456 parejas en 70 enjambres (rango 0–93, moda
  6) ⇒ con la regla `0,072·M` y una cópula por macho, la moda 6 implica un enjambre de ~83
  machos, coherente con las modas de tamaño 100/180. Supuesto explícito del artículo: "cada
  macho se aparea **como mucho una vez** por noche".
- Ekechukwu 2019 (*coluzzii*, **[M]**): "un macho puede inseminar **~3 hembras** por noche";
  "las hembras son en gran medida monándricas y visitan los enjambres **una vez en su vida**"
  (fuente secundaria, [NO-VERIFICADO]); "**las hembras son claramente el sexo limitante**"
  con "~7 % de los machos se empareja cada noche".
- **Conflicto en la evidencia**: el propio extracto de Ekechukwu rotula "**los machos** son el
  sexo limitante en el enjambre" mientras la cita dice "las hembras son claramente el sexo
  limitante". De ahí depende toda la semántica.
- El tope de 3 hembras/macho limita el **lado hembra**; el 0,072 limita el **lado macho**
  (qué fracción de los machos se aparea). El §5.7.2 los mezclaba, y el tope de 3 nunca
  acota si se compara con `0,072·M`.

**Las dos lecturas, con números** (100 hembras, un enjambre de 100 machos):

| Lectura | Regla | Resultado | Consistencia |
|---|---|---|---|
| **R1**: los machos limitan a la hembra | `p = min(1, 0,072 × M_alcance)` | `p = 1` ⇒ las 100 hembras se inseminan ⇒ hacen falta 100 cópulas con 7,2 machos ⇒ **14 hembras por macho** | **contradice** el tope de 3 de Ekechukwu |
| **R2**: las hembras compiten por cupos | cupos = `3 × 0,072 × M` = 21,6; `p = 1 − exp(−cupos/competidoras)` | ~19 hembras inseminadas (7,2 machos × 3) | coherente con **las dos** mediciones |

**Opciones de implementación**

| | Mecanismo | Implicaciones |
|---|---|---|
| **(a)** | **Cupos + carrera** (R2): el enjambre ofrece `3 × 0,072 × M` cupos; las hembras no inseminadas al alcance los compiten; `p = 1 − exp(−cupos/competidoras)` | Respeta las dos cifras medidas. La fracción de hembras sin inseminar **depende de la densidad espacial** ⇒ la alarma de §5.7.2 discrimina de verdad. Coste: la **tasa de llegada de hembras al enjambre no está medida** ⇒ ese número sale del modelo (no de una medición) y arrastra el prior de `swarm_markers_per_km2` y de la regla de vuelo |
| **(b)** | **Cupos + asignación determinista** (R2 con reparto por orden) | Sin aleatoriedad extra y tests más fáciles; introduce un orden artificial (quién llega primero) ⇒ el resultado depende del criterio de orden, que hay que fijar en la especificación para que sea reproducible e interpretable |
| **(c)** | **Saturación por disponibilidad de machos** (R1): `p = min(1, 0,072 × M_alcance)` con el tope de 3 aplicado después como restricción | Más simple; el tope de 3 pasa a ser un recorte posterior (puede generar descartes); las hembras sin inseminar sólo aparecen **por ausencia de machos**, no por densidad ⇒ la alarma de enjambre apenas discrimina |
| **(d)** | **Sin geometría de enjambre** (agregado puro): probabilidad por hembra a partir de la densidad de machos por celda | Lo más barato. El arquitecto escéptico señaló que el modelo espacial puede no cambiar ninguna salida epidemiológica ⇒ habría que **medirlo** (E13/E14 como test de equivalencia) antes de pagar su coste; se pierde el diagnóstico de enjambre |

**Qué hay que decidir**: (i) la semántica (R1 vs R2), (ii) el reparto de cupos (carrera vs
determinista), (iii) si se mantiene la geometría de enjambre (opción (d) = no).

**Decisión (Q22): (a) cupos + carrera.** Los cupos del enjambre son
`3 × 0,072 × M` (21,6 con 100 machos); las hembras no inseminadas dentro del alcance los
compiten y `p = 1 − exp(−cupos/competidoras)`. La fracción de hembras sin inseminar
resultante es una **salida** del modelo (depende de la densidad espacial y del prior de
`swarm_markers_per_km2`), no un valor fijado a mano ⇒ es lo que hace útil la alarma de
§5.7.2.

#### D4 — Qué cambia exactamente con (b), y qué deuda deja (a)

**Decisión (Q21): pendiente.** El análisis se desarrolla aquí porque es la decisión con
más radio de impacto y la que más fácilmente se subestima.

**Lo que "patch" significa hoy, exactamente** (verificado):

- `coordinator.cpp:156-236` (`to_dataframe`): los candidatos son la **unión** de las
  células del gpkg y las células cuyo potencial estático ≥ `habitat_candidate_min_engine`.
  **Sólo esas células** reciben un `PatchState` (`wire.hpp:179-194`) con el estado acuático
  del día: `rain_d`, `temp_d`, `salinity_ppt`, `habitat_avail`, `habitat_dry_days`,
  `k_habitat`.
- Los datos por celda **ya existen** para todas las células (`K_cell_[idx]`,
  `dry_days_[idx]`, `climate_->rain_at(r,c)`); lo que hoy se materializa es sólo el
  subconjunto de candidatas.
- `patch_id` es un id sintético por celda candidata (del gpkg si está, si no un contador).
  `oviposition_seeking.cpp:36-52` filtra por `activated` y usa el potencial del gpkg, con
  **fallback** a `ps.habitat_avail` si el patch no está en el gpkg ⇒ ya hoy hay **dos
  fuentes** de "potencial".
- `aquatic_cohort_bank.cpp:308` lanza `runtime_error` si una cohorte cae en una célula sin
  `PatchState` ("has no PatchState for today — cannot resolve capacity").

**(a) Celda-clave + posición de la madre como payload — qué cambia**

- El **comportamiento acuático no cambia**: la cohorte sigue teniendo la celda como clave y
  la competencia sigue siendo por celda (1 km²). Es el comportamiento de hoy.
- Lo nuevo: la cohorte guarda el `(x, y)` exacto de la madre ⇒ **los adultos nuevos
  emergen donde puso los huevos la madre**, no en el centro de la celda (que es lo que pide
  el §1 del brief).
- No hay bump de contrato de hábitat; `patch_id` sigue significando lo que significa; el
  sidecar acuático sólo gana campos.

**Deuda que genera (a)** — cuatro cosas concretas:

1. **La celda sigue siendo la unidad de competencia**: todas las larvas de un km² compiten
   como un único grupo ⇒ **la sensibilidad al tamaño de celda permanece** (un artefacto
   clásico de ABM). Con los alcances medidos (486–695 m/día), la heterogeneidad real es
   más fina que 1 km².
2. **Deuda de vocabulario**: "patch" sigue queriendo decir "celda candidata", mientras que
   el lado de adultos ya no tiene parche (Q20 = c) ⇒ dos vocabularios conviviendo.
3. **Deuda de contrato menor**: `patch_id` sigue en el sidecar acuático y en el banco de
   cohortes, y convive con una noción de parche que en el gpkg es de otra granularidad.
4. **La ruta de error sigue viva**: `aquatic_cohort_bank.cpp:308` puede seguir lanzando si
   una celda con cohorte deja de ser candidata.

**(b) Estado acuático por celda como contrato de primera clase — qué cambia**

- `PatchState` pasa a ser un registro **por celda para todas las células** del AOI, y
  "patch" deja de ser un contenedor de información para pasar a ser un **filtro de
  elegibilidad** (booleano). El campo de hábitat diario pasa a ser un contrato de primera
  clase.
- Lo que hay que tocar, en el código: `coordinator.cpp` (materializar el estado de todas
  las celdas en vez de las candidatas), `oviposition_seeking.cpp` (filtrar por el nuevo
  booleano de elegibilidad en vez de por `activated`), `aquatic_cohort_bank.cpp` (la clave
  y el `patch_id` → `cell_id`), `mosquito_submodel.cpp` (`update_patch_id` → afiliación por celda), el sidecar JSON acuático (`patch_id` → `cell_id`), y el nombre del tipo en todo
  el C++ (~15 puntos de uso).
- Lo que hay que tocar, fuera del motor: el contrato de hábitat 3.0 → 5.0 (los contratos de
  estado y de entorno se versionan por separado, memoria #195), el gpkg (su papel se
  reduce a potencial estático + tipo por celda candidata) y la **unificación de las dos
  fuentes de potencial** que hoy conviven, y el test de paridad Python/C++
  (`test_habitat_python_contract`), que hay que extender al nuevo registro.
- Coste computacional: despreciable (5 525 celdas × ~40 B ≈ 220 kB por día; los campos ya
  se calculan para todas las celdas).
- Lo que compra: (i) **ninguna celda puede quedarse sin contexto** ⇒ la ruta de error
  `aquatic_cohort_bank.cpp:308` desaparece por construcción; (ii) vocabulario honesto;
  (iii) es la **precondición de la competencia sub-celda**: si algún día se quiere que dos
  hembras a 50 m dentro de la misma celda no compitan como un único pool, (b) es la base
  sobre la que se puede añadir una clave más fina; (a) no lo es.
- Lo que cuesta: un bump de contrato y un renombrado en toda la cadena, en el mismo PR
  donde ya se mueven el COG de estado, la capa humana y el ledger ⇒ radio de impacto
  mayor.

**La diferencia, en una frase**: con (a) el modelo sigue siendo, en la fase acuática, un
modelo de charcos de 1 km² (con memoria de dónde puso los huevos la madre); con (b) el
modelo pasa a tener un **estado acuático por celda**, y "charco" deja de ser una categoría
del mundo y pasa a ser un filtro.

#### D3 — Detalle operativo de la deprecación (Q20 = c)

- **4.1 (MINOR)**: la banda 1 `adult_patch_count` **se mantiene** en el shape (los
  lectores por nombre siguen funcionando y el surrogate conserva sus 2 canales ⇒ se puede
  reentrenar sin cambio de forma), pero sus valores pasan a ser la **copia de la banda 2** y
  el sidecar lo declara: `"deprecated_bands": ["adult_patch_count"]` con nota de que la
  afiliación reproductiva ya no se publica.
- **5.0 (MAJOR)**: se publica **una sola banda** (`adult_count`, la de posición) más el
  sidecar nuevo con las estadísticas por individuo. `VECTOR_CHANNELS` 2→1 en
  `training/dataset.py`, actualización de `prediction/state_loader.py` y del golden del COG
  de estado.
- Lo que **no** se pierde: la información de "dónde se cría" sigue en el sidecar acuático
  (`*_aquatic.json`, con sus cohortes y patch ids) y en el artefacto individual nuevo; y el
  `patch_id` sigue vivo en el lado acuático (ver D4), de modo que nada se descarta por
  prisa.


## 13. Orden de ejecución previsto

**Estrategia de entrega**: **un único PR** que se cierra cuando el plan entero esté
ejecutado, con **commits** por paso (el PR es la unidad de revisión; el commit es la unidad
de cambio). Cuando toque implementar, los cambios independientes se aplican en
paralelo con subagentes sobre ramas de trabajo separadas, y se integran al final; el
brief y el plan se redactan primero.

0. **Arnés de escenarios sintéticos** (prerrequisito de todo lo demás): hook de siembra por
   individuo (x, y, sexo), override de población humana por celda, semilla por escenario y
   ruta de ejecución que **no** pase por el modo manifiesto (`run_abm_from_manifest` valida
   completitud contra el catálogo de ingesta). Reutiliza el generador de fixtures existente
   (`tests/fixtures/make_golden_fixtures.py`, AOI 8×8) extendido a 10×10. Sin este paso,
   E1–E14 no son ejecutables y el resto del plan no tiene termómetro.
1. **Verificación sintética mínima** (escenarios E1–E2 con la cadena actual, marcando los
   fallos esperados) — sin tocar el motor. Es el termómetro: todo lo que sigue se mide
   contra él. Es un **script**, no un test con aserciones que fallan: escribe
   observado-vs-esperado en `runs/_check_current/` y termina con código 0.
2. **Individuos humanos** + ledger por individuo + picadura con `probing_success_rate`
   (sustituyendo a `feeding_success_rate`, que el motor ni siquiera consulta).
3. **Acumulación de volumen sanguíneo** + multipicadura + umbral gonotrófico + estado
   `PRE_GRAVID` + ventana postprandial explícita + reloj de inanición propio (§6.3,
   §6.4 bis).
4. **Cascada de percepción y movimiento emergente por especie**: activación / orientación
   olfativa / aproximación visual / aterrizaje, con la velocidad de vuelo medida;
   retirada de `host_seeking_radius_m` y `host_seeking_scale_m`; `detect_range_m` y
   `host_flight_step_m` derivados de la evidencia (§5.1–§5.4).
5. **Estado fisiológico**: `ovarian_stage`, `gonotrophic_arrest` (estación seca) y la
   semántica de parche seco = "no hay criadero", no "mueren" (§8.1).
6. **Cohortes con posición de la madre** (parches por posición) y semántica de parche seco.
7. **Machos triviales pero configurados**: `male_ratio`, `insemination_prob` (respaldo
   local), ventana de apareamiento al atardecer, **capacidad de enjambre espacial**
   (marcadores derivados del patrón de asentamiento, 0,072 × machos, ≤3 hembras/macho/
   noche), regla de movimiento de la hembra hacia el enjambre + **diagnóstico de enjambre**
   (oferta vs demanda, hembras sin inseminar). Escenarios E13/E14 como puerta de entrada
   (§5.7).
8. **Escenarios E3–E14 completos** con expectativas calculadas a mano.
9. **Recalibración**: los scorers D-xx se desplazan (más picaduras ⇒ más transmisión;
   maduración retardada ⇒ menos oviposiciones por día-hembra; parada en época seca ⇒ caída
   en la producción larvaria). **La política de comparación hay que crearla**: hoy el
   comparador "run anterior" no tiene referente — el marco de scoring de este checkout
   (`mal-core/src/mal_core/scoring/`: `registry.py`, `scorers/base.py`, `runner.py`) escribe
   un `scorecard.json` por corrida y **no** guarda historial ni `max_delta`. Hace falta un
   registro de corridas con clave de comparabilidad (`constants_sha256` + versión de
   contrato) y una corrida de referencia fijada.

Cada paso es un PR (memoria #228/#233: nada directo a `main`).

## 14. Riesgos

- **Coste computacional**: el tamaño de la población humana debe **derivarse del
  manifiesto** (`human_total`), no de una constante escrita a mano (el ODD habla de ~32 M;
  la cifra real depende del AOI). Con D2 = (a) (todas las personas son individuos), el estado
  individual cuesta ~58 B por persona ⇒ **2–4 GB por corrida** a escala de país, más el
  coste de ageing/timers diario (O(N) por día: 64 M × 30 d ≈ 2 000 M de actualizaciones,
  trivial en C++). **Se optimiza después**: materializar sólo a los humanos que un mosquito
  pica (o un muestreo estratificado con pesos) exige que el `human_id` sea **determinista y
  estable** (`celda × slot + slot`) desde el primer día, o el contrato de observación se
  rompe al cambiar la representación.
- **Los checkpoints del surrogate** entrenados con bandas normalizadas ≤3.0 no son
  reutilizables (memoria #195).
- **La línea base de calibración se desplaza**: el comparador "run anterior" deja de ser
  comparable ⇒ hay que definir la política de comparación (pack 08/calibración).
- **Proxy en casi toda la cadena sensorial**: los radios de activación (100 m) y de
  orientación olfativa (30–70 m) son de *gambiae* s.s. y *arabiensis*, **no** de
  *coluzzii*: no existe ningún radio de detección de hospedero medido en *coluzzii*.
  Los únicos valores de *coluzzii* son los **visuales** (25–72 cm, modelo ocular) y la
  sensorialidad del CO₂ (≤350–400 ppm).
- **Atribución no verificada**: las cifras de 3–4 µL para *Anopheles* en
  `konopka-2026` no son medición de ese artículo (§6.5).
- **Coluzzii es el vector MENOS competente de los tres** del sur de Ghana (CSP 1,1 % vs
  3,8 % de *gambiae* s.s. y 4,9 % de *funestus*): como piloto es lo correcto (es la local y
  la dominante), pero como indicador de malaria subestimará el riesgo.
- **El piloto no es universal en el AOI**: en el peri-urbano de Accra predomina
  *gambiae* s.s.; *coluzzii* es la especie de la franja costera y de las aldeas costeras; y
  *gambiae* s.s. **no estiva** (Dao 2014) ⇒ la semántica de época seca es **por especie**.
- **La parada ovárica de estación seca es la mayor incertidumbre nueva**: el rango medido
  es **por especie** (*coluzzii* 19,23–34,85 %; *arabiensis* 40,09–48,98 %; *gambiae* s.s.
  68,12–68,64 %) y **estacional** en *coluzzii* (p = 0,004 / 0,018), no en las otras dos;
  el motor tendrá que elegir un valor por especie y por hábitat, y esa elección es un prior
  inevitable.
- **El viento como evento aparte** no se ha tocado todavía: la decisión W = a deja el
  canal `dispersal.wind_*` como estaba, y sus parámetros (`wind_flight_hours` 4,0,
  `wind_survival` 0,85) siguen siendo [EP].
