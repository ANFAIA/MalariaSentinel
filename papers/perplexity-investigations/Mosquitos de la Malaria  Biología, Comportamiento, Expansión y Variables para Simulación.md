# Mosquitos de la Malaria: Biología, Comportamiento, Expansión y Variables para Simulación
**Source:** Perplexity Investigation (2026-07-04)
**Language:** Spanish
**File:** papers/perplexity-investigations/Mosquitos de la Malaria Biología, Comportamiento, Expansión y Variables para Simulación.md

---

## Resumen Ejecutivo

La malaria registró ~282 millones de casos y 610.000 muertes en 2024, con el 94% de la carga en África. El único vector es el mosquito *Anopheles* (~70 especies competentes de >450 descritas). Este documento compila sistemáticamente la biología, ecología y dinámica poblacional del género como base para simulaciones predictivas ABM. Se cubren: taxonomía y complejos de especies crípticas, ciclo de vida holometábolo (huevo-adulto en 10–18+ días), ciclo gonotrófico (2–4 días), comportamiento de hembras (búsqueda de hospedador mediada por CO₂, olores cutáneos, temperatura), preferencias de hábitat larvario (agua limpia, somera, soleada, pH 7.0–8.5), y mecanismos de dispersión que van desde vuelo local de 1–2 km hasta migración eólica de cientos de kilómetros a 120–290 m de altitud.

La sección más relevante para modelado es la **Taxonomía Completa de Variables para Simulación** (Sección 10), que cataloga ~80 variables organizadas en cinco dominios: biológicas del ciclo de vida (huevo, larva, pupa, adulto, parásito), ambientales/climáticas (temperatura, precipitación, humedad, viento, cobertura terrestre), comportamentales y de dispersión (dispersal local y eólico, enjambres, aestivación), poblacionales/especie (composición, estructura genética, resistencia), y antropogénicas/de control (ITNs, IRS, larvicidas, gene drives, zooprofilaxis). Cada variable incluye rangos numéricos extraídos de la literatura (ej. temperatura letal larval >40°C, humedad relativa crítica <40% para aestivación). El documento concluye con una arquitectura recomendada de ABM espacio-temporal de 8 capas, identificando además 6 brechas de conocimiento críticas que limitan la calibración realista.

## Contenido Principal

## 1. Taxonomía y Diversidad de Especies

### 1.1 Clasificación General
El género *Anopheles* (familia Culicidae, orden Díptera) comprende >450 especies descritas, de las cuales ~70 transmiten malaria humana. Las especies se agrupan en complejos crípticos o "especies hermanas" morfológicamente casi idénticas pero con diferencias biológicas y de capacidad vectorial cruciales, distinguibles solo por ADN.

### 1.2 Principales Vectores por Región Geográfica
| Región | Especies Principales | Parásito Transmitido |
|---|---|---|
| **África Subsahariana** | *An. gambiae s.s.*, *An. coluzzii*, *An. arabiensis*, *An. funestus*, *An. moucheti*, *An. nili*, *An. melas*, *An. merus* | Principalmente *P. falciparum* |
| **Asia del Sur/Sudeste** | *An. stephensi*, *An. dirus*, *An. minimus*, *An. fluviatilis*, *An. culicifacies*, *An. maculatus*, *An. sundaicus* | *P. falciparum*, *P. vivax* |
| **América** | *An. darlingi*, *An. albimanus*, *An. freeborni*, *An. pseudopunctipennis* | *P. vivax*, *P. falciparum* |
| **Europa y Oriente Medio** | *An. atroparvus*, *An. labranchiae*, *An. messeae*, *An. sacharovi*, *An. sergentii* | *P. vivax* (eliminado de Europa) |

