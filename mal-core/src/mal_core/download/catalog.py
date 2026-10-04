"""Dataset catalog — the single place where dataset identity lives.

Identity of a dataset is its **manifest key**. There are exactly two kinds:

* **Downloaded datasets** declare their keys in each loader's
  ``DOWNLOADER.manifest_keys`` (mal-commonlib, discovered via the
  registry). This module adds NO new tables for them — it derives the
  list from the registry itself.
* **Derived ingest artifacts** (env NC, host grid, mobility CSRs...) declare
  theirs in ``INGEST_ARTIFACTS`` below — the only new table, replacing the
  key strings that used to be hardcoded at each registration site.

Consumers (ingest builders, the ABM wrapper, CLI, viz scripts) declare
dependencies as :class:`Slot` specs and resolve paths through
:func:`resolve_inputs`. ``manifest.json`` is the single source of truth
for what exists and in which file (docs/specs/data/spec.md §5.2).

Resolution semantics (agreed 2026-10-04):

* Manifest entry present → the declared file MUST exist on disk
  (stale manifest = error, never a silent fallback).
* Per-year entry lacking the requested year → error.
* No entry at all → ``FileNotFoundError`` for required inputs (with the
  download hint); ``None`` for optional inputs.

There is NO conventional-name fallback inside consumers. Legacy data dirs
that predate manifests are migrated once with :func:`register_existing`,
which derives conventional names from the loaders' own ``formats`` and the
runner's naming helpers — the naming knowledge lives only there.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .manifest import read_manifest, resolve_dataset_file, update_dataset
from .registry import discover_downloaders


# --- derived ingest artifacts -------------------------------------------------

@dataclass(frozen=True)
class IngestArtifact:
    """A derived artifact an ingest stage builds and registers."""

    key: str  # manifest dataset key
    producer: str  # dotted path of the function that builds + registers it
    description: str = ""
    required_for_abm: bool = False


INGEST_ARTIFACTS: dict[str, IngestArtifact] = {
    "env": IngestArtifact(
        "env", "mal_core.ingest.env.build_env_tensor",
        "Daily env NetCDF (time,y,x) — the C++ ABM climate/habitat input",
        required_for_abm=True,
    ),
    "habitat": IngestArtifact(
        "habitat", "mal_core.ingest.env.build_env_tensor",
        "Habitat patches GeoPackage", required_for_abm=True,
    ),
    "host_static": IngestArtifact(
        "host_static", "mal_core.ingest.hosts.build_host_dataset",
        "Static host grid NC (humans, livestock, urban, buildings)",
        required_for_abm=True,
    ),
    "host_manifest": IngestArtifact(
        "host_manifest", "mal_core.ingest.hosts.build_host_dataset",
        "Per-variable host stats JSON",
    ),
    "mobility_day": IngestArtifact(
        "mobility_day", "mal_core.ingest.mobility.build_mobility_dataset",
        "Human daytime mobility CSR", required_for_abm=True,
    ),
    "mobility_night": IngestArtifact(
        "mobility_night", "mal_core.ingest.mobility.build_mobility_dataset",
        "Human nighttime mobility CSR", required_for_abm=True,
    ),
    "livestock_mobility": IngestArtifact(
        "livestock_mobility",
        "mal_core.ingest.mobility.build_mobility_dataset",
        "Livestock mobility CSR", required_for_abm=True,
    ),
    "mobility_manifest": IngestArtifact(
        "mobility_manifest",
        "mal_core.ingest.mobility.build_mobility_dataset",
        "Mobility betas/params JSON",
    ),
}


# --- consumer dependency declaration ------------------------------------------

@dataclass(frozen=True)
class Slot:
    """One consumer input dependency, identified by its manifest key.

    ``required`` → resolution error when absent from the manifest.
    ``per_year`` → the manifest entry is (or may be) keyed by year; the
    resolved value is a ``dict[year, Path]``.
    """

    key: str
    required: bool = True
    per_year: bool = False


def _artifacts_by_producer_suffix(suffix: str) -> tuple[str, ...]:
    """Ingest-artifact keys whose producer callable ends with ``suffix``."""
    return tuple(
        art.key for art in INGEST_ARTIFACTS.values()
        if art.producer.rsplit(".", 1)[-1] == suffix
    )


# --- manifest access -----------------------------------------------------------

def load_local_manifest(data_dir: Path | str) -> dict:
    """Datasets block of ``data_dir / manifest.json`` (empty if absent).

    Data-dir-local read (rather than ``read_manifest``) so tmp sandboxes
    resolve against the manifest they carry next to their files.
    """
    path = Path(data_dir) / "manifest.json"
    if not path.exists():
        return {}
    try:
        with open(path) as f:
            return json.load(f).get("datasets", {})
    except Exception as e:  # noqa: BLE001 — corrupt manifest must not brick builds
        print(f"warning: could not read {path}: {e}")
        return {}


def _datasets_for(
    aoi: str,
    data_dir: Path | None = None,
    data_root: Path | None = None,
    manifest: dict | None = None,
) -> tuple[Path, dict]:
    """Return (data_dir, datasets_block) honouring explicit overrides."""
    if data_dir is not None:
        datasets = (
            manifest.get("datasets", {}) if manifest is not None
            else load_local_manifest(data_dir)
        )
        return Path(data_dir), datasets
    m = manifest if manifest is not None else read_manifest(aoi, data_root)
    return (data_root or Path("data")) / aoi, m.get("datasets", {})


def resolve(
    aoi: str,
    key: str,
    *,
    year: int | str | None = None,
    data_dir: Path | None = None,
    data_root: Path | None = None,
    manifest: dict | None = None,
) -> Path | None:
    """Resolve one dataset's file path — manifest-first, strict.

    ``None`` when the manifest has no entry (the optional-input signal).
    Raises ``FileNotFoundError`` when the entry exists but its file is
    missing on disk, or when a per-year entry lacks the requested year.
    """
    dd, datasets = _datasets_for(aoi, data_dir, data_root, manifest)
    return resolve_dataset_file(
        aoi, key, year=year, data_dir=dd, manifest={"datasets": datasets}
    )


def resolve_inputs(
    aoi: str,
    slots: dict[str, Slot],
    *,
    data_dir: Path | None = None,
    data_root: Path | None = None,
    manifest: dict | None = None,
    years: list[int] | None = None,
    explicit: dict[str, Path] | None = None,
) -> dict[str, Any]:
    """Resolve a consumer's declared dependencies in one call.

    Args:
        aoi: AOI slug.
        slots: ``{slot_name: Slot(manifest_key, required, per_year)}`` —
            the consumer's ONLY dataset knowledge.
        data_dir / data_root / manifest: where to read the manifest and
            files from (data_dir wins).
        years: for ``per_year`` slots, the years each day-stack needs
            (defaults to the entry's declared numeric keys).
        explicit: ``{slot_name: Path}`` overrides — always win, validated
            to exist.

    Returns:
        ``{slot_name: Path | dict[year, Path] | None}`` — ``None`` only
        for optional slots with no manifest entry.
    """
    dd, datasets = _datasets_for(aoi, data_dir, data_root, manifest)
    explicit = explicit or {}
    out: dict[str, Any] = {}

    for slot_name, slot in slots.items():
        exp = explicit.get(slot_name)
        if exp is not None:
            exp = Path(exp)
            if not exp.exists():
                raise FileNotFoundError(
                    f"explicit input for slot '{slot_name}' not found: {exp}"
                )
            out[slot_name] = exp
            continue
        if slot.per_year:
            entry = datasets.get(slot.key)
            files: dict = entry.get("files", {}) if entry else {}
            numeric = sorted(int(k) for k in files if str(k).isdigit())
            if entry is not None and not numeric:
                # Single-file entry: usable for every requested year.
                single = resolve_dataset_file(
                    aoi, slot.key, data_dir=dd, manifest={"datasets": datasets}
                )
                out[slot_name] = single
                continue
            if entry is None:
                if slot.required:
                    raise FileNotFoundError(
                        f"required per-year input '{slot.key}' has no manifest "
                        f"entry for AOI '{aoi}' ({dd}). Run: malariasim "
                        f"download --aoi {aoi} ..."
                    )
                out[slot_name] = None
                continue
            wanted = years if years is not None else numeric
            yearly: dict[int, Path] = {}
            for y in wanted:
                p = resolve_dataset_file(
                    aoi, slot.key, year=y, data_dir=dd,
                    manifest={"datasets": datasets},
                )
                # resolve_dataset_file raises for year-keyed entries missing
                # the year; a requested year absent from the entry with
                # other years present should surface loudly as well.
                if p is None:
                    raise FileNotFoundError(
                        f"per-year input '{slot.key}' declares nothing for "
                        f"year {y} (AOI '{aoi}', {dd})."
                    )
                yearly[int(y)] = p
            out[slot_name] = yearly
            continue
        p = resolve_dataset_file(
            aoi, slot.key, data_dir=dd, manifest={"datasets": datasets}
        )
        if p is None and slot.required:
            raise FileNotFoundError(
                f"required input '{slot.key}' not found in manifest for AOI "
                f"'{aoi}' ({dd}). Run: malariasim download --aoi {aoi} ... "
                f"(or register_existing for pre-manifest data dirs)"
            )
        out[slot_name] = p
    return out


# --- catalog inspection --------------------------------------------------------

def downloadable_datasets() -> list[dict[str, Any]]:
    """Flatten the loader registry: one row per (loader output → key).

    Zero new tables: everything comes from each loader's DOWNLOADER dict.
    """
    rows: list[dict[str, Any]] = []
    for loader_name, spec in discover_downloaders().items():
        for output_name in spec.outputs:
            rows.append({
                "kind": "download",
                "key": spec.manifest_keys.get(output_name, output_name),
                "loader": loader_name,
                "output": output_name,
                "format": (spec.formats or {}).get(output_name, "monthly"),
                "in_abm_profile": (
                    spec.abm_default_outputs is None
                    or output_name in spec.abm_default_outputs
                ),
            })
    return rows


def catalog_status(
    aoi: str, *, data_root: Path | None = None
) -> list[dict[str, Any]]:
    """Compare loaders + ingest artifacts against the manifest and disk.

    One row per known dataset key: whether it is registered in the
    manifest, whether the declared file exists, and its path. This is the
    machine-readable backing for ``malariasim datasets``.
    """
    data_dir = (data_root or Path("data")) / aoi
    datasets = load_local_manifest(data_dir)
    rows: list[dict[str, Any]] = []

    def _row(kind, key, source, required=False):
        entry = datasets.get(key)
        files = entry.get("files", {}) if entry else {}
        fname = next(iter(files.values()), None) if files else None
        path = data_dir / fname if fname else None
        rows.append({
            "kind": kind,
            "key": key,
            "source": source,
            "required_for_abm": required,
            "in_manifest": entry is not None,
            "on_disk": bool(path and path.exists()),
            "path": str(path) if path else None,
        })

    for d in downloadable_datasets():
        _row("download", d["key"], f"loader:{d['loader']}.{d['output']}")
    for key, art in INGEST_ARTIFACTS.items():
        _row("artifact", key, f"ingest:{art.producer.rsplit('.', 1)[-1]}",
             required=art.required_for_abm)
    return rows


# --- legacy migration ----------------------------------------------------------

_NC_PERIOD_RE = re.compile(r"_(20\d{2})_(20\d{2})_(daily|monthly)\.nc$")
_ANNUAL_RE = re.compile(r"_(20\d{2})\.tif$")


def register_existing(
    aoi: str,
    *,
    data_dir: Path | None = None,
    data_root: Path | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """One-shot migration for pre-manifest data dirs.

    Scans the data dir for files with the loaders' conventional names
    (derived from each spec's ``formats`` + the runner naming conventions —
    the ONLY place conventional names live) and registers every file found
    into the manifest. Entries already present are never overwritten.
    Ingest artifacts (env NC, host grid, CSRs, manifests) are migrated
    too, keyed by ``INGEST_ARTIFACTS``.

    Returns ``{"registered": [...], "skipped": [...], "missing": [...],
    "dry_run": bool}`` (the would-be summary with ``dry_run=True``).
    """
    dd = Path(data_dir) if data_dir else (data_root or Path("data")) / aoi
    datasets = load_local_manifest(dd)
    registered: list[str] = []
    skipped: list[str] = []
    missing: list[str] = []

    def _register(key: str, year, fname: str, **meta):
        entry = datasets.get(key)
        if entry is not None and (
            year is None or str(year) in entry.get("files", {})
        ):
            skipped.append(f"{key} (already registered)")
            return
        if not (dd / fname).exists():
            missing.append(f"{key} -> {fname} (file not found)")
            return
        if not dry_run:
            update_dataset(aoi, key, year, fname, data_root=dd.parent, **meta)
            datasets[key] = datasets.get(key) or {}
            datasets[key].setdefault("files", {})
            if year is not None:
                datasets[key]["files"][str(year)] = fname
            else:
                datasets[key]["files"][key] = fname
        registered.append(f"{key}:{fname}")

    for loader_name, spec in discover_downloaders().items():
        for output_name in spec.outputs:
            key = spec.manifest_keys.get(output_name, output_name)
            fmt = (spec.formats or {}).get(output_name, "monthly")
            if spec.is_time_series:
                if fmt in ("daily", "monthly_nc"):
                    suffix = "daily" if fmt == "daily" else "monthly"
                    for f in sorted(dd.glob(f"{aoi}_{output_name}_*_{suffix}.nc")):
                        m = _NC_PERIOD_RE.search(f.name)
                        period = (
                            {"start": f"{m.group(1)}-01-01",
                             "end": f"{m.group(2)}-12-31"}
                            if m else None
                        )
                        _register(key, None, f.name, format="nc",
                                  type="time-series", period=period,
                                  license=spec.license,
                                  attribution=spec.attribution)
                else:
                    # Monthly/annual TIF products: one file per year.
                    for f in sorted(dd.glob(f"{aoi}_{output_name}_20*.tif")):
                        m = _ANNUAL_RE.search(f.name)
                        _register(key, int(m.group(1)) if m else None, f.name,
                                  type="time-series", license=spec.license,
                                  attribution=spec.attribution)
            else:
                f = dd / f"{aoi}_{output_name}.tif"
                if f.exists():
                    _register(key, None, f.name,
                              license=spec.license,
                              attribution=spec.attribution)

    # Ingest artifacts — conventional names mirror what each builder writes.
    artifact_patterns = {
        "env": f"{aoi}_regional_*_env.nc",
        "habitat": f"{aoi}_habitat_patches.gpkg",
        "host_static": f"{aoi}_host_static.nc",
        "host_manifest": "host_manifest.json",
        "mobility_day": f"{aoi}_mobility_day.csr",
        "mobility_night": f"{aoi}_mobility_night.csr",
        "livestock_mobility": f"{aoi}_livestock_mobility.csr",
        "mobility_manifest": "mobility_manifest.json",
    }
    for key, pattern in artifact_patterns.items():
        candidates = sorted(dd.glob(pattern))
        if not candidates:
            missing.append(f"{key} -> {pattern}")
            continue
        _register(key, None, candidates[0].name,
                  required_for_abm=INGEST_ARTIFACTS[key].required_for_abm)

    return {
        "registered": registered,
        "skipped": skipped,
        "missing": missing,
        "dry_run": dry_run,
    }
