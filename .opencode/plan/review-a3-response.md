# review-a3-response — respuesta del agente 3 al review-a3-round0

Fecha: 2026-10-20 · Commits de la ronda: 89b3be8 → (ver tabla).

Veredicto del supervisor (הרשלergo de executor sólo los ítems P1/pendientes
del encargo; no se expande alcance):

| # | Ítem del review | SHA(s) | Notas |
|---|---|---|---|
| P1-1 | EGG/PUPA_DAILY_MORT → `aquatic_stages.egg/pupa_daily_mort` | `89b3be8` | accessors al singleton; constexpr muertos |
| P1-2 | instar≤2 literal → `vulnerable_instar_max` | `89b3be8` | campo renombrado `instar_max`→`vulnerable_instar_max` en `AquaticStressCfg` (+config_dump) |
| P1-3 | salinity-missing 0.0f → `salinity_missing_psu` | `89b3be8` | climate.cpp (2 sitios) + bank.cpp (1) + comentario bank:284 |
| P1-4 | seeding espejo 100.0f | `89b3be8` | slot de inyección queda en la struct (`-1.0f` sentinel), fallback borrado: seeding throws si engine no inyectó; comentario honesto |
| P1-5 | dispersal 111320 local | `89b3be8` | usa `geodesy.metres_per_deg_lat`; test_dispersal lee config; doc 111320 borrada (dispersalhpp:13-14, wire:230) |
| P1-6 | Golden test 7 | `89b3be8` | `test_config_engine_golden.cpp`: CLI-spawn del engine binario con la invocación frozen; fixtures de 85d5537 en `tests/golden/`; PASS pre-v2 y POST-v2 (dfcbfc3) |
| INFRA-7 | check_no_constants cobertura | `eed723f` | patrones 0.08f/0.05f/16/110/111320/-9999-py, límites de palabra; hits reales resueltos (indoor/urbanicity/nodata py) |
| Item 8 | PASO 9 (documentar) | `6e43388` | `habitat/README.md` (única fuente; calibración SOLO YAML; K_REF_DIAG ≠ k_ref) + `model_constants-CHANGELOG.md` (conflictos/divergencias/desición +18 hojas) |
| Item 9 | v2 pasos 10-13 | `dfcbfc3` | YAML v2 (version 2, filas verbatim del doc §1); schema py+C++; species_params_for = lookup puro (switch borrado); paridad + golden bit-identical; melas/stephensi completas (dormant) |
| Item 10 | Flaky CandidateFloorDropsEmptyCells | `86725f4` | CAUSA REAL: filename tmp fixed compartido entre PROCESOS ctest -j (gtest_discover_tests); fix filename por pid en 4 test files; 5x ctest -j8 estable (sólo 2 pre-existentes) |

No-resueltos: ninguno. Notas de responsabilidad parcial:
- P1-4: el CAMPO `host_seeking_scale_m` se conserva como slot de inyección
  obligatoria del engine (sin default compilado; `-1.0f` sentinel +
  throw en `build_seed_instructions` si falta) — el reviewer pedía
  borrar campo+fallback; el fallback está borrado, el campo es la
  interfaz de inyección (documentado en el hpp).
- arabiensis pref-echo del test coluzzii («mirror») etc.: fuera.

Suites de cierre de ronda: pytest mal-core+mal-commonlib
**308 passed, 6 skipped**; `ctest -j8 x5` estable **250/252** (las 2
gonotrophic PRE-existentes: DefaultValues,
SubsequentCycleEggMaturationTakesThreeDays); golden POST-v2
bit-identical; `tools/check_no_constants.sh` OK;
`bin/mal_abm_fast_darwin` actualizado tras cada paso que tocó el motor.
