// SPDX-License-Identifier: MIT
// mobility_schedule.cpp — Stub implementation for future OD-matrix mobility.
//
// Placeholder: loads and validates OD matrices from .csr files in a
// directory.  The actual per-day movement logic will be wired in a
// later gate.
#include "mobility_schedule.hpp"

#include <iostream>

namespace mal_abm_fast {

void MobilitySchedule::load_from_directory(const std::string& /*dir*/,
                                           const AOI& /*aoi*/) {
    // Placeholder — no-op.  The real implementation will scan
    // the directory for .csr files and populate matrices_.
}

}  // namespace mal_abm_fast
