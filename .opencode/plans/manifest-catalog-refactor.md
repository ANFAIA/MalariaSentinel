# Plan: Catálogo de datasets — identidad única vía manifest (2026-10-04)

Estado: **aprobado por usuario** (4 decisiones respondidas). Pendiente de desbloqueo de edición para ejecución.

## Objetivo

Eliminar TODA duplicación de identidad/nombres de datasets: las claves viven SOLO en los loaders (`DOWNLOADER.manifest_keys`, ya existente) y en UNA tabla nueva de artefactos de ingest. Los consumidores declaran dependencias (`Slot(key, required, per_year)`) y resuelven TODO vía catálogo. `manifest.json` = única fuente de verdad, estricto (sin fallbacks convencionales en consumidores).

## Decisiones (usuario, 2026-10-04)

1. **Puro manifest** + `register_existing()` para dirs legacy. Sin globs en consumidores.
2. **wrapper.py incluido** (convergencia del reader ABM al catálogo).
3. **CLI `malariasim datasets`** (tabla loaders↔manifest↔disco).
4. **Un solo commit**, verificado como conjunto — incluyendo un run ABM Ghana corto que demuestre que la cadena C++ importa todo vía las nuevas funcionalidades.

## Evidencia (claves reales verificadas hoy)

- Loaders (ya declaran output→manifest_key): `era5:{temp_suitability→era5_temp, water_temp→era5_water_temp, wind_6hourly→wind}`, `chirps:{rainfall_daily→chirps_rainfall_daily}`, `dem:{elevation→dem}`, `jrc_gsw:{water_occurrence→jrc_water}`, `modis:{ndvi→modis_ndvi}`, `coastline:{land_mask→coastline_land_mask}`, `smap:{salinity→smap_salinity}`, `worldpop→worldpop`, `glw→glw_*`, `ghsl→ghsl_urban`, `buildings→buildings`, `wildlife→wildlife_proxy`, `hydrorivers:{permanent_rivers→hydrorivers_rivers}`; NO registrados en LOADER_MODULES: worldcover (`worldcover_water`/`worldcover_wetland`/`worldcover_lc`/`worldcover_mangrove`), _legacy hydrolakes (`hydrolakes_lakes`).
- Artefactos ingest (strings hoy dispersos en productores): `env` (env.py:144), `habitat` (env.py:264), `host_static` (hosts.py:211), `host_manifest` (hosts.py:229), `mobility_day/night` + `livestock_mobility` (mobility.py:146-158), `mobility_manifest` (mobility.py:158). Mismos strings re-tipeados como consumidores en wrapper.py:129-156, cli.py, visualize_mobility.py.
- Naming convencional: SOLO en `runner.py:34-50` (4 helpers), elección data-driven por `spec.formats[output]` — reutilizable por `register_existing`.
- Manifest ghana real: contiene TODOS los inputs de daily_nc (verificado con resolve_daily_env_inputs: 10/10 slots manifest=True, 731 días, rasters 779×551 finitos).
- Bug del enfoque actual que este plan corrige: claves adivinadas por consumidores (`permanent_lakes`≠`hydrolakes_lakes`, `permanent_rivers`≠`hydrorivers_rivers`); con catálogo derivado del registry esa clase de error es estructuralmente imposible.

## Cambios por archivo

