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
    double initial_human_prevalence     = 0.05; // Initial I_H fraction in inhabited cells
    double initial_vector_infected_frac = 0.0;  // Initial I_V fraction in adult females
    std::string initial_infected_path   = "";   // Optional raster/json path

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
};

}  // namespace mal_abm_fast
