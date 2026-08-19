// SPDX-License-Identifier: MIT
// effective_host_landscape.hpp — Phase-aware effective host landscape (M7.8).
//
// H_eff(j, phase) = Σ_i P(i→j, phase) × H_residential(i), with a per-day
// multinomial flow realization on top (plan §3.3). This module is the single
// operator that samples realized host presence by phase. It reads residential
// populations + MobilitySchedule and produces per-phase effective grids.
//
// Contract (defined by supervisor, implemented by ag-mov):
//   * expected_effective_hosts(phase, is_livestock) — deterministic
//     Σ P(i→j)·H_res(i) (audit / reference).
//   * sample_effective_hosts(day, phase, is_livestock, rng) — multinomial
//     flow realization with named sub-stream rng(seed, day, phase, host_type).
#pragma once

#include <cstdint>
#include <vector>

#include "mobility_schedule.hpp"
#include "prng.hpp"
#include "species_params.hpp"

namespace mal_abm_fast {

/// Per-phase effective-host grids for one host type.
/// Row-major vector of length n_cells; index = row * w + col.
using EffectiveGrid = std::vector<float>;

class EffectiveHostLandscape {
public:
    EffectiveHostLandscape() = default;

    /// Wire up residential populations (length n_cells) for humans and
    /// livestock. Copies are owned internally.
    void configure(std::vector<float> residential_human,
                   std::vector<float> residential_livestock,
                   int32_t n_cells);

    /// Attach the mobility schedule (non-owning). The schedule must outlive
    /// this object; `select_od` is consulted for the phase matrix.
    void set_schedule(const MobilitySchedule* schedule) { schedule_ = schedule; }

    /// Deterministic expectation H_eff(j, phase) = Σ_i P(i→j)·H_res(i).
    /// Falls back to residential when no schedule or no OD is loaded.
    EffectiveGrid expected_effective_hosts(TimePhase phase,
                                           bool is_livestock) const;

    /// Multinomial flow realization for one (day, phase, host_type).
    /// Each origin i draws F_i→j ~ Multinomial(N_i, P(i→j)); H_eff(j) = Σ_i F_i→j.
    /// Sub-stream: rng seeded as splitmix64(day, phase, host_type) from base rng.
    /// Conserves mass exactly per origin (stochastic rounding for fractional N_i).
    EffectiveGrid sample_effective_hosts(int32_t day, TimePhase phase,
                                         bool is_livestock, Prng& rng) const;

    /// Aggregate sampled per-phase grids into a daily weighted reference
    /// H_expected_daily(j) = Σ_p w_species,p × E[H_eff(d,p)] (diagnostic only).
    EffectiveGrid weighted_daily_expectation(
        const std::array<float, PHASE_WEIGHT_COUNT>& weights) const;

    int32_t n_cells() const { return n_cells_; }
    bool has_schedule() const { return schedule_ != nullptr; }

private:
    const MobilitySchedule* schedule_ = nullptr;
    std::vector<float> residential_human_;
    std::vector<float> residential_livestock_;
    int32_t n_cells_ = 0;
};

}  // namespace mal_abm_fast
