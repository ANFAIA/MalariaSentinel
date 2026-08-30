// SPDX-License-Identifier: MIT
// pool_hydrology.hpp — Per-patch water-balance model (M14).
//
// Replaces the binary rain-threshold activation with a continuous
// water-balance model:
//   W[t+1] = max(0, W[t] + rain[t] - evap(T[t]))
//
// State transitions:
//   W >= POOL_WATER_BREED_MM  → patch active for breeding
//   W <  POOL_WATER_DRY_MM   → patch dry, larval desiccation begins
//   rain >= POOL_RAIN_WASH_MM → washout event
//
// Larval mortality gains two new drivers:
//   desiccation(W, days_dry) — eggs + L1-L2 mortality when dry
//   washout(rain)            — fraction of cohorts flushed by heavy rain
#pragma once

#include <algorithm>
#include <cmath>
#include <cstdint>

#include "wire.hpp"

namespace mal_abm_fast {

// ---------------------------------------------------------------------------
// PoolState — per-patch daily water state
// ---------------------------------------------------------------------------
struct PoolState {
    float water_mm        = 0.0f;   // current water depth (mm)
    int   days_dry        = 0;      // consecutive days with water < DRY
    int   days_since_fill = 0;      // consecutive days since last rain > REFILL
};

// ---------------------------------------------------------------------------
// DailyForcing — daily climate inputs for one patch
// ---------------------------------------------------------------------------
struct DailyForcing {
    float rain_mm = 0.0f;           // today's daily rainfall (mm, ERA5)
    float temp_c  = 25.0f;          // today's mean air temp (°C, ERA5)
    // Catchment runoff factor (M7.4.1 fondo-fix): a pool does not fill
    // only from the rain falling on its own footprint — it collects the
    // runoff of its catchment. Bomblies 2008 (HYDREMATS, Niger) models
    // pond volume as rain x catchment_area x runoff coefficient, with
    // catchment:pond ratios of 10-50x. Urban cells: impervious cover
    // (40-80%) concentrates drainage into depressions/ditches, so the
    // factor is high; rural soils infiltrate most of the storm, so the
    // factor is small. 1.0 = direct rainfall only (old behaviour).
    float catchment_factor = 1.0f;
    // Evaporation scale: shaded, organic-lined urban pools (drainage
    // ditches, tyre ruts, construction pits) lose water more slowly
    // than an open sun-exposed rural puddle.
    float evap_scale = 1.0f;
};

// ---------------------------------------------------------------------------
// advance_pool — evolve water balance for one day
//
// Returns the new PoolState. Pure function, no side effects.
// ---------------------------------------------------------------------------
inline PoolState advance_pool(const PoolState& prev, const DailyForcing& f) {
    PoolState next;

    // 1. Evaporation — simplified Penman-Monteith, daily (mm/day).
    //    Reference: 5 mm/day at 30°C (FAO Penman-Monteith climatology
    //    for West Africa; Ward 2015). Temperature coefficient 0.07/°C
    //    gives ~3.5 mm/day at 20°C, ~6.5 mm/day at 35°C.
    float evap = POOL_EVAP_REF_MM *
        (1.0f + POOL_EVAP_T_COEFF * (f.temp_c - POOL_EVAP_REF_T));
    if (evap < 0.5f) evap = 0.5f;  // floor: even cold dry days lose some water
    evap *= f.evap_scale;

    // 2. Water update — rainfall amplified by the catchment runoff
    //    factor (see DailyForcing note).
    const float rain_in = f.rain_mm * f.catchment_factor;
    float w = prev.water_mm + rain_in - evap;
    if (w < 0.0f) w = 0.0f;
    if (w > POOL_WATER_MAX_MM) w = POOL_WATER_MAX_MM;
    next.water_mm = w;

    // 3. Dry-day counter.
    next.days_dry = (w < POOL_WATER_DRY_MM)
        ? prev.days_dry + 1
        : 0;

    // 4. Days since last significant rain (> REFILL threshold).
    next.days_since_fill = (f.rain_mm > PLUVIAL_POOL_RAIN_THRESHOLD_MM)
        ? 0
        : prev.days_since_fill + 1;

    return next;
}

// ---------------------------------------------------------------------------
// desiccation_rate — larval mortality rate when pool is dry
//
// Only eggs and early instars (L1, L2) are vulnerable (Depinay 2004 §3.1).
// Grace period: first POOL_DESICCATION_GRACE_DAYS dry days → no mortality.
// After grace: rate ramps exponentially over ~5 days to POOL_DESICC_BASE_DAILY.
// ---------------------------------------------------------------------------
inline float desiccation_rate(const PoolState& pool) {
    if (pool.water_mm >= POOL_WATER_DRY_MM) return 0.0f;
    if (pool.days_dry <= static_cast<int>(POOL_DESICCATION_GRACE_DAYS)) return 0.0f;
    // Exponential ramp: approaches BASE over ~5 days past grace.
    const int past_grace = pool.days_dry -
        static_cast<int>(POOL_DESICCATION_GRACE_DAYS);
    const float ramp = 1.0f - std::exp(-0.3f * static_cast<float>(past_grace));
    return POOL_DESICC_BASE_DAILY * ramp;
}

// ---------------------------------------------------------------------------
// washout_fraction — fraction of aquatic cohorts flushed by heavy rain
//
// Linear from 0 at POOL_RAIN_WASH_MM to POOL_WASH_FRACTION_MAX at
// 2 * POOL_RAIN_WASH_MM, capped.
// ---------------------------------------------------------------------------
inline float washout_fraction(float rain_mm) {
    if (rain_mm < POOL_RAIN_WASH_MM) return 0.0f;
    const float excess = (rain_mm - POOL_RAIN_WASH_MM) / POOL_RAIN_WASH_MM;
    return std::min(POOL_WASH_FRACTION_MAX, excess * POOL_WASH_FRACTION_MAX);
}

}  // namespace mal_abm_fast
