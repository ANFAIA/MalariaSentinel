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

namespace mal_abm_fast {

/// Hour of day in [0, 24). Used by the multirate scheduler.
using HourOfDay = int32_t;

/// Check whether a given hour falls within the active nighttime
/// window for host-seeking An. gambiae.
///
/// Active window: 18:00–05:59 (12 hours total).
/// Hours 0–5 (midnight–dawn) and 18–23 (dusk–midnight) are active.
inline bool is_nighttime_hour(HourOfDay hour) {
    return hour >= 18 || hour < 6;
}

/// Return the first active hour of the day (inclusive).
inline constexpr HourOfDay nighttime_start() { return 18; }

/// Return the number of active nighttime hours per day.
inline constexpr int32_t nighttime_hours_count() { return 12; }

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
