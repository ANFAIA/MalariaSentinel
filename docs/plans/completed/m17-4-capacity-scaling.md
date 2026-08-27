# M17.4 — Capacity Scaling para Habitat Urbano Temporal

> **Estado**: ✅ Completado (2026-08-27).
> **Predecesor**: `M17` (Habitat urbano temporal, plan §6.3-6.6 en `plan-correccion-brote-y-hidrologia.md`).
> **Objetivo**: Conectar `urban_capacity_factor` (calculado en `PatchState` desde commit `6b75ddc`) al seed path y al aquatic cohort bank, de modo que la productividad vectorial por cell refleje la densidad de edificios del AOI.
>
> **Implementación**: 4 commits separados (PR-A, PR-B, PR-C, PR-D). Slowdown medido: 1.0421 (< 1.20 → PR-C aceptado sin §4.1 vectorisation). Detalles en `runs/perf/comparison.md`. PR-D (`D24_urban_productivity_ratio`) registrado en `thresholds.yaml` y `composite.py` con peso 0.05.

---

## 1. Motivación y Diagnóstico del Estado Actual

En el commit `6b75ddc` (M12-fix branch) se implementó la **regla de activación urbana** del plan §6.3:

```
urban_class == 30 AND building_fraction >= URBAN_B_MIN (0.05)
AND (rain >= URBAN_R_MIN_MM (12) OR rain_7d >= URBAN_R_MIN_MM)
AND twi >= URBAN_TWI_MIN (7)
```

Y se introdujo el factor `urban_capacity_factor` en `PatchState` como `clamp(building_fraction, 0.30, 1.00)` (plan §6.4).

### Problema

El factor se **calcula** correctamente y se **registra** en `PatchState`, pero **no se consume** en ningún punto del flujo de población:

```
Engine::step()
├── coord_->to_dataframe()              ← urban_capacity_factor ESCRITO ✓
├── sub_->seed_instructions()           ← USA k_per_patch_ GLOBAL ✗
├── sub_->advance_day()
│   ├── AquaticCohortBank::advance_day() ← USA K_MAX GLOBAL ✗
│   ├── collect_emergence()              ← USA K_MAX GLOBAL ✗
│   ├── GonotrophicCycle                 ← USA K_MAX GLOBAL ✗
│   └── adult_dispersal + mortality      ← USA K_MAX GLOBAL ✗
└── coord_->aggregate_density()          ← USA K_MAX GLOBAL ✗
```

**Consecuencia empírica**: en un AOI donde un suburbio con `building_fraction=0.3` y el centro de Accra con `building_fraction=1.0` reciben la misma lluvia, **ambos producen la misma densidad vectorial** porque ambos tienen `K_eff = K_MAX = 1000`. Esto es biológicamente falso.

### Impacto cuantitativo

Calibración actual con `building_fraction` ignorada:
- **Sobre-estimación** de productividad en cells urbanos de baja densidad (~3x para suburbios con `building_fraction < 0.33`)
- **Sub-estimación** del gradiente urbano-rural: la malaria simulada en zonas periurbanas se parece a la rural, cuando debería ser ~2x mayor
- **Calibration composite ciego**: 0 de 23 scorers distinguen urban vs rural, así que un regression pasa el PR gate sin disparar nada

---

## 2. Diseño: K_eff per-patch como array row-major pre-flatten

### 2.1 Pre-flatten en constructor (no en `to_dataframe()`)

**Insight crítico**: `building_fraction` y `urban_class` son **datos estáticos del AOI**, cargados una sola vez del `host_static.nc` en `Engine::Engine()` → `HostLandscape::load_from_nc()`. Nunca se mutan durante la simulación (verificado: 0 asignaciones a `c.building_fraction` o `c.urban_class` fuera de `load_from_nc:248,255`; `EffectiveHostLandscape` no los referencia).

Esto permite construir el array `K_eff_grid_` **una sola vez** en el constructor del `CoordinatorModel` (en lugar de rebuild cada día en `to_dataframe()`).

