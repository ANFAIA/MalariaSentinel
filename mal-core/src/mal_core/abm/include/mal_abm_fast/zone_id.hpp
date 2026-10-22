// SPDX-License-Identifier: MIT
// zone_id.hpp — habitat ZoneId enum (extracted from habitat_availability.hpp
// so config.hpp can reference it without an include cycle).
#pragma once

#include <cstddef>

namespace mal_abm_fast {

/// Six static habitat types (g). The order is a FROZEN contract for the
/// py index API (habitat_types.types); C++ loads weights BY NAME — this
/// enum is internal only.
enum class ZoneId : std::size_t {
    JRC_PERSISTENT = 0,   // JRC GSW persistent surface water fraction
    URBAN_PERSISTENT,     // built-surface persistent supply (human)
    WETLAND,              // wetland + mangrove (persistent; loaded by name)
    OPEN_PLUVIAL,         // open/low-veg + bare + water (+ rain pools)
    CROP,                 // cropland (irrigation/backyard agriculture)
    FOREST,               // forest fraction (currently unused; 0 throughout)
};
constexpr size_t kNumZoneId = 6;

}  // namespace mal_abm_fast
