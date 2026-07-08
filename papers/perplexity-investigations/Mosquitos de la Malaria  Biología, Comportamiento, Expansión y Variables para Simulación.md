# Mosquitos de la Malaria: Biología, Comportamiento, Expansión y Variables para Simulación
## Resumen Ejecutivo
La malaria es una de las enfermedades infecciosas más devastadoras de la historia humana. En 2024 se registraron aproximadamente **282 millones de casos** y **610.000 muertes** en todo el mundo, con la Región Africana de la OMS cargando el 94% de los casos y el 95% de las muertes[^1][^2]. El único vector del parásito *Plasmodium* al ser humano es el mosquito del género *Anopheles*, con más de 450 especies descritas, de las cuales aproximadamente 70 son vectores competentes de malaria humana[^3][^4]. Comprender en profundidad la biología, el comportamiento y la dinámica poblacional de este mosquito es fundamental para diseñar simulaciones predictivas que modelen su evolución y expansión territorial.

***
## 1. Taxonomía y Diversidad de Especies
### 1.1 Clasificación General
El género *Anopheles* pertenece a la familia Culicidae, orden Díptera. Con más de 450 especies descritas[^3], solo un subconjunto de ellas transmite malaria humana. Las especies se agrupan en complejos de especies crípticas o "especies hermanas" que son morfológicamente casi idénticas pero presentan diferencias biológicas y de capacidad vectorial cruciales[^5]. Los avances en biología molecular han permitido distinguirlas mediante análisis de ADN[^5].
### 1.2 Principales Vectores por Región Geográfica
| Región | Especies Principales | Parásito Transmitido |
|---|---|---|
| **África Subsahariana** | *An. gambiae s.s.*, *An. coluzzii*, *An. arabiensis*, *An. funestus*, *An. moucheti*, *An. nili*, *An. melas*, *An. merus* | Principalmente *P. falciparum*[^6][^7] |
| **Asia del Sur/Sudeste** | *An. stephensi*, *An. dirus*, *An. minimus*, *An. fluviatilis*, *An. culicifacies*, *An. maculatus*, *An. sundaicus* | *P. falciparum*, *P. vivax*[^5] |
| **América** | *An. darlingi*, *An. albimanus*, *An. freeborni*, *An. pseudopunctipennis* | *P. vivax*, *P. falciparum*[^8] |
| **Europa y Oriente Medio** | *An. atroparvus*, *An. labranchiae*, *An. messeae*, *An. sacharovi*, *An. sergentii* | *P. vivax* (actualmente eliminado de Europa)[^7] |
### 1.3 El Complejo *Anopheles gambiae* — Modelo Más Estudiado
El complejo *An. gambiae sensu lato* es la especie más importante de malaria en el mundo[^9]. Comprende al menos **8 especies crípticas**, incluyendo[^6][^9]:

- **_An. gambiae s.s._** — vector primario de *P. falciparum* en África Subsahariana, altamente antropofílico y endofílico.
- **_An. coluzzii_** — vector principal en África Occidental; antes llamado "forma M" de *An. gambiae*.
- **_An. arabiensis_** — más generalista en cuanto a huésped (zoo/antropofílico), más tolerante a condiciones áridas.
- **_An. melas_** — especie de agua salada, costa oeste de África.
- **_An. merus_** — especie de agua salada, costa este de África.
- **_An. quadriannulatus_** — vector de menor impacto, generalmente zoofílico.
- **_An. amharicus_** — descubierto más recientemente en Etiopía.
- **_An. fontenillei_** — especie más reciente del complejo.

Las inversiones cromosómicas polimórficas dentro de este complejo juegan un papel fundamental en la adaptación local a diferentes entornos (áridos, húmedos, altas altitudes)[^10][^11][^12]. Por ejemplo, la inversión **2La** está asociada con mayor resistencia a la desecación en *An. gambiae*, permitiendo la colonización de hábitats más secos[^13][^11].
### 1.4 Especies Crípticas Emergentes
En 2025, un análisis genómico identificó un nuevo taxón críptico dentro del complejo *An. gambiae*[^14]. La detección de nuevas especies crípticas es clínicamente relevante porque estas pueden variar enormemente en capacidad vectorial, preferencia de hospedador y resistencia a insecticidas[^15].

***
## 2. Ciclo de Vida y Biología Reproductiva
### 2.1 Las Cuatro Etapas del Ciclo de Vida
*Anopheles* es holometábolo: pasa por cuatro fases: huevo, larva, pupa y adulto. El tiempo total de huevo a adulto es de **10 a 18+ días** según temperatura y especie[^3][^16].

**Fase de Huevo**
- Las hembras adultas depositan entre **50 y 200 huevos** directamente sobre la superficie del agua[^16][^17].
- Los huevos de *Anopheles* se depositan de forma individual (no en "balsas" como *Culex*) y poseen flotadores laterales para mantenerse en la superficie[^17].
- La eclosión ocurre en **24 a 48 horas** en condiciones cálidas[^17].
- Crítico: los huevos de *Anopheles* **no toleran la desecación** y mueren en horas si el agua se evapora[^16][^18]. Esto contrasta con *Aedes*, cuyos huevos pueden sobrevivir meses en suelo seco.

**Fase Larvaria**
- Las larvas pasan por **4 estadios (instares)** antes de convertirse en pupas[^16][^17].
- Característica diagnóstica: las larvas de *Anopheles* descansan **paralelas a la superficie del agua**, respirando mediante placas espiraculares en el abdomen (no a través de un sifón como *Culex*)[^3][^17].
- Se alimentan de microorganismos (algas, bacterias, detritos) presentes en el agua[^17].
- Duración: **4 a 10+ días** dependiendo de temperatura, nutrientes y densidad poblacional[^16].

**Fase de Pupa**
- Las pupas son móviles ("tumblers") pero no se alimentan[^17].
- Duración: **2 a 4 días**, durante los cuales ocurre la metamorfosis completa[^19].

**Fase Adulta**
- Los machos emergen primero y se alimentan exclusivamente de néctar vegetal y azúcares[^3].
- Las hembras requieren una **toma de sangre** para la maduración de los huevos (excepto en algunas especies autogénicas raras)[^3][^16].
- Longevidad adulta: **2 a 4 semanas** en condiciones naturales, aunque en laboratorio pueden superar los 2 meses si tienen acceso a azúcares[^3][^20].
### 2.2 El Ciclo Gonotrófico
El **ciclo gonotrófico** es el ciclo que va desde la toma de sangre hasta la oviposición, y se repite a lo largo de la vida adulta de la hembra[^21][^22]. Sus fases son:

1. **Búsqueda y toma de sangre** (hematofagia)
2. **Digestión de la sangre y vitelogénesis** (desarrollo de los ovarios)
3. **Búsqueda de sitio de oviposición**
4. **Puesta de huevos**

La duración del ciclo gonotrófico es de **2 a 4 días** a temperaturas óptimas (~28°C), aunque se alarga significativamente con temperaturas más bajas[^21]. Algunas hembras, especialmente nulíparas (primera puesta), requieren **múltiples tomas de sangre** dentro del mismo ciclo para completar la vitelogénesis[^23][^24]. Esta característica tiene implicaciones epidemiológicas importantes porque aumenta la probabilidad de exposición a y transmisión del parásito.
### 2.3 Comportamiento de Apareamiento y Enjambres
El apareamiento en *Anopheles* ocurre durante **enjambres al anochecer**[^25][^26]. Los machos se congregan en sitios específicos ("marcadores de enjambre"), frecuentemente sobre objetos visibles en el paisaje (arbustos, esquinas de edificios, líneas de horizonte)[^27][^28]. Las hembras virgenes vuelan hacia el enjambre, se aparean brevemente en vuelo, y parten copuladas[^26][^29].

