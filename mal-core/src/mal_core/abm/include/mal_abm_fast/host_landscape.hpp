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
    float pigs_present         = 0.0f;
    float chickens_present     = 0.0f;
    float wildlife_proxy       = 0.0f;   // from NC wildlife_host_proxy; 0 if no data
    float building_fraction    = 0.0f;   // [0,1] from Overture Maps
    float indoor_fraction      = 0.5f;   // 0.72 for urban, 0.30 for rural (gambiae)
    float residential_fraction = 0.5f;
    float urbanicity           = 0.0f;   // 1.0 = urban, 0.0 = rural
    int32_t urban_class        = 0;      // GHS-SMOD (30=urban, 50=rural, 0=unset)
};

/// Grid-wide host density landscape.  Loads from `host_static.nc` or
/// returns sensible defaults when the file is missing.
///
/// The class serves two roles:
///   * the static **residential** grid (loaded from NC), and
///   * an **effective** view built by `make_effective` for a specific
///     phase (H_eff(d, p)).  Effective views are deep copies of the
///     residential cells with per-cell humans (and optionally cattle)
///     replaced by runtime-supplied values; they never mutate the
///     residential grid they were derived from.  `is_effective()`
///     distinguishes the two so callers know which grid they hold.
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

    /// True if this grid is an effective (phase-specific) view built by
    /// `make_effective`, as opposed to the static residential grid.
    bool is_effective() const { return is_effective_; }

    /// Build an effective (phase-specific) host landscape view for one
    /// phase: a deep copy of `residential` in which every cell's
    /// `humans_present` is replaced by the H_eff value supplied in
    /// `h_eff_human` (row-major, length h*w).  Non-human fields
    /// (livestock, urbanicity, building fractions) are inherited from
    /// the residential grid unchanged.  The residential grid itself is
    /// NOT modified.
    ///
    /// Throws std::runtime_error if dimensions are non-positive or
    /// `h_eff_human` does not match h*w.
    static HostLandscape make_effective(
        const HostLandscape& residential,
        const std::vector<float>& h_eff_human,
        int32_t h, int32_t w);

    /// Overload that also replaces `cattle_present` per cell from
    /// `h_eff_cattle` (e.g. the livestock H_eff grid).  Pass an empty
    /// vector to leave cattle as the residential value.
    static HostLandscape make_effective(
        const HostLandscape& residential,
        const std::vector<float>& h_eff_human,
        const std::vector<float>& h_eff_cattle,
        int32_t h, int32_t w);

private:
    std::vector<HostCell> cells_;
    int32_t h_ = 0;
    int32_t w_ = 0;
    bool has_data_ = false;
    bool is_effective_ = false;
};

}  // namespace mal_abm_fast
