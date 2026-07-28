// SPDX-License-Identifier: MIT
// wind_field.cpp — WindField implementation (GDAL-based GeoTIFF reader).
#include "mal_abm_fast/wind_field.hpp"

#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <string>
#include <vector>

#include <gdal_priv.h>

namespace mal_abm_fast {

void WindField::load_from_tif(const std::string& path) {
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

    // Geo-transform: [origin_lon, dlon, 0, origin_lat, 0, -dlat]
    double gt[6];
    poDS->GetGeoTransform(gt);
    origin_lon_ = gt[0];
    origin_lat_ = gt[3];
    dlon_ = gt[1];
    dlat_ = std::abs(gt[5]);  // positive

    const size_t grid_size = static_cast<size_t>(nlat_) * static_cast<size_t>(nlon_);
    u100_.resize(12 * grid_size);
    v100_.resize(12 * grid_size);

    // Read bands 1-12 (u100) and 13-24 (v100).
    for (int m = 0; m < 12; ++m) {
        // u100 band (m+1)
        GDALRasterBand* band_u = poDS->GetRasterBand(m + 1);
        if (band_u->RasterIO(GF_Read, 0, 0, nlon_, nlat_,
                             u100_.data() + m * grid_size,
                             nlon_, nlat_, GDT_Float32, 0, 0) != CE_None) {
            throw std::runtime_error("WindField: failed to read u100 band " + std::to_string(m + 1));
        }
        // v100 band (m+13)
        GDALRasterBand* band_v = poDS->GetRasterBand(m + 13);
        if (band_v->RasterIO(GF_Read, 0, 0, nlon_, nlat_,
                             v100_.data() + m * grid_size,
                             nlon_, nlat_, GDT_Float32, 0, 0) != CE_None) {
            throw std::runtime_error("WindField: failed to read v100 band " + std::to_string(m + 13));
        }
    }
}

WindVector WindField::wind_at(double lon, double lat, int month) const {
    if (month < 1 || month > 12 || nlat_ == 0) return {0.0f, 0.0f};

    // Convert lon/lat to grid indices (nearest-neighbor).
    const double col_f = (lon - origin_lon_) / dlon_;
    const double row_f = (origin_lat_ - lat) / dlat_;  // lat decreases downward

    const int col = static_cast<int>(std::round(col_f));
    const int row = static_cast<int>(std::round(row_f));

    if (col < 0 || col >= nlon_ || row < 0 || row >= nlat_) return {0.0f, 0.0f};

    const size_t idx = static_cast<size_t>(month - 1) * static_cast<size_t>(nlat_) * static_cast<size_t>(nlon_)
                     + static_cast<size_t>(row) * static_cast<size_t>(nlon_)
                     + static_cast<size_t>(col);

    return {u100_[idx], v100_[idx]};
}

bool WindField::is_migration_season(int month) noexcept {
    // Monsoon: Jul-Oct (7, 8, 9, 10), Harmattan: Dec-Mar (12, 1, 2, 3)
    return (month >= 7 && month <= 10) || (month >= 12) || (month <= 3);
}

}  // namespace mal_abm_fast
