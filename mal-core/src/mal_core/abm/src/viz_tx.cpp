// SPDX-License-Identifier: MIT
// viz_tx.cpp — native transmission GIF renderer (plan 05, "mapa 2").
//
// Draws, per simulated day, from LIVE engine state (no state COGs read
// back, no model input, no engine RNG consumed):
//
//   1. base — biteable cells (with humans / animal-only / empty)
//   2. daily movement — top OD flows of the day (human cyan, livestock
//      brown) + a DAY vs NIGHT H_eff inset
//   3. mosquitoes — identical symbology to map 1
//   4. today's bites — squares at the bitten cell, red ring if infectious
//   5. human infection — red I_H contour + new-incidence dots
//
// Deliberately excluded (plan 05 §6): S(i,t), habitat classes, K, aquatic
// cohorts, pluvial z, patch markers, JRC. Strictly complementary to map 1.
#include "mal_abm_fast/viz_tx.hpp"

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <filesystem>
#include <limits>
#include <memory>
#include <string>
#include <utility>
#include <vector>

#include "mal_abm_fast/aoi.hpp"
#include "mal_abm_fast/bite_ledger.hpp"
#include "mal_abm_fast/effective_host_landscape.hpp"
#include "mal_abm_fast/engine.hpp"
#include "mal_abm_fast/gonotrophic_cycle.hpp"
#include "mal_abm_fast/habitat_engine.hpp"
#include "mal_abm_fast/host_landscape.hpp"
#include "mal_abm_fast/human_state.hpp"
#include "mal_abm_fast/mobility_schedule.hpp"
#include "mal_abm_fast/mosquito_state.hpp"
#include "mal_abm_fast/species_params.hpp"
#include "mal_abm_fast/transmission.hpp"
#include "mal_abm_fast/viz_common.hpp"
#include "mal_abm_fast/wire.hpp"

