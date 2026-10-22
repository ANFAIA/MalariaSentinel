// SPDX-License-Identifier: MIT
// aquatic_stress.hpp — aquatic stress factors, contract v3.0.
//
// Preserved stressors driven by the new habitat state:
//   desiccation_rate(int days_dry)  — grace period + exponential ramp on
//       the consecutive days the cell was habitat-dry (consecutive days
//       with accuracy S <= habitat.activation_min_engine; carried in
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

#include "mal_abm_fast/config.hpp"

namespace mal_abm_fast {

// Values live in model_constants.yaml (aquatic_stress section); these
// wrappers read the load_config() singleton (plan constants-yaml §4).

inline float desiccation_rate(const int days_dry) {
    const auto& aq = load_config().aquatic_stress;
    const float grace = static_cast<float>(aq.desicc_grace_days);
    if (static_cast<float>(days_dry) <= grace) return 0.0f;
    const float past_grace = static_cast<float>(days_dry) - grace;
    const float ramp = 1.0f - std::exp(
        -static_cast<float>(aq.desicc_ramp_decay) * past_grace);
    return static_cast<float>(aq.desicc_base_daily) * ramp;
}

inline float washout_fraction(const float rain_d) {
    const auto& aq = load_config().aquatic_stress;
    const float wash_mm = static_cast<float>(aq.wash_threshold_mm);
    const float frac_max = static_cast<float>(aq.wash_fraction_max);
    if (rain_d < wash_mm) return 0.0f;
    const float excess = (rain_d - wash_mm) / wash_mm;
    return std::min(frac_max, excess * frac_max);
}

}  // namespace mal_abm_fast
