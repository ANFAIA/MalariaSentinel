// SPDX-License-Identifier: MIT
// aquatic_stages.hpp — Enum definitions for mosquito aquatic development
// stages and adult sex.
//
// These enums decouple mosquito biology from the old conflated
// `eip_progress` field:
//   - AquaticStage: tracks egg -> larva -> pupa maturation (replaces the
//     overloading of eip_progress for larval development).
//   - AdultSex: MALE / FEMALE. Only females take blood meals and seek
//     hosts; this field is essential for M7.2 host-seeking logic.
#pragma once

#include <cstdint>

namespace mal_abm_fast {

/// Aquatic development stage for immature mosquitoes (stage == 0).
/// Values are stored as uint8_t in MosquitoSoA::aquatic_stage.
enum class AquaticStage : uint8_t {
    EGG   = 0,
    LARVA = 1,
    PUPA  = 2,
};

/// Adult sex. Only females (FEMALE) take blood meals and seek hosts.
/// Values are stored as uint8_t in MosquitoSoA::sex.
enum class AdultSex : uint8_t {
    MALE   = 0,
    FEMALE = 1,
};

}  // namespace mal_abm_fast
