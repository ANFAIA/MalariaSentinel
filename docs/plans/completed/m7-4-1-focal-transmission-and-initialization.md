# M7.4.1 — Transmisión Focal de Malaria, Inicialización por Escenarios y Transmisión Exclusiva en Hembras

> **Estado**: Plan de Diseño e Implementación (2026-08-25).  
> **Predecesor directo**: `M7.4` (Ciclo SEIR-SEI espacial en C++).  
> **Objetivo**: Reemplazar la prevalencia uniforme nacional por focos estocásticos/deterministas realistas, modelar escenarios de inicio (vector infeccioso vs humano importado con warm-up), y blindar biológicamente la transmisión exclusiva en mosquitos hembra.

---

## 1. Motivación y Diagnóstico del Modelo Actual

En la versión inicial de M7.4, el parámetro `--initial-human-prevalence 0.05` asigna un 5% de prevalencia infecciosa ($I_H$) a **todas las 9.466 celdas pobladas de Ghana** de forma homogénea en el día 0.

### Problemas observados en simulaciones reales:
1. **Antinaturalidad espacial**: Los brotes de malaria nunca aparecen simultáneamente en todo un país. Se originan como **microfocos epidémicos** (aldeas, barrios periurbanos, campamentos de trabajadores o zonas agrícolas receptivas).
2. **Extinción artificial en 20 días**: Al comenzar en estación seca con pocos mosquitos en zonas rurales deshabitadas (donde los vectores solo pican ganado), los 27.294 humanos infectados iniciales se recuperan espontáneamente a los 20 días ($I_H \to R_H$) sin haber sido picados por mosquitos. La prevalencia nacional cae a 0% en el día 30 y nunca revive.
3. **Falta de acoplamiento vector-hospedero inicial**: Si los mosquitos se siembran en celdas de agua sin humanos, y los humanos infectados están en ciudades sin mosquitos, la cadena de transmisión se rompe en el día 0.

---

## 2. Principios Biológicos Fundamentales

### 2.1 Transmisión Exclusiva en Mosquitos Hembra (*Anopheles* spp.)
- **Hematofagia**: Únicamente las hembras adultas (`stage == 1 && sex == 1`) se alimentan de sangre para obtener proteínas necesarias para la ovogénesis (ciclo gonotrófico).
- **Machos no vectores**: Los machos adultos (`sex == 0`) poseen piezas bucales reducidas que no perforan la piel humana; se alimentan exclusivamente de néctar y jugos vegetales. Nunca ingieren gametocitos ni inoculan esporozoitos.
- **Invariante C++**: Ningún mosquito macho puede adquirir el estado `EXPOSED` ni `INFECTIOUS`. Las rutinas de picadura, acumulación de EIP, e inoculación deben tener aserciones estrictas `sex == 1`.

### 2.2 Focos de Transmisión Humana
- Un brote humano comienza típicamente por:
  - **Casos índice importados**: Viajeros o migrantes que llegan a una localidad receptiva con presencia activa de vectores susceptibles ($S_V$).
  - **Incursión de vectores infectados**: Llegada o emergencia de hembras con esporozoitos activos ($I_V$) en una población humana susceptible ($S_H$).

---

## 3. Escenarios de Incepción de la Transmisión

El modelo admitirá dos escenarios principales de disparo epidémico:

```
                      ┌──────────────────────────────────────────────┐
                      │    ESCENARIOS DE INICIACIÓN DE TRANSMISIÓN   │
                      └──────────────────────┬───────────────────────┘
                                             │
                  ┌──────────────────────────┴──────────────────────────┐
                  ▼                                                     ▼
     [ ESCENARIO A: Vector Infectado ]                  [ ESCENARIO B: Humanos Infectados ]
     Hembras I_V llegan con parásito                    Casos índice llegan a zona con mosquitos
     (Esporozoitos en glándulas salivales)              
                  │                                                     │
                  ▼                                     ┌───────────────┴───────────────┐
     Pican humanos susceptibles en foco                 ▼                               ▼
     Inoculan S_H ──> E_H ──> I_H              [ B.1: Warm-up + Brote ]       [ B.2: Warm-Start ]
                                               Población vectorial se         Población vectorial
                                               estabiliza W días (ej. 60d);   cargada desde snapshot
                                               luego brote humano se inyecta  previo calibrado.
```

### Escenario A: Foco de Incursión Vectorial (`vector_focal_incursion`)
- Se introduce un número determinado de hembras adultas con estado $I_V$ y EIP completo en uno o varios parches/celdas específicas.
- Al buscar hospedero, pican a humanos locales y desatan la onda infecciosa $S_H \to E_H \to I_H$.

