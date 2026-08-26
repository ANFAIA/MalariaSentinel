// SPDX-License-Identifier: MIT
// transmission.cpp — Ross-Macdonald spatial SEIR-SEI malaria transmission implementation.
#include "mal_abm_fast/transmission.hpp"

#include <algorithm>
#include <cmath>
#include <iostream>
#include <stdexcept>

namespace mal_abm_fast {

namespace {

std::vector<std::tuple<int32_t, int32_t, double>> parse_explicit_foci(
    const std::string& str, double default_cases)
{
    std::vector<std::tuple<int32_t, int32_t, double>> result;
    if (str.empty()) return result;

    size_t start = 0;
    while (start < str.size()) {
        size_t end = str.find(';', start);
        if (end == std::string::npos) end = str.size();
        std::string token = str.substr(start, end - start);
        start = end + 1;

        if (token.empty()) continue;
        double cases = default_cases;
        size_t colon_pos = token.find(':');
        if (colon_pos != std::string::npos) {
            try {
                cases = std::stod(token.substr(colon_pos + 1));
            } catch (...) {}
            token = token.substr(0, colon_pos);
        }

        size_t comma_pos = token.find(',');
        if (comma_pos != std::string::npos) {
            try {
                int32_t r = std::stoi(token.substr(0, comma_pos));
                int32_t c = std::stoi(token.substr(comma_pos + 1));
                result.push_back({r, c, cases});
            } catch (...) {}
        }
    }
    return result;
}

}  // namespace

void TransmissionModel::init(
    int32_t h, int32_t w,
    const std::vector<float>& human_density,
    const TransmissionParams& params,
    uint64_t seed)
{
    h_ = h;
    w_ = w;
    params_ = params;
    rng_ = Prng(seed);

    const int64_t n_cells = static_cast<int64_t>(h_) * static_cast<int64_t>(w_);
    lambda_h_.assign(static_cast<size_t>(n_cells), 0.0);
    infectious_pressure_.assign(static_cast<size_t>(n_cells), 0.0f);
    history_.clear();
    last_day_stats_ = TransmissionDailyStats{};
    outbreak_triggered_ = false;

    double init_prev = (params_.human_seeding_mode == "uniform-legacy")
        ? params_.initial_human_prevalence : 0.0;

    human_grid_.init(
        h_, w_, human_density,
        params_.human_incubation_days,
        params_.human_infectious_days,
        params_.immunity_duration_days,
        params_.immunity_enabled,
        init_prev);

}

void TransmissionModel::seed_vector_infections(MosquitoSoA& soa, double fraction) {
    if (fraction <= 0.0) return;
    const double frac = std::clamp(fraction, 0.0, 1.0);

    for (int64_t i = 0; i < soa.n_alive; ++i) {
        const size_t si = static_cast<size_t>(i);
        if (soa.stage[si] != 1 || soa.sex[si] != 1) continue;  // adult females only

        if (rng_.uniform_double() < frac) {
            soa.vector_state[si] = static_cast<uint8_t>(VectorTransmissionState::INFECTIOUS);
            soa.parasite_eip_progress[si] = params_.eip_threshold_gd;
        }
    }
}

void TransmissionModel::seed_human_infections(int32_t row, int32_t col, double count) {
    human_grid_.seed_infections(row, col, count);
}

std::vector<std::pair<int32_t, int32_t>> TransmissionModel::seed_random_viable_foci(
    int32_t n_foci,
    double cases_per_focus,
    double min_pop,
    const std::vector<float>& mosquito_density)
{
    return human_grid_.seed_random_viable_foci(n_foci, cases_per_focus, min_pop, mosquito_density, rng_);
}

void TransmissionModel::seed_explicit_foci(
    const std::vector<std::tuple<int32_t, int32_t, double>>& foci)
{
    human_grid_.seed_explicit_foci(foci);
}

void TransmissionModel::check_and_trigger_outbreak(
    int64_t day_index,
    const std::vector<float>& mosquito_density)
{
    if (outbreak_triggered_) return;
    if (day_index < params_.human_outbreak_day) return;
    if (params_.human_seeding_mode == "none" || params_.human_seeding_mode == "uniform-legacy") {
        outbreak_triggered_ = true;
        return;
    }

    if (params_.human_seeding_mode == "random-viable") {
        if (mosquito_density.empty()) {
            std::cerr << "warning: outbreak not seeded: no current mosquito density\n";
            return;
        }
        const double infectious_before = human_grid_.compute_stats().total_infectious;
        human_grid_.seed_random_viable_foci(
            params_.human_outbreak_foci,
            params_.human_outbreak_cases,
            params_.human_min_cell_pop,
            mosquito_density,
            rng_);
        const double infectious_after = human_grid_.compute_stats().total_infectious;
        outbreak_triggered_ = infectious_after > infectious_before;
        if (!outbreak_triggered_) {
            std::cerr << "warning: outbreak not seeded: no viable focus received cases\n";
        }
    } else if (params_.human_seeding_mode == "explicit") {
        auto foci = parse_explicit_foci(params_.human_foci_coords, params_.human_outbreak_cases);
        const double infectious_before = human_grid_.compute_stats().total_infectious;
        human_grid_.seed_explicit_foci(foci);
        const double infectious_after = human_grid_.compute_stats().total_infectious;
        outbreak_triggered_ = infectious_after > infectious_before;
        if (!outbreak_triggered_) {
            std::cerr << "warning: outbreak not seeded: explicit foci received no cases\n";
        }
    }
}

void TransmissionModel::advance_vector_eip(
    MosquitoSoA& soa,
    const ClimateEngine& climate,
    const std::vector<PatchState>& patch_states,
    const AOI& aoi)
{
    (void)patch_states;
    (void)aoi;

    for (int64_t i = 0; i < soa.n_alive; ++i) {
        const size_t si = static_cast<size_t>(i);
        if (soa.stage[si] != 1 || soa.sex[si] != 1) continue;  // adult females only
        if (soa.vector_state[si] != static_cast<uint8_t>(VectorTransmissionState::EXPOSED)) continue;

        const int32_t r = soa.row[si];
        const int32_t c = soa.col[si];
        float temp = climate.temp_at(r, c);
        if (!std::isfinite(static_cast<double>(temp))) {
            temp = ADULT_TEMP_FALLBACK_C;
        }

        const float new_eip = accumulate_eip(soa.parasite_eip_progress[si], temp);
        soa.parasite_eip_progress[si] = new_eip;

        if (is_infective(new_eip)) {
            soa.vector_state[si] = static_cast<uint8_t>(VectorTransmissionState::INFECTIOUS);
        }
    }
}

void TransmissionModel::advance_human_transmission(
    const BiteLedger& bite_ledger,
    const AOI& aoi)
{
    (void)aoi;
    const int64_t n_cells = static_cast<int64_t>(h_) * static_cast<int64_t>(w_);
    std::fill(lambda_h_.begin(), lambda_h_.end(), 0.0);
    std::fill(infectious_pressure_.begin(), infectious_pressure_.end(), 0.0f);

    // Aggregate infectious bites on humans from BiteLedger
    for (const auto& agg : bite_ledger.today()) {
        if (agg.host != HostType::HUMAN) continue;
        if (agg.row < 0 || agg.row >= h_ || agg.col < 0 || agg.col >= w_) continue;

        const size_t idx = static_cast<size_t>(agg.row * w_ + agg.col);
        infectious_pressure_[idx] += static_cast<float>(agg.infectious_meals);
    }

    // Compute force of infection lambda_H(x) = 1 - exp(- beta_vh * I_bites(x) / H(x))
    for (int64_t c = 0; c < n_cells; ++c) {
        const size_t idx = static_cast<size_t>(c);
        const double pop = human_grid_.population()[idx];
        const double i_bites = static_cast<double>(infectious_pressure_[idx]);

        if (pop > 0.0 && i_bites > 0.0) {
            const double exponent = -static_cast<double>(params_.beta_vh) * (i_bites / pop);
            const double lambda = 1.0 - std::exp(exponent);
            lambda_h_[idx] = std::clamp(lambda, 0.0, 1.0);
        } else {
            lambda_h_[idx] = 0.0;
        }
    }

    human_grid_.advance_day(lambda_h_, rng_);
}

void TransmissionModel::record_daily_stats(
    int64_t day,
    const MosquitoSoA& soa,
    const BiteLedger& bite_ledger)
{
    TransmissionDailyStats stats;
    stats.day = day;

    const auto h_stats = human_grid_.compute_stats();
    stats.total_humans     = h_stats.total_population;
    stats.human_s          = h_stats.total_susceptible;
    stats.human_e          = h_stats.total_exposed;
    stats.human_i          = h_stats.total_infectious;
    stats.human_r          = h_stats.total_recovered;
    stats.human_incidence  = h_stats.total_incidence;
    stats.human_prevalence = h_stats.mean_prevalence;

    int64_t v_s = 0;
    int64_t v_e = 0;
    int64_t v_i = 0;
    int64_t v_tot = 0;

    for (int64_t k = 0; k < soa.n_alive; ++k) {
        const size_t si = static_cast<size_t>(k);
        if (soa.stage[si] != 1 || soa.sex[si] != 1) continue;  // adult females only
        ++v_tot;
        const auto st = static_cast<VectorTransmissionState>(soa.vector_state[si]);
        if (st == VectorTransmissionState::INFECTIOUS) {
            ++v_i;
        } else if (st == VectorTransmissionState::EXPOSED) {
            ++v_e;
        } else {
            ++v_s;
        }
    }

    stats.vector_s     = v_s;
    stats.vector_e     = v_e;
    stats.vector_i     = v_i;
    stats.vector_total = v_tot;

    int64_t human_meals = 0;
    int64_t inf_meals   = 0;
    for (const auto& agg : bite_ledger.today()) {
        if (agg.host == HostType::HUMAN) {
            human_meals += agg.successful_meals;
            inf_meals   += agg.infectious_meals;
        }
    }
    stats.total_bites_on_humans = human_meals;
    stats.infectious_bites      = inf_meals;

    // Approximate R_eff: daily new human infections per currently infectious human scaled by infectious duration
    if (stats.human_i > 0.0) {
        stats.r_eff_approx = (stats.human_incidence / stats.human_i) *
                             static_cast<double>(params_.human_infectious_days);
    } else {
        stats.r_eff_approx = 0.0;
    }

    last_day_stats_ = stats;
    history_.push_back(stats);
}

}  // namespace mal_abm_fast
