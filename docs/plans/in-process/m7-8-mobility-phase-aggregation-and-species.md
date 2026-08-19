# M7.8 — Movilidad por fases, movimiento de mosquito y especie

| Campo | Valor |
|---|---|
| **Estado** | Propuesto, pendiente de revisión humana |
| **Objetivo** | Convertir movilidad humana/ganadera en presencia diaria coherente, agregar fases intra-día sin abandonar paso diario, y preparar especie de mosquito para preferencias de hospedador y tolerancia de salinidad |
| **Dependencias** | M7.2 gonotrophic cycle; `MobilitySchedule`; `HostLandscape`; Plan D de kernels; M7.3 multi-species |
| **Primer entregable** | Simulador/diagnóstico de presencia humana y ganadera por fase y por día, sin cambiar aún dinámica de mosquitos |
| **Especie inicial propuesta** | *Anopheles coluzzii* |

> Este documento es plan de diseño. No autoriza implementación todavía.

---

## 1. Contexto y diagnóstico actual

### 1.1 Lo que existe

- `host_static.nc` contiene población humana, cinco clases de ganado, `wildlife_host_proxy`, urbanidad, edificios e interioridad.
- `build_mobility_dataset()` construye tres CSR row-stochastic:
  - humana diurna;
  - humana nocturna;
  - ganadera.
- `MobilitySchedule::select_od()` selecciona matriz por `TimePhase` y por `is_livestock`.
- `effective_hosts_at()` ya expresa la operación correcta de redistribución:

```text
H_eff(j, phase) = Σ_i P(i→j, phase) × H_residential(i)
```

- `Engine` carga matrices y las inyecta en `MosquitoSubmodel`.
- `MultirateDayState` define 12 horas nocturnas, pero no gobierna todavía `advance_day()`.
- `HostSeekingModel` lee `HostLandscape` estático. No consulta `MobilitySchedule`.
- El ABM ejecuta `engine.step()` una vez por día. La alimentación se resuelve dentro de ese paso, sin loop horario efectivo.

### 1.2 Defectos y drift documental

- Documentación declara “movilidad implementada” y “12 sub-pasos nocturnos”, pero el camino de ejecución actual solo carga las matrices.
- El `HostLandscape` no tiene buffers residenciales y efectivos separados.
- `select_od()` está encapsulado en `MobilitySchedule`; no debe exponerse como matriz mutable ni duplicarse en host-seeking.
- `load_from_directory()` espera `livestock_mobility_season.csr`, mientras ingest genera `ghana_livestock_mobility.csr`. Debe resolverse antes de declarar movilidad activa.
- `host_seeking.cpp` contiene lógica de preferencia y distancia, pero sus pesos actuales (`human=.99`, cattle=.005, etc.) no deben considerarse parámetros validados de HBI.
- Existe un segundo bloque G14 de host-seeking en `mosquito_submodel.cpp`; antes de integrar movilidad hay que eliminar doble contabilización o definir explícitamente cuál bloque es canónico.

### 1.3 Planes relacionados

- `m7-3-multi-species.md`: stub para gambiae, coluzzii, arabiensis y funestus; propone HBI, térmica, hábitat, exo/endo y EIP por especie.
- `m7-4-seir-sei.md`: depende de especie y capa de host; fuera de este plan.
- Plan D: propone ampliar kernel de host-seeking, movimiento dirigido, kernel de oviposición y corregir `patch_id`; sigue propuesto, no asumir integrado.
- Plan B/C: históricos o superseded por Plan D; no reutilizar site fidelity de Plan C porque plan D documenta evidencia posterior en contra.
- Plan A: windborne; no mezclar su ajuste con primera validación de movilidad.

---

## 2. Decisión biológica inicial

### 2.1 Especie recomendada: *Anopheles coluzzii*

Para una primera simulación Ghana-wide de una sola especie, usar *Anopheles coluzzii* como hipótesis operativa. Evidencia disponible:

- En estudios de Ghana, *An. gambiae* s.l. domina los anophelinos; dentro del complejo, *An. coluzzii* aparece frecuentemente como miembro más abundante, aunque cambia por zona ecológica.
- Un estudio multi-zona de Ghana reportó, entre individuos tipados del complejo, aproximadamente 55.9% *An. coluzzii*, 39.5% *An. gambiae* s.s., 2.3% *An. arabiensis* y 2.2% *An. melas*.
- Otros estudios del sur de Ghana encuentran coexistencia de *An. coluzzii*, *An. gambiae* s.s. y *An. funestus*; por tanto, esta elección es una priorización de MVP, no una afirmación de exclusividad nacional.
- *An. coluzzii* es vector humano relevante, altamente antropofílico, y aparece en costa, sabana y entornos urbanizados.
- *An. coluzzii* tolera más salinidad que *An. gambiae* s.s. en estudios comparativos, pero sigue siendo principalmente una especie de agua dulce con tolerancia a condiciones salobres/contaminadas. No debe modelarse como equivalente a *An. melas*.

### 2.2 Qué no afirmar

- No usar “la especie más importante de Ghana” sin estratificar por región, estación y método de captura.
- No convertir tolerancia salina en booleano `salt=true/false`.
- No extrapolar HBI de una población local a todo Ghana sin etiquetar fuente y zona.

### 2.3 Especies futuras

| Especie | Papel futuro | Hábitat salino | Prioridad |
|---|---|---|---|
| *An. coluzzii* | MVP Ghana-wide | Dulce + tolerancia salobre limitada/variable | Ahora |
| *An. gambiae* s.s. | Comparación inland/forest y agua temporal | Principalmente dulce | Alta |
| *An. funestus* s.s. | Vector mayor, agua permanente con vegetación | Principalmente dulce | Alta, después |
| *An. arabiensis* | Sabana seca, mayor zoofilia/exofilia | Dulce | Media |
| *An. melas* | Costa/manglar, vector salino | Salobre/salina | Media, requiere datos costeros |
| *An. stephensi* | Invasora urbana emergente | Por investigar localmente | M8+, no introducir ahora |

---

## 3. Arquitectura propuesta

### 3.1 Separar cuatro conceptos

1. **Población residencial**: dónde viven humanos/ganado. No cambia por movilidad diaria.
2. **Realización de movimiento**: individuos humanos/ganado que, con probabilidades OD, están temporalmente en destinos.
3. **Presencia efectiva por fase**: resultado agregado de esa realización para una fase concreta.
4. **Exposición/movimiento del mosquito**: mosquito que responde a la presencia de hosts de esa fase.

`H_residential` es ancla fija. La movilidad no cambia residencia, no crea migración permanente y no mueve agentes humanos dentro de la SoA de mosquitos. Conceptualmente, cada individuo de origen `i` sortea un destino `j` según `P(i→j)`. Operativamente, se muestrean flujos agregados para no crear una entidad por persona o animal.

Por tanto, `H_eff` no es constante: cambia entre fases y entre días por las realizaciones aleatorias, aunque su esperanza matemática sea la redistribución OD determinista.

Si se usa directamente la esperanza, una matriz estática produciría el mismo `H_eff` en todos los días. Eso sería válido como campo medio poblacional, pero no como realización de movimiento. Este plan usa la esperanza para auditoría y el muestreo diario para el runtime. La semilla controla la realización; una sub-secuencia RNG nombrada evita que los diagnósticos cambien el resultado biológico.

### 3.2 Matriz seleccionada por fase

`select_od(phase, is_livestock)` debe seguir siendo única fuente de selección:

```text
humano:
  DAY, EVENING, DAWN -> human_day
  NIGHT              -> human_night

ganado:
  DAY, EVENING, DAWN -> livestock_day
  NIGHT              -> identity
```

La identidad nocturna del ganado es una hipótesis inicial, no una verdad universal. Validar contra datos de estabulación/movimiento antes de fijarla.

### 3.3 Cuatro fases completas y agregación diaria

Las cuatro fases se implementan en este plan desde el inicio. No habrá una implementación nocturna seguida de otra diurna posterior.

Para cada día `d` y fase `p`:

1. Partir de `H_residential` como origen residencial estable.
2. Muestrear flujo OD humano y ganadero con `P(i→j,p)`.
3. Construir `H_eff(d,p)` a partir de los destinos muestreados.
4. Ejecutar virtualmente el movimiento/host-seeking del mosquito durante esa fase.

El ABM mantiene un solo `engine.step()` externo diario, pero internamente procesa cuatro estados de fase. El output diario representa el estado tras DAWN y conserva diagnósticos de cada fase.

La agregación final sirve para métricas, no para reemplazar la evolución fase a fase:

```text
H_expected_daily(j) = Σ_p w_species,p × E[H_eff(d,p)]
Σ_p w_species,p = 1
```

