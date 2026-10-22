# Retirar K_MAX: capacidad, inicialización y observación independientes

Estado: **ejecutado el 2026-10-20** (aprobado en sesión; compilación y ctest verificados,
3 fallos pre-existentes documentados permanecen). Contrato de salida de estado `4.0`.
Base previa: `8ec9e85` (contrato ambiental 3.0 intacto — este cambio no lo toca).

## Objetivo cumplido

`K_MAX=1000` y sus acoplamientos eliminados sin renombrarlo globalmente a `K_ref=50`.
Cuatro conceptos separados:

| Concepto | Fuente | Unidad |
|---|---|---|
| Capacidad acuática diaria | `PatchState.k_habitat` (coordinador: `K_ref × área_km² × S`) | larvas efectivas |
| Población inicial | conteos explícitos adultos/inmaduros | individuos |
| Estado observado | conteos por celda crudos | adultos/celda |
| Protección operativa | `--max-population` | agentes adultos |

## 1. Banco acuático (`aquatic_cohort_bank.{hpp,cpp}`)

- Retiradas: rama K_eff (vista M17.4 muerta desde 84ad0d8), setter/getters/campos
  `K_eff_*`, y el fallback global `K_MAX` en `larva_mortality_density`. Ninguna
  llamada activa a `set_K_eff_view` existía (verificado por búsqueda).
- Contrato: `K>0` → Beverton-Holt actual; `K==0` → p=0 (todas las larvas del patch
  mueren ese día; no toca pupas/huevos); `K<0/NaN/+inf` o patch sin estado →
  `std::runtime_error` identificando el patch. `α` validado finito y ≥0.
  `patch_to_cell` se conserva (emergencia necesita coordenadas).
- Biología nueva explícita: los patches secos ya no reciben capacidad fantasma
  1000 — antes el fallback convertía "sequía" en "supercriadero".

## 2. Inicialización (`seeding.{hpp,cpp}`, `coordinator.{hpp,cpp}`,
`mosquito_submodel.{hpp,cpp}`, `engine.{hpp,cpp}`, `main.cpp`)

- `SeedingConfig`: `init_frac` → `n_adults_per_patch=30` +
  `n_immatures_per_patch=270` (30/270 reproduce el mix histórico 0.30×1000:
  10% adultos / 90% inmaduros).
- `build_uniform_seed_instructions(n_adults, n_immatures)`: conteos directos.
- Constructor round-robin con conteos explícitos `(n_patches, n_adults, n_immatures,
  seed)` reemplaza al path `k_per_patch × init_frac` (staggering de huevos idéntico:
  5 cohortes dev 0.00–0.80).
- Constructor detection-based: única vía para instrucciones; **cap adulto
  `k_per_patch × urban_capacity_factor` eliminado** (los conteos seed verbatim).
  Miembro `k_per_patch_` y campo `SeedInstruction.urban_capacity_factor` retirados.
- `--init-frac` eliminado (C++ + cli.py, ambos flujos `abm` y `validate-cases`);
  nuevos flags `--seed-adults-per-patch` / `--seed-immatures-per-patch`
  (pasan a través de `run_abm_from_manifest` kwargs→`--seed-...`).
- Engine UNIFORM sin candidate patches → población vacía + log (antes usaba el
  ctor legacy round-robin).
- No se limita el seeding adulto con `K_ref`: unidades distintas (memoria: K_ref
  es larvas efectivas/km² a índice 1, no techo adulto).

## 3. Salidas y outbreak (contrato de estado v4.0)

- `aggregate_density` / `suitability_grid`: sin divisor ni clamp — conteos crudos.
  Nombres de banda `{"adult_occupancy","host_seeking_pressure"} →
  {"adult_patch_count","adult_cell_count"}` (wire.hpp). Bandas: adultos asociados
  a patch (post-dispersal) y adultos por posición actual.
