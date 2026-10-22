# Plan 2 — Oferta de criaderos mediante proxies: download → ingest → ABM

- Fecha: 2026-10-17.
- Estado: EJECUTADO 2026-10-17 (contract v3.0 landed). H/A/w/K in mal_core.habitat + habitat_availability.hpp; ingest/download wired; pending real-data run.
- Diseño conceptual aprobado: oferta explícita por tipo de hábitat `H[i,g]`, dos respuestas temporales compartidas —persistente y pluvial— y afinidad por especie y hábitat `w[s,g]`.
- Complemento: [Plan 1 — Sustitución completa del sistema anterior](01-retirada-hidrologia-dem-escorrentia.md).
- Identificador propuesto: `proxy_habitat_v1`.
- Prioridad: MVP verificable con fuentes existentes. No reconstruir charcas ni añadir nuevas fuentes sin necesidad demostrada.
- Política de entrega: ruptura completa y corte único con plan 1. Sistema nuevo sustituye al anterior; no se añade como backend opcional.
- Premisa urbana conservada: filtraciones, fugas y almacenamiento humano aportan oferta persistente estimada, aunque JRC no detecte agua y falte lluvia.

## 1. Qué significa «capacidad de acumular y secar» aquí

JRC + cobertura/uso del suelo + lluvia + temperatura permiten construir una **aproximación estadística de oferta y persistencia de criaderos**. No identifican volumen, profundidad, número de pozas ni infiltración real.

Separar cuatro magnitudes:

| Magnitud | Significado | Unidad |
|---|---|---|
| Predictor observado | Agua detectada, fracción de cultivo, humedal, construido, etc. | Fracción u ocurrencia, según producto |
| Oferta potencial `H[i,g]` | Intensidad relativa del tipo de hábitat `g` en celda `i`, independiente de especie y meteorología diaria | Índice, no superficie de charcas medida |
| Disponibilidad `A[i,k,t]` | Qué parte relativa de oferta con respuesta temporal `k` está disponible en fecha `t` | Índice entre 0 y 1 |
| Capacidad acuática `K[i,s,t]` | Escala usada por regulación de densidad del banco larvario | Número efectivo de larvas, calibrado |

«Acumular» será recuperar/saturar disponibilidad tras lluvia. «Secar» será perder disponibilidad durante periodos sin lluvia. No guardar estas variables bajo nombres `water_mm`, `volume_m3` o «profundidad».

## 2. Alcance mínimo y exclusiones

### Incluido

- Dos fuentes estáticas: JRC GSW y ESA WorldCover.
- Dos forzantes: precipitación CHIRPS y temperatura del aire ERA5-Land como proxy térmico.
- Pocos tipos de hábitat explícitos por celda; distinguir urbano, agua superficial, humedal, abierto y cultivo donde proxies permitan aproximarlos.
- Solo dos respuestas temporales compartidas: persistente y pluvial. Más tipos de hábitat no crean un solver ni un estado dinámico por tipo.
- Un estado pluvial con memoria; disponibilidad persistente constante como baseline mínimo.
- Configuración de afinidades acuáticas por especie; primera integración con especie actualmente soportada.
- Integración de capacidad, candidatos, activación y pérdidas acuáticas sin cambiar conducta adulta.
- Validación separada de funcionamiento, plausibilidad ecológica y mejora predictiva.

### Excluido del MVP

DEM, TWI, D8, transporte de agua entre celdas, curvas profundidad–volumen, LiDAR, predictor global de microrelieve, mapas de pozos, nuevos productos de suelo/infiltración, cartografía obligatoria de riego, química del agua no observada y rediseño multiespecie simultáneo del motor.

Agricultura no significa riego; construido no significa pozos; humedal no significa agua permanente. No inferir estas equivalencias como datos medidos.

La ausencia de infraestructura observada no obliga a anular hipótesis urbana: el MVP incorpora un prior humano persistente positivo y explícitamente incierto. No es garantía de agua real en toda celda urbana ni introduce tercera respuesta hidrológica.

## 3. Estado actual observado en código

Mapa inicial basado en inspección de código al redactar primera versión el 2026-10-17; revalidar al implementar. No es auditoría de datasets locales. Toda disponibilidad real se comprobará con catálogo al ejecutar el plan.

1. `mal-commonlib/src/mal_commonlib/data/loaders/worldcover.py` ya expone clases de cultivo, construido, terreno abierto, agua, humedal y manglar. Su ruta `_load_worldcover_pc` usa nearest-neighbour por clase y selección `argmax` en grilla AOI: no conserva composición subcelda. No se pueden recuperar fracciones desde su salida categórica kilométrica.
2. `mal-commonlib/src/mal_commonlib/data/loaders/jrc_gsw.py` lee occurrence, aplica `DEFAULT_THRESHOLD_PCT` y reproyecta máscara por nearest-neighbour. Output registrado como `jrc_water` no equivale a occurrence continua ni a fracción correctamente integrada de píxeles nativos dentro de celda.
3. Registro WorldCover actual: `worldcover_lc`, `worldcover_water`, `worldcover_wetland`, `worldcover_mangrove`. JRC actual: output `water_occurrence` → `jrc_water`, aunque implementación produce máscara umbralizada.
4. Registro y CLI autoprovisionan DEM para hábitat y no incluyen WorldCover en perfil ABM por defecto.
5. Loader ERA5 ya puede producir temperaturas diarias, pero `registry.py` configura `water_temp` por ruta mensual y `runner.py` reduce por año a TIF. `daily_nc.py::_annual_raster_stack` vuelve a emitir esa temperatura anual cada día. Dimensión diaria del NC no demuestra variación térmica diaria.
6. Ingest genera candidatos desde DEM/TWI/JRC. C++ vuelve a filtrar TWI al cargar GPKG.
7. Capacidad actual se deriva estáticamente en ingest y vuelve a escalarse por agua en banco acuático. `Engine` conecta vista de K al construir, condicionada a existencia de host landscape: nueva capacidad debe funcionar también sin hosts.
8. `mal-core/src/mal_core/download/catalog.py` es contrato obligatorio de resolución: `Slot`, `resolve_inputs`, `DOWNLOADER.manifest_keys` e `INGEST_ARTIFACTS`. Nunca introducir búsqueda por nombres convencionales en consumidores.

## 4. Datos y agregación: conservar composición, no relieve

### 4.1 WorldCover: reutilizar fuente existente

Definir output propuesto `class_fractions` en loader WorldCover, manifest key propuesta `worldcover_fractions`. Sustituir ruta categórica que pierde composición para estos usos y migrar consumidores en mismo corte. No mantener implementaciones antiguas equivalentes por compatibilidad. Una salida categórica para visualización independiente, si sigue siendo necesaria, deriva del producto canónico y no contiene otra ruta de estimación de hábitat.

Retorno recomendado: `xr.Dataset` estático. Runner ya persiste datasets estáticos como NetCDF y writer acepta `xr.Dataset`; no hace falta desarrollar otro formato multibanda.

Variables por celda AOI, calculadas desde ventanas nativas de 10 m:

| Variable propuesta | Clase WorldCover | Interpretación |
|---|---|---|
| `lc_tree_frac` | 10 | Cobertura arbórea; no medición de sombra sobre charcas |
| `lc_open_frac` | 20 + 30 + 60 | Arbusto, pastizal y suelo desnudo/vegetación escasa; agrupación explícita del MVP |
| `lc_crop_frac` | 40 | Cultivo, sin asumir riego |
| `lc_built_frac` | 50 | Construido, sin asumir drenaje defectuoso o depósitos de agua |
| `lc_water_frac` | 80 | Agua de esa clasificación, distinta de occurrence JRC |
| `lc_wetland_frac` | 90 | Humedal herbáceo, no garantía de persistencia anual |
| `lc_mangrove_frac` | 95 | Manglar; no convertir automáticamente a agua dulce |
| `lc_other_frac` | 70 + 100 | Nieve/hielo y musgo/liquen, conservados para cierre de composición |
| `lc_valid_fraction` | Píxeles válidos | Cobertura observada dentro del dominio considerado |

Las ocho fracciones de clase se expresan sobre superficie válida; suman 1 donde hay cobertura suficiente. `lc_valid_fraction` se expresa sobre superficie objetivo, para no disfrazar falta de observaciones como clase ausente.

Algoritmo:

1. Leer ventanas nativas por bloques; no descargar mosaico global ni conservar resolución de 10 m en runtime.
2. Crear indicadores por clase **antes** de reducir a grilla AOI.
3. Agregar áreas de intersección válidas a celdas destino. Promedio de indicadores con ponderación de área, nodata excluido; nunca promedio de códigos de clase.
4. Resolver bordes y solapamientos de tiles sin contar superficie dos veces.
5. Guardar fracciones, validez, CRS, transform, coordenadas, año real, versión y método de agregación.

No hace falta una nueva fuente para cultivos, humedales o terreno abierto. Tampoco interpretar fracción dominante como fracción de cobertura.

### 4.2 JRC: separar ocurrencia temporal de fracción espacial

Añadir output propuesto `habitat_features`, manifest key propuesta `jrc_habitat_features`, también `xr.Dataset` estático.

Mínimo:

- `jrc_occurrence_mean`: promedio espacial ponderado de occurrence nativa normalizada a [0,1]. Es frecuencia histórica de detección de agua, **no porcentaje actual de superficie inundada**.
- `jrc_persistent_frac`: proporción espacial válida de píxeles con occurrence ≥ umbral de persistencia operativa.
- `jrc_intermittent_frac`: proporción de píxeles con 0 < occurrence < ese umbral. Indica agua histórica menos frecuente; no identifica por sí sola estación ni mes de inundación.
- `jrc_valid_fraction`: fracción de dominio con observaciones válidas. Excluir valores de nodata/no observación antes de agregar.

Umbral inicial de continuidad operativa: 80%, heredado como **heurística**, no definición universal de agua permanente. Guardar valor en metadata/config y evaluar sensibilidad; no usarlo como veto para criar en celda.

Seasonality/recurrence mensual sería mejora opcional si producto y endpoint elegidos lo ofrecen sin esfuerzo adicional significativo. No bloquear MVP para conseguirlos. No llamar «seasonality» a occurrence umbralizada: JRC distingue esos productos.

Occurrence usa histórico y tiene edición/ventana temporal propia: fecha STAC no implica serie anual del año solicitado. Registrar versión, periodo observado real, año pedido y snapshot real. No afirmar que se descarga «agua de 2024» si se obtiene snapshot histórico.

### 4.3 Forzantes temporales

- CHIRPS diario ya previsto: conservar mm/día, coordenadas y calendario; días sin observación no equivalen a lluvia cero.
- El canal térmico de este contrato representa **temperatura del aire a 2 m de ERA5-Land**, no temperatura medida del agua. `water_temp`/`water_temp_c` es etiqueta histórica engañosa para ese proxy.
- Añadir output ERA5 propuesto `air_temp_daily`, manifest key propuesta `era5_air_temp_daily`, usando producto con fechas diarias y declarando formato `daily`. Antes de implementarlo, verificar mediante catálogo el producto, calendario, cobertura y resolución realmente disponibles; no inferir disponibilidad por el código del loader.
- **Situación del contrato antiguo:** la ruta actual configura temperatura por ruta mensual, runner la reduce a raster anual y `daily_nc.py::_annual_raster_stack` puede repetir ese raster en cada fecha. Que NC tenga dimensión `time` no convierte ese valor en observación diaria: puede ser la misma temperatura anual replicada todos los días.
- **Contrato canónico nuevo:** banda `air_temp_c(time,y,x)` con timestamps reales, unidades °C, calendario, fuente, variable ERA5-Land y altura de referencia de 2 m sobre superficie, máscara/nodata y método de remuestreo declarados. No emitir además `water_temp_c` como alias.
- La serie diaria puede alterar desarrollo, supervivencia y EIP frente al raster anual repetido. Esa alteración es cambio de forzante biológico y debe medirse/reportarse por separado en A/B; no atribuir automáticamente todo cambio de malaria al nuevo modelo de hábitat. Congelar parámetros biológicos no significa que entrada térmica equivalente permanezca igual.
- La temperatura diaria es necesaria para preservar explícitamente los consumidores térmicos que la requieran. La extensión opcional `gamma_T` de secado empieza en cero: en baseline la temperatura **no** acelera ni retarda disponibilidad pluvial. Solo activarla como ablación posterior con evidencia y sensibilidad.
- Migrar todos los consumidores activos del canal anterior —writer de ingest, reader C++, climate, respuestas térmicas acuáticas/EIP si lo consumen, scoring, entrenamiento, predicción y documentación— en un solo cambio de contrato. Inventariar consumidores directos e indirectos; no dejar un subsistema leyendo banda antigua ni retirar un consumidor por accidente.
- Archivos TIF anuales, manifests y ejecuciones anteriores **no se borran ni se reinterpretan**. Se conservan como artefactos históricos, no como alternativa del runtime nuevo. La revisión nueva rechaza el contrato anterior con instrucción para regenerar el env; reproducir resultado antiguo requiere checkout histórico correspondiente.
- Sin alias `water_temp_c`→`air_temp_c`, doble escritura, lectura dual, reducción anual de fallback ni conversión anual→diaria. Si una climatología anual tiene uso científico independiente futuro, requerirá variable y contrato separados con consumidor justificado; no puede hacerse pasar por la serie diaria.
- Mantener interpolación espacial como remuestreo: nunca afirmar que lluvia o temperatura tienen resolución informativa de 1 km porque se escriban en esa grilla.

### 4.4 Reglas comunes

CRS, transform, extensión, orden de ejes y centros de celda deben coincidir; misma forma de array no basta. Este es contrato básico de cualquier mapa, no motivo para volver a microhidrología.

Aplicar máscara de dominio terrestre/costero existente. Océano abierto no es hábitat; no eliminar automáticamente lagunas o manglares que puedan importar para especies salobres. Salinidad sigue como módulo independiente, con sus limitaciones actuales.

Definir política explícita de cobertura incompleta: error si no puede sostenerse estimación; cualquier degradación parcial permitida debe quedar marcada. No rellenar todo nodata con cero ni renormalizar silenciosamente una pequeña porción observada como si cubriera celda completa.

## 5. Modelo mínimo propuesto