Los pesos representan actividad/exposición de la especie y se aplican a métricas diarias. No eliminan fases de la simulación. Todos los pesos existen desde el inicio, incluidos DAY, EVENING, NIGHT y DAWN.

El runtime usa `H_eff(d,p)` muestreado, no `H_expected_daily`, para que el mosquito vea realizaciones distintas. `H_expected_daily` se conserva como referencia estadística y mapa de diagnóstico.

```text
H_eff(d,p) = aggregate_multinomial_flows(
    H_residential,
    P_phase[p],
    rng(seed, d, p, host_type)
)
```

No habrá dos modos funcionales ambiguos. Habrá un único modo productivo: fases secuenciales con flujos probabilísticos. La esperanza determinista se usará únicamente para validación, comparación y visualización.

#### Muestreo y conservación

Para cada celda origen `i`, el flujo se muestrea como multinomial sobre sus destinos CSR:

```text
(F_i→j) ~ Multinomial(N_i, P(i→j))
H_eff(j) = Σ_i F_i→j
```

Esto conserva exactamente `N_i` por origen y la masa total, a diferencia de aplicar Bernoulli independiente por destino. Para valores raster fraccionarios, se define una regla explícita de integerización/stochastic rounding al construir el stock simulable; los valores no integerizados siguen disponibles para el cálculo esperado.

Si el coste de muestrear cada individuo resulta excesivo para Ghana, usar muestreo por bloques de peso configurable, manteniendo la misma distribución esperada y documentando el tamaño efectivo de muestra. No sustituirlo por un `H_eff` fijo sin medir el impacto de la varianza.

### 3.4 Aplicación al movimiento del mosquito por fases

El paso diario conserva contrato externo y coste razonable del ABM:

1. Construir `H_eff(d, DAY)` y actualizar actividad/posición virtual del mosquito.
2. Repetir para EVENING, NIGHT y DAWN.
3. En cada fase, host-seeking calcula atracción con el paisaje efectivo de esa fase.
4. Aplicar movimiento dirigido, local y windborne según reglas y actividad de especie.
5. Actualizar posición y `patch_id` inmediatamente tras cada cambio relevante.
6. Aplicar alimentación y transición gonotrófica según actividad de la fase.
7. Emitir un único estado diario después de la cuarta fase.

Importante: no se agrega primero el paisaje y luego se ejecuta un único movimiento. Se simulan cuatro paisajes fase-específicos y cuatro oportunidades de movimiento dentro del paso diario. La agregación ponderada se conserva para resumen, no como sustituto de esas fases.

### 3.5 Diagnóstico obligatorio y runtime único

- **Diagnóstico obligatorio**: generar `H_eff(d,p)`, medias, varianzas, conservación de masa y distancias OD.
- **Runtime integrado**: usar esas mismas realizaciones `H_eff(d,p)` dentro de host-seeking y movimiento del mosquito.

No son dos modos funcionales alternativos. El diagnóstico forma parte de la misma implementación y permanece como output de auditoría. El runtime final siempre procesa las cuatro fases e integra movilidad.

---

## 4. Movimiento de humanos y ganado: entregable obligatorio

### 4.1 Objetivo

Medir si el gravity model genera realizaciones fase-específicas físicamente plausibles antes de usar esas realizaciones para mover mosquitos. Este diagnóstico forma parte de la implementación completa, no es un modo alternativo permanente.

### 4.2 Salidas requeridas

Para cada AOI, día de referencia y matriz:

- mapa residencial `H_residential`;
- mapa efectivo `H_eff(d,p)` para las cuatro fases;
- mapas de media y varianza de `H_eff(d,p)` sobre varias semillas/días;
- mapa diferencial `H_eff - H_residential`;
- mapa de razón `H_eff / max(H_residential, epsilon)`;
- masa total residencial vs efectiva;
- centroide ponderado antes/después;
- percentiles de distancia origen-destino;
- fracción de masa que abandona su celda, radio 1 km, 5 km, 10 km, 50 km;
- top destinos receptores y top orígenes emisores;
- overlay de asentamientos/urbanidad y ganado.

### 4.3 Criterios de plausibilidad iniciales

No fijar aún umbrales biológicos universales. Reportar:

- conservación de masa por fila y global;
- ausencia de destinos fuera de AOI;
- simetría/anisotropía explicable por atractividad, no por error de índice;
- desplazamiento humano agregado razonable respecto a clusters residenciales;
- ganado no concentrado artificialmente en una sola celda;
- contraste entre las cuatro fases sin borrar estructura residencial;
- sensibilidad a `beta_day`, `beta_night`, `beta_livestock` y `max_distance_km`.