Un hallazgo reciente muestra que tanto machos como hembras de *An. gambiae* se comportan como **"boids"** (similar a los modelos de bandadas de pájaros), donde la coincidencia de frecuencias de batido de alas (convergencia armónica) facilita el acoplamiento[^26][^30]. *An. gambiae* y *An. coluzzii* comparten a veces los mismos sitios de enjambre pero evitan la hibridización mediante mecanismos de reconocimiento específico de especie[^28].

***
## 3. Comportamiento de las Hembras Adultas
### 3.1 Búsqueda de Hospedador (Host-Seeking)
Las hembras de *Anopheles* utilizan una combinación de señales físicas y químicas para localizar sus hospedadores[^31][^32]:

- **CO₂**: La señal más potente a larga distancia. Las hembras detectan el CO₂ exhalado mediante receptores específicos en sus palpos maxilares (genes *Gr22*, *Gr23*, *Gr24*)[^33][^34]. El CO₂ activa el vuelo orientado al viento (*upwind flight*).
- **Olores cutáneos**: Compuestos producidos por la microbiota cutánea humana (ácido láctico, ácidos grasos volátiles, aldeídos). La composición de la microbiota varía entre individuos, explicando por qué algunas personas son más "atractivas" para los mosquitos[^31][^32].
- **Temperatura y humedad**: La hembra integra señales térmicas e higrométricas durante la aproximación final al hospedador[^31].
- **Señales visuales**: El movimiento y el color oscuro son factores de orientación a corta distancia[^35].
- **1-octen-3-ol**: Un compuesto clave en el aliento y sudor de mamíferos que actúa sinérgicamente con el CO₂[^36].

La búsqueda de hospedador es **edad-dependiente**: las hembras jóvenes (<3 días) tienen menor sensibilidad al CO₂ y menor propensión a la hematofagia; la sensibilidad aumenta progresivamente con la madurez fisiológica[^36].
### 3.2 Preferencia de Hospedador: Antropofilia y Zoofilia
Las especies varían enormemente en su preferencia por hospedadores humanos versus animales[^37][^38]:

- **Altamente antropofílicas**: *An. gambiae s.s.* (hasta >95% de comidas de sangre de humanos), *An. funestus*.
- **Generalistasy zoofílicas**: *An. arabiensis* puede alimentarse de ganado cuando los humanos están protegidos por redes mosquiteras[^38]. Esta plasticidad tiene implicaciones cruciales para el control mediante redes: la presión selectiva puede llevar a la evolución de comportamientos más zoofílicos[^38].
- **El "Human Blood Index" (HBI)**: proporción de comidas tomadas de humanos, varía entre 0.04 y >0.95 según especie, condiciones locales y presión de control[^39].
### 3.3 Comportamiento de Reposo: Endofilia vs. Exofilia
- **Endofílicas**: descansan dentro de las casas después de alimentarse (ej. *An. gambiae s.s.*). Esto las hace muy susceptibles al rociado residual interior (IRS) y las redes insecticidas (ITNs)[^39].
- **Exofílicas**: descansan en exteriores, reduciendo la eficacia de las herramientas de control intradomiciliario[^39]. Estudios recientes en São Tomé y Príncipe muestran que *An. coluzzii* está evolucionando hacia mayor exofilia y zoofilia en respuesta a programas intensivos de control[^39].
### 3.4 Actividad Nocturna y Ciclos de Picadura
La mayoría de los *Anopheles* son activos entre el **atardecer y el amanecer** (actividad crepuscular-nocturna), con picos de actividad tipicamente entre las 22:00 y 02:00[^3][^35]. Sin embargo, algunas poblaciones han desarrollado comportamientos de picadura diurna como adaptación a las redes mosquiteras nocturnas[^3].
### 3.5 Alimentación de Azúcares
Además de la sangre, tanto machos como hembras de *Anopheles* requieren **fuentes de azúcar** (néctares florales, jugos de fruta, melaza de insectos) para cubrir sus necesidades energéticas de vuelo y longevidad[^20][^40]. La disponibilidad de fuentes de azúcar afecta significativamente la supervivencia del adulto y, por ende, la capacidad vectorial[^20][^41]. Diferentes fuentes vegetales tienen efectos diferenciales en la infección por *Plasmodium*, con algunas actuando como "transmisión-reductora" y otras como "transmisión-amplificadora" por sus metabolitos secundarios[^41].

***
## 4. Hábitats Larvarios y Ecología Acuática
### 4.1 Características del Hábitat
*Anopheles* muestra preferencias de hábitat de oviposición específicas[^42][^43]:

- **Agua limpia, poco perturbada**: en contraste con *Culex*, que tolera aguas más contaminadas. Los estudios muestran que la abundancia de *Anopheles* se correlaciona con agua oligotrófica (pocas bacterias heterótrofas)[^44].
- **Exposición solar**: *An. gambiae* prefiere charcas temporales soleadas con escasa vegetación emergente[^42].
- **Agua somera y estancada**: charcos de lluvia, bordes de ríos, arrozales, huellas de animales, cunetas de caminos, depósitos artificiales de agua[^45][^46].
- **pH**: ligeramente alcalino o neutro (≈ 7.0–8.5)[^43][^47].
- **Temperatura del agua**: entre 16°C y 34°C para el desarrollo larvario[^48].
### 4.2 Competencia y Depredación Larvaria
Los principales reguladores de la densidad larvaria son[^49][^18]:

- **Competencia intraespecífica e interespecífica** por recursos alimenticios (la "carrying capacity" del hábitat).
- **Depredadores acuáticos**: coleópteros ditíscidos (escarabajos acuáticos), arañas de agua (Cybaeidae), peces larvífagos (*Gambusia affinis*), copépodos, larvas de *Toxorhynchites*.
- **Patógenos larvarios**: hongos (*Metarhizium*, *Beauveria*), microsporidios, bacterias (*Bacillus thuringiensis israelensis* — Bti, *Lysinibacillus sphaericus*).
### 4.3 Características Fisicoquímicas del Agua
Las variables que los estudios han identificado como determinantes de la abundancia larvaria incluyen[^43][^44][^42]:

| Variable | Efecto en *Anopheles* |
|---|---|
| Temperatura del agua | Controla tasa de desarrollo; óptima 25–28°C |
| pH | Preferencia neutral-alcalina (7.0–8.5) |
| Turbidez | Generalmente baja; prefieren aguas más claras |
| Conductividad eléctrica / TDS | Bajos niveles asociados con mayor presencia |
| Salinidad | Varía: la mayoría requiere agua dulce; *An. melas* y *An. merus* toleran agua salada |
| Oxígeno disuelto | Correlación positiva con la presencia larval |
| Sombra/exposición solar | *An. gambiae* prefiere hábitats soleados; *An. funestus* prefiere sombreados |
| Presencia de vegetación emergente | *An. gambiae* la evita; otras especies la prefieren |
| Profundidad del agua | Aguas someras preferidas |
| Permanencia del hábitat | Preferencia de hábitats temporales (menos depredadores) |

***
## 5. Dispersión y Expansión Territorial
### 5.1 Vuelo de Corto Alcance
En condiciones normales, los *Anopheles* adultos **no se dispersan más de 1–2 km** de su hábitat larvario de origen[^16][^50]. Los estudios de captura-recaptura en Gambia demostraron que la mayoría de *An. gambiae* se mueven dentro de un radio de ~1 km, con poca migración entre localidades separadas por >5 km[^50].
### 5.2 Migración Eólica de Largo Alcance (High-Altitude Wind-Assisted Migration)
Uno de los descubrimientos más importantes de la última década es la demostración de que *Anopheles* puede migrar **cientos de kilómetros** a través del viento, viajando a alturas de 120–290 metros sobre el suelo[^51][^52][^53]:

- Estudios con redes de captura a alta altitud en la región del Sahel mostraron que millones de mosquitos cruzan zonas áridas estacionales cada año[^51][^52].
- Experimentos de supervivencia post-migración confirmaron que los mosquitos sobreviven vuelos de 6–11 horas a alta altitud y mantienen su capacidad reproductiva y hematófaga[^53].
- Se propone que esta migración eólica explica el mantenimiento de poblaciones en el Sahel durante la estación seca y la recolonización de zonas tras la llegada de las lluvias[^51].
- Para *An. stephensi*, los datos genómicos apuntan a que el viento en terrenos planos de Sudán facilitó su dispersión hacia el interior de África[^54].
### 5.3 Expansión Territorial por Cambio Climático
El cambio climático está modificando la distribución geográfica de *Anopheles* de varias maneras[^55][^56]:

- **Expansión altitudinal**: hacia zonas montañosas previamente demasiado frías (Highlands africanas, Andes).
- **Expansión latitudinal**: hacia latitudes más altas en ambos hemisferios.
- **Estacionalidad prolongada**: la transmisión dura más meses al año en zonas con malaria existente.
- Análisis sistemáticos publicados en 2025 confirman desplazamientos de rango documentados en múltiples vectores mosquiteros a nivel global, con proyecciones preocupantes para zonas urbanas densamente pobladas[^56].
### 5.4 *Anopheles stephensi*: Caso de Invasión Reciente (2012–2026)
*An. stephensi* es el caso más alarmante de expansión vectorial invasiva contemporánea[^57][^54][^58]:

- Nativa de Asia del Sur y la Península Arábiga, fue detectada por primera vez en **Djibouti en 2012** y ha colonizado progresivamente Etiopía, Sudán, Yemen, Somalia, Nigeria, Ghana y Níger[^57][^54].
- A diferencia de los vectores africanos tradicionales que son rurales, *An. stephensi* es un **vector urbano** que se reproduce en depósitos artificiales de agua (cisternas, barriles, piletas)[^57][^54].
- El mayor estudio genómico hasta la fecha (645 mosquitos secuenciados) publicado en 2025 determinó que el origen fue una sola introducción desde Asia del Sur vía puerto marítimo a Djibouti, que luego generó múltiples frentes de invasión[^58][^54].
- Llegó a África ya portando **resistencia a múltiples insecticidas** (piretroides, carbamatos) derivada de genes de detoxificación asiáticos, lo que complica su control[^58][^54].
- Amenaza a **126 millones de residentes urbanos** en un continente donde la malaria era principalmente rural[^58].

***
## 6. Factores Ambientales que Modulan las Poblaciones de Mosquitos
### 6.1 Temperatura
La temperatura es el factor ambiental más crítico para *Anopheles*, dado que son poiquilotermos (ectotermos). Sus efectos abarcan todas las etapas del ciclo de vida[^59][^60][^61]:

| Parámetro biológico | Rango óptimo de temperatura | Efecto de la temperatura extrema |
|---|---|---|
| Desarrollo larvario completo | 25–28°C | Detención <16°C y >34°C; muerte >40°C |
| Tasa de desarrollo larval | Mayor con más calor (hasta 34°C) | Inversa: más temperatura = menos días |
| Supervivencia larvaria | Mayor a 20–26°C | Alta mortalidad en extremos |
| Longevidad adulta | Mayor entre 22–26°C | Aumenta a bajas T°; disminuye a altas T° |
| Duración del ciclo gonotrófico | Se acorta con mayor temperatura | Afecta directamente la tasa de picadura |
| Período de incubación extrínseco (EIP) | Se acorta entre 20–35°C | Por debajo de 17°C, el parásito no completa desarrollo |
| Fecundidad | Máxima ~25–28°C | Reducida en temperaturas extremas |

Una variación de tan solo **1°C** puede cambiar la esperanza de vida de un mosquito adulto en más de una semana, con importantes consecuencias para la transmisión[^18]. Modelos computacionales muestran que un aumento de 2°C incrementa la abundancia de adultos de *An. gambiae* en ~15%[^18].
### 6.2 Precipitación y Humedad Relativa
La lluvia es fundamental para crear y mantener los hábitats larvarios[^62]:

- La lluvia crea charcas temporales, incrementando drásticamente la disponibilidad de sitios de oviposición.
- La humedad relativa >60% es necesaria para la supervivencia adulta en zonas áridas (por debajo de este umbral, la desecación mata a los adultos rápidamente)[^18].
- La humedad afecta la velocidad de evaporación de los hábitats larvarios, impactando la duración disponible para el desarrollo acuático.
- Existe un retraso ("lag") entre la precipitación y el pico de adultos, típicamente de 2–4 semanas[^63].
### 6.3 Estacionalidad y Sequía (Aestivación)
En el Sahel africano, donde la estación seca puede durar 5–7 meses sin agua superficial disponible, *An. gambiae* sobrevive mediante un proceso de **aestivación** (dormancia estival)[^64][^65][^66]:

- Durante la aestivación, los mosquitos reducen drásticamente la reproducción y el metabolismo, mientras incrementan la tolerancia a la desecación.
- Los cambios moleculares incluyen alteraciones en el metabolismo de lípidos, expresión génica diferencial y cambios fisiológicos en los espiráculos[^67].
- La probabilidad de supervivencia diaria durante la aestivación es significativamente mayor que en temporada normal, compensando la ausencia de reproducción[^66].
- Este fenómeno es crucial para la dinámica espaciotemporal: el mismo pool genético "reaparece" al inicio de la estación lluviosa, sincronizando el pico de transmisión con las primeras lluvias[^66].
### 6.4 Uso del Suelo y Paisaje
El tipo de cobertura terrestre modifica profundamente la disponibilidad de hábitats larvarios[^68][^69]:

- **Arrozales**: crean hábitats semi-permanentes de alta productividad para *An. gambiae* y *An. arabiensis*.
- **Deforestación**: incrementa la temperatura local y crea charcas temporales adicionales.
- **Urbanización**: favorece a *An. stephensi* (depósitos artificiales) y desfavorece a especies rurales dependientes de agua superficial natural.
- **Altitud (DEM)**: las zonas de baja pendiente y alta humedad topográfica predicen la presencia de hábitats larvarios[^69].
- **Proximidad a cuerpos de agua**: factor crítico para la dispersión adulta.

***
## 7. El Parásito en el Mosquito: Período de Incubación Extrínseco (EIP)
El **Período de Incubación Extrínseco (EIP)** es el tiempo que tarda el parásito *Plasmodium* en completar su ciclo sexual (esporogonia) dentro del mosquito, desde que este se infecta hasta que puede transmitir el parásito en una picadura subsecuente[^70][^71]. Este período es críticamente importante porque:

- A **25°C**, el EIP de *P. falciparum* es de aproximadamente **10–12 días**[^70].
- A temperaturas más bajas el EIP se alarga; por debajo de ~17°C, el parásito no completa el desarrollo y la transmisión cesa[^71].
- La mayoría de los mosquitos mueren antes de que el parásito complete el EIP, lo que explica por qué las intervenciones que aumentan levemente la mortalidad del adulto tienen un impacto desproporcionado en la transmisión[^70].
- Las fluctuaciones diurnas de temperatura (vs. temperatura constante) aceleran el desarrollo del parásito, lo que debe incorporarse en modelos realistas[^71][^72].

***
## 8. Resistencia a Insecticidas: Una Crisis en Expansión
### 8.1 Mecanismos de Resistencia
Los *Anopheles* han desarrollado resistencia a virtualmente todas las clases de insecticidas disponibles[^73][^74]:

| Mecanismo | Descripción | Genes implicados |
|---|---|---|
| **Resistencia de sitio blanco (kdr)** | Mutaciones en el canal de sodio que reducen la unión del piretroide | *Vgsc* (L995F, L995S, N1570Y) |
| **Resistencia metabólica** | Sobreexpresión de enzimas detoxificadoras | *CYP6M2*, *CYP6P3*, *CYP9K1*, *GSTs* |
| **Resistencia cuticular** | Mayor grosor cuticular que reduce la penetración | Genes de cutícula |
| **Resistencia conductual** | Cambio en horario de actividad para evitar insecticida | Comportamental |

