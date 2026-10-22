// SPDX-License-Identifier: MIT
// eip.hpp — extrinsic incubation period (growing-degree-day) tracker.
//
// Pure functions; both implemented inline in the header. The math
// subagent (F1.c) keeps them as-is — the formulas are pinned by
// `tests/test_smoke.cpp::EipAccumulate` (F1.a).
//
//   daily_gd       = max(0, T - EIP_BASE_C())            (deg C above base_c)
//   eip_progress'  = eip_progress + daily_gd           (NaN-safe)
//   infective iff  = eip_progress >= EIP_THRESHOLD_GD() (threshold_gd)
//
// The NaN check is essential: when the env COG has a no-data pixel
// (e.g. ocean / non-land), rasterio returns the NoData sentinel.
// After the thermal inverse that becomes a NaN, and the growth step
// must not corrupt the eip_progress.
#pragma once

#include <algorithm>
#include <cmath>

#include "wire.hpp"

namespace mal_abm_fast {

// Accumulate one day's GDD onto eip_progress. NaN-safe (returns the
// current progress unchanged when the daily mean temperature is NaN).
inline float accumulate_eip(float eip_progress, float daily_mean_temp_c) {
    if (std::isnan(daily_mean_temp_c)) return eip_progress;
    const float gd = std::max(0.0f, daily_mean_temp_c - static_cast<float>(load_config().eip.base_c));
    return eip_progress + gd;
}

// True when the agent has accumulated enough GDD to be infective.
inline bool is_infective(float eip_progress) {
    return eip_progress >= static_cast<float>(load_config().eip.threshold_gd);
}

}  // namespace mal_abm_fast
