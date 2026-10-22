// SPDX-License-Identifier: MIT
// aquatic_stress.hpp — aquatic stress factors, contract v3.0.
//
// Preserved stressors driven by the new habitat state:
//   desiccation_rate(int days_dry)  — grace period + exponential ramp on
//       the consecutive days the cell was habitat-dry (consecutive days
//       with accuracy S <= kActivationMin; carried in
//       PatchState.habitat_dry_days). PoolState days_dry was the old
//       driver (dry mm days count); replaced one-to-one by the
//       habitat-dry streak (the aquatic module contract changes only in
//       the driver, not in the stressor semantics).
//   washout_fraction(float rain_d)  — flush fraction on heavy rain;
//       linear ramp preserved from the pool module.
//   aquatic_survival_factor(float temp_d) — thermal gate on aquatic
//       survival, unchanged.
//
// Removed with the pool model: everything else pool_hydrology.hpp carried
// (PoolState, the mm balance, POOL_* constants, urban baseline override).
#pragma once

#include <algorithm>
#include <cmath>

namespace mal_abm_fast {

// -- constants (all preserved from the M14 pool module) -----------------------

/// Aquatic desiccation grace period (days) — first dry days are free.
/// Days beyond this ramp the kill rate up to the base fraction via the
/// exponential ramp (see desiccation_rate).
constexpr float AQUATIC_DESICCATION_GRACE_DAYS = 5.0f;

/// The base kill fraction of the ramp (reached over ~5 days past grace).
constexpr float AQUATIC_DESICC_BASE_DAILY = 0.10f;

/// Heavy-rain washout threshold (mm). Linear ramp from 0 at this
/// threshold to AQUATIC_WASHOUT_FRACTION_MAX at twice the threshold.
constexpr float AQUATIC_RAIN_WASH_MM = 40.0f;

/// Washout fraction at or above twice the heavy-rain threshold.
constexpr float AQUATIC_WASHOUT_FRACTION_MAX = 0.60f;

inline float desiccation_rate(int days_dry) {
    if (days_dry <= static_cast<int>(AQUATIC_DESICCATION_GRACE_DAYS)) {
        return 0.0f;
    }
    const float past_grace = static_cast<float>(days_dry) -
        AQUATIC_DESICCATION_GRACE_DAYS;
    const float ramp = 1.0f - std::exp(-0.3f * past_grace);
    return AQUATIC_DESICC_BASE_DAILY * ramp;
}

inline float washout_fraction(float rain_d) {
    if (rain_d < AQUATIC_RAIN_WASH_MM) return 0.0f;
    const float excess = (rain_d - AQUATIC_RAIN_WASH_MM) / AQUATIC_RAIN_WASH_MM;
    return std::min(AQUATIC_WASHOUT_FRACTION_MAX,
                    excess * AQUATIC_WASHOUT_FRACTION_MAX);
}

}  // namespace mal_abm_fast
