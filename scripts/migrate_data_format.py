"""Migrate data/ghana/ to standard naming convention.

Renames files to <aoi>_<product>_<year>.<ext> (time-series) or
<aoi>_<product>.<ext> (static), updates manifest to v2, cleans up
Phase 1 artifacts.

Idempotent: skips files that are already renamed.
"""
import json
import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "data" / "ghana"

# Rename map: old_name -> new_name (None = delete)
RENAMES = {
    "ghana_regional_2024_06_habitat_patches.gpkg": "ghana_habitat.gpkg",
    "host_static.nc": "ghana_host_static.nc",
    "host_manifest.json": "ghana_host_manifest.json",
    "human_mobility_day.csr": "ghana_mobility_day.csr",
    "human_mobility_night.csr": "ghana_mobility_night.csr",
    "livestock_mobility_season.csr": "ghana_livestock_mobility.csr",
    "wind_era5_6hourly_2024.nc": "ghana_wind_2024.nc",
    "wind_era5_6hourly_2025.nc": "ghana_wind_2025.nc",
    # Phase 1 artifacts: delete
    "wind_era5_6hourly_2024_2025.nc": None,  # merged artifact
    "wind_era5_monthly_mean_2024.nc": None,   # Phase 1
    "wind_era5_monthly_mean_2024.tif": None,   # Phase 1
}

# Phase 1 artifact directories to delete
PHASE1_DIRS = ["wind_era5_monthly"]


def migrate():
    print("=== Migrating data/ghana/ to standard naming ===")

    # Step 1: Rename files
    for old, new in RENAMES.items():
        old_path = DATA / old
        if not old_path.exists():
            print(f"  SKIP (not found): {old}")
            continue
        if new is None:
            if old_path.is_dir():
                shutil.rmtree(old_path)
            else:
                old_path.unlink()
            print(f"  DELETE: {old}")
        else:
            new_path = DATA / new
            if new_path.exists():
                print(f"  SKIP (target exists): {old} -> {new}")
                continue
            old_path.rename(new_path)
            print(f"  RENAME: {old} -> {new}")

    # Step 2: Delete Phase 1 directories
    for dirname in PHASE1_DIRS:
        dir_path = DATA / dirname
        if dir_path.exists():
            shutil.rmtree(dir_path)
            print(f"  DELETE DIR: {dirname}")

    # Step 3: Update manifest to v2
    manifest_path = DATA / "manifest.json"
    if manifest_path.exists():
        with open(manifest_path) as f:
            manifest = json.load(f)
    else:
        manifest = {"aoi": "ghana", "name": "Ghana NMCP AOI"}

    # Build v2 datasets block
    manifest["datasets"] = {
        "env": {
            "type": "time-series",
            "format": "nc",
            "temporal": {"freq": "daily"},
            "files": {
                "2024": "ghana_regional_2024_2025_env.nc",
                "2025": "ghana_regional_2024_2025_env.nc",
            },
            "variables": ["rainfall", "water_temp_c", "water_frac", "ndvi"],
            "required_for_abm": True,
        },
        "wind": {
            "type": "time-series",
            "format": "nc",
            "temporal": {"freq": "6hourly"},
            "files": {
                "2024": "ghana_wind_2024.nc",
                "2025": "ghana_wind_2025.nc",
            },
            "variables": ["u100", "v100"],
            "required_for_abm": False,
        },
        "habitat": {
            "type": "static",
            "format": "gpkg",
            "files": {"habitat": "ghana_habitat.gpkg"},
            "required_for_abm": True,
        },
        "host_static": {
            "type": "static",
            "format": "nc",
            "files": {"host_static": "ghana_host_static.nc"},
            "required_for_abm": True,
        },
        "host_manifest": {
            "type": "static",
            "format": "json",
            "files": {"host_manifest": "ghana_host_manifest.json"},
            "required_for_abm": True,
        },
        "mobility_day": {
            "type": "static",
            "format": "csr",
            "files": {"mobility_day": "ghana_mobility_day.csr"},
            "required_for_abm": False,
        },
        "mobility_night": {
            "type": "static",
            "format": "csr",
            "files": {"mobility_night": "ghana_mobility_night.csr"},
            "required_for_abm": False,
        },
        "livestock_mobility": {
            "type": "static",
            "format": "csr",
            "files": {"livestock_mobility": "ghana_livestock_mobility.csr"},
            "required_for_abm": False,
        },
    }

    # Build expected_files
    all_files = []
    for ds in manifest["datasets"].values():
        all_files.extend(ds.get("files", {}).values())
    manifest["expected_files"] = sorted(set(all_files))

    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"  MANIFEST: updated to v2 ({len(manifest['datasets'])} datasets)")

    print("\n=== Migration complete ===")


if __name__ == "__main__":
    migrate()
