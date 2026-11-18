// SPDX-License-Identifier: MIT
// test_scenario_seeding.cpp — GoogleTest for the SCENARIO seeding primitives
// (plan 13.2 / 13.3 / 13.4, Paso 0 of the individualization plan):
//
//   * derive_substream_seed: deterministic, label- and master-sensitive,
//     independent of call order.
//   * load_scenario_spec: full and minimal documents, strict key/enum/range
//     validation with the offending key path in the message.
//   * MosquitoSubmodel::seed_scenario: adults and aquatic cohorts land at the
//     spec's positions; no RNG is consumed (same initial state for any seed).
//   * AquaticCohortBank::seed_streams: same master -> same mortality, different
//     master -> different mortality.
//   * CoordinatorModel::register_scenario_cell: a cell outside the habitat
//     candidate union is forced into the candidate set with a stable pid.
//
// Every test is named ScenarioSeeding.* so `ctest -R ScenarioSeeding` selects
// the whole file.
#include <gtest/gtest.h>

#include <unistd.h>

#include <chrono>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <memory>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

#include <netcdf.h>

#include "aoi.hpp"
#include "aquatic_cohort_bank.hpp"
#include "climate.hpp"
#include "coordinator.hpp"
#include "habitat_engine.hpp"
#include "mosquito_submodel.hpp"
#include "prng.hpp"
#include "seeding.hpp"
#include "wire.hpp"