### 5.1 Capas → oferta por hábitat: reglas explícitas, sin matrices de conversión

Cadena canónica:

```text
capas estáticas → H[i,g] → H[i,g] × A[i,k(g),t] × w[s,g] → S[i,s,t] → K[i,s,t]
```

Se retira la fórmula agregada anterior `B[i,k]` y sus coeficientes `alpha[k,g]`. No se introduce `theta` como matriz de conversión de capas a hábitats. El cambio es de diseño, no un renombrado algebraico: guardar solo una oferta persistente y otra pluvial perdía la distinción urbano/humedal/abierto/cultivo antes de aplicar preferencias.

#### Glosario único

| Símbolo | Qué es | Ejemplo/función |
|---|---|---|
| `i` | Celda de simulación | Una celda AOI, sin asumir siempre 1 km² |
| `t` | Fecha de actualización | Un día, con historial causal |
| `s` | Especie | Perfil de la especie activa |
| `g` | Tipo de hábitat proxy, no una capa ni una especie | `urban_persistent`, `crop_pluvial` |
| `H[i,g]` | Oferta potencial de ese tipo, entre 0 y 1 | Reglas estáticas de tabla siguiente |
| `k` | Respuesta temporal | Solo `persistente` o `pluvial` |
| `k(g)` | Asignación fija de tipo a respuesta temporal | `urban_persistent` → `persistente`; no coeficiente aprendido |
| `A[i,k,t]` | Disponibilidad de esa respuesta en esa fecha | Persistente = 1; pluvial = estado `z` |
| `w[s,g]` | Afinidad relativa de especie por tipo de hábitat | Puede distinguir urbano de humedal aunque ambos sean persistentes |
| `S[i,s,t]` | Oferta adecuada y disponible para especie | Suma ponderada de sección 5.4 |
| `K_ref[s]` | Escala de capacidad acuática | Larvas efectivas por km² a índice 1, pendiente de calibración |
| `clip(x,0,1)` | Limitar un número al intervalo [0,1] | `min(1,max(0,x))`; no convierte índice en probabilidad |

No hay `F` genérica en el contrato nuevo: cada regla nombra directamente las capas que usa. **Lluvia y temperatura no entran en `H`**; son forzantes temporales o biológicos. No es necesario aprender una matriz de coeficientes para construir estos proxies.

#### Reglas mínimas por tipo de hábitat

Usar abreviaturas locales solo para legibilidad:

```text
P = jrc_persistent_frac[i]
V = lc_wetland_frac[i]
U = lc_built_frac[i]
O = clip(lc_open_frac[i] + lc_water_frac[i], 0, 1)
C = lc_crop_frac[i]
```

| Identificador `g` | Regla explícita de `H[i,g]` | `k(g)` | Interpretación |
|---|---|---|---|
| `surface_persistent` | `P * (1 - V)` | `persistente` | Potencial de agua persistente en contexto menos asociado a humedal |
| `wetland_persistent` | `P * V` | `persistente` | Potencial persistente asociado a contexto de humedal |
| `urban_persistent` | `beta_urban * U` | `persistente` | Aporte humano persistente hipotético, incluso con JRC=0 |
| `wetland_pluvial` | `(1 - P) * V` | `pluvial` | Potencial de humedal sin respaldo persistente en baseline |
| `open_pluvial` | `(1 - P) * O` | `pluvial` | Potencial abierto y agua WorldCover no respaldada como persistente |
| `crop_pluvial` | `(1 - P) * C` | `pluvial` | Potencial ligado a cultivo; no supone riego |

Son seis contribuciones estáticas y **solo un estado dinámico pluvial por celda**, no seis sistemas hidrológicos. Se separan abierto/cultivo y persistente/humedal para que `w[s,g]` pueda expresar preferencias sin añadir matrices libres ni requerir nuevos datasets.

Precondición: capas finitas, en rangos válidos y con cobertura suficiente, conforme a sección 4. No usar `clip` para ocultar nodata, sumas de clases erróneas o unidades incorrectas; corregir/rechazar entrada antes de calcular `H`.

Estas reglas son **baseline de ingeniería propuesto**, no relaciones estimadas por estudios citados. Restricciones y límites:

1. `P * V` usa contexto de celda: no demuestra coincidencia espacial entre píxeles de agua y humedal. Dos porcentajes marginales no permiten recuperar su intersección real. Tampoco `1-P` es un mapa observado de suelo seco. Guardar estas operaciones como proxies, no hectáreas medidas.
2. `surface_persistent + wetland_persistent = P`: se reparte una única señal persistente; no se vuelve a añadir JRC como otro hábitat independiente. La partición por contexto sigue siendo aproximación subcelda declarada.
3. `lc_water_frac` entra solo como parte de `O`, no como segunda oferta persistente sumada a JRC. `jrc_occurrence_mean` e `jrc_intermittent_frac` quedan para control/diagnóstico de esta primera versión; no añadirlos otra vez a `H` sin revisar solapamientos y versionar reglas.
4. Las seis `H` son intensidades proxy, no fracciones mutuamente excluyentes de agua real. No sumar `H` y reportar resultado como superficie inundada. La normalización fija de pesos de sección 5.4 mantiene índice acotado sin fingir partición física exacta.
5. Humedal sin señal JRC persistente sigue pudiendo producir oferta, pero baseline la hace depender de lluvia. Cultivo irrigado sin señal observada no recibe oferta anual por definición. Son limitaciones evaluables, no hechos sobre cada terreno.
6. Superficie construida aporta aquí oferta persistente humana; no se añade aún grupo urbano pluvial separado. No confundir esta simplificación con ausencia real de charcos de lluvia urbanos.
7. Árboles, manglar y otras coberturas no reciben automáticamente índice genérico de cría dulceacuícola. Conservar capas para dominio/diagnóstico y declarar posibles falsos negativos; no inventar intercepto universal para ocultar limitación. Bosque no equivale a ausencia biológica demostrada de criaderos.
8. En datos inválidos no calcular ofertas como si faltase agua; aplicar política de validez de sección 4.4. No usar tamaño total de ciudad ni proporción de patches urbanos del AOI como multiplicador.

Si validación exige coincidencia agua/humedal observada, estudiar agregación conjunta de fuentes nativas. No inferirla mediante `min(P,V)` o producto y etiquetarla «medida». Esa mejora no es requisito del MVP.

#### Aporte urbano persistente: premisa conservada

`beta_urban` es un **escalar**, no una matriz: convierte fracción construida en índice de oferta humana persistente. No expresa preferencia de especie; eso corresponde a `w[s,urban_persistent]`.

- Baseline exige `0 < beta_urban <= 1`, para mantener regla acotada. Valor exacto es prior de ingeniería, no coeficiente establecido por artículos citados; no se inventa aquí una calibración.
- Con construido positivo, oferta urbana sigue positiva sin señal JRC ni lluvia. No multiplicarla por `P`, `z` ni otro veto hidrológico.
- Entra una vez como `H[i,urban_persistent]`; no añadir después capacidad urbana extra ni profundidad mínima.
- Mantener fijo durante primer ajuste de `P0`, `tau_ref` y `K_ref`; probar sensibilidad, incluida ablación cero explícita, no como default silencioso.

