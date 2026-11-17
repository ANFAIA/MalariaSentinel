/**
 * SPDX-License-Identifier: MIT
 * config.hpp — single model-constants source for the C++ engine
 * (plan constants-yaml §4). mal-core/config/model_constants.yaml is the
 * ONLY source of shared py⇄C++ parameters. The loader:
 *
 *   * parses a PLAIN YAML SUBSET with a hand-written micro-parser
 *     (no yaml-cpp dependency; see config.cc SupportedSubsetData rules);
 *   * fails LOUDLY: missing keys are reported as a COMPLETE list,
 *     unknown keys (typos) are an error, wrong types are an error,
 *     duplicate keys inside the file are an error;
 *   * embeds NO default for any model key — the YAML is the source;
 *   * pre-transforms species weight rows by habitat NAME → ZoneId once
 *     at load time (the day-loop consumes a plain std::array);
 *   * derives num_persistent from habitat_types.dynamics (no
 *     "the first three are persistent" positional rule).
 *
 * singleton: load_config() reads once per process (env
 * MAL_MODEL_CONSTANTS overrides the default search).
 */
#pragma once

#include <array>
#include <map>
#include <optional>
#include <stdexcept>
#include <string>
#include <vector>

#include "zone_id.hpp"

namespace mal_abm_fast {

/// Error raised by the configuration loader: model_constants.yaml is
/// missing keys, contains unknown keys, duplicates a key or gives a key
/// the wrong type.
struct ConfigError : std::runtime_error {
    using std::runtime_error::runtime_error;
};

/// Frozen input/output contract versions, mirroring the `contracts:`
/// section of model_constants.yaml.
struct ContractsCfg {
    /// Version string of the environment NetCDF input contract; the value
    /// the ingest writer stamps on the file it produces
    /// (`contracts.env_nc`). Declared only: no code compares the file's
    /// attribute against it.
    std::string env_nc;
    /// Version string of the state COG + sidecar output contract; read at
    /// runtime by wire.hpp CONTRACT_VERSION() and written into the state
    /// sidecar (`contracts.cogs_state`).
    std::string cogs_state;
};

/// Habitat configuration. The loader fills two instances of it: the
/// `habitat_types:` section (the habitat taxonomy and the persistent vs.
/// pluvial dynamics of each type) and the `habitat:` section (the
/// engine-side activation and candidate thresholds).
struct HabitatCfg {
    std::vector<std::string> types;                 ///< frozen order (py API)
    std::map<std::string, std::string> dynamics;    ///< persistent | pluvial
    size_t num_persistent = 0;                      ///< DERIVED at load
    std::array<bool, kNumZoneId> persistent_zone{}; ///< ZoneId→dynamics==persistent
    /// Habitat-accuracy index S above which a cell counts as a live
    /// (activated) patch; below it the cell counts as habitat-dry and its
    /// aquatic cohorts desiccate (`habitat.activation_min_engine`).
    double activation_min_engine = 0.0;
    /// Minimum habitat potential S a cell must reach to become a candidate
    /// patch at all — the union of the coordinator's candidate filter and the
    /// habitat engine's feature floor (`habitat.candidate_min_engine`).
    /// Distinct from ingest.candidate_min_ingest, which the ingest census
    /// applies instead.
    double candidate_min_engine = 0.0;
};

/// Rain-driven state of the pluvial (seasonal) habitats: the shared
/// wetness factor z, in [0,1], that scales their availability
/// (`pluvial:` section of model_constants.yaml).
struct PluvialCfg {
    /// Rainfall depth (mm) that sets the scale of the wetness response
    /// z = z_dry + (1 - z_dry) * (1 - exp(-rain_mm / rain_scale_mm))
    /// (`pluvial.rain_scale_mm`).
    double rain_scale_mm = 0.0;
    /// Memory constant (days) of the dry decay of the wetness state,
    /// z_dry = z * exp(-delta_days / dry_memory_days)
    /// (`pluvial.dry_memory_days`).
    double dry_memory_days = 0.0;
    /// Length (days) of the model time step used when decaying the wetness
    /// state (`pluvial.delta_days`).
    double delta_days = 0.0;
    /// Initial value of the wetness state z at the start of a run (cold
    /// start), dimensionless in [0,1] (`pluvial.cold_start_z`).
    double cold_start_z = 0.0;
};

/// Stressors applied to the aquatic cohorts of a patch: desiccation driven
/// by the habitat-dry streak and washout driven by heavy rain
/// (`aquatic_stress:` section of model_constants.yaml).
struct AquaticStressCfg {
    /// Number of consecutive habitat-dry days tolerated before the
    /// desiccation stressor starts killing aquatic stages
    /// (`aquatic_stress.desicc_grace_days`).
    double desicc_grace_days = 0.0;
    /// Ceiling (1/day) of the daily desiccation mortality; the realised
    /// rate is this value times the exponential ramp in the dry-day streak
    /// (`aquatic_stress.desicc_base_daily`).
    double desicc_base_daily = 0.0;
    /// Rate (1/day) at which the desiccation ramp grows with each day past
    /// the grace period (`aquatic_stress.desicc_ramp_decay`).
    double desicc_ramp_decay = 0.0;
    /// Daily rainfall (mm) at or above which heavy rain washes aquatic
    /// cohorts out of their patches (`aquatic_stress.wash_threshold_mm`).
    double wash_threshold_mm = 0.0;
    /// Maximum fraction (in [0,1]) of a patch's aquatic cohorts that a
    /// single heavy-rain event can wash out
    /// (`aquatic_stress.wash_fraction_max`).
    double wash_fraction_max = 0.0;
    /// Highest larval instar (index) still vulnerable to desiccation;
    /// instars above it are not affected by the desiccation stressor
    /// (`aquatic_stress.vulnerable_instar_max`).
    int vulnerable_instar_max = 0;
};

/// Corrections the built surface applies to the habitat potential
/// (`urban:` section of model_constants.yaml).
struct UrbanCfg {
    /// Dimensionless coefficient converting the built-surface fraction of a
    /// cell into the urban persistent habitat potential
    /// (H_urban = beta_urban * lc_built) (`urban.beta_urban`).
    double beta_urban = 0.0;
    /// Dimensionless coefficient by which the built-surface fraction
    /// reduces the rain-driven potential of the open pluvial habitat
    /// (`urban.rain_pools_built_damage`).
    double rain_pools_built_damage = 0.0;
};

/// One species' row of the `species:` section: habitat affinities, daily
/// activity, host preference and the tolerances that shape its range.
struct SpeciesRow {
    /// Species key as written in the YAML (the map key under `species:`);
    /// the canonical display name is resolved elsewhere.
    std::string name;
    std::array<double, kNumZoneId> weights{};   ///< name→ZoneId pre-transform
    /// v2 extension (plan v2 §1): behavioural physiological block.
    std::array<double, 4> activity_weights{};   ///< [DAY, EVENING, NIGHT, DAWN] Σ=1
    std::array<double, 5> pref{};               ///< HostType order (human, cattle,
                                                //  goat, sheep, wildlife→OTHER)
    /// Salinity (psu) at which the species' breeding-suitability multiplier
    /// equals 1 (`species.<name>.salinity_opt_ppt`).
    double salinity_opt_ppt = 0.0;
    /// Salinity (psu) above which the species cannot breed at all — the
    /// suitability multiplier is hard-capped to 0 there
    /// (`species.<name>.salinity_hi_tol_ppt`).
    double salinity_hi_tol_ppt = 0.0;
    /// Rate (1/psu) at which the breeding-suitability multiplier decays as
    /// the salinity rises above the optimum
    /// (`species.<name>.salinity_slope`).
    double salinity_slope = 0.0;
    /// Decay length (m) of the host-seeking attraction plume, i.e. how fast
    /// the attraction of a host falls off with distance
    /// (`species.<name>.host_seeking_scale_m`).
    double host_seeking_scale_m = 0.0;
    /// Radius (m) of the host-seeking attraction field: beyond it a host
    /// exerts no attraction at all (`species.&lt;name&gt;.host_seeking_radius_m`).
    /// A different concept from host_seeking.detect_range_m, the engine's
    /// kernel detection radius.
    double host_seeking_radius_m = 0.0;
};

/// Species section of the configuration: the active species, the single
/// Beverton-Holt capacity constant, and the per-species rows keyed by name.
struct SpeciesCfg {
    /// Key of the species row used as the engine's default parameter set
    /// (species_params.hpp, coordinator) and as the fallback of the species
    /// registry (`species.default_species`).
    std::string default_species;
    double k_ref = 0.0;                         ///< [ind·km⁻²·d⁻¹]
    std::map<std::string, SpeciesRow> rows;     ///< named rows, by NAME
    /// Habitat affinities (fraction per habitat type, Σ=1) of the
    /// species-neutral row, used by runs that select no explicit species
    /// (`species.neutral.weights`).
    std::array<double, kNumZoneId> neutral_weights{};
};

/// Availability of the persistent habitats (`capacity:` section of
/// model_constants.yaml).
struct CapacityCfg {
    /// Availability factor A (dimensionless, in [0,1]) applied to every
    /// persistent habitat whose potential is positive
    /// (`capacity.persistent_availability`).
    double persistent_availability = 0.0;
};

/// Geodesic constants used to convert between metric distances and
/// degrees (`geodesy:` section of model_constants.yaml).
struct GeodesyCfg {
    /// Mean Earth radius (m) used by the AOI and the geodesic conversions
    /// of the dispersal kernel (`geodesy.earth_radius_m`).
    double earth_radius_m = 0.0;
    /// Metres per degree of latitude (m/°), the factor that turns a metric
    /// displacement into a latitude/longitude step
    /// (`geodesy.metres_per_deg_lat`).
    double metres_per_deg_lat = 0.0;
};

/// Input-side constants of the ingest stage: the NoData sentinel, the
/// coastal band and the masking/threshold rules applied while the
/// environment NetCDF is written. Several of them are consumed by the
/// Python writer, not by the engine (`ingest:` section of
/// model_constants.yaml).
struct IngestCfg {
    /// Float NoData sentinel written into the environment NetCDF and the
    /// COGs, and recognised when they are read back
    /// (`ingest.nodata_sentinel`).
    double nodata_sentinel = 0.0;
    /// Integer mirror of the NoData sentinel, used by the label-mode
    /// (categorical) writers (`ingest.nodata_sentinel_int`).
    int nodata_sentinel_int = 0;
    /// Fraction of the indoor host fraction attributed to residential cells
    /// when the building fraction is unavailable
    /// (`ingest.residential_from_indoor_frac`).
    double residential_from_indoor_frac = 0.0;
    /// Width of the coastal band that keeps its JRC water (historical name:
    /// it no longer dilates the land mask; see coastline.py sea_mask()).
    double coastline_buffer_m = 0.0;
    /// GSHHG resolution code for the coastline artifact: c/l/i/h/f.
    std::string coastline_resolution = "f";
    /// Land fraction below which an AOI cell counts as water.
    double sea_water_floor = 0.05;
    /// Default cell size (m) of the simulation grid when the run does not
    /// override the AOI resolution (`ingest.cell_size_hint_m`).
    double cell_size_hint_m = 0.0;
    /// Habitat-potential floor (index) applied by the ingest census when it
    /// marks candidate patches — a deliberately different role from
    /// habitat.candidate_min_engine, which the engine applies afterwards
    /// (`ingest.candidate_min_ingest`).
    double candidate_min_ingest = 0.0;
    /// Minimum radius (in cells) of the morphological dilation applied to
    /// the land/ocean masks (`ingest.min_dilation_radius_cells`). Loaded
    /// into this struct but read by no engine code.
    int min_dilation_radius_cells = 0;
    /// Maximum NoData fraction of a cell for it to count as valid
    /// (`ingest.fill_frac_valid_max`).
    double fill_frac_valid_max = 0.0;
    /// Land-fraction threshold of the ocean mask
    /// (`ingest.ocean_mask_threshold`). Loaded into this struct but read by
    /// no engine code.
    double ocean_mask_threshold = 0.0;
    /// Land-fraction threshold of the land mask (`ingest.land_mask_threshold`).
    /// Loaded into this struct but read by no engine code.
    double land_mask_threshold = 0.0;
    /// Tolerance (counts) below which a valid-pixel count is treated as zero
    /// (`ingest.valid_count_epsilon`).
    double valid_count_epsilon = 0.0;
    /// Maximum implicit step (degrees) allowed when reconstructing a grid
    /// expressed in degrees (`ingest.grid_degrees_step_max`).
    int grid_degrees_step_max = 0;
    /// zlib compression level used when writing the environment NetCDF — a
    /// file-format setting, not a model parameter
    /// (`ingest.nc_compression_level`).
    int nc_compression_level = 0;
};

/// Adult survival model: the Lardeux thermal Gaussian evaluated for every
/// adult on every day (`adults:` section of model_constants.yaml).
struct AdultsCfg {
    /// Basal daily survival probability of an adult female, used as the
    /// constant factor of the thermal Gaussian and as the survival when no
    /// temperature is available. The name is historical: the value is a
    /// survival probability per day, not a mortality rate
    /// (`adults.daily_mort_basal`).
    double daily_mort_basal = 0.0;
    /// Temperature (°C) at which the survival Gaussian peaks
    /// (`adults.opt_c`).
    double opt_c = 0.0;
    /// Standard deviation (°C) of the survival Gaussian (`adults.sigma_c`).
    double sigma_c = 0.0;
    /// Upper clamp (fraction in [0,1]) applied to the daily survival
    /// probability p_d (`adults.mort_cap`).
    double mort_cap = 0.0;
    /// Lower clamp (fraction in [0,1]) applied to the daily survival
    /// probability p_d (`adults.mort_floor`).
    double mort_floor = 0.0;
};

/// Degree-day model of the extrinsic incubation period of the parasite
/// (`eip:` section of model_constants.yaml).
struct EipCfg {
    /// Thermal base temperature (°C) of the degree-day accumulation: the
    /// daily increment is max(0, T - base_c) (`eip.base_c`).
    double base_c = 0.0;
    /// Accumulated degree-days (°C·days) the parasite must reach before
    /// the vector becomes infectious (`eip.threshold_gd`).
    double threshold_gd = 0.0;
};

/// Ross–Macdonald transmission parameters: the human SEI compartments and
/// the two bite-rate terms (`transmission:` section of
/// model_constants.yaml).
struct TransmissionCfg {
    /// Probability that an infectious human infects a vector per blood
    /// meal (`transmission.beta_hv`).
    double beta_hv = 0.0;
    /// Probability that an infectious vector infects a human per blood meal
    /// (`transmission.beta_vh`).
    double beta_vh = 0.0;
    /// Length (days) of the human incubation period, from infection to
    /// infectiousness (`transmission.human_incubation_days`).
    int human_incubation_days = 0;
    /// Length (days) a human remains infectious before recovering or
    /// entering the immune state (`transmission.human_infectious_days`).
    int human_infectious_days = 0;
    /// Length (days) of immunity after recovery; consulted only when
    /// immunity is enabled for the run
    /// (`transmission.human_immunity_days`).
    int human_immunity_days = 0;
    /// Initial fraction of the human population placed in the infectious
    /// state by the legacy uniform-initialisation mode
    /// (`transmission.initial_human_prevalence`).
    double initial_human_prevalence = 0.0;
    /// Initial fraction of adult females placed in the infectious state
    /// (`transmission.initial_vector_infected_frac`).
    double initial_vector_infected_frac = 0.0;
};

/// Thermal response curves: the aquatic development rates and the
/// temperature-dependent egg production rate (`thermal:` section of
/// model_constants.yaml).
struct ThermalCfg {
    /// Peak of the egg-production-rate curve (eggs per female per day),
    /// reached at efd_topt_c (`thermal.efd_max_eggs_per_day`).
    double efd_max_eggs_per_day = 0.0;
    /// Lower temperature threshold (°C) of the egg-production curve, where
    /// the rate falls to zero (`thermal.efd_tmin_c`).
    double efd_tmin_c = 0.0;
    /// Upper temperature threshold (°C) of the egg-production curve, where
    /// the rate falls to zero (`thermal.efd_tmax_c`).
    double efd_tmax_c = 0.0;
    /// Temperature (°C) at which the egg-production curve is maximal; used
    /// to normalise the birth-rate modifier to 1 (`thermal.efd_topt_c`).
    double efd_topt_c = 0.0;
    /// Lower threshold (°C) of the Brière-1 egg-development curve, below
    /// which eggs do not develop (`thermal.egg_development_tmin_c`).
    double egg_development_tmin_c = 0.0;
    /// Upper threshold (°C) of the Brière-1 egg-development curve, above
    /// which eggs do not develop (`thermal.egg_development_tmax_c`).
    double egg_development_tmax_c = 0.0;
    /// Scale coefficient a of the Brière-1 egg-development rate
    /// a * T * (T - T_L) * sqrt(T_H - T) (`thermal.egg_development_scale`).
    double egg_development_scale = 0.0;
    /// Lower threshold (°C) of the quadratic larval-development curve,
    /// below which larvae do not develop
    /// (`thermal.larva_development_tmin_c`).
    double larva_development_tmin_c = 0.0;
    /// Upper threshold (°C) of the quadratic larval-development curve,
    /// above which larvae do not develop
    /// (`thermal.larva_development_tmax_c`).
    double larva_development_tmax_c = 0.0;
    /// Scale coefficient a of the quadratic larval-development rate
    /// a * (T - T_L) * (T_H - T) (`thermal.larva_development_scale`).
    double larva_development_scale = 0.0;
    /// Lower threshold (°C) of the Brière-1 pupal-development curve, below
    /// which pupae do not develop (`thermal.pupa_development_tmin_c`).
    double pupa_development_tmin_c = 0.0;
    /// Upper threshold (°C) of the Brière-1 pupal-development curve, above
    /// which pupae do not develop (`thermal.pupa_development_tmax_c`).
    double pupa_development_tmax_c = 0.0;
    /// Scale coefficient a of the Brière-1 pupal-development rate
    /// a * T * (T - T_L) * sqrt(T_H - T) (`thermal.pupa_development_scale`).
    double pupa_development_scale = 0.0;
};

/// Gonotrophic cycle parameters: blood-feeding success, the egg-batch draw
/// and the post-feed resting time (`gonotrophic:` section of
/// model_constants.yaml).
struct GonotrophicCfg {
    /// Days (rounded up) a female needs to mature her eggs once the first
    /// gonotrophic cycle is over (`gonotrophic.cycle_duration_days`).
    double cycle_duration_days = 0.0;
    /// Days (rounded up) a female needs to mature the eggs of her first
    /// gonotrophic cycle (`gonotrophic.first_cycle_days`).
    double first_cycle_days = 0.0;
    /// Probability (fraction in [0,1]) that a probing female obtains a
    /// blood meal and enters the BLOOD_FED state
    /// (`gonotrophic.feeding_success_rate`).
    double feeding_success_rate = 0.0;
    /// Mean number of eggs of the binomial batch drawn at each oviposition
    /// (`gonotrophic.egg_batch_mean`).
    int egg_batch_mean = 0;
    /// Number of trials of the binomial egg-batch draw; the per-trial
    /// probability is egg_batch_mean / egg_batch_n
    /// (`gonotrophic.egg_batch_n`).
    int egg_batch_n = 0;
    /// Lower clamp (eggs) applied to the drawn egg batch
    /// (`gonotrophic.egg_batch_min`).
    int egg_batch_min = 0;
    /// Upper clamp (eggs) applied to the drawn egg batch
    /// (`gonotrophic.egg_batch_max`).
    int egg_batch_max = 0;
    /// Resting time (days, rounded to whole days) between blood feeding and
    /// the start of egg maturation (`gonotrophic.resting_duration_days`).
    double resting_duration_days = 0.0;
};

/// Movement of the adult stage: local diffusion, wind-driven migration and
/// the night window during which they occur (`dispersal:` section of
/// model_constants.yaml).
struct DispersalCfg {
    /// Probability (per day) that an adult disperses
    /// (`dispersal.adult_prob_day`).
    double adult_prob_day = 0.0;
    /// Standard deviation (m) of the Gaussian kernel of adult dispersal
    /// (`dispersal.adult_sigma_m`).
    double adult_sigma_m = 0.0;
    /// Maximum distance (m) an adult may cover in one dispersal event
    /// (`dispersal.adult_max_m`).
    double adult_max_m = 0.0;
    /// Probability (per day) that an adult migrates with the wind
    /// (`dispersal.wind_migration_prob`).
    double wind_migration_prob = 0.0;
    /// Duration (h) of the wind-driven flight (`dispersal.wind_flight_hours`).
    double wind_flight_hours = 0.0;
    /// Probability (fraction in [0,1]) that an adult survives the
    /// wind-driven flight (`dispersal.wind_survival`).
    double wind_survival = 0.0;
    /// Self-propelled flight speed (m/s) added to the wind speed during
    /// migration (`dispersal.wind_self_speed_ms`).
    double wind_self_speed_ms = 0.0;
    /// Hour of the day (0-23) at which the wind flight is triggered
    /// (`dispersal.flight_hour`).
    int flight_hour = 0;
    /// Length (m) of the step taken by a mosquito flying towards a detected
    /// host (`dispersal.host_flight_step_m`).
    double host_flight_step_m = 0.0;
    /// Radius (m) within which an adult is snapped to the nearest activated
    /// patch (`dispersal.snap_radius_m`).
    double snap_radius_m = 0.0;
    /// First hour (0-23) of the night window in which wind migration and
    /// the multirate schedule apply (`dispersal.night_start_hour`).
    int night_start_hour = 0;
    /// Exclusive last hour (0-23) of the night window; when it is not
    /// greater than night_start_hour the window wraps around midnight
    /// (`dispersal.night_end_hour`).
    int night_end_hour = 0;
};

/// Host-seeking behaviour: the engine-level attraction terms and the
/// detection geometry (`host_seeking:` section of model_constants.yaml).
/// The per-species plume scale and radius live in the species rows.
struct HostSeekingCfg {
    /// Maximum number of days a female can go without feeding before she
    /// dies of starvation (`host_seeking.starvation_days`).
    int starvation_days = 0;
    /// Additive term (dimensionless) added to a host cell's attraction in
    /// proportion to its indoor fraction
    /// (`host_seeking.indoor_attraction_add`).
    double indoor_attraction_add = 0.0;
    /// Additive term (dimensionless) scaling the attraction by the
    /// urbanicity of the cell (`host_seeking.urbanicity_add`).
    double urbanicity_add = 0.0;
    /// Indoor fraction (in [0,1]) assigned to urban cells of the host
    /// landscape (`host_seeking.indoor_fraction_urban`).
    double indoor_fraction_urban = 0.0;
    /// Indoor fraction (in [0,1]) assigned to rural cells of the host
    /// landscape (`host_seeking.indoor_fraction_rural`).
    double indoor_fraction_rural = 0.0;
    /// Detection radius (m) within which the engine's host-seeking kernel
    /// can see a host cell (`host_seeking.detect_range_m`). A different
    /// concept from the per-species attraction-field radius
    /// species.&lt;name&gt;.host_seeking_radius_m.
    double detect_range_m = 0.0;
    /// Length (m) of the step taken while approaching a detected host
    /// (`host_seeking.approach_step_m`).
    double approach_step_m = 0.0;
};

/// Search for a breeding site: the attraction plume and the geometry of
/// the search (`oviposition:` section of model_constants.yaml).
struct OvipositionCfg {
    /// Decay length (m) of the oviposition attraction plume around a
    /// breeding site (`oviposition.scale_m`).
    double scale_m = 0.0;
    /// Detection radius (m) within which a breeding site is visible to the
    /// oviposition kernel (`oviposition.detect_range_m`).
    double detect_range_m = 0.0;
    /// Length (m) of the step taken while moving towards a breeding site
    /// (`oviposition.step_m`).
    double step_m = 0.0;
    /// Minimum attraction (dimensionless) a breeding site must have for it
    /// to be accepted (`oviposition.min_attraction`).
    double min_attraction = 0.0;
    /// Maximum number of days a female keeps searching for a breeding site
    /// before giving up (`oviposition.timeout_days`).
    int timeout_days = 0;
};

/// Mortality and density dependence of the aquatic stages
/// (`aquatic_stages:` section of model_constants.yaml).
struct AquaticStagesCfg {
    /// Daily mortality rate (1/day) applied to the eggs of every patch
    /// (`aquatic_stages.egg_daily_mort`).
    double egg_daily_mort = 0.0;
    /// Daily mortality rate (1/day) applied to the pupae of every patch
    /// (`aquatic_stages.pupa_daily_mort`).
    double pupa_daily_mort = 0.0;
    /// Low-density survival fraction (in [0,1]) of the larval stage in the
    /// Beverton-Holt density response (`aquatic_stages.larva_bh_s0`).
    double larva_bh_s0 = 0.0;
    /// Competition coefficient alpha (dimensionless) of the Beverton-Holt
    /// larval density response p = S0 * K / (K + alpha * N)
    /// (`aquatic_stages.larva_bh_alpha`).
    double larva_bh_alpha = 0.0;
    /// Index of the last (most advanced) larval instar the engine tracks,
    /// e.g. L4 (`aquatic_stages.last_larval_instar`).
    int last_larval_instar = 0;
    /// Salinity (psu) assumed for a water body whose salinity measurement
    /// is missing — the freshwater anchor, which yields a suitability of 1
    /// (`aquatic_stages.salinity_missing_psu`).
    double salinity_missing_psu = 0.0;
};

/// Seeds of the engine's production random sub-streams; they make a run
/// reproducible and test fixtures do not belong here (`rng:` section of
/// model_constants.yaml).
struct RngCfg {
    /// Seed of the sub-stream that draws the rain washout of aquatic
    /// cohorts (`rng.aquatic_seed_washout`).
    int aquatic_seed_washout = 0;
    /// Seed of the sub-stream that draws egg and pupa stage mortality
    /// (`rng.aquatic_seed_stage_mortality`).
    int aquatic_seed_stage_mortality = 0;
    /// Seed of the sub-stream that draws larval density-dependent mortality
    /// (`rng.aquatic_seed_larva_mortality`).
    int aquatic_seed_larva_mortality = 0;
};

/// The whole parsed and validated model configuration: one member per
/// top-level section of model_constants.yaml.
struct ModelConfig {
    /// Schema version of model_constants.yaml; changing a frozen contract
    /// requires bumping it (`version`).
    int version = 0;
    /// The `contracts:` section — the frozen input/output contract versions.
    ContractsCfg contracts;
    /// The `habitat_types:` section — the habitat taxonomy, the
    /// persistent/pluvial dynamics of each type and the zone masks derived
    /// from them.
    HabitatCfg habitat_types;
    HabitatCfg habitat;   ///< activation/candidate thresholds
    /// The `pluvial:` section — the rain-driven wetness state of the
    /// seasonal habitats.
    PluvialCfg pluvial;
    /// The `aquatic_stress:` section — desiccation and rain washout.
    AquaticStressCfg aquatic_stress;
    /// The `urban:` section — built-surface corrections to the habitat
    /// potential.
    UrbanCfg urban;
    /// The `species:` section — the species rows, the active species and
    /// the capacity constant.
    SpeciesCfg species;
    /// The `capacity:` section — the availability of the persistent
    /// habitats.
    CapacityCfg capacity;
    /// The `geodesy:` section — Earth radius and the degrees-to-metres
    /// conversion.
    GeodesyCfg geodesy;
    /// The `ingest:` section — input-side constants and thresholds.
    IngestCfg ingest;
    /// The `adults:` section — the adult survival model.
    AdultsCfg adults;
    /// The `eip:` section — the degree-day incubation model.
    EipCfg eip;
    /// The `transmission:` section — human–vector transmission parameters.
    TransmissionCfg transmission;
    /// The `dispersal:` section — adult movement and the night window.
    DispersalCfg dispersal;
    /// The `host_seeking:` section — host-seeking behaviour.
    HostSeekingCfg host_seeking;
    /// The `oviposition:` section — the breeding-site search.
    OvipositionCfg oviposition;
    /// The `aquatic_stages:` section — aquatic mortality and density
    /// dependence.
    AquaticStagesCfg aquatic_stages;
    /// The `thermal:` section — thermal development and egg-production
    /// curves.
    ThermalCfg thermal;
    /// The `gonotrophic:` section — blood-feeding and egg-batch
    /// parameters.
    GonotrophicCfg gonotrophic;
    /// The `rng:` section — the production random seeds.
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

/// Habitat-accuracy threshold S above which a cell counts as a live
/// (activated) patch; reads habitat.activation_min_engine from the
/// configuration singleton.
inline float habitat_activation_min() {
    return static_cast<float>(load_config().habitat.activation_min_engine);
}

/// Habitat-potential floor a cell must clear to become a candidate patch;
/// reads habitat.candidate_min_engine from the configuration singleton.
inline float habitat_candidate_min_engine() {
    return static_cast<float>(load_config().habitat.candidate_min_engine);
}

}  // namespace mal_abm_fast