namespace {

using namespace mal_abm_fast;

// Per-process unique scratch name: gtest_discover_tests runs each TEST in its
// own process, so the pid keeps parallel ctest runs from colliding.
std::filesystem::path scratch_path(const std::string& name) {
    return std::filesystem::temp_directory_path() /
           ("mal_scenario_seeding_" + std::to_string(static_cast<long>(::getpid())) +
            "_" + name);
}

std::string write_json(const std::string& name, const std::string& text) {
    const auto p = scratch_path(name + ".json");
    std::ofstream f(p);
    f << text;
    f.close();
    return p.string();
}

// Loads the document and returns the exception message ("" if it loaded).
std::string load_error(const std::string& name, const std::string& text) {
    const std::string p = write_json(name, text);
    try {
        (void)load_scenario_spec(p);
    } catch (const std::runtime_error& e) {
        std::filesystem::remove(p);
        return e.what();
    }
    std::filesystem::remove(p);
    return "";
}

// Minimal valid document; tests splice in one bad field at a time.
const char* kMinimal = R"({"id":"s","seed":1,"days":10,"agents":[]})";

// ---------------------------------------------------------------------------
// Synthetic env NC (same contract as test_coordinator.cpp), with the five
// static habitat planes set to `static_value` so the candidate floor drops
// every cell when it is 0.
// ---------------------------------------------------------------------------
void write_env_nc(const std::filesystem::path& path, int n_days, int h, int w,
                  float static_value) {
    int ncid = 0, dimids[3] = {0, 0, 0}, vid[2] = {0, 0};
    int dimid_time = 0, dimid_y = 0, dimid_x = 0;

    ASSERT_EQ(nc_create(path.string().c_str(), NC_CLOBBER | NC_NETCDF4, &ncid), NC_NOERR);
    ASSERT_EQ(nc_def_dim(ncid, "time", NC_UNLIMITED, &dimid_time), NC_NOERR);
    ASSERT_EQ(nc_def_dim(ncid, "y", static_cast<size_t>(h), &dimid_y), NC_NOERR);
    ASSERT_EQ(nc_def_dim(ncid, "x", static_cast<size_t>(w), &dimid_x), NC_NOERR);
    dimids[0] = dimid_time;
    dimids[1] = dimid_y;
    dimids[2] = dimid_x;
    ASSERT_EQ(nc_def_var(ncid, "rainfall", NC_FLOAT, 3, dimids, &vid[0]), NC_NOERR);
    ASSERT_EQ(nc_def_var(ncid, "air_temp_c", NC_FLOAT, 3, dimids, &vid[1]), NC_NOERR);
    ASSERT_EQ(nc_put_att_text(ncid, NC_GLOBAL, "Conventions", 6, "CF-1.8"), NC_NOERR);

    const char* statics[] = {"jrc_persistent", "lc_built", "lc_wetland",
                             "lc_open_plus_water", "lc_crop"};
    for (const char* name : statics) {
        int dids[2] = {dimid_y, dimid_x};
        int varid = -1;
        ASSERT_EQ(nc_def_var(ncid, name, NC_FLOAT, 2, dids, &varid), NC_NOERR);
        ASSERT_EQ(nc_enddef(ncid), NC_NOERR);
        std::vector<float> plane(static_cast<size_t>(h) * static_cast<size_t>(w),
                                 static_value);
        ASSERT_EQ(nc_put_var_float(ncid, varid, plane.data()), NC_NOERR);
        ASSERT_EQ(nc_redef(ncid), NC_NOERR);
    }

    std::vector<float> buf(static_cast<size_t>(h) * static_cast<size_t>(w));
    size_t start[3] = {0, 0, 0};
    size_t count[3] = {1, static_cast<size_t>(h), static_cast<size_t>(w)};
    for (int d = 0; d < n_days; ++d) {
        start[0] = static_cast<size_t>(d);
        std::fill(buf.begin(), buf.end(), 40.0f);
        ASSERT_EQ(nc_put_vara_float(ncid, vid[0], start, count, buf.data()), NC_NOERR);
        std::fill(buf.begin(), buf.end(), 25.0f);
        ASSERT_EQ(nc_put_vara_float(ncid, vid[1], start, count, buf.data()), NC_NOERR);
    }
    ASSERT_EQ(nc_close(ncid), NC_NOERR);
}

AOI make_aoi_4x4() {
    AOI aoi;
    aoi.west = 0.0;
    aoi.east = 0.04;
    aoi.south = 0.0;
    aoi.north = 0.04;
    aoi.crs = "EPSG:4326";
    aoi.slug = "scenario-test";
    aoi.resolution_m = 1000;
    aoi.scale = "regional";
    return aoi;
}

std::chrono::sys_days make_date(int year, unsigned month, unsigned day) {
    return std::chrono::sys_days{std::chrono::year_month_day{
        std::chrono::year{year}, std::chrono::month{month}, std::chrono::day{day}}};
}

// Fake locator for seed_scenario: 100 m cells on a 10x10 grid, pid = row*10+col,
// lon/lat derived linearly so the test can check the stored coordinates.
ScenarioCell fake_locate(double x, double y) {
    ScenarioCell c;
    c.col = static_cast<int32_t>(x / 100.0);
    c.row = static_cast<int32_t>(y / 100.0);
    c.pid = static_cast<int64_t>(c.row) * 10 + c.col;
    c.lon = 1.0 + x * 1e-5;
    c.lat = 2.0 + y * 1e-5;
    return c;
}

ScenarioSpec make_seed_spec() {
    ScenarioSpec spec;
    spec.id = "unit";
    spec.seed = 9;
    spec.days = 5;

    ScenarioAgent a0;
    a0.x = 50.0;  a0.y = 50.0;
    a0.sex = AdultSex::MALE;
    a0.state = GonotrophicState::RESTING;
    a0.age_days = 4;
    a0.infective = false;
    ScenarioAgent a1;
    a1.x = 150.0; a1.y = 50.0;
    a1.sex = AdultSex::FEMALE;
    a1.state = GonotrophicState::TENERAL;
    a1.age_days = 0;
    a1.infective = true;
    ScenarioAgent a2;
    a2.x = 250.0; a2.y = 350.0;
    a2.sex = AdultSex::FEMALE;
    a2.state = GonotrophicState::HOST_SEEKING;
    a2.age_days = 9;
    a2.infective = false;
    spec.agents = {a0, a1, a2};

    ScenarioAquatic e;
    e.x = 50.0; e.y = 50.0; e.cell_id = 0;
    e.stage = AquaticStage::EGG; e.instar = 0; e.development = 0.5f; e.count = 100;
    ScenarioAquatic l;
    l.x = 150.0; l.y = 50.0; l.cell_id = 1;
    l.stage = AquaticStage::LARVA; l.instar = 3; l.development = 0.2f; l.count = 40;
    ScenarioAquatic p;
    p.x = 250.0; p.y = 350.0; p.cell_id = 1;  // cell_id is not checked by the submodel
    p.stage = AquaticStage::PUPA; p.instar = 0; p.development = 0.0f; p.count = 7;
    spec.aquatic = {e, l, p};
    return spec;
}

}  // namespace

// ===========================================================================
// derive_substream_seed
// ===========================================================================

TEST(ScenarioSeeding, SubstreamSeedIsDeterministic) {
    EXPECT_EQ(derive_substream_seed(42, "aquatic/washout"),
              derive_substream_seed(42, "aquatic/washout"));
    EXPECT_EQ(derive_substream_seed(0, ""), derive_substream_seed(0, ""));
}

