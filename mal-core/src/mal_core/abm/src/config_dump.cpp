// SPDX-License-Identifier: MIT
// config_dump — dump the parsed model constants (plan constants-yaml
// test 4 / parity). Prints a flat JSON mapping "dotted.key" -> value; the
// Python parity test compares key-by-key (tolerance 1e-9) against the
// mal_core.habitat.config dump of the SAME file.
//
//   config_dump --yaml <path>     # dump the given file
//   config_dump                   # dump the resolved default path
#include <cstdio>
#include <iostream>
#include <string>

#include <nlohmann/json.hpp>

#include "mal_abm_fast/config.hpp"

namespace {

inline ::nlohmann::json json_of(const std::array<double, 4>& a) {
    ::nlohmann::json j = ::nlohmann::json::array();
    for (const double v : a) j.push_back(v);
    return j;
}

inline ::nlohmann::json json_of(const std::array<double, 5>& a) {
    ::nlohmann::json j = ::nlohmann::json::array();
    for (const double v : a) j.push_back(v);
    return j;
}

inline ::nlohmann::json json_of(const std::array<double, 6>& a) {
    ::nlohmann::json j = ::nlohmann::json::array();
    for (const double v : a) j.push_back(v);
    return j;
}

}  // namespace

int main(int argc, char** argv) {
    std::string path;
    for (int i = 1; i < argc; ++i) {
        const std::string arg = argv[i];
        if (arg == "--yaml" && i + 1 < argc) {
            path = argv[++i];
        } else if (arg == "--help" || arg == "-h") {
            std::cout << "usage: config_dump [--yaml <model_constants.yaml>]"
                      << "\n";
            return 0;
        }
    }
    try {
        const auto cfg = path.empty()
                             ? mal_abm_fast::load_config()
                             : mal_abm_fast::parse_config_file(path);
        ::nlohmann::json out;
        out["version"] = cfg.version;
        out["contracts.env_nc"] = cfg.contracts.env_nc;
        out["contracts.cogs_state"] = cfg.contracts.cogs_state;
        out["contracts.habitat"] = cfg.contracts.habitat;
        for (size_t i = 0; i < cfg.habitat_types.types.size(); ++i) {
            out["habitat_types.types." +
                std::to_string(i)] = cfg.habitat_types.types[i];
        }
        for (const auto& [name, dyn] : cfg.habitat_types.dynamics) {
            out["habitat_types.dynamics." + name] = dyn;
        }
        out["habitat_types.num_persistent"] =
            int(cfg.habitat_types.num_persistent);
        out["habitat.activation_min_engine"] =
            cfg.habitat.activation_min_engine;
        out["habitat.candidate_min_engine"] =
            cfg.habitat.candidate_min_engine;
        out["pluvial.rain_scale_mm"] = cfg.pluvial.rain_scale_mm;
        out["pluvial.dry_memory_days"] = cfg.pluvial.dry_memory_days;
        out["pluvial.delta_days"] = cfg.pluvial.delta_days;
        out["pluvial.cold_start_z"] = cfg.pluvial.cold_start_z;
        out["aquatic_stress.desicc_grace_days"] =
            cfg.aquatic_stress.desicc_grace_days;
        out["aquatic_stress.desicc_base_daily"] =
            cfg.aquatic_stress.desicc_base_daily;
        out["aquatic_stress.desicc_ramp_decay"] =
            cfg.aquatic_stress.desicc_ramp_decay;
        out["aquatic_stress.wash_threshold_mm"] =
            cfg.aquatic_stress.wash_threshold_mm;
        out["aquatic_stress.wash_fraction_max"] =
            cfg.aquatic_stress.wash_fraction_max;
        out["aquatic_stress.vulnerable_instar_max"] =
            cfg.aquatic_stress.vulnerable_instar_max;
        out["urban.beta_urban"] = cfg.urban.beta_urban;
        out["urban.rain_pools_built_damage"] =
            cfg.urban.rain_pools_built_damage;
        out["species.default_species"] = cfg.species.default_species;
        out["species.k_ref"] = cfg.species.k_ref;
        for (const auto& [name, row] : cfg.species.rows) {
            out["species." + name + ".weights"] = json_of(row.weights);
            out["species." + name + ".activity_weights"] =
                json_of(row.activity_weights);
            out["species." + name + ".pref"] = json_of(row.pref);
            out["species." + name + ".salinity_opt_ppt"] =
                row.salinity_opt_ppt;
            out["species." + name + ".salinity_slope"] = row.salinity_slope;
            out["species." + name + ".salinity_hi_tol_ppt"] =
                row.salinity_hi_tol_ppt;
            out["species." + name + ".co2_activation_radius_m"] =
                row.co2_activation_radius_m;
            out["species." + name + ".olfactory_radius_m"] =
                row.olfactory_radius_m;
            out["species." + name + ".visual_radius_m"] =
                row.visual_radius_m;
            out["species." + name + ".terminal_radius_m"] =
                row.terminal_radius_m;
            out["species." + name + ".flight_speed_ms"] =
                row.flight_speed_ms;
            out["species." + name + ".exploration_range_m"] =
                row.exploration_range_m;
            out["species." + name + ".exploration_step_m"] =
                row.exploration_step_m;
            out["species." + name + ".exploration_step_correlation"] =
                row.exploration_step_correlation;
            out["species." + name + ".casting_probability"] =
                row.casting_probability;
            out["species." + name + ".casting_angle_deg"] =
                row.casting_angle_deg;
            out["species." + name + ".plume_memory_s"] =
                row.plume_memory_s;
            out["species." + name + ".anemotaxis_rule"] =
                row.anemotaxis_rule;
            out["species." + name + ".anemotaxis_deviation_deg"] =
                row.anemotaxis_deviation_deg;
            out["species." + name + ".wind_reference"] =
                row.wind_reference;
            out["species." + name + ".wind_block_threshold_ms"] =
                row.wind_block_threshold_ms;
            out["species." + name + ".daily_move_capacity_m"] =
                row.daily_move_capacity_m;
            out["species." + name + ".directed_flight_budget_h"] =
                row.directed_flight_budget_h;
            out["species." + name + ".blood_meal_target_ul"] =
                row.blood_meal_target_ul;
            out["species." + name + ".first_cycle_target_ul"] =
                row.first_cycle_target_ul;
            out["species." + name + ".blood_meal_size_ul"] =
                row.blood_meal_size_ul;
            out["species." + name + ".meal_size_min_ul"] =
                row.meal_size_min_ul;
            out["species." + name + ".blood_meal_refractory_days"] =
                row.blood_meal_refractory_days;
            out["species." + name + ".probing_success_rate"] =
                row.probing_success_rate;
            out["species." + name + ".eggs_per_ul"] =
                row.eggs_per_ul;
            out["species." + name + ".arrested_daily_survival"] =
                row.arrested_daily_survival;
            out["species." + name + ".gonotrophic_arrest_prob_dry"] =
                row.gonotrophic_arrest_prob_dry;
            out["species." + name + ".aestivation_supported"] =
                row.aestivation_supported;
            out["species." + name + ".male_ratio"] =
                row.male_ratio;
            out["species." + name + ".male_daily_survival"] =
                row.male_daily_survival;
        }
        out["species.neutral.weights"] =
            json_of(cfg.species.neutral_weights);
        out["integration.phase_duration_hours"] =
            json_of(cfg.integration.phase_duration_hours);
        out["integration.directed_flight_budget_h"] =
            cfg.integration.directed_flight_budget_h;
        out["integration.dt_terminal_s"] =
            cfg.integration.dt_terminal_s;
        out["integration.dt_olfactory_s"] =
            cfg.integration.dt_olfactory_s;
        out["integration.plume_memory_s"] =
            cfg.integration.plume_memory_s;
        out["integration.landing_speed_mm_s"] =
            cfg.integration.landing_speed_mm_s;
        out["integration.landing_speed_hold_s"] =
            cfg.integration.landing_speed_hold_s;
        out["mating.p_mate_male_fraction"] =
            cfg.mating.p_mate_male_fraction;
        out["mating.p_mate_pairs_per_individual"] =
            cfg.mating.p_mate_pairs_per_individual;
        out["mating.p_mate_size_exponent"] =
            cfg.mating.p_mate_size_exponent;
        out["mating.male_swarm_reference_size"] =
            cfg.mating.male_swarm_reference_size;
        out["mating.female_attendance_rate"] =
            cfg.mating.female_attendance_rate;
        out["mating.local_swarm_male_offer_factor"] =
            cfg.mating.local_swarm_male_offer_factor;
        out["mating.male_move_capacity_m"] =
            cfg.mating.male_move_capacity_m;
        out["mating.male_females_per_night_max"] =
            cfg.mating.male_females_per_night_max;
        out["mating.swarm_duration_min"] =
            cfg.mating.swarm_duration_min;
        out["mating.swarm_start_min_after_sunset"] =
            cfg.mating.swarm_start_min_after_sunset;
        out["mating.swarm_height_m"] =
            cfg.mating.swarm_height_m;
        out["mating.swarm_markers_per_km2"] =
            cfg.mating.swarm_markers_per_km2;
        out["mating.swarm_markers_source"] =
            cfg.mating.swarm_markers_source;
        out["mating.rain_suppresses_swarming"] =
            cfg.mating.rain_suppresses_swarming;
        out["capacity.persistent_availability"] =
            cfg.capacity.persistent_availability;
        out["geodesy.earth_radius_m"] = cfg.geodesy.earth_radius_m;
        out["geodesy.metres_per_deg_lat"] = cfg.geodesy.metres_per_deg_lat;
        out["ingest.nodata_sentinel"] = cfg.ingest.nodata_sentinel;
        out["ingest.nodata_sentinel_int"] = cfg.ingest.nodata_sentinel_int;
        out["ingest.residential_from_indoor_frac"] =
            cfg.ingest.residential_from_indoor_frac;
        out["ingest.coastline_buffer_m"] = cfg.ingest.coastline_buffer_m;
        out["ingest.coastline_resolution"] = cfg.ingest.coastline_resolution;
        out["ingest.sea_water_floor"] = cfg.ingest.sea_water_floor;
        out["ingest.cell_size_hint_m"] = cfg.ingest.cell_size_hint_m;
        out["ingest.candidate_min_ingest"] = cfg.ingest.candidate_min_ingest;
        out["ingest.min_dilation_radius_cells"] =
            cfg.ingest.min_dilation_radius_cells;
        out["ingest.fill_frac_valid_max"] = cfg.ingest.fill_frac_valid_max;
        out["ingest.ocean_mask_threshold"] = cfg.ingest.ocean_mask_threshold;
        out["ingest.land_mask_threshold"] = cfg.ingest.land_mask_threshold;
        out["ingest.valid_count_epsilon"] = cfg.ingest.valid_count_epsilon;
        out["ingest.grid_degrees_step_max"] =
            cfg.ingest.grid_degrees_step_max;
        out["ingest.nc_compression_level"] =
            cfg.ingest.nc_compression_level;
        out["adults.daily_mort_basal"] = cfg.adults.daily_mort_basal;
        out["adults.opt_c"] = cfg.adults.opt_c;
        out["adults.sigma_c"] = cfg.adults.sigma_c;
        out["adults.mort_cap"] = cfg.adults.mort_cap;
        out["adults.mort_floor"] = cfg.adults.mort_floor;
        out["eip.base_c"] = cfg.eip.base_c;
        out["eip.threshold_gd"] = cfg.eip.threshold_gd;
        out["transmission.beta_hv"] = cfg.transmission.beta_hv;
        out["transmission.beta_vh"] = cfg.transmission.beta_vh;
        out["transmission.human_incubation_days"] =
            cfg.transmission.human_incubation_days;
        out["transmission.human_infectious_days"] =
            cfg.transmission.human_infectious_days;
        out["transmission.human_immunity_days"] =
            cfg.transmission.human_immunity_days;
        out["transmission.initial_human_prevalence"] =
            cfg.transmission.initial_human_prevalence;
        out["transmission.initial_vector_infected_frac"] =
            cfg.transmission.initial_vector_infected_frac;
        out["dispersal.wind_migration_prob"] =
            cfg.dispersal.wind_migration_prob;
        out["dispersal.wind_flight_hours"] = cfg.dispersal.wind_flight_hours;
        out["dispersal.wind_survival"] = cfg.dispersal.wind_survival;
        out["dispersal.wind_self_speed_ms"] =
            cfg.dispersal.wind_self_speed_ms;
        out["dispersal.flight_hour"] = cfg.dispersal.flight_hour;
        out["dispersal.snap_radius_m"] = cfg.dispersal.snap_radius_m;
        out["dispersal.night_start_hour"] = cfg.dispersal.night_start_hour;
        out["dispersal.night_end_hour"] = cfg.dispersal.night_end_hour;
        out["host_seeking.starvation_days"] =
            cfg.host_seeking.starvation_days;
        out["host_seeking.indoor_attraction_add"] =
            cfg.host_seeking.indoor_attraction_add;
        out["host_seeking.urbanicity_add"] =
            cfg.host_seeking.urbanicity_add;
        out["host_seeking.indoor_fraction_urban"] =
            cfg.host_seeking.indoor_fraction_urban;
        out["host_seeking.indoor_fraction_rural"] =
            cfg.host_seeking.indoor_fraction_rural;
        out["oviposition.scale_m"] = cfg.oviposition.scale_m;
        out["oviposition.detect_range_m"] = cfg.oviposition.detect_range_m;
        out["oviposition.step_m"] = cfg.oviposition.step_m;
        out["oviposition.min_attraction"] = cfg.oviposition.min_attraction;
        out["oviposition.timeout_days"] = cfg.oviposition.timeout_days;
        out["aquatic_stages.egg_daily_mort"] =
            cfg.aquatic_stages.egg_daily_mort;
        out["aquatic_stages.pupa_daily_mort"] =
            cfg.aquatic_stages.pupa_daily_mort;
        out["aquatic_stages.larva_bh_s0"] = cfg.aquatic_stages.larva_bh_s0;
        out["aquatic_stages.larva_bh_alpha"] =
            cfg.aquatic_stages.larva_bh_alpha;
        out["aquatic_stages.last_larval_instar"] =
            cfg.aquatic_stages.last_larval_instar;
        out["aquatic_stages.salinity_missing_psu"] =
            cfg.aquatic_stages.salinity_missing_psu;
        out["thermal.efd_max_eggs_per_day"] =
            cfg.thermal.efd_max_eggs_per_day;
        out["thermal.efd_tmin_c"] = cfg.thermal.efd_tmin_c;
        out["thermal.efd_tmax_c"] = cfg.thermal.efd_tmax_c;
        out["thermal.efd_topt_c"] = cfg.thermal.efd_topt_c;
        out["thermal.egg_development_tmin_c"] =
            cfg.thermal.egg_development_tmin_c;
        out["thermal.egg_development_tmax_c"] =
            cfg.thermal.egg_development_tmax_c;
        out["thermal.egg_development_scale"] =
            cfg.thermal.egg_development_scale;
        out["thermal.larva_development_tmin_c"] =
            cfg.thermal.larva_development_tmin_c;
        out["thermal.larva_development_tmax_c"] =
            cfg.thermal.larva_development_tmax_c;
        out["thermal.larva_development_scale"] =
            cfg.thermal.larva_development_scale;
        out["thermal.pupa_development_tmin_c"] =
            cfg.thermal.pupa_development_tmin_c;
        out["thermal.pupa_development_tmax_c"] =
            cfg.thermal.pupa_development_tmax_c;
        out["thermal.pupa_development_scale"] =
            cfg.thermal.pupa_development_scale;
        out["gonotrophic.cycle_duration_days"] =
            cfg.gonotrophic.cycle_duration_days;
        out["gonotrophic.first_cycle_days"] =
            cfg.gonotrophic.first_cycle_days;
        out["gonotrophic.feeding_success_rate"] =
            cfg.gonotrophic.feeding_success_rate;
        out["gonotrophic.egg_batch_mean"] =
            cfg.gonotrophic.egg_batch_mean;
        out["gonotrophic.egg_batch_n"] = cfg.gonotrophic.egg_batch_n;
        out["gonotrophic.egg_batch_min"] = cfg.gonotrophic.egg_batch_min;
        out["gonotrophic.egg_batch_max"] = cfg.gonotrophic.egg_batch_max;
        out["gonotrophic.resting_duration_days"] =
            cfg.gonotrophic.resting_duration_days;
        out["rng.aquatic_seed_washout"] = cfg.rng.aquatic_seed_washout;
        out["rng.aquatic_seed_stage_mortality"] =
            cfg.rng.aquatic_seed_stage_mortality;
        out["rng.aquatic_seed_larva_mortality"] =
            cfg.rng.aquatic_seed_larva_mortality;
        std::cout << out.dump() << "\n";
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "config_dump: " << e.what() << "\n";
        return 1;
    }
}