### 1.3 El Complejo *Anopheles gambiae* — Modelo Más Estudiado
Comprende al menos **8 especies crípticas**: *An. gambiae s.s.* (vector primario, antropofílico, endofílico), *An. coluzzii* (África Occidental, antes "forma M"), *An. arabiensis* (generalista, tolerante a aridez), *An. melas* (agua salada, costa oeste), *An. merus* (agua salada, costa este), *An. quadriannulatus* (zoofílico, menor impacto), *An. amharicus* (Etiopía), *An. fontenillei* (especie más reciente). Las inversiones cromosómicas polimórficas (especialmente **2La**) son mecanismos centrales de adaptación local: 2La confiere resistencia a desecación en *An. gambiae*, permitiendo colonizar hábitats más secos.

### 1.4 Especies Crípticas Emergentes
En 2025, un análisis genómico identificó un nuevo taxón críptico en el complejo *An. gambiae*. Las especies crípticas varían enormemente en capacidad vectorial, preferencia de hospedador y resistencia a insecticidas.

---

## 2. Ciclo de Vida y Biología Reproductiva

### 2.1 Las Cuatro Etapas del Ciclo de Vida
*Anopheles* es holometábolo: huevo → larva (4 instares) → pupa → adulto. Duración total: **10–18+ días** según temperatura y especie.

**Fase de Huevo**: 50–200 huevos depositados individualmente sobre la superficie del agua, con flotadores laterales. Eclosión en 24–48 h. Crítico: los huevos de *Anopheles* **no toleran la desecación** (mueren en horas si el agua se evapora), a diferencia de *Aedes*.

**Fase Larvaria**: 4 instares. Las larvas descansan **paralelas a la superficie** (diagnóstico: sin sifón como *Culex*). Se alimentan de microorganismos. Duración: 4–10+ días.

**Fase de Pupa**: Móviles pero no se alimentan. Duración: 2–4 días (metamorfosis completa).

**Fase Adulta**: Machos se alimentan de néctar. Hembras requieren **toma de sangre** para maduración de huevos. Longevidad: 2–4 semanas en campo (hasta 2 meses en laboratorio con azúcares).

### 2.2 El Ciclo Gonotrófico
Ciclo desde la toma de sangre hasta la oviposición: (1) búsqueda y hematofagia, (2) digestión y vitelogénesis, (3) búsqueda de sitio de oviposición, (4) puesta. Duración: **2–4 días** a ~28°C, se alarga con temperaturas más bajas. Hembras nulíparas (~42% en *An. gambiae*) requieren **múltiples tomas de sangre** dentro del mismo ciclo, aumentando la exposición al parásito y la transmisión.

### 2.3 Comportamiento de Apareamiento y Enjambres
Apareamiento en **enjambres al anochecer** sobre marcadores visuales del paisaje (arbustos, esquinas, líneas de horizonte). Machos y hembras se comportan como **"boids"** (modelo de bandadas): la convergencia armónica de frecuencias de batido de alas facilita el acoplamiento. *An. gambiae* y *An. coluzzii* comparten sitios de enjambre pero evitan hibridización por reconocimiento específico.

---

## 3. Comportamiento de las Hembras Adultas

### 3.1 Búsqueda de Hospedador (Host-Seeking)
Señales integradas: **CO₂** (señal más potente a larga distancia, detectada por receptores en palpos maxilares vía genes *Gr22-24*), **olores cutáneos** (ácido láctico, ácidos grasos volátiles de microbiota), **temperatura y humedad** (aproximación final), **señales visuales** (movimiento, color oscuro), **1-octen-3-ol** (sinérgico con CO₂). La sensibilidad es **edad-dependiente**: aumenta progresivamente con la madurez fisiológica (>3 días).

### 3.2 Preferencia de Hospedador: Antropofilia vs. Zoofilia
El Human Blood Index (HBI) varía entre 0.04 y >0.95: *An. gambiae s.s.* (HBI >95%), *An. funestus* (altamente antropofílicas); *An. arabiensis* (generalista, se alimenta de ganado si los humanos están protegidos). La presión selectiva por ITNs puede inducir evolución hacia mayor zoofilia.