**Comparación de estrategias**:

| Cuándo | Frecuencia | Coste total (Ghana 60d) | Código |
|---|---|---|---|
| Cada `to_dataframe()` | 731 rebuilds × 26K cells = 19M ops | ~0.5s | Rebuild + invalidate |
| Una vez en constructor | 1 build × 429K cells | ~5ms | Inmutable, set-and-forget |
| **Delta** | — | **~100x más rápido** | **Más simple** |

### 2.2 Forma del array

`std::vector<float> K_eff_grid_` de tamaño `H*W`, row-major, indexable por `(r, c)`:

```cpp
const float K_eff = K_eff_grid_[r * W + c];  // O(1), sin hash
```

Cada elemento vale:
- `clamp(building_fraction, 0.30, 1.00)` si `urban_class == 30`
- `1.0` (terrain default) en cualquier otro caso

### 2.3 Propagación al cohort bank

`AquaticCohortBank` recibe el array como **const view** (ptr + dims) vía setter, no por step:

```cpp
// En Engine::Engine(), después de crear CoordinatorModel:
coord_->build_K_eff_grid();  // constructor-style init
sub_->set_K_eff_grid(coord_->K_eff_grid_view());  // once, never changes
```

El cohort bank almacena `const float* K_eff_grid_view_` + `int32_t W_` para indexar.

---

## 3. Tres Niveles de Implementación

### Nivel A — `SeedInstruction::urban_capacity_factor`

**Objetivo**: propagar el factor al momento del seed.

**Cambios**:
1. `SeedInstruction` (definido en `seeding.hpp`): añadir `float urban_capacity_factor = 1.0f;`
2. `CoordinatorModel::build_seed_instructions()`: setear el campo desde `PatchState.urban_capacity_factor`
3. **No consumir aún** (mantiene back-compat). Solo registrar.

**Tests**:
- `test_seeding.cpp::SeedInstructionCarriesUrbanFactor`: verificar que el campo se popula correctamente

**Coste**: despreciable (<0.1% CPU, +4 bytes/instruction)

### Nivel B — `MosquitoSubmodel::seed_instructions()` consume factor

**Objetivo**: limitar el seed de adultos por `K_eff` per-patch.

**Cambios**:
1. En `mosquito_submodel.cpp` línea ~324 (`n_adults_capped`), reemplazar `min(n_adults, K_MAX)` por `min(n_adults, K_MAX * inst.urban_capacity_factor)`
2. **No propagar al cohort bank** aún. El seed inicial respeta el factor; el crecimiento posterior (Nivel C) lo hará.

**Tests**:
- `test_seeding.cpp::UrbanSeedCappedByK_eff`: con `factor=0.3`, el seed debe ser ~30% del seed con `factor=1.0`
- `test_seeding.cpp::TerrainSeedUsesK_MAX`: con `factor=1.0`, comportamiento idéntico al actual

**Coste**: <0.1% CPU, 0 memoria extra

### Nivel C — `AquaticCohortBank` per-patch K_eff (PRINCIPAL)

**Objetivo**: la Beverton-Holt density-dependence respeta `K_eff` per-patch.

**Cambios**:
1. `coordinator.hpp`: añadir `std::vector<float> K_eff_grid_` + método `build_K_eff_grid()`
2. `coordinator.cpp`: implementar `build_K_eff_grid()` (constructor-time, una vez)
3. `coordinator.hpp`: añadir `K_eff_grid_view()` que devuelve `std::pair<const float*, int32_t>` (ptr + W)
4. `aquatic_cohort_bank.hpp`: añadir `const float* K_eff_grid_view_ = nullptr; int32_t K_eff_W_ = 0;` + setter
5. `aquatic_cohort_bank.cpp`: en el loop Beverton-Holt, reemplazar el literal `K_MAX` por `K_eff_grid_view_[r * K_eff_W_ + c]` (con fallback a `K_MAX` si el view es null)
6. `engine.cpp`: llamar `coord_->build_K_eff_grid()` después del `set_host_landscape()`; pasar el view al submodel

