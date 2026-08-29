// SPDX-License-Identifier: MIT
// transmission_output.cpp — 4-band transmission GeoTIFF and sidecar JSON writer implementation.
#include "mal_abm_fast/transmission_output.hpp"

#include <array>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
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

namespace mal_abm_fast {

namespace {

std::string sidecar_path_for(const std::string& tif_path) {
    constexpr const char* kTifExt = ".tif";
    constexpr std::size_t kExtLen = 4;
    if (tif_path.size() >= kExtLen) {
        const std::string tail = tif_path.substr(tif_path.size() - kExtLen);
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

void write_transmission_cog(
    const std::string& path,
    const HumanCompartmentGrid& human_grid,
    const std::vector<float>& infectious_pressure,
    float focus_threshold,
    const TransmissionCogMetadata& meta)
{
    const int32_t h = human_grid.h();
    const int32_t w = human_grid.w();
    if (h <= 0 || w <= 0) {
        throw std::runtime_error("write_transmission_cog: invalid grid dimensions");
    }
    const int64_t n_cells = static_cast<int64_t>(h) * static_cast<int64_t>(w);

    std::vector<float> b1_prev(static_cast<size_t>(n_cells), meta.nodata);
    std::vector<float> b2_inc(static_cast<size_t>(n_cells), meta.nodata);
    std::vector<float> b3_press(static_cast<size_t>(n_cells), meta.nodata);
    std::vector<float> b4_focus(static_cast<size_t>(n_cells), meta.nodata);

    const auto& pop = human_grid.population();
    const auto& inc = human_grid.incidence();
    const auto& prev = human_grid.prevalence();

    for (int64_t i = 0; i < n_cells; ++i) {
        const size_t idx = static_cast<size_t>(i);
        const double p = pop[idx];
        if (p > 0.0) {
            const float pr = static_cast<float>(prev[idx]);
            const float in = static_cast<float>(inc[idx] / std::max(1.0, p));
            const float prs = (idx < infectious_pressure.size()) ? infectious_pressure[idx] : 0.0f;
            const float foc = (pr >= focus_threshold || inc[idx] > 0.0) ? 1.0f : 0.0f;

            b1_prev[idx] = pr;
            b2_inc[idx]  = in;
            b3_press[idx] = prs;
            b4_focus[idx] = foc;
        }
    }

    GDALDriver* drv = GetGDALDriverManager()->GetDriverByName("GTiff");
    if (drv == nullptr) {
        GDALAllRegister();
        drv = GetGDALDriverManager()->GetDriverByName("GTiff");
    }
    if (drv == nullptr) {
        throw std::runtime_error("write_transmission_cog: GTiff driver not registered");
    }

    char** opts = nullptr;
    opts = CSLSetNameValue(opts, "TILED", "YES");
    opts = CSLSetNameValue(opts, "BLOCKXSIZE", "128");
    opts = CSLSetNameValue(opts, "BLOCKYSIZE", "128");
    opts = CSLSetNameValue(opts, "COMPRESS", "DEFLATE");
    opts = CSLSetNameValue(opts, "COPY_SRC_OVERVIEWS", "YES");

    GDALDataset* ds = drv->Create(path.c_str(), w, h, 4, GDT_Float32, opts);
    CSLDestroy(opts);
    if (ds == nullptr) {
        throw std::runtime_error("write_transmission_cog: cannot create GeoTIFF at " + path);
    }

    std::array<double, 6> transform = meta.transform;
    if (ds->SetGeoTransform(transform.data()) != CE_None) {
        GDALClose(ds);
        throw std::runtime_error("write_transmission_cog: SetGeoTransform failed");
    }

    if (!meta.crs.empty()) {
        OGRSpatialReference srs;
        if (srs.SetFromUserInput(meta.crs.c_str()) != OGRERR_NONE) {
            GDALClose(ds);
            throw std::runtime_error("write_transmission_cog: cannot parse CRS '" + meta.crs + "'");
        }
        if (ds->SetSpatialRef(&srs) != OGRERR_NONE) {
            GDALClose(ds);
            throw std::runtime_error("write_transmission_cog: SetSpatialRef failed");
        }
    }

    auto write_band = [&](int band_idx, const std::vector<float>& buffer, const char* name) {
        GDALRasterBand* band = ds->GetRasterBand(band_idx);
        if (band == nullptr) {
            GDALClose(ds);
            throw std::runtime_error("write_transmission_cog: cannot get band " + std::to_string(band_idx));
        }
        band->SetDescription(name);
        band->SetNoDataValue(static_cast<double>(meta.nodata));
        CPLErr err = band->RasterIO(
            GF_Write, 0, 0, w, h,
            const_cast<float*>(buffer.data()), w, h,
            GDT_Float32, 0, 0);
        if (err != CE_None) {
            GDALClose(ds);
            throw std::runtime_error("write_transmission_cog: band " + std::to_string(band_idx) + " RasterIO failed");
        }
    };

    write_band(1, b1_prev, TRANSMISSION_BAND_NAMES[0]);
    write_band(2, b2_inc,  TRANSMISSION_BAND_NAMES[1]);
    write_band(3, b3_press, TRANSMISSION_BAND_NAMES[2]);
    write_band(4, b4_focus, TRANSMISSION_BAND_NAMES[3]);

    GDALClose(ds);
}

void write_transmission_sidecar(
    const std::string& tif_path,
    const TransmissionCogMetadata& meta)
{
    nlohmann::json j;
    j["crs"]               = meta.crs;
    j["transform"]         = nlohmann::json::array();
    for (int i = 0; i < 6; ++i) {
        j["transform"].push_back(static_cast<double>(meta.transform[i]));
    }
    j["aoi_slug"]          = meta.aoi_slug;
    j["scale"]             = meta.scale;
    j["year"]              = meta.year;
    j["month"]             = meta.month;
    j["day"]               = meta.day;
    j["seed"]              = meta.seed;
    j["n_rollouts"]        = meta.n_rollouts;
    j["rollout_index"]     = meta.rollout_index;
    j["generator_version"] = meta.generator_version;
    j["contract_version"]  = meta.contract_version;
    j["band_names"]        = nlohmann::json::array();
    for (int i = 0; i < 4; ++i) {
        j["band_names"].push_back(meta.band_names[i]);
    }
    j["nodata"]            = static_cast<double>(meta.nodata);
    j["shape"]             = nlohmann::json::array({4, meta.h, meta.w});

    // Epidemiological summary
    j["total_human_population"] = meta.stats.total_humans;
    j["total_susceptible"]      = meta.stats.human_s;
    j["total_exposed"]          = meta.stats.human_e;
    j["total_infectious"]       = meta.stats.human_i;
    j["total_recovered"]        = meta.stats.human_r;
    j["total_incidence"]        = meta.stats.human_incidence;
    j["mean_prevalence"]        = meta.stats.human_prevalence;
    j["vector_susceptible"]     = meta.stats.vector_s;
    j["vector_exposed"]         = meta.stats.vector_e;
    j["vector_infectious"]      = meta.stats.vector_i;
    j["vector_total"]           = meta.stats.vector_total;
    j["total_infectious_bites"] = meta.stats.infectious_bites;
    j["total_bites_on_humans"]  = meta.stats.total_bites_on_humans;
    j["r_eff_approx"]           = meta.stats.r_eff_approx;

    const std::string sidecar_path = sidecar_path_for(tif_path);
    std::ofstream f(sidecar_path, std::ios::out | std::ios::trunc);
    if (!f.is_open()) {
        throw std::runtime_error("write_transmission_sidecar: cannot open " + sidecar_path);
    }
    f << j.dump(2) << "\n";
}

void write_transmission_log(
    const std::string& path,
    const std::vector<TransmissionDailyStats>& history,
    int32_t n_days)
{
    const std::filesystem::path p(path);
    if (p.has_parent_path()) {
        std::error_code ec;
        std::filesystem::create_directories(p.parent_path(), ec);
    }

    std::ofstream ofs(path);
    if (!ofs.is_open()) {
        throw std::runtime_error("write_transmission_log: cannot open " + path);
    }

    ofs << "{\n  \"n_days\": " << n_days << ",\n  \"daily\": [\n";
    for (size_t di = 0; di < history.size(); ++di) {
        const auto& s = history[di];
        ofs << "    {"
            << "\"day\": " << s.day
            << ", \"S_H\": " << std::fixed << std::setprecision(2) << s.human_s
            << ", \"E_H\": " << std::fixed << std::setprecision(2) << s.human_e
            << ", \"I_H\": " << std::fixed << std::setprecision(2) << s.human_i
            << ", \"R_H\": " << std::fixed << std::setprecision(2) << s.human_r
            << ", \"incidence\": " << std::fixed << std::setprecision(4) << s.human_incidence
            << ", \"prevalence\": " << std::fixed << std::setprecision(4) << s.human_prevalence
            << ", \"S_V\": " << s.vector_s
            << ", \"E_V\": " << s.vector_e
            << ", \"I_V\": " << s.vector_i
            << ", \"vector_total\": " << s.vector_total
            << ", \"infectious_bites\": " << s.infectious_bites
            << ", \"r_eff_approx\": " << std::fixed << std::setprecision(4) << s.r_eff_approx
            << "}";
        if (di + 1 < history.size()) ofs << ",";
        ofs << "\n";
    }
    ofs << "  ]\n}\n";
}

}  // namespace mal_abm_fast
