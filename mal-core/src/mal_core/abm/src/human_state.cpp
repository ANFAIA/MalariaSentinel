// SPDX-License-Identifier: MIT
// human_state.cpp — Spatial SEIR human compartment grid implementation.
#include "mal_abm_fast/human_state.hpp"

#include <algorithm>
#include <cmath>
#include <numeric>
#include <stdexcept>
#include <string>

namespace mal_abm_fast {

void HumanCompartmentGrid::init(
    int32_t h, int32_t w,
    const std::vector<float>& human_density,
    int32_t incubation_days,
    int32_t infectious_days,
    int32_t immunity_days,
    bool immunity_enabled,
    double initial_prevalence)
{
    if (h <= 0 || w <= 0) {
        throw std::invalid_argument("HumanCompartmentGrid: invalid grid dimensions");
    }
    h_ = h;
    w_ = w;
    const int64_t n_cells = static_cast<int64_t>(h_) * static_cast<int64_t>(w_);
    if (static_cast<int64_t>(human_density.size()) != n_cells) {
        throw std::invalid_argument(
            "HumanCompartmentGrid: human_density size (" +
            std::to_string(human_density.size()) + ") does not match h*w (" +
            std::to_string(n_cells) + ")");
    }

    incubation_days_ = std::max(1, incubation_days);
    infectious_days_ = std::max(1, infectious_days);
    immunity_days_   = std::max(1, immunity_days);
    immunity_enabled_ = immunity_enabled;

    susceptible_.assign(static_cast<size_t>(n_cells), 0.0);
    exposed_.assign(static_cast<size_t>(n_cells), 0.0);
    infectious_.assign(static_cast<size_t>(n_cells), 0.0);
    recovered_.assign(static_cast<size_t>(n_cells), 0.0);
    population_.assign(static_cast<size_t>(n_cells), 0.0);
    daily_incidence_.assign(static_cast<size_t>(n_cells), 0.0);
    daily_prevalence_.assign(static_cast<size_t>(n_cells), 0.0);

    exposed_cohorts_.assign(
        static_cast<size_t>(n_cells * incubation_days_), 0.0);
    infectious_cohorts_.assign(
        static_cast<size_t>(n_cells * infectious_days_), 0.0);
    recovered_cohorts_.assign(
        static_cast<size_t>(n_cells * immunity_days_), 0.0);

    const double init_prev = std::clamp(initial_prevalence, 0.0, 1.0);

    for (int64_t c = 0; c < n_cells; ++c) {
        const double pop = std::max(0.0, static_cast<double>(human_density[static_cast<size_t>(c)]));
        population_[static_cast<size_t>(c)] = pop;

        if (pop > 0.0 && init_prev > 0.0) {
            const double init_inf = pop * init_prev;
            const double init_susc = pop - init_inf;
            susceptible_[static_cast<size_t>(c)] = init_susc;
            infectious_[static_cast<size_t>(c)]  = init_inf;
            daily_prevalence_[static_cast<size_t>(c)] = init_prev;

            // Distribute initial infected evenly across the infectious cohort queue
            const double per_day = init_inf / static_cast<double>(infectious_days_);
            for (int32_t a = 0; a < infectious_days_; ++a) {
                infectious_cohorts_[static_cast<size_t>(c * infectious_days_ + a)] = per_day;
            }
        } else {
            susceptible_[static_cast<size_t>(c)] = pop;
        }
    }
}

void HumanCompartmentGrid::seed_infections(int32_t row, int32_t col, double count) {
    if (row < 0 || row >= h_ || col < 0 || col >= w_) return;
    const size_t c = static_cast<size_t>(row * w_ + col);
    const double pop = population_[c];
    if (pop <= 0.0 || count <= 0.0) return;

    // Convert up to available susceptible to infectious
    const double to_infect = std::min(count, susceptible_[c]);
    if (to_infect <= 0.0) return;

    susceptible_[c] -= to_infect;
    infectious_[c]  += to_infect;

    // Imported cases enter at infectious age zero, not as an already-aged cohort.
    infectious_cohorts_[static_cast<size_t>(c * infectious_days_)] += to_infect;
    daily_prevalence_[c] = infectious_[c] / pop;
}

std::vector<std::pair<int32_t, int32_t>> HumanCompartmentGrid::seed_random_viable_foci(
    int32_t n_foci,
    double cases_per_focus,
    double min_pop,
    const std::vector<float>& mosquito_density,
    Prng& rng)
{
    std::vector<std::pair<int32_t, int32_t>> seeded;
    if (n_foci <= 0 || cases_per_focus <= 0.0) return seeded;

    const int64_t n_cells = total_cells();
    std::vector<int64_t> with_mosquitoes;

    for (int64_t c = 0; c < n_cells; ++c) {
        const size_t idx = static_cast<size_t>(c);
        if (population_[idx] >= min_pop && susceptible_[idx] > 0.0) {
            if (!mosquito_density.empty() && idx < mosquito_density.size() &&
                mosquito_density[idx] > 0.0f)
            {
                with_mosquitoes.push_back(c);
            }
        }
    }

    // A viable outbreak focus needs local vectors; human-only fallback would
    // falsely report transmission establishment.
    if (with_mosquitoes.empty()) return seeded;
    std::vector<int64_t>& pool = with_mosquitoes;

    // Shuffle pool using Fisher-Yates
    for (size_t i = pool.size() - 1; i > 0; --i) {
        size_t j = static_cast<size_t>(rng.uniform_double() * static_cast<double>(i + 1));
        if (j > i) j = i;
        std::swap(pool[i], pool[j]);
    }

    const size_t count = std::min(static_cast<size_t>(n_foci), pool.size());
    for (size_t i = 0; i < count; ++i) {
        const int64_t c = pool[i];
        const int32_t r = static_cast<int32_t>(c / w_);
        const int32_t col = static_cast<int32_t>(c % w_);
        seed_infections(r, col, cases_per_focus);
        seeded.push_back({r, col});
    }

    return seeded;
}

void HumanCompartmentGrid::seed_explicit_foci(
    const std::vector<std::tuple<int32_t, int32_t, double>>& foci)
{
    for (const auto& [r, c, cases] : foci) {
        seed_infections(r, c, cases);
    }
}

void HumanCompartmentGrid::advance_day(
    const std::vector<double>& force_of_infection,
    Prng& rng)
{
    const int64_t n_cells = total_cells();
    if (static_cast<int64_t>(force_of_infection.size()) != n_cells) {
        throw std::invalid_argument("HumanCompartmentGrid::advance_day: force_of_infection size mismatch");
    }

    for (int64_t c = 0; c < n_cells; ++c) {
        const size_t idx = static_cast<size_t>(c);
        const double pop = population_[idx];
        if (pop <= 0.0) {
            daily_incidence_[idx]  = 0.0;
            daily_prevalence_[idx] = 0.0;
            continue;
        }

        const double lambda = std::clamp(force_of_infection[idx], 0.0, 1.0);
        double s = susceptible_[idx];

        // 1. New exposures from Susceptible: S_H -> E_H
        double new_exposed = 0.0;
        if (s > 0.0 && lambda > 0.0) {
            // If population is integer-like or large, binomial draw
            const int64_t s_int = static_cast<int64_t>(std::round(s));
            if (s_int > 0) {
                const int64_t draws = rng.binomial(s_int, lambda);
                new_exposed = std::min(s, static_cast<double>(draws));
            } else {
                new_exposed = s * lambda;
            }
        }
        new_exposed = std::clamp(new_exposed, 0.0, s);
        s -= new_exposed;
        daily_incidence_[idx] = new_exposed;

        // 2. Advance Exposed Cohorts: E_H -> I_H
        // The oldest exposed cohort leaves exposed state and enters infectious
        const size_t exp_offset = static_cast<size_t>(c * incubation_days_);
        const double maturing_e = exposed_cohorts_[exp_offset + static_cast<size_t>(incubation_days_ - 1)];

        for (int32_t a = incubation_days_ - 1; a >= 1; --a) {
            exposed_cohorts_[exp_offset + static_cast<size_t>(a)] =
                exposed_cohorts_[exp_offset + static_cast<size_t>(a - 1)];
        }
        exposed_cohorts_[exp_offset + 0] = new_exposed;

        double sum_e = 0.0;
        for (int32_t a = 0; a < incubation_days_; ++a) {
            sum_e += exposed_cohorts_[exp_offset + static_cast<size_t>(a)];
        }
        exposed_[idx] = sum_e;

        // 3. Advance Infectious Cohorts: I_H -> R_H (or S_H if no immunity)
        // The oldest infectious cohort recovers
        const size_t inf_offset = static_cast<size_t>(c * infectious_days_);
        const double recovering_i = infectious_cohorts_[inf_offset + static_cast<size_t>(infectious_days_ - 1)];

        for (int32_t a = infectious_days_ - 1; a >= 1; --a) {
            infectious_cohorts_[inf_offset + static_cast<size_t>(a)] =
                infectious_cohorts_[inf_offset + static_cast<size_t>(a - 1)];
        }
        infectious_cohorts_[inf_offset + 0] = maturing_e;

        double sum_i = 0.0;
        for (int32_t a = 0; a < infectious_days_; ++a) {
            sum_i += infectious_cohorts_[inf_offset + static_cast<size_t>(a)];
        }
        infectious_[idx] = sum_i;

        // 4. Advance Recovered Cohorts / Immunity: R_H -> S_H
        if (immunity_enabled_ && immunity_days_ > 0) {
            const size_t rec_offset = static_cast<size_t>(c * immunity_days_);
            const double waning_r = recovered_cohorts_[rec_offset + static_cast<size_t>(immunity_days_ - 1)];

            for (int32_t a = immunity_days_ - 1; a >= 1; --a) {
                recovered_cohorts_[rec_offset + static_cast<size_t>(a)] =
                    recovered_cohorts_[rec_offset + static_cast<size_t>(a - 1)];
            }
            recovered_cohorts_[rec_offset + 0] = recovering_i;

            double sum_r = 0.0;
            for (int32_t a = 0; a < immunity_days_; ++a) {
                sum_r += recovered_cohorts_[rec_offset + static_cast<size_t>(a)];
            }
            recovered_[idx] = sum_r;

            s += waning_r;
        } else {
            // Direct recovery without immunity: I_H -> S_H
            s += recovering_i;
            recovered_[idx] = 0.0;
        }

        // Clamp S to ensure total conservation
        s = std::max(0.0, pop - (exposed_[idx] + infectious_[idx] + recovered_[idx]));
        susceptible_[idx] = s;
        daily_prevalence_[idx] = infectious_[idx] / pop;
    }
}

HumanCompartmentStats HumanCompartmentGrid::compute_stats() const {
    HumanCompartmentStats stats;
    const int64_t n = total_cells();
    for (int64_t i = 0; i < n; ++i) {
        const size_t idx = static_cast<size_t>(i);
        stats.total_susceptible += susceptible_[idx];
        stats.total_exposed     += exposed_[idx];
        stats.total_infectious  += infectious_[idx];
        stats.total_recovered   += recovered_[idx];
        stats.total_population  += population_[idx];
        stats.total_incidence   += daily_incidence_[idx];
    }
    if (stats.total_population > 0.0) {
        stats.mean_prevalence = stats.total_infectious / stats.total_population;
    }
    return stats;
}

bool HumanCompartmentGrid::validate_invariants(bool strict) const {
    const int64_t n = total_cells();
    for (int64_t i = 0; i < n; ++i) {
        const size_t idx = static_cast<size_t>(i);
        const double s = susceptible_[idx];
        const double e = exposed_[idx];
        const double inf = infectious_[idx];
        const double r = recovered_[idx];
        const double pop = population_[idx];

        if (s < -1e-6 || e < -1e-6 || inf < -1e-6 || r < -1e-6) {
            if (strict) {
                throw std::runtime_error(
                    "HumanCompartmentGrid invariant violation: negative compartment at cell " +
                    std::to_string(i) + " (S=" + std::to_string(s) + ", E=" +
                    std::to_string(e) + ", I=" + std::to_string(inf) + ", R=" +
                    std::to_string(r) + ")");
            }
            return false;
        }

        const double sum = s + e + inf + r;
        const double diff = std::abs(sum - pop);
        const double tol = 1e-3 * std::max(1.0, pop) + 1e-4;
        if (diff > tol) {
            if (strict) {
                throw std::runtime_error(
                    "HumanCompartmentGrid invariant violation: mass not conserved at cell " +
                    std::to_string(i) + " (sum=" + std::to_string(sum) + ", pop=" +
                    std::to_string(pop) + ", diff=" + std::to_string(diff) + ")");
            }
            return false;
        }
    }
    return true;
}

}  // namespace mal_abm_fast