namespace mal_abm_fast {
namespace {

// ---------------------------------------------------------------------------
// Map-2 palette (chrome + mosquito colours come from viz_common).
// ---------------------------------------------------------------------------

// Layer 1: biteable-cell base classes.
constexpr Color kHumanCellLow{214, 196, 150, 255};   // arena (few humans)
constexpr Color kHumanCellHigh{196, 44, 44, 255};    // red (many humans)
constexpr Color kAnimalCellLow{44, 58, 40, 255};     // dark olive (few)
constexpr Color kAnimalCellHigh{150, 190, 80, 255};  // bright olive (many)
constexpr Color kEmptyCell{30, 33, 39, 255};         // no hosts / sea
constexpr Color kHumanOutline{245, 240, 225, 255};   // light contour on humans

// Layer 2: movement arrows.
constexpr Color kMoveHuman{90, 210, 235, 255};     // cyan
constexpr Color kMoveLivestock{170, 120, 70, 255}; // brown

// Layer 5: bite markers.
constexpr Color kBiteHuman{255, 210, 90, 255};
constexpr Color kBiteAnimal{160, 200, 90, 255};

// Panel 1: SEIR compartments.
constexpr Color kSEIR_S{120, 150, 200, 255};
constexpr Color kSEIR_E{235, 180, 60, 255};
constexpr Color kSEIR_I{220, 60, 60, 255};
constexpr Color kSEIR_R{90, 190, 120, 255};
constexpr Color kIncidence{255, 150, 80, 255};

// How the human / animal cell ramp is normalised (log1p over the run max).
double cell_t(double v, double run_max) {
    if (run_max <= 0.0) return 0.0;
    return std::clamp(std::log1p(v) / std::log1p(run_max), 0.0, 1.0);
}

// Log-scale value → pixel row inside a plot rect (thin wrapper shared with
// map 1 via viz_common::plot_y).

// --- series panels ------------------------------------------------------

// Panel 1: human SEIR on a log axis + incidence bars underneath.
void draw_seir_panel(Canvas& cv, int x, int y, int w, int h,
                     const std::vector<TransmissionDailyStats>& hist) {
    draw_panel_frame(cv, x, y, w, h, "SEIR / inc");
    const int px = x + 8;
    const int py = y + 26;
    const int axis_w = text_w("00", 2) + 6;
    const int pw = std::max(20, w - 16 - axis_w);
    // Top 72% for the SEIR curves, bottom 28% for incidence bars.
    const int seir_h = std::max(20, static_cast<int>(0.72 * (h - 34)));
    const int inc_h = std::max(8, (h - 34) - seir_h - 4);
    if (pw <= 20 || hist.empty()) return;

    const int n = static_cast<int>(hist.size());
    auto sx_at = [&](int i) {
        if (n <= 1) return px + pw - 1;
        return px + (pw - 1) * i / (n - 1);
    };
    // Bars occupy per-day slots, unlike the point/line series whose samples
    // are placed at slot centers including both plot endpoints.
    auto bar_x_at = [&](int i) { return px + pw * i / n; };

    // Decade bounds over the whole run (monotone, so no sample is clipped).
    double vmax = 1.0;
    for (const auto& s : hist) {
        vmax = std::max(vmax, std::max(s.human_s, std::max(s.human_e,
                        std::max(s.human_i, s.human_r))));
    }
    const int hi_dec = std::max(1, static_cast<int>(std::ceil(std::log10(std::max(1.0, vmax)))));
    const double vmin = 1.0;
    const double vpow = dec_pow10(hi_dec);

    for (int d = 0; d <= hi_dec; ++d) {
        const double v = dec_pow10(d);
        const int yy = plot_y(v, vmin, vpow, py, seir_h, true);
        cv.line(px, yy, px + pw - 1, yy, Color{46, 49, 58, 255});
    }

    auto series = [&](auto field, Color c) {
        for (int i = 1; i < n; ++i) {
            const double a = static_cast<double>(hist[static_cast<size_t>(i - 1)].*field);
            const double b = static_cast<double>(hist[static_cast<size_t>(i)].*field);
            const int xa = sx_at(i - 1), xb = sx_at(i);
            const int ya = plot_y(a, vmin, vpow, py, seir_h, true);
            const int yb = plot_y(b, vmin, vpow, py, seir_h, true);
            cv.line(xa, ya, xb, yb, c);
        }
        if (n == 1) {
            cv.disc(sx_at(0),
                    plot_y(static_cast<double>(hist[0].*field), vmin, vpow, py, seir_h, true),
                    2, c);
        }
    };
    series(&TransmissionDailyStats::human_s, kSEIR_S);
    series(&TransmissionDailyStats::human_e, kSEIR_E);
    series(&TransmissionDailyStats::human_i, kSEIR_I);
    series(&TransmissionDailyStats::human_r, kSEIR_R);

    // Incidence bars (new E_H per day) in the bottom strip.
    double imax = 1.0;
    for (const auto& s : hist) imax = std::max(imax, s.human_incidence);
    const int ibase = py + seir_h + 4;
    const int bw = std::max(1, (pw + n - 1) / n);
    for (int i = 0; i < n; ++i) {
        const double v = hist[static_cast<size_t>(i)].human_incidence;
        if (v <= 0.0) continue;
        const double t = std::clamp(v / imax, 0.0, 1.0);
        const int bh = static_cast<int>(std::lround(t * inc_h));
        if (bh <= 0) continue;
        cv.fill_rect(bar_x_at(i), ibase + inc_h - bh, bw, bh, kIncidence);
    }

    // Key: S / E / I / R / incidence.
    struct Key { const char* l; Color c; };
    const Key keys[5] = {{"S", kSEIR_S}, {"E", kSEIR_E}, {"I", kSEIR_I},
                         {"R", kSEIR_R}, {"inc", kIncidence}};
    int kx = x + w - 8;
    for (int i = 4; i >= 0; --i) {
        const int wl = text_w(keys[i].l, 1);
        kx -= wl;
        cv.text(kx, y + 4, keys[i].l, keys[i].c, 1);
        kx -= 7;
    }
}

// Panel 2: host-specific bites (bars) + infectious meals across hosts (line).
void draw_bites_panel(Canvas& cv, int x, int y, int w, int h,
                      const std::vector<double>& human_bites,
                      const std::vector<double>& animal_bites,
                      const std::vector<double>& inf_bites) {
    draw_panel_frame(cv, x, y, w, h, "Bites/day");
    const int px = x + 8;
    const int py = y + 26;
    const int pw = std::max(20, w - 16);
    const int ph = h - 34;
    if (pw <= 20 || ph <= 20) return;
    const int n = static_cast<int>(human_bites.size());
    if (n <= 0) return;

    double vmax = 1.0;
    for (int i = 0; i < n; ++i) {
        vmax = std::max(vmax, std::max(human_bites[static_cast<size_t>(i)],
                                       animal_bites[static_cast<size_t>(i)]));
        vmax = std::max(vmax, inf_bites[static_cast<size_t>(i)]);
    }
    auto sx_at = [&](int i) {
        if (n <= 1) return px + pw - 1;
        return px + (pw - 1) * i / (n - 1);
    };
    // Bars use bounded slots; anchoring them at sx_at(i) would extend the
    // last day's bar beyond the right edge because sx_at(n-1) is the endpoint.
    auto bar_x_at = [&](int i) { return px + pw * i / n; };
    const int bw = std::max(1, (pw + n - 1) / n);
    for (int i = 0; i < n; ++i) {
        const double hv = human_bites[static_cast<size_t>(i)];
        const double av = animal_bites[static_cast<size_t>(i)];
        const int hh = static_cast<int>(std::lround(std::clamp(hv / vmax, 0.0, 1.0) * ph));
        const int ah = static_cast<int>(std::lround(std::clamp(av / vmax, 0.0, 1.0) * ph));
        const int bx = bar_x_at(i);
        if (hh > 0) cv.fill_rect(bx, py + ph - hh, std::max(1, bw / 2), hh, kBiteHuman);
        if (ah > 0) cv.fill_rect(bx + std::max(1, bw / 2), py + ph - ah,
                                 std::max(1, bw / 2), ah, kBiteAnimal);
    }
    // Infectious-meal line across both host types (right-scaled to its own max).
    double imax = 1.0;
    for (double v : inf_bites) imax = std::max(imax, v);
    for (int i = 1; i < n; ++i) {
        const int xa = sx_at(i - 1), xb = sx_at(i);
        const int ya = py + ph - static_cast<int>(std::lround(
            std::clamp(inf_bites[static_cast<size_t>(i - 1)] / imax, 0.0, 1.0) * ph));
        const int yb = py + ph - static_cast<int>(std::lround(
            std::clamp(inf_bites[static_cast<size_t>(i)] / imax, 0.0, 1.0) * ph));
        cv.line(xa, ya, xb, yb, kInfectious);
    }
    // Key: host-specific bite bars and infectious meals for any host. The
    // `inf meals/day` line is a daily event count, not the I_V population.
    const int key_scale = 1;
    constexpr int key_gap = 7;
    int key_x = x + w - 8;
    key_x -= text_w("H", key_scale);
    cv.text(key_x, y + 4, "H", kBiteHuman, key_scale);
    key_x -= key_gap + text_w("A", key_scale);
    cv.text(key_x, y + 4, "A", kBiteAnimal, key_scale);
    key_x -= key_gap + text_w("inf meals/day", key_scale);
    cv.text(key_x, y + 4, "inf meals/day", kInfectious, key_scale);
}

// Panel 3: total infectious adult females. The first point is the actual
// pre-step seeded population; subsequent points are end-of-day vector_i counts.
void draw_vector_i_panel(Canvas& cv, int x, int y, int w, int h,
                         const std::vector<int64_t>& series) {
    draw_panel_frame(cv, x, y, w, h, "I_V total (seeded start included)");
    if (series.empty()) return;

    int64_t max_count = 0;
    for (const int64_t value : series) max_count = std::max(max_count, value);
    const int64_t axis_max = std::max<int64_t>(1, max_count);
    const int label_w = text_w(fmt_count(axis_max), 1);
    const int px = x + 8 + label_w + 8;
    const int py = y + 36;
    const int ph = std::max(2, h - 48);
    const int pw = std::max(1, x + w - 8 - px);
    const int label_y = y + h - 10;

    cv.text(x + 8, y + 23, "count", kTextDim, 1);
    cv.text(x + w - 8 - text_w("day", 1), y + 23, "day", kTextDim, 1);
    const int64_t ticks[3] = {axis_max, axis_max / 2, 0};
    int64_t previous_tick = -1;
    for (const int64_t tick : ticks) {
        if (tick == previous_tick) continue;
        previous_tick = tick;
        const int yy = plot_y(static_cast<double>(tick), 0.0,
                              static_cast<double>(axis_max), py, ph, false);
        cv.line(px, yy, px + pw - 1, yy, Color{46, 49, 58, 255});
        cv.text(x + 8, yy - 4, fmt_count(tick), kTextDim, 1);
    }

    const int n = static_cast<int>(series.size());
    auto sx_at = [&](int i) {
        if (n <= 1) return px;
        return px + (pw - 1) * i / (n - 1);
    };
    auto sy_at = [&](int i) {
        return plot_y(static_cast<double>(std::max<int64_t>(0, series[static_cast<size_t>(i)])),
                      0.0, static_cast<double>(axis_max), py, ph, false);
    };
    for (int i = 1; i < n; ++i)
        cv.line(sx_at(i - 1), sy_at(i - 1), sx_at(i), sy_at(i), kInfectious);
    if (n == 1) cv.disc(sx_at(0), sy_at(0), 2, kInfectious);

    cv.text(px, label_y, "0", kTextDim, 1);
    const std::string last_day = std::to_string(n - 1);
    cv.text(px + pw - text_w(last_day, 1), label_y, last_day, kTextDim, 1);
}

// --- legend -------------------------------------------------------------

void draw_legend_tx(Canvas& cv, int x, int y) {
    cv.text(x, y, "legend", kTextDim, 2);
    int cx = x + 104;
    auto circle = [&](Color c, const std::string& label) {
        cv.disc(cx, y + 7, 5, c);
        cv.ring(cx, y + 7, 5, Color{12, 12, 14, 255});
        cv.text(cx + 10, y, label, kText, 2);
        cx += 10 + text_w(label, 2) + 20;
    };
    circle(kHostSeek, "host-seek");
    circle(kBloodFed, "blood-fed");
    circle(kGravid, "gravid");
    cv.ring(cx, y + 7, 6, kInfectious);
    cv.text(cx + 10, y, "I_V", kText, 2);
    cx += 10 + text_w("I_V", 2) + 20;

    // Row 2: base cell classes + bite markers.
    const int y2 = y + 19;
    int cx2 = x + 104;
    auto sq = [&](Color c, const std::string& label) {
        cv.fill_rect(cx2 - 5, y2 + 1, 11, 11, c);
        cv.stroke_rect(cx2 - 5, y2 + 1, 11, 11, Color{12, 12, 14, 255});
        cv.text(cx2 + 10, y2, label, kText, 2);
        cx2 += 10 + text_w(label, 2) + 20;
    };
    sq(kHumanCellHigh, "human");
    sq(kAnimalCellHigh, "animal");
    sq(kEmptyCell, "empty");
    sq(kBiteHuman, "bite H");
    sq(kBiteAnimal, "bite A");

    // Row 3: movement arrows.
    const int y3 = y + 36;
    const int cx3 = x + 104;
    cv.line(cx3, y3 + 10, cx3 + 14, y3 + 4, kMoveHuman);
    cv.text(cx3 + 18, y3, "move", kText, 2);
}

}  // namespace

// ---------------------------------------------------------------------------
// tx_diag — pure, testable kernels (plan 05 §8)
// ---------------------------------------------------------------------------

namespace tx_diag {

int classify_biteable(double humans, double livestock) {
    if (humans > 0.0) return 2;
    if (livestock > 0.0) return 1;
    return 0;
}

std::vector<int64_t> build_vector_i_series(
    int64_t initial_vector_i,
    const std::vector<TransmissionDailyStats>& daily_history) {
    std::vector<int64_t> series;
    series.reserve(daily_history.size() + 1);
    series.push_back(initial_vector_i);
    for (const auto& day : daily_history) series.push_back(day.vector_i);
    return series;
}

std::vector<TxFlow> extract_top_flows(const SparseOD& od,
                                      const std::vector<float>& residential,
                                      int32_t W, int K, double& moved_out) {
    moved_out = 0.0;
    std::vector<TxFlow> all;
    if (W <= 0 || K <= 0) return all;
    for (int32_t i = 0; i < od.n_rows; ++i) {
        const float res = (static_cast<size_t>(i) < residential.size())
            ? residential[static_cast<size_t>(i)]
            : 0.0f;
        if (res <= 0.0f) continue;
        const int32_t start = od.row_ptr[static_cast<size_t>(i)];
        const int32_t end = od.row_ptr[static_cast<size_t>(i) + 1];
        for (int32_t k = start; k < end; ++k) {
            const float frac = od.values[static_cast<size_t>(k)];
            if (frac <= 0.0f) continue;
            const int32_t j = od.col_idx[static_cast<size_t>(k)];
            const float vol = frac * res;
            if (vol <= 0.0f) continue;
            const int32_t r0 = i / W, c0 = i % W;
            const int32_t r1 = j / W, c1 = j % W;
            if (r0 == r1 && c0 == c1) continue;  // staying home
            moved_out += vol;
            all.push_back({r0, c0, r1, c1, vol});
        }
    }
    const size_t kk = std::min(all.size(), static_cast<size_t>(K));
    std::partial_sort(all.begin(),
                      all.begin() + static_cast<std::ptrdiff_t>(kk), all.end(),
                      [](const TxFlow& a, const TxFlow& b) { return a.vol > b.vol; });
    all.resize(kk);
    return all;
}

}  // namespace tx_diag

// ---------------------------------------------------------------------------
// Impl
// ---------------------------------------------------------------------------

struct GifVizTx::Impl {
    explicit Impl(const GifVizTxConfig& c) : cfg(c) {
        width = std::clamp(cfg.width, 640, 2048);
        // The three diagnostics plus info need a little more vertical room at
        // the minimum width; larger GIFs retain the existing 0.60 aspect ratio.
        height = std::max(432, static_cast<int>(std::lround(0.60 * static_cast<double>(width))));
        if (cfg.path.empty()) {
            fail("empty transmission GIF path");
            return;
        }
        try {
            const std::filesystem::path p(cfg.path);
            if (p.has_parent_path()) {
                std::error_code ec;
                std::filesystem::create_directories(p.parent_path(), ec);
                if (ec) {
                    fail("cannot create output directory: " + ec.message());
                    return;
                }
            }
            canvas = std::make_unique<Canvas>(width, height);
        } catch (const std::exception& e) {
            fail(std::string("allocation failed: ") + e.what());
            return;
        }
        if (!canvas || !canvas->valid()) {
            fail("invalid canvas size");
            return;
        }
        if (!sink.open(cfg.path, width, height, frame_delay())) {
            fail("cannot open GIF for writing: " + cfg.path);
            return;
        }
        ok = true;
    }

