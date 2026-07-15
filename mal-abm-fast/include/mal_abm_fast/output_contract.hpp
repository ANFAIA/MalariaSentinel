// SPDX-License-Identifier: MIT
// output_contract.hpp — COG + sidecar writer per arch-abm-output-contract@v1.0
// (stub; F1.d implements the full writer)
#pragma once

#include <array>
#include <cstdint>
#include <string>

namespace mal_abm_fast {

// Minimal sidecar metadata that the writer must produce. Mirrors the 9 required
// keys in docs/abm-output-contract.md §3.
struct StateSidecar {
    std::string crs;                 // EPSG code or WKT
    std::array<double, 6> transform; // affine 6-tuple
    std::string aoi_slug;
    std::string scale;               // "regional" / "national" / "continental"
    int year = 0;
    int month = 0;
    int seed = 0;
    std::string generator_version;   // "m-perf-0.1.0"
    std::string abm_params_hash;     // "sha256:..."
};

// Write a 2-band state COG (density + suitability) and sidecar (stub in F1.a).
// Returns the path written. Stub: creates an empty file and returns the path.
std::string write_state_cog(
    const std::string& path,
    const float* density,            // (H, W) row-major
    const float* suitability,        // (H, W) row-major
    int H, int W,
    const StateSidecar& sidecar
);

}  // namespace mal_abm_fast
