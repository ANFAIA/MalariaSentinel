// SPDX-License-Identifier: MIT
// viz.cpp — software rasterizer + GIF writer for the native ABM animation
// (plan 04-viz-gif-nativo-cpp §2). No external plotting library: every pixel
// is composed into an RGBA canvas and encoded with the vendored gif-h.
//
// Shape encodes scale (hard rule from the plan):
//   * square  = patch / aquatic cohort aggregate (occupancy, not quality)
//   * circle  = individual adult agent
// The map background is S(i,t) (species-neutral availability), never the
// gpkg `habitat_potential` (~0.9999 at ingest) and never K (K ∝ S).
#include "mal_abm_fast/viz.hpp"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <filesystem>
#include <limits>
#include <memory>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

#include "mal_abm_fast/third_party/font8x8_basic.hpp"
#include "mal_abm_fast/third_party/gif.h"

#include "mal_abm_fast/aoi.hpp"
#include "mal_abm_fast/climate.hpp"
#include "mal_abm_fast/config.hpp"
#include "mal_abm_fast/coordinator.hpp"
#include "mal_abm_fast/engine.hpp"
#include "mal_abm_fast/habitat_availability.hpp"
#include "mal_abm_fast/mosquito_state.hpp"
#include "mal_abm_fast/mosquito_submodel.hpp"
#include "mal_abm_fast/transmission.hpp"

namespace mal_abm_fast {
namespace {

// ---------------------------------------------------------------------------
// Canvas primitives
// ---------------------------------------------------------------------------

struct Color {
    uint8_t r = 0, g = 0, b = 0, a = 255;
};

Color lerp(Color a, Color b, double t) {
    t = std::clamp(t, 0.0, 1.0);
    auto mix = [t](uint8_t x, uint8_t y) {
        return static_cast<uint8_t>(std::lround(
            static_cast<double>(x) * (1.0 - t) + static_cast<double>(y) * t));
    };
    return Color{mix(a.r, b.r), mix(a.g, b.g), mix(a.b, b.b), 255};
}

class Canvas {
public:
    Canvas(int w, int h)
        : w_(w), h_(h),
          px_(static_cast<size_t>(std::max(0, w)) *
                  static_cast<size_t>(std::max(0, h)) * 4u,
              0) {}

    int width() const { return w_; }
    int height() const { return h_; }
    uint8_t* data() { return px_.data(); }
    const uint8_t* data() const { return px_.data(); }
    bool valid() const {
        return w_ > 0 && h_ > 0 &&
               px_.size() == static_cast<size_t>(w_) *
                                 static_cast<size_t>(h_) * 4u;
    }

    void fill(Color c) {
        for (size_t i = 0; i + 3 < px_.size(); i += 4) {
            px_[i] = c.r;
            px_[i + 1] = c.g;
            px_[i + 2] = c.b;
            px_[i + 3] = 255;
        }
    }

    void blend(int x, int y, Color c) {
        if (x < 0 || y < 0 || x >= w_ || y >= h_ || c.a == 0) return;
        const size_t i = (static_cast<size_t>(y) * static_cast<size_t>(w_) +
                          static_cast<size_t>(x)) * 4u;
        if (c.a == 255) {
            px_[i] = c.r;
            px_[i + 1] = c.g;
            px_[i + 2] = c.b;
            px_[i + 3] = 255;
            return;
        }
        const int a = static_cast<int>(c.a);
        const int ia = 255 - a;
        px_[i] = static_cast<uint8_t>(
            (static_cast<int>(c.r) * a + static_cast<int>(px_[i]) * ia) / 255);
        px_[i + 1] = static_cast<uint8_t>(
            (static_cast<int>(c.g) * a + static_cast<int>(px_[i + 1]) * ia) / 255);
        px_[i + 2] = static_cast<uint8_t>(
            (static_cast<int>(c.b) * a + static_cast<int>(px_[i + 2]) * ia) / 255);
        px_[i + 3] = 255;
    }

    void fill_rect(int x, int y, int w, int h, Color c) {
        if (w <= 0 || h <= 0) return;
        const int x0 = std::max(0, x);
        const int y0 = std::max(0, y);
        const int x1 = std::min(w_, x + w);
        const int y1 = std::min(h_, y + h);
        for (int yy = y0; yy < y1; ++yy)
            for (int xx = x0; xx < x1; ++xx) blend(xx, yy, c);
    }

    void stroke_rect(int x, int y, int w, int h, Color c) {
        if (w <= 0 || h <= 0) return;
        for (int xx = x; xx < x + w; ++xx) {
            blend(xx, y, c);
            blend(xx, y + h - 1, c);
        }
        for (int yy = y; yy < y + h; ++yy) {
            blend(x, yy, c);
            blend(x + w - 1, yy, c);
        }
    }

    void disc(int cx, int cy, int r, Color c) {
        const int rr = std::max(0, r);
        for (int dy = -rr; dy <= rr; ++dy)
            for (int dx = -rr; dx <= rr; ++dx)
                if (dx * dx + dy * dy <= rr * rr) blend(cx + dx, cy + dy, c);
    }

    void ring(int cx, int cy, int r, Color c) {
        if (r <= 0) {
            blend(cx, cy, c);
            return;
        }
        // Midpoint circle, 8-way symmetry.
        int x = r;
        int y = 0;
        int err = 1 - r;
        while (x >= y) {
            blend(cx + x, cy + y, c);
            blend(cx + y, cy + x, c);
            blend(cx - y, cy + x, c);
            blend(cx - x, cy + y, c);
            blend(cx - x, cy - y, c);
            blend(cx - y, cy - x, c);
            blend(cx + y, cy - x, c);
            blend(cx + x, cy - y, c);
            ++y;
            if (err < 0) {
                err += 2 * y + 1;
            } else {
                --x;
                err += 2 * (y - x) + 1;
            }
        }
    }

    void line(int x0, int y0, int x1, int y1, Color c) {
        const int dx = x1 - x0;
        const int dy = y1 - y0;
        const int steps = std::max(std::abs(dx), std::abs(dy));
        if (steps == 0) {
            blend(x0, y0, c);
            return;
        }
        for (int i = 0; i <= steps; ++i) {
            const double t = static_cast<double>(i) / static_cast<double>(steps);
            const int x = x0 + static_cast<int>(std::lround(
                                    static_cast<double>(dx) * t));
            const int y = y0 + static_cast<int>(std::lround(
                                    static_cast<double>(dy) * t));
            blend(x, y, c);
        }
    }

