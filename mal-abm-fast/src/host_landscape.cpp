// SPDX-License-Identifier: MIT
// host_landscape.cpp — Read host_static.nc via GDAL and populate HostLandscape.
//
// Uses GDAL's netCDF driver (same pattern as env_reader.cpp). Each
// variable is a subdataset with 1 band (static file). urban_class
// (int32, 30=urban, 50=rural) drives indoor_fraction and urbanicity.

#include "host_landscape.hpp"

#include <cmath>
#include <cstring>
#include <filesystem>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>

#include "gdal.h"

#include "aoi.hpp"
#include "wire.hpp"

namespace mal_abm_fast {

namespace {

void EnsureGdalRegistered() {
    static const bool kRegistered = []() {
        GDALAllRegister();
        return true;
    }();
    (void)kRegistered;
}

struct DatasetCloser {
    GDALDatasetH ds;
    explicit DatasetCloser(GDALDatasetH d) : ds(d) {}
    ~DatasetCloser() { if (ds) GDALClose(ds); }
    DatasetCloser(const DatasetCloser&) = delete;
    DatasetCloser& operator=(const DatasetCloser&) = delete;
};

struct BandRead {
    std::vector<float> data;
    int32_t h = 0;
    int32_t w = 0;
};

BandRead ReadBand(GDALRasterBandH band) {
    if (band == nullptr) {
        throw std::runtime_error(
            "host_landscape: null band handle");
    }
    const int h = GDALGetRasterBandYSize(band);
    const int w = GDALGetRasterBandXSize(band);
    if (h <= 0 || w <= 0) {
        throw std::runtime_error(
            "host_landscape: band has non-positive size");
    }
    BandRead out;
    out.h = static_cast<int32_t>(h);
    out.w = static_cast<int32_t>(w);
    out.data.assign(static_cast<size_t>(h) * static_cast<size_t>(w), 0.0f);

    const CPLErr err = GDALRasterIO(
        band, GF_Read,
        0, 0, w, h,
        out.data.data(), w, h,
        GDT_Float32, 0, 0);
    if (err != CE_None) {
        throw std::runtime_error(
            std::string("host_landscape: GDALRasterIO failed: ")
            + CPLGetLastErrorMsg());
    }
    return out;
}

// Read an int32 band into a float vector (for urban_class).
std::vector<float> ReadInt32BandAsFloat(GDALRasterBandH band) {
    if (band == nullptr) {
        throw std::runtime_error(
            "host_landscape: null int32 band handle");
    }
    const int h = GDALGetRasterBandYSize(band);
    const int w = GDALGetRasterBandXSize(band);
    if (h <= 0 || w <= 0) {
        throw std::runtime_error(
            "host_landscape: int32 band has non-positive size");
    }
    std::vector<int32_t> buf(static_cast<size_t>(h) * static_cast<size_t>(w));
    const CPLErr err = GDALRasterIO(
        band, GF_Read,
        0, 0, w, h,
        buf.data(), w, h,
        GDT_Int32, 0, 0);
    if (err != CE_None) {
        throw std::runtime_error(
            std::string("host_landscape: GDALRasterIO int32 failed: ")
            + CPLGetLastErrorMsg());
    }
    std::vector<float> out(buf.size());
    for (size_t i = 0; i < buf.size(); ++i) {
        out[i] = static_cast<float>(buf[i]);
    }
    return out;
}

// Map urban_class to indoor_fraction.
// An. gambiae: 72% endophilic (indoor) in urban, ~30% in rural.
float urban_class_to_indoor_fraction(float urban_class) {
    // GHSL SMOD: 30 = urban centre, 50 = rural.
    // Treat any value <= 40 as urban, >= 40 as rural.
    return (urban_class <= 40.0f) ? 0.72f : 0.30f;
}

float urban_class_to_urbanicity(float urban_class) {
    return (urban_class <= 40.0f) ? 1.0f : 0.0f;
}

}  // namespace

void HostLandscape::load_from_nc(const std::string& path, const AOI& aoi) {
    h_ = cells_per_side_h(aoi);
    w_ = aoi.cells_per_side();

    if (h_ <= 0 || w_ <= 0) {
        throw std::runtime_error(
            "host_landscape: AOI yields non-positive grid dimensions");
    }

    // If the file doesn't exist, return defaults.
    if (!std::filesystem::exists(path)) {
        cells_.resize(static_cast<size_t>(h_) * static_cast<size_t>(w_));
        has_data_ = false;
        return;
    }

    EnsureGdalRegistered();

    GDALDatasetH raw = GDALOpen(path.c_str(), GA_ReadOnly);
    if (raw == nullptr) {
        throw std::runtime_error(
            std::string("host_landscape: GDALOpen failed for ")
            + path + ": " + CPLGetLastErrorMsg());
    }
    DatasetCloser closer(raw);

    // Collect subdataset variable names.
    const char* const* md = GDALGetMetadata(raw, "SUBDATASETS");
    std::unordered_map<std::string, std::string> subdatasets;
    for (int i = 0; md && md[i]; ++i) {
        const std::string key(md[i]);
        if (key.find("_NAME=") != std::string::npos) {
            auto eq = key.find('=');
            auto val = key.substr(eq + 1);
            auto colon = val.rfind(':');
            if (colon != std::string::npos) {
                std::string varname = val.substr(colon + 1);
                if (!varname.empty() && varname.back() == '"')
                    varname.pop_back();
                subdatasets[varname] = val;
            }
        }
    }

    // Read each variable. Shape must match (h_ x w_).
    auto read_float_var = [&](const char* varname) -> std::vector<float> {
        auto it = subdatasets.find(varname);
        if (it == subdatasets.end()) {
            // Variable not present — return zeros.
            return std::vector<float>(
                static_cast<size_t>(h_) * static_cast<size_t>(w_), 0.0f);
        }
        GDALDatasetH ds = GDALOpen(it->second.c_str(), GA_ReadOnly);
        if (ds == nullptr) {
            throw std::runtime_error(
                std::string("host_landscape: failed to open subdataset '")
                + varname + "': " + CPLGetLastErrorMsg());
        }
        DatasetCloser dc(ds);
        GDALRasterBandH band = GDALGetRasterBand(ds, 1);
        if (band == nullptr) {
            throw std::runtime_error(
                std::string("host_landscape: variable '")
                + varname + "' has no bands");
        }
        BandRead br = ReadBand(band);
        if (br.h != h_ || br.w != w_) {
            throw std::runtime_error(
                std::string("host_landscape: variable '")
                + varname + "' shape mismatch: got "
                + std::to_string(br.h) + "x" + std::to_string(br.w)
                + ", expected " + std::to_string(h_) + "x" + std::to_string(w_));
        }
        return std::move(br.data);
    };

    auto read_int32_var = [&](const char* varname) -> std::vector<float> {
        auto it = subdatasets.find(varname);
        if (it == subdatasets.end()) {
            return std::vector<float>(
                static_cast<size_t>(h_) * static_cast<size_t>(w_), 0.0f);
        }
        GDALDatasetH ds = GDALOpen(it->second.c_str(), GA_ReadOnly);
        if (ds == nullptr) {
            throw std::runtime_error(
                std::string("host_landscape: failed to open subdataset '")
                + varname + "': " + CPLGetLastErrorMsg());
        }
        DatasetCloser dc(ds);
        GDALRasterBandH band = GDALGetRasterBand(ds, 1);
        if (band == nullptr) {
            throw std::runtime_error(
                std::string("host_landscape: variable '")
                + varname + "' has no bands");
        }
        std::vector<float> raw_f = ReadInt32BandAsFloat(band);
        if (static_cast<int32_t>(raw_f.size()) != h_ * w_) {
            throw std::runtime_error(
                std::string("host_landscape: variable '")
                + varname + "' size mismatch");
        }
        return raw_f;
    };

    std::vector<float> human     = read_float_var("human");
    std::vector<float> cattle    = read_float_var("cattle");
    std::vector<float> goats     = read_float_var("goats");
    std::vector<float> sheep     = read_float_var("sheep");
    std::vector<float> urban_cls = read_int32_var("urban_class");

    // Populate HostCell grid.
    const size_t n = static_cast<size_t>(h_) * static_cast<size_t>(w_);
    cells_.resize(n);
    for (size_t i = 0; i < n; ++i) {
        HostCell& c = cells_[i];
        c.humans_present  = human[i];
        c.cattle_present  = cattle[i];
        c.goats_present   = goats[i];
        c.sheep_present   = sheep[i];
        c.wildlife_proxy  = 0.0f;  // not in host_static.nc
        const float uc    = urban_cls[i];
        c.indoor_fraction      = urban_class_to_indoor_fraction(uc);
        c.residential_fraction = c.indoor_fraction * 0.8f;
        c.urbanicity           = urban_class_to_urbanicity(uc);
    }
    has_data_ = true;
}

HostCell HostLandscape::at(int32_t row, int32_t col) const {
    if (row < 0 || row >= h_ || col < 0 || col >= w_ || cells_.empty()) {
        return HostCell{};  // defaults
    }
    return cells_[static_cast<size_t>(row) * static_cast<size_t>(w_) +
                  static_cast<size_t>(col)];
}

}  // namespace mal_abm_fast
