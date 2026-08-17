"""Auto-managed AOI manifest — updates data/<aoi>/manifest.json after downloads.

Supports v1 (flat files dict), v2 (datasets block), and v3.1 schemas.
Reads auto-migrate v1 → v2 in memory; writes always produce v3.1.
"""
from __future__ import annotations
import json
import logging
from pathlib import Path

log = logging.getLogger(__name__)

def _find_repo_root() -> Path:
    """Walk up from this file to find the repo root (has opencode.json or .git)."""
    p = Path(__file__).resolve().parent
    for _ in range(10):
        if (p / "opencode.json").exists() or (p / ".git").exists():
            return p
        p = p.parent
    return Path(__file__).resolve().parents[4]

_REPO_ROOT = _find_repo_root()
DATA_ROOT = _REPO_ROOT / "data"


def read_manifest(aoi: str, data_root: Path | None = None) -> dict:
    """Read manifest. Handles both v1 (flat files) and v2 (datasets block)."""
    path = (data_root or DATA_ROOT) / aoi / "manifest.json"
    if not path.exists():
        return {"aoi": aoi, "datasets": {}, "expected_files": []}
    with open(path) as f:
        manifest = json.load(f)
    if "datasets" not in manifest and "files" in manifest:
        manifest = _migrate_v1_to_v2(manifest)
    return manifest


def _migrate_v1_to_v2(manifest: dict) -> dict:
    """Convert v1 flat files dict to v2 datasets block."""
    files = manifest.get("files", {})
    datasets = {}
    for key, filename in files.items():
        if any(x in key for x in ["habitat", "host", "mobility"]):
            dtype = "static"
        else:
            dtype = "time-series"
        datasets[key] = {
            "type": dtype,
            "format": filename.rsplit(".", 1)[-1] if "." in filename else "unknown",
            "files": {key: filename},
        }
    manifest["datasets"] = datasets
    manifest["expected_files"] = list(files.values())
    return manifest


def update_manifest(aoi: str, key: str, filename: str) -> Path:
    """Update a flat-key entry (legacy compat). Delegates to update_dataset."""
    return update_dataset(aoi, key, None, filename)


def update_dataset(
    aoi: str,
    dataset_name: str,
    year: int | str | None,
    filename: str,
    *,
    type: str = "time-series",
    required_for_abm: bool = False,
    variables: list[str] | None = None,
    format: str | None = None,
    period: dict[str, str] | None = None,
    data_root: Path | None = None,
) -> Path:
    """Update a specific dataset entry in the manifest.

    Args:
        aoi: AOI slug.
        dataset_name: dataset key (e.g. "chirps_rainfall_daily").
        year: year for per-year entries, or None for multi-year NC.
        filename: output filename.
        type: "static" | "time-series".
        required_for_abm: whether this dataset is required for ABM runs.
        variables: list of variable names in the file.
        format: file format ("tif" | "nc" | "gpkg" | "csr").
        period: for multi-year NC, {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"}.
    """
    root = data_root or DATA_ROOT
    path = root / aoi / "manifest.json"
    manifest = read_manifest(aoi, root)
    if dataset_name not in manifest.get("datasets", {}):
        manifest.setdefault("datasets", {})[dataset_name] = {
            "type": type,
            "format": format or filename.rsplit(".", 1)[-1],
            "required_for_abm": required_for_abm,
            "files": {},
        }
    ds = manifest["datasets"][dataset_name]
    # Update metadata fields
    ds["type"] = type
    if format:
        ds["format"] = format
    ds["required_for_abm"] = required_for_abm
    if variables:
        ds["variables"] = variables
    if period:
        ds["period"] = period

    if year:
        ds.setdefault("files", {})[str(year)] = filename
    else:
        ds.setdefault("files", {})[dataset_name] = filename

    all_files = []
    for d in manifest.get("datasets", {}).values():
        all_files.extend(d.get("files", {}).values())
    manifest["expected_files"] = sorted(set(all_files))
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(manifest, f, indent=2)
    log.info("Manifest updated: %s[%s] = %s", aoi, dataset_name, filename)
    return path


def list_files(aoi: str) -> dict[str, str]:
    """Return flat filename dict (v1 compat)."""
    manifest = read_manifest(aoi)
    datasets = manifest.get("datasets", {})
    flat = {}
    for ds in datasets.values():
        flat.update(ds.get("files", {}))
    return flat


def validate_completeness(aoi: str, *, years: list[int] | None = None, data_root: Path | None = None) -> list[str]:
    """Return list of missing expected files. Empty = complete.

    For daily NC entries with a ``period`` field, checks that the
    period covers the requested years rather than individual file existence.
    """
    root = data_root or DATA_ROOT
    manifest = read_manifest(aoi, root)
    data_dir = root / aoi
    missing = []

    for ds_name, ds in manifest.get("datasets", {}).items():
        period = ds.get("period")
        if period and years:
            # Daily NC entry: check period covers requested years
            period_start = period.get("start", "")
            period_end = period.get("end", "")
            if period_start and period_end:
                start_year = int(period_start[:4])
                end_year = int(period_end[:4])
                for y in years:
                    if y < start_year or y > end_year:
                        missing.append(
                            f"{ds_name}: period {period_start}..{period_end} "
                            f"does not cover year {y}"
                        )
                # Also check that at least one file exists
                files = ds.get("files", {})
                if not any((data_dir / f).exists() for f in files.values()):
                    for f in files.values():
                        if not (data_dir / f).exists():
                            missing.append(f)
            else:
                # Incomplete period metadata
                for f in ds.get("files", {}).values():
                    if not (data_dir / f).exists():
                        missing.append(f)
        else:
            # Standard per-file check
            for f in ds.get("files", {}).values():
                if not (data_dir / f).exists():
                    missing.append(f)

    # Also check legacy expected_files list
    for f in manifest.get("expected_files", []):
        if f not in missing and not (data_dir / f).exists():
            missing.append(f)

    return sorted(set(missing))


def get_dataset_files(aoi: str, dataset_name: str, year: int | str | None = None) -> list[Path]:
    """Get file paths for a dataset, optionally filtered by year."""
    manifest = read_manifest(aoi)
    ds = manifest.get("datasets", {}).get(dataset_name)
    if not ds:
        return []
    data_dir = DATA_ROOT / aoi
    if year:
        fname = ds.get("files", {}).get(str(year))
        return [data_dir / fname] if fname else []
    return [data_dir / f for f in ds.get("files", {}).values()]
