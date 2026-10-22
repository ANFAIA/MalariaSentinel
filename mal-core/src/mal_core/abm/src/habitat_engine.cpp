// SPDX-License-Identifier: MIT
// habitat_engine.cpp — read the habitat patches gpkg via OGR.
//
// The gpkg is a single-layer OGR datasource with one Point feature per
// patch. The loader accepts both `hab_type == 'pluvial_pool'` and
// `hab_type == 'permanent_water'`; the subtype is captured in the
// `is_permanent` flag. Columns read per feature:
//
//   * `hab_type`    (string) — habitat type label (v3.0: dominant
//                habitat type, e.g. 'wetland_pluvial'); legacy values
//                'pluvial_pool'/'permanent_water' still parse as strings
//   * `row`         (int32)  — pre-computed cell row (F1.3b build_env)
//   * `col`         (int32)  — pre-computed cell col (F1.3b build_env)
//   * geometry      (Point)  — EPSG:4326 lon/lat
//
// Legacy columns `is_permanent`, `K` and `twi_value` are NOT read:
// per-cell capacity K is recomputed every day by the coordinator
// (k_habitat; contract 3.0/4.0), and TWI was retired with the pool
// model.
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

    // Resolve field indices. All fields are optional with sensible
    // defaults; the loader is contract-tolerant.
    const int hab_type_idx = FieldIndex(fdefn, "hab_type");
    const int potential_idx = FieldIndex(fdefn, "habitat_potential");
    const int dynamics_idx = FieldIndex(fdefn, "dynamics");
    const int row_idx      = FieldIndex(fdefn, "row");
    const int col_idx      = FieldIndex(fdefn, "col");
    if (hab_type_idx < 0) {
        // No hab_type column: every feature is treated as a candidate
        // habitat patch (the ingest gpkg defaults hab_type to its
        // dominant type when the column is absent).
    }

    patches_.clear();
    id_to_idx_.clear();

    int64_t candidate_seen = 0;
    int64_t candidate_dropped = 0;

    OGR_L_ResetReading(layer);
    for (OGRFeatureH raw_feat = OGR_L_GetNextFeature(layer);
         raw_feat != nullptr;
         raw_feat = OGR_L_GetNextFeature(layer)) {
        FeatureDestroyer feat(raw_feat);

        // Accept any feature: the contract no longer filters by
        // hab_type (patch viability is potential-based).
        (void)hab_type_idx;
        ++candidate_seen;

        // (lon, lat) from the Point geometry.
        double lon = 0.0, lat = 0.0;
        if (!GetPointXY(feat.f, lon, lat)) {
            // Skip features without a usable Point geometry.
            continue;
        }

        // (row, col) from explicit columns. Fall back to (0, 0) if
        // missing — the gpkg emitted by ingest/env.py always has
        // them, so this is a defensive default only.
        const int32_t row = GetIntField(feat.f, row_idx, 0);
        const int32_t col = GetIntField(feat.f, col_idx, 0);

        // Static potential amplitude H_total in [0, 1]. Defaults to
        // the full cell (a hand-written gpkg without a potential
        // column is a valid habitat source at 1.0).
        float potential = static_cast<float>(
            GetDoubleField(feat.f, potential_idx, 1.0));
        potential = std::clamp(potential, 0.0f, 1.0f);
        // Candidate floor (engineering constant; plan §8). Dropped
        // patches are the negative case of the ingest census.
        if (potential < habitat_candidate_min_engine()) {
            ++candidate_dropped;
            continue;
        }
        const int dynamics = GetIntField(feat.f, dynamics_idx, 0);

        HabitatPatch patch;
        patch.patch_id        = static_cast<int64_t>(patches_.size());
        patch.row             = row;
        patch.col             = col;
        patch.potential       = potential;
        patch.lon             = lon;
        patch.lat             = lat;
        patch.dynamics       = dynamics;

        const int64_t new_idx = static_cast<int64_t>(patches_.size());
        id_to_idx_.emplace(patch.patch_id, new_idx);
        patches_.push_back(std::move(patch));
    }

    std::cerr << "habitat_engine: loaded " << patches_.size() << " of "
              << candidate_seen << " candidate patches (dropped "
              << candidate_dropped << " below the "
              << habitat_candidate_min_engine() << " candidate floor)\n";
}

const HabitatPatch& HabitatEngine::patch_by_id(int64_t pid) const {
    auto it = id_to_idx_.find(pid);
    if (it == id_to_idx_.end()) {
        throw std::out_of_range(
            "HabitatEngine::patch_by_id: unknown patch_id");
    }
    return patches_[static_cast<size_t>(it->second)];
}

}  // namespace mal_abm_fast