Los pesos `w` determinan cuánto aprovecha especie esa oferta. Tener oportunidad urbana no implica que cualquier especie la use ni que cada celda contenga un criadero observado.

### 5.2 Disponibilidad pluvial y memoria de secado

Un estado normalizado `z[i,t] ∈ [0,1]`, actualizado una sola vez por día:

```text
d[i,t] = exp(-delta_days / tau[i,t])
z_dry  = z[i,t-1] * d[i,t]
z[i,t] = z_dry + (1 - z_dry) * (1 - exp(-rain[i,t] / P0))
A[i,pluvial,t] = z[i,t]
```

`exp(x)=e^x` es función exponencial. `d` indica fracción que queda tras secado; `z_dry` es disponibilidad restante. `1-exp(-rain/P0)` recupera parte del espacio libre `1-z_dry`: sin lluvia vale cero y con lluvia grande tiende a uno. `delta_days=1` en actualización diaria normal; lluvia debe corresponder al mismo intervalo. Misma `A[i,pluvial,t]` se consulta para los tres tipos pluviales, sin volver a avanzar estado por cada uno.

Parámetros:

| Parámetro | Unidad | Papel |
|---|---|---|
| `P0 > 0` | mm de lluvia | Escala de recuperación de disponibilidad; no profundidad de charca |
| `tau_ref > 0` | días | Memoria de secado del componente pluvial |
| `gamma_T >= 0` | 1/°C | Sensibilidad térmica opcional de memoria |
| `T_ref` | °C | Referencia matemática, no óptimo biológico |

Inicio mínimo: `tau[i,t] = tau_ref`, `gamma_T = 0`. Calibrar primero `P0` y `tau_ref`; no asignar una constante libre por celda.

Extensión acotada, solo tras baseline:

```text
tau[i,t] = tau_ref * exp(-gamma_T * (temperature[i,t] - T_ref))
```

Comprobar rango numérico y límites de uso antes de activarla. Esta respuesta es proxy de persistencia; no ecuación Penman–Monteith ni estimación de evaporación real. No reutilizar coeficiente antiguo 0,07/°C como evidencia de `gamma_T`.

Ejemplo **solo para tests**, no recomendación de campo: `P0=10 mm`, `tau_ref=5 días`, `gamma_T=0`, estado inicial cero. Lluvia de 10 mm produce `z=1-exp(-1)≈0,6321`; día siguiente sin lluvia, `z≈0,5175`. Sin más lluvias, semivida = `5*ln(2)≈3,466 días`.

No se proporcionan valores de producción ficticiamente calibrados. Seleccionarlos en fase experimental y guardar sensibilidad/rango de uso.

### 5.3 Componente persistente

Baseline del MVP:

```text
A[i,persistente,t] = 1
```

Se aplica a todos los tipos cuyo `k(g)=persistente`, incluido urbano. Mantiene disponibilidad del **potencial estimado**, no garantiza agua real ni convierte toda celda con río en criadero. Magnitud depende de cada `H[i,g]` y `w[s,g]`. Una celda urbana sin agua JRC puede, por hipótesis, conservar pequeña oferta durante sequía.

No responde a sequías extraordinarias: limitación explícita del baseline. Si validación muestra necesidad, ampliar sin nuevo solver:

```text
A_p = b_p + (1-b_p) * z_p
```

`z_p` usaría misma ecuación con memoria mayor y `b_p` sería respaldo persistente. Esto añade parámetros y estado; **no es requisito de primera entrega**. Proximidad a agua grande puede justificar estudiar esa dependencia, no introducir automáticamente alimentación subterránea.

### 5.4 Afinidad por especie y escala de capacidad

```text
S[i,s,t] = sum_g w[s,g] * H[i,g] * A[i,k(g),t]
K[i,s,t] = K_ref[s] * cell_area_km2[i] * S[i,s,t]
```

- `sum_g` significa sumar una contribución por cada uno de los seis tipos de tabla; no por capa original ni por clase temporal.
- `w[s,g] >= 0` y suma sobre los seis tipos = 1 para cada especie. Perfil fijo incluye todos los identificadores; no renormalizar según hábitats presentes en celda o lluvia del día. Cero oferta debe reducir índice, no redistribuir preferencias a otros tipos.
- Es convención de índice relativo, no reparto de huevos ni probabilidad de elegir destino. Un especialista puede concentrar peso en un tipo; un generalista repartirlo. Comparación de abundancia entre especies requiere además `K_ref[s]`; no inferirla solo de pesos normalizados.
- Un vector con todos los pesos cero, IDs duplicados/desconocidos, grupos ausentes, negativos o suma incorrecta produce error. No convertir automáticamente antiguo perfil por `k` a nuevo perfil por `g`.
- Con `H` y `A` entre 0 y 1, `S` queda entre 0 y 1 sin `clip` global que esconda exceso de suma o invalidación de datos.
- Afinidad actúa sobre **tipo de hábitat**, no directamente sobre código WorldCover: cobertura es proxy de oportunidades, no terreno por sí mismo como causa biológica. Dos tipos persistentes pueden tener pesos diferentes.
- `S` es índice relativo de oferta adecuada, no probabilidad de presencia ni malaria.
- `K_ref` tiene unidades de larvas efectivas por km² a índice 1. No adultos/m² ni volumen de agua.
- Área real de celda, incluida intersección con dominio cuando corresponda; nunca `1e6 m²` fijo para todos los AOIs.
- MVP: perfil de especie actualmente activa, `Anopheles coluzzii`, y estructura extensible. No afirmar soporte simultáneo de otras especies por añadir una tabla.
- Se distingue contexto de humedal/urbano/abierto/cultivo, pero no sombra real sobre charcas, química, salinidad ni tipos de recipientes. No afirmar ecología completa de `funestus` o `stephensi` por disponer de seis pesos. Tipos adicionales requieren evidencia y cambio explícito de schema/perfiles.
- Preferencia acuática cambia oferta/capacidad, no kernels de movimiento, host preference o mortalidad adulta.
- No multiplicar `S` por otra aptitud térmica si banco acuático ya aplica desarrollo/supervivencia térmica. Efecto térmico sobre secado, si se activa, debe mantenerse conceptualmente separado y comprobarse por ablación.

Definir `S_max[i,s] = sum_g w[s,g] * H[i,g]`: oferta adecuada con todas las disponibilidades en 1. Se usa solo para disponibilidad relativa/activación cuando haga falta, no como segundo multiplicador de K. Con `S_max=0`, capacidad y disponibilidad relativa son cero.

#### Ejemplo integrado, solo didáctico

Celda con `P=0,20`, `V=0,10`, `U=0,40`, `O=0,30`, `C=0,20`; usar `beta_urban=0,10` solo para ilustrar cálculo. Con disponibilidad pluvial `z=0,50`:

| Tipo `g` | `H[i,g]` | `A[i,k(g),t]` | `w[perfil_A,g]` | `w[perfil_B,g]` |
|---|---|---|---|---|
| `surface_persistent` | 0,18 | 1 | 0,10 | 0,10 |
| `wetland_persistent` | 0,02 | 1 | 0,10 | 0,50 |
| `urban_persistent` | 0,04 | 1 | 0,50 | 0,10 |
| `wetland_pluvial` | 0,08 | 0,50 | 0,05 | 0,05 |
| `open_pluvial` | 0,24 | 0,50 | 0,10 | 0,10 |
| `crop_pluvial` | 0,16 | 0,50 | 0,15 | 0,15 |

