// SPDX-License-Identifier: MIT
// transmission_debug_log.cpp — versioned per-day transmission debug JSONL.
#include "mal_abm_fast/transmission_debug_log.hpp"

#include <array>
#include <iomanip>
#include <iostream>
#include <sstream>

#include <nlohmann/json.hpp>

namespace mal_abm_fast {
namespace {

using nlohmann::json;

std::string iso_date(std::chrono::sys_days date) {
    const std::chrono::year_month_day ymd{date};
    std::ostringstream out;
    out << std::setfill('0') << std::setw(4) << int(ymd.year()) << '-'
        << std::setw(2) << unsigned(ymd.month()) << '-'
        << std::setw(2) << unsigned(ymd.day());
    return out.str();
}

const char* host_name(HostType host) {
    switch (host) {
    case HostType::HUMAN: return "human";
    case HostType::CATTLE: return "cattle";
    case HostType::GOAT: return "goat";
    case HostType::SHEEP: return "sheep";
    case HostType::OTHER: return "other";
    }
    return "unknown";
}

struct BiteCounts {
    int64_t attempts = 0;
    int64_t successful = 0;
    int64_t infectious = 0;

    void add(const BiteEventAggregate& event) {
        attempts += event.attempts;
        successful += event.successful_meals;
        infectious += event.infectious_meals;
    }

    json to_json() const {
        return json{
            {"attempts", attempts},
            {"successful", successful},
            // BiteLedger defines this as a successful meal delivered by an
            // infectious vector (I_V), independent of the host category.
            {"infectious", infectious},
        };
    }
};

json parameters_json(const TransmissionParams& p,
                     double human_cluster_radius_km) {
    return json{
        {"beta_hv", p.beta_hv},
        {"beta_vh", p.beta_vh},
        {"human_incubation_days", p.human_incubation_days},
        {"human_infectious_days", p.human_infectious_days},
        {"immunity_duration_days", p.immunity_duration_days},
        {"immunity_enabled", p.immunity_enabled},
        {"initial_human_prevalence", p.initial_human_prevalence},
        {"initial_vector_infected_frac", p.initial_vector_infected_frac},
        {"initial_infected_path", p.initial_infected_path},
        {"human_seeding_mode", p.human_seeding_mode},
        {"human_outbreak_day", p.human_outbreak_day},
        {"human_outbreak_foci", p.human_outbreak_foci},
        {"human_outbreak_cases", p.human_outbreak_cases},
        {"human_min_cell_pop", p.human_min_cell_pop},
        {"human_foci_coords", p.human_foci_coords},
        {"human_cluster_radius_km", human_cluster_radius_km},
        {"human_cluster_radius_cells", p.human_cluster_radius_cells},
        {"human_outbreak_min_density", p.human_outbreak_min_density},
        {"human_cluster_max_core_pop", p.human_cluster_max_core_pop},
        {"focus_threshold", p.focus_threshold},
    };
}

}  // namespace

TransmissionDebugLog::TransmissionDebugLog(
    const std::string& path,
    const TransmissionDebugRunMetadata& run,
    const TransmissionParams& params) noexcept
    : path_(path) {
    try {
        stream_.open(path_, std::ios::out | std::ios::trunc);
        if (!stream_.is_open()) {
            warn("cannot open output file");
            return;
        }
        usable_ = true;
        const auto first_day = std::chrono::sys_days{
            std::chrono::year{run.year} /
            std::chrono::month{static_cast<unsigned>(run.month)} /
            std::chrono::day{1}};
        const json metadata{
            {"record_type", "metadata"},
            {"schema", "malaria-sentinel.transmission-debug"},
            {"schema_version", 1},
            {"run", {
                {"aoi", run.aoi},
                {"start_date", iso_date(first_day)},
                {"year", run.year},
                {"month", run.month},
                {"days_requested", run.days},
                {"seed", run.seed},
                {"n_rollouts", run.n_rollouts},
                {"rollout_index", run.rollout_index},
            }},
            {"parameters", parameters_json(params, run.human_cluster_radius_km)},
            {"bite_semantics", {
                {"infectious", "successful meal delivered by an infectious vector (I_V)"},
                {"animal", "combined non-human HostType values; see by_host_type"},
            }},
        };
        write_record(metadata.dump());
    } catch (const std::exception& e) {
        usable_ = false;
        warn(std::string("failed to write metadata: ") + e.what());
    } catch (...) {
        usable_ = false;
        warn("failed to write metadata: unknown error");
    }
}

TransmissionDebugLog::~TransmissionDebugLog() {
    try {
        if (stream_.is_open()) {
            stream_.flush();
            if (!stream_) warn("flush failed");
            stream_.close();
            if (stream_.fail()) warn("close failed");
        }
    } catch (...) {
        warn("close failed with an unknown error");
    }
}

void TransmissionDebugLog::record_day(
    int32_t day_index,
    std::chrono::sys_days date,
    const TransmissionDailyStats& stats,
    const BiteLedger& bite_ledger) noexcept {
    if (!usable_) return;
    try {
        std::array<BiteCounts, 5> by_host{};
        BiteCounts human;
        BiteCounts animal;
        json cell_events = json::array();
        for (const auto& event : bite_ledger.today()) {
            const auto host_i = static_cast<size_t>(event.host);
            if (host_i < by_host.size()) by_host[host_i].add(event);
            if (event.host == HostType::HUMAN) {
                human.add(event);
            } else {
                animal.add(event);
            }
            cell_events.push_back({
                {"row", event.row},
                {"col", event.col},
                {"host", host_name(event.host)},
                {"attempts", event.attempts},
                {"successful", event.successful_meals},
                {"infectious", event.infectious_meals},
            });
        }
        json host_breakdown = json::object();
        constexpr std::array<HostType, 5> host_types{
            HostType::HUMAN, HostType::CATTLE, HostType::GOAT,
            HostType::SHEEP, HostType::OTHER};
        for (size_t i = 0; i < host_types.size(); ++i) {
            host_breakdown[host_name(host_types[i])] = by_host[i].to_json();
        }
        const json daily{
            {"record_type", "daily"},
            {"day_index", day_index},
            {"day", day_index + 1},
            {"date", iso_date(date)},
            {"humans", {
                {"susceptible", stats.human_s},
                {"exposed", stats.human_e},
                {"infectious", stats.human_i},
                {"recovered", stats.human_r},
                {"total", stats.total_humans},
                {"incidence", stats.human_incidence},
                {"prevalence", stats.human_prevalence},
            }},
            {"vectors", {
                {"susceptible", stats.vector_s},
                {"exposed", stats.vector_e},
                {"infectious", stats.vector_i},
                {"initial_seeded", stats.vector_seeded_initial},
                {"new_exposures", stats.vector_new_exposures},
                {"eip_completions", stats.vector_eip_completions},
            }},
            {"bites", {
                {"human", human.to_json()},
                {"animal", animal.to_json()},
                {"by_host_type", std::move(host_breakdown)},
                {"events_by_cell", std::move(cell_events)},
            }},
        };
        write_record(daily.dump());
    } catch (const std::exception& e) {
        usable_ = false;
        warn(std::string("failed to serialize daily record: ") + e.what());
    } catch (...) {
        usable_ = false;
        warn("failed to serialize daily record: unknown error");
    }
}

void TransmissionDebugLog::write_record(const std::string& record) noexcept {
    if (!usable_) return;
    try {
        stream_ << record << '\n';
        if (!stream_) {
            usable_ = false;
            warn("write failed");
        }
    } catch (...) {
        usable_ = false;
        warn("write failed with an unknown error");
    }
}

void TransmissionDebugLog::warn(const std::string& message) noexcept {
    try {
        std::cerr << "abm_run: transmission debug log '" << path_ << "': "
                  << message << "; simulation continues\n";
    } catch (...) {
        // Diagnostics must not turn a logging problem into a simulation error.
    }
}

}  // namespace mal_abm_fast