### Escenario B: Brote por Casos Humanos Índice (`human_focal_outbreak`)
Requiere que ya exista una población vectorial establecida en el territorio. Se implementan dos modalidades:

#### Modalidad B.1: Calentamiento Vectorial + Brote Diferido (`--warmup-days` + `--human-outbreak-day`)
1. **Fase de calentamiento (ej. 60 días / 2 meses)**:
   - Se siembran mosquitos en todo el territorio (`--seeding-mode uniform` o `--seeding-mode patch`).
   - Durante los primeros $W$ días no hay malaria humana activa ($I_H = 0, S_H = \text{Pop}$).
   - La población de mosquitos busca hábitats, oviposita, entra en equilibrio estacional y coloniza celdas periurbanas y rurales.
2. **Fase de inyección del brote (Día $T_{\text{outbreak}} \ge W$)**:
   - En el día $T_{\text{outbreak}}$, se seleccionan $K$ celdas habitadas viables (`random-viable` o coordenadas explícitas) y se convierten $N_{\text{casos}}$ humanos a $I_H$.
   - Los mosquitos $S_V$ presentes en esas celdas pican a los humanos $I_H$, adquieren gametocitos ($S_V \to E_V$), incuban el parásito durante el EIP térmico, y generan nuevas infecciones autóctonas ($E_V \to I_V \to S_H$).

#### Modalidad B.2: Reanudación de Estado / Warm-Start (`--warm-start-state <path>`)
- La simulación lee el GeoTIFF/JSON de una corrida previa (donde la densidad vectorial y los bancos acuáticos ya están maduros y distribuidos) y arranca inmediatamente inyectando el brote humano focal.

---

## 4. Mecanismos de Siembra Focal Humana

Se elimina la inicialización uniforme y se agregan los siguientes modos de siembra humana:

| Modo | Parámetro CLI | Descripción |
|---|---|---|
| **Focos Aleatorios Viables** (Default) | `--human-seeding-mode random-viable` | Selecciona $K$ celdas con $H(x) \ge H_{\min}$ y presencia/idoneidad de mosquitos. Inyecta $N$ casos o prevalencia local en esas $K$ celdas. |
| **Coordenadas Explícitas** | `--human-seeding-mode explicit --human-foci-coords "row1,col1:N1;row2,col2:N2"` | Inyecta casos en asentamientos específicos (ej. Accra, Kumasi, Tamale). |
| **Prevalencia Uniforme** (Legado) | `--human-seeding-mode uniform-legacy` | Modo anterior homogéneo en todo el país (solo para retrocompatibilidad y pruebas unitarias). |

### Parámetros de Control Focal:
- `--human-outbreak-foci <int>`: Número de focos a generar (default: `3`).
- `--human-outbreak-cases-per-focus <float>`: Cantidad de humanos infectados $I_H$ por foco (default: `50.0`).
- `--human-outbreak-day <int>`: Día de la simulación en que aparece el brote humano (default: `60`).
- `--human-min-cell-pop <float>`: Población mínima de la celda para ser candidata a foco (default: `50.0`).

---

## 5. Diseño Técnico en C++ (`mal_abm_fast`)

### 5.1 Extensión de `TransmissionParams` (`include/mal_abm_fast/transmission.hpp`)

```cpp
enum class HumanSeedingMode : uint8_t {
    NONE = 0,
    RANDOM_VIABLE = 1,
    EXPLICIT = 2,
    UNIFORM_LEGACY = 3
};

struct HumanOutbreakFocus {
    int32_t row = 0;
    int32_t col = 0;
    double cases = 0.0;
};

struct TransmissionParams {
    bool enabled = false;
    HumanSeedingMode human_seeding_mode = HumanSeedingMode::RANDOM_VIABLE;
    int32_t human_outbreak_day = 60;
    int32_t human_outbreak_foci_count = 3;
    double human_outbreak_cases_per_focus = 50.0;
    double human_min_cell_pop = 50.0;
    std::vector<HumanOutbreakFocus> explicit_human_foci;

    double initial_human_prevalence = 0.0;  // Solo activo si UNIFORM_LEGACY
    double initial_vector_infected_frac = 0.0;
    float beta_hv = 0.4f;
    float beta_vh = 0.5f;
    int32_t human_incubation_days = 12;
    int32_t human_infectious_days = 20;
    int32_t immunity_duration_days = 180;
    bool immunity_enabled = true;
    float focus_threshold = 0.01f;
    float eip_threshold_gd = 111.0f;
};
```

