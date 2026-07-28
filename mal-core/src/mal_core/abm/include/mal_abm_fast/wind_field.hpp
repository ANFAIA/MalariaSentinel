// SPDX-License-Identifier: MIT
// wind_field.hpp — Monthly mean wind field (ERA5 u100/v100) for windborne
// mosquito migration (M7.6 Phase 1).
//
// Loads a 24-band GeoTIFF (bands 1-12 = u100 monthly mean Jan-Dec,
// bands 13-24 = v100 monthly mean Jan-Dec) via GDAL. Provides
// nearest-neighbor lookup at (lon, lat, month).
//
// Reference: Huestis et al. 2019 (Nature Communications) — windborne
// migration of Anopheles in the Sahel, ERA5 + HYSPLIT trajectories.
#pragma once

#include <cstdint>
#include <string>
#include <vector>

namespace mal_abm_fast {

// Wind vector at a point (m/s).
struct WindVector {
    float u = 0.0f;  // east-west component (positive = eastward)
    float v = 0.0f;  // north-south component (positive = northward)
};

class WindField {
public:
    WindField() = default;

    // Load the 24-band GeoTIFF wind field. Throws std::runtime_error
    // on failure.
    void load_from_tif(const std::string& path);

    // Query wind at (lon, lat) for month 1-12 (nearest-neighbor).
    // Returns {0, 0} if out of bounds.
    WindVector wind_at(double lon, double lat, int month) const;

    // Is the given month in the migration season?
    // Monsoon: Jul-Oct (7-10), Harmattan: Dec-Mar (12, 1-3).
    static bool is_migration_season(int month) noexcept;

    // Grid info (for diagnostics).
    int32_t nlat() const { return nlat_; }
    int32_t nlon() const { return nlon_; }

private:
    // 12 months × nlat × nlon, row-major.
    std::vector<float> u100_;  // [month * nlat * nlon + row * nlon + col]
    std::vector<float> v100_;
    int32_t nlat_ = 0;
    int32_t nlon_ = 0;
    // Geo-referencing (top-left corner + pixel size).
    double origin_lon_ = 0.0;
    double origin_lat_ = 0.0;
    double dlon_ = 0.0;
    double dlat_ = 0.0;
};

}  // namespace mal_abm_fast
