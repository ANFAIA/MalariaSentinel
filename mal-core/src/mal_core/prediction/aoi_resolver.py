"""AOI data resolver — maps AOI slug to data file paths.

Convention: each AOI has a directory under data/<aoi>/ with a manifest.json
listing available files. This module resolves paths from the manifest so no
code needs to hardcode "data/ghana/...".
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]


@dataclass
class AOIFiles:
    """Resolved file paths for an AOI."""
    aoi: str
    data_dir: Path
    env: Path | None = None
    habitat: Path | None = None
    hosts: Path | None = None
    mobility_day: Path | None = None
    mobility_night: Path | None = None
    livestock_mobility: Path | None = None

    def exists(self, key: str) -> bool:
        p = getattr(self, key, None)
        return p is not None and p.exists()

    def required_args(self) -> dict[str, str]:
        """Return ABM CLI flags for files that exist."""
        args: dict[str, str] = {}
        mapping = {
            "env": "--env",
            "habitat": "--habitat",
            "hosts": "--hosts",
            "mobility_day": "--human-mobility-day",
            "mobility_night": "--human-mobility-night",
            "livestock_mobility": "--livestock-mobility",
        }
        for attr, flag in mapping.items():
            p = getattr(self, attr, None)
            if p and p.exists():
                args[flag] = str(p)
        return args


def resolve_aoi(aoi_slug: str, data_root: Path | None = None) -> AOIFiles:
    """Resolve data file paths for an AOI from its manifest.json.

    Looks for data/<aoi>/manifest.json. Each key in the manifest's "files"
    dict is resolved relative to the AOI data directory.

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
        # Fallback: convention-based resolution without manifest
        return _fallback_resolve(aoi_slug, aoi_dir)

    with open(manifest_path) as f:
        manifest = json.load(f)

    files = manifest.get("files", {})
    return AOIFiles(
        aoi=aoi_slug,
        data_dir=aoi_dir,
        env=aoi_dir / files.get("env") if files.get("env") else None,
        habitat=aoi_dir / files.get("habitat") if files.get("habitat") else None,
        hosts=aoi_dir / files.get("hosts") if files.get("hosts") else None,
        mobility_day=aoi_dir / files.get("mobility_day") if files.get("mobility_day") else None,
        mobility_night=aoi_dir / files.get("mobility_night") if files.get("mobility_night") else None,
        livestock_mobility=aoi_dir / files.get("livestock_mobility") if files.get("livestock_mobility") else None,
    )


def _fallback_resolve(aoi_slug: str, aoi_dir: Path) -> AOIFiles:
    """Convention-based fallback: look for common filenames."""
    env = None
    for candidate in sorted(aoi_dir.glob("*env*.nc")):
        env = candidate
        break

    habitat = None
    for candidate in sorted(aoi_dir.glob("*habitat*.gpkg")):
        habitat = candidate
        break

    hosts = aoi_dir / "host_static.nc" if (aoi_dir / "host_static.nc").exists() else None

    return AOIFiles(
        aoi=aoi_slug,
        data_dir=aoi_dir,
        env=env,
        habitat=habitat,
        hosts=hosts,
    )