    void text(int x, int y, const std::string& s, Color c, int scale = 2) {
        const int sc = std::max(1, scale);
        int cx = x;
        for (const char ch : s) {
            unsigned char u = static_cast<unsigned char>(ch);
            if (u >= 128u) u = static_cast<unsigned char>('?');
            if (u >= static_cast<unsigned char>(' ')) {
                for (int row = 0; row < 8; ++row) {
                    const unsigned char bits = font8x8_basic[u][row];
                    if (bits == 0u) continue;
                    for (int bit = 0; bit < 8; ++bit) {
                        // bit0 is the leftmost pixel of the row byte.
                        if (((bits >> bit) & 1u) == 0u) continue;
                        fill_rect(cx + bit * sc, y + row * sc, sc, sc, c);
                    }
                }
            }
            cx += 8 * sc;
        }
    }

private:
    int w_ = 0;
    int h_ = 0;
    std::vector<uint8_t> px_;
};

int text_w(const std::string& s, int scale = 2) {
    return static_cast<int>(s.size()) * 8 * std::max(1, scale);
}

int text_scale_fit(const std::string& s, int avail_px) {
    return text_w(s, 2) <= avail_px ? 2 : 1;
}

// ---------------------------------------------------------------------------
// Palette
// ---------------------------------------------------------------------------

constexpr Color kBackground{13, 15, 19, 255};
constexpr Color kPanel{23, 26, 32, 255};
constexpr Color kPanelBorder{48, 54, 66, 255};
constexpr Color kText{228, 231, 238, 255};
constexpr Color kTextDim{148, 155, 168, 255};
constexpr Color kNeutralCell{54, 58, 66, 255};
// Truthful basemap tones (2026-10 coastline fix). Open sea is deep navy,
// coastal water a steel blue, land a muted olive/tan that cannot be confused
// with the habitat palette.
constexpr Color kOpenSea{14, 30, 52, 255};
constexpr Color kCoastalWater{78, 128, 168, 255};
constexpr Color kLandBase{140, 132, 102, 255};
// Land-fraction threshold under which a cell is water; mirrors
// ingest.sea_water_floor (0.05) from model_constants.yaml.
constexpr float kSeaWaterFloor = 0.05f;
constexpr Color kWater{38, 92, 190, 255};
constexpr Color kPrev{214, 48, 48, 255};
constexpr Color kAmber{240, 180, 60, 255};
constexpr Color kLarva{60, 200, 120, 255};
constexpr Color kPupa{230, 80, 180, 255};
constexpr Color kHostSeek{255, 190, 60, 255};
constexpr Color kBloodFed{190, 110, 240, 255};
constexpr Color kGravid{255, 60, 160, 255};
constexpr Color kInfectious{255, 40, 40, 255};
constexpr Color kDry{170, 170, 176, 255};

// Discrete availability classes (D9). A continuous ramp over the run range
// is unreadable here: S sits in [~0.19, ~0.65] with z ~= 0 in the dry
// season, so most cells land in the bottom fifth and neighbouring cells
// differ by <= 4 RGB units. Fixed, numerically meaningful bounds instead:
// every class is a visibly different colour, the encoding is identical
// across frames and runs, and the run's own min/max is printed next to the
// legend so the reader still knows which classes the run used.
constexpr int kSBoundCount = 9;
constexpr double kSBounds[kSBoundCount] = {
    0.00, 0.02, 0.10, 0.20, 0.25, 0.30, 0.35, 0.45, 1.00};
// D6: the S palette is a LAND palette. Blue already means water in the
// basemap (navy open sea, steel coastal band), and the old ramp put its
// [0.10,0.20) class at (34,104,168) — a blue, which is exactly where dry-
// season land sits (S ~ 0.12). The result was land reading as water and the
// coastal band (S = 0.25) reading as land. The sequence below runs
// taupe -> khaki -> olive -> green -> yellow -> cream, so "more habitat"
// stays monotone in warmth/lightness and no class can be confused with sea.
constexpr Color kSClassColors[kSBoundCount - 1] = {
    {86, 84, 80, 255},    // [0.00,0.02) no habitat: basemap shows through
    {128, 124, 112, 255}, // [0.02,0.10) trace, grey-taupe
    {150, 142, 104, 255}, // [0.10,0.20) low, single-zone cells: khaki
    {168, 158, 96, 255},  // [0.20,0.25) below the persistent floor
    {150, 176, 84, 255},  // [0.25,0.30) persistent water, dry: olive
    {120, 178, 80, 255},  // [0.30,0.35) persistent + first rain: green
    {208, 196, 96, 255},  // [0.35,0.45) standing water: yellow
    {242, 236, 168, 255}, // [0.45,1.00] near-saturated, wet season: cream
};

int s_class_index(double v) {
    int i = 0;
    while (i < kSBoundCount - 2 && v >= kSBounds[i + 1]) ++i;
    return i;
}

Color s_class_color(double v) {
    return kSClassColors[s_class_index(v)];
}

Color z_colormap(double t) {
    return lerp(Color{10, 26, 64, 255}, Color{82, 158, 255, 255}, t);
}

// Compact integer formatting so the info block never overflows.
std::string fmt_count(int64_t v) {
    char buf[48];
    const double d = static_cast<double>(v);
    if (v >= 1000000) {
        std::snprintf(buf, sizeof(buf), "%.2fM", d / 1.0e6);
    } else if (v >= 10000) {
        std::snprintf(buf, sizeof(buf), "%.1fk", d / 1.0e3);
    } else {
        std::snprintf(buf, sizeof(buf), "%lld", static_cast<long long>(v));
    }
    return std::string(buf);
}

std::string date_iso(std::chrono::sys_days d) {
    const std::chrono::year_month_day ymd{d};
    char buf[32];
    std::snprintf(buf, sizeof(buf), "%04d-%02u-%02u",
                  static_cast<int>(ymd.year()),
                  static_cast<unsigned>(ymd.month()),
                  static_cast<unsigned>(ymd.day()));
    return std::string(buf);
}

// Log/linear value → pixel row inside a plot rect (y0 = top).
int plot_y(double v, double vmin, double vmax, int y0, int h, bool log_scale) {
    if (h <= 0) return y0;
    double lo = vmin;
    double hi = vmax;
    if (log_scale) {
        lo = std::log10(std::max(1.0, lo));
        hi = std::log10(std::max(10.0, hi));
        if (hi - lo < 1.0e-9) hi = lo + 1.0;
        v = std::log10(std::max(1.0, v));
    } else {
        if (hi - lo < 1.0e-9) hi = lo + 1.0;
    }
    const double t = std::clamp((v - lo) / (hi - lo), 0.0, 1.0);
    // Keep the mark one pixel inside the box: a sample at the floor (v = 0 on
    // a log axis) must not sit on the plot border, where it reads as clipped.
    const int y = y0 + static_cast<int>(std::lround((1.0 - t) * h));
    return std::clamp(y, y0 + 1, y0 + std::max(1, h - 1));
}

// ---------------------------------------------------------------------------
// Panels
// ---------------------------------------------------------------------------

void draw_panel_frame(Canvas& cv, int x, int y, int w, int h,
                      const std::string& title) {
    cv.fill_rect(x, y, w, h, kPanel);
    cv.stroke_rect(x, y, w, h, kPanelBorder);
    cv.text(x + 6, y + 5, title, kTextDim, text_scale_fit(title, w - 12));
}

// Discrete S legend for the right column (D8/D9). The strip shows the eight
// classes with their numeric bounds; the run's observed range is printed on
// the title row so the reader still sees which part of the scale the run
// actually used.
void draw_s_legend(Canvas& cv, int x, int y, int w, int h,
                   double s_min, double s_max) {
    cv.fill_rect(x, y, w, h, kPanel);
    cv.stroke_rect(x, y, w, h, kPanelBorder);
    const int pad = 6;
    // Compact bound labels ("0" / ".02" / "1") are the only form that fits
    // the 286 px column at the 640 canvas; wider canvases get scale 2.
    const int lab_scale = (w >= 460) ? 2 : 1;
    const bool wide = (h >= 40);
    int strip_y = y + 14;
    if (wide) {
        cv.text(x + pad, y + 4, "S avail. land", kTextDim, 1);
        char run[48];
        std::snprintf(run, sizeof(run), "run %.2f-%.2f", s_min, s_max);
        if (text_w(run, 1) + text_w("S avail. land", 1) + 4 * pad <= w) {
            cv.text(x + w - pad - text_w(run, 1), y + 4, run, kTextDim, 1);
        }
    } else {
        // Narrow canvas: the title row is dropped so the two charts keep
        // their height; the bounds below the strip already say what it is.
        strip_y = y + 4;
    }
    const int strip_h = wide ? 10 : 8;
    const int n_cls = kSBoundCount - 1;
    const int sx = x + pad;
    const int sw = std::max(4, (w - 2 * pad) / n_cls);
    for (int i = 0; i < n_cls; ++i) {
        cv.fill_rect(sx + i * sw, strip_y, sw - 1, strip_h,
                     kSClassColors[i]);
    }
    cv.stroke_rect(sx, strip_y, sw * n_cls, strip_h,
                   Color{235, 235, 240, 255});
    // One label per class boundary, centred on it and clamped to the panel.
    const int lab_y = strip_y + strip_h + 2;
    for (int i = 0; i < kSBoundCount; ++i) {
        char buf[16];
        if (i == 0) {
            std::snprintf(buf, sizeof(buf), "0");
        } else if (i == kSBoundCount - 1) {
            std::snprintf(buf, sizeof(buf), "1");
        } else {
            std::snprintf(buf, sizeof(buf), "%.2f", kSBounds[i]);
            // Drop the leading zero: ".20" keeps nine labels legible.
            if (buf[0] == '0') {
                std::memmove(buf, buf + 1, std::strlen(buf));
            }
        }
        const int bx = sx + i * sw - text_w(buf, lab_scale) / 2;
        const int x0 = x + pad;
        const int x1 = x + w - pad - text_w(buf, lab_scale);
        cv.text(std::clamp(bx, std::min(x0, x1), std::max(x0, x1)), lab_y,
                buf, kText, lab_scale);
    }
}

// D3: fast, exact power of ten for the decade bounds.
double dec_pow10(int d) {
    return std::pow(10.0, static_cast<double>(d));
}

void draw_population(Canvas& cv, int x, int y, int w, int h,
                     const std::vector<DailyStats>& history,
                     int lo_dec, int hi_dec) {
    draw_panel_frame(cv, x, y, w, h, "pop log10");
    const int px = x + 8;
    const int py = y + 26;
    // Reserve the right-hand gutter for the decade labels: they used to be
    // painted on top of the plot edge, which also hid the cursor and any
    // single-sample marker at the newest position.
    const int axis_w = text_w("00", 2) + 6;
    const int pw = std::max(20, w - 16 - axis_w);
    const int ph = h - 34;
    if (pw <= 20 || ph <= 20 || history.empty()) return;

    const int n = static_cast<int>(history.size());
    // x mapping shared by every series and by the cursor. With a single
    // sample (n == 1) there is no span to divide by, so the sample and the
    // cursor both sit on the right edge (newest = current) and the sample is
    // drawn as a marker instead of a zero-length segment.
    auto sx_at = [&](int i) {
        if (n <= 1) return px + pw - 1;
        return px + (pw - 1) * i / (n - 1);
    };
    // D3: the axis is driven by the decade bounds the caller tracks across
    // frames (monotone, never shrinking), not by "1.5 x today's max" — that
    // made the data touch the top of the box on every busy day and let the
    // plotted values disagree with the decade labels.
    const double vmin = dec_pow10(lo_dec);
    const double vmax = dec_pow10(hi_dec);

    // Decade gridlines, labelled with the decade they actually are.
    for (int d = lo_dec; d <= hi_dec; ++d) {
        const double v = dec_pow10(d);
        const int yy = plot_y(v, vmin, vmax, py, ph, true);
        cv.line(px, yy, px + pw - 1, yy, Color{46, 49, 58, 255});
        char buf[16];
        std::snprintf(buf, sizeof(buf), "%d", d);
        // Keep the top decade label out of the title/key row: annotate it
        // just below its gridline instead of 8 px above.
        const int lab_y = (yy - 8 < py + 2) ? py + 2 : yy - 8;
        cv.text(x + w - 10 - text_w(buf, 2), lab_y, buf, kTextDim, 2);
    }

    auto draw_series = [&](auto field, Color c, bool mean_only) {
        std::vector<double> vals(static_cast<size_t>(n));
        for (int i = 0; i < n; ++i)
            vals[static_cast<size_t>(i)] =
                static_cast<double>(history[static_cast<size_t>(i)].*field);
        if (!mean_only) {
            Color faint = c;
            faint.a = 70;
            for (int i = 1; i < n; ++i) {
                const int xa = sx_at(i - 1);
                const int xb = sx_at(i);
                const int ya = plot_y(vals[static_cast<size_t>(i - 1)], vmin,
                                      vmax, py, ph, true);
                const int yb = plot_y(vals[static_cast<size_t>(i)], vmin,
                                      vmax, py, ph, true);
                cv.line(xa, ya, xb, yb, faint);
            }
        }
        // 7-day trailing mean (solid).
        for (int i = 0; i < n; ++i) {
            double sum = 0.0;
            int cnt = 0;
            for (int k = std::max(0, i - 6); k <= i; ++k) {
                sum += vals[static_cast<size_t>(k)];
                ++cnt;
            }
            const double m = sum / static_cast<double>(std::max(1, cnt));
            const int xa = sx_at(i);
            const int ya = plot_y(m, vmin, vmax, py, ph, true);
            if (i > 0) {
                double psum = 0.0;
                int pcnt = 0;
                for (int k = std::max(0, i - 7); k <= i - 1; ++k) {
                    psum += vals[static_cast<size_t>(k)];
                    ++pcnt;
                }
                const double pm = psum / static_cast<double>(std::max(1, pcnt));
                const int xb = sx_at(i - 1);
                const int yb = plot_y(pm, vmin, vmax, py, ph, true);
                cv.line(xb, yb, xa, ya, c);
            } else if (n == 1) {
                // Single-day history: a dot is the only way the series can
                // show up at all (there is no segment to draw).
                cv.disc(xa, ya, 3, c);
            } else {
                cv.blend(xa, ya, c);
            }
        }
    };

    draw_series(&DailyStats::n_adults, Color{255, 214, 128, 255}, false);
    draw_series(&DailyStats::n_eggs, kAmber, false);
    draw_series(&DailyStats::n_larvae, kLarva, false);
    draw_series(&DailyStats::n_pupae, kPupa, false);

    // Series key (2-letter-free, one glyph each).
    struct Key { const char* label; Color c; };
    const Key keys[4] = {{"A", {255, 214, 128, 255}},
                         {"E", kAmber},
                         {"L", kLarva},
                         {"P", kPupa}};
    int kx = x + w - 8;
    for (int i = 3; i >= 0; --i) {
        const int wlab = text_w(keys[i].label, 2);
        kx -= wlab;
        cv.text(kx, y + 4, keys[i].label, keys[i].c, 2);
        kx -= 12;
    }

    // Current-day cursor: always on the newest sample.
    const int xc = sx_at(n - 1);
    cv.line(xc, py, xc, py + ph, Color{235, 235, 240, 140});
}

void draw_forcers(Canvas& cv, int x, int y, int w, int h,
                  const std::vector<float>& rain,
                  const std::vector<float>& temp,
                  int day_index, const char* mask_label, bool temp_ok) {
    // Contract §2.4: a 90-day window, not the whole run. The series grow by
    // one sample per observe() call, so slice the last 90 here and label the
    // window with the real simulated days it covers.
    const int kWindow = 90;
    const int total = static_cast<int>(rain.size());
    const int first = std::max(0, total - kWindow);
    const int n = total - first;
    char title[64];
    const char* qualifier = mask_label != nullptr ? mask_label : "grid";
    if (n <= 0) {
        std::snprintf(title, sizeof(title), "forcers 90d");
    } else {
        const int span_first = std::max(1, day_index - (n - 1));
        // The qualifier names the mask both series are averaged over (D13).
        if (temp_ok) {
            std::snprintf(title, sizeof(title), "forcers %dd (d%d-d%d) %s", n,
                          span_first, std::max(span_first, day_index),
                          qualifier);
        } else {
            std::snprintf(title, sizeof(title), "forcers %dd (d%d-d%d) T n/a",
                          n, span_first, std::max(span_first, day_index));
        }
    }
    draw_panel_frame(cv, x, y, w, h, title);
    const int px = x + 8;
    const int py = y + 26;
    const int pw = w - 16;
    const int ph = h - 34;
    if (pw <= 20 || ph <= 20 || n <= 0) return;

    double rmax = 1.0;
    for (int i = first; i < total; ++i) {
        const float v = rain[static_cast<size_t>(i)];
        if (std::isfinite(v)) rmax = std::max(rmax, static_cast<double>(v));
    }
    rmax *= 1.15;

    const int bar_w = std::max(1, pw / std::max(1, n));
    for (int i = 0; i < n; ++i) {
        const float v = rain[static_cast<size_t>(first + i)];
        if (!std::isfinite(v)) continue;
        const double t = std::clamp(static_cast<double>(v) / rmax, 0.0, 1.0);
        const int bh = static_cast<int>(std::lround(t * (ph - 2)));
        if (bh <= 0) continue;
        const int bx = px + i * pw / std::max(1, n);
        cv.fill_rect(bx, py + ph - bh, bar_w, bh, Color{70, 130, 220, 190});
    }

    // Temperature on the right axis, same 90-day window. A mask whose
    // temperature buffer is shorter than the grid (or an all-NaN slice)
    // leaves nothing to plot: say "T n/a" instead of drawing a bogus axis
    // label derived from an empty min/max (D14).
    const int tn = (temp_ok && !temp.empty())
        ? std::min(n, static_cast<int>(temp.size()) - first)
        : 0;
    double tmin = std::numeric_limits<double>::max();
    double tmax = std::numeric_limits<double>::lowest();
    int t_valid = 0;
    for (int i = 0; i < tn; ++i) {
        const float v = temp[static_cast<size_t>(first + i)];
        if (!std::isfinite(v)) continue;
        tmin = std::min(tmin, static_cast<double>(v));
        tmax = std::max(tmax, static_cast<double>(v));
        ++t_valid;
    }
    if (tmax <= tmin) {
        tmin -= 1.0;
        tmax += 1.0;
    }
    if (t_valid > 0) {
        for (int i = 1; i < tn; ++i) {
            const float a = temp[static_cast<size_t>(first + i - 1)];
            const float b = temp[static_cast<size_t>(first + i)];
            if (!std::isfinite(a) || !std::isfinite(b)) continue;
            const int xa = px + (pw - 1) * (i - 1) / std::max(1, tn - 1);
            const int xb = px + (pw - 1) * i / std::max(1, tn - 1);
            const int ya =
                plot_y(static_cast<double>(a), tmin, tmax, py, ph, false);
            const int yb =
                plot_y(static_cast<double>(b), tmin, tmax, py, ph, false);
            cv.line(xa, ya, xb, yb, Color{255, 120, 90, 255});
        }
    }

    char buf[32];
    std::snprintf(buf, sizeof(buf), "%.0f", rmax);
    cv.text(px + 2, py + 2, buf, Color{120, 170, 240, 255}, 2);
    if (t_valid > 0) {
        std::snprintf(buf, sizeof(buf), "%.0fC", tmax);
    } else {
        std::snprintf(buf, sizeof(buf), "T n/a");
    }
    cv.text(x + w - 8 - text_w(buf, 2), py + 2, buf,
            Color{255, 140, 110, 255}, 2);
}

void draw_info(Canvas& cv, int x, int y, int w, int h,
               const std::vector<std::pair<std::string, Color>>& lines) {
    draw_panel_frame(cv, x, y, w, h, "info");
    if (lines.empty()) return;
    // Every metric line must fit, including on the 640x384 minimum canvas:
    // the row pitch shrinks (never the list) and the glyph scale follows it.
    const int n = static_cast<int>(lines.size());
    const int title_h = 20;
    // 8px glyphs need `lh >= 10`; the -26 reserves the panel border and one
    // blank row at the bottom so the last metric never touches the frame.
    const int lh = std::clamp((h - 26) / std::max(1, n), 10, 18);
    const int scale = (lh >= 16) ? 2 : 1;
    const int avail = w - 12;
    int ty = y + 4 + title_h;
    for (const auto& [text, color] : lines) {
        const int sc = std::min(scale, text_scale_fit(text, avail));
        cv.text(x + 6, ty, text, color, sc);
        ty += lh;
    }
}

void draw_legend(Canvas& cv, int x, int y, bool have_land_frac) {
    cv.text(x, y, "legend", kTextDim, 2);
    int cx = x + 104;

    auto swatch_circle = [&](Color c, const std::string& label) {
        cv.disc(cx, y + 7, 5, c);
        cv.ring(cx, y + 7, 5, Color{12, 12, 14, 255});
        cv.text(cx + 10, y, label, kText, 2);
        cx += 10 + text_w(label, 2) + 22;
    };
    swatch_circle(kHostSeek, "host-seek");
    swatch_circle(kBloodFed, "blood-fed");
    swatch_circle(kGravid, "gravid");

    // Second row: scale encoding. 19 px pitch (16 px glyphs, 3 px gap) and a
    // 2 px top inset: three rows end at y + 52, i.e. 4 px above the footer
    // edge. A 20 px pitch with a 6 px inset overflowed the 58 px footer by
    // 2 px at every width (visible as a clipped "base" row at 2048).
    const int y2 = y + 19;
    int cx2 = x + 104;
    auto swatch_square = [&](Color c, const std::string& label) {
        cv.fill_rect(cx2 - 5, y2 + 1, 11, 11, c);
        cv.stroke_rect(cx2 - 5, y2 + 1, 11, 11, Color{12, 12, 14, 255});
        cv.text(cx2 + 10, y2, label, kText, 2);
        cx2 += 10 + text_w(label, 2) + 22;
    };
    swatch_square(kLarva, "patch");
    auto swatch_dot = [&](Color c, const std::string& label) {
        cv.disc(cx2, y2 + 6, 3, c);
        cv.text(cx2 + 8, y2, label, kText, 2);
        cx2 += 8 + text_w(label, 2) + 22;
    };
    swatch_dot(kAmber, "eggs");
    swatch_dot(kPupa, "emerged");
    cv.ring(cx2, y2 + 6, 6, kInfectious);
    cv.text(cx2 + 10, y2, "I_V", kText, 2);

    // Third row: the truthful basemap tones (or the legacy notice when the
    // env NC predates the `land_frac` plane). Rows at +0, +19, +36.
    const int y3 = y + 36;
    int cx3 = x + 104;
    cv.text(x, y3, "base", kTextDim, 2);
    if (!have_land_frac) {
        cv.text(cx3, y3, "legacy (no land_frac)", kTextDim, 2);
        return;
    }
    auto swatch_base = [&](Color c, const std::string& label) {
        cv.fill_rect(cx3 - 5, y3 + 1, 11, 11, c);
        cv.stroke_rect(cx3 - 5, y3 + 1, 11, 11, Color{12, 12, 14, 255});
        cv.text(cx3 + 10, y3, label, kText, 2);
        cx3 += 10 + text_w(label, 2) + 22;
    };
    swatch_base(kOpenSea, "open sea");
    swatch_base(kCoastalWater, "coastal water");
    swatch_base(kLandBase, "land");
}

}  // namespace

// ---------------------------------------------------------------------------
// Impl
// ---------------------------------------------------------------------------

struct GifViz::Impl {
    explicit Impl(const GifVizConfig& c) : cfg(c) {
        width = std::clamp(cfg.width, 640, 2048);
        height = static_cast<int>(std::lround(0.60 * static_cast<double>(width)));
        if (cfg.path.empty()) {
            fail("empty --gif path");
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
        if (!GifBegin(&writer, cfg.path.c_str(), static_cast<uint32_t>(width),
                      static_cast<uint32_t>(height), frame_delay(), 8, false)) {
            fail("cannot open GIF for writing: " + cfg.path);
            return;
        }
        writer_open = true;
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
            std::fprintf(stderr, "abm_gif: %s\n", msg.c_str());
        }
        if (writer_open) {
            GifEnd(&writer);
            writer_open = false;
        }
    }