**Pre-condición crítica**: `build_K_eff_grid()` debe llamarse **después** de `set_host_landscape()`. Si el host es null, el grid se llena de 1.0s (terrain default everywhere).

**Tests**:
- `test_coordinator.cpp::K_eff_grid_static_after_load`: verificar que el grid se construye una vez y no cambia entre steps
- `test_aquatic_cohort_bank.cpp::BevertonHoltUsesK_eff`: con `K_eff=0.3`, density-dependence es ~3x más fuerte que con `K_eff=1.0` (mismo input, menos supervivientes)
- `test_e2e.cpp::UrbanUnderCapacity`: ABM con AOI sintético 2x2 (1 urban + 1 rural) → final density urban < rural con misma lluvia

**Coste esperado**:
- Memoria: +200 KB (`429K cells × 4 bytes + overhead`)
- CPU: lookup O(1) por cohort, vs unordered_map O(1) promedio pero con peor constant factor. En Ghana 56M cohorts × 60 días, estimado **+5-15% del runtime total** del aquatic loop (no 600% como en mi estimación previa, porque el lookup array es comparable al constant-factor de un map pequeño, pero más cache-friendly)

---

## 4. Estimación de Rendimiento

### Baseline medido (Ghana 30 días, --threads 1)

| Loop | Coste |
|---|---|
| `to_dataframe()` | ~0.5s |
| Aquatic cohort advance | ~10s |
| Adult dispersal + mortality | ~5s |
| Gonotrophic cycle | ~3s |
| Aggregate density + write | ~1s |
| **Total** | **~30s** |

### Con Niveles A+B+C aplicados

| Loop | Cambio |
|---|---|
| `to_dataframe()` | igual (build_K_eff_grid ya se hizo en constructor) |
| Aquatic cohort advance | **+5-15%** (~10s → 11-12s) por lookup array vs literal |
| Adult dispersal + mortality | igual |
| Gonotrophic cycle | igual (no usa K_eff aquí) |
| Aggregate density | igual (usa K_MAX global, no se cambia) |
| **Total** | **~33-35s** |

**Aceleración del aquatic loop**: si antes se usaba `unordered_map` (~50ns lookup), el array row-major (~5ns) da **~10x speedup en lookup**, pero el loop está dominado por otras ops (Briere-1 thermal dev, density calc), así que el speedup global es modesto.

**Decisión**: el coste es aceptable. La métrica que importa es **corrección biológica** (urban < rural productivity), no performance.

### Validación empírica esperada (Ghana, 30 días)

| Métrica | Sin capacity scaling | Con capacity scaling |
|---|---|---|
| Total aquatic (rural cells) | ~50M | ~50M (igual) |
| Total aquatic (urban cells) | ~6M (igual que rural) | ~2M (~30% de rural) |
| Densidad media rural | uniforme | uniforme |
| Densidad media urban | uniforme (sobre-estimada) | **menor** (refleja buildings) |
| Ratio urban/rural productivity | ~1.0 (biológicamente falso) | **~0.4-0.6** (biológicamente plausible) |

### 4.1 Optimización opcional: vectorización del aquatic loop

**Cuándo aplicar**: solo si la métrica M4.2 (siguiente sección) muestra slowdown significativo.

**Qué es**: reorganizar el `AquaticCohortBank::advance_day()` para procesar cohorts **agrupados por `patch_id`** en lugar de recorrer el SoA plano. Cada grupo se procesa en bloque: lookup `K_eff` una vez, aplicar Beverton-Holt a todo el grupo con la misma `K_eff`, escribir resultados.

**Por qué funciona**: el lookup de `K_eff` y el cálculo de density-dependence tienen localidad espacial fuerte — todos los cohorts de un patch comparten la misma `K_eff`. La versión actual recorre el SoA plano (orden de inserción = orden de promoción), lo que cache-miss en cada lookup de `K_eff`.