### 3.3 Comportamiento de Reposo: Endofilia vs. Exofilia
Endofílicas (*An. gambiae s.s.*): descansan dentro de casas → susceptibles a IRS/ITNs. Exofílicas: descansan en exteriores → reducen eficacia de control intradomiciliario. *An. coluzzii* en São Tomé y Príncipe está evolucionando hacia mayor exofilia/zoofilia por presión de control.

### 3.4 Actividad Nocturna y Ciclos de Picadura
Actividad crepuscular-nocturna (picos 22:00–02:00). Algunas poblaciones desarrollan picadura diurna como adaptación a redes mosquiteras.

### 3.5 Alimentación de Azúcares
Ambos sexos requieren fuentes de azúcar (néctares, jugos, melaza) para energía de vuelo y longevidad. Diferentes fuentes vegetales tienen efectos diferenciales en la infección por *Plasmodium* (transmisión-reductoras vs. amplificadoras por metabolitos secundarios).

---

## 4. Hábitats Larvarios y Ecología Acuática

### 4.1 Características del Hábitat
Agua limpia y poco perturbada (oligotrófica), exposición solar, somera y estancada (charcos de lluvia, bordes de ríos, arrozales, huellas, cunetas, depósitos artificiales). pH 7.0–8.5. Temperatura del agua 16–34°C para desarrollo larvario. *An. gambiae* prefiere charcas temporales soleadas sin vegetación emergente.

### 4.2 Competencia y Depredación Larvaria
Reguladores principales: competencia intraespecífica por recursos (carrying capacity K), depredadores acuáticos (ditíscidos, arañas de agua, *Gambusia affinis*, copépodos, larvas de *Toxorhynchites*), patógenos (hongos *Metarhizium*, *Beauveria*; bacterias Bti, *Lysinibacillus sphaericus*).

### 4.3 Características Fisicoquímicas del Agua
| Variable | Efecto en *Anopheles* |
|---|---|
| Temperatura del agua | Controla tasa de desarrollo; óptima 25–28°C |
| pH | Neutral-alcalina (7.0–8.5) |
| Turbidez | Generalmente baja; prefieren aguas claras |
| Conductividad / TDS | Bajos niveles asociados con mayor presencia |
| Salinidad | Mayoría requiere agua dulce; *An. melas/merus* toleran salada |
| Oxígeno disuelto | Correlación positiva con presencia larval |
| Sombra/exposición solar | *An. gambiae* soleado; *An. funestus* sombreado |
| Profundidad | Aguas someras preferidas |
| Permanencia | Preferencia temporal (menos depredadores) |

---

## 5. Dispersión y Expansión Territorial

### 5.1 Vuelo de Corto Alcance
Dispersión normal ≤ **1–2 km** del hábitat larvario de origen. Estudios de captura-recaptura en Gambia: la mayoría se mueve en radio de ~1 km, poca migración entre localidades >5 km.

### 5.2 Migración Eólica de Largo Alcance (High-Altitude Wind-Assisted Migration)
Uno de los descubrimientos más importantes de la última década: *Anopheles* migra **cientos de kilómetros** a 120–290 m de altitud. Millones de mosquitos cruzan zonas áridas del Sahel anualmente. Vuelos de 6–11 h mantienen capacidad reproductiva y hematófaga. Este mecanismo explica la recolonización post-estación seca en el Sahel. Para *An. stephensi*, datos genómicos apuntan a viento en terrenos planos de Sudán facilitando su dispersión hacia el interior de África.

### 5.3 Expansión Territorial por Cambio Climático
El cambio climático modifica la distribución: expansión altitudinal (highlands africanas, Andes), latitudinal (mayores latitudes), estacionalidad prolongada. Revisión sistemática 2025 confirma desplazamientos de rango documentados en múltiples vectores a nivel global.

