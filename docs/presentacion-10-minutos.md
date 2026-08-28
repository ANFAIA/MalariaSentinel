# Presentacion de 10 minutos — MalariaSentinel

> Documento de conceptos. No es guion cerrado. Define ideas, orden, evidencia y decisiones de comunicacion para presentar MalariaSentinel desde el **Why** hacia el **How** y terminar en el **What**.

**Siguiente paso:** [guion hablado por slides](guion-presentacion-10-minutos.md).

## Tesis central

La malaria no espera a que un sistema de salud confirme un brote. MalariaSentinel busca convertir datos ambientales y epidemiologicos en anticipacion espacial: ayudar a los programas de eliminacion a decidir **donde mirar, cuando actuar y como priorizar recursos limitados**.

La presentacion no debe vender "una IA que predice la malaria". Debe invitar a construir y validar una capacidad de vigilancia anticipada, abierta y operativa.

## Objetivo de la presentacion

Al terminar, la audiencia debe entender cuatro cosas:

1. El problema no es falta de datos; es falta de traduccion de datos en decisiones locales a tiempo.
2. La propuesta es pasar de reaccionar ante casos confirmados a anticipar zonas de riesgo.
3. La tecnologia combina datos geoespaciales, simulacion biologica y aprendizaje automatico.
4. El siguiente paso requiere alianzas con programas de malaria, ONG, investigadores y capacidad computacional para validar en campo.

## Audiencia prioritaria

### Primera audiencia: ONG y programas de eliminacion

Son el punto de entrada porque conocen el problema operativo, gestionan intervenciones y pueden aportar datos de vigilancia y validacion.

La pregunta no es "¿comprarias este software?". La pregunta es:

> ¿Que decision de vigilancia o intervencion tomarias antes si tuvieras un mapa de riesgo actualizado y explicable para tu zona?

### Audiencias secundarias

- Programas nacionales y subnacionales de control de malaria.
- Institutos de salud publica y equipos de vigilancia epidemiologica.
- Investigadores en epidemiologia espacial, entomologia y modelado.
- Centros de supercomputacion y equipos de infraestructura.
- Financiadores de salud global y adaptacion climatica.

## Distribucion de tiempo

| Bloque | Tiempo | Funcion |
|---|---:|---|
| Why: dolor y creencia | 3:00 | Hacer visible urgencia y proposito |
| How: enfoque y tecnologia | 3:00 | Explicar por que este enfoque puede cerrar la brecha |
| What: producto y demostracion | 2:30 | Mostrar que existe hoy |
| Hitos, equipo y llamada | 1:30 | Convertir interes en colaboracion |

La tabla marca ritmo, no texto para leer palabra por palabra.

---

## 1. Why — Por que existe

### Creencia central

Las comunidades no deberian esperar a que el daño sea visible para recibir una respuesta. Si los factores que favorecen la transmision cambian en el espacio y en el tiempo, la vigilancia tambien debe hacerlo.

### Entrada: ir directo al dolor

Abrir con una imagen mental concreta, no con arquitectura:

> Una intervencion que llega despues de detectar el brote llega tarde para las personas que ya estuvieron expuestas.

Despues, apoyar el dolor con un dato global y un dato operativo. No acumular cifras. La cifra debe llevar a una consecuencia:

- En 2024, la malaria registro aproximadamente **282 millones de casos y 610.000 muertes**; cerca del 94 % de la carga se concentro en Africa. Fuente de trabajo: [nota de investigacion del proyecto](../papers/perplexity-investigations/Mosquitos%20de%20la%20Malaria%20%20Biolog%C3%ADa%2C%20Comportamiento%2C%20Expansi%C3%B3n%20y%20Variables%20para%20Simulaci%C3%B3n.md). Verificar cifra y edicion del informe OMS antes de presentacion publica.
- Los sistemas suelen actuar con datos de casos ya detectados, mientras que el riesgo puede cambiar antes por lluvia, temperatura, agua, vegetacion, movilidad y condiciones del vector. El [marco SDSS de Kelly et al.](../papers/spatial-analysis/MalariaEliminationWithSpatialDecisionSupportSystems.md) fundamenta esta necesidad de vigilancia espacial, prevencion focalizada y respuesta operativa.

### El problema que queremos resolver

No presentar problema como "faltan datos". Presentarlo como una cadena rota:

1. Existen datos satelitales, ambientales, epidemiologicos y entomologicos.
2. Esos datos viven en fuentes, formatos y escalas diferentes.
3. Los equipos locales necesitan respuestas espaciales y accionables, no solo capas de datos.
4. La intervencion suele empezar cuando los casos ya hacen visible la expansion.
5. Con recursos limitados, actuar igual en todas partes reduce capacidad de impacto.

### Cambio ambiental y expansion geografica: como hablarlo

