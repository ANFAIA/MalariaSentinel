// SPDX-License-Identifier: MIT
// species.hpp — Mosquito species identity (M7.8).
//
// Stable enum + name mapping. The enum is the SoA-level species identity;
// all quantitative behaviour lives in SpeciesParams (species_params.hpp).
#pragma once

#include <cstdint>

namespace mal_abm_fast {

enum class MosquitoSpeciesId : uint8_t {
    ANOPHELES_COLUZZII   = 0,
    ANOPHELES_GAMBIAE_SS = 1,
    ANOPHELES_FUNESTUS_SS = 2,
    ANOPHELES_ARABIENSIS = 3,
    ANOPHELES_MELAS      = 4,
    ANOPHELES_STEPHENSI  = 5,
};

inline constexpr int MOSQUITO_SPECIES_COUNT = 6;

/// Canonical scientific name for a species id.
inline const char* species_name(MosquitoSpeciesId id) {
    switch (id) {
        case MosquitoSpeciesId::ANOPHELES_COLUZZII:   return "Anopheles coluzzii";
        case MosquitoSpeciesId::ANOPHELES_GAMBIAE_SS: return "Anopheles gambiae s.s.";
        case MosquitoSpeciesId::ANOPHELES_FUNESTUS_SS: return "Anopheles funestus s.s.";
        case MosquitoSpeciesId::ANOPHELES_ARABIENSIS: return "Anopheles arabiensis";
        case MosquitoSpeciesId::ANOPHELES_MELAS:      return "Anopheles melas";
        case MosquitoSpeciesId::ANOPHELES_STEPHENSI:  return "Anopheles stephensi";
    }
    return "unknown";
}

}  // namespace mal_abm_fast
