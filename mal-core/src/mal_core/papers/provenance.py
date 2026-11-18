"""Per-paper ``provenance.yaml`` and file checksums.

Every paper folder holds a ``provenance.yaml`` written by the tool: the observed
status, where the PDF came from, its sha256, and the docling version and device
used for extraction. Updates merge into the existing file, so the fetch and
extract steps can run independently.
"""

from __future__ import annotations

import hashlib
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

PROVENANCE_NAME = "provenance.yaml"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path, chunk_size: int = 1 << 20) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def read_provenance(paper_dir: Path) -> dict[str, Any]:
    path = paper_dir / PROVENANCE_NAME
    if not path.is_file():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def read_observed_status(paper_dir: Path) -> str | None:
    """The observed status the tool last recorded for a paper, or None if none is recorded.

    Observed status is not a manifest field (plan §6.2): it lives here, written by fetch and extract.
    """
    value = read_provenance(paper_dir).get("observed_status")
    return value if isinstance(value, str) else None


def update_provenance(paper_dir: Path, **blocks: Any) -> Path:
    """Merge ``blocks`` into the paper's provenance file and write it atomically."""
    paper_dir.mkdir(parents=True, exist_ok=True)
    data = read_provenance(paper_dir)
    data.update(blocks)
    path = paper_dir / PROVENANCE_NAME
    tmp = path.with_name(path.name + ".part")
    tmp.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    os.replace(tmp, path)
    return path