- Un estudio de 2026 identificó la mutación **E205D en CYP6P3** como marcador diagnóstico de resistencia metabólica a piretroides en *An. gambiae* en África Occidental y Central, el primero de su tipo[^75].
- La resistencia a piretroides (los insecticidas de las redes ITN) está en tendencia de aumento en casi todas las zonas de transmisión[^73][^74].
- En *An. stephensi* invasivo, la resistencia fue **importada desde Asia** antes de que el mosquito llegara a África, lo que significa que no hay variabilidad regional para explotar con estrategias regionales diferenciadas[^58].

***
## 9. Modelos Matemáticos y de Simulación
### 9.1 Modelos Clásicos: Ross-Macdonald y Capacidad Vectorial
El modelo de **Ross (1911) y Macdonald (1957)** es la base de toda la teoría cuantitativa de transmisión de malaria[^76][^77]. La capacidad vectorial (VC) se define como el número diario de picaduras infectivas que surgiría de un humano completamente infeccioso, capturadas por todas las hembras de mosquito en una zona:

$$ VC = \frac{m \cdot a^2 \cdot p^n \cdot e^{-g \cdot n}}{-\ln(p)} $$

Donde[^76][^77]:
- $$m$$ = densidad de mosquitos por humano
- $$a$$ = tasa de picadura diaria (frecuencia de toma de sangre × antropofilia)
- $$p$$ = supervivencia diaria del adulto
- $$n$$ = duración del EIP (período de incubación extrínseco) en días
- $$g$$ = tasa de mortalidad diaria del adulto ($$g = -\ln(p)$$)

La extensión espacial de este modelo mediante **matrices de dispersión** (Vectorial Capacity Matrix) permite modelar el flujo de transmisión entre parches geográficos interconectados[^78].
### 9.2 Modelos Matemáticos Compartimentales (ODE/DDE)
Los modelos de ecuaciones diferenciales ordinarias y retardadas (ODE/DDE) dividen la población en compartimentos (Susceptible, Expuesto, Infectado)[^77][^79][^72]. Estos modelos permiten:

- Análisis de equilibrio y número reproductivo básico $$R_0$$
- Análisis de bifurcación y umbrales de eliminación
- Incorporación de temperatura dependiente del tiempo
- Modelado de la estacionalidad del mosquito
### 9.3 Modelos Basados en Agentes (ABM)
Los **ABMs** representan cada individuo (mosquito, humano) como un agente autónomo con sus propias propiedades y reglas de comportamiento[^80][^81][^82]. Son los más adecuados para la simulación detallada requerida en este proyecto, ya que capturan:

- Heterogeneidad espacial explícita (integración GIS)
- Stochasticidad (eventos aleatorios)
- Comportamientos emergentes no anticipados
- Dinámicas de paisaje y movimiento realista

**Plataformas de Simulación Existentes:**

| Plataforma | Tipo | Características |
|---|---|---|
| **EMOD (IDM)** | ABM estocástico-espacial | Modela mosquitos y humanos individualmente; integra demografía, hábitat, migración y intervenciones; open-source[^81][^83][^84] |
| **OpenMalaria** | ABM/compartmental híbrido | Desarrollado por Swiss TPH; orientado a evaluación de intervenciones[^85][^86] |
| **MALARIA TOOLS (malmod)** | ABM basado en mosquito | Modelo del ciclo de vida completo del mosquito con variables ambientales[^87] |
| **MBites** | ABM del comportamiento adulto | Modela cada picadura y evento conductual[^87] |

El paper de Depinay et al. (2004) en PMC514565 representa la primera simulación orientada a objetos del ciclo de vida completo de *An. gambiae* integrando variables biológicas y ambientales[^18].
### 9.4 Modelos Espaciales con GIS
La integración de **Sistemas de Información Geográfica (GIS)** con modelos de mosquitos permite[^69][^88][^89]:

- Identificar y mapear hábitats larvarios potenciales mediante pendiente, índice de humedad topográfica y cobertura terrestre
- Modelar flujos de dispersión entre parches de hábitat
- Incorporar datos de temperatura y precipitación con resolución espacial alta
- Validar modelos con datos de campo georreferenciados

Un modelo ABM espacio-temporal reciente (2025) integra datos climáticos, GIS y poblaciones de agentes para proyectar la distribución espacial de la malaria con alta resolución[^89].

***
## 10. Taxonomía Completa de Variables para Simulación
Esta sección compila, de forma sistemática, todas las variables identificadas en la literatura que deben considerarse para una simulación realista del comportamiento y expansión territorial de *Anopheles*.
### 10.1 Variables Biológicas del Ciclo de Vida
**Variables de Huevo:**
- Tasa de oviposición (50–200 huevos/ciclo)[^16]
- Variabilidad individual de fecundidad (relacionada con el peso corporal adulto)[^18]
- Mortalidad diaria de huevos
- Tolerancia a la desecación (prácticamente nula en *Anopheles*)[^18]
- Temperatura de incubación y tasa de desarrollo

**Variables Larvarias:**
- Número de estadios (4 instares)
- Tasa de desarrollo dependiente de temperatura (curva enzimática de Sharpe-DeMichele)[^18]
- Peso larvario y tasa de crecimiento
- Capacidad de carga del hábitat (*K*) en mg de biomasa/m²[^18]
- Mortalidad dependiente de densidad
- Mortalidad por predación (con efecto de retraso temporal)[^18]
- Mortalidad por patógenos
- Temperatura mínima de desarrollo larval (~16°C) y temperatura letal máxima (40°C para *An. gambiae*)[^48]

**Variables de Pupa:**
- Duración de la fase pupal (temperatura-dependiente)
- Mortalidad pupal
- Ratio de emergencia macho:hembra (~1:1)

**Variables del Adulto:**
- Longevidad adulta (supervivencia diaria: ~0.9 en campo)[^18]
- Duración del ciclo gonotrófico (temperatura-dependiente)
- Número de ciclos gonotróficos en la vida (paridad)
- Requerimiento de tomas múltiples de sangre (42% de nulíparas en *An. gambiae*)[^18]
- Proporción de hembras con "discordancia gonotrófica"
- Tasa de picadura (*a*): frecuencia de toma de sangre
- Antropofilia (Human Blood Index)
- Endofilia/exofilia
- Preferencia de descanso (intradomiciliario vs extradomiciliario)
- Tasa de alimentación de azúcares
- Disponibilidad y tipo de fuentes de azúcar (efecto en supervivencia y parasitemia)[^41]

**Variables Relacionadas con el Parásito:**
- Período de Incubación Extrínseco (EIP), temperatura-dependiente[^70][^71]
- Prevalencia de esporozoitos
- Tasa de infección por picadura infectiva
- Susceptibilidad a *Plasmodium* (varía entre especies y linajes)
### 10.2 Variables Ambientales y Climáticas
**Temperatura:**
- Temperatura mínima, máxima y media diaria (o sub-diaria)[^59][^90]
- Temperatura del agua en hábitats larvarios
- Amplitud de la fluctuación diurna de temperatura
- Temperatura acumulada (grados-día)
- Calidad del modelo de temperatura: constante vs. fluctuante (importante para EIP)[^71]

**Precipitación e Hidrología:**
- Precipitación diaria (mm)
- Intensidad y duración de eventos lluviosos
- Cobertura de hábitats larvarios activos post-lluvia
- Evapotranspiración (ETp)
- Volumen y permanencia de los hábitats larvarios
- Índice de humedad topográfica
- Proximidad a cuerpos de agua permanentes

**Humedad:**
- Humedad relativa del aire (%)[^62]
- Déficit de presión de vapor (relacionado con la desecación adulta)

**Viento:**
- Velocidad y dirección del viento (para dispersión a alta altitud)[^51][^52]
- Corrientes de baja altitud (vuelo local)

