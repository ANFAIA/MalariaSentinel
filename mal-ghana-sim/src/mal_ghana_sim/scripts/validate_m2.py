"""M2 validation: build_env + 100 abm_run rollouts + AUC vs 20 larval sites.

Drives the M1.3b (build_env) + M1.4 (abm_run) stack end-to-end on real Ghana
data and validates the mean suitability field against the 20 unique larval
sites in ``data/ghana_idit/occurrence.txt`` using the casablanca
``auc_with_ci`` implementation.

Usage:
    uv run python -m mal_ghana_sim.scripts.validate_m2 \\
        --aoi ghana --year 2024 --month 06 \\
        --output-dir data/runs/ghana/m2 \\
        --n-rollouts 100 --bootstrap 1000
    uv run python -m mal_ghana_sim.scripts.validate_m2 --help

Output:
    <output-dir>/<aoi>_<scale>_<YYYY>_<MM>_env.tif                  COG, 4 bands
    <output-dir>/<aoi>_<scale>_<YYYY>_<MM>_env.json                 sidecar
    <output-dir>/<aoi>_<scale>_<YYYY>_<MM>_habitat_patches.gpkg
    <output-dir>/rollouts/<aoi>_<scale>_<YYYY>_<MM>_seed{seed:04d}.tif
    <output-dir>/suitability_mean_<YYYY>_<MM>.tif                   COG, 1 band
    <output-dir>/m2_validation_scatter.png                          plot for the report
    <output-dir>/M2_REPORT.md                                       human-readable report
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import subprocess
import sys
import time
from datetime import datetime, timezone
from typing import Any, Mapping

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import rasterio
import typer
from rasterio.transform import Affine

from mal_commonlib.aoi import AOI, Scale
from mal_ghana_sim import config as C
from mal_ghana_sim.suitability import auc_with_ci, load_occurrences


# Path to the package's mal-ghana-sim/ root (cwd for child `uv run` invocations).
_REPO_ROOT = pathlib.Path(__file__).resolve().parents[4]
_GHANA_SIM_ROOT = _REPO_ROOT / "mal-ghana-sim"
_OCCURRENCE_PATH = C.OCCURRENCE
_AUC_CI_TARGET = 0.65  # design doc: lower 95% bootstrap bound must exceed this


# Minimal in-repo slug registry (mirrors build_env.py + abm/run.py).
_DEFAULT_REGISTRY: dict[str, AOI] = {
    "ghana": AOI.from_bbox(-3.5, 4.5, 1.5, 11.5, "EPSG:4326", "ghana", 1000),
}


app = typer.Typer(
    add_completion=False,
    help=(
        "M2 validation: build_env + N abm_run rollouts + AUC vs larval sites. "
        "Writes env COG, rollouts, suitability mean, and M2_REPORT.md."
    ),
)


# -- helpers ----------------------------------------------------------------


def _resolve_aoi_obj(aoi: str) -> AOI:
    """Resolve an AOI slug against the in-repo registry. Mirrors build_env."""
    if aoi in _DEFAULT_REGISTRY:
        return _DEFAULT_REGISTRY[aoi]
    raise typer.BadParameter(
        f"unknown AOI slug {aoi!r}; pass one of: {sorted(_DEFAULT_REGISTRY)}"
    )


def _env_filename(aoi_obj: AOI, year: int, month: int) -> str:
    return f"{aoi_obj.slug}_{aoi_obj.scale.value}_{year:04d}_{month:02d}_env.tif"


def _env_path(output_dir: pathlib.Path, aoi_obj: AOI, year: int, month: int) -> pathlib.Path:
    return output_dir / _env_filename(aoi_obj, year, month)


def _habitat_path(output_dir: pathlib.Path, aoi_obj: AOI, year: int, month: int) -> pathlib.Path:
    return output_dir / _env_filename(aoi_obj, year, month).replace("_env.tif", "_habitat_patches.gpkg")


def _sidecar_path(env_path: pathlib.Path) -> pathlib.Path:
    return env_path.with_suffix(".json")


def _run_build_env(
    aoi: str,
    year: int,
    month: int,
    output_dir: pathlib.Path,
    *,
    scale: Scale = Scale.REGIONAL,
    skip_era5: bool = False,
    skip_modis: bool = False,
    skip_worldcover: bool = False,
) -> None:
    """Invoke the M1.3b build_env CLI as a subprocess.

    The env COG, sidecar, and habitat gpkg land in ``output_dir``. We pass
    ``env=os.environ.copy()`` explicitly so CDS / EARTHDATA / OPENTOPO auth
    propagates even if a future refactor changes ``subprocess`` defaults.
    """
    cmd = [
        "uv", "run", "python", "-m", "mal_ghana_sim.scripts.build_env",
        "--aoi", aoi,
        "--year", str(year),
        "--month", str(month),
        "--output-dir", str(output_dir),
        "--scale", scale.value,
    ]
    if skip_era5:
        cmd.append("--skip-era5")
    if skip_modis:
        cmd.append("--skip-modis")
    if skip_worldcover:
        cmd.append("--skip-worldcover")
    subprocess.run(
        cmd, check=True, cwd=str(_GHANA_SIM_ROOT), env=os.environ.copy(),
    )


def _run_abm_rollout(
    seed: int,
    year: int,
    month: int,
    env_path: pathlib.Path,
    habitat_path: pathlib.Path,
    output_path: pathlib.Path,
    *,
    aoi: str = "ghana",
    scale: Scale = Scale.REGIONAL,
    days: int = 30,
) -> None:
    """Invoke the M1.4 abm_run CLI for one seed."""
    cmd = [
        "uv", "run", "python", "-m", "mal_ghana_sim.abm.run",
        "--aoi", aoi,
        "--year", str(year),
        "--month", str(month),
        "--seed", str(seed),
        "--env", str(env_path),
        "--habitat", str(habitat_path),
        "--output", str(output_path),
        "--days", str(days),
        "--scale", scale.value,
    ]
    subprocess.run(
        cmd, check=True, cwd=str(_GHANA_SIM_ROOT), env=os.environ.copy(),
    )


def _aggregate_suitability(
    rollout_paths: list[pathlib.Path],
    output_path: pathlib.Path,
) -> dict:
    """Stack band 2 (suitability) from each rollout COG, take the mean, write 1-band COG.

    Band 1 in the state COG is ``density`` and band 2 is ``suitability`` per
    ``docs/abm-output-contract.md`` §1. The aggregate ignores NoData (-9999.0).
    """
    if not rollout_paths:
        raise ValueError("no rollout paths to aggregate")

    stack: list[np.ndarray] = []
    with rasterio.open(rollout_paths[0]) as src0:
        template = src0.profile
        crs = src0.crs
        transform = src0.transform

    for p in rollout_paths:
        with rasterio.open(p) as src:
            arr = src.read(2).astype(np.float32)  # band 2 = suitability
            nodata = src.nodata
        if nodata is not None:
            arr = np.where(arr == nodata, np.nan, arr)
        stack.append(arr)

    arr3d = np.stack(stack, axis=0)
    with np.errstate(invalid="ignore"):
        mean = np.nanmean(arr3d, axis=0).astype(np.float32)
    mean = np.where(np.isfinite(mean), mean, -9999.0).astype(np.float32)

    h, w = mean.shape
    profile = {
        "driver": "GTiff",
        "dtype": "float32",
        "count": 1,
        "height": h,
        "width": w,
        "crs": crs,
        "transform": transform,
        "nodata": -9999.0,
        "tiled": True,
        "compress": "deflate",
        "blockxsize": 128,
        "blockysize": 128,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(output_path, "w", **profile) as dst:
        dst.write(mean, 1)
        dst.set_band_description(1, "suitability_mean")

    finite = mean[np.isfinite(mean) & (mean != -9999.0)]
    stats = {
        "min": float(np.min(finite)) if finite.size else float("nan"),
        "mean": float(np.mean(finite)) if finite.size else float("nan"),
        "max": float(np.max(finite)) if finite.size else float("nan"),
        "frac_gt_0_1": float(np.mean(finite > 0.1)) if finite.size else float("nan"),
        "frac_gt_0_5": float(np.mean(finite > 0.5)) if finite.size else float("nan"),
        "n_cells": int(finite.size),
    }
    return stats


def _sample_suitability(
    suit: np.ndarray,
    affine: Affine,
    lats: np.ndarray,
    lons: np.ndarray,
) -> np.ndarray:
    """Sample the suitability grid at (lat, lon) points, in EPSG:4326.

    Mirrors the casablanca ``_points_to_grid`` to stay consistent with
    ``auc_with_ci``'s grid math. Returns NaN for points outside the grid.
    """
    from pyproj import Transformer
    from rasterio.transform import rowcol
    crs = C.DST_CRS
    t = Transformer.from_crs("EPSG:4326", crs, always_xy=True)
    xs, ys = t.transform(lons, lats)
    rows, cols = rowcol(affine, xs, ys)
    H, W = suit.shape
    out = np.full(len(lats), np.nan, dtype=np.float32)
    for i, (r, c) in enumerate(zip(rows, cols)):
        if 0 <= r < H and 0 <= c < W:
            out[i] = float(suit[int(r), int(c)])
    return out


def _read_env_meta(env_path: pathlib.Path) -> dict:
    """Read the env COG attributes for the report."""
    with rasterio.open(env_path) as src:
        meta = {
            "path": str(env_path),
            "count": int(src.count),
            "dtype": src.dtypes[0],
            "crs": str(src.crs),
            "epsg": src.crs.to_epsg() if src.crs is not None else None,
            "shape": [int(src.height), int(src.width)],
            "band_descriptions": list(src.descriptions),
            "nodata": src.nodata,
            "transform": [float(x) for x in src.transform[:6]],
        }
    sidecar = _sidecar_path(env_path)
    if sidecar.exists():
        meta["sidecar"] = json.loads(sidecar.read_text())
    meta["sha256"] = hashlib.sha256(env_path.read_bytes()).hexdigest()
    return meta


def _validate_suitability(
    suit_path: pathlib.Path,
    occurrence_path: pathlib.Path,
    *,
    bootstrap: int,
    seed: int = 42,
    n_background: int = 10_000,
) -> dict:
    """Load the suitability mean + the dedup'd larval sites; compute AUC + bootstrap CI.

    Reuses the casablanca ``auc_with_ci`` for the AUC + CI computation (same
    function as ``02_suitability.py``). Also samples the suitability at each
    unique site so the per-site table in the report can be filled in.
    """
    with rasterio.open(suit_path) as src:
        suit = src.read(1).astype(np.float32)
        affine = Affine(*src.transform[:6])
        nodata = src.nodata
    if nodata is not None:
        suit_masked = np.where(suit == nodata, np.nan, suit)
    else:
        suit_masked = suit

    lats, lons = load_occurrences()
    in_aoi = (
        (lats >= -3.5) & (lats <= 11.5) &
        (lons >= -3.5) & (lons <= 1.5)
    )
    lats = lats[in_aoi]; lons = lons[in_aoi]
    # Dedup to unique (lat, lon) (mirrors casablanca).
    pts = np.unique(np.stack([lats, lons], axis=1), axis=0)
    site_lats, site_lons = pts[:, 0], pts[:, 1]

    res = auc_with_ci(
        suit_masked, affine, site_lats, site_lons,
        n_bg=n_background, n_boot=bootstrap, seed=seed,
    )

    # Sample suitability at each unique site for the per-site table.
    site_values = _sample_suitability(suit_masked, affine, site_lats, site_lons)

    # Sample suitability at the same background points used by auc_with_ci,
    # so the scatter plot is reproducible.
    H, W = suit_masked.shape
    rng = np.random.default_rng(seed)
    bg_rows = rng.integers(0, H, n_background)
    bg_cols = rng.integers(0, W, n_background)
    bg_values = np.array(
        [float(suit_masked[int(r), int(c)]) for r, c in zip(bg_rows, bg_cols)],
        dtype=np.float32,
    )

    res["suit_array"] = suit_masked
    res["affine"] = affine
    res["site_lats"] = site_lats
    res["site_lons"] = site_lons
    res["site_values"] = site_values
    res["bg_values"] = bg_values
    res["n_backgrounds"] = int(n_background)
    return res


def _make_scatter(
    site_values: np.ndarray,
    bg_values: np.ndarray,
    out_path: pathlib.Path,
) -> pathlib.Path:
    """Save a scatter (log-suitability at sites vs background) for the report."""
    fig, ax = plt.subplots(figsize=(7, 4))
    eps = 1e-3
    bg_plot = np.clip(bg_values, eps, 1.0)
    site_plot = np.clip(site_values, eps, 1.0)
    ax.scatter(
        bg_plot, np.random.default_rng(0).normal(0, 0.05, size=len(bg_plot)),
        s=6, c="steelblue", alpha=0.4, label=f"background (n={len(bg_plot)})",
    )
    ax.scatter(
        site_plot, np.random.default_rng(1).normal(1, 0.05, size=len(site_plot)),
        s=30, c="crimson", edgecolor="black", label=f"sites (n={len(site_plot)})",
    )
    med_bg = float(np.median(bg_plot))
    ax.axvline(med_bg, color="grey", linestyle="--", linewidth=1, label=f"bg median={med_bg:.3f}")
    ax.set_xscale("log")
    ax.set_xlabel("suitability (log scale)")
    ax.set_yticks([0, 1])
    ax.set_yticklabels(["background", "site"])
    ax.set_xlim(eps, 1.0)
    ax.set_title("M2 validation: site vs background suitability")
    ax.legend(loc="best", fontsize=8)
    fig.tight_layout()
    fig.savefig(out_path, dpi=130)
    plt.close(fig)
    return out_path


def _load_localities(occurrence_path: pathlib.Path) -> dict[tuple[float, float], str]:
    """Build a (lat, lon) -> locality map from the DwC occurrence file."""
    import csv
    out: dict[tuple[float, float], str] = {}
    if not occurrence_path.exists():
        return out
    with open(occurrence_path, encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            try:
                la = float(row["decimalLatitude"]); lo = float(row["decimalLongitude"])
            except (KeyError, ValueError, TypeError):
                continue
            loc = (row.get("locality") or "").strip()
            out[(la, lo)] = loc
    return out


def _write_report(
    report_path: pathlib.Path,
    *,
    res: Mapping[str, Any],
    env_meta: Mapping[str, Any],
    suit_stats: Mapping[str, float],
    n_rollouts: int,
    wall_seconds: float,
    command: str,
    seed_range: tuple[int, int],
    scatter_path: pathlib.Path,
    localities: Mapping[tuple[float, float], str],
) -> None:
    """Write M2_REPORT.md with the AUC, CI, pass/fail, plot, table."""
    auc = res["auc"]; lo = res["ci_low"]; hi = res["ci_high"]
    n_sites = res["n_sites"]; n_bg = res["n_backgrounds"]
    verdict = "PASS" if lo > _AUC_CI_TARGET else "FAIL"
    verdict_why = (
        f"lower-95 ({lo:.3f}) > {_AUC_CI_TARGET} (design doc threshold)"
        if verdict == "PASS"
        else f"lower-95 ({lo:.3f}) <= {_AUC_CI_TARGET} (design doc threshold)"
    )

    site_lats = res["site_lats"]; site_lons = res["site_lons"]
    site_vals = res["site_values"]
    # Build the per-site table rows.
    table_rows: list[str] = []
    table_rows.append("| # | locality | lat | lon | suitability |")
    table_rows.append("|---:|---|---:|---:|---:|")
    for i, (la, lo_, sv) in enumerate(zip(site_lats, site_lons, site_vals), start=1):
        loc = localities.get((float(la), float(lo_)), "") or "—"
        sv_str = f"{sv:.4f}" if np.isfinite(sv) else "n/a"
        loc_esc = loc.replace("|", "\\|")
        table_rows.append(f"| {i} | {loc_esc} | {la:.5f} | {lo_:.5f} | {sv_str} |")

    env_band_str = ", ".join(f"`{n}`" for n in env_meta.get("band_descriptions", []))
    sidecar_block = ""
    if "sidecar" in env_meta:
        sc = env_meta["sidecar"]
        sidecar_block = (
            f"- `contract_version`: `{sc.get('contract_version')}`\n"
            f"- `generator_version`: `{sc.get('generator_version')}`\n"
            f"- `aoi_slug` / `scale`: `{sc.get('aoi_slug')}` / `{sc.get('scale')}`\n"
        )

    report = f"""# M2 validation report

