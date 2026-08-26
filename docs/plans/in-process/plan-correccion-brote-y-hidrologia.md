# Plan quirurgico: brote focal, hidrologia y habitat urbano

## 0. Alcance

Este plan **no modifica downloaders ni vuelve a descargar datos**. Los productos ya existentes son la fuente de verdad.

Se modifican solamente:

- `mal-core/src/mal_core/ingest/` para conservar informacion ya descargada;
- schema del GPKG/NetCDF generado por ingest;
- runtime C++ del ABM;
- logs, pruebas y validaciones.

Capas disponibles que debemos reutilizar:

- CHIRPS: lluvia diaria;
- JRC GSW y capas M12: agua permanente/proxy de agua;
- MERIT DEM: TWI/topografia;
- `host_static.nc`: poblacion, `urban_class`, `building_fraction` y hospedadores;
- snapshots acuaticos y de transmision existentes para regresion.

No se debe inferir que una capa falta hasta revisar manifest y filesystem. Si una capa opcional no existe, ingest debe mantener fallback explicito y registrarlo.

## 1. Congelar caso de regresion

Antes de tocar codigo, conservar metricas de `runs/ghana/1year_focal_outbreak`.

Registrar:

- `I_H`, `E_H`, incidencia y prevalencia por dia;
- `S_V`, `E_V`, `I_V` y hembras adultas por dia;
- huevos, larvas, pupas y emergencias;
- numero de parches activos y dias secos;
- focos seleccionados y casos asignados;
- version de binario, parametros y rutas de inputs.

Limitacion actual: `*_aquatic.tif` no existe y `*_transmission.json` final sobrescribe el log diario. Primero corregir observabilidad para que la siguiente corrida permita distinguir causa de correlacion.

## 2. Reparar log y metadata antes de diagnosticar

### 2.1. Separar nombres

En `abm/wrapper.py` y `abm/src/main.cpp`, separar:

```text
*_transmission_daily.json  # serie diaria
*_transmission.tif         # raster
*_transmission.json        # sidecar del raster
*_aquatic_daily.json       # estado acuatico diario
```

El log diario no puede compartir ruta con sidecar.

### 2.2. Registrar parametros efectivos

Eliminar `sha256:pending`. Guardar:

- modo de siembra;
- dia, numero y tamano de focos;
- `human_min_cell_pop`;
- `beta_hv`, `beta_vh`;
- umbral y duracion EIP;
- semilla;
- paths y hashes de env, host y habitat.

### 2.3. Corregir metadatos temporales

Cada snapshot debe registrar fecha/dia real. Una corrida de 365 dias no debe aparecer siempre como `month=1`.

## 3. Corregir brote humano: casos importados y trigger

### 3.1. Casos importados entran en edad cero

`HumanCompartmentGrid::seed_infections()` actualmente reparte `N` entre todos los 20 slots infecciosos. Eso modela una poblacion ya estacionaria, no casos importados en una fecha concreta.

Cambiarlo para que:

```text
infectious_[cell] += N
infectious_cohorts_[cell, 0] += N
```

Los slots restantes quedan en cero.

Mantener, si hace falta para `uniform-legacy`, una funcion distinta para inicializacion estacionaria. No reutilizar mismo metodo para ambos conceptos.

### 3.2. No disparar foco con densidad vacia

`TransmissionModel::init()` no debe llamar a `check_and_trigger_outbreak(0, {})`.

El trigger debe ocurrir desde `Engine::step()` cuando ya existe:

- densidad vectorial actual;
- fecha/dia actual;
- estado de parches activos.

Para dia 0, el trigger sigue siendo posible, pero usa datos reales del primer paso.

### 3.3. Foco viable significa foco transmisible

`random-viable` debe seleccionar celdas que cumplan simultaneamente:

- poblacion humana suficiente;
- parche activo o hembras adultas locales;
- al menos una hembra susceptible con posibilidad de picar.

Si se seleccionan cero focos, escribir warning/error con motivo. No marcar `outbreak_triggered_` como exitoso si no se inyecto ningun caso.

### 3.4. Criterio de extincion

No llamar “transmision establecida” porque `I_H > 0`. La cadena minima es:

```text
I_H importado
-> comida humana de hembra
-> S_V -> E_V
-> E_V -> I_V tras EIP
-> picadura infecciosa
-> S_H -> E_H
-> I_H autóctono
```