El usuario revisará estos mapas como gate de aceptación del operador completo. Si humanos aparecen “dispersos” de forma no plausible, no ajustar mosquito para compensarlo: corregir el operador OD antes de continuar.

### 4.4 Hipótesis explícita sobre humanos

La movilidad OD actual es una realización probabilística de presencia temporal a partir de población residencial, no una simulación de commuters identificables, viajes puntuales ni migración permanente. Por tanto, no debe interpretarse como que cada habitante cambia de domicilio diariamente. Para MVP:

- conservar población residencial como ancla;
- usar movilidad como presencia efectiva fase-específica de exposición;
- no cambiar `H_residential` ni `patch_id` humano;
- reservar commuting calibrado, viajes y migración para trabajo posterior.

---

## 5. Esquema de especie

### 5.1 Identidad

Añadir especie como enum estable y campo SoA, separado de parámetros:

```text
MosquitoSpeciesId
  ANOPHELES_COLUZZII = 0
  ANOPHELES_GAMBIAE_SS = 1
  ANOPHELES_FUNESTUS_SS = 2
  ANOPHELES_ARABIENSIS = 3
  ANOPHELES_MELAS = 4
  ANOPHELES_STEPHENSI = 5
```

MVP solo instancia `ANOPHELES_COLUZZII`. No sembrar otras especies hasta contar con parámetros y datos.

### 5.2 Registro de parámetros

Separar `SpeciesParams` de `MosquitoSoA`:

- nombre canónico y taxonomía;
- HBI por host y fuente;
- preferencia relativa por host (`pref_k`), normalizada y versionada;
- actividad por fase del día;
- indoor/outdoor y endophagy/exophagy;
- escala/radio de host-seeking;
- duración de ciclo gonotrófico;
- fecundidad y supervivencia por etapa;
- curva térmica/EIP;
- curva de tolerancia a salinidad;
- hábitat de cría preferido: temporal/permanente, vegetación, salinidad;
- incertidumbre/rango y referencia bibliográfica.

### 5.3 `pref_k` no igual a HBI sin transformación

HBI observado es fracción de comidas con sangre humana. `pref_k` es peso de atracción en el modelo. El registro debe conservar ambos:

```text
observed_blood_meal_fraction[k]
model_attraction_weight[k]
calibration_transform
source_population / region / season
```

Primera hipótesis para *An. coluzzii*: antropofilia alta; usar rangos y análisis de sensibilidad, no `human=.99` como verdad global. Los datos ghaneses muestran alimentación principalmente humana, pero también alimentación animal ocasional en *An. gambiae* s.l.; *An. funestus* fue exclusivamente antropofágico en un estudio del sur de Ghana.

### 5.4 Tolerancia salina

Implementar interfaz de respuesta, no bandera:

```text
salinity_suitability(species, salinity_ppt) -> [0,1]
```

Para *An. coluzzii*:

- pico inicial en agua dulce;
- caída progresiva con salinidad;
- tolerancia mayor que *An. gambiae* s.s.;
- parámetros regionales configurables porque tolerancia varía por población y urbanización;
- no permitir supervivencia equivalente a *An. melas* en agua marina/brackish alta.

La respuesta debe multiplicar aptitud de hábitat y/o supervivencia larvaria, no reescribir `water_frac`. `water_frac` dice cantidad/presencia de agua; salinidad dice compatibilidad de especie.

### 5.5 Fuente de salinidad: NASA SMAP RSS SSS V6

Para señalar zonas salinas se añade **SMAP RSS Sea Surface Salinity V6.0**, vía PO.DAAC (NASA Earthdata). Este plan incorpora el dataset completo con `malariasim download` y su integración en `malariasim ingest`.

Referencia del producto:

| Campo | Valor |
|---|---|
| Producto | RSS SMAP L3 Sea Surface Salinity (SSS) Standard Mapped Image **Monthly V6.0** (validado) |
| Distribuidor | PO.DAAC / NASA Earthdata (`SMAP_RSS_L3_SSS_SMI_MONTHLY_V6`) |
| DOI | `10.5067/SMP60-3SMCS` |
| Formato | netCDF-4, CF/ACDD |
| Grid | 0.25° × 0.25° (WGS 84, lon 0–360) |
| Resolución espacial | 40 km original (`sss_smap_40km`); estándar suavizado ~70 km (`sss_smap`) |
| Temporalidad | Mensual, desde 2015-04, latencia ~7 días |
| Variables útiles | `sss_smap` (70 km, estándar), `sss_smap_40km`, `sss_smap_RF` (rain-filtered), `fland`/`gland` (fracción de tierra), incertidumbres |
| Unidades | PSS/PSU (practical salinity units), escala 1e-3, fill `-9999`, rango 0–45 |
| Autenticación | Earthdata Login (`EARTHDATA_TOKEN`) |
| Acceso | OPENDAP / Harmony subsetter / `podaac-data-subscriber` / S3 us-west-2 |
| Huecos conocidos | Sin datos 2019-06-19→07-23 y 2022-08-09→10-06 (SMAP fuera de modo ciencia) |

**Caveat crítico**: es **salinidad de superficie marina**. Solo cubre océano y celdas costeras/estuarios. Para Ghana, las zonas señaladas son el Golfo de Guinea y aguas costeras (estuario del Volta, lagunas costeras). No entrega valores para hábitats de cría interiores de agua dulce, que quedan como no-salinos (masa continental). Este comportamiento es el esperado: salinidad alta solo donde SMAP la mide.

### 5.6 Integración con `malariasim download` e `ingest`

**Download — nuevo loader `smap`** (patrón de un fichero por dataset):

- Crear `mal-commonlib/src/mal_commonlib/data/loaders/smap.py`.
- Exportar `DOWNLOADER` con:
  - `name = "smap"`;
  - `requires_auth = ["earthdata"]`;
  - `is_time_series = True`;
  - `outputs = {"salinity": load_smap_salinity}`;
  - `manifest_keys = {"salinity": "smap_salinity"}`;
  - `formats = {"salinity": "monthly"}`.
- `load_smap_salinity(aoi, *, years, months, cache_dir) -> xr.Dataset`:
  - descargar granulos mensuales V6 por OPENDAP/Harmony para el periodo pedido;
  - seleccionar `sss_smap_40km` (resolución más fina; 70 km solo para mar abierto) y `fland`/`gland`;
  - recortar al bbox del AOI y convertir lon 0–360 → −180–180;
  - aplicar escala `1e-3` y enmascarar `-9999`.
- Añadir `"smap"` a `LOADER_MODULES` en `mal_core.download.registry`.
- Documentar en `docs/specs/download/spec.md` §5.4 la nueva fila `smap`.

**Runner — soporte para salinidad mensual en NC**: el runner actual tiene dos rutas de escritura: mensual→TIF por año (pierde resolución mensual, inaceptable para salinidad) y diaria→NC multi-año. Se añade un tercer formato `"monthly_nc"` que escribe un NC multi-año con pasos mensuales: `data/<aoi>/<aoi>_salinity_<start>_<end>_monthly.nc` y registra en manifest con `period`. Si se prefiere minimizar cambios de runner, la alternativa es usar la ruta diaria existente con frecuencia mensual; se rechaza porque el nombre `_daily.nc` y el `var_name` sin sufijo causarían drift documental.

**Ingest — variable `salinity_ppt` en el env NC**:

- En `build_daily_env_nc`, leer `{aoi}_salinity_<start>_<end>_monthly.nc`.
- Reproyectar al grid del AOI (bilinear) y remuestrear a la resolución ABM.
- Enmascarar masa continental: usar `fland`/`gland` y el AOI; celdas sin dato SMAP → 0.0 (agua dulce), nunca NaN.
- Asignar a cada día del mes el valor mensual de ese mes (broadcast, mismo patrón que `water_temp`/`ndvi` anuales). Salinidad no cambia intra-mes.
- Añadir variable `salinity_ppt` (units `psu`) al Dataset del env NC y a la lista `variables` del manifest.
- El lector C++ (`climate.hpp`) ignora variables extra vía GDAL, así que `salinity_ppt` puede ser diagnóstico al principio; el consumo real por `salinity_suitability` se activa en la fase de cría species-aware.

**Checklist de revisión de datos antes de activar salinidad espacial**:

- [ ] Comprobar cobertura del AOI Ghana: cuántas celdas costeras/marinas quedan dentro del bbox y con `nobs > 0`.
- [ ] Confirmar rangos PSU plausibles (costa ghanesa ~33–36 psu; estuarios diluidos más bajos).
- [ ] Verificar huecos 2019/2022 dentro del periodo del run y su impacto (meses sin dato → dulce, documentado).
- [ ] Verificar que la resolución 0.25° no introduce artefactos en la costa tras remuestreo.
- [ ] Confirmar que `fland`/`gland` enmascaran correctamente las celdas continentales (que no se etiquete Ghana interior como salino).
- [ ] Decidir entre `sss_smap_40km` (más fino, más ruido) y `sss_smap` (70 km, estándar) para el MVP; recomendación inicial: `sss_smap_40km` en zonas costeras, validar ruido.
- [ ] Generar mapas mensuales de salinidad del AOI y overlay con `water_frac` para confirmar zonas salinas donde existen hábitats acuáticos.

---

## 6. Fases de implementación

### Fase 0 — Reconciliación y baseline

- Confirmar nombre correcto de CSR ganadera.
- Corregir carga de `livestock_mobility` sin aliases silenciosos.
- Eliminar doble host-seeking o marcar un único bloque canónico.
- Actualizar documentación que afirma movilidad activa.
- Capturar baseline: run 30/180 días, métricas D1/D13/D14 y mapas.

### Fase 1 — Operador completo de movilidad y diagnósticos

- Extraer operador común `effective_hosts_grid(day, phase, host_type)` basado en `select_od`.
- Implementar muestreo multinomial por fase, día, semilla y tipo de host.
- Implementar las cuatro fases y la agregación estadística diaria.
- Generar mapas/CSVs/JSON de conservación y distancias.
- Añadir tests de identidad, conservación, reproducibilidad y sensibilidad beta.

### Fase 2 — Gate de plausibilidad dentro del mismo entregable

- Revisar mapas humanos y ganado.
- Fijar pesos de las cuatro fases y regla nocturna ganadera en configuración versionada.
- Rechazar implementación si humanos se dispersan de forma no plausible.
- Registrar parámetros finales en este plan; no dejar configuración provisional activa.

### Fase 3 — Integrar presencia fase-específica en host-seeking

- Añadir `EffectiveHostLandscape` o vista equivalente, sin mutar datos residenciales.
- Consumir `H_eff(d,p)` en `HostSeekingModel` durante cada fase.
- Añadir métricas comparativas baseline vs mobility:
  - host-seeking distance;
  - host type selected;
  - bites by cell and host;
  - spatial clustering;
  - human/livestock mass conservation.
- Implementar movimiento dirigido del mosquito en este plan, con la misma secuencia de fases; no depender de un Plan D externo.

### Fase 4 — Movimiento mosquito por fases y cierre diario

- Integrar `SpeciesParams.activity_weights` en la agregación estadística, manteniendo ejecución de las cuatro fases.
- Aplicar host-seeking y movimiento dirigido durante cada fase según actividad de especie.
- Resolver estado duplicado y `patch_id` antes de aceptar la integración.
- Validar que un día no aplica dos veces movimiento dirigido por el mismo evento.
- Comparar kernel local, windborne y host-directed como canales separados.
- Emitir un único estado diario y sidecar con resumen por fase.

### Fase 5 — Especie MVP + dataset SMAP

- Añadir enum, SoA field, registry y sidecar de especie.
- Migrar constantes de *An. gambiae* hard-coded a `SpeciesParams`.
- Configurar *An. coluzzii* como única población activa.
- Añadir curva salinidad sintética y tests de monotonicidad/óptimo.
- Implementar loader `smap` + registro en `LOADER_MODULES` + `malariasim download --datasets smap --outputs salinity --years 2024,2025`.
- Añadir formato `monthly_nc` al runner (o rechazarlo en revisión) para persistir salinidad mensual multi-año.
- Añadir variable `salinity_ppt` al env NC vía `build_daily_env_nc` (broadcast mensual por día).
- Ejecutar checklist de revisión de datos (§5.6) antes de activar salinidad espacial.

### Fase 6 — Cría species-aware

- Multiplicar aptitud de patch por respuesta salina de especie usando `salinity_ppt`.
- Separar agua dulce, salobre y marina solo cuando datos permitan clasificación.
- Mantener `water_frac` y `salinity_suitability` como factores distintos.
- Añadir tests de patch: agua dulce viable para MVP; salinidad alta reduce supervivencia; *An. melas* futuro podría invertir ese perfil.
- Añadir test de integración: celda interior sin dato SMAP → dulce (0.0) y aptitud plena para *An. coluzzii*; celda costera ~35 psu → aptitud reducida.

### Fase 7 — Especies adicionales y transmisión