    ~Impl() { finish(); }

    uint32_t frame_delay() const {
        const int fps = std::max(1, cfg.fps);
        const int cs = static_cast<int>(std::lround(100.0 / static_cast<double>(fps)));
        return static_cast<uint32_t>(std::max(1, cs));
    }

    void fail(const std::string& msg) {
        ok = false;
        if (!logged) {
            logged = true;
            std::fprintf(stderr, "abm_gif_tx: %s\n", msg.c_str());
        }
        sink.close();
    }

    void finish() {
        sink.close();
    }

    // --- static per-run precomputation (cached, done once) ---------------

    void ensure_base(const Engine& engine) {
        const int32_t H = engine.climate().h();
        const int32_t W = engine.climate().w();
        if (H <= 0 || W <= 0) return;
        if (base_done && base_h == H && base_w == W) return;
        base_h = H; base_w = W;
        const HostLandscape* hl = engine.host_landscape();
        humans.assign(static_cast<size_t>(H) * W, 0.0f);
        livestock.assign(static_cast<size_t>(H) * W, 0.0f);
        if (hl != nullptr) {
            for (int32_t r = 0; r < H; ++r) {
                for (int32_t c = 0; c < W; ++c) {
                    const HostCell cell = hl->at(r, c);
                    const size_t i = static_cast<size_t>(r) * W + c;
                    humans[i] = cell.humans_present;
                    livestock[i] = cell.cattle_present + cell.goats_present +
                                   cell.sheep_present + cell.pigs_present +
                                   cell.chickens_present + cell.wildlife_proxy;
                    run_max_humans = std::max(run_max_humans,
                                              static_cast<double>(cell.humans_present));
                    run_max_livestock = std::max(run_max_livestock,
                                                 static_cast<double>(livestock[i]));
                }
            }
        } else {
            // No --hosts: the default is humans everywhere (degradation rule).
            std::fill(humans.begin(), humans.end(), 1.0f);
            run_max_humans = std::max(run_max_humans, 1.0);
        }
        base_done = true;
    }

