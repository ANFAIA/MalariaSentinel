#!/usr/bin/env python3
"""Fase 1 mobility diagnostics (M7.8).

Computes deterministic and sampled effective host grids from the real OD CSR
matrices + host_static.nc, and emits the Fase 1 plausibility-gate outputs
(plan m7-8 section 4.2): PNG maps + mobility_diagnostics.json with mass
conservation, weighted centroids, OD distance percentiles and top cells.

Usage:
    uv run python mal-core/src/mal_core/abm/scripts/visualize_mobility.py \
        --aoi ghana --seed 1 --days 2
"""
from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr

# Species phase activity weights (An. coluzzii default), TimePhase order.
PHASE_NAMES = ["DAY", "EVENING", "NIGHT", "DAWN"]
SPECIES_WEIGHTS = np.array([0.02, 0.10, 0.80, 0.08], dtype=np.float64)

LIVESTOCK_VARS = ["cattle", "goats", "sheep", "pigs", "chickens"]
HUMAN_VAR = "human"

DIST_EDGE_KM = 0.25  # histogram resolution for OD distance percentiles


def read_csr(path: Path):
    """Read binary CSR: [int32 nrows, int32 ncols, int32 nnz, row_ptr, col_idx, values]."""
    with open(path, "rb") as f:
        nrows, ncols, nnz = struct.unpack("iii", f.read(12))
        row_ptr = np.fromfile(f, dtype=np.int32, count=nrows + 1)
        col_idx = np.fromfile(f, dtype=np.int32, count=nnz)
        values = np.fromfile(f, dtype=np.float32, count=nnz)
    return nrows, ncols, nnz, row_ptr, col_idx, values


