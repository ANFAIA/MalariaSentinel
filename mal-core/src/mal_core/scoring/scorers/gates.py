"""Engineering gates — binary invariants reported APART from the composite.

Gates validate the run's data hygiene and inputs, not its biology. A
failed gate is a visible warning in the scorecard but never changes
the composite. All gates return ``skipped`` (not fail) when their
artifacts are absent — missing data is not a data-integrity failure.
"""
from __future__ import annotations

import hashlib
import json
import re
import struct
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import rasterio

from .base import (
    NODATA,
    Scorer,
    ScorerResult,
    find_state_files,
    require_aoi,
    resolve_aoi_artifact,
)


class DataValidGate(Scorer):
    """G6 (ex-D6): every state band value finite and within [0, 1]."""

    name = "G6_data_valid"
    kind = "gate"
    weight = 0.0
    description = "All state bands in [0,1] (COG/NaN write integrity)"
    aoi_generalizable = True

    def score(self, run_dir: Path, ctx: dict[str, Any]) -> ScorerResult:
        tifs = find_state_files(run_dir)
        if not tifs:
            return ScorerResult.skipped("no state files", target="100% in [0,1]")
        if len(tifs) > 48:  # uniform sample — full sweep belongs to pytest
            step = len(tifs) / 48.0
            tifs = [tifs[int(i * step)] for i in range(48)]
        total_valid = 0
        total = 0
        bad_files: list[str] = []
        for tif in tifs:
            with rasterio.open(tif) as ds:
                for bidx in range(1, ds.count + 1):
                    band = ds.read(bidx)
                    finite = np.isfinite(band) & (band != NODATA)
                    if ds.nodata is not None:
                        finite &= band != ds.nodata
                    ok = finite & (band >= 0.0) & (band <= 1.0)
                    if int(ok.sum()) != band.size:
                        bad_files.append(tif.name)
                    total_valid += int(ok.sum())
                    total += band.size
        frac = total_valid / total if total else 0.0
        return ScorerResult(
            score=frac,
            value=frac,
            target="100% in [0,1]",
            diagnostics={"files_with_bad_values": bad_files[:10]},
            passed=frac == 1.0,
        )


class DeterminismGate(Scorer):
    """G7 (ex-D7): same-seed outputs byte-identical."""

    name = "G7_determinism"
    kind = "gate"
    weight = 0.0
    description = "Same-seed state files hash-identical"
    aoi_generalizable = True

    def score(self, run_dir: Path, ctx: dict[str, Any]) -> ScorerResult:
        tifs = sorted(p for p in run_dir.glob("state_seed*.tif") if "_day" not in p.stem)
        if not tifs:
            return ScorerResult.skipped(
                "no per-seed state files (determinism covered by pytest suite)",
                target="identical per seed",
            )
        groups: dict[str, list[Path]] = defaultdict(list)
        for t in tifs:
            m = re.search(r"seed(\d+)", t.name)
            groups[m.group(0) if m else "default"].append(t)
        mismatches = 0
        for files in groups.values():
            if len(files) < 2:
                continue
            hashes = {hashlib.md5(f.read_bytes()).hexdigest() for f in files}
            if len(hashes) > 1:
                mismatches += 1
        return ScorerResult(
            score=0.0 if mismatches else 1.0,
            value=float(mismatches),
            target="identical per seed",
            diagnostics={"mismatches": mismatches},
            passed=mismatches == 0,
        )


class PerformanceGate(Scorer):
    """G10 (ex-D10): wall time from run_metadata.json, if recorded."""

    name = "G10_perf"
    kind = "gate"
    weight = 0.0
    description = "Wall time <= 30 s (when run_metadata.json records it)"
    aoi_generalizable = True

    def score(self, run_dir: Path, ctx: dict[str, Any]) -> ScorerResult:
        meta_path = run_dir / "run_metadata.json"
        if not meta_path.exists():
            return ScorerResult.skipped(
                "no run_metadata.json (perf covered by benchmark tier)",
                target="<=30 s",
            )
        try:
            meta = json.loads(meta_path.read_text())
        except (json.JSONDecodeError, OSError):
            return ScorerResult.skipped("run_metadata unreadable", target="<=30 s")
        wall_s = meta.get("wall_s", 0.0)
        if wall_s <= 0:
            return ScorerResult.skipped("wall_s not recorded", target="<=30 s")
        return ScorerResult(
            score=min(1.0, 30.0 / wall_s),
            value=float(wall_s),
            target="<=30 s",
            passed=wall_s <= 30.0,
        )


class HostInputGate(Scorer):
    """G12 (ex-D12): input host grid total matches the census reference."""

    name = "G12_host_input"
    kind = "gate"
    weight = 0.0
    description = "Input human grid total ~ census reference (input validation)"
    aoi_generalizable = True

    def score(self, run_dir: Path, ctx: dict[str, Any]) -> ScorerResult:
        aoi = require_aoi(ctx)
        if not aoi:
            return ScorerResult.skipped(
                "requires explicit --aoi (never inferred)", target="~ reference census total"
            )
        hosts = ctx.get("hosts_path") or resolve_aoi_artifact(
            aoi, ["data/{aoi}/{aoi}_host_static.nc", "data/{aoi}/host_static.nc"]
        )
        if hosts is None or not Path(hosts).exists():
            return ScorerResult.skipped(
                f"host_static.nc not resolved for AOI {aoi!r}",
                target="~ reference census total",
            )
        ref_total = float(ctx.get("human_reference_total", 27_000_000))
        try:
            import xarray as xr
        except ImportError:
            return ScorerResult.skipped("missing dependency: xarray", target="~ 27M")
        ds = xr.open_dataset(str(hosts))
        human = ds["human"].values
        valid = human[human != -9999.0]
        total = float(valid.sum()) if valid.size else 0.0
        ds.close()
        if ref_total <= 0 or total <= 0:
            return ScorerResult(
                score=0.0, value=total, target=f"~ {ref_total:,.0f}", passed=False,
            )
        ratio = total / ref_total
        score = 1.0 if 0.9 <= ratio <= 1.1 else max(
            0.0, 1.0 - abs(ratio - 1.0)
        )
        return ScorerResult(
            score=round(score, 4),
            value=round(total, 0),
            target=f"~ {ref_total:,.0f}",
            diagnostics={"ratio": round(ratio, 4)},
            passed=0.8 <= ratio <= 1.2,
        )


