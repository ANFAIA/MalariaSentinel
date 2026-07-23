// SPDX-License-Identifier: MIT
// bite_ledger.hpp — Aggregate feeding events per cell per day.
//
// The BiteLedger records host-seeking attempts, successful blood
// meals, and mosquito deaths per cell per host type per day. It is
// reset at the start of each day and queried by the coordinator
// for output.
#pragma once

#include <cstdint>
#include <vector>

#include "gonotrophic_cycle.hpp"

namespace mal_abm_fast {

/// Per-cell per-host-type aggregate for one day.
struct BiteEventAggregate {
    int32_t row            = 0;
    int32_t col            = 0;
    HostType host          = HostType::HUMAN;
    int64_t attempts       = 0;
    int64_t successful_meals = 0;
    int64_t mosquito_deaths = 0;  // from ITN/IRS (future) or feeding failure
};

/// Aggregate feeding events per cell per host type per day.
///
/// The submodel calls record_attempt / record_success / record_death
/// during the nightly host-seeking loop. The coordinator reads
/// today() after advance_day() for output and ITN/IRS logic.
class BiteLedger {
public:
    BiteLedger() = default;

    /// Record a feeding attempt at (row, col) for the given host type.
    void record_attempt(int32_t row, int32_t col, HostType host) {
        auto& agg = find_or_create(row, col, host);
        agg.attempts++;
    }

    /// Record a successful blood meal at (row, col).
    void record_success(int32_t row, int32_t col, HostType host) {
        auto& agg = find_or_create(row, col, host);
        agg.successful_meals++;
    }

    /// Record a mosquito death during feeding (future: ITN/IRS).
    void record_death(int32_t row, int32_t col, HostType host) {
        auto& agg = find_or_create(row, col, host);
        agg.mosquito_deaths++;
    }

    /// Reset all aggregates for the next day.
    void reset_day() {
        today_.clear();
    }

    /// Read-only access to today's aggregates.
    const std::vector<BiteEventAggregate>& today() const { return today_; }

    /// Total successful meals across all cells and host types today.
    int64_t total_successful_meals() const {
        int64_t sum = 0;
        for (const auto& agg : today_) {
            sum += agg.successful_meals;
        }
        return sum;
    }

    /// Total attempts across all cells and host types today.
    int64_t total_attempts() const {
        int64_t sum = 0;
        for (const auto& agg : today_) {
            sum += agg.attempts;
        }
        return sum;
    }

private:
    std::vector<BiteEventAggregate> today_;

    /// Find existing aggregate for (row, col, host) or create a new one.
    BiteEventAggregate& find_or_create(int32_t row, int32_t col, HostType host) {
        for (auto& agg : today_) {
            if (agg.row == row && agg.col == col && agg.host == host) {
                return agg;
            }
        }
        today_.push_back({row, col, host, 0, 0, 0});
        return today_.back();
    }
};

}  // namespace mal_abm_fast