Resultado: `S[perfil_A]=0,066` y `S[perfil_B]=0,058`. Ambos perfiles asignan peso total 0,70 a tipos persistentes y 0,30 a pluviales; aun así difieren porque uno aprovecha más contexto urbano y otro humedal. Agrupar primero por `k` y aplicar solo dos pesos perdería esa diferencia.

Perfiles A/B no corresponden a especies medidas ni sugieren valores para Ghana. `S=0,066` no significa 6,6% de presencia ni superficie de agua.

### 5.5 De dónde salen parámetros y cómo pulirlos sin sobreajustar

| Elemento | Procedencia inicial | Qué se valida/ajusta |
|---|---|---|
| Capas y fracciones | JRC y WorldCover, con validez/procedencia | Agregación y significado observacional |
| Reglas de `H` y `k(g)` | Baseline de ingeniería explícito de sección 5.1 | Sensibilidad de proxies y errores de clasificación, no geometría inventada |
| `beta_urban` | Prior positivo por premisa humana acordada | Sensibilidad y, con observaciones adecuadas, ajuste regional |
| `w[s,g]` | Literatura/juicio experto específico de especie, con grado de evidencia | Rangos y contrastes por hábitat; no derivar cifras de WorldCover |
| `P0`, `tau_ref` | Respuesta temporal a contrastar | Ajustar con series de disponibilidad/larvas y meteorología cuando existan |
| `K_ref` | Escala acuática no observada directamente por satélite | Ajustar a abundancia/emergencia, o declarar ajuste indirecto limitado |

Cada valor tiene unidad/rango, fuente, versión y estado (`engineering_prior`, `literature_prior`, `fitted`). Artículo que describe asociación cualitativa no proporciona automáticamente peso numérico universal; tampoco proporción de hábitats de una muestra equivale a preferencia corregida por disponibilidad.

Observaciones útiles: hábitats georreferenciados, tipo, presencia/conteo de larvas, fecha, disponibilidad de hábitats alternativos y esfuerzo/detección. Modelar sesgo de muestreo antes de estimar afinidad. Sin ellas, priors siguen siendo hipótesis sometidas a sensibilidad, no calibración entomológica.

Identificabilidad: `beta_urban`, pesos y `K_ref` pueden compensarse. Fijar reglas, prior urbano y afinidades durante primer ajuste; variar inicialmente solo `P0`, `tau_ref` y una escala `K_ref`. Casos de malaria solos no identifican limpiamente todos esos efectos. Evaluación reservada y criterios de sección 7 siguen obligatorios; no introducir matriz libre de conversión ni un parámetro por celda para mejorar ajuste aparente.

## 6. Integración técnica

Todos los nombres nuevos de esta sección son **propuestos**, no APIs ya disponibles. Son contrato único tras corte: no aliases para nombres antiguos, parsers duales ni selector de sistema hidrológico.

### 6.1 Download y catálogo

| Dataset | Output nuevo | Manifest key nueva | Formato |
|---|---|---|---|
| `jrc_gsw` | `habitat_features` | `jrc_habitat_features` | Dataset NC estático |
| `worldcover` | `class_fractions` | `worldcover_fractions` | Dataset NC estático |
| `era5` | `air_temp_daily` | `era5_air_temp_daily` | NC diario |

1. Prototipar agregación en tier experimental; no poner fórmula exploratoria directamente en core. Verificar resultados y tests antes de promover.
2. Al promover, actualizar loaders existentes y `DOWNLOADER.outputs/manifest_keys`, formatos y defaults; migrar callers y borrar outputs/implementaciones sustituidas. Registry descubre módulos automáticamente: no crear lista paralela de proveedores.
3. Nuevo perfil y `_ensure_env_stack` solicitan solo productos canónicos; eliminar perfil/opciones del sistema anterior según plan 1. Conservar descargas de hosts/viento para sus funciones propias.
4. Declarar dependencias reales mediante `Slot(..., required=True, per_year=...)` en consumidor nuevo. El flag `required_for_abm` del manifest es metadata; no sustituye contrato de slots.
5. Resolver exclusivamente mediante catálogo. Mismo manifest con archivo ausente produce error incluso si se ve otro archivo parecido en disco.
6. Escribir producto nuevo con schema y procedencia. No registrar `jrc_water` antiguo como features nuevos ni `worldcover_lc` como fracciones.
7. Mantener atribuciones WorldCover, JRC, CHIRPS y ERA5 y condiciones de licencia en registros/derivados. No acceder a credenciales directamente ni añadir nuevas credenciales para estas mejoras de agregación.
8. No implementar conversión desde máscara JRC antigua, land-cover kilométrico o temperatura anual: información necesaria ya se perdió. Mensaje de error pide regenerar desde fuente; no activar descarga/ingest antigua automáticamente.
9. Registro antiguo de producto retirado puede permanecer en manifest histórico, pero no como proveedor, slot, key alternativa o resolución por compatibilidad en código nuevo. Migrar uso legítimo independiente a producto canónico o justificar producto realmente distinto.

Comandos orientativos **tras implementar outputs**:

```bash
uv run malariasim download --aoi <AOI> --datasets jrc_gsw --outputs habitat_features
uv run malariasim download --aoi <AOI> --datasets worldcover --outputs class_fractions
uv run malariasim download --aoi <AOI> --datasets era5 --outputs air_temp_daily --years 2024,2025
```

No ejecutar descargas durante mera redacción ni asumir rango temporal adecuado para todos los experimentos.

### 6.2 Ingest

Puntos a modificar: `mal_core/ingest/daily_nc.py`, `mal_core/ingest/env.py`, registro de artefactos y rutas CLI afectadas.

Contrato propuesto del env nuevo:

- Atributos: `contract_version=3.0`, `habitat_model=proxy_habitat_v1`, versión de reglas explícitas y catálogo de tipos, `beta_urban`, procedencia, cadencia real de T, política de nodata e inicialización. Son identificación y validación, no selectores de implementación; reader admite solo contrato actual.
- Estáticos: `habitat_potential(habitat_type,y,x)` con los seis `H[i,g]`; coordenada `habitat_type` contiene identificadores explícitos de sección 5.1. Área real de celda, features WorldCover/JRC necesarias para auditoría y validez/dominio quedan en `(y,x)`.
- Definición de IDs, orden y `k(g)` procede de único schema versionado compartido por ingest/reader/perfiles. No confiar en orden implícito de bandas ni mantener tablas Python/C++ divergentes. Pesos de especie no se incorporan al mapa: `H` es reutilizable entre perfiles.
- Diarios `(time,y,x)`: `rainfall`, `air_temp_c` y demás canales requeridos por subsistemas preservados.
- No emitir nuevos TWI, CR ni capacidad antigua. No emitir índices estáticos repetidos cientos de veces sobre eje temporal.
- Oferta potencial independiente de fecha meteorológica. Ingest no calcula además una segunda trayectoria hidrológica: ABM es dueño de evolución diaria.
- `n_viable_cells` pasa a describir candidatos por oferta potencial. Retirar error «JRC sin agua ⇒ cero hábitats» cuando existan candidatos pluviales válidos.
- No escribir `habitat_potential_persistent`/`habitat_potential_pluvial` como fuentes alternativas de capacidad ni bandas de `alpha`/`theta`. Eran propuestas descartadas de este documento, no se presupone que existan en código actual. Resúmenes por respuesta temporal son solo diagnósticos derivados, nunca sustitutos de `H[i,g]` antes de aplicar `w[s,g]`.

