# LinkedIn Post

## English

I have been building MalariaSentinel as a spatial decision-support system (SDSS) for malaria elimination.

The hard engineering challenge is connecting the complete end-to-end chain:

Heterogeneous Data Streams → Ingestion Pipeline & Standardization → Mechanistic Mosquito Ecology (C++ ABM) → Neural Surrogate Learning → Full Transmission Coupling.

The animation shows the live pipeline and a 731-day Ghana simulation run (2024–2025):
- **Ecology & Physics in the Engine**: Models stage-specific thermal development (Brière-1 curves), continuous pool hydrology (Penman-Monteith evaporation & desiccation), gonotrophic cycle, host seeking, 6-hourly wind dispersal, and rain washout.
- **Surrogate AI**: 731 days of biological states and cohort time-series generate synthetic training data for a spatial neural surrogate (<50ms real-time inference).

**What is next on the roadmap**:
1. Coupling vector sporogony (SEI) with human infection dynamics (SEIR) for direct malaria incidence prediction.
2. Connecting and benchmarking spatio-temporal neural operators (U-Net, FNO).
3. Multi-species expansion (*An. funestus*, *An. gambiae s.s.*) and spatial field validation with surveillance data.

Built with support from ANFAIA. Feedback and collaboration welcome.

github.com/ANFAIA/MalariaSentinel

#Malaria #PublicHealth #OpenSource #MachineLearning #AgentBasedModeling #SpatialData

---

## Versión en español

Estoy construyendo MalariaSentinel como un sistema espacial de apoyo a decisiones (SDSS) para la eliminación de la malaria.

El reto de ingeniería no es un modelo aislado, sino conectar toda la cadena de extremo a extremo:

Fuentes de Datos Heterogéneas → Pipeline de Ingestión y Estandarización → Ecología Mecanicista del Mosquito (C++ ABM) → Aprendizaje de Surrogates Neuronales → Acoplamiento de Transmisión.

La animación muestra el pipeline en funcionamiento y una simulación de 731 días en Ghana (2024–2025):
- **Ecología y Física en el Motor**: Modela desarrollo térmico por etapas (curvas Brière-1), balance hídrico continuo en charcas (evaporación Penman-Monteith y desecación), ciclo gonotrófico, búsqueda de hospedadores, dispersión por viento cada 6 horas y lavado por lluvias torrenciales.
- **IA Surrogate**: 731 días de estados espaciales y cohortes biológicas generan datos de entrenamiento sintéticos para un emulador neuronal (<50ms para inferencia en tiempo real).

**Próximos hitos en el roadmap**:
1. Acoplamiento de infección vectorial (SEI) con infección humana (SEIR) para predicción directa de casos e incidencia clínica de malaria.
2. Integración end-to-end de surrogates neuronales espaciotemporales (U-Net, FNO).
3. Expansión multi-especie (*An. funestus*, *An. gambiae s.s.*) y validación espacial con datos de vigilancia epidemiológica.

Proyecto desarrollado con apoyo de ANFAIA. Comentarios y colaboración son bienvenidos.

github.com/ANFAIA/MalariaSentinel

#Malaria #SaludPublica #OpenSource #MachineLearning #AgentBasedModeling #DatosEspaciales