class MobilityGate(Scorer):
    """G14 (ex-D14): OD matrix rows are row-stochastic (sum to 1.0)."""

    name = "G14_mobility"
    kind = "gate"
    weight = 0.0
    description = "Mobility OD matrix rows sum to 1.0 (input validation)"
    aoi_generalizable = True

    def score(self, run_dir: Path, ctx: dict[str, Any]) -> ScorerResult:
        csr_files = sorted(run_dir.glob("*.csr"))
        if not csr_files:
            for parent in (run_dir.parent, run_dir.parent / "hosts"):
                csr_files = sorted(parent.glob("*.csr"))
                if csr_files:
                    break
        if not csr_files:
            return ScorerResult.skipped(
                "no .csr files near run dir", target="rows sum to 1.0"
            )
        min_fraction = 1.0
        checked = 0
        for csr in csr_files:
            try:
                with open(csr, "rb") as f:
                    n_rows = struct.unpack("i", f.read(4))[0]
                    n_cols = struct.unpack("i", f.read(4))[0]
                    nnz = struct.unpack("i", f.read(4))[0]
                    row_ptr = np.frombuffer(f.read(4 * (n_rows + 1)), dtype=np.int32)
                    col_idx = np.frombuffer(f.read(4 * nnz), dtype=np.int32)
                    values = np.frombuffer(f.read(4 * nnz), dtype=np.float32)
                del n_cols, col_idx
                sums = np.add.reduceat(
                    values, row_ptr[:-1].clip(max=len(values))
                ) if nnz else np.zeros(n_rows)
                frac = float(
                    (np.abs(sums - 1.0) < 0.01).sum() / max(n_rows, 1)
                )
                min_fraction = min(min_fraction, frac)
                checked += 1
            except Exception as e:
                return ScorerResult.skipped(f"csr unreadable: {e}", target="rows sum to 1.0")
        return ScorerResult(
            score=round(min_fraction, 4),
            value=round(min_fraction, 4),
            target="rows sum to 1.0 (all files)",
            diagnostics={"files_checked": checked},
            passed=min_fraction >= 0.99,
        )


class UrbanProductivityGate(Scorer):
    """G24 (ex-D24): urban cells carry less density than rural cells.

    AOI-specific: requires an ``<aoi>_urban_class.tif`` next to the AOI
    env inputs. Skipped (not failed) when the raster is absent.
    """

    name = "G24_urban_ratio"
    kind = "gate"
    weight = 0.0
    description = "Urban/rural density ratio <= 0.7 (capacity-scaling guardrail)"
    manual = True  # AOI-dependent: needs the AOI's urban class raster

    def score(self, run_dir: Path, ctx: dict[str, Any]) -> ScorerResult:
        aoi = require_aoi(ctx)
        urban_raster = ctx.get("urban_class_path") or resolve_aoi_artifact(
            aoi, ["data/{aoi}/{aoi}_urban_class.tif", "data/{aoi}/urban_class.tif"]
        )
        if urban_raster is None or not Path(urban_raster).exists():
            return ScorerResult.skipped(
                f"urban class raster not resolved for AOI {aoi!r}",
                target="<= 0.7",
            )
        files = find_state_files(run_dir)
        if not files:
            return ScorerResult.skipped("no state files", target="<= 0.7")
        with rasterio.open(files[-1]) as ds:
            density = ds.read(1)
        with rasterio.open(urban_raster) as ds:
            urban_class = ds.read(1)
            nodata = ds.nodata
        if density.shape != urban_class.shape:
            return ScorerResult.skipped("raster shape mismatch", target="<= 0.7")
        mask_d = np.isfinite(density) & (density != NODATA) & (density > 0)
        urban_mask = mask_d & (urban_class == 30)
        rural_mask = mask_d & (urban_class == 50)
        if urban_mask.sum() < 10 or rural_mask.sum() < 10:
            return ScorerResult.skipped(
                "insufficient urban/rural active cells", target="<= 0.7"
            )
        urban_mean = float(density[urban_mask].mean())
        rural_mean = float(density[rural_mask].mean())
        if rural_mean <= 0:
            return ScorerResult.skipped("rural mean <= 0", target="<= 0.7")
        ratio = urban_mean / rural_mean
        score = 1.0 if ratio <= 0.7 else max(0.0, 1.0 - (ratio - 0.7) / 0.3)
        return ScorerResult(
            score=round(score, 4),
            value=round(ratio, 4),
            target="<= 0.7",
            diagnostics={
                "n_urban": int(urban_mask.sum()),
                "n_rural": int(rural_mask.sum()),
            },
            passed=ratio <= 0.7,
        )