TEST(ScenarioSeeding, SubstreamSeedDiffersByLabel) {
    const uint64_t a = derive_substream_seed(42, "aquatic/washout");
    const uint64_t b = derive_substream_seed(42, "aquatic/stage_mortality");
    const uint64_t c = derive_substream_seed(42, "aquatic/larva_mortality");
    const uint64_t d = derive_substream_seed(42, "aquatic");
    EXPECT_NE(a, b);
    EXPECT_NE(a, c);
    EXPECT_NE(b, c);
    EXPECT_NE(a, d);
    // Label is case-sensitive.
    EXPECT_NE(derive_substream_seed(42, "Aquatic"), d);
}

TEST(ScenarioSeeding, SubstreamSeedDiffersByMaster) {
    EXPECT_NE(derive_substream_seed(1, "aquatic"), derive_substream_seed(2, "aquatic"));
    EXPECT_NE(derive_substream_seed(0, "aquatic"), derive_substream_seed(42, "aquatic"));
}

TEST(ScenarioSeeding, SubstreamSeedIsIndependentOfCallOrder) {
    const uint64_t master = 2024;
    const uint64_t a_first = derive_substream_seed(master, "a");
    const uint64_t b_second = derive_substream_seed(master, "b");

    // Reverse the order and interleave unrelated draws from a Prng on the same
    // master: the derived values must not move.
    Prng noise(master);
    for (int i = 0; i < 17; ++i) (void)noise.uniform_double();
    const uint64_t b_first = derive_substream_seed(master, "b");
    const uint64_t a_second = derive_substream_seed(master, "a");
    EXPECT_EQ(a_first, a_second);
    EXPECT_EQ(b_second, b_first);
}

// ===========================================================================
// load_scenario_spec — valid documents
// ===========================================================================

TEST(ScenarioSeeding, LoadsEveryField) {
    const std::string json = R"({
        "id": "ghana-village-1",
        "mode": "gate",
        "seed": 42,
        "days": 30,
        "agents": [
            {"x": 120.5, "y": 340.0, "sex": "FEMALE", "state": "BLOOD_FED",
             "age_days": 4, "infective": true},
            {"x": 10.0, "y": 20.0, "sex": "MALE"}
        ],
        "aquatic": [
            {"x": 50.0, "y": 60.0, "cell_id": 3, "stage": "L3", "instar": 3,
             "development": 0.25, "count": 120}
        ],
        "humans": [{"x": 1.0, "y": 2.0, "state": "INFECTIOUS", "timer": 3.5}],
        "livestock": [{"x": 4.0, "y": 5.0, "species": "goat"}],
        "overrides": {},
        "variants": [],
        "expectations": {"anything": true}
    })";
    const std::string p = write_json("full", json);
    const ScenarioSpec s = load_scenario_spec(p);
    std::filesystem::remove(p);

    EXPECT_EQ(s.id, "ghana-village-1");
    EXPECT_EQ(s.mode, "gate");
    EXPECT_EQ(s.seed, 42u);
    EXPECT_EQ(s.days, 30);

    ASSERT_EQ(s.agents.size(), 2u);
    EXPECT_DOUBLE_EQ(s.agents[0].x, 120.5);
    EXPECT_DOUBLE_EQ(s.agents[0].y, 340.0);
    EXPECT_EQ(s.agents[0].sex, AdultSex::FEMALE);
    EXPECT_EQ(s.agents[0].state, GonotrophicState::BLOOD_FED);
    EXPECT_EQ(s.agents[0].age_days, 4);
    EXPECT_TRUE(s.agents[0].infective);
    // Second agent: every optional field takes its default.
    EXPECT_EQ(s.agents[1].sex, AdultSex::MALE);
    EXPECT_EQ(s.agents[1].state, GonotrophicState::TENERAL);
    EXPECT_EQ(s.agents[1].age_days, 0);
    EXPECT_FALSE(s.agents[1].infective);

    ASSERT_EQ(s.aquatic.size(), 1u);
    EXPECT_EQ(s.aquatic[0].stage, AquaticStage::LARVA);
    EXPECT_EQ(s.aquatic[0].instar, 3);
    EXPECT_EQ(s.aquatic[0].cell_id, 3);
    EXPECT_FLOAT_EQ(s.aquatic[0].development, 0.25f);
    EXPECT_EQ(s.aquatic[0].count, 120);

    ASSERT_EQ(s.humans.size(), 1u);
    EXPECT_EQ(s.humans[0].state, "INFECTIOUS");
    EXPECT_DOUBLE_EQ(s.humans[0].timer_days, 3.5);

    ASSERT_EQ(s.livestock.size(), 1u);
    EXPECT_EQ(s.livestock[0].species, "goat");

    EXPECT_TRUE(s.overrides.empty());
}

