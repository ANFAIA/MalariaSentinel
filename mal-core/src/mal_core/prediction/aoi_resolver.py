"""AOI data resolver — maps AOI slug to data file paths.

Convention: each AOI has a directory under data/<aoi>/ with a manifest.json
listing available files. This module resolves paths from the manifest so no
code needs to hardcode "data/ghana/...".

Supports manifest v2 (datasets block) and v1 (flat files dict).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

def _find_repo_root() -> Path:
    """Walk up from this file to find the repo root (has opencode.json or .git)."""
    p = Path(__file__).resolve().parent
    for _ in range(10):
        if (p / "opencode.json").exists() or (p / ".git").exists():
            return p
        p = p.parent
    return Path(__file__).resolve().parents[4]

_REPO_ROOT = _find_repo_root()


@dataclass
class AOIFiles:
    """Resolved file paths for an AOI from manifest v2."""
    aoi: str
    data_dir: Path
    datasets: dict[str, dict]  # dataset_name → {type, format, files, ...}

    def get_files(self, dataset_name: str, year: int | str | None = None) -> list[Path]:
        ds = self.datasets.get(dataset_name)
        if not ds:
            return []
        if year:
            fname = ds.get("files", {}).get(str(year))
            return [self.data_dir / fname] if fname else []
        return [self.data_dir / f for f in ds.get("files", {}).values()]

    def exists(self, key: str) -> bool:
        files = self.get_files(key)
        return any(f.exists() for f in files)

    def required_args(self) -> dict[str, str]:
        """Return ABM CLI flags for files that exist."""
        args: dict[str, str] = {}
        mapping = {
            "env": "--env",
            "habitat": "--habitat",
            "host_static": "--hosts",
            "mobility_day": "--human-mobility-day",
            "mobility_night": "--human-mobility-night",
            "livestock_mobility": "--livestock-mobility",
        }
        for ds_name, flag in mapping.items():
            files = self.get_files(ds_name)
            for f in files:
                if f.exists():
                    args[flag] = str(f)
                    break
        return args


def resolve_aoi(aoi_slug: str, data_root: Path | None = None) -> AOIFiles:
    """Resolve data file paths for an AOI from its manifest.json.

    Looks for data/<aoi>/manifest.json. Supports both v1 and v2 schemas.

    Args:
        aoi_slug: AOI identifier (e.g. "ghana", "morocco").
        data_root: Override the data root (default: <repo>/data/).

    Returns:
        AOIFiles with resolved paths (files may not exist yet).
    """
    root = data_root or (_REPO_ROOT / "data")
    aoi_dir = root / aoi_slug
    manifest_path = aoi_dir / "manifest.json"

    if not manifest_path.exists():
        return _fallback_resolve(aoi_slug, aoi_dir)

    with open(manifest_path) as f:
        manifest = json.load(f)

    # Migrate v1 → v2 in memory
    if "datasets" not in manifest and "files" in manifest:
        manifest = _migrate_v1_to_v2(manifest)

    datasets = manifest.get("datasets", {})
    return AOIFiles(
        aoi=aoi_slug,
        data_dir=aoi_dir,
        datasets=datasets,
    )


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
    return manifest


def _fallback_resolve(aoi_slug: str, aoi_dir: Path) -> AOIFiles:
    """Convention-based fallback: look for common filenames."""
    datasets: dict[str, dict] = {}

    for candidate in sorted(aoi_dir.glob("*env*.nc")):
        datasets["env"] = {
            "type": "time-series",
            "format": "nc",
            "files": {"env": candidate.name},
        }
        break

    for candidate in sorted(aoi_dir.glob("*habitat*.gpkg")):
        datasets["habitat"] = {
            "type": "static",
            "format": "gpkg",
            "files": {"habitat": candidate.name},
        }
        break

    if (aoi_dir / "host_static.nc").exists():
        datasets["host_static"] = {
            "type": "static",
            "format": "nc",
            "files": {"host_static": "host_static.nc"},
        }

    return AOIFiles(
        aoi=aoi_slug,
        data_dir=aoi_dir,
        datasets=datasets,
    )