### 1. NUEVO `mal-core/src/mal_core/download/catalog.py` (~330 líneas)
- `INGEST_ARTIFACTS: dict[str, IngestArtifact]` — LA única tabla nueva (key, producer, required_for_abm).
- `Slot(key, required=True, per_year=False)` — declaración de dependencias de consumidores.
- `load_local_manifest(data_dir)` — datasets block de `data_dir/manifest.json` (móvil a tmp sandboxes).
- `resolve(aoi, key, year?, data_dir?, data_root?, manifest?)` — envuelve `resolve_dataset_file` (ya implementado + 7 tests): estricto en declarado-pero-faltante y en per-year-faltante; `None` si no hay entrada.
- `resolve_inputs(aoi, slots, data_dir?, years?, explicit?)` — API "declaro y listo": required-ausente→`FileNotFoundError` con hint; opcional-ausente→`None`; per_year→`dict[year, Path]` (años pedidos o claves numéricas del entry); entry single-file cubre todos los años (preserva semántica fallback original, pero vía manifest).
- `downloadable_datasets()` — aplana registry (CERO tablas nuevas).
- `catalog_status(aoi)` — filas kind/key/source/in_manifest/on_disk/path para todos los loaders + artefactos → backing de `malariasim datasets`.
- `register_existing(aoi, data_dir?, dry_run?)` — migración one-shot: deriva nombres convencionales de `spec.formats` + helpers runner (única convivencia futura con nombres convencionales), registra descargables (annual-tif por año, daily/monthly_nc con period por regex, static-tif) + artefactos ingest (patterns espejo de lo que escriben los builders); nunca sobreescribe; devuelve resumen {registered, skipped, missing}.
- Exportar en `download/__init__.py`.

### 2. `mal-core/src/mal_core/ingest/daily_nc.py` — reescritura de resolución
- NUEVA tabla única `ENV_INPUT_SLOTS` (la ÚNICA declaración del consumidor):
  - required: `rainfall→chirps_rainfall_daily`, `water_frac→jrc_water`, `water_temp→era5_water_temp(per_year)`, `ndvi→modis_ndvi(per_year)`.
  - opcionales: `dem→dem`, `land_mask→coastline_land_mask`, `host_static→host_static`, `salinity→smap_salinity`, M12: `permanent_lakes→hydrolakes_lakes`, `permanent_rivers→hydrorivers_rivers`, `worldcover_permanent_water→worldcover_water`, `worldcover_wetland→worldcover_wetland` (claves CORREGIDAS a las reales).
- `build_daily_env_nc` + `resolve_daily_env_inputs` ambos consumen esa tabla vía `resolve_inputs` (explicits del signature siguen ganando, validados existencia).
- BORRAR: globals muertos `REQUIRED_DATASETS`/`OPTIONAL_DATASETS`/`M12_OPTIONAL_KEYS`, `_discover_path`, `_resolve_entry_year`, `_read_local_manifest`, `_find_chirps_daily`, `_find_salinity_monthly`, TODOS los patterns convencionales, regex deduce-año para nombres (queda solo para el attr del NC si aplica).
- Semántica preservada: opcional-ausente → warning/skip (dem→no twi, host_static→sin urban, salinity→sin var, M12→JRC-only); per-year single-entry cubre todos los años; coastline se resuelve UNA vez (dedupe del parche actual).
- `resolve_daily_env_inputs` queda como la función reducida de verificación (sin build), reportando path+source por slot y per-year.

### 3. Productores usan constantes (fin de strings dispersos)
- `env.py:144` → `INGEST_ARTIFACTS["env"].key`; `env.py:264` → `["habitat"]`; `hosts.py:211/229` → `host_static`/`host_manifest`; `mobility.py:140-160` → las 4 claves del dict → iterar `INGEST_ARTIFACTS` filtrando producer mobility.
- `env.py` resolución de inputs (dem/jrc/coastline de mi parche actual) → `resolve_inputs` con slots, eliminando el helper `_find` local.

### 4. Consumidores convergen al catálogo
- `abm/wrapper.py run_abm_from_manifest` (L119-156): scan manual → `resolve(aoi, INGEST_ARTIFACTS.key, data_dir)` para env/habitat (required: None→raise con mensaje actual), host_static/wind/mobility_day/night/livestock (opcional→None tolerado, flags omitidos como hoy). −30 líneas. `validate_completeness` se mantiene.
- `cli.py _ensure_env_stack` (mi parche) → `resolve(aoi, "env", year=y_min, data_dir)`.
- `cli.py _ensure_abm_inputs` (L687+): hosts/habitat → constantes + resolve.
- `visualize_mobility.py` (mi parche `_resolve` local) → `resolve` catálogo; csr ausentes → error explícito claro (antes crash dentro de read_csr).

