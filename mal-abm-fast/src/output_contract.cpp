// SPDX-License-Identifier: MIT
// output_contract.cpp — 2-band state COG writer + sidecar JSON writer.
//
// `write_state_cog` produces a tiled, deflate-compressed, 128x128
// block GeoTIFF with two float32 bands: band 1 = adult_occupancy
// (total adult mosquitoes in cell post-dispersal / K_MAX ∈ [0, 1]),
// band 2 = host_seeking_pressure (female adults in host-seeking state
// / K_MAX ∈ [0, 1]). The nodata sentinel is `NODATA_SENTINEL`
// (-9999). The COG profile mirrors `docs/wire-spec.md` §2.
//
// `write_state_sidecar` writes a JSON sidecar next to the .tif, with
// the 14 keys the F1.e parity test pins. The keys are emitted in the
// order listed in `docs/wire-spec.md` so the byte-equal test is
// stable across engines.
#include "output_contract.hpp"

#include <array>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <stdexcept>
#include <string>
#include <vector>

#include <nlohmann/json.hpp>

#include <gdal.h>
#include <gdal_priv.h>
#include <ogr_spatialref.h>
#include <ogr_srs_api.h>
#include <cpl_conv.h>
#include <cpl_string.h>

#include "wire.hpp"

namespace mal_abm_fast {

namespace {

// Replace ".tif" with ".json" in `tif_path` (case-insensitive on the
// last 4 characters). If the path does not end in ".tif", append
// ".json". The F1.e parity test reads this sidecar after the COG.
std::string sidecar_path_for(const std::string& tif_path) {
    constexpr const char* kTifExt = ".tif";
    constexpr std::size_t kExtLen = 4;
    if (tif_path.size() >= kExtLen) {
        const std::string tail = tif_path.substr(tif_path.size() - kExtLen);
        // Case-insensitive compare against ".tif".
        bool match = true;
        for (std::size_t i = 0; i < kExtLen; ++i) {
            char a = tail[i];
            char b = kTifExt[i];
            if (a >= 'A' && a <= 'Z') a = static_cast<char>(a - 'A' + 'a');
            if (b >= 'A' && b <= 'Z') b = static_cast<char>(b - 'A' + 'a');
            if (a != b) { match = false; break; }
        }
        if (match) {
            return tif_path.substr(0, tif_path.size() - kExtLen) + ".json";
        }
    }
    return tif_path + ".json";
}

}  // namespace

void write_state_cog(const std::string& path,
                     const DensityGrid& density,
                     const SuitabilityGrid& suit,
                     const StateCogMetadata& meta) {
    if (density.h != suit.h || density.w != suit.w) {
        throw std::runtime_error(
            "write_state_cog: density/suitability shape mismatch "
            "(density=" + std::to_string(density.h) + "x" +
            std::to_string(density.w) + ", suit=" +
            std::to_string(suit.h) + "x" + std::to_string(suit.w) + ")");
    }
    if (density.h <= 0 || density.w <= 0) {
        throw std::runtime_error(
            "write_state_cog: zero-sized grid");
    }
    if (static_cast<int64_t>(density.data.size()) !=
        static_cast<int64_t>(density.h) * static_cast<int64_t>(density.w)) {
        throw std::runtime_error(
            "write_state_cog: density.data size does not match h*w");
    }
    if (static_cast<int64_t>(suit.data.size()) !=
        static_cast<int64_t>(suit.h) * static_cast<int64_t>(suit.w)) {
        throw std::runtime_error(
            "write_state_cog: suit.data size does not match h*w");
    }

    // NaN guards
    for (size_t i = 0; i < density.data.size(); ++i) {
        if (std::isnan(density.data[i])) {
            throw std::runtime_error(
                "write_state_cog: NaN detected in density grid at index " +
                std::to_string(i));
        }
    }
    for (size_t i = 0; i < suit.data.size(); ++i) {
        if (std::isnan(suit.data[i])) {
            throw std::runtime_error(
                "write_state_cog: NaN detected in suitability grid at index " +
                std::to_string(i));
        }
    }

    const int h = static_cast<int>(density.h);
    const int w = static_cast<int>(density.w);

    GDALDriver* drv = GetGDALDriverManager()->GetDriverByName("GTiff");
    if (drv == nullptr) {
        throw std::runtime_error(
            "write_state_cog: GTiff driver not registered");
    }

    char** opts = nullptr;
    opts = CSLSetNameValue(opts, "TILED", "YES");
    opts = CSLSetNameValue(opts, "BLOCKXSIZE", "128");
    opts = CSLSetNameValue(opts, "BLOCKYSIZE", "128");
    opts = CSLSetNameValue(opts, "COMPRESS", "DEFLATE");
    opts = CSLSetNameValue(opts, "COPY_SRC_OVERVIEWS", "YES");

    GDALDataset* ds = drv->Create(path.c_str(), w, h, 2, GDT_Float32, opts);
    CSLDestroy(opts);
    if (ds == nullptr) {
        throw std::runtime_error(
            "write_state_cog: cannot create COG at " + path);
    }

    // Affine transform (6 doubles).
    std::array<double, 6> transform = meta.transform;
    if (ds->SetGeoTransform(transform.data()) != CE_None) {
        GDALClose(ds);
        throw std::runtime_error(
            "write_state_cog: SetGeoTransform failed");
    }

    // CRS (e.g. "EPSG:4326"). The OGRSpatialReference ctor parses
    // the user input string; SetFromUserInput handles EPSG codes,
    // WKT, and proj4.
    if (!meta.crs.empty()) {
        OGRSpatialReference srs;
        if (srs.SetFromUserInput(meta.crs.c_str()) != OGRERR_NONE) {
            GDALClose(ds);
            throw std::runtime_error(
                "write_state_cog: cannot parse CRS '" + meta.crs + "'");
        }
        // SetSpatialRef takes ownership of a reference to srs; we
        // pass a non-const pointer. The dataset copies the SRS
        // internally, so we do not call srs.release().
        char* opts2 = nullptr;
        OGRErr err = ds->SetSpatialRef(&srs);
        (void)opts2;
        if (err != OGRERR_NONE) {
            GDALClose(ds);
            throw std::runtime_error(
                "write_state_cog: SetSpatialRef failed");
        }
    }

    // Band 1 = density. Write the row-major float32 buffer.
    {
        GDALRasterBand* band = ds->GetRasterBand(1);
        if (band == nullptr) {
            GDALClose(ds);
            throw std::runtime_error(
                "write_state_cog: cannot get band 1");
        }
        band->SetDescription(STATE_BAND_NAMES[STATE_BAND_DENSITY - 1]);
        band->SetNoDataValue(static_cast<double>(NODATA_SENTINEL));
        CPLErr err = band->RasterIO(
            GF_Write, 0, 0, w, h,
            const_cast<float*>(density.data.data()), w, h,
            GDT_Float32, 0, 0);
        if (err != CE_None) {
            GDALClose(ds);
            throw std::runtime_error(
                "write_state_cog: band 1 RasterIO failed");
        }
    }

    // Band 2 = suitability.
    {
        GDALRasterBand* band = ds->GetRasterBand(2);
        if (band == nullptr) {
            GDALClose(ds);
            throw std::runtime_error(
                "write_state_cog: cannot get band 2");
        }
        band->SetDescription(STATE_BAND_NAMES[STATE_BAND_SUITABILITY - 1]);
        band->SetNoDataValue(static_cast<double>(NODATA_SENTINEL));
        CPLErr err = band->RasterIO(
            GF_Write, 0, 0, w, h,
            const_cast<float*>(suit.data.data()), w, h,
            GDT_Float32, 0, 0);
        if (err != CE_None) {
            GDALClose(ds);
            throw std::runtime_error(
                "write_state_cog: band 2 RasterIO failed");
        }
    }

    GDALClose(ds);
}

void write_state_sidecar(const std::string& tif_path,
                         const StateCogMetadata& meta) {
    nlohmann::json j;
    // The key order here matches docs/wire-spec.md §2 (the parity
    // test relies on a stable ordering for the JSON object).
    //
    // F1.c: `n_rollouts` and `rollout_index` are inserted between
    // `seed` and `generator_version` (after the F1.b keys, before
    // the F1.d keys). The v1.1 contract adds these two fields.
    j["crs"]               = meta.crs;
    j["transform"]         = nlohmann::json::array();
    for (int i = 0; i < 6; ++i) {
        j["transform"].push_back(static_cast<double>(meta.transform[i]));
    }
    j["aoi_slug"]          = meta.aoi_slug;
    j["scale"]             = meta.scale;
    j["year"]              = meta.year;
    j["month"]             = meta.month;
    j["seed"]              = meta.seed;
    j["n_rollouts"]        = meta.n_rollouts;
    j["rollout_index"]     = meta.rollout_index;
    j["generator_version"] = meta.generator_version;
    j["abm_params_hash"]   = meta.abm_params_hash;
    j["contract_version"]  = meta.contract_version;
    j["band_names"]        = nlohmann::json::array();
    for (int i = 0; i < 2; ++i) {
        j["band_names"].push_back(meta.band_names[i]);
    }
    j["nodata"]            = static_cast<double>(meta.nodata);
    j["shape"]             = nlohmann::json::array();
    j["shape"].push_back(2);
    j["shape"].push_back(meta.h);
    j["shape"].push_back(meta.w);
    j["k_max"]             = meta.k_max;

    const std::string sidecar_path = sidecar_path_for(tif_path);
    std::ofstream f(sidecar_path, std::ios::out | std::ios::trunc);
    if (!f.is_open()) {
        throw std::runtime_error(
            "write_state_sidecar: cannot open " + sidecar_path);
    }
    f << j.dump(2) << "\n";
    if (!f.good()) {
        throw std::runtime_error(
            "write_state_sidecar: write failed for " + sidecar_path);
    }
}

}  // namespace mal_abm_fast