- *An. gambiae* s.s., *An. funestus*, *An. arabiensis*, *An. melas* por lotes separados.
- Actualizar M7.3 completo y luego M7.4 SEIR-SEI.
- No iniciar infección humana antes de que especie, host presence y bite ledger sean estables.

---

## 7. Contratos y archivos candidatos

### Nuevos candidatos

- `mal-core/src/mal_core/abm/include/mal_abm_fast/species.hpp`
- `mal-core/src/mal_core/abm/include/mal_abm_fast/species_params.hpp`
- `mal-core/src/mal_core/abm/include/mal_abm_fast/effective_host_landscape.hpp`
- `mal-core/src/mal_core/abm/src/effective_host_landscape.cpp`
- `mal-core/src/mal_core/abm/tests/test_species.cpp`
- `mal-core/src/mal_core/abm/tests/test_effective_hosts.cpp`
- `mal-core/src/mal_core/abm/scripts/visualize_mobility.py`
- `mal-commonlib/src/mal_commonlib/data/loaders/smap.py` (loader SMAP RSS SSS V6, output `salinity`)

### Archivos existentes a tocar, solo tras aprobación

- `mal_core.download.registry.LOADER_MODULES` — añadir `"smap"`.
- `mal_core.download.runner` — formato `"monthly_nc"` (salida NC multi-año mensual) si se aprueba.
- `mal_core.ingest.daily_nc` — leer NC mensual SMAP, reproyectar/remuestrear, broadcast mensual a `salinity_ppt`.

### Archivos existentes a tocar, solo tras aprobación

- `mobility_schedule.hpp` — API de agregación, no duplicar `select_od`.
- `host_landscape.hpp/.cpp` — separar residencial de vista efectiva.
- `host_seeking.hpp/.cpp` — consumir vista efectiva y parámetros de especie.
- `mosquito_state.hpp` / `mosquito_submodel.hpp/.cpp` — especie y ciclo.
- `wire.hpp` — defaults/versiones, evitando más drift.
- `engine.cpp` — wiring de especie y paisaje efectivo.
- `main.cpp` / `flags.py` / `wrapper.py` — configuración y sidecar.
- `docs/specs/abm/spec.md` y `docs/system-status.md` — actualizar solo cuando comportamiento esté probado.

### Datos/outputs nuevos

- `mobility_diagnostics.json` con masa, centroides, percentiles y parámetros.
- `*_hosts_phase_{day,night,livestock}.png`.
- `*_hosts_daily_aggregate.png`.
- `*_salinity_monthly.png` (mapas mensuales SMAP del AOI, overlay con `water_frac`).
- `*_salinity_species_suitability.png` (respuesta salina de especie sobre el AOI).
- sidecar con `species_id`, `phase_aggregation_mode`, `phase_weights`, `mobility_manifest_hash`, `salinity_source`.

---

## 8. Tests y aceptación

### Unitarios

- `select_od` devuelve matriz esperada para cada fase/tipo.
- Cada CSR conserva suma de fila ≈ 1.
- `effective_hosts_at` conserva masa global dentro de tolerancia.
- Matriz identidad devuelve exactamente población residencial.
- Agregación de pesos suma 1 y reproduce fase única cuando weight=1.
- Humanos y ganado no comparten accidentalmente matriz.
- Salinidad: aptitud de *An. coluzzii* máxima en dulce y decreciente en salinidad alta.
- Especie default explícita y serializable.

### Integración

- Los diagnósticos usan el mismo operador y RNG que el runtime integrado.
- Baseline y mobility-enabled son reproducibles con misma seed, pero distintas seeds producen realizaciones distintas.
- No hay doble host-seeking.
- `H_residential` no muta después de construir `H_eff`.
- `patch_id` se actualiza antes de depositar huevos cuando Plan D se integre.

### Criterios de aprobación de movilidad

- Conservación global y por fila.
- Mapas revisados por usuario.
- Humanos permanecen estructurados alrededor de clusters residenciales; no se acepta dispersión uniforme o concentración artificial.
- Ganado muestra desplazamiento plausible y distinto de humano.
- Diferencia day/night tiene explicación visible.
- No se usa movilidad para justificar comportamiento absurdo; se corrige movilidad primero.

### Calibración posterior

- D14: conservación de movilidad.
- D13: distancia host-seeking, actualizado al rango Plan D si se aprueba.
- D16/D17: dispersión/clustering solo después de separar efecto mobility de kernel mosquito.
- Nuevo scorer futuro: `phase_presence_plausibility`, no registrarlo hasta tener observaciones de validación.

