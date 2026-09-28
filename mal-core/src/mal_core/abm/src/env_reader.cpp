// SPDX-License-Identifier: MIT
// env_reader.cpp — read the daily env NetCDF into a flat DailyEnvBands
// struct (the legacy 4-band COG reader `read_env_tif` was removed — the
// env input contract is NC-only; see docs/specs/abm/spec.md INV-6).

#include "env_reader.hpp"

#include <netcdf.h>

#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <cstring>
#include <stdexcept>
#include <string>
#include <unordered_map>
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

// GDAL's netCDF driver exposes an index-ordered y dimension from south to
// north as a north-up raster, so RasterIO returns the vertical order reversed
// relative to the row-major arrays written by daily_nc.py. Restore the
// producer's row order before the ABM aligns climate cells with habitat rows.
void FlipVertical(BandRead& band) {
    for (int32_t row = 0; row < band.h / 2; ++row) {
        const int32_t other = band.h - 1 - row;
        auto first = band.data.begin() +
            static_cast<std::ptrdiff_t>(row) * band.w;
        auto second = band.data.begin() +
            static_cast<std::ptrdiff_t>(other) * band.w;
        std::swap_ranges(first, first + band.w, second);
    }
}

// RAII wrapper around GDALDatasetH to guarantee GDALClose runs even
// when the body of read_env_nc throws.
struct DatasetCloser {
    GDALDatasetH ds;
    explicit DatasetCloser(GDALDatasetH d) : ds(d) {}
    ~DatasetCloser() { if (ds) GDALClose(ds); }
    DatasetCloser(const DatasetCloser&) = delete;
    DatasetCloser& operator=(const DatasetCloser&) = delete;
};

}  // namespace

// -- NetCDF reader (daily-env-netcdf feature) --------------------------------