**Estimación**:
- Coste de implementación: 1-2 días (refactor cuidadoso del SoA → grouped layout, o pre-sort por patch_id)
- Aceleración esperada: **~20x** en el aquatic loop (de ~12s a ~0.6s para Ghana 60 días)
- Resultado neto: ABM completo más rápido que el baseline (porque la agrupación elimina también misses en otros SoA lookups)

**Trade-off**: complica el código del cohort bank (inserción en grupo, promoción entre grupos). Solo vale si el slowdown de Nivel C lo justifica.

#### 4.2 Métrica de decisión (cuándo aplicar la optimización)

**Procedimiento empírico obligatorio** al final del PR-C (antes de mergear):

1. Compilar binario **sin** Nivel C (commit `6b75ddc` o revertir el cambio de lookup temporalmente)
2. Compilar binario **con** Nivel C (branch actual post-PR-C)
3. Ejecutar **idéntica** configuración en ambos:
   ```
   ./build/src/mal_abm_fast run \
     --aoi ghana --year 2024 --month 6 \
     --seed 1 --days 30 \
     --env data/ghana/ghana_regional_2024_2025_env.nc \
     --habitat data/ghana/ghana_habitat_patches.gpkg \
     --hosts data/ghana/ghana_host_static.nc \
     --output /tmp/baseline_state.tif \
     --seeding-mode uniform --threads 1
   ```
4. Medir wall-clock time con `time` (3 runs cada uno, tomar mediana)
5. Calcular slowdown: `slowdown = t_con_Nivel_C / t_sin_Nivel_C`

**Umbral de decisión**:

| Slowdown medido | Acción |
|---|---|
| `< 1.20` (≤20%) | **Aceptar PR-C sin optimizar**. Documentar métrica en commit message. |
| `>= 1.20` (≥20%) | **Bloquear merge de PR-C**. Aplicar vectorización (§4.1) antes de aceptar. PR-C se reabre como PR-C+vec. |

**Justificación del umbral 1.20**: coincide con el límite informal de "slowdown aceptable para un fix de correctness biológica" en este proyecto (validado en commits previos de la rama M12). A partir de aquí, la nueva abstracción tiene un coste desproporcionado al beneficio y/o empieza a afectar el throughput de CI (calibration tier `full` corre ~10 rollouts de 90 días) y bloquea experimentación interactiva. La optimización pasa de opcional a **mandatoria**.

**Outputs del procedimiento** (commitear junto con PR-C):
- `runs/perf/baseline_30d.txt` — wall-clock sin Nivel C
- `runs/perf/nivel_c_30d.txt` — wall-clock con Nivel C
- `runs/perf/comparison.md` — tabla con slowdown calculado y veredicto

Si `comparison.md` reporta slowdown ≥1.20, el PR-C se reabre como PR-C+vec con la optimización aplicada y los nuevos `comparison.md`.

---

## 5. Riesgos y Mitigaciones

### 5.1 Orden de inicialización

**Riesgo**: si `build_K_eff_grid()` se llama antes de `set_host_landscape()`, el grid queda lleno de 1.0s y nunca se actualiza.

**Mitigación**: validar en `build_K_eff_grid()` que `host_landscape_ != nullptr` y throw `std::runtime_error` si no. Engine garantiza el orden en su constructor.

### 5.2 Hot-reload de host durante simulación

**Riesgo**: si en el futuro se permite recargar `host_landscape_` durante una ejecución (hoy no es un feature), el `K_eff_grid_` queda stale.

**Mitigación**: añadir `K_eff_grid_version_` que se incrementa cada vez que `host_landscape_` cambia. `AquaticCohortBank` valida que las versiones coincidan antes de cada step. Por ahora, solo documentar la limitación.

### 5.3 Cambio de AOI mid-run

**Riesgo**: si el Engine cambia de AOI (cambio de bbox), el `K_eff_grid_` tiene dims equivocadas.

**Mitigación**: hoy el Engine no soporta multi-AOI mid-run. Si se añade, el constructor del CoordinatorModel se llama de nuevo → grid se reconstruye.

### 5.4 Tests existentes rompen por cambio de contrato

