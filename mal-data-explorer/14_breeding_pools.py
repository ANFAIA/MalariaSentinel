"""Visualisation of mosquito breeding pools (charcas) with the M7.4.1
catchment-runoff + urban-baseline pool model (commits bfce93b, 17f08b6,
d23793a, 7f2a8c9).

Replicates in Python the dynamic-patch union + pool water balance that
`coordinator.cpp` runs per day, over the full env NC (2024-2025), and
renders ONE png in the same style as the `--debug` overlay
(humans green, livestock brown, permanent water cyan) plus the
breeding-pool layers:

  1. Base debug map (humanos / ganado / agua_perm)
  2. Charcas activas el día pico (urbana = magenta, terreno = ámbar,
     agua permanente = cian claro)
  3. Fracción de días activos 2024-2025 por celda
  4. Zoom Accra el día pico

Rules replicated (wire.hpp / coordinator.cpp):
  terrain: twi > 8 & water_frac > 0
  urban:   urban_class==30 & bldg>=0.05 & (rain>=12 | rain7d>=12) & twi>=7
  union:   permanent | ((terrain|urban) & rain > 15 mm)
  urban cap: top 5% of grid by building_fraction
  water:   W' = clip(W + rain*(1+CR*C_eff) - evap, 0, 500), evap =
           5*(1+0.07*(T-30)) * clamp(1-0.30*ndvi-0.15*urban, .55, 1)
  urban floor: water = max(water, 6 mm) on urban union cells
  active:  water >= 5 mm

Usage (from mal-data-explorer/):
  uv run python 14_breeding_pools.py
Output: ../runs/visualisations/breeding_pools/charcas_cria.png
"""
from __future__ import annotations

import pathlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import rasterio  # noqa: E402
import xarray as xr  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

DATA = pathlib.Path("../data/ghana")
OUT = pathlib.Path("../runs/visualisations/breeding_pools")
OUT.mkdir(parents=True, exist_ok=True)

ORIGIN_LON, ORIGIN_LAT, RES = -3.5, 11.5, 0.009074
# City cell coords (row, col) — knowledge-graph CONFIG_VALUES.
CITIES = {"Accra": (656, 364), "Kumasi": (535, 207), "Tamale": (233, 293)}

# wire.hpp constants
RAIN_UNION_MM = 15.0
TWI_TERRAIN = 8.0
URBAN_CLASS, URBAN_B_MIN, URBAN_R_MIN, URBAN_TWI_MIN = 30, 0.05, 12.0, 7.0
URBAN_CAP = 0.05
BREED_MM, DRY_MM, WMAX = 5.0, 1.0, 500.0
URBAN_BASELINE_MM = 6.0
EVAP_REF, EVAP_T0, EVAP_TK = 5.0, 30.0, 0.07
C_URB_BASE, C_URB_SLOPE = 0.40, 0.50
C_RUR_BASE, C_RUR_FLOOR, C_RUR_NDVI = 0.35, 0.05, 0.30
SAT_MIN, SAT_REF = 0.60, 25.0
EVAP_NDVI, EVAP_URBAN = 0.30, 0.15


def _to_lonlat(r: np.ndarray, c: np.ndarray):
    return ORIGIN_LON + (c + 0.5) * RES, ORIGIN_LAT - (r + 0.5) * RES


