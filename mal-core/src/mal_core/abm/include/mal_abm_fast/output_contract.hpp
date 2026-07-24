// SPDX-License-Identifier: MIT
// output_contract.hpp — 2-band state COG writer + sidecar JSON writer.
//
// The state COG is a 2-band GeoTIFF (band 1 = adult_occupancy, band 2 =
// host_seeking_pressure), tiled, deflate-compressed, 128x128 blocks, with
// `nodata = NODATA_SENTINEL` (-9999). The sidecar JSON is a small
// metadata file written next to the .tif (e.g.
// `ghana_regional_2024_06_seed0001.json` for the COG
// `ghana_regional_2024_06_seed0001.tif`).
//
// The sidecar is the F1.e parity test's primary input — it lists
// `contract_version`, `generator_version`, `band_names`, `nodata`,
// `k_max`, etc. Two engines producing the same state COG bytes for
// the same inputs must also produce byte-equal sidecars.
#pragma once

#include <array>
#include <cstdint>
#include <string>

#include "wire.hpp"

namespace mal_abm_fast {

// The metadata blob written into the sidecar JSON. Every field is
// required; the writer must emit them in this exact order (the
// `k_max` and `band_names` are pinned by the parity test).
//
// F1.c `n_rollouts` and `rollout_index` (default 1 / 0): added in
// the F1.c `--n-rollouts` change. The single-rollout case
// (n_rollouts=1, rollout_index=0) is the legacy behaviour: the
// fields are written but always read as 1 / 0, so the v1.0 sidecars
// from F1.b are bit-compatible with v1.1 *except* for the two
// added keys and the `contract_version` bump (1.0 -> 1.1).
struct StateCogMetadata {
    std::string                 crs;                // EPSG string ("EPSG:4326")
    std::array<double, 6>       transform;          // GDAL affine 6-tuple
    std::string                 aoi_slug;           // matches AOI.slug
    std::string                 scale;              // matches AOI.scale
    int32_t                     year  = 0;
    int32_t                     month = 0;
    int32_t                     seed  = 0;
    int32_t                     n_rollouts     = 1;  // F1.c
    int32_t                     rollout_index  = 0;  // F1.c (0-indexed)
    std::string                 generator_version = GENERATOR_VERSION;
    std::string                 abm_params_hash   = "sha256:pending";
    std::string                 contract_version  = CONTRACT_VERSION;
    std::array<std::string, 2>  band_names         = {
        STATE_BAND_NAMES[0], STATE_BAND_NAMES[1]
    };
    float                       nodata = NODATA_SENTINEL;
    int32_t                     h = 0;
    int32_t                     w = 0;
    int32_t                     k_max = K_MAX;
};

// Write the 2-band state COG. The implementation subagent uses GDAL
// (GTiff driver) with:
//   * tiled = true
//   * compress = deflate
//   * blockxsize = blockysize = 128
//   * nodata = NODATA_SENTINEL
//   * band descriptions = band_names[0], band_names[1]
//
// Returns the .tif path on success. Throws std::runtime_error on
// GDAL failure.
void write_state_cog(const std::string& path,
                     const DensityGrid& density,
                     const SuitabilityGrid& suit,
                     const StateCogMetadata& meta);

// Write the sidecar JSON (e.g. `<tif_path>.json` for a `.tif` path).
// The keys in the JSON are the F1.e parity test's contract; the
// implementation subagent must emit them in the order listed in
// docs/wire-spec.md.
void write_state_sidecar(const std::string& tif_path,
                         const StateCogMetadata& meta);

}  // namespace mal_abm_fast
