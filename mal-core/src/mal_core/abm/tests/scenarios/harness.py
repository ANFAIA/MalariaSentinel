"""Scenario harness (plan 13.3.1): runs one scenario through the manifest route.

Route (identical to production): ``validate_completeness`` -> ``resolve`` ->
binary, via ``run_abm_from_manifest(..., scenario=<id>)``.

Step 0/1 scope: load and expand a scenario, run it, collect the observables
the current chain exposes (daily cohort log, adult-cell COG bands, transmission
debug JSONL) and write

* ``runs/_check_current/<id>.baseline.json`` - what today's chain does (Paso 1;
  a regression reference, NOT an expectation);
* ``runs/_check_current/<id>.observed.json`` - observed vs. expected (empty
  expectations until the step that implements the behaviour writes them).

``mode == "gate"`` fails (non-zero) only when an expectation is violated; with
no expectations a gate cannot fail, which is the Paso 0/1 state.
"""

from __future__ import annotations

import copy
import hashlib
import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[6]
SCENARIOS_DIR = Path(__file__).resolve().parent
AOI_SLUG = "accra-synth-10x10"
AOI_BBOX = "-0.2,5.7,-0.10971147034573944,5.789842104336081"
DATA_ROOT = REPO_ROOT / "runs" / "synthetic"
CHECK_DIR = REPO_ROOT / "runs" / "_check_current"
ALL_IDS = [f"E{i:02d}" for i in range(20)]

# Non-spec keys the harness itself reads from a variant element.
_VARIANT_ONLY = {"label"}


@dataclass
class ScenarioRun:
    scenario_id: str
    variant: str | None
    out_dir: Path
    spec: dict[str, Any]
    observed: dict[str, Any] = field(default_factory=dict)


def load_spec(scenario_id: str, scenarios_dir: Path = SCENARIOS_DIR) -> dict[str, Any]:
    spec = json.loads((scenarios_dir / f"{scenario_id}.json").read_text())
    if spec.get("id") != scenario_id:
        raise ValueError(f"{scenario_id}.json declares id {spec.get('id')!r}")
    return spec


def expand_variants(spec: dict[str, Any]) -> list[tuple[str | None, dict[str, Any]]]:
    """One (label, engine-ready spec) per variant; ``[(None, spec)]`` if none.

    The engine parser rejects non-empty ``variants`` (seeding.cpp), so the
    harness writes one expanded JSON per variant, with the same seed.
    """
    variants = spec.get("variants") or []
    if not variants:
        return [(None, spec)]
    out = []
    for i, v in enumerate(variants):
        merged = copy.deepcopy(spec)
        merged["variants"] = []
        for k, val in v.items():
            if k in _VARIANT_ONLY:
                continue
            merged[k] = val
        merged["id"] = spec["id"]
        out.append((v.get("label", f"v{i}"), merged))
    return out


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _collect(out_dir: Path, seed: int) -> dict[str, Any]:
    stem = f"{AOI_SLUG}_abm_seed{seed:04d}"
    cohort = json.loads((out_dir / f"{stem}_cohort.json").read_text())
    daily = cohort["daily"]
    obs: dict[str, Any] = {
        "adults_by_day": [d["n_adults"] for d in daily],
        "alive_by_day": [d["n_alive"] for d in daily],
        "births_by_day": [d["n_births"] for d in daily],
        "deaths_by_day": [d["n_deaths"] for d in daily],
    }
    dbg = out_dir / f"{stem}_transmission_debug.jsonl"
    if dbg.exists():
        bites = []
        for line in dbg.read_text().splitlines():
            rec = json.loads(line)
            if rec.get("record_type") == "daily":
                h = rec["bites"]["human"]
                bites.append({
                    "day": rec["day"],
                    "human_attempts": h["attempts"],
                    "human_successful": h["successful"],
                    "human_infectious": h["infectious"],
                    "events_by_cell": rec["bites"]["events_by_cell"],
                })
        obs["bites_by_day"] = bites
        obs["human_bites_total"] = sum(b["human_successful"] for b in bites)
    # adult cell counts per day from the COG snapshots (band 2 = cell count)
    try:
        import rasterio  # noqa: PLC0415

        cells = []
        for tif in sorted(out_dir.glob(f"{stem}_day*.tif")):
            with rasterio.open(tif) as ds:
                a = ds.read(2)
            nz = [[int(r), int(c), float(a[r, c])] for r, c in zip(*a.nonzero())]
            cells.append({"snapshot": tif.stem[-6:], "occupied_cells": nz})
        obs["adult_cells_by_snapshot"] = cells
    except ImportError:  # pragma: no cover
        pass
    return obs


