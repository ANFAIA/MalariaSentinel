// SPDX-License-Identifier: MIT
// config.cc — YAML-subset micro-parser + ModelConfig loader (plan §4).
// No yaml-cpp: engine deps stay find_package. Schema and business
// invariants are validated ONCE in mal_core/config_validation.py (R2);
// this parser only enforces syntax and reports missing key access.
//
// Supported subset (exactly what model_constants.yaml needs):
//   * top-level `key:` sections, nested `key:` blocks by 2-space indent
//   * scalars: int, float, bare string, "quoted string"
//   * inline flow list  [a, b, c]   and flow map  {k: v, k2: v2}
//   * full-line comments and trailing `#` comments
// Rejected (loud, with line numbers): tab indentation, duplicate keys,
// YAML anchors/multi-line literals (`&x`, `|`, `>`), NaN/inf values.
#include "mal_abm_fast/config.hpp"

#include <algorithm>
#include <cctype>
#include <cmath>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <sstream>

#include <nlohmann/json.hpp>

#ifdef _WIN32
#include <windows.h>
#elif defined(__APPLE__)
#include <mach-o/dyld.h>
#else
#include <limits.h>
#include <unistd.h>
#endif
#include <cstring>

namespace mal_abm_fast {

// ---------------------------------------------------------------------------
// Mini YAML-subset parser
// ---------------------------------------------------------------------------

namespace {

struct YNode {
    enum class Kind { Scalar, Map, List };
    Kind kind = Kind::Scalar;
    std::string scalar;
    bool quoted = false;
    // map/list keep (parsed child); list items are scalars in this subset.
    std::map<std::string, YNode> map;
    std::vector<YNode> list;
    int line = 0;
};

struct Line {
    int number;
    int indent;
    std::string key;   // empty for a bare list item (unused)
    std::string rest;  // text after 'key:' (may be empty)
};

std::string strip_quotes(std::string s) {
    if (s.size() >= 2 && (s.front() == '"' || s.front() == '\'') &&
        s.back() == s.front()) {
        s = s.substr(1, s.size() - 2);
    }
    return s;
}

std::string trim(const std::string& s) {
    size_t a = 0, b = s.size();
    while (a < b && std::isspace(static_cast<unsigned char>(s[a]))) ++a;
    while (b > a && std::isspace(static_cast<unsigned char>(s[b - 1]))) --b;
    return s.substr(a, b - a);
}

// Net bracket depth of a (comment-stripped) line, honouring quotes.
int bracket_depth(const std::string& s);

// Strip a comment honouring single/double quotes.
std::string strip_comment(const std::string& raw, int line_no) {
    bool in_s = false, in_d = false;
    for (size_t i = 0; i < raw.size(); ++i) {
        const char c = raw[i];
        if (c == '\'' && !in_d) in_s = !in_s;
        else if (c == '"' && !in_s) in_d = !in_d;
        else if (c == '#' && !in_s && !in_d) {
            if (raw.find("&") == 0)
                throw ConfigError("config parse error line " +
                                  std::to_string(line_no) +
                                  ": YAML anchors are not supported");
            if (i > 0 && (raw[i - 1] == '|' || raw[i - 1] == '>'))
                throw ConfigError("config parse error line " +
                                  std::to_string(line_no) +
                                  ": block literals are not supported");
            return raw.substr(0, i);
        }
    }
    return raw;
}

std::vector<Line> scan_lines(const std::string& path) {
    std::ifstream fh(path);
    if (!fh) throw ConfigError("cannot open model constants file: " + path);
    std::vector<Line> lines;
    std::string raw;
    int n = 0;
    while (std::getline(fh, raw)) {
        ++n;
        if (raw.find('\t') != std::string::npos) {
            throw ConfigError("config parse error line " + std::to_string(n) +
                              ": tab indentation is not allowed");
        }
        const std::string first = trim(strip_comment(raw, n));
        if (first.empty()) continue;
        if (first.front() == '&' || first.front() == '*' ||
            first.front() == '|' || first.front() == '>') {
            throw ConfigError("config parse error line " + std::to_string(n) +
                              ": YAML anchors/blocks are not supported");
        }
        // Bracket continuation: an inline list/map may wrap to following
        // lines (e.g. habitat_types.types). Accumulate until balanced.
        std::string content = first;
        if (bracket_depth(content) > 0) {
            std::string more;
            while (bracket_depth(content) > 0 && std::getline(fh, more)) {
                ++n;
                if (more.find('\t') != std::string::npos) {
                    throw ConfigError("config parse error line " +
                                      std::to_string(n) +
                                      ": tab indentation is not allowed");
                }
                const std::string add = trim(strip_comment(more, n));
                if (add.empty()) continue;
                content += " " + add;
            }
        }
        int indent = 0;
        while (indent < static_cast<int>(raw.size()) &&
               raw[static_cast<size_t>(indent)] == ' ')
            ++indent;
        Line line;
        line.number = n;
        line.indent = indent;
        const size_t colon = content.find(':');
        if (colon == std::string::npos) {
            throw ConfigError("config parse error line " + std::to_string(n) +
                              ": expected 'key: value' or 'key:' (" + content +
                              ")");
        }
        line.key = trim(content.substr(0, colon));
        line.rest = trim(content.substr(colon + 1));
        lines.push_back(line);
    }
    return lines;
}



// Net bracket depth of a (comment-stripped) line, honouring quotes.
int bracket_depth(const std::string& s) {
    int depth = 0;
    bool in_s = false, in_d = false;
    for (const char c : s) {
        if (c == '\'' && !in_d) in_s = !in_s;
        else if (c == '"' && !in_s) in_d = !in_d;
        else if (!in_s && !in_d) {
            if (c == '[' || c == '{') ++depth;
            if (c == ']' || c == '}') --depth;
        }
    }
    return depth;
}


double parse_scalar_double(const std::string& raw, int line_no) {
    const std::string s = strip_quotes(trim(raw));
    try {
        size_t consumed = 0;
        const double v = std::stod(s, &consumed);
        if (consumed != s.size() || !std::isfinite(v)) {
            throw std::invalid_argument("bad");
        }
        return v;
    } catch (const std::exception&) {
        throw ConfigError("config parse error line " + std::to_string(line_no) +
                          ": numeric value expected, got '" + s + "'");
    }
}

int parse_scalar_int(const std::string& raw, int line_no) {
    const std::string s = strip_quotes(trim(raw));
    try {
        size_t consumed = 0;
        const double d = std::stod(s, &consumed);
        if (consumed != s.size() || !std::isfinite(d) ||
            std::fabs(d - std::llround(d)) > 1e-12) {
            throw std::invalid_argument("bad");
        }
        return static_cast<int>(std::llround(d));
    } catch (const std::exception&) {
        throw ConfigError("config parse error line " + std::to_string(line_no) +
                          ": integer value expected, got '" + s + "'");
    }
}

std::vector<std::string> parse_flow_list(const std::string& raw, int line_no) {
    if (raw.front() != '[' || raw.back() != ']') {
        throw ConfigError("config parse error line " + std::to_string(line_no) +
                          ": inline list expected, got '" + raw + "'");
    }
    std::vector<std::string> out;
    std::string item;
    int depth = 0;
    bool quoted = false;
    char q = 0;
    for (const char c : raw.substr(1, raw.size() - 2)) {
        if (quoted) {
            item += (c == q) ? (quoted = false, ' ') : c;
            continue;
        }
        if (c == '"' || c == '\'') { quoted = true; q = c; continue; }
        if (c == '[' || c == '{') ++depth;
        if (c == ']' || c == '}') --depth;
        if (c == ',' && depth == 0) {
            out.push_back(strip_quotes(trim(item)));
            item.clear();
        } else {
            item += c;
        }
    }
    out.push_back(strip_quotes(trim(item)));
    return out;
}

std::map<std::string, std::string> parse_flow_map(const std::string& raw,
                                                  int line_no) {
    if (raw.front() != '{' || raw.back() != '}') {
        throw ConfigError("config parse error line " + std::to_string(line_no) +
                          ": inline map expected, got '" + raw + "'");
    }
    std::map<std::string, std::string> out;
    std::string item;
    int depth = 0;
    bool quoted = false;
    char q = 0;
    const std::string inner = raw.substr(1, raw.size() - 2);
    for (size_t i = 0; i <= inner.size(); ++i) {
        const bool end = i == inner.size();
        const char c = end ? ',' : inner[i];
        if (!end && !quoted) {
            if (c == '"' || c == '\'') { quoted = true; q = c; }
            if (c == '[' || c == '{') ++depth;
            if (c == ']' || c == '}') --depth;
        }
        if (!end && (c != ',' || depth != 0 || quoted)) {
            item += c;
            continue;
        }
        const size_t colon = item.find(':');
        if (colon == std::string::npos) {
            throw ConfigError("config parse error line " +
                              std::to_string(line_no) +
                              ": inline map item without ':' ('" + item + "')");
        }
        out[strip_quotes(trim(item.substr(0, colon)))] =
            trim(item.substr(colon + 1));
        item.clear();
        if (!end) continue;
    }
    return out;
}

bool starts_inline_container(const std::string& rest) {
    return !rest.empty() && (rest.front() == '{' || rest.front() == '[');
}

YNode parse_block(const std::vector<Line>& lines, size_t& cursor, int indent);

YNode parse_scalar_node(Line line) {
    YNode node;
    node.line = line.number;
    const std::string rest = line.rest;
    if (starts_inline_container(rest)) {
        if ((rest.front() == '{' && rest.back() != '}') ||
            (rest.front() == '[' && rest.back() != ']')) {
            throw ConfigError("config parse error line " +
                              std::to_string(line.number) +
                              ": unterminated inline container");
        }
        if (rest.front() == '{') {
            node.kind = YNode::Kind::Map;
            for (const auto& kv : parse_flow_map(rest, line.number)) {
                YNode child;
                child.kind = YNode::Kind::Scalar;
                child.scalar = kv.second;
                child.line = line.number;
                node.map[kv.first] = child;
            }
        } else {
            node.kind = YNode::Kind::List;
            for (const auto& item : parse_flow_list(rest, line.number)) {
                YNode child;
                child.kind = YNode::Kind::Scalar;
                child.scalar = item;
                child.line = line.number;
                node.list.push_back(child);
            }
        }
        return node;
    }
    node.kind = YNode::Kind::Scalar;
    node.scalar = rest;
    node.quoted = rest.size() >= 2 &&
                  (rest.front() == '"' || rest.front() == '\'');
    return node;
}

YNode parse_block(const std::vector<Line>& lines, size_t& cursor,
                  const int indent) {
    YNode node;
    node.kind = YNode::Kind::Map;
    bool first = true;
    int child_indent = -1;
    while (cursor < lines.size()) {
        const Line line = lines[cursor];
        if (line.indent < indent) break;
        if (first) { child_indent = line.indent; first = false; }
        if (line.indent > child_indent) {
            throw ConfigError("config parse error line " +
                              std::to_string(line.number) +
                              ": unexpected extra indentation");
        }
        ++cursor;
        if (node.map.count(line.key)) {
            throw ConfigError("config parse error line " +
                              std::to_string(line.number) +
                              ": duplicate key '" + line.key + "'");
        }
        if (starts_inline_container(line.rest) ||
            !line.rest.empty()) {
            node.map[line.key] = parse_scalar_node(line);
        } else {
            // nested block; children must be indented deeper
            if (cursor >= lines.size() ||
                lines[cursor].indent <= line.indent) {
                YNode empty_child;
                empty_child.kind = YNode::Kind::Map;  // tolerated empty
                node.map[line.key] = empty_child;
            } else {
                node.map[line.key] =
                    parse_block(lines, cursor, lines[cursor].indent);
            }
        }
    }
    return node;
}

// ---------------------------------------------------------------------------
// Required-key accessor + error bookkeeping.  Unknown keys and
// cross-section invariants belong to the Python validator (R2).
// ---------------------------------------------------------------------------

const std::array<const char*, 6> kNamedSpecies = {
    "coluzzii", "gambiae_ss", "funestus", "arabiensis", "melas",
    "stephensi"};

template <typename T>
struct Checked {  // typed accessor with error bookkeeping
};

struct Loader {
    const YNode* root;
    std::string path;
    std::vector<std::string> missing;
    std::vector<std::string> bad_type;