GPKG sigue siendo contenedor geoespacial, no compatibilidad con schema anterior. Generador y parser se reescriben para admitir únicamente celdas proxy:

- Una feature por celda candidata, centro geométrico de celda y `row/col` explícitos.
- `hab_type=cell_proxy`, schema/modelo, procedencia y seis valores `h_<identificador_g>` derivados de mismos `H`. No filtrar por una clase exclusiva permanente/temporal de celda: puede tener varios tipos.
- IDs deterministas por orden row-major del conjunto estático; sin regenerarlos según lluvia diaria.
- No presentar centro como posición real de pozo ni `is_permanent=true` para toda celda mixta.
- Dominio/candidatos definidos por algún `H[i,g]>0`, no por lluvia de día cero ni por preferencias de una especie codificadas en ingest. ABM comprueba `S_max[i,s]>0` para seeding de especie activa. Umbral computacional, si existe, documentado y con test de sensibilidad, no cupo urbano del AOI.
- Registrar mediante artefacto `habitat` del catálogo; mantener un único cálculo de features. GPKG deriva de mismos arrays que NC, no vuelve a leer y reclasificar fuentes.

Versionar outputs y conservar originales. Cambiar referencias del manifest operativo solo en corte controlado y después de copia/versionado; no sobrescribir salidas de baseline.

### 6.3 ABM

| Punto | Trabajo |
|---|---|
| `abm/src/env_reader.cpp` y `include/.../env_reader.hpp` | Leer `habitat_potential(habitat_type,y,x)` y versión; validar IDs/orden, shape, grid, unidades y dimensiones; error ante contrato incompatible |
| `abm/src/climate.cpp` y `include/.../climate.hpp` | Exponer cada `H[i,g]` y forzantes sin agregación prematura por persistencia ni fallback topográfico |
| `abm/src/habitat_engine.cpp` | Leer `cell_proxy`, sin `HABITAT_MIN_TWI`; validar índices/duplicados |
| `abm/src/coordinator.cpp` | Actualizar único `z` por fecha/celda, aplicar `k(g)` y `w[s,g]`, construir capacidad diaria; retirar reglas/cupos antiguos |
| `abm/src/engine.cpp` | Conectar capacidad en ambos constructores y recorridos sin hosts; evitar avance doble al consultar día cero |
| `abm/src/aquatic_cohort_bank.cpp` | Usar K nueva una sola vez; mantener regulación de densidad y biología ajena sin retoques |
| `abm/include/mal_abm_fast/species_params.hpp` y registro correspondiente | Perfil completo `w[s,g]` por identificador de hábitat, separado de preferencias de hospedadores y de reglas de oferta |
| `abm/wrapper.py`, CLI y contratos de flags | Configurar único modelo, validar artefactos y eliminar opciones anteriores; versión identifica contrato, no selecciona backend |

Detalles obligatorios:

1. Un estado pluvial `z` por celda y rollout, compartido por tipos pluviales; persistentes usan disponibilidad 1. No crear seis estados ni un estado por especie. No compartir estados mutables entre threads que comparten clima estático.
2. Actualización una vez por fecha. `to_dataframe`, seeding, snapshots o consultas repetidas no avanzan disponibilidad. Arranque con `z=0` y lluvia previa de warm-up; registrar si historial no existe y excluir transitorio al comparar.
3. Warm-up causal: solo fechas anteriores. No inicializar usando lluvia de días futuros ni media del periodo evaluado.
4. K debe cambiar cada día antes de actualizar cohortes. Si se reutiliza vista de memoria, asegurar lifetime y que actualizaciones no invaliden punteros; hoy vista se instala en construcción.
5. Mantener cohortes de candidatos secos en estado/lookup. Ausencia de patch no debe significar «no aplicar desecación».
6. Activación/desecación: interfaz canónica recibe disponibilidad relativa `S(t)/S_max`, con caso `S_max=0` explícito. Si hacen falta decisiones binarias, umbral es de ingeniería adimensional; no hereda significado de 1/5 mm. Actualizar APIs y callers, no construir adaptador de profundidad ni conservar API anterior. Probar sensibilidad y evitar que umbral domine escala continua de K.
7. Primera versión conserva una población acuática agregada por celda para especie soportada, no cohortes por tipo de hábitat ni por charca. Si algún tipo persistente con afinidad positiva sigue disponible, no declarar seca toda celda por desaparecer tipos pluviales. Esta mezcla es aproximación subgrilla declarada.
8. Desecación/washout: conservar inicialmente tasas y etapas existentes, trasladando mecanismos a módulo biológico independiente y borrando solver/headers anteriores. Una única definición. Washout basado en lluvia sigue siendo proxy biológico, no flujo D8; no duplicar pérdida con penalización nueva por tormentas.
9. No convertir `A` en milímetros falsos para reutilizar escalado antiguo. K llega en unidades compatibles con número de larvas de Beverton–Holt, con caso K=0 tratado explícitamente.
10. Oferta distinta puede cambiar destinos elegibles de oviposición a través de interfaces existentes. No modificar umbrales de detección, plume range, caminata dirigida ni reglas de conducta durante este trabajo.
11. No alterar seeding total entre A/B para ocultar diferencias; selección espacial usa nuevos candidatos y queda registrada.

Módulos nuevos recomendados tras promoción: `mal_core/habitat/` para schema/reglas explícitas de `H` en ingest y `abm/include/mal_abm_fast/habitat_availability.hpp` para evolución temporal y combinación con perfiles en C++. Python no mantiene un segundo simulador temporal de producción. Tests usan fixtures numéricas verificables; prototipo se elimina o queda como entrypoint al módulo promovido, nunca como copia independiente.

### 6.4 Observabilidad mínima

Guardar por ejecución configuración efectiva, versiones/hashes de inputs, reglas de `H`, catálogo `g`/`k(g)`, `beta_urban`, perfil completo `w`, `K_ref`, especie, área, inicialización y flags. Emitir diagnósticos compactos por día:

- Por tipo `g`: oferta estática `H`, disponibilidad correspondiente y contribución ponderada `w * H * A`. Mostrar aporte urbano por separado.
- Agregados persistente/pluvial solo después de conservar tipos y aplicar pesos; no reutilizarlos como única entrada de capacidad.
- Índice agregado y K acuática, con min/mediana/percentiles/suma en dominio.
- Candidatos, activos, días secos y fracción sin datos válidos.
- Series de lluvia y temperatura para celdas testigo urbanas, agrícolas, abiertas y de humedal/agua.
- Huevos, larvas, pupas y emergencia como respuestas del motor, no como prueba de validez de proxy.

