---
title: Bucle diario Engine::step()
tags: [abm, flujo, critical]
tier: core-flow
calls: ["[[22-coordinator]]", "[[23-mosquito-submodel]]", "[[27-transmission]]"]
called_by: ["[[21-engine]]"]
file: "mal-core/src/mal_core/abm/src/engine.cpp"
lines: "537-597"
---
up:: [[10-sistema]]

<!-- bc:auto:start -->
```breadcrumbs
type: mermaid
depth: [0, 1]
sort: field
show-attributes: [field]
mermaid-direction: LR
mermaid-arrow: true
```

> [!info] Conexiones exactas del grafo
> **Nodo actual · nota: 15 bucle diario**
> *Mantenida manualmente — fuente: cpp real + índice codebase (“no es suposición”).*
| método llamador | llamada → destino | en archivo | detalle / firma |
|---|---|---|---|
| [[21-engine]] | [[22-coordinator]] | coordinator.cpp | steps 1, 2, 3, 6, 12 |
| [[21-engine]] | [[23-mosquito-submodel]] | mosquito_submodel.cpp:466 | step 5 |
| [[21-engine]] | [[27-transmission]] | transmission.cpp | steps 7-10 |
| `step()` | `cells_per_side()` | wire.hpp (AOI) | cap divergence |
| `step()` | `K_MAX` | [[31-constantes]] | en cap y aggregate |

<!-- bc:auto:end -->





# 15 · Bucle diario — `Engine::step()` (el corazón)

**Rol.** Un día completo de simulación en orden fijo, con `wind guard` intermedio y divergence checks al final. Todo lo demás cuelga de esta función.

## Secuencia exacta (engine.cpp:537-597)

```mermaid
sequenceDiagram
  participant E as Engine::step()
  participant C as CoordinatorModel
  participant S as MosquitoSubmodel
  participant T as TransmissionModel
  participant CL as ClimateEngine

  E->>C: set_climate_day(day_index)
  C->>CL: cur_day_ = day_index
  E->>C: activate_patches()
  Note over C: water-balance M14<br/>pool_states_ · activación
  E->>C: to_dataframe()
  Note over C: arma vector<PatchState><br/>caché = patch_states_today()
  alt M7.6 wind activo (wind_field_ por null)
    E->>S: set_current_month(ymd.month)
    E->>S: set_current_hour(20) ← vuelo 8pm
    E->>S: set_current_day_index(day_index)
  end
  E->>S: sub_->advance_day(aoi_, patch_states_today())
  Note over S: 1. cohort_bank advance_day<br/>2. collect_emergence → SoA<br/>3. ciclo gonotrófico hembras<br/>4. adult_dispersal<br/>5. adult_mortality
  alt transmission_model_ && is_enabled()
    E->>C: aggregate_density(*sub_, K_MAX)
    E->>T: check_and_trigger_outbreak(day, density)
    opt outbreak && foci_log_path_
      E->>T: write_foci_log(path)
    end
    E->>T: advance_vector_eip(soa_mutable, climate, states, aoi)
    E->>T: advance_human_transmission(bite_ledger, aoi)
    E->>T: record_daily_stats(day, soa, bite_ledger)
  end
  E->>E: n<0 → throw · n>cap → warning
  E->>C: current_date() += 1 día
```

## Código al detalle

| Paso | Línea | Llamada | Por qué |
|---|---|---|---|
| 1 | 540 | `coord_->set_climate_day(day_index)` | hora cero del clima: `cur_day_` del ClimateEngine fija bandas del día |
| 2 | 542 | `coord_->activate_patches()` | charcos activan/desactivan por agua: `W[t+1]=max(0, W+rain−evap)` [[31-constantes]] |
| 3 | 544 | `coord_->to_dataframe()` | materializa `vector<PatchState>`: estado por parche + rain_7d_buffer |
| 4 | 550-555 | `sub_->set_current_month/hour/day_index` | solo si `wind_field_` no-null; hora 20h = inicio vuelo típico |
| 5 | 556 | `sub_->advance_day(aoi_, states)` | **las 5 fases del submodelo**, ver [[23-mosquito-submodel]] |
| 6 | 560 | `coord_->aggregate_density(*sub_, K_MAX)` | densidad actual → grilla (H,W) para detección de brote |
| 7 | 561 | `check_and_trigger_outbreak(...)` | si hot-spot denso → dispara foco SEIR |
| 8 | 568 | `advance_vector_eip(soa_mutable(), ...)` | EIP(GDD) de cada vector según temp del día |
| 9 | 569 | `advance_human_transmission(bite_ledger(), aoi_)` | bites del ledger → infección humana → human SEIR |
| 10 | 571 | `record_daily_stats(...)` | snapshot métricas del día (prevalencia, EIR) |
| 11 | 576-591 | divergence | `n<0` = throw; `n>cap` = warning (cap = celda² × K_MAX×10) |
| 12 | 595 | `coord_->current_date() += 1 día` | fecha se guarda en coordinator, no en Engine |

## Conexiones

| Desde | Llama a | En | Detalle |
|---|---|---|---|
| [[21-engine]] | [[22-coordinator]] | coordinator.cpp | steps 1, 2, 3, 6, 12 |
| [[21-engine]] | [[23-mosquito-submodel]] | mosquito_submodel.cpp:466 | step 5 |
| [[21-engine]] | [[27-transmission]] | transmission.cpp | steps 7-10 |
| `step()` | `cells_per_side()` | wire.hpp (AOI) | cap divergence |
| `step()` | `K_MAX` | [[31-constantes]] | en cap y aggregate |

## Orden no negociable

Emergencia → ciclo de sangre → oviposición → dispersión → muerte: si se invierte el orden, los conteos📇 de cohortes y de muertes cambian (el test de ciclo de vida lo asegura). Cualquier nueva fase se inserta **entre** 5 y 6 en `step()`, nunca dentro del submodelo.

up:: [[10-sistema]] · related:: [[23-mosquito-submodel]] · [[27-transmission]]