### 5.4 *Anopheles stephensi*: Caso de Invasión Reciente (2012–2026)
Nativo de Asia del Sur, detectado en **Djibouti en 2012**. Ha colonizado Etiopía, Sudán, Yemen, Somalia, Nigeria, Ghana, Níger. Es un **vector urbano** (se reproduce en depósitos artificiales). El mayor estudio genómico (645 mosquitos, 2025) determinó que fue una sola introducción desde Asia del Sur vía puerto marítimo, generando múltiples frentes de invasión. Llegó portando **resistencia a múltiples insecticidas** (piretroides, carbamatos). Amenaza a 126 millones de residentes urbanos.

---

## 6. Factores Ambientales que Modulan las Poblaciones

### 6.1 Temperatura
Factor más crítico (poiquilotermos):
| Parámetro | Rango óptimo | Efecto extremo |
|---|---|---|
| Desarrollo larvario | 25–28°C | Detención <16°C y >34°C; muerte >40°C |
| Longevidad adulta | Mayor 22–26°C | Disminuye en extremos |
| Ciclo gonotrófico | Se acorta con calor | Afecta tasa de picadura |
| EIP | Se acorta 20–35°C | <17°C el parásito no completa desarrollo |
| Fecundidad | Máxima ~25–28°C | Reducida en extremos |

Una variación de **1°C** puede cambiar la esperanza de vida adulta en más de una semana. Un aumento de 2°C incrementa la abundancia de adultos en ~15%.

### 6.2 Precipitación y Humedad Relativa
La lluvia crea hábitats larvarios. Humedad relativa >60% necesaria para supervivencia adulta en zonas áridas. Existe un **retraso (lag) de 2–4 semanas** entre precipitación y pico de adultos.

### 6.3 Estacionalidad y Sequía (Aestivación)
En el Sahel (5–7 meses de sequía), *An. gambiae* sobrevive mediante **aestivación**: reducción drástica de reproducción y metabolismo, incremento de tolerancia a desecación. Cambios moleculares incluyen alteraciones en metabolismo de lípidos y expresión génica diferencial. La supervivencia diaria durante aestivación es significativamente mayor.

### 6.4 Uso del Suelo y Paisaje
Arrozales (hábitats semi-permanentes de alta productividad), deforestación (incrementa temperatura local y charcas), urbanización (favorece *An. stephensi*, desfavorece especies rurales), altitud/baja pendiente (alta humedad topográfica → hábitats larvarios), proximidad a cuerpos de agua (factor crítico de dispersión).

---

## 7. El Parásito en el Mosquito: Período de Incubación Extrínseco (EIP)

El EIP (tiempo del parásito *Plasmodium* desde infección hasta transmisibilidad) es críticamente importante:
- A **25°C**, EIP de *P. falciparum* ≈ **10–12 días**
- <17°C: el parásito no completa el desarrollo
- La mayoría de mosquitos mueren antes de completar el EIP → intervenciones que aumentan levemente la mortalidad adulta tienen impacto desproporcionado
- Fluctuaciones diurnas aceleran el desarrollo del parásito vs. temperatura constante (debe incorporarse en modelos realistas)

---

## 8. Resistencia a Insecticidas: Una Crisis en Expansión

### 8.1 Mecanismos de Resistencia
| Mecanismo | Descripción | Genes |
|---|---|---|
| **Sitio blanco (kdr)** | Mutaciones en canal de sodio | *Vgsc* (L995F, L995S, N1570Y) |
| **Metabólica** | Sobreexpresión de enzimas detoxificadoras | *CYP6M2*, *CYP6P3*, *CYP9K1*, *GSTs* |
| **Cuticular** | Mayor grosor cuticular | Genes de cutícula |
| **Conductual** | Cambio en horario de actividad | Comportamental |

Un estudio de 2026 identificó la mutación **E205D en CYP6P3** como primer marcador diagnóstico de resistencia metabólica a piretroides en *An. gambiae* en África Occidental y Central. En *An. stephensi* invasivo, la resistencia fue **importada desde Asia** antes de llegar a África.

---