def main() -> None:
    env = xr.open_dataset(DATA / "ghana_regional_2024_2025_env.nc")
    host = xr.open_dataset(DATA / "ghana_host_static.nc")
    land = rasterio.open(DATA / "ghana_land_mask.tif").read(1)

    rain = np.asarray(env["rainfall"].values, dtype=np.float64)  # (t, y, x)
    temp = np.asarray(env["water_temp_c"].values, dtype=np.float64)
    temp = np.where(np.isnan(temp), 25.0, temp)
    wfrac = np.asarray(env["water_frac"].values, dtype=np.float64)
    def _static(name: str) -> np.ndarray:
        v = np.asarray(env[name].squeeze(), dtype=np.float64)
        return v[0] if v.ndim == 3 else v

    twi = np.nan_to_num(_static("twi"))
    cr = np.nan_to_num(_static("catchment_ratio"))
    ndvi = np.clip(np.nan_to_num(_static("ndvi")), 0.0, 1.0)
    perm = np.nan_to_num(_static("permanent_water_mask"))
    n_days, H, W = rain.shape

    urban = (np.asarray(host["urban_class"].squeeze()) == URBAN_CLASS) & (
        land > 0)
    bldg = np.nan_to_num(np.asarray(host["building_fraction"].squeeze()))
    land_ok = land > 0
    perm = np.where(land_ok, perm, 0.0)

    # Static per-cell coefficients
    evap_scale = np.clip(
        1.0 - EVAP_NDVI * ndvi - np.where(urban, EVAP_URBAN, 0.0), 0.55, 1.0)
    c_terrain = np.where(
        urban, C_URB_BASE + C_URB_SLOPE * np.clip(bldg, 0, 1),
        np.maximum(C_RUR_FLOOR, C_RUR_BASE - C_RUR_NDVI * ndvi))
    cap_cells = int(URBAN_CAP * H * W)

    water = np.zeros((H, W))
    registered = np.zeros((H, W), dtype=bool)
    days_dry = np.zeros((H, W), dtype=np.int32)
    rain7d = np.zeros((H, W))

    active_frac = np.zeros((H, W))
    perm_frac = np.zeros((H, W))
    urban_frac = np.zeros((H, W))
    snap: dict = {"day": -1, "active": np.zeros((H, W), dtype=bool),
                  "n_urb": 0, "n_rur": 0}
    best = -1  # n dynamic pools at the recorded snapshot
    urban_series, rural_series = [], []

    for t in range(n_days):
        rain7d = rain7d + rain[t]
        if t >= 7:
            rain7d -= rain[t - 7]

        terrain = (twi > TWI_TERRAIN) & (wfrac[t] > 0)
        urban_cand = (urban & (bldg >= URBAN_B_MIN)
                      & ((rain[t] >= URBAN_R_MIN) | (rain7d >= URBAN_R_MIN))
                      & (twi >= URBAN_TWI_MIN))
        dyn = (terrain | urban_cand) & (rain[t] > RAIN_UNION_MM)
        union = (perm > 0) | dyn

        # Urban density cap: top `cap_cells` urban cells by building_fraction
        u_idx = np.flatnonzero(dyn & urban)
        if u_idx.size > cap_cells:
            keep = u_idx[np.argsort(-bldg.ravel()[u_idx])[:cap_cells]]
            drop = np.setdiff1d(u_idx, keep, assume_unique=False)
            flat = dyn.ravel()
            flat[drop] = False
            dyn = flat.reshape(H, W)
            union = (perm > 0) | dyn

        idx = np.flatnonzero(union)
        if idx.size:
            r_t = rain[t].ravel()[idx]
            t_t = temp[t].ravel()[idx]
            ev = EVAP_REF * (1.0 + EVAP_TK * (t_t - EVAP_T0))
            ev = np.maximum(ev, 0.5) * evap_scale.ravel()[idx]
            c_moist = SAT_MIN + (1 - SAT_MIN) * np.minimum(
                1.0, rain7d.ravel()[idx] / SAT_REF)
            c_eff = c_terrain.ravel()[idx] * c_moist
            rain_in = r_t * (1.0 + cr.ravel()[idx] * c_eff)

            w = water.ravel()
            first = ~registered.ravel()[idx]
            w[idx[first]] = r_t[first] * (1.0 + cr.ravel()[idx[first]]
                                          * c_eff[first])
            registered.ravel()[idx[~first]] = True
            adv = idx[~first]
            w[adv] = np.clip(w[adv] + rain_in[~first] - ev[~first], 0.0, WMAX)

            days_dry.ravel()[idx] = np.where(
                w[idx] < DRY_MM, days_dry.ravel()[idx] + 1, 0)

            u_mask = urban.ravel()[idx]
            w[idx[u_mask]] = np.maximum(w[idx[u_mask]], URBAN_BASELINE_MM)
            days_dry.ravel()[idx[u_mask]] = 0

            p_mask = (perm > 0).ravel()[idx]
            w[idx[p_mask]] = WMAX
            days_dry.ravel()[idx[p_mask]] = 0
            water = w.reshape(H, W)

        active = union & (water >= BREED_MM)
        active_frac += (active & ~((perm > 0))).astype(np.float64)
        perm_frac += ((perm > 0) & active).astype(np.float64)
        urban_frac += (active & urban & (perm == 0)).astype(np.float64)

        n_urb = int((active & urban & (perm == 0)).sum())
        n_rur = int((active & ~urban & (perm == 0)).sum())
        urban_series.append(n_urb)
        rural_series.append(n_rur)
        if n_urb + n_rur > best:
            best = n_urb + n_rur
            snap = {"day": t, "active": active.copy(),
                    "n_urb": n_urb, "n_rur": n_rur}
    active_frac /= n_days
    perm_frac /= n_days
    urban_frac /= n_days
    print(f"días: {n_days}  día pico: d{snap['day']} "
          f"(urbanas {snap['n_urb']:,} / terreno {snap['n_rur']:,})")
    for city, (r, c) in CITIES.items():
        r0, r1 = max(0, r - 55), r + 55
        c0, c1 = max(0, c - 55), c + 55
        n = int((snap["active"][r0:r1, c0:c1] & urban[r0:r1, c0:c1]).sum())
        print(f"  {city}: {n:,} celdas-urbano activas en ±5 km (día pico)")

    # ------------------------------------------------------------------ PNG
    human = np.asarray(host["human"].squeeze(), dtype=float)
    livestock = (
        np.asarray(host["cattle"].squeeze(), dtype=float)
        + np.asarray(host["goats"].squeeze(), dtype=float)
        + np.asarray(host["sheep"].squeeze(), dtype=float)
        + np.asarray(host["pigs"].squeeze(), dtype=float))

    def norm_log(a, q=99.0):
        v = np.log1p(np.clip(a, 0, None))
        pos = v[v > 0]
        hi = np.percentile(pos, q) if pos.size else 1.0
        return np.clip(v / (hi or 1.0), 0, 1)

    Hn, Ln = norm_log(human), norm_log(livestock)
    base = np.clip(
        np.stack([Hn * .15, Hn * .85, Hn * .35], -1)
        + np.stack([Ln * .75, Ln * .55, Ln * .20], -1)
        + np.stack([perm * .10, perm * .45, perm * .95], -1), 0, 1)
    dim = 0.25 + 0.75 * base  # keep hosts faintly visible under pools

    ext = [ORIGIN_LON, ORIGIN_LON + W * RES,
           ORIGIN_LAT - H * RES, ORIGIN_LAT]
    fig, axes = plt.subplots(2, 2, figsize=(13, 15))
    day_lbl = f"d{snap['day']:03d}"

    # Panel A — base debug
    ax = axes[0, 0]
    ax.imshow(base, extent=ext, origin="upper", interpolation="nearest")
    ax.set_title("Base (estilo --debug): humanos, ganado, agua perm.",
                 fontsize=10)

    # Panel B — charcas día pico
    ax = axes[0, 1]
    ax.imshow(dim, extent=ext, origin="upper", interpolation="nearest")
    urb_a = np.ma.masked_where(
        ~(snap["active"] & urban & (perm == 0)), np.ones((H, W)))
    rur_a = np.ma.masked_where(
        ~(snap["active"] & ~urban & (perm == 0)), np.ones((H, W)))
    ax.imshow(urb_a, extent=ext, origin="upper", cmap="magma",
              vmin=0, vmax=2.2, interpolation="nearest", alpha=0.95)
    ax.imshow(rur_a, extent=ext, origin="upper", cmap="copper",
              vmin=0, vmax=2.2, interpolation="nearest", alpha=0.85)
    ax.set_title(f"Charcas activas {day_lbl} — urbanas {snap['n_urb']:,} "
                 f"(magenta) / terreno {snap['n_rur']:,} (ámbar)", fontsize=10)

    # Panel C — días activos por celda
    ax = axes[1, 0]
    days_active = np.round((active_frac + urban_frac) * n_days).astype(int)
    vmax = int(np.percentile(days_active[days_active > 0], 99)) if (
        days_active > 0).any() else 1
    img = ax.imshow(np.ma.masked_where(days_active == 0, days_active),
                    extent=ext, origin="upper", cmap="inferno", vmin=1,
                    vmax=max(vmax, 2), interpolation="nearest")
    pos = days_active[days_active > 0]
    ax.set_title(
        f"Días activos por celda 2024-25 (media {pos.mean():.0f}, "
        f"máx {pos.max()}) — solo lluvia >{RAIN_UNION_MM:.0f} mm activa",
        fontsize=10)
    plt.colorbar(img, ax=ax, shrink=0.6, label="días activos / 731")

    # Panel D — zoom Accra día pico
    ax = axes[1, 1]
    r, c = CITIES["Accra"]
    r0, r1, c0, c1 = max(0, r - 90), min(H, r + 90), max(0, c - 90), min(W, c + 90)
    zext = [ORIGIN_LON + c0 * RES, ORIGIN_LON + c1 * RES,
            ORIGIN_LAT - r1 * RES, ORIGIN_LAT - r0 * RES]
    ax.imshow(dim[r0:r1, c0:c1], extent=zext, origin="upper",
              interpolation="nearest")
    ax.imshow(urb_a[r0:r1, c0:c1], extent=zext, origin="upper", cmap="magma",
              vmin=0, vmax=2.2, interpolation="nearest", alpha=0.95)
    ax.imshow(rur_a[r0:r1, c0:c1], extent=zext, origin="upper", cmap="copper",
              vmin=0, vmax=2.2, interpolation="nearest", alpha=0.85)
    lon_c, lat_c = _to_lonlat(np.array([r]), np.array([c]))
    lon_c, lat_c = float(lon_c[0]), float(lat_c[0])
    ax.plot(lon_c, lat_c, "*", ms=14, color="lime", mec="k")
    ax.text(lon_c, lat_c - 0.05, "Accra", color="lime", fontsize=9,
            ha="center", weight="bold")
    ax.set_title(f"Zoom Accra {day_lbl} — charcas urbanas dentro de la ciudad",
                 fontsize=10)

    for ax in axes.flat:
        ax.set_xticks([]), ax.set_yticks([])
        for city, (rr, cc) in CITIES.items():
            lon, lat = _to_lonlat(np.array([rr]), np.array([cc]))
            lon, lat = float(lon[0]), float(lat[0])
            if ax in (axes[1, 1],):
                continue
            ax.plot(lon, lat, ".", ms=4, color="w", mec="k", mew=.5)
            ax.text(lon, lat, city, color="w", fontsize=7, ha="center")

    leg = [
        Line2D([0], [0], marker="s", color="w", markerfacecolor=(.15, .85, .35),
               ms=10, label="Humanos"),
        Line2D([0], [0], marker="s", color="w", markerfacecolor=(.75, .55, .20),
               ms=10, label="Ganado"),
        Line2D([0], [0], marker="s", color="w", markerfacecolor=(.1, .45, .95),
               ms=10, label="Agua perm."),
        Line2D([0], [0], marker="s", color="w", markerfacecolor="#b73779",
               ms=10, label="Charca urbana (baseline 6 mm; activa con lluvia >15 mm)"),
        Line2D([0], [0], marker="s", color="w", markerfacecolor="#8c4a2f",
               ms=10, label="Charca de terreno (temporal)"),
    ]
    fig.legend(handles=leg, loc="lower center", ncol=5, fontsize=9,
               framealpha=0.9)
    fig.suptitle(
        "Charcas de cría del mosquito — modelo catchment-runoff + baseline "
        f"urbano (6 mm)\n{best:,} charcas dinámicas activas el día pico "
        f"({day_lbl}); umbral de cría: 5 mm", fontsize=12)
    fig.tight_layout(rect=(0, 0.04, 1, 0.96))
    out = OUT / "charcas_cria.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"PNG -> {out}")


if __name__ == "__main__":
    main()