    const YNode* section(const YNode* node, const char* name) {
        if (node == nullptr || node->kind != YNode::Kind::Map) {
            missing.push_back(name);
            return nullptr;
        }
        auto it = node->map.find(name);
        if (it == node->map.end()) {
            missing.push_back(std::string(name));
            return nullptr;
        }
        return &it->second;
    }

    const YNode* key(const YNode* section_node, const std::string& sname,
                     const char* kname) {
        if (section_node == nullptr) return nullptr;
        auto it = section_node->map.find(kname);
        if (it == section_node->map.end()) {
            missing.push_back(sname + "." + kname);
            return nullptr;
        }
        return &it->second;
    }

    double num(const YNode* v, const std::string& dotted) {
        if (v == nullptr || v->kind != YNode::Kind::Scalar ||
            v->quoted) {
            bad_type.push_back(dotted + " (expected number)");
            return 0.0;
        }
        try {
            return std::stod(strip_quotes(v->scalar));
        } catch (const std::exception&) {
            bad_type.push_back(dotted + " (expected number)");
            return 0.0;
        }
    }

    int integer(const YNode* v, const std::string& dotted) {
        if (v == nullptr || v->kind != YNode::Kind::Scalar) {
            bad_type.push_back(dotted + " (expected int)");
            return 0;
        }
        try {
            size_t consumed = 0;
            const double d = std::stod(strip_quotes(v->scalar), &consumed);
            if (consumed != v->scalar.size() ||
                std::fabs(d - std::llround(d)) > 1e-12) {
                throw std::invalid_argument("x");
            }
            return static_cast<int>(std::llround(d));
        } catch (const std::exception&) {
            bad_type.push_back(dotted + " (expected int)");
            return 0;
        }
    }