---

## 9. Riesgos y decisiones abiertas

| Riesgo/pregunta | Tratamiento inicial |
|---|---|
| Gravity model dispersa demasiado humanos | Fallo del gate; corregir OD antes de aceptar implementación |
| Pesos de fase sin datos de picadura horarios | Configurables; usar literatura local y sensibilidad |
| OD describe destinos, no individuos | Documentar presencia agregada; no inferir trayectorias individuales |
| Ganado nocturno no siempre identidad | Mantener parámetro reemplazable; validar por sistema productivo |
| *An. coluzzii* no es especie marina | Curva salina continua; *An. melas* futuro |
| SMAP solo mide salinidad marina | Marcar solo costas/estuarios; interior sin dato → dulce (0.0); validar con checklist §5.6 |
| SMAP requiere Earthdata auth | Mismo gate que MODIS (`EARTHDATA_TOKEN`); sin token → dataset skipped, salinidad no activa |
| Resolución 0.25° (~27 km) vs ABM 1 km | Remuestreo bilinear; artefactos de costa controlados en checklist |
| Huecos de misión SMAP (2019, 2022) | Meses sin dato → dulce, documentado en sidecar/env attrs |
| Plan D no implementado | Este plan incorpora movimiento fase-específico y corrige sus dependencias necesarias; Plan D queda como referencia |
| Documentación afirma funcionalidades no ejecutadas | Actualizar tras pruebas, no antes |
| Infección SEIR depende de especie estable | Mantener M7.4 fuera de alcance |

### Decisiones que requiere revisión del usuario

1. ¿Aceptar *An. coluzzii* como especie MVP Ghana-wide, sustituyendo provisionalmente la elección documental de *An. gambiae* s.s.?
2. ¿Fijar pesos de fase desde datos horarios locales o usar duración de fase como prior explícito cuando falten datos?
3. ¿Aceptar el muestreo multinomial por fase como realización final, con esperanza OD determinista solo como referencia?
4. ¿Tratar ganado como identidad nocturna en la primera configuración versionada?
5. ¿Qué parámetros concretos de movimiento dirigido y `patch_id` deben adoptarse al incorporar la lógica de Plan D?
6. ¿Confirmar NASA SMAP RSS SSS V6.0 mensual como única fuente de salinidad para el MVP, con interior sin dato tratado como dulce? (¿O añadir un proxy continental de salinidad de agua dulce como trabajo posterior?)

---

## 10. Referencias

- `docs/plans/in-process/m7-3-multi-species.md`
- `docs/plans/in-process/dispersal-plans/plan-D-mosquito-search-kernels.md`
- `docs/plans/in-process/dispersal-plans/plan-B-host-seeking.md`
- `docs/specs/ingest/spec.md`
- `docs/specs/abm/spec.md`
- `docs/system-status.md`
- Ghana vector composition: `Biting behaviour, spatio-temporal dynamics... Ghana`, Parasites & Vectors, 2024.
- Ghana larval ecology: `Larval habitat diversity and Anopheles mosquito species distribution... Ghana`, Parasites & Vectors, 2021.
- Ghana southern vectors: `Diversity, resistance and vector competence of endophilic anophelines from southern Ghana`, 2024.
- Salinity segregation: Tene Fossog et al., `Habitat segregation and ecological character displacement in cryptic African malaria mosquitoes`, Evolutionary Applications, 2015.
- Salinity physiology: `Tolerance of disease-vector mosquitoes to brackish water and their osmoregulatory ability`, 2019.
- Ghana *An. coluzzii* larval ecology: Kudom, `Larval ecology of Anopheles coluzzii in Cape Coast, Ghana`, 2015.
- NASA SMAP RSS SSS: Remote Sensing Systems (RSS). 2024. SMAP Sea Surface Salinity Products. Ver. 6.0. PO.DAAC, CA, USA. https://doi.org/10.5067/SMP60-3SMCS (monthly L3), docs: https://podaac.jpl.nasa.gov/dataset/SMAP_RSS_L3_SSS_SMI_MONTHLY_V6.

---

## 11. Sign-off gate

Implementation starts only after:

- user reviews this plan;
- species MVP and phase aggregation mode are selected;
- mobility-only diagnostic outputs are specified;
- CSR naming mismatch and duplicate host-seeking block are resolved;
- baseline metrics are recorded;
- any change to protected project docs is explicitly approved where required.