    void finish() {
        if (writer_open) {
            GifEnd(&writer);
            writer_open = false;
        }
    }

    // --- helpers ---------------------------------------------------------

    // Pluvial presence per cell, from the SAME config mapping the
    // coordinator uses: `habitat_types.dynamics` is pre-transformed into
    // `persistent_zone[ZoneId]`; every type there that is NOT persistent is
    // pluvial. A cell is pluvial when any pluvial type has H[i,g] > 0.
    // (Plan 04 §2.3 explicitly allows this config-level choice.)
    void ensure_pluvial_mask(const ClimateEngine& climate) {
        const int h = climate.h();
        const int w = climate.w();
        if (h <= 0 || w <= 0) return;
        if (mask_h == h && mask_w == w &&
            pluvial_mask.size() == static_cast<size_t>(h) * static_cast<size_t>(w))
            return;
        mask_h = h;
        mask_w = w;
        pluvial_mask.assign(static_cast<size_t>(h) * static_cast<size_t>(w), 0);
        const auto& persistent = load_config().habitat_types.persistent_zone;
        for (int r = 0; r < h; ++r) {
            for (int c = 0; c < w; ++c) {
                const HabitatFeatures f = climate.habitat_features_at(r, c);
                const std::array<float, kNumZoneId> hh = habitat_potential(f);
                bool pluvial = false;
                for (size_t g = 0; g < kNumZoneId; ++g) {
                    if (persistent[g]) continue;
                    if (hh[g] > 0.0f) {
                        pluvial = true;
                        break;
                    }
                }
                pluvial_mask[static_cast<size_t>(r) * static_cast<size_t>(w) +
                             static_cast<size_t>(c)] = pluvial ? 1u : 0u;
            }
        }
    }