_Generated {datetime.now(timezone.utc).isoformat(timespec='seconds')}_

## Run metadata

| Field | Value |
|---|---|
| AOI | `{env_meta.get('sidecar', {}).get('aoi_slug', '?')}` |
| Year / Month | `{env_meta.get('sidecar', {}).get('year', '?')}` / `{int(env_meta.get('sidecar', {}).get('month', 0)):02d}` |
| Scale | `{env_meta.get('sidecar', {}).get('scale', '?')}` |
| N rollouts | {n_rollouts} |
| Seed range | {seed_range[0]}..{seed_range[1]} |
| N larval sites (dedup) | {n_sites} |
| N background points | {n_bg} |
| Wall-clock (s) | {wall_seconds:.1f} |

Command:

```
{command}
```

## Validation result

**AUC = {auc:.3f}  95% CI = [{lo:.3f}, {hi:.3f}]  n_sites = {n_sites}**

**Verdict: `{verdict}`** — {verdict_why}.

Design criterion: `lower_95 > {_AUC_CI_TARGET}` (casablanca `AUC_CI_TARGET`).

## Env COG attributes

- Path: `{env_meta['path']}`
- Bands: {env_meta['count']} × `{env_meta['dtype']}`
- CRS: `{env_meta['crs']}` (EPSG:{env_meta.get('epsg')})
- Shape: {env_meta['shape'][0]} × {env_meta['shape'][1]} (H × W)
- Band descriptions: {env_band_str or "—"}
- NoData: `{env_meta.get('nodata')}`
- SHA-256: `{env_meta.get('sha256', '?')[:16]}…`
{sidecar_block}

