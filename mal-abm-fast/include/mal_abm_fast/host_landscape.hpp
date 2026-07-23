// SPDX-License-Identifier: MIT
// host_landscape.hpp — Grid-wide host density reader from host_static.nc.
//
// HostLandscape provides per-cell host densities and urbanicity derived
// from the Python-built `host_static.nc` NetCDF file. If the file is
// absent, defaults are returned (humans=1.0, everything else=0).
//
// The NC file has 5 2-D variables on (y, x):
//   human       — persons per ABM cell (float32)
//   cattle      — cattle per ABM cell (float32)
//   goats       — goats per ABM cell (float32)
//   sheep       — sheep per ABM cell (float32)
//   urban_class — GHS-SMOD class (int32: 30=urban, 50=rural)
#pragma once

#include <cstdint>
#include <string>
#include <vector>

#include "aoi.hpp"

namespace mal_abm_fast {

/// Per-cell host densities and urbanicity.
struct HostCell {
    float humans_present       = 1.0f;   // persons per cell
    float cattle_present       = 0.0f;
    float goats_present        = 0.0f;
    float sheep_present        = 0.0f;
    float wildlife_proxy       = 0.0f;   // derived from livestock; 0 if no data
    float indoor_fraction      = 0.5f;   // 0.72 for urban, 0.30 for rural (gambiae)
    float residential_fraction = 0.5f;
    float urbanicity           = 0.0f;   // 1.0 = urban, 0.0 = rural
};

/// Grid-wide host density landscape.  Loads from `host_static.nc` or
/// returns sensible defaults when the file is missing.
class HostLandscape {
public:
    HostLandscape() = default;

    /// Load host densities from a NetCDF file written by build_hosts.py.
    /// If the file does not exist, populates the grid with defaults.
    /// `aoi` provides spatial metadata; `h`/`w` are derived from it.
    void load_from_nc(const std::string& path, const AOI& aoi);

    /// Row-major accessor.  Returns defaults if (row, col) is out of bounds.
    HostCell at(int32_t row, int32_t col) const;

    int32_t h() const { return h_; }
    int32_t w() const { return w_; }

    /// True if data was loaded from a real NC file (vs defaults).
    bool has_data() const { return has_data_; }

private:
    std::vector<HostCell> cells_;
    int32_t h_ = 0;
    int32_t w_ = 0;
    bool has_data_ = false;
};

}  // namespace mal_abm_fast