TEST(ScenarioSeeding, MinimalDocumentTakesDefaults) {
    const std::string p = write_json("minimal", kMinimal);
    const ScenarioSpec s = load_scenario_spec(p);
    std::filesystem::remove(p);
    EXPECT_EQ(s.mode, "report");
    EXPECT_EQ(s.seed, 1u);
    EXPECT_EQ(s.days, 10);
    EXPECT_TRUE(s.agents.empty());
    EXPECT_TRUE(s.aquatic.empty());
    EXPECT_TRUE(s.humans.empty());
    EXPECT_TRUE(s.livestock.empty());
}

TEST(ScenarioSeeding, FullRangeSeedIsAccepted) {
    const std::string text =
        R"({"id":"s","seed":18446744073709551615,"days":1,"agents":[]})";
    const std::string p = write_json("maxseed", text);
    const ScenarioSpec s = load_scenario_spec(p);
    std::filesystem::remove(p);
    EXPECT_EQ(s.seed, UINT64_MAX);
}

TEST(ScenarioSeeding, EmptyVariantsArrayIsAccepted) {
    const std::string text =
        R"({"id":"s","seed":1,"days":1,"agents":[],"variants":[]})";
    const std::string p = write_json("empty_variants", text);
    EXPECT_NO_THROW((void)load_scenario_spec(p));
    std::filesystem::remove(p);
}

TEST(ScenarioSeeding, EmptyAgentsArrayIsAccepted) {
    const std::string p = write_json("no_agents", kMinimal);
    const ScenarioSpec s = load_scenario_spec(p);
    std::filesystem::remove(p);
    EXPECT_TRUE(s.agents.empty());
}

// ===========================================================================
// load_scenario_spec — rejected documents
// ===========================================================================

TEST(ScenarioSeeding, UnknownTopLevelKeyNamesItsPath) {
    const std::string msg = load_error("top_unknown",
        R"({"id":"s","seed":1,"days":1,"agents":[],"bogus":1})");
    EXPECT_NE(msg.find("$.bogus"), std::string::npos) << msg;
    EXPECT_NE(msg.find("unknown key"), std::string::npos) << msg;
}

TEST(ScenarioSeeding, UnknownAgentKeyNamesItsPath) {
    const std::string msg = load_error("agent_unknown",
        R"({"id":"s","seed":1,"days":1,"agents":[{"x":0,"y":0,"sex":"MALE","sexx":1}]})");
    EXPECT_NE(msg.find("$.agents[0].sexx"), std::string::npos) << msg;
}

TEST(ScenarioSeeding, UnknownAquaticAndHumanKeysNameTheirPaths) {
    const std::string aq = load_error("aq_unknown",
        R"({"id":"s","seed":1,"days":1,"agents":[],"aquatic":[)"
        R"({"x":0,"y":0,"cell_id":0,"stage":"EGG","count":1,"colour":"red"}]})");
    EXPECT_NE(aq.find("$.aquatic[0].colour"), std::string::npos) << aq;

    const std::string hu = load_error("hu_unknown",
        R"({"id":"s","seed":1,"days":1,"agents":[],"humans":[{"x":0,"y":0,"age":3}]})");
    EXPECT_NE(hu.find("$.humans[0].age"), std::string::npos) << hu;
}

TEST(ScenarioSeeding, InvalidAgentSexIsRejected) {
    const std::string lower = load_error("sex_lower",
        R"({"id":"s","seed":1,"days":1,"agents":[{"x":0,"y":0,"sex":"male"}]})");
    EXPECT_NE(lower.find("$.agents[0].sex"), std::string::npos) << lower;

    const std::string missing = load_error("sex_missing",
        R"({"id":"s","seed":1,"days":1,"agents":[{"x":0,"y":0}]})");
    EXPECT_NE(missing.find("$.agents[0].sex"), std::string::npos) << missing;
}

TEST(ScenarioSeeding, InvalidAgentStateIsRejected) {
    // A valid enum value the loader does not support (MATE_SEEKING) and an
    // unknown name must both fail, with the path of the state field.
    const std::string unsupported = load_error("state_mate",
        R"({"id":"s","seed":1,"days":1,"agents":[{"x":0,"y":0,"sex":"FEMALE","state":"MATE_SEEKING"}]})");
    EXPECT_NE(unsupported.find("$.agents[0].state"), std::string::npos) << unsupported;
    EXPECT_NE(unsupported.find("unsupported agent state"), std::string::npos) << unsupported;

    const std::string unknown = load_error("state_foo",
        R"({"id":"s","seed":1,"days":1,"agents":[{"x":0,"y":0,"sex":"FEMALE","state":"FOO"}]})");
    EXPECT_NE(unknown.find("$.agents[0].state"), std::string::npos) << unknown;
}

