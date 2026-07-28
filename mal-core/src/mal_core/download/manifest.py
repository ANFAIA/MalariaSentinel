"""Auto-managed AOI manifest — updates data/<aoi>/manifest.json after downloads."""
from __future__ import annotations
import json
import logging
from pathlib import Path

log = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_ROOT = _REPO_ROOT / "data"

def read_manifest(aoi: str) -> dict:
    path = DATA_ROOT / aoi / "manifest.json"
    if not path.exists():
        return {"aoi": aoi, "name": "", "files": {}, "grid": {}}
    with open(path) as f:
        return json.load(f)

def update_manifest(aoi: str, key: str, filename: str) -> Path:
    path = DATA_ROOT / aoi / "manifest.json"
    manifest = read_manifest(aoi)
    manifest["files"][key] = filename
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(manifest, f, indent=2)
    log.info("Manifest updated: %s[%s] = %s", aoi, key, filename)
    return path

def list_files(aoi: str) -> dict[str, str]:
    return read_manifest(aoi).get("files", {})
