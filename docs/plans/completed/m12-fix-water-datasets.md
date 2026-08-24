# M12 Fix — Water Datasets, Download, Ingest y ABM

> **Estado:** en corrección. La implementación previa añadió loaders, pero no cerró el contrato extremo a extremo.
>
> **Objetivo:** dejar un camino mínimo y verificable desde datasets descargados hasta `env.nc`, ingest y ABM, sin descargar salidas que no consume la corrida actual.

## 1. Hallazgos de auditoría

| Área | Hallazgo | Acción |
|---|---|---|
| Plan M12 | Prometía `load_water_stack`, OPERA DSWX-S1, coastline y scorer de agua. No existen en código actual. | No declarar esas piezas como terminadas. Registrar como trabajo futuro o eliminar del alcance M12 actual. |
| Download | `runner.py` fija `required_for_abm=True` para todo output. | Añadir metadata por output y seleccionar perfil ABM mínimo por defecto. |
| ERA5 wind | Devuelve `xr.Dataset` 6-horario, pero falta routing `daily`; intenta TIF. | Declarar `wind_6hourly: daily`; guardar NC. Mantener opcional hasta conectar wrapper. |
| CHIRPS mensual | ABM NC usa lluvia diaria; mensual no es necesario para ABM. | Mantener loader para análisis explícito, excluirlo del perfil ABM. |
| M12 HydroLAKES | `permanent_lakes.tif` se mezcla en `water_frac` solo si existe. | Mantener y probar integración. |
| M12 HydroRIVERS | No lo lee `daily_nc.py`, hosts ni ABM. | Excluir del perfil ABM hasta tener consumidor. |
| M12 WorldCover | `wc_wetland` solo se escribe como diagnóstico; `wc_permanent_water` no se consume por ingest. | Integrar permanent water en composición o marcar outputs opcionales. No usar wetland como señal principal sin validación. |
| Wildlife | Descarga WorldCover, JRC GSW y buildings internamente; no reutiliza TIF M12 del manifest. | Documentar dependencia indirecta; evitar contar esos TIF como inputs directos de `host_static.nc`. |
| M14 | Pool hydrology necesita secuencia diaria de lluvia y estado por patch. | Verificar que `env.nc` conserva `rainfall(time,y,x)` y que ABM lee cada día. |

## 2. Contrato final M12 actual

### 2.1 Perfil ABM mínimo

| Output | Cadencia | Formato disco | Consumidor |
|---|---:|---|---|
| CHIRPS `rainfall_daily` | diaria | NC | `daily_nc.py`, M14, Climate/Habitat engine |
| ERA5 `water_temp` | mensual/static por período | TIF por período | `daily_nc.py`, temperatura acuática |
| MODIS `ndvi` | mensual/static por período | TIF por período | `daily_nc.py` |
| JRC GSW `water_occurrence` | estática | TIF | `daily_nc.py` base `water_frac` |
| HydroLAKES `permanent_lakes` | estática | TIF | `daily_nc.py`, enriquecimiento M12 |
| WorldPop `population` | estática | TIF | `host_static.nc` |
| GLW4 especies | estática | TIF | `host_static.nc` |
| GHSL `urban_class` | estática | TIF | `host_static.nc` |

### 2.2 Inputs opcionales

- Overture buildings: mejora `building_fraction`; existe fallback urbano/rural.
- Wildlife proxy: mejora fauna; existe fallback `0.3`.
- WorldCover wetland/permanent water: capas M12 auxiliares; deben tener consumidor explícito antes de ser obligatorias.
- ERA5 `wind_6hourly`: NC 6-horario; no usar en perfil ABM hasta que wrapper pase `--wind-field`.
- CHIRPS `rainfall`: total mensual; solo análisis mensual, no M14.

### 2.3 Fuera de perfil ABM

- HydroRIVERS `permanent_rivers` y `river_proximity`: sin consumidor actual.
- WorldCover `landcover` y `wc_mangrove`: sin consumidor actual.
- ERA5 `temp_suitability`: no leído por `daily_nc.py` en camino NC.

## 3. Cambios de código

1. Añadir metadata `abm_default` y `required_for_abm` por output en `DOWNLOADER`.
2. Cambiar runner para:
   - usar solo outputs `abm_default` cuando no se pasa `--outputs`;
   - registrar `required_for_abm` real, no `True` global;
   - guardar ERA5 wind como NC 6-horario;
   - eliminar dimensión temporal singleton antes de escribir TIF mensual;
   - rechazar explícitamente formato/cadencia incompatible.
