// SPDX-License-Identifier: MIT
// wind_field.hpp — 6-hourly wind field (ERA5 u100/v100) for windborne
// mosquito migration (M7.6 Phase 2).
//
// Loads a 6-hourly NetCDF (u100, v100 variables with valid_time,
// latitude, longitude dimensions) via GDAL. Provides spatial
// nearest-neighbor lookup with temporal linear interpolation at
// (lon, lat, day_index, hour_of_day).
//
// The NetCDF stores N time steps at 6-hourly intervals (4 per day).
// day_index is the 0-based simulation day; it maps to the first
// time step of that day (slot 0 = 00:00 UTC). hour_of_day (0-23)
// selects which 6-hourly slot to interpolate within.
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

    // Load 6-hourly NetCDF wind field. Throws std::runtime_error
    // on failure. Reads u100 and v100 subdatasets via GDAL.
    void load_from_nc(const std::string& path);

    // Deprecated: load 24-band monthly mean GeoTIFF.
    // Internally converts to synthetic 6-hourly time steps.
    void load_from_tif(const std::string& path);

    // Query wind at (lon, lat) for simulation day_index (0-based)
    // and hour_of_day (0-23). Temporal linear interpolation between
    // the two bracketing 6-hourly slots within the day.
    // Returns {0, 0} if out of bounds or day_index exceeds data.
    WindVector wind_at(double lon, double lat,
                       int day_index, int hour_of_day) const;

    // Is the given month in the migration season?
    // Monsoon: Jul-Oct (7-10), Harmattan: Dec-Mar (12, 1-3).
    static bool is_migration_season(int month) noexcept;

    // Total number of days available in the dataset.
    int32_t n_days() const { return n_times_ / 4; }

    // Grid info (for diagnostics).
    int32_t nlat() const { return nlat_; }
    int32_t nlon() const { return nlon_; }
    int32_t n_times() const { return n_times_; }

private:
    // n_times_ × nlat_ × nlon_, row-major.
    std::vector<float> u100_;  // [t * nlat * nlon + row * nlon + col]
    std::vector<float> v100_;
    int32_t nlat_ = 0;
    int32_t nlon_ = 0;
    int32_t n_times_ = 0;
    // Geo-referencing (top-left corner + pixel size).
    double origin_lon_ = 0.0;
    double origin_lat_ = 0.0;
    double dlon_ = 0.0;
    double dlat_ = 0.0;
};

}  // namespace mal_abm_fast