No guardar un cubo gigante adicional por defecto. Series agregadas y celdas testigo bastan; mapas detallados bajo opción diagnóstica.

### 6.5 Unicidad de implementación y rechazo de contratos antiguos

- Entregar solo nuevos loaders/transformaciones canónicos, builder, parser y motor de disponibilidad.
- No introducir `--habitat-model old|new`, `use_legacy`, `skip_dem` de compatibilidad ni selección equivalente por variable de entorno.
- No escribir campos retirados con cero/uno para satisfacer estructuras antiguas; quitarlos y migrar cada caller.
- No implementar la formulación provisional descartada con `B`, `alpha`, `theta` o afinidad solo por clase temporal. Una única formulación de capacidad: `H` por hábitat → disponibilidad compartida → `w[s,g]` → `K`.
- No admitir `water_temp_c` como alias de `air_temp_c`, ni `k_capacity_mult` como alias de capacidad nueva. Contrato diario exige timestamps reales; un raster anual no lo satisface.
- Rechazar schema anterior antes de arrancar simulación, mostrando productos a regenerar. No incluir migrador que simule antiguo modelo.
- Eliminar documentación operativa, fixtures y prompts que todavía recomienden solver anterior. Referencias históricas y papers no se convierten en instrucciones de uso.
- Conservar artefactos históricos no implica soporte de lectura por runtime actual. Baseline para A/B es resultado guardado antes del corte.

## 7. Pruebas y validación

### 7.1 Agregación y catálogo

- Fixture nativa con 10% cultivo, 20% construido y 70% abierto: fracciones correctas aunque centro/dominante sugiera una única clase.
- JRC con píxeles 0/50/100: diferenciar promedio de occurrence y fracciones por umbral; nodata queda fuera del denominador válido.
- Fixture de reglas `H`: conservar IDs, valores y asignaciones `k(g)` de seis tipos; `H[surface_persistent]+H[wetland_persistent]=P` y ningún grupo depende de especie, lluvia o temperatura diaria.
- Mismos porcentajes marginales de agua/humedal pueden corresponder a distintas distribuciones subcelda. Metadata y tests no etiquetan producto `P*V` como intersección observada.
- Tiles solapados, bordes y cobertura parcial: sin doble conteo; validez explícita.
- Una celda de igual shape y transform distinto no se acepta por índice.
- Output estático NC se guarda/resuelve con su key; missing requerido y declared-but-missing fallan.
- Contrato viejo no se acepta como features nuevas; metadata incluye versión/periodo real.
- ERA5 diaria sintética con temperatura distinta cada día: diferencias sobreviven download → writer → ingest → reader C++.
- Reader requiere `air_temp_c`; contrato que solo contiene `water_temp_c` se rechaza. No hay alias de compatibilidad ni doble escritura de temperatura.
- Un raster anual repetido sobre eje `time`, sin observaciones/timestamps diarios reales, se rechaza como serie diaria. Fixture con valores diarios distintos debe conservarlos en download → ingest → reader.
- Tests enumeran consumidores térmicos migrados; desarrollo/supervivencia/EIP reciben la banda nueva cuando corresponda y su diferencia respecto al baseline anual queda reportada como cambio de forzante, no escondida como resultado hidrológico.
- Orden permutado, ID ausente/desconocido o catálogo de hábitats incompatible no cambia silenciosamente asociación de pesos: reader reordena explícitamente por ID o rechaza entrada según contrato, nunca se guía solo por posición.

### 7.2 Modelo temporal

- Límites [0,1], lluvia no negativa, tau/P0 positivos y control de NaN.
- Sin lluvia, disponibilidad pluvial decae monótonamente; lluvia aumenta disponibilidad hacia saturación.
- Lluvias consecutivas pequeñas aportan; no hay gate obligatorio de 15 mm.
- Independencia de DEM y de extensión total del AOI.
- Con `gamma_T=0`, temperatura no altera secado; al habilitar `gamma_T>0`, más calor reduce memoria dentro de dominio válido.
- Componente persistente del baseline no desaparece tras varios días secos.
- Dos consultas del mismo día, checkpoint/resume y ejecución continua producen mismo estado.
- Sin K/biología, evolución ambiental es determinista e independiente de seed.
- Cambiar perfil de especie no modifica `H`, `k(g)` ni trayectoria `z`. Tipos pluviales consultan misma disponibilidad sin actualizarla varias veces por día.

### 7.3 Integración biológica

- Celda sin JRC puede aportar capacidad pluvial. Además, con construido positivo, `beta_urban>0` y `w[s,urban_persistent]>0`, conserva capacidad humana persistente estimada durante periodo sin lluvia.
- La contribución urbana entra una sola vez y no rellena un campo de profundidad. Con `beta_urban=0` en ablación explícita desaparece ese término, no otra capacidad oculta.
- Día seco reduce K sin multiplicar por `pool_water_mm` antiguo.
- K=0 con larvas presentes no produce NaN ni deja cohortes eternamente ignoradas.
- Oferta mixta no pasa toda a seca al perder solo componente pluvial.
- Dos perfiles con igual peso total persistente/pluvial y distinta preferencia urbana/humedal producen distintas capacidades cuando sus `H` difieren: verificar ejemplo 0,066/0,058 de sección 5.4.
- Pesos no se renormalizan por celda, ausencia de hábitats ni sequía; una celda sin hábitat adecuado no obtiene capacidad por redistribución de preferencias.
- `S_max=0`, `K_ref=0`, pesos inválidos y oferta inválida tienen manejo explícito. La suma ponderada permanece en [0,1] sin un `clip` que oculte errores.
- Versión nueva funciona sin host landscape para tests del banco acuático; hosts siguen necesarios donde transmisión los requiere.
- Preservar mortalidad adulta, respuestas térmicas y parámetros de búsqueda entre comparaciones.
- Comparar suma de capacidad de región a 1/2/5 km con predictores agregados conservativamente. Reportar efectos de clipping/no linealidad; no exigir identidad exacta del ABM, cuyo movimiento también depende de grilla.

### 7.4 Experimento mínimo y criterio predictivo

1. Prototipo en tier experimental, preferiblemente `mal-ghana-sim/`, antes de promoción a core. Outputs aislados bajo directorio nuevo, por ejemplo `runs/habitat_proxy_v1/`. Tras promoción no queda duplicado del motor en ese experimento.
2. Elegir AOI operativo de Ghana con datos resueltos y leíbles; no usar AOI LiDAR suizo como validación ecológica de Ghana. Identificar contrastes urbano, agrícola, abierto y agua/humedal donde existan.
3. Primera pasada solo disponibilidad: lluvia → respuesta → sequía. Ver curvas y magnitudes antes de ejecutar transmisión.
4. Ensayo ABM controlado: resultados de baseline capturados antes del corte vs nuevo, mismas seeds, población hospedadora, periodo, total de seeding y conducta adulta. No incorporar dos motores a revisión nueva para ejecutar comparación. Guardar versiones de inputs para distinguir cambio de datos de cambio de algoritmo.
5. Ablaciones mínimas dentro del único modelo nuevo: oferta estática, oferta + lluvia/memoria y con/sin prior urbano persistente. Temperatura en secado solo si añade valor. No hacer grid search de decenas de coeficientes; ablación de un término no es conservar backend antiguo.
6. Scoring canónico en `mal_core/scoring/`; adaptar dimensiones pertinentes, declarar cambio de semántica y no comparar números históricos como si fueran la misma métrica. Missing observaciones ⇒ skipped/no validado, no cero ni éxito.
7. Con datos independientes disponibles, evaluación espacial/temporal reservada: ajuste en entrenamiento, elección en validación, resultado final en test. Partir datos antes de calibrar.
8. Métrica primaria de malaria según objetivo disponible: por ejemplo deviance para conteos con denominador/exposición; MAE/RMSE como auxiliares. No usar correlación sola ni score interno como sustituto de evaluación predictiva.
9. Registrar periodo de disponibilidad de mapas estáticos: usar productos posteriores al periodo test introduce información futura. Si se usan para reconstrucción retrospectiva, declararlo y no llamarlo pronóstico prospectivo.
10. Sin observaciones entomológicas/epidemiológicas adecuadas se puede aceptar integración funcional, pero estado científico queda «proxy no validado». No prometer que beta predice mejor solo por simplificar.

