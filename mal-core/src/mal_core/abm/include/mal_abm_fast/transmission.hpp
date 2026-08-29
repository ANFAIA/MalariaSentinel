// SPDX-License-Identifier: MIT
// transmission.hpp — Ross-Macdonald spatial SEIR-SEI malaria transmission model.
//
// M7.4: Implements bidirectional transmission between mosquitoes and humans:
//   Vector: S_V -> E_V -> I_V
//   Human:  S_H -> E_H -> I_H -> R_H -> S_H
//
// Force of infection:
//   lambda_H(x) = 1 - exp(- sum_s [ a_s(x) * beta_vh_s * I_V_s(x) / H(x) ])
//   lambda_V(x) = beta_hv * I_H(x) / H(x)  (per blood meal on human)
#pragma once

#include <cstdint>
#include <memory>
#include <string>
#include <vector>

#include "aoi.hpp"
#include "bite_ledger.hpp"
#include "climate.hpp"
#include "eip.hpp"
#include "human_state.hpp"
#include "mosquito_state.hpp"
#include "prng.hpp"
#include "wire.hpp"

namespace mal_abm_fast {

/// Parameters for SEIR-SEI transmission.
struct TransmissionParams {
    bool enabled = false;

    // Transmission efficiencies
    float beta_hv = 0.40f;   // Human-to-vector transmission probability per infectious bite
    float beta_vh = 0.50f;   // Vector-to-human transmission probability per infectious bite

    // Human epidemiology durations (days)
    int32_t human_incubation_days = 12;   // Intrinsic incubation period (E_H -> I_H)
    int32_t human_infectious_days = 20;   // Human infectious duration (I_H -> R_H / S_H)
    int32_t immunity_duration_days = 180; // Waning immunity duration (R_H -> S_H)
    bool    immunity_enabled       = false; // If false: SIS-like I_H -> S_H recovery

    // Initial infection conditions
    double initial_human_prevalence     = 0.05; // Initial I_H fraction in inhabited cells (used if mode == "uniform-legacy")
    double initial_vector_infected_frac = 0.0;  // Initial I_V fraction in adult females
    std::string initial_infected_path   = "";   // Optional raster/json path

    // Focal seeding & outbreak control (M7.4.1)
    std::string human_seeding_mode        = "random-viable"; // "random-viable" | "explicit" | "uniform-legacy" | "none"
    int32_t     human_outbreak_day        = 0;               // Day to trigger human outbreak (0 = day 0)
    int32_t     human_outbreak_foci       = 3;               // Number of random foci
    double      human_outbreak_cases      = 50.0;            // Cases per focus
    double      human_min_cell_pop        = 50.0;            // Minimum human population in candidate cell
    std::string human_foci_coords         = "";              // "r1,c1:N1;r2,c2:N2"
    // Cluster mode (M7.4.1 iteration): when > 0, all outbreak cases are
    // seeded as ONE spatially concentrated outbreak — a single core cell
    // (random-viable: highest-population viable cell; explicit: the given
    // coordinate) plus satellite cells within this radius (in grid cells;
    // a 1 km cell ⇒ radius_km * 1000 / resolution_m). Cases are split
    // across cluster cells ∝ cell population. 0 = legacy behaviour
    // (independent foci wherever viability picks them).
    double      human_cluster_radius_km   = 0.0;
    int32_t     human_cluster_radius_cells = 0;               // derived by the CLI from radius_km / resolution

    // Threshold for active transmission focus band
    float focus_threshold = 0.01f;

    // EIP parameters (Plasmodium falciparum extrinsic incubation period)
    float eip_base_temp     = EIP_BASE_C;       // 16.0 deg C
    float eip_threshold_gd  = EIP_THRESHOLD_GD; // 110.0 GDD
};

/// Daily aggregated statistics for transmission.
struct TransmissionDailyStats {
    int64_t day = 0;

    // Human compartments & rates
    double total_humans     = 0.0;
    double human_s          = 0.0;
    double human_e          = 0.0;
    double human_i          = 0.0;
    double human_r          = 0.0;
    double human_incidence  = 0.0;  // new E_H today
    double human_prevalence = 0.0;  // I_H / H