    // Static top OD flows of the DAY + total moved. Computed once (OD and
    // residential populations are constant). Expected flows E[F] = P·H_res —
    // the deterministic day-flow field (no RNG), satisfying plan 05 §9.4.
    void ensure_flows(const Engine& engine) {
        if (flows_done) return;
        flows_done = true;
        const MobilitySchedule* mob = engine.mobility_schedule();
        if (mob == nullptr) return;
        const int32_t W = base_w;
        if (W <= 0) return;
        const int kTop = 120;
        if (mob->has_human()) {
            top_human = tx_diag::extract_top_flows(
                mob->od(TimePhase::DAY, /*is_livestock=*/false), humans, W,
                kTop, moved_human);
        }
        if (mob->has_livestock()) {
            top_livestock = tx_diag::extract_top_flows(
                mob->od(TimePhase::DAY, /*is_livestock=*/true), livestock, W,
                kTop, moved_livestock);
        }
    }

    void draw(const Engine& engine,
              const std::vector<TransmissionDailyStats>& tx_hist,
              const std::vector<double>& human_bites,
              const std::vector<double>& animal_bites,
              const std::vector<double>& inf_bites,
              int day_index, int total_days);

    // --- state -----------------------------------------------------------
    GifVizTxConfig cfg;
    bool ok = false;
    bool logged = false;
    int width = 0, height = 0, frames = 0;
    GifSink sink;
    std::unique_ptr<Canvas> canvas;