TEST(ScenarioSeeding, InvalidAquaticStageIsRejected) {
    const std::string l5 = load_error("stage_l5",
        R"({"id":"s","seed":1,"days":1,"agents":[],"aquatic":[)"
        R"({"x":0,"y":0,"cell_id":0,"stage":"L5","count":1}]})");
    EXPECT_NE(l5.find("$.aquatic[0].stage"), std::string::npos) << l5;

    const std::string lower = load_error("stage_lower",
        R"({"id":"s","seed":1,"days":1,"agents":[],"aquatic":[)"
        R"({"x":0,"y":0,"cell_id":0,"stage":"egg","count":1}]})");
    EXPECT_NE(lower.find("$.aquatic[0].stage"), std::string::npos) << lower;
}

TEST(ScenarioSeeding, InstarMustAgreeWithLarvalStage) {
    const std::string msg = load_error("instar_mismatch",
        R"({"id":"s","seed":1,"days":1,"agents":[],"aquatic":[)"
        R"({"x":0,"y":0,"cell_id":0,"stage":"L2","instar":3,"count":1}]})");
    EXPECT_NE(msg.find("$.aquatic[0].instar"), std::string::npos) << msg;
}

TEST(ScenarioSeeding, AquaticDevelopmentAndCountRanges) {
    const std::string dev = load_error("dev_range",
        R"({"id":"s","seed":1,"days":1,"agents":[],"aquatic":[)"
        R"({"x":0,"y":0,"cell_id":0,"stage":"EGG","development":1.5,"count":1}]})");
    EXPECT_NE(dev.find("$.aquatic[0].development"), std::string::npos) << dev;

    const std::string neg = load_error("count_neg",
        R"({"id":"s","seed":1,"days":1,"agents":[],"aquatic":[)"
        R"({"x":0,"y":0,"cell_id":0,"stage":"EGG","count":-1}]})");
    EXPECT_NE(neg.find("$.aquatic[0].count"), std::string::npos) << neg;

    const std::string frac = load_error("count_frac",
        R"({"id":"s","seed":1,"days":1,"agents":[],"aquatic":[)"
        R"({"x":0,"y":0,"cell_id":0,"stage":"EGG","count":1.5}]})");
    EXPECT_NE(frac.find("$.aquatic[0].count"), std::string::npos) << frac;
}

TEST(ScenarioSeeding, SeedMustBeNonNegativeInteger) {
    const std::string neg = load_error("seed_neg",
        R"({"id":"s","seed":-1,"days":1,"agents":[]})");
    EXPECT_NE(neg.find("$.seed"), std::string::npos) << neg;

    const std::string str = load_error("seed_str",
        R"({"id":"s","seed":"7","days":1,"agents":[]})");
    EXPECT_NE(str.find("$.seed"), std::string::npos) << str;

    const std::string missing = load_error("seed_missing",
        R"({"id":"s","days":1,"agents":[]})");
    EXPECT_NE(missing.find("$.seed"), std::string::npos) << missing;
}

TEST(ScenarioSeeding, DaysMustBeIntegerAtLeastOne) {
    for (const char* text : {
             R"({"id":"s","seed":1,"days":0,"agents":[]})",
             R"({"id":"s","seed":1,"days":-3,"agents":[]})",
             R"({"id":"s","seed":1,"days":1.5,"agents":[]})",
             R"({"id":"s","seed":1,"agents":[]})"}) {
        const std::string msg = load_error("days_bad", text);
        EXPECT_NE(msg.find("$.days"), std::string::npos) << text << " -> " << msg;
    }
}

TEST(ScenarioSeeding, NonEmptyVariantsAreRejected) {
    const std::string msg = load_error("variants_nonempty",
        R"({"id":"s","seed":1,"days":1,"agents":[],"variants":[{"name":"hi"}]})");
    EXPECT_NE(msg.find("$.variants"), std::string::npos) << msg;
}

TEST(ScenarioSeeding, NonEmptyOverridesAreRejected) {
    // Overrides are not applied before Paso 5; a silent no-op would let a
    // sensitivity band run with the canonical value.
    const std::string msg = load_error("overrides_nonempty",
        R"({"id":"s","seed":1,"days":1,"agents":[],"overrides":{"k":1.0}})");
    EXPECT_NE(msg.find("$.overrides"), std::string::npos) << msg;
}