    // Vector compartments
    int64_t vector_s     = 0;
    int64_t vector_e     = 0;
    int64_t vector_i     = 0;
    int64_t vector_total = 0;

    // Feeding & transmission pressure
    int64_t total_bites_on_humans = 0;
    int64_t infectious_bites      = 0;
    double  r_eff_approx          = 0.0;
};

class TransmissionModel {
public:
    TransmissionModel() = default;

    /// Initialize transmission model with grid dimensions, host landscape, and parameters.
    void init(int32_t h, int32_t w,
              const std::vector<float>& human_density,
              const TransmissionParams& params,
              uint64_t seed);

    /// Seed initial vector infections in adult females (fraction of females become I_V).
    void seed_vector_infections(MosquitoSoA& soa, double fraction);

    /// Seed explicit human infections at a specific cell.
    void seed_human_infections(int32_t row, int32_t col, double count);

    /// Seed random viable foci: picks up to n_foci cells and injects cases.
    std::vector<std::pair<int32_t, int32_t>> seed_random_viable_foci(
        int32_t n_foci,
        double cases_per_focus,
        double min_pop,
        const std::vector<float>& mosquito_density);

    /// Seed explicit foci: vector of (row, col, cases).
    void seed_explicit_foci(
        const std::vector<std::tuple<int32_t, int32_t, double>>& foci);

    /// Check and trigger human outbreak if day matches human_outbreak_day.
    void check_and_trigger_outbreak(int64_t day_index, const std::vector<float>& mosquito_density);

    bool outbreak_triggered() const { return outbreak_triggered_; }

    /// Audit record for one seeded focus (plan §5.2: foci must be logged).
    struct FociLogEntry {
        int32_t row  = 0;
        int32_t col  = 0;
        double  cases           = 0.0;  // actually seeded (post-truncation)
        double  cell_population = 0.0;  // human population of the cell
        float   mosquito_density = 0.0f; // adult density in the cell at seed time
        bool    truncated = false;      // true when cases were capped by cell pop
    };

    /// Foci seeded by the most recent (successful) outbreak trigger.
    const std::vector<FociLogEntry>& last_foci_log() const { return last_foci_log_; }

    /// Dump the last foci log to `path` as a small JSON sidecar.
    void write_foci_log(const std::string& path) const;

    /// Advance extrinsic incubation period (EIP) for all exposed adult females (E_V -> I_V).
    void advance_vector_eip(MosquitoSoA& soa,
                            const ClimateEngine& climate,
                            const std::vector<PatchState>& patch_states,
                            const AOI& aoi);

    /// Advance human SEIR transitions (S_H -> E_H -> I_H -> R_H -> S_H) given today's bite ledger.
    void advance_human_transmission(const BiteLedger& bite_ledger, const AOI& aoi);

    /// Record daily stats from current state.
    void record_daily_stats(int64_t day,
                            const MosquitoSoA& soa,
                            const BiteLedger& bite_ledger);

    // Accessors
    const HumanCompartmentGrid& human_grid() const { return human_grid_; }
    HumanCompartmentGrid& human_grid_mutable() { return human_grid_; }
    const TransmissionParams& params() const { return params_; }
    TransmissionParams& params_mutable() { return params_; }

    const TransmissionDailyStats& last_day_stats() const { return last_day_stats_; }
    const std::vector<TransmissionDailyStats>& history() const { return history_; }

    bool is_enabled() const { return params_.enabled; }

    /// Force of infection lambda_H grid for today (row-major, size h*w)
    const std::vector<double>& last_force_of_infection() const { return lambda_h_; }

    /// Infectious vector pressure grid (infectious bites delivered today per cell)
    const std::vector<float>& infectious_pressure_grid() const { return infectious_pressure_; }

private:
    HumanCompartmentGrid human_grid_;
    TransmissionParams   params_;
    Prng                 rng_;

    int32_t h_ = 0;
    int32_t w_ = 0;

    std::vector<double> lambda_h_;             // force of infection on humans
    std::vector<float>  infectious_pressure_;  // infectious bites per cell today
    TransmissionDailyStats last_day_stats_{};
    std::vector<TransmissionDailyStats> history_;
    bool outbreak_triggered_ = false;
    std::vector<FociLogEntry> last_foci_log_;
};

}  // namespace mal_abm_fast
