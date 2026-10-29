// SPDX-License-Identifier: MIT
// config.hpp — single model-constants source for the C++ engine
// (plan constants-yaml §4). mal-core/config/model_constants.yaml is the
// ONLY source of shared py⇄C++ parameters. The loader:
//
//   * parses a PLAIN YAML SUBSET with a hand-written micro-parser
//     (no yaml-cpp dependency; see config.cc SupportedSubsetData rules);
//   * fails LOUDLY: missing keys are reported as a COMPLETE list,
//     unknown keys (typos) are an error, wrong types are an error,
//     duplicate keys inside the file are an error;
//   * embeds NO default for any model key — the YAML is the source;
//   * pre-transforms species weight rows by habitat NAME → ZoneId once
//     at load time (the day-loop consumes a plain std::array);
//   * derives num_persistent from habitat_types.dynamics (no
//     "the first three are persistent" positional rule).
//
// singleton: load_config() reads once per process (env
// MAL_MODEL_CONSTANTS overrides the default search).
#pragma once

#include <array>
#include <map>
#include <optional>
#include <stdexcept>
#include <string>
#include <vector>

#include "zone_id.hpp"

namespace mal_abm_fast {

struct ConfigError : std::runtime_error {
    using std::runtime_error::runtime_error;
};

struct ContractsCfg {
    std::string env_nc;
    std::string cogs_state;
};

struct HabitatCfg {
    std::vector<std::string> types;                 // frozen order (py API)
    std::map<std::string, std::string> dynamics;    // persistent | pluvial
    size_t num_persistent = 0;                      // DERIVED at load
    std::array<bool, kNumZoneId> persistent_zone{}; // ZoneId→dynamics==persistent
    double activation_min_engine = 0.0;
    double candidate_min_engine = 0.0;
};

struct PluvialCfg {
    double rain_scale_mm = 0.0;
    double dry_memory_days = 0.0;
    double delta_days = 0.0;
    double cold_start_z = 0.0;
};

struct AquaticStressCfg {
    double desicc_grace_days = 0.0;
    double desicc_base_daily = 0.0;
    double desicc_ramp_decay = 0.0;
    double wash_threshold_mm = 0.0;
    double wash_fraction_max = 0.0;
    int vulnerable_instar_max = 0;
};

struct UrbanCfg {
    double beta_urban = 0.0;
    double rain_pools_built_damage = 0.0;
};

struct SpeciesRow {
    std::string name;
    std::array<double, kNumZoneId> weights{};   // name→ZoneId pre-transform
    // v2 extension (plan v2 §1): behavioural physiological block.
    std::array<double, 4> activity_weights{};   // [DAY, EVENING, NIGHT, DAWN] Σ=1
    std::array<double, 5> pref{};               // HostType order (human, cattle,
                                                //  goat, sheep, wildlife→OTHER)
    double salinity_opt_ppt = 0.0;
    double salinity_hi_tol_ppt = 0.0;
    double salinity_slope = 0.0;
    double host_seeking_scale_m = 0.0;
    double host_seeking_radius_m = 0.0;
};

struct SpeciesCfg {
    std::string default_species;
    double k_ref = 0.0;                         // [ind·km⁻²·d⁻¹]
    std::map<std::string, SpeciesRow> rows;     // named rows, by NAME
    std::array<double, kNumZoneId> neutral_weights{};
};

struct CapacityCfg {
    double persistent_availability = 0.0;
};

struct GeodesyCfg {
    double earth_radius_m = 0.0;
    double metres_per_deg_lat = 0.0;
};

struct IngestCfg {
    double nodata_sentinel = 0.0;
    int nodata_sentinel_int = 0;
    double residential_from_indoor_frac = 0.0;
    // Width of the coastal band that keeps its JRC water (historical name:
    // it no longer dilates the land mask; see coastline.py sea_mask()).
    double coastline_buffer_m = 0.0;
    // GSHHG resolution code for the coastline artifact: c/l/i/h/f.
    std::string coastline_resolution = "f";
    // Land fraction below which an AOI cell counts as water.
    double sea_water_floor = 0.05;
    double cell_size_hint_m = 0.0;
    double candidate_min_ingest = 0.0;
    int min_dilation_radius_cells = 0;
    double fill_frac_valid_max = 0.0;
    double ocean_mask_threshold = 0.0;
    double land_mask_threshold = 0.0;
    double valid_count_epsilon = 0.0;
    int grid_degrees_step_max = 0;
    int nc_compression_level = 0;
};

struct AdultsCfg {
    double daily_mort_basal = 0.0;
    double opt_c = 0.0;
    double sigma_c = 0.0;
    double mort_cap = 0.0;
    double mort_floor = 0.0;
};

struct EipCfg {
    double base_c = 0.0;
    double threshold_gd = 0.0;
};

struct TransmissionCfg {
    double beta_hv = 0.0;
    double beta_vh = 0.0;
    int human_incubation_days = 0;
    int human_infectious_days = 0;
    int human_immunity_days = 0;
    double initial_human_prevalence = 0.0;
    double initial_vector_infected_frac = 0.0;
};

struct ThermalCfg {
    double efd_max_eggs_per_day = 0.0;
    double efd_tmin_c = 0.0;
    double efd_tmax_c = 0.0;
    double efd_topt_c = 0.0;
    double egg_development_tmin_c = 0.0;
    double egg_development_tmax_c = 0.0;
    double egg_development_scale = 0.0;
    double larva_development_tmin_c = 0.0;
    double larva_development_tmax_c = 0.0;
    double larva_development_scale = 0.0;
    double pupa_development_tmin_c = 0.0;
    double pupa_development_tmax_c = 0.0;
    double pupa_development_scale = 0.0;
};

struct GonotrophicCfg {
    double cycle_duration_days = 0.0;
    double first_cycle_days = 0.0;
    double feeding_success_rate = 0.0;
    int egg_batch_mean = 0;
    int egg_batch_n = 0;
    int egg_batch_min = 0;
    int egg_batch_max = 0;
    double resting_duration_days = 0.0;
};

struct DispersalCfg {
    double adult_prob_day = 0.0;
    double adult_sigma_m = 0.0;
    double adult_max_m = 0.0;
    double wind_migration_prob = 0.0;
    double wind_flight_hours = 0.0;
    double wind_survival = 0.0;
    double wind_self_speed_ms = 0.0;
    int flight_hour = 0;
    double host_flight_step_m = 0.0;
    double snap_radius_m = 0.0;
    int night_start_hour = 0;
    int night_end_hour = 0;
};

struct HostSeekingCfg {
    int starvation_days = 0;
    double indoor_attraction_add = 0.0;
    double urbanicity_add = 0.0;
    double indoor_fraction_urban = 0.0;
    double indoor_fraction_rural = 0.0;
    double detect_range_m = 0.0;
    double approach_step_m = 0.0;
};

struct OvipositionCfg {
    double scale_m = 0.0;
    double detect_range_m = 0.0;
    double step_m = 0.0;
    double min_attraction = 0.0;
    int timeout_days = 0;
};

struct AquaticStagesCfg {
    double egg_daily_mort = 0.0;
    double pupa_daily_mort = 0.0;
    double larva_bh_s0 = 0.0;
    double larva_bh_alpha = 0.0;
    int last_larval_instar = 0;
    double salinity_missing_psu = 0.0;
};

struct RngCfg {
    int aquatic_seed_washout = 0;
    int aquatic_seed_stage_mortality = 0;
    int aquatic_seed_larva_mortality = 0;
};

struct ModelConfig {
    int version = 0;
    ContractsCfg contracts;
    HabitatCfg habitat_types;
    HabitatCfg habitat;   // activation/candidate thresholds
    PluvialCfg pluvial;
    AquaticStressCfg aquatic_stress;
    UrbanCfg urban;
    SpeciesCfg species;
    CapacityCfg capacity;
    GeodesyCfg geodesy;
    IngestCfg ingest;
    AdultsCfg adults;
    EipCfg eip;
    TransmissionCfg transmission;
    DispersalCfg dispersal;
    HostSeekingCfg host_seeking;
    OvipositionCfg oviposition;
    AquaticStagesCfg aquatic_stages;
    ThermalCfg thermal;
    GonotrophicCfg gonotrophic;
    RngCfg rng;
};

/// Parse + validate the model constants YAML (singleton; loads once).
/// Throws ConfigError with the full missing/unknown/type lists.
const ModelConfig& load_config();

/// Explicit parse of a given path (tests / config_dump tool).
ModelConfig parse_config_file(const std::string& path);

/// Resolve the constants path: MAL_MODEL_CONSTANTS env override, else a
/// search upward from the executable directory (bin/config/model_constants.yaml,
/// ../config/, ../../config/, mal-core/config/). Throws when nothing found.
std::string resolve_config_path();

/// Habitat-type name → ZoneId (static mapping table; throws ConfigError
/// on an unknown name). wetland_pluvial has NO ZoneId — nullopt.
std::optional<ZoneId> zone_id_of_habitat(const std::string& name);

inline float habitat_activation_min() {
    return static_cast<float>(load_config().habitat.activation_min_engine);
}

inline float habitat_candidate_min_engine() {
    return static_cast<float>(load_config().habitat.candidate_min_engine);
}

}  // namespace mal_abm_fast