**Cobertura Terrestre y Paisaje (GIS):**
- Tipo de uso del suelo (bosque, agricultura, arrozal, urbano, semiárido)[^68]
- Elevación y pendiente (DEM)
- Índice de vegetación (NDVI)
- Exposición solar de hábitats acuáticos
- Cobertura de sombra en hábitats larvarios
- Densidad y distribución de hábitats larvarios
- Mapa de cuerpos de agua
- Geometría y volumen de hábitats (caja, cilindro)
- Coeficiente de sun-exposure del hábitat[^18]
### 10.3 Variables de Comportamiento y Dispersión
**Dispersal del Adulto:**
- Radio de dispersal normal (≤2 km)[^16]
- Probabilidad de migración de largo alcance (windborne)
- Velocidad de vuelo y capacidad energética
- Patrón de selección de hábitat de oviposición (distancia, calidad, señales químicas)
- Patrón de selección de hospedador (distancia, densidad, attractiveness)
- Fidelidad a sitios de reposo y picadura ("habitat loyalty")

**Comportamiento de Enjambre:**
- Umbrales ambientales para la formación de enjambres (anochecer, temperatura, viento)
- Localización de "swarm markers" en el paisaje
- Densidad mínima viable de machos para enjambres exitosos

**Aestivación/Diapause:**
- Umbral de humedad relativa para inducción de aestivación (<40% RH)[^18]
- Disponibilidad de agua superficial
- Fisiología de supervivencia en dormancia
- Duración máxima de aestivación
### 10.4 Variables Poblacionales y de Especie
- Composición de especies (múltiples especies con diferentes parámetros)
- Estructura genética de la población y frecuencias de alelos (incluyendo inversiones cromosómicas)[^11][^10]
- Frecuencias de alelos de resistencia a insecticidas (*Vgsc*, *CYP* genes)
- Ratio de especies crípticas en simpatría
- Parámetros de competencia interespecífica e intraespecífica
- Tasa de hibridización entre especies (generalmente muy baja)[^28]
### 10.5 Variables de Control y Anthropogénicas
- Cobertura y tipo de redes mosquiteras (ITNs, LLINs)
- Rociado residual interior (IRS): insecticida usado, cobertura, duración
- Larvidicida: tipo, cobertura, eficacia, frecuencia
- Densidad y distribución de hospedadores humanos y animales
- Tipo de vivienda (materiales, apertura de ventanas, presencia de mallas)
- Comportamiento humano (uso de redes, hora de dormir, actividad nocturna exterior)
- Presencia de ganado (efecto de zooprofilaxis)
- Gene drives (en modelos prospectivos)[^91][^92][^93][^94]

***
## 11. Resistencia Genética y Evolución
### 11.1 Inversiones Cromosómicas y Adaptación Local
Las inversiones cromosómicas polimórficas son un mecanismo central de adaptación rápida en *Anopheles*[^10][^11][^95]. Funcionan como "supergenes": el segmento invertido hereda conjuntamente múltiples alelos adaptativos, protegiéndolos de la recombinación. En *An. gambiae* y *An. funestus*:

- La inversión **2La** confiere resistencia a la desecación, favoreciendo la colonización de zonas áridas[^13].
- La inversión **2Rb** está asociada con la adaptación a zonas de sabana frente a bosque lluvioso[^11].
- Las frecuencias de inversiones varían geográficamente siguiendo gradientes climáticos de aridez[^13][^11].

En *An. funestus*, una sola inversión puede generar hasta un **92% de aislamiento reproductivo** entre poblaciones de sabana, actuando casi como barrera de especiación[^95].
### 11.2 Genomics y Vigilancia de la Resistencia
El **Proyecto An. gambiae 1000 Genomes** ha secuenciado miles de mosquitos de toda África, revelando la estructura poblacional fina y las variantes de resistencia[^96][^97][^98]. Esta vigilancia genómica a escala continental es esencial para calibrar modelos de simulación con parámetros localmente relevantes[^73][^99].

***
## 12. Tecnologías de Control Emergentes
### 12.1 Gene Drive
Los **gene drives** son sistemas de edición genética (principalmente basados en CRISPR-Cas9) diseñados para propagarse a través de poblaciones de mosquitos más rápidamente de lo que permitiría la herencia mendeliana normal[^100][^91][^92]. Dos tipos principales:

- **Gene drives de supresión**: interrumpen genes esenciales (ej. doublesex) para colapsar poblaciones[^91][^93].
- **Gene drives de modificación**: reemplazan alelos que confieren capacidad vectorial por alelos refractarios al parásito[^92][^93].

Modelos de simulación en 16 entornos africanos muestran que el impacto del gene drive depende críticamente de la ecología local y la epidemiología[^94]. La resistencia al gene drive en sitios conservados evolutivamente es una limitación importante[^100].
### 12.2 Symbolic Toxic Sugar Baits (ATSB)
Los "Attractive Toxic Sugar Baits" (ATSB) son cebos de azúcar que atraen a ambos sexos de mosquito (que se alimentan de azúcar) y los matan con insecticida[^40][^101].

***
## 13. Implicaciones para el Diseño de la Simulación
Para construir una simulación completa y realista del comportamiento y expansión territorial de *Anopheles*, se recomienda una arquitectura de **Modelo Basado en Agentes Espacio-Temporal (Spatio-Temporal ABM)** con las siguientes capas:

1. **Capa geoespacial**: datos GIS de elevación (DEM), uso del suelo, cuerpos de agua, temperatura y precipitación con resolución espacial y temporal adecuada (idealmente diaria).
2. **Motor de hábitat**: modelo hidrológico simple que determina qué hábitats están activos en cada paso de tiempo, su volumen y temperatura del agua.
3. **Agente mosquito**: cada individuo tiene propiedades (especie, estadio, edad, peso, estado reproductivo, estado de infección, posición GPS) y transita entre estados según reglas probabilísticas dependientes de las variables ambientales.
4. **Motor de comportamiento adulto**: búsqueda de hospedador (con señales de CO₂, olor), elección de sitio de oviposición, dispersión, reposo, formación de enjambres.
5. **Motor de dispersión**: distribución de corto alcance (Gaussiana truncada) más un componente de migración eólica de largo alcance (modelado con datos de viento).
6. **Módulo de parásito (opcional)**: track del EIP dentro de cada mosquito infectado, permitiendo calcular la capacidad vectorial emergente.
7. **Módulo de control**: implementación de intervenciones (ITNs, IRS, larvicidas, gene drive) con parámetros de cobertura, eficacia y resistencia.
8. **Validación**: calibración con datos entomológicos de campo (densidad de adultos, prevalencia de esporozoitos, diversidad de especies), preferiblemente de múltiples localidades con condiciones ecológicas distintas.

Plataformas open-source como **EMOD** (Python/C++) o frameworks de ABM como **Mesa** (Python) pueden servir de base, integrando datos climáticos de ERA5 o CHIRPS y datos de cobertura terrestre de Copernicus o MODIS[^81][^84].

***
## Conclusiones y Brechas de Conocimiento
La simulación realista de *Anopheles* requiere modelar simultáneamente la biología del ciclo de vida, el comportamiento complejo del adulto, la dinámica del hábitat acuático, la dispersión multi-escala (local + migración eólica), la variabilidad interespecífica e intraespecífica, y los efectos del cambio climático. Las brechas de conocimiento más críticas identificadas en la literatura son[^18][^60]:

1. Datos de tasas de supervivencia y desarrollo larvario en temperaturas extremas para la mayoría de especies distintas de *An. gambiae*.
2. Mecanismos precisos de orientación al hábitat de oviposición (señales químicas del agua).
3. Cuantificación de la migración eólica inter-estacional y sus determinantes meteorológicos.
4. Datos de campo sobre el ciclo de vida de *An. stephensi* en los ecosistemas africanos recién invadidos.
5. Impacto de la diversidad de fuentes de azúcar en la longevidad y capacidad vectorial en campo.
6. Datos genómicos poblacionales para calibrar modelos de resistencia a insecticidas con resolución local.

---

## References

