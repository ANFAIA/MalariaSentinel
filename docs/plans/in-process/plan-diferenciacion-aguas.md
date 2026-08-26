# Plan de diferenciacion de aguas y habitats

## 0. Proposito

Este plan queda separado de `plan-correccion-brote-y-hidrologia.md`. No se implementa en la continuacion actual del brote SER-SEI.

Objetivo: distinguir agua oceánica, costera, lentica, fluvial y temporal usando evidencia que ya existe en el codigo y en los productos descargados. No asumir que una clase ecologica puede inferirse de una sola variable raster.

## 1. Estado conocido del codigo

- `permanent_water_mask` indica permanencia/proxy de agua, no tipo de cuerpo de agua.
- `water_frac` representa intensidad/capacidad espacial, no flujo.
- GPKG ya transporta `habitat_type`, `is_permanent`, `source_layer`, `water_frac_value` y `twi_value`.
- Runtime aplica hidrologia temporal/permanente, pero no caudal, velocidad, profundidad ni depredacion.
- Limpieza actual elimina componentes de agua conectadas al borde del raster para evitar oceano abierto como habitat.
- `salinity` existe como canal ambiental y tolerancia por especie ya existe, pero no hay clase costera validada.
- No existe aun una variable de rio, estuario, laguna o margen fluvial en el contrato del parche.

Estas afirmaciones deben verificarse contra codigo y artefactos antes de cada implementacion; este documento no convierte hipotesis en datos.

## 2. Taxonomia minima propuesta

Usar nombres estables, con fallback explicito:

```text
ocean_open
coastal_saline
lentic_permanent
river_channel
river_margin_pool
temporary_pool
urban_temporary
unknown_water
```

`ocean_open` existe en geografia pero no es habitat de oviposicion. `coastal_saline` puede ser habitat segun salinidad y especie. `river_channel` no debe recibir automaticamente la misma capacidad que una charca. `river_margin_pool` representa remansos, bordes y depresiones inundables; no debe confundirse con el cauce.

## 3. Fuentes y reglas de evidencia

Orden de confianza:

1. Capas hidrologicas existentes en manifest/filesystem.
2. Variables ya presentes en NetCDF/GPKG.
3. Geometria y conectividad raster, solo como proxy documentado.
4. TWI, lluvia y urbanidad para candidatos temporales, nunca para declarar rio o permanencia.
5. Heuristica `unknown_water` cuando evidencia insuficiente.

No clasificar rio por `permanent_water_mask` solamente. No clasificar oceano por salinidad solamente. No crear una clase nueva sin registrar fuente, regla y cobertura.

## 4. Diseño de ingest

1. Auditar `manifest.json`, filesystem y variables NetCDF antes de cambiar reglas.
2. Medir componentes conectadas de agua y conservar estadisticas por componente: area, borde tocado, salinidad, TWI, elevacion.
3. Sustituir la regla global de borde por una mascara costera validada si una fuente existente la permite.
4. Mantener oceano abierto fuera de habitat sin borrar datos ambientales.
5. Añadir atributos de evidencia al GPKG:

```text
habitat_type
habitat_confidence
source_layer
is_permanent
salinity_value
water_frac_value
twi_value
```

6. Preservar compatibilidad de lectura: campos ausentes producen `unknown_water` y warning, no crash silencioso.

## 5. Diseño runtime futuro

Extender `PatchState` y el contrato de habitat solo cuando exista fuente suficiente:

- `ocean_open`: desactivado para oviposicion y bancos acuaticos.
- `coastal_saline`: permanencia independiente de lluvia; salinidad filtra por especie.
- `lentic_permanent`: balance permanente actual, sujeto a capacidad y mortalidad biologica.
- `river_channel`: capacidad reducida y mortalidad por flujo solo con parametro calibrado.
- `river_margin_pool`: balance temporal/permanente segun evidencia local.
- `temporary_pool`: balance lluvia-evaporacion y desecacion.
- `urban_temporary`: regla urbana existente, sin permanencia implicita.

No introducir depredacion, caudal o washout fluvial por constantes arbitrarias. Cada mecanismo necesita parametro, unidad, rango, prueba sintetica y evidencia.

## 6. Validacion

Crear fixtures pequeños para:

- océano conectado al borde: no habitat;
- lago interior: permanente conservado;
- laguna salobre: `coastal_saline`, disponible solo para especies compatibles;
- cauce y remanso adyacente: clases distintas;
- charca temporal urbana: activa solo con lluvia/antecedente;
- raster sin evidencia fluvial: `unknown_water`, sin inferencia excesiva.

Validar en Ghana:

- conteo por clase y cobertura espacial;
- interseccion con costa y salinidad;
- parches costeros eliminados por limpieza actual;
- abundancia acuática por clase;
- estabilidad vectorial y no solo conteo de agua.

## 7. Criterio de salida

No implementar diferenciacion completa hasta disponer de:

- fuente o proxy explícito para cada clase usada;
- cobertura y falsos positivos auditados;
- contrato GPKG/NetCDF documentado;
- pruebas de regresion ingest/runtime;
- corrida Ghana comparando clases y poblacion vectorial.
