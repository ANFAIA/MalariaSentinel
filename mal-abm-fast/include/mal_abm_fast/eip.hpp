// SPDX-License-Identifier: MIT
// eip.hpp — extrinsic incubation period (growing-degree-day) tracker (stub)
#pragma once

namespace mal_abm_fast {

// Constants from the M1.5 thin slice.
constexpr double EIP_BASE_C       = 16.0;   // base temperature (C)
constexpr double EIP_THRESHOLD_GD = 110.0;  // infective threshold (growing-degree-days)

// Accumulate one day's GDD onto ``eip_progress``. NaN-safe.
double accumulate_eip(double eip_progress, double daily_mean_temp_c);

}  // namespace mal_abm_fast
