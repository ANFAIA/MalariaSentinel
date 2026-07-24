// SPDX-License-Identifier: MIT
// habitat_engine.hpp — habitat patches reader (gpkg via OGR).
//
// The habitat patches gpkg is a single-layer OGR datasource with one
// Point feature per patch. The M1.5 thin slice honours
// `hab_type == 'pluvial_pool'` only. The columns the engine reads:
//
//   * a `hab_type` (string) field — filter to 'pluvial_pool'
//   * optional `K` (int32) field — carrying capacity (default = K_MAX)
//   * optional `twi` (float) field — static TWI value for the patch
//   * optional `row`, `col` (int32) fields — pre-computed cell index
//     (F1.3b `build_env` writes them); if absent, derived via
//     `rasterio::rowcol` on the AOI transform
//   * the Point geometry — provides (lon, lat) in EPSG:4326
//
// The IO subagent (F1.b) implements the actual OGR calls.
#pragma once

#include <cstdint>
#include <functional>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>

#include "wire.hpp"

namespace mal_abm_fast {

class HabitatEngine {
public:
    HabitatEngine() = default;

    // Read the habitat patches gpkg from `path` and populate
    // `patches_`. Each row becomes a `HabitatPatch` (see wire.hpp).
    // Throws std::runtime_error if the OGR driver fails or the
    // layer is missing.
    void load_from_gpkg(const std::string& path, const AOI& aoi);

    // Patches loaded from the gpkg. May be empty if the gpkg
    // contained zero 'pluvial_pool' features.
    const std::vector<HabitatPatch>& patches() const { return patches_; }

    // O(1) lookup by patch_id (the gpkg's sequential index, 0-based).
    // Throws std::out_of_range if the id is not present.
    const HabitatPatch& patch_by_id(int64_t pid) const;

    // The TWI grid is shared between climate and habitat engines —
    // the climate reads it from the env COG (optional 5th band) and
    // the habitat engine may load it from a gpkg field. Either side
    // can set a provider; `get_twi_grid` calls whichever is set.
    void set_twi_grid_provider(std::function<std::vector<float>(const AOI&)> fn) {
        twi_provider_ = std::move(fn);
    }
    std::vector<float> get_twi_grid(const AOI& aoi) const;

private:
    std::vector<HabitatPatch>                            patches_;
    std::unordered_map<int64_t, int64_t>                 id_to_idx_;
    std::function<std::vector<float>(const AOI&)>        twi_provider_;
};

}  // namespace mal_abm_fast
