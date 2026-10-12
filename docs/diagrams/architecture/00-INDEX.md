---
title: "ABM · Mapa de Arquitectura"
tags: [abm, index, moc]
tier: index
cssclasses: [wide-page]
down: ["[[10-sistema]]", "[[15-bucle-diario]]", "[[dependency-flow-diagram]]", "[[20-main-cli]]", "[[21-engine]]", "[[22-coordinator]]", "[[23-mosquito-submodel]]", "[[24-aquatic-cohort-bank]]", "[[25-host-seeking]]", "[[26-oviposition-seeking]]", "[[27-transmission]]", "[[28-wind-field]]", "[[30-tipos-datos]]", "[[31-constantes]]", "[[40-wrapper]]", "[[90-convenciones]]"]
---

# 00 · Índice — Motor ABM (`mal-core/src/mal_core/abm/`)

Nota-raíz del vault MalariaSentinel. Todo lo demás cuelga de aquí.

## Codificación de relaciones

- Tablas `Conexiones` = call graph **verificado** (src real + índice codebase-memory, 130 aristas CALLS).
- Cada nota lleva edges tipado en frontmatter (`calls:` / `called_by:` / `owns:` / `reads:` / `writes:`) con wikilinks → navegable en Obsidian Graph View y clickable en texto.
- Convención completa y cómo extender: [[90-convenciones]].

## Navegación

1. **Vista macro:** [[10-sistema]] — capas Python → CLI → Engine → submodelos → COG/JSON. Dependencias (binario/datos/flags): [[dependency-flow-diagram]].
2. **Vista temporal:** [[15-bucle-diario]] — el pulso del sistema, `Engine::step()`.
3. **Clase por clase:** notas [[20-main-cli]] [[21-engine]] [[22-coordinator]] [[23-mosquito-submodel]] [[24-aquatic-cohort-bank]] [[25-host-seeking]] [[26-oviposition-seeking]] [[27-transmission]] [[28-wind-field]].
4. **Contrato de datos:** [[30-tipos-datos]] · [[31-constantes]].
5. **Capa Python:** [[40-wrapper]].
6. **Canvas nativo:** [[90-convenciones]] (el canvas `abm-architecture.canvas` se abre como canvas, no como texto).

## Diagrama maestro

```mermaid
flowchart LR
  subgraph PY[Capa Python]
    W["wrapper.py<br/>CppAbmWrapper"]
  end
  subgraph ENT[Entrada C++]
    M["main.cpp<br/>CLI11 · OpenMP rollouts"]
  end
  subgraph NUC[Engine facade]
    E["Engine"]
    C["CoordinatorModel"]
    S["MosquitoSubmodel"]
    T["TransmissionModel"]
  end
  subgraph BIO[Comportamiento]
    A["AquaticCohortBank"]
    H["HostSeekingModel"]
    O["OvipositionSeekingModel"]
    F["WindField"]
  end
  subgraph DAT[Contrato]
    D["wire.hpp · tipos"]
    K["constantes"]
  end

  W -->|"subprocess.run(argv)"| M
  M -->|"Engine ctor ×n_rollouts · Prng(seed+i)"| E
  E -->|"step(): set_climate_day → activate_patches → to_dataframe → advance_day"| C
  E -->|"sub_->advance_day(patch_states)"| S
  E -->|"advance_vector_eip · advance_human_transmission · record_daily_stats"| T
  C -->|"'parches activos' · patch_states_today"| S
  S -->|"cohort_bank_.advance_day · collect_emergence"| A
  S -->|"detect_host_cell · approach_vector · select_host_entry"| H
  S -->|"detect_breeding_cell · step_toward"| O
  F -->|"is_migration_season · advect(u,v)"| H
  K -->|"K_MAX · EIP_THRESHOLD_GD · DISPERSAL_*"| D
  S --> D
```

## Enrutado build + runtime

```mermaid
flowchart TD
  malariasim["malariasim CLI (pyproject entry)"]
  comp["compile.py · compile_abm()"]
  runner["runner.py · run_abm_from_manifest"]
  catalog["mal_core/download/catalog · resolve / Slots"]
  wrapper["wrapper.py · CppAbmWrapper"]
  binbin["bin/mal_abm_fast_darwin"]
  cli["src/main.cpp · mal_abm_fast"]
  out1[("state.tif + state.json")]
  out2[("transmission.tif + foci_log")]

  malariasim --> comp
  malariasim --> runner
  runner --> catalog
  catalog --> wrapper
  comp --> binbin
  wrapper --> binbin --> cli
  cli --> out1
  cli --> out2
```

## Orden de lectura recomendado

[[10-sistema]] · [[15-bucle-diario]] · [[dependency-flow-diagram]] · [[20-main-cli]] · [[21-engine]] · [[22-coordinator]] · [[23-mosquito-submodel]] · [[24-aquatic-cohort-bank]] · [[25-host-seeking]] · [[26-oviposition-seeking]] · [[27-transmission]] · [[28-wind-field]] · [[30-tipos-datos]] · [[31-constantes]] · [[40-wrapper]] · [[90-convenciones]] · [[91-plugins-setup]]

## up

up:: [[10-sistema]]