Una corrida que solo muestra `I_H importado -> 0` es fallo de establecimiento, no extincion biologica valida.

## 4. Evitar que warm-up entregue cero vectores

El caso observado cae de `174978` hembras en dia 7 a `67` en dia 140. El brote del dia 180 no tiene vector local suficiente.

### 4.1. Separar warm-up y brote

Ejecutar primero warm-up sin infeccion humana. Inyectar casos solo tras verificar por foco:

- hembras adultas;
- comidas humanas;
- parches acuaticos activos;
- temperatura compatible con EIP.

### 4.2. No esconder problema con un parametro

No bajar mortalidad ni subir fecundidad sin calibracion. Primero comparar:

- adultos con edad inicial escalonada;
- bancos acuaticos escalonados;
- warm-start desde estado maduro.

La opcion elegida debe reproducir poblacion estable sin producir explosion.

## 5. Conservar permanencia hidrologica en ingest y runtime

### 5.1. Ingest: reutilizar datos, no cambiar fuentes

`daily_nc.py` ya compone `permanent_water_mask` y lo escribe como variable diagnostica. Mantener esa logica.

Cambios necesarios:

- comprobar que `permanent_water_mask` llega al producto usado por ABM;
- no reducirlo a `water_frac` exclusivamente;
- registrar conteo de celdas permanentes y cobertura;
- usar nearest para mascaras discretas;
- conservar `water_frac` como intensidad/capacidad espacial.

### 5.2. GPKG: añadir tipo sin regenerar datos externos

`_write_habitat_patches_gpkg()` en `ingest/env.py` debe incluir:

- `habitat_type`;
- `is_permanent`;
- `source_layer`;
- `water_frac_value`;
- `twi_value`.

La clasificacion sale de las mascaras ya disponibles:

```text
permanent_water: permanent_water_mask > 0
temporary_pool:  no permanente y candidato TWI/lluvia
urban_temporary: no permanente, urbano y candidato edificio/lluvia
```

No usar TWI para declarar permanencia.

### 5.3. Runtime: dos reglas de agua

En `CoordinatorModel::activate_patches()` y `PoolState`:

Permanente:

- `activated = true` mientras mascara sea valida;
- no aplicar secado por evaporacion;
- no aumentar `days_dry` por falta de lluvia;
- no matar cohortes por desecacion;
- permitir reproduccion.

Temporal:

```text
W[t+1] = max(0, W[t] + lluvia[t] - evaporacion[t])
```

Aplicar umbral de agua, gracia seca, mortalidad y washout solamente a temporales.

## 6. Añadir habitat temporal urbano basado en edificios

### 6.1. Justificacion cientifica

No se debe usar edificio como sinonimo de agua. Se usa como indicador de superficie antropizada donde lluvia puede quedar retenida o drenarse mal.

La evidencia disponible en el proyecto y literatura sobre Accra respalda estos mecanismos:

- `papers/` contiene referencias sobre malaria urbana y habitat antropogenico;
- Klinkenberg et al. (2008), Accra: tuberias rotas, charcos en construccion, drenaje deficiente y zonas inundables;
- Dzorgbe Mattah et al. (2016), Ghana urbano: mayoria de habitats man-made; charcos, zanjas, drenajes y sitios de construccion;
- estudio de Accra publicado en *Malaria Journal* (2025): zanjas, canales, charcos, recipientes y construccion como habitats de `Anopheles`;
- Vanhuysse et al. (2023), disponible en referencias del proyecto, apoya estratificacion de exposicion urbana.

La conclusion aplicable al ABM es: edificios deben modificar probabilidad/capacidad de acumulacion urbana, no crear lagos permanentes automaticamente.

### 6.2. Datos usados

Reutilizar `host_static.nc` generado por `ingest/hosts.py`:

- `building_fraction`;
- `urban_class`;
- poblacion humana.

No exigir NDVI. NDVI puede modular vegetacion, pero una charca urbana por drenaje, construccion, canal o recipiente puede existir con NDVI bajo.

### 6.3. Regla propuesta

Crear candidatos urbanos temporales cuando:

```text
urban_class == urban
AND building_fraction >= B_min
AND (rainfall >= R_min OR antecedent_rain_7d >= R7_min)
AND (TWI >= TWI_urban_min OR lowland/flood indicator)
```

Parametros deben quedar configurables, no hardcodeados. Valores iniciales para calibracion, no verdades biologicas:

- `B_min`: 0.05;
- `R_min`: 10-15 mm/dia;
- `R7_min`: suma de lluvia de 7 dias;
- `TWI_urban_min`: menor que el rural, por ejemplo 6-8.

La reduccion de TWI representa drenaje urbano imperfecto, no agua garantizada.

### 6.4. Capacidad urbana

`building_fraction` debe afectar capacidad o persistencia, no solo presencia:

```text
urban_capacity = base_capacity * f(building_fraction, urban_class)
```

La funcion debe ser monotona y acotada. Edificio alto aumenta probabilidad de retencion, pero lluvia insuficiente sigue dejando el parche seco.

### 6.5. Implementacion minima

1. Ingest lee `building_fraction` y `urban_class` desde `host_static.nc` si existe.
2. Ingest los copia como atributos de parche GPKG y/o variables estaticas del NetCDF ambiental.
3. `env_reader.cpp` carga canales opcionales, sin romper NetCDF antiguos.
4. `ClimateEngine` expone `building_fraction_at()` y `urban_class_at()`.
5. `CoordinatorModel` crea/actualiza `urban_temporary` con lluvia antecedente y TWI urbano.
6. `PoolState` aplica balance temporal, nunca permanencia implicita.

No conectar regla urbana a NDVI.

### 6.6. Riesgo a controlar

No crear un parche urbano por cada pixel construido. Validar densidad de parches, agua acumulada y abundancia vectorial contra observaciones. La regla debe ampliar habitat plausible, no causar explosion poblacional.

## 7. Telemetria acuática y epidemiologica

Exportar diariamente, al menos en modo debug:

- `patch_id`, fila, columna;
- `habitat_type`, `is_permanent`;
- `water_mm`, `days_dry`, `activated`;
- lluvia diaria y lluvia antecedente de 7 dias;
- `building_fraction`, `urban_class`;
- huevos, larvas, pupas;
- muertes por desecacion y washout;
- hembras adultas y comidas humanas;
- transiciones `S_V -> E_V`, `E_V -> I_V`, `S_H -> E_H`.

Esto permite distinguir “agua ausente” de “agua presente pero sin oviposicion”.

## 8. Pruebas

### 8.1. Hidrologia sintetica

- Permanente + 60 dias sin lluvia: sigue activo, cero muertes por desecacion.
- Temporal + evaporacion neta: se seca.
- Temporal + lluvia: vuelve a activarse.
- Urbano construido + lluvia + TWI moderado: crea charca temporal.
- Urbano construido + sin lluvia: no crea charca.
- Urbano sin NDVI: regla sigue funcionando.

### 8.2. Transmision sintetica

Una celda con poblacion, hembras, agua permanente y temperatura controlada debe demostrar:

```text
I_H importado > 0
E_V > 0
I_V > 0 despues de EIP
infectious_bites > 0
incidencia autóctona > 0
```

### 8.3. Ghana

Comparar corrida nueva con la regresion:

- no pulso aislado sin `E_V/I_V`;
- permanentes no desaparecen;
- urbanos generan habitat solo bajo lluvia/antecedente hidrico;
- población vectorial no colapsa antes del brote elegido;
- logs completos y reproducibles.

## 9. Orden de ejecucion

1. Separar logs y registrar parametros.
2. Corregir cohorte de casos importados.
3. Corregir trigger y validacion de focos.
4. Añadir tipo permanente al GPKG/runtime usando datos existentes.
5. Añadir telemetria hidrologica y transiciones epidemiologicas.
6. Implementar regla urbana basada en edificios, lluvia y TWI.
7. Ejecutar pruebas sinteticas.
8. Calibrar warm-up/vector.
9. Reejecutar Ghana 365 dias.

## 10. Aceptacion

1. Downloaders sin cambios.
2. Cada parche permanente conserva `is_permanent=1` hasta final.
3. Ningun permanente registra desecacion.
4. Charcas temporales responden a lluvia y evaporacion.
5. Edificios permiten habitat urbano temporal sin requerir NDVI.
6. Casos importados entran en edad cero.
7. Un foco viable produce `E_V`, luego `I_V`, luego casos autóctonos.
8. Un pulso sin ciclo vectorial se reporta como fallo de establecimiento.
9. Log diario no es sobrescrito.
10. Corrida queda reproducible desde parametros e inputs registrados.