    // Base host grids (static).
    bool base_done = false;
    int base_h = 0, base_w = 0;
    std::vector<float> humans;
    std::vector<float> livestock;
    double run_max_humans = 0.0;
    double run_max_livestock = 0.0;

    // Top flows (static).
    bool flows_done = false;
    std::vector<tx_diag::TxFlow> top_human;
    std::vector<tx_diag::TxFlow> top_livestock;
    double moved_human = 0.0;
    double moved_livestock = 0.0;

    // Per-day bite series (appended once per day in observe()).
    std::vector<double> human_bites;
    std::vector<double> animal_bites;
    std::vector<double> inf_bites;
};

void GifVizTx::Impl::draw(const Engine& engine,
                          const std::vector<TransmissionDailyStats>& tx_hist,
                          const std::vector<double>& human_bites,
                          const std::vector<double>& animal_bites,
                          const std::vector<double>& inf_bites,
                          int day_index, int total_days) {
    if (!canvas) return;
    Canvas& cv = *canvas;
    cv.fill(kBackground);

    const auto& climate = engine.climate();
    const int32_t H = climate.h();
    const int32_t W = climate.w();
    if (H <= 0 || W <= 0) return;

    ensure_base(engine);

    // -- layout (mirror map 1) -------------------------------------------
    const int margin = 10;
    const int header_h = 30;
    const int footer_h = 58;
    const int body_top = header_h + 6;
    const int body_bottom = height - footer_h - 6;
    const int body_h = std::max(100, body_bottom - body_top);
    const int map_rect_w = std::max(
        240, std::min(static_cast<int>(std::lround(0.58 * width)),
                      width - 2 * margin - 300));
    const double cell = std::min(static_cast<double>(map_rect_w) / W,
                                 static_cast<double>(body_h) / H);
    const int mw = std::max(1, static_cast<int>(std::floor(cell * W)));
    const int mh = std::max(1, static_cast<int>(std::floor(cell * H)));
    const int mx = margin + (map_rect_w - mw) / 2;
    const int my = body_top + (body_h - mh) / 2;
    auto cell_x = [&](int c) { return mx + static_cast<int>(std::lround(cell * c)); };
    auto cell_y = [&](int r) { return my + static_cast<int>(std::lround(cell * r)); };
    auto lon_to_x = [&](double lon) {
        const double t = (lon - engine.aoi().west) /
                         std::max(1.0e-12, engine.aoi().east - engine.aoi().west);
        return mx + static_cast<int>(std::lround(t * mw));
    };
    auto lat_to_y = [&](double lat) {
        const double t = (engine.aoi().north - lat) /
                         std::max(1.0e-12, engine.aoi().north - engine.aoi().south);
        return my + static_cast<int>(std::lround(t * mh));
    };
    const double res_m = static_cast<double>(std::max(1, engine.aoi().resolution_m));

    // -- Layer 1: biteable-cell base (3 classes) -------------------------
    for (int32_t r = 0; r < H; ++r) {
        const int y0 = cell_y(r), y1 = cell_y(r + 1);
        for (int32_t c = 0; c < W; ++c) {
            const int x0 = cell_x(c), x1 = cell_x(c + 1);
            const int cw = std::max(1, x1 - x0), ch = std::max(1, y1 - y0);
            const size_t i = static_cast<size_t>(r) * W + c;
            const double hu = humans[i];
            const double li = livestock[i];
            const int cls = tx_diag::classify_biteable(hu, li);
            if (cls == 2) {
                // Has humans: arena→red ramp + light contour (plan 05 §4.1).
                cv.fill_rect(x0, y0, cw, ch,
                             lerp(kHumanCellLow, kHumanCellHigh,
                                  cell_t(hu, run_max_humans)));
                cv.stroke_rect(x0, y0, cw, ch, kHumanOutline);
            } else if (cls == 1) {
                // Animal-only: olive ramp.
                cv.fill_rect(x0, y0, cw, ch,
                             lerp(kAnimalCellLow, kAnimalCellHigh,
                                  cell_t(li, run_max_livestock)));
            } else {
                // No hosts (incl. sea).
                cv.fill_rect(x0, y0, cw, ch, kEmptyCell);
            }
        }
    }

    // -- Layer 2: movement arrows + DAY/NIGHT inset ----------------------
    const int cell_cx_margin = static_cast<int>(std::lround(cell / 2));
    ensure_flows(engine);
    auto draw_flow = [&](const tx_diag::TxFlow& f, Color col) {
        const int x0 = cell_x(f.fc) + cell_cx_margin;
        const int y0 = cell_y(f.fr) + cell_cx_margin;
        const int x1 = cell_x(f.tc) + cell_cx_margin;
        const int y1 = cell_y(f.tr) + cell_cx_margin;
        cv.line(x0, y0, x1, y1, col);
        // Arrow head.
        const double ang = std::atan2(static_cast<double>(y1 - y0),
                                      static_cast<double>(x1 - x0));
        const int hx = static_cast<int>(std::lround(x1 - 5 * std::cos(ang)));
        const int hy = static_cast<int>(std::lround(y1 - 5 * std::sin(ang)));
        cv.line(x1, y1, hx, hy + 3, col);
        cv.line(x1, y1, hx, hy - 3, col);
    };
    for (const auto& f : top_livestock) draw_flow(f, kMoveLivestock);
    for (const auto& f : top_human) draw_flow(f, kMoveHuman);

    // DAY vs NIGHT H_eff inset (human), from the realized snapshot.
    {
        const auto& snap = engine.submodel().effective_phase_snapshot();
        if (snap.valid) {
            const int iw = std::max(48, static_cast<int>(std::lround(mw * 0.22)));
            const int ih = std::max(36, static_cast<int>(std::lround(mh * 0.34)));
            const int ix = mx + 4;
            const int iy = my + mh - 2 * ih - 12;
            auto panel = [&](const EffectiveGrid& g, int py, const char* label) {
                cv.fill_rect(ix, py, iw, ih, Color{0, 0, 0, 255});
                double gmax = 1.0;
                for (const float v : g) gmax = std::max(gmax, static_cast<double>(v));
                for (int32_t r = 0; r < H; ++r) {
                    for (int32_t c = 0; c < W; ++c) {
                        const size_t i = static_cast<size_t>(r) * W + c;
                        if (i >= g.size()) continue;
                        const double t = std::clamp(static_cast<double>(g[i]) / gmax, 0.0, 1.0);
                        const int x0 = ix + c * iw / W;
                        const int y0 = py + r * ih / H;
                        const int x1 = ix + (c + 1) * iw / W;
                        const int y1 = py + (r + 1) * ih / H;
                        Color cc = lerp(Color{20, 26, 40, 255}, kMoveHuman, t);
                        cv.fill_rect(x0, y0, std::max(1, x1 - x0),
                                     std::max(1, y1 - y0), cc);
                    }
                }
                cv.stroke_rect(ix, py, iw, ih, Color{255, 255, 255, 255});
                cv.fill_rect(ix + 1, py + 1, text_w(label, 1) + 4, 12, Color{0, 0, 0, 190});
                cv.text(ix + 3, py + 2, label, kText, 1);
            };
            panel(snap.human[static_cast<size_t>(TimePhase::DAY)], iy, "DAY");
            panel(snap.human[static_cast<size_t>(TimePhase::NIGHT)], iy + ih + 4, "NIGHT");
        }
    }

    // -- Layer 3: mosquitoes (same symbology as map 1) -------------------
    const MosquitoSoA& agents = engine.submodel().agents();
    int64_t n_infected = 0;
    const int agent_r = std::clamp(static_cast<int>(std::lround(cell / 6.0)), 1, 4);
    for (int64_t i = 0; i < agents.n_alive; ++i) {
        const size_t si = static_cast<size_t>(i);
        if (agents.stage[si] != 1) continue;
        const bool female = agents.sex[si] == 1;
        if (agents.vector_state[si] ==
            static_cast<uint8_t>(VectorTransmissionState::INFECTIOUS))
            ++n_infected;
        const int ax = lon_to_x(static_cast<double>(agents.lon[si]));
        const int ay = lat_to_y(static_cast<double>(agents.lat[si]));
        if (ax < mx || ax >= mx + mw || ay < my || ay >= my + mh) continue;
        Color sc = kHostSeek;
        if (female) {
            const auto gs = static_cast<GonotrophicState>(agents.gonotrophic_state[si]);
            switch (gs) {
                case GonotrophicState::TENERAL:
                case GonotrophicState::MATE_SEEKING:
                case GonotrophicState::HOST_SEEKING:
                case GonotrophicState::HOST_APPROACH:
                case GonotrophicState::PROBING:
                    sc = kHostSeek; break;
                case GonotrophicState::BLOOD_FED:
                case GonotrophicState::RESTING:
                case GonotrophicState::EGG_MATURING:
                    sc = kBloodFed; break;
                case GonotrophicState::GRAVID:
                case GonotrophicState::OVIPOSITION_SEEKING:
                case GonotrophicState::OVIPOSITING:
                    sc = kGravid; break;
            }
            cv.disc(ax, ay, agent_r + 1, Color{10, 10, 12, 255});
            cv.disc(ax, ay, agent_r, sc);
        } else {
            cv.ring(ax, ay, agent_r + 1, Color{10, 10, 12, 255});
            cv.ring(ax, ay, agent_r, Color{226, 220, 205, 255});
        }
        if (agents.vector_state[si] ==
            static_cast<uint8_t>(VectorTransmissionState::INFECTIOUS))
            cv.ring(ax, ay, agent_r + 2, kInfectious);
    }

    // -- Layer 4: today's bites (squares at the bitten cell) -------------
    const TransmissionModel* tr = engine.transmission();
    {
        const auto& ledger = engine.submodel().bite_ledger();
        for (const auto& agg : ledger.today()) {
            if (agg.row < 0 || agg.row >= H || agg.col < 0 || agg.col >= W) continue;
            if (agg.successful_meals <= 0) continue;
            const int side = std::max(3, std::min(static_cast<int>(std::lround(cell)) - 2,
                                     static_cast<int>(std::lround(
                                         3.0 + 1.2 * std::log1p(
                                             static_cast<double>(agg.successful_meals))))));
            const bool is_human = (agg.host == HostType::HUMAN);
            const int sx = (cell_x(agg.col) + cell_x(agg.col + 1)) / 2 - side / 2;
            const int sy = (cell_y(agg.row) + cell_y(agg.row + 1)) / 2 - side / 2;
            cv.fill_rect(sx, sy, side, side, is_human ? kBiteHuman : kBiteAnimal);
            cv.stroke_rect(sx, sy, side, side, Color{10, 10, 12, 255});
            if (agg.infectious_meals > 0) {
                cv.ring(sx + side / 2, sy + side / 2, side / 2 + 2, kInfectious);
            }
        }
    }

    // -- Layer 5: human infection (I_H contour + incidence dots) ---------
    if (tr != nullptr && tr->human_grid().h() == H && tr->human_grid().w() == W) {
        const auto& hg = tr->human_grid();
        for (int32_t r = 0; r < H; ++r) {
            for (int32_t c = 0; c < W; ++c) {
                const double ih = hg.i_at(r, c);
                const double inc = hg.inc_at(r, c);
                if (ih <= 0.0 && inc <= 0.0) continue;
                const int x0 = cell_x(c), y0 = cell_y(r);
                const int cw = std::max(1, cell_x(c + 1) - x0);
                const int ch = std::max(1, cell_y(r + 1) - y0);
                if (ih > 0.0) {
                    Color rc = kPrev;
                    rc.a = static_cast<uint8_t>(std::clamp(40.0 + 6.0 * ih, 40.0, 160.0));
                    cv.stroke_rect(x0, y0, cw, ch, rc);
                }
                if (inc > 0.0) {
                    cv.disc((x0 + cell_x(c + 1)) / 2, (y0 + cell_y(r + 1)) / 2, 2,
                            kIncidence);
                }
            }
        }
    }

    // -- scale bar + north ------------------------------------------------
    {
        const int px_per_km = std::max(3, static_cast<int>(std::lround((1000.0 / res_m) * cell)));
        const int len = std::min(px_per_km, mw / 3);
        const int bx = mx + 10, by = my + mh - 12;
        cv.line(bx, by, bx + len, by, Color{255, 255, 255, 255});
        cv.line(bx, by - 3, bx, by + 3, Color{255, 255, 255, 255});
        cv.line(bx + len, by - 3, bx + len, by + 3, Color{255, 255, 255, 255});
        cv.text(bx, by - 22, "1 km", kText, 2);
        const int nx = mx + mw - 14, ny = my + 12;
        cv.text(nx - 6, ny - 6, "N", kText, 2);
        cv.line(nx, ny + 14, nx, ny + 2, Color{255, 255, 255, 255});
        cv.line(nx, ny + 2, nx - 4, ny + 7, Color{255, 255, 255, 255});
        cv.line(nx, ny + 2, nx + 4, ny + 7, Color{255, 255, 255, 255});
    }

    // -- right column -----------------------------------------------------
    const int col_x = margin + map_rect_w + 14;
    const int col_w = std::max(120, width - col_x - margin);
    const int n_info_lines = 9;
    constexpr int panel_gap = 8;
    constexpr int min_panel_h = 58;
    constexpr int min_panels_h = 3 * min_panel_h;
    int info_h = 22 + n_info_lines * 18;
    if (body_h - info_h - 3 * panel_gap < min_panels_h)
        info_h = 22 + n_info_lines * 11;
    const int panels_h = std::max(0, body_h - info_h - 3 * panel_gap);
    int seir_h = static_cast<int>(std::lround(panels_h * 0.42));
    int bites_h = (panels_h - seir_h) / 2;
    int vector_i_h = panels_h - seir_h - bites_h;
    if (bites_h < min_panel_h || vector_i_h < min_panel_h) {
        seir_h = panels_h - 2 * min_panel_h;
        bites_h = min_panel_h;
        vector_i_h = min_panel_h;
    }

    draw_seir_panel(cv, col_x, body_top, col_w, seir_h, tx_hist);
    const int bites_y = body_top + seir_h + panel_gap;
    draw_bites_panel(cv, col_x, bites_y, col_w, bites_h,
                     human_bites, animal_bites, inf_bites);
    const int vector_i_y = bites_y + bites_h + panel_gap;
    const std::vector<int64_t> vector_i_series = tx_diag::build_vector_i_series(
        tr != nullptr ? tr->initial_vector_infected() : 0, tx_hist);
    draw_vector_i_panel(cv, col_x, vector_i_y, col_w, vector_i_h, vector_i_series);

    // Info block (all live values).
    const std::string date = date_iso(engine.current_date() - std::chrono::days{1});
    double total_humans = 0.0, i_h = 0.0;
    int64_t adults = 0;
    for (int64_t i = 0; i < agents.n_alive; ++i)
        if (agents.stage[static_cast<size_t>(i)] == 1) ++adults;
    if (tr != nullptr) {
        for (const double v : tr->human_grid().population()) total_humans += v;
        for (const double v : tr->human_grid().infectious()) i_h += v;
    }
    const auto& ts = (tr != nullptr) ? tr->last_day_stats() : TransmissionDailyStats{};
    const int64_t hb = static_cast<int64_t>(human_bites.empty() ? 0 : human_bites.back());
    const int64_t ab = static_cast<int64_t>(animal_bites.empty() ? 0 : animal_bites.back());
    const int64_t ib = static_cast<int64_t>(inf_bites.empty() ? 0 : inf_bites.back());

    char line[160];
    std::vector<std::pair<std::string, Color>> info;
    std::snprintf(line, sizeof(line), "day %d/%d  %s", day_index,
                  std::max(day_index, total_days), date.c_str());
    info.emplace_back(line, kText);
    std::snprintf(line, sizeof(line), "humans tot  %s",
                  fmt_count(static_cast<int64_t>(std::llround(total_humans))).c_str());
    info.emplace_back(line, kText);
    std::snprintf(line, sizeof(line), "I_H  %s  prev %.4f",
                  fmt_count(static_cast<int64_t>(std::llround(i_h))).c_str(),
                  ts.human_prevalence);
    info.emplace_back(line, i_h > 0 ? kInfectious : kText);
    std::snprintf(line, sizeof(line), "incidence  %.1f", ts.human_incidence);
    info.emplace_back(line, kText);
    std::snprintf(line, sizeof(line), "R_eff  %.2f", ts.r_eff_approx);
    info.emplace_back(line, kText);
    std::snprintf(line, sizeof(line), "bites H/A  %s/%s",
                  fmt_count(hb).c_str(), fmt_count(ab).c_str());
    info.emplace_back(line, kText);
    std::snprintf(line, sizeof(line), "inf meals/day  %s", fmt_count(ib).c_str());
    info.emplace_back(line, ib > 0 ? kInfectious : kText);
    std::snprintf(line, sizeof(line), "adults  %s", fmt_count(adults).c_str());
    info.emplace_back(line, kText);
    std::snprintf(line, sizeof(line), "I_V  %s", fmt_count(n_infected).c_str());
    info.emplace_back(line, n_infected > 0 ? kInfectious : kText);
    const int info_y = vector_i_y + vector_i_h + panel_gap;
    draw_info(cv, col_x, info_y, col_w, std::max(40, body_bottom - info_y), info);

    // -- header -----------------------------------------------------------
    cv.fill_rect(0, 0, width, header_h, kPanel);
    cv.line(0, header_h - 1, width, header_h - 1, kPanelBorder);
    const std::string title = "MalariaSentinel ABM - transmission";
    const int title_scale = text_scale_fit(title, width / 2);
    cv.text(margin, 6, title, kText, title_scale);
    std::snprintf(line, sizeof(line), "day %d/%d  %s", day_index,
                  std::max(day_index, total_days), date.c_str());
    const std::string right = line;
    const int right_scale =
        (text_w(right, 2) + text_w(title, title_scale) + 3 * margin <= width) ? 2 : 1;
    cv.text(width - margin - text_w(right, right_scale), 6, right, kText, right_scale);

    // -- footer legend ----------------------------------------------------
    cv.fill_rect(0, height - footer_h, width, footer_h, kPanel);
    cv.line(0, height - footer_h, width, height - footer_h, kPanelBorder);
    draw_legend_tx(cv, margin, height - footer_h + 2);
}

// ---------------------------------------------------------------------------
// GifVizTx facade
// ---------------------------------------------------------------------------

GifVizTx::GifVizTx(const GifVizTxConfig& cfg) {
    try {
        impl_ = std::make_unique<Impl>(cfg);
    } catch (const std::exception& e) {
        std::fprintf(stderr, "abm_gif_tx: initialization failed: %s\n", e.what());
        impl_.reset();
    } catch (...) {
        std::fprintf(stderr, "abm_gif_tx: initialization failed (unknown error)\n");
        impl_.reset();
    }
}

GifVizTx::~GifVizTx() = default;
GifVizTx::GifVizTx(GifVizTx&&) noexcept = default;
GifVizTx& GifVizTx::operator=(GifVizTx&&) noexcept = default;

bool GifVizTx::ok() const { return impl_ != nullptr && impl_->ok; }
int GifVizTx::frame_count() const { return impl_ != nullptr ? impl_->frames : 0; }

void GifVizTx::observe(const Engine& engine,
                       const std::vector<DailyStats>& /*history*/,
                       int day_index, int total_days) {
    if (impl_ == nullptr || !impl_->ok) return;
    try {
        Impl& im = *impl_;

        // Per-day series (appended once per day, even on non-frame days).
        const TransmissionModel* tr = engine.transmission();
        const auto& ledger = engine.submodel().bite_ledger();
        double hb = 0.0, ab = 0.0, ib = 0.0;
        for (const auto& agg : ledger.today()) {
            if (agg.host == HostType::HUMAN) hb += static_cast<double>(agg.successful_meals);
            else ab += static_cast<double>(agg.successful_meals);
            ib += static_cast<double>(agg.infectious_meals);
        }
        im.human_bites.push_back(hb);
        im.animal_bites.push_back(ab);
        im.inf_bites.push_back(ib);
        im.ensure_base(engine);
        im.ensure_flows(engine);
        // TransmissionModel history already holds S/E/I/R + incidence + bites.
        std::vector<TransmissionDailyStats> tx_hist;
        if (tr != nullptr) tx_hist = tr->history();

        const int every = std::max(1, im.cfg.every);
        if (day_index <= 0 || day_index % every != 0) return;

        im.draw(engine, tx_hist, im.human_bites, im.animal_bites, im.inf_bites,
                day_index, total_days);
        if (!im.ok || !im.canvas) return;
        if (!im.sink.write_frame(im.canvas->data(), im.width, im.height,
                                 im.frame_delay())) {
            im.fail("GifWriteFrame failed");
            return;
        }
        ++im.frames;
    } catch (const std::exception& e) {
        impl_->fail(std::string("frame render failed: ") + e.what());
    } catch (...) {
        impl_->fail("frame render failed (unknown error)");
    }
}

void GifVizTx::finish() {
    if (impl_ != nullptr) impl_->finish();
}

}  // namespace mal_abm_fast