## 9. Modelos Matemáticos y de Simulación

### 9.1 Modelos Clásicos: Ross-Macdonald y Capacidad Vectorial
$$VC = \frac{m \cdot a^2 \cdot p^n \cdot e^{-g \cdot n}}{-\ln(p)}$$
Donde: *m* = densidad de mosquitos por humano, *a* = tasa de picadura, *p* = supervivencia diaria, *n* = EIP, *g* = tasa de mortalidad. La extensión espacial mediante matrices de dispersión permite modelar flujo de transmisión entre parches geográficos.

### 9.2 Modelos Compartimentales (ODE/DDE)
Permiten análisis de equilibrio, R₀, bifurcación, temperatura dependiente del tiempo y estacionalidad.

### 9.3 Modelos Basados en Agentes (ABM)
Los más adecuados para simulación detallada: heterogeneidad espacial explícita (GIS), estocasticidad, comportamientos emergentes, dinámicas de paisaje realistas. Plataformas existentes: **EMOD** (IDM, open-source), **OpenMalaria** (Swiss TPH, híbrido ABM/compartimental), **MALARIA TOOLS** (malmod, ciclo de vida completo), **MBites** (comportamiento adulto). El paper seminal de Depinay et al. (2004) representa la primera simulación orientada a objetos del ciclo de vida completo de *An. gambiae*.

### 9.4 Modelos Espaciales con GIS
Integración GIS para: identificar hábitats larvarios (pendiente, TWI, cobertura terrestre), modelar flujos de dispersión, incorporar datos climáticos de alta resolución, validar con datos de campo georreferenciados.

---

## 10. Taxonomía Completa de Variables para Simulación

### 10.1 Variables Biológicas del Ciclo de Vida
**Huevo**: tasa de oviposición (50–200/ciclo), variabilidad individual de fecundidad, mortalidad diaria, tolerancia a desecación (nula), temperatura de incubación.
**Larva**: 4 instares, tasa de desarrollo (curva Sharpe-DeMichele), peso larvario, carrying capacity K (mg biomasa/m²), mortalidad densidad-dependiente, mortalidad por predación (retraso temporal), temperatura mínima (~16°C) y letal (40°C).
**Pupa**: duración temperatura-dependiente, mortalidad, ratio emergencia (~1:1).
**Adulto**: longevidad (supervivencia diaria ~0.9), duración ciclo gonotrófico, paridad, tomas múltiples (~42% nulíparas), tasa de picadura *a*, HBI, endo/exofilia, alimentación de azúcares.
**Parásito**: EIP temperatura-dependiente, prevalencia esporozoitos, tasa de infección, susceptibilidad a *Plasmodium*.

### 10.2 Variables Ambientales y Climáticas
**Temperatura**: min/max/media diaria, temperatura del agua, amplitud de fluctuación diurna, grados-día acumulados.
**Precipitación e Hidrología**: precipitación diaria (mm), intensidad/duración, cobertura de hábitats activos post-lluvia, evapotranspiración, volumen/permanencia de hábitats, TWI, proximidad a cuerpos de agua.
**Humedad**: HR (%), déficit de presión de vapor.
**Viento**: velocidad y dirección (alta altitud + baja altitud).
**Cobertura Terrestre y Paisaje**: uso del suelo, elevación/pendiente (DEM), NDVI, exposición solar, sombra, densidad de hábitats larvarios, geometría de hábitats.

### 10.3 Variables de Comportamiento y Dispersión
Radio de dispersión (≤2 km), probabilidad de migración eólica, velocidad de vuelo, selección de hábitat de oviposición (distancia, calidad, señales), selección de hospedador, fidelidad a sitios, umbrales de enjambre, densidad mínima viable de machos, umbral de HR para aestivación (<40%).

### 10.4 Variables Poblacionales y de Especie
Composición de especies, estructura genética (frecuencias alélicas, inversiones cromosómicas), frecuencias de resistencia (*Vgsc*, *CYP*), ratio de especies crípticas en simpatría, competencia interespecífica, tasa de hibridización.

