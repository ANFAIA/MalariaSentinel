// SPDX-License-Identifier: MIT
// env_reader.cpp — read the 4-band env COG into a flat EnvBands struct.
//
// The env COG is a single GeoTIFF with 4 (or 5) bands described by name
// (per docs/wire-spec.md §2):
//
//   band "rainfall"          (mm/day, float32)
//   band "temp_suitability"  ([0, 1] Mordecai parabolic — INVERTED on
//                             read to deg C, lower branch:
//                             T = 25 - 8 * sqrt(1 - s))
//   band "water_frac"        ([0, 1] open water fraction)
//   band "ndvi"              ([0, 1] vegetation index)
//   band "twi"  (optional)   (static TWI grid for the dynamic
//                             PLUVIAL_POOL rule)
//
// The temp_suitability band is Mordecai-inverted on read so the
// ClimateEngine's `temp_` grid is already in deg C (the EIP code
// expects T in deg C, not the raw [0, 1] suitability).
//
// The band order is not pinned — we look each band up by its
// GDALBandH->GetDescription() name. A missing required band is a
// hard error: the engine cannot fall back to a zero grid for a real
// run.

#include "env_reader.hpp"

#include <array>
#include <cmath>
#include <cstring>
#include <stdexcept>
#include <string>
#include <vector>

#include "gdal.h"

namespace mal_abm_fast {
namespace env_reader {

// -- internal helpers ---------------------------------------------------------

namespace {

// One-shot GDAL driver registration. GDALAllRegister is reference-counted
// by GDAL itself, so it's safe to call multiple times; we guard with a
// static local to keep the call cheap after the first invocation.
void EnsureGdalRegistered() {
    static const bool kRegistered = []() {
        GDALAllRegister();
        return true;
    }();
    (void)kRegistered;
}

// Read one raster band into a row-major float32 vector. Returns
// {h*w floats, h, w}. Throws std::runtime_error on failure.
struct BandRead {
    std::vector<float> data;
    int32_t            h = 0;
    int32_t            w = 0;
};

BandRead ReadBand(GDALRasterBandH band) {
    if (band == nullptr) {
        throw std::runtime_error(
            "env_reader::ReadBand: null band handle");
    }
    const int h = GDALGetRasterBandYSize(band);
    const int w = GDALGetRasterBandXSize(band);
    if (h <= 0 || w <= 0) {
        throw std::runtime_error(
            "env_reader::ReadBand: band has non-positive size");
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
            std::string("env_reader::ReadBand: GDALRasterIO failed: ")
            + CPLGetLastErrorMsg());
    }
    return out;
}

// Apply the Mordecai inverse element-wise to `v` in place.
//   T = 25 - 8 * sqrt(max(0, 1 - s))
// `s` is clamped to [0, 1] before the inverse (the Python `_suit_to_c`
// does the same clamp). NaN is propagated: std::isnan(s) yields NaN
// in the output, which the NaN-safe accumulate_eip then drops to zero
// GD (matches the Python env_reader behaviour, where NaN propagates
// through max/min/sqrt and the eip.py:25 NaN guard catches it).
void ApplyMordecaiInverse(std::vector<float>& v) {
    for (float& s : v) {
        if (std::isnan(s)) continue;             // propagate NaN (Python parity)
        if (s < 0.0f) s = 0.0f;
        else if (s > 1.0f) s = 1.0f;
        const float one_minus_s = 1.0f - s;
        const float root = std::sqrt(one_minus_s > 0.0f ? one_minus_s : 0.0f);
        s = 25.0f - 8.0f * root;
    }
}

// Find the 1-based band index whose description matches `name`. Returns
// 0 if no band matches. We use 1-based indices to match GDAL's
// GetRasterBand(int) signature and the wire-spec band numbering.
int FindBandByDescription(GDALDatasetH ds, const char* name) {
    if (ds == nullptr || name == nullptr) return 0;
    const int n = GDALGetRasterCount(ds);
    for (int i = 1; i <= n; ++i) {
        GDALRasterBandH b = GDALGetRasterBand(ds, i);
        if (b == nullptr) continue;
        const char* desc = GDALGetDescription(b);
        if (desc != nullptr && std::strcmp(desc, name) == 0) {
            return i;
        }
    }
    return 0;
}

// Read the 6-tuple GDAL affine transform. We always copy the first 6
// doubles (GDAL guarantees the array is at least 6 long).
std::array<double, 6> ReadTransform(GDALDatasetH ds) {
    std::array<double, 6> t{};
    if (GDALGetGeoTransform(ds, t.data()) != CE_None) {
        // On failure, GDAL leaves the array untouched. We zero it.
        t.fill(0.0);
    }
    return t;
}

// Read the WKT CRS string. Falls back to "" if the dataset has no CRS.
std::string ReadCrs(GDALDatasetH ds) {
    if (ds == nullptr) return std::string();
    const char* wkt = GDALGetProjectionRef(ds);
    if (wkt == nullptr) return std::string();
    return std::string(wkt);
}

// RAII wrapper around GDALDatasetH to guarantee GDALClose runs even
// when the body of read_env_tif throws.
struct DatasetCloser {
    GDALDatasetH ds;
    explicit DatasetCloser(GDALDatasetH d) : ds(d) {}
    ~DatasetCloser() { if (ds) GDALClose(ds); }
    DatasetCloser(const DatasetCloser&) = delete;
    DatasetCloser& operator=(const DatasetCloser&) = delete;
};

}  // namespace

// -- public API ---------------------------------------------------------------

EnvBands read_env_tif(const std::string& path) {
    EnsureGdalRegistered();

    GDALDatasetH raw = GDALOpen(path.c_str(), GA_ReadOnly);
    if (raw == nullptr) {
        throw std::runtime_error(
            std::string("env_reader::read_env_tif: GDALOpen failed for ")
            + path + ": " + CPLGetLastErrorMsg());
    }
    DatasetCloser closer(raw);

    EnvBands out;
    out.transform = ReadTransform(raw);
    out.crs       = ReadCrs(raw);

    // Required bands. We look each up by description; the first one we
    // find sets h/w (they must all agree — we assert below).
    auto read_named = [&](const char* name) -> std::vector<float> {
        const int idx = FindBandByDescription(raw, name);
        if (idx == 0) {
            throw std::runtime_error(
                std::string("env_reader::read_env_tif: missing required band '")
                + name + "' in " + path);
        }
        BandRead br = ReadBand(GDALGetRasterBand(raw, idx));
        if (out.h == 0) { out.h = br.h; out.w = br.w; }
        else if (out.h != br.h || out.w != br.w) {
            throw std::runtime_error(
                std::string("env_reader::read_env_tif: band '")
                + name + "' has a different shape");
        }
        return std::move(br.data);
    };

    out.water_frac  = read_named("water_frac");
    out.rainfall    = read_named("rainfall");
    out.ndvi        = read_named("ndvi");

    // temp_suitability: same lookup, then Mordecai-invert in place.
    {
        std::vector<float> s = read_named("temp_suitability");
        ApplyMordecaiInverse(s);
        out.temp_suitability = std::move(s);
    }

    // Optional 5th band. Missing is fine (the dynamic PLUVIAL_POOL rule
    // treats TWI as 0 everywhere in that case — see climate.hpp).
    {
        const int idx = FindBandByDescription(raw, "twi");
        if (idx != 0) {
            BandRead br = ReadBand(GDALGetRasterBand(raw, idx));
            if (out.h == 0) { out.h = br.h; out.w = br.w; }
            else if (out.h != br.h || out.w != br.w) {
                // Tolerate a TWI shape mismatch: leave twi_ empty and
                // let the climate engine fall back to zeros. The env
                // bands still drive the simulation.
                out.twi.clear();
            } else {
                out.twi = std::move(br.data);
            }
        }
    }

    if (out.h <= 0 || out.w <= 0) {
        throw std::runtime_error(
            "env_reader::read_env_tif: dataset has no rasters");
    }
    return out;
}

}  // namespace env_reader
}  // namespace mal_abm_fast