### 5.2 Lógica de Inyección en `HumanCompartmentGrid` y `Engine`

1. **Inicialización (`day == 0`)**:
   - Si `human_outbreak_day == 0` y `human_seeding_mode == RANDOM_VIABLE`: Selecciona las $K$ celdas con $H(x) \ge H_{\min}$ usando el PRNG y siembra los casos.
   - Si `human_outbreak_day > 0`: Todo el país inicia con $S_H = \text{Pop}, I_H = 0, E_H = 0, R_H = 0$.
2. **Paso diario (`Engine::step`, día $T$)**:
   - Si `current_day == params.human_outbreak_day` y `human_outbreak_day > 0`:
     - Invoca `transmission_model_->trigger_human_outbreak(host_landscape, submodel_density, rng_)`.
     - Se registran en log los focos seleccionados con sus coordenadas y casos asignados.
3. **Auditoría de Sexo en Infección Vectorial**:
```cpp
inline void record_female_feed(...) {
    // Invariante de sexo: solo hembras participan en transmisión
    if (soa.sex[si] != 1) return;
    
    // Transmisión solo si hembra es susceptible
    if (host == HostType::HUMAN &&
        soa.vector_state[si] == static_cast<uint8_t>(VectorTransmissionState::SUSCEPTIBLE) &&
        human_grid && transmission_params && transmission_params->enabled)
    {
        const double prev = human_grid->prev_at(soa.row[si], soa.col[si]);
        if (prev > 0.0) {
            const double p_inf = static_cast<double>(transmission_params->beta_hv) * prev;
            if (rng.uniform_double() < p_inf) {
                soa.vector_state[si] = static_cast<uint8_t>(VectorTransmissionState::EXPOSED);
                soa.parasite_eip_progress[si] = 0.0f;
            }
        }
    }
}
```

---

## 6. Plan de Implementación por Fases

### Fase 1: Blindaje de Invariante de Género (Hembras Exclusivas)
1. Modificar `seed_vector_infections` y `record_female_feed` en `mosquito_submodel.cpp` y `transmission.cpp` para asegurar chequeos `stage == 1 && sex == 1`.
2. Añadir prueba unitaria en `test_transmission.cpp`: verificar que mosquitos machos nunca pasen a $E_V$ o $I_V$ ni generen picaduras en `BiteLedger`.

### Fase 2: Implementación de Focos Humanos y Brote Diferido (C++)
1. Extender `HumanCompartmentGrid` con métodos:
   - `seed_random_viable_foci(int32_t count, double cases_per_focus, double min_pop, const std::vector<float>& mosquito_density, Prng& rng)`.
   - `seed_explicit_foci(const std::vector<HumanOutbreakFocus>& foci)`.
2. Integrar el disparador de brote en `TransmissionModel::advance_human_transmission` / `record_daily_stats` para el día configurado.
3. Exponer opciones CLI en `mal_abm_fast/src/main.cpp`.

### Fase 3: Integración en CLI Python (`malariasim abm`) y Wrappers
1. Agregar argumentos Typer en `mal-core/src/mal_core/cli.py` y `mal-core/src/mal_core/abm/wrapper.py`:
   - `--human-seeding-mode [random-viable|explicit|uniform-legacy]`
   - `--human-outbreak-foci <int>`
   - `--human-outbreak-cases <float>`
   - `--human-outbreak-day <int>`
   - `--human-foci-coords <str>`
2. Actualizar suite de pruebas Python `mal-core/tests/`.

### Fase 4: Validación y Visualización
1. Ejecutar simulación de prueba en Ghana con 60 días de warm-up y brote humano en día 60.
2. Verificar que las picaduras a humanos (`total_bites_on_humans > 0`) y la curva de prevalencia se eleven de forma focal y natural tras el día 60.
3. Generar GIF con `visualize_transmission.py` confirmando la propagación radial desde los focos.

---

## 7. Criterios de Aceptación

1. **Cero Machos Infectados**: 100% garantizado en pruebas unitarias (`ASSERT_EQ(vector_i_males, 0)`).
2. **Cero Prevalencia Uniforme Prematura**: En el día 0, las celdas no seleccionadas como foco tienen prevalencia 0.0%.
3. **Persistencia de Transmisión con Vector Estable**: Cuando el brote aparece en una zona con mosquitos establecidos, se registran picaduras a humanos ($>0$), adquisición de parásito por mosquitos ($E_V > 0 \to I_V > 0$) y nuevos casos humanos autóctonos ($E_H > 0 \to I_H > 0$), evitando la extinción artificial inmediata.
