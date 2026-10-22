# Plan 1 — Sustitución rupturista: eliminar sistema hidrológico anterior

- Fecha: 2026-10-17.
- Estado: EJECUTADO 2026-10-17 (contract v3.0 landed). Dem/TWI/solver mm/eras nước channels retired; ver docs/specs/*.
- Decisión de diseño aprobada: estimar oferta relativa de criaderos por celda mediante proxies, no reconstruir microhidrología.
- Formulación canónica: oferta por tipo `H[i,g]`, dos respuestas temporales compartidas `A[i,k,t]` y afinidad de especie por hábitat `w[s,g]`. Sin matrices libres de conversión.
- Política de cambio: ruptura de contratos y eliminación completa del sistema sustituido. No coexistencia, ni siquiera desconectada.
- Complemento obligatorio: [Plan 2 — Oferta de criaderos e integración](02-oferta-criaderos-proxies-download-ingest-abm.md).
- Alcance: sistema anterior de criaderos y su cierre transitivo de dependencias en download → ingest → ABM, APIs, constantes, librerías, tests, configuración y documentación activa. No es una limpieza indiscriminada de datos o experimentos ajenos.

## 1. Problema que se elimina

DEM de 30–90 m, agregado durante descarga a celdas de aproximadamente 1 km, no observa las microestructuras donde crían mosquitos. Derivar TWI, acumulación D8 o capacidad de depresiones de esa malla no recupera información subpíxel perdida.

No se trata principalmente de corregir alineación o ajustar constantes. Se abandona la premisa de que esa topografía determine presencia, profundidad o persistencia de pequeños criaderos. Una celda elevada también puede contenerlos.

Resultado buscado:

```text
Antes: DEM → TWI/D8 → candidatos → lluvia amplificada → agua_mm → capacidad
Después: agua observada + uso del suelo → H por hábitat → disponibilidad A + afinidad w por hábitat → capacidad acuática
```

La nueva disponibilidad será un índice estadístico, no volumen físico. Por tanto, tampoco se exigirá balance de masa de un sistema que ya no pretende transportar agua.

## 2. Decisión de ruptura y estado final obligatorio

La entrega no consiste en desconectar DEM y añadir otro modelo al lado. Consiste en **sustituir el sistema y borrar su implementación anterior**. Mantener código muerto dificulta incorporación de personas y permite que futuros cambios con LLM mezclen modelos incompatibles.

Estado final:

- Una sola implementación de oferta y disponibilidad de criaderos: la descrita en plan 2.
- Se conservan tipos de hábitat hasta aplicar afinidad de especie; no reducir primero urbano/humedal/abierto/cultivo a dos índices y perder contexto.
- Un solo contrato admitido para nuevos inputs del ABM, sin lectores del formato anterior.
- Una única capacidad acuática, sin componentes residuales del solver retirado.
- Cero flags de selección antiguo/nuevo, shims, aliases históricos, fallbacks o dobles rutas de descarga/ingest.
- Cero módulos, constantes, parámetros, dependencias o tests conservados solo para sistema sustituido.
- Ninguna copia del solver en `_legacy/`, `deprecated/`, `archive/`, experimentos o notebooks ejecutables para «por si acaso».
- Recuperación histórica mediante Git y resultados conservados, no mediante una segunda implementación dentro del checkout entregado.

**Código roto o consumidores desactualizados se migran o eliminan dentro de la misma entrega.** No justifican mantener sistema antiguo por compatibilidad.

Ruptura se refiere a implementación, no a biología: se conserva hipótesis de pequeñas aportaciones urbanas persistentes por filtraciones, fugas y almacenamiento humano. Se elimina su representación como profundidad mínima artificial; plan 2 la expresa como `H[i,urban_persistent]`. Dos respuestas temporales no significan solo dos tipos de hábitat.

## 3. Límites de seguridad y frontera de eliminación

1. Eliminar implementación DEM/TWI/D8 dedicada a criaderos, no solo sus llamadas. Loader o utilidad DEM compartida solo puede permanecer con uso independiente concreto y vigente; «puede servir después» no basta.
2. No eliminar datasets, manifests, tiles, `terrain/`, LiDAR, notebooks, papers, ejecuciones anteriores ni `agents/memory/`.
3. Mantener intacto trabajo concurrente y cambios locales ajenos. No usar reset, checkout ni limpieza recursiva para esta migración.
4. Cada eliminación requiere inventario de consumidores. Migrar consumidores del sistema sustituido, no preservarlos como excusa para mantenerlo. Código realmente independiente puede quedar, con alcance y pruebas propios, sin ruta de vuelta al sistema antiguo.
5. No modificar mortalidad adulta, movimiento, búsqueda de hospedadores, EIP, fecundidad ni ciclo gonotrófico para compensar cambios de capacidad acuática.
6. Trabajar en rama de ruptura y entregar planes 1 y 2 como un corte integrado. La rama puede quedar temporalmente incompleta; no fusionar una desconexión parcial ni mantener segundo motor para que cada paso siga ejecutando el anterior.
7. Los artefactos científicos e investigaciones independientes protegidos no son código muerto por definición. Si una eliminación propuesta afecta trabajo concurrente o datos, detener ese elemento y pedir decisión; no ampliar autorización de limpieza.

## 4. Mapa inicial para eliminación: código, no contenido de datasets

Mapa basado en inspección de código realizada al redactar primera versión el 2026-10-17. Grafo consultado entonces: `Users-davidflorezmazuera-Downloads-MalariaSentinel`, generación `2026-10-16T18:00:06Z`, con cobertura de rutas y lecturas directas relevantes. Revalidar antes de implementar. Grafo es evidencia orientativa; no prueba ausencia de consumidores.

No se resolvieron ni inspeccionaron datos de AOIs para redactar estos planes. No se presupone que descargas existentes contengan productos nuevos, fracciones correctas o temperatura diaria.

| Punto real | Dependencia actual observada | Cambio objetivo |
|---|---|---|
| `mal-core/src/mal_core/download/registry.py::discover_downloaders` | Perfil por defecto incluye `dem.elevation`; WorldCover queda fuera | Sustituir perfil, registros y outputs obsoletos; no dejar perfil hidrológico alternativo |
| `mal-core/src/mal_core/cli.py::_ensure_env_stack` | Autodescarga explícita DEM y JRC antiguo | Usar dependencias del sistema nuevo; revisar además comprobación de caché por mera existencia |
| `mal-core/src/mal_core/ingest/daily_nc.py::ENV_INPUT_SLOTS` | Slot DEM opcional y JRC requerido | Eliminar slots del modelo anterior y migrar consumidores a nuevos productos |
| `daily_nc.py::build_daily_env_nc` | Calcula `twi`, `catchment_ratio` y `k_capacity_mult` con supuestos de agua/NDVI/urbanización | Retirar topografía y fórmula antigua de capacidad |
| `mal-core/src/mal_core/ingest/env.py::_write_habitat_patches_gpkg` | Genera candidatos con TWI > 8 y agua > 0 | Generar candidatos virtuales por oferta potencial, sin DEM |
| `mal-core/src/mal_core/abm/src/habitat_engine.cpp::load_from_gpkg` | Descarta patches con `HABITAT_MIN_TWI` | Admitir nuevo contrato de celda candidata sin veto topográfico |
| `mal-core/src/mal_core/abm/src/coordinator.cpp::to_dataframe` | Combina TWI, agua, lluvia, reglas urbanas y escorrentía | Sustituir por disponibilidad continua del plan 2 |
| `coordinator.cpp::build_seed_instructions` | Documenta/usa criterios de viabilidad de agua/TWI | Revisar selección espacial de candidatos; no reintroducir veto antiguo |
| `abm/include/mal_abm_fast/pool_hydrology.hpp::advance_pool` | Lluvia × `catchment_factor`, evaporación y tope de agua | Reemplazar estado de profundidad por estado de disponibilidad |
| `abm/src/aquatic_cohort_bank.cpp::larva_mortality_density` | Multiplica K por `K_eff` y después por `pool_water_mm / POOL_WATER_CAPACITY_SAT_MM` | Una sola capacidad diaria, sin segundo factor hidrológico |

Rutas abreviadas `abm/...` pertenecen a `mal-core/src/mal_core/abm/`.

## 5. Matriz de eliminación obligatoria

### 5.1 Código, librerías y dependencias

| Elemento | Acción final | Qué no cuenta como terminado |
|---|---|---|
| `abm/include/mal_abm_fast/pool_hydrology.hpp` | Extraer únicamente mecanismos biológicos conservados a módulo con nombre propio y borrar solver/header anterior | Dejar `advance_pool` sin callers o como implementación de referencia |
| `abm/pool_hydrology.py` | Migrar usos biológicos/scoring pertinentes y eliminar réplica del modelo anterior | Mantener versión Python para tests mientras producción usa otro modelo |
| `mal-commonlib/src/mal_commonlib/terrain/twi.py` y helpers TWI/D8 relacionados | Eliminar APIs usadas únicamente por criaderos; si hay uso independiente real, separar y justificar su alcance | Conservar librería entera porque importaba una función útil |
| Loader `dem.py`, exports, registros, extras y paquetes asociados | Eliminar piezas cuyo único propósito era criaderos; conservar exclusivamente prestaciones con consumidor independiente comprobado | Loader registrado o dependencia instalada sin usuario actual |
| Generación DEM/TWI/escorrentía en ingest | Borrar algoritmos, imports, parámetros, salidas y escritura de metadata | `skip_dem=True`, rama muerta o valores neutros |
| Forzantes/estado hidrológico en C++ y Python | Borrar structs/campos viejos y migrar cada acceso a contrato nuevo | Campos `water_mm` o TWI rellenados con ceros para compilar |
| Outputs y readers antiguos JRC/WorldCover/temperatura | Migrar consumidores y retirar implementaciones sustituidas; un producto distinto con función independiente sí puede permanecer | Dos outputs equivalentes para que siga funcionando un consumidor no migrado |
| Dependencias de build/runtime | Retirar includes, fuentes CMake, extras Python, exports y paquetes que pierdan último uso | Quitar fuente pero dejar biblioteca/extra instalado |

«Eliminar dependencia» no significa retirar GDAL, rasterio o librerías geoespaciales que siguen usando los loaders nuevos. Decidir por usos reales, no por relación histórica con DEM.

### 5.2 Constantes y reglas antiguas

- DEM como input de ingest de hábitat, autodescarga para ejecutar ABM y parámetro opcional de compatibilidad.
- TWI y umbrales topográficos para generar, cargar, activar o sembrar criaderos.
- D8, `catchment_ratio`, `catchment_factor` y multiplicación de precipitación por área contribuyente en este subsistema.
- Fallbacks `POOL_CATCHMENT_URBAN/RURAL` y familia `POOL_RUNOFF_*`: migrar consumidores y eliminar definiciones, no esperar a que se vuelvan huérfanos por casualidad.
- Reglas `PLUVIAL_POOL_RAIN_THRESHOLD_MM`, `PLUVIAL_POOL_TWI_THRESHOLD`, `PLUVIAL_POOL_WATER_FRAC_MIN` como requisitos de pertenencia. Lluvias pequeñas también pueden aumentar disponibilidad.
- `POOL_URBAN_BASELINE_MM`, `POOL_URBAN_BASELINE_FACTOR` y clamps que inventan una lámina fija. **Conservar aporte urbano persistente**, como `H[i,urban_persistent] = beta_urban * lc_built_frac[i]`, incluso sin señal JRC ni lluvia reciente. Aprovechamiento depende de `w[s,urban_persistent]`.
- Cupo `URBAN_DENSITY_CAP_FRACTION`: no debe descartarse hábitat porque otras celdas urbanas del AOI ocupen un cupo. Controlar magnitud mediante oferta continua y coste mediante implementación.
- Fórmula antigua de `water_eff`/`k_capacity_mult`, incluidos área fija de 1 km² y conversión mediante emergencia y longevidad adulta como si eso fuese capacidad larvaria medida.
- Multiplicación posterior por disponibilidad de agua antigua dentro de Beverton–Holt.
- `POOL_WATER_MAX_MM`, `POOL_WATER_BREED_MM`, `POOL_WATER_DRY_MM`, `POOL_WATER_CAPACITY_SAT_MM`, `POOL_EVAP_*`, `HABITAT_MIN_TWI` y parámetros de activación urbana por relieve/lluvia pertenecientes al modelo sustituido.
- Estados `water_mm`, `days_since_fill`, buffers de lluvia antecedente y clamps urbanos del solver antiguo. Los nuevos estados tendrán semántica y nombres propios, no reutilizarán falsas profundidades.
- Campos, flags, parámetros de escenarios, visualizaciones y tests que describan exclusivamente sistema retirado. Revisar consumidores antes de quitar cada uno.

No eliminar a ciegas todo prefijo `POOL_*`: constantes biológicas de desecación/washout que sigan siendo necesarias se trasladan y renombran según su función. Una única definición y mecanismo, no duplicación entre header viejo y nuevo.

### 5.3 APIs, contratos, configuración y documentación

| Pieza | Reemplazo |
|---|---|
| Estado `PoolState` y forzantes de escorrentía | Estado normalizado de disponibilidad con memoria temporal |
| GPKG de supuestas pozas detectadas | Mismo contenedor geoespacial si resulta útil, pero únicamente schema nuevo de celdas virtuales; borrar parser anterior |
| Activación húmeda/seca desde milímetros | API nueva de disponibilidad adimensional; sin adaptador que vuelva a producir milímetros |
| Vista estática `K_eff` | Capacidad acuática diaria por celda; renovación segura en ambos constructores de Engine |
| Seeding filtrado por TWI | Candidatos de oferta nueva; mismos controles y total inicial en comparación A/B |
| Scorers basados en charcas/profundidades antiguas | Migrar/retirar métricas incompatibles y sus imports; baseline histórico conserva propia semántica |
| Flags, argumentos, aliases y defaults viejos | Retirar de CLI, wrapper, schemas, dataclasses, escenarios, fixtures y ayuda |
| Outputs y nombres engañosos heredados | Cambiar productor y todos los consumidores juntos; sin alias de lectura/escritura |

Diseño provisional de estos planes también queda sustituido: no implementar `B[i,k]`, matrices `alpha`/`theta`, bandas de solo dos potenciales ni preferencias de especie únicamente por respuesta temporal. Eran propuestas, no se presupone que estén implementadas. Contrato nuevo conserva seis tipos `H` y solo dos respuestas `A`, según plan 2.

No mapear índice nuevo a `500 mm` o `6 mm` para seguir ejecutando física antigua. Eso ocultaría convivencia de modelos.

Inventariar también ejemplos, notebooks, herramientas de visualización, prompts/skills, configuraciones de experimentos y especificaciones activas. Migrarlos o retirar receta obsoleta; no dejar instrucciones que inviten a futuros LLM a reintroducir solver antiguo. Papers, resultados e informes históricos pueden explicar modelo anterior como historia, nunca como alternativa vigente.

### 5.4 Qué permanece y por qué no son dos sistemas paralelos

- Prestaciones DEM con uso independiente documentado, por ejemplo visualización topográfica vigente. No pueden conservar solver acuático antiguo, dependencias exclusivas de criaderos ni un modo de activarlo. Ausencia de usuario independiente significa eliminación.
- Experimentos LiDAR y sus resultados: dejan de ser prerrequisito del MVP, no se borran.
- JRC, WorldCover, lluvia y temperatura: se reutilizan con semántica y agregación correctas.
- Máscaras terrestres/océano y distinción de agua salobre: son controles de dominio, no escorrentía.
- Host grid, GHSL, edificios, WorldPop, ganado, movilidad y viento: siguen alimentando otros subsistemas. No eliminarlos por dejar de usarlos en oferta acuática.
- Respuestas térmicas de desarrollo acuático y mecanismos biológicos existentes.
- Mortalidad por desecación y washout: mover mecanismos conservados a módulos biológicos nuevos y quitar archivo contenedor antiguo. Congelar inicialmente tasas y etapas; cambiar API de disponibilidad. No inventar nuevas pérdidas para compensar crecimiento de hábitats.
- NDVI: quitar su papel hidrológico antiguo no autoriza su retirada global. Auditar consumo y contrato; si queda necesario para otro consumidor, mantenerlo. Si se elimina de reader/ingest, migrar ambos conjuntamente.

Distinción obligatoria: preservar datos o investigación LiDAR independiente no autoriza esconder una copia ejecutable del sistema de criaderos retirado en `terrain/` o experimentos. Ante trabajo compartido afectado, resolver frontera explícitamente antes de borrar.

## 6. Ejecución: una entrega integrada, no transición con dos motores

### Fase A — Baseline histórico e inventario cerrado

1. Registrar estado git y cambios concurrentes. Trabajar en rama/área aislada sin copiar modificaciones ajenas sobre otras versiones.
2. Resolver inputs del AOI elegido mediante `mal_core.download.catalog`; comprobar lectura, cobertura y procedencia. Archivo declarado y ausente sigue siendo error.
3. Ejecutar baseline antes de eliminar, registrando commit, ejecutable, parámetros, seeds, fechas, grid y hashes de inputs. Conservar resultados; no copiar fuentes antiguas al nuevo checkout ni crear ejecutable `legacy` distribuido con versión nueva.
4. Inventariar usos de DEM/TWI/CR, `POOL_*`, `PLUVIAL_POOL_*`, `HABITAT_MIN_TWI`, reglas urbanas y `k_capacity_mult`: Python, C++, CLI, seeding, metadata, tests, scorers y lectores de entrenamiento/predicción.
5. Usar grafo, trazas relevantes y búsqueda literal complementaria. Para eliminar funciones compartidas, comprobar ambos sentidos y usos declarativos en registros/configuración: grafo sin callers no demuestra desuso.
6. Crear inventario con ruta/símbolo, consumidores, acción (`borrar`, `reescribir`, `conservar_independiente`), prueba y motivo. Todo elemento de conservación necesita consumidor independiente concreto; inventario sin clasificar bloquea cierre.
7. Capturar fallos previos de tests. No corregir biología ni actualizar expectativas arbitrariamente como parte de limpieza.

**Salida:** inventario revisable y baseline reproducible. Ningún dato eliminado.

### Fase B — Implementar ruptura en rama de trabajo

1. Prototipar plan 2 en tier experimental según reglas del monorepo. Experimento tiene fecha de salida por promoción o abandono, no queda como segundo backend permanente.
2. En rama de ruptura, eliminar solver y superficies públicas anteriores. Implementar único contrato nuevo y migrar consumidores dentro de la misma entrega.
3. No introducir flag antiguo/nuevo ni decoder doble, tampoco temporalmente. Comparación usa resultados de baseline capturados en revisión anterior.
4. Preparar NC/GPKG nuevo con seis tipos `H` e identificadores explícitos, sin TWI. Un estado pluvial compartido, oferta urbana persistente y capacidad diaria con `w[s,g]`; sin intermediario que agregue por respuesta antes de aplicar preferencias.
5. Separar helpers biológicos útiles, con nombres correctos, y borrar archivos/contenedores anteriores.
6. Promover partes verificadas del prototipo; eliminar duplicados experimentales del sistema promovido, dejando como máximo entrypoint que llame a implementación canónica. No mantener réplicas Python/C++ completas para comparación.

**Salida:** una implementación nueva en rama, sin antiguo motor ni capas de compatibilidad. No se fusiona hasta completar recorrido y pruebas.

### Fase C — Integración completa, coordinada con plan 2

1. Cambiar defaults de descarga y autoprovisión: DEM deja de solicitarse para criaderos.
2. Cambiar slots, builders, metadata y cachés al contrato nuevo.
3. Cambiar generador y lector de GPKG. Eliminar veto TWI también en seeding y carga C++, no solo en Python.
4. Actualizar reader de NetCDF, estructuras de clima y ambas rutas de construcción de Engine.
5. Calcular disponibilidad una sola vez por celda y fecha, no por tipo de hábitat ni por especie. Consultar estado, generar dataframe o sembrar no debe avanzar un día adicional.
6. Alimentar capacidad diaria al banco acuático y retirar todos los factores hidrológicos antiguos de esa capacidad.
7. Separar desecación/washout de `water_mm`. Ninguna cohorte seca desaparece del seguimiento por no entrar en lista de patches activos.
8. Migrar flags, escenarios, tests, scorers, visualización, entrenamiento/predicción y documentación activa afectados. Quitar APIs/imports sin propósito tras migración.
9. Rechazar artefactos antiguos con mensaje de regeneración. Validación de schema no incorpora parser, conversor ni ejecución del modelo anterior.

**Salida:** download → ingest → ABM funciona sin DEM ni productos topográficos en inputs nuevos.

### Fase D — Auditoría de residuos y corte único

1. Revisar todos los elementos del inventario, incluidos archivos sin callers: no basta demostrar que sistema nuevo no los ejecuta.
2. Confirmar ausencia de solver antiguo, constantes huérfanas, opciones de selección, wrappers de compatibilidad, exports, dependencias exclusivas y copias en experimentos.
3. Regenerar artefactos nuevos en destino separado; conservar originales como datos históricos no admitidos por runtime nuevo. Esto incluye raster anuales antiguos `water_temp`/`water_temp_c`: no borrarlos ni presentarlos como serie diaria. Cambio de manifest operativo solo tras validación, con copia/versionado previo.
4. Actualizar `docs/specs/{download,ingest,abm,data,scoring}/spec.md`, contratos de salida, ayuda CLI y diagramas afectados. Auditar también entrenamiento/predicción para no romper canales de entrada.
5. Si hay planes previos que exijan depresiones DEM o LiDAR para esta entrega, marcarlos como sustituidos cuando existan. No recrearlos ni eliminarlos basándose solo en historial de conversación.
6. Mantener registro de atribuciones reales de nuevos derivados. Quitar atribución MERIT de outputs nuevos solo si no contienen ya derivados MERIT; no reetiquetar outputs históricos.
7. Fusionar corte completo cuando código nuevo y auditoría de eliminación superen aceptación. Ninguna fase intermedia se publica como «nuevo sistema» con viejo motor escondido.

## 7. Validación de eliminación, no solo de desconexión

### Tests requeridos

- AOI con inputs nuevos y sin slot DEM: descarga/ingest/ABM exitosos; ningún acceso a DEM o TWI. Construir fixture nueva en directorio aislado, no borrar datos existentes para probarlo.
- Mismos inputs de hábitat, lluvia y temperatura; DEM ausente o valores DEM radicalmente distintos: idéntica oferta/capacidad nueva.
- Celda sin agua JRC pero cobertura compatible y lluvia: puede tener oferta pluvial positiva.
- Celda urbana con fracción construida positiva y coeficiente humano persistente positivo: conserva oferta persistente estimada aunque JRC=0 y no llueva. No recibe profundidad mínima ficticia ni garantía de criadero observado.
- Mismo vecindario/celda en AOIs de distinta extensión: no cambia por cupo urbano global.
- Falta de producto requerido, producto inválido o caché de contrato antiguo: error informativo, no fallback antiguo.
- Raster anual histórico de temperatura y contrato ambiental anterior se rechazan como inputs del contrato nuevo; los archivos quedan intactos para revisión/reproducción con revisión de código compatible.
- Temperatura diaria nueva identifica temperatura de aire ERA5-Land, no medición de agua. Todos los consumidores activos que pasen a la banda diaria quedan inventariados y su cambio de respuesta se informa separadamente del cambio hidrológico.
- Candidatos húmedos y secos siguen representados; pérdida de disponibilidad alcanza banco acuático.
- Capacidad de cohortes procede una sola vez de `K_habitat(cell, day, species)`.
- Perfiles con igual preferencia agregada persistente/pluvial pero distinto peso urbano/humedal distinguen capacidad: no queda un atajo que pierda `g`. `H` es independiente de especie y `A` se comparte por respuesta temporal.
- Sin cambios en mortalidad adulta, fecundidad, movimiento ni kernels de búsqueda.

### Auditoría de residuos obligatoria

1. Buscar símbolos/campos/flags inventariados en código, registros, imports, build, dependencias, tests, configuración, ejemplos y documentación operativa. Verificar contenido, no solo nombres de archivo.
2. Hacer cierre transitivo de utilidades y paquetes que pierdan último uso; actualizar dependencias y lockfiles únicamente donde corresponda.
3. Cada hit se clasifica: implementación prohibida a eliminar, uso independiente autorizado o referencia histórica/no ejecutable. No imponer cero menciones a la palabra DEM en papers.
4. Smoke test de imports y build limpio: eliminar artefactos de compilación propios solo con alcance seguro, o compilar en directorio nuevo. Evitar enlace accidental a objetos viejos.
5. Verificar tests/scorers no importan versión Python del solver borrado. Fixtures esperadas no deben requerir ejecutarlo.
6. Contrato anterior produce error de regeneración; no queda conversión automática ni camino de ejecución alternativo.

Generar informe final con elementos borrados, consumidores migrados y excepciones independientes justificadas. «No se usa» no es criterio de aceptación para una implementación del modelo sustituido: debe dejar de existir.

### Builds y scoring

- Tests unitarios Python de loaders/catalog/ingest y nuevos módulos, más suite C++ relevante.
- Compilar con `malariasim abm --compile`. Si se usa CMake manualmente, copiar ejecutable de `abm/build/src/mal_abm_fast` a `abm/bin/mal_abm_fast_darwin`: wrapper prioriza `bin/`.
- Guardar identidad de binario usado. Comparar ctest con baseline: existen cinco fallos previamente documentados de duración de reposo gonotrófico; verificar estado actual antes de clasificarlos como previos.
- Scoring canónico: `mal_core/scoring/`, `scorecard.json`. No recrear harness eliminado bajo `abm/tests/calibration/`.
- No afirmar mejora de malaria solo porque desaparezca dependencia DEM o suba número de celdas candidatas. Validación predictiva corresponde al plan 2.

## 8. Criterios de aceptación

- [ ] Camino principal de criaderos no descarga, resuelve ni lee DEM.
- [ ] Solver anterior Python/C++, módulos exclusivos y sus constantes han sido eliminados, no archivados ni desconectados.
- [ ] Sin backend viejo, selector, shim, alias histórico, parser anterior o fallback; un único contrato de ejecución.
- [ ] Dependencias, exports y archivos de build sin residuos del sistema retirado.
- [ ] Sin vetos TWI, D8, escorrentía ni multiplicadores de cuenca en ese camino.
- [ ] Aporte urbano persistente conservado como proxy explícito; sin lámina fija en mm, cupo urbano global ni doble escalado hidrológico de K.
- [ ] Nuevos candidatos, capacidad diaria, activación, desecación y seeding usan contrato coherente.
- [ ] Oferta por hábitat y `w[s,g]` conservan diferencias de contexto; sin `B`, matrices libres de conversión o pesos únicamente por persistencia/pluvial como alternativa.
- [ ] Todos los puntos de entrada relevantes usan misma versión y política de caché.
- [ ] Pipeline real sin DEM funciona; fixtures validan independencia de relieve kilométrico.
- [ ] Biología adulta y otros subsistemas permanecen fuera de alcance.
- [ ] Inventario cerrado y auditoría transitiva justifican cualquier prestación compartida conservada; ninguna es copia del motor anterior.
- [ ] Configuración, tests, scorers, docs, ejemplos y prompts activos ya no enseñan ni invocan sistema retirado.
- [ ] Prototipo promovido no queda como segunda implementación en experimentos.
- [ ] No se ha borrado ni sobrescrito trabajo ajeno, dataset o experimento existente.
- [ ] Planes 1 y 2 se entregan juntos: implementación nueva validada y sistema antiguo eliminado en corte único.

## 9. Recuperación sin compatibilidad permanente

Rollback de despliegue significa volver a revisión completa previa y a sus artefactos compatibles, no reintroducir módulo viejo dentro de revisión nueva. La revisión nueva no incluye segundo ejecutable ni motor alternativo. Conservar resultados/manifests históricos no obliga a que código actual los acepte. Cualquier modificación de manifest operativo requiere copia/versionado previo y activación explícita; no editarlo manualmente para fingir compatibilidad.

Este plan termina al retirar dependencia microhidrológica no observable del MVP. No abre un proyecto paralelo de reconstrucción del terreno.
