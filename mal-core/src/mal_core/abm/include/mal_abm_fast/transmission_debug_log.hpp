// SPDX-License-Identifier: MIT
// transmission_debug_log.hpp — versioned per-day transmission debug JSONL.
#pragma once

#include <chrono>
#include <cstdint>
#include <fstream>
#include <string>

#include "bite_ledger.hpp"
#include "transmission.hpp"

namespace mal_abm_fast {

struct TransmissionDebugRunMetadata {
    std::string aoi;
    int32_t year = 0;
    int32_t month = 0;
    int32_t seed = 0;
    int32_t n_rollouts = 1;
    int32_t rollout_index = 0;
    int32_t days = 0;
    double human_cluster_radius_km = 0.0;
};

/// Writes one metadata record followed by one record per simulated day.
/// All write failures are reported as warnings and never propagated to the run.
class TransmissionDebugLog {
public:
    TransmissionDebugLog(const std::string& path,
                         const TransmissionDebugRunMetadata& run,
                         const TransmissionParams& params) noexcept;
    ~TransmissionDebugLog();

    TransmissionDebugLog(const TransmissionDebugLog&) = delete;
    TransmissionDebugLog& operator=(const TransmissionDebugLog&) = delete;

    void record_day(int32_t day_index,
                    std::chrono::sys_days date,
                    const TransmissionDailyStats& stats,
                    const BiteLedger& bite_ledger) noexcept;

private:
    void warn(const std::string& message) noexcept;
    void write_record(const std::string& record) noexcept;

    std::string path_;
    std::ofstream stream_;
    bool usable_ = false;
};

}  // namespace mal_abm_fast
