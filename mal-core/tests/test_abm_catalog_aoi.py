"""Catalog AOIs must reach the C++ engine with their aois.yaml bbox.

The C++ binary only knows ``ghana`` natively; every other catalog slug
(``accra-coastal-test``, future regions) must receive the registry bbox,
resolution and scale from the Python wrapper.  Without this the run aborts
with ``unknown --aoi slug`` even though ``malariasim datasets`` reports the
AOI as complete.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from mal_commonlib.aoi import AOI


def _run_manifest(tmp_path: Path, **kwargs):
    from mal_core.abm.wrapper import run_abm_from_manifest

    captured: dict = {}

    def fake_run(**flags):
        captured.update(flags)
        return {"stdout": "", "stderr": "", "returncode": 0}

    with (
        patch(
            "mal_core.download.manifest.validate_completeness",
            return_value=[],
        ),
        patch("mal_core.download.catalog.resolve", return_value=tmp_path / "x"),
        patch("mal_core.abm.wrapper.CppAbmWrapper") as wrapper_cls,
    ):
        wrapper_cls.return_value.run.side_effect = fake_run
        run_abm_from_manifest(
            aoi="accra-coastal-test",
            days=1,
            output_dir=tmp_path,
            data_root=tmp_path,
            **kwargs,
        )
    return captured


def test_catalog_slug_forwards_registry_bbox_resolution_scale(tmp_path):
    flags = _run_manifest(tmp_path)
    aoi = AOI.from_slug("accra-coastal-test")

    assert flags["bbox"] == ",".join(f"{coord:g}" for coord in aoi.bbox)
    assert flags["resolution_m"] == aoi.resolution_m
    assert flags["scale"] == aoi.scale.value


def test_explicit_bbox_is_not_overridden(tmp_path):
    flags = _run_manifest(tmp_path, bbox="1,2,3,4")
    assert flags["bbox"] == "1,2,3,4"