    void draw(const Engine& engine, const std::vector<DailyStats>& history,
              int day_index, int total_days);

    // --- state -----------------------------------------------------------
    GifVizConfig cfg;
    bool ok = false;
    bool logged = false;
    int width = 0;
    int height = 0;
    int frames = 0;
    GifWriter writer{};
    bool writer_open = false;
    std::unique_ptr<Canvas> canvas;

    // Running S range over the whole run (stable colour scale, plan 04 §2.2).
    double s_min = 1.0;
    double s_max = 0.0;
    bool have_s = false;

    std::vector<float> rain_hist;
    std::vector<float> temp_hist;

    // D3: population-panel decade window, tracked over the whole run so the
    // axis never shrinks between frames and no sample is clipped.
    //   hi = max(1, ceil(log10(max of the four series AND their 7-day means)))
    //   lo = min(0, floor(log10(min positive sample)))
    //   span >= 2 decades
    int pop_lo_dec = 0;
    int pop_hi_dec = 2;

    std::vector<uint8_t> pluvial_mask;
    int mask_h = 0;
    int mask_w = 0;

    // Land/habitat mask for the forcer means (D13). The env NC writes 0.0
    // into `air_temp_c` over the ocean (`ingest/daily_nc.py:251`), so a
    // full-grid mean is meaningless in a coastal AOI: accra reads 5.48 C on
    // a grid that is 80.3 % ocean while its habitats sit at 27.74 C.
    // Rule, in order:
    //   1. static habitat signal present (jrc + built + wetland +
    //      open_plus_water + crop > 0), minus the ingest's ocean fill;
    //   2. cells whose patch has habitat_avail > 0.01 today;
    //   3. the full grid, labelled "grid".
    // The ocean filter in step 1 is necessary because every static plane also
    // covers the sea (lc_open_plus_water == 1.0 over all 2203 ocean cells in
    // accra), so the plane sum alone selects 2745/2745 cells and reproduces
    // the very artefact this mask exists to remove. The filter only engages
    // when the exact-0.0 block is >= 1 % of the grid, so a small AOI that
    // genuinely sits at 0 C keeps its cells.
    std::vector<uint8_t> plane_mask;  // static planes (computed once)
    std::vector<uint8_t> land_mask;   // plane mask minus ocean fill (per day)
    std::vector<uint8_t> patch_mask;
    std::vector<uint8_t> full_mask;
    int stat_mask_h = 0;
    int stat_mask_w = 0;
    bool stat_mask_done = false;
    // 1 = static habitat planes, 2 = active patches today, 3 = full grid.
    int mask_kind = 0;
    bool temp_unusable = false;

    // Cells counted by the mask rule; below this the mask is degenerate.
    int mask_min_cells(int h, int w) const {
        const int cells = h * w;
        return std::max(1, cells / 100);  // 1 % of the grid
    }

    // Layer 1: static habitat signal from the env NC static planes.
    int build_static_mask(const ClimateEngine& climate, int h, int w) {
        const size_t n = static_cast<size_t>(h) * static_cast<size_t>(w);
        plane_mask.assign(n, 0);
        const auto& jrc = climate.jrc_persistent();
        const auto& built = climate.lc_built();
        const auto& wet = climate.lc_wetland();
        const auto& open = climate.lc_open_plus_water();
        const auto& crop = climate.lc_crop();
        const auto usable = [n](const std::vector<float>& v) {
            return v.size() == n;
        };
        const bool any_plane = usable(jrc) || usable(built) || usable(wet) ||
                               usable(open) || usable(crop);
        if (!any_plane) return 0;
        int count = 0;
        for (size_t i = 0; i < n; ++i) {
            float sum = 0.0f;
            if (usable(jrc)) sum += jrc[i];
            if (usable(built)) sum += built[i];
            if (usable(wet)) sum += wet[i];
            if (usable(open)) sum += open[i];
            if (usable(crop)) sum += crop[i];
            if (sum > 0.0f) {
                plane_mask[i] = 1u;
                ++count;
            }
        }
        return count;
    }

