// SPDX-License-Identifier: MIT
// debug_parquet_writer.cpp — see debug_parquet_writer.hpp.
#include "mal_abm_fast/debug_parquet_writer.hpp"

#include <arrow/api.h>
#include <arrow/io/file.h>
#include <parquet/arrow/writer.h>

#include <cmath>
#include <filesystem>
#include <memory>
#include <stdexcept>

#include "mal_abm_fast/aoi.hpp"
#include "mal_abm_fast/engine.hpp"
#include "mal_abm_fast/host_cascade.hpp"

namespace mal_abm_fast {

namespace {

const char* gono_name(uint8_t s) {
    switch (static_cast<GonotrophicState>(s)) {
        case GonotrophicState::TENERAL: return "TENERAL";
        case GonotrophicState::MATE_SEEKING: return "MATE_SEEKING";
        case GonotrophicState::HOST_SEEKING: return "HOST_SEEKING";
        case GonotrophicState::HOST_APPROACH: return "HOST_APPROACH";
        case GonotrophicState::PROBING: return "PROBING";
        case GonotrophicState::BLOOD_FED: return "BLOOD_FED";
        case GonotrophicState::RESTING: return "RESTING";
        case GonotrophicState::EGG_MATURING: return "EGG_MATURING";
        case GonotrophicState::GRAVID: return "GRAVID";
        case GonotrophicState::OVIPOSITION_SEEKING: return "OVIPOSITION_SEEKING";
        case GonotrophicState::OVIPOSITING: return "OVIPOSITING";
    }
    return "UNKNOWN";
}
const char* vector_name(uint8_t s) {
    switch (static_cast<VectorTransmissionState>(s)) {
        case VectorTransmissionState::SUSCEPTIBLE: return "S";
        case VectorTransmissionState::EXPOSED: return "E";
        case VectorTransmissionState::INFECTIOUS: return "I";
    }
    return "?";
}
const char* human_name(uint8_t s) {
    switch (static_cast<HumanState>(s)) {
        case HumanState::SUSCEPTIBLE: return "S";
        case HumanState::EXPOSED: return "E";
        case HumanState::INFECTIOUS: return "I";
        case HumanState::RECOVERED: return "R";
    }
    return "?";
}
const char* host_name(HostType h) {
    switch (h) {
        case HostType::HUMAN: return "HUMAN";
        case HostType::CATTLE: return "CATTLE";
        case HostType::GOAT: return "GOAT";
        case HostType::SHEEP: return "SHEEP";
        case HostType::OTHER: return "OTHER";
    }
    return "?";
}

void check(const arrow::Status& st) {
    if (!st.ok()) throw std::runtime_error("debug parquet: " + st.ToString());
}

template <class Builder, class T>
std::shared_ptr<arrow::Array> column(const std::vector<T>& v) {
    Builder b;
    check(b.AppendValues(v));
    std::shared_ptr<arrow::Array> out;
    check(b.Finish(&out));
    return out;
}
std::shared_ptr<arrow::Array> str_column(const std::vector<std::string>& v) {
    arrow::StringBuilder b;
    for (const auto& s : v) check(b.Append(s));
    std::shared_ptr<arrow::Array> out;
    check(b.Finish(&out));
    return out;
}
std::shared_ptr<arrow::Array> bool_column(const std::vector<uint8_t>& v) {
    arrow::BooleanBuilder b;
    for (const uint8_t x : v) check(b.Append(x != 0));
    std::shared_ptr<arrow::Array> out;
    check(b.Finish(&out));
    return out;
}

void write_table(const std::string& path,
                 const std::shared_ptr<arrow::Table>& table) {
    std::filesystem::path p(path);
    if (p.has_parent_path()) std::filesystem::create_directories(p.parent_path());
    auto out = arrow::io::FileOutputStream::Open(path);
    if (!out.ok()) throw std::runtime_error("debug parquet: cannot open " + path + ": " + out.status().ToString());
    check(parquet::arrow::WriteTable(*table, arrow::default_memory_pool(), *out, 1 << 20));
}

}  // namespace

struct DebugParquetWriter::Impl {
    std::string stem;
    // agents
    std::vector<int32_t> a_day; std::vector<int64_t> a_uid; std::vector<int8_t> a_sex;
    std::vector<float> a_x, a_y; std::vector<int32_t> a_row, a_col, a_age;
    std::vector<std::string> a_gono, a_stage, a_vec; std::vector<int64_t> a_patch;
    // humans
    std::vector<int32_t> h_day; std::vector<int64_t> h_id; std::vector<float> h_x, h_y;
    std::vector<int32_t> h_cell, h_timer; std::vector<std::string> h_state;
    // bites
    std::vector<int32_t> b_day, b_row, b_col; std::vector<int8_t> b_phase;
    std::vector<int64_t> b_uid, b_hid; std::vector<std::string> b_host;
    std::vector<float> b_x, b_y; std::vector<uint8_t> b_inf, b_vinf, b_new;
};

DebugParquetWriter::DebugParquetWriter(std::string stem) : impl_(new Impl) { impl_->stem = std::move(stem); }
DebugParquetWriter::~DebugParquetWriter() { delete impl_; }
int64_t DebugParquetWriter::n_agent_rows() const { return static_cast<int64_t>(impl_->a_day.size()); }
int64_t DebugParquetWriter::n_human_rows() const { return static_cast<int64_t>(impl_->h_day.size()); }
int64_t DebugParquetWriter::n_bite_rows() const { return static_cast<int64_t>(impl_->b_day.size()); }

void DebugParquetWriter::record_day(const Engine& engine, int day) {
    Impl& m = *impl_;
    const AOI& aoi = engine.aoi();
    const MosquitoSoA& soa = engine.submodel().agents();
    for (int64_t i = 0; i < soa.n_alive; ++i) {
        const size_t si = static_cast<size_t>(i);
        if (soa.stage[si] != 1) continue;
        float x = si < soa.pos_x.size() ? soa.pos_x[si] : std::nanf("");
        float y = si < soa.pos_y.size() ? soa.pos_y[si] : std::nanf("");
        if (std::isnan(x) || std::isnan(y)) {
            const XY xy = lonlat_to_xy(aoi, soa.lon[si], soa.lat[si]);
            x = static_cast<float>(xy.x);
            y = static_cast<float>(xy.y);
        }
        m.a_day.push_back(day);
        m.a_uid.push_back(soa.uid[si]);
        m.a_sex.push_back(static_cast<int8_t>(soa.sex[si]));
        m.a_x.push_back(x);
        m.a_y.push_back(y);
        m.a_row.push_back(soa.row[si]);
        m.a_col.push_back(soa.col[si]);
        m.a_age.push_back(soa.stage_age[si]);
        m.a_gono.emplace_back(gono_name(soa.gonotrophic_state[si]));
        m.a_stage.emplace_back(cascade_stage_name(static_cast<CascadeStage>(
            si < soa.cascade_stage.size() ? soa.cascade_stage[si] : 0)));
        m.a_vec.emplace_back(vector_name(soa.vector_state[si]));
        m.a_patch.push_back(soa.patch_id[si]);
    }
    if (const HumanCompartmentGrid* hg = engine.human_population()) {
        const HumanSoA& p = hg->people();
        for (size_t i = 0; i < p.size(); ++i) {
            if (p.state[i] == static_cast<uint8_t>(HumanState::SUSCEPTIBLE)) continue;   // only E, I, R
            m.h_day.push_back(day);
            m.h_id.push_back(p.human_id[i]);
            m.h_cell.push_back(p.cell_id[i]);
            m.h_x.push_back(p.cur_x[i]);
            m.h_y.push_back(p.cur_y[i]);
            m.h_timer.push_back(p.timer[i]);
            m.h_state.emplace_back(human_name(p.state[i]));
        }
    }
    for (const BiteEvent& e : engine.submodel().bite_ledger().events_today()) {
        m.b_day.push_back(day);
        m.b_phase.push_back(static_cast<int8_t>(e.phase));
        m.b_uid.push_back(e.mosquito_uid);
        m.b_hid.push_back(e.human_id);
        m.b_host.emplace_back(host_name(e.host));
        m.b_row.push_back(e.row);
        m.b_col.push_back(e.col);
        m.b_x.push_back(e.x);
        m.b_y.push_back(e.y);
        m.b_inf.push_back(e.infectious_vector);
        m.b_vinf.push_back(e.vector_infected);
        m.b_new.push_back(e.new_infection);
    }
}

std::vector<std::string> DebugParquetWriter::finish() {
    Impl& m = *impl_;
    std::vector<std::string> paths;

    {   // agents
        auto schema = arrow::schema({
            arrow::field("day", arrow::int32()), arrow::field("uid", arrow::int64()),
            arrow::field("sex", arrow::int8()), arrow::field("x_m", arrow::float32()),
            arrow::field("y_m", arrow::float32()), arrow::field("row", arrow::int32()),
            arrow::field("col", arrow::int32()), arrow::field("age_days", arrow::int32()),
            arrow::field("gonotrophic_state", arrow::utf8()),
            arrow::field("cascade_stage", arrow::utf8()),
            arrow::field("vector_state", arrow::utf8()), arrow::field("patch_id", arrow::int64())});
        auto t = arrow::Table::Make(schema, {
            column<arrow::Int32Builder>(m.a_day), column<arrow::Int64Builder>(m.a_uid),
            column<arrow::Int8Builder>(m.a_sex), column<arrow::FloatBuilder>(m.a_x),
            column<arrow::FloatBuilder>(m.a_y), column<arrow::Int32Builder>(m.a_row),
            column<arrow::Int32Builder>(m.a_col), column<arrow::Int32Builder>(m.a_age),
            str_column(m.a_gono), str_column(m.a_stage), str_column(m.a_vec),
            column<arrow::Int64Builder>(m.a_patch)});
        paths.push_back(m.stem + "_agents.parquet");
        write_table(paths.back(), t);
    }
    {   // humans (E, I, R only)
        auto schema = arrow::schema({
            arrow::field("day", arrow::int32()), arrow::field("human_id", arrow::int64()),
            arrow::field("cell_id", arrow::int32()), arrow::field("x_m", arrow::float32()),
            arrow::field("y_m", arrow::float32()), arrow::field("state", arrow::utf8()),
            arrow::field("timer_days", arrow::int32())});
        auto t = arrow::Table::Make(schema, {
            column<arrow::Int32Builder>(m.h_day), column<arrow::Int64Builder>(m.h_id),
            column<arrow::Int32Builder>(m.h_cell), column<arrow::FloatBuilder>(m.h_x),
            column<arrow::FloatBuilder>(m.h_y), str_column(m.h_state),
            column<arrow::Int32Builder>(m.h_timer)});
        paths.push_back(m.stem + "_humans.parquet");
        write_table(paths.back(), t);
    }
    {   // bites
        auto schema = arrow::schema({
            arrow::field("day", arrow::int32()), arrow::field("phase", arrow::int8()),
            arrow::field("mosquito_uid", arrow::int64()), arrow::field("human_id", arrow::int64()),
            arrow::field("host", arrow::utf8()), arrow::field("row", arrow::int32()),
            arrow::field("col", arrow::int32()), arrow::field("x_m", arrow::float32()),
            arrow::field("y_m", arrow::float32()),
            arrow::field("infectious_vector", arrow::boolean()),
            arrow::field("vector_infected", arrow::boolean()),
            arrow::field("new_infection", arrow::boolean())});
        auto t = arrow::Table::Make(schema, {
            column<arrow::Int32Builder>(m.b_day), column<arrow::Int8Builder>(m.b_phase),
            column<arrow::Int64Builder>(m.b_uid), column<arrow::Int64Builder>(m.b_hid),
            str_column(m.b_host), column<arrow::Int32Builder>(m.b_row),
            column<arrow::Int32Builder>(m.b_col), column<arrow::FloatBuilder>(m.b_x),
            column<arrow::FloatBuilder>(m.b_y), bool_column(m.b_inf),
            bool_column(m.b_vinf), bool_column(m.b_new)});
        paths.push_back(m.stem + "_bites.parquet");
        write_table(paths.back(), t);
    }
    {   // mating: schema only until the male layer exists (Paso 8)
        auto schema = arrow::schema({
            arrow::field("day", arrow::int32()), arrow::field("male_uid", arrow::int64()),
            arrow::field("female_uid", arrow::int64()), arrow::field("swarm_site_id", arrow::int32()),
            arrow::field("inseminated", arrow::boolean())});
        std::vector<int32_t> e32; std::vector<int64_t> e64; std::vector<uint8_t> eb;
        auto t = arrow::Table::Make(schema, {
            column<arrow::Int32Builder>(e32), column<arrow::Int64Builder>(e64),
            column<arrow::Int64Builder>(e64), column<arrow::Int32Builder>(e32), bool_column(eb)});
        paths.push_back(m.stem + "_mating.parquet");
        write_table(paths.back(), t);
    }
    return paths;
}

}  // namespace mal_abm_fast
