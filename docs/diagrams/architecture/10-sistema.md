---
title: Sistema en capas
tags: [abm, overview]
tier: overview
calls: ["[[20-main-cli]]", "[[21-engine]]"]
called_by: []
down: ["[[15-bucle-diario]]", "[[20-main-cli]]", "[[21-engine]]", "[[40-wrapper]]"]
---
up:: [[00-INDEX]]

<!-- bc:auto:start -->
```breadcrumbs
type: mermaid
fields: [calls]
depth: 1
mermaid-direction: LR
show-attributes: true
```


<!-- bc:auto:end -->



# 10 · Sistema en capas

**Rol.** El ABM es un pipeline de 4 capas: Python decide *qué* correr (data, slots, flags), C++ decide *cómo* simular (día a día), y la salida queda como COG GeoTIFF + JSON sidecar por rollout. Nada de Python entra al bucle numérico.

```mermaid
flowchart TB
  subgraph L1["Capa 1 · Orquestación Python"]
    runner["runner.py<br/>run_abm_from_manifest()"]
    wrapper["wrapper.py<br/>CppAbmWrapper"]
  end
  subgraph L2["Capa 2 · Main C++"]
    main["main.cpp<br/>CLI11 parser · engine loop"]
  end
  subgraph L3["Capa 3 · Engine facade"]
    engine["Engine (step × N days)<br/>own: Coordinator · Submodel · Transmission"]
  end
  subgraph L4["Capa 4 · Submodelos"]
    quad["Coordinator · MosquitoSubmodel<br/>TransmissionModel · WindField"]
  end
  subgraph L5["Salida"]
    cog[("state.tif (COG)<br+/>transmission.tif")]
    json[("state.json / transmissions_*.json")]
  end

  runner -->|"arma argv"| wrapper
  wrapper -->|"subprocess.run(bin, argv)"| main
  main -->|"Engine ctor (1 por rollout, OpenMP)"| engine
  engine -->|"step() diario"| quad
  engine -->|"por rollout"| cog
  engine -->|""| json
```

## Cadena exacta (build → ejecución)

| # | Etapa | Actor | Efecto |
|---|---|---|---|
| 1 | compilar | `malariasim abm --compile` → `compile.py::compile_abm()` | cmake build + **auto-cp a `bin/mal_abm_fast_darwin`** (regla #28) |
| 2 | resolver datos | `runner.py::run_abm_from_manifest()` | `mal_core/download/catalog` resuelve Slots → paths reales `data/<aoi>/...` |
| 3 | lanzar | `wrapper.py::CppAbmWrapper.run()` | `subprocess.run([bin, "--aoi", ...])`, 50+ flags |
| 4 | simular | `main.cpp` → [[21-engine]] | 1 Engine por rollout, `step()` × days, OpenMP paralelo |
| 5 | persistir | `Engine::snapshot` / `snapshot_transmission` | COG + sidecar JSON + foci_log |

## Por qué esta separación

- Python = I/O, catálogo de datasets, manifest, licenses, CLI DX. Nada crítico de performance.
- C++ = 5 fases diarias a ~millones de agentes. SoA cache-friendly, RNG xoshiro reproducible.
- El contrato entre ambas = argv ([[40-wrapper]]) + archivos ([[30-tipos-datos]]).

## Conexiones → downstream

| Nada invoca esta nota (es raíz) | pero cada capa tiene su nota |
|---|---|
| Python | [[40-wrapper]] |
| Entrada C++ | [[20-main-cli]] |
| Facade | [[21-engine]] |
| Submodelos | [[22-coordinator]] · [[23-mosquito-submodel]] · [[27-transmission]] · [[28-wind-field]] |