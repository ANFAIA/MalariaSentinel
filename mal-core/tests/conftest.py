"""Shared test fixtures for mal-core tests."""
from __future__ import annotations

import json

import pytest


@pytest.fixture
def write_manifest():
    """Write a manifest.json (v3.1 datasets block) into a tmp data dir.

    Since the catalog went manifest-only (2026-10-04), tests must register
    the files they write — which also proves resolution honours the
    manifest regardless of the filenames used.
    """
    def _write(data_dir, datasets: dict, period: dict | None = None) -> None:
        """datasets: {manifest_key: filename | {year: filename}}."""
        block = {}
        for key, val in datasets.items():
            files = val if isinstance(val, dict) else {key: val}
            entry = {"files": files}
            if period is not None:
                entry["period"] = period
            block[key] = entry
        (data_dir / "manifest.json").write_text(
            json.dumps({"datasets": block})
        )
    return _write