3. Añadir `formats` de ERA5:
   - `water_temp`: mensual;
   - `temp_suitability`: fuera de perfil ABM;
   - `wind_6hourly`: diario NC.
4. Extender `daily_nc.py` para componer `water_frac` con capas M12 disponibles:
   - JRC GSW base;
   - HydroLAKES permanent lakes;
   - HydroRIVERS permanent rivers, solo cuando se habilite explícitamente;
   - WorldCover permanent water, solo como capa declarada y validada.
5. Mantener wetland como diagnóstico hasta prueba de precisión/recall.
6. Añadir manifest variables y provenance para cada capa compuesta.

## 4. Pruebas pequeñas

### 4.1 Unitarias

- Registry: outputs, formatos y perfil ABM coherentes.
- Runner: no procesa outputs no seleccionados; singleton `(1,H,W)` se convierte a `(H,W)`.
- Writer: DataArray 3D va a NC; DataArray 2D va a TIF; Dataset wind va a NC.
- M12 loaders: máscaras tienen shape, CRS, dtype, nodata y rango esperado.
- `daily_nc.py`: composición `max(base, permanent_mask)`; variables diagnósticas presentes; fallback sin M12 funciona.
- M14: dos meses de lluvia diaria producen estado acumulado, evaporación, desecación y washout.

### 4.2 Fixture temporal de dos meses

Usar directorio temporal, AOI pequeño y datos sintéticos con dos meses:

- lluvia diaria: 60/61 días en NC, dimensión `time,y,x`;
- viento: timestamps cada 6 horas, variables `u100` y `v100`, NC;
- temperatura y NDVI: una capa por período mensual;
- JRC, HydroLAKES, rivers y WorldCover: TIF estáticos pequeños;
- hosts: construcción de `host_static.nc` y tres CSR.

Verificar archivos, dimensiones, manifest, variables y formatos antes de ejecutar ABM.

### 4.3 Smoke ABM

- Ejecutar binario C++ con `days=2`, `seed=1`, un rollout y fixture temporal.
- Confirmar lectura de `env.nc`, activación de patches, estado de `PoolState`, snapshot y `state.tif`.
- Ejecutar dos días con lluvia distinta y confirmar que el estado hídrico no se reinicia diariamente.

### 4.4 Descarga real acotada

Tras tests sintéticos, probar Ghana con solo dos meses y directorio temporal/cache temporal. No descargar todo el registry.

```bash
uv run malariasim download --aoi ghana --datasets chirps --outputs rainfall_daily --years 2024,2025 --months 6,7 --output-dir <tmp>/data/ghana
uv run malariasim download --aoi ghana --datasets era5 --outputs water_temp --years 2024,2025 --months 6,7 --output-dir <tmp>/data/ghana
uv run malariasim download --aoi ghana --datasets era5 --outputs wind_6hourly --years 2024,2025 --months 6,7 --output-dir <tmp>/data/ghana
```

Las capas estáticas M12 se prueban con fixture y, si upstream responde, con una descarga AOI acotada independiente.

## 5. Criterios de terminado

- [ ] Perfil ABM no descarga CHIRPS mensual, ERA5 wind ni HydroRIVERS por defecto.
- [ ] `rainfall_daily` queda en NC con una muestra por día.
- [ ] `wind_6hourly` queda en NC con 4 muestras por día y u/v.
- [ ] TIF mensual queda 2D, no `(1,H,W)`.
- [ ] `env.nc` contiene lluvia diaria, temperatura, NDVI y `water_frac` M12 enriquecido.
- [ ] M14 consume `rainfall(time,y,x)` y mantiene `PoolState` entre días.
- [ ] Manifest describe formato, período, variables y provenance.
- [ ] Ingest pasa con y sin capas M12 opcionales.
- [ ] ABM smoke test lee el `env.nc` generado y produce salida.
- [ ] La prueba real de dos meses se ejecuta en directorio temporal sin contaminar `data/` ni `runs/`.

## 6. No declarar todavía

M12 no debe declararse completo en su alcance original hasta implementar o retirar formalmente:

- `load_water_stack()`;
- OPERA DSWX-S1;
- GSHHG coastline y `distance_to_coast_m`;
- scorer de water-mask contra sitios larvales;
- integración real de HydroRIVERS y WorldCover permanent water en ABM.
