// SPDX-License-Identifier: MIT
#include "output_contract.hpp"

#include <fstream>

namespace mal_abm_fast {
std::string write_state_cog(
    const std::string& path,
    const float* density, const float* suitability,
    int H, int W, const StateSidecar& sidecar
) {
    (void)density; (void)suitability; (void)H; (void)W; (void)sidecar;
    // F1.a stub: just touch the file so the round-trip is observable.
    std::ofstream f(path);
    f << "F1.a stub — real COG writer ships in F1.d.\n";
    return path;
}
}  // namespace mal_abm_fast