def rounded_stock(res: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Stochastic rounding: int = floor(N) + Bernoulli(frac); E[int] == N."""
    lo = np.floor(res).astype(np.int64)
    frac = res - np.floor(res)
    add = (rng.random(len(res)) < frac).astype(np.int64)
    return lo + add


def analyze_matrix(
    row_ptr: np.ndarray,
    col_idx: np.ndarray,
    values: np.ndarray,
    res: np.ndarray,
    grid_h: int,
    grid_w: int,
    cell_size_km: float,
    max_distance_km: float,
    chunk: int = 100_000,
):
    """Deterministic H_eff + distance diagnostics on the full CSR.

    H_eff[j] = Σ_i P(i→j) · res[i]. Processed in row chunks so the large
    livestock matrix (197M nnz) never materialises in full. Returns:
      H                 float64 (n_cells)
      moved_per_origin  float64 (nrows) mass that leaves its origin cell
      dist_hist         float64 weighted OD mass by distance bin
      dist_edges        float64 bin edges (km)
      total_res, mass_self, mass_moved
    """
    n_cells = len(res)
    nrows = row_ptr.size - 1
    counts = np.diff(row_ptr)
    total_res = float(np.sum(res, dtype=np.float64))

    H = np.zeros(n_cells, dtype=np.float64)
    moved_per_origin = np.zeros(nrows, dtype=np.float64)

    n_bins = max(1, int(max_distance_km / DIST_EDGE_KM))
    dist_edges = np.arange(n_bins + 2, dtype=np.float64) * DIST_EDGE_KM
    dist_hist = np.zeros(n_bins + 1, dtype=np.float64)
    mass_self = 0.0

    res_f64 = res.astype(np.float64)
    for start in range(0, nrows, chunk):
        end = min(start + chunk, nrows)
        s0, s1 = int(row_ptr[start]), int(row_ptr[end])
        local_col = col_idx[s0:s1]
        local_val = values[s0:s1]
        local_counts = counts[start:end]

        orig_flat = np.repeat(np.arange(start, end, dtype=np.int32), local_counts)
        res_origin = np.repeat(res_f64[start:end], local_counts)
        contrib = local_val.astype(np.float64) * res_origin

        np.add.at(H, local_col, contrib)

        orig_row = orig_flat // grid_w
        orig_col = orig_flat - orig_row * grid_w
        dest_row = local_col // grid_w
        dest_col = local_col - dest_row * grid_w
        dr = (orig_row - dest_row).astype(np.float64)
        dc = (orig_col - dest_col).astype(np.float64)
        dist_km = np.sqrt(dr * dr + dc * dc) * cell_size_km

        moved_mask = dist_km > 0.0
        moved = np.where(moved_mask, contrib, 0.0)
        np.add.at(moved_per_origin, orig_flat, moved)
        mass_self += float(np.sum(contrib[~moved_mask]))

        hist, _ = np.histogram(dist_km, bins=dist_edges, weights=contrib)
        dist_hist += hist

    mass_moved = float(np.sum(moved_per_origin, dtype=np.float64))
    return H, moved_per_origin, dist_hist, dist_edges, total_res, mass_self, mass_moved


def sample_effective_hosts(
    res: np.ndarray,
    row_ptr: np.ndarray,
    col_idx: np.ndarray,
    values: np.ndarray,
    rng: np.random.Generator,
):
    """Per-origin multinomial realization. Conserves Σ round(N_i) exactly.

    Returns (H, rounded_total) where rounded_total is the stochastic-rounding
    integer stock total this realization conserves.
    """
    n_cells = len(res)
    stock = rounded_stock(res, rng)
    H = np.zeros(n_cells, dtype=np.float64)
    starts = row_ptr[:-1]
    ends = row_ptr[1:]
    for i in range(n_cells):
        n_i = int(stock[i])
        if n_i <= 0:
            continue
        s, e = int(starts[i]), int(ends[i])
        if e - s == 1:
            H[col_idx[s]] += n_i
            continue
        p = values[s:e].astype(np.float64)
        p /= p.sum()
        flow = rng.multinomial(n_i, p)
        H[col_idx[s:e]] += flow
    return H, int(stock.sum())


def weighted_percentiles(dist_hist, dist_edges, quants=(10, 25, 50, 75, 90, 99)):
    """Weighted distance percentiles of the MOVED mass (dist > 0)."""
    bins = dist_hist[1:]  # drop the dist==0 bin
    total = float(bins.sum())
    if total <= 0:
        return {f"p{q}": None for q in quants}
    cum = np.cumsum(bins) / total
    mids = (dist_edges[1:-1] + dist_edges[2:]) / 2.0
    out = {}
    for q in quants:
        t = q / 100.0
        idx = int(np.searchsorted(cum, t))
        out[f"p{q}"] = float(mids[min(idx, len(mids) - 1)])
    return out


def gridify(H: np.ndarray, grid_h: int, grid_w: int) -> np.ndarray:
    return np.asarray(H, dtype=np.float64).reshape(grid_h, grid_w)


def downsample(arr: np.ndarray, target: int = 220) -> np.ndarray:
    """Block-sum downsample to at most target cells per side (for maps)."""
    h, w = arr.shape
    fh = max(1, h // target)
    fw = max(1, w // target)
    nh, nw = h // fh, w // fw
    return arr[: nh * fh, : nw * fw].reshape(nh, fh, nw, fw).sum(axis=(1, 3))


def save_map(arr: np.ndarray, title: str, out_path: Path, cmap: str = "YlOrRd",
             log: bool = True, vmin_pct: float = 0.5, vmax_pct: float = 99.0):
    fig, ax = plt.subplots(figsize=(8, 11), dpi=120)
    a = np.asarray(arr, dtype=np.float64)
    a = np.where(np.isnan(a), 0.0, a)
    if log:
        a = np.log1p(a)
        norm = None
    else:
        lo = np.percentile(a[a > 0], vmin_pct) if np.any(a > 0) else 0.0
        hi = np.percentile(a[a > 0], vmax_pct) if np.any(a > 0) else 1.0
        norm = __import__("matplotlib").colors.Normalize(vmin=lo, vmax=hi)
    im = ax.imshow(a, cmap=cmap, origin="lower", norm=norm)
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    ax.set_title(title, fontsize=13)
    ax.set_axis_off()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)
    print(f"  saved {out_path.name}")


def centroid(grid: np.ndarray) -> tuple[float, float]:
    rows = np.arange(grid.shape[0])[:, None]
    cols = np.arange(grid.shape[1])[None, :]
    tot = float(grid.sum())
    if tot <= 0:
        return (0.0, 0.0)
    return (float((grid * rows).sum() / tot), float((grid * cols).sum() / tot))


def top_n(arr: np.ndarray, n: int, grid_w: int):
    if len(arr) == 0:
        return []
    n = min(n, len(arr))
    idx = np.argpartition(arr, -n)[-n:]
    idx = idx[np.argsort(arr[idx])[::-1]]
    return [{"cell": int(i), "row": int(i // grid_w), "col": int(i % grid_w),
             "value": float(arr[i])} for i in idx]


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Fase 1 mobility diagnostics.")
    parser.add_argument("--aoi", default="ghana", help="AOI slug (default: ghana)")
    parser.add_argument("--data-dir", type=Path, default=None,
                        help="Data dir (default: data/<aoi>)")
    parser.add_argument("--host-nc", type=Path, default=None,
                        help="Host static NC (default: <data-dir>/<aoi>_host_static.nc)")
    parser.add_argument("--output-dir", type=Path,
                        default=Path("runs/abm/mobility_diagnostics"),
                        help="Output directory")
    parser.add_argument("--seed", type=int, default=1, help="RNG seed")
    parser.add_argument("--days", type=int, default=2,
                        help="Number of sampled days for realizations")
    args = parser.parse_args(argv)

    aoi = args.aoi
    data_dir = args.data_dir or Path("data") / aoi
    host_nc = args.host_nc or data_dir / f"{aoi}_host_static.nc"
    out_dir = args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    day_csr = data_dir / f"{aoi}_mobility_day.csr"
    night_csr = data_dir / f"{aoi}_mobility_night.csr"
    live_csr = data_dir / f"{aoi}_livestock_mobility.csr"
    manifest = data_dir / "mobility_manifest.json"

    # Beta parameters: manifest is the single source when present.
    beta_day, beta_night, beta_livestock = 0.05, 0.5, 0.1
    max_distance_km = 50.0
    if manifest.exists():
        m = json.loads(manifest.read_text())
        beta_day = m.get("beta_day", beta_day)
        beta_night = m.get("beta_night", beta_night)
        beta_livestock = m.get("beta_livestock", beta_livestock)
        max_distance_km = m.get("max_distance_km", max_distance_km)

    print(f"[mobility] AOI={aoi} data={data_dir}")
    print(f"[mobility] beta day/night/livestock = {beta_day}/{beta_night}/{beta_livestock}")
    print(f"[mobility] max_distance_km = {max_distance_km}")

    # --- residential hosts --------------------------------------------------
    ds = xr.open_dataset(host_nc)
    grid_h, grid_w = int(ds.sizes["y"]), int(ds.sizes["x"])
    n_cells = grid_h * grid_w
    print(f"[mobility] grid {grid_h}x{grid_w} = {n_cells} cells")

    human_res = np.nan_to_num(ds[HUMAN_VAR].values.astype(np.float64).ravel())
    live_res = np.zeros(n_cells, dtype=np.float64)
    for v in LIVESTOCK_VARS:
        live_res += np.nan_to_num(ds[v].values.astype(np.float64).ravel())
    ds.close()
    human_total = float(human_res.sum())
    live_total = float(live_res.sum())
    print(f"[mobility] residential humans={human_total:.1f} livestock={live_total:.1f}")

    # --- load CSR matrices ---------------------------------------------------
    print("[mobility] loading day CSR ...")
    nrow_d, ncol_d, nnz_d, rp_d, ci_d, vl_d = read_csr(day_csr)
    print(f"[mobility]   day {nrow_d}x{ncol_d} nnz={nnz_d}")
    print("[mobility] loading night CSR ...")
    nrow_n, ncol_n, nnz_n, rp_n, ci_n, vl_n = read_csr(night_csr)
    print(f"[mobility]   night {nrow_n}x{ncol_n} nnz={nnz_n}")
    print("[mobility] loading livestock CSR ...")
    nrow_l, ncol_l, nnz_l, rp_l, ci_l, vl_l = read_csr(live_csr)
    print(f"[mobility]   livestock {nrow_l}x{ncol_l} nnz={nnz_l}")

    cell_size_km = 1.0  # ABM grid is 1 km cells

    # --- deterministic effective hosts ---------------------------------------
    print("[mobility] deterministic expectations ...")
    H_day, mv_day, hist_day, edges_day, _, ms_day, mm_day = analyze_matrix(
        rp_d, ci_d, vl_d, human_res, grid_h, grid_w, cell_size_km, max_distance_km)
    print(f"[mobility]   day H_eff total={H_day.sum():.1f} (res {human_total:.1f})")
    H_night, mv_night, hist_night, edges_night, _, ms_night, mm_night = analyze_matrix(
        rp_n, ci_n, vl_n, human_res, grid_h, grid_w, cell_size_km, max_distance_km)
    print(f"[mobility]   night H_eff total={H_night.sum():.1f} (res {human_total:.1f})")
    H_live, mv_live, hist_live, edges_live, _, ms_live, mm_live = analyze_matrix(
        rp_l, ci_l, vl_l, live_res, grid_h, grid_w, cell_size_km, max_distance_km)
    print(f"[mobility]   livestock H_eff total={H_live.sum():.1f} (res {live_total:.1f})")

    # Livestock night = identity.
    H_live_night = live_res.copy()

    # Species daily aggregate for humans:
    #   DAY/EVENING/DAWN use the day matrix, NIGHT the night matrix.
    w_day = SPECIES_WEIGHTS[0] + SPECIES_WEIGHTS[1] + SPECIES_WEIGHTS[3]
    w_night = SPECIES_WEIGHTS[2]
    H_daily = w_day * H_day + w_night * H_night

    # --- sampled realizations ------------------------------------------------
    print(f"[mobility] sampling {args.days} days (seed {args.seed}) ...")
    sampled = {}
    for d in range(args.days):
        seed_off = args.seed + 1000 * d
        # Human day phase
        rng_d = np.random.default_rng(seed_off)
        s_day, rnd_h_day = sample_effective_hosts(human_res, rp_d, ci_d, vl_d, rng_d)
        s_night, rnd_h_night = sample_effective_hosts(human_res, rp_n, ci_n, vl_n,
                                                      np.random.default_rng(seed_off + 1))
        s_live, rnd_l = sample_effective_hosts(live_res, rp_l, ci_l, vl_l,
                                               np.random.default_rng(seed_off + 2))
        sampled[f"day_{d}"] = {
            "human_day": float(s_day.sum()),
            "human_night": float(s_night.sum()),
            "livestock_day": float(s_live.sum()),
            "round_human_res_day": rnd_h_day,
            "round_human_res_night": rnd_h_night,
            "round_livestock_res": rnd_l,
        }
        # Per-day mass conservation vs the per-phase rounded stock.
        assert abs(s_day.sum() - rnd_h_day) < 1e-3, "human day mass not conserved"
        assert abs(s_night.sum() - rnd_h_night) < 1e-3, "human night mass not conserved"
        assert abs(s_live.sum() - rnd_l) < 1e-3, "livestock mass not conserved"
        print(f"  day {d}: human {s_day.sum():.1f} | night {s_night.sum():.1f} "
              f"| livestock {s_live.sum():.1f}")

    # --- diagnostics numbers ---------------------------------------------------
    def frac_leq(hist, edges, r):
        idx = int(np.searchsorted(edges, r, side="right"))
        return float(hist[:idx].sum() / max(hist.sum(), 1e-12))

    def mat_diag(hist, edges, total_res, mass_self, mass_moved, name):
        return {
            "total_residential": round(total_res, 3),
            "mass_self_loop": round(mass_self, 3),
            "mass_moved": round(mass_moved, 3),
            "frac_leaving_origin": round(mass_moved / max(total_res, 1e-12), 5),
            "frac_leq_1km": round(frac_leq(hist, edges, 1.0), 5),
            "frac_leq_5km": round(frac_leq(hist, edges, 5.0), 5),
            "frac_leq_10km": round(frac_leq(hist, edges, 10.0), 5),
            "frac_leq_50km": round(frac_leq(hist, edges, 50.0), 5),
            "percentiles_km": weighted_percentiles(hist, edges),
        }

    g_res_h = gridify(human_res, grid_h, grid_w)
    g_res_l = gridify(live_res, grid_h, grid_w)
    g_day = gridify(H_day, grid_h, grid_w)
    g_night = gridify(H_night, grid_h, grid_w)
    g_live = gridify(H_live, grid_h, grid_w)
    g_daily = gridify(H_daily, grid_h, grid_w)

    c_res_h = centroid(g_res_h)
    c_day = centroid(g_day)
    c_night = centroid(g_night)
    c_res_l = centroid(g_res_l)
    c_live = centroid(g_live)

    def disp(a, b):
        return float(np.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2))

    diag = {
        "aoi": aoi,
        "grid": {"height": grid_h, "width": grid_w, "n_cells": n_cells,
                 "cell_size_km": cell_size_km},
        "beta": {"day": beta_day, "night": beta_night, "livestock": beta_livestock,
                 "max_distance_km": max_distance_km},
        "matrices": {
            "day": {"file": day_csr.name, "nnz": nnz_d},
            "night": {"file": night_csr.name, "nnz": nnz_n},
            "livestock": {"file": live_csr.name, "nnz": nnz_l},
        },
        "phase_weights": {p: float(w) for p, w in zip(PHASE_NAMES, SPECIES_WEIGHTS)},
        "mass": {
            "human": {
                "residential": round(human_total, 3),
                "effective_day": round(float(H_day.sum()), 3),
                "effective_night": round(float(H_night.sum()), 3),
                "daily_aggregate": round(float(H_daily.sum()), 3),
                "conservation_day_rel": round(float(H_day.sum() / max(human_total, 1e-12) - 1.0), 8),
                "conservation_night_rel": round(float(H_night.sum() / max(human_total, 1e-12) - 1.0), 8),
                "sampled": sampled,
            },
            "livestock": {
                "residential": round(live_total, 3),
                "effective_day": round(float(H_live.sum()), 3),
                "effective_night": round(float(H_live_night.sum()), 3),
                "conservation_day_rel": round(float(H_live.sum() / max(live_total, 1e-12) - 1.0), 8),
            },
        },
        "centroids": {
            "human": {
                "residential": {"row": round(c_res_h[0], 3), "col": round(c_res_h[1], 3)},
                "day": {"row": round(c_day[0], 3), "col": round(c_day[1], 3),
                        "displacement_cells": round(disp(c_res_h, c_day), 3),
                        "displacement_km": round(disp(c_res_h, c_day) * cell_size_km, 3)},
                "night": {"row": round(c_night[0], 3), "col": round(c_night[1], 3),
                          "displacement_cells": round(disp(c_res_h, c_night), 3),
                          "displacement_km": round(disp(c_res_h, c_night) * cell_size_km, 3)},
            },
            "livestock": {
                "residential": {"row": round(c_res_l[0], 3), "col": round(c_res_l[1], 3)},
                "day": {"row": round(c_live[0], 3), "col": round(c_live[1], 3),
                        "displacement_cells": round(disp(c_res_l, c_live), 3),
                        "displacement_km": round(disp(c_res_l, c_live) * cell_size_km, 3)},
            },
        },
        "distance": {
            "day": mat_diag(hist_day, edges_day, human_total, ms_day, mm_day, "day"),
            "night": mat_diag(hist_night, edges_night, human_total, ms_night, mm_night, "night"),
            "livestock": mat_diag(hist_live, edges_live, live_total, ms_live, mm_live, "livestock"),
        },
        "top_destinations": {
            "day": top_n(H_day, 10, grid_w),
            "night": top_n(H_night, 10, grid_w),
            "livestock": top_n(H_live, 10, grid_w),
        },
        "top_emitters": {
            "day": top_n(mv_day, 10, grid_w),
            "night": top_n(mv_night, 10, grid_w),
            "livestock": top_n(mv_live, 10, grid_w),
        },
        "seed": args.seed,
        "days": args.days,
    }

    json_path = out_dir / "mobility_diagnostics.json"
    json_path.write_text(json.dumps(diag, indent=2))
    print(f"saved {json_path.name}")

    # --- maps -------------------------------------------------------------------
    print("[mobility] rendering maps ...")
    d = downsample
    save_map(d(g_res_h), f"{aoi} — residential human density", out_dir / f"{aoi}_H_residential.png")
    save_map(d(g_day), f"{aoi} — H_eff DAY (human)", out_dir / f"{aoi}_hosts_phase_day.png")
    save_map(d(g_night), f"{aoi} — H_eff NIGHT (human)", out_dir / f"{aoi}_hosts_phase_night.png")
    save_map(d(g_live), f"{aoi} — H_eff DAY (livestock)", out_dir / f"{aoi}_hosts_phase_livestock.png")
    save_map(d(g_daily), f"{aoi} — H_expected daily aggregate (human)", out_dir / f"{aoi}_hosts_daily_aggregate.png")
    save_map(d(g_day - g_res_h), f"{aoi} — H_eff minus H_res (DAY)", out_dir / f"{aoi}_H_eff_minus_H_res.png", log=False)
    save_map(d(g_day) / (d(g_res_h) + 1e-6), f"{aoi} — H_eff / H_res (DAY)", out_dir / f"{aoi}_H_eff_over_H_res.png", log=True)

    print(f"[mobility] diagnostics written to {out_dir}")


if __name__ == "__main__":
    main()