    // Layer 2: cells whose patch has any habitat availability today.
    int build_patch_mask(const std::vector<PatchState>& patches, int h, int w) {
        const size_t n = static_cast<size_t>(h) * static_cast<size_t>(w);
        patch_mask.assign(n, 0);
        int count = 0;
        for (const auto& ps : patches) {
            if (ps.row < 0 || ps.row >= h || ps.col < 0 || ps.col >= w) continue;
            if (!(ps.habitat_avail > 0.01f)) continue;
            const size_t i = static_cast<size_t>(ps.row) * static_cast<size_t>(w) +
                             static_cast<size_t>(ps.col);
            if (!patch_mask[i]) {
                patch_mask[i] = 1u;
                ++count;
            }
        }
        return count;
    }

    // Resolve the mask for this frame; sets `mask_kind` and returns a
    // pointer to the chosen bitmask (never null).
    const std::vector<uint8_t>* resolve_mask(const ClimateEngine& climate,
                                             const std::vector<PatchState>& patches,
                                             int h, int w) {
        const size_t n = static_cast<size_t>(h) * static_cast<size_t>(w);
        if (n == 0) return nullptr;
        const int need = mask_min_cells(h, w);
        if (stat_mask_h != h || stat_mask_w != w || !stat_mask_done) {
            build_static_mask(climate, h, w);
            stat_mask_h = h;
            stat_mask_w = w;
            stat_mask_done = true;
        }
        // Apply the ocean-fill filter to the static mask. `temp_d()` holds
        // the ingest's 0.0 over the sea; use it only when the zero block is
        // large enough to be that fill and not a genuine 0 C AOI.
        land_mask = plane_mask;
        const auto& temp_arr = climate.temp_d();
        if (temp_arr.size() == n) {
            size_t zeros = 0;
            for (size_t i = 0; i < n; ++i) {
                if (temp_arr[i] == 0.0f) ++zeros;
            }
            if (zeros >= static_cast<size_t>(need)) {
                for (size_t i = 0; i < n; ++i) {
                    if (temp_arr[i] == 0.0f) land_mask[i] = 0u;
                }
            }
        }
        size_t land_cells = 0;
        for (size_t i = 0; i < n; ++i) land_cells += land_mask[i] ? 1u : 0u;
        if (land_cells >= static_cast<size_t>(need)) {
            mask_kind = 1;
            return &land_mask;
        }
        // Layer 2 is rebuilt every frame: patch activation can change.
        if (build_patch_mask(patches, h, w) >= need) {
            mask_kind = 2;
            return &patch_mask;
        }
        if (full_mask.size() != n) full_mask.assign(n, 1u);
        mask_kind = 3;
        return &full_mask;
    }

