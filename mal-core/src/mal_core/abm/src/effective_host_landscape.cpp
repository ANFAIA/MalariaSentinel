// SPDX-License-Identifier: MIT
// effective_host_landscape.cpp — Phase-aware effective host landscape (M7.8).
// Implementation by ag-mov: multinomial flow sampling + deterministic
// expectation using MobilitySchedule::get_presence / select_od.
#include "mal_abm_fast/effective_host_landscape.hpp"

#include <array>
#include <cmath>

namespace mal_abm_fast {

void EffectiveHostLandscape::configure(std::vector<float> residential_human,
                                       std::vector<float> residential_livestock,
                                       int32_t n_cells) {
    residential_human_ = std::move(residential_human);
    residential_livestock_ = std::move(residential_livestock);
    n_cells_ = n_cells;
}

EffectiveGrid EffectiveHostLandscape::expected_effective_hosts(
    TimePhase phase, bool is_livestock) const {
    EffectiveGrid out(n_cells_, 0.0f);
    if (!schedule_ || n_cells_ == 0) return out;
    const auto& res = is_livestock ? residential_livestock_ : residential_human_;
    for (int32_t i = 0; i < n_cells_; ++i) {
        for (const auto& [j, p] : schedule_->get_presence(i, phase, is_livestock)) {
            if (j >= 0 && j < n_cells_) out[j] += p * res[static_cast<size_t>(i)];
        }
    }
    return out;
}

EffectiveGrid EffectiveHostLandscape::sample_effective_hosts(
    int32_t day, TimePhase phase, bool is_livestock, Prng& rng) const {
    EffectiveGrid out(n_cells_, 0.0f);
    if (n_cells_ == 0) return out;

    const auto& res = is_livestock ? residential_livestock_ : residential_human_;

    // Build a named sub-stream from the base rng so the base stays reusable
    // across phases/days: seed = splitmix64(base_seed ^ day ^ phase ^ host_type).
    uint64_t base_seed = rng.peek_state()[0];
    uint64_t mix = base_seed ^ (static_cast<uint64_t>(day) * 131ULL) ^
                   (static_cast<uint64_t>(static_cast<uint8_t>(phase)) * 7ULL) ^
                   (is_livestock ? 1ULL : 0ULL);
    uint64_t sub_seed = splitmix64(mix);
    Prng local(sub_seed);

    // Identity fallback: when no schedule or no OD row exists, everyone stays
    // in their residential cell (H_eff == H_res).
    const bool schedule_absent = (schedule_ == nullptr);
    const bool host_missing = schedule_absent ? false
        : (is_livestock ? !schedule_->has_livestock() : !schedule_->has_human());

    for (int32_t i = 0; i < n_cells_; ++i) {
        const float N_i = res[static_cast<size_t>(i)];
        if (N_i <= 0.0f) continue;

        const bool fallback = schedule_absent || host_missing ||
                              (schedule_->n_cells() == 0);
        if (fallback) {
            out[static_cast<size_t>(i)] += N_i;
            continue;
        }

        auto dests = schedule_->get_presence(i, phase, is_livestock);
        if (dests.empty()) {
            out[static_cast<size_t>(i)] += N_i;
            continue;
        }

        // Stochastic rounding of the fractional stock to an integer count:
        //  int = floor(N_i) + Bernoulli(frac), so E[int] == N_i.
        const float frac = N_i - std::floor(N_i);
        int64_t stock = static_cast<int64_t>(std::floor(N_i));
        if (frac > 0.0f && local.uniform_double() < frac) ++stock;
        if (stock <= 0) continue;

        if (dests.size() == 1) {
            const int32_t j = dests[0].first;
            if (j >= 0 && j < n_cells_) {
                out[static_cast<size_t>(j)] += static_cast<float>(stock);
            }
            continue;
        }

        // Sequential multinomial draw over destinations, conserving stock
        // exactly by assigning the remainder to the last destination.
        double prob_remaining = 0.0;
        for (const auto& [j, p] : dests) prob_remaining += p;

        int64_t remaining = stock;
        const size_t nd = dests.size();
        for (size_t k = 0; k < nd && remaining > 0; ++k) {
            const int32_t j = dests[k].first;
            double p = dests[k].second;
            int64_t flow;
            if (k + 1 == nd || prob_remaining <= 0.0) {
                flow = remaining;  // last destination absorbs the remainder
            } else {
                double p_cond = p / prob_remaining;
                if (p_cond > 1.0) p_cond = 1.0;
                if (p_cond < 0.0) p_cond = 0.0;
                flow = local.binomial(static_cast<int>(remaining), p_cond);
                if (flow > remaining) flow = remaining;
            }
            if (j >= 0 && j < n_cells_) {
                out[static_cast<size_t>(j)] += static_cast<float>(flow);
            }
            remaining -= flow;
            prob_remaining -= p;
        }
    }
    return out;
}

EffectiveGrid EffectiveHostLandscape::weighted_daily_expectation(
    const std::array<float, PHASE_WEIGHT_COUNT>& weights) const {
    EffectiveGrid out(n_cells_, 0.0f);
    // Daily species-level aggregate for the primary (human) host:
    // H_expected_daily(j) = Σ_p w_p × E[H_eff(d,p)] over [DAY, EVENING, NIGHT, DAWN].
    for (int p = 0; p < PHASE_WEIGHT_COUNT; ++p) {
        const float w = weights[static_cast<size_t>(p)];
        if (w == 0.0f) continue;
        const auto phase_grid =
            expected_effective_hosts(static_cast<TimePhase>(p), /*is_livestock=*/false);
        for (int32_t j = 0; j < n_cells_; ++j) {
            out[static_cast<size_t>(j)] += w * phase_grid[static_cast<size_t>(j)];
        }
    }
    return out;
}

}  // namespace mal_abm_fast