Evitar afirmar que "la malaria se esta desplazando inevitablemente hacia Occidente". Es demasiado amplio y puede sonar alarmista.

Usar una formulacion precisa:

> El clima, la movilidad humana y la expansion de vectores modifican donde puede aparecer riesgo. Incluso paises con baja transmision necesitan vigilancia capaz de detectar reintroduccion y brotes locales.

El proyecto documenta la expansion de *Anopheles stephensi* hacia nuevos territorios y casos de malaria en zonas no endemicas en [investigaciones de dinamica de brotes](../papers/outbreak-dynamics/README.md). Presentarlo como razon para mejorar vigilancia, no como prediccion catastrofista.

### Por que ahora

- La eliminacion exige pasar de promedios nacionales a decisiones subnacionales y focales.
- La teledeteccion y los datos geoespaciales permiten actualizar condiciones ambientales con mayor frecuencia.
- Los modelos biologicos pueden explorar escenarios que no se observan directamente.
- Un sustituto neuronal puede hacer usable en tiempos operativos lo que una simulacion detallada no puede ejecutar repetidamente.

### Invitacion, no convencimiento

La audiencia debe sentirse parte de una capacidad compartida:

> No venimos a reemplazar el conocimiento local. Venimos a darle una capa de anticipacion, explicacion y comparacion de escenarios.

---

## 2. How — Como lo hacemos

### Principio de diseño

MalariaSentinel une tres escalas de conocimiento:

- **Observacion:** datos de clima, lluvia, vegetacion, agua, terreno, poblacion, movilidad, casos y vectores.
- **Mecanismo:** simulacion basada en agentes que representa dinamica de mosquitos, habitat y transmision.
- **Decision:** mapas de riesgo y escenarios que orientan vigilancia e intervenciones.

No es una caja negra unica. Es una cadena donde cada etapa puede inspeccionarse, calibrarse y sustituirse.

### Flujo tecnico que hay que explicar

1. **Ingesta:** descarga y normalizacion de capas por area de interes.
2. **Idoneidad ambiental:** construccion de una grilla comun, actualmente orientada a resolucion de 1 km en Ghana.
3. **ABM:** simulacion detallada de poblaciones de vectores y estados de transmision.
4. **Calibracion:** comparacion de curvas, estacionalidad y patrones espaciales con observaciones.
5. **U-Net:** aprendizaje de un modelo sustituto a partir de salidas del ABM.
6. **Prediccion:** generacion de mapas de riesgo mensuales para apoyar priorizacion.

El [estado de arquitectura](system-status.md) describe este pipeline. La [especificacion de ABM](specs/abm/spec.md) y la [especificacion de prediccion](specs/prediction/spec.md) contienen contratos tecnicos.

### Metafora ABM → U-Net

Usar una sola metafora:

- **ABM es profesor:** lento, detallado, biologicamente explicito.
- **U-Net es estudiante:** aprende de muchos rollouts y responde rapido, con aproximacion.

La velocidad no convierte automaticamente el resultado en verdad. Primero hace falta calibracion y validacion externa.

### Diferenciacion

La propuesta no es solo un mapa estadistico ni solo una simulacion:

- Integra fuentes heterogeneas en una unidad espacial comun.
- Representa mecanismos biologicos, no unicamente correlaciones.
- Permite escenarios contrafactuales de intervencion.
- Produce una salida pensada para decisiones operativas.
- Mantiene arquitectura abierta y componentes reproducibles.

### Limite que debe decirse en voz alta

El sistema actual es una **prueba de pipeline**, no un predictor clinicamente validado. El README registra un mejor Dice de validacion de 0,24 para la U-Net, por debajo del objetivo de 0,6, debido a limites de datos y computacion. Esta honestidad aumenta credibilidad y convierte validacion en llamada a colaboracion.

---

## 3. What — Que existe

### Producto actual

MalariaSentinel es un SDSS abierto para eliminacion de malaria, con caso de trabajo inicial en Ghana. Su pipeline ejecutable incluye:

- Descarga y registro de datos por area de interes.
- Ingesta ambiental, habitat, hospedadores y movilidad.
- Motor ABM C++ para rollouts de transmision.
- Scorers de calibracion y composicion de resultados.
- Entrenamiento de U-Net como modelo sustituto.
- Prediccion de mapas de riesgo.
- CLI `malariasim` y API FastAPI para integrar etapas.

La secuencia completa esta documentada en [`mal-core/README.md`](../mal-core/README.md): `download → ingest → abm → score → train → predict`.

### Demostracion recomendada

Mostrar flujo y salida, no repositorio completo:

1. Seleccionar Ghana y un periodo.
2. Enseñar capas ambientales que alimentan grilla.
3. Mostrar rollout o mapa de estado del ABM.
4. Mostrar paso ABM → dataset → U-Net.
5. Mostrar mapa de riesgo y formular la decision que podria informar.

Cerrar demo con pregunta operativa: "¿Que zona merece vigilancia prioritaria el proximo periodo y que dato de campo necesitamos para comprobarlo?"

### Lo que no afirmar

- No decir "predice casos clinicos con precision".
- No decir "reemplaza epidemiologos o programas de salud".
- No presentar resultado Ghana como validacion transferible a cualquier pais.
- No presentar expansion de vectores como destino inevitable.
- No confundir simulacion de riesgo con diagnostico individual.

---

## Hitos que cuentan una historia

Presentar hitos como reduccion de incertidumbre, no como lista de tareas:

| Hito | Pregunta que responde |
|---|---|
| Pipeline Ghana de extremo a extremo | ¿Podemos mover datos hasta una salida de riesgo? |
| ABM C++ consolidado | ¿Podemos ejecutar muchos escenarios a coste operativo? |
| Calibracion biologica y espacial | ¿El comportamiento simulado se parece al observado? |
| U-Net con datos ampliados | ¿Podemos acelerar escenarios sin perder utilidad? |
| Validacion con datos de programa | ¿La salida mejora una decision real? |
| Piloto con ONG en una zona definida | ¿El flujo funciona con usuarios, tiempos y restricciones reales? |
| Transferencia a otra region | ¿Que parte generaliza y que parte necesita recalibracion? |

Orden narrativo: primero demostrar ejecucion, despues demostrar validez, finalmente demostrar utilidad.

## Equipo necesario para escalar

No pedir "mas gente" sin funcion. Pedir capacidades concretas:

- **Lider de programa malaria:** convierte mapas en decisiones y define criterios de utilidad.
- **Epidemiologo espacial:** diseña validacion, sesgos y lectura de incertidumbre.
- **Entomologo:** calibra especies, supervivencia, desarrollo, dispersión y resistencia.
- **Ingeniero de datos geoespaciales:** automatiza fuentes, calidad, CRS, resolucion y procedencia.
- **Cientifico de modelos:** mantiene ABM, escenarios e incertidumbre.
- **Ingeniero ML/MLOps:** escala rollouts, entrenamiento, versionado y serving.
- **Ingeniero de producto o UX:** transforma salidas tecnicas en flujo de trabajo para ONG.
- **Infraestructura/HPC:** habilita GPU, paralelismo, almacenamiento y costes reproducibles.
- **Socio local de implementacion:** aporta datos, contexto, acceso a terreno y validacion de adopcion.

Equipo minimo de piloto: lider de programa, epidemiologo/entomologo compartido, ingeniero geoespacial y una persona de modelos/infraestructura.

## Llamada a la accion

Un solo CTA, concreto y medible:

> Buscamos una ONG o programa de malaria que aporte una zona piloto, datos historicos y una decision operativa concreta. A cambio, construimos juntos un primer ciclo de validacion: riesgo anticipado, intervencion priorizada y comprobacion con datos de campo.

Despues del CTA:

- QR a pagina del proyecto.
- Link corto visible en pantalla.
- Contacto del equipo.
- Tres elementos para una primera reunion: zona, decision y datos disponibles.

El cierre debe dejar una pregunta abierta, no una promesa:

> ¿Que podriamos anticipar juntos si el mapa de riesgo llegara antes que el brote?

## Fuentes para la version publica

- [WHO Global Malaria Programme](https://www.who.int/teams/global-malaria-programme)
- [WHO World Malaria Report](https://www.who.int/teams/global-malaria-programme/reports/world-malaria-report-2025)
- Kelly GC, Tanner M, Vallely A, Clements A. *Malaria elimination: moving forward with spatial decision support systems*. 2012. [DOI](https://doi.org/10.1016/j.pt.2012.04.002). Resumen local: [`papers/spatial-analysis/MalariaEliminationWithSpatialDecisionSupportSystems.md`](../papers/spatial-analysis/MalariaEliminationWithSpatialDecisionSupportSystems.md).
- [CDC: investigacion de malaria transmitida localmente, 2026](https://doi.org/10.15585/mmwr.rr7501a1)
- [Referencias y atribuciones del proyecto](../papers/REFERENCES.md)

### Control final antes de presentar

- Confirmar cifras OMS y fecha del informe.
- Cambiar toda afirmacion de "prediccion" por "salida de riesgo" cuando no exista validacion suficiente.
- Llevar una sola cifra global, una cifra del pipeline y un ejemplo de decision.
- Mostrar incertidumbre y limitaciones sin esconderlas en letra pequeña.
- Probar QR, link y demo sin internet o con capturas de respaldo.
- Terminar con una peticion concreta a una audiencia concreta.