    const char* mask_label() const {
        switch (mask_kind) {
            case 1: return "land";
            case 2: return "land";  // patch cells are land by construction
            default: return "grid";
        }
    }
};

void GifViz::Impl::draw(const Engine& engine,
                        const std::vector<DailyStats>& history,
                        int day_index, int total_days) {
    if (!canvas) return;
    Canvas& cv = *canvas;
    cv.fill(kBackground);

    const auto& climate = engine.climate();
    const auto& coord = engine.coordinator();
    const auto& patches = coord.patch_states_today();
    const int H = climate.h();
    const int W = climate.w();
    if (H <= 0 || W <= 0) return;

    // -- layout ----------------------------------------------------------
    const int margin = 10;
    const int header_h = 30;
    const int footer_h = 58;
    const int body_top = header_h + 6;
    const int body_bottom = height - footer_h - 6;
    const int body_h = std::max(100, body_bottom - body_top);
    const int map_rect_x = margin;
    const int map_rect_y = body_top;
    const int map_rect_w = std::max(
        240, std::min(static_cast<int>(std::lround(0.58 * width)),
                      width - 2 * margin - 300));
    const int map_rect_h = body_h;

    const double cell = std::min(static_cast<double>(map_rect_w) /
                                     static_cast<double>(W),
                                 static_cast<double>(map_rect_h) /
                                     static_cast<double>(H));
    const int mw = std::max(1, static_cast<int>(std::floor(cell * W)));
    const int mh = std::max(1, static_cast<int>(std::floor(cell * H)));
    const int mx = map_rect_x + (map_rect_w - mw) / 2;
    const int my = map_rect_y + (map_rect_h - mh) / 2;

    auto cell_x = [&](int c) {
        return mx + static_cast<int>(std::lround(cell * c));
    };
    auto cell_y = [&](int r) {
        return my + static_cast<int>(std::lround(cell * r));
    };
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

    // -- patch lookup grid ----------------------------------------------
    std::vector<const PatchState*> grid(
        static_cast<size_t>(H) * static_cast<size_t>(W), nullptr);
    for (const auto& ps : patches) {
        if (ps.row < 0 || ps.row >= H || ps.col < 0 || ps.col >= W) continue;
        grid[static_cast<size_t>(ps.row) * static_cast<size_t>(W) +
             static_cast<size_t>(ps.col)] = &ps;
    }

    // -- (a) S background -------------------------------------------------
    // Discrete classes (see kSBounds): colour never depends on the run
    // range, so a cell keeps its colour from frame to frame. s_min/s_max
    // are still tracked and printed with the legend.
    const auto& jrc = climate.jrc_persistent();
    const bool have_jrc =
        jrc.size() == static_cast<size_t>(H) * static_cast<size_t>(W);

    const TransmissionModel* tr = cfg.transmission ? engine.transmission() : nullptr;
    const bool have_prev = tr != nullptr &&
        tr->human_grid().h() == H && tr->human_grid().w() == W;

    // -- truthful basemap -------------------------------------------------
    // Three-way base from the env NC `land_frac` plane (added by the 2026-10
    // coastline fix). The classes mirror the ingest rule exactly:
    //   water   : land_frac < sea_water_floor
    //   open sea: water AND the day slice carries the ingest 0.0 temperature
    //             sentinel (the ingest only zeroes temperature on open sea)
    //   coastal : water AND NOT open sea (lagoons, estuaries, the shallow
    //             plume that keeps its JRC water)
    //   land    : NOT water
    // The old NC has no `land_frac`: fall back to the legacy look (S class
    // colour / neutral grey + JRC tint) and say so in the legend.
    const auto& lf = climate.land_frac();
    const size_t n_cells_map = static_cast<size_t>(H) * static_cast<size_t>(W);
    const bool have_lf = lf.size() == n_cells_map;
    const auto& temp_now = climate.temp_d();
    const bool temp_map_ok = temp_now.size() == n_cells_map;
    bool temp_zero_block = false;
    if (temp_map_ok) {
        size_t zeros = 0;
        for (const float v : temp_now) {
            if (v == 0.0f) ++zeros;
        }
        temp_zero_block =
            zeros >= static_cast<size_t>(std::max<size_t>(1, n_cells_map / 100));
    }

    for (int r = 0; r < H; ++r) {
        const int y0 = cell_y(r);
        const int y1 = cell_y(r + 1);
        for (int c = 0; c < W; ++c) {
            const int x0 = cell_x(c);
            const int x1 = cell_x(c + 1);
            const int cw = std::max(1, x1 - x0);
            const int ch = std::max(1, y1 - y0);
            const size_t idx = static_cast<size_t>(r) * static_cast<size_t>(W) +
                               static_cast<size_t>(c);
            const PatchState* ps = grid[idx];
            Color base = kNeutralCell;
            bool is_water = false;
            if (!have_lf) {
                if (ps != nullptr) {
                    base = s_class_color(static_cast<double>(ps->habitat_avail));
                }
            } else {
                const bool water = lf[idx] < kSeaWaterFloor;
                is_water = water;
                bool sea = water;
                if (water && temp_map_ok && temp_zero_block) {
                    // Only trust the sentinel when the zero block is a real
                    // sea block (>= 1 % of the grid), so a genuinely 0 C AOI
                    // is not painted as ocean.
                    sea = (temp_now[idx] == 0.0f);
                }
                base = sea ? kOpenSea : (water ? kCoastalWater : kLandBase);
            }
            cv.fill_rect(x0, y0, cw, ch, base);

            // (b) persistent-water tint. Drawn BEFORE the habitat class so
            // the class keeps its land identity: the tint is a blue wash, and
            // painting it on top of the cream class turned the wettest land
            // (high S AND persistent water) into a pale teal that read as
            // water. Underneath, it still marks water on land without
            // competing with "how much habitat".
            if (have_jrc && jrc[idx] > 0.05f) {
                Color w = kWater;
                w.a = 90;  // 0.35 × 255
                cv.fill_rect(x0, y0, cw, ch, w);
            }

            // Habitat overlay: land only, and only from the second class up.
            //   * class [0.00,0.02) is "no habitat" -> nothing drawn, the
            //     basemap tile shows through (bare ground stays bare);
            //   * water cells keep the basemap colour: S on the coastal band
            //     is the structural persistent floor (0.25), not a habitat
            //     gradient, so tinting it would paint the water green and
            //     destroy the one cue that separates land from sea.
            // On land the class fill is strong (200/255) because the land
            // base is itself a tan tone; the coastline stays readable because
            // the water cells are never touched by this layer.
            if (have_lf && !is_water && ps != nullptr &&
                ps->habitat_avail >= kSBounds[1]) {
                Color s = s_class_color(
                    static_cast<double>(ps->habitat_avail));
                s.a = 200;
                cv.fill_rect(x0, y0, cw, ch, s);
            }
            // (c) human prevalence tint
            if (have_prev && tr->human_grid().prev_at(r, c) > 0.0) {
                Color p = kPrev;
                p.a = 77;  // 0.30 × 255
                cv.fill_rect(x0, y0, cw, ch, p);
            }
        }
    }

    // -- aquatic aggregates per patch ------------------------------------
    struct AquaticAgg {
        int64_t eggs = 0;
        int64_t larvae = 0;
        int64_t pupae = 0;
        int64_t total = 0;
    };
    std::unordered_map<int64_t, AquaticAgg> aquatic;
    for (const auto& co : engine.submodel().cohort_bank().cohorts()) {
        if (co.count <= 0) continue;
        AquaticAgg& a = aquatic[co.patch_id];
        switch (co.stage) {
            case AquaticStage::EGG: a.eggs += co.count; break;
            case AquaticStage::LARVA: a.larvae += co.count; break;
            case AquaticStage::PUPA: a.pupae += co.count; break;
        }
        a.total += co.count;
    }

    const auto& flux = engine.submodel().patch_daily_flux();

    // -- (d)-(f) patch squares, flux dots, dry rings ----------------------
    int patches_with_aquatic = 0;
    // Cell centre + square side for every patch that got a square, so the
    // flux pass below can also mark patches that laid/emerged today but
    // have no aquatic cohort left (e.g. the last pupae emerged).
    std::unordered_map<int64_t, std::pair<int, int>> square_centre;
    std::unordered_map<int64_t, int> square_side;
    for (const auto& [pid, agg] : aquatic) {
        ++patches_with_aquatic;
        // Resolve the patch cell from today's PatchState list.
        const PatchState* ps = nullptr;
        for (const auto& cand : patches) {
            if (cand.patch_id == pid) {
                ps = &cand;
                break;
            }
        }
        if (ps == nullptr || ps->row < 0 || ps->row >= H || ps->col < 0 ||
            ps->col >= W)
            continue;

        const double side_d =
            3.0 + 2.0 * std::log10(1.0 + static_cast<double>(agg.total));
        const int side = std::max(
            3, std::min(static_cast<int>(std::lround(cell)) - 2,
                        static_cast<int>(std::lround(side_d))));
        const int ccx = (cell_x(ps->col) + cell_x(ps->col + 1)) / 2;
        const int ccy = (cell_y(ps->row) + cell_y(ps->row + 1)) / 2;
        const int sx = ccx - side / 2;
        const int sy = ccy - side / 2;

        // Dominant stage decides the fill (plan 04 §2.2 item 4).
        Color fill = kAmber;
        if (agg.larvae >= agg.eggs && agg.larvae >= agg.pupae) fill = kLarva;
        else if (agg.pupae >= agg.eggs && agg.pupae >= agg.larvae) fill = kPupa;

        cv.fill_rect(sx, sy, side, side, fill);
        cv.stroke_rect(sx, sy, side, side, Color{10, 10, 12, 255});
        square_centre[pid] = {ccx, ccy};
        square_side[pid] = side;

        if (ps->habitat_dry_days > 0 && agg.total > 0) {
            cv.stroke_rect(sx - 2, sy - 2, side + 4, side + 4, kDry);
        }
    }

    // -- (e) daily reproductive flux --------------------------------------
    // Drawn for EVERY patch with flux, including patches whose aquatic
    // cohorts already emptied today (the emergence would otherwise vanish).
    for (const auto& [pid, f] : flux) {
        if (f.eggs_laid <= 0 && f.emerged <= 0) continue;
        int ccx = 0;
        int ccy = 0;
        const auto sc = square_centre.find(pid);
        if (sc != square_centre.end()) {
            ccx = sc->second.first;
            ccy = sc->second.second;
        } else {
            const PatchState* ps = nullptr;
            for (const auto& cand : patches) {
                if (cand.patch_id == pid) {
                    ps = &cand;
                    break;
                }
            }
            if (ps == nullptr || ps->row < 0 || ps->row >= H ||
                ps->col < 0 || ps->col >= W)
                continue;
            ccx = (cell_x(ps->col) + cell_x(ps->col + 1)) / 2;
            ccy = (cell_y(ps->row) + cell_y(ps->row + 1)) / 2;
        }
        const int side = square_side.count(pid) ? square_side[pid] : 5;
        const int sx = ccx - side / 2;
        const int sy = ccy - side / 2;
        if (f.eggs_laid > 0) {
            const int r = std::clamp(
                static_cast<int>(std::lround(
                    1.0 + 0.9 * std::log1p(
                                    static_cast<double>(f.eggs_laid)))),
                1, 4);
            cv.disc(sx, sy, r, kAmber);
        }
        if (f.emerged > 0) {
            const int r = std::clamp(
                static_cast<int>(std::lround(
                    1.0 + 0.9 * std::log1p(
                                    static_cast<double>(f.emerged)))),
                1, 4);
            cv.disc(sx + side - 1, sy, r, kPupa);
        }
    }

    // -- (g) individual adults -------------------------------------------
    const MosquitoSoA& agents = engine.submodel().agents();
    int64_t n_females = 0;
    int64_t n_males = 0;
    int64_t n_infected = 0;
    const int agent_r = std::clamp(
        static_cast<int>(std::lround(cell / 6.0)), 1, 4);
    for (int64_t i = 0; i < agents.n_alive; ++i) {
        const size_t si = static_cast<size_t>(i);
        if (agents.stage[si] != 1) continue;
        const bool female = agents.sex[si] == 1;
        if (female) ++n_females; else ++n_males;
        if (agents.vector_state[si] ==
            static_cast<uint8_t>(VectorTransmissionState::INFECTIOUS))
            ++n_infected;

        const int ax = lon_to_x(static_cast<double>(agents.lon[si]));
        const int ay = lat_to_y(static_cast<double>(agents.lat[si]));
        if (ax < mx || ax >= mx + mw || ay < my || ay >= my + mh) continue;

        Color sc = kHostSeek;
        if (female) {
            const auto gs =
                static_cast<GonotrophicState>(agents.gonotrophic_state[si]);
            switch (gs) {
                case GonotrophicState::TENERAL:
                case GonotrophicState::MATE_SEEKING:
                case GonotrophicState::HOST_SEEKING:
                case GonotrophicState::HOST_APPROACH:
                case GonotrophicState::PROBING:
                    sc = kHostSeek;
                    break;
                case GonotrophicState::BLOOD_FED:
                case GonotrophicState::RESTING:
                case GonotrophicState::EGG_MATURING:
                    sc = kBloodFed;
                    break;
                case GonotrophicState::GRAVID:
                case GonotrophicState::OVIPOSITION_SEEKING:
                case GonotrophicState::OVIPOSITING:
                    sc = kGravid;
                    break;
            }
        }

        if (female) {
            cv.disc(ax, ay, agent_r + 1, Color{10, 10, 12, 255});
            cv.disc(ax, ay, agent_r, sc);
        } else {
            // Males: hollow disc (shape/outline, not a fourth colour).
            cv.ring(ax, ay, agent_r + 1, Color{10, 10, 12, 255});
            cv.ring(ax, ay, agent_r, Color{226, 220, 205, 255});
        }
        if (agents.vector_state[si] ==
            static_cast<uint8_t>(VectorTransmissionState::INFECTIOUS))
            cv.ring(ax, ay, agent_r + 2, kInfectious);
    }

    // The S legend used to be painted inside the map rect, which hid every
    // cell under it — including all row-0 foci in the accra transmission
    // layout. It now lives in the right column (draw_s_legend), so no map
    // cell can ever be occluded at any canvas width.

    // -- z inset (bottom-right of the map, 25% of map w/h) ----------------
    ensure_pluvial_mask(climate);
    {
        const auto& z = coord.z_grid();
        const int iw = std::max(40, static_cast<int>(std::lround(mw * 0.25)));
        const int ih = std::max(30, static_cast<int>(std::lround(mh * 0.25)));
        const int ix = mx + mw - iw - 4;
        const int iy = my + mh - ih - 4;
        cv.fill_rect(ix, iy, iw, ih, Color{0, 0, 0, 255});
        const bool have_z = z.size() == static_cast<size_t>(H) * static_cast<size_t>(W);
        // Day's z range over the pluvial cells that are actually painted, so
        // the labels match the pixels (§2.3 / A7).
        double z_lo = std::numeric_limits<double>::max();
        double z_hi = std::numeric_limits<double>::lowest();
        int z_cells = 0;
        if (have_z) {
            for (int r = 0; r < H; ++r) {
                const int y0 = iy + r * ih / H;
                const int y1 = iy + (r + 1) * ih / H;
                for (int c = 0; c < W; ++c) {
                    const int x0 = ix + c * iw / W;
                    const int x1 = ix + (c + 1) * iw / W;
                    const size_t idx =
                        static_cast<size_t>(r) * static_cast<size_t>(W) +
                        static_cast<size_t>(c);
                    if (idx >= pluvial_mask.size() || pluvial_mask[idx] == 0)
                        continue;
                    const double zv =
                        std::clamp(static_cast<double>(z[idx]), 0.0, 1.0);
                    z_lo = std::min(z_lo, zv);
                    z_hi = std::max(z_hi, zv);
                    ++z_cells;
                    cv.fill_rect(x0, y0, std::max(1, x1 - x0),
                                 std::max(1, y1 - y0), z_colormap(zv));
                }
            }
        }
        cv.stroke_rect(ix, iy, iw, ih, Color{255, 255, 255, 255});
        const int z_scale = text_scale_fit("z pluvial", iw - 8);
        const int z_tw = text_w("z pluvial", z_scale);
        cv.fill_rect(ix + 2, iy + 2, std::min(iw - 4, z_tw + 4), 20,
                     Color{0, 0, 0, 190});
        cv.text(ix + 4, iy + 2, "z pluvial", kText, z_scale);

        // Numeric scale for the inset: the day's own min/max (what the pixels
        // show) plus the fixed 0-1 domain of the reservoir. The strip sits
        // inside the white border, so it can never collide with the legend.
        char zlab[64];
        if (z_cells > 0) {
            std::snprintf(zlab, sizeof(zlab), "z %.2f-%.2f (0-1)", z_lo, z_hi);
        } else {
            std::snprintf(zlab, sizeof(zlab), "z n/a (0-1)");
        }
        const int lab_scale = std::max(1, text_scale_fit(zlab, iw - 8));
        const int lab_h = 8 * lab_scale + 3;
        const int lab_y = iy + ih - lab_h;
        cv.fill_rect(ix + 1, lab_y, iw - 2, lab_h, Color{0, 0, 0, 200});
        cv.text(ix + 4, lab_y + 1, zlab, kText, lab_scale);
    }

    // -- scale bar + north ------------------------------------------------
    {
        const double res_m = static_cast<double>(
            std::max(1, engine.aoi().resolution_m));
        const int px_per_km = std::max(
            3, static_cast<int>(std::lround((1000.0 / res_m) * cell)));
        const int len = std::min(px_per_km, mw / 3);
        const int bx = mx + 10;
        const int by = my + mh - 12;
        cv.line(bx, by, bx + len, by, Color{255, 255, 255, 255});
        cv.line(bx, by - 3, bx, by + 3, Color{255, 255, 255, 255});
        cv.line(bx + len, by - 3, bx + len, by + 3,
                Color{255, 255, 255, 255});
        cv.text(bx, by - 22, "1 km", kText, 2);

        const int nx = mx + mw - 14;
        const int ny = my + 12;
        cv.text(nx - 6, ny - 6, "N", kText, 2);
        cv.line(nx, ny + 14, nx, ny + 2, Color{255, 255, 255, 255});
        cv.line(nx, ny + 2, nx - 4, ny + 7, Color{255, 255, 255, 255});
        cv.line(nx, ny + 2, nx + 4, ny + 7, Color{255, 255, 255, 255});
    }

    // -- right column -----------------------------------------------------
    const int col_x = map_rect_x + map_rect_w + 14;
    const int col_w = std::max(120, width - col_x - margin);
    // The info block needs room for all of its metric lines even on the
    // 640x384 minimum canvas, so it is reserved first: scale-2 rows when
    // the body is tall enough, otherwise compact scale-1 rows. The two
    // charts split what is left.
    const int n_info_lines = (cfg.transmission && tr != nullptr) ? 11 : 9;
    int info_h = 22 + n_info_lines * 18;
    if (body_h - info_h - 16 < 120) info_h = 22 + n_info_lines * 11;
    // Discrete classes need a strip plus nine bound labels; the compact form
    // (scale-1 labels) is used on the narrow canvases. On the 640 canvas the
    // drawn map is shorter than its rect (the AOI is wider than tall), and
    // that unused strip below the last cell row is free: parking the classes
    // there keeps them off every map cell AND returns 26 px to the charts,
    // which otherwise could not be plotted with the 11-line info block.
    const bool legend_below_map =
        (col_w < 460) && (my + mh + 24 <= body_bottom);
    const int sbar_h =
        legend_below_map ? 0 : ((col_w >= 460) ? 44 : 26);
    const int charts_h =
        std::max(40, body_h - info_h - 16 - sbar_h - 8);
    int pop_h = std::max(50, static_cast<int>(std::lround(charts_h * 0.60)));
    int forc_h = std::max(40, charts_h - pop_h);
    if (col_w < 460) {
        // Narrow canvas: draw_forcers needs h > 54 to paint a plot under its
        // title (ph = h - 34 must exceed 20), so hand it 56 px when that
        // still leaves the population panel legible. Below that the two
        // panels split what is left; on 640x384 plus the 11-line
        // transmission info block neither chart can be plotted, which is
        // reported rather than hidden by a fake height.
        forc_h = (charts_h >= 118) ? 56 : std::max(40, charts_h / 2);
        pop_h = std::max(30, charts_h - forc_h);
    }
    // On the 640x384 canvas (and with the transmission info block) the two
    // panel floors can exceed the space left by the legend; give the height
    // back to the population panel so nothing runs into the info block.
    if (pop_h + forc_h > charts_h) {
        pop_h = std::max(30, charts_h - forc_h);
    }
    draw_population(cv, col_x, body_top, col_w, pop_h, history,
                    pop_lo_dec, pop_hi_dec);
    if (legend_below_map) {
        draw_s_legend(cv, map_rect_x, my + mh + 2, map_rect_w, 22, s_min,
                      s_max);
    } else {
        draw_s_legend(cv, col_x, body_top + pop_h + 8, col_w, sbar_h, s_min,
                      s_max);
    }
    draw_forcers(cv, col_x, body_top + pop_h + 8 + sbar_h + 8, col_w, forc_h,
                 rain_hist, temp_hist, day_index, mask_label(),
                 !temp_unusable);

    // Info block values, all from live state.
    int64_t k_total = 0;
    double s_sum = 0.0;
    int s_count = 0;
    for (const auto& ps : patches) {
        k_total += static_cast<int64_t>(std::llround(ps.k_habitat));
        if (ps.habitat_avail >= 0.01f) {
            s_sum += static_cast<double>(ps.habitat_avail);
            ++s_count;
        }
    }
    const double mean_s = s_count > 0 ? s_sum / static_cast<double>(s_count) : 0.0;
    const int64_t adults = n_females + n_males;

    int64_t eggs = 0, larvae = 0, pupae = 0;
    for (const auto& co : engine.submodel().cohort_bank().cohorts()) {
        if (co.count <= 0) continue;
        switch (co.stage) {
            case AquaticStage::EGG: eggs += co.count; break;
            case AquaticStage::LARVA: larvae += co.count; break;
            case AquaticStage::PUPA: pupae += co.count; break;
        }
    }

    double rain_mean = 0.0;
    double temp_mean = 0.0;
    if (!rain_hist.empty()) rain_mean = static_cast<double>(rain_hist.back());
    if (!temp_hist.empty()) temp_mean = static_cast<double>(temp_hist.back());
    // Mask qualifier for the two forcer means (D13): "land" when the static
    // habitat planes (or today's active patches) gave a usable mask, "grid"
    // when they did not.
    const char* forcer_label = mask_label();

    // observe() runs AFTER engine.step() advanced current_date_ to the NEXT
    // day, so the day that was just simulated is current_date - 1. Printing
    // current_date() would label frame d as d+1 (and roll the year early).
    const std::string date =
        date_iso(engine.current_date() - std::chrono::days{1});
    char line[160];
    std::vector<std::pair<std::string, Color>> info;
    std::snprintf(line, sizeof(line), "day %d/%d  %s", day_index,
                  std::max(day_index, total_days), date.c_str());
    info.emplace_back(line, kText);
    std::snprintf(line, sizeof(line), "adults F/M  %s/%s",
                  fmt_count(n_females).c_str(), fmt_count(n_males).c_str());
    info.emplace_back(line, kText);
    std::snprintf(line, sizeof(line), "infected V  %s",
                  fmt_count(n_infected).c_str());
    info.emplace_back(line, n_infected > 0 ? kInfectious : kText);
    std::snprintf(line, sizeof(line), "E/L/P  %s/%s/%s",
                  fmt_count(eggs).c_str(), fmt_count(larvae).c_str(),
                  fmt_count(pupae).c_str());
    info.emplace_back(line, kText);
    std::snprintf(line, sizeof(line), "aqua patches  %d/%d",
                  patches_with_aquatic, static_cast<int>(patches.size()));
    info.emplace_back(line, kText);
    std::snprintf(line, sizeof(line), "mean S  %.3f", mean_s);
    info.emplace_back(line, kText);
    std::snprintf(line, sizeof(line), "K_total  %s", fmt_count(k_total).c_str());
    info.emplace_back(line, kText);
    // D4: adults/K as a percentage with two significant digits. "0.000"
    // hid a real (if small) occupancy; "<0.1%" is explicit about the floor.
    const double adults_pct =
        k_total > 0 ? 100.0 * static_cast<double>(adults) /
                          static_cast<double>(k_total)
                    : 0.0;
    if (adults_pct >= 0.1) {
        std::snprintf(line, sizeof(line), "adults/K  %.2g%%", adults_pct);
    } else {
        std::snprintf(line, sizeof(line), "adults/K  <0.1%%");
    }
    info.emplace_back(line, kText);
    if (temp_unusable) {
        std::snprintf(line, sizeof(line), "rain %.1fmm  T n/a", rain_mean);
    } else {
        std::snprintf(line, sizeof(line), "rain %.1fmm  T %s %.1fC", rain_mean,
                      forcer_label, temp_mean);
    }
    info.emplace_back(line, kText);
    if (cfg.transmission && tr != nullptr) {
        double i_h = 0.0;
        for (const double v : tr->human_grid().infectious()) i_h += v;
        const auto& ts = tr->last_day_stats();
        std::snprintf(line, sizeof(line), "I_H %s  prev %.4f",
                      fmt_count(static_cast<int64_t>(std::llround(i_h))).c_str(),
                      ts.human_prevalence);
        info.emplace_back(line, kText);
        std::snprintf(line, sizeof(line), "R_eff  %.2f", ts.r_eff_approx);
        info.emplace_back(line, kText);
    }

    const int info_y =
        body_top + pop_h + 8 + sbar_h + 8 + forc_h + 8;
    draw_info(cv, col_x, info_y, col_w,
              std::max(40, body_bottom - info_y), info);

    // -- header -----------------------------------------------------------
    cv.fill_rect(0, 0, width, header_h, kPanel);
    cv.line(0, header_h - 1, width, header_h - 1, kPanelBorder);
    const std::string title = "MalariaSentinel ABM";
    const int title_scale = text_scale_fit(title, width / 2);
    cv.text(margin, 6, title, kText, title_scale);
    std::snprintf(line, sizeof(line), "day %d/%d  %s", day_index,
                  std::max(day_index, total_days), date.c_str());
    const std::string right = line;
    const int right_scale =
        (text_w(right, 2) + text_w(title, title_scale) + 3 * margin <= width)
            ? 2 : 1;
    cv.text(width - margin - text_w(right, right_scale), 6, right, kText,
            right_scale);
    // Slug only when it fits between the title and the day stamp.
    const int title_end = margin + text_w(title, title_scale);
    const int right_start = width - margin - text_w(right, right_scale);
    const int slug_room = right_start - title_end - 32;
    if (slug_room > 0 &&
        text_w(engine.aoi().slug, 2) <= slug_room) {
        cv.text(title_end + 24, 6, engine.aoi().slug, kTextDim, 2);
    }

    // -- footer legend ----------------------------------------------------
    cv.fill_rect(0, height - footer_h, width, footer_h, kPanel);
    cv.line(0, height - footer_h, width, height - footer_h, kPanelBorder);
    draw_legend(cv, margin, height - footer_h + 2, have_lf);
}

// ---------------------------------------------------------------------------
// GifViz facade
// ---------------------------------------------------------------------------

GifViz::GifViz(const GifVizConfig& cfg) {
    try {
        impl_ = std::make_unique<Impl>(cfg);
    } catch (const std::exception& e) {
        std::fprintf(stderr, "abm_gif: initialization failed: %s\n", e.what());
        impl_.reset();
    } catch (...) {
        std::fprintf(stderr, "abm_gif: initialization failed (unknown error)\n");
        impl_.reset();
    }
}

GifViz::~GifViz() = default;
GifViz::GifViz(GifViz&&) noexcept = default;
GifViz& GifViz::operator=(GifViz&&) noexcept = default;

bool GifViz::ok() const { return impl_ != nullptr && impl_->ok; }

int GifViz::frame_count() const { return impl_ != nullptr ? impl_->frames : 0; }

void GifViz::observe(const Engine& engine,
                     const std::vector<DailyStats>& history,
                     int day_index, int total_days) {
    if (impl_ == nullptr || !impl_->ok) return;
    try {
        Impl& im = *impl_;

        // Forcers: exactly one sample per observe() call (one per day),
        // even on days that do not emit a frame. Means are taken over the
        // land/habitat mask (D13): the env NC zeroes air_temp_c over the
        // ocean, so a full-grid mean would report a fabricated 5.5 C for a
        // run whose habitats sit at ~27.7 C.
        const int ch = engine.climate().h();
        const int cw = engine.climate().w();
        const auto* mask = im.resolve_mask(engine.climate(),
                                          engine.coordinator().patch_states_today(),
                                          ch, cw);
        const size_t n_cells = mask != nullptr ? mask->size() : 0u;
        const auto& rain_arr = engine.climate().rain_daily();
        const auto& temp_arr = engine.climate().temp_d();
        // A buffer shorter than the grid cannot be indexed by the mask; the
        // engine leaves temp_d empty for some env files (D14). Plot nothing
        // and print "n/a" rather than reading out of bounds.
        const bool rain_ok = n_cells > 0 && rain_arr.size() >= n_cells;
        const bool temp_ok = n_cells > 0 && temp_arr.size() >= n_cells;
        im.temp_unusable = !temp_ok;
        double rain_sum = 0.0;
        double temp_sum = 0.0;
        int rain_n = 0;
        int temp_n = 0;
        for (size_t i = 0; i < n_cells; ++i) {
            if ((*mask)[i] == 0) continue;
            if (rain_ok) {
                const float v = rain_arr[i];
                if (std::isfinite(v)) {
                    rain_sum += static_cast<double>(v);
                    ++rain_n;
                }
            }
            if (temp_ok) {
                const float v = temp_arr[i];
                if (std::isfinite(v)) {
                    temp_sum += static_cast<double>(v);
                    ++temp_n;
                }
            }
        }
        im.rain_hist.push_back(static_cast<float>(
            rain_n > 0 ? rain_sum / static_cast<double>(rain_n) : 0.0));
        im.temp_hist.push_back(static_cast<float>(
            temp_n > 0 ? temp_sum / static_cast<double>(temp_n)
                       : std::numeric_limits<float>::quiet_NaN()));

        // D3: extend the population decade window from this frame's data
        // (raw samples and their 7-day trailing means). Monotone: the window
        // only ever grows, so a series can never leave the box later.
        {
            const int n_hist = static_cast<int>(history.size());
            double vmax = 1.0;
            double vmin_pos = std::numeric_limits<double>::infinity();
            for (int i = 0; i < n_hist; ++i) {
                const DailyStats& st = history[static_cast<size_t>(i)];
                const double raw[4] = {static_cast<double>(st.n_adults),
                                       static_cast<double>(st.n_eggs),
                                       static_cast<double>(st.n_larvae),
                                       static_cast<double>(st.n_pupae)};
                for (double v : raw) {
                    vmax = std::max(vmax, v);
                    if (v > 0.0) vmin_pos = std::min(vmin_pos, v);
                }
                for (int s_i = 0; s_i < 4; ++s_i) {
                    double sum = 0.0;
                    int cnt = 0;
                    for (int k = std::max(0, i - 6); k <= i; ++k) {
                        const DailyStats& sk = history[static_cast<size_t>(k)];
                        switch (s_i) {
                            case 0: sum += static_cast<double>(sk.n_adults); break;
                            case 1: sum += static_cast<double>(sk.n_eggs); break;
                            case 2: sum += static_cast<double>(sk.n_larvae); break;
                            default: sum += static_cast<double>(sk.n_pupae); break;
                        }
                        ++cnt;
                    }
                    const double m = sum / static_cast<double>(std::max(1, cnt));
                    vmax = std::max(vmax, m);
                    if (m > 0.0) vmin_pos = std::min(vmin_pos, m);
                }
            }
            const int hi_needed = std::max(
                1, static_cast<int>(std::ceil(std::log10(std::max(1.0, vmax)))));
            int lo_needed = 0;
            if (std::isfinite(vmin_pos)) {
                lo_needed = std::min(
                    0, static_cast<int>(std::floor(std::log10(vmin_pos))));
            }
            im.pop_hi_dec = std::max(im.pop_hi_dec, hi_needed);
            im.pop_lo_dec = std::min(im.pop_lo_dec, lo_needed);
            while (im.pop_hi_dec - im.pop_lo_dec < 2) ++im.pop_hi_dec;
        }

        // Running S range: updated every day, so the colour scale is stable
        // across frames but adapts to the whole run (plan 04 §2.2).
        for (const auto& ps : engine.coordinator().patch_states_today()) {
            const double v = static_cast<double>(ps.habitat_avail);
            if (!std::isfinite(v)) continue;
            if (!im.have_s) {
                im.s_min = v;
                im.s_max = v;
                im.have_s = true;
            } else {
                im.s_min = std::min(im.s_min, v);
                im.s_max = std::max(im.s_max, v);
            }
        }

        // Contract: a frame is emitted iff `day % every == 0` — no forced
        // first frame, so frame_count() == floor(total_days / every).
        const int every = std::max(1, im.cfg.every);
        if (day_index <= 0 || day_index % every != 0) return;

        im.draw(engine, history, day_index, total_days);
        if (!im.ok || !im.canvas) return;
        if (!GifWriteFrame(&im.writer, im.canvas->data(),
                           static_cast<uint32_t>(im.width),
                           static_cast<uint32_t>(im.height), im.frame_delay(),
                           8, false)) {
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

void GifViz::finish() {
    if (impl_ != nullptr) impl_->finish();
}

}  // namespace mal_abm_fast
