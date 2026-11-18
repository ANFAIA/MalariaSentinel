// SPDX-License-Identifier: MIT
// seeding.cpp — detection-based initial seeding implementation.
//
// Three modes:
//
//   * UNIFORM: emit zero instructions. The submodel seeds the
//              SeedingConfig explicit per-patch counts in every
//              candidate patch (via build_uniform_seed_instructions).
//   * RANDOM_VIABLE: pick N random patch_ids from `viable_patch_ids`,
//              where each chosen patch receives
//              `n_adults_per_detection` adults (ready to disperse)
//              and `n_larvae_per_detection` larvae (need EIP).
//   * EXPLICIT: for each user-supplied DetectionPoint, find the
//              nearest viable patch within `detection_radius_km`
//              (Euclidean metric on lon/lat — a proper geodesic
//              metric is a future improvement). If no patch is
//              within radius, the point is silently dropped.
//
// Distance is computed in degrees (Euclidean on the (lon, lat)
// grid). The Ghana regional AOI spans a few degrees, so the degree
// conversion is coarse but stable: the km radius is divided by the
// geodesy metres-per-degree accessor. This is a coarse approximation
// but adequate for "snap a village to the nearest patch".
#include "mal_abm_fast/seeding.hpp"

#include <array>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <set>
#include <stdexcept>
#include <vector>

#include <nlohmann/json.hpp>

