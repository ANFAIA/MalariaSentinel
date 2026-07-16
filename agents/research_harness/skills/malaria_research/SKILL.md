# Malaria Research Domain Knowledge

## Core Concepts

### Malaria Transmission Cycle
- **Plasmodium** parasites (P. falciparum, P. vivax) infect humans via **Anopheles** mosquito bites
- Sporozoites develop in the mosquito, then infect the human liver and blood
- Gametocytes in human blood are picked up by new mosquitoes, completing the cycle

### Key Vectors
- **Anopheles gambiae**: Primary vector in sub-Saharan Africa
- **An. funestus**: Secondary vector, often found in wetlands
- **An. stephensi**: Emerging urban vector in East Africa

### Agent-Based Modeling (ABM)
- Models individual mosquitoes, humans, and parasites
- Captures spatial heterogeneity in transmission
- Enables testing of intervention strategies before deployment
- Key parameters: biting rate, survival rate, extrinsic incubation period

### Spatial Decision Support Systems (SDSS)
- Framework for integrating surveillance data with intervention targeting
- Reference: Kelly et al. (2012) — SDSS for malaria elimination
- Components: data collection, analysis, decision rules, implementation feedback

## Research Domains

### 1. Vector Ecology
- Population dynamics and seasonality
- Insecticide resistance mechanisms
- Breeding site mapping and prediction

### 2. Transmission Modeling
- Mathematical models (Ross-Macdonald, individual-based)
- Heterogeneity in exposure and susceptibility
- Super-spreading events and focal transmission

### 3. Intervention Strategies
- Indoor Residual Spraying (IRS)
- Long-Lasting Insecticidal Nets (LLINs)
- Seasonal Malaria Chemoprevention (SMC)
- Larval source management
- Targeted biologic interventions

### 4. Surveillance and Detection
- Case-based surveillance systems
- Molecular detection methods
- Genomic surveillance for drug resistance
- Mobile health (mHealth) data collection

### 5. Geospatial Analysis
- Risk mapping and stratification
- Accessibility analysis for health facilities
- Climate and environmental drivers
- Remote sensing for habitat prediction

## MalariaSentinel Framework Goals

1. **Predictive surveillance**: Identify hotspots before outbreaks occur
2. **Intervention optimization**: Target resources to highest-impact locations
3. **Elimination tracking**: Monitor progress toward zero cases
4. **Adaptive management**: Update strategies based on real-time data

## Key Metrics

- **EIR** (Entomological Inoculation Rate): Infectious bites per person per year
- **PAR** (Population At Risk): People living in transmission zones
- **ITN** (Insecticide-Treated Net) coverage: Percentage of population protected
- **IRS** (Indoor Residual Spraying) coverage: Percentage of structures sprayed
- **Slide positivity rate**: Percentage of blood smears positive for parasites

## Common Data Sources

- **DHS** (Demographic and Health Surveys): Population-level health data
- **MIS** (Malaria Indicator Surveys): Malaria-specific survey data
- **HMIS** (Health Management Information System): Facility-level case data
- **MODIS/Landsat**: Satellite imagery for environmental variables
- **WorldClim**: Climate data at 1km resolution
- **GBIF**: Biodiversity occurrence records for vector species
