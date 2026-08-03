"""Auto-managed AOI manifest — updates data/<aoi>/manifest.json after downloads.

Supports v1 (flat files dict) and v2 (datasets block) schemas.
Reads auto-migrate v1 → v2 in memory; writes always produce v2.
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


def read_manifest(aoi: str) -> dict:
    """Read manifest. Handles both v1 (flat files) and v2 (datasets block)."""
    path = DATA_ROOT / aoi / "manifest.json"
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
    period: dict[str, str] | None = None,
    **kwargs,
) -> Path:
    """Update a specific dataset entry in the manifest.

    Parameters
    ----------
    period:
        Optional dict with ``"start"`` and ``"end"`` keys (ISO date strings)
        for multi-year entries where ``year`` is ``None``.
        Example: ``{"start": "2024-01-01", "end": "2025-12-31"}``.

    kwargs accepted (forward-compat for Phase 3): type, required_for_abm, variables, format.
    """
    path = DATA_ROOT / aoi / "manifest.json"
    manifest = read_manifest(aoi)
    if dataset_name not in manifest.get("datasets", {}):
        manifest.setdefault("datasets", {})[dataset_name] = {
            "type": kwargs.get("type", "time-series"),
            "format": filename.rsplit(".", 1)[-1],
            "files": {},
        }
    ds = manifest["datasets"][dataset_name]

    # Store period metadata when provided (multi-year / daily outputs)
    if period is not None:
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


def validate_completeness(aoi: str) -> list[str]:
    """Return list of missing expected files. Empty = complete."""
    manifest = read_manifest(aoi)
    data_dir = DATA_ROOT / aoi
    missing = []
    for f in manifest.get("expected_files", []):
        if not (data_dir / f).exists():
            missing.append(f)
    return missing


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