1. [Malaria - World Health Organization (WHO)](https://www.who.int/data/gho/data/themes/malaria) - Malaria transmission occurs in 80 countries across five WHO regions. Since 2015, the WHO European Re...

2. [World malaria report 2025 - World Health Organization (WHO)](https://www.who.int/teams/global-malaria-programme/reports/world-malaria-report-2025) - Each year, WHO’s World malaria report provides a comprehensive and up-to-date assessment of trends i...

3. [Anopheles | Mosquito, Malaria, Description, Species ... - Britannica](https://www.britannica.com/animal/Anopheles) - The anopheles mosquito genus is a genus of mosquitoes in the family Culicidae that includes more tha...

4. [Anopheles - Wikipedia](https://en.wikipedia.org/wiki/Anopheles)

5. [Bionomics, taxonomy, and distribution of the major malaria vector ...](https://pubmed.ncbi.nlm.nih.gov/18178531/) - There is high diversity of Anopheles mosquitoes in Southeast Asia and the main vectors of malaria be...

6. [Table 1.](https://pmc.ncbi.nlm.nih.gov/articles/PMC12568711/table/T1/) - Malaria and schistosomiasis represent two of the most significant global parasitic diseases in terms...

7. [The dominant Anopheles vectors of human malaria in Africa, Europe ...](https://agris.fao.org/search/en/providers/122535/records/65dffdca63b8185d9cb089bb)

8. [A global map of dominant malaria vectors - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC3349467/) - Global maps, in particular those based on vector distributions, have long been used to help visualis...

9. [Anopheles gambiae complex and disease transmission in Africa](https://academic.oup.com/trstmh/article-lookup/doi/10.1016/0035-9203(74)90035-2) - Abstract. Anopheles gambiae complex mosquitoes are present throughout tropical Africa and its offsho...

10. [Chromosomal Inversions, Natural Selection and Adaptation in the Malaria Vector Anopheles funestus](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC3002248/) - Chromosomal polymorphisms, such as inversions, are presumably involved in the rapid adaptation of po...

11. [Chromosome inversions and ecological plasticity in the main ...](https://pmc.ncbi.nlm.nih.gov/articles/PMC5340588/) - por D Ayala · 2017 · Mencionado por 80 — We investigated the roles played by 23 chromosome inversion...

12. [Chromosome Inversions, Genomic Differentiation and Speciation in the African Malaria Mosquito Anopheles gambiae](https://pmc.ncbi.nlm.nih.gov/articles/PMC3603965/) - The African malaria vector, Anopheles gambiae, is characterized by multiple polymorphic chromosomal ...

13. [Systems genetic analysis of inversion polymorphisms in the malaria mosquito Anopheles gambiae | PNAS](https://www.pnas.org/doi/10.1073/pnas.1806760115) - Inversion polymorphisms in the African malaria vector Anopheles gambiae segregate along climatic gra...

14. [Genomic Analysis Reveals a New Cryptic Taxon Within the ... - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC12051790/) - Anopheles mosquitoes are major malaria vectors, encompassing several species complexes with diverse ...

15. [Unveiling mosquito cryptic species and their reproductive isolation](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7754467/) - Mosquitoes are major vectors of many infectious pathogens or parasites. Understanding cryptic specie...

16. [[PDF] Mosquito Life Cycle - CDC](https://www.cdc.gov/mosquitoes/pdfs/AnophelesLifeCycle-ENG.pdf)

17. [The Life Cycle of the Anopheles Mosquito](https://www.youtube.com/watch?v=KzQS220sHHE) - This video explores the fascinating life cycle of the Anopheles mosquito, the primary vector for mal...

18. [A simulation model of African Anopheles ecology and population dynamics for the analysis of malaria transmission](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC514565/) - Malaria is one of the oldest and deadliest infectious diseases in humans. Many mathematical models o...

19. [The Anopheles mosquito lifecycle | Mosquito Minutes](https://www.youtube.com/watch?v=qoRRamzumBk) - “Mosquito Minutes” is a series of short animations that give intriguing and insightful facts about m...

20. [Anopheles gambiae feeding and survival on honeydew and extra-floral nectar of peridomestic plants - PubMed](https://pubmed.ncbi.nlm.nih.gov/15189234/) - It is widely believed that the malaria vector Anopheles gambiae Giles (Diptera: Culicidae) rarely or...

21. [Mating Behavior and Gonotrophic Cycle in Anopheles ...](https://www.jelsciences.com/articles/jbres1398.php) - The time between blood meal and oviposition is called gonotrophic period. Consequently, blood feedin...

22. [Mosquito Gonotrophic Cycle and Multiple Feeding Potential](https://scispace.com/pdf/mosquito-gonotrophic-cycle-and-multiple-feeding-potential-bj0vzg4gkl.pdf) - Many Anopheles con- centrate the blood meal during feeding to compensate for their relatively small ...

23. [Multiple Blood Meals as a Reproductive Strategy in Anopheles (Diptera: Culicidae)](https://academic.oup.com/jme/article-abstract/30/6/975/2221327) - Abstract. Multiple blood meals within one gonotrophic cycle were taken readily at 6-24-hr intervals ...

24. [Diet and Oviposition Deprivation Effects on Survivorship ...](https://pmc.ncbi.nlm.nih.gov/articles/PMC9233601/) - por PS Chisulumi · 2022 · Mencionado por 5 — The female Anopheles gambiae s.s. fed on both blood mea...

25. [Swarming Behavior in Anopheles gambiae (sensu lato)](https://pmc.ncbi.nlm.nih.gov/articles/PMC8755986/) - Effective management of insect disease vectors requires a detailed understanding of their ecology an...

26. [Swarming and mate selection in Anopheles gambiae ...](https://pubmed.ncbi.nlm.nih.gov/37392071/) - Treating both male and female Anopheles gambiae as if they are "boids" (a computer program that mimi...

27. [Spatial distribution and male mating success of Anopheles ...](https://pmc.ncbi.nlm.nih.gov/articles/PMC3146442/) - Anopheles gambiae mates in flight at particular mating sites over specific landmarks known as swarm ...

28. [Swarming behaviour in natural populations of Anopheles gambiae ...](https://pubmed.ncbi.nlm.nih.gov/24370676/) - The swarming behaviour of natural populations of Anopheles gambiae and An. coluzzii (formerly known ...

29. [Natural swarming behaviour of the molecular M form of Anopheles gambiae](https://www.sciencedirect.com/science/article/abs/pii/S0035920303801104)

30. [Harmonic convergence coordinates swarm mating by ...](https://www.nature.com/articles/s41598-021-03236-5) - por SS Garcia Castillo · 2021 · Mencionado por 12 — Here, for the first time, we present detailed an...

31. [Human attractive cues and mosquito host-seeking behavior](https://www.sciencedirect.com/science/article/abs/pii/S1471492221002373) - por IV Coutinho-Abreu · 2022 · Mencionado por 119 — Mosquito host-seeking is mediated by attraction ...

32. [Human attractive cues and mosquito host-seeking behavior - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC10789295/) - Female mosquitoes use chemical and physical cues, including vision, smell, heat, and humidity, to or...

33. [Odorant ligands for the CO2 receptor in two Anopheles vectors of malaria](https://pmc.ncbi.nlm.nih.gov/articles/PMC6385339/) - Exhaled CO2 is an important host-seeking cue for Anopheles mosquitoes, which is detected by a highly...

34. [Functional development of carbon dioxide detection in the maxillary palp of Anopheles gambiae - PubMed](https://pubmed.ncbi.nlm.nih.gov/26056246/) - Olfactory information drives several behaviours critical for the survival and persistence of insect ...

35. [Life cycle Anopheles mosquito](https://www.naturetoday.com/intl/en/observations/umubu-radar/mosquitoes1/life-cycle-anopheles-mosquito) - Op naturetoday.com vind je dagelijks het actuele nieuws over de natuur. De berichten gaan over vogel...

36. [Age-dependent regulation of host seeking in Anopheles ...](https://www.nature.com/articles/s41598-019-46220-w) - por AB Omondi · 2019 · Mencionado por 68 — Multimodal integration of carbon dioxide and other sensor...

37. [Feeding and resting behaviour of malaria vector ...](https://pmc.ncbi.nlm.nih.gov/articles/PMC1964787/) - The most important factor for effective zooprophylaxis in reducing malaria transmission is a predomi...

38. [The Genetic Basis of Host Preference and Resting Behavior in the Major African Malaria Vector, Anopheles arabiensis - PubMed](https://pubmed.ncbi.nlm.nih.gov/27631375/) - Malaria transmission is dependent on the propensity of Anopheles mosquitoes to bite humans (anthropo...

39. [Host preference and resting behavior of Anopheles coluzzii (Diptera](https://pubmed.ncbi.nlm.nih.gov/41812224/?fc=20220523101529&ff=20260311210609&v=2.19.0.post6+133c1fe) - Host preference and resting behavior of Anopheles coluzzii Coetzee & Wilkerson, 2013 were investigat...

40. [Natural Plant Sugar Sources of Anopheles Mosquitoes Strongly ...](https://pmc.ncbi.nlm.nih.gov/articles/PMC3024498/) - An improved knowledge of mosquito life history could strengthen malaria vector control efforts that ...

41. [Dryad](https://datadryad.org/stash/dataset/doi:10.5061/dryad.9s690)

42. [Anopheles larval species composition and characterization of breeding habitats in two localities in the Ghibe River Basin, southwestern Ethiopia - PubMed](https://pubmed.ncbi.nlm.nih.gov/32046734/) - Different species of Anopheles larvae were identified including An. gambiae s.l., the main malaria v...

43. [Anopheles arabiensis larval habitats characterization and Anopheles species diversity in water bodies from Jozini, KwaZulu-Natal Province - PubMed](https://pubmed.ncbi.nlm.nih.gov/39979987/) - This study showed that An. arabiensis primarily breed in small temporary water bodies characterized ...

44. [Water Physicochemical Parameters and Microbial ...](https://pubmed.ncbi.nlm.nih.gov/35920087/) - The presence of mosquitoes in an area is dependent on the availability of suitable breeding sites th...

45. [[PDF] Physico-chemical characteristics of Anopheles breeding sites](https://academicjournals.org/article/article1380211116_Oyewole%20et%20al.pdf)

46. [Anopheles larval ecology and physicochemical characterization of larval habitats in Dire Dawa: an area colonized by Anopheles stephensi in Eastern Ethiopia - PubMed](https://pubmed.ncbi.nlm.nih.gov/41646345/) - <span><i>Anopheles stephensi</i> was the predominant species found in the study area, followed by <i...

47. [Combined effect of physico-chemical and microbial quality of breeding habitat water on oviposition of malarial vector Anopheles subpictus](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10004544/) - Mosquitoes prefer diverse water bodies for egg laying and larval survival. Present study was perform...

48. [Temperature-related duration of aquatic stages of the Afrotropical ...](https://pubmed.ncbi.nlm.nih.gov/15189243/) - Vector abundance is an important factor governing disease risk and is often employed when modelling ...

49. [Predatory and competitive interaction in Anopheles gambiae sensu lato larval breeding habitats in selected villages of central Uganda - PubMed](https://pubmed.ncbi.nlm.nih.gov/34419140/) - Ponds and streams are habitats that host the largest diversity and abundance of aquatic insect taxa....

50. [Landscape Movements of Anopheles gambiae Malaria Vector Mosquitoes in Rural Gambia](https://pmc.ncbi.nlm.nih.gov/articles/PMC3715529/) - For malaria control in Africa it is crucial to characterise the dispersal of its most efficient vect...

51. [Windborne long-distance migration of malaria mosquitoes in ...](https://pmc.ncbi.nlm.nih.gov/articles/PMC11095661/) - Over the past two decades, control efforts have halved malaria cases globally, yet burdens remain hi...

52. [Wind-assisted high-altitude dispersal of mosquitoes and other ...](https://pmc.ncbi.nlm.nih.gov/articles/PMC10337859/) - por HE Atieli · 2023 · Mencionado por 46 — These data suggest that windborne dispersal activity of m...

53. [The Effects of High-Altitude Windborne Migration on Survival ...](https://pubmed.ncbi.nlm.nih.gov/32667040/) - Recent results of high-altitude windborne mosquito migration raised questions about the viability of...

54. [A new malaria mosquito is causing outbreaks in African ...](https://www.gavi.org/vaccineswork/new-malaria-mosquito-causing-outbreaks-african-cites-heres-where-it-came) - Anopheles stephensi is an invasive urban-dwelling species of mosquito capable of transmitting two hi...

55. [The Ecology of Anopheles Mosquitoes under Climate ...](https://pmc.ncbi.nlm.nih.gov/articles/PMC3767301/) - Climate change is expected to lead to latitudinal and altitudinal temperature increases. High elevat...

56. [A systematic review of climate-change driven range shifts in mosquito vectors](https://www.biorxiv.org/content/10.1101/2025.03.25.645279v1.full.pdf)

57. [Vector alert: Anopheles stephensi invasion and spread](https://www.who.int/docs/default-source/young-leaders-blog/stephensi-info-note-august2019.pdf?sfvrsn=90a1305a_3)

58. [The origin, invasion history and resistance architecture of ...](https://pubmed.ncbi.nlm.nih.gov/40196515/) - por TPW Dennis · 2025 · Mencionado por 6 — The invasion of Africa by the Asian urban malaria vector,...

59. [The Effect of Temperature on Anopheles Mosquito Population ...](https://pmc.ncbi.nlm.nih.gov/articles/PMC3828393/) - The parasites that cause malaria depend on Anopheles mosquitoes for transmission; because of this, m...

60. [A Systematic Review of the Effects of Temperature on Anopheles Mosquito Development and Survival: Implications for Malaria Control in a Future Warmer Climate - PubMed](https://pubmed.ncbi.nlm.nih.gov/34299706/) - The rearing temperature of the immature stages can have a significant impact on the life-history tra...

61. [Anopheles aquatic development kinetic and adults' longevity ... - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC11000375/) - Anopheles mosquitoes are ectothermic and involved in numerous pathogen transmissions. Their life his...

62. [6. Factors that Affect Malaria Transmission: View as single page](https://www.open.edu/openlearncreate/mod/oucontent/view.php?id=89&printable=1) - The three main climatic factors that directly affect malaria transmission are temperature, rainfall ...

63. [Modeling the role of environmental variables on the population dynamics of the malaria vector Anopheles gambiae sensu stricto](https://pmc.ncbi.nlm.nih.gov/articles/PMC3496602/) - The impact of weather and climate on malaria transmission has attracted considerable attention in re...

64. [Ecophysiology of Anopheles gambiae s.l.: persistence in the Sahel - PubMed](https://pubmed.ncbi.nlm.nih.gov/24933461/) - The dry-season biology of malaria vectors is poorly understood, especially in arid environments when...

65. [Dry season reproductive depression of Anopheles gambiae ... - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC4789105/) - Adults of the M form of An. gambiae persist through the long dry season, when no surface waters are ...

66. [A trade-off between dry season survival longevity and wet season high net reproduction can explain the persistence of Anopheles mosquitoes](https://pmc.ncbi.nlm.nih.gov/articles/PMC6215619/) - Plasmodium falciparum malaria remains a leading cause of death in tropical regions of the world. Des...

67. [Morphological changes in the spiracles of Anopheles gambiae s.l (Diptera) as a response to the dry season conditions in Burkina Faso (West Africa)](https://pmc.ncbi.nlm.nih.gov/articles/PMC4704408/) - Survival to dry season conditions of sub-Saharan savannahs is a major challenge for insects inhabiti...

68. [The Impacts of Land Use Change on Malaria Vector](https://www.uvm.edu/giee/pubpdfs/Stryker_2012_Ecohealth.pdf)

69. [Use of GIS-based spatial modeling approach to characterize the ...](https://pubmed.ncbi.nlm.nih.gov/15115121/) - We sampled 291 bodies of water for Anopheles larvae around three malaria-endemic villages of Ban Khu...

70. [The importance of the extrinsic incubation period for malaria ...](https://spiral.imperial.ac.uk/entities/publication/ed7f3d42-2171-4699-a7b1-dfccb21edbb1) - The extrinsic incubation period (EIP) of malaria is the time required for Plasmodium parasites to un...

71. [Exploring the lower thermal limits for development of the human malaria parasite, Plasmodium falciparum - PubMed](https://pubmed.ncbi.nlm.nih.gov/31238857/) - The rate of malaria transmission is strongly determined by parasite development time in the mosquito...

72. [A Malaria Transmission Model with Temperature-Dependent ...](https://pubmed.ncbi.nlm.nih.gov/28389985/) - Malaria is an infectious disease caused by Plasmodium parasites and is transmitted among humans by f...

73. [Trends in insecticide resistance in Anopheles mosquitoes (Diptera: Culicidae) in Ghana: a systematic review - PubMed](https://pubmed.ncbi.nlm.nih.gov/41063499/) - Malaria continues to be a major public health issue in Ghana, contributing significantly to hospital...

74. [Evidence of intensification of pyrethroid resistance in the major malaria vectors in Kinshasa, Democratic Republic of Congo - Scientific Reports](https://www.nature.com/articles/s41598-023-41952-2) - Assessing patterns and evolution of insecticide resistance in malaria vectors is a prerequisite to d...

75. [DNA marker reveals pyrethroid resistance in malaria ...](https://www.news-medical.net/news/20260204/DNA-marker-reveals-pyrethroid-resistance-in-malaria-mosquitoes.aspx) - A new study, jointly led by Liverpool School of Tropical Medicine and the Centre for Research in Inf...

76. [Ross, Macdonald, and a Theory for the Dynamics and Control ... - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC3320609/) - Ronald Ross and George Macdonald are credited with developing a mathematical model of mosquito-borne...

77. [Mathematical models of malaria - a review - PMC - NIH](https://pmc.ncbi.nlm.nih.gov/articles/PMC3162588/) - Mathematical models have been used to provide an explicit framework for understanding malaria transm...

78. [Vectorial Capacity in Metapopulation Models – Malaria Theory](https://faculty.washington.edu/smitdave/malaria_theory/vc_spatial.html)

79. [Mathematical modeling of malaria transmission dynamics ...](https://pmc.ncbi.nlm.nih.gov/articles/PMC10463202/) - Malaria importation is one of the hypothetical drivers of malaria transmission dynamics across the g...

80. [Agent-based models of malaria transmission: a systematic ...](https://pmc.ncbi.nlm.nih.gov/articles/PMC6098619/) - Much of the extensive research regarding transmission of malaria is underpinned by mathematical mode...

81. [emodpy-malaria - EMOD-Hub](https://emod.idmod.org/emodpy-malaria/) - emodpy-malaria is the primary interface for working with EMOD. It provides the tools to configure th...

82. [Agent-Based Modeling and Simulation of Mosquito-Borne Disease Transmission | Proceedings of the 16th Conference on Autonomous Agents and MultiAgent Systems](https://dl.acm.org/doi/10.5555/3091125.3091190)

83. [Implementation and applications of EMOD, an individual ...](https://pmc.ncbi.nlm.nih.gov/articles/PMC6067119/) - por A Bershteyn · 2018 · Mencionado por 120 — We have described the experience of developing EMOD, a...

84. [EMOD malaria - IDMOD](https://www.idmod.org/tool/emod-malaria/) - EMOD malaria is a stochastic, agent-based, spatial model designed to inform policy decisions as well...

85. [Medical and entomological malarial interventions, a comparison and synergy of two control measures using a Ross/Macdonald model variant and openmalaria simulation](https://pmc.ncbi.nlm.nih.gov/articles/PMC6013649/) - An adaptation of the classical Ross–Macdonald model for vector disease transmission to incorporate t...

86. [Introduction to OpenMalaria](https://www.ndmconsortium.com/events/pdf/introduction-openmalaria.pdf) - Model the emergence of mosquitos and the feeding cycle (parameters depend on vector species). ❖ Thre...

87. [A malaria transmission-directed model of mosquito life cycle and ecology](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC3224385/) - Malaria is a major public health issue in much of the world, and the mosquito vectors which drive tr...

88. [A Spatial Agent-Based Model to Assess the Spread of Malaria in Relation to Anti-Malaria Interventions in Southeast Iran](https://dspace.library.uu.nl/bitstream/handle/1874/408774/ijgi_09_00549.pdf?sequence=1)

89. [Spatio-temporal agent-based modelling of malaria](https://arxiv.org/html/2505.16240v1)

90. [The importance of temperature fluctuations in understanding mosquito population dynamics and malaria risk | Royal Society Open Science](https://royalsocietypublishing.org/doi/10.1098/rsos.160969) - Temperature is a key environmental driver of Anopheles mosquito population dynamics; understanding i...

91. [Gene drive-based population suppression in the malaria vector Anopheles stephensi - Nature Communications](https://www.nature.com/articles/s41467-025-56290-2) - Gene drive alleles bias their inheritance to spread through populations. Here, we constructed a mode...

92. [A suppression-modification gene drive for malaria control ...](https://ideas.repec.org/a/nat/natcom/v16y2025i1d10.1038_s41467-025-58954-5.html) - Gene drive technology presents a promising approach to controlling malaria vector populations. Suppr...

93. [A suppression-modification gene drive for malaria control targeting ...](https://pmc.ncbi.nlm.nih.gov/articles/PMC12032250/) - Gene drive technology presents a promising approach to controlling malaria vector populations. Suppr...

94. [The potential of gene drives in malaria vector species to control malaria in African environments - Nature Communications](https://www.nature.com/articles/s41467-024-53065-z) - Gene drives have the potential to support malaria control by suppressing vector populations, but the...

95. [Reproductive isolation and local adaptation quantified for a chromosome inversion in a malaria mosquito - PubMed](https://pubmed.ncbi.nlm.nih.gov/23550747/) - Chromosome inversions have long been thought to be involved in speciation and local adaptation. We h...

96. [Spatially-explicit genomics of An. gambiae s.l uncovers fine-scale population structure and mechanisms of insecticide resistance - PubMed](https://pubmed.ncbi.nlm.nih.gov/40667006/) - Progress in malaria control in sub-Saharan Africa is stalling, partly due to the spread of insectici...

97. [Genetic divergence and lower frequencies of insecticide resistance markers in the novel Anopheles gambiae Bissau molecular form in The Gambia](https://www.nature.com/articles/s41598-026-35295-x) - The members of Anopheles gambiae species complex are ubiquitous in Afro-tropics. They have been expo

98. [Whole-genome sequencing of major malaria vectors ...](https://targetmalaria.org/wp-content/uploads/2024/09/s12936-024-05106-7.pdf) - por M Kientega · 2024 · Mencionado por 32 — This study investigated the change in genetic structure ...

99. [Signatures of adaptation at key insecticide resistance loci in Anopheles gambiae in Southern Ghana revealed by reduced-coverage WGS - PubMed](https://pubmed.ncbi.nlm.nih.gov/38622230/) - Resistance to insecticides and adaptation to a diverse range of environments present challenges to A...

100. [Resistance to a CRISPR-based gene drive at an evolutionarily ...](https://pmc.ncbi.nlm.nih.gov/articles/PMC8519452/) - CRISPR-based homing gene drives can be designed to disrupt essential genes whilst biasing their own ...

101. [Insights into malaria vectors–plant interaction in a dryland ecosystem](https://pmc.ncbi.nlm.nih.gov/articles/PMC11375087/) - Improved understanding of mosquito–plant feeding interactions can reveal insights into the ecologica...