    std::string str(const YNode* v, const std::string& dotted) {
        if (v == nullptr || v->kind != YNode::Kind::Scalar) {
            bad_type.push_back(dotted + " (expected string)");
            return "";
        }
        return strip_quotes(v->scalar);
    }

    std::vector<std::string> list_of(const YNode* v, const std::string& dotted) {
        if (v == nullptr || v->kind != YNode::Kind::List) {
            bad_type.push_back(dotted + " (expected list)");
            return {};
        }
        std::vector<std::string> out;
        for (const auto& item : v->list) out.push_back(item.scalar);
        return out;
    }

    void raise() const {
        std::ostringstream msg;
        size_t n = missing.size() + bad_type.size();
        if (n == 0) return;
        msg << "config access: " << n << " problem(s) in " << path << ":\n";
        if (!missing.empty()) {
            msg << "  missing keys:\n";
            for (const auto& m : missing) msg << "    " << m << "\n";
        }
        if (!bad_type.empty()) {
            msg << "  wrong types:\n";
            for (const auto& m : bad_type) msg << "    " << m << "\n";
        }
        throw ConfigError(msg.str());
    }
};

}  // namespace

std::optional<ZoneId> zone_id_of_habitat(const std::string& name) {
    static const std::map<std::string, ZoneId> table = {
        {"surface_persistent", ZoneId::JRC_PERSISTENT},
        {"urban_persistent", ZoneId::URBAN_PERSISTENT},
        {"wetland_persistent", ZoneId::WETLAND},
        {"open_pluvial", ZoneId::OPEN_PLUVIAL},
        {"crop_pluvial", ZoneId::CROP},
    };
    auto it = table.find(name);
    if (it == table.end()) return std::nullopt;
    return it->second;
}

ModelConfig parse_config_file(const std::string& path) {
    const std::vector<Line> lines = scan_lines(path);
    size_t cursor = 0;
    const YNode root = lines.empty() ? YNode{} : parse_block(lines, cursor, 0);
    Loader L;
    L.root = &root;
    L.path = path;

    ModelConfig cfg;
    cfg.version = L.integer(L.key(&root, "", "version"), "version");
    const YNode* contracts = L.section(&root, "contracts");
    cfg.contracts.env_nc = L.str(L.key(contracts, "contracts", "env_nc"),
                                 "contracts.env_nc");
    cfg.contracts.cogs_state = L.str(
        L.key(contracts, "contracts", "cogs_state"), "contracts.cogs_state");

    // -- habitat_types -------------------------------------------------------
    const YNode* ht = L.section(&root, "habitat_types");
    cfg.habitat_types.types = L.list_of(
        L.key(ht, "habitat_types", "types"), "habitat_types.types");
    const YNode* dyn = L.key(ht, "habitat_types", "dynamics");
    if (dyn != nullptr && dyn->kind == YNode::Kind::Map) {
        for (const auto& kv : dyn->map) {
            cfg.habitat_types.dynamics[kv.first] =
                trim(kv.second.scalar);
        }
    }

    // -- habitat thresholds --------------------------------------------------
    const YNode* hab = L.section(&root, "habitat");
    cfg.habitat.activation_min_engine = L.num(
        L.key(hab, "habitat", "activation_min_engine"),
        "habitat.activation_min_engine");
    cfg.habitat.candidate_min_engine = L.num(
        L.key(hab, "habitat", "candidate_min_engine"),
        "habitat.candidate_min_engine");

    // -- pluvial -------------------------------------------------------------
    const YNode* pluv = L.section(&root, "pluvial");
    cfg.pluvial.rain_scale_mm = L.num(
        L.key(pluv, "pluvial", "rain_scale_mm"), "pluvial.rain_scale_mm");
    cfg.pluvial.dry_memory_days = L.num(
        L.key(pluv, "pluvial", "dry_memory_days"),
        "pluvial.dry_memory_days");
    cfg.pluvial.delta_days = L.num(
        L.key(pluv, "pluvial", "delta_days"), "pluvial.delta_days");
    cfg.pluvial.cold_start_z = L.num(
        L.key(pluv, "pluvial", "cold_start_z"), "pluvial.cold_start_z");

    // -- aquatic_stress ------------------------------------------------------
    const YNode* aq = L.section(&root, "aquatic_stress");
    cfg.aquatic_stress.desicc_grace_days = L.num(
        L.key(aq, "aquatic_stress", "desicc_grace_days"),
        "aquatic_stress.desicc_grace_days");
    cfg.aquatic_stress.desicc_base_daily = L.num(
        L.key(aq, "aquatic_stress", "desicc_base_daily"),
        "aquatic_stress.desicc_base_daily");
    cfg.aquatic_stress.desicc_ramp_decay = L.num(
        L.key(aq, "aquatic_stress", "desicc_ramp_decay"),
        "aquatic_stress.desicc_ramp_decay");
    cfg.aquatic_stress.wash_threshold_mm = L.num(
        L.key(aq, "aquatic_stress", "wash_threshold_mm"),
        "aquatic_stress.wash_threshold_mm");
    cfg.aquatic_stress.wash_fraction_max = L.num(
        L.key(aq, "aquatic_stress", "wash_fraction_max"),
        "aquatic_stress.wash_fraction_max");
    cfg.aquatic_stress.vulnerable_instar_max = L.integer(
        L.key(aq, "aquatic_stress", "vulnerable_instar_max"),
        "aquatic_stress.vulnerable_instar_max");

    // -- urban ---------------------------------------------------------------
    const YNode* urb = L.section(&root, "urban");
    cfg.urban.beta_urban = L.num(L.key(urb, "urban", "beta_urban"),
                                 "urban.beta_urban");
    cfg.urban.rain_pools_built_damage = L.num(
        L.key(urb, "urban", "rain_pools_built_damage"),
        "urban.rain_pools_built_damage");

    // -- species -------------------------------------------------------------
    const YNode* sp = L.section(&root, "species");
    cfg.species.default_species = L.str(
        L.key(sp, "species", "default_species"), "species.default_species");
    cfg.species.k_ref = L.num(L.key(sp, "species", "k_ref"), "species.k_ref");
    for (const char* name : kNamedSpecies) {
        const YNode* row = L.key(sp, "species", name);
        if (row == nullptr) continue;
        SpeciesRow out;
        out.name = name;
        const YNode* w = L.key(row, std::string("species.") + name, "weights");
        if (w != nullptr && w->kind == YNode::Kind::Map) {
            for (const auto& [gname, val] : w->map) {
                if (gname == "wetland_pluvial") {
                    // No ZoneId in the engine; the Python validator pins it
                    // to 0.00 (plan §2), so there is nothing to map here.
                    continue;
                }
                const auto zone = zone_id_of_habitat(gname);
                if (!zone.has_value()) continue;
                out.weights[static_cast<size_t>(*zone)] =
                    L.num(&val, std::string("species.") + name +
                                    ".weights." + gname);
            }
        }
        out.salinity_hi_tol_ppt = L.num(
            L.key(row, std::string("species.") + name, "salinity_hi_tol_ppt"),
            std::string("species.") + name + ".salinity_hi_tol_ppt");
        out.salinity_opt_ppt = L.num(
            L.key(row, std::string("species.") + name, "salinity_opt_ppt"),
            std::string("species.") + name + ".salinity_opt_ppt");
        out.salinity_slope = L.num(
            L.key(row, std::string("species.") + name, "salinity_slope"),
            std::string("species.") + name + ".salinity_slope");
        // v2: activity_weights inline list [DAY, EVENING, NIGHT, DAWN]
        if (const YNode* aw = L.key(row, std::string("species.") + name,
                                    "activity_weights");
            aw != nullptr && aw->kind == YNode::Kind::List) {
            if (aw->list.size() != 4) {
                L.bad_type.push_back(std::string("species.") + name +
                                     ".activity_weights (expected 4 items)");
            }
            for (size_t i = 0; i < aw->list.size() && i < 4; ++i) {
                out.activity_weights[i] =
                    L.num(&aw->list[i], std::string("species.") + name +
                                            ".activity_weights[" +
                                            std::to_string(i) + "]");
            }
        }
        // v2: pref inline map, HostType BY NAME (never positional).
        if (const YNode* pf = L.key(row, std::string("species.") + name,
                                    "pref");
            pf != nullptr && pf->kind == YNode::Kind::Map) {
            static const std::array<const char*, 5> kHostNames = {
                "human", "cattle", "goat", "sheep", "wildlife"};
            for (size_t i = 0; i < kHostNames.size(); ++i) {
                if (const YNode* v = L.key(pf, std::string("species.") + name +
                                                    ".pref",
                                           kHostNames[i]);
                    v != nullptr) {
                    out.pref[i] = L.num(v, std::string("species.") + name +
                                               ".pref." + kHostNames[i]);
                }
            }
        }
        out.host_seeking_scale_m = L.num(
            L.key(row, std::string("species.") + name,
                  "host_seeking_scale_m"),
            std::string("species.") + name + ".host_seeking_scale_m");
        out.host_seeking_radius_m = L.num(
            L.key(row, std::string("species.") + name,
                  "host_seeking_radius_m"),
            std::string("species.") + name + ".host_seeking_radius_m");
        cfg.species.rows[name] = out;
    }
    const YNode* neutral = L.key(sp, "species", "neutral");
    if (neutral != nullptr && neutral->kind == YNode::Kind::Map) {
        const YNode* w = L.key(neutral, "species.neutral", "weights");
        if (w != nullptr && w->kind == YNode::Kind::Map) {
            for (const auto& [gname, val] : w->map) {
                if (gname == "wetland_pluvial") {
                    // No ZoneId in the engine; the Python validator pins it
                    // to 0.00 (plan §2), so there is nothing to map here.
                    continue;
                }
                const auto zone = zone_id_of_habitat(gname);
                if (!zone.has_value()) continue;
                cfg.species.neutral_weights[static_cast<size_t>(*zone)] =
                    L.num(&val, "species.neutral.weights." + gname);
            }
        }
    }

    // -- capacity ------------------------------------------------------------
    const YNode* cap = L.section(&root, "capacity");
    cfg.capacity.persistent_availability = L.num(
        L.key(cap, "capacity", "persistent_availability"),
        "capacity.persistent_availability");

    // -- geodesy -------------------------------------------------------------
    const YNode* geo = L.section(&root, "geodesy");
    cfg.geodesy.earth_radius_m = L.num(L.key(geo, "geodesy", "earth_radius_m"),
                                       "geodesy.earth_radius_m");
    cfg.geodesy.metres_per_deg_lat = L.num(
        L.key(geo, "geodesy", "metres_per_deg_lat"),
        "geodesy.metres_per_deg_lat");

    // -- ingest --------------------------------------------------------------
    const YNode* ing = L.section(&root, "ingest");
    cfg.ingest.nodata_sentinel = L.num(
        L.key(ing, "ingest", "nodata_sentinel"), "ingest.nodata_sentinel");
    cfg.ingest.nodata_sentinel_int = L.integer(
        L.key(ing, "ingest", "nodata_sentinel_int"),
        "ingest.nodata_sentinel_int");
    cfg.ingest.residential_from_indoor_frac = L.num(
        L.key(ing, "ingest", "residential_from_indoor_frac"),
        "ingest.residential_from_indoor_frac");
    cfg.ingest.coastline_buffer_m = L.num(
        L.key(ing, "ingest", "coastline_buffer_m"),
        "ingest.coastline_buffer_m");
    cfg.ingest.cell_size_hint_m = L.num(
        L.key(ing, "ingest", "cell_size_hint_m"), "ingest.cell_size_hint_m");
    cfg.ingest.candidate_min_ingest = L.num(
        L.key(ing, "ingest", "candidate_min_ingest"),
        "ingest.candidate_min_ingest");
    cfg.ingest.min_dilation_radius_cells = L.integer(
        L.key(ing, "ingest", "min_dilation_radius_cells"),
        "ingest.min_dilation_radius_cells");
    cfg.ingest.fill_frac_valid_max = L.num(
        L.key(ing, "ingest", "fill_frac_valid_max"),
        "ingest.fill_frac_valid_max");
    cfg.ingest.ocean_mask_threshold = L.num(
        L.key(ing, "ingest", "ocean_mask_threshold"),
        "ingest.ocean_mask_threshold");
    cfg.ingest.land_mask_threshold = L.num(
        L.key(ing, "ingest", "land_mask_threshold"),
        "ingest.land_mask_threshold");
    cfg.ingest.valid_count_epsilon = L.num(
        L.key(ing, "ingest", "valid_count_epsilon"),
        "ingest.valid_count_epsilon");
    cfg.ingest.grid_degrees_step_max = L.integer(
        L.key(ing, "ingest", "grid_degrees_step_max"),
        "ingest.grid_degrees_step_max");
    cfg.ingest.nc_compression_level = L.integer(
        L.key(ing, "ingest", "nc_compression_level"),
        "ingest.nc_compression_level");

    // -- adults --------------------------------------------------------------
    const YNode* ad = L.section(&root, "adults");
    cfg.adults.daily_mort_basal = L.num(
        L.key(ad, "adults", "daily_mort_basal"), "adults.daily_mort_basal");
    cfg.adults.opt_c = L.num(L.key(ad, "adults", "opt_c"), "adults.opt_c");
    cfg.adults.sigma_c = L.num(L.key(ad, "adults", "sigma_c"),
                               "adults.sigma_c");
    cfg.adults.mort_cap = L.num(L.key(ad, "adults", "mort_cap"),
                                "adults.mort_cap");
    cfg.adults.mort_floor = L.num(L.key(ad, "adults", "mort_floor"),
                                  "adults.mort_floor");

    // -- eip -----------------------------------------------------------------
    const YNode* eipn = L.section(&root, "eip");
    cfg.eip.base_c = L.num(L.key(eipn, "eip", "base_c"), "eip.base_c");
    cfg.eip.threshold_gd = L.num(L.key(eipn, "eip", "threshold_gd"),
                                 "eip.threshold_gd");

    // -- transmission --------------------------------------------------------
    const YNode* txn = L.section(&root, "transmission");
    cfg.transmission.beta_hv = L.num(
        L.key(txn, "transmission", "beta_hv"), "transmission.beta_hv");
    cfg.transmission.beta_vh = L.num(
        L.key(txn, "transmission", "beta_vh"), "transmission.beta_vh");
    cfg.transmission.human_incubation_days = L.integer(
        L.key(txn, "transmission", "human_incubation_days"),
        "transmission.human_incubation_days");
    cfg.transmission.human_infectious_days = L.integer(
        L.key(txn, "transmission", "human_infectious_days"),
        "transmission.human_infectious_days");
    cfg.transmission.human_immunity_days = L.integer(
        L.key(txn, "transmission", "human_immunity_days"),
        "transmission.human_immunity_days");
    cfg.transmission.initial_human_prevalence = L.num(
        L.key(txn, "transmission", "initial_human_prevalence"),
        "transmission.initial_human_prevalence");
    cfg.transmission.initial_vector_infected_frac = L.num(
        L.key(txn, "transmission", "initial_vector_infected_frac"),
        "transmission.initial_vector_infected_frac");

    // -- dispersal -----------------------------------------------------------
    const YNode* dsp = L.section(&root, "dispersal");
    cfg.dispersal.adult_prob_day = L.num(
        L.key(dsp, "dispersal", "adult_prob_day"), "dispersal.adult_prob_day");
    cfg.dispersal.adult_sigma_m = L.num(
        L.key(dsp, "dispersal", "adult_sigma_m"), "dispersal.adult_sigma_m");
    cfg.dispersal.adult_max_m = L.num(
        L.key(dsp, "dispersal", "adult_max_m"), "dispersal.adult_max_m");
    cfg.dispersal.wind_migration_prob = L.num(
        L.key(dsp, "dispersal", "wind_migration_prob"),
        "dispersal.wind_migration_prob");
    cfg.dispersal.wind_flight_hours = L.num(
        L.key(dsp, "dispersal", "wind_flight_hours"),
        "dispersal.wind_flight_hours");
    cfg.dispersal.wind_survival = L.num(
        L.key(dsp, "dispersal", "wind_survival"), "dispersal.wind_survival");
    cfg.dispersal.wind_self_speed_ms = L.num(
        L.key(dsp, "dispersal", "wind_self_speed_ms"),
        "dispersal.wind_self_speed_ms");
    cfg.dispersal.flight_hour = L.integer(
        L.key(dsp, "dispersal", "flight_hour"), "dispersal.flight_hour");
    cfg.dispersal.host_flight_step_m = L.num(
        L.key(dsp, "dispersal", "host_flight_step_m"),
        "dispersal.host_flight_step_m");
    cfg.dispersal.snap_radius_m = L.num(
        L.key(dsp, "dispersal", "snap_radius_m"), "dispersal.snap_radius_m");
    cfg.dispersal.night_start_hour = L.integer(
        L.key(dsp, "dispersal", "night_start_hour"),
        "dispersal.night_start_hour");
    cfg.dispersal.night_end_hour = L.integer(
        L.key(dsp, "dispersal", "night_end_hour"),
        "dispersal.night_end_hour");

    // -- host_seeking --------------------------------------------------------
    const YNode* hs = L.section(&root, "host_seeking");
    cfg.host_seeking.starvation_days = L.integer(
        L.key(hs, "host_seeking", "starvation_days"),
        "host_seeking.starvation_days");
    cfg.host_seeking.indoor_attraction_add = L.num(
        L.key(hs, "host_seeking", "indoor_attraction_add"),
        "host_seeking.indoor_attraction_add");
    cfg.host_seeking.urbanicity_add = L.num(
        L.key(hs, "host_seeking", "urbanicity_add"),
        "host_seeking.urbanicity_add");
    cfg.host_seeking.indoor_fraction_urban = L.num(
        L.key(hs, "host_seeking", "indoor_fraction_urban"),
        "host_seeking.indoor_fraction_urban");
    cfg.host_seeking.indoor_fraction_rural = L.num(
        L.key(hs, "host_seeking", "indoor_fraction_rural"),
        "host_seeking.indoor_fraction_rural");
    cfg.host_seeking.detect_range_m = L.num(
        L.key(hs, "host_seeking", "detect_range_m"),
        "host_seeking.detect_range_m");
    cfg.host_seeking.approach_step_m = L.num(
        L.key(hs, "host_seeking", "approach_step_m"),
        "host_seeking.approach_step_m");

    // -- oviposition ---------------------------------------------------------
    const YNode* ov = L.section(&root, "oviposition");
    cfg.oviposition.scale_m = L.num(L.key(ov, "oviposition", "scale_m"),
                                    "oviposition.scale_m");
    cfg.oviposition.detect_range_m = L.num(
        L.key(ov, "oviposition", "detect_range_m"),
        "oviposition.detect_range_m");
    cfg.oviposition.step_m = L.num(L.key(ov, "oviposition", "step_m"),
                                   "oviposition.step_m");
    cfg.oviposition.min_attraction = L.num(
        L.key(ov, "oviposition", "min_attraction"),
        "oviposition.min_attraction");
    cfg.oviposition.timeout_days = L.integer(
        L.key(ov, "oviposition", "timeout_days"),
        "oviposition.timeout_days");

    // -- aquatic_stages ------------------------------------------------------
    const YNode* stg = L.section(&root, "aquatic_stages");
    cfg.aquatic_stages.egg_daily_mort = L.num(
        L.key(stg, "aquatic_stages", "egg_daily_mort"),
        "aquatic_stages.egg_daily_mort");
    cfg.aquatic_stages.pupa_daily_mort = L.num(
        L.key(stg, "aquatic_stages", "pupa_daily_mort"),
        "aquatic_stages.pupa_daily_mort");
    cfg.aquatic_stages.larva_bh_s0 = L.num(
        L.key(stg, "aquatic_stages", "larva_bh_s0"),
        "aquatic_stages.larva_bh_s0");
    cfg.aquatic_stages.larva_bh_alpha = L.num(
        L.key(stg, "aquatic_stages", "larva_bh_alpha"),
        "aquatic_stages.larva_bh_alpha");
    cfg.aquatic_stages.last_larval_instar = L.integer(
        L.key(stg, "aquatic_stages", "last_larval_instar"),
        "aquatic_stages.last_larval_instar");
    cfg.aquatic_stages.salinity_missing_psu = L.num(
        L.key(stg, "aquatic_stages", "salinity_missing_psu"),
        "aquatic_stages.salinity_missing_psu");

    // -- thermal -------------------------------------------------------------
    const YNode* thm = L.section(&root, "thermal");
    cfg.thermal.efd_max_eggs_per_day = L.num(
        L.key(thm, "thermal", "efd_max_eggs_per_day"),
        "thermal.efd_max_eggs_per_day");
    cfg.thermal.efd_tmin_c = L.num(L.key(thm, "thermal", "efd_tmin_c"),
                                   "thermal.efd_tmin_c");
    cfg.thermal.efd_tmax_c = L.num(L.key(thm, "thermal", "efd_tmax_c"),
                                   "thermal.efd_tmax_c");
    cfg.thermal.efd_topt_c = L.num(L.key(thm, "thermal", "efd_topt_c"),
                                   "thermal.efd_topt_c");
    cfg.thermal.egg_development_tmin_c = L.num(
        L.key(thm, "thermal", "egg_development_tmin_c"),
        "thermal.egg_development_tmin_c");
    cfg.thermal.egg_development_tmax_c = L.num(
        L.key(thm, "thermal", "egg_development_tmax_c"),
        "thermal.egg_development_tmax_c");
    cfg.thermal.egg_development_scale = L.num(
        L.key(thm, "thermal", "egg_development_scale"),
        "thermal.egg_development_scale");
    cfg.thermal.larva_development_tmin_c = L.num(
        L.key(thm, "thermal", "larva_development_tmin_c"),
        "thermal.larva_development_tmin_c");
    cfg.thermal.larva_development_tmax_c = L.num(
        L.key(thm, "thermal", "larva_development_tmax_c"),
        "thermal.larva_development_tmax_c");
    cfg.thermal.larva_development_scale = L.num(
        L.key(thm, "thermal", "larva_development_scale"),
        "thermal.larva_development_scale");
    cfg.thermal.pupa_development_tmin_c = L.num(
        L.key(thm, "thermal", "pupa_development_tmin_c"),
        "thermal.pupa_development_tmin_c");
    cfg.thermal.pupa_development_tmax_c = L.num(
        L.key(thm, "thermal", "pupa_development_tmax_c"),
        "thermal.pupa_development_tmax_c");
    cfg.thermal.pupa_development_scale = L.num(
        L.key(thm, "thermal", "pupa_development_scale"),
        "thermal.pupa_development_scale");

    // -- gonotrophic ---------------------------------------------------------
    const YNode* gon = L.section(&root, "gonotrophic");
    cfg.gonotrophic.cycle_duration_days = L.num(
        L.key(gon, "gonotrophic", "cycle_duration_days"),
        "gonotrophic.cycle_duration_days");
    cfg.gonotrophic.first_cycle_days = L.num(
        L.key(gon, "gonotrophic", "first_cycle_days"),
        "gonotrophic.first_cycle_days");
    cfg.gonotrophic.feeding_success_rate = L.num(
        L.key(gon, "gonotrophic", "feeding_success_rate"),
        "gonotrophic.feeding_success_rate");
    cfg.gonotrophic.egg_batch_mean = L.integer(
        L.key(gon, "gonotrophic", "egg_batch_mean"),
        "gonotrophic.egg_batch_mean");
    cfg.gonotrophic.egg_batch_n = L.integer(
        L.key(gon, "gonotrophic", "egg_batch_n"),
        "gonotrophic.egg_batch_n");
    cfg.gonotrophic.egg_batch_min = L.integer(
        L.key(gon, "gonotrophic", "egg_batch_min"),
        "gonotrophic.egg_batch_min");
    cfg.gonotrophic.egg_batch_max = L.integer(
        L.key(gon, "gonotrophic", "egg_batch_max"),
        "gonotrophic.egg_batch_max");
    cfg.gonotrophic.resting_duration_days = L.num(
        L.key(gon, "gonotrophic", "resting_duration_days"),
        "gonotrophic.resting_duration_days");

    // -- rng -----------------------------------------------------------------
    const YNode* rng = L.section(&root, "rng");
    cfg.rng.aquatic_seed_washout = L.integer(
        L.key(rng, "rng", "aquatic_seed_washout"),
        "rng.aquatic_seed_washout");
    cfg.rng.aquatic_seed_stage_mortality = L.integer(
        L.key(rng, "rng", "aquatic_seed_stage_mortality"),
        "rng.aquatic_seed_stage_mortality");
    cfg.rng.aquatic_seed_larva_mortality = L.integer(
        L.key(rng, "rng", "aquatic_seed_larva_mortality"),
        "rng.aquatic_seed_larva_mortality");

    L.raise();

    // -- derived values (plan §9.5: never stored in the YAML) ---------------
    cfg.habitat_types.num_persistent = 0;
    std::fill(cfg.habitat_types.persistent_zone.begin(),
              cfg.habitat_types.persistent_zone.end(), false);
    for (const auto& kv : cfg.habitat_types.dynamics) {
        if (kv.second == "persistent") ++cfg.habitat_types.num_persistent;
        if (const auto zone = zone_id_of_habitat(kv.first);
            zone.has_value()) {
            cfg.habitat_types.persistent_zone[static_cast<size_t>(*zone)] =
                kv.second == "persistent";
        }
    }

    return cfg;
}

// ---------------------------------------------------------------------------
// Path resolution + singleton
// ---------------------------------------------------------------------------

static std::string exe_dir() {
#ifdef _WIN32
    char buf[MAX_PATH];
    GetModuleFileNameA(nullptr, buf, MAX_PATH);
    std::string full = buf;
    const size_t slash = full.find_last_of("\\/");
    return slash == std::string::npos ? "." : full.substr(0, slash);
#elif defined(__APPLE__)
    uint32_t size = 0;
    _NSGetExecutablePath(nullptr, &size);
    std::string full(size + 1, '\0');
    if (_NSGetExecutablePath(full.data(), &size) != 0) return ".";
    full.resize(std::strlen(full.data()));
    const size_t slash = full.find_last_of('/');
    return slash == std::string::npos ? "." : full.substr(0, slash);
#else
    std::array<char, PATH_MAX> buf{};
    const ssize_t n = ::readlink("/proc/self/exe", buf.data(), buf.size() - 1);
    if (n <= 0) return ".";
    std::string full(buf.data(), static_cast<size_t>(n));
    const size_t slash = full.find_last_of('/');
    return slash == std::string::npos ? "." : full.substr(0, slash);
#endif
}

std::string resolve_config_path() {
    if (const char* env = std::getenv("MAL_MODEL_CONSTANTS")) {
        return env;
    }
    std::string dir = exe_dir();
    std::string previous;
    for (int depth = 0; depth < 8; ++depth) {
        for (const char* candidate :
             {"config/model_constants.yaml", "model_constants.yaml",
              "mal-core/config/model_constants.yaml"}) {
            const std::string p = dir + "/" + candidate;
            std::ifstream fh(p);
            if (fh.good()) return p;
        }
        const size_t slash = dir.find_last_of('/');
        if (slash == std::string::npos) break;
        const std::string parent = dir.substr(0, slash);
        if (parent == previous) break;
        previous = dir;
        dir = parent;
        if (dir.empty() || dir == "/") break;
    }
    throw ConfigError(
        "model_constants.yaml not found: set MAL_MODEL_CONSTANTS or place "
        "config/model_constants.yaml next to the binary");
}

const ModelConfig& load_config() {
    static const ModelConfig cfg = []() {
        const std::string path = resolve_config_path();
        std::clog << "model_constants: " << path << "\n";
        return parse_config_file(path);
    }();
    return cfg;
}



}  // namespace mal_abm_fast
