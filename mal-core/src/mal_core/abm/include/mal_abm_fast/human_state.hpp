// SPDX-License-Identifier: MIT
// human_state.hpp — Spatial SEIR human compartment grid with discrete cohort queues.
//
// M7.4: Implements human malaria epidemiology on the ABM grid.
// Each grid cell maintains susceptible (S_H), exposed (E_H), infectious (I_H),
// and recovered (R_H) compartments.
//
// Discrete cohort queues (flat contiguous arrays) model non-Markovian fixed
// duration intrinsic incubation (E_H -> I_H), human infectious period (I_H -> R_H),
// and waning immunity (R_H -> S_H), avoiding exponential-dwell distortion.
#pragma once

#include <cstdint>
#include <vector>
#include <cmath>
#include <string>

#include "prng.hpp"

namespace mal_abm_fast {

struct HumanCompartmentStats {
    double total_susceptible = 0.0;
    double total_exposed     = 0.0;
    double total_infectious  = 0.0;
    double total_recovered   = 0.0;
    double total_population  = 0.0;
    double total_incidence   = 0.0;  // new E_H today across grid
    double mean_prevalence   = 0.0;  // total_infectious / total_population
};

class HumanCompartmentGrid {
public:
    HumanCompartmentGrid() = default;

    /// Initialize grid dimensions, cohort queues, and initial human population.
    /// If initial_prevalence > 0, seeds that fraction of humans as infectious (I_H).
    void init(int32_t h, int32_t w,
              const std::vector<float>& human_density,
              int32_t incubation_days = 12,
              int32_t infectious_days = 20,
              int32_t immunity_days = 180,
              bool immunity_enabled = false,
              double initial_prevalence = 0.0);

    /// Seed explicit infectious humans at a specific cell (row, col).
    void seed_infections(int32_t row, int32_t col, double count);

    /// Seed random viable foci: picks up to n_foci cells with population >= min_pop.
    /// Prefers cells with mosquito_density > 0 if mosquito_density is non-empty.
    /// Injects up to cases_per_focus into each selected cell as infectious humans (I_H).
    /// Returns vector of selected (row, col) coordinates.
    std::vector<std::pair<int32_t, int32_t>> seed_random_viable_foci(
        int32_t n_foci,
        double cases_per_focus,
        double min_pop,
        const std::vector<float>& mosquito_density,
        Prng& rng);

    /// Seed explicit foci list: vector of (row, col, cases).
    void seed_explicit_foci(
        const std::vector<std::tuple<int32_t, int32_t, double>>& foci);

    /// Advance one day given per-cell force of infection lambda_H in [0, 1].
    /// Computes new exposures S_H -> E_H via stochastic binomial sampling,
    /// advances discrete cohort queues E_H -> I_H, I_H -> R_H, R_H -> S_H,
    /// updates daily incidence and prevalence, and asserts conservation invariants.
    void advance_day(const std::vector<double>& force_of_infection, Prng& rng);

    // Grid properties
    int32_t h() const { return h_; }
    int32_t w() const { return w_; }
    int64_t total_cells() const { return static_cast<int64_t>(h_) * static_cast<int64_t>(w_); }

    // Compartment accessors (row-major, size h*w)
    const std::vector<double>& susceptible() const { return susceptible_; }
    const std::vector<double>& exposed()     const { return exposed_; }
    const std::vector<double>& infectious()  const { return infectious_; }
    const std::vector<double>& recovered()   const { return recovered_; }
    const std::vector<double>& population()  const { return population_; }
    const std::vector<double>& incidence()   const { return daily_incidence_; }
    const std::vector<double>& prevalence()  const { return daily_prevalence_; }

    // Single cell accessors
    double s_at(int32_t r, int32_t c) const { return susceptible_[r * w_ + c]; }
    double e_at(int32_t r, int32_t c) const { return exposed_[r * w_ + c]; }
    double i_at(int32_t r, int32_t c) const { return infectious_[r * w_ + c]; }
    double r_at(int32_t r, int32_t c) const { return recovered_[r * w_ + c]; }
    double pop_at(int32_t r, int32_t c) const { return population_[r * w_ + c]; }
    double prev_at(int32_t r, int32_t c) const { return daily_prevalence_[r * w_ + c]; }
    double inc_at(int32_t r, int32_t c) const { return daily_incidence_[r * w_ + c]; }

    // Grid-wide summary statistics
    HumanCompartmentStats compute_stats() const;

    // Parameters
    int32_t incubation_days() const { return incubation_days_; }
    int32_t infectious_days() const { return infectious_days_; }
    int32_t immunity_days()   const { return immunity_days_; }
    bool    immunity_enabled() const { return immunity_enabled_; }

    // Validate conservation invariants. Returns true if valid, throws if strict=true.
    bool validate_invariants(bool strict = true) const;

private:
    int32_t h_ = 0;
    int32_t w_ = 0;

    int32_t incubation_days_ = 12;
    int32_t infectious_days_ = 20;
    int32_t immunity_days_   = 180;
    bool    immunity_enabled_ = false;

    // Per-cell compartments
    std::vector<double> susceptible_;
    std::vector<double> exposed_;
    std::vector<double> infectious_;
    std::vector<double> recovered_;
    std::vector<double> population_;

    // Daily per-cell outputs
    std::vector<double> daily_incidence_;   // count of new E_H today
    std::vector<double> daily_prevalence_;  // I_H / population

    // Discrete age cohort queues: flat arrays of shape [total_cells * duration]
    // Entry at cell c, age a is at: c * duration + a
    std::vector<double> exposed_cohorts_;    // size = total_cells * incubation_days_
    std::vector<double> infectious_cohorts_; // size = total_cells * infectious_days_
    std::vector<double> recovered_cohorts_;  // size = total_cells * immunity_days_
};

}  // namespace mal_abm_fast
