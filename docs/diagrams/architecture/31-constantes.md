---
title: Constantes físicas · model_constants.yaml
tags: [abm, cpp, constantes, paridad, yaml]
tier: contract
file: "mal-core/config/model_constants.yaml"
---
up:: [[00-INDEX]]

# 31 · Constantes — fuente única YAML

**Rol.** `mal-core/config/model_constants.yaml` es la ÚNICA fuente de parámetros
de modelo (py ⇄ C++), con la unidad y la cita de paper en el comentario de cada
clave. El código no declara valores de modelo: los loaders (`load_config()` en
C++, `mal_core.habitat.config.CONFIG` en py) los leen del YAML.

## Fuente y validación

| Pieza | Ruta | Rol |
|---|---|---|
| Valores | `mal-core/config/model_constants.yaml` | fuente única; una sección por dominio |
| Historial | `mal-core/config/model_constants-CHANGELOG.md` | altas/cambios de claves y su motivo |
| Validador (py) | `mal-core/src/mal_core/config_validation.py` | pydantic v2, `extra="forbid"`, sin defaults; invariantes e impresión de claves faltantes |
| Acceso C++ | `mal-core/src/mal_core/abm/include/mal_abm_fast/wire.hpp` | accesores `inline` que leen `load_config()` (p.ej. `EIP_THRESHOLD_GD()`, `kMetresPerDegLat()`); no son constantes compiladas |
| Acceso py | `mal-core/src/mal_core/habitat/config.py` | singleton `CONFIG` validado |
| Guard mecánico | `tools/check_no_constants.sh` | falla si un valor migrado reaparece como literal |

## Secciones del YAML (sin duplicar valores aquí)

- `version` / `contracts` — versionado del fichero y contratos `env_nc` / `cogs_state`.
- `habitat_types` — tipos de hábitat y su dinámica (persistent/pluvial).
- `habitat` / `pluvial` / `aquatic_stress` / `urban` — umbrales y respuestas temporales.
- `species` — filas por especie: pesos por hábitat, `activity_weights`, `pref`,
  salinidad y kernels de host-seeking. `k_ref` es única para el motor.
- `capacity` — disponibilidad persistente y escala Beverton-Holt.
- `ingest` — sentinelas NoData y resolución de ingest (espejo py⇄C++).
- `geodesy` — `earth_radius_m` y `metres_per_deg_lat` (el validador comprueba
  la relación exacta π·R/180).
- `eip` / `transmission` — modelo SEIR-SEI Ross-Macdonald.
- `thermal` — curvas térmicas (EFD, desarrollo de huevo/larva/pupa).
- `gonotrophic` — ciclo gonotrófico (`GonotrophicParams` lee esta sección).
- `dispersal` / `host_seeking` / `oviposition` — kernels de movimiento y ventanas.

## Reglas

- **R1** — ningún default de modelo en código; si un valor vive en un `.cpp`/`.py`,
  se mueve al YAML con clave nombrada por concepto y unidad en comentario.
- **R2** — el validador pydantic es el único validador; toda alta/renombre/borrado
  de clave extiende el modelo y sus tests.
- **R4/R5** — cambiar un valor científico exige paper en `papers/`; las tareas de
  migración no cambian valores.
- La paridad py⇄C++ se verifica en los tests (`test_config_loader.py` incluye el
  dump C++ `config_dump`), y el golden del motor congela el comportamiento.

up:: [[00-INDEX]] · related:: [[30-tipos-datos]] · [[23-mosquito-submodel]]