## Suitability aggregate stats

| Stat | Value |
|---|---:|
| min | {suit_stats.get('min', float('nan')):.4f} |
| mean | {suit_stats.get('mean', float('nan')):.4f} |
| max | {suit_stats.get('max', float('nan')):.4f} |
| frac cells > 0.1 | {suit_stats.get('frac_gt_0_1', float('nan')):.4f} |
| frac cells > 0.5 | {suit_stats.get('frac_gt_0_5', float('nan')):.4f} |
| n cells (finite) | {int(suit_stats.get('n_cells', 0))} |

## Suitability: sites vs background

![scatter]({scatter_path.name})

The scatter shows suitability at the {n_sites} unique larval sites (red) and
at {n_bg} random background cells (blue), on a log x-axis. Sites that
cluster to the right of the background median indicate the ABM-rollout-mean
suitability field is informative for the observed presence locations.

## Per-site table

{chr(10).join(table_rows)}

## Reproducibility

- Env COG: `{env_meta['path']}` (sha256 `{env_meta.get('sha256', '?')[:16]}…`)
- Sidecar: `{_sidecar_path(pathlib.Path(env_meta['path']))}`
- Suitability mean: `{report_path.parent / f'suitability_mean_{env_meta.get("sidecar", {}).get("year", 0)}_{int(env_meta.get("sidecar", {}).get("month", 0)):02d}.tif'}`
- Rollouts dir: `{report_path.parent / 'rollouts'}`
- ABM seed range: `{seed_range[0]}`..`{seed_range[1]}` (inclusive)
- Determinism: ABM seed is the only stochastic input; build_env and the
  aggregator are deterministic given identical upstream data.
