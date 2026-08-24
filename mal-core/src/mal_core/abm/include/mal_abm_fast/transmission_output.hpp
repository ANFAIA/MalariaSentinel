// SPDX-License-Identifier: MIT
// transmission_output.hpp — 4-band transmission GeoTIFF and sidecar JSON writer.
//
// M7.4: Writes spatial transmission outputs without modifying the 2-band state COG.
// Band 1: human_prevalence (I_H / H)
// Band 2: human_incidence (new E_H / H)
// Band 3: infectious_vector_pressure (infectious bites delivered today)
// Band 4: active_focus (1.0 if prevalence > threshold or incidence > 0, else 0.0)
#pragma once

#include <array>
#include <cstdint>
#include <string>
#include <vector>

#include "transmission.hpp"
#include "wire.hpp"

namespace mal_abm_fast {

inline constexpr const char* TRANSMISSION_BAND_NAMES[4] = {
    "human_prevalence",
    "human_incidence",
    "infectious_vector_pressure",
    "active_focus"
};

struct TransmissionCogMetadata {
    std::string           crs;
    std::array<double, 6> transform;
    std::string           aoi_slug;
    std::string           scale;
    int32_t               year = 0;
    int32_t               month = 0;
    int32_t               day = 0;
    int32_t               seed = 0;
    int32_t               n_rollouts = 1;
    int32_t               rollout_index = 0;
    std::string           generator_version = GENERATOR_VERSION;
    std::string           contract_version  = "2.0-transmission";
    std::array<std::string, 4> band_names = {
        TRANSMISSION_BAND_NAMES[0],
        TRANSMISSION_BAND_NAMES[1],
        TRANSMISSION_BAND_NAMES[2],
        TRANSMISSION_BAND_NAMES[3]
    };
    float                 nodata = NODATA_SENTINEL;
    int32_t               h = 0;
    int32_t               w = 0;

    // Aggregate summary
    TransmissionDailyStats stats{};
};

/// Write the 4-band transmission GeoTIFF.
void write_transmission_cog(const std::string& path,
                            const HumanCompartmentGrid& human_grid,
                            const std::vector<float>& infectious_pressure,
                            float focus_threshold,
                            const TransmissionCogMetadata& meta);

/// Write the sidecar JSON next to the transmission GeoTIFF.
void write_transmission_sidecar(const std::string& tif_path,
                                const TransmissionCogMetadata& meta);

/// Write the complete daily transmission log to a JSON file.
void write_transmission_log(const std::string& path,
                            const std::vector<TransmissionDailyStats>& history,
                            int32_t n_days);

}  // namespace mal_abm_fast
