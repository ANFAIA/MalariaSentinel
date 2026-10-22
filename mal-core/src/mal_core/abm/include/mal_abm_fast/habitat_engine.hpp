// SPDX-License-Identifier: MIT
// habitat_engine.hpp — candidate habitat patches reader (gpkg via OGR).
//
// Contract v3.0: a single-layer OGR Point datasource; the loader reads
//   * optional `hab_type`     (string; accepted without filtering)
//   * optional `habitat_potential` (float, [0,1]; default = full potential)
//   * optional `dynamics`     (int; 0 = persistent, 1 = pluvial)
//   * optional `row`, `col`   (int32; pre-computed cell index)
//   * the Point geometry      (lon, lat)
// Features below the habitat.candidate_min_engine floor are dropped.
#pragma once

#include <cstdint>
#include <functional>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>

#include "habitat_availability.hpp"
#include "wire.hpp"

namespace mal_abm_fast {

class HabitatEngine {
public:
    HabitatEngine() = default;

    // Read the candidate-patch gpkg from `path` and populate
    // `patches_`. Each row becomes a `HabitatPatch` (see wire.hpp).
    // Throws std::runtime_error if the OGR driver fails or the
    // layer is missing.
    void load_from_gpkg(const std::string& path, const AOI& aoi);

    // Patches loaded from the gpkg. May be empty if the gpkg was
    // absent (the union then comes from the static env planes).
    const std::vector<HabitatPatch>& patches() const { return patches_; }

    // O(1) lookup by patch_id (the gpkg's sequential index, 0-based).
    // Throws std::out_of_range if the id is not present.
    const HabitatPatch& patch_by_id(int64_t pid) const;

private:
    std::vector<HabitatPatch>                            patches_;
    std::unordered_map<int64_t, int64_t>                 id_to_idx_;
};

}  // namespace mal_abm_fast