- Sidecar: clave `k_max` eliminada (`StateCogMetadata` + writer + tests).
  `CONTRACT_VERSION` "3.0" → "4.0" (solo la de salida de estado; el env NC
  mantiene "3.0").
- `docs/specs/abm/spec.md` actualizado: INV-2/3/9/12/15 + snippet reader +
  política de versión.
- Outbreak: la grilla que entra a `check_and_trigger_outbreak` ahora son conteos
  absolutos. El umbral `--human-outbreak-min-density` pasa a adultos/celda
  (0.5 antiguo ≙ 500). Ayuda de CLI (C++ y Python) actualizada.
- G6 (`scoring/scorers/gates.py`): ahora exige finito y ≥0 (ya no [0,1]).
- Surrogate/predicción: nombres de canales → `predicted_adult_patch_count` /
  `predicted_adult_cell_count`; thresholds Dice/presencia a unidades de conteo
  (0.5 adultos). **Los checkpoints v≤3.0 no son re-usables sin re-entrenar** —
  las bandas cambiaron de escala sin transformación guardada.
- Coordenadas de visualización (individuos/km²): se derivan con área de celda
  explícita — nunca dividiendo adultos por K(t) (adultos existen donde K=0).

## 4. Protección operativa

- `engine.cpp step()`: fuera el umbral `n_celdas × K_MAX × 10` (era solo warning).
  `--max-population`: 0 = desactivado; positivo = `std::runtime_error` si el total
  de adultos lo supera. Comentarios de engine.hpp/main.cpp alineados.
- `mal-commonlib/config.py`: `K_MAX`, `SimParams.k_max`, `PARAM_RANGES["k_max"]`
  eliminados (sin consumidores). `PRESENCE_THRESH` 0.05 → 0.5 (conteos).

## 5. Verificación (2026-10-20)

- `malariasim abm --compile` OK → binario copiado a `bin/mal_abm_fast_darwin`
  (regla #96/#28 cumplida: copia automática por la herramienta de compilación).
- `ctest`: **240/243**. Los 3 fallos son los pre-existentes documentados
  (`GonotrophicParams.DefaultValues` y `SubsequentCycleEggMaturationTakesThreeDays`
  — resting_duration_days 1.0 vs 0.5 histórico —, `Species.ColuzziiDefaultsAreAnthropophilic`
  — constantes de especie de sesiones anteriores). Ninguno toca código modificado hoy.
- Python: `test_feedback.py` (gates) y `test_abm_wrapper.py` pasan.
- Criterio textual: cero referencias operativas a `K_MAX`, `k_max`, `K_eff_*`,
  `k_per_patch_`, `urban_capacity_factor`, `--init-frac` en mal-core/mal-commonlib/
  mal-execution (solo comentarios históricos de retiro).

## 6. Devastación de tests y ajustes de fixtures

- Fábricas de `PatchState` en `test_lifecycle/test_gonotrophic/
  test_mosquito_submodel` ahora fijan `k_habitat=1000.0f` — con el contrato nuevo,
  K=0 mataría todas las larvas el primer día y rompería silenciosamente expectativas
  de ciclo/campo. Números idénticos al comportamiento antiguo efectivo.
- `test_coordinator`: instrucciones explícitas 30/270; agregaciones sin argumento
  K_MAX. `test_state_cog`/`test_engine`: `k_max` fuera del sidecar + assertion de
  ausencia. `test_seeding`: ctor sin K_MAX.

## 7. Pendiente / fuera de alcance

- Calibración de `K_ref=50`: sigue sin validar contra datos de campo (plan 02 §7).
- Smoke del contrato v3.0 con datos reales Ghana: sigue pendiente (manifest sin
  `era5_air_temp_daily`/`jrc_habitat_features`/`dw_class_fractions` resueltos).
- Re-entrenamiento del surrogate U-Net contra salidas v4.0 si se pretende usarlo.
- Área de celda en borde de AOI: la fórmula actual usa `res²·cos(lat)` sin
  intersección exacta de borde (extensión de plan 02 §8, no asumida aquí).