### 10.5 Variables de Control y Antropogénicas
Cobertura/tipo de ITNs/LLINs, IRS (insecticida, cobertura, duración), larvicidas, densidad de hospedadores humanos/animales, tipo de vivienda, comportamiento humano, presencia de ganado (zooprofilaxis), gene drives (prospectivo).

---

## 11. Resistencia Genética y Evolución

### 11.1 Inversiones Cromosómicas y Adaptación Local
Mecanismo central de adaptación rápida: funcionan como "supergenes". 2La (resistencia a desecación), 2Rb (adaptación a sabana vs. bosque). En *An. funestus*, una sola inversión puede generar hasta **92% de aislamiento reproductivo** entre poblaciones.

### 11.2 Genómica y Vigilancia de la Resistencia
El **Proyecto An. gambiae 1000 Genomes** ha secuenciado miles de mosquitos de toda África, revelando estructura poblacional fina y variantes de resistencia. Vigilancia genómica continental esencial para calibrar simulaciones con parámetros localmente relevantes.

---

## 12. Tecnologías de Control Emergentes

### 12.1 Gene Drive
Sistemas CRISPR-Cas9 para propagación más rápida que herencia mendeliana. Dos tipos: supresión (colapsan poblaciones interrumpiendo genes como doublesex) y modificación (reemplazan alelos de capacidad vectorial por refractarios). Modelos en 16 entornos africanos muestran que el impacto depende de la ecología local. La resistencia en sitios conservados es una limitación importante.

### 12.2 Attractive Toxic Sugar Baits (ATSB)
Cebos de azúcar que atraen a ambos sexos y los matan con insecticida.

---

## 13. Implicaciones para el Diseño de la Simulación

Arquitectura recomendada: **ABM Espacio-Temporal** con 8 capas:
1. **Capa geoespacial**: DEM, uso del suelo, cuerpos de agua, temperatura, precipitación (resolución diaria ideal)
2. **Motor de hábitat**: modelo hidrológico simple (hábitats activos, volumen, temperatura del agua)
3. **Agente mosquito**: propiedades (especie, estadio, edad, peso, estado reproductivo/infección, GPS) con reglas probabilísticas
4. **Motor de comportamiento adulto**: host-seeking (CO₂, olor), oviposición, dispersión, reposo, enjambres
5. **Motor de dispersión**: Gaussiana truncada (local) + migración eólica (viento ERA5)
6. **Módulo de parásito**: EIP intra-mosquito → capacidad vectorial emergente
7. **Módulo de control**: ITNs, IRS, larvicidas, gene drive
8. **Validación**: calibración con datos entomológicos de campo (densidad, prevalencia esporozoitos, diversidad)

Plataformas base: **EMOD** (Python/C++) o **Mesa** (Python), integrando ERA5/CHIRPS y Copernicus/MODIS.

---

## Conclusiones y Brechas de Conocimiento

La simulación realista requiere modelar simultáneamente: biología del ciclo de vida, comportamiento complejo, dinámica del hábitat acuático, dispersión multi-escala, variabilidad inter/ intraespecífica, y cambio climático. Brechas críticas:
1. Tasas de supervivencia/desarrollo larval en temperaturas extremas para especies no-*An. gambiae*
2. Mecanismos de orientación al hábitat de oviposición (señales químicas del agua)
3. Cuantificación de migración eólica inter-estacional y determinantes meteorológicos
4. Datos de campo del ciclo de vida de *An. stephensi* en ecosistemas africanos invadidos
5. Impacto de diversidad de fuentes de azúcar en longevidad y capacidad vectorial
6. Datos genómicos poblacionales para calibrar resistencia a insecticidas con resolución local

---

## References