namespace mal_abm_fast {

namespace {

// Flat-tangent-plane degree conversion: latitude uses the local
// km-per-degree factor; longitude varies with latitude (cos(lat)).
// The combined factors keep the squared-distance formula isotropic
// in the AOI's local tangent plane.
constexpr double kKmPerDegLat = 111.32;

inline double km_per_deg_lon(double lat_deg) {
    return kKmPerDegLat * std::cos(lat_deg * (3.14159265358979323846 / 180.0));
}

// Approximate distance in km between two (lon, lat) points using
// a simple equirectangular projection. Good enough for snapping
// a user detection to the nearest habitat patch on a regional
// AOI; not suitable for continental or polar scales.
inline double haversine_km(double lon1, double lat1,
                           double lon2, double lat2) {
    // Use the equirectangular approximation since the radius is
    // small (a few km). Convert to km: dlon * km_per_deg_lon at
    // the midpoint latitude, dlat * km_per_deg_lat.
    const double mid_lat = 0.5 * (lat1 + lat2);
    const double dlon_km = (lon1 - lon2) * km_per_deg_lon(mid_lat);
    const double dlat_km = (lat1 - lat2) * kKmPerDegLat;
    return std::sqrt(dlon_km * dlon_km + dlat_km * dlat_km);
}

// Find the index (into `viable_patch_ids`) of the nearest patch
// to (lon, lat) within `radius_km`. Returns -1 if no patch is
// within radius. Operates on the parallel arrays directly to
// avoid a hashmap allocation.
inline int32_t find_nearest_patch(
    double lon, double lat, double radius_km,
    const std::vector<int32_t>& viable_patch_ids,
    const std::vector<std::array<double, 2>>& patch_lonlat) {
    int32_t best_idx = -1;
    double  best_dist = radius_km;
    for (size_t i = 0; i < viable_patch_ids.size(); ++i) {
        const double plon = patch_lonlat[i][0];
        const double plat = patch_lonlat[i][1];
        const double d = haversine_km(lon, lat, plon, plat);
        if (d <= best_dist) {
            best_dist = d;
            best_idx = static_cast<int32_t>(i);
        }
    }
    return best_idx;
}

}  // namespace

std::vector<SeedInstruction> build_seed_instructions_host_weighted(
    const SeedingConfig& config,
    const std::vector<int32_t>& viable_patch_ids,
    const std::vector<std::array<double, 2>>& patch_lonlat,
    const std::vector<std::array<int32_t, 2>>& patch_rowcol,
    const std::vector<float>& cell_host_score,
    int32_t grid_h,
    int32_t grid_w,
    float cell_size_m,
    Prng& rng) {
    std::vector<SeedInstruction> out;
    const size_t n_patches = viable_patch_ids.size();
    if (n_patches == 0 || cell_host_score.empty() ||
        grid_h <= 0 || grid_w <= 0 || !(cell_size_m > 0.0f)) {
        return out;
    }
    if (cell_host_score.size() !=
        static_cast<size_t>(grid_h) * static_cast<size_t>(grid_w)) {
        throw std::runtime_error(
            "build_seed_instructions_host_weighted: cell_host_score size "
            "does not match grid dimensions");
    }

    // -- 1. Per-patch weight: Σ nearby host score with Gaussian decay ---
    // Mirrors HostSeekingModel::cell_attraction's distance kernel
    // (exp(-dist/scale)) but sums host density rather than a single
    // target cell: patches surrounded by preferred hosts weigh most.
    const double scale_m = static_cast<double>(config.host_seeking_scale_m);
    if (!(scale_m > 0.0)) {
        throw std::invalid_argument(
            "build_seed_instructions: host_seeking_scale_m not injected by "
            "the engine (no default: model_constants.yaml species.<name>."
            "host_seeking_scale_m is the single source; review-a3 P1-4)");
    }
    const double radius_km = std::max(0.05, config.host_weight_radius_km);
    const int32_t search_cells = static_cast<int32_t>(
        std::ceil(radius_km * 1000.0 / static_cast<double>(cell_size_m)));
    const double radius_m = radius_km * 1000.0;

    std::vector<double> weights(n_patches, 0.0);
    for (size_t i = 0; i < n_patches; ++i) {
        const int32_t pr = patch_rowcol[i][0];
        const int32_t pc = patch_rowcol[i][1];
        if (pr < 0 || pr >= grid_h || pc < 0 || pc >= grid_w) continue;
        const int32_t r_min = std::max(0, pr - search_cells);
        const int32_t r_max = std::min(grid_h - 1, pr + search_cells);
        const int32_t c_min = std::max(0, pc - search_cells);
        const int32_t c_max = std::min(grid_w - 1, pc + search_cells);
        double w = 0.0;
        for (int32_t r = r_min; r <= r_max; ++r) {
            const double dy = (static_cast<double>(r) - static_cast<double>(pr))
                * static_cast<double>(cell_size_m);
            for (int32_t c = c_min; c <= c_max; ++c) {
                const double dx = (static_cast<double>(c) - static_cast<double>(pc))
                    * static_cast<double>(cell_size_m);
                const double dist_m = std::sqrt(dx * dx + dy * dy);
                if (dist_m > radius_m) continue;
                const float score = cell_host_score[static_cast<size_t>(r) *
                    static_cast<size_t>(grid_w) + static_cast<size_t>(c)];
                if (score <= 0.0f) continue;
                w += static_cast<double>(score) * std::exp(-dist_m / scale_m);
            }
        }
        weights[i] = w;
    }

    double total = 0.0;
    for (const double w : weights) total += w;
    if (total <= 0.0) {
        std::cerr << "seeding: host-weighted mode found no hosts within "
                  << radius_km << " km of any viable patch; nothing seeded\n";
        return out;
    }

    // -- 2. Weighted sampling without replacement (roulette w/ removal) --
    std::vector<double> remaining = weights;
    const int32_t n = std::min<int32_t>(
        config.n_detections, static_cast<int32_t>(n_patches));
    out.reserve(static_cast<size_t>(n));
    for (int32_t k = 0; k < n; ++k) {
        double tot = 0.0;
        for (const double w : remaining) tot += w;
        if (tot <= 0.0) break;
        const double draw = rng.uniform_double() * tot;
        size_t chosen = n_patches;
        double cum = 0.0;
        for (size_t i = 0; i < n_patches; ++i) {
            cum += remaining[i];
            if (cum >= draw) { chosen = i; break; }
        }
        if (chosen == n_patches) {
            // Floating-point edge: fall back to the last non-zero patch.
            for (size_t i = n_patches; i-- > 0;) {
                if (remaining[i] > 0.0) { chosen = i; break; }
            }
            if (chosen == n_patches) break;
        }
        SeedInstruction inst;
        inst.patch_id = viable_patch_ids[chosen];
        inst.row      = patch_rowcol[chosen][0];
        inst.col      = patch_rowcol[chosen][1];
        inst.lon      = patch_lonlat[chosen][0];
        inst.lat      = patch_lonlat[chosen][1];
        inst.n_adults = config.n_adults_per_detection;
        inst.n_larvae = config.n_larvae_per_detection;
        out.push_back(inst);
        remaining[chosen] = 0.0;  // removal: spread across distinct patches
    }
    return out;
}

std::vector<SeedInstruction> build_seed_instructions_for_patches(
    const SeedingConfig& config,
    const std::vector<int32_t>& viable_patch_ids,
    const std::vector<std::array<double, 2>>& patch_lonlat,
    const std::vector<std::array<int32_t, 2>>& patch_rowcol,
    Prng& rng) {
    std::vector<SeedInstruction> out;

    switch (config.mode) {
        case SeedingMode::UNIFORM:
            // UNIFORM instructions are built by
            // CoordinatorModel::build_uniform_seed_instructions (the
            // day-0 patch union). No instructions here.
            return out;

        case SeedingMode::RANDOM_VIABLE: {
            if (viable_patch_ids.empty()) return out;
            if (patch_lonlat.size() != viable_patch_ids.size() ||
                patch_rowcol.size() != viable_patch_ids.size()) {
                throw std::runtime_error(
                    "build_seed_instructions: viable_patch_ids / patch_lonlat / "
                    "patch_rowcol size mismatch");
            }
            const int32_t n = std::min<int32_t>(
                config.n_detections,
                static_cast<int32_t>(viable_patch_ids.size()));
            if (n <= 0) return out;

            // Sample without replacement using a Fisher-Yates
            // partial shuffle on the first `n` slots. The Prng
            // stream is consumed in `n + (n_patches - n)` draws so
            // two calls with the same seed produce the same
            // selection.
            const int32_t nv = static_cast<int32_t>(viable_patch_ids.size());
            std::vector<int32_t> idx(static_cast<size_t>(nv));
            for (int32_t i = 0; i < nv; ++i) idx[static_cast<size_t>(i)] = i;
            for (int32_t i = 0; i < n; ++i) {
                const int32_t j = i + static_cast<int32_t>(
                    rng.uniform_double() * static_cast<double>(nv - i));
                if (j != i) {
                    std::swap(idx[static_cast<size_t>(i)],
                              idx[static_cast<size_t>(j)]);
                }
            }

            out.reserve(static_cast<size_t>(n));
            for (int32_t k = 0; k < n; ++k) {
                const int32_t i = idx[static_cast<size_t>(k)];
                SeedInstruction inst;
                inst.patch_id = viable_patch_ids[static_cast<size_t>(i)];
                inst.row      = patch_rowcol[static_cast<size_t>(i)][0];
                inst.col      = patch_rowcol[static_cast<size_t>(i)][1];
                inst.lon      = patch_lonlat[static_cast<size_t>(i)][0];
                inst.lat      = patch_lonlat[static_cast<size_t>(i)][1];
                inst.n_adults = config.n_adults_per_detection;
                inst.n_larvae = config.n_larvae_per_detection;
                out.push_back(inst);
            }
            return out;
        }

        case SeedingMode::EXPLICIT: {
            if (config.detections.empty()) return out;
            if (viable_patch_ids.empty()) return out;
            if (patch_lonlat.size() != viable_patch_ids.size() ||
                patch_rowcol.size() != viable_patch_ids.size()) {
                throw std::runtime_error(
                    "build_seed_instructions: viable_patch_ids / patch_lonlat / "
                    "patch_rowcol size mismatch");
            }
            out.reserve(config.detections.size());
            for (const auto& det : config.detections) {
                const int32_t idx = find_nearest_patch(
                    det.lon, det.lat, config.detection_radius_km,
                    viable_patch_ids, patch_lonlat);
                if (idx < 0) continue;  // no patch within radius
                SeedInstruction inst;
                inst.patch_id = viable_patch_ids[static_cast<size_t>(idx)];
                inst.row      = patch_rowcol[static_cast<size_t>(idx)][0];
                inst.col      = patch_rowcol[static_cast<size_t>(idx)][1];
                inst.lon      = patch_lonlat[static_cast<size_t>(idx)][0];
                inst.lat      = patch_lonlat[static_cast<size_t>(idx)][1];
                inst.n_adults = det.n_adults > 0
                    ? det.n_adults
                    : config.n_adults_per_detection;
                inst.n_larvae = det.n_larvae > 0
                    ? det.n_larvae
                    : config.n_larvae_per_detection;
                out.push_back(inst);
            }
            return out;
        }
    }
    return out;
}


// ---------------------------------------------------------------------------
// Scenario JSON loader (plan 13.2 / 13.3.1). Strict: every key is checked
// against an allow-list, so a typo fails loudly instead of seeding nothing.
// ---------------------------------------------------------------------------

namespace {

using Json = nlohmann::json;

[[noreturn]] void scenario_fail(const std::string& path,
                                const std::string& where,
                                const std::string& what) {
    throw std::runtime_error("scenario '" + path + "': " + where + ": " + what);
}

void check_keys(const Json& obj, const std::set<std::string>& allowed,
                const std::string& path, const std::string& where) {
    if (!obj.is_object()) scenario_fail(path, where, "must be a JSON object");
    for (auto it = obj.begin(); it != obj.end(); ++it) {
        if (allowed.count(it.key()) == 0) {
            scenario_fail(path, where + "." + it.key(), "unknown key");
        }
    }
}

double number_field(const Json& obj, const char* key, const std::string& path,
                    const std::string& where) {
    if (!obj.contains(key) || !obj.at(key).is_number()) {
        scenario_fail(path, where + "." + key, "required number");
    }
    return obj.at(key).get<double>();
}

double optional_number(const Json& obj, const char* key, double fallback,
                       const std::string& path, const std::string& where) {
    if (!obj.contains(key)) return fallback;
    if (!obj.at(key).is_number()) {
        scenario_fail(path, where + "." + key, "must be a number");
    }
    return obj.at(key).get<double>();
}

GonotrophicState parse_state(const std::string& name, const std::string& path,
                             const std::string& where) {
    if (name == "TENERAL")  return GonotrophicState::TENERAL;
    if (name == "HOST_SEEKING") return GonotrophicState::HOST_SEEKING;
    if (name == "BLOOD_FED") return GonotrophicState::BLOOD_FED;
    if (name == "RESTING")  return GonotrophicState::RESTING;
    if (name == "GRAVID")   return GonotrophicState::GRAVID;
    scenario_fail(path, where,
                  "unsupported agent state '" + name +
                  "' (expected TENERAL, HOST_SEEKING, BLOOD_FED, RESTING or GRAVID)");
}

// Stage names: EGG, L1..L4 (LARVA with instar), PUPA.
void parse_stage(const std::string& name, const std::string& path,
                 const std::string& where, AquaticStage& stage, uint8_t& instar) {
    if (name == "EGG")  { stage = AquaticStage::EGG;  instar = 0; return; }
    if (name == "PUPA") { stage = AquaticStage::PUPA; instar = 0; return; }
    if (name.size() == 2 && name[0] == 'L' && name[1] >= '1' && name[1] <= '4') {
        stage = AquaticStage::LARVA;
        instar = static_cast<uint8_t>(name[1] - '0');
        return;
    }
    scenario_fail(path, where,
                  "unsupported stage '" + name + "' (expected EGG, L1..L4, PUPA)");
}

}  // namespace

ScenarioSpec load_scenario_spec(const std::string& path) {
    std::ifstream in(path);
    if (!in) throw std::runtime_error("scenario: cannot open '" + path + "'");
    Json root;
    try {
        root = Json::parse(in);
    } catch (const std::exception& e) {
        throw std::runtime_error("scenario '" + path + "': invalid JSON: " + e.what());
    }
    check_keys(root,
               {"id", "mode", "seed", "days", "agents", "aquatic", "humans",
                "livestock", "overrides", "variants", "expectations"},
               path, "$");

    ScenarioSpec spec;
    if (!root.contains("id") || !root.at("id").is_string()) {
        scenario_fail(path, "$.id", "required string");
    }
    spec.id = root.at("id").get<std::string>();

    spec.mode = root.contains("mode") ? root.at("mode").get<std::string>() : "report";
    if (spec.mode != "gate" && spec.mode != "report") {
        scenario_fail(path, "$.mode", "must be 'gate' or 'report'");
    }

    if (!root.contains("seed") || !root.at("seed").is_number_unsigned()) {
        scenario_fail(path, "$.seed", "required non-negative integer");
    }
    spec.seed = root.at("seed").get<uint64_t>();

    const double days = number_field(root, "days", path, "$");
    if (days < 1.0 || days != static_cast<double>(static_cast<int32_t>(days))) {
        scenario_fail(path, "$.days", "must be an integer >= 1");
    }
    spec.days = static_cast<int32_t>(days);

    // `variants` are expanded by the harness into one file per variant; the
    // engine never receives a file that still declares them.
    if (root.contains("variants") && !root.at("variants").empty()) {
        scenario_fail(path, "$.variants",
                      "variants must be expanded by the harness before the engine runs");
    }

    // -- agents (required, may be empty) -----------------------------------
    if (!root.contains("agents") || !root.at("agents").is_array()) {
        scenario_fail(path, "$.agents", "required array");
    }
    for (size_t i = 0; i < root.at("agents").size(); ++i) {
        const std::string where = "$.agents[" + std::to_string(i) + "]";
        const Json& a = root.at("agents")[i];
        check_keys(a, {"x", "y", "sex", "state", "age_days", "infective"}, path, where);
        ScenarioAgent ag;
        ag.x = number_field(a, "x", path, where);
        ag.y = number_field(a, "y", path, where);
        if (!a.contains("sex") || !a.at("sex").is_string()) {
            scenario_fail(path, where + ".sex", "required 'MALE' or 'FEMALE'");
        }
        const std::string sex = a.at("sex").get<std::string>();
        if (sex == "MALE") ag.sex = AdultSex::MALE;
        else if (sex == "FEMALE") ag.sex = AdultSex::FEMALE;
        else scenario_fail(path, where + ".sex", "must be 'MALE' or 'FEMALE'");
        if (a.contains("state")) {
            ag.state = parse_state(a.at("state").get<std::string>(), path, where + ".state");
        }
        ag.age_days = static_cast<int32_t>(
            optional_number(a, "age_days", 0.0, path, where));
        if (a.contains("infective")) {
            if (!a.at("infective").is_boolean()) {
                scenario_fail(path, where + ".infective", "must be a boolean");
            }
            ag.infective = a.at("infective").get<bool>();
        }
        spec.agents.push_back(ag);
    }

    // -- aquatic cohorts ----------------------------------------------------
    if (root.contains("aquatic")) {
        for (size_t i = 0; i < root.at("aquatic").size(); ++i) {
            const std::string where = "$.aquatic[" + std::to_string(i) + "]";
            const Json& c = root.at("aquatic")[i];
            check_keys(c, {"x", "y", "cell_id", "stage", "instar", "development", "count"},
                       path, where);
            ScenarioAquatic aq;
            aq.x = number_field(c, "x", path, where);
            aq.y = number_field(c, "y", path, where);
            aq.cell_id = static_cast<int64_t>(number_field(c, "cell_id", path, where));
            if (!c.contains("stage") || !c.at("stage").is_string()) {
                scenario_fail(path, where + ".stage", "required string");
            }
            parse_stage(c.at("stage").get<std::string>(), path, where + ".stage",
                        aq.stage, aq.instar);
            if (c.contains("instar") &&
                static_cast<int>(c.at("instar").get<double>()) != aq.instar) {
                scenario_fail(path, where + ".instar",
                              "disagrees with stage (L1..L4 fix the instar)");
            }
            aq.development = static_cast<float>(
                optional_number(c, "development", 0.0, path, where));
            if (aq.development < 0.0f || aq.development > 1.0f) {
                scenario_fail(path, where + ".development", "must lie in [0, 1]");
            }
            const double count = number_field(c, "count", path, where);
            if (count < 0.0 || count != static_cast<double>(static_cast<int64_t>(count))) {
                scenario_fail(path, where + ".count", "must be a non-negative integer");
            }
            aq.count = static_cast<int64_t>(count);
            spec.aquatic.push_back(aq);
        }
    }

    // -- humans (declared now, seeded by Paso 2) ---------------------------
    if (root.contains("humans")) {
        for (size_t i = 0; i < root.at("humans").size(); ++i) {
            const std::string where = "$.humans[" + std::to_string(i) + "]";
            const Json& h = root.at("humans")[i];
            check_keys(h, {"x", "y", "state", "timer"}, path, where);
            ScenarioHuman hu;
            hu.x = number_field(h, "x", path, where);
            hu.y = number_field(h, "y", path, where);
            if (h.contains("state")) hu.state = h.at("state").get<std::string>();
            if (hu.state != "SUSCEPTIBLE" && hu.state != "EXPOSED" &&
                hu.state != "INFECTIOUS" && hu.state != "RECOVERED") {
                scenario_fail(path, where + ".state",
                              "must be SUSCEPTIBLE, EXPOSED, INFECTIOUS or RECOVERED");
            }
            hu.timer_days = optional_number(h, "timer", 0.0, path, where);
            spec.humans.push_back(hu);
        }
    }

    // -- livestock (declared now, seeded later) ----------------------------
    if (root.contains("livestock")) {
        for (size_t i = 0; i < root.at("livestock").size(); ++i) {
            const std::string where = "$.livestock[" + std::to_string(i) + "]";
            const Json& l = root.at("livestock")[i];
            check_keys(l, {"x", "y", "species"}, path, where);
            ScenarioLivestock ls;
            ls.x = number_field(l, "x", path, where);
            ls.y = number_field(l, "y", path, where);
            if (l.contains("species")) ls.species = l.at("species").get<std::string>();
            spec.livestock.push_back(ls);
        }
    }

    // -- overrides: applied from Paso 5; until then a non-empty map is an
    // error, never a silent no-op (a sensitivity band would otherwise run
    // with the canonical value and look like a pass).
    if (root.contains("overrides") && !root.at("overrides").empty()) {
        if (!root.at("overrides").is_object()) {
            scenario_fail(path, "$.overrides", "must be an object");
        }
        scenario_fail(path, "$.overrides",
                      "overrides are not applied before Paso 5; must be empty");
    }
    return spec;
}

}  // namespace mal_abm_fast
