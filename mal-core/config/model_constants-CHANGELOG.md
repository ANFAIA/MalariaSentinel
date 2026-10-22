# Changelog — model_constants.yaml

Registro de los conflictos resueltos y decisiones de la migración de
constantes (plan `.opencode/plan/constants-yaml-plan.md` v1 + v2-doc).
Fecha: 2026-10-20 · agente 3.

## v1 — migración inicial (commits 34f90ac..89b3be8)

- **rain_scale_mm: 2.5** [mm/d] — conflicto py 1.0 / cpp 2.5 → **cpp gana**
  (el motor es la fuente canónica, §1.7).
- **activation_min / candidate floor: 0.01** — cpp 0.01 gana (py 1e-6 era
  otro rol: queda como `ingest.candidate_min_ingest`, roles separados).
- **host_seeking scale/radius: 300/1500** — la fila de especie
  (`species.<name>`) gana sobre la sombra wire 100/300; la sombra BORRADA
  (tests adaptados al canon; review-a3 P1-4 cerró el espejo restante en
  seeding).
- **k_ref: 50.0** [ind·km⁻²·d⁻¹] engine único. El 1.33e6 py muere como
  `K_REF_DAILY_PER_KM2` y RENACE en `habitat/capacity.py` como
  `K_REF_DIAG_PER_KM2` (otro concepto — capacidad diagnóstica py, sin
  conversión entre ellos, §9.1).
- **wetland_pluvial = 0.00** en TODAS las filas C++ pre-transformadas
  (columna muerta del enum; los consumos nombrados la leen por nombre).
- **geodesy.metres_per_deg_lat = 111195.08023353292** (π·R/180 exacto con
  R = 6371008.8; el borrador del plan decía 111194.9 — se adopta el exacto,
  el loader valida la relación metres_per_deg·180/π == earth_radius).
  Divergencia plan-borrador⇄YAML registrada aquí (review-a3 P2-6).
  dispersal.cpp tenía SU PROPIO 111320 (0.11% off) — unificado al exacto
  (review-a3 P1-5).
- **contract_version separada**: `contracts.env_nc = "3.0"` y
  `contracts.cogs_state = "4.0"` (frozen) — una clave cada uno.
- **rng: aquatic_seed_washout 789 · stage_mortality 42 · larva_mort 123**
  (los fixtures de test NO tocan el YAML).
- **num_persistent DERIVADO** del dynamics map (muere la regla 'los
  primeros 3' y kNumPersistent local).
- **Divergencia plan-borrador⇄código-real**: las duraciones de instar
  (ration em-leurs) y la filament fuente `adults` — el plan §2 y el código
  hoy — el YAML trae los literales del motor (review-a3 no marcó ninguna
  de esos contra-verifico).
- **+18 hojas melas/stephensi (v2 incorporadas en v1)**: el gap del
  registry de 6 ids se cerró YA en la migración (weights = fila neutral,
  salinity_hi_tol 38/20, host 300/1500) — decisión documentada aquí y en
  los comentarios del YAML (el plan v2 lo permitía "paso 6-7 del v1 o
  dejarlo a la v2").

## Habilitación

- `habitat/constants.py`: pasarela→tombstone (paso 2 shims → paso 8).
- Anti-hardcode: `tools/check_no_constants.sh` (0 hits; allowlists
  documentadas para el bloque v2-phase en species_params.cpp).
- Golden: `tests/golden/state_seed42_day5.*` (pre-migración 85d5537;
  seed 42, 5 días accra) — test 7 CLI-driven PASS.

## v2 (pasos 10-13) — APLICADOS (commit dfcbfc3)

- activity_weights [DAY, EVENING, NIGHT, DAWN] Σ=1 inline list (4 fases
  reales del código, NO 24 h; el encargo asumía 24 — corrección §0-1).
- pref {human,cattle,goat,sheep,wildlife} = HostType Σ=1, por NOMBRE.
- salinity_opt_ppt (0.0 hoy) + salinity_slope per-species (la misma
  formula opt/hi_tol/slope vive completa en el bloque).
- species_params.cpp: switch in-code BORRADO (v2 §… paso 12); body =
  lookup.
- version 1 → 2 (dual-read prohibido).
- melas/stephensi filas completas; weights = fila neutral (noop hasta
  activar la especie).
- Flaky resuelto: CoordinatorModel.CandidateFloorDropsEmptyCells y
  ClimateEngine.StaticBandsReachAccessor compartían un filename fixed
  en tmp entre PROCESOS ctest -j (nc_create 13/race) — filename único
  por pid (test_coordinator/test_climate/test_env_reader/test_habitat_engine).