"""
    report_path.write_text(report)


# -- CLI --------------------------------------------------------------------


@app.command()
def main(
    aoi: str = typer.Option("ghana", "--aoi", help="AOI slug (must be in the in-repo registry)."),
    year: int = typer.Option(2024, "--year", help="Year (e.g. 2024)."),
    month: int = typer.Option(6, "--month", min=1, max=12, help="Month (1-12)."),
    output_dir: pathlib.Path = typer.Option(..., "--output-dir", help="Directory for env COG, rollouts, suit mean, and report."),
    n_rollouts: int = typer.Option(100, "--n-rollouts", min=1, help="Number of ABM rollouts (seeds 1..N)."),
    bootstrap: int = typer.Option(1000, "--bootstrap", min=1, help="Bootstrap iterations for the 95% CI."),
    days: int = typer.Option(30, "--days", min=1, max=366, help="Days per ABM rollout (passed to abm_run)."),
    seed: int = typer.Option(42, "--seed", help="Seed for the bootstrap background sampling."),
    scale: Scale = typer.Option(Scale.REGIONAL, "--scale", help="Multi-scale level (mirrors build_env / abm_run)."),
    skip_era5: bool = typer.Option(False, "--skip-era5", help="Skip the ERA5 download (channel becomes NoData)."),
    skip_modis: bool = typer.Option(False, "--skip-modis", help="Skip the MODIS download (channel becomes NoData)."),
    skip_worldcover: bool = typer.Option(False, "--skip-worldcover", help="Skip the WorldCover download (water_frac channel becomes NoData)."),
    strict: bool = typer.Option(
        False, "--strict",
        help="Exit with code 1 if the lower 95% CI is below 0.65 (default: 0, the verdict is in the report).",
    ),
) -> None:
    """Run the M2 validation pipeline."""
    t0 = time.time()
    aoi_obj = _resolve_aoi_obj(aoi)
    output_dir.mkdir(parents=True, exist_ok=True)
    env_path = _env_path(output_dir, aoi_obj, year, month)
    habitat_path = _habitat_path(output_dir, aoi_obj, year, month)
    rollouts_dir = output_dir / "rollouts"
    suit_path = output_dir / f"suitability_mean_{year:04d}_{month:02d}.tif"
    report_path = output_dir / "M2_REPORT.md"
    scatter_path = output_dir / "m2_validation_scatter.png"

    # 1. build_env
    typer.echo(f"[1/4] build_env -> {env_path}")
    _run_build_env(
        aoi, year, month, output_dir,
        scale=scale, skip_era5=skip_era5, skip_modis=skip_modis,
        skip_worldcover=skip_worldcover,
    )

    # 2. N rollouts
    typer.echo(f"[2/4] {n_rollouts} abm_run rollouts (seeds 1..{n_rollouts})")
    rollouts_dir.mkdir(parents=True, exist_ok=True)
    for seed_i in range(1, n_rollouts + 1):
        rp = rollouts_dir / (
            f"{aoi_obj.slug}_{aoi_obj.scale.value}_{year:04d}_{month:02d}"
            f"_seed{seed_i:04d}.tif"
        )
        _run_abm_rollout(
            seed_i, year, month, env_path, habitat_path, rp,
            aoi=aoi, scale=scale, days=days,
        )
    rollout_paths = sorted(rollouts_dir.glob(f"{aoi_obj.slug}_*_seed*.tif"))
    if len(rollout_paths) != n_rollouts:
        typer.echo(
            f"WARNING: expected {n_rollouts} rollout COGs, found {len(rollout_paths)}.",
            err=True,
        )

    # 3. aggregate
    typer.echo(f"[3/4] aggregate suitability -> {suit_path}")
    suit_stats = _aggregate_suitability(rollout_paths, suit_path)

    # 4. validate + report
    typer.echo(f"[4/4] validate (AUC + bootstrap CI) + report -> {report_path}")
    res = _validate_suitability(
        suit_path, _OCCURRENCE_PATH,
        bootstrap=bootstrap, seed=seed,
    )
    env_meta = _read_env_meta(env_path)
    _make_scatter(
        res["site_values"], res["bg_values"], scatter_path,
    )
    localities = _load_localities(_OCCURRENCE_PATH)
    wall = time.time() - t0
    _write_report(
        report_path,
        res=res, env_meta=env_meta, suit_stats=suit_stats,
        n_rollouts=n_rollouts, wall_seconds=wall,
        command=" ".join(sys.argv),
        seed_range=(1, n_rollouts),
        scatter_path=scatter_path,
        localities=localities,
    )

    typer.echo(
        f"M2 done. AUC={res['auc']:.3f} 95% CI=[{res['ci_low']:.3f}, {res['ci_high']:.3f}] "
        f"(n_sites={res['n_sites']}). Report: {report_path}"
    )
    if strict and res["ci_low"] < _AUC_CI_TARGET:
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
