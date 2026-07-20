// SPDX-License-Identifier: MIT
// habitat_engine.cpp — read the habitat patches gpkg via OGR.
//
// The gpkg is a single-layer OGR datasource with one Point feature per
// patch. The M1.5 thin slice honours `hab_type == 'pluvial_pool'`
// only. Columns read per feature:
//
//   * `hab_type`  (string) — filter to 'pluvial_pool' (others skipped)
//   * `K`         (int32)  — carrying capacity, default = K_MAX
//   * `twi_value` (float)  — static TWI value, default = 0
//   * `row`       (int32)  — pre-computed cell row (F1.3b build_env)
//   * `col`       (int32)  — pre-computed cell col (F1.3b build_env)
//   * geometry    (Point)  — EPSG:4326 lon/lat
//
// The (row, col) columns are read when present and valid; we do not
// derive them in the thin slice (rasterio::rowcol equivalent would
// need a transform that we don't have on the gpkg side, and the gpkg
// emitted by `build_env` always carries pre-computed row/col).
#include "habitat_engine.hpp"

#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

#include "gdal.h"
#include "ogr_api.h"

namespace mal_abm_fast {

// -- internal helpers ---------------------------------------------------------

namespace {

// One-shot GDAL/OGR driver registration (idempotent; ref-counted by GDAL).
void EnsureGdalRegistered() {
    static const bool kRegistered = []() {
        GDALAllRegister();
        return true;
    }();
    (void)kRegistered;
}

// RAII wrapper for GDALDatasetH (OGR layer is owned by the dataset).
struct DatasetCloser {
    GDALDatasetH ds;
    explicit DatasetCloser(GDALDatasetH d) : ds(d) {}
    ~DatasetCloser() { if (ds) GDALClose(ds); }
    DatasetCloser(const DatasetCloser&) = delete;
    DatasetCloser& operator=(const DatasetCloser&) = delete;
};

// RAII wrapper for OGRFeatureH.
struct FeatureDestroyer {
    OGRFeatureH f;
    explicit FeatureDestroyer(OGRFeatureH x) : f(x) {}
    ~FeatureDestroyer() { if (f) OGR_F_Destroy(f); }
    FeatureDestroyer(const FeatureDestroyer&) = delete;
    FeatureDestroyer& operator=(const FeatureDestroyer&) = delete;
};

// Look up a field index on the layer definition. Returns -1 if the
// field does not exist.
int FieldIndex(OGRFeatureDefnH fdefn, const char* name) {
    if (fdefn == nullptr || name == nullptr) return -1;
    return OGR_FD_GetFieldIndex(fdefn, name);
}

// Read a string field as std::string. Returns the supplied default if
// the field is missing or its value is null.
std::string GetStringField(OGRFeatureH feat, int idx,
                           const std::string& def = std::string()) {
    if (idx < 0 || feat == nullptr) return def;
    if (OGR_F_IsFieldSetAndNotNull(feat, idx) == 0) return def;
    const char* v = OGR_F_GetFieldAsString(feat, idx);
    return (v == nullptr) ? def : std::string(v);
}

// Read an int32 field. Returns the supplied default if the field is
// missing or its value is null.
int32_t GetIntField(OGRFeatureH feat, int idx, int32_t def) {
    if (idx < 0 || feat == nullptr) return def;
    if (OGR_F_IsFieldSetAndNotNull(feat, idx) == 0) return def;
    return static_cast<int32_t>(OGR_F_GetFieldAsInteger(feat, idx));
}

// Read a double field. Returns the supplied default if the field is
// missing or its value is null.
double GetDoubleField(OGRFeatureH feat, int idx, double def) {
    if (idx < 0 || feat == nullptr) return def;
    if (OGR_F_IsFieldSetAndNotNull(feat, idx) == 0) return def;
    return OGR_F_GetFieldAsDouble(feat, idx);
}

// Read the Point X/Y as (lon, lat). Returns true on success; false if
// the geometry is missing, not a Point, or empty.
bool GetPointXY(OGRFeatureH feat, double& x, double& y) {
    if (feat == nullptr) return false;
    OGRGeometryH geom = OGR_F_GetGeometryRef(feat);
    if (geom == nullptr) return false;
    if (OGR_G_IsEmpty(geom)) return false;
    if (wkbFlatten(OGR_G_GetGeometryType(geom)) != wkbPoint) return false;
    // OGR_G_GetX / OGR_G_GetY accept an OGRGeometryH and an index;
    // for a Point, index 0 returns the (X, Y) of the only vertex.
    x = OGR_G_GetX(geom, 0);
    y = OGR_G_GetY(geom, 0);
    return true;
}

}  // namespace

// -- public API ---------------------------------------------------------------

void HabitatEngine::load_from_gpkg(const std::string& path,
                                    const AOI& aoi) {
    (void)aoi;  // The thin slice gpkg carries pre-computed row/col.
                // AOI is reserved for a future fallback path that
                // derives (row, col) from (lon, lat) when the columns
                // are missing.
    EnsureGdalRegistered();

    // Open with the vector-driver flag. The GPKG driver is one of the
    // built-in OGR vector drivers; GDALOpenEx with GDAL_OF_VECTOR
    // picks it up automatically. We disallow updates (read-only).
    GDALDatasetH raw = GDALOpenEx(
        path.c_str(),
        GDAL_OF_VECTOR | GDAL_OF_READONLY,
        nullptr, nullptr, nullptr);
    if (raw == nullptr) {
        throw std::runtime_error(
            std::string("HabitatEngine::load_from_gpkg: GDALOpenEx failed for ")
            + path + ": " + CPLGetLastErrorMsg());
    }
    DatasetCloser closer(raw);

    // We only honour a single layer; if the gpkg has more, take the
    // first one. (M1.5 emits a single layer named 'patches' or similar
    // — the field-level column lookups below are independent of the
    // layer name.)
    if (GDALDatasetGetLayerCount(raw) < 1) {
        throw std::runtime_error(
            std::string("HabitatEngine::load_from_gpkg: no layers in ") + path);
    }
    OGRLayerH layer = GDALDatasetGetLayer(raw, 0);
    if (layer == nullptr) {
        throw std::runtime_error(
            std::string("HabitatEngine::load_from_gpkg: null layer 0 in ")
            + path);
    }

    OGRFeatureDefnH fdefn = OGR_L_GetLayerDefn(layer);
    if (fdefn == nullptr) {
        throw std::runtime_error(
            std::string("HabitatEngine::load_from_gpkg: null feature defn in ")
            + path);
    }

    // Resolve field indices. `hab_type` is required (we filter on it);
    // the rest are optional with sensible defaults.
    const int hab_type_idx = FieldIndex(fdefn, "hab_type");
    const int k_idx        = FieldIndex(fdefn, "K");
    const int twi_idx      = FieldIndex(fdefn, "twi_value");
    const int row_idx      = FieldIndex(fdefn, "row");
    const int col_idx      = FieldIndex(fdefn, "col");
    if (hab_type_idx < 0) {
        // No hab_type column: every feature is treated as pluvial_pool
        // (M1 only honours that subtype anyway, and the Python loader
        // defaults hab_type to PLUVIAL_POOL if the column is absent).
    }

    patches_.clear();
    id_to_idx_.clear();

    int64_t pluvial_pool_seen = 0;
    int64_t twi_dropped       = 0;

    OGR_L_ResetReading(layer);
    for (OGRFeatureH raw_feat = OGR_L_GetNextFeature(layer);
         raw_feat != nullptr;
         raw_feat = OGR_L_GetNextFeature(layer)) {
        FeatureDestroyer feat(raw_feat);

        // Filter to hab_type == 'pluvial_pool'. If the column is
        // missing, we accept every feature (M1.5 honours only that
        // subtype, so the M1.5 gpkg without hab_type is implicitly
        // all-pools).
        if (hab_type_idx >= 0) {
            const std::string ht = GetStringField(feat.f, hab_type_idx);
            if (ht != "pluvial_pool") continue;
        }
        ++pluvial_pool_seen;

        // (lon, lat) from the Point geometry.
        double lon = 0.0, lat = 0.0;
        if (!GetPointXY(feat.f, lon, lat)) {
            // Skip features without a usable Point geometry.
            continue;
        }

        // (row, col) from explicit columns. Fall back to (0, 0) if
        // missing — the gpkg emitted by F1.3b build_env always has
        // them, so this is a defensive default only.
        const int32_t row = GetIntField(feat.f, row_idx, 0);
        const int32_t col = GetIntField(feat.f, col_idx, 0);

        // K capped at K_MAX.
        int32_t K = GetIntField(feat.f, k_idx, K_MAX);
        if (K < 0)        K = 0;
        if (K > K_MAX)    K = K_MAX;

        const float twi_value = static_cast<float>(
            GetDoubleField(feat.f, twi_idx, 0.0));

        // Build-time filter: TWI is a STATIC terrain signal
        // (Topographic Wetness Index, derived from the SRTM DEM). It
        // does not change daily. Patches with TWI <= HABITAT_MIN_TWI
        // are not viable Anopheles habitat (Kleinschmidt 2000) and
        // are dropped here, once, at habitat-engine build time. Daily
        // activation is governed separately by water_frac + rain
        // (see coordinator.cpp:to_dataframe()).
        if (twi_value <= HABITAT_MIN_TWI) {
            ++twi_dropped;
            continue;
        }

        HabitatPatch patch;
        patch.patch_id        = static_cast<int64_t>(patches_.size());
        patch.row             = row;
        patch.col             = col;
        patch.K               = K;
        patch.twi_value       = twi_value;
        patch.lon             = lon;
        patch.lat             = lat;
        patch.hab_pluvial_pool = true;

        const int64_t new_idx = static_cast<int64_t>(patches_.size());
        id_to_idx_.emplace(patch.patch_id, new_idx);
        patches_.push_back(std::move(patch));
    }

    std::cerr << "habitat_engine: dropped " << twi_dropped
              << "/" << pluvial_pool_seen
              << " patches below TWI threshold "
              << HABITAT_MIN_TWI
              << " (loaded " << patches_.size() << ")\n";
}

const HabitatPatch& HabitatEngine::patch_by_id(int64_t pid) const {
    auto it = id_to_idx_.find(pid);
    if (it == id_to_idx_.end()) {
        throw std::out_of_range(
            "HabitatEngine::patch_by_id: unknown patch_id");
    }
    return patches_[static_cast<size_t>(it->second)];
}

std::vector<float> HabitatEngine::get_twi_grid(const AOI& aoi) const {
    if (twi_provider_) return twi_provider_(aoi);
    return {};
}

}  // namespace mal_abm_fast