def run_scenario(
    scenario_id: str,
    out_root: Path = CHECK_DIR,
    data_root: Path = DATA_ROOT,
    enable_transmission: bool = True,
    month: int = 6,
    seed_override: int | None = None,
    debug: bool = False,
) -> list[ScenarioRun]:
    """Run every variant of ``scenario_id`` through the manifest route."""
    from mal_core.abm.wrapper import run_abm_from_manifest

    spec = load_spec(scenario_id)
    runs: list[ScenarioRun] = []
    for label, eng_spec in expand_variants(spec):
        if seed_override is not None:
            eng_spec = {**eng_spec, "seed": seed_override}
        sub = scenario_id if label is None else f"{scenario_id}_{label}"
        out_dir = out_root / sub
        if out_dir.exists():
            shutil.rmtree(out_dir)
        out_dir.mkdir(parents=True)
        # Regenerate the AOI scenario copy with the (possibly expanded) spec.
        aoi_dir = data_root / AOI_SLUG
        run_spec = dict(eng_spec)
        target = aoi_dir / "scenarios" / f"{scenario_id}.json"
        original = target.read_text() if target.exists() else None
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(run_spec, indent=2))
        _declare(aoi_dir, scenario_id, data_root)
        try:
            result = run_abm_from_manifest(
                aoi=AOI_SLUG,
                data_root=data_root,
                scenario=scenario_id,
                bbox=AOI_BBOX,
                year=2024,
                month=month,
                days=int(eng_spec["days"]),
                seed=int(eng_spec["seed"]),
                output_dir=out_dir,
                enable_transmission=enable_transmission,
                debug=debug,
            )
        finally:
            if original is not None:
                target.write_text(original)
        if result.get("returncode", 0) != 0:
            raise RuntimeError(
                f"{scenario_id}{'/' + label if label else ''}: binary exited "
                f"{result['returncode']}: {result.get('stderr', '')[-800:]}")
        run = ScenarioRun(scenario_id, label, out_dir, eng_spec)
        run.observed = _collect(out_dir, int(eng_spec["seed"]))
        runs.append(run)
    return runs


WIND_SCENARIOS = ("E18", "E19")
WEAK_WIND_MAX_MS = 0.2   # below wind_block_threshold_ms (= flight_speed_ms, 0.3375)


def _weak_wind_file(aoi_dir: Path, strong_name: str) -> Path:
    """A copy of the synthetic wind field scaled so its speed never exceeds
    WEAK_WIND_MAX_MS: a breeze, below the blocking threshold of the cascade."""
    import numpy as np
    import xarray as xr

    out = aoi_dir / strong_name.replace(".nc", "_weak.nc")
    if out.exists():
        return out
    with xr.open_dataset(aoi_dir / strong_name) as ds:
        ds = ds.load()
    speed = np.hypot(ds["u100"], ds["v100"])
    scale = WEAK_WIND_MAX_MS / float(speed.max())
    ds["u100"] = ds["u100"] * scale
    ds["v100"] = ds["v100"] * scale
    ds.attrs["title"] = str(ds.attrs.get("title", "")) + f" (scaled x{scale:.4f}: weak wind for E19)"
    ds.to_netcdf(out)
    return out