### 5. CLI nuevo `malariasim datasets --aoi ghana`
- `@app.command("datasets")`: imprime `catalog_status` — tabla kind/key/source/manifest/disk/file (~30 líneas).

### 6. Tests
- `test_m12_integration.py` (6 tests, 32 escrituras) y `test_smap.py` (2 tests, 9): helper `_write_manifest(tmp_path, {key: fname|{year: fname}})` — cada test registra lo que escribe; nombres de archivos SIN CAMBIO (registrados → prueban que el manifest manda aunque el nombre sea el convencional). Cobertura JRC-only, coast filter on/off (COASTLINE_BUFFER_M negativo), salinity broadcast, no-salinity backward-compat.
- NUEVO `test_catalog.py`: `catalog_status` sobre dir sintético; `resolve_inputs` required-missing→raise, optional-missing→None, per_year strict; `register_existing` sobre dir pre-manifest sintético (crea convencionales → assert manifest escrito, dry_run no toca).
- `test_manifest.py`: se queda íntegro (7 tests del resolver ya verdes).
- `test_runner.py` (wrapper): revisar fixture — si escribe manifest propio se mantiene; si construía paths convencionales SIN manifest, se le añade `_write_manifest`.
- `test_download_profiles_match_current_abm_contract`: fallo pre-existing (era5 wind_6hourly), fuera de alcance, se documenta en el commit.

### 7. Docs (mínimo)
- `docs/specs/data/spec.md` §6.3: párrafo — "consumidores resuelven inputs vía `mal_core.download.catalog.resolve_inputs`; identidad = manifest key; dirs pre-manifest → `register_existing`". AGENTS.md no cambia (la regla ya está escrita; ahora se cumple).

## Verificación (requisito del usuario: conjunto bien testeado)

1. `uv run pytest mal-core/tests -q` → 74+ verdes, SOLO los 5 fallos pre-existing (4 feedback + 1 profiles contract).
2. `resolve_daily_env_inputs("ghana")` → 10/10 slots `manifest=True`, per-year {2024,2025} correctos.
3. `catalog_status("ghana")` → tabla sana: jrc_water ✓, env/habitat/host_static/mobility ✓, hydrorivers_rivers declarado-loader-pero-no-descargado ✗ (correcto), worldcover ausente del registry (gap conocido, visible como no-listado).
4. **ABM Ghana end-to-end** (la prueba que pediste): `uv run malariasim abm --aoi ghana --days 3 --seed 1` (o `run_abm_from_manifest` directo) — valida que el C++ carga env NC + habitat + host_static + wind + 3 CSRs TODOS resueltos por el catálogo nuevo. Esperado ~6-8 min (CSR 2.4GB, constraint #2). Criterio exit: runcode 0 + snapshot tif día>0 sin errores de carga.
5. Un commit único + push (incluye el trabajo actual sin commitear, reescrito según este plan).

## Riesgos / notas

- **Comportamiento nuevo**: data-dir de producción sin manifest ahora falla ruidoso (antes glob silencioso). Migración: `register_existing` una vez. Ghana ya tiene manifest completo (verificado).
- **worldcover fuera del registry** (gap M11 conocido): sus claves NO aparecen en catalog_status; los slots M12 opcionallos resuelven si alguien lo registra. No se agrava; queda visible.
- **_legacy hydrolakes**: clave real `hydrolakes_lakes` usada en el slot; nunca descargable hoy (legacy) → opcional-ausente para siempre hasta que exista producer.
- **wrapper.py** es el entry del ABM: convergencia mecánica (mismas claves/manifest), cubierta por test_runner + verificación #4.
- `register_existing` con regex de periodos derivados (año-01-01..año-12-31) es aproximación deliberada: es migración one-shot, no fuente de verdad futura.

## Orden de implementación

1. catalog.py + export __init__ → 2. daily_nc reescritura → 3. productores constantes → 4. consumidores (wrapper/cli/env/viz) → 5. comando datasets → 6. tests (helper manifest + test_catalog) → 7. verificación 1-4 → 8. commit único + push.
