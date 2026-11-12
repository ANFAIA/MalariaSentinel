// SPDX-License-Identifier: MIT
#include <chrono>
#include <filesystem>
#include <fstream>
#include <string>
#include <vector>

#include <gtest/gtest.h>
#include <nlohmann/json.hpp>

#include "mal_abm_fast/transmission_debug_log.hpp"

namespace mal_abm_fast {
namespace {

TEST(TransmissionDebugLog, WritesVersionedMetadataDailyStatsAndHostGroupedBites) {
    const auto nonce = std::chrono::steady_clock::now().time_since_epoch().count();
    const std::filesystem::path path = std::filesystem::temp_directory_path() /
        ("malaria_transmission_debug_" + std::to_string(nonce) + ".jsonl");
    struct RemoveFile {
        std::filesystem::path path;
        ~RemoveFile() {
            std::error_code ec;
            std::filesystem::remove(path, ec);
        }
    } cleanup{path};

    TransmissionParams params;
    params.initial_vector_infected_frac = 0.125;
    params.initial_human_prevalence = 0.025;
    params.human_seeding_mode = "explicit";
    params.human_outbreak_day = 4;
    params.human_outbreak_foci = 2;
    params.human_outbreak_cases = 17.0;
    TransmissionDebugRunMetadata run;
    run.aoi = "ghana";
    run.year = 2024;
    run.month = 2;
    run.seed = 41;
    run.n_rollouts = 3;
    run.rollout_index = 1;
    run.days = 59;
    run.human_cluster_radius_km = 2.5;

    TransmissionDailyStats stats;
    stats.day = 58;
    stats.total_humans = 121.0;
    stats.human_s = 100.0;
    stats.human_e = 11.0;
    stats.human_i = 7.0;
    stats.human_r = 3.0;
    stats.human_incidence = 2.5;
    stats.human_prevalence = 7.0 / 121.0;
    stats.vector_s = 130;
    stats.vector_e = 17;
    stats.vector_i = 5;
    stats.vector_total = 152;
    stats.vector_seeded_initial = 6;
    stats.vector_new_exposures = 2;
    stats.vector_eip_completions = 1;

    BiteLedger bites;
    bites.record_attempt(0, 0, HostType::HUMAN);
    bites.record_attempt(0, 0, HostType::HUMAN);
    bites.record_infectious_success(0, 0, HostType::HUMAN);
    bites.record_success(0, 0, HostType::HUMAN);
    bites.record_attempt(0, 1, HostType::CATTLE);
    bites.record_infectious_success(0, 1, HostType::CATTLE);
    bites.record_attempt(0, 2, HostType::GOAT);
    bites.record_infectious_success(0, 2, HostType::GOAT);

    {
        TransmissionDebugLog log(path.string(), run, params);
        log.record_day(58, std::chrono::sys_days{
            std::chrono::year{2024} / std::chrono::February / std::chrono::day{29}},
            stats, bites);
    }

    std::ifstream input(path);
    ASSERT_TRUE(input.is_open());
    std::vector<nlohmann::json> records;
    for (std::string line; std::getline(input, line);) {
        ASSERT_FALSE(line.empty());
        records.push_back(nlohmann::json::parse(line));
    }
    ASSERT_EQ(records.size(), 2u);

    const auto& metadata = records[0];
    EXPECT_EQ(metadata.at("record_type"), "metadata");
    EXPECT_EQ(metadata.at("schema"), "malaria-sentinel.transmission-debug");
    EXPECT_EQ(metadata.at("schema_version"), 1);
    EXPECT_EQ(metadata.at("run").at("aoi"), "ghana");
    EXPECT_EQ(metadata.at("run").at("start_date"), "2024-02-01");
    EXPECT_EQ(metadata.at("run").at("seed"), 41);
    EXPECT_EQ(metadata.at("run").at("n_rollouts"), 3);
    EXPECT_EQ(metadata.at("run").at("rollout_index"), 1);
    EXPECT_DOUBLE_EQ(
        metadata.at("parameters").at("initial_vector_infected_frac").get<double>(),
        0.125);
    EXPECT_DOUBLE_EQ(
        metadata.at("parameters").at("initial_human_prevalence").get<double>(),
        0.025);
    EXPECT_EQ(metadata.at("parameters").at("human_seeding_mode"), "explicit");
    EXPECT_EQ(metadata.at("parameters").at("human_outbreak_day"), 4);
    EXPECT_EQ(metadata.at("parameters").at("human_outbreak_foci"), 2);
    EXPECT_DOUBLE_EQ(
        metadata.at("parameters").at("human_outbreak_cases").get<double>(),
        17.0);

    const auto& daily = records[1];
    EXPECT_EQ(daily.at("record_type"), "daily");
    EXPECT_EQ(daily.at("day_index"), 58);
    EXPECT_EQ(daily.at("day"), 59);
    EXPECT_EQ(daily.at("date"), "2024-02-29");
    const auto& humans = daily.at("humans");
    EXPECT_DOUBLE_EQ(humans.at("susceptible").get<double>(), 100.0);
    EXPECT_DOUBLE_EQ(humans.at("exposed").get<double>(), 11.0);
    EXPECT_DOUBLE_EQ(humans.at("infectious").get<double>(), 7.0);
    EXPECT_DOUBLE_EQ(humans.at("recovered").get<double>(), 3.0);
    EXPECT_DOUBLE_EQ(humans.at("total").get<double>(), 121.0);
    EXPECT_DOUBLE_EQ(humans.at("incidence").get<double>(), 2.5);
    EXPECT_DOUBLE_EQ(humans.at("prevalence").get<double>(), 7.0 / 121.0);

    const auto& vectors = daily.at("vectors");
    EXPECT_EQ(vectors.at("susceptible"), 130);
    EXPECT_EQ(vectors.at("exposed"), 17);
    EXPECT_EQ(vectors.at("infectious"), 5);
    EXPECT_EQ(vectors.at("initial_seeded"), 6);
    EXPECT_EQ(vectors.at("new_exposures"), 2);
    EXPECT_EQ(vectors.at("eip_completions"), 1);

    const auto& grouped_bites = daily.at("bites");
    EXPECT_EQ(grouped_bites.at("human").at("attempts"), 2);
    EXPECT_EQ(grouped_bites.at("human").at("successful"), 2);
    EXPECT_EQ(grouped_bites.at("human").at("infectious"), 1);
    EXPECT_EQ(grouped_bites.at("animal").at("attempts"), 2);
    EXPECT_EQ(grouped_bites.at("animal").at("successful"), 2);
    EXPECT_EQ(grouped_bites.at("animal").at("infectious"), 2);
    EXPECT_EQ(grouped_bites.at("by_host_type").at("human").at("infectious"), 1);
    EXPECT_EQ(grouped_bites.at("by_host_type").at("cattle").at("infectious"), 1);
    EXPECT_EQ(grouped_bites.at("by_host_type").at("goat").at("infectious"), 1);
    const auto& bite_events = grouped_bites.at("events_by_cell");
    ASSERT_EQ(bite_events.size(), 3u);
    EXPECT_EQ(bite_events[0].at("row"), 0);
    EXPECT_EQ(bite_events[0].at("col"), 0);
    EXPECT_EQ(bite_events[0].at("host"), "human");
    EXPECT_EQ(bite_events[0].at("infectious"), 1);
    EXPECT_EQ(bite_events[1].at("col"), 1);
    EXPECT_EQ(bite_events[1].at("host"), "cattle");
    EXPECT_EQ(bite_events[1].at("infectious"), 1);
    EXPECT_EQ(bite_events[2].at("col"), 2);
    EXPECT_EQ(bite_events[2].at("host"), "goat");
    EXPECT_EQ(bite_events[2].at("infectious"), 1);
}

}  // namespace
}  // namespace mal_abm_fast
