// SPDX-License-Identifier: MIT
// viz_common.cpp — shared raster primitives for the native GIF renderers.
//
// Implementations moved verbatim from viz.cpp (plan 04 / plan 05 §7) so
// both GIF renderers share one Canvas, one text path, and one palette.
// No behaviour change for map 1: every routine below is byte-for-byte the
// code that used to live in viz.cpp's anonymous namespace.
#include "mal_abm_fast/viz_common.hpp"

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <stdexcept>

#include "mal_abm_fast/third_party/font8x8_basic.hpp"
#include "mal_abm_fast/third_party/gif.h"

namespace mal_abm_fast {

// ---------------------------------------------------------------------------
// Colour
// ---------------------------------------------------------------------------

Color lerp(Color a, Color b, double t) {
    t = std::clamp(t, 0.0, 1.0);
    auto mix = [t](uint8_t x, uint8_t y) {
        return static_cast<uint8_t>(std::lround(
            static_cast<double>(x) * (1.0 - t) + static_cast<double>(y) * t));
    };
    return Color{mix(a.r, b.r), mix(a.g, b.g), mix(a.b, b.b), 255};
}

// ---------------------------------------------------------------------------
// Canvas
// ---------------------------------------------------------------------------

Canvas::Canvas(int w, int h)
    : w_(w), h_(h),
      px_(static_cast<size_t>(std::max(0, w)) *
              static_cast<size_t>(std::max(0, h)) * 4u,
          0) {}

bool Canvas::valid() const {
    return w_ > 0 && h_ > 0 &&
           px_.size() == static_cast<size_t>(w_) *
                             static_cast<size_t>(h_) * 4u;
}

void Canvas::fill(Color c) {
    for (size_t i = 0; i + 3 < px_.size(); i += 4) {
        px_[i] = c.r;
        px_[i + 1] = c.g;
        px_[i + 2] = c.b;
        px_[i + 3] = 255;
    }
}

void Canvas::blend(int x, int y, Color c) {
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

void Canvas::fill_rect(int x, int y, int w, int h, Color c) {
    if (w <= 0 || h <= 0) return;
    const int x0 = std::max(0, x);
    const int y0 = std::max(0, y);
    const int x1 = std::min(w_, x + w);
    const int y1 = std::min(h_, y + h);
    for (int yy = y0; yy < y1; ++yy)
        for (int xx = x0; xx < x1; ++xx) blend(xx, yy, c);
}

void Canvas::stroke_rect(int x, int y, int w, int h, Color c) {
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

void Canvas::disc(int cx, int cy, int r, Color c) {
    const int rr = std::max(0, r);
    for (int dy = -rr; dy <= rr; ++dy)
        for (int dx = -rr; dx <= rr; ++dx)
            if (dx * dx + dy * dy <= rr * rr) blend(cx + dx, cy + dy, c);
}

void Canvas::ring(int cx, int cy, int r, Color c) {
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

void Canvas::line(int x0, int y0, int x1, int y1, Color c) {
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

void Canvas::text(int x, int y, const std::string& s, Color c, int scale) {
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

// ---------------------------------------------------------------------------
// Text metrics / formatting
// ---------------------------------------------------------------------------

int text_w(const std::string& s, int scale) {
    return static_cast<int>(s.size()) * 8 * std::max(1, scale);
}

int text_scale_fit(const std::string& s, int avail_px) {
    return text_w(s, 2) <= avail_px ? 2 : 1;
}

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

// ---------------------------------------------------------------------------
// Plotting helpers
// ---------------------------------------------------------------------------

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

double dec_pow10(int d) {
    return std::pow(10.0, static_cast<double>(d));
}

// ---------------------------------------------------------------------------
// Shared panel chrome
// ---------------------------------------------------------------------------

void draw_panel_frame(Canvas& cv, int x, int y, int w, int h,
                      const std::string& title) {
    cv.fill_rect(x, y, w, h, kPanel);
    cv.stroke_rect(x, y, w, h, kPanelBorder);
    cv.text(x + 6, y + 5, title, kTextDim, text_scale_fit(title, w - 12));
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

// ---------------------------------------------------------------------------
// Shared palette
// ---------------------------------------------------------------------------

const Color kBackground{13, 15, 19, 255};
const Color kPanel{23, 26, 32, 255};
const Color kPanelBorder{48, 54, 66, 255};
const Color kText{228, 231, 238, 255};
const Color kTextDim{148, 155, 168, 255};
const Color kHostSeek{255, 190, 60, 255};
const Color kBloodFed{190, 110, 240, 255};
const Color kGravid{255, 60, 160, 255};
const Color kInfectious{255, 40, 40, 255};
const Color kPrev{214, 48, 48, 255};

// ---------------------------------------------------------------------------
// GifSink — the sole translation unit that compiles gif.h (plan 05 §7).
// ---------------------------------------------------------------------------

struct GifSink::Impl {
    GifWriter writer{};
    bool open = false;
};

GifSink::GifSink() = default;
GifSink::~GifSink() { close(); }

GifSink::GifSink(GifSink&&) noexcept = default;
GifSink& GifSink::operator=(GifSink&&) noexcept = default;

bool GifSink::open(const std::string& path, int width, int height,
                   uint32_t delay_cs) {
    close();
    impl_ = std::make_unique<Impl>();
    if (path.empty() || width <= 0 || height <= 0) return false;
    if (!GifBegin(&impl_->writer, path.c_str(), static_cast<uint32_t>(width),
                  static_cast<uint32_t>(height), delay_cs, 8, false)) {
        impl_.reset();
        return false;
    }
    impl_->open = true;
    return true;
}

bool GifSink::write_frame(const uint8_t* rgba, int width, int height,
                          uint32_t delay_cs) {
    if (!impl_ || !impl_->open || rgba == nullptr) return false;
    return GifWriteFrame(&impl_->writer, rgba, static_cast<uint32_t>(width),
                         static_cast<uint32_t>(height), delay_cs, 8, false);
}

void GifSink::close() {
    if (impl_ && impl_->open) {
        GifEnd(&impl_->writer);
        impl_->open = false;
    }
    impl_.reset();
}

bool GifSink::is_open() const { return impl_ != nullptr && impl_->open; }

}  // namespace mal_abm_fast