def _declare(aoi_dir: Path, scenario_id: str, data_root: Path) -> None:
    """Declare exactly one scenario key in the manifest (plan 13.5)."""
    from mal_core.download.manifest import read_manifest, update_dataset

    manifest = read_manifest(AOI_SLUG, data_root=data_root)
    for key in [k for k in manifest["datasets"] if k.startswith("scenario:")]:
        if key != f"scenario:{scenario_id}":
            manifest["datasets"].pop(key)
    # The wind field is loaded ONLY by the wind scenarios (plan 13.1/13.6): with
    # it declared, every scenario would fly under a 2-5 m/s wind that blocks
    # the advance of the cascade (headwind >= flight speed). Stash the entry the
    # AOI builder wrote and put it back for them: E18 uses the field as built
    # (strong: it blocks), E19 a weak copy (below the blocking threshold).
    stash = aoi_dir / "wind_entry.json"
    current = manifest["datasets"].get("wind")
    if current is not None and "_weak" not in current["files"]["wind"]:
        stash.write_text(json.dumps(current))      # always the STRONG entry
    if scenario_id in WIND_SCENARIOS:
        if stash.exists():
            entry = json.loads(stash.read_text())
            if scenario_id == "E19":
                entry = dict(entry)
                entry["files"] = {"wind": _weak_wind_file(aoi_dir, entry["files"]["wind"]).name}
            manifest["datasets"]["wind"] = entry
    else:
        manifest["datasets"].pop("wind", None)
    path = aoi_dir / "manifest.json"
    path.write_text(json.dumps(manifest, indent=2))
    update_dataset(
        AOI_SLUG, f"scenario:{scenario_id}", scenario_id,
        f"scenarios/{scenario_id}.json", type="static", data_root=data_root,
    )


def evaluate(spec: dict[str, Any], observed: dict[str, Any]) -> dict[str, Any]:
    """Compare observed vs. expectations. No expectations -> nothing to fail."""
    results = []
    for exp in spec.get("expectations", []):
        results.append({"expectation": exp, "status": "pending"})
    failed = [r for r in results if r["status"] == "fail"]
    return {
        "id": spec["id"],
        "mode": spec["mode"],
        "expectations": results,
        "passed": not failed,
        "observed": observed,
    }


def write_reports(runs: list[ScenarioRun], out_root: Path = CHECK_DIR) -> dict[str, Any]:
    scenario_id = runs[0].scenario_id
    baseline = {
        "id": scenario_id,
        "note": "Paso 1 baseline: what the current chain does. Regression "
                "reference, not an expectation.",
        "variants": {(r.variant or "base"): r.observed for r in runs},
    }
    (out_root / f"{scenario_id}.baseline.json").write_text(
        json.dumps(baseline, indent=2, sort_keys=True))
    report = {
        (r.variant or "base"): evaluate(r.spec, r.observed) for r in runs
    }
    (out_root / f"{scenario_id}.observed.json").write_text(
        json.dumps(report, indent=2, sort_keys=True))
    return report


def exit_code(report: dict[str, Any]) -> int:
    """gate -> non-zero when an expectation fails; report -> always 0."""
    for ev in report.values():
        if ev["mode"] == "gate" and not ev["passed"]:
            return 1
    return 0


def artifact_digests(out_dir: Path) -> dict[str, str]:
    """Byte-level digests of the deterministic artifacts (plan Nivel 5).

    GeoPackages are excluded (gpkg stamps last_change).
    """
    keep = (".tif", ".json", ".jsonl", ".parquet")
    return {
        p.name: _sha256(p)
        for p in sorted(out_dir.iterdir())
        if p.suffix in keep
    }


if __name__ == "__main__":  # pragma: no cover
    import sys

    ids = sys.argv[1:] or ["E00", "E01", "E02"]
    rc = 0
    for sid in ids:
        rep = write_reports(run_scenario(sid))
        rc = max(rc, exit_code(rep))
        print(sid, "ok" if exit_code(rep) == 0 else "FAIL")
    sys.exit(rc)