**Riesgo**: tests que mockean `AquaticCohortBank` o `CoordinatorModel` pueden romperse si se cambia la firma del setter.

**Mitigación**: el setter `set_K_eff_grid(ptr, W)` es aditivo. Tests que no lo llamen obtienen el comportamiento por defecto (`K_eff=1.0` everywhere, equivalente a `K_MAX` global). Back-compat preservada.

### 5.5 Calibration composite no detecta regressions

**Riesgo**: si alguien rompe la lógica de `K_eff` (e.g., grid siempre=1.0), el composite (D1-D23) no lo detecta porque ningún scorer mira urban-vs-rural productivity.

**Mitigación**: nuevo scorer `D24_urban_productivity_ratio` que mide la densidad vectorial media en cells con `urban_class==30` vs cells con `urban_class==50`. Comportamiento esperado: ratio < 1.0 si el capacity scaling funciona, ~1.0 si está roto. Se añade al `composite.py::DEFAULT_WEIGHTS` con peso bajo (0.05) para no perturbar el scorecard existente.

---

## 6. Plan de Commits

### PR-A: solo propagación del factor (~30 min)

```
abm: propagate urban_capacity_factor through SeedInstruction

Plan §6.4 step 1: register the per-patch factor in SeedInstruction.
No behavioral change — the submodel still uses k_per_patch_ global.
The factor is now available for downstream consumers (PR-B/C).

Files:
- seeding.hpp           +4 lines (field)
- coordinator.cpp       +3 lines (set in build_seed_instructions)
- test_seeding.cpp      +30 lines (test)

Tests: 1 new, 238 existing pass.
```

### PR-B: submodel consume factor (~1 h)

```
abm: cap adult seed by urban_capacity_factor

Plan §6.4 step 2: replace min(n_adults, K_MAX) with
min(n_adults, K_MAX * urban_capacity_factor) in seed_instructions.

Files:
- mosquito_submodel.cpp +2/-1 lines (capping change)
- test_seeding.cpp      +60 lines (2 tests)

Tests: 2 new, 238 existing pass.
```

### PR-C: per-patch K_eff en aquatic cohort bank (~4 h, PRINCIPAL)

```
abm: per-patch K_eff from urban buildings in cohort bank

Plan §6.4 step 3: pre-flatten building_fraction to a row-major
K_eff_grid in CoordinatorModel constructor (one-time, O(H*W)).
AquaticCohortBank reads K_eff via const view, replacing the
global K_MAX literal in Beverton-Holt density-dependence.

Files:
- coordinator.hpp           +6 lines (grid + view)
- coordinator.cpp           +25 lines (build_K_eff_grid)
- aquatic_cohort_bank.hpp   +8 lines (setter + view fields)
- aquatic_cohort_bank.cpp   +5/-2 lines (lookup change)
- engine.cpp                +4 lines (wiring)
- test_coordinator.cpp      +15 lines (test)
- test_aquatic_cohort_bank.cpp +30 lines (test)
- test_e2e.cpp              +50 lines (e2e test)

Tests: 3 new, 238 existing pass. ABM Ghana 30d: +5-15% runtime
in aquatic loop, total +10-15% in ~30s baseline.

Calibration:
- D24_urban_productivity_ratio.py (new scorer, weight 0.05)
```

### PR-D: calibration scorer (~1 h)

```
calibration: D24 urban-vs-rural productivity ratio

Detects regressions in urban capacity scaling. Compares mean
adult vector density in urban cells (urban_class==30) vs rural
cells (urban_class==50). Score 1.0 if ratio < 0.7 (urban
correctly under-capacity); 0.0 if ratio > 0.95 (scaling broken).

Files:
- scorers/D24_urban_productivity_ratio.py (new, ~80 lines)
- scorers/composite.py (add weight 0.05)
- thresholds.yaml (register D24)
```

---

## 7. Criterios de Aceptación

### Por nivel

**Nivel A**: el campo `urban_capacity_factor` aparece en `SeedInstruction` después del seed. Test pasa. Sin cambio de comportamiento poblacional.

