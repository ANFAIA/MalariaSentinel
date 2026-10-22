// SPDX-License-Identifier: MIT
// multirate_scheduler.hpp — Daily outer step with hourly nighttime sub-steps.
//
// The ABM engine advances in daily steps. Host-seeking activity in
// An. gambiae is concentrated during nighttime hours (18:00–06:00).
// The multirate scheduler runs 12 hourly sub-steps during nighttime
// for host-seeking/feeding logic, while all other processes (aquatic
// development, adult mortality, dispersal) run once per day.
//
// Key design: we do NOT run all 24 hourly steps. Only the 12
// nighttime hours (18:00–06:00) execute the host-seeking loop.
// This is a biological optimization, not just a performance one.
#pragma once

#include <cstdint>

#include "config.hpp"

namespace mal_abm_fast {

/// Hour of day in [0, 24). Used by the multirate scheduler.
using HourOfDay = int32_t;

/// Check whether a given hour falls within the active nighttime
/// window for host-seeking An. gambiae. The window lives in
/// model_constants.yaml (dispersal.night_start_hour/night_end_hour);
/// a window whose end is <= start crosses midnight.
inline bool is_nighttime_hour(HourOfDay hour) {
    const DispersalCfg& cfg = load_config().dispersal;
    if (cfg.night_start_hour <= cfg.night_end_hour) {
        return hour >= cfg.night_start_hour && hour < cfg.night_end_hour;
    }
    return hour >= cfg.night_start_hour || hour < cfg.night_end_hour;
}

/// Return the first active hour of the day (inclusive).
inline HourOfDay nighttime_start() {
    return load_config().dispersal.night_start_hour;
}

/// Return the number of active nighttime hours per day (derived).
inline int32_t nighttime_hours_count() {
    const DispersalCfg& cfg = load_config().dispersal;
    return (cfg.night_end_hour - cfg.night_start_hour + 24) % 24;
}

/// Get the hour-of-day from a global hour count.
/// hour_of_day = global_hour % 24.
inline HourOfDay hour_of_day(int64_t global_hour) {
    return static_cast<HourOfDay>(global_hour % 24);
}

/// The multirate scheduler state for one simulation day.
/// Tracks which nighttime sub-step we are on and which hours
/// have been processed.
struct MultirateDayState {
    int32_t night_hour_index = 0;  // 0–11: which of the 12 night hours

    /// Advance to the next nighttime hour. Returns true if more
    /// hours remain, false if the night is complete.
    bool advance_night_hour() {
        night_hour_index++;
        return night_hour_index < nighttime_hours_count();
    }

    /// Reset for a new day.
    void reset_day() { night_hour_index = 0; }
};

}  // namespace mal_abm_fast