TEST(ScenarioSeeding, AgentsArrayIsRequired) {
    const std::string msg = load_error("agents_missing",
        R"({"id":"s","seed":1,"days":1})");
    EXPECT_NE(msg.find("$.agents"), std::string::npos) << msg;
}

TEST(ScenarioSeeding, IdAndModeAreValidated) {
    const std::string no_id = load_error("id_missing",
        R"({"seed":1,"days":1,"agents":[]})");
    EXPECT_NE(no_id.find("$.id"), std::string::npos) << no_id;

    const std::string bad_mode = load_error("mode_bad",
        R"({"id":"s","mode":"live","seed":1,"days":1,"agents":[]})");
    EXPECT_NE(bad_mode.find("$.mode"), std::string::npos) << bad_mode;
}

TEST(ScenarioSeeding, InfectiveMustBeBoolean) {
    const std::string msg = load_error("infective_str",
        R"({"id":"s","seed":1,"days":1,"agents":[{"x":0,"y":0,"sex":"FEMALE","infective":"yes"}]})");
    EXPECT_NE(msg.find("$.agents[0].infective"), std::string::npos) << msg;
}

TEST(ScenarioSeeding, HumanStateIsValidated) {
    const std::string msg = load_error("human_state",
        R"({"id":"s","seed":1,"days":1,"agents":[],"humans":[{"x":0,"y":0,"state":"DEAD"}]})");
    EXPECT_NE(msg.find("$.humans[0].state"), std::string::npos) << msg;
}

TEST(ScenarioSeeding, MalformedJsonIsReported) {
    const std::string msg = load_error("broken", R"({"id":)");
    EXPECT_NE(msg.find("invalid JSON"), std::string::npos) << msg;
}

TEST(ScenarioSeeding, MissingFileIsReported) {
    const auto p = scratch_path("does_not_exist.json");
    std::filesystem::remove(p);
    try {
        (void)load_scenario_spec(p.string());
        FAIL() << "expected a runtime_error for a missing file";
    } catch (const std::runtime_error& e) {
        EXPECT_NE(std::string(e.what()).find("cannot open"), std::string::npos) << e.what();
    }
}

// cell_id vs (x, y) coherence is NOT checked here: the grid is needed, and the
// check lives in Engine::seed_scenario_population_ (src/engine.cpp). It is
// therefore not covered by this unit file.

// ===========================================================================
// MosquitoSubmodel::seed_scenario
// ===========================================================================

TEST(ScenarioSeeding, SeedScenarioPlacesAdultsAtSpecPositions) {
    MosquitoSubmodel sub(100, std::vector<SeedInstruction>{}, 1);
    const ScenarioSpec spec = make_seed_spec();
    sub.seed_scenario(spec, fake_locate);

    const MosquitoSoA& soa = sub.soa();
    ASSERT_EQ(soa.n_alive, 3);
    ASSERT_EQ(soa.uid.size(), 3u);
    ASSERT_EQ(soa.sex.size(), 3u);

    const std::vector<uint8_t> expect_sex = {
        static_cast<uint8_t>(AdultSex::MALE),
        static_cast<uint8_t>(AdultSex::FEMALE),
        static_cast<uint8_t>(AdultSex::FEMALE)};
    const std::vector<uint8_t> expect_state = {
        static_cast<uint8_t>(GonotrophicState::RESTING),
        static_cast<uint8_t>(GonotrophicState::TENERAL),
        static_cast<uint8_t>(GonotrophicState::HOST_SEEKING)};
    const std::vector<uint8_t> expect_vs = {
        static_cast<uint8_t>(VectorTransmissionState::SUSCEPTIBLE),
        static_cast<uint8_t>(VectorTransmissionState::INFECTIOUS),
        static_cast<uint8_t>(VectorTransmissionState::SUSCEPTIBLE)};
    const std::vector<int32_t> expect_age = {4, 0, 9};

    for (size_t i = 0; i < 3; ++i) {
        const ScenarioCell c = fake_locate(spec.agents[i].x, spec.agents[i].y);
        EXPECT_EQ(soa.stage[i], 1) << "agent " << i << " must be an adult";
        EXPECT_EQ(soa.sex[i], expect_sex[i]) << "agent " << i;
        EXPECT_EQ(soa.gonotrophic_state[i], expect_state[i]) << "agent " << i;
        EXPECT_EQ(soa.vector_state[i], expect_vs[i]) << "agent " << i;
        EXPECT_EQ(soa.stage_age[i], expect_age[i]) << "agent " << i;
        EXPECT_EQ(soa.patch_id[i], c.pid) << "agent " << i;
        EXPECT_EQ(soa.row[i], c.row) << "agent " << i;
        EXPECT_EQ(soa.col[i], c.col) << "agent " << i;
        EXPECT_NEAR(soa.lon[i], c.lon, 1e-6) << "agent " << i;
        EXPECT_NEAR(soa.lat[i], c.lat, 1e-6) << "agent " << i;
        EXPECT_EQ(soa.uid[i], static_cast<int64_t>(i));
    }
    EXPECT_EQ(soa.next_uid, 3);
}