**Nivel B**: con `factor=0.3`, el seed de adultos en urban cells es exactamente 30% del seed con `factor=1.0`. Test pasa.

**Nivel C**:
1. El `K_eff_grid_` se construye una vez en el constructor y no cambia entre steps (verificable con assertion en test)
2. Con `factor=0.3`, la Beverton-Holt density-dependence es más fuerte (mismo input → menos supervivientes)
3. E2E: en AOI sintético 2x2, urban cells tienen menos densidad vectorial final que rural cells con misma lluvia
4. ABM Ghana 30 días corre sin crash, output poblacional cambia (urban < rural donde antes eran iguales)

### Validación práctica (siguiendo la convención de M12)

- ABM Ghana 30 días, `--seeding-mode uniform`, `--threads 4`
- Comparar output con/sin Niveles A+B+C
- Métrica clave: `urban_density / rural_density` ratio
- Esperado pre-C: ~1.0 (biológicamente falso)
- Esperado post-C: ~0.4-0.6 (biológicamente plausible)

---

## 8. Trabajo NO Incluido (debt explícito)

1. **Capacity scaling en GonotrophicCycle**: el `# biting per host per day` se modela con probabilidad, no con `K_eff`. No se toca aquí.
2. **Capacity scaling en `collect_emergence`**: las pupas que emergen a adultos usan `K_MAX` global. Cambiarlo es más invasivo (afecta la cohorte adulta directamente, no las larvas). Pendiente para revisión post-C.
3. **Capacity scaling en `aggregate_density`**: el bin count de adultos por patch se normaliza por `K_MAX` global. Si per-patch `K_eff` debe afectar la "saturación" visual del COG, hay que cambiar `aggregate_density` también. Pendiente.
4. **Refactor de `K_MAX` global a per-AOI constant**: hoy `K_MAX` está en `wire.hpp` como `constexpr`. Si cada AOI tuviera su propio `K_MAX` (basado en datos entomológicos locales), el capacity scaling sería aún más expresivo. Out of scope.
5. **Multi-AOI mid-run**: hoy un Engine = un AOI. Si se permite cambiar AOI, hay que re-llamar `build_K_eff_grid()` en cada switch. Out of scope.

---

## 9. Referencias

- `plan-correccion-brote-y-hidrologia.md` §6.3-6.6 (regla urbana y density cap)
- `wire.hpp:163-179` (URBAN_* constants)
- `coordinator.cpp:139-148` (current `is_permanent` y urban-rule logic)
- `coordinator.cpp:280-285` (current `urban_capacity_factor` calculation in PatchState)
- `aquatic_cohort_bank.cpp` (Beverton-Holt density-dependence loop, donde se aplicará Nivel C)
- `host_landscape.cpp:248,255` (única fuente de `building_fraction` y `urban_class`, confirmación de estáticidad)
- Commit `6b75ddc` (M12-fix branch, introdujo `urban_capacity_factor` como campo decorativo)
- Calibration framework: `mal-core/src/mal_core/abm/tests/calibration/scorers/`

---

## 10. Orden de Ejecución Recomendado

1. **PR-A**: propagación del campo (~30 min). Riesgo cero. Back-compat total.
2. **PR-B**: consumo en seed (~1 h). Cambio de comportamiento limitado al seed inicial; el crecimiento posterior lo dominará.
3. **PR-C**: pre-flatten + aquatic loop (~4 h). Cambio principal. Requiere profiler run.
4. **PR-D**: calibration scorer (~1 h). Detecta futuras regressions.

**Total**: ~6-7 horas de trabajo, repartidas en 4 PRs pequeños y revisables.

**Decisión de optimización**: el procedimiento empírico de §4.2 (medir slowdown binario con/sin Nivel C en Ghana 30d) decide si PR-C se acepta directo (slowdown <1.20x) o se bloquea hasta aplicar la vectorización de §4.1 (slowdown >=1.20x). Outputs `runs/perf/comparison.md` se commitean junto con PR-C.