DailyEnvBands read_env_nc(const std::string& path, int32_t max_days) {
    EnsureGdalRegistered();

    // GDAL's netCDF driver exposes multi-variable files as subdatasets
    // (NETCDF:"path":varname). Each subdataset contains bands = time
    // steps for that variable. We open the root to find subdatasets,
    // then open each required variable's subdataset to read bands.
    GDALDatasetH root = GDALOpen(path.c_str(), GA_ReadOnly);
    if (root == nullptr) {
        throw std::runtime_error(
            std::string("env_reader::read_env_nc: GDALOpen failed for ")
            + path + ": " + CPLGetLastErrorMsg());
    }

    // Collect subdataset names from the root's SUBDATASETS metadata domain.
    const char* const* md = GDALGetMetadata(root, "SUBDATASETS");
    std::unordered_map<std::string, std::string> subdatasets;
    for (int i = 0; md && md[i]; ++i) {
        const std::string key(md[i]);
        if (key.find("_NAME=") != std::string::npos) {
            // Format: SUBDATASET_1_NAME=NETCDF:"path":varname
            auto eq = key.find('=');
            auto val = key.substr(eq + 1);
            auto colon = val.rfind(':');
            if (colon != std::string::npos) {
                std::string varname = val.substr(colon + 1);
                // Strip trailing quotes if any
                if (!varname.empty() && varname.back() == '"')
                    varname.pop_back();
                subdatasets[varname] = val;
            }
        }
    }
    GDALClose(root);

    DailyEnvBands out;
    out.transform.fill(0.0);

    // `static_plane=true` reads a single-plane variable (e.g. static
    // TWI) and skips the n_days consistency check that time-series
    // variables must satisfy.
    auto read_variable = [&](const char* varname,
                             bool static_plane = false) -> std::vector<float> {
        auto it = subdatasets.find(varname);
        if (it == subdatasets.end()) {
            throw std::runtime_error(
                std::string("env_reader::read_env_nc: missing required variable '")
                + varname + "' in " + path);
        }
        GDALDatasetH ds = GDALOpen(it->second.c_str(), GA_ReadOnly);
        if (ds == nullptr) {
            throw std::runtime_error(
                std::string("env_reader::read_env_nc: failed to open subdataset for '")
                + varname + "': " + CPLGetLastErrorMsg());
        }
        DatasetCloser closer(ds);

        const int nbands = GDALGetRasterCount(ds);
        if (nbands <= 0) {
            throw std::runtime_error(
                std::string("env_reader::read_env_nc: variable '")
                + varname + "' has no bands");
        }

        // Determine how many bands to read
        const int bands_to_read = static_plane
            ? nbands
            : ((max_days > 0 && max_days < nbands) ? max_days : nbands);

        std::vector<float> result;
        for (int i = 1; i <= bands_to_read; ++i) {
            BandRead br = ReadBand(GDALGetRasterBand(ds, i));
            FlipVertical(br);
            if (out.h == 0) { out.h = br.h; out.w = br.w; }
            else if (out.h != br.h || out.w != br.w) {
                throw std::runtime_error(
                    std::string("env_reader::read_env_nc: variable '")
                    + varname + "' has inconsistent band shape");
            }
            result.insert(result.end(), br.data.begin(), br.data.end());
        }

        if (!static_plane) {
            if (out.n_days == 0) {
                out.n_days = bands_to_read;
            } else if (out.n_days != bands_to_read) {
                throw std::runtime_error(
                    std::string("env_reader::read_env_nc: variable '")
                    + varname + "' has " + std::to_string(bands_to_read)
                    + " time steps, expected " + std::to_string(out.n_days));
            }
        }
        return result;
    };

    out.rainfall     = read_variable("rainfall");
    out.water_temp_c = read_variable("water_temp_c");
    out.water_frac   = read_variable("water_frac");
    out.ndvi         = read_variable("ndvi");

    // Optional salinity (psu). The env NC predates salinity; a file
    // without `salinity_ppt` must load identically (salinity_ empty,
    // accessor returns 0.0 = freshwater, the legacy behaviour).
    if (subdatasets.count("salinity_ppt") != 0) {
        std::vector<float> v = read_variable("salinity_ppt");
        const size_t expected = static_cast<size_t>(out.n_days)
                             * static_cast<size_t>(out.h) * static_cast<size_t>(out.w);
        if (v.size() != expected) {
            throw std::runtime_error(
                std::string("env_reader::read_env_nc: salinity_ppt size ")
                + std::to_string(v.size()) + " != " + std::to_string(expected));
        }
        // Fill no-data / NaN / negative values with 0.0 (freshwater).
        for (float& x : v) {
            if (!std::isfinite(x)) x = 0.0f;
            else if (x < 0.0f) x = 0.0f;
        }
        out.salinity_ppt = std::move(v);
    }

    if (subdatasets.count("permanent_water_mask") != 0) {
        out.permanent_water_mask = read_variable("permanent_water_mask");
        for (float& x : out.permanent_water_mask) {
            if (!std::isfinite(x) || x < 0.0f) x = 0.0f;
            else if (x > 1.0f) x = 1.0f;
        }
    }

    // Optional static TWI (plan §6.3 pluvial-pool rules; M7.4.1).
    // Static variable: single band (no time dimension). A file without
    // 'twi' must load identically (twi stays empty; the coordinator
    // treats missing TWI as 0 and the urban rule falls back to
    // rain + building-cover gating).
    if (subdatasets.count("twi") != 0) {
        std::vector<float> v = read_variable("twi", /*static_plane=*/true);
        const size_t expected =
            static_cast<size_t>(out.h) * static_cast<size_t>(out.w);
        if (v.size() == expected) {
            for (float& x : v) {
                if (!std::isfinite(x) || x < 0.0f) x = 0.0f;
            }
            out.twi = std::move(v);
        }
        // Size mismatch (e.g. stale variable) → leave empty, warn-free:
        // the simulation proceeds with the documented fallback.
    }

    // Optional static per-cell capacity multiplier (M7.4.1): feeds the
    // Beverton-Holt larval cap K_patch = K_MAX × mult through the
    // coordinator's K_eff view. Absent → legacy urban-only K_eff.
    if (subdatasets.count("k_capacity_mult") != 0) {
        std::vector<float> v =
            read_variable("k_capacity_mult", /*static_plane=*/true);
        const size_t expected =
            static_cast<size_t>(out.h) * static_cast<size_t>(out.w);
        if (v.size() == expected) {
            for (float& x : v) {
                if (!std::isfinite(x) || x < 0.0f) x = 0.0f;
            }
            out.k_capacity_mult = std::move(v);
        }
    }

    // Optional static catchment-to-cell area ratio (M7.4.1): physical
    // input of the pool catchment-runoff model. Absent → the
    // coordinator falls back to the land-cover constant factors.
    if (subdatasets.count("catchment_ratio") != 0) {
        std::vector<float> v =
            read_variable("catchment_ratio", /*static_plane=*/true);
        const size_t expected =
            static_cast<size_t>(out.h) * static_cast<size_t>(out.w);
        if (v.size() == expected) {
            for (float& x : v) {
                if (!std::isfinite(x) || x < 0.0f) x = 0.0f;
            }
            out.catchment_ratio = std::move(v);
        }
    }

    // Static-band netCDF-C fallback (M7.4.1): older GDAL netCDF drivers
    // do not expose plain 2-D (y, x) variables as SUBDATASETS, which
    // silently zeroed twi / k_capacity_mult / catchment_ratio on such
    // systems. Read them straight from the file by variable name.
    auto read_static_netcdf = [&](const char* varname,
                                  std::vector<float>& dst) {
        if (!dst.empty()) return;  // GDAL path already delivered it
        int ncid = -1;
        if (nc_open(path.c_str(), NC_NOWRITE, &ncid) != NC_NOERR) return;
        int varid = -1;
        int ndims = 0;
        int dimids[2] = {-1, -1};
        size_t dims[2] = {0, 0};
        if (nc_inq_varid(ncid, varname, &varid) == NC_NOERR &&
            nc_inq_var(ncid, varid, nullptr, nullptr, &ndims, dimids,
                       nullptr) == NC_NOERR && ndims == 2 &&
            nc_inq_dimlen(ncid, dimids[0], &dims[0]) == NC_NOERR &&
            nc_inq_dimlen(ncid, dimids[1], &dims[1]) == NC_NOERR &&
            dims[0] == static_cast<size_t>(out.h) &&
            dims[1] == static_cast<size_t>(out.w)) {
            std::vector<float> v(dims[0] * dims[1], 0.0f);
            if (nc_get_var_float(ncid, varid, v.data()) == NC_NOERR) {
                for (float& x : v) {
                    if (!std::isfinite(x) || x < 0.0f) x = 0.0f;
                }
                dst = std::move(v);
            }
        }
        nc_close(ncid);
    };
    read_static_netcdf("twi", out.twi);
    read_static_netcdf("k_capacity_mult", out.k_capacity_mult);
    read_static_netcdf("catchment_ratio", out.catchment_ratio);

    if (out.h <= 0 || out.w <= 0) {
        throw std::runtime_error(
            "env_reader::read_env_nc: dataset has no rasters");
    }
    if (static_cast<int32_t>(out.rainfall.size()) != out.n_days * out.h * out.w) {
        throw std::runtime_error(
            "env_reader::read_env_nc: rainfall size mismatch");
    }
    return out;
}

}  // namespace env_reader
}  // namespace mal_abm_fast
