// SPDX-License-Identifier: MIT
// mobility_schedule.hpp — Stub for future OD-matrix-based mobility scheduling.
//
// This header declares the MobilitySchedule class which will load OD matrices
// (human day/night, livestock seasonal) for movement-based host-seeking.
// Currently a placeholder — the actual load/apply logic will be implemented
// when the mobility data pipeline is ready.
#pragma once

#include <cstdint>
#include <string>
#include <vector>

#include "aoi.hpp"

namespace mal_abm_fast {

/// Origin-destination matrix for a single population group.
struct ODMatrix {
    std::string label;                    // e.g. "human_day", "human_night", "livestock"
    int32_t n_origins = 0;
    int32_t n_destinations = 0;
    std::vector<float> probabilities;     // row-major (n_origins x n_destinations)
};

/// Placeholder mobility schedule loaded from OD matrices.
///
/// In a future gate this will provide per-cell, per-day movement
/// probabilities that modify the host-seeking attraction field. For
/// now the class loads and validates the matrices but is not called
/// from the simulation loop.
class MobilitySchedule {
public:
    MobilitySchedule() = default;

    /// Load mobility matrices from a directory of .csr files.
    /// No-op if the directory is empty or does not exist.
    void load_from_directory(const std::string& dir, const AOI& aoi);

    /// True if at least one OD matrix was loaded.
    bool has_data() const { return !matrices_.empty(); }

    /// Number of loaded matrices.
    size_t n_matrices() const { return matrices_.size(); }

    /// Access a matrix by index.
    const ODMatrix& at(size_t i) const { return matrices_.at(i); }

private:
    std::vector<ODMatrix> matrices_;
};

}  // namespace mal_abm_fast