1. [Malaria - World Health Organization (WHO)](https://www.who.int/data/gho/data/themes/malaria)
2. [World malaria report 2025 - World Health Organization (WHO)](https://www.who.int/teams/global-malaria-programme/reports/world-malaria-report-2025)
3. [Anopheles - Britannica](https://www.britannica.com/animal/Anopheles)
4. [Anopheles - Wikipedia](https://en.wikipedia.org/wiki/Anopheles)
5. [Bionomics, taxonomy, and distribution of the major malaria vector - PubMed](https://pubmed.ncbi.nlm.nih.gov/18178531/)
6. [Table 1 - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC12568711/table/T1/)
7. [The dominant Anopheles vectors of human malaria in Africa, Europe - AGRIS](https://agris.fao.org/search/en/providers/122535/records/65dffdca63b8185d9cb089bb)
8. [A global map of dominant malaria vectors - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC3349467/)
9. [Anopheles gambiae complex and disease transmission in Africa](https://academic.oup.com/trstmh/article-lookup/doi/10.1016/0035-9203(74)90035-2)
10. [Chromosomal Inversions, Natural Selection and Adaptation in Anopheles funestus - PMC](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC3002248/)
11. [Chromosome inversions and ecological plasticity - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC5340588/)
12. [Chromosome Inversions, Genomic Differentiation and Speciation in Anopheles gambiae - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC3603965/)
13. [Systems genetic analysis of inversion polymorphisms - PNAS](https://www.pnas.org/doi/10.1073/pnas.1806760115)
14. [Genomic Analysis Reveals a New Cryptic Taxon - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC12051790/)
15. [Unveiling mosquito cryptic species and their reproductive isolation - PMC](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7754467/)
16. [Mosquito Life Cycle - CDC](https://www.cdc.gov/mosquitoes/pdfs/AnophelesLifeCycle-ENG.pdf)
17. [The Life Cycle of the Anopheles Mosquito - YouTube](https://www.youtube.com/watch?v=KzQS220sHHE)
18. [A simulation model of African Anopheles ecology - PMC](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC514565/)
19. [The Anopheles mosquito lifecycle - YouTube](https://www.youtube.com/watch?v=qoRRamzumBk)
20. [Anopheles gambiae feeding and survival on honeydew - PubMed](https://pubmed.ncbi.nlm.nih.gov/15189234/)
21. [Mating Behavior and Gonotrophic Cycle - JELS](https://www.jelsciences.com/articles/jbres1398.php)
22. [Mosquito Gonotrophic Cycle and Multiple Feeding Potential](https://scispace.com/pdf/mosquito-gonotrophic-cycle-and-multiple-feeding-potential-bj0vzg4gkl.pdf)
23. [Multiple Blood Meals as a Reproductive Strategy - JME](https://academic.oup.com/jme/article-abstract/30/6/975/2221327)
24. [Diet and Oviposition Deprivation Effects - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9233601/)
25. [Swarming Behavior in Anopheles gambiae - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC8755986/)
26. [Swarming and mate selection in Anopheles gambiae - PubMed](https://pubmed.ncbi.nlm.nih.gov/37392071/)
27. [Spatial distribution and male mating success - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC3146442/)
28. [Swarming behaviour in natural populations - PubMed](https://pubmed.ncbi.nlm.nih.gov/24370676/)
29. [Natural swarming behaviour of the molecular M form - ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0035920303801104)
30. [Harmonic convergence coordinates swarm mating - Nature](https://www.nature.com/articles/s41598-021-03236-5)
31. [Human attractive cues and mosquito host-seeking behavior - ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S1471492221002373)
32. [Human attractive cues and mosquito host-seeking behavior - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC10789295/)
33. [Odorant ligands for the CO2 receptor - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC6385339/)
34. [Functional development of carbon dioxide detection - PubMed](https://pubmed.ncbi.nlm.nih.gov/26056246/)
35. [Life cycle Anopheles mosquito - Nature Today](https://www.naturetoday.com/intl/en/observations/umubu-radar/mosquitoes1/life-cycle-anopheles-mosquito)
36. [Age-dependent regulation of host seeking - Nature](https://www.nature.com/articles/s41598-019-46220-w)
37. [Feeding and resting behaviour - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC1964787/)
38. [Genetic Basis of Host Preference - PubMed](https://pubmed.ncbi.nlm.nih.gov/27631375/)
39. [Host preference and resting behavior of An. coluzzii - PubMed](https://pubmed.ncbi.nlm.nih.gov/41812224/)
40. [Natural Plant Sugar Sources - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC3024498/)
41. [Dryad Dataset](https://datadryad.org/stash/dataset/doi:10.5061/dryad.9s690)
42. [Anopheles larval species composition - PubMed](https://pubmed.ncbi.nlm.nih.gov/32046734/)
43. [An. arabiensis larval habitats characterization - PubMed](https://pubmed.ncbi.nlm.nih.gov/39979987/)
44. [Water Physicochemical Parameters and Microbial - PubMed](https://pubmed.ncbi.nlm.nih.gov/35920087/)
45. [Physico-chemical characteristics of Anopheles breeding sites](https://academicjournals.org/article/article1380211116_Oyewole%20et%20al.pdf)
46. [Anopheles larval ecology in Dire Dawa - PubMed](https://pubmed.ncbi.nlm.nih.gov/41646345/)
47. [Combined effect of physico-chemical and microbial quality - PMC](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10004544/)
48. [Temperature-related duration of aquatic stages - PubMed](https://pubmed.ncbi.nlm.nih.gov/15189243/)
49. [Predatory and competitive interaction - PubMed](https://pubmed.ncbi.nlm.nih.gov/34419140/)
50. [Landscape Movements of Anopheles gambiae - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC3715529/)
51. [Windborne long-distance migration - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC11095661/)
52. [Wind-assisted high-altitude dispersal - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC10337859/)
53. [Effects of High-Altitude Windborne Migration - PubMed](https://pubmed.ncbi.nlm.nih.gov/32667040/)
54. [New malaria mosquito causing outbreaks - GAVI](https://www.gavi.org/vaccineswork/new-malaria-mosquito-causing-outbreaks-african-cites-heres-where-it-came)
55. [Ecology of Anopheles Mosquitoes under Climate - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC3767301/)
56. [Climate-change driven range shifts in mosquito vectors - bioRxiv](https://www.biorxiv.org/content/10.1101/2025.03.25.645279v1.full.pdf)
57. [Vector alert: Anopheles stephensi invasion - WHO](https://www.who.int/docs/default-source/young-leaders-blog/stephensi-info-note-august2019.pdf)
58. [The origin, invasion history and resistance architecture - PubMed](https://pubmed.ncbi.nlm.nih.gov/40196515/)
59. [Effect of Temperature on Anopheles Population - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC3828393/)
60. [Effects of Temperature on Development and Survival - PubMed](https://pubmed.ncbi.nlm.nih.gov/34299706/)

---

## Relevancia para MalariaSentinel / Centinela

Este documento constituye la **base biológica fundamental** del proyecto Centinela. Cada sección alimenta directamente un componente del ABM: la Sección 2 (ciclo de vida) parametriza las transiciones de estadio en `MosquitoAgent`; la Sección 3 (comportamiento de hembras) define las reglas de host-seeking, oviposición y resting en el motor conductual; la Sección 4 (hábitats larvarios) establece las variables fisicoquímicas para `HabitatPatch`; la Sección 5 (dispersión) provee los dos regímenes de movimiento (local Gaussiano + eólico) para el motor de dispersión; la Sección 6 (factores ambientales) define las dependencias climáticas del modelo; la Sección 8 (resistencia) parametriza el módulo genético; y la Sección 10 es el **catálogo maestro de variables** (~80 entradas con rangos numéricos) que debe traducirse directamente al esquema de datos del ABM. Las 6 brechas de conocimiento identificadas guían prioridades de investigación futura del proyecto.
