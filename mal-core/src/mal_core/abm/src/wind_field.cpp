// SPDX-License-Identifier: MIT
// wind_field.cpp — WindField implementation (GDAL-based, 6-hourly NetCDF).
#include "mal_abm_fast/wind_field.hpp"

#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <string>
#include <vector>

#include <gdal_priv.h>

namespace mal_abm_fast {

namespace {
constexpr int kSlotsPerDay = 4;  // 00, 06, 12, 18 UTC
constexpr double kHoursPerSlot = 6.0;

// Read a single GDAL raster band into a float buffer.
void read_band(GDALRasterBand* band, float* buf, int nlon, int nlat) {
    if (band->RasterIO(GF_Read, 0, 0, nlon, nlat,
                       buf, nlon, nlat, GDT_Float32, 0, 0) != CE_None) {
        throw std::runtime_error("WindField: failed to read raster band");
    }
}

}  // namespace

void WindField::load_from_nc(const std::string& path) {
    // GDAL presents NetCDF variables as subdatasets.
    // We need to open the u100 and v100 subdatasets separately.
    GDALDatasetUniquePtr poDS(GDALDataset::FromHandle(GDALOpen(path.c_str(), GA_ReadOnly)));
    if (!poDS) {
        throw std::runtime_error("WindField: cannot open '" + path + "'");
    }

    // Get subdataset list
    CSLConstList subdatasets = poDS->GetMetadata("SUBDATASETS");
    if (!subdatasets || !subdatasets[0]) {
        throw std::runtime_error(
            "WindField: no subdatasets found in '" + path + "'. "
            "Is this a NetCDF with u100/v100 variables?");
    }

    // Find u100 and v100 subdataset paths
    std::string u100_path, v100_path;
    for (int i = 0; subdatasets[i]; ++i) {
        std::string entry(subdatasets[i]);
        if (entry.find("u100") != std::string::npos &&
            entry.find("_NAME=") != std::string::npos) {
            u100_path = entry.substr(entry.find('=') + 1);
        }
        if (entry.find("v100") != std::string::npos &&
            entry.find("_NAME=") != std::string::npos) {
            v100_path = entry.substr(entry.find('=') + 1);
        }
    }

    if (u100_path.empty() || v100_path.empty()) {
        throw std::runtime_error(
            "WindField: could not find u100/v100 subdatasets in '" + path + "'");
    }

    // Open u100 subdataset
    GDALDatasetUniquePtr poU(GDALDataset::FromHandle(GDALOpen(u100_path.c_str(), GA_ReadOnly)));
    if (!poU) {
        throw std::runtime_error("WindField: cannot open u100 subdataset");
    }

    nlon_ = poU->GetRasterXSize();
    nlat_ = poU->GetRasterYSize();
    n_times_ = poU->GetRasterCount();

    if (n_times_ < 1) {
        throw std::runtime_error("WindField: u100 has no time steps");
    }

    // Geo-transform: [origin_lon, dlon, 0, origin_lat, 0, -dlat]
    double gt[6];
    poU->GetGeoTransform(gt);
    origin_lon_ = gt[0];
    origin_lat_ = gt[3];
    dlon_ = gt[1];
    dlat_ = std::abs(gt[5]);

    const size_t grid_size = static_cast<size_t>(nlat_) * static_cast<size_t>(nlon_);
    const size_t total = static_cast<size_t>(n_times_) * grid_size;
    u100_.resize(total);
    v100_.resize(total);

    // Read all time steps for u100
    for (int t = 0; t < n_times_; ++t) {
        GDALRasterBand* band = poU->GetRasterBand(t + 1);
        read_band(band, u100_.data() + t * grid_size, nlon_, nlat_);
    }
    poU.reset();

    // Open v100 subdataset and read all time steps
    GDALDatasetUniquePtr poV(GDALDataset::FromHandle(GDALOpen(v100_path.c_str(), GA_ReadOnly)));
    if (!poV) {
        throw std::runtime_error("WindField: cannot open v100 subdataset");
    }
    for (int t = 0; t < n_times_; ++t) {
        GDALRasterBand* band = poV->GetRasterBand(t + 1);
        read_band(band, v100_.data() + t * grid_size, nlon_, nlat_);
    }
    poV.reset();
}

void WindField::load_from_tif(const std::string& path) {
    // Deprecated fallback: load 24-band monthly mean GeoTIFF.
    // Expand 12 months → 48 synthetic 6-hourly time steps (4 per month).
    GDALDatasetUniquePtr poDS(GDALDataset::FromHandle(GDALOpen(path.c_str(), GA_ReadOnly)));
    if (!poDS) {
        throw std::runtime_error("WindField: cannot open '" + path + "'");
    }

    const int nBands = poDS->GetRasterCount();
    if (nBands != 24) {
        throw std::runtime_error(
            "WindField: expected 24 bands (u100 month 1-12, v100 month 1-12), got "
            + std::to_string(nBands));
    }

    nlon_ = poDS->GetRasterXSize();
    nlat_ = poDS->GetRasterYSize();

    double gt[6];
    poDS->GetGeoTransform(gt);
    origin_lon_ = gt[0];
    origin_lat_ = gt[3];
    dlon_ = gt[1];
    dlat_ = std::abs(gt[5]);

    const size_t grid_size = static_cast<size_t>(nlat_) * static_cast<size_t>(nlon_);
    // 12 months × 4 slots/month = 48 time steps
    n_times_ = 48;
    u100_.resize(48 * grid_size);
    v100_.resize(48 * grid_size);

    for (int m = 0; m < 12; ++m) {
        GDALRasterBand* band_u = poDS->GetRasterBand(m + 1);
        GDALRasterBand* band_v = poDS->GetRasterBand(m + 13);

        // Read monthly mean into a temp buffer
        std::vector<float> buf_u(grid_size), buf_v(grid_size);
        read_band(band_u, buf_u.data(), nlon_, nlat_);
        read_band(band_v, buf_v.data(), nlon_, nlat_);

        // Copy to all 4 slots for this month
        for (int s = 0; s < 4; ++s) {
            const int t = m * 4 + s;
            float* dst_u = u100_.data() + t * grid_size;
            float* dst_v = v100_.data() + t * grid_size;
            std::copy(buf_u.begin(), buf_u.end(), dst_u);
            std::copy(buf_v.begin(), buf_v.end(), dst_v);
        }
    }
}

WindVector WindField::wind_at(double lon, double lat, int hour_of_day) const {
    if (nlat_ == 0 || n_times_ == 0) return {0.0f, 0.0f};
    if (hour_of_day < 0 || hour_of_day > 23) return {0.0f, 0.0f};

    // Spatial: nearest-neighbor
    const double col_f = (lon - origin_lon_) / dlon_;
    const double row_f = (origin_lat_ - lat) / dlat_;

    const int col = static_cast<int>(std::round(col_f));
    const int row = static_cast<int>(std::round(row_f));

    if (col < 0 || col >= nlon_ || row < 0 || row >= nlat_) return {0.0f, 0.0f};

    // Temporal: linear interpolation between 6-hourly slots.
    // Slots: 0→00:00, 1→06:00, 2→12:00, 3→18:00, 4→00:00 (next day)
    // hour_of_day 0-23 maps to fractional slot index.
    const double slot_f = static_cast<double>(hour_of_day) / kHoursPerSlot;
    int slot0 = static_cast<int>(std::floor(slot_f)) % kSlotsPerDay;
    int slot1 = (slot0 + 1) % kSlotsPerDay;
    const double frac = slot_f - std::floor(slot_f);

    // If we only have one day of data, wrap around
    const int t0 = slot0 % n_times_;
    const int t1 = slot1 % n_times_;

    const size_t base0 = static_cast<size_t>(t0) * static_cast<size_t>(nlat_) * static_cast<size_t>(nlon_)
                       + static_cast<size_t>(row) * static_cast<size_t>(nlon_)
                       + static_cast<size_t>(col);
    const size_t base1 = static_cast<size_t>(t1) * static_cast<size_t>(nlat_) * static_cast<size_t>(nlon_)
                       + static_cast<size_t>(row) * static_cast<size_t>(nlon_)
                       + static_cast<size_t>(col);

    const float u = u100_[base0] * static_cast<float>(1.0 - frac) + u100_[base1] * static_cast<float>(frac);
    const float v = v100_[base0] * static_cast<float>(1.0 - frac) + v100_[base1] * static_cast<float>(frac);

    return {u, v};
}

bool WindField::is_migration_season(int month) noexcept {
    return (month >= 7 && month <= 10) || (month >= 12) || (month <= 3);
}

}  // namespace mal_abm_fast
