"""Shared helpers for the ingest stage."""
from __future__ import annotations

import json
from pathlib import Path


def register_dataset(
    aoi_slug: str,
    dataset_name: str,
    year: int | str | None,
    filename: str,
    *,
    type: str = "static",
    required_for_abm: bool = False,
    variables: list[str] | None = None,
    format: str | None = None,
    data_root: Path | None = None,
) -> None:
    """Register a build output in the central manifest."""
    from mal_core.download.manifest import read_manifest, update_dataset

    update_dataset(aoi_slug, dataset_name, year, filename, type=type, required_for_abm=required_for_abm, variables=variables, format=format, data_root=data_root)

    manifest = read_manifest(aoi_slug)
    ds = manifest.get("datasets", {}).get(dataset_name, {})
    if required_for_abm:
        ds["required_for_abm"] = True
    if variables:
        ds["variables"] = variables
    if format:
        ds["format"] = format

    manifest_path = Path("data") / aoi_slug / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