Antes del ensayo registrar métrica principal y tolerancia de no-inferioridad, basada en ruido y uso del producto; no elegir tolerancia después de ver resultados. Sin incertidumbre, observaciones o baseline suficientes, no declarar superioridad/no-inferioridad estadística.

## 8. Entregas y orden de ejecución

| Entrega | Resultado verificable | Dependencia |
|---|---|---|
| E0 | Baseline histórico, inventario de eliminación y contrato cerrado | Capturar antes de borrar |
| E1 | Prototipo de fracciones, seis reglas `H`, perfil `w[s,g]` y dos respuestas temporales, fixtures numéricas | Inputs disponibles por catálogo |
| E2 | Productos nuevos JRC/WorldCover y T diaria, con manifests y procedencia | Verificación E1 y promoción de partes estables |
| E3 | NC/GPKG con `H` por tipo, IDs/schema compartidos y reader C++ sin DEM | E2 |
| E4 | Disponibilidad diaria → K acuática → activación/desecación, ambos constructores | E3 |
| E5 | Diagnósticos, comparación con baseline guardado, scoring y estado de validación explícito | E4 |
| E6 | Auditoría de ausencia de residuos y entrega única de nuevo sistema | Criterios técnicos y eliminación completa del plan 1 |

Promoción sigue flujo del monorepo: verificar experimento con datos reales → extraer lógica estable con tests a core/commonlib → eliminar implementación experimental duplicada → actualizar entrypoints de ejecución. No mover infraestructura/datasets ni tocar investigaciones concurrentes como parte de promoción.

Entregas son hitos internos de una rama de ruptura. No publicar fases incompletas que mantengan sistema anterior como fallback. Planes 1 y 2 se fusionan como corte integrado; recuperación usa revisión completa anterior, no coexistencia de motores.

No son entregas adicionales obligatorias: predictor LiDAR, solver de escorrentía, mapas globales de suelo, riego, pozos o motor multiespecie completo.

## 9. Criterios de aceptación

- [ ] Nuevos datos de cultivo/humedal/abierto/construido vienen de WorldCover existente, preservando fracciones antes de agregación.
- [ ] JRC distingue occurrence histórica, fracción espacial y persistencia operativa; no finge observar microcharcas.
- [ ] Lluvia y temperatura conservan cadencia documentada y no introducen información futura.
- [ ] Catálogo/manifest es única resolución; contratos/versiones impiden reusar silenciosamente productos antiguos.
- [ ] Oferta `H` por tipo, dos respuestas temporales y único estado pluvial funcionan sin DEM, D8 ni LiDAR.
- [ ] Sin matrices libres `alpha`/`theta`, agregado previo que pierda contexto ni perfil de especie solo por persistencia/pluvial.
- [ ] Reglas, IDs, `k(g)` y pesos son explícitos; fórmulas de contexto no se presentan como coincidencia espacial medida.
- [ ] Prior urbano persistente positivo conserva premisa de filtraciones; contribución distinguible, configurable y evaluada por sensibilidad.
- [ ] Config distingue observaciones, priors y parámetros ajustados; sin volúmenes/profundidades inventados.
- [ ] Capacidad tiene escala acuática y área real; una única aplicación de disponibilidad.
- [ ] Candidatos, seeding, activación, cohortes secas y ambas rutas Engine usan mismo modelo.
- [ ] Preferencia por hábitat distingue urbano/humedal/abierto/cultivo; ausencia de contexto no renormaliza pesos hacia los restantes.
- [ ] Sin cambios compensatorios de conducta/mortalidad adulta ni nuevos parámetros libres por celda.
- [ ] Tests Python/C++ y pipeline real pasan con limitaciones/fallos previos identificados.
- [ ] Comparación reproducible, métricas de validación y estado de evidencia quedan escritos.
- [ ] Artefactos originales, datos y experimentos permanecen recuperables y sin sobrescritura silenciosa.
- [ ] Sistema anterior, librerías exclusivas, constantes, aliases, parsers y flags sustituidos no existen en checkout entregado.
- [ ] No queda segundo simulador en experimentos, `_legacy/` o módulos desconectados; solo una implementación canónica.
- [ ] Productores, consumidores, tests, configuración y documentación activa usan contrato nuevo, incluido `air_temp_c`.

## 10. Fuentes y límites de inferencia

- **Hinne et al. (2021)**, *Larval habitat diversity and Anopheles mosquito species distribution in different ecological zones in Ghana*. DOI: [10.1186/s13071-021-04701-w](https://doi.org/10.1186/s13071-021-04701-w). Registraron 267/383 hábitats artificiales (69,71%); 58,75% de hábitats en terrenos agrícolas. Apoya usar contexto humano/agrícola. No da coeficiente universal urbano → pozos ni convierte proporción de muestra en densidad por km².
- **Nambunga et al. (2020)**, *Aquatic habitats of the malaria vector Anopheles funestus in rural south-eastern Tanzania*. DOI: [10.1186/s12936-020-03295-5](https://doi.org/10.1186/s12936-020-03295-5). De 36 hábitats con funestus, 26 (72,2%) tenían vegetación emergente y 24 (66,7%) profundidad >50 cm. Justifica preservar contexto y persistencia; no permite medir profundidad en Ghana desde WorldCover.
- **JRC GSW / Pekel et al. (2016)**: [documentación de occurrence, seasonality y recurrence](https://global-surface-water.appspot.com/faq); DOI [10.1038/nature20584](https://doi.org/10.1038/nature20584). Occurrence es frecuencia temporal de agua detectada; seasonality y recurrence son variables diferentes. Consultar edición y ventana reales del producto seleccionado.
- **ESA WorldCover 2021 v200**: clases y atribución ya presentes en `mal-commonlib/src/mal_commonlib/data/loaders/worldcover.py`; fuente de referencia [ESA WorldCover](https://esa-worldcover.org/en/data-access). Clasificación de cobertura, no inventario de infraestructura hídrica.

Las ecuaciones, coeficientes y agrupaciones de este plan son diseño del MVP. No atribuirlos a esos artículos ni etiquetarlos «calibrados para Ghana» antes de validación.