TEST(ScenarioSeeding, SeedScenarioSeedsAquaticCohorts) {
    MosquitoSubmodel sub(100, std::vector<SeedInstruction>{}, 1);
    const ScenarioSpec spec = make_seed_spec();
    sub.seed_scenario(spec, fake_locate);

    const AquaticCohortBank& bank = sub.cohort_bank();
    EXPECT_EQ(bank.count_by_stage(AquaticStage::EGG), 100);
    EXPECT_EQ(bank.count_by_stage(AquaticStage::LARVA), 40);
    EXPECT_EQ(bank.count_by_stage(AquaticStage::PUPA), 7);
    EXPECT_EQ(bank.count_by_stage_instar(AquaticStage::LARVA, 3), 40);
    EXPECT_EQ(bank.total_aquatic(), 147);

    bool found_egg = false;
    for (const auto& c : bank.cohorts()) {
        if (c.stage == AquaticStage::EGG) {
            found_egg = true;
            EXPECT_EQ(c.patch_id, fake_locate(50.0, 50.0).pid);
            EXPECT_FLOAT_EQ(c.development, 0.5f);
        }
    }
    EXPECT_TRUE(found_egg);
}

TEST(ScenarioSeeding, SeedScenarioConsumesNoRngAndIsSeedIndependent) {
    // Two submodels with different master seeds receive the same spec. Nothing
    // in seed_scenario may draw from the RNG, so the initial state is identical.
    MosquitoSubmodel a(100, std::vector<SeedInstruction>{}, 1);
    MosquitoSubmodel b(100, std::vector<SeedInstruction>{}, 999);
    const ScenarioSpec spec = make_seed_spec();
    a.seed_scenario(spec, fake_locate);
    b.seed_scenario(spec, fake_locate);

    const MosquitoSoA& sa = a.soa();
    const MosquitoSoA& sb = b.soa();
    EXPECT_EQ(sa.n_alive, sb.n_alive);
    EXPECT_EQ(sa.uid, sb.uid);
    EXPECT_EQ(sa.patch_id, sb.patch_id);
    EXPECT_EQ(sa.row, sb.row);
    EXPECT_EQ(sa.col, sb.col);
    EXPECT_EQ(sa.stage, sb.stage);
    EXPECT_EQ(sa.sex, sb.sex);
    EXPECT_EQ(sa.lon, sb.lon);
    EXPECT_EQ(sa.lat, sb.lat);
    EXPECT_EQ(sa.gonotrophic_state, sb.gonotrophic_state);
    EXPECT_EQ(sa.gonotrophic_timer, sb.gonotrophic_timer);
    EXPECT_EQ(sa.vector_state, sb.vector_state);
    EXPECT_EQ(sa.stage_age, sb.stage_age);
    EXPECT_EQ(sa.development_progress, sb.development_progress);
    EXPECT_EQ(sa.parasite_eip_progress, sb.parasite_eip_progress);

    for (const AquaticStage st : {AquaticStage::EGG, AquaticStage::LARVA, AquaticStage::PUPA}) {
        EXPECT_EQ(a.cohort_bank().count_by_stage(st), b.cohort_bank().count_by_stage(st));
    }
}

TEST(ScenarioSeeding, SeedScenarioWithEmptySpecSeedsNothing) {
    MosquitoSubmodel sub(100, std::vector<SeedInstruction>{}, 1);
    ScenarioSpec spec;
    spec.id = "empty";
    sub.seed_scenario(spec, fake_locate);
    EXPECT_EQ(sub.soa().n_alive, 0);
    EXPECT_EQ(sub.cohort_bank().total_aquatic(), 0);
}

// ===========================================================================
// AquaticCohortBank::seed_streams
// ===========================================================================

