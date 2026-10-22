// SPDX-License-Identifier: MIT
// thermal_responses.hpp — Stage-specific thermal development rates for
// mosquito aquatic stages (Egg, Larva, Pupa).
//
// Each function returns the daily development rate as a fraction [0, 1].
// A rate of 1.0 means the stage completes in exactly one day at that
// temperature. Rates above 0 indicate temperatures that support
// development; rates below the lower threshold are clamped to 0.
//
// Thermal response curves: Brière-1 (eggs, pupae) and quadratic
// (larvae). All parameters (T_L, T_H, a) live in model_constants.yaml
// under `thermal:`; this header only implements the formulas.
#pragma once

#include <algorithm>
#include <cmath>

#include "config.hpp"

namespace mal_abm_fast {

// ---------------------------------------------------------------------------
// Egg development — Brière-1 thermal response
//   rate(T) = a * T * (T - T_L) * sqrt(T_H - T)  if T_L < T < T_H
//   rate(T) = 0                                    otherwise
// ---------------------------------------------------------------------------
inline float egg_development_rate(float temp_c) {
    static const ThermalCfg& cfg = load_config().thermal;
    const double T = static_cast<double>(temp_c);
    const double tl = cfg.egg_development_tmin_c;
    const double th = cfg.egg_development_tmax_c;
    if (T <= tl || T >= th) return 0.0f;
    const double rate = cfg.egg_development_scale * T * (T - tl) * std::sqrt(th - T);
    return static_cast<float>(std::max(0.0, std::min(rate, 1.0)));
}

// ---------------------------------------------------------------------------
// Larva development — quadratic thermal response
//   rate(T) = a * (T - T_L) * (T_H - T)  if T_L < T < T_H
//   rate(T) = 0                           otherwise
// ---------------------------------------------------------------------------
inline float larva_development_rate(float temp_c) {
    static const ThermalCfg& cfg = load_config().thermal;
    const double T = static_cast<double>(temp_c);
    const double tl = cfg.larva_development_tmin_c;
    const double th = cfg.larva_development_tmax_c;
    if (T <= tl || T >= th) return 0.0f;
    const double rate = cfg.larva_development_scale * (T - tl) * (th - T);
    return static_cast<float>(std::max(0.0, std::min(rate, 1.0)));
}

// ---------------------------------------------------------------------------
// Pupa development — Brière-1 thermal response
//   rate(T) = a * T * (T - T_L) * sqrt(T_H - T)  if T_L < T < T_H
//   rate(T) = 0                                    otherwise
//
// The pupal lower threshold is higher than the egg one (pupae are more
// sensitive to cold).
// ---------------------------------------------------------------------------
inline float pupa_development_rate(float temp_c) {
    static const ThermalCfg& cfg = load_config().thermal;
    const double T = static_cast<double>(temp_c);
    const double tl = cfg.pupa_development_tmin_c;
    const double th = cfg.pupa_development_tmax_c;
    if (T <= tl || T >= th) return 0.0f;
    const double rate = cfg.pupa_development_scale * T * (T - tl) * std::sqrt(th - T);
    return static_cast<float>(std::max(0.0, std::min(rate, 1.0)));
}

// ---------------------------------------------------------------------------
// Gonotrophic development rate — placeholder for M7.2 (test-only today; no
// production caller). The GONO_* constants are compiled fixtures that mirror
// the thermal thresholds; they are NOT read from model_constants.yaml.
// Migration to gonotrophic.* is a task-07 backlog item, not a comment fix.
// ---------------------------------------------------------------------------
inline constexpr double GONO_TL   = 16.0;
inline constexpr double GONO_TH   = 38.0;
inline constexpr double GONO_TOPT = 25.0;

inline float gonotrophic_development_rate(float temp_c) {
    const double T = static_cast<double>(temp_c);
    if (T <= GONO_TL || T >= GONO_TH) return 0.0f;
    // Normalised quadratic: peaks at 1.0 at Topt
    const double rate = (T - GONO_TL) * (GONO_TH - T) /
                        ((GONO_TOPT - GONO_TL) * (GONO_TH - GONO_TOPT));
    return static_cast<float>(std::max(0.0, std::min(rate * 0.25, 1.0)));
}

}  // namespace mal_abm_fast