namespace {

AquaticCohortBank make_seeded_bank(uint64_t master) {
    AquaticCohortBank bank;
    bank.seed_streams(master);
    bank.seed_stage(0, AquaticStage::EGG, 0, 5000, 0.0f);
    bank.seed_stage(0, AquaticStage::LARVA, 2, 5000, 0.3f);
    bank.seed_stage(1, AquaticStage::PUPA, 0, 5000, 0.0f);
    return bank;
}

std::vector<PatchState> make_wet_patches() {
    std::vector<PatchState> ps(2);
    for (int64_t i = 0; i < 2; ++i) {
        PatchState& p = ps[static_cast<size_t>(i)];
        p.patch_id = i;
        p.row = 0;
        p.col = static_cast<int32_t>(i);
        p.activated = true;
        p.rain_d = 30.0f;
        p.temp_d = 25.0f;
        p.habitat_avail = 1.0f;
        p.k_habitat = 2000.0f;
        p.salinity_ppt = 0.0f;
    }
    return ps;
}

std::vector<int64_t> run_bank_days(AquaticCohortBank& bank, int days) {
    const auto ps = make_wet_patches();
    const RuntimeOverrides overrides{};
    for (int d = 0; d < days; ++d) bank.advance_day(ps, overrides);
    std::vector<int64_t> counts;
    for (const auto& c : bank.cohorts()) counts.push_back(c.count);
    return counts;
}

int64_t sum_counts(const std::vector<int64_t>& v) {
    int64_t s = 0;
    for (const int64_t x : v) s += x;
    return s;
}

}  // namespace

TEST(ScenarioSeeding, SameMasterSeedGivesSameMortality) {
    AquaticCohortBank a = make_seeded_bank(7);
    AquaticCohortBank b = make_seeded_bank(7);
    const int64_t before = a.total_aquatic();
    ASSERT_EQ(before, 15000);

    const auto ca = run_bank_days(a, 10);
    const auto cb = run_bank_days(b, 10);
    EXPECT_EQ(ca, cb);
    EXPECT_EQ(a.total_aquatic(), b.total_aquatic());
    // Non-vacuous: the stochastic mortality really removed individuals.
    EXPECT_LT(sum_counts(ca), before);
}

TEST(ScenarioSeeding, DifferentMasterSeedGivesDifferentMortality) {
    AquaticCohortBank a = make_seeded_bank(7);
    AquaticCohortBank b = make_seeded_bank(8);
    const auto ca = run_bank_days(a, 10);
    const auto cb = run_bank_days(b, 10);
    EXPECT_NE(ca, cb);
}

// ===========================================================================
// CoordinatorModel::register_scenario_cell
// ===========================================================================

TEST(ScenarioSeeding, RegisterScenarioCellAddsCandidateOutsideFloor) {
    const std::filesystem::path nc = scratch_path("coord_zero.nc");
    std::filesystem::remove(nc);
    // Zero static planes: no cell passes the candidate floor on its own.
    write_env_nc(nc, 1, 4, 4, 0.0f);

    const AOI aoi = make_aoi_4x4();
    auto climate = std::make_shared<ClimateEngine>();
    climate->load_from_env_nc(nc.string(), aoi);
    CoordinatorModel coord(aoi, climate, HabitatEngine{}, 1, make_date(2024, 1, 1));

    const int64_t pid = coord.register_scenario_cell(1, 2);
    EXPECT_GE(pid, 0);
    // Registering the same cell again returns the same stable pid.
    EXPECT_EQ(coord.register_scenario_cell(1, 2), pid);

    coord.update_habitat_day();
    const auto states = coord.to_dataframe();
    ASSERT_EQ(states.size(), 1u);
    EXPECT_EQ(states[0].row, 1);
    EXPECT_EQ(states[0].col, 2);
    EXPECT_EQ(states[0].patch_id, pid);

    std::filesystem::remove(nc);
}

TEST(ScenarioSeeding, RegisterScenarioCellRejectsCellOutsideGrid) {
    const std::filesystem::path nc = scratch_path("coord_bounds.nc");
    std::filesystem::remove(nc);
    write_env_nc(nc, 1, 4, 4, 0.0f);

    const AOI aoi = make_aoi_4x4();
    auto climate = std::make_shared<ClimateEngine>();
    climate->load_from_env_nc(nc.string(), aoi);
    CoordinatorModel coord(aoi, climate, HabitatEngine{}, 1, make_date(2024, 1, 1));

    EXPECT_THROW(coord.register_scenario_cell(4, 0), std::runtime_error);
    EXPECT_THROW(coord.register_scenario_cell(0, -1), std::runtime_error);

    std::filesystem::remove(nc);